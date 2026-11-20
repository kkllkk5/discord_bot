"""Discordの共通メッセージ処理。"""

MAX_MESSAGE_LENGTH = 2000


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Discordの本文上限以内に、改行や空白を優先して分割する。"""
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    if not text:
        return [""]

    chunks = []
    remaining = text
    while len(remaining) > max_length:
        split_at = remaining.rfind("\n", 0, max_length + 1)
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, max_length + 1)
        if split_at <= 0:
            split_at = max_length
        else:
            split_at += 1

        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]

    if remaining:
        chunks.append(remaining)
    return chunks


__all__ = ["MAX_MESSAGE_LENGTH", "split_message"]
