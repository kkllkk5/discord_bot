
import asyncio
import logging

# スケジューリングタスク
TECH_TREND_CHANNEL_ID = 1493961159148310578  # 技術記事チャンネルのID
TECH_NEWS_CHANNEL_ID = 1515350526718378034  # 技術ニュースチャンネルのID

MEAL_ANALYZE_CHANNEL_ID = [1521351966415130645,1366375555016032336,1393923479023386750] # 食事の写真解析を許可するチャンネルのID
DEBUG_CHANNNEL_ID = 1521351966415130645 # デバッグ用のチャンネル
SRAN_RESULT_CHANNNEL_ID = 1528012029565079623 # s乱リザルトチャンネル

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord.client")

#食事解析の同時実行数制限
meal_analyze_semaphore = asyncio.Semaphore(2)