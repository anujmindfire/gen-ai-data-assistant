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
        default="gemini-2.5-flash",
        description="Default Gemini model to use",
    )
    GEMINI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-004",
        description="Google Gemini embedding model to use",
    )
    EMBEDDING_BATCH_SIZE: int = Field(
        default=16,
        description="Maximum number of text chunks per embedding batch API call",
    )

    # Document Chunking settings
    CHUNK_SIZE: int = Field(
        default=500,
        description="Target character size per document text chunk",
    )
    CHUNK_OVERLAP: int = Field(
        default=100,
        description="Character overlap between consecutive chunks",
    )

    @property
    def is_gemini_configured(self) -> bool:
        """Check if GEMINI_API_KEY is configured with a non-empty, non-placeholder value."""
        key = self.GEMINI_API_KEY.strip()
        return bool(key) and key != "your_gemini_api_key_here"

    def validate_gemini_config(self) -> None:
        """Validate Gemini API key configuration.

        Raises:
            ValueError: If GEMINI_API_KEY is missing or invalid.
        """
        if not self.is_gemini_configured:
            raise ValueError(
                "GEMINI_API_KEY is missing or set to placeholder. "
                "Please configure a valid GEMINI_API_KEY in your .env file."
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
    QDRANT_COLLECTION: str = Field(
        default="company_documents",
        description="Qdrant collection name for document vector embeddings",
    )
    QDRANT_VECTOR_SIZE: int = Field(
        default=768,
        description="Dimensionality of vector embeddings (Gemini text-embedding-004 output size)",
    )

    # RAG Retrieval settings
    RAG_TOP_K: int = Field(
        default=5,
        description="Default top-k number of matching chunks to retrieve",
    )
    RAG_SCORE_THRESHOLD: float = Field(
        default=0.5,
        description="Minimum cosine similarity score threshold for retrieved chunks",
    )
    RAG_MAX_CONTEXT_CHARS: int = Field(
        default=4000,
        description="Maximum character limit for retrieved RAG context in LLM prompt",
    )

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL async connection URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_sync_url(self) -> str:
        """Construct PostgreSQL synchronous connection URL for SQLAlchemy inspection."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def qdrant_url(self) -> str:
        """Construct Qdrant connection URL."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


# Shared settings instance
settings = Settings()
