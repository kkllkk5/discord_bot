"""天気予報の取得とDiscordへの1回分の投稿を担当する。"""

import asyncio
import logging
from datetime import datetime

import discord

from .forecast import ForecastProvider, JmaForecastProvider, JST, format_forecast

logger = logging.getLogger(__name__)


class WeatherReporter:
    def __init__(self, client: discord.Client, channel_id: int,
                 provider: ForecastProvider | None = None):
        self.client = client
        self.channel_id = channel_id
        self.provider = provider if provider is not None else JmaForecastProvider()

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
            await channel.send(format_forecast(forecast),
                               allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            # 取得・権限・投稿エラーでループを停止させず翌朝も実行する。
            logger.exception("天気予報の取得または投稿に失敗しました")
