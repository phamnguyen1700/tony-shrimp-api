from functools import lru_cache
from decimal import Decimal

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
    access_token_cookie_name: str = "tony_access_token"
    refresh_token_cookie_name: str = "tony_refresh_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_domain: str | None = None

    email_provider: str = "dev"
    email_from: str = "phamnguyen1700@gmail.com"
    # email_from: str = "no-reply@tonyshrimp.local"
    email_logo_url: str = ""
    resend_api_key: str = ""
    resend_api_url: str = "https://api.resend.com/emails"

    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5
    otp_request_cooldown_seconds: int = 30

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "tony-shrimp-media"
    r2_public_base_url: str = ""
    r2_presigned_url_expire_seconds: int = 300

    pii_encryption_key: str = ""

    australian_suburbs_lookup_suburb_url: str = (
        "https://australiansuburbs.au/api/lookup_suburb"
    )
    australian_suburbs_validate_url: str = "https://australiansuburbs.au/api/validate"

    order_shipping_flat_rate_amount: Decimal = Decimal("25.00")
    order_currency: str = "AUD"
    business_timezone: str = "Australia/Sydney"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "aud"
    stripe_success_url: str = (
        "https://tonyshrimp.com.au/orders/success?session_id={CHECKOUT_SESSION_ID}"
    )
    stripe_cancel_url: str = (
        "https://tonyshrimp.com.au/orders/failed?session_id={CHECKOUT_SESSION_ID}"
    )
    stripe_checkout_expires_after_minutes: int = 30

    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,https://tonyshrimp.com.au"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def r2_endpoint_url(self) -> str:
        if not self.r2_account_id:
            return ""

        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
