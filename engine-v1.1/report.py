#!/usr/bin/env python3
"""Generate a new, offline comparison snapshot. Never overwrite an earlier report."""
import argparse, hashlib, html, json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='https://github.com/verdiwagner1813-ai/mini-game-lab'
def sha(b): return hashlib.sha256(b).hexdigest()
def records(root=ROOT):
    rows=[]
    for p in sorted((root/'engine-v1/releases').glob('*/*/PUBLISHED.json')):
        try:
            receipt=json.loads(p.read_text()); folder=p.parent
            raw=(folder/'report.json').read_bytes(); report=json.loads(raw)
            if receipt.get('status')!='GITHUB_PUBLISHED' or receipt.get('game_sha256')!=sha((folder/'game.html').read_bytes()) or receipt.get('report_sha256')!=sha(raw):
                raise ValueError('receipt/hash mismatch')
            attempts=report['attempts']; final=attempts[-1]
            if final.get('status')!='PASS' or any(t.get('status')!='PASS' for t in final['tests']):raise ValueError('not passing')
            lineage=report.get('continuity',{})
            rows.append({'game':report['game_id'],'run':report['run_id'],'status':'PASS / GitHub保存済み',
                         'summary':final.get('ai_acknowledgement',{}).get('summary',''),
                         'source':lineage.get('source_path',report.get('source','')),
                         'tests':str(len(final['tests']))+'件PASS / 評価'+str(len(attempts))+'回',
                         'game_path':str((folder/'game.html').relative_to(root)),
                         'report_path':str((folder/'report.json').relative_to(root)),
                         'when':report.get('finished_utc','')})
        except (ValueError,KeyError,OSError) as exc:
            rows.append({'game':p.parent.parent.name,'run':p.parent.name,'status':'証拠不整合','summary':str(exc),'source':'','tests':'未確認','game_path':'','report_path':str(p.relative_to(root)),'when':''})
    for p in sorted((root/'engine-v1.1/runs').glob('**/record.json')):
        try:
            raw=p.read_bytes(); r=json.loads(raw); proof=json.loads((p.parent/'RECORDED.json').read_text())
            if proof.get('status')!='GITHUB_RECORDED' or proof.get('record_sha256')!=sha(raw):raise ValueError('record proof mismatch')
            status=r.get('status','UNKNOWN')
            if status=='PASS' and r.get('github_status')=='GITHUB_PUBLISHED': continue
            rows.append({'game':r.get('game_id',''),'run':r.get('run_id',p.parent.name),'status':status,'summary':r.get('skip_reason',r.get('publication_error',r.get('error',''))),'source':str(r.get('source',{}).get('path','')),'tests':'ゲーム版を追加しない','game_path':'','report_path':str(p.relative_to(root)),'when':r.get('finished_utc','')})
        except (ValueError,OSError):continue
    return sorted(rows,key=lambda r:(r['game'],r['when'],r['run']))
def render(rows):
    e=lambda x:html.escape(str(x),quote=True)
    def link(path,text):return '<a href="'+e(BASE+'/blob/main/'+path)+'">'+e(text)+'</a>' if path else '—'
    body=''.join('<tr>'+''.join('<td>'+e(r[k])+'</td>' for k in ('game','run','status','summary','source','tests'))+'<td>'+link(r['game_path'],'HTMLを取得')+' / '+link(r['report_path'],'記録')+'</td></tr>' for r in rows)
    return '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ミニゲーム改善 比較記録</title><style>body{font:16px/1.6 system-ui,sans-serif;margin:24px;color:#172637;background:#f6f8fb}table{border-collapse:collapse;background:white;min-width:900px}td,th{border:1px solid #ccd5df;padding:10px;text-align:left;vertical-align:top}main{overflow:auto}a{color:#164d9c}</style><h1>ミニゲーム改善 比較記録</h1><p>GitHubから取得した版の保存証跡・ハッシュを照合したスナップショット。HTMLリンクはソース取得ページで、プレイにはダウンロードが必要です。時系列の最新判定はcontinuity.pyがGit履歴で行います。</p><main><table><thead><tr><th>作品</th><th>実行</th><th>結果</th><th>改善内容・理由</th><th>引継ぎ元</th><th>検査</th><th>成果物</th></tr></thead><tbody>'+body+'</tbody></table></main><p>Linux Chromium HTTPの自動試験と、学校端末・実児童での確認は区別してください。定期実行の起動保証・費用残量を示すページではありません。</p></html>\n'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:f.write(render(records()))
    print(json.dumps({'status':'REPORT_CREATED','path':str(out),'rows':len(records())}))
if __name__=='__main__':main()
