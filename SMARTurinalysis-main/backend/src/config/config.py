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
