# Bot Console

Sitesで作成したデザインを既存FastAPIへ移植した、実Bot接続用の管理画面です。サンプルデータやデモ操作は含みません。

## 起動

既存のBot用環境変数に加え、32文字以上のランダムな `DASHBOARD_TOKEN` を環境変数または `.env` に設定してください。管理画面のログインで使用するトークンです。Discordの `TOKEN` とは別にしてください。

ランダムな値を作る場合は、自分の端末で `python -c 'import secrets; print(secrets.token_urlsafe(32))'` を実行します。

```sh
pip install -r requirements.txt
sh run_all.sh
```

ブラウザで `http://localhost:8080/dashboard/` を開き、管理用トークンでログインします。トークン未設定または32文字未満の場合、管理APIは無効です。Botの起動に必要な既存の `TOKEN`、機能用の `GENAI_API_KEY`、`NOTION_TOKEN` は従来通りサーバー側に置きます。

設定できる環境変数:

| 名前 | 内容 |
| --- | --- |
| DASHBOARD_TOKEN | 32文字以上の管理用トークン。必須 |
| DASHBOARD_DB_PATH | 両プロセスが使うSQLiteファイル。既定はプロジェクト内 `runtime/dashboard.sqlite3` |
| DASHBOARD_ORIGIN | 外部公開時の正確なオリジン（例: `https://bot.example.com`）。未指定時はリクエストのオリジンと一致させる |

本番ではHTTPSで配信してください。セッションcookieはHttpOnly・SameSite=Strictで、HTTPSではSecureです。ログイン状態は8時間有効、管理トークン変更でも失効します。トークンはlocalStorageへ保存しません。

## できること

- 実Botの接続状態、プロセス起動からの稼働時間、Gateway遅延、接続サーバー数の表示。
- 実ログのレベル・機能・本文による検索、詳細表示、追従、一時停止、JSON保存。共有ログは最新300件。
- 食事解析、IIDX課題曲、DP難易度、S乱リザルト解析、技術トレンド通知、ダイスロールの有効・無効。
- オンライン・退席中・取り込み中へのプレゼンス変更。定期的なアクティビティ変更でも管理者指定のstatusを維持。
- 確認ダイアログ、1回限りの確認券、実Botが適用した結果、直近30件の操作履歴。

機能のON/OFFは新しく受け付ける処理を制御します。実行中の処理を中断しません。技術トレンドは手動取得と定期通知の両方に適用します。最初の起動では従来の機能をすべて有効にし、以後はSQLiteに設定を保存します。

Botの起動・停止・再起動は実装していません。現行 `run_all.sh` は `main.py` の終了でコンテナが終了する構成で、停止したBotをWeb画面から再起動する管理サービスがないためです。

## プロセス間の連携

`main.py` の `dashboard_sync_task` が2秒ごとに状態を共有DBへ書き、確認済みの操作を取得します。`server.py` は同じDBから読み、画面は5秒ごとに取得します。Botのheartbeatが15秒更新されなければ未接続として操作を拒否します。

操作の流れは、確認券発行 → 画面で同意 → 原子的に1回消費してキューへ格納 → Botが適用 → 適用結果をAPIで取得、です。確認券は60秒、実行待ちコマンドは6秒で失効します。BotプロセスID・操作内容・管理者セッション・操作revisionが違えば拒否します。期限切れの未開始コマンドは後から実行されません。

APIが成功を返すのはBot側の適用完了が記録されたときです。Discordへのプレゼンス送信中のタイムアウトなどで結果を確認できない場合、自動再試行せず、状態・操作履歴・ログを確認してください。起動中BotのWebSocketへ直接送信するので、Webプロセスで別のdiscord.Clientを作ることはありません。

SQLiteを同一マシン・同一共有ファイルで使う構成です。BotとAPIを別サーバーや別コンテナへ分離する際は、そのままでは連携しません。複数のBotプロセスを同じDBで動かすことも対象外です。コンテナを再作成しても設定を保持する場合、DBの保存先を永続ボリュームにしてください。

## ファイル

- `index.html`, `assets/`: ビルド不要の画面。
- `web.py`: 認証・HTML/アセット配信・確認付きAPI。
- `store.py`: 状態・設定・ログ・セッション・確認券・操作キュー・履歴。
- `runtime.py`: 実Botの状態取得、操作適用、秘密情報をマスクするログHandler。
- ルート `dashboard.py`: 旧ファイルを削除せず、互換用importとして保持。

## 検証

```sh
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
node --test dashboard/tests/*.test.mjs
```

FastAPI・独立した共有DB接続・Bot側の処理経路・確認制御・認証・ログマスク・既存機能・画面のイベント処理をテストします。Discordへの送信は代替クライアントで検証し、本番Botへ管理操作は実行しません。画面テストはDOMを模したテストで、実ブラウザのレイアウト・表示確認は含みません。
