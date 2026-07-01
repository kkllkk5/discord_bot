from google import genai
from google.genai import types
import os

client = None
config = types.GenerateContentConfig(
    response_mime_type="text/plain",
)


def get_client():
    global client
    if client is None:
        api_key = os.getenv("GENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("GENAI_API_KEY environment variable is not set")
        client = genai.Client(api_key=api_key)
    return client


# 食事の写真を解析する関数
def analyze_meal_images(images: list[tuple[bytes, str]]) -> str:
    if not images:
        return ""

    prompt = f"""
    あなたは「学園アイドルマスター」の「花海咲季」として振る舞ってください。
    以下の条件を厳守して応答してください：
    - 応答は必ず「花海咲季よ！」から始めてください。
    - 全体として敬語は使わず、「〜よ！」「〜だわ！」などの口調（咲季らしい勝気で自信家な口調）にしてください。
    - 一人称は「わたし」で統一してください。
    - 二人称は「あなた」で統一してください。
    - あなたは食事や自己管理に対して非常にストイックです。健康に良くない食べ物に対しては「アイドルの食べ物ではない」という強い感情を持っています。
    - もし衣を纏った揚げ物が写っている場合は、衣を剥がそうとするような発言を交えてください。ない場合は，そのことについて言及する必要はありません．

    # タスク
    ユーザーから送られた複数の食事画像を解析し、以下の条件に従って出力してください。

    # 条件
    1. 【フィルタリング】画像ごとに「食事の写真である可能性」を評価し、80%以下の画像は完全に無視してください。
    2. 【例外処理】すべての画像が80%以下だった場合は、何も出力せず「空文字列（""）」を返してください。
    3. 【トーン】返答内で「確率（80%など）」について直接言及する必要はありません。
    4. 【内容】画像に写っている食べ物の「名前」「カロリー」「栄養素」、そしてそれが「アイドルの食べ物として相応しいかどうか（厳しめにお願いします）」の判定を含めてください。全体的に内容は簡潔にまとめて下さい.
    5. 【構成】複数の画像に食事が写っている場合は、画像ごとにセクションを分けて、簡潔に出力してください。

    # 出力フォーマット（食べ物ごとの記述例）
    ・**食べ物の名前**:
    ・**カロリー**:
    ・**栄養素**:
    ・**アイドルの食べ物か**: 
    """
    contents = [prompt]
    for image_bytes, mime_type in images:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    try:
        response = get_client().models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=contents,
                config=config,
            )
    except Exception as e:
        print(f"Error analyzing meal image(3.1-flash-lite): {e}")
        # 失敗した場合は別のモデルでも試す
        try:
            response = get_client().models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config=config,
        )
        except Exception as e2:
            print(f"Error analyzing meal image(3.5-flash): {e2}")
            # 失敗した場合は下位モデルでも試す
            try:
                response = get_client().models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config,
                )
            except Exception as e3:
                print(f"Error analyzing meal image(2.5-flash): {e3}")
                return "いっぱい送ってくれてありがとうね!今日はもう遅いから寝るわよ!"

    return response.text

# 食事の写真を解析する関数（単一画像用，現在は未使用）
def analyze_meal_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    return analyze_meal_images([(image_bytes, mime_type)])
