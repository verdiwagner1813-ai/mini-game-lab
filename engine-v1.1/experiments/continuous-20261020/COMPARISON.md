# 展示室：1回のCodex実行内での3連続改善

実施日：2026年10月20日（日本時間）。既存v1.1を利用し、3回すべて改善・検証・GitHub mainへの追加保存まで完了。予約方式は使用していない。

|回|異なる改善内容|引継ぎ元|検証結果|ゲームcommit|完成版|
|---|---|---|---|---|---|
|1|ヒント本文の読み上げ用通知属性|開始時の最新合格版|既存5検査＋追加UI 合格|`b53a4fc9679f7a030068dc10c9a977674a512d92`|[HTML](https://github.com/verdiwagner1813-ai/mini-game-lab/blob/main/engine-v1/releases/exhibit-mission/continuous-20261020-01/game.html) / [ZIP](https://github.com/verdiwagner1813-ai/mini-game-lab/raw/refs/heads/main/engine-v1/releases/exhibit-mission/continuous-20261020-01/game.zip)|
|2|手がかり対象の可視バッジ|1回目の合格版|既存5検査＋追加UI＋前改善の回帰 合格|`bd40b8465a7c1f011c4a60c52b46ff2fe6c29e24`|[HTML](https://github.com/verdiwagner1813-ai/mini-game-lab/blob/main/engine-v1/releases/exhibit-mission/continuous-20261020-02/game.html) / [ZIP](https://github.com/verdiwagner1813-ai/mini-game-lab/raw/refs/heads/main/engine-v1/releases/exhibit-mission/continuous-20261020-02/game.zip)|
|3|交換した2作品名の通知|2回目の合格版|既存5検査＋追加UI＋前改善の回帰 合格|`0b6cc683b4a36d50a103800ae6c024708711a665`|[HTML](https://github.com/verdiwagner1813-ai/mini-game-lab/blob/main/engine-v1/releases/exhibit-mission/continuous-20261020-03/game.html) / [ZIP](https://github.com/verdiwagner1813-ai/mini-game-lab/raw/refs/heads/main/engine-v1/releases/exhibit-mission/continuous-20261020-03/game.zip)|

## 実際に実行した処理

新しいcloneで最新合格版をGit履歴・保存証跡・SHA照合して開始。各回のAI_REQUESTを実際の独立AI /root/child_viewへ渡し、複数案からの選定と候補だけの編集を実施。独立テストAI /root/testingが追加UIを確認してから、既存エンジンへready応答を中継。合格・GitHub保存確認後に次のrunを起動し、3回は並行制作していない。Python自体が企画したり、新しいモデルAPIを追加したりしたわけではない。

各回、既存のHTML/JS検証、Chromium HTTP操作、推理ロジック（生成2400件・有限手がかり組4960件）、全体操作、対象強調の5検査を実行。3回ともこの既存5検査は初回合格で、候補の修正再試行は0回。最大3回修正の既存制限は維持した。

追加UIは1366×768と360×800タッチ模擬で実行。1回目はヒント3段階・次問リセット、2回目は単体/2作品の対象バッジ・交換追従・解除・収まり、3回目は交換2名の通知・2箇所だけの交換・undo復元を検査。後続で前の改善の回帰も実行し、計6追加/回帰スイートが合格。ブラウザエラー・外部要求なし。2回目の画面は親AIも画像で確認した。

2回目の新規補助テストで交換後も手がかり通知を保持すると誤期待した箇所は、既存の交換操作通知との違いを明確にして修正後再実行した。候補ゲームや既存登録済みテストをそのために変更してはいない。

最後に別cloneへmainを取得し、3版すべてのHTML/ZIP/report/PUBLISHEDとrecord/RECORDEDを読み戻してハッシュ照合。各source SHAが直前の合格HTML SHAと一致し、現在のlatestが3回目を選ぶことを確認した。開始時の117ファイルは全て同じGit blobで保持。古い原本・完成版・実験記録・停止記録・エンジン/テスト/設定は変更・削除していない。

## 証拠と実行時間

|回|元SHA256|合格SHA256|engine実行秒|実行記録commit|
|---|---|---|---|---|
|1|`8eaef99bf1828b507f1608e8b85a1c2e433f16b762625e2607ea55f6d1c6da11`|`f04313b24476ed0aa57e720641851b5b4d5e43036d2e00eb6e82b3fcda90827f`|122.828|`f3d41cb6fac13231c81bd5a3ab3b77dda9fae4fc`|
|2|`f04313b24476ed0aa57e720641851b5b4d5e43036d2e00eb6e82b3fcda90827f`|`da2abc022cc74e149dd8ac536eebb447df24b033ddfcf0799d40e0dd336e710b`|164.096|`d2a64c65cb7da5d87bc5e355e1961b3dce19c038`|
|3|`da2abc022cc74e149dd8ac536eebb447df24b033ddfcf0799d40e0dd336e710b`|`29cdd09a54a5b65bdeab6cbc5f2e4b0db5a67709931f02087bc884a8303f9ddc`|155.626|`7f27f1b56f9d75bba270c1164db62b4a1667697e`|

engine時間はAI待機・検証・ゲーム保存を含む各wrapperの記録値で、全体の準備・最終報告保存時間とは別。

[集約JSON](COMPLETED.json) / [比較HTML](COMPARISON.html) / [1回目詳細](results/01.json) / [2回目詳細](results/02.json) / [3回目詳細](results/03.json) / [追加検査スクリプト・JSON・画面](evidence/)

コアのreport.jsonは不変の公開前検査記録LOCAL_PASS_AWAITING_GITHUBであり、GitHub送信完了はPUBLISHED.jsonとrunのgithub_status=GITHUB_PUBLISHED、読み戻しで別に確認している。

## 未実施の検証・制約

学校のChromebook/Windows実機、実タッチ端末、実スクリーンリーダー、file://起動、HTTPS配信、児童試遊は未確認。読み上げ対応はDOM属性と画面更新の確認であり、実際の読み上げ品質や教育効果の検証ではない。

追加課金・APIキー登録・公開設定変更なし。既存契約の利用枠は消費し得るが残量/費用の数値は未確認。新規予約や既存予約の変更なし。今回の3回は現在のCodex実行内で完了し、停止後の自動再起動を試験したものではない。

ZIPをダウンロード・展開しgame.htmlをChromeで開く。GitHubのHTMLページ自体はゲームを実行するページではない。学校端末でのローカルHTML制限は実機で確認する。
