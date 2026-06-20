from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


class LLMConfigDocument(Document):
    """Stores LLM provider configuration. Singleton — only one document expected."""

    llm_model_endpoint: str
    llm_model_api_key: str
    llm_model_deployment: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "llm_config"
