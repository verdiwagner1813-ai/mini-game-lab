これはユーザーが承認したミニゲーム自動改善エンジンv1.1の3回限定予約実験、固定slot=1、run-id=triad-20261019-01 の一回分です。指定枠は2026年10月19日07:30 Asia/Tokyo。前回成功したCodexクラウド実行とAIライブブリッジを使い、通常の通知だけで終わらせない。4回目や代替予約を作らない。追加課金・APIキー・外部契約・公開/権限設定変更は禁止。既存の原本/完成版/コード/設定/記録は上書き・削除しない。

GitHub verdiwagner1813-ai/mini-game-lab のmainから engine-v1.1/experiments/triad-20261019/RUN_PROTOCOL.md と PLAN.json と REGISTRATION.json を最初に読み、この最新の3枠承認を確認して従う。旧START_HERE.mdの再承認待ちは今回の明示承認でこの3枠についてのみ満たされた。REGISTRATION.jsonがなければ登録準備未完了として改善を開始しない。

過去の/workspaceがあると仮定せず、GitHub読取り・環境status・shell/書込み可能一時領域/Python/Node/Chromium/Playwright/GitHub書込みを確認。認証/プロキシ/CAを維持、秘密値を出力しない。新しい領域へmainをcloneしてAGENTS.mdとPROJECT_RULES.mdを読む。既存Playwright/Chromiumの所在は存在確認して指定。追加インストールやキー設定で回避しない。

STOPPED.json/COMPLETED.jsonを確認。あればゲーム改善は実行しない。予定枠が過ぎて60分を超えていたり、順番逆転、前回未完了/未送信なら追い付き実行をせず全体停止。コード gate.py --slot 1 のexit0かつELIGIBLE_NOT_EXECUTEDを要求。前回record/RECORDED/hash、PASS時release/PUBLISHED/hash、results/前slot.jsonのallow_nextを照合。確認できないものは成功としない。

通過後だけGitHub create_fileでclaims/01.jsonを新規追加。更新shaを使わず、既存claimなら同一でもゲームを再実行しない。create timeoutもreadbackし二重実行を避ける。前slotの完了証拠がない限り同じゲームの並行改善を開始しない。

既存continuity.py latestで最新合格版を選び、run --game exhibit-mission --run-id triad-20261019-01 --work-root <new outside repo work> --publish --invocation scheduled --timeout-seconds <remaining budget>を使う。毎回最新の合格版から開始し、固定の元原本に戻さない。実行時間は全体55分目標、wrapperは50分以下で記録時間を残す。

AI_REQUESTは実際の独立AIへ渡す。AIが複数改善案を比較し1案を選び、候補HTMLだけを編集する。目的/基本ルールを維持し、undo・対象強調・取消後フォーカス等の以前の改善を保つ。企画/選定理由をsummaryへ記録。無理な変更はせず未編集skipで見送り可能。新機能操作も追加ブラウザ検査して合格後readyを中継。既存共通/作品固有のChromium HTTP検査を使い、不合格なら初回後最大3回修正。テストや設定を合格のため変更しない。

合格版だけ既存publisherでmainへ新規追加。保存後は別cloneでHTML/ZIP/report/PUBLISHED/record/RECORDEDのhashと継承元を検証。ローカルPASSとGitHub保存を区別。不合格版を公開しない。送信未確認・利用上限・権限/環境問題は停止し、勝手な課金や別サービスへ移行しない。

各回results/01.jsonへstatus/変更内容/比較候補/選定理由/検査結果/継承元SHA/新SHA/ゲームと記録のcommit/完成HTML・ZIPリンク/allow_next/未確認点を新規保存。BLOCKEDや権限/環境/上限障害はallow_next=false、STOPPED.json新規追加と残り当該実験タスクのpause（REGISTRATION.jsonのIDだけ）を試みる。停止記録/予約pauseも不能なら会話へ正確に報告。後続は前回完了証拠なしで改善しない。

比較snapshot engine-v1.1/reports/triad-20261019-01.htmlを新規保存。slot3または全体停止時はCOMPARISON.mdで前回成功版と全3枠を比較し、未実行を未実行と記す。slot3完了後COMPLETED.jsonを新規保存し、その後は予約作成/再実行しない。3枠終了は3版合格とは別。最後に実際の変更/試験/commit/完成ゲームリンク/未確認を日本語で報告。将来の認証・利用残量・冷起動・学校実機・60分のクラウド全体強制停止を保証しない。
