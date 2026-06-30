from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
config = types.GenerateContentConfig(
    response_mime_type="text/plain",
)


# 食事の写真を解析する関数
def analyze_meal_images(images: list[tuple[bytes, str]]) -> str:
    if not images:
        return ""

    prompt = f"""
    以下の食事の写真をまとめて解析してください.画像はバイト列として複数渡されます．
    解析した結果,食事の写真である可能性が80%以下の画像は無視して下さい.全ての写真が食事の写真である可能性が80%以下の場合は，返答は空文字列にして下さい．
    画像の内容を正確に解析し，食べ物の名前とカロリー，栄養素を出力してください．ただ画像に写っている食べ物の情報さえ得られれば十分なので，簡潔に回答するようにお願いします．
    複数の画像に食事が写っている場合は，画像ごとに分けて簡潔に回答してください．
    なお,あなたは花海咲季なので,応答は「花海咲季よ！」で初め,全体として敬語は使わず「〜よ！」や「〜だわ！」などの口調で出力して下さい．
    一人称は「わたし」で統一して下さい．
    そして，あなたは食べ物に関してストイックで，健康に良くない食べ物に対して「アイドルの食べ物ではない」という感情を抱いています．
    解析した食べ物について,アイドルの食べ物かどうかも合わせて判別して下さい．
    なお，揚げ物が写っている場合は，衣を剥がそうとして下さい．
    """
    contents = [prompt]
    for image_bytes, mime_type in images:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config=config,
        )
    except Exception as e:
        print(f"Error analyzing meal image(3.5-flash): {e}")
        # 失敗した場合は下位モデルでも試す
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
        except Exception as e2:
            print(f"Error analyzing meal image(2.5-flash): {e2}")
            return "Error:利用制限に達した可能性があります.時間をおいて試して下さい．"

    return response.text

# 食事の写真を解析する関数（単一画像用，現在は未使用）
def analyze_meal_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    return analyze_meal_images([(image_bytes, mime_type)])

