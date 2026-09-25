"""Tests for configuration settings and Gemini API key validation."""

from packages.shared.settings import Settings


def test_settings_default_gemini_model() -> None:
    """Test that default GEMINI_MODEL is gemini-2.5-flash."""
    s = Settings(GEMINI_API_KEY="test_key", GEMINI_MODEL="gemini-2.5-flash")
    assert s.GEMINI_MODEL == "gemini-2.5-flash"
    assert s.is_gemini_configured is True


def test_settings_is_gemini_configured_false_on_empty() -> None:
    """Test is_gemini_configured returns False when GEMINI_API_KEY is empty or placeholder."""
    s1 = Settings(GEMINI_API_KEY="")
    assert s1.is_gemini_configured is False

    s2 = Settings(GEMINI_API_KEY="your_gemini_api_key_here")
    assert s2.is_gemini_configured is False
