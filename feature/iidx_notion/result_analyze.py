import feature.gemini
import json
import csv


def make_prompt(song_list: str):
    prompt = f"""
    入力された画像から以下の情報を抽出してください。

    - 曲名
    - 難易度 (BEGINNER/NORMAL/HYPER/ANOTHER/LEGGENDARIA)
    - S乱利用可否
    - EX SCORE
    - MISS COUNT
    - CLEAR TYPE

    以下のルールを必ず守ってください。

    ・JSONのみを返してください。
    ・Markdownや説明文は不要です。
    ・取得できない項目は null にしてください。
    ・数値は文字列ではなく数値型で返してください。
    ・S乱利用可否については,S-RANDOMを利用している場合は1,その他の場合(RANDOM,R-RANDOM,MIRROR,OFF)の場合は0を返してください.
    ・EX SCORE,MISS COUNT,CLEAR TYPEについては2つ表示されていますが,必ず右側の「今回のスコア」列に入力されている方を採用してください.
    ・CLEAR TYPEは
    NO PLAY
    FAILED
    ASSIST CLEAR
    EASY CLEAR
    CLEAR
    HARD CLEAR
    EX HARD CLEAR
    FULLCOMBO CLEAR
    のいずれかを返してください。
    ・曲名については，以下の一覧の中から探してください．
    {song_list}

    出力例

    {{
    "title": "Dolphin Kick",
    "difficulty": "ANOTHER",
    "use_sran": 1,
    "ex_score": 2487,
    "miss_count": 1,
    "clear_type": "HARD CLEAR"
    }}
    """
    return prompt

def analyze_result_with_gemini(images: list[tuple[bytes, str]]):
    if not images:
        return ""
    
    # geminiのコンフィグを設定（jsonで応答）
    config = feature.gemini.types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    song_list = ""

    with open("feature/iidx_notion/page_ids.csv", "r", encoding="utf-8") as csvfile:
        #CSVファイルを辞書型で読み込む
        reader = csv.DictReader(csvfile, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
        song_list =  {song_list + row["SONGNAME"] + "," for row in reader} 



    prompt = make_prompt(song_list)
    contents = [prompt]

    # プロンプトに添付写真を追加
    for image_bytes, mime_type in images:
        contents.append(feature.gemini.types.Part.from_bytes(
            data=image_bytes, mime_type=mime_type))
        
    response = feature.gemini.analyze_with_gemini(contents,config)

    result = json.loads(response)

    # s乱を使用していないと判断した場合はそのことを伝える
    if not result["use_sran"]:
        return "このリザルトはS乱を使用していないわ!"
    return result






