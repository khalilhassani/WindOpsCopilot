import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "WindOps Copilot"
    API_V1_STR: str = "/api"
    
    # MongoDB Config
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "windops_copilot"
    COLLECTION_INCIDENTS: str = "incidents"
    COLLECTION_TURBINES: str = "turbines"
    COLLECTION_ALERTS: str = "alerts"
    
    # LLM keys (optional fallbacks if missing)
    OPENAI_API_KEY: str | None = None
    
    # SMTP / Gmail Notification settings
    SMTP_SERVER: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str = "ops@smartwindfarm.ai"
    EMAIL_TO: str = "khlilhssani@gmail.com"
    EMAIL_METHOD: str = "smtp"
    
    # File storage paths for simulation/outputs
    MAILBOX_DIR: str = str(BASE_DIR / "data" / "sent_emails")
    REPORTS_DIR: str = str(BASE_DIR / "data" / "reports")
    
    # Dev settings
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
os.makedirs(settings.MAILBOX_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
