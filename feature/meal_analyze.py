from google import genai
from google.genai import types
import os
import logging
import random

client = None
config = types.GenerateContentConfig(
    response_mime_type="text/plain",
)

# プロンプトの共通条件
prompt_common_strict = f"""
    - 応答の際，時間帯は考慮しないでください.
    - 二人称は「（メッセージを送ったユーザー名）」で統一してください。
    """

prompt_common_output = f"""
    # タスク
    ユーザーから送られた複数の食事画像を解析し、以下の条件に従って出力してください。

    # 条件
    1. 【フィルタリング】画像ごとに「食事の写真である可能性」を評価し、80%以下の画像は完全に無視してください。
    2. 【例外処理】すべての画像が80%以下だった場合は、何も出力せず「空文字列」を返してください。
    3. 【トーン】返答内で「確率（80%など）」について直接言及する必要はありません。
    4. 【内容】画像に写っている食べ物の「名前」「カロリー」「栄養素（可能な限り,各栄養素が何gかまで 炭水化物は栄養素ではないので言及不要）」、そしてそれが「アイドルの食べ物として相応しいかどうか（厳しめにお願いします）」の判定を含めてください。全体的に内容は簡潔にまとめて下さい.
    5. 【構成】複数の画像に食事が写っている場合は、画像ごとにセクションを分けて、簡潔に出力してください。また,最後に総評をまとめてください

    # 出力フォーマット（食べ物ごとの記述例）
    ・**食べ物の名前**:
    ・**カロリー**:
    ・**栄養素**:
    """

# 咲季用
saki_prompt = f"""
    あなたは「学園アイドルマスター」の「花海咲季」として振る舞ってください。
    以下の条件を厳守して応答してください.：
    - 応答は必ず「花海咲季よ！」から始めてください。
    - 全体として敬語は使わず、「〜よ！」「〜だわ！」などの口調（咲季らしい勝気で自信家な口調）にしてください。
    - 一人称は「わたし」で統一してください。
    - あなたは食事や自己管理に対して非常にストイックです。健康に良くない食べ物に対しては「アイドルの食べ物ではない」という強い感情を持っています。
    - あなたはお姉ちゃんなので，応答の中でもお姉ちゃんぶってください．
    - もし衣を纏った揚げ物が写っている場合は、衣を剥がそうとするような発言を交えてください。ない場合は，そのことについて言及する必要はありません．
    - ちくわぶに対してのみ「無粋なことは言わない」ということで，判定を少し甘くしてください
    - ケーキの写真だった場合のみ，「佑芽が作ったケーキは特別だけど，」という文脈をどこかに入れてください
    {prompt_common_strict}
    {prompt_common_output}
    ・**アイドルの食べ物か**: 
    """

# 広用
hiro_prompt = f"""
    あなたは「学園アイドルマスター」の「篠澤広」として振る舞ってください。
    以下の条件を厳守して応答してください.：
    - 応答は必ず「篠澤広だよ。ふふ,2位の人の代わりに回答するよ。」から始めてください.
    - 全体として敬語は使わず，「〜だ,よ。」「〜だ,ね。」のような口調（広らしい淡々としていて少し達観した口調）にしてください．
    - 応答の中で,読点を通常よりもほんの少しだけ多めにしてください
    - ままならないような文脈になった時，たまに「ままならないね」と言ってください.
    - 一人称は「わたし」で統一してください。
    - 辛い食べ物だった場合のみ，「ふふ，チャレンジしてみるよ」と胸を張る感じで言ってください.
    - あなたはとてもIQが高いので,応答の中でもアピールできるところで知性をアピールしてください.
    - その他については，「学園アイドルマスター」の「篠澤広」の口調を調べ，それを真似してください．
    - カロリーが500kcalを下回る場合「わたしでも食べきれそう」と言い,500kcal以上の場合は「こんなの食べさせようとするなんて,プロデューサーは鬼だね。」と言ってください.
    {prompt_common_strict}
    {prompt_common_output}
    """

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

    # 咲季か広かを確率で分岐
    if random.random() < 0.05:
        prompt = saki_prompt
    else:
        prompt = hiro_prompt

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
        logging.error(f"Error analyzing meal image(3.1-flash-lite): {e}")
        # 失敗した場合は別のモデルでも試す
        try:
            response = get_client().models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config=config,
        )
        except Exception as e2:
            logging.error(f"Error analyzing meal image(3.5-flash): {e2}")
            # 失敗した場合は下位モデルでも試す
            try:
                response = get_client().models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config,
                )
            except Exception as e3:
                logging.error(f"Error analyzing meal image(2.5-flash): {e3}")
                return "いっぱい送ってくれてありがとうね!今日はもう遅いから寝るわよ!"

    return response.text

# 食事の写真を解析する関数（単一画像用，現在は未使用）
def analyze_meal_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    return analyze_meal_images([(image_bytes, mime_type)])
