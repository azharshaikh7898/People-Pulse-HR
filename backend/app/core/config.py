"""Application settings, read from environment variables (or a local .env file)."""
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRETS = {"change-me", "changeme", "secret", "your-secret-key"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # No default on purpose: the app refuses to start without these.
    DATABASE_URL: str
    SECRET_KEY: str

    ENVIRONMENT: str = "development"  # development | test | production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"
    # Comma-separated list of allowed frontend origins.
    CORS_ORIGINS: str = "http://localhost:5173"

    @field_validator("DATABASE_URL")
    @classmethod
    def normalise_db_url(cls, v: str) -> str:
        # Render/Heroku style URLs start with postgres:// or postgresql://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg2://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    @model_validator(mode="after")
    def check_production_safety(self):
        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.lower() in INSECURE_SECRETS:
                raise ValueError("In production SECRET_KEY must be a random string of 32+ characters.")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
