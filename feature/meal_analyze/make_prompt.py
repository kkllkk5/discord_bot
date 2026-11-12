"""食事解析プロンプトの登録・選択を行う公開モジュール。"""

import os
import random
from dataclasses import dataclass
from typing import Callable

from feature import constants
from feature.meal_analyze import prompt_characters as characters
from feature.meal_analyze.prompt_common import (
    compose_prompt,
    make_prompt_common_strict,
    make_prompt_meal_analysis,
    make_prompt_output_format,
    make_prompt_persona,
    make_prompt_user_message,
    make_prompt_visual_identification,
    sanitize_user_name,
)

PromptFactory = Callable[[str, str], str]


@dataclass(frozen=True)
class AnalyzerButton:
    """解析者ボタンの表示情報。配置はanalyzer_options.pyで管理する。"""

    label: str
    emoji_id: int | None = None
    primary: bool = True


ANALYZER_BUTTON_REGISTRY: dict[int, AnalyzerButton] = {}
PROMPT_FACTORY_REGISTRY: dict[int, tuple[PromptFactory, str]] = {}


def register_prompt(
    analyzer_id: int,
    group: str,
    *,
    button: AnalyzerButton | None = None,
    enabled: bool = True,
) -> Callable[[PromptFactory], PromptFactory]:
    """関数定義時にプロンプトとボタン情報を登録するデコレータ。"""
    def decorator(prompt_factory: PromptFactory) -> PromptFactory:
        if not enabled:
            return prompt_factory
        if analyzer_id in PROMPT_FACTORY_REGISTRY:
            raise ValueError(f"Duplicate analyzer ID: {analyzer_id}")
        PROMPT_FACTORY_REGISTRY[analyzer_id] = (prompt_factory, group)
        if button is not None:
            ANALYZER_BUTTON_REGISTRY[analyzer_id] = button
        return prompt_factory

    return decorator


def register_prompt_factory(
    analyzer_id: int, prompt_factory: PromptFactory, group: str
) -> None:
    """既存利用との互換用の直接登録。"""
    PROMPT_FACTORY_REGISTRY[analyzer_id] = (prompt_factory, group)


def get_prompt_factories_for_group(group: str) -> list[PromptFactory]:
    return [
        factory
        for factory, registered_group in PROMPT_FACTORY_REGISTRY.values()
        if registered_group == group
    ]


def get_prompt_for_analyzer(analyzer_id: int, user_name: str, message: str = "") -> str:
    """登録済み解析者、または指定されたランダムグループからプロンプトを作る。"""
    safe_user_name = sanitize_user_name(user_name)
    entry = PROMPT_FACTORY_REGISTRY.get(analyzer_id)
    if entry is not None:
        factory, _ = entry
        return factory(safe_user_name, message)

    random_group = {
        constants.ANALYZER_ID_ALL_IDOL: "idol",
        constants.ANALYZER_ID_ALL_AIRPLAY: "airplay",
    }.get(analyzer_id)
    if random_group is None:
        raise ValueError(f"Unknown analyzer ID: {analyzer_id}")

    return random.choice(get_prompt_factories_for_group(random_group))(
        safe_user_name, message
    )


def make_prompt_common_output(user_message: str) -> str:
    """互換用に食事タスクとユーザー追加メッセージをまとめる。"""
    return compose_prompt(
        make_prompt_meal_analysis(),
        make_prompt_user_message(user_message),
    )


