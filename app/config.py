
import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Configuration settings for the application"""
    APP_NAME: str = "Notification System"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./notification.db")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # Vendor API Keys
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    
    # Drupal CMS
    DRUPAL_API_URL: str = os.getenv("DRUPAL_API_URL", "")
    DRUPAL_USERNAME: str = os.getenv("DRUPAL_USERNAME", "")
    DRUPAL_PASSWORD: str = os.getenv("DRUPAL_PASSWORD", "")

    # Email settings
    USE_FIREBASE_EMAIL: bool = os.getenv("USE_FIREBASE_EMAIL", "False") == "True"
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "notifications@example.com")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True") == "True"

    # Database - use async SQLite for application, sync SQLite for migrations
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./notification_system.db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "sqlite:///./notification_system.db")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "False") == "True"

    # Dialog API Settings
    DIALOG_API_BASE_URL: str = os.getenv("DIALOG_API_BASE_URL", "https://richcommunication.dialog.lk/api")
    DIALOG_API_USERNAME: str = os.getenv("DIALOG_API_USERNAME", "")
    DIALOG_API_PASSWORD: str = os.getenv("DIALOG_API_PASSWORD", "")
    DIALOG_DEFAULT_MASK: str = os.getenv("DIALOG_DEFAULT_MASK", "NOTIFY")

settings = Settings()