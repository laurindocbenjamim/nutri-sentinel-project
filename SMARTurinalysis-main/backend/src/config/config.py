"""
Configuration module for the SMARTurinalysis backend.
Handles loading environment variables and configuring Sentry.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import sentry_sdk

class Settings(BaseSettings):
    """
    App settings using Pydantic Settings.
    Loads variables from environment or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT: Path = BASE_DIR.parent
    
    # API Settings
    APP_NAME: str = "SMARTurinalysis API"
    DEBUG: bool = False
    PORT: int = 8000
    
    # Sentry DSN (mocked by default to satisfy SecOps rule)
    SENTRY_DSN: str = ""

    # JWT Session Token Settings
    JWT_SECRET: str = "supersecretdefaultkeyfortestingonly12345"  # Secret key to sign the JWT session token
    JWT_ALGORITHM: str = "HS256"  # Cryptographic algorithm for signing the session token

    # Cookie Security
    SECURE_COOKIE: bool = False

    # MongoDB Configuration
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "nutrisentinel_agent_ai"
    MONGODB_COLLECTION: str = "analysis"

    # PostgreSQL Configuration
    POSTGRES_URL: str = ""

    # LLM Configuration
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: str = ""
    GROQ_STT_MODEL: str = "whisper-large-v3"

    # Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Market Updater Background Agent Settings
    MARKET_UPDATER_INTERVAL_MINUTES: int = 10080 # Default: 7 Days (10080 minutes)
    MARKETS_TO_SEARCH: str = "continente, lidl, mercadona"
    MARKET_UPDATER_SLEEP_SECONDS: int = 3

# Instantiate settings
settings = Settings()

def init_sentry() -> None:
    """
    Initialize Sentry monitoring for the backend.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        print("Sentry initialized successfully.")
    else:
        print("Sentry DSN not set. Skipping initialization.")
