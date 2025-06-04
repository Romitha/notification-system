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
    DIALOG_API_BASE_URL: str = os.getenv("DIALOG_API_BASE_URL", "https://esms.dialog.lk/api/v2")
    DIALOG_API_USERNAME: str = os.getenv("DIALOG_API_USERNAME", "")
    DIALOG_API_PASSWORD: str = os.getenv("DIALOG_API_PASSWORD", "")
    DIALOG_DEFAULT_MASK: str = os.getenv("DIALOG_DEFAULT_MASK", "NOTIFY")

    # ==========================================
    # 🔄 RETRY MECHANISM CONFIGURATION
    # ==========================================

    # Retry Delays (in minutes)
    RETRY_FIRST_DELAY_MINUTES: int = int(os.getenv("RETRY_FIRST_DELAY_MINUTES", "5"))  # Default: 5 minutes
    RETRY_SECOND_DELAY_MINUTES: int = int(os.getenv("RETRY_SECOND_DELAY_MINUTES", "5"))  # Default: 5 minutes
    RETRY_FINAL_DELAY_MINUTES: int = int(os.getenv("RETRY_FINAL_DELAY_MINUTES", "30"))  # Default: 30 minutes

    # Retry Attempts Configuration
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))  # Default: 3 total attempts

    # Retry Topics Configuration
    RETRY_TOPIC_SHORT: str = os.getenv("RETRY_TOPIC_SHORT", "notifications-retry-5m")
    RETRY_TOPIC_LONG: str = os.getenv("RETRY_TOPIC_LONG", "notifications-retry-30m")
    FAILED_TOPIC: str = os.getenv("FAILED_TOPIC", "notifications-failed")

    # Testing Mode - Fast Retry for Development/Testing
    TESTING_MODE: bool = os.getenv("TESTING_MODE", "False") == "True"

    # Fast retry delays for testing (in seconds, not minutes!)
    TEST_RETRY_FIRST_DELAY_SECONDS: int = int(os.getenv("TEST_RETRY_FIRST_DELAY_SECONDS", "30"))  # 30 seconds
    TEST_RETRY_SECOND_DELAY_SECONDS: int = int(os.getenv("TEST_RETRY_SECOND_DELAY_SECONDS", "30"))  # 30 seconds
    TEST_RETRY_FINAL_DELAY_SECONDS: int = int(os.getenv("TEST_RETRY_FINAL_DELAY_SECONDS", "60"))  # 60 seconds

    # ==========================================
    # 🎯 RETRY HELPER PROPERTIES
    # ==========================================

    @property
    def retry_delays(self) -> dict:
        """Get retry delays based on testing mode"""
        if self.TESTING_MODE:
            return {
                "first_delay": self.TEST_RETRY_FIRST_DELAY_SECONDS / 60,  # Convert to minutes for consistency
                "second_delay": self.TEST_RETRY_SECOND_DELAY_SECONDS / 60,
                "final_delay": self.TEST_RETRY_FINAL_DELAY_SECONDS / 60,
                "unit": "seconds",
                "first_delay_seconds": self.TEST_RETRY_FIRST_DELAY_SECONDS,
                "second_delay_seconds": self.TEST_RETRY_SECOND_DELAY_SECONDS,
                "final_delay_seconds": self.TEST_RETRY_FINAL_DELAY_SECONDS
            }
        else:
            return {
                "first_delay": self.RETRY_FIRST_DELAY_MINUTES,
                "second_delay": self.RETRY_SECOND_DELAY_MINUTES,
                "final_delay": self.RETRY_FINAL_DELAY_MINUTES,
                "unit": "minutes",
                "first_delay_seconds": self.RETRY_FIRST_DELAY_MINUTES * 60,
                "second_delay_seconds": self.RETRY_SECOND_DELAY_MINUTES * 60,
                "final_delay_seconds": self.RETRY_FINAL_DELAY_MINUTES * 60
            }

    @property
    def retry_config_summary(self) -> str:
        """Get a summary of retry configuration"""
        delays = self.retry_delays
        mode = "TESTING" if self.TESTING_MODE else "PRODUCTION"

        return f"""
🔄 Retry Configuration ({mode} Mode):
  - First Retry:  {delays['first_delay_seconds']} seconds
  - Second Retry: {delays['second_delay_seconds']} seconds  
  - Final Retry:  {delays['final_delay_seconds']} seconds
  - Max Attempts: {self.MAX_RETRY_ATTEMPTS}
  - After {self.MAX_RETRY_ATTEMPTS} attempts: Permanent failure
        """.strip()

    class Config:
        env_file = ".env"


settings = Settings()
