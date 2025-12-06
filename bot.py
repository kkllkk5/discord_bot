import discord
import json
import os
import re
import feature.iidx as iidx  # 自作パッケージ
from server import server_thread

token = os.getenv('TOKEN')
# 接続に必要なオブジェクトを生成
client = discord.Client()

# 起動時に動作する処理


@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    print('ログインしました')

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
                response += (music[0])
        except Exception as e:
            response = "レベルには11,12のみを現在サポートしています"
        await message.channel.send(response)

    # 「/dp_level {曲名の一部}」と送ると，指定した曲のDP非公式難易度を答える
    # 曲名の一部から候補を複数提示し，その中から番号を指定して指定楽曲を特定する
    if re.match('/dp_level .*',message.content):
        _, song_name = message.content.split()
        candidate_list = iidx.search_songname_for_dp(song_name)
        response = candidate_list
        await message.channel.send(response)



# Botの起動とDiscordサーバーへの接続
client.run(token)
