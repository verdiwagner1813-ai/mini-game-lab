#!/usr/bin/env python3
import unittest,tempfile,pathlib,json,hashlib,importlib.util,sys
from datetime import datetime,timedelta
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('triad_gate',pathlib.Path(__file__).with_name('gate.py'));gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class GateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.exp=self.root/'engine-v1.1/experiments/triad-20261019';self.exp.mkdir(parents=True)
 def put(self,path,data):
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data if isinstance(data,bytes) else json.dumps(data).encode())
 def now(self,slot):return datetime.fromisoformat(gate.TIMES[slot-1])
 def prior(self,n):
  run=f'triad-20261019-{n:02}';self.put(self.exp/'claims'/f'{n:02}.json',{})
  release=f'engine-v1/releases/exhibit-mission/{run}';html=b'GAME';report={'status':'LOCAL_PASS_AWAITING_GITHUB','game_id':'exhibit-mission','run_id':run,'validated_sha256':hashlib.sha256(html).hexdigest()};report_bytes=json.dumps(report).encode();self.put(self.root/release/'game.html',html);self.put(self.root/release/'report.json',report_bytes);self.put(self.root/release/'PUBLISHED.json',{'status':'GITHUB_PUBLISHED','game_id':'exhibit-mission','run_id':run,'game_sha256':hashlib.sha256(html).hexdigest(),'report_sha256':hashlib.sha256(report_bytes).hexdigest()})
  record={'game_id':'exhibit-mission','run_id':run,'status':'PASS','github_status':'GITHUB_PUBLISHED','release':release,'validated_sha256':hashlib.sha256(html).hexdigest()};folder=self.root/'engine-v1.1/runs/exhibit-mission'/run;data=json.dumps(record).encode();self.put(folder/'record.json',data);self.put(folder/'RECORDED.json',{'status':'GITHUB_RECORDED','record_sha256':hashlib.sha256(data).hexdigest()});self.put(self.exp/'results'/f'{n:02}.json',{'run_id':run,'status':'PASS','allow_next':True});return folder,self.root/release
 def test_due(self):self.assertEqual(gate.check(self.root,self.exp,1,self.now(1))['slot'],1)
 def test_early_refused(self):
  with self.assertRaisesRegex(ValueError,'not due'):gate.check(self.root,self.exp,1,self.now(1)-timedelta(seconds=11))
 def test_expired_refused(self):
  with self.assertRaisesRegex(ValueError,'expired'):gate.check(self.root,self.exp,1,self.now(1)+timedelta(minutes=60))
 def test_stop_refused(self):
  self.put(self.exp/'STOPPED.json',{})
  with self.assertRaisesRegex(ValueError,'stopped'):gate.check(self.root,self.exp,1,self.now(1))
 def test_completed_refused(self):
  self.put(self.exp/'COMPLETED.json',{})
  with self.assertRaisesRegex(ValueError,'completed'):gate.check(self.root,self.exp,1,self.now(1))
 def test_duplicate_refused(self):
  self.put(self.exp/'claims/01.json',{})
  with self.assertRaisesRegex(ValueError,'Claim already'):gate.check(self.root,self.exp,1,self.now(1))
 def test_missing_previous_refused(self):
  with self.assertRaisesRegex(ValueError,'never claimed'):gate.check(self.root,self.exp,2,self.now(2))
 def test_proof_hash_mismatch_refused(self):
  _,release=self.prior(1);self.put(release/'game.html',b'TAMPERED')
  with self.assertRaisesRegex(ValueError,'proof/hash'):gate.check(self.root,self.exp,2,self.now(2))
 def test_record_hash_mismatch_refused(self):
  folder,_=self.prior(1);self.put(folder/'RECORDED.json',{'status':'GITHUB_RECORDED','record_sha256':'WRONG'})
  with self.assertRaisesRegex(ValueError,'receipt/hash'):gate.check(self.root,self.exp,2,self.now(2))
 def test_three_sequential_slots_only(self):
  for n in (1,2,3):self.assertEqual(gate.check(self.root,self.exp,n,self.now(n))['slot'],n);self.prior(n)
  with self.assertRaisesRegex(ValueError,'Only slots'):gate.check(self.root,self.exp,4,self.now(3))
 def test_later_claim_refused(self):
  self.put(self.exp/'claims/02.json',{})
  with self.assertRaisesRegex(ValueError,'later slot'):gate.check(self.root,self.exp,1,self.now(1))
 def update_record(self,folder,**changes):
  record=json.loads((folder/'record.json').read_text());record.update(changes);raw=json.dumps(record).encode();self.put(folder/'record.json',raw);self.put(folder/'RECORDED.json',{'status':'GITHUB_RECORDED','record_sha256':hashlib.sha256(raw).hexdigest()})
 def update_release_report(self,release,**changes):
  report=json.loads((release/'report.json').read_text());report.update(changes);raw=json.dumps(report).encode();self.put(release/'report.json',raw);proof=json.loads((release/'PUBLISHED.json').read_text());proof['report_sha256']=hashlib.sha256(raw).hexdigest();self.put(release/'PUBLISHED.json',proof)
 def test_wrong_release_path_refused(self):
  folder,_=self.prior(1);self.update_record(folder,release='engine-v1/releases/exhibit-mission/OTHER')
  with self.assertRaisesRegex(ValueError,'release path'):gate.check(self.root,self.exp,2,self.now(2))
 def test_wrong_report_game_refused_despite_consistent_hashes(self):
  _,release=self.prior(1);self.update_release_report(release,game_id='OTHER')
  with self.assertRaisesRegex(ValueError,'release ID'):gate.check(self.root,self.exp,2,self.now(2))
 def test_wrong_proof_run_refused(self):
  _,release=self.prior(1);proof=json.loads((release/'PUBLISHED.json').read_text());proof['run_id']='OTHER';self.put(release/'PUBLISHED.json',proof)
  with self.assertRaisesRegex(ValueError,'release ID'):gate.check(self.root,self.exp,2,self.now(2))
 def test_failed_report_refused_despite_consistent_hashes(self):
  _,release=self.prior(1);self.update_release_report(release,status='FAILED')
  with self.assertRaisesRegex(ValueError,'not passing'):gate.check(self.root,self.exp,2,self.now(2))
 def test_record_validated_sha_refused_despite_valid_receipt(self):
  folder,_=self.prior(1);self.update_record(folder,validated_sha256='WRONG')
  with self.assertRaisesRegex(ValueError,'validated SHA'):gate.check(self.root,self.exp,2,self.now(2))
 def test_blocked_previous_refused(self):
  folder,_=self.prior(1);self.update_record(folder,status='BLOCKED')
  with self.assertRaisesRegex(ValueError,'BLOCKED'):gate.check(self.root,self.exp,2,self.now(2))
 def test_no_allow_next_refused(self):
  self.prior(1);self.put(self.exp/'results/01.json',{'run_id':'triad-20261019-01','status':'PASS','allow_next':False})
  with self.assertRaisesRegex(ValueError,'requests stop'):gate.check(self.root,self.exp,2,self.now(2))
if __name__=='__main__':unittest.main(verbosity=2)
