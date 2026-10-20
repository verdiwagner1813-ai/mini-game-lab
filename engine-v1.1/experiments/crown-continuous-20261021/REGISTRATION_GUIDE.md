# 単一HTMLゲームを追加して継続改善する手順

既存の engine-v1 と engine-v1.1 をそのまま使う。ゲームIDごとのJSON・原本・固有テストを新規追加し、過去のファイルを変更しない。今回は `crown-star-catch` を例にする。

## 利用者が用意するもの

1. 遊べる単一HTML（ZIPなら中身のタイトルも確認）。
2. 作品名、対象年齢と人数、目的、必ず維持するルール・禁止する変更。
3. 画像・音声の公開許可。児童の似顔絵など許可未確認の素材は、公開版では代替物にする。
4. 改善回数。通常対話の連続実行と予約実行は別に指定する。

Codexへの依頼例：

> 添付HTMLを未使用ID「new-game」に登録してください。基本ルールは［記入］、変更禁止は［記入］です。未許可の素材は代替してください。元版の実ブラウザ検証と固有テストを作り、v1.1で最新合格版から3回連続改善してください。元版や過去版は保持し、合格版だけmainへ新規保存してください。追加課金やキー登録はしないでください。

## 登録担当の作業

- AGENTS.md / PROJECT_RULES.md と現行ユーザー条件を読む。人数等の個別条件が共通既定と異なる場合は、個別条件を優先した理由を新しい登録記録に残す。
- 添付をリポジトリ外で確認し、元HTMLを編集せずChromiumで操作する。埋込画像の許可確認前に原本やスクリーンショットをGitへ入れない。
- 公開用原本を `games/<ID>/original-public.html` の未使用パスへ用意する。公開適合の変更と、後続の改善サイクルを分けて記録する。
- 既存 `engine-v1/REGISTRATION_TEMPLATE.json.example` を参照し `engine-v1/games/<ID>.json` を新規作成する。purpose / target_age / basic_rules / forbidden_changes / browser_contract / specific_tests を埋める。
- 現在の共通静的検査は画像のsrc属性（data URLを含む）も禁止する。公開イラストはインラインSVG等にし、共通検査を弱めない。音がWeb Audio APIによる合成なら外部依存なしで保持できる。
- 共通操作検査はstart_selectorを押すとその要素が非表示になり、action_selectorが表示される構成を要求する。即開始型には小さな開始画面を公開コピーへ追加し、その適合変更を記録する。
- `engine-v1/tests/<ID>/` 等の新規パスへ固有検査を作る。候補HTMLのパスを引数で受け、実際の検査成功時だけexit 0・JSON `pass:true`・`sourceSha256`を返す。失敗は非0終了。
- 勝利・敗北・合法手・禁止手・初期化・戻す操作等を作品固有に確認する。できれば実装と別の判定モデルで多数の状態を照合する。実HTMLのChromium操作と、テスト時だけ内部関数を呼ぶ検査は区別する。
- 元版と公開登録版の検査結果・素材差替え・未確認点を保存し、共通検査と固有検査が合格してから追加のみのコミットでmainへ保存する。

## 実行コマンド（実在する環境パスを指定）

```sh
python engine-v1/engine.py validate --game crown-star-catch
export PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core
export CHROMIUM_PATH=/usr/bin/chromium
python engine-v1.1/continuity.py latest --game crown-star-catch
python engine-v1.1/continuity.py run --game crown-star-catch --run-id UNIQUE_ID --work-root /tmp/new-game-runs --publish --invocation interactive --timeout-seconds 1200
```

既存モジュールの存在と権限を先に確認する。通常の認証・プロキシ・CAを維持し、不足時に新契約やキーを勝手に追加しない。

AI_REQUESTには本当の独立AIを接続する。AIは少なくとも3案を比較し、候補HTMLのみ編集して `ready/summary/ai_agent` を返す。親Codexは追加操作検査を確認して応答を中継する。Python自体は企画もコード編集もしない。共通・固有テスト、最大3回の修正、期限、ハッシュ保全、新規保存は既存プログラムが担当する。

3回連続実行する場合は、毎回未使用run-idで1回ずつ終了を待つ。保存とreadbackが成功したら次へ進み、continuity.pyが直前の合格版を引き継いだSHAを確認する。不合格が修正上限に達した、環境や権限が不足した、利用上限に達した場合は停止する。

## 保存先と最終確認

- 完成版：`engine-v1/releases/<ID>/<RUN>/game.html`、`game.zip`、`report.json`、`PUBLISHED.json`
- 実行記録：`engine-v1.1/runs/<ID>/<RUN>/record.json`、`RECORDED.json`
- 比較記録：未使用の実験ディレクトリへ追加。`report.py`の既存レンダラーを再利用可能。
- 別のcloneでHTML/ZIP/合格記録/保存証跡/継承SHAを読み戻し、開始時の既存Git blobがすべて同一で差分がAのみと確認する。
- 学校実機・実タッチ・聴感・児童試遊・file://等、実施していない確認は未確認と書く。

登録後はsourceや既存設定を書き換えず、同じIDで最新合格releaseを自動継承する。ルール・固有テスト契約を改める場合は、既存v1.1の整合検査に従い、新しいID/versionの登録として扱う。追加専用制約はプログラム上の検査であり、GitHubアカウント権限自体を追加専用へ変更するものではない。
