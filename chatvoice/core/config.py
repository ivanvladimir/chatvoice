import os
from enum import Enum

from pydantic import SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.config import Config

current_file_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_file_dir, "..", "..", ".env")
config = Config(env_path)


class AppSettings:
    APP_NAME: str = "Chatvoice"
    APP_DESCRIPTION: str | None = None
    APP_VERSION: str | None = None
    LICENSE_NAME: str | None = None
    CONTACT_NAME: str | None = None
    CONTACT_EMAIL: str | None = None


class CryptSettings:
    SECRET_KEY: SecretStr = SecretStr("secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    WS_SESSION_EXPIRE_MINUTES: int = 15


class DatabaseOption(str, Enum):
    SQLITE: str = "sqlite"
    MYSQL: str = "mysql"
    POSTGRES: str = "postgres"


class DatabaseOptionSettings:
    DATABASE: DatabaseOption = "sqlite"


class DatabaseSettings:
    pass


class SQLiteSettings(DatabaseSettings):
    SQLITE_URI: str = "./sql_app.db"
    SQLITE_SYNC_PREFIX: str = "sqlite:///"
    SQLITE_ASYNC_PREFIX: str = "sqlite+aiosqlite:///"


class MySQLSettings(DatabaseSettings):
    MYSQL_USER: str = "username"
    MYSQL_PASSWORD: str = "password"
    MYSQL_SERVER: str = "localhost"
    MYSQL_PORT: int = 5432
    MYSQL_DB: str = "dbname"
    MYSQL_SYNC_PREFIX: str = "mysql://"
    MYSQL_ASYNC_PREFIX: str = "mysql+aiomysql://"
    MYSQL_URL: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MYSQL_URI(self) -> str:
        credentials = f"{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
        location = f"{self.MYSQL_SERVER}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        return f"{credentials}@{location}"


class PostgresSettings(DatabaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres"
    POSTGRES_SYNC_PREFIX: str = "postgresql://"
    POSTGRES_ASYNC_PREFIX: str = "postgresql+asyncpg://"
    POSTGRES_URL: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def POSTGRES_URI(self) -> str:
        credentials = f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        location = f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return f"{credentials}@{location}"


class CRUDAdminSettings:
    CRUD_ADMIN_ENABLED: bool = True
    CRUD_ADMIN_MOUNT_PATH: str = "/admin"

    CRUD_ADMIN_ALLOWED_IPS_LIST: list[str] | None = None
    CRUD_ADMIN_ALLOWED_NETWORKS_LIST: list[str] | None = None
    CRUD_ADMIN_MAX_SESSIONS: int = 10
    CRUD_ADMIN_SESSION_TIMEOUT: int = 1440
    SESSION_SECURE_COOKIES: bool = True

    CRUD_ADMIN_TRACK_EVENTS: bool = True
    CRUD_ADMIN_TRACK_SESSIONS: bool = True

    CRUD_ADMIN_REDIS_ENABLED: bool = False
    CRUD_ADMIN_REDIS_HOST: str = "localhost"
    CRUD_ADMIN_REDIS_PORT: int = 6379
    CRUD_ADMIN_REDIS_DB: int = 0
    CRUD_ADMIN_REDIS_PASSWORD: str | None = "None"
    CRUD_ADMIN_REDIS_SSL: bool = False


class EnvironmentOption(str, Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: EnvironmentOption = EnvironmentOption.LOCAL


class CORSSettings(BaseSettings):
    CORS_ORIGINS: list[str] = ["*"]
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]


class DefaultRateLimitSettings(BaseSettings):
    DEFAULT_RATE_LIMIT_LIMIT: int = 10
    DEFAULT_RATE_LIMIT_PERIOD: int = 3600


class ClientSideCacheSettings(BaseSettings):
    CLIENT_CACHE_MAX_AGE: int = 60


class EnvironmentOption(str, Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    NONE = "none"


class LLMSettings:  # <-- plain class, no BaseSettings here
    LLM_PROVIDER: LLMProvider = LLMProvider.NONE

    OPENAI_API_KEY: SecretStr | None = None
    ANTHROPIC_API_KEY: SecretStr | None = None
    GOOGLE_API_KEY: SecretStr | None = None
    AZURE_OPENAI_API_KEY: SecretStr | None = None
    NONE_API_KEY: None = None
    AZURE_OPENAI_ENDPOINT: str | None = None

    @model_validator(mode="after")
    def check_active_key_present(self) -> "LLMSettings":
        key = self.active_api_key
        if key is None or not key.get_secret_value().strip():
            raise ValueError(
                f"LLM_PROVIDER is set to '{self.LLM_PROVIDER.value}' but "
                f"'{self.LLM_PROVIDER.value.upper()}_API_KEY' is missing or empty in .env"
            )
        return self

    @property
    def active_api_key(self) -> SecretStr | None:
        mapping = {
            LLMProvider.OPENAI: self.OPENAI_API_KEY,
            LLMProvider.ANTHROPIC: self.ANTHROPIC_API_KEY,
            LLMProvider.GOOGLE: self.GOOGLE_API_KEY,
            LLMProvider.AZURE_OPENAI: self.AZURE_OPENAI_API_KEY,
            LLMProvider.NONE: self.NONE_API_KEY,
        }
        return mapping[self.LLM_PROVIDER]

    def get_key(self) -> str:
        key = self.active_api_key
        assert key is not None
        return key.get_secret_value()


class Settings(
    AppSettings,
    CryptSettings,
    DatabaseOptionSettings,
    SQLiteSettings,
    MySQLSettings,
    PostgresSettings,
    CRUDAdminSettings,
    EnvironmentSettings,
    CORSSettings,
    DefaultRateLimitSettings,
    ClientSideCacheSettings,
    BaseSettings,
    LLMSettings,
):
    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "..", ".env"
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def get_settings() -> Settings:
    return settings
