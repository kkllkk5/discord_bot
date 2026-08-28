import logging
import os

from google import genai
from google.genai import types

# 内部用変数のため，prefixに_
_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("GENAI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=api_key)
    return _client



# geminiにcontentsの内容を問い合わせる関数
# 3.5が最新モデルだが，速度重視のため3.1に最初に実行してもらう
def analyze_with_gemini(contents, config) -> str:
    models = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]

    for model in models:
        try:
            response = get_client().models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            logging.error(f"Error analyzing meal image({model}): {e}")
            continue

    logging.error(f"全てのモデルにおいてエラーが発生しました\n")
    return "geminiが一時的に利用できない恐れがあるから,時間をおいてもう一度送ってね!"