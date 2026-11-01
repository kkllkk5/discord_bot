"""Discordでの食事解析の受付・返信・例外処理。"""

import asyncio

import config as cfg

from feature import constants
from .analysis import analyze_meal_images
from .analyzer_options import build_analyzer_options
from .analyze_view import AnalyzeView
from .make_prompt import PROMPT_FACTORY_REGISTRY


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


__all__ = [
    "handle_meal_analyze",
    "AnalyzeView",
    "build_analyzer_options",
    "analyze_meal_images",
    "PROMPT_FACTORY_REGISTRY",
]
