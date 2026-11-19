from feature import constants
from feature.ai_config.characters import get_character_persona
from feature.meal_analyze.meal_prompt_parts import (
    compose_prompt,
    make_prompt_common_strict,
    make_prompt_image_task,
    make_prompt_visual_identification,
    make_prompt_user_message,
    make_prompt_output_format,
    make_prompt_persona,
)

def make_saki_prompt(user_name: str, message: str) -> str:
    meal_instructions = make_prompt_persona(f"""
        以下の条件を厳守して応答してください.:
        画像に写っている食べ物が「アイドルの食べ物として相応しいかどうか」を厳しめに判定してください。また、食べ物を別の食べ物に置き換える提案はなるべく避け、どのようにアレンジすれば「アイドルの食べ物」として相応しくなるか、簡潔に厳しめに説明してください。
        ・**アイドルの食べ物か**:
        """)
    return _compose_meal_prompt(
        constants.ANALYZER_ID_SAKI, user_name, meal_instructions, message
    )


def _compose_meal_prompt(
    character_id: int | str,
    user_name: str,
    meal_instructions: str,
    message: str,
) -> str:
    """共有キャラクター設定に、食事解析固有の指示を重ねる。"""
    return compose_prompt(
        get_character_persona(character_id, user_name),
        make_prompt_common_strict(),
        make_prompt_image_task(),
        make_prompt_visual_identification(),
        make_prompt_user_message(message),
        make_prompt_output_format(),
        meal_instructions,
    )


# 咲季（エアプ）用
def make_saki_airplay_prompt(user_name: str, message: str) -> str:
    saki_airplay_prompt = f"""
        以下の条件を厳守して応答してください.:
        画像に写っている食べ物が「アイドルの食べ物として相応しいかどうか」を逆張りな基準で判定してください。また、食べ物を無視したうえで、どのように手を加えれば「アイドルの食べ物」として相応しくなるか簡潔に説明してください。
        ・**アイドルの食べ物か**:
        """
    meal_instructions = make_prompt_persona(saki_airplay_prompt)
    return _compose_meal_prompt(
        constants.ANALYZER_ID_SAKI_AIRPLAY, user_name, meal_instructions, message
    )


# 広用
def make_hiro_prompt(user_name: str, message: str) -> str:
    hiro_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_HIRO, user_name, hiro_prompt, message)


# 広(エアプ)用
def make_hiro_airplay_prompt(user_name: str, message: str) -> str:
    hiro_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_HIRO_AIRPLAY, user_name, hiro_prompt, message)


# 莉波用
def make_rinami_prompt(user_name: str, message: str) -> str:
    rinami_prompt = f"""
        以下の条件を厳守して応答してください.：
        """

    return _compose_meal_prompt(constants.ANALYZER_ID_RINAMI, user_name, rinami_prompt, message)


# 莉波(エアプ)用
def make_rinami_airplay_prompt(user_name: str, message: str) -> str:
    rinami_prompt = f"""
        以下の条件を厳守して応答してください.：
        """

    return _compose_meal_prompt(constants.ANALYZER_ID_RINAMI_AIRPLAY, user_name, rinami_prompt, message)


# 美鈴用
def make_misuzu_prompt(user_name: str, message: str) -> str:
    misuzu_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_MISUZU, user_name, misuzu_prompt, message)


# 美鈴(エアプ)用
def make_misuzu_airplay_prompt(user_name: str, message: str) -> str:
    misuzu_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_MISUZU_AIRPLAY, user_name, misuzu_prompt, message)


# 千奈用
def make_china_prompt(user_name: str, message: str) -> str:
    china_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt("china", user_name, china_prompt, message)


# 手毬用
def make_temari_prompt(user_name: str, message: str) -> str:
    temari_prompt = f"""
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_TEMARI, user_name, temari_prompt, message)


# 手毬(エアプ)用
def make_temari_airplay_prompt(user_name: str, message: str) -> str:
    temari_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_TEMARI_AIRPLAY, user_name, temari_prompt, message)


# ことね用
def make_kotone_prompt(user_name: str, message: str) -> str:
    kotone_prompt = f"""
        送られた写真に何が写っていようと、それが何円するのかを無理にでも計算してください。
        ・**推定価格**:
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_KOTONE, user_name, kotone_prompt, message)


# ことね(エアプ)用
def make_kotone_airplay_prompt(user_name: str, message: str) -> str:
    kotone_prompt = f"""
        以下の条件を厳守して応答してください.：
        応答の中で推定価格を発表してください。ただし、送られた画像は完全に無視して適当な金額にしてください。極端に高くなったり、逆に安くても問題ありません。
        ・**推定価格**:
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_KOTONE_AIRPLAY, user_name, kotone_prompt, message)


def make_test_prompt(user_name: str, message: str) -> str:
    test_prompt = f"""
        以下の条件を厳守して応答してください.：
        """
    return _compose_meal_prompt(constants.ANALYZER_ID_TEST, user_name, test_prompt, message)

