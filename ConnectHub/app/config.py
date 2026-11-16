from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (the ConnectHub/ folder), regardless of the current working directory
BASE_DIR = Path(__file__).resolve().parents[1]

# Central configuration for the ConnectHub application
class Settings(BaseSettings):

    # Application settings
    APP_NAME: str = "ConnectHub"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database settings
    DATABASE_URL: str

    # JWT authentication settings
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Password hashing (bcrypt cost). Lower it only for tests/local tuning.
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=31)

    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Frontend CORS settings
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Create one settings object for the application
settings = Settings()


# Quick self-check: `python app/config.py` from the ConnectHub
if __name__ == "__main__":
    print(f"{settings.APP_NAME} {settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    print(f"env file : {BASE_DIR / '.env'}")
    print(f"database : {settings.DATABASE_URL}")
    print(f"redis    : {settings.REDIS_URL}")
