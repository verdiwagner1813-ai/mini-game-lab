# v1.1 一回限りの予約実証（再開後の現行指示）

これは承認済みのミニゲーム自動改善エンジンv1.1の一回限りの予約実証です。3回の定期実行は再承認まで禁止。旧README.md/experiment-plan.jsonの3回承認記述は失効しておりSTART_HERE.md/experiment-plan-resumed.jsonが正本です。GitHub verdiwagner1813-ai/mini-game-lab のmainが正本です。新しいAPIキー、追加課金、外部契約、公開/権限設定の変更、原本/完成版/既存記録の上書きや削除は禁止。既存契約の利用枠の範囲でのみ実行し、上限や追加設定で止まったら回避しない。定期タスクの作成/再登録/有効化はしない。

1. 前回のローカル領域や環境があると仮定せず、GitHub接続でmainとengine-v1.1/START_HERE.mdを読めることを確認。cloud_environment.environment_statusが利用可能なら呼ぶ。shell/書込可能一時領域/Python/Node/Chromium/Playwright/GitHub書込みを確認。通常の認証・プロキシ・CA設定を保つ。秘密や環境変数の値を記録しない。
2. 新しい一時ディレクトリへmainをcloneし、AGENTS.md/PROJECT_RULES.md、engine-v1.1/START_HERE.mdを読む。必要なshellやブラウザが無い、承認待ち、認証拒否ならBLOCKED。未実行テストをPASSとしない。環境が同じだった場合は冷起動成功と主張しない。
3. game_id=exhibit-mission。未使用run-idを生成し、continuity.pyのlatestで最新合格版を検証し、run --invocation scheduled --publishで既存engine-v1に渡す。候補の元が前回最新合格版のSHAと一致することを確認。既存Playwrightは/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core、Chromiumは/usr/bin/chromiumの場合があるが、存在確認してから指定する。追加インストールやキー設定はしない。
4. AI_REQUESTは本当の独立AIへ渡す。AIは候補と目的・禁止事項・過去改善を読み、少なくとも複数の改善候補を比較し、低リスクで意味のある案を1つ選んで候補HTMLだけを編集。企画/評価の理由をsummaryに記す。すでに十分なら編集せずskip:true,reason,ai_agentで理由を返す。テスト・設定・エンジンを合格させる目的で改変しない。
5. 共通検証・Chromium実操作・登録済みゲーム固有テストを実行。不合格時は失敗ログをAIへ返し最大3回修正。実際のブラウザ合格と保存readbackがなければ成功としない。新機能の挙動も可能な範囲で実ブラウザ確認し、未確認部分を明記。
6. 合格時だけ--publishで新しいreleaseをmainへ追加。wrapperのrecord.jsonも新規保存。source/過去版は保持。不合格/改善不要/BLOCKEDならゲーム版を増やさず理由を新規run記録に残す。書込みも不可能なら会話に正確に報告。
7. mainを新しい場所へ取得してHTML/PUBLISHED/run記録と引継ぎSHAを読み戻し確認。report.pyで未使用名の比較レポートを生成し、新規保存。元ファイルが不変で差分が追加だけであることも確認する。
8. 60分以内を目標とし、プログラムのdeadlineを3600秒以下にする。予約ランナー全体の強制停止を保証できない点を報告。ゲームの完成リンク・改善/見送り理由・実行テスト・実際のコミット・未確認点を日本語で報告。これは一回分のみであり、次の予約を勝手に作らない。

今回のrun-idはscheduled-v11-20261018-a。すでに同じrunの合格ゲームと記録がある場合は内容を照合して結果を報告し、ゲームを再実行しない。一度だけの実証で、残りの予約は作成しない。終了後の比較レポートはengine-v1.1/reports/scheduled-v11-20261018-a.htmlへ新規追加（存在すれば更新せず照合）。追加専用のGitHub create_fileまたは差分Aのみの非force Gitコミットを使える。環境能力・タスクID/予約時刻との照合・冷起動未検証を実行記録の補足ファイルに追加してもよい。新規保存したゲーム・記録のURLを報告する。
