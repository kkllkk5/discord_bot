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
import feature.constants

song_url = "https://textage.cc/score/titletbl.js"
difficilty_url = "https://textage.cc/score/actbl.js"
data_url = "https://textage.cc/score/datatbl.js"

notion = Client(auth=os.getenv('NOTION_TOKEN'))

def make_page_id_dict():
    page_id_dict = {}
    with open("feature/iidx_notion/page_ids.csv", "r", encoding="utf-8") as csvfile:
        #CSVファイルを辞書型で読み込む
        reader = csv.DictReader(csvfile, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
        page_id_dict = {
            (row["SONGNAME"],row["DIFF"]) : row["Notion_Page_ID"]
            for row in reader
        }
    return page_id_dict


def notion_update(page_id:str,song_name:str,artist:str,bpm:str,diff):
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


def make_song_list():
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
    for id,info in titletbl.items():
        try:
            # 削除された楽曲はdifficilty_tbl[id][0] == 0:
            # SPAの難易度はdifficilty_tbl[id][9]
            if (difficilty_tbl[id][0]) != 0 and (difficilty_tbl[id][9] == 12 or difficilty_tbl[id][11] == 12):
                song_name = ""
                prefix = ""
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
                
                page_id_dict = make_page_id_dict()

                if difficilty_tbl[id][9] == 12:
                    page_id = page_id_dict[(song_name,"ANOTHER")]
                    notion_update(page_id,song_name,artist,bpm,"ANOTHER")
                if difficilty_tbl[id][11] == 12:
                    page_id = page_id_dict[(song_name,"LEGGENDARIA")]
                    notion_update(page_id,song_name,artist,bpm,"LEGGENDARIA")


                
                
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

def make_page_ids_csv():
    with open("feature/iidx_notion/page_ids.csv", "w", encoding="utf-8") as csvfile:
        #CSVファイルを辞書型で読み込む
        writer = csv.writer(csvfile)
        writer.writerow(["SONGNAME","DIFF","Notion_Page_ID"])

        pages = get_all_pages(notion, feature.constants.DATABASE_ID)
        for page in pages:
            title_property = page["properties"]["曲名"]["title"][0]["plain_text"]
            difficulty = page["properties"]["難易度"]["rich_text"][0]["text"]["content"]

            writer.writerow([title_property,difficulty,page["id"]])
