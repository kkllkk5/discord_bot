from google import genai
from google.genai import types
import json
import os

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
config = types.GenerateContentConfig(
    response_mime_type="text/plain",
)

# 食事の写真を解析する関数
def analyze_meal_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:

    prompt = f"""
    以下の食事の写真を解析してください.画像はバイト列として渡されます．
    解析した結果,食事の写真である可能性が80%以下の場合は何も出力しないでください．
    画像の内容を正確に解析し，食べ物の名前とカロリーなどの詳細情報を出力してください．ただ画像に写っている食べ物の情報さえ得られれば十分です．
    なお,あなたは花海咲季なので,応答は「花海咲季よ！」で初め,全体として敬語は使わず「〜よ！」や「〜だわ！」などの口調で出力して下さい．
    一人称は「わたし」で統一して下さい．
    そして，あなたは食べ物に関してストイックで，健康に良くない食べ物に対して「アイドルの食べ物ではない」という感情を抱いています．
    解析した食べ物について,アイドルの食べ物かどうかも合わせて判別して下さい．
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=config,
        )
    except Exception as e:
        print(f"Error analyzing meal image: {e}")
        return {"foods": [], "summary": "解析に失敗しました."}

    try:
        return response.text
    except (TypeError, json.JSONDecodeError) as e:
        print(f"Error parsing meal analysis response: {e}")
        return {"foods": [], "summary": "解析結果の読み取りに失敗しました."}



