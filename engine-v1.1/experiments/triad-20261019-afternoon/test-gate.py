#!/usr/bin/env python3
"""Reuse the existing 18 safety checks and test the new time adapter."""
import importlib.util,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('afternoon_gate',HERE/'gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
spec=importlib.util.spec_from_file_location('existing_gate_tests',HERE.parent/'triad-20261019/test-gate.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);old.gate=gate
class AfternoonGateTests(old.GateTests):
 def setUp(self):
  super().setUp();self.exp=self.root/'engine-v1.1/experiments/triad-20261019-afternoon';self.exp.mkdir(parents=True)
 def test_japan_times(self):
  for s,h in zip(gate.TIMES,[16,18,20]):
   t=datetime.fromisoformat(s).astimezone(timezone(timedelta(hours=9)));self.assertEqual((t.day,t.hour,t.minute),(19,h,30))
 def test_morning_not_due(self):
  with self.assertRaisesRegex(ValueError,'not due'):gate.check(self.root,self.exp,1,datetime.fromisoformat('2026-10-19T07:30:00+09:00'))
 def test_legacy_claim_refused(self):
  self.put(self.root/'engine-v1.1/experiments/triad-20261019/claims/01.json',{})
  with self.assertRaisesRegex(ValueError,'Legacy'):gate.check(self.root,self.exp,1,self.now(1))
 def test_existing_own_record_refused(self):
  self.prior(1)
  with self.assertRaisesRegex(ValueError,'already exists'):gate.check(self.root,self.exp,1,self.now(1))
if __name__=='__main__':unittest.main(verbosity=2)
