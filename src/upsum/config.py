import argparse
import logging
import sys
from logging.handlers import SysLogHandler
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


from dataclasses import dataclass

class ConfigError(Exception):
    """Raised when application configuration is invalid."""


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    mail_from: str
    mail_to: str


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Gemini Settings
    gemini_api_key: str = Field(validation_alias="GEMINI_API_KEY")
    gemini_models: str = Field(default="gemini-3.5-flash,gemini-2.5-flash", validation_alias="GEMINI_MODELS")
    gemini_attempts_per_model: int = Field(default=3, validation_alias="GEMINI_MODEL_ATTEMPTS_PER_MODEL")
    gemini_retry_interval_seconds: int = Field(default=300, validation_alias="GEMINI_RETRY_INTERVAL_SECONDS")
    gemini_http_retry_attempts: int = Field(default=2, validation_alias="GEMINI_HTTP_RETRY_ATTEMPTS")

    # SMTP Settings
    smtp_host: str = Field(validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    mail_from: str = Field(default="upsum@example.com", validation_alias="MAIL_FROM")
    mail_to: str = Field(validation_alias="MAIL_TO")

    # General Settings
    log_dir: Path = Field(default=Path("~/logs"))
    log_file: Optional[Path] = Field(default=None)
    dry_run: bool = False

    @property
    def gemini_model_list(self) -> list[str]:
        return [m.strip() for m in self.gemini_models.split(",") if m.strip()]

    @property
    def smtp(self):
        """Provide backwards compatibility with the nested SmtpConfig struct."""
        class SmtpConfigProxy:
            def __init__(self, settings: "AppSettings"):
                self.host = settings.smtp_host
                self.port = settings.smtp_port
                self.user = settings.smtp_user
                self.password = settings.smtp_password
                self.mail_from = settings.mail_from
                self.mail_to = settings.mail_to
        return SmtpConfigProxy(self)


def get_logger() -> logging.Logger:
    """Configure and return a logger with both syslog and console outputs."""
    logger = logging.getLogger("upsum")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("upsum: %(levelname)s %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Syslog handler
    try:
        syslog_handler = SysLogHandler(address="/dev/log")
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)
    except Exception:
        pass

    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize system update logs and send an email."
    )
    parser.add_argument("--log-dir", default="~/logs", help="Directory where log files are stored.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary to console instead of sending email.")
    parser.add_argument("--log-file", help="Specific log file to process, bypassing log directory search.")
    return parser.parse_args()


def load_config(args: argparse.Namespace) -> AppSettings:
    """Load configuration from environment variables and CLI overrides."""
    try:
        settings = AppSettings()
    except Exception as e:
        raise ConfigError(f"Configuration validation failed: {e}") from e

    # Command-line overrides
    if args.log_dir:
        settings.log_dir = Path(args.log_dir).expanduser()
    if args.dry_run:
        settings.dry_run = True
    if args.log_file:
        settings.log_file = Path(args.log_file).expanduser()

    return settings
