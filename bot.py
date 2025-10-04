import discord
import json
import os
import re
import feature.iidx as iidx  # 自作パッケージ
from server import server_thread

token = os.getenv('TOKEN')
# 接続に必要なオブジェクトを生成
client = discord.Client()

# 「歩数」チャンネル
STEPS_CHANNNEL_ID = "1423994718743957515"

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

    # 「歩数」チャンネルにショートカット経由での投稿があった場合，そのメッセージを元に集計する
    if message.channel.id == STEPS_CHANNNEL_ID:
        steps = int(message.content)



# Botの起動とDiscordサーバーへの接続
client.run(token)
