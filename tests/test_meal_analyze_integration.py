import asyncio
import importlib
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from feature import constants


def _install_python_stubs():
    discord_module = types.ModuleType('discord')
    ui_module = types.ModuleType('discord.ui')

    class View:
        def __init__(self, timeout=None):
            self.timeout = timeout
            self.children = []

        def add_item(self, item):
            self.children.append(item)

        def stop(self):
            pass

    class Button:
        def __init__(self, label=None, emoji=None, style=None, row=None):
            self.label = label
            self.emoji = emoji
            self.style = style
            self.row = row
            self.disabled = False
            self.callback = None

    class ButtonStyle:
        primary = 1
        secondary = 2
        success = 3

    class Emoji:
        pass

    class Message:
        pass

    ui_module.View = View
    ui_module.Button = Button
    ui_module.ButtonStyle = ButtonStyle
    discord_module.ui = ui_module
    discord_module.Emoji = Emoji
    discord_module.Message = Message
    discord_module.ButtonStyle = ButtonStyle
    sys.modules['discord'] = discord_module
    sys.modules['discord.ui'] = ui_module

    google_module = types.ModuleType('google')
    genai_module = types.ModuleType('google.genai')

    class Types:
        class Part:
            @staticmethod
            def from_bytes(data, mime_type):
                return (data, mime_type)

        class GenerateContentConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class ThinkingConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

    genai_module.types = Types
    google_module.genai = genai_module
    sys.modules['google'] = google_module
    sys.modules['google.genai'] = genai_module


_install_python_stubs()
ma = importlib.import_module('feature.meal_analyze')

# 解析メソッドの中で，geminiに送るパラメータが正当なこと
def test_meal_analyze_integration_flow(monkeypatch):
    ma.PROMPT_FACTORY_REGISTRY.clear()

    def prompt_factory(user_name: str) -> str:
        return f"prompt:{user_name}"

    ma.register_prompt_factory(constants.ANALYZER_ID_SAKI, prompt_factory, 'idol')

    def fake_analyze_with_gemini(contents, config):
        assert contents[0] == 'prompt:alice'
        assert contents[1] == (b'abc123', 'image/png')
        assert config.kwargs['response_mime_type'] == 'text/plain'
        return '解析結果:OK'

    monkeypatch.setattr(ma.gemini, 'analyze_with_gemini', fake_analyze_with_gemini)

    result = ma.analyze_meal_images([(b'abc123', 'image/png')], 'alice', constants.ANALYZER_ID_SAKI)
    assert result == '解析結果:OK'

# アナライザービューのボタンフローをテスト
def test_analyzer_view_button_flow():
    class DummyUser:
        id = 42

    class DummyResponse:
        async def edit_message(self, **kwargs):
            return None

    class DummyInteraction:
        def __init__(self):
            self.user = DummyUser()
            self.response = DummyResponse()

    view = ma.AnalyzeView(owner_id=42, IDOLS=[('テスト', 0, 123, None, ma.discord.ButtonStyle.primary)])
    assert len(view.children) == 1

    button = view.children[0]
    assert button.label == 'テスト'

    asyncio.run(button.callback(DummyInteraction()))

    assert view.result == 123
    assert button.style == ma.discord.ButtonStyle.success
    assert all(item.disabled for item in view.children)
