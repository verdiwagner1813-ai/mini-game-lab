#!/usr/bin/env python3
"""Runs only against isolated local bare Git. No external network publication."""
import unittest,tempfile,pathlib,subprocess,json,zipfile,importlib.util,sys,hashlib
sys.dont_write_bytecode=True
SOURCE=pathlib.Path(__file__).resolve().parents[1]/'publish.py'
spec=importlib.util.spec_from_file_location('engine_publisher_under_test',SOURCE);publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
class PublisherTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='publisher-independent-');self.addCleanup(self.temp.cleanup);base=pathlib.Path(self.temp.name);self.repo=base/'repo';self.remote=base/'remote.git';self.repo.mkdir();self.git('init','-q');self.git('config','user.name','Fixture');self.git('config','user.email','fixture@example.invalid');(self.repo/'README.md').write_text('PROTECTED');self.git('add','.');self.git('commit','-qm','base');self.git('branch','-M','main');subprocess.run(['git','init','--bare','-q',str(self.remote)],check=True);self.git('remote','add','origin',str(self.remote));self.git('push','-q','origin','main')
  self.oldroot,self.oldexpected=publisher.ROOT,publisher.EXPECTED;publisher.ROOT=self.repo;publisher.EXPECTED=str(self.remote);self.addCleanup(self.restore)
  self.rel='engine-v1/releases/fixture/r1';self.release=self.repo/self.rel;self.release.mkdir(parents=True);(self.release/'game.html').write_text('<title>fixture</title>');cfg=self.repo/'engine-v1/games/fixture.json';cfg.parent.mkdir(parents=True);cfg.write_text(json.dumps({'specific_tests':[{'id':'specific'}]}));self.report={'status':'LOCAL_PASS_AWAITING_GITHUB','game_id':'fixture','run_id':'r1','validated_sha256':publisher.sha(self.release/'game.html'),'config_sha256':publisher.sha(cfg),'attempts':[{'status':'PASS','candidate_sha256':publisher.sha(self.release/'game.html'),'tests':[{'id':x,'status':'PASS','exit_code':0} for x in ['common-static','common-browser','specific']]}]};self.write_report()
 def restore(self):publisher.ROOT,publisher.EXPECTED=self.oldroot,self.oldexpected
 def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.repo,stderr=subprocess.DEVNULL).decode().strip()
 def write_report(self):
  (self.release/'report.json').write_text(json.dumps(self.report))
  with zipfile.ZipFile(self.release/'game.zip','w') as z:
   for name in ['game.html','report.json']:z.write(self.release/name,name)
 def test_publish_readback_add_only_duplicate_rejected(self):
  before=self.git('rev-parse','origin/main');result=publisher.publish(self.rel);self.assertEqual(result['status'],'GITHUB_PUBLISHED');self.assertTrue(result['readback_verified']);self.assertEqual(self.git('show','origin/main:README.md'),'PROTECTED');changes=self.git('diff','--name-status',before,'origin/main').splitlines();self.assertEqual(len(changes),4);self.assertTrue(all(x.startswith('A\t') for x in changes));self.assertEqual(self.git('show','origin/main:'+self.rel+'/game.html'),(self.release/'game.html').read_text())
  with self.assertRaisesRegex(ValueError,'exists'):publisher.publish(self.rel)
 def test_failed_report_never_sent(self):
  before=self.git('rev-parse','origin/main');self.report['status']='FAILED';self.write_report()
  with self.assertRaisesRegex(ValueError,'not passing'):publisher.publish(self.rel)
  self.assertEqual(self.git('ls-remote','origin','refs/heads/main').split()[0],before)
 def test_missing_specific_evidence_rejected(self):
  self.report['attempts'][0]['tests'].pop();self.write_report()
  with self.assertRaisesRegex(ValueError,'incomplete'):publisher.publish(self.rel)
 def test_html_tamper_rejected(self):
  (self.release/'game.html').write_text('tampered')
  with self.assertRaisesRegex(ValueError,'SHA'):publisher.publish(self.rel)
if __name__=='__main__':unittest.main(verbosity=2)
