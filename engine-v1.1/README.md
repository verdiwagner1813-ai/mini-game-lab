# ミニゲーム自動改善エンジン v1.1

既存engine-v1を再利用し、前回の最新合格版を次のAI改善へ渡す。AIの企画・編集・再検討と、プログラムによる検証・保存をつなぐ。予約起動は既存Codexのタスク機能を利用する方式を第一候補とする。追加APIキーや有料契約は設定しない。

## 再利用するものと追加するもの

- engine-v1/engine.py：元の共通検証・ゲーム固有テスト・最大3回修正・合格版生成をそのまま使用。
- engine-v1/publish.py：元の追加専用GitHub保存とreadbackをそのまま使用。
- continuity.py：最新合格版の検証、隔離実行環境への引継ぎ、AI橋の中継、改善不要の見送り、独立run記録を追加。
- report.py：保存済み版と見送り記録の比較レポートを、未使用名で生成。

元のengine-v1、原本、過去の完成版と記録は変更・削除しない。最新のHTMLは一時cloneの実行用sourceへだけコピーする。この一時コピーは実行前の準備であり、GitHubのsourceは上書きしない。v1の検証が始まってからは一時コピーも保護対象とする。

## 最新版を決める基準

HTML・report・PUBLISHED.json・ZIPとゲーム別検査を照合した合格版だけが候補。保存日時だけを比較せず、その版が導入されたGitコミットの祖先関係で選ぶ。不整合や分岐を安全に解決できない場合は停止する。receiptのない途中保存版は最新合格版にしない。対象がなければ登録sourceを起点とする。

各合格reportに引継ぎ元のパス・SHA・導入コミットを残し、次の実行で照合できるようにする。公開直前にも最新合格版が変わっていないか確認する。同じゲームの同時改善は禁止し、予約の重なりや別の人の改善中には実行しない。

## AIによる処理

予約で起動したCodexがAI_REQUESTを独立AIへ渡す。独立AIは元版と履歴、目的・基本ルール・禁止事項を読み、複数の改善案を比較し1つを選んで候補HTMLだけを編集する。失敗時はテストログから再検討する。

プログラムは改善案を考案しない。AIを内蔵していないので、通常のPythonコマンドだけではAI応答待ちになる。Codexライブブリッジまたは既存のAIアダプタが必要。外部モデルAPIの追加設定はしない。

改善する価値のある案がなければskip応答で理由を記録し、ゲーム版を増やさない。全修正で不合格・実行環境不足の場合も正常な旧版を維持する。

## 予約実験

[SCHEDULED_PROMPT.md](SCHEDULED_PROMPT.md)を予約タスクの一回分の指示として使う。[experiment-plan.json](experiment-plan.json)に方針を保存。

ユーザーは追加確認への返答「３回試験して」で、既存契約の枠内で合計3回の予約試験を承認した。最初の実行が実際のAI改善・ブラウザ検査・GitHub保存まで成功した場合に限り、残り2回を2時間間隔で設定する。失敗・BLOCKED・改善不要は成功と扱わず、残りを自動有効化しない。登録したことと実行成功は別に報告する。

予約promptは以前の/workspaceが存在すると仮定せず、毎回mainから新しい領域へ取得して開始する。GitHubの接続やshellがないならBLOCKEDを記録。予約タスクを作成できること自体は、停止後のクラウド再起動を保証しない。環境を意図的に停止する破壊的実験は行わない。

## 実行時間・費用・権限

AI応答待ち・検証・保存を含め3600秒以内を目標とし、ラッパーにdeadlineを設ける。クラウドの予約ランナー自体を60分で強制終了する機能・費用上限は確認できないため、全体のhard capは保証しない。

現在のGit認証とmainへの書込み権限を利用する。期限切れ・ブランチ保護・ツール審査で拒否されたら停止し、設定を回避しない。GitHubの既存ファイルは上書きしない。追加専用はアカウント権限の縮小ではなく保存処理の制約。

既存契約の利用枠を消費し得る。料金・残量・上限の数値は接続から確認できずusageCostKnown=false。ユーザーはこの不明点を示したうえで3回試験を承認した。追加課金・キー登録・契約が必要なら停止して確認する。

## 他方式との比較

|方式|利点|必要設定・費用の扱い|今回|
|---|---|---|---|
|既存Codex予約|現在のAI連携・GitHub接続を再利用|予約時のshell/ブラウザ/認証は実証が必要。契約枠は未確認|一回試験を優先|
|GitHub Actions|毎回新しいrunner、timeout-minutesや実行履歴、Chromiumテストを設定可能|GitHub枠/公開範囲/組織設定を確認。AI改善には別途認証済みAI接続が必要で、ActionsだけではAIにならない|作成・有効化しない|
|常時稼働PC/サーバー|既存AI CLIが認証済みならcron等と連携可能|電源維持・運用・認証更新、機器/契約費用の確認が必要|構築しない|

Codex予約で失敗しても、未承認のAPIやActions課金へ自動移行しない。

## 比較・新作品

report.pyは新しいHTMLレポートを生成する。古いレポートは更新せず残す。GitHubのHTMLページはソース表示なので、レポートやゲームの実行にはダウンロードが必要。既存の公開設定やホスティングは変更しない。

新規作品はengine-v1の登録テンプレートを使い、未使用IDの設定と作品固有テストを追加する。その後は同じgame_idについて、合格releaseの連鎖をcontinuity.pyで継続する。元の登録sourceを毎回手で更新する必要はない。

## 未確認事項

学校Chromebook/Windows実機・実タッチ端末・file://起動・HTTPS公開運用・児童試遊と教育効果は未確認。自動テストは意味や教育目的を全面的に保証しない。将来の認証・利用枠・予約配信の遅延・環境停止後の復帰は保証しない。

## コマンド

```sh
python engine-v1.1/continuity.py latest --game exhibit-mission
# 存在を確認した既存ランタイムのみ指定する
export PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core
export CHROMIUM_PATH=/usr/bin/chromium
python engine-v1.1/continuity.py run --game exhibit-mission --run-id UNIQUE_ID --work-root /tmp/mini-game-continuity --publish --timeout-seconds 3600
# AI_REQUESTをCodexの独立AIへ渡し、ready応答を返す。
# 改善不要なら初回に限り {"skip":true,"reason":"具体的理由","ai_agent":"担当identity"}。
python engine-v1.1/report.py --output engine-v1.1/reports/UNUSED_NAME.html
```

CodexへSCHEDULED_PROMPT.mdの実行を依頼すれば、AIの呼出しと応答中継を担当させられる。利用者がJSONを毎回入力する前提ではない。外部アダプタの場合は既存v1と同じJSON argv形式の--ai-commandを使う。

--publishはゲーム合格版と別にengine-v1.1/runs/<game>/<run>/record.jsonとRECORDED.jsonを追加保存する。合格ゲームは既存のengine-v1/releases/<game>/<run>/へ追加される。PASSはローカル検査の結果、github_status=GITHUB_PUBLISHEDとreadbackがGitHub保存の証拠。記録だけ送れた場合をゲーム保存成功と混同しない。
