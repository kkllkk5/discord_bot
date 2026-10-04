import datetime
import discord
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# 現在時刻に応じたアクティビティを設定する。statusは管理画面の指定を維持するための引数。
# Discordへ送信したactivityを返し、送信失敗は呼び出し元へ伝播する。
async def set_presence(client, status=discord.Status.online):
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
        status=status,
        activity=activity,
    )
    return activity
