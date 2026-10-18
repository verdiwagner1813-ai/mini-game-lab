#!/usr/bin/env python3
"""Read-only eligibility gate for three approved slots. Does not schedule or edit games."""
import argparse,hashlib,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXPERIMENT=Path(__file__).resolve().parent
TIMES=['2026-10-18T22:30:00+00:00','2026-10-19T00:30:00+00:00','2026-10-19T02:30:00+00:00']
def check(root,experiment,slot,now):
    if slot not in (1,2,3):raise ValueError('Only slots 1, 2, 3 are authorized')
    for name in ('STOPPED.json','COMPLETED.json'):
        if (experiment/name).exists():raise ValueError('Experiment already stopped/completed: '+name)
    due=datetime.fromisoformat(TIMES[slot-1])
    if now < due-timedelta(seconds=10):raise ValueError('Slot is not due yet')
    if now >= due+timedelta(minutes=60):raise ValueError('Slot window expired; no catch-up execution')
    if (experiment/'claims'/f'{slot:02}.json').exists():raise ValueError('Claim already exists; never execute the same slot twice')
    if any((experiment/'claims'/f'{s:02}.json').exists() for s in range(slot+1,4)):
        raise ValueError('A later slot already started; ordering invalid')
    for previous in range(1,slot):
        if not (experiment/'claims'/f'{previous:02}.json').is_file():raise ValueError('Previous slot never claimed; no catch-up')
        run_id=f'triad-20261019-{previous:02}'
        folder=root/'engine-v1.1/runs/exhibit-mission'/run_id
        raw=(folder/'record.json').read_bytes();record=json.loads(raw)
        receipt=json.loads((folder/'RECORDED.json').read_text())
        if receipt.get('status')!='GITHUB_RECORDED' or receipt.get('record_sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('Previous record receipt/hash mismatch')
        if record.get('game_id')!='exhibit-mission' or record.get('run_id')!=run_id:raise ValueError('Previous record ID mismatch')
        status=record.get('status')
        if status not in ('PASS','SKIPPED','FAILED'):raise ValueError('Previous slot not terminal or BLOCKED; stop experiment')
        if status=='PASS':
            if record.get('github_status')!='GITHUB_PUBLISHED':raise ValueError('Previous game not published')
            expected_release=f'engine-v1/releases/exhibit-mission/{run_id}'
            if record.get('release')!=expected_release:raise ValueError('Previous release path mismatch')
            release=root/expected_release;html=(release/'game.html').read_bytes();report_raw=(release/'report.json').read_bytes()
            proof=json.loads((release/'PUBLISHED.json').read_text());report=json.loads(report_raw)
            if proof.get('status')!='GITHUB_PUBLISHED' or proof.get('game_sha256')!=hashlib.sha256(html).hexdigest() or proof.get('report_sha256')!=hashlib.sha256(report_raw).hexdigest():raise ValueError('Previous release proof/hash mismatch')
            if report.get('status')!='LOCAL_PASS_AWAITING_GITHUB':raise ValueError('Previous report not passing')
            for item in (report,proof):
                if item.get('game_id')!='exhibit-mission' or item.get('run_id')!=run_id:raise ValueError('Previous release ID mismatch')
            if report.get('validated_sha256')!=proof['game_sha256'] or record.get('validated_sha256')!=proof['game_sha256']:raise ValueError('Previous validated SHA differs')
        result=json.loads((experiment/'results'/f'{previous:02}.json').read_text())
        if result.get('run_id')!=run_id or result.get('status')!=status or result.get('allow_next') is not True:raise ValueError('Previous slot missing verified completion or requests stop')
    return {'status':'ELIGIBLE_NOT_EXECUTED','slot':slot,'run_id':f'triad-20261019-{slot:02}','claim':str((experiment/'claims'/f'{slot:02}.json').relative_to(root))}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--slot',type=int,required=True);a=p.parse_args()
    try:print(json.dumps(check(ROOT,EXPERIMENT,a.slot,datetime.now(timezone.utc))));return 0
    except Exception as e:print(json.dumps({'status':'BLOCKED','reason':str(e)}));return 1
if __name__=='__main__':raise SystemExit(main())
