#!/usr/bin/env python3
"""Add an already passing release atomically to origin/main without overwriting paths.
Uses existing Git authentication only; never configures credentials or billing.
"""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
EXPECTED='https://github.com/verdiwagner1813-ai/mini-game-lab.git'
def git(*argv,env=None,input=None):
    p=subprocess.run(['git',*argv],cwd=ROOT,env=env,input=input,capture_output=True,text=True,check=True)
    return p.stdout.strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_release(relative):
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts or len(rel.parts)!=4 or tuple(rel.parts[:2])!=('engine-v1','releases'):
        raise ValueError('Only engine-v1/releases/<game>/<run> may be published')
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',x) for x in rel.parts[2:]):raise ValueError('Invalid IDs')
    root=ROOT/rel
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):raise ValueError('No symlinks')
    files=sorted(p for p in root.rglob('*') if p.is_file())
    if {p.name for p in files}!={'game.html','game.zip','report.json'} or any(p.parent!=root for p in files):raise ValueError('Unexpected release files')
    report=json.loads((root/'report.json').read_text())
    if report.get('status')!='LOCAL_PASS_AWAITING_GITHUB':raise ValueError('Release not passing')
    if report.get('game_id')!=rel.parts[2] or report.get('run_id')!=rel.parts[3]:raise ValueError('Report ID mismatch')
    if report.get('validated_sha256')!=sha(root/'game.html'):raise ValueError('Release SHA mismatch')
    attempts=report.get('attempts',[])
    if not attempts or attempts[-1].get('status')!='PASS':raise ValueError('No passing attempt')
    tests=attempts[-1].get('tests',[])
    ids=[t.get('id') for t in tests]
    config_path=ROOT/'engine-v1/games'/f'{rel.parts[2]}.json'
    if report.get('config_sha256')!=sha(config_path):raise ValueError('Config hash changed since validation')
    config=json.loads(config_path.read_text())
    if attempts[-1].get('candidate_sha256')!=report['validated_sha256']:raise ValueError('Attempt SHA mismatch')
    required=['common-static','common-browser']+[t['id'] for t in config['specific_tests']]
    if ids!=required or any(t.get('status')!='PASS' or t.get('exit_code')!=0 for t in tests):raise ValueError('Required tests incomplete')
    import zipfile
    with zipfile.ZipFile(root/'game.zip') as z:
        if z.testzip() is not None or z.read('game.html')!=(root/'game.html').read_bytes() or z.read('report.json')!=(root/'report.json').read_bytes():raise ValueError('ZIP mismatch')
    return rel,files,report

def publish(relative):
    rel,files,report=validate_release(relative)
    if git('remote','get-url','origin')!=EXPECTED:raise ValueError('Unexpected remote; refusing publication')
    for retry in range(3):
        git('fetch','origin','main')
        base=git('rev-parse','origin/main')
        # Every destination must be absent. No existing completion record is overwritten.
        destinations=[str(p.relative_to(ROOT)) for p in files]+[str(rel/'PUBLISHED.json')]
        for path in destinations:
            if git('ls-tree',base,'--',path):raise ValueError('Remote path exists: '+path)
        receipt={'schemaVersion':1,'status':'GITHUB_PUBLISHED','game_id':report['game_id'],'run_id':report['run_id'],
                 'game_sha256':report['validated_sha256'],'report_sha256':sha(ROOT/rel/'report.json'),
                 'parent_main':base,'published_utc':datetime.now(timezone.utc).isoformat(),
                 'policy':'new files only; no force; release and receipt in one Git commit'}
        with tempfile.TemporaryDirectory(prefix='mini-game-publish-') as temp:
            env=os.environ.copy();env['GIT_INDEX_FILE']=str(Path(temp)/'index')
            git('read-tree',base,env=env)
            expected_blobs={}
            for p in files:
                blob=git('hash-object','-w',str(p))
                path=str(p.relative_to(ROOT));expected_blobs[path]=blob
                git('update-index','--add','--cacheinfo',f'100644,{blob},{path}',env=env)
            receipt_path=Path(temp)/'PUBLISHED.json';receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
            path=str(rel/'PUBLISHED.json');blob=git('hash-object','-w',str(receipt_path));expected_blobs[path]=blob
            git('update-index','--add','--cacheinfo',f'100644,{blob},{path}',env=env)
            tree=git('write-tree',env=env)
            changes=git('diff-tree','-r','--no-commit-id','--name-status',base,tree).splitlines()
            if len(changes)!=4 or any(not x.startswith('A\t') for x in changes):raise ValueError('Non-additive Git tree')
            commit=git('commit-tree',tree,'-p',base,'-m',f'Publish tested {report["game_id"]} {report["run_id"]} as new files')
            try:git('push','origin',f'{commit}:refs/heads/main')
            except subprocess.CalledProcessError:
                # If the network lost the acknowledgement after success, prove it by read-back.
                git('fetch','origin','main')
                remote=git('rev-parse','origin/main')
                if all(git('ls-tree',remote,'--',p).split()[2:3]==[b] for p,b in expected_blobs.items()):
                    return {'status':'GITHUB_PUBLISHED','commit':commit,'readback_verified':True,'release':str(rel)}
                if retry==2:raise
                continue
            git('fetch','origin','main')
            remote=git('rev-parse','origin/main')
            for path,blob in expected_blobs.items():
                if git('ls-tree',remote,'--',path).split()[2:3]!=[blob]:raise ValueError('Remote read-back differs: '+path)
            return {'status':'GITHUB_PUBLISHED','commit':commit,'readback_verified':True,'release':str(rel)}
    raise RuntimeError('Publication not confirmed')
if __name__=='__main__':
    import sys
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--release',required=True);a=p.parse_args()
    try:print(json.dumps(publish(a.release),ensure_ascii=False))
    except Exception as e:
        detail=(e.stderr or '')[-4000:] if isinstance(e,subprocess.CalledProcessError) else ''
        print(json.dumps({'status':'GITHUB_NOT_CONFIRMED','error':str(e),'git_detail':detail},ensure_ascii=False));sys.exit(1)
