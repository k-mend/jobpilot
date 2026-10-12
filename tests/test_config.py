from app.config import Settings


def test_no_keys_means_no_provider():
    s = Settings(openrouter_api_key=None, gemini_api_key=None, _env_file=None)
    assert s.llm_enabled is False
    assert s.active_provider is None


def test_gemini_only():
    s = Settings(openrouter_api_key=None, gemini_api_key="g-key", _env_file=None)
    assert s.llm_enabled is True
    assert s.active_provider == "gemini"


def test_openrouter_only():
    s = Settings(openrouter_api_key="or-key", gemini_api_key=None, _env_file=None)
    assert s.llm_enabled is True
    assert s.active_provider == "openrouter"


def test_openrouter_takes_priority_over_gemini():
    s = Settings(openrouter_api_key="or-key", gemini_api_key="g-key", _env_file=None)
    assert s.active_provider == "openrouter"
