import discord
import json
import os
import re
import feature.iidx as iidx  # 自作パッケージ
import feature.tech as tech  # 自作パッケージ
import feature.constants as constants  # 自作パッケージ
import feature.dice_roll as dice_roll # 自作パッケージ
import feature.bot_status as bot_status # 自作パッケージ
import feature.meal_analyze as meal_analyze # 自作パッケージ
import feature.iidx_notion.result_analyze as result_analyze # 自作パッケージ
from zoneinfo import ZoneInfo
from datetime import time,datetime
import config as cfg
from discord.ext import tasks
import logging
import asyncio

token = os.getenv('TOKEN')
JST = ZoneInfo("Asia/Tokyo")
# 接続に必要なオブジェクトを生成
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def get_result_analyze_module():
    import feature.iidx_notion.result_analyze as result_analyze_module
    return result_analyze_module

async def send_scheduled_message(channel_id: int, message: str) -> None:
    if not message:
        return
    channel = client.get_channel(channel_id)
    if isinstance(channel, discord.abc.Messageable):
        await channel.send(message)

# 技術記事の取得を毎日午前8時に実行

@tasks.loop(time=time(hour=8, tzinfo=JST))
async def scheduled_tech_trend_task():
    today = datetime.now().day
    if (today % 2) == 0:  # 偶数日なら実行
        message = tech.fetch_trending_qiita()
        await send_scheduled_message(cfg.TECH_TREND_CHANNEL_ID, message)

# 技術ニュースの取得を毎日午前8時に実行
# (停止中)
'''
@tasks.loop(time=time(hour=8, tzinfo=ZoneInfo("Asia/Tokyo")))
async def scheduled_tech_news_task():
    message = news.main()
    await send_scheduled_message(cfg.TECH_NEWS_CHANNEL_ID, message)
'''

# 4,5,20時にアクティビティを更新
@tasks.loop(time=[
    time(hour=4, tzinfo=JST),
    time(hour=5, tzinfo=JST),
    time(hour=20, tzinfo=JST),
])
async def update_presence():
    await bot_status.set_presence(client)

# 起動時に動作する処理
@client.event
async def on_ready():
    # 起動したらログイン通知が表示される
    cfg.logger.info('ログインしました')
    # アクティビティを更新
    await bot_status.set_presence(client)
    # スケジューリングをセット
    if not scheduled_tech_trend_task.is_running():
        scheduled_tech_trend_task.start()
    if not update_presence.is_running():
        update_presence.start()
    # scheduled_tech_news_task.start()

# メッセージ受信時に動作する処理
@client.event
async def on_message(message):
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return

    # 本番起動の場合は，デバッグ用チャンネルの投稿は無視する
    if (os.getenv("DEBUG_MODE") == "0") and (message.channel.id == cfg.DEBUG_CHANNNEL_ID):
        return
    
    # デバッグモード（ローカル起動）の場合は，テスト用チャンネル以外のメッセージを無視する
    if (os.getenv("DEBUG_MODE") == "1") and not (message.channel.id == cfg.DEBUG_CHANNNEL_ID or message.channel.id == cfg.SRAN_RESULT_CHANNNEL_ID):
        return
        
    # 「/iidx {レベル} {課題曲数}」と送るとiidxの課題曲をランダムで作成
    if re.match('/iidx [0-9]+ [0-9]+', message.content):
        await iidx.handle_iidx_practice_music(message)

    # 「/tech_trend」と送ると，急上昇Qiita記事を答える（手動取得用）
    if re.match('/tech_trend', message.content):
        response = tech.fetch_trending_qiita()
        await message.channel.send(response)


    # 「/tech_news」と送ると，最新の技術記事を答える
    '''
    if re.match('/tech_news', message.content):
        import feature.news as news
        response = news.main()
        await message.channel.send(response)
    '''

    # /dice {振る回数} {ダイスの面数}と送ると，ダイスロールを実行
    # 例: 「/dice 1 100」と送ると，1d100を実行
    # 「/dice 1 4 1 6」と送ると，1d4+1d6を実行
    if message.content.startswith('/dice'):
        await dice_roll.handle_dice(message)

    # 「S乱リザルト」のチャンネルに画像が投稿された場合，その内容を解析しNotionのDBの内容を更新する
    if message.attachments and (message.channel.id == cfg.SRAN_RESULT_CHANNNEL_ID):
        await result_analyze.handle_sran_result(message)

    # 食事の写真を送ると,内容をAIが解析
    # 複数送った場合は，まとめて解析してくれる
    if message.attachments and (message.channel.id in cfg.MEAL_ANALYZE_CHANNEL_ID):
        await meal_analyze.handle_meal_analyze(message,client.get_emoji)

    # 「/dp_level {曲名の一部}」と送ると，指定した曲のDP非公式難易度を答える
    # 曲名の一部から候補を複数提示し，その中から番号を指定して指定楽曲を特定する
    if re.match('/dp_level .*', message.content):
        await iidx.handle_dp_level(message,client)

# Botの起動
if __name__ == "__main__":
    if token is None:
        raise RuntimeError('TOKEN environment variable is not set')
    client.run(token)
