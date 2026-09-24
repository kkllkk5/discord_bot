from . import meal_analyze as _meal_analyze_module
from . import make_prompt as _make_prompt_module

# Re-export the legacy package API expected by existing imports/tests.
for _name in [
    "PROMPT_FACTORY_REGISTRY",
    "sanitize_user_name",
    "register_prompt_factory",
    "get_prompt_factories_for_group",
    "get_prompt_for_analyzer",
    "handle_meal_analyze",
    "AnalyzeView",
    "build_analyzer_options",
    "analyze_meal_images",
    "gemini",
    "constants",
    "discord",
    "asyncio",
    "os",
    "re",
    "random",
    "Callable",
    "Optional",
]:
    if hasattr(_make_prompt_module, _name):
        globals()[_name] = getattr(_make_prompt_module, _name)
    if hasattr(_meal_analyze_module, _name):
        globals()[_name] = getattr(_meal_analyze_module, _name)

# Keep the concrete module objects available too.
gemini = _meal_analyze_module.gemini
constants = _meal_analyze_module.constants
discord = _meal_analyze_module.discord

__all__ = [
    "PROMPT_FACTORY_REGISTRY",
    "sanitize_user_name",
    "register_prompt_factory",
    "get_prompt_factories_for_group",
    "get_prompt_for_analyzer",
    "handle_meal_analyze",
    "AnalyzeView",
    "build_analyzer_options",
    "analyze_meal_images",
    "gemini",
    "constants",
    "discord",
]
