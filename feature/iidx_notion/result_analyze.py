import feature.gemini
import json
import csv
import feature.iidx_notion.textage
from notion_client import Client
import os
import logging
import feature.constants
from pathlib import Path

_notion_client = None


def get_notion_client():
    global _notion_client
    if _notion_client is None:
        token = os.getenv('NOTION_TOKEN')
        if not token:
            raise RuntimeError('NOTION_TOKEN environment variable is not set')
        _notion_client = Client(auth=token)
    return _notion_client


# プロンプトの作成関数
# song_list（Lv12曲名リスト）についてはCSVから作成して渡す
def make_prompt(song_list: str):
    prompt = f"""
    入力された画像から以下の情報を抽出してください。

    - 曲名
    - 難易度 (BEGINNER/NORMAL/HYPER/ANOTHER/LEGGENDARIA)
    - S乱利用可否
    - EX SCORE
    - MISS COUNT

    以下のルールを必ず守ってください。

    ・JSONのみを返してください。
    ・Markdownや説明文は不要です。
    ・キーは絶対に省略しないでください.取得できない項目は null にしてください。
    ・数値は文字列ではなく数値型で返してください。
    ・S乱利用可否については,S-RANDOMを利用している場合は1,その他の場合(RANDOM,R-RANDOM,MIRROR,OFF)の場合は0を返してください.
    ・左上に大きく「A」「AA」「F」と書かれていてもそれは曲名ではありません.絶対に無視してください.曲名は下中央に書いてあります.
    ・EX SCORE,MISS COUNT,CLEAR TYPEについては2つ表示されていますが,必ず右側の「今回のスコア」列に入力されている方を採用してください.
    ・曲名については，以下の一覧の中から探してください．
    {song_list}

    出力例:
    {{
    "title": "Dolphin Kick",
    "difficulty": "ANOTHER",
    "use_sran": 1,
    "ex_score": 2487,
    "miss_count": 1,
    }}
    """
    return prompt

# 「最高スコア」のみの更新関数
def notion_score_update(page_id:str,best_score:int):
    get_notion_client().pages.update(
        page_id=page_id,
        properties={
            "最高スコア": {
                "number": best_score
            },
        }
    )
# 「最小BP」のみの更新関数
def notion_bp_update(page_id:str,min_bp:int):
    get_notion_client().pages.update(
        page_id=page_id,
        properties={
            "最小BP": {
                "number": min_bp
            }
        }
    )

# リザルトの解析関数
# images:送られた画像
def analyze_result_with_gemini(images: list[tuple[bytes, str]]):
    if not images:
        return ""
    
    # geminiのコンフィグを設定（jsonで応答）
    config = feature.gemini.types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    # 楽曲リストを取得し,プロンプトを作成
    song_list = ""
    csv_path = Path(__file__).resolve().parent / "page_ids.csv" 
    with open(csv_path, "r", encoding="utf-8") as csvfile:
        #CSVファイルを辞書型で読み込む
        reader = csv.DictReader(csvfile, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
        song_list =  sorted({row["SONGNAME"] for row in reader})


    song_list_str = "\n".join(song_list)
    prompt = make_prompt(song_list_str)
    contents = [prompt]

    # プロンプトに添付写真を追加
    for image_bytes, mime_type in images:
        contents.append(feature.gemini.types.Part.from_bytes(
            data=image_bytes, mime_type=mime_type))
        
    
    response = feature.gemini.analyze_with_gemini(contents,config)

    try:
        result = json.loads(response)
    except Exception as e:
        logging.error(f"S乱リザルト解析機能実行エラー:{e}")
        return "画像の解析に失敗したわ!ごめんなさい!"

    # s乱を使用していないと判断した場合はそのことを伝える
    if not result.get("use_sran"):
        return "このリザルトはS乱を使用していないわ!S乱を使用しているリザルトを見せてちょうだい!"
    
    
    '''
    例
    {'title': 'Marie Antoinette', 'difficulty': 'LEGGENDARIA', 'use_sran': 0, 'ex_score': 2906, 'miss_count': 17}
    '''
    title = result['title']
    difficulty = result['difficulty']
    ex_score = result['ex_score']
    miss_count = result['miss_count']

    page_id_dict = feature.iidx_notion.textage.make_page_id_dict()

    try:
        page_id = page_id_dict[(title,difficulty)]

        page = get_notion_client().pages.retrieve(page_id=page_id)

        update_flag = False

        response_text = "スコアの更新を行ったわ！\n"

        # notionに現在記載されている最高スコア・最小BPを取得
        best_score = None
        if page['properties']['最高スコア']['number'] != None:
            best_score = page['properties']['最高スコア']['number']
        
        min_bp = None
        if page['properties']['最小BP']['number'] != None:
            min_bp = page['properties']['最小BP']['number']

        # スコアが登録されていないか，
        if (best_score == None):
            update_flag = True
            notion_score_update(page_id=page_id,best_score=ex_score)
            response_text += f"スコア:{ex_score} (ベストスコア:登録なし)\n"
        # スコアを上回った場合はnotionのデータを更新
        elif (ex_score > best_score):
            update_flag = True
            notion_score_update(page_id=page_id,best_score=ex_score)
            response_text += f"スコア:{ex_score} (+{ex_score - best_score})\n"
        else:
            response_text += f"スコア:{ex_score} (-{best_score - ex_score})\n"
        
        # BPが登録されていないか，
        if (min_bp == None):
            update_flag = True
            notion_bp_update(page_id=page_id,min_bp=miss_count)
            response_text += f"BP:{miss_count}(自己最小BP:登録なし)\n"
        # BPを少なくできた場合はnotionのデータを更新
        elif (miss_count < min_bp):
            update_flag = True
            response_text += f"BP:{miss_count} (-{min_bp - miss_count})\n"
        else:
            response_text += f"BP:{miss_count} (+{miss_count - min_bp})\n"
        
        # 更新を行わなかった場合は専用のメッセージを返す
        if not update_flag:
            response_text = "更新は行わなかったわ！\n"
            if best_score != None:
                response_text += f"自己最高スコア:{best_score} (+{ex_score - best_score})\n"
            if min_bp != None:
                response_text += f"自己最小BP:{min_bp} (-{miss_count - min_bp})\n"

        

        return response_text 
    except KeyError as e:
        logging.error(f"S乱リザルト解析機能実行エラー:{e}")
        return "この楽曲はDBに登録されていないわ!"
    except Exception as e:
        logging.error(f"S乱リザルト解析機能実行エラー:{e}")
        return "エラーが発生したわ!期間をおいてやり直してちょうだい!"






