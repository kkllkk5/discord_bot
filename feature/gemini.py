import logging
import os

from google import genai
from google.genai import types

client = None


def get_client():
    global client
    if client is None:
        api_key = os.getenv("GENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("GENAI_API_KEY environment variable is not set")
        client = genai.Client(api_key=api_key)
    return client


# geminiにcontentsの内容を問い合わせる関数
def analyze_with_gemini(contents, config) -> str:
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