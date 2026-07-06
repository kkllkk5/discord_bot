import discord
import json
import os
import re
import feature.iidx as iidx  # 自作パッケージ
import feature.tech as tech  # 自作パッケージ
import feature.news as news  # 自作パッケージ
import feature.meal_analyze as meal_analyze  # 自作パッケージ
import feature.constants as constants  # 自作パッケージ
import feature.dice_roll as dice_roll # 自作パッケージ
from zoneinfo import ZoneInfo
from datetime import time
import datetime
from discord.ext import tasks
from server import server_thread
import logging
import asyncio

token = os.getenv('TOKEN')
# 接続に必要なオブジェクトを生成
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord.client")


# スケジューリングタスク
TECH_TREND_CHANNEL_ID = 1493961159148310578  # 技術記事チャンネルのID
TECH_NEWS_CHANNEL_ID = 1515350526718378034  # 技術ニュースチャンネルのID

MEAL_ANALYZE_CHANNEL_ID = [1521351966415130645,1366375555016032336,1393923479023386750] # 食事の写真解析を許可するチャンネルのID
DEBUG_CHANNNEL_ID = 1521351966415130645 # デバッグ用のチャンネル

async def send_scheduled_message(channel_id: int, message: str) -> None:
    channel = client.get_channel(channel_id)
    if isinstance(channel, discord.abc.Messageable):
        await channel.send(message)

# 技術記事の取得を毎日午前8時に実行


@tasks.loop(time=time(hour=8, tzinfo=ZoneInfo("Asia/Tokyo")))
async def scheduled_tech_trend_task():
    today = datetime.datetime.now().day
    if (today % 2) == 0:  # 偶数日なら実行
        message = tech.fetch_trending_qiita()
        await send_scheduled_message(TECH_TREND_CHANNEL_ID, message)

# 技術ニュースの取得を毎日午前8時に実行

'''
@tasks.loop(time=time(hour=8, tzinfo=ZoneInfo("Asia/Tokyo")))
async def scheduled_tech_news_task():
    message = news.main()
    await send_scheduled_message(TECH_NEWS_CHANNEL_ID, message)
'''
# 起動時に動作する処理


@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    logger.info('ログインしました')
    # スケジューリングをセット
    scheduled_tech_trend_task.start()
    # scheduled_tech_news_task.start()

# メッセージ受信時に動作する処理


@client.event
async def on_message(message):
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return

    # 本番起動の場合は，デバッグ用チャンネルの投稿は無視する
    if (os.getenv("DEBUG_MODE") == "0") and (message.channel.id == DEBUG_CHANNNEL_ID):
        return
    
    # デバッグモード（ローカル起動）の場合は，テスト用チャンネル以外のメッセージを無視する
    if (os.getenv("DEBUG_MODE") == "1") and not (message.channel.id == DEBUG_CHANNNEL_ID):
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

    # 「/tech_trend」と送ると，急上昇Qiita記事を答える（手動取得用）
    if re.match('/tech_trend', message.content):
        response = tech.fetch_trending_qiita()
        await message.channel.send(response)

    # 「/tech_news」と送ると，最新の技術記事を答える
    '''
    if re.match('/tech_news', message.content):
        response = news.main()
        await message.channel.send(response)
    '''

    # /dice {振る回数} {ダイスの面数}と送ると，ダイスロールを実行
    # 例: 「/dice 1 100」と送ると，1d100を実行
    # 「/dice 1 4 1 6」と送ると，1d4+1d6を実行
    if re.match('/dice ([0-9]+)+', message.content):
        try:
            # 入力から振る回数・ダイスの面数のリストを作成
            times_list, num_faces_list = list(map(int,message.content.split()[1::2])),list(map(int,message.content.split()[2::2]))

            response = dice_roll.dice_roll(times_list,num_faces_list)
            await message.reply(response)

        except TypeError as e:
            logging.error(f"{e}:message:{message.content}")
            await message.reply("ダイスを振る回数,面数を正しく指定してね！")
        except ValueError as e:
            logging.error(f"{e}:message:{message.content}")
            await message.reply("ダイスを振る回数,面数を正しく指定してね！")
    # /diceとだけ送った場合は1d100を実行
    elif message.content == '/dice':
        response = dice_roll.dice_roll([1],[100])
        await message.reply(response)


    
    # 食事の写真を送ると,内容をAIが解析
    # 複数送った場合は，まとめて解析してくれる
    # 食事の写真の可能性が80%以下の場合は，何も応答しない
    if message.attachments and (message.channel.id in MEAL_ANALYZE_CHANNEL_ID):
        images = []
        # 添付ファイルを取得
        for attachment in message.attachments:
            # 添付ファイルが画像かどうかを判定
            if attachment.content_type and attachment.content_type.startswith("image"):
                logger.info("画像を受け取りました")
                # 中身をバイト列として取得
                image_bytes = await attachment.read()
                images.append((image_bytes, attachment.content_type))

        analyzer_id = constants.ANALYZER_ID_ALL # デフォルトは全員からランダムに選択

        # テキストでコマンドが打たれている場合は，回答者を指定する
        if message.content.startswith("/saki"):
            analyzer_id = constants.ANALYZER_ID_SAKI
        elif message.content.startswith("/hiro"):
            analyzer_id = constants.ANALYZER_ID_HIRO
        elif message.content.startswith("/rinami"):
            analyzer_id = constants.ANALYZER_ID_RINAMI

        if images != []:
            user_name = message.author.display_name
            meal_analyze_semaphore = asyncio.Semaphore(2)

            async with meal_analyze_semaphore:
                response_text = await asyncio.to_thread(
                    meal_analyze.analyze_meal_images,
                    images,
                    user_name,
                    analyzer_id
                )

            if (response_text != None) and (response_text != ""):
                await message.reply(response_text)
        else:
            logger.info("食事の画像ではないと判断されたため，解析はスキップされました．")

    # 「/dp_level {曲名の一部}」と送ると，指定した曲のDP非公式難易度を答える
    # 曲名の一部から候補を複数提示し，その中から番号を指定して指定楽曲を特定する
    if re.match('/dp_level .*', message.content):
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
            response = candidate_list[0][0] + "のDP非公式難易度は" + \
                str.strip(candidate_list[0][1]) + "です."
            await message.channel.send(response)
        else:

            response = "以下の楽曲が候補です．対象の楽曲を番号で指定してください．\n"

            # 番号（1から順番に振る）と曲名を一覧で送信する
            for i, (music_name, _) in enumerate(candidate_list):
                response += "[" + str(i+1) + "]:" + music_name + "\n"

            await message.channel.send(response)

            # 待っているものに該当するかを確認する関数
            def check(m):
                # メッセージが数字かつ メッセージを送信したチャンネルが
                # コマンドを打ったチャンネルという条件
                return m.content.isdigit() and m.channel == message.channel

            try:
                while (True):
                    msg = await client.wait_for('message', check=check)
                    target_num = int(msg.content) - 1
                    # 番号が不正(マイナスだったり，想定よりも大きな数)だった場合，送信し直してもらう
                    if target_num < 0 or target_num >= len(candidate_list):
                        await message.channel.send("対象の楽曲を番号で正しく指定してください.")
                        continue
                    else:
                        response = candidate_list[target_num][0] + "のDP非公式難易度は" + str.strip(
                            candidate_list[target_num][1]) + "です."
                        await message.channel.send(response)
                        break
            except ValueError as e:
                await message.channel.send("対象の楽曲を番号で指定してください.")
            except Exception as e:
                await message.channel.send("不明なエラーが発生しました.")


# Botの起動
if __name__ == "__main__":
    if token is None:
        raise RuntimeError('TOKEN environment variable is not set')
    client.run(token)
