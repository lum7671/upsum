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


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # General Settings
    log_dir: Path = Field(default=Path("~/logs"))
    log_file: Optional[Path] = Field(default=None)
    dry_run: bool = False


import datetime

KST = datetime.timezone(datetime.timedelta(hours=9), "KST")


class KSTFormatter(logging.Formatter):
    """Logging formatter that explicitly formats time in KST (UTC+9)."""
    def formatTime(self, record, datefmt=None):
        dt = datetime.datetime.fromtimestamp(record.created, tz=KST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S KST")


def get_logger() -> logging.Logger:
    """Configure and return a logger with both syslog and console outputs."""
    logger = logging.getLogger("upsum")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = KSTFormatter("%(asctime)s upsum: %(levelname)s %(message)s")

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
