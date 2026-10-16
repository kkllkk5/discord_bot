from threading import Thread

from fastapi import FastAPI
import uvicorn
import os
import dotenv
import asyncio
import schedule
import time
import requests
import logging

dotenv.load_dotenv()

app = FastAPI()
port = int(os.environ.get("PORT", 8080))
HEALTH_CHECK_URL = os.environ.get("HEALTH_CHECK_URL","http://0.0.0.0:"+str(port))

HEALTH_CHECK_TIMEOUT = (5, 10)  # 接続・読み取りの待ち時間（秒）
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {"message": "Server is Online."}


def start():
    asyncio.set_event_loop(asyncio.new_event_loop())
    uvicorn.run(app, host="0.0.0.0", port=port)

#sleep対策用定期実行health check
def health_check():
    try:
        with requests.get(HEALTH_CHECK_URL, timeout=HEALTH_CHECK_TIMEOUT) as response:
            response.raise_for_status()
            return response.status_code
    except requests.RequestException as exc:
        # 例外をscheduleへ伝播させると定期実行ループが終了してしまう。
        # URLや例外本文には認証情報が含まれ得るため、種類のみを記録する。
        logger.warning("Health check failed (%s); retrying on the next interval", type(exc).__name__)
        return None

schedule.every(1).minutes.do(health_check)

def server_thread():
    t = Thread(target=start)
    t.start()
    while True:
        schedule.run_pending()  # 3. 指定時間が来てたら実行、まだなら何もしない
        time.sleep(1)  # 待ち

if __name__ == '__main__':
    server_thread()
