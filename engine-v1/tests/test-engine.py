#!/usr/bin/env python3
"""Isolated orchestrator regression checks. Fixture adapters are NOT AI demonstrations."""
import unittest,tempfile,pathlib,subprocess,json,shutil,sys,hashlib
SOURCE=pathlib.Path(__file__).resolve().parents[1]/'engine.py'
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='engine-independent-');self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.repo=self.root/'repo';self.repo.mkdir();self.work=self.root/'work'
  self.write('engine-v1/engine.py',SOURCE.read_text());self.write('source.html','original')
  test="const fs=require('fs'),c=require('crypto'),s=process.argv[2];console.log(JSON.stringify({pass:true,sourceSha256:c.createHash('sha256').update(fs.readFileSync(s)).digest('hex')}));"
  self.write('engine-v1/tests/common-static.cjs',test);self.write('engine-v1/tests/common-browser.cjs',test);self.write('specific.cjs',test)
  self.config={'id':'fixture','title':'fixture','source':'source.html','purpose':'test','target_age':'4-6','basic_rules':['fixture invariant'],'forbidden_changes':['no source edit'],'specific_tests':[{'id':'specific','command':['node','specific.cjs','{candidate}']}],'browser_contract':{'start_selector':'#start','action_selector':'#action'}};self.save_config()
  self.write('adapter.py',"import json,sys,pathlib\nr=json.loads(sys.stdin.readline());p=pathlib.Path(r['candidate']);p.write_text(p.read_text()+' improved '+str(r['attempt']));print(json.dumps({'ready':True,'summary':'fixture only','ai_agent':'NON-AI TEST FIXTURE'}))\n")
  subprocess.run(['git','init','-q',str(self.repo)],check=True);subprocess.run(['git','add','.'],cwd=self.repo,check=True);subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture'],cwd=self.repo,check=True)
 def write(self,p,s):
  p=self.repo/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s);return p
 def save_config(self):self.write('engine-v1/games/fixture.json',json.dumps(self.config))
 def run_engine(self,runid='r1'):
  p=subprocess.run([sys.executable,str(self.repo/'engine-v1/engine.py'),'run','--game','fixture','--run-id',runid,'--work-root',str(self.work),'--timeout-seconds','20','--ai-command',json.dumps([sys.executable,str(self.repo/'adapter.py')])],capture_output=True,text=True)
  events=[json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')];return p,[x for x in events if x['event']=='RUN_RESULT'][-1]
 def test_success_prior_unchanged_and_duplicate_refused(self):
  old=self.write('engine-v1/releases/fixture/old/game.html','OLD');p,r=self.run_engine();self.assertEqual(p.returncode,0,p.stdout);self.assertEqual(old.read_text(),'OLD');self.assertEqual((self.repo/'source.html').read_text(),'original');p,r=self.run_engine();self.assertNotEqual(p.returncode,0);self.assertIn('already exists',r['error'])
 def test_four_evaluations_failure_never_released(self):
  self.write('specific.cjs','process.exit(1)');p,r=self.run_engine();self.assertEqual(r['status'],'FAILED_MAX_ATTEMPTS');self.assertEqual(len(r['attempts']),4);self.assertFalse((self.repo/'engine-v1/releases/fixture/r1').exists())
 def test_specific_switch_is_effective(self):
  self.write('reject.cjs','process.exit(1)');self.config['specific_tests']=[{'id':'different-rule','command':['node','reject.cjs','{candidate}']}];self.save_config();p,r=self.run_engine();self.assertEqual(r['status'],'FAILED_MAX_ATTEMPTS');self.assertTrue(all(x['tests'][-1]['id']=='different-rule' for x in r['attempts']))
 def test_config_tamper_blocks(self):
  self.write('adapter.py',"import json,sys,pathlib\nr=json.loads(sys.stdin.readline());pathlib.Path('engine-v1/games/fixture.json').write_text('{}');print(json.dumps({'ready':True,'summary':'fixture','ai_agent':'NON-AI'}))")
  p,r=self.run_engine();self.assertIn('Protected',r['error']);self.assertFalse((self.repo/'engine-v1/releases/fixture/r1').exists())
 def test_test_tamper_blocks(self):
  self.write('adapter.py',"import json,sys,pathlib\nr=json.loads(sys.stdin.readline());pathlib.Path('specific.cjs').write_text('');print(json.dumps({'ready':True,'summary':'fixture','ai_agent':'NON-AI'}))")
  p,r=self.run_engine();self.assertIn('Protected',r['error'])
 def test_candidate_changes_during_validation_block(self):
  self.write('specific.cjs',"require('fs').appendFileSync(process.argv[2],'tampered')")
  p,r=self.run_engine();self.assertIn('Candidate changed',r['error']);self.assertFalse((self.repo/'engine-v1/releases/fixture/r1').exists())
 def test_noop_test_exit_zero_is_not_evidence(self):
  self.write('specific.cjs','process.exit(0)');p,r=self.run_engine();self.assertNotEqual(p.returncode,0,'empty test evidence must not publish');self.assertFalse((self.repo/'engine-v1/releases/fixture/r1').exists())
if __name__=='__main__':unittest.main(verbosity=2)
