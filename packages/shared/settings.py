"""Configuration settings module using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and environment settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = Field(default="GenAI Data Assistant API")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)

    # Gemini API settings
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key required for LLM operations",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Default Gemini model to use",
    )

    # PostgreSQL Database settings
    POSTGRES_HOST: str = Field(default="postgres")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="assistant")
    POSTGRES_USER: str = Field(default="genai")
    POSTGRES_PASSWORD: str = Field(default="genai")

    # Qdrant Vector DB settings
    QDRANT_HOST: str = Field(default="qdrant")
    QDRANT_PORT: int = Field(default=6333)

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def qdrant_url(self) -> str:
        """Construct Qdrant connection URL."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


# Shared settings instance
settings = Settings()
