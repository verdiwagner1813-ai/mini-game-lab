# DAY2 独立検証（2026-10-18）

④が独立テストを作成。Nodeロジック検証は④、権限を伴うLinux Chromium検証は親がスクリプトを実行し、④が結果を評価した。

- 正式元: `games/exhibit-mission/index.html`、SHA-256 `06cbe2e3a11325a54e17535460e0eaa5dc7e91533a258f7048954739b7094062`。
- 保全preview: `experiments/exhibit-seven-days/day02-undo-preview.html`、SHA-256 `58a5712d85ea74e16d5ef045b31d6710248a4a47af6725150e2c3451d8cbd28f`。
- 修正版: `experiments/exhibit-seven-days/day-02-final/game.html`、SHA-256 `e1f0bee3775577894eac5d2591d7d0b89d01cb5df94676f7e95d4de8dafdbc8c`。

## 結果

3ファイルとも独立述語による2,400生成問題×24配置と有限4,960条件組の検証に合格。条件3枚すべてが不可欠な一意解組は168組、正答24配置を網羅。

previewのブラウザ試験でundo後のフォーカス復帰不在を実測。開発担当は元を変更せず新規修正版へ、undo後の確認ボタンへのフォーカス復帰、完成・見本・リセット時の履歴消去を反映した。

正式元と修正版は最終Linux Chromium/127.0.0.1 HTTP試験に合格。開始・キー操作・作品交換・誤答・3段階ヒント・担当循環・休憩・リセット・再挑戦と配置変化を確認。修正版では1回undo、再無効化、履歴消去、フォーカス復帰も確認。768×1024および360×800のタッチ操作と横はみ出しなし、実行エラー0件、外部要求0件。デスクトップ1366×768の主要表示も検査。

## 保存処理の読み取りレビュー

`automation/add-only/publisher.cjs` は固定prefix、新規作成のみ、同一既存の再利用と相違拒否、HTMLハッシュとテスト証跡の対応、書込み後読戻し、最後のCOMPLETED記録によって部分保存と完了を区別する。親作成の8試験は重複・相違・証跡不合格・部分保存・作成成功後タイムアウト・パス逸脱・ハッシュ不一致を確認している。

実transport.createは既存ファイルを更新しない契約を守る必要がある。publisherは依存注入されたtransport内部の動作までは強制できない。実アダプタでGitHubのshaなし新規作成と既存時の拒否を維持する。

## 未確認

学校Chromebook、Windows実機、学校HTTPS、実児童試遊・実所要時間は未確認。file://は以前同環境で管理遮断され、今回は再検証せず回避もしていない。Linux Chromiumの検証を学校実機の確認とは扱わない。

検証コードは新規 `tests/day2-acceptance-logic.cjs` と `tests/day2-acceptance-browser.cjs`。既存リモートファイルの上書き・削除は行っていない。
