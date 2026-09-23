"""Gemini client module providing lazy-initialized singleton LLM interface."""

from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from packages.shared.logging import get_logger
from packages.shared.settings import settings

logger = get_logger(__name__)


class GeminiClient:
    """Lazy-initialized singleton client wrapper for Google Gemini LLM."""

    _instance: Optional["GeminiClient"] = None
    _llm: ChatGoogleGenerativeAI | None = None

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        """Lazy-initialize ChatGoogleGenerativeAI instance."""
        if self._llm is None:
            settings.validate_gemini_config()
            logger.info(
                f"Initializing singleton Gemini client with model: {settings.GEMINI_MODEL}"
            )
            self._llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.2,
            )
        return self._llm

    def reset(self) -> None:
        """Reset the cached LLM instance (useful for testing or config updates)."""
        self._llm = None

    def chat(self, prompt: str) -> str:
        """Send prompt to Gemini model and return text response.

        Args:
            prompt: Input text prompt message.

        Returns:
            str: Generated text answer string from Gemini.

        Raises:
            ValueError: If Gemini API key is not configured or prompt is empty.
            Exception: If Gemini API invocation fails.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Message prompt cannot be empty.")

        llm = self._get_llm()
        logger.info(f"Invoking Gemini model: {settings.GEMINI_MODEL}")
        response = llm.invoke(prompt)

        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(str(part["text"]))
                    elif isinstance(part, str):
                        parts.append(part)
                    elif hasattr(part, "text"):
                        parts.append(str(part.text))
                    else:
                        parts.append(str(part))
                return "".join(parts)
            return str(content)
        return str(response)


# Module-level singleton instance
_client_instance = GeminiClient()


def chat(prompt: str) -> str:
    """Reusable function for chat completion using the singleton Gemini client.

    Args:
        prompt: User message prompt string.

    Returns:
        str: Gemini answer string.
    """
    return _client_instance.chat(prompt)
