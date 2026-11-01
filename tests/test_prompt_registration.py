import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from feature import constants


@pytest.mark.parametrize('debug_mode', [None, '0', '1'])
def test_prompt_registration_on_load(monkeypatch, debug_mode):
    if debug_mode is None:
        monkeypatch.delenv('DEBUG_MODE', raising=False)
    else:
        monkeypatch.setenv('DEBUG_MODE', debug_mode)
    module = runpy.run_path(str(ROOT / 'feature/meal_analyze/make_prompt.py'))
    expected = {}
    for name in ('saki', 'hiro', 'rinami', 'misuzu', 'temari', 'kotone'):
        for suffix, group in (('', 'idol'), ('_airplay', 'airplay')):
            analyzer_id = getattr(constants, f'ANALYZER_ID_{name.upper()}{suffix.upper()}')
            expected[analyzer_id] = (module[f'make_{name}{suffix}_prompt'], group)
    if debug_mode == '1':
        expected[constants.ANALYZER_ID_TEST] = (module['make_test_prompt'], 'idol')
    assert module['PROMPT_FACTORY_REGISTRY'] == expected


def test_decorator_preserves_function_and_rejects_duplicate():
    module = runpy.run_path(str(ROOT / 'feature/meal_analyze/make_prompt.py'))
    register = module['register_prompt']
    registry = module['PROMPT_FACTORY_REGISTRY']

    def factory(user_name: str, message: str) -> str:
        return f'{user_name}:{message}'

    assert register(-1, 'idol')(factory) is factory
    assert registry[-1] == (factory, 'idol')
    assert factory('alice', 'hello') == 'alice:hello'
    with pytest.raises(ValueError, match='Duplicate analyzer ID: -1'):
        register(-1, 'airplay')(lambda user_name, message: 'duplicate')
    assert registry[-1] == (factory, 'idol')
    assert register(-2, 'idol', enabled=False)(factory) is factory
    assert -2 not in registry


@pytest.mark.parametrize('analyzer_id, expected_group', [
    (constants.ANALYZER_ID_ALL_IDOL, 'idol'),
    (constants.ANALYZER_ID_ALL_AIRPLAY, 'airplay'),
    (constants.ANALYZER_ID_SAKI, None),
])
def test_prompt_selection_calls_only_selected_factory(monkeypatch, analyzer_id, expected_group):
    from unittest.mock import Mock

    module = runpy.run_path(str(ROOT / 'feature/meal_analyze/make_prompt.py'))
    registry = module['PROMPT_FACTORY_REGISTRY']
    registry.clear()
    idol = Mock(return_value='idol prompt')
    other_idol = Mock(return_value='other idol prompt')
    airplay = Mock(return_value='airplay prompt')
    registry.update({
        constants.ANALYZER_ID_SAKI: (idol, 'idol'),
        constants.ANALYZER_ID_HIRO: (other_idol, 'idol'),
        constants.ANALYZER_ID_SAKI_AIRPLAY: (airplay, 'airplay'),
    })
    choice = Mock(side_effect=lambda factories: factories[0])
    monkeypatch.setattr(module['random'], 'choice', choice)

    result = module['get_prompt_for_analyzer'](analyzer_id, 'alice\n', 'hello')

    selected = airplay if expected_group == 'airplay' else idol
    assert result == selected.return_value
    selected.assert_called_once_with('alice', 'hello')
    for factory in (idol, other_idol, airplay):
        if factory is not selected:
            factory.assert_not_called()
    if expected_group is None:
        choice.assert_not_called()
    else:
        choice.assert_called_once_with([airplay] if expected_group == 'airplay' else [idol, other_idol])


def test_unknown_analyzer_does_not_select_or_generate_prompt(monkeypatch):
    from unittest.mock import Mock

    module = runpy.run_path(str(ROOT / 'feature/meal_analyze/make_prompt.py'))
    choice = Mock()
    factory = Mock()
    module['PROMPT_FACTORY_REGISTRY'].clear()
    module['PROMPT_FACTORY_REGISTRY'][constants.ANALYZER_ID_SAKI] = (factory, 'idol')
    monkeypatch.setattr(module['random'], 'choice', choice)

    with pytest.raises(ValueError, match='Unknown analyzer ID: -999'):
        module['get_prompt_for_analyzer'](-999, 'alice', 'hello')

    choice.assert_not_called()
    factory.assert_not_called()
