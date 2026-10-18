# ミニゲーム自動改善エンジン v1：実証結果

実施日：2026-10-18 UTC。GitHub mainへ保存済み。追加課金設定・APIキー登録・外部契約・定期実行登録・公開設定変更は行っていない。

## 実行結果

|作品|AIが選んだ改善|実際の評価|GitHub保存コミット|
|---|---|---|---|
|展示室の並び替えミッション|選んだ手がかりの対象作品を任意で強調。正解は表示しない|初回FAIL（確認ボタンがデスクトップ画面外）→AI修正後5検査PASS|0d507bc470a0b6f3bdff2d55789ed49f2a6ad3a9|
|架空サンプル：つりあいラボ|未配置の重りの残数・配置途中を表示し、空の天秤を完了と誤解しにくくする|初回4検査PASS|a98d11be652a05fa43b6b03523535ac8f2303d32|

### 完成品

- [展示室HTML](releases/exhibit-mission/demo-20261018/game.html) / [ZIP](releases/exhibit-mission/demo-20261018/game.zip) / [検査記録](releases/exhibit-mission/demo-20261018/report.json) / [GitHub保存証明](releases/exhibit-mission/demo-20261018/PUBLISHED.json)
- [つりあいラボHTML](releases/balance-lab/demo-20261018/game.html) / [ZIP](releases/balance-lab/demo-20261018/game.zip) / [検査記録](releases/balance-lab/demo-20261018/report.json) / [GitHub保存証明](releases/balance-lab/demo-20261018/PUBLISHED.json)

GitHubのHTML表示ページはゲーム実行画面ではない。ZIPをダウンロード・展開しgame.htmlをChromeで開く。学校管理ポリシーによるローカルHTML制限は実機確認が必要。ブラウザアクセス用の新規ホスティングは設定していない。

検証済みHTML SHA256：
- 展示室：b26475b85175dcc89c0076169f15065963912f35ea994ede1e78dee83f7298fa
- つりあいラボ：4aa1103e4f98fd0cd570071d1ece90e376e7e67597bf980625fd16742f9de8c5

## 実際に実施した検査

両作品にHTML/JavaScript基本検証とLinux Chromiumのlocalhost HTTP操作試験を実施。1366×768、768×1024、360×800、キーボード・クリック・タッチエミュレーション、横はみ出し、ブラウザエラー、外部通信を確認。最終版はいずれもPASS、外部要求・ブラウザエラーなし。

展示室は既存の成功済みday2-acceptance-logic.cjsとday2-acceptance-browser.cjsを変更せず再利用。生成問題2400件、有限手がかり組4960件、undo等の既存操作に加え、今回の強調表示を検査した。

つりあいラボは独立計算による左右合計・正解判定、全5出題の解存在、3問の操作、ヒント・パス・役割交代・再挑戦、今回の配置表示を専用テストで確認。別ゲームの固有テストへ切り替わったことを各reportのコマンドで確認できる。

エンジン7件＋保存処理4件の隔離テストもPASS。再試行上限、ゲーム別テスト切替、設定/テスト改変、検証中HTML改変、証拠なし成功、重複保存、失敗版や不一致成果物の送信拒否を検査。これはプログラムのテストであり、AIが改善を考案した実績とは区別する。

公開後にorigin/mainを再取得し、両HTMLのハッシュ・ZIP整合性・PUBLISHED.jsonを確認。開始時コミット5cef35fb0d9703871f1059987e4c8dfaf5a27f51に存在した31ファイルはすべて同じGit blobで保持。実装と2リリースの23ファイルはすべてengine-v1配下への追加のみ。初回の不合格候補HTMLは公開していない。

## AIとプログラム

実際の独立した4担当（planning、child_view、development、testing）が参加。企画担当が架空サンプルを作成、児童目線担当が改善を比較・選び候補HTMLと再修正を担当、開発担当がエンジンを実装、テスト担当が独立した検証と成果物レビューを担当した。

AIは改善の選定・コード編集・失敗原因からの修正を行った。プログラムはテスト、最大3回の修正要求、ハッシュ保護、成果物生成、合格版の追加専用GitHub保存を行った。今回はCodexの親がAI_REQUEST/応答を独立AIへ中継し、利用者による追加のコード編集・承認なしで2作品を完了した。

Python単体にAIモデルは内蔵されていない。今後もCodexライブブリッジまたは既存認証済みAIアダプタが必要。新しいAPI接続は設定していない。定期実行や環境停止後の自動再起動を構築・保証したものではない。

## 利用・追加登録

[実行手順](README.md)、[AI実行指示](RUN_PROMPT.md)、[登録テンプレート](REGISTRATION_TEMPLATE.json.example)、[展示室設定](games/exhibit-mission.json)、[サンプル設定](games/balance-lab.json)を参照。

新作品は未使用パスのHTML、目的・対象・基本ルール・変更禁止事項を用意し、新規IDの設定と固有テストを追加する。Codexにこれらの作成を依頼できる。validateは登録形式の検証であり、合格判定には実際のrunが必要。登録sourceは固定版。次の合格版を元にする際は新しい登録ID/versionで指定し、旧設定を残す。

## 未確認・制限

学校Chromebook/Windows実機、実タッチ端末、file://起動、HTTPS公開運用、児童の試遊・教育効果は未確認。自動テストで教育目的の維持を全面的に保証することはできない。新規ゲームの意味に沿う固有テストは登録時に用意する。

既存Git接続でmainへの書込みは実証済み。将来の認証・ブランチ保護・利用残量は保証しない。追加専用は保存プログラムの制約であり、アカウント権限自体の縮小ではない。追加課金やAPIキーの設定はなし。既存契約の消費量・残量・料金上限は未確認（usageCostKnown=false）。

report.jsonは公開前のLOCAL_PASS_AWAITING_GITHUB状態を保存した不変の検査記録。GitHub保存完了は別ファイルPUBLISHED.jsonと公開後readbackで確認している。
