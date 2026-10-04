import logging
import os
from google.genai import types
from google import genai

# 初回利用で作る共有クライアント。インポート時の認証・クライアント生成を避ける。
_client = None


# GENAI_API_KEYでSDKクライアントを遅延生成・再利用する。未設定ならRuntimeError。
#
# APIキーは初回生成時に読み、生成後の環境変数変更は反映しない。
def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("GENAI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=api_key)
    return _client



# SDK形式のcontents(テキスト・画像等)と生成configから空でない応答を同期生成する。
#
# modelsの順で試し、例外や空の応答なら次のモデルへ進む。
# 全モデル失敗時は既存機能向けの案内文を返す。raise_on_failure=Trueなら
# RuntimeErrorを送出し、呼び出し元に代替処理を委ねる。タイムアウトはconfigで指定する。
def analyze_with_gemini(contents, config, *, raise_on_failure=False) -> str:
    # 利用を試す優先順。モデル名・順序の変更はこの一覧で管理する。
    models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]

    for model in models:
        try:
            response = get_client().models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            if not response.text or not response.text.strip():
                raise ValueError("Gemini returned an empty response")
            return response.text
        except Exception as e:
            logging.error(f"Error generating Gemini response({model}): {e}")
            continue

    logging.error(f"全てのモデルにおいてエラーが発生しました\n")
    if raise_on_failure:
        raise RuntimeError("Gemini generation failed for all models")
    return "geminiが一時的に利用できない恐れがあるから,時間をおいてもう一度送ってね!"
