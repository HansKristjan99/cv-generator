from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ---- OpenAI runtime ----
# Model used for every CV generation, invention, and memory-extraction call.
MODEL = "gpt-5.4-mini-2026-03-17"
OPENAI_DEFAULT_TOOL_ITERATIONS = 4
OPENAI_CONVERSATION_ITEM_CHAR_CAP = 4_000

# Agent-specific tool budgets.
WRITER_MAX_TOOL_ITERATIONS = 10
COVER_LETTER_MAX_TOOL_ITERATIONS = 6

# ---- Cost-guard limits (free tier) ----
MAX_SESSIONS_PER_MONTH = 3
MAX_MESSAGES_PER_SESSION = 15
MAX_INVENTS_PER_MONTH = 6
MAX_INVENT_QUESTIONS = 10
MAX_FILE_SIZE_MB = 3
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CV_TEXT_CHARS = 30_000
MAX_JOB_DESCRIPTION_CHARS = 10_000
MAX_USER_MESSAGE_CHARS = 10_000
MAX_MEMORY_NOTE_CHARS = 600

# ---- CV and cover-letter generation ----
DEFAULT_TEMPLATE_SLUG = "default"
DEFAULT_CV_PAGE_COUNT = 1
CV_PAGE_COUNT_OPTIONS = (1, 2, 3)
COVER_LETTER_TARGET_PAGES = 1
REQUIREMENTS_MAX_GATE_QUESTIONS = 3
INITIAL_SESSION_MESSAGE_COUNT = 1
INITIAL_SESSION_INVENT_COUNT = 0
SESSION_LIST_LIMIT = 50
SESSION_ERROR_MESSAGE_CHARS = 500

# Tool-result payload caps.
COMPILE_TOOL_ERROR_CHARS = 600

# Session title prompt/result caps.
SESSION_TITLE_JOB_DESCRIPTION_CHARS = 1_200
SESSION_TITLE_USER_MESSAGE_CHARS = 300
SESSION_TITLE_MAX_CHARS = 80

# ---- LaTeX rendering ----
LATEX_COMPILE_TIMEOUT_SECONDS = 25.0
LATEX_COMPILE_ERROR_TAIL_CHARS = 1_200

# Default CV template layout knobs.
DEFAULT_TEMPLATE_FONT_PT = 10
DEFAULT_TEMPLATE_MARGIN_CM = 1.2
DEFAULT_TEMPLATE_SECTION_SPACING_PT = 8

# ---- Logging ----
LOG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"


class Settings(BaseSettings):
    # Accept either a full DATABASE_URL or individual DB_* parts (as injected by
    # CDK from the RDS-generated secret).  The validator builds the URL from
    # parts when DATABASE_URL is not provided directly.
    database_url: str = ""
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "cvapp"
    db_user: str = "cvapp"
    db_password: str | None = None

    log_level: str = "INFO"
    clerk_secret_key: str | None = None
    clerk_jwt_key: str | None = None
    clerk_authorized_parties: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_database_url(self) -> "Settings":
        if not self.database_url:
            if self.db_host and self.db_password:
                self.database_url = (
                    f"postgresql+psycopg://{self.db_user}:{self.db_password}"
                    f"@{self.db_host}:{self.db_port}/{self.db_name}"
                )
            else:
                raise ValueError(
                    "Set DATABASE_URL, or set DB_HOST + DB_PASSWORD to build it."
                )
        return self

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
        if not value:
            return None
        return value.replace("\\n", "\n")

    model_config = SettingsConfigDict(
        env_file=(".env", "app/.env"),
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
