from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Tony Shrimp API"
    environment: str = "development"

    database_url: str = Field(
        default="postgresql+psycopg://admin:admin@localhost:5432/tony_shrimp"
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-local-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    email_provider: str = "dev"
    email_from: str = "phamnguyen1700@gmail.com"
    # email_from: str = "no-reply@tonyshrimp.local"
    resend_api_key: str = ""
    resend_api_url: str = "https://api.resend.com/emails"

    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5
    otp_request_cooldown_seconds: int = 30

    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
