"""Botへのメンションを受け付け、分析者選択UIを介してチャット応答する。"""

import asyncio
import discord

import config as cfg
from feature import constants
from feature.meal_analyze.meal_analyze import request_analyzer_selection
from .analysis import analyze_chat_message


async def handle_chat_mention(
    message: discord.Message,
    get_emoji: Callable[[int], discord.Emoji | None],
) -> None:
    """メンションを受け、キャラ選択から返信までのDiscord処理を調整する。"""
    control_message = None
    try:
        # 既存の食事解析と同じ選択肢・Viewを使い、UIとチャット処理を共通化する。
        control_message, view = await request_analyzer_selection(message, get_emoji)

        # ボタン選択またはViewのタイムアウトまで待機する。
        await view.event.wait()
        analyzer_id = view.result

        # キャンセルまたはタイムアウトならGeminiを呼ばずに終了する。
        if analyzer_id is None or analyzer_id == constants.ANALYZER_ID_CANCELLED:
            return

        # 同時実行枠を食事解析と共有し、同期的なGemini SDK呼び出しは別スレッドで行う。
        response = await _generate_response(message, analyzer_id)
        if response:
            await message.reply(response)
    except Exception:
        # 失敗通知の送信失敗も個別に記録し、元の処理例外を隠さない。
        cfg.logger.exception("チャット返信の処理に失敗しました")
        await _notify_failure(message)
    finally:
        if control_message is not None:
            await _delete_control_message(control_message)


async def _generate_response(message: discord.Message, analyzer_id: int) -> str:
    """共有セマフォを取得し、チャット解析をワーカースレッドで実行する。"""
    async with cfg.ai_semaphore:
        return await asyncio.to_thread(
            analyze_chat_message,
            message.content,
            message.author.display_name,
            analyzer_id,
        )


async def _notify_failure(message: discord.Message) -> None:
    """チャット失敗を利用者へ通知する。通知に失敗した場合はログへ残す。"""
    try:
        await message.reply("返信の生成に失敗しました。時間をおいてもう一度試してください。")
    except Exception:
        cfg.logger.exception("チャット返信の失敗通知を送信できませんでした")


async def _delete_control_message(control_message: discord.Message) -> None:
    """選択UIを削除し、削除失敗はログに記録する。"""
    try:
        await control_message.delete()
    except Exception:
        cfg.logger.exception("チャット返信の操作メッセージを削除できませんでした")


__all__ = ["handle_chat_mention"]
