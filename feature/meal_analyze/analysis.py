"""食事画像とプロンプトを組み立て、Geminiで解析する。"""

from feature import gemini
from .make_prompt import get_prompt_for_analyzer


# 食事の写真を解析する関数
def analyze_meal_images(images: list[tuple[bytes, str]], message: str, user_name: str, analyzer_id: int) -> str:
    if not images:
        return ""

    # analyzer_idと対応するプロンプトを取得
    # get_prompt_for_analyzer 側でユーザー名を安全に正規化するため、ここでは再正規化しない
    prompt = get_prompt_for_analyzer(analyzer_id, user_name, message)
    contents = [prompt]

    # プロンプトに添付写真を追加
    for image_bytes, mime_type in images:
        contents.append(
            gemini.types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )
        )

    # geminiのコンフィグを設定（テキスト応答）
    config = gemini.types.GenerateContentConfig(response_mime_type="text/plain")
    return gemini.analyze_with_gemini(contents, config)
