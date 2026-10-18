#!/usr/bin/env python3
"""A local validation orchestrator, not an AI. An independent AI edits one candidate.

Protocol: stdout JSONL AI_REQUEST; stdin one JSON line with ready:true,
summary and ai_agent. Optional --ai-command is a JSON argv array receiving the
same request on stdin and returning that acknowledgement on stdout.
No GitHub upload, deployment, or scheduled job is performed by this program.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone


class StopRun(Exception):
    pass


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(path):
    if path.is_symlink():
        return ('symlink', os.readlink(path))
    if path.is_file():
        return ('file', digest(path), path.stat().st_mode & 0o777)
    if path.exists():
        return ('other',)
    return ('missing',)


def emit(event, **data):
    print(json.dumps({'event': event, **data}, ensure_ascii=False), flush=True)


def under(path, root):
    return path == root or root in path.parents


def safe_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise StopRun('ID must contain only letters, numbers, underscore or hyphen (max 80).')
    return value


def inside_repo(repo, value):
    path = repo / value
    if not isinstance(value, str) or Path(value).is_absolute() or '..' in Path(value).parts:
        raise StopRun('Registry paths must be relative repository paths.')
    if not under(path.resolve(), repo):
        raise StopRun('Registry path escapes repository.')
    if not path.is_file() or path.is_symlink():
        raise StopRun('Required regular file missing: ' + str(path))
    return path


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise StopRun('Overall time limit exceeded (including AI waiting).')
    return seconds


def read_ack(deadline):
    # Read bytes only after readiness, so a partial line cannot bypass timeout.
    data = bytearray()
    while True:
        readable, _, _ = select.select([sys.stdin.fileno()], [], [], remaining(deadline))
        if not readable:
            raise StopRun('AI acknowledgement timed out.')
        chunk = os.read(sys.stdin.fileno(), 1)
        if not chunk:
            raise StopRun('AI bridge stdin closed before acknowledgement.')
        if chunk == b'\n':
            break
        data.extend(chunk)
        if len(data) > 100000:
            raise StopRun('AI acknowledgement too large.')
    return json.loads(data.decode('utf-8'))


def run(args):
    repo = Path(__file__).resolve().parents[1]
    report = {'engine': 'mini-game-improvement-engine-v1', 'program_is_ai': False,
              'ai_protocol': 'Independent AI edits candidate; program runs checks only.',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'attempts': [],
              'status': 'INITIALIZING', 'github_status': 'NOT_SENT_BY_ENGINE'}
    work = None
    try:
        game_id, run_id = safe_id(args.game), safe_id(args.run_id)
        if not 0 < args.timeout_seconds <= 3600:
            raise StopRun('Timeout must be greater than zero and at most 3600 seconds.')
        deadline = time.monotonic() + args.timeout_seconds
        root = Path(args.work_root).expanduser().resolve()
        if under(root, repo) or under(repo, root):
            raise StopRun('work-root must be outside the repository and not its ancestor.')
        inspect_registry(repo, game_id)
        config_path = inside_repo(repo, f'engine-v1/games/{game_id}.json')
        config = json.loads(config_path.read_text(encoding='utf-8'))
        for key in ('id', 'title', 'source', 'purpose', 'target_age', 'basic_rules',
                    'forbidden_changes', 'specific_tests', 'browser_contract'):
            if key not in config:
                raise StopRun('Missing registry field: ' + key)
        if config['id'] != game_id or not config['specific_tests']:
            raise StopRun('Registry ID mismatch or missing game-specific tests.')
        if not isinstance(config['basic_rules'], list) or not isinstance(config['forbidden_changes'], list):
            raise StopRun('Rules and forbidden_changes must be arrays.')
        if not all(isinstance(config['browser_contract'].get(k), str) and config['browser_contract'][k]
                   for k in ('start_selector', 'action_selector')):
            raise StopRun('Browser contract requires start_selector and action_selector.')
        source = inside_repo(repo, config['source'])
        static = inside_repo(repo, 'engine-v1/tests/common-static.cjs')
        browser = inside_repo(repo, 'engine-v1/tests/common-browser.cjs')
        release = repo / 'engine-v1' / 'releases' / game_id / run_id
        if release.exists() or release.is_symlink():
            raise StopRun('Release already exists; refusing overwrite.')
        planned_work = root / game_id / run_id
        planned_work.mkdir(parents=True, exist_ok=False)
        work = planned_work
        candidate = work / 'candidate.html'
        shutil.copyfile(source, candidate)
        source_sha = digest(source)
        report.update(game_id=game_id, run_id=run_id, source=str(source.relative_to(repo)),
                      source_sha256=source_sha, config_sha256=digest(config_path),
                      work_directory=str(work), max_evaluations=4, timeout_seconds=args.timeout_seconds)
        # Protect all tracked files, including missing tracked paths, and all
        # engine files present at run start. Other agents may add unrelated files.
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=repo).split(b'\0')
        protected = {repo / os.fsdecode(p) for p in tracked if p}
        protected.update(p for p in (repo / 'engine-v1').rglob('*') if p.is_file() or p.is_symlink())
        protected.update((source, config_path, static, browser, Path(__file__).resolve()))
        if args.publish:
            protected.add(inside_repo(repo, 'engine-v1/publish.py'))
        commands = [('common-static', ['node', str(static), str(candidate), str(config_path)]),
                    ('common-browser', ['node', str(browser), str(candidate), str(config_path)])]
        for test in config['specific_tests']:
            command = test.get('command')
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise StopRun('Every test command must be a nonempty argv string array.')
            expanded = [x.replace('{candidate}', str(candidate)).replace('{config}', str(config_path)) for x in command]
            if not any('{candidate}' in x for x in command):
                raise StopRun('Game-specific test must explicitly receive {candidate}.')
            commands.append((str(test['id']), expanded))
            # Protect script/assets referenced directly by a test command.
            for argument in command:
                p = repo / argument
                if p.is_file() or p.is_symlink():
                    protected.add(p)
        before = {str(p): signature(p) for p in protected}
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).strip()
        def integrity():
            changed = [p for p, sig in before.items() if signature(Path(p)) != sig]
            if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).strip() != head:
                changed.append('git HEAD')
            if changed:
                raise StopRun('Protected source/test/config/history changed: ' + ', '.join(changed[:20]))
        adapter = json.loads(args.ai_command) if args.ai_command else None
        if adapter is not None and (not isinstance(adapter, list) or not adapter or not all(isinstance(x, str) for x in adapter)):
            raise StopRun('--ai-command must be a JSON argv string array.')
        prior_sha = source_sha
        for attempt in range(4):
            integrity()
            request = {'attempt': attempt, 'max_repair_attempts': 3, 'candidate': str(candidate),
                       'config': config, 'source_sha256': source_sha,
                       'previous_failures': report['attempts'][-1:] if report['attempts'] else [],
                       'editable_paths': [str(candidate)], 'instructions':
                       'You must be an actual independent AI agent. Improve only candidate.html; '
                       'preserve purpose, rules, offline/input/privacy requirements. Do not edit '
                       'source, tests, configuration, engine or past releases. Return one JSON '
                       'line {"ready":true,"summary":"...","ai_agent":"actual agent identity"}. '
                       'The program is not AI and cannot edit the game itself.'}
            emit('AI_REQUEST', **request)
            record = {'attempt': attempt, 'tests': [], 'status': 'WAITING_FOR_AI'}
            report['attempts'].append(record)
            if adapter:
                proc = subprocess.run(adapter, input=json.dumps({'event': 'AI_REQUEST', **request})+'\n',
                                      text=True, capture_output=True, cwd=repo, timeout=remaining(deadline), shell=False)
                (work / f'attempt-{attempt}-adapter-stderr.log').write_text(proc.stderr, encoding='utf-8')
                if proc.returncode:
                    raise StopRun('AI adapter failed with exit code ' + str(proc.returncode))
                lines = proc.stdout.strip().splitlines()
                if len(lines) != 1:
                    raise StopRun('AI adapter must return exactly one JSON acknowledgement line.')
                ack = json.loads(lines[0])
            else:
                ack = read_ack(deadline)
            remaining(deadline)
            integrity()
            if not isinstance(ack, dict) or ack.get('ready') is not True or not all(isinstance(ack.get(k), str) and ack[k].strip() for k in ('summary', 'ai_agent')):
                raise StopRun('AI acknowledgement needs ready:true, nonempty summary and ai_agent.')
            record['ai_acknowledgement'] = ack
            if candidate.is_symlink() or not candidate.is_file() or not candidate.read_bytes().strip():
                raise StopRun('Candidate must be a nonempty regular file, never a symlink.')
            candidate_sha = digest(candidate)
            record['candidate_sha256'] = candidate_sha
            if candidate_sha in (source_sha, prior_sha):
                record['status'] = 'REJECTED_UNCHANGED'
                record['failure'] = 'Candidate unchanged from source or previous evaluated candidate.'
                prior_sha = candidate_sha
                emit('ATTEMPT_RESULT', **record)
                continue
            prior_sha = candidate_sha
            for index, (test_id, command) in enumerate(commands):
                integrity()
                if candidate.is_symlink() or digest(candidate) != candidate_sha:
                    raise StopRun('Candidate changed after acknowledgement/during validation.')
                started = time.monotonic()
                try:
                    proc = subprocess.run(command, cwd=repo, text=True, capture_output=True,
                                          shell=False, timeout=remaining(deadline))
                    code, output = proc.returncode, proc.stdout + '\n' + proc.stderr
                    if code == 0:
                        records = []
                        for line in proc.stdout.splitlines():
                            try:
                                item = json.loads(line)
                                if isinstance(item, dict):
                                    records.append(item)
                            except json.JSONDecodeError:
                                pass
                        hashes = [item[key] for item in records
                                  for key in ('sourceSha256', 'sha256') if key in item]
                        if (not any(item.get('pass') is True for item in records)
                                or any(item.get('pass') is False for item in records)
                                or not hashes or any(h != candidate_sha for h in hashes)):
                            code = -2
                            output += '\nENGINE: exit 0 is insufficient: require pass:true and matching candidate SHA256.'
                except subprocess.TimeoutExpired as exc:
                    code, output = -1, 'Overall timeout during test: ' + str(exc)
                log = work / f'attempt-{attempt}-test-{index}.log'
                log.write_text(output, encoding='utf-8')
                record['tests'].append({'id': test_id, 'command': command, 'exit_code': code,
                                        'seconds': round(time.monotonic()-started, 3),
                                        'status': 'PASS' if code == 0 else 'FAIL',
                                        'log': str(log), 'output': output[-30000:]})
                integrity()
                if candidate.is_symlink() or digest(candidate) != candidate_sha:
                    raise StopRun('Candidate changed during validation; pass invalidated.')
                if code:
                    break
            if len(record['tests']) == len(commands) and all(t['status'] == 'PASS' for t in record['tests']):
                remaining(deadline)
                integrity()
                if digest(candidate) != candidate_sha or candidate.is_symlink():
                    raise StopRun('Validated SHA differs from release candidate.')
                record['status'] = 'PASS'
                report.update(status='LOCAL_PASS_AWAITING_GITHUB', validated_sha256=candidate_sha,
                              release_directory=str(release.relative_to(repo)),
                              finished_utc=datetime.now(timezone.utc).isoformat(),
                              protected_files=len(before), source_and_history_unchanged=True,
                              limitations=['Automated checks do not establish real-child usability.',
                                           'AI identity is supplied by bridge, not cryptographically verified.',
                                           'GitHub upload/main merge is a separate operation.'])
                if any(p.is_symlink() for p in (release, *release.parents) if under(p, repo)):
                    raise StopRun('Symlink in release path; refusing publication.')
                if not under(release.resolve(), repo):
                    raise StopRun('Release path escaped repository.')
                release.mkdir(parents=True, exist_ok=False)
                try:
                    # Copy the already validated bytes, then verify the copy.
                    shutil.copyfile(candidate, release / 'game.html')
                    if digest(release / 'game.html') != candidate_sha:
                        raise StopRun('Release copy SHA mismatch.')
                    (release / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                    with zipfile.ZipFile(release / 'game.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
                        archive.write(release / 'game.html', 'game.html')
                        archive.write(release / 'report.json', 'report.json')
                    with zipfile.ZipFile(release / 'game.zip') as archive:
                        if hashlib.sha256(archive.read('game.html')).hexdigest() != candidate_sha:
                            raise StopRun('ZIP content SHA mismatch.')
                except Exception:
                    shutil.rmtree(release)
                    raise
                (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                emit('RUN_RESULT', **report)
                if args.publish:
                    # Publication is separate; never turn local PASS into a claim
                    # of GitHub success merely because an upload was attempted.
                    try:
                        publisher = subprocess.run([sys.executable, str(repo / 'engine-v1/publish.py'),
                                                    '--release', str(release.relative_to(repo))],
                                                   cwd=repo, text=True, capture_output=True, shell=False,
                                                   timeout=remaining(deadline))
                        (work / 'publish.log').write_text(publisher.stdout+'\n'+publisher.stderr, encoding='utf-8')
                        emit('PUBLISH_RESULT', exit_code=publisher.returncode,
                             stdout=publisher.stdout[-30000:], stderr=publisher.stderr[-30000:],
                             local_status='LOCAL_PASS_AWAITING_GITHUB',
                             receipt=str(release / 'PUBLISHED.json'))
                        return 0 if publisher.returncode == 0 else 2
                    except Exception as exc:
                        emit('PUBLISH_RESULT', exit_code=2, error=str(exc),
                             local_status='LOCAL_PASS_AWAITING_GITHUB')
                        return 2
                return 0
            record['status'] = 'FAIL'
            emit('ATTEMPT_RESULT', **record)
        report['status'] = 'FAILED_MAX_ATTEMPTS'
    except Exception as exc:
        report['status'] = 'BLOCKED'
        report['error'] = str(exc)
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    if work is not None and work.is_dir():
        (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    emit('RUN_RESULT', **report)
    return 1


def inspect_registry(repo, game_id):
    """Validate registration without copying, editing, running tests, or AI calls."""
    path = inside_repo(repo, f'engine-v1/games/{safe_id(game_id)}.json')
    config = json.loads(path.read_text(encoding='utf-8'))
    required = ('id', 'title', 'source', 'purpose', 'target_age', 'basic_rules',
                'forbidden_changes', 'specific_tests', 'browser_contract')
    if any(key not in config for key in required) or config['id'] != game_id:
        raise StopRun('Incomplete registry or ID mismatch.')
    for key in ('title', 'source', 'purpose', 'target_age'):
        if not isinstance(config[key], str) or not config[key].strip():
            raise StopRun('Registry field must be nonempty text: '+key)
    for key in ('basic_rules', 'forbidden_changes'):
        if not isinstance(config[key], list) or not config[key] or not all(isinstance(x, str) and x for x in config[key]):
            raise StopRun('Registry field must be nonempty text array: '+key)
    contract = config['browser_contract']
    if not isinstance(contract, dict) or not all(isinstance(contract.get(k), str) and contract[k]
            for k in ('start_selector', 'action_selector')):
        raise StopRun('Invalid browser_contract.')
    source = inside_repo(repo, config['source'])
    inside_repo(repo, 'engine-v1/tests/common-static.cjs')
    inside_repo(repo, 'engine-v1/tests/common-browser.cjs')
    tests = config['specific_tests']
    if not isinstance(tests, list) or not tests:
        raise StopRun('At least one explicit game-specific test is required.')
    ids = set()
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get('id'), str) or not test['id'] or test['id'] in ids:
            raise StopRun('Specific tests require distinct nonempty IDs.')
        ids.add(test['id'])
        command = test.get('command')
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            raise StopRun('Test command must be a nonempty argv array.')
        if not any('{candidate}' in x for x in command):
            raise StopRun('Test must explicitly receive {candidate}.')
        executable = command[0]
        if not shutil.which(executable):
            raise StopRun('Test executable unavailable: '+executable)
        for argument in command[1:]:
            if '{' not in argument and argument.endswith(('.cjs', '.mjs', '.js', '.py')):
                inside_repo(repo, argument)
    return config, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='List JSON game registrations; no AI or tests run.')
    validate = sub.add_parser('validate', help='Check registry schema and required files; no test execution.')
    validate.add_argument('--game', required=True)
    execute = sub.add_parser('run')
    execute.add_argument('--game', required=True)
    execute.add_argument('--run-id', required=True)
    execute.add_argument('--work-root', required=True)
    execute.add_argument('--timeout-seconds', type=float, default=3600)
    execute.add_argument('--publish', action='store_true', help='Invoke separate add-only publisher after local PASS.')
    execute.add_argument('--ai-command', help='JSON argv array for a real independent AI adapter; no shell.')
    args = parser.parse_args()
    if args.command == 'run':
        return run(args)
    repo = Path(__file__).resolve().parents[1]
    try:
        if args.command == 'list':
            games = []
            for path in sorted((repo / 'engine-v1/games').glob('*.json')):
                config = json.loads(path.read_text(encoding='utf-8'))
                games.append({key: config[key] for key in ('id', 'title', 'source')})
            emit('GAMES', games=games)
        else:
            config, source = inspect_registry(repo, args.game)
            emit('REGISTRY_VALID', game=config['id'], source=config['source'],
                 source_sha256=digest(source), specific_tests=len(config['specific_tests']),
                 tests_executed=False, source_selection='Explicit registry source; not latest release.')
        return 0
    except Exception as exc:
        emit('REGISTRY_ERROR', error=str(exc))
        return 1


if __name__ == '__main__':
    sys.exit(main())
