#!/usr/bin/env python3
import importlib.util,unittest
from pathlib import Path
from datetime import timedelta,timezone,datetime
spec=importlib.util.spec_from_file_location('slot_dispatch',Path(__file__).with_name('choose_slot.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DispatchTests(unittest.TestCase):
 def test_three_exact_times(self):
  for n,t in enumerate(m.TIMES,1):self.assertEqual(m.choose(t)['slot'],n)
 def test_three_japan_times(self):
  for t,h in zip(m.TIMES,[16,18,20]):self.assertEqual(t.astimezone(timezone(timedelta(hours=9))).hour,h)
 def test_early_delivery(self):
  for n,t in enumerate(m.TIMES,1):self.assertEqual(m.choose(t-timedelta(seconds=2))['slot'],n)
 def test_before_start_rejected(self):
  with self.assertRaises(ValueError):m.choose(m.TIMES[0]-timedelta(seconds=11))
 def test_expired_slot_not_replayed(self):
  with self.assertRaises(ValueError):m.choose(m.TIMES[0]+timedelta(hours=1))
 def test_next_day_no_fourth_slot(self):
  with self.assertRaises(ValueError):m.choose(m.TIMES[2]+timedelta(days=1))
 def test_after_last_window_rejected(self):
  with self.assertRaises(ValueError):m.choose(m.TIMES[2]+timedelta(hours=1))
if __name__=='__main__':unittest.main(verbosity=2)
