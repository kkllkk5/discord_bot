"""天気予報の取得とDiscordへの1回分の投稿を担当する。"""

import asyncio
import logging
from datetime import datetime

import discord

from .forecast import ForecastProvider, JmaForecastProvider, JST, format_forecast
from .narrator import ForecastNarrator

logger = logging.getLogger(__name__)


class WeatherReporter:
    # 依存先を保持する。provider未指定なら気象庁、narrator=Noneなら生成なし。
    #
    # clientはDiscordクライアント、channel_idは送信先ID。生成時には通信・投稿・
    # スケジュール開始を行わない。無効なチャンネルIDによる起動抑止はmain側で行う。
    def __init__(self, client: discord.Client, channel_id: int,
                 provider: ForecastProvider | None = None,
                 narrator: ForecastNarrator | None = None):
        self.client = client
        self.channel_id = channel_id
        self.provider = provider if provider is not None else JmaForecastProvider()
        self.narrator = narrator

    # 実行時点のJST当日予報を取得し、指定チャンネルへ1回投稿する。
    #
    # 同期の取得・生成は別スレッドで実行する。生成失敗時は元の予報に戻し、
    # 取得・投稿失敗はログに記録して終了する。キャンセルは呼び出し元へ伝播する。
    # 再試行・実行間の重複排除は行わず、実行時刻と起動管理はmainに委ねる。
    async def post_report(self) -> None:
        try:
            await self.client.wait_until_ready()
            channel = self.client.get_channel(self.channel_id)
            if channel is None:
                channel = await self.client.fetch_channel(self.channel_id)
            if not isinstance(channel, discord.abc.Messageable):
                raise TypeError("天気投稿先がメッセージ送信可能なチャンネルではありません")
            day = datetime.now(JST).date()
            forecast = await asyncio.to_thread(self.provider.fetch, day)
            message = format_forecast(forecast)  # 生成なし・生成失敗時にも使用する元の予報。
            if self.narrator is not None:
                try:
                    # 待機の上限は60秒。打切り後もスレッド内の通信は終了まで続く場合がある。
                    narration = await asyncio.wait_for(
                        asyncio.to_thread(self.narrator.narrate, forecast), timeout=60)
                    if not isinstance(narration, str) or not narration.strip():
                        raise ValueError("天気案内が空です")
                    # 生成文と併せて元の予報も掲載し、数値と出典を確認できるようにする。
                    message = f"{narration}\n\n{message}"
                    if len(message) > 2000:
                        raise ValueError("天気投稿がDiscordの文字数上限を超えています")
                except Exception:
                    logger.exception("Geminiの天気案内に失敗したため元の予報を投稿します")
                    message = format_forecast(forecast)
            await channel.send(message,
                               allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            # 取得・権限・投稿エラーでループを停止させず翌朝も実行する。
            logger.exception("天気予報の取得または投稿に失敗しました")
