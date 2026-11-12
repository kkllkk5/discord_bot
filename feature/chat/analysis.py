"""チャット用プロンプトを作り、Geminiへ問い合わせる。"""

from feature import gemini
from feature.meal_analyze.prompt_common import compose_character_chat_prompt


def analyze_chat_message(message: str, user_name: str, analyzer_id: int) -> str:
    task = f"""
# タスク: テキストチャット
ユーザーのメッセージに、会話相手として自然に返信してください。
食事解析や画像解析は行わず、画像がある前提で話を作らないでください。
分からない情報は断定せず、必要なら短く確認してください。
ユーザーが口調・一人称・冒頭の定型文の変更を明示した場合は、その指定された項目だけ変更してください。
それ以外のキャラクター設定と正確さは維持してください。

<user_message>
{message[:3000]}
</user_message>
    """.strip()
    prompt = compose_character_chat_prompt(analyzer_id, user_name, task)
    config = gemini.types.GenerateContentConfig(response_mime_type="text/plain")
    return gemini.analyze_with_gemini([prompt], config)


__all__ = ["analyze_chat_message"]
