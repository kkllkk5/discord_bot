import requests
import quickjs
import json

song_url = "https://textage.cc/score/titletbl.js"
difficilty_url = "https://textage.cc/score/actbl.js"

response = requests.get(song_url)
response.encoding = "shift_jis"

js = response.text

ctx = quickjs.Context()

ctx.eval(js)

# 曲名情報が入った辞書
titletbl = json.loads(
    ctx.eval("JSON.stringify(titletbl)")
)

response = requests.get(difficilty_url)
response.encoding = "shift_jis"

js = response.text

ctx = quickjs.Context()

ctx.eval(js)

difficilty_tbl = json.loads(
    ctx.eval("JSON.stringify(actbl)")
)



for id,info in titletbl.items():
    try:
        print(info,difficilty_tbl[id])
    except KeyError as e:
        pass