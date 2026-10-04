import discord
import os
import re
import feature.iidx as iidx  # 自作パッケージ
import feature.tech as tech  # 自作パッケージ
import feature.dice_roll as dice_roll # 自作パッケージ
import feature.bot_status as bot_status # 自作パッケージ
import feature.meal_analyze as meal_analyze # 自作パッケージ
import feature.iidx_notion.result_analyze as result_analyze # 自作パッケージ
from zoneinfo import ZoneInfo
from datetime import time,datetime
import config as cfg
from discord.ext import tasks
from dotenv import load_dotenv
from dashboard.runtime import RuntimeBridge, install_log_handler

load_dotenv()

token = os.getenv('TOKEN')
JST = ZoneInfo("Asia/Tokyo")
# 接続に必要なオブジェクトを生成
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
dashboard_runtime = RuntimeBridge(client)

async def send_scheduled_message(channel_id: int, message: str) -> None:
    if not message:
        return
    channel = client.get_channel(channel_id)
    if isinstance(channel, discord.abc.Messageable):
        await channel.send(message)

# 技術記事の取得を毎日午前8時に実行

@tasks.loop(time=time(hour=8, tzinfo=JST))
async def scheduled_tech_trend_task():
    if not dashboard_runtime.enabled("tech_trend"):
        return
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
    dashboard_runtime.activity = await bot_status.set_presence(client, status=dashboard_runtime.presence())

# 実Botの状態を共有DBへ更新し、確認済み管理操作を適用する。失敗しても次回の更新を継続する。
@tasks.loop(seconds=2)
async def dashboard_sync_task():
    try:
        await dashboard_runtime.poll()
    except Exception:
        cfg.logger.exception("Dashboard連携の更新に失敗")

# 接続断を記録する。Heartbeatの期限切れ検知でも管理画面の操作は無効になる。
@client.event
async def on_disconnect():
    dashboard_runtime.connected = False
    dashboard_runtime.publish()

# Gatewayのセッション再開を記録する。キャッシュのis_readyだけでは接続断を判定しない。
@client.event
async def on_resumed():
    dashboard_runtime.connected = True
    dashboard_runtime.publish()

# 起動時に動作する処理
@client.event
async def on_ready():
    # 起動したらログイン通知が表示される
    dashboard_runtime.connected = True
    cfg.logger.info('ログインしました')
    dashboard_runtime.publish()
    if not dashboard_sync_task.is_running():
        dashboard_sync_task.start()
    # アクティビティを更新
    dashboard_runtime.activity = await bot_status.set_presence(client, status=dashboard_runtime.presence())
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
    if dashboard_runtime.enabled('iidx') and re.match('/iidx [0-9]+ [0-9]+', message.content):
        cfg.logger.info("機能の処理を開始: iidx", extra={"dashboard_module":"iidx"})
        await iidx.handle_iidx_practice_music(message)

    # 「/tech_trend」と送ると，急上昇Qiita記事を答える（手動取得用）
    if dashboard_runtime.enabled('tech_trend') and re.match('/tech_trend', message.content):
        cfg.logger.info("機能の処理を開始: tech_trend", extra={"dashboard_module":"tech_trend"})
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
    if dashboard_runtime.enabled('dice') and message.content.startswith('/dice'):
        cfg.logger.info("機能の処理を開始: dice", extra={"dashboard_module":"dice"})
        await dice_roll.handle_dice(message)

    # 「S乱リザルト」のチャンネルに画像が投稿された場合，その内容を解析しNotionのDBの内容を更新する
    if dashboard_runtime.enabled("result_analyze") and message.attachments and (message.channel.id == cfg.SRAN_RESULT_CHANNNEL_ID):
        cfg.logger.info("機能の処理を開始: result_analyze", extra={"dashboard_module":"result_analyze"})
        await result_analyze.handle_sran_result(message)

    # 食事の写真を送ると,内容をAIが解析
    # 複数送った場合は，まとめて解析してくれる
    if dashboard_runtime.enabled("meal_analyze") and message.attachments and (message.channel.id in cfg.MEAL_ANALYZE_CHANNEL_ID):
        cfg.logger.info("機能の処理を開始: meal_analyze", extra={"dashboard_module":"meal_analyze"})
        await meal_analyze.handle_meal_analyze(message,client.get_emoji)

    # 「/dp_level {曲名の一部}」と送ると，指定した曲のDP非公式難易度を答える
    # 曲名の一部から候補を複数提示し，その中から番号を指定して指定楽曲を特定する
    if dashboard_runtime.enabled('dp_level') and re.match('/dp_level .*', message.content):
        cfg.logger.info("機能の処理を開始: dp_level", extra={"dashboard_module":"dp_level"})
        await iidx.handle_dp_level(message,client)

# Botの起動
if __name__ == "__main__":
    if token is None:
        raise RuntimeError('TOKEN environment variable is not set')
    install_log_handler(dashboard_runtime.store)
    client.run(token)
