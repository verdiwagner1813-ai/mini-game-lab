# 実登録方式の変更（この文書とREGISTRATION.jsonが予約方式の正本）

3単発タスクのうち1/2を作成した後、3件目は予約サービスが too_many_active_automations / 現行プランは有効5タスクまで、と返して拒否した。AI利用残量超過を確認したものではない。追加課金や他のユーザー予約の変更は行わない。

今回作成した第2回用タスクを休止し、第1回用タスクを、16:30開始・RRULE:FREQ=HOURLY;INTERVAL=2;COUNT=3の1つのCodexクラウド予約へ更新する。16:30/18:30/20:30の3呼出しを1つのタスクにまとめ、4回目はない。登録結果はREGISTRATION.jsonだけを証拠とする。準備段階PLAN等に残る「3単発」は履歴として保持し、この方式へ置き換える。

choose_slot.pyで実際の呼出し時刻からslot=1/2/3を選ぶ。対応する既存PROMPT-NNと午後gateを再利用し、前回完了/保存証跡と固定claimを確認する。遅延・前後逆転時は追い付き実行をせず停止。STOPPED/COMPLETEDは全呼出しで確認し、障害や第3回終了時はcontroller_task_idをpauseする。REGISTRATIONのtasks配列には有効controllerだけを置き、休止した準備用taskはretired_setup_tasksへ記録する。

停止・完了後の比較も既存の規約通り新規COMPARISON.mdへ保存する。課金/キー/公開設定変更なし、他の既存予約は維持。時刻・実行対象・最大3回の改善という承認範囲は変更しない。
