"""Google Gemini LLM client configuration using LangChain Google GenAI integration."""

import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


def get_gemini_client(
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> ChatGoogleGenerativeAI:
    """Initialize and return a ChatGoogleGenerativeAI client instance.

    Reads GEMINI_API_KEY from environment configuration.

    Args:
        model_name: Optional model override. Defaults to settings.GEMINI_MODEL.
        temperature: Sampling temperature for generation.

    Returns:
        ChatGoogleGenerativeAI: Configured LangChain Gemini client.

    Raises:
        ValueError: If GEMINI_API_KEY environment variable is not configured.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("GEMINI_API_KEY is missing or set to placeholder value.")
        raise ValueError(
            "GEMINI_API_KEY is not set. Please configure GEMINI_API_KEY in .env file."
        )

    model = model_name or settings.GEMINI_MODEL
    logger.info(f"Initializing Gemini LLM client with model: {model}")

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
    )


def smoke_test_gemini() -> bool:
    """Perform a dry-run check of the Gemini client configuration.

    Validates that the API key is present without making an active external API call.

    Returns:
        bool: True if configuration is valid.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.error("Gemini smoke-test failed: GEMINI_API_KEY is missing.")
        return False
    logger.info("Gemini smoke-test passed: API key is configured.")
    return True
