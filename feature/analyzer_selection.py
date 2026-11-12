"""複数のAI機能で共有する分析者選択UI。"""

from typing import Callable

import discord

from feature.meal_analyze.analyze_view import AnalyzeView
from feature.meal_analyze.analyzer_options import build_analyzer_options


async def request_analyzer_selection(
    message: discord.Message,
    get_emoji: Callable[[int], discord.Emoji | None],
) -> tuple[discord.Message, AnalyzeView]:
    """共通の分析者選択メッセージを送り、後始末用メッセージとViewを返す。"""
    options = build_analyzer_options(get_emoji)
    view = AnalyzeView(owner_id=message.author.id, IDOLS=options)
    control_message = await message.reply(
        f"{message.author.mention} 誰に返信してもらう？",
        view=view,
    )
    return control_message, view


__all__ = ["request_analyzer_selection"]
