from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# OpenAI model used for every CV generation, invention, and memory-extraction call.
MODEL = "gpt-5.4-mini-2026-03-17"

# ---- Cost-guard limits (free tier) ----
MAX_SESSIONS_PER_MONTH = 3
MAX_MESSAGES_PER_SESSION = 8
MAX_INVENTS_PER_MONTH = 6
MAX_INVENT_QUESTIONS = 10
MAX_FILE_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB
MAX_CV_TEXT_CHARS = 30_000
MAX_JOB_DESCRIPTION_CHARS = 10_000
MAX_USER_MESSAGE_CHARS = 1_000


class Settings(BaseSettings):
    database_url: str
    log_level: str = "INFO"
    clerk_secret_key: str | None = None
    clerk_jwt_key: str | None = None
    clerk_authorized_parties: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("clerk_authorized_parties", mode="before")
    @classmethod
    def split_clerk_authorized_parties(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [party.strip() for party in value.split(",") if party.strip()]
        return value

    @field_validator("clerk_jwt_key", mode="before")
    @classmethod
    def normalize_clerk_jwt_key(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.replace("\\n", "\n")
        return value

    model_config = SettingsConfigDict(
        env_file=(".env", "app/.env"),
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
