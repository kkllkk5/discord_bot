"""Bot-side heartbeat, confirmed command consumer and redacted log capture."""
import asyncio
import logging
import math
import os
import re
import sqlite3
import uuid
import discord
from .store import Store, iso, validate_action

class DatabaseLogHandler(logging.Handler):
    # 共有DBへログを出すHandlerを作る。Bot操作や外部送信は行わない。
    def __init__(self, store):
        super().__init__(logging.INFO)
        self.store = store

    # 環境変数の秘密とBearer文字列をマスクして保存する。DBエラーはBotの通常処理へ伝播させない。
    def emit(self, record):
        try:
            message = self.format(record)
            for key, value in os.environ.items():
                if value and len(value) >= 8 and any(word in key.upper() for word in ("TOKEN", "KEY", "SECRET", "PASSWORD")):
                    message = message.replace(value, "[REDACTED]")
            message = re.sub(r"(?i)Bearer\s+[^\s,;]+", "Bearer [REDACTED]", message)
            module = getattr(record, "dashboard_module", "gateway" if record.name.startswith("discord") else "system")
            level = "ERROR" if record.levelno >= logging.ERROR else "WARN" if record.levelno >= logging.WARNING else "INFO"
            self.store.add_log(level, module, message)
        except (sqlite3.Error, OSError):
            pass

# root loggerに共有DB用Handlerを1つ取り付ける。標準のストリームログは維持する。
def install_log_handler(store=None):
    root = logging.getLogger()
    if not any(isinstance(h, DatabaseLogHandler) for h in root.handlers):
        root.addHandler(DatabaseLogHandler(store or Store()))

class RuntimeBridge:
    # 実discord.Clientと共有DBに接続する。bootはこのBotプロセスに固有のID。
    def __init__(self, client, store=None):
        self.client = client
        self.store = store or Store()
        self.connected = False
        self.activity = client.activity
        self.boot = uuid.uuid4().hex
        self.started_at = iso(self.store.clock())

    # 受付設定を参照する。DB障害時は例外を呼び出し元へ返し、機能を無断で再有効化しない。
    def enabled(self, feature):
        return self.store.setting("feature:"+feature, True)

    # 管理者が指定したプレゼンスを返す。定期アクティビティ更新でもこの設定を維持する。
    def presence(self):
        return discord.Status(self.store.setting("presence", "online"))

    # 実クライアントの状態をDBに書く。latencyは秒からmsへ変換し、欠測値はNoneにする。
    def publish(self):
        latency = self.client.latency
        self.store.heartbeat(self.boot, {"name":"discord_bot","status":"online" if self.connected and self.client.is_ready() else "offline","presence":self.store.setting("presence","online"),"startedAt":self.started_at,"latencyMs":round(latency*1000) if math.isfinite(latency) else None,"guilds":len(self.client.guilds)})

    # main.pyの定期タスクから呼ぶ。確認済みキューを実Botに適用し、結果を記録する。
    async def poll(self):
        self.publish()
        command = self.store.claim(self.boot)
        if not command:
            return
        try:
            action = validate_action(command["action"])
            if not self.connected or not self.client.is_ready():
                raise RuntimeError("Bot is disconnected")
            if action["kind"] == "presence":
                await asyncio.wait_for(self.client.change_presence(status=discord.Status(action["value"]), activity=self.activity), timeout=3)
                self.store.set_setting("presence", action["value"])
            else:
                self.store.set_setting("feature:"+action["featureId"], action["enabled"])
            self.publish()
            self.store.finish(command["id"])
            logging.getLogger(__name__).info("確認済みの管理操作を適用: %s", action, extra={"dashboard_module":action.get("featureId","gateway")})
        except Exception:
            self.store.finish(command["id"], "Botへの操作適用に失敗しました。状態を確認してください")
            logging.getLogger(__name__).exception("管理操作の適用に失敗")
