"""Configuration and third-party client initialization module."""

from .gemini import get_gemini_client, smoke_test_gemini

__all__ = ["get_gemini_client", "smoke_test_gemini"]
