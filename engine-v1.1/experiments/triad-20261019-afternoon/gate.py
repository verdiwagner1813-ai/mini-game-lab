#!/usr/bin/env python3
"""Reuse the verified three-slot gate with the newly approved afternoon times."""
import argparse,importlib.util,json
from datetime import datetime,timezone
from pathlib import Path
EXPERIMENT=Path(__file__).resolve().parent
ROOT=EXPERIMENT.parents[2]
LEGACY=ROOT/'engine-v1.1/experiments/triad-20261019'
spec=importlib.util.spec_from_file_location('verified_three_slot_gate',LEGACY/'gate.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
TIMES=['2026-10-19T07:30:00+00:00','2026-10-19T09:30:00+00:00','2026-10-19T11:30:00+00:00']
legacy.TIMES=TIMES

def check(root,experiment,slot,now):
    # Morning registrations were never made. Their fixed run IDs are reserved
    # for this approved schedule only while no old run has claimed them.
    old=root/'engine-v1.1/experiments/triad-20261019/claims'
    if old.exists() and any(old.glob('*.json')):raise ValueError('Legacy experiment already claimed a run; refuse duplicate experiment')
    if slot in (1,2,3) and (root/'engine-v1.1/runs/exhibit-mission'/f'triad-20261019-{slot:02}').exists():raise ValueError('This run record already exists; do not execute again')
    return legacy.check(root,experiment,slot,now)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--slot',type=int,required=True);a=p.parse_args()
    try:print(json.dumps(check(ROOT,EXPERIMENT,a.slot,datetime.now(timezone.utc))));return 0
    except Exception as e:print(json.dumps({'status':'BLOCKED','reason':str(e)}));return 1
if __name__=='__main__':raise SystemExit(main())
