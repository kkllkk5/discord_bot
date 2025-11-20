import discord
import json
import os
import re
import feature.iidx as iidx # 自作パッケージ
import feature.steps as steps # 自作パッケージ
from server import server_thread
from discord.ext import tasks
import datetime
import pytz 

token = os.getenv('TOKEN')
# 接続に必要なオブジェクトを生成
client = discord.Client()

JST = pytz.timezone("Asia/Tokyo")

# 「歩数」チャンネル
STEPS_CHANNEL_ID = 1441063627581948065
steps_channel = client.get_channel(STEPS_CHANNEL_ID)
# 起動時に動作する処理

@client.event
async def on_ready():

# メッセージ受信時に動作する処理


@client.event
async def on_message(message):
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return
    # 「/iidx {レベル} {課題曲数}」と送るとiidxの課題曲をランダムで作成
    if re.match('/iidx [0-9]+ [0-9]+', message.content):
        _, level, song_num = message.content.split()
        try:
            practice_music_list = iidx.make_practice_music(
                int(level), int(song_num))
            response = "以下が課題曲です!\n"
            for music in practice_music_list:
                response += (music)
        except Exception as e:
            response = "レベルは11,12のみを現在サポートしています"
        await message.channel.send(response)

# 毎日0時に歩数の集計を行う
@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=JST))
async def daily_job():
    ave_recent_steps = steps.get_ave_recent_steps()
    today_steps = steps.get_today_steps
    await steps_channel.send("本日の歩数は" + today_steps + "です!\n直近7日間の歩数は" + ave_recent_steps " です!")

@daily_job.before_loop
async def before_daily_job():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    daily_job.start()

# Botの起動とDiscordサーバーへの接続
client.run(token)


