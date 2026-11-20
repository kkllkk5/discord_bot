"""チャット用プロンプトを作り、Geminiへ問い合わせる。"""

from feature import gemini
from feature.ai_config.prompting import compose_character_chat_prompt


def generate_chat_response(
    message: str,
    user_name: str,
    analyzer_id: int,
    images: list[tuple[bytes, str]] | None = None,
) -> str:
    task = f"""
# タスク: テキストチャット
ユーザーのメッセージに、会話相手として自然に返信してください。
ユーザーのメッセージに含まれる内容を中心に会話してください。
画像が添付されている場合は実際に確認できる範囲で会話に反映し、画像がない場合は画像の内容を想像しないでください。
分からない情報は断定せず、必要なら短く確認してください。
ユーザーが口調・一人称・冒頭の定型文の変更を明示した場合は、その指定された項目だけ変更してください。
それ以外のキャラクター設定と正確さは維持してください。

<user_message>
{message[:3000]}
</user_message>
    """.strip()
    prompt = compose_character_chat_prompt(analyzer_id, user_name, task)
    # 画像は既存の会話プロンプトを変えず、Geminiへの補助入力として添える。
    contents = [prompt]
    for image_bytes, mime_type in images or []:
        contents.append(
            gemini.types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
                media_resolution={"level": "media_resolution_medium"},
            )
        )
    config = gemini.types.GenerateContentConfig(response_mime_type="text/plain")
    return gemini.analyze_with_gemini(contents, config)


__all__ = ["generate_chat_response"]
