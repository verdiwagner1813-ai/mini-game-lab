【現行承認：午後の3枠のみ】2026-10-19 16:30/18:30/20:30 Asia/Tokyo。残量数値が未確認でも既存契約内で予約することは承認済み。上限時は停止し、追加課金・キー登録・有料枠切替は禁止。朝の未登録計画を実行しない。実験の全パスはengine-v1.1/experiments/triad-20261019-afternoon配下（claims/results/STOPPED/COMPLETED/COMPARISON/REGISTRATION）。run-idは未使用を確認済みのtriad-20261019-NNを維持する。

# 2026年10月19日 3回限定実験の実行規約

今回のユーザー承認は、この実験の16:30/18:30/20:30（Asia/Tokyo）3枠だけ。旧START_HERE.md/experiment-plan-resumed.jsonの再承認条件は今回の承認によりこの3枠について満たされた。原本・過去版・過去記録を変更/削除しない条件は継続。新しいサービス/APIキー/課金設定・公開/権限設定変更は禁止。4回目や代替時刻を勝手に登録しない。

## 予約方式と開始

前回の成功したCodexスレッドのクラウド予約を使用。通常通知だけのChatGPTリマインダーへ置き換えない。登録が返したthread_idを前回の成功記録に照合する。ただしこれは将来の認証・環境停止後の冷起動保証ではない。

毎回GitHub接続でmainの本規約・PLAN.json・REGISTRATION.jsonを読む。前回ローカル領域を仮定せず、新しい作業領域へmainをclone。環境statusがあれば確認し、shell/Python/Node/Chromium/既存Playwright/GitHub権限を確認。秘密・環境変数値を出力しない。通常のプロキシ/CA/認証を維持。

## 全体停止と並行防止

1. STOPPED.json/COMPLETED.jsonがあれば改善に着手しない。後続予約が残っていればREGISTRATION.json記載の当該実験タスクだけをpauseする。
2. 固定slotとrun-idはPLAN.jsonから取得。予定から60分を過ぎた枠、順序逆転、前回が未着手/進行中/記録未検証なら追い付き実行せず停止。数秒早く届いた場合だけ予定時刻まで短く待つ。
3. cloneで `python engine-v1.1/experiments/triad-20261019-afternoon/gate.py --slot N` を実行。exit0とELIGIBLE_NOT_EXECUTED以外ならゲームを実行しない。第2/3回は前回のrecord+RECORDED、PASSならrelease+PUBLISHEDとhash、resultsのallow_nextを検証してから着手。前回FAILEDでも権限/環境/上限の障害でないと確認できる場合のみallow_next可能。
4. gate通過後、GitHub create_fileで `engine-v1.1/experiments/triad-20261019-afternoon/claims/NN.json` を一度だけ新規作成（slot/run_id/時刻/selected source等）。shaを渡さず更新しない。既存なら内容同一でもゲーム再実行禁止。create timeoutはreadbackで確認し、存在するclaimを上書き・再実行しない。固定claimが重複呼出しの片方だけを通す。claim書込み権限がなければ改善しない。
5. 利用上限・権限/認証問題・実行能力不足・前回未完了・時刻異常ならSTOPPED.jsonを新規追加して理由を記録し、残り当該実験タスクをpause。STOPPEDが既存なら変更せず報告。書込み自体が拒否されたら会話へ報告し、後続は前回完了証拠がないため着手しない。利用制限で停止処理すら呼べない場合、予約システムの物理停止は保証できず、後続の事前条件で改善を拒否する。

同じゲームへの別の手動改善も実験中は避ける。既存wrapperの公開直前latest競合検知も再利用し、古い元版での保存を拒否する。

## AI改善と検証

既存 `engine-v1.1/continuity.py latest --game exhibit-mission` と `run --game exhibit-mission --run-id triad-20261019-NN --work-root <new external work root> --publish --invocation scheduled --timeout-seconds <remaining budget>` を使用。最新合格版を元にし、登録sourceに戻さない。第1回の基準は前回scheduled-v11-20261018-aだが、新しい合格版があればGit履歴で検証した最新を使う。

AI_REQUESTを本当の独立AIへ渡し、目的・対象・基本ルール・禁止事項・過去改善を読み、複数案を比較して低リスクの1案を選ぶ。候補HTMLだけを編集しsummaryに比較と選定理由を残す。無理な改善はせず未編集skip/reason/ai_agentで見送る。プログラム自身が改善を思いつくと表現しない。

既存の共通HTML/JS・Chromium HTTP操作・ゲーム固有検査を再利用。初回＋不合格時の最大3回修正。新機能の挙動も候補上で追加のブラウザ操作検査を行い、その合格を確認してからready応答を返す。テストや設定を改変して合格させない。前回の取消フォーカス改善やundo/対象強調が後退していないかも確認する。

合格した版のみ既存publisherでmainへ追加し、HTML/ZIP/report/PUBLISHEDとrecord/RECORDEDを再取得・hash照合。途中候補・不合格HTMLを公開しない。未送信の合格とGitHub保存成功は別。送信不明なら成功とせず停止。wrapperのrecord保存だけ未送信ならrecordコマンドで追送可能だが既存pathは更新しない。

## 記録・比較・終了

各回に `results/NN.json` を新規追加：slot/run_id、実際の開始終了、status(PASS/SKIPPED/FAILED/BLOCKED)、source path/SHA/導入commit、新SHA、改善案比較と選定、各検査結果、ゲーム保存commit、record保存commit、ゲーム/ZIPリンク、allow_next、未確認事項。allow_next=trueは全保存証拠を検証済みかつ継続可能な場合だけ。BLOCKED/上限/権限/環境障害ならfalse。

各回に既存report.pyで `reports/triad-20261019-afternoon-NN.html` の比較snapshotを新規生成・保存。第三回または全体停止時に `COMPARISON.md` を新規作成し、前回成功版＋3枠を比較。未実行は未実行と明記、テストしていない版をPASSにしない。第3回終了時COMPLETED.jsonを新規追加し、3件すべて終わったことを示す（ゲーム3作PASSとは別）。以後の予約は作成しない。

全工程55分を目標に残時間を管理、wrapperは最大50分程度とし記録用時間を残す。プログラムのdeadline/子プロセス終了は利用するがクラウド予約ランナー全体の強制終了は保証できない。学校実機・実児童・file://・冷起動は未確認。追加課金なしでも既存利用枠は消費し得る。残量数値はツール取得不可。
