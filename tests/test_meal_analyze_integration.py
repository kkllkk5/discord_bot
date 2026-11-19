import asyncio
import importlib
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _install_dependency_stubs():
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
            def from_bytes(data, mime_type, media_resolution=None, **kwargs):
                return (data, mime_type)

        class GenerateContentConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                for key, value in kwargs.items():
                    setattr(self, key, value)

    genai_module.types = Types
    google_module.genai = genai_module
    sys.modules['google'] = google_module
    sys.modules['google.genai'] = genai_module

    feature_pkg = sys.modules.setdefault('feature', types.ModuleType('feature'))
    feature_pkg.__path__ = [os.path.join(ROOT, 'feature')]

    gemini_stub = types.ModuleType('feature.gemini')
    gemini_stub.types = Types
    gemini_stub.analyze_with_gemini = lambda contents, config: 'OK'
    sys.modules['feature.gemini'] = gemini_stub


_install_dependency_stubs()
ma = importlib.import_module('feature.meal_analyze')
from feature import constants


def test_meal_analyze_integration_flow(monkeypatch):
    ma.PROMPT_FACTORY_REGISTRY.clear()

    def prompt_factory(user_name: str,text: str) -> str:
        return f'prompt:{user_name}:{text}'

    ma.register_prompt_factory(constants.ANALYZER_ID_SAKI, prompt_factory, 'idol')

    def fake_analyze_with_gemini(contents, config):
        assert contents[0] == 'prompt:alice:hello'
        assert contents[1] == (b'abc123', 'image/png')
        assert config.kwargs['response_mime_type'] == 'text/plain'
        return '解析結果:OK'

    monkeypatch.setattr(ma.gemini, 'analyze_with_gemini', fake_analyze_with_gemini)

    result = ma.analyze_meal_images([(b'abc123', 'image/png')], 'hello', 'alice', constants.ANALYZER_ID_SAKI)
    assert result == '解析結果:OK'


def test_chat_analysis_passes_images_without_changing_prompt(monkeypatch):
    from feature import gemini
    from feature.chat import analysis as chat_analysis

    expected_prompt = 'existing chat prompt'
    monkeypatch.setattr(
        chat_analysis,
        'compose_character_chat_prompt',
        lambda analyzer_id, user_name, task: expected_prompt,
    )
    captured = {}

    def fake_analyze_with_gemini(contents, config):
        captured['contents'] = contents
        captured['config'] = config
        return 'chat reply'

    monkeypatch.setattr(gemini, 'analyze_with_gemini', fake_analyze_with_gemini)

    result = chat_analysis.analyze_chat_message(
        'hello', 'alice', constants.ANALYZER_ID_SAKI, [(b'photo', 'image/png')]
    )

    assert result == 'chat reply'
    assert captured['contents'] == [expected_prompt, (b'photo', 'image/png')]
    assert captured['config'].kwargs['response_mime_type'] == 'text/plain'


def test_chat_handler_reads_only_image_attachments():
    from feature.chat.handler import _read_chat_images

    class DummyAttachment:
        def __init__(self, content_type, data):
            self.content_type = content_type
            self.data = data

        async def read(self):
            return self.data

    attachments = [
        DummyAttachment('image/jpeg', b'photo'),
        DummyAttachment('text/plain', b'text'),
        DummyAttachment(None, b'unknown'),
    ]

    result = asyncio.run(_read_chat_images(attachments))

    assert result == [(b'photo', 'image/jpeg')]


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
