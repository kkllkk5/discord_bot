import requests
import quickjs
import json
import re
import html
from notion_client import Client
import os
from pprint import pprint
import csv 
import time

song_url = "https://textage.cc/score/titletbl.js"
difficilty_url = "https://textage.cc/score/actbl.js"
data_url = "https://textage.cc/score/datatbl.js"

notion = Client(auth=os.getenv('NOTION_TOKEN'))
DATABASE_ID="3a061b60-123e-80c2-8faf-000b6c63d025"

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

response = requests.get(data_url)
response.encoding = "shift_jis"

js = response.text

ctx = quickjs.Context()

ctx.eval(js)

data_tbl = json.loads(
    ctx.eval("JSON.stringify(datatbl)")
)

page_id_dict = {}
with open("feature/iidx_notion/page_ids.csv", "r", encoding="utf-8") as csvfile:
    #CSVファイルを辞書型で読み込む
    reader = csv.DictReader(csvfile, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
    page_id_dict = {
        row["SONGNAME"]: {
            row["DIFF"]:row["Notion_Page_ID"]
        }
        for row in reader
    }


def notion_update(pafe_id:str,song_name:str,artist:str,bpm:str,diff):
            notion.pages.update(
                page_id=page_id,
                properties={
                    "曲名": {
                        "title": [
                            {
                                "text": {
                                    "content": song_name
                                }
                            }
                        ]
                    },
                    "アーティスト": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": artist
                                }
                            }
                        ]
                    },
                    "BPM": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": bpm
                                }
                            }
                        ]
                    },
                    "難易度": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": diff
                                }
                            }
                        ]
                    }
                }
            )

            time.sleep(0.1)

for id,info in titletbl.items():
    try:
        # 削除された楽曲はdifficilty_tbl[id][0] == 0:
        # SPAの難易度はdifficilty_tbl[id][9]
        if (difficilty_tbl[id][0]) != 0 and (difficilty_tbl[id][9] == 12 or difficilty_tbl[id][11] == 12):
            song_name = ""
            # サブタイトルがある場合は合体
            if len(info) == 7:
                song_name = info[5] + info[6]
            else:
                song_name = info[5] 

            # 一部楽曲には余計なフォント装飾が入っているので，消す
            song_name = re.sub(r'<font[^>]*>(.*?)</font>', r'\1', song_name)
            song_name = re.sub(r'<div[^>]*>(.*?)</div>', r'\1', song_name)
            song_name = re.sub(r'<span[^>]*>(.*?)>', r'\1', song_name)
            song_name = song_name.replace('<br>','')
            song_name = song_name.replace('</span','')
            song_name = html.unescape(song_name)
            artist = info[4]
            song_data = data_tbl[id]
            notes = song_data[4]
            bpm = song_data[-1]


            if difficilty_tbl[id][9] == 12:
                continue
                #page_id = page_id_dict[str(info[5])]["ANOTHER"]
                #notion_update(page_id,song_name,artist,bpm,"ANOTHER")
            if difficilty_tbl[id][11] == 12:
                results = notion.data_sources.query(
                    data_source_id=DATABASE_ID,
                        filter={
                            "property": "曲名",
                            "title": {
                                "equals": song_name
                            }
                        }
                )
                if results["results"]:
                    #page_id = page_id_dict[str(info[5])]["LEGGENDARIA"]
                    #page_id = results["results"][0]["id"]
                    #notion_update(page_id,song_name,artist,bpm,"LEGGENDARIA")
                    continue
                else:
                    notion.pages.create(
                        parent={"data_source_id": DATABASE_ID},
                        properties={
                            "曲名": {
                                "title": [
                                    {
                                        "text": {
                                            "content": song_name
                                        }
                                    }
                                ]
                            },
                            "アーティスト": {
                                "rich_text": [
                                    {
                                        "text": {
                                            "content": artist
                                        }
                                    }
                                ]
                            },
                            "BPM": {
                                "rich_text": [
                                    {
                                        "text": {
                                            "content": bpm
                                        }
                                    }
                                ]
                            },
                            "難易度": {
                                "rich_text": [
                                    {
                                        "text": {
                                            "content": "LEGGENDARIA"
                                        }
                                    }
                                ]
                            }
                        }
                    )
            
            
    except KeyError as e:
        # TODO:新規に追加された楽曲については，列を追加する処理を入れる
        # バージョンが33以降として管理できそう？
        "if info[0] >= 33:"
        pass
    

def get_all_pages(notion, data_source_id):
    pages = []
    cursor = None

    while True:
        response = notion.data_sources.query(
            data_source_id=data_source_id,
            start_cursor=cursor
        ) if cursor else notion.data_sources.query(
            data_source_id=data_source_id
        )

        pages.extend(response["results"])

        if not response["has_more"]:
            break

        cursor = response["next_cursor"]

    return pages

if __name__ == "__main__":

    with open("feature/iidx_notion/page_ids.csv", "w", encoding="utf-8") as csvfile:
        #CSVファイルを辞書型で読み込む
        writer = csv.writer(csvfile)
        writer.writerow(["SONGNAME","DIFF","Notion_Page_ID"])

        pages = get_all_pages(notion, DATABASE_ID)
        for page in pages:
            title_property = page["properties"]["曲名"]["title"][0]["plain_text"]
            difficulty = page["properties"]["難易度"]["rich_text"][0]["text"]["content"]

            writer.writerow([title_property,difficulty,page["id"]])
