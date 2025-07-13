from threading import Thread

from fastapi import FastAPI
import uvicorn
import os
import dotenv
import asyncio
import schedule
import time
import requests

dotenv.load_dotenv()

app = FastAPI()
port = int(os.environ.get("PORT", 8080))

@app.get("/")
async def root():
    return {"message": "Server is Online."}


def start():
    asyncio.set_event_loop(asyncio.new_event_loop())
    uvicorn.run(app, host="0.0.0.0", port=port)

def health_check():
    print(requests.get('http://0.0.0.0:'+str(port)).status_code)
    return requests.get('http://0.0.0.0:'+str(port)).status_code

def server_thread():
    t = Thread(target=start)
    t.start()
    while True:
        schedule.run_pending()  # 3. 指定時間が来てたら実行、まだなら何もしない
        time.sleep(1)  # 待ち

schedule.every(1).minutes.do(health_check)

if __name__ == '__main__':
    server_thread()
