"""SQLite bridge shared by server.py and the running main.py process."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

FEATURES = [
    {"id":"meal_analyze","name":"食事画像のAI解析","description":"Gemini · 画像から栄養を推定","icon":"spark"},
    {"id":"iidx","name":"IIDX課題曲生成","description":"レベル11・12の課題曲を生成","icon":"music"},
    {"id":"dp_level","name":"DP難易度検索","description":"曲名から非公式難易度を検索","icon":"search"},
    {"id":"result_analyze","name":"S乱リザルト解析","description":"画像の解析・Notionへの記録","icon":"chart"},
    {"id":"tech_trend","name":"技術トレンド通知","description":"Qiita · 手動取得と定期通知","icon":"globe"},
    {"id":"dice","name":"ダイスロール","description":"/dice · 指定したダイスを振る","icon":"grid"},
]
FEATURE_IDS = {f["id"] for f in FEATURES}

# UNIX秒をタイムゾーン付きISO形式へ変換する。
def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

# 許可操作を検証し、余分な項目・プロセス制御はValueErrorで拒否する。
def validate_action(action):
    if not isinstance(action, dict):
        raise ValueError("操作の形式が不正です")
    if action.get("kind") == "presence" and set(action) == {"kind", "value"}:
        if isinstance(action["value"], str) and action["value"] in {"online", "idle", "dnd"}:
            return action.copy()
    if action.get("kind") == "feature" and set(action) == {"kind", "featureId", "enabled"}:
        if isinstance(action["featureId"], str) and action["featureId"] in FEATURE_IDS and type(action["enabled"]) is bool:
            return action.copy()
    raise ValueError("この操作には対応していません")

class Store:
    # DBとスキーマを作成する。BotとAPIは同じpathを使用すること。
    def __init__(self, path=None, clock=time.time):
        self.path = Path(path or os.getenv("DASHBOARD_DB_PATH") or Path(__file__).resolve().parent.parent / "runtime" / "dashboard.sqlite3")
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runtime (id INTEGER PRIMARY KEY CHECK(id=1), boot TEXT NOT NULL, seen REAL NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, level TEXT NOT NULL, module TEXT NOT NULL, message TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, expires REAL NOT NULL, token_tag TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS confirmations (id TEXT PRIMARY KEY, actor TEXT NOT NULL, expires REAL NOT NULL, action TEXT NOT NULL, boot TEXT NOT NULL, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, action TEXT NOT NULL, boot TEXT NOT NULL, expires REAL NOT NULL, state TEXT NOT NULL, error TEXT, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, action TEXT NOT NULL, result TEXT NOT NULL);
            """)
            db.execute("INSERT OR IGNORE INTO settings VALUES ('revision','0')")
            db.execute("INSERT OR IGNORE INTO settings VALUES ('presence','\"online\"')")
            for key in FEATURE_IDS:
                db.execute("INSERT OR IGNORE INTO settings VALUES (?, 'true')", ("feature:"+key,))

    # 正常終了でcommit、例外でrollbackし、必ず接続を閉じる。
    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    # 設定の現在値を読み取る。未知のキーにはdefaultを返す。
    def setting(self, key, default=None):
        with self.connection() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return json.loads(row["value"]) if row else default

    # Botが確認済み操作を適用した後の共有設定を書き込む。
    def set_setting(self, key, value):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    # Botプロセス識別子と実際の状態をheartbeatとして保存する。
    def heartbeat(self, boot, data):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO runtime VALUES (1,?,?,?)", (boot, self.clock(), json.dumps(data)))

    # マスク済みの実ログを保存し、最新300件に制限する。
    def add_log(self, level, module, message):
        with self.connection() as db:
            db.execute("INSERT INTO logs(timestamp,level,module,message) VALUES (?,?,?,?)", (iso(self.clock()), level, module, message[:4000]))
            db.execute("DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 300)")

    # 状態・設定・ログを一貫した読み取りで返す。15秒heartbeatがなければ操作を無効にする。
    def snapshot(self):
        with self.connection() as db:
            db.execute("BEGIN")
            runtime = db.execute("SELECT * FROM runtime WHERE id=1").fetchone()
            settings = {r["key"]:json.loads(r["value"]) for r in db.execute("SELECT * FROM settings")}
            bot = json.loads(runtime["data"]) if runtime else {"name":"discord_bot","status":"offline","presence":settings["presence"],"startedAt":None,"latencyMs":None,"guilds":0}
            fresh = bool(runtime and self.clock()-runtime["seen"] <= 15)
            online = fresh and bot["status"] == "online"
            if not online:
                bot.update(status="offline", latencyMs=None)
            audit = []
            for a in db.execute("SELECT * FROM audit ORDER BY timestamp DESC LIMIT 30"):
                action = json.loads(a["action"])
                name = next((f["name"] for f in FEATURES if f["id"] == action.get("featureId")), "")
                label = f"{name}を{'有効' if action.get('enabled') else '無効'}に変更" if action["kind"]=="feature" else "プレゼンスを変更"
                audit.append({"id":a["id"],"timestamp":a["timestamp"],"label":label,"actor":"管理者","result":a["result"]})
            logs = [{"id":str(r["id"]),"timestamp":r["timestamp"],"level":r["level"],"module":r["module"],"message":r["message"],"context":{}} for r in db.execute("SELECT * FROM logs ORDER BY id")]
            return {"mode":"http","controlsEnabled":online,"bot":bot,"features":[dict(f,enabled=settings["feature:"+f["id"]]) for f in FEATURES],"logs":logs,"audit":audit,"revision":settings["revision"],"runtimeFresh":fresh}

    # ランダムなセッションcookieを発行し、DBにはハッシュのみ保存する。
    def new_session(self, token):
        value = secrets.token_urlsafe(32)
        digest = hashlib.sha256(value.encode()).hexdigest()
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE expires<=?", (self.clock(),))
            db.execute("INSERT INTO sessions VALUES (?,?,?)", (digest,self.clock()+28800,hashlib.sha256(token.encode()).hexdigest()))
        return value

    # cookieの期限と管理トークンを検証する。未認証時はNoneを返す。
    def session_actor(self, cookie, token):
        if not cookie or not token:
            return None
        digest = hashlib.sha256(cookie.encode()).hexdigest()
        with self.connection() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=? AND expires>?", (digest,self.clock())).fetchone()
            return digest if row and secrets.compare_digest(row["token_tag"],hashlib.sha256(token.encode()).hexdigest()) else None

    # セッションと、その管理者の未実行の確認券を失効させる。
    def logout(self, actor):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE id=?", (actor,))
            db.execute("DELETE FROM confirmations WHERE actor=?", (actor,))

    # 現Botとrevisionに紐づく60秒・1回限りの確認券を発行する。Bot操作はしない。
    def prepare(self, actor, action):
        safe = validate_action(action)
        now = self.clock()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            runtime = db.execute("SELECT * FROM runtime WHERE id=1").fetchone()
            if not runtime or now-runtime["seen"]>15 or json.loads(runtime["data"])["status"]!="online":
                raise ValueError("Botが未接続のため操作できません")
            db.execute("DELETE FROM confirmations WHERE expires<=?", (now,))
            if db.execute("SELECT COUNT(*) FROM confirmations").fetchone()[0]>=100:
                raise ValueError("確認中の操作が多すぎます")
            revision = int(db.execute("SELECT value FROM settings WHERE key='revision'").fetchone()[0])
            ticket = secrets.token_urlsafe(32)
            db.execute("INSERT INTO confirmations VALUES (?,?,?,?,?,?)", (ticket,actor,now+60,json.dumps(safe,sort_keys=True),runtime["boot"],revision))
            return {"id":ticket,"expiresAt":iso(now+60),"target":"discord_bot / 実Bot","action":safe}

    # 確認・ユーザー・操作・期限・Bot・revisionを原子的に検証し、1回だけ操作をキューへ入れる。
    def enqueue(self, actor, ticket, action, confirmed):
        if confirmed is not True:
            raise ValueError("明示的な確認が必要です")
        encoded = json.dumps(validate_action(action),sort_keys=True)
        now = self.clock()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM confirmations WHERE id=? AND actor=?", (ticket,actor)).fetchone()
            runtime = db.execute("SELECT * FROM runtime WHERE id=1").fetchone()
            revision = int(db.execute("SELECT value FROM settings WHERE key='revision'").fetchone()[0])
            if not row or row["expires"]<=now or row["action"]!=encoded or row["revision"]!=revision or not runtime or row["boot"]!=runtime["boot"] or now-runtime["seen"]>15 or json.loads(runtime["data"])["status"]!="online":
                raise ValueError("確認が期限切れ、またはBotの状態が変更されました。再確認してください")
            db.execute("DELETE FROM confirmations WHERE id=?", (ticket,))
            db.execute("UPDATE settings SET value=? WHERE key='revision'", (str(revision+1),))
            command = secrets.token_hex(16)
            db.execute("INSERT INTO commands VALUES (?,?,?,?,?,?,?)", (command,encoded,runtime["boot"],now+6,"pending",None,now))
            db.execute("INSERT INTO audit VALUES (?,?,?,?)", (command,iso(now),encoded,"実行待ち"))
            db.execute("DELETE FROM commands WHERE created<? AND state NOT IN ('pending','running')", (now-86400,))
            db.execute("DELETE FROM audit WHERE id NOT IN (SELECT id FROM audit ORDER BY timestamp DESC LIMIT 30)")
            return command

    # 同一Bot向けの未期限切れコマンドを1件claimする。古いプロセス宛ての操作は破棄する。
    def claim(self, boot):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            invalid = db.execute("SELECT id FROM commands WHERE state='pending' AND (expires<=? OR boot!=?)", (self.clock(),boot)).fetchall()
            for row in invalid:
                db.execute("UPDATE commands SET state='cancelled',error='Bot changed or command expired' WHERE id=?", (row["id"],))
                db.execute("UPDATE audit SET result='期限切れ' WHERE id=?", (row["id"],))
            unknown = db.execute("SELECT id FROM commands WHERE state='running' AND boot!=?", (boot,)).fetchall()
            for previous in unknown:
                db.execute("UPDATE commands SET state='unknown',error='Bot restarted before acknowledging the result' WHERE id=?", (previous["id"],))
                db.execute("UPDATE audit SET result='結果未確認' WHERE id=?", (previous["id"],))
            row = db.execute("SELECT * FROM commands WHERE state='pending' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE commands SET state='running' WHERE id=?", (row["id"],))
                return dict(row,action=json.loads(row["action"]))
            return None

    # Botが操作の完了結果を記録する。errorには秘密を含まない一般化した文を渡す。
    def finish(self, command, error=None):
        with self.connection() as db:
            db.execute("UPDATE commands SET state=?,error=? WHERE id=?", ("failed" if error else "done",error,command))
            db.execute("UPDATE audit SET result=? WHERE id=?", ("失敗" if error else "成功",command))

    # 適用結果を読み取る。未開始の期限切れをcancelし、後からの実行を防ぐ。
    def command(self, command):
        with self.connection() as db:
            db.execute("UPDATE commands SET state='cancelled',error='Bot did not acknowledge in time' WHERE id=? AND state='pending' AND expires<=?", (command,self.clock()))
            row = db.execute("SELECT * FROM commands WHERE id=?", (command,)).fetchone()
            if row and row["state"]=="cancelled":
                db.execute("UPDATE audit SET result='期限切れ' WHERE id=?", (command,))
            elif row and row["state"]=="running" and row["expires"]<=self.clock():
                db.execute("UPDATE audit SET result='結果未確認' WHERE id=?", (command,))
            return dict(row) if row else None
