import argparse
import logging
import os
import sys
from dataclasses import dataclass
from logging.handlers import SysLogHandler
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when application configuration is invalid."""


def _get_env(name: str, required: bool = False, default: Optional[str] = None) -> str:
    """Fetch and trim environment variables; enforce required values."""
    raw = os.getenv(name, default)
    if raw is None:
        if required:
            raise ConfigError(f"Missing required environment variable: {name}")
        return ""

    value = raw.strip()
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def get_logger() -> logging.Logger:
    """Configure and return a syslog-backed logger with console fallback."""
    logger = logging.getLogger("upsum")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("upsum: %(levelname)s %(message)s")

    try:
        syslog_handler = SysLogHandler(address="/dev/log")
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)
    except Exception:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

    return logger


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    mail_from: str
    mail_to: str


@dataclass
class AppConfig:
    gemini_api_key: str
    smtp: SmtpConfig
    log_dir: Path
    log_file: Optional[Path]
    dry_run: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize system update logs and send an email."
    )
    parser.add_argument("--log-dir", default="~/logs", help="Directory where log files are stored.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary to console instead of sending email.")
    parser.add_argument("--log-file", help="Specific log file to process, bypassing log directory search.")
    return parser.parse_args()


def load_config(args: argparse.Namespace) -> AppConfig:
    load_dotenv()

    gemini_api_key = _get_env("GEMINI_API_KEY", required=True)

    host = _get_env("SMTP_HOST", required=True)
    port_raw = _get_env("SMTP_PORT", default="587")
    user = _get_env("SMTP_USER", default="")
    password = _get_env("SMTP_PASSWORD", default="")
    mail_from = _get_env("MAIL_FROM", default="")
    mail_to = _get_env("MAIL_TO", required=True)

    try:
        port = int(port_raw)
    except ValueError:
        raise ConfigError(f"Invalid SMTP_PORT value: {port_raw}") from None

    if not (1 <= port <= 65535):
        raise ConfigError(f"Invalid SMTP_PORT: {port}")

    smtp_config = SmtpConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        mail_from=mail_from,
        mail_to=mail_to,
    )

    log_dir = Path(args.log_dir).expanduser()
    log_file: Optional[Path] = Path(args.log_file).expanduser() if args.log_file else None

    return AppConfig(
        gemini_api_key=gemini_api_key,
        smtp=smtp_config,
        log_dir=log_dir,
        log_file=log_file,
        dry_run=args.dry_run,
    )
