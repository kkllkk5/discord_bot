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

        # 指定した曲名の一部が1文字だった場合は検索しない
        # (候補が非常に多くなる恐れがあるため)
        # [({楽曲名},{楽曲の非公式難易度})]
        candidate_list = iidx.search_songname_for_dp(song_name)

        # 楽曲が見つからなかった場合は，処理を終了し最初からやり直す
        if len(candidate_list) == 0:
            response = "楽曲が見つかりませんでした.曲名を確認し再度実行してください."
            await message.channel.send(response)
        # 楽曲の候補が一つしかなかった場合は，その楽曲の難易度を送信する
        elif len(candidate_list) == 1:
            response = candidate_list[0][0] + "のDP非公式難易度は" + str.strip(candidate_list[0][1]) + "です."
            await message.channel.send(response)
        else:

            response = "以下の楽曲が候補です．対象の楽曲を番号で指定してください．\n"

            # 番号（1から順番に振る）と曲名を一覧で送信する
            for i,(music_name,_) in enumerate(candidate_list):
                response += "[" + str(i+1) + "]:" + music_name + "\n"

            await message.channel.send(response)

            # 待っているものに該当するかを確認する関数
            def check(m):
                # メッセージが数字かつ メッセージを送信したチャンネルが
                # コマンドを打ったチャンネルという条件
                return m.content.isdigit() and m.channel == message.channel

            try:
                while(True):
                    msg = await client.wait_for('message', check=check)
                    target_num = int(msg.content) - 1 
                    # 番号が不正(0やマイナスだったり，想定よりも大きな数)だった場合，送信し直してもらう
                    if target_num <= 0 or target_num >= len(candidate_list):
                        await message.channel.send("対象の楽曲を番号で正しく指定してください.")
                        continue
                    else:
                        response = candidate_list[target_num][0] + "のDP非公式難易度は" + str.strip(candidate_list[target_num][1]) + "です."
                        await message.channel.send(response)
                        break
            except ValueError as e:
                await message.channel.send("対象の楽曲を番号で指定してください.")
            except Exception as e:
                await message.channel.send("不明なエラーが発生しました.")



# Botの起動とDiscordサーバーへの接続
client.run(token)
