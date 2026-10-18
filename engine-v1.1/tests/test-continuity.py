#!/usr/bin/env python3
"""Independent isolated continuity tests. Adapter fixtures are not actual AI or scheduled runs."""
import unittest,tempfile,pathlib,subprocess,json,zipfile,hashlib,importlib.util,sys,time
from unittest.mock import patch
from types import SimpleNamespace
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[2];SOURCE=ROOT/'engine-v1.1/continuity.py'
spec=importlib.util.spec_from_file_location('continuity_test_target',SOURCE);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class ContinuityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='continuity-independent-');self.addCleanup(self.tmp.cleanup);self.base=pathlib.Path(self.tmp.name);self.repo=self.base/'repo';self.repo.mkdir()
  self.write('engine-v1.1/continuity.py',SOURCE.read_bytes());self.write('engine-v1/engine.py',(ROOT/'engine-v1/engine.py').read_bytes());self.write('source.html',b'ORIGINAL')
  self.config={'id':'fixture','title':'Fixture','source':'source.html','purpose':'test','target_age':'4-6','basic_rules':['test'],'forbidden_changes':['no original edit'],'specific_tests':[{'id':'specific','command':['node','specific.cjs','{candidate}']}],'browser_contract':{'start_selector':'#start','action_selector':'#action'}}
  self.config_bytes=json.dumps(self.config).encode();self.write('engine-v1/games/fixture.json',self.config_bytes)
  script=b"const f=require('fs'),c=require('crypto');console.log(JSON.stringify({pass:true,sourceSha256:c.createHash('sha256').update(f.readFileSync(process.argv[2])).digest('hex')}));"
  for path in ['engine-v1/tests/common-static.cjs','engine-v1/tests/common-browser.cjs','specific.cjs']:self.write(path,script)
  self.git('init','-q');self.git('config','user.name','Fixture');self.git('config','user.email','fixture@example.invalid');self.commit('base');self.git('branch','-M','main');self.git('remote','add','origin',str(self.repo));self.ref()
 def write(self,path,data):
  p=self.repo/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);return p
 def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.repo,stderr=subprocess.DEVNULL).decode().strip()
 def commit(self,message):self.git('add','.');self.git('commit','-qm',message);return self.git('rev-parse','HEAD')
 def ref(self):self.git('update-ref','refs/remotes/origin/main','HEAD')
 def release(self,name,content=b'LATEST'):
  parent=self.git('rev-parse','HEAD');rel=f'engine-v1/releases/fixture/{name}';self.write(rel+'/game.html',content);h=mod.sha(content)
  report={'status':'LOCAL_PASS_AWAITING_GITHUB','game_id':'fixture','run_id':name,'validated_sha256':h,'config_sha256':mod.sha(self.config_bytes),'attempts':[{'status':'PASS','candidate_sha256':h,'tests':[{'id':i,'status':'PASS','exit_code':0} for i in ['common-static','common-browser','specific']]}]};data=json.dumps(report).encode();self.write(rel+'/report.json',data)
  with zipfile.ZipFile(self.repo/rel/'game.zip','w') as z:z.writestr('game.html',content);z.writestr('report.json',data)
  self.write(rel+'/PUBLISHED.json',json.dumps({'status':'GITHUB_PUBLISHED','game_id':'fixture','run_id':name,'game_sha256':h,'report_sha256':mod.sha(data),'parent_main':parent}).encode());self.commit('publish '+name);self.ref();return rel
 def run_adapter(self,code,runid='test-run'):
  adapter=self.base/'fixture-adapter.py';adapter.write_text(code)
  p=subprocess.run([sys.executable,str(self.repo/'engine-v1.1/continuity.py'),'run','--game','fixture','--run-id',runid,'--work-root',str(self.base/'work'),'--no-fetch','--timeout-seconds','20','--ai-command',json.dumps([sys.executable,str(adapter)])],capture_output=True,text=True)
  events=[json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')];return p,next(e for e in reversed(events) if e['event']=='CONTINUITY_RESULT')
 def test_registry_fallback_ignores_unpublished(self):
  self.write('engine-v1/releases/fixture/incomplete/game.html',b'UNTESTED');self.commit('incomplete');self.ref();s=mod.select_source(self.repo,'fixture');self.assertEqual(s['kind'],'registry');self.assertEqual(s['sha256'],mod.sha(b'ORIGINAL'))
 def test_latest_by_ancestry_not_filename(self):
  self.release('zzz',b'OLDER');latest=self.release('aaa',b'NEWER');s=mod.select_source(self.repo,'fixture');self.assertEqual(s['path'],latest+'/game.html');self.assertEqual(s['sha256'],mod.sha(b'NEWER'))
 def test_incomparable_ancestry_refused(self):
  with self.assertRaisesRegex(mod.ContinuityError,'incomparable'):mod.choose_latest([{'commit':'a','path':'a'},{'commit':'b','path':'b'}],lambda a,b:False)
 def test_published_game_modified_refused(self):
  rel=self.release('one');self.write(rel+'/game.html',b'MODIFIED');self.commit('tamper');self.ref()
  with self.assertRaises(mod.ContinuityError):mod.select_source(self.repo,'fixture')
 def test_registry_changed_since_release_refused(self):
  self.release('one');self.write('engine-v1/games/fixture.json',json.dumps({**self.config,'title':'changed'}).encode());self.commit('change config');self.ref()
  with self.assertRaisesRegex(mod.ContinuityError,'Registry changed'):mod.select_source(self.repo,'fixture')
 def test_failed_report_receipt_refused(self):
  rel=self.release('one');report=json.loads((self.repo/rel/'report.json').read_text());report['status']='FAILED';self.write(rel+'/report.json',json.dumps(report).encode());self.commit('bad report');self.ref()
  with self.assertRaises(mod.ContinuityError):mod.select_source(self.repo,'fixture')
 def test_skip_inherits_latest_without_release(self):
  rel=self.release('one',b'INHERITED')
  code="import json,sys,pathlib\nr=json.loads(sys.stdin.readline());assert pathlib.Path(r['candidate']).read_bytes()==b'INHERITED';print(json.dumps({'skip':True,'reason':'No useful improvement','ai_agent':'NON-AI FIXTURE'}))"
  p,r=self.run_adapter(code);self.assertEqual(p.returncode,0,p.stdout);self.assertEqual(r['status'],'SKIPPED');self.assertFalse(r['release_created']);self.assertEqual(r['sandbox_seed']['sha256'],mod.sha(b'INHERITED'));self.assertEqual((self.repo/'source.html').read_bytes(),b'ORIGINAL');self.assertEqual((self.repo/rel/'game.html').read_bytes(),b'INHERITED');self.assertFalse((pathlib.Path(r['work_directory'])/'checkout/engine-v1/releases/fixture/test-run').exists())
 def test_modified_candidate_cannot_skip(self):
  code="import json,sys,pathlib\nr=json.loads(sys.stdin.readline());pathlib.Path(r['candidate']).write_text('CHANGED');print(json.dumps({'skip':True,'reason':'hide','ai_agent':'NON-AI FIXTURE'}))"
  p,r=self.run_adapter(code);self.assertNotEqual(p.returncode,0);self.assertEqual(r['status'],'BLOCKED');self.assertIn('modified candidate',r['error'])
 def test_skip_with_ready_refused(self):
  code="import json,sys\nr=json.loads(sys.stdin.readline());print(json.dumps({'skip':True,'ready':True,'reason':'invalid','ai_agent':'NON-AI FIXTURE'}))"
  p,r=self.run_adapter(code);self.assertNotEqual(p.returncode,0);self.assertEqual(r['status'],'BLOCKED')
 def test_skip_hides_test_change_refused(self):
  code="import json,sys,pathlib\nr=json.loads(sys.stdin.readline());pathlib.Path('specific.cjs').write_text('CHANGED');print(json.dumps({'skip':True,'reason':'hide','ai_agent':'NON-AI FIXTURE'}))"
  p,r=self.run_adapter(code);self.assertNotEqual(p.returncode,0);self.assertIn('modifications',r['error'])
 def test_success_inherits_latest_and_preserves_original(self):
  rel=self.release('one',b'INHERITED')
  code="import json,sys,pathlib\nr=json.loads(sys.stdin.readline());p=pathlib.Path(r['candidate']);assert p.read_bytes()==b'INHERITED';p.write_bytes(p.read_bytes()+b' IMPROVED');print(json.dumps({'ready':True,'summary':'fixture','ai_agent':'NON-AI FIXTURE'}))"
  p,r=self.run_adapter(code);self.assertEqual(p.returncode,0,p.stdout);self.assertEqual(r['status'],'PASS');self.assertEqual(r['attempts'][0]['status'],'PASS');self.assertEqual((self.repo/'source.html').read_bytes(),b'ORIGINAL');self.assertEqual((self.repo/rel/'game.html').read_bytes(),b'INHERITED')
  report=json.loads((pathlib.Path(r['work_directory'])/'checkout'/r['release']/'report.json').read_text());self.assertEqual(report['source_sha256'],mod.sha(b'INHERITED'));self.assertEqual(report['continuity']['source_path'],rel+'/game.html')
 def test_four_failures_do_not_create_release_or_change_previous(self):
  self.write('specific.cjs',b'process.exit(1)');self.commit('reject test');self.ref();rel=self.release('one',b'INHERITED')
  code="import json,sys,pathlib\nr=json.loads(sys.stdin.readline());p=pathlib.Path(r['candidate']);p.write_bytes(p.read_bytes()+str(r['attempt']).encode());print(json.dumps({'ready':True,'summary':'fixture','ai_agent':'NON-AI FIXTURE'}))"
  p,r=self.run_adapter(code);self.assertNotEqual(p.returncode,0);self.assertEqual(r['status'],'FAILED');self.assertEqual(len(r['attempts']),4);self.assertFalse(r['release_created']);self.assertEqual((self.repo/rel/'game.html').read_bytes(),b'INHERITED');self.assertEqual((self.repo/'source.html').read_bytes(),b'ORIGINAL')
 def test_duplicate_record_path_refused(self):
  self.write('engine-v1.1/runs/fixture/repeat/record.json',b'OLD');self.commit('existing record');self.ref();real_git=mod.git
  def isolated_git(repo,*args,**kwargs):
   if args==('remote','get-url','origin'):return b'https://github.com/verdiwagner1813-ai/mini-game-lab.git\n'
   return real_git(repo,*args,**kwargs)
  with patch.object(mod,'git',side_effect=isolated_git):
   with self.assertRaisesRegex(mod.ContinuityError,'exists remotely'):mod.save_record(self.repo,{'game_id':'fixture','run_id':'repeat','status':'SKIPPED','work_directory':str(self.base)},time.monotonic()+20)
  self.assertEqual((self.repo/'engine-v1.1/runs/fixture/repeat/record.json').read_bytes(),b'OLD')
 def test_stale_same_game_publication_refused(self):
  fake=SimpleNamespace();fake.publish=lambda relative:fake.git('fetch','origin','main')
  loader=SimpleNamespace(exec_module=lambda module:None)
  release=self.base/'sandbox'/'release';release.mkdir(parents=True);(release/'game.html').write_bytes(b'CANDIDATE')
  source={'kind':'release','path':'old','sha256':'old','commit':'old','config_sha256':'same'}
  with patch.object(mod.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=loader)),patch.object(mod.importlib.util,'module_from_spec',return_value=fake),patch.object(mod,'git',return_value=b''),patch.object(mod,'select_source',return_value={**source,'commit':'new','path':'new'}):
   with self.assertRaisesRegex(mod.ContinuityError,'stale publication blocked'):mod.publish_legacy(self.base/'sandbox','release',source,'fixture',time.monotonic()+20)
if __name__=='__main__':unittest.main(verbosity=2)
