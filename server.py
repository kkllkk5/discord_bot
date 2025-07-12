from threading import Thread

from fastapi import FastAPI
import uvicorn
import os
import dotenv
import asyncio

dotenv.load_dotenv()

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Server is Online."}


def start():
    asyncio.set_event_loop(asyncio.new_event_loop())
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)


def server_thread():
    t = Thread(target=start)
    t.start()

if __name__ == '__main__':
    server_thread()
