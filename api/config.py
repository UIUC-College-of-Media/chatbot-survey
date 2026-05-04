from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "persuasive_ai_study"
    allowed_origins_raw: str = Field(default="*", alias="ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins_raw.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def _validate_production_requirements(self) -> "Settings":
        if self.app_env != "production":
            return self

        missing_fields = []
        for field_name in (
            "mongodb_url",
            "database_name",
        ):
            if not getattr(self, field_name, "").strip():
                missing_fields.append(field_name.upper())

        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(f"Missing required production settings: {missing}")

        if not self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS must not be empty")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
