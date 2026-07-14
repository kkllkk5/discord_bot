import datetime
import discord
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

async def set_presence(client):
    now = datetime.datetime.now(JST)

    if (20 <= now.hour) or (now.hour < 4):
        activity = discord.CustomActivity(
            name="じゃ,おやすみっ!ぐー。"
        )
    elif now.hour == 4:
        activity = discord.CustomActivity(
            name="朝の4時よ!これから走りに出るんでしょ?"
        )
    else:
        activity = discord.Game(
            name="🎮 学園アイドルマスターをプレイ中"
        )

    await client.change_presence(
        status=discord.Status.online,
        activity=activity,
    )