# ミニゲーム自動改善エンジン v1

ゲーム別の目的・対象・基本ルール・変更禁止事項と専用テストを登録し、AIによる改善→プログラムによる検証→不合格時のAI修正→合格版の新規保存をつなぐ。単一HTML・インラインJavaScript・オフラインのブラウザゲーム向け。

## AIとプログラムの違い

- **AI**：実行中のCodexの独立担当がソースと設定を読み、改善案を比較・選定し、候補HTMLだけを編集する。テスト失敗時はログから修正する。今回は実際の独立サブエージェントを使用した。
- **プログラム**：設定読込み、元版のコピー、ハッシュ保護、テスト切替、再試行上限、時間制限、HTML/ZIP/記録の作成、追加専用GitHub保存を行う。Python自身が改善点を思い付くことはない。
- **接続**：engine.pyがJSONのAI_REQUESTを出力し、AIが編集後にJSONを返す。現在のCodexでは親がツールで独立AIを呼び、このJSONを中継する。利用者が候補のコード修正やJSON応答を毎回手作業する実証ではない。
- ローカル単独コマンドにAIモデルを内蔵してはいない。任意の既存AIアダプタを `--ai-command '["実行ファイル", "引数"]'` で接続することもできるが、別サービスを勝手に契約・認証しない。未設定ならCodexのライブブリッジが必要。

## 登録済み

- `games/exhibit-mission.json`：展示室。元の推理・undoを含む成功済みテストを変更せず再利用し、今回の強調表示検査を追加。
- `games/balance-lab.json`：架空の実証用「つりあいラボ」。合計と釣り合いの独立判定、全出題の解存在、3問操作を専用テストで確認。今回の未配置表示検査も追加。

## 使い方

Node、Python 3、Chromium、Playwrightを利用する。今回の環境では既存のものを使用し、追加インストール・APIキー登録はしていない。別環境での導入にはその環境の管理条件を確認する。

```sh
python engine-v1/engine.py list
python engine-v1/engine.py validate --game exhibit-mission
# 既存Playwrightの所在を環境に合わせる。固定パスは他の環境では保証しない。
export PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core
export CHROMIUM_PATH=/usr/bin/chromium
python engine-v1/engine.py run --game exhibit-mission --run-id trial-001 --work-root /tmp/mini-game-runs --publish
```

run-idには未使用の英数字・ハイフン・アンダースコアを使う。work-rootはリポジトリ外にする。CodexにRUN_PROMPT.mdを使わせると、AI_REQUESTの候補編集と応答を担当させられる。AIアダプタがないまま通常の端末だけで起動するとAI応答待ちになる。

初回候補＋不合格後の最大3回修正＝最大4回評価。AI待機・検証・保存を含め上限60分（変更可、3600秒超不可）。テストは、共通HTML/JS検証→共通ブラウザ→登録したゲーム固有テストの順。exit 0だけでは合格にせず、JSONのpass:trueと検証対象ハッシュも確認する。

合格前の候補・失敗ログはwork-rootだけに保存する。合格時だけ `releases/<game-id>/<run-id>/game.html`, `game.zip`, `report.json` が作成される。過去の同名run-idは拒否する。

## GitHub保存

`--publish` は既存Git接続を利用する別プログラムpublish.pyを呼ぶ。合格ゲーム・ZIP・reportとPUBLISHED.jsonの4ファイルを、一時Git indexから1つのコミットでorigin/mainへ追加する。既存パスが1つでもあれば拒否。差分が全てAであることを確認し、forceなしpush、fetch後のblob一致を検証する。公開設定を変更しない。

ローカル合格とGitHub保存は別状態。report.jsonの `LOCAL_PASS_AWAITING_GITHUB` は試験結果でありGitHub送信の証明ではない。公開先の `PUBLISHED.json` とエンジンのPUBLISH_RESULTにより確認する。送信失敗でも合格ファイルは保持し、未送信と報告する。

権限はリポジトリのread/writeが必要。アカウント権限自体を新規追加専用へ縮小しているわけではなく、プログラムが追加専用のGit treeを制約する。ブランチ保護が拒否したら設定回避せず停止する。

## 新しい作品を1つ登録するには

1. 元の単一HTMLを新しい未使用パスへ置く（既存ゲームを上書きしない）。
2. 作品名・目的・対象年齢・基本ルール・変更禁止事項を用意する。
3. `games/` に未使用IDのJSONを追加し、source、上記情報、開始ボタンと基本操作ボタンのCSSセレクタ、ゲーム固有テストのコマンドを設定する。REGISTRATION_TEMPLATE.json.exampleを参照。
4. 固有テストを新規追加する。意味のある正解や勝利条件は作品ごとに違うため、共通テストだけで登録完了とはしない。CodexへHTMLと目的・禁止事項を渡し、設定と固有テストの作成も依頼できる。
5. `validate --game ID` で登録形式を検査し、AIブリッジ付きrunで実証する。

ファイルを置くだけで未知のゲームの教育目的や正解を自動保証する仕組みではない。validateは形式確認であり、ゲーム動作のテスト合格とは別。元sourceは設定に明記した固定版で、次回の元を変更する場合は新しい登録ID/versionに合格版sourceを指定する（既存設定を上書きしない）。

## 再現可能な検査

```sh
python engine-v1/tests/test-engine.py
python engine-v1/tests/test-publisher.py
```

これらの隔離fixtureはプログラムの検査用であり、AI改善の実績ではない。実際のAI改善は2作品のrelease/report.jsonのai_acknowledgementと各テスト結果を参照する。ブラウザ検証はLinux ChromiumのHTTP上で実施。学校Chromebook・Windows実機・実タッチ端末・file://・実児童試遊や改善効果は未確認。特にfile://は以前の管理ポリシーで遮断されており、回避していない。

APIキー・追加課金・外部サービス契約・定期実行の登録は行わない。既存契約の利用枠を消費し得るが、残量や料金上限の数値はこの接続から確認できていない。
