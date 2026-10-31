import asyncio
from typing import Callable, Optional

import config as cfg
import discord

from feature import constants
from feature import gemini
from feature.meal_analyze.analyze_view import AnalyzeView
from feature.meal_analyze.make_prompt import (
    ANALYZER_BUTTON_REGISTRY,
    PROMPT_FACTORY_REGISTRY,
    AnalyzerButton,
    get_prompt_for_analyzer,
)


# 食事解析
async def handle_meal_analyze(message, get_emoji):
    user_message = message.content
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
                    user_message,
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


def build_analyzer_options(get_emoji: Callable[[int], Optional[discord.Emoji]]) -> list[tuple[str, int, int, Optional[discord.Emoji], discord.ButtonStyle]]:
    """登録済みの表示情報から、表示順にDiscord用のボタン設定を作る。"""
    # プロンプトを持たない操作ボタンは表示側で定義する。
    # 各分析者とテスト用ボタンの表示情報は、プロンプトのデコレータで登録する。
    button_definitions = {
        constants.ANALYZER_ID_ALL_IDOL: AnalyzerButton(
            "アイドル全員からランダム", row=0, order=0, primary=False,
        ),
        constants.ANALYZER_ID_ALL_AIRPLAY: AnalyzerButton(
            "エアプ全員からランダム", row=2, order=7, primary=False,
        ),
        constants.ANALYZER_ID_CANCELLED: AnalyzerButton(
            "キャンセル", row=4, order=14, primary=False,
        ),
        **ANALYZER_BUTTON_REGISTRY,
    }
    # 関数の定義順に依存せずorderで並べ、表示時に絵文字と色を解決する。
    # 戻り値の各要素は（表示名、行番号、分析者ID、絵文字、ボタン色）。
    return [
        (
            button.label,
            button.row,
            analyzer_id,
            get_emoji(button.emoji_id) if button.emoji_id is not None else None,
            discord.ButtonStyle.primary if button.primary else discord.ButtonStyle.secondary,
        )
        for analyzer_id, button in sorted(
            button_definitions.items(), key=lambda item: item[1].order,
        )
    ]


# 食事の写真を解析する関数
def analyze_meal_images(images: list[tuple[bytes, str]], message:str, user_name:str, analyzer_id:int) -> str:
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


__all__ = [
    "handle_meal_analyze",
    "AnalyzeView",
    "build_analyzer_options",
    "analyze_meal_images",
    "PROMPT_FACTORY_REGISTRY",
]
