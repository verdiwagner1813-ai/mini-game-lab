# v1.1 再開後の正本

利用制限リセット後のユーザー指示を最優先する。**3回の定期実行は新たな承認が得られるまで有効化しない。追加課金・APIキー登録を行わない。** 原依頼の1回限りの予約実証のみ進める。

中断前のREADME.mdとexperiment-plan.jsonは草案として内容を保持した。そこにある「3回承認済み」「最初の成功後に残り2回を登録」は失効。予約の現行設定は[experiment-plan-resumed.json](experiment-plan-resumed.json)、実行指示は[ONE_SHOT_PROMPT.md](ONE_SHOT_PROMPT.md)。旧草案から予約を登録しない。Pythonプログラム自体に予約登録の機能はない。

## 完成した実装

- continuity.pyがGitHub mainの保存済み合格版を検証し、最新の版を既存engine-v1へ渡す。日時やファイル名順で選ばず、Git祖先・導入commit・合格試験・HTML/report/ZIP/receiptの整合性を照合する。
- 原本の代わりに最新HTMLを一時cloneの実行用sourceに置く。GitHubや元の作業領域の原本・過去版・設定・既存v1は変更しない。
- AIは改善案を比較・選定・編集し、失敗時に再検討。プログラムは共通/作品固有テスト、最大3回修正、合格版生成、既存publisherによるmain追加保存と読み戻しを行う。
- 改善不要は初回にskip応答で理由を記録し、ゲーム版を増やさない。失敗・BLOCKEDでも正常な旧版は保持する。
- 実行記録はengine-v1.1/runs/<game>/<run>/record.jsonとRECORDED.json、新しい合格版はengine-v1/releases/<game>/<run>/へ追加する。ローカルPASS、ゲーム送信、記録送信を別々に確認する。
- 同ゲームの別版が検証中に公開されたら古い引継ぎ元からの保存を拒否。同ゲームの同時改善は運用でも避ける。

## 実行

```sh
python engine-v1.1/continuity.py latest --game exhibit-mission
# 環境ごとに既存の実行ファイル/モジュールがあることを確認して設定
export PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core
export CHROMIUM_PATH=/usr/bin/chromium
python engine-v1.1/continuity.py run --game exhibit-mission --run-id UNIQUE_ID --work-root /tmp/continuity-work --publish --timeout-seconds 3600 --invocation interactive
```

AI_REQUESTを実際の独立AIへ渡し、編集後のready/summary/ai_agentを返す。初回に編集せず見送る場合はskip/reason/ai_agent。CodexにONE_SHOT_PROMPT.mdの実行を依頼すれば、利用者の毎回のコード編集を必要とせず中継できる。Python単体にはAIモデルがなく、Codexのライブブリッジまたは既存AIアダプタが必要。新APIは設定していない。

予約呼出しだけ--invocation scheduledを指定する。このmetadataは自己申告なので外部のタスクID/実行時刻と照合し、通常対話で動いたことを予約成功と主張しない。

記録だけ未送信なら、ゲームを再実行せず以下で再送できる。既存の保存先は更新しない。

```sh
python engine-v1.1/continuity.py record --file /outside/work/record.json --timeout-seconds 120
python engine-v1.1/report.py --output engine-v1.1/reports/UNUSED_NAME.html
```

## 検証と制限

再開時、v1.1継承/見送り/不整合拒否/最大4評価/重複記録拒否/競合拒否の14試験PASS。既存v1の7試験とpublisherの4試験は中断前にPASSしており、完了済み検査は重複実行していない。現在環境のChromium HTTP操作も中断前にPASS。独立テスト担当がコードを読み取りレビューした。

予約タスクを作成できることと、予約でAI改善・Chromium・GitHub保存まで動くことは別。停止後の冷起動は未検証。60分のdeadlineと子プロセス群終了処理を設けるが、クラウド予約ランナー全体の強制終了は保証できない。期限切れ時はローカル記録だけになり得る。

追加課金・APIキー・外部契約・公開設定変更はなし。既存契約の残量/料金上限は未確認。利用制限に達したら停止し、勝手に有料枠へ移らない。

学校Chromebook/Windows実機、実タッチ端末、file://、HTTPS運用、児童試遊・教育効果は未確認。GitHub HTMLページはソース表示であり、プレイするにはダウンロードする。

GitHub Actionsはrunnerの作り直しやtimeout設定に向くが、AI接続には別途認証が必要。GitHub利用枠/費用・設定を確認してから検討する。今回はworkflowや新サービスを作成しない。

## 新作品

既存engine-v1の登録テンプレートを使い、未使用IDの設定（目的・対象年齢・基本ルール・禁止事項・元HTML・開始/操作セレクタ）と固有テストを追加する。以後は同じIDの最新合格releaseを自動継承するので、毎回sourceを書き換える必要はない。
