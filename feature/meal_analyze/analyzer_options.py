"""分析者選択ボタンの配置とDiscord用の表示設定。"""

from typing import Callable, Optional

import discord

from feature import constants
from .make_prompt import ANALYZER_BUTTON_REGISTRY, AnalyzerButton


# ボタン配置はここだけで管理する。キーは0始まりの行番号、各行のIDは左から順。
# 移動はIDの並べ替え・行間の移動で行う。未登録の分析者（通常時のテスト用など）は表示しない。
ANALYZER_BUTTON_LAYOUT: dict[int, tuple[int, ...]] = {
    0: (
        constants.ANALYZER_ID_ALL_IDOL,
        constants.ANALYZER_ID_SAKI,
        constants.ANALYZER_ID_TEMARI,
        constants.ANALYZER_ID_KOTONE,
        constants.ANALYZER_ID_HIRO,
    ),
    1: (
        constants.ANALYZER_ID_RINAMI,
        constants.ANALYZER_ID_MISUZU,
    ),
    2: (
        constants.ANALYZER_ID_ALL_AIRPLAY,
        constants.ANALYZER_ID_SAKI_AIRPLAY,
        constants.ANALYZER_ID_TEMARI_AIRPLAY,
        constants.ANALYZER_ID_KOTONE_AIRPLAY,
        constants.ANALYZER_ID_HIRO_AIRPLAY,
    ),
    3: (
        constants.ANALYZER_ID_RINAMI_AIRPLAY,
        constants.ANALYZER_ID_MISUZU_AIRPLAY,
    ),
    4: (
        constants.ANALYZER_ID_CANCELLED,
        constants.ANALYZER_ID_TEST,
    ),
}


def build_analyzer_options(get_emoji: Callable[[int], Optional[discord.Emoji]]) -> list[tuple[str, int, int, Optional[discord.Emoji], discord.ButtonStyle]]:
    """配置マップと登録済みの表示情報からDiscord用のボタン設定を作る。"""
    # プロンプトを持たない操作ボタンは表示側で定義する。
    # 各分析者とテスト用ボタンの表示情報は、プロンプトのデコレータで登録する。
    button_definitions = {
        constants.ANALYZER_ID_ALL_IDOL: AnalyzerButton(
            "アイドル全員からランダム", primary=False,
        ),
        constants.ANALYZER_ID_ALL_AIRPLAY: AnalyzerButton(
            "エアプ全員からランダム", primary=False,
        ),
        constants.ANALYZER_ID_CANCELLED: AnalyzerButton(
            "キャンセル", primary=False,
        ),
        **ANALYZER_BUTTON_REGISTRY,
    }
    # 配置マップの行番号とIDの並びに従い、表示時に絵文字と色を解決する。
    # 戻り値の各要素は（表示名、行番号、分析者ID、絵文字、ボタン色）。
    buttons = []
    for row, analyzer_ids in sorted(ANALYZER_BUTTON_LAYOUT.items()):
        for analyzer_id in analyzer_ids:
            button = button_definitions.get(analyzer_id)
            if button is None:
                continue
            buttons.append((
                button.label,
                row,
                analyzer_id,
                get_emoji(button.emoji_id) if button.emoji_id is not None else None,
                discord.ButtonStyle.primary if button.primary else discord.ButtonStyle.secondary,
            ))
    return buttons
