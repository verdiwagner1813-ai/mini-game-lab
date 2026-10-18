# GitHubへの追加専用保存プロトコル

対象：verdiwagner1813-ai/mini-game-lab のmain。既存ファイルの更新・削除、公開設定変更、認証情報追加、課金設定は禁止。

## 保存するもの
- 合格版：experiments/exhibit-seven-days/day-02-final/game.html
- 独立したテスト証跡：同フォルダのACCEPTED.json
- 予約検証：experiments/exhibit-seven-days/add-only-runs/<一意runId>/game.html と COMPLETED.json

## 1回の無人処理
1. ローカルの前回状態を仮定せず、GitHubから固定された合格版コミット、HTML、テストを取得する。プロンプトに固定した期待SHA-256と一致させる。
2. Nodeの独立ロジック検証とHTTP上Chromium操作テストを実行し、両方PASSと検証対象HTMLのハッシュを保存する。環境/権限不足・承認待ちならBLOCKED。テスト未実施を合格にしない。
3. 検証後にHTMLを変更しない。repositoryとmainと保存先prefixを固定する。`publisher.cjs`の契約に従い、更新用blob shaを渡さないGitHub create_fileのみを使う。update_file/delete_file/git push/force/設定変更は使用しない。
4. HTMLを新規追加して再取得照合し、その後COMPLETED.jsonを新規追加して再取得照合する。HTMLだけの部分保存は完了・新合格版と扱わない。
5. 同名があれば読み取り、内容一致なら再利用、不一致なら衝突として停止する。存在確認後の競合や通信timeoutも、再取得して保存済みか判別する。既存への上書きで修復しない。
6. 最後にHTMLと成功記録を再読込みして一致を確認する。失敗した場合は新規FAILURE記録を許可するが、過去の成功記録は変更しない。

## 権限の境界
GitHub接続にはcontentsの書込権限が必要。現在のアカウントはそれより広い権限も持つ。追加専用は本プロトコルとcreate_file呼出しの制限であり、資格情報自体を「新規追加しかできない権限」に変更したわけではない。GitHubの既存ファイル更新には現在blobのshaが必要で、create_file呼出しには渡さない。プロトコルを外れた別ツール呼出しまでアカウント権限で禁止できることは未検証。ブランチ保護によりmain直接追加が拒否された場合、保護を変更せず原因を報告する。

## テスト
`node tests/add-only-publisher.cjs` は8ケースを隔離メモリ上で検査する。新規追加成功、同一リトライ、異内容衝突、ブラウザ不合格時の書込禁止、HTMLだけの部分保存と回復、成功直後timeoutの再照合、不正パス拒否、HTMLハッシュ不一致拒否。
実際のGitHub無人書込は一回限りの予約タスクで別途検証する。定期実行は今回登録しない。

## 費用・限界
新規APIキー、有料API、外部の契約・課金設定は使用しない。既存ChatGPT/Code実行・GitHub接続の利用枠は消費し得る。利用者の契約プラン、残量、従量課金設定や月額上限の数値をこの接続から取得できていないため「費用ゼロ」「無制限」とは保証しない。
一回限りの試験合格は、その時点の環境・権限・接続での成功であり、環境停止後の再起動や将来の認証継続、毎日の機能改善の成功を保証しない。学校Chromebook/Windows実機・実児童試遊も未確認。
