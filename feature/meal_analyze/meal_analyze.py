import asyncio
import os
from typing import Callable, Optional

import config as cfg
import discord

from feature import constants
from feature import gemini
from feature.meal_analyze.analyze_view import AnalyzeView
from feature.meal_analyze.make_prompt import PROMPT_FACTORY_REGISTRY, get_prompt_for_analyzer


# 食事解析
async def handle_meal_analyze(message, get_emoji):
    text = message.content
    images = []
    # 添付ファイルを取得
    for attachment in message.attachments:
        # 添付ファイルが画像かどうかを判定
        if attachment.content_type and attachment.content_type.startswith("image"):
            cfg.logger.info("画像を受け取りました")
            # 中身をバイト列として取得
            image_bytes = await attachment.read()
            images.append((image_bytes, attachment.content_type))

    analyzer_id = constants.ANALYZER_ID_ALL_IDOL

    if images:
        analyzer_options = build_analyzer_options(get_emoji)
        view = AnalyzeView(owner_id=message.author.id, IDOLS=analyzer_options)

        # 誰に分析してもらうかどうかを質問
        control_message = await message.reply(
            f"{message.author.mention} 誰に分析してもらう？",
            view=view,
        )

        try:
            # ボタンの押下待ちを無期限に待たないようにする
            await view.event.wait()

            analyzer_id = view.result
            if analyzer_id is None:
                # 想定外の状態: analyzer_idが設定されていない場合は処理を中断
                return
        
            # キャンセルとなった場合は解析を実行しない
            if analyzer_id == constants.ANALYZER_ID_CANCELLED:
                return

            user_name = message.author.display_name
            async with cfg.meal_analyze_semaphore:
                response_text = await asyncio.to_thread(
                    analyze_meal_images,
                    images,
                    text,
                    user_name,
                    analyzer_id,
                )
            if (response_text is not None) and (response_text != ""):
                await message.reply(response_text)
        finally:
            if control_message is not None:
                await control_message.delete()
    else:
        cfg.logger.info("画像が見つかりませんでした.")


# Discord上に表示するボタンをコントロールする関数
def build_analyzer_options(get_emoji: Callable[[int], Optional[discord.Emoji]]) -> list[tuple[str, int, int, Optional[discord.Emoji], discord.ButtonStyle]]:
    buttons = [
        # 表示文字列,表示列,分析者ID,表示絵文字,ボタンの表示色
        ("アイドル全員からランダム", 0, constants.ANALYZER_ID_ALL_IDOL, None, discord.ButtonStyle.secondary),
        ("咲季", 0, constants.ANALYZER_ID_SAKI, get_emoji(1525052785333239829), discord.ButtonStyle.primary),
        ("手毬", 0, constants.ANALYZER_ID_TEMARI, get_emoji(1531255289083334749), discord.ButtonStyle.primary),
        ("ことね", 0, constants.ANALYZER_ID_KOTONE, get_emoji(1529460170609004614), discord.ButtonStyle.primary),
        ("広", 0, constants.ANALYZER_ID_HIRO, get_emoji(1525055654686097569), discord.ButtonStyle.primary),
        ("莉波", 1, constants.ANALYZER_ID_RINAMI, get_emoji(1525055724181524610), discord.ButtonStyle.primary),
        ("美鈴", 1, constants.ANALYZER_ID_MISUZU, get_emoji(1525336748283006996), discord.ButtonStyle.primary),
        ("エアプ全員からランダム", 2, constants.ANALYZER_ID_ALL_AIRPLAY, None, discord.ButtonStyle.secondary),
        ("咲季(エアプ)", 2, constants.ANALYZER_ID_SAKI_AIRPLAY, get_emoji(1525052785333239829), discord.ButtonStyle.primary),
        ("手毬(エアプ)", 2, constants.ANALYZER_ID_TEMARI_AIRPLAY, get_emoji(1531255289083334749), discord.ButtonStyle.primary),
        ("ことね(エアプ)", 2, constants.ANALYZER_ID_KOTONE_AIRPLAY, get_emoji(1529460170609004614), discord.ButtonStyle.primary),
        ("広(エアプ)", 2, constants.ANALYZER_ID_HIRO_AIRPLAY, get_emoji(1525055654686097569), discord.ButtonStyle.primary),
        ("莉波(エアプ)", 3, constants.ANALYZER_ID_RINAMI_AIRPLAY, get_emoji(1525055724181524610), discord.ButtonStyle.primary),
        ("美鈴(エアプ)", 3, constants.ANALYZER_ID_MISUZU_AIRPLAY, get_emoji(1525336748283006996), discord.ButtonStyle.primary),
        ("キャンセル", 4, constants.ANALYZER_ID_CANCELLED, None, discord.ButtonStyle.secondary),
    ]

    # デバッグモード（ローカル起動）の場合のみ，テスト用の解析者を追加
    if os.getenv("DEBUG_MODE") == "1":
        buttons.append(("テスト用", 4, constants.ANALYZER_ID_TEST, None, discord.ButtonStyle.secondary))

    return buttons


# 食事の写真を解析する関数
def analyze_meal_images(images: list[tuple[bytes, str]], text:str, user_name:str, analyzer_id:int) -> str:
    if not images:
        return ""

    # analyzer_idと対応するプロンプトを取得
    # get_prompt_for_analyzer 側でユーザー名を安全に正規化するため、ここでは再正規化しない
    prompt = get_prompt_for_analyzer(analyzer_id, user_name, text)
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


__all__ = [
    "handle_meal_analyze",
    "AnalyzeView",
    "build_analyzer_options",
    "analyze_meal_images",
    "PROMPT_FACTORY_REGISTRY",
]
