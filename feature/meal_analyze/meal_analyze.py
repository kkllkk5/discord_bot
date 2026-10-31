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
    control_message = None
    # 食事解析の処理境界でログと失敗通知を担当する。
    # タスクのキャンセル（CancelledError）は捕捉せず呼び出し元へ伝える。
    try:
        images = await _read_meal_images(message.attachments)
        if not images:
            cfg.logger.info("画像が見つかりませんでした.")
            return

        control_message, view = await _request_analyzer_selection(message, get_emoji)
        await view.event.wait()
        analyzer_id = view.result
        # 選択結果がない場合とキャンセル時は解析を行わない。
        if analyzer_id is None or analyzer_id == constants.ANALYZER_ID_CANCELLED:
            return

        await _analyze_and_reply(message, images, analyzer_id)
    except Exception:
        cfg.logger.exception("食事解析の処理に失敗しました")
        await _notify_meal_analyze_failure(message)
    finally:
        if control_message is not None:
            await _delete_control_message(control_message)


async def _read_meal_images(attachments) -> list[tuple[bytes, str]]:
    """添付ファイルから画像だけを読み込む。"""
    images = []
    for attachment in attachments:
        if not attachment.content_type or not attachment.content_type.startswith("image"):
            continue
        cfg.logger.info("画像を受け取りました")
        image_bytes = await attachment.read()
        images.append((image_bytes, attachment.content_type))
    return images


async def _request_analyzer_selection(message, get_emoji):
    """選択ボタンを送信し、後始末用のメッセージと選択待ち用のViewを返す。"""
    analyzer_options = build_analyzer_options(get_emoji)
    view = AnalyzeView(owner_id=message.author.id, IDOLS=analyzer_options)
    control_message = await message.reply(
        f"{message.author.mention} 誰に分析してもらう？",
        view=view,
    )
    # 待機前に呼び出し元へ渡し、待機中のキャンセルでも削除できるようにする。
    return control_message, view


async def _analyze_and_reply(message, images: list[tuple[bytes, str]], analyzer_id: int):
    """同時実行数を制限して解析し、結果があれば返信する。"""
    async with cfg.meal_analyze_semaphore:
        response_text = await asyncio.to_thread(
            analyze_meal_images,
            images,
            message.content,
            message.author.display_name,
            analyzer_id,
        )
    if response_text is None or response_text == "":
        return
    await message.reply(response_text)


async def _notify_meal_analyze_failure(message):
    """解析失敗を通知し、通知自体の失敗はログに残す。"""
    try:
        await message.reply("食事の解析に失敗しました。時間をおいてもう一度試してください。")
    except Exception:
        cfg.logger.exception("食事解析の失敗通知を送信できませんでした")


async def _delete_control_message(control_message):
    """操作メッセージを削除し、失敗しても元の例外やキャンセルを保つ。"""
    try:
        await control_message.delete()
    except Exception:
        cfg.logger.exception("食事解析の操作メッセージを削除できませんでした")


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
