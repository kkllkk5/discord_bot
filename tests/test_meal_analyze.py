import importlib.util
import sys
import types
import os


def _make_dummy_discord():
    discord = types.SimpleNamespace()
    ui = types.SimpleNamespace()

    class View:
        def __init__(self, timeout=None):
            pass

    class Button:
        pass

    class ButtonStyle:
        primary = 1
        secondary = 2
        success = 3

    class Emoji:
        pass

    class Message:
        pass

    ui.View = View
    ui.Button = Button
    ui.ButtonStyle = ButtonStyle
    discord.ui = ui
    discord.Emoji = Emoji
    discord.Message = Message
    # some code references discord.ButtonStyle at module level
    discord.ButtonStyle = ButtonStyle
    return discord


def _make_dummy_google_genai_types():
    genai = types.SimpleNamespace()

    class Types:
        class Part:
            @staticmethod
            def from_bytes(data, mime_type):
                return (data, mime_type)

        class GenerateContentConfig:
            def __init__(self, **kwargs):
                pass

        class ThinkingConfig:
            def __init__(self, **kwargs):
                pass

    genai.types = Types
    return genai


def import_meal_analyze():
    # inject minimal stub modules so importing the target module succeeds
    sys.modules.setdefault('discord', _make_dummy_discord())
    google = types.ModuleType('google')
    genai = _make_dummy_google_genai_types()

    google.genai = genai

    # ensure 'feature' package exists so relative imports inside feature/* work
    if 'feature' not in sys.modules:
        feature_pkg = types.ModuleType('feature')
        feature_pkg.__path__ = [os.path.join(os.getcwd(), 'feature')]
        sys.modules['feature'] = feature_pkg

    spec = importlib.util.spec_from_file_location(
        'feature.meal_analyze', os.path.join('feature', 'meal_analyze.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules['feature.meal_analyze'] = module
    sys.modules['google'] = google
    sys.modules['google.genai'] = genai
    spec.loader.exec_module(module)
    return module

# テスト1:prompt_factoryへの登録テスト
def test_register_and_get_prompt_factories_for_group():
    ma = import_meal_analyze()

    # clear registry
    ma.PROMPT_FACTORY_REGISTRY.clear()

    def pf_a(name):
        return f"A:{name}"

    def pf_b(name):
        return f"B:{name}"

    ma.register_prompt_factory(1000, pf_a, 'group1')
    ma.register_prompt_factory(1001, pf_b, 'group2')

    g1 = ma.get_prompt_factories_for_group('group1')
    g2 = ma.get_prompt_factories_for_group('group2')

    assert callable(g1[0]) and g1[0]('u') == 'A:u'
    assert callable(g2[0]) and g2[0]('u') == 'B:u'

# テスト2:無効なanalyzer_idが指定された場合に、idolグループのprompt_factoryが返ることを確認するテスト
def test_get_prompt_for_analyzer_invalid_id_falls_back():
    ma = import_meal_analyze()
    ma.PROMPT_FACTORY_REGISTRY.clear()

    def p1(name):
        return f"P1:{name}"

    ma.register_prompt_factory(2000, p1, 'idol')

    # invalid analyzer id should pick from 'idol' group
    prompt = ma.get_prompt_for_analyzer(9999, 'tester')
    assert prompt.startswith('P1:')

# テスト3:analyze_meal_imagesの空配列入力
def test_analyze_meal_images_empty():
    ma = import_meal_analyze()
    res = ma.analyze_meal_images([], 'user', 0)
    assert res == ''
