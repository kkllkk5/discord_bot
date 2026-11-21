"""複数のAI機能で共有するプロンプトユーティリティ。"""

import random
import re

from feature import constants
from . import characters


def sanitize_user_name(user_name: str | None) -> str:
    """ユーザー名をプロンプトへ安全に埋め込める範囲に整える。"""
    if user_name is None:
        return "ユーザー"

    cleaned = str(user_name)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)

    for marker in [
        r"(?i)ignore\s+all\s+previous\s+instructions",
        r"(?i)you\s+are\s+now",
        r"(?i)act\s+as\s+if",
        r"(?i)new\s+instructions?",
        r"(?i)^\s*(?:system|assistant|user|developer)\s*[:\-]",
    ]:
        pattern = re.compile(marker)
        if pattern.search(cleaned):
            cleaned = pattern.split(cleaned, maxsplit=1)[0]
            break

    cleaned = re.sub(r"[^A-Za-z0-9ぁ-んァ-ン一-龯ー_ -]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:32] if cleaned else "ユーザー"


def compose_prompt(*parts: str) -> str:
    """空でないプロンプト部品を順番に連結する。"""
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def compose_character_chat_prompt(character_id: int, user_name: str, task: str) -> str:
    """共有キャラクター設定に、機能側で用意したチャットタスクを組み合わせる。"""
    if character_id == constants.ANALYZER_ID_ALL_IDOL:
        character_id = random.choice(characters.get_character_ids_for_group("idol"))
    elif character_id == constants.ANALYZER_ID_ALL_AIRPLAY:
        character_id = random.choice(characters.get_character_ids_for_group("airplay"))
    safe_user_name = sanitize_user_name(user_name)
    name_rule = f"""
# 最優先ルール: ユーザー名の表記を厳守
ユーザーの名前は次の文字列です。
<user_name>{safe_user_name}</user_name>

ユーザーに呼びかけるときは、上の名前を一字一句そのまま使ってください。
英字の大文字・小文字を含め、綴りを絶対に変更しないでください。カタカナ・ひらがな・漢字への翻字、翻訳、読み仮名への置き換え、短縮、別名化は禁止です。
名前に敬称や語尾を付ける場合も、元の名前の綴りはそのまま残してください。
他のキャラクター設定や自然な会話の指示より、この表記ルールを優先してください。
    """.strip()
    return compose_prompt(
        characters.get_character_persona(character_id, safe_user_name),
        task,
        name_rule,
    )