# キャラクターのプロンプト関数は別モジュールで定義し、ここでIDと表示情報を登録する。
@register_prompt(
    constants.ANALYZER_ID_SAKI, "idol",
    button=AnalyzerButton("咲季", emoji_id=1525052785333239829),
)
def make_saki_prompt(user_name: str, message: str) -> str:
    return characters.make_saki_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_SAKI_AIRPLAY, "airplay",
    button=AnalyzerButton("咲季(エアプ)", emoji_id=1525052785333239829),
)
def make_saki_airplay_prompt(user_name: str, message: str) -> str:
    return characters.make_saki_airplay_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_HIRO, "idol",
    button=AnalyzerButton("広", emoji_id=1525055654686097569),
)
def make_hiro_prompt(user_name: str, message: str) -> str:
    return characters.make_hiro_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_HIRO_AIRPLAY, "airplay",
    button=AnalyzerButton("広(エアプ)", emoji_id=1525055654686097569),
)
def make_hiro_airplay_prompt(user_name: str, message: str) -> str:
    return characters.make_hiro_airplay_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_RINAMI, "idol",
    button=AnalyzerButton("莉波", emoji_id=1525055724181524610),
)
def make_rinami_prompt(user_name: str, message: str) -> str:
    return characters.make_rinami_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_RINAMI_AIRPLAY, "airplay",
    button=AnalyzerButton("莉波(エアプ)", emoji_id=1525055724181524610),
)
def make_rinami_airplay_prompt(user_name: str, message: str) -> str:
    return characters.make_rinami_airplay_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_MISUZU, "idol",
    button=AnalyzerButton("美鈴", emoji_id=1525336748283006996),
)
def make_misuzu_prompt(user_name: str, message: str) -> str:
    return characters.make_misuzu_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_MISUZU_AIRPLAY, "airplay",
    button=AnalyzerButton("美鈴(エアプ)", emoji_id=1525336748283006996),
)
def make_misuzu_airplay_prompt(user_name: str, message: str) -> str:
    return characters.make_misuzu_airplay_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_TEMARI, "idol",
    button=AnalyzerButton("手毬", emoji_id=1531255289083334749),
)
def make_temari_prompt(user_name: str, message: str) -> str:
    return characters.make_temari_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_TEMARI_AIRPLAY, "airplay",
    button=AnalyzerButton("手毬(エアプ)", emoji_id=1531255289083334749),
)
def make_temari_airplay_prompt(user_name: str, message: str) -> str:
    return characters.make_temari_airplay_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_KOTONE, "idol",
    button=AnalyzerButton("ことね", emoji_id=1529460170609004614),
)
def make_kotone_prompt(user_name: str, message: str) -> str:
    return characters.make_kotone_prompt(user_name, message)


@register_prompt(
    constants.ANALYZER_ID_KOTONE_AIRPLAY, "airplay",
    button=AnalyzerButton("ことね(エアプ)", emoji_id=1529460170609004614),
)
def make_kotone_airplay_prompt(user_name: str, message: str) -> str:
    return characters.make_kotone_airplay_prompt(user_name, message)


if os.getenv("DEBUG_MODE") == "1":
    @register_prompt(
        constants.ANALYZER_ID_TEST, "idol",
        button=AnalyzerButton("テスト用", primary=False),
    )
    def make_test_prompt(user_name: str, message: str) -> str:
        return characters.make_test_prompt(user_name, message)


# 千奈用は登録せず、必要な場合に直接呼び出せるよう公開する。
make_china_prompt = characters.make_china_prompt

__all__ = [
    "PromptFactory", "AnalyzerButton", "ANALYZER_BUTTON_REGISTRY",
    "PROMPT_FACTORY_REGISTRY", "sanitize_user_name", "register_prompt",
    "register_prompt_factory", "get_prompt_factories_for_group",
    "get_prompt_for_analyzer", "make_prompt_common_strict",
    "make_prompt_common_output", "make_prompt_meal_analysis",
    "make_prompt_user_message", "make_prompt_persona",
    "make_prompt_output_format", "make_prompt_visual_identification",
    "compose_prompt", "make_saki_prompt", "make_saki_airplay_prompt",
    "make_hiro_prompt", "make_hiro_airplay_prompt", "make_rinami_prompt",
    "make_rinami_airplay_prompt", "make_misuzu_prompt",
    "make_misuzu_airplay_prompt", "make_china_prompt", "make_temari_prompt",
    "make_temari_airplay_prompt", "make_kotone_prompt",
    "make_kotone_airplay_prompt",
    # make_test_prompt は DEBUG_MODE=1 のときだけ定義・登録するため公開一覧には含めない。
]
