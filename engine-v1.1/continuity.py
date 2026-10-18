#!/usr/bin/env python3
"""Continue a verified published game using v1 in an isolated clone.
This wrapper is not AI. It relays a real independent agent's JSON acknowledgement.
No new credentials, model API, scheduling service, or original-file edits.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import select
import signal
import shutil
import subprocess
import sys
import time
import zipfile


_DEADLINE = None
_SOURCE_CACHE = {}


class ContinuityError(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise ContinuityError('Invalid game/run ID.')
    return value


def git(repo, *args, input=None, env=None, timeout=60):
    if _DEADLINE is not None:
        timeout = min(timeout, left(_DEADLINE))
    return subprocess.run(['git', *args], cwd=repo, input=input, env=env,
                          capture_output=True, check=True, timeout=timeout).stdout


def blob(repo, ref, path):
    if not isinstance(path, str) or Path(path).is_absolute() or '..' in Path(path).parts:
        raise ContinuityError('Unsafe repository path.')
    mode = git(repo, 'ls-tree', ref, '--', path).decode().split()
    if len(mode) < 4 or mode[0] != '100644' or mode[1] != 'blob':
        raise ContinuityError('Missing/nonregular Git blob: '+path)
    return git(repo, 'show', f'{ref}:{path}')


def ancestor(repo, a, b):
    p = subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], cwd=repo,
                       capture_output=True, timeout=min(60, left(_DEADLINE)) if _DEADLINE else 60)
    if p.returncode not in (0, 1):
        raise ContinuityError('Cannot determine Git ancestry.')
    return p.returncode == 0


def choose_latest(releases, is_ancestor):
    """Select by commit ancestry only; an ambiguous branch is never guessed."""
    latest = None
    for release in releases:
        if latest is None:
            latest = release
        elif latest['commit'] == release['commit']:
            if latest['path'] != release['path']:
                raise ContinuityError('Multiple releases in one publication commit.')
        elif is_ancestor(latest['commit'], release['commit']):
            latest = release
        elif not is_ancestor(release['commit'], latest['commit']):
            raise ContinuityError('Published releases have incomparable Git ancestry.')
    return latest


def verify_release(repo, ref, relative, config=None):
    """Verify immutable publisher output from Git objects, never working files."""
    repo = Path(repo)
    parts = Path(relative).parts
    if len(parts) != 4 or parts[:2] != ('engine-v1', 'releases'):
        raise ContinuityError('Invalid release path.')
    game_id, run_id = map(identifier, parts[2:])
    required = ['game.html', 'game.zip', 'report.json', 'PUBLISHED.json']
    data = {name: blob(repo, ref, f'{relative}/{name}') for name in required}
    report, receipt = json.loads(data['report.json']), json.loads(data['PUBLISHED.json'])
    if report.get('status') != 'LOCAL_PASS_AWAITING_GITHUB' or receipt.get('status') != 'GITHUB_PUBLISHED':
        raise ContinuityError('Release is not both locally passing and published: '+relative)
    for record in (report, receipt):
        if record.get('game_id') != game_id or record.get('run_id') != run_id:
            raise ContinuityError('Release/receipt IDs differ: '+relative)
    html_sha = sha(data['game.html'])
    if (not data['game.html'].strip() or report.get('validated_sha256') != html_sha
            or receipt.get('game_sha256') != html_sha
            or receipt.get('report_sha256') != sha(data['report.json'])):
        raise ContinuityError('Release or receipt hash mismatch: '+relative)
    # A publisher adds these four blobs atomically in exactly one single-parent
    # commit. Their bytes must be unchanged at the currently selected remote ref.
    history = git(repo, 'log', '--format=%H', '--diff-filter=A', ref, '--', relative+'/PUBLISHED.json').decode().splitlines()
    if len(history) != 1:
        raise ContinuityError('Receipt has ambiguous/missing introduction commit.')
    commit = history[0]
    parent_line = git(repo, 'rev-list', '--parents', '-n', '1', commit).decode().split()
    if len(parent_line) != 2 or receipt.get('parent_main') != parent_line[1]:
        raise ContinuityError('Receipt parent_main does not match publication ancestry.')
    changes = git(repo, 'diff-tree', '-r', '--no-commit-id', '--name-status', parent_line[1], commit).decode().splitlines()
    expected = {'A\t'+relative+'/'+name for name in required}
    if set(changes) != expected or len(changes) != 4:
        raise ContinuityError('Publication commit was not exactly four new release files.')
    for name in required:
        if blob(repo, commit, f'{relative}/{name}') != data[name]:
            raise ContinuityError('A previously published release was changed: '+relative)
    historical_config = json.loads(blob(repo, commit, f'engine-v1/games/{game_id}.json'))
    config_bytes = blob(repo, commit, f'engine-v1/games/{game_id}.json')
    if report.get('config_sha256') != sha(config_bytes):
        raise ContinuityError('Release configuration hash differs from publication registry.')
    if historical_config.get('id') != game_id:
        raise ContinuityError('Registry ID mismatch.')
    attempts = report.get('attempts', [])
    if not attempts or attempts[-1].get('status') != 'PASS' or attempts[-1].get('candidate_sha256') != html_sha:
        raise ContinuityError('No verified passing candidate attempt.')
    tests = attempts[-1].get('tests', [])
    expected_tests = ['common-static', 'common-browser']+[t['id'] for t in historical_config['specific_tests']]
    if [t.get('id') for t in tests] != expected_tests or any(t.get('status') != 'PASS' or t.get('exit_code') != 0 for t in tests):
        raise ContinuityError('Required tests were not all passing.')
    with zipfile.ZipFile(io.BytesIO(data['game.zip'])) as archive:
        if (set(archive.namelist()) != {'game.html', 'report.json'} or archive.testzip() is not None
                or archive.read('game.html') != data['game.html'] or archive.read('report.json') != data['report.json']):
            raise ContinuityError('Release ZIP differs from tested HTML/report.')
    lineage = report.get('continuity')
    if lineage:
        if report.get('source_sha256') != lineage.get('source_sha256'):
            raise ContinuityError('Inherited source SHA differs from continuity evidence.')
        path = lineage.get('source_path')
        source_commit = lineage.get('source_ref_commit')
        if not source_commit or not ancestor(repo, source_commit, parent_line[1]):
            raise ContinuityError('Inherited source revision is outside publication ancestry.')
        if sha(blob(repo, source_commit, path)) != lineage['source_sha256']:
            raise ContinuityError('Inherited source evidence does not match Git bytes.')
        inherited_source = select_source(repo, game_id, source_commit)
        if (inherited_source['path'] != path or inherited_source['sha256'] != lineage['source_sha256']
                or inherited_source['commit'] != lineage.get('source_publication_commit')
                or inherited_source['kind'] != lineage.get('source_kind')):
            raise ContinuityError('Continuity did not inherit the latest verified source at its base revision.')
    return {'kind': 'release', 'path': relative+'/game.html', 'release': relative,
            'sha256': html_sha, 'commit': commit, 'config_sha256': sha(config_bytes)}


def select_source(repo, game_id, ref='origin/main'):
    repo = Path(repo)
    game_id = identifier(game_id)
    ref_commit = git(repo, 'rev-parse', '--verify', ref+'^{commit}').decode().strip()
    cache_key = (str(repo.resolve()), game_id, ref_commit)
    if cache_key in _SOURCE_CACHE:
        return dict(_SOURCE_CACHE[cache_key])
    config_path = f'engine-v1/games/{game_id}.json'
    config_bytes = blob(repo, ref_commit, config_path)
    config = json.loads(config_bytes)
    if config.get('id') != game_id:
        raise ContinuityError('Registry ID mismatch.')
    names = git(repo, 'ls-tree', '-r', '--name-only', ref_commit, '--', f'engine-v1/releases/{game_id}/').decode().splitlines()
    receipt_paths = [name for name in names if name.endswith('/PUBLISHED.json')]
    verified = [verify_release(repo, ref_commit, name.rsplit('/', 1)[0], config) for name in receipt_paths]
    result = choose_latest(verified, lambda a, b: ancestor(repo, a, b))
    if result is None:
        data = blob(repo, ref_commit, config['source'])
        if not data.strip():
            raise ContinuityError('Registry source is empty.')
        result = {'kind': 'registry', 'path': config['source'], 'sha256': sha(data),
                  'commit': ref_commit, 'config_sha256': sha(config_bytes)}
    # A registry with changed rules/tests needs an explicit new game ID/version;
    # silently continuing an old validated game under a changed contract is blocked.
    if result['config_sha256'] != sha(config_bytes):
        raise ContinuityError('Registry changed since accepted release; register a new game/version.')
    selected = {**result, 'ref_commit': ref_commit, 'game_id': game_id}
    _SOURCE_CACHE[cache_key] = selected
    return dict(selected)


def emit(event, **data):
    print(json.dumps({'event': event, **data}, ensure_ascii=False), flush=True)


def left(deadline):
    value = deadline-time.monotonic()
    if value <= 0:
        raise ContinuityError('60-minute overall deadline exceeded, including AI waiting.')
    return value


def read_json_line(stream, deadline):
    line = bytearray()
    while True:
        if not select.select([stream.fileno()], [], [], left(deadline))[0]:
            raise ContinuityError('AI bridge timed out.')
        byte = os.read(stream.fileno(), 1)
        if not byte:
            raise ContinuityError('AI bridge closed before acknowledgement.')
        if byte == b'\n':
            return json.loads(line.decode('utf-8'))
        line.extend(byte)
        if len(line) > 100000:
            raise ContinuityError('AI bridge acknowledgement too large.')


def snapshot(repo):
    names = git(repo, 'ls-files', '-z').split(b'\0')
    paths = {repo/os.fsdecode(p) for p in names if p}
    paths.update(p for p in (repo/'engine-v1.1').rglob('*') if p.is_file() or p.is_symlink())
    def sig(p):
        if p.is_symlink():
            return ['symlink', os.readlink(p)]
        return ['file', sha(p.read_bytes()), p.stat().st_mode & 0o777] if p.is_file() else ['missing']
    frozen = {str(p): sig(p) for p in paths}
    head = git(repo, 'rev-parse', 'HEAD')
    def check():
        changed = [p for p, value in frozen.items() if sig(Path(p)) != value]
        if git(repo, 'rev-parse', 'HEAD') != head:
            changed.append('HEAD')
        if changed:
            raise ContinuityError('Authoritative original/tracked/config/test changed: '+', '.join(changed[:10]))
    return check


def same_source(a, b):
    return all(a.get(k) == b.get(k) for k in ('kind', 'path', 'sha256', 'commit', 'config_sha256'))


def publish_legacy(sandbox, relative, source, game_id, deadline):
    """Call unmodified v1 publisher; check same-game lineage on EVERY fetch.

    If another same-game publication wins between validation and push, v1's
    non-force rejection triggers fetch and this guard blocks its stale retry.
    """
    spec = importlib.util.spec_from_file_location('legacy_add_only_publisher', sandbox/'engine-v1/publish.py')
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    expected_html = sha((sandbox/relative/'game.html').read_bytes())
    def guarded_git(*args, env=None, input=None):
        output = git(sandbox, *args, env=env, input=input.encode() if isinstance(input, str) else input,
                     timeout=left(deadline)).decode().strip()
        if args[:3] == ('fetch', 'origin', 'main'):
            now = select_source(sandbox, game_id)
            own_release = now.get('release') == relative and now['sha256'] == expected_html
            if not same_source(now, source) and not own_release:
                raise ContinuityError('A newer same-game release appeared; stale publication blocked.')
        return output
    publisher.git = guarded_git
    return publisher.publish(relative)


def save_record(repo, record, deadline):
    """Add record + recording receipt only; never edit/delete remote paths."""
    game_id, run_id = identifier(record['game_id']), identifier(record['run_id'])
    remote = git(repo, 'remote', 'get-url', 'origin', timeout=left(deadline)).decode().strip()
    if remote != 'https://github.com/verdiwagner1813-ai/mini-game-lab.git':
        raise ContinuityError('Unexpected publication remote.')
    relative = f'engine-v1.1/runs/{game_id}/{run_id}'
    content = (json.dumps(record, ensure_ascii=False, indent=2)+'\n').encode()
    for retry in range(3):
        git(repo, 'fetch', 'origin', 'main', timeout=left(deadline))
        base = git(repo, 'rev-parse', 'origin/main', timeout=left(deadline)).decode().strip()
        paths = [relative+'/record.json', relative+'/RECORDED.json']
        for path in paths:
            if git(repo, 'ls-tree', base, '--', path, timeout=left(deadline)).strip():
                raise ContinuityError('Run record exists remotely; refusing overwrite: '+path)
        receipt = {'status': 'GITHUB_RECORDED', 'game_id': game_id, 'run_id': run_id,
                   'record_sha256': sha(content), 'parent_main': base,
                   'policy': 'two new files only; no force; read-back verification'}
        receipt_data = (json.dumps(receipt, ensure_ascii=False, indent=2)+'\n').encode()
        index = Path(record['work_directory'])/f'publish-record-index-{retry}'
        env = os.environ.copy(); env['GIT_INDEX_FILE'] = str(index)
        git(repo, 'read-tree', base, env=env, timeout=left(deadline))
        expected = {}
        for path, data in zip(paths, [content, receipt_data]):
            oid = git(repo, 'hash-object', '-w', '--stdin', input=data, timeout=left(deadline)).decode().strip()
            expected[path] = oid
            git(repo, 'update-index', '--add', '--cacheinfo', f'100644,{oid},{path}', env=env, timeout=left(deadline))
        tree = git(repo, 'write-tree', env=env, timeout=left(deadline)).decode().strip()
        changes = git(repo, 'diff-tree', '-r', '--no-commit-id', '--name-status', base, tree, timeout=left(deadline)).decode().splitlines()
        if set(changes) != {'A\t'+path for path in paths}:
            raise ContinuityError('Record saver attempted a non-additive change.')
        commit = git(repo, 'commit-tree', tree, '-p', base, '-m', f'Record continuity {game_id} {run_id}: {record["status"]}', timeout=left(deadline)).decode().strip()
        try:
            git(repo, 'push', 'origin', commit+':refs/heads/main', timeout=left(deadline))
        except subprocess.CalledProcessError:
            git(repo, 'fetch', 'origin', 'main', timeout=left(deadline))
            actual = git(repo, 'rev-parse', 'origin/main').decode().strip()
            if all(git(repo, 'ls-tree', actual, '--', path).decode().split()[2:3] == [oid] for path, oid in expected.items()):
                return {'status': 'GITHUB_RECORDED', 'commit': commit, 'path': relative, 'readback_verified': True}
            if retry == 2:
                raise
            continue
        git(repo, 'fetch', 'origin', 'main', timeout=left(deadline))
        for path, oid in expected.items():
            if git(repo, 'ls-tree', 'origin/main', '--', path, timeout=left(deadline)).decode().split()[2:3] != [oid]:
                raise ContinuityError('Run record read-back mismatch.')
        return {'status': 'GITHUB_RECORDED', 'commit': commit, 'path': relative, 'readback_verified': True}
    raise ContinuityError('Run record was not confirmed.')


def stop_child(child):
    if child is None:
        return
    # v1, Node and Chromium inherit this new process group. Clean up the group
    # even when its original leader has already exited; never target our group.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if child.poll() is None:
        child.wait(timeout=2)


def run(args):
    global _DEADLINE
    repo = Path(__file__).resolve().parents[1]
    started = time.monotonic()
    deadline = started+min(args.timeout_seconds, 3600)
    _DEADLINE = deadline
    record = {'schema_version': '1.1', 'engine': 'mini-game-continuity-wrapper',
              'program_is_ai': False, 'game_id': args.game, 'run_id': args.run_id,
              'invocation': args.invocation,
              'invocation_evidence': 'Self-declared metadata only; match external schedule ID/time separately.',
              'status': 'BLOCKED', 'github_status': 'NOT_SENT',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'ai_decisions': [],
              'scope': 'Automated checks; no real-child or Windows/Chromebook hardware verification.'}
    work = None; child = None; integrity = None; sandbox = None
    try:
        identifier(args.game); identifier(args.run_id)
        if not 0 < args.timeout_seconds <= 3600:
            raise ContinuityError('timeout-seconds must be greater than zero and <=3600.')
        root = Path(args.work_root).expanduser().resolve()
        if root == repo or repo in root.parents or root in repo.parents:
            raise ContinuityError('work-root must be outside the repository and not its ancestor.')
        planned = root/'continuity'/args.game/args.run_id
        planned.mkdir(parents=True, exist_ok=False)
        work = planned; record['work_directory'] = str(work)
        integrity = snapshot(repo)
        if not args.no_fetch:
            git(repo, 'fetch', 'origin', 'main', timeout=left(deadline))
        source = select_source(repo, args.game, args.ref)
        record['source'] = source
        emit('SOURCE_SELECTED', **source)
        sandbox = work/'checkout'
        git(repo, 'clone', '--shared', '--no-checkout', str(repo), str(sandbox), timeout=left(deadline))
        git(sandbox, 'checkout', '--detach', source['ref_commit'], timeout=left(deadline))
        origin = git(repo, 'remote', 'get-url', 'origin').decode().strip()
        git(sandbox, 'remote', 'set-url', 'origin', origin, timeout=left(deadline))
        config = json.loads(blob(repo, source['ref_commit'], f'engine-v1/games/{args.game}.json'))
        source_file = sandbox/config['source']
        if source_file.is_symlink() or not source_file.is_file() or sandbox not in source_file.resolve().parents:
            raise ContinuityError('Unsafe sandbox registered source.')
        inherited = blob(repo, source['ref_commit'], source['path'])
        if sha(inherited) != source['sha256']:
            raise ContinuityError('Selected source changed before seeding.')
        source_file.write_bytes(inherited)
        record['sandbox_seed'] = {'source_path': config['source'], 'sha256': sha(inherited),
                                  'config_unchanged': True,
                                  'note': 'Only isolated working-copy source bytes replaced; authoritative original is unchanged.'}
        command = [sys.executable, str(sandbox/'engine-v1/engine.py'), 'run', '--game', args.game,
                   '--run-id', args.run_id, '--work-root', str(work/'v1-work'),
                   '--timeout-seconds', str(left(deadline))]
        adapter = json.loads(args.ai_command) if args.ai_command else None
        if adapter is not None and (not isinstance(adapter, list) or not adapter or not all(isinstance(x, str) for x in adapter)):
            raise ContinuityError('ai-command must be a JSON argv array.')
        error_log = (work/'v1-stderr.log').open('wb')
        child = subprocess.Popen(command, cwd=sandbox, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_log, start_new_session=True)
        buffer = bytearray(); engine_result = None; skipped = False
        while True:
            if not select.select([child.stdout.fileno()], [], [], left(deadline))[0]:
                raise ContinuityError('v1 engine deadline exceeded.')
            chunk = os.read(child.stdout.fileno(), 65536)
            if not chunk:
                break
            buffer.extend(chunk)
            if len(buffer) > 5000000:
                raise ContinuityError('v1 bridge line exceeded limit.')
            while b'\n' in buffer:
                raw, _, tail = buffer.partition(b'\n'); buffer = bytearray(tail)
                event = json.loads(raw)
                if event.get('event') == 'AI_REQUEST':
                    integrity()
                    event['continuity'] = source
                    event['skip_protocol'] = {'skip': True, 'reason': 'No useful improvement identified', 'ai_agent': 'actual independent agent'}
                    emit('AI_REQUEST', **{k: v for k, v in event.items() if k != 'event'})
                    if adapter:
                        response = subprocess.run(adapter, input=json.dumps(event)+'\n', text=True, capture_output=True,
                                                  timeout=left(deadline), shell=False, cwd=sandbox)
                        if response.returncode:
                            raise ContinuityError('AI adapter failed.')
                        lines = response.stdout.strip().splitlines()
                        if len(lines) != 1:
                            raise ContinuityError('AI adapter must return one JSON line.')
                        ack = json.loads(lines[0])
                    else:
                        ack = read_json_line(sys.stdin, deadline)
                    integrity()
                    if not isinstance(ack, dict):
                        raise ContinuityError('AI response must be an object.')
                    record['ai_decisions'].append(ack)
                    if ack.get('skip') is True:
                        if (event.get('attempt') != 0 or not all(isinstance(ack.get(k), str) and ack[k].strip() for k in ('reason', 'ai_agent'))
                                or ack.get('ready') is True):
                            raise ContinuityError('Skip allowed only before the first evaluation with reason and actual AI identity.')
                        candidate = Path(event['candidate'])
                        if candidate.is_symlink() or sha(candidate.read_bytes()) != source['sha256']:
                            raise ContinuityError('Skip cannot conceal a modified candidate.')
                        # Existing v1 protects sandbox files only after ready. Check
                        # its entire tracked worktree against the seeded baseline on skip.
                        changes = git(sandbox, 'diff', '--name-only').decode().splitlines()
                        expected_change = [config['source']] if inherited != blob(repo, source['ref_commit'], config['source']) else []
                        if sorted(changes) != sorted(expected_change) or source_file.read_bytes() != inherited:
                            raise ContinuityError('Skip cannot conceal sandbox source/test/config modifications.')
                        record.update(status='SKIPPED', skip_reason=ack['reason'], release_created=False)
                        skipped = True; stop_child(child); break
                    child.stdin.write((json.dumps(ack)+'\n').encode()); child.stdin.flush()
                elif event.get('event') == 'RUN_RESULT':
                    engine_result = event
                    emit('V1_RESULT', result=event)
                else:
                    emit('V1_EVENT', result=event)
            if skipped:
                break
        if not skipped:
            child.wait(timeout=left(deadline)); error_log.close(); integrity()
            if not engine_result:
                raise ContinuityError('v1 ended without a final result.')
            record['v1_status'] = engine_result['status']
            record['attempts'] = engine_result.get('attempts', [])
            if engine_result['status'] == 'LOCAL_PASS_AWAITING_GITHUB':
                if engine_result.get('source_sha256') != source['sha256']:
                    raise ContinuityError('v1 did not validate against selected inherited bytes.')
                relative = engine_result['release_directory']
                release = sandbox/relative
                report_path = release/'report.json'
                report = json.loads(report_path.read_text())
                report['continuity'] = {'wrapper_version': '1.1', 'source_kind': source['kind'],
                                        'source_path': source['path'], 'source_sha256': source['sha256'],
                                        'source_ref_commit': source['ref_commit'],
                                        'source_publication_commit': source['commit'],
                                        'config_unchanged': True}
                report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
                with zipfile.ZipFile(release/'game.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                    archive.write(release/'game.html', 'game.html'); archive.write(report_path, 'report.json')
                record.update(status='PASS', release_created=True, release=relative,
                              validated_sha256=engine_result['validated_sha256'],
                              local_status='LOCAL_PASS_AWAITING_GITHUB')
                if args.publish:
                    integrity()
                    publication = publish_legacy(sandbox, relative, source, args.game, deadline)
                    record['release_publication'] = publication
                    record['github_status'] = publication['status']
            elif engine_result['status'] == 'FAILED_MAX_ATTEMPTS':
                record.update(status='FAILED', release_created=False)
            else:
                record.update(status='BLOCKED', error=engine_result.get('error', engine_result['status']), release_created=False)
        integrity()
    except Exception as exc:
        # Keep actual local PASS separate from a later publication block.
        if record.get('status') == 'PASS':
            record['publication_error'] = str(exc)
            record['github_status'] = 'GITHUB_NOT_CONFIRMED'
        else:
            record.update(status='BLOCKED', error=str(exc), release_created=False)
    finally:
        stop_child(child)
        if 'error_log' in locals():
            error_log.close()
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    record['elapsed_seconds'] = round(time.monotonic()-started, 3)
    if work is not None:
        local = work/'record.json'
        local.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        if args.publish:
            try:
                if integrity:
                    integrity()
                recording = save_record(sandbox or repo, record, deadline)
                (work/'RECORDED.json').write_text(json.dumps(recording, ensure_ascii=False, indent=2)+'\n')
                emit('RECORD_SAVED', **recording)
            except Exception as exc:
                emit('RECORD_NOT_CONFIRMED', error=str(exc), local_record=str(local))
    emit('CONTINUITY_RESULT', **record)
    if record['status'] in ('PASS', 'SKIPPED') and (not args.publish or (work/'RECORDED.json').exists()) and record.get('github_status') != 'GITHUB_NOT_CONFIRMED':
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    recorder = sub.add_parser('record', help='Retry add-only saving of an existing local record; no game publication.')
    recorder.add_argument('--file', required=True)
    recorder.add_argument('--timeout-seconds', type=float, default=3600)
    latest = sub.add_parser('latest', help='Verify source inheritance from Git evidence; no AI/edit.')
    execute = sub.add_parser('run')
    for p in (latest, execute):
        p.add_argument('--game', required=True); p.add_argument('--ref', default='origin/main')
        p.add_argument('--no-fetch', action='store_true', help='Use existing fetched Git objects (offline tests).')
    execute.add_argument('--run-id', required=True); execute.add_argument('--work-root', required=True)
    execute.add_argument('--timeout-seconds', type=float, default=3600)
    execute.add_argument('--ai-command', help='JSON argv array for real independent AI bridge.')
    execute.add_argument('--publish', action='store_true')
    execute.add_argument('--invocation', choices=('scheduled', 'interactive'), default='interactive')
    args = parser.parse_args()
    if args.command == 'run':
        return run(args)
    if args.command == 'record':
        try:
            if not 0 < args.timeout_seconds <= 3600:
                raise ContinuityError('Record timeout must be >0 and <=3600.')
            data = json.loads(Path(args.file).read_text())
            if data.get('status') not in ('PASS', 'SKIPPED', 'FAILED', 'BLOCKED') or data.get('schema_version') != '1.1':
                raise ContinuityError('Not a continuity v1.1 result record.')
            emit('RECORD_SAVED', **save_record(Path(__file__).resolve().parents[1], data, time.monotonic()+args.timeout_seconds))
            return 0
        except Exception as exc:
            emit('RECORD_NOT_CONFIRMED', error=str(exc)); return 1
    try:
        repo = Path(__file__).resolve().parents[1]
        if not args.no_fetch:
            git(repo, 'fetch', 'origin', 'main')
        emit('SOURCE_SELECTED', **select_source(repo, args.game, args.ref))
        return 0
    except Exception as exc:
        emit('SOURCE_BLOCKED', error=str(exc)); return 1


if __name__ == '__main__':
    sys.exit(main())
