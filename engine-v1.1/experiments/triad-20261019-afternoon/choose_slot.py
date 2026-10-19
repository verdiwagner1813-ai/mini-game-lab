#!/usr/bin/env python3
"""Map actual delivery time to exactly one authorized slot; never catch up."""
import json
from datetime import datetime,timedelta,timezone
TIMES=[datetime.fromisoformat(t) for t in ['2026-10-19T07:30:00+00:00','2026-10-19T09:30:00+00:00','2026-10-19T11:30:00+00:00']]
def choose(now):
    for slot,due in enumerate(TIMES,1):
        if due-timedelta(seconds=10)<=now<due+timedelta(hours=1):
            return {'status':'SLOT_IDENTIFIED_NOT_EXECUTED','slot':slot,'run_id':f'triad-20261019-{slot:02}','prompt':f'engine-v1.1/experiments/triad-20261019-afternoon/PROMPT-{slot:02}.md','seconds_until_due':max(0,(due-now).total_seconds())}
    raise ValueError('Outside all authorized slot windows; do not catch up or create another schedule')
def main():
    try:print(json.dumps(choose(datetime.now(timezone.utc))));return 0
    except Exception as e:print(json.dumps({'status':'BLOCKED','reason':str(e)}));return 1
if __name__=='__main__':raise SystemExit(main())
