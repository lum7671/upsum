import sys
from pathlib import Path

from .config import AppConfig, ConfigError, get_logger, load_config, parse_args
from .email_sender import send_email
from .logs import find_latest_log_file, parse_log_file
from .report import formatted_today, generate_summary_with_gemini


def resolve_log_file(config: AppConfig) -> Path:
    """Determine which log file to process, honoring overrides."""
    if config.log_file:
        if not config.log_file.exists():
            raise ConfigError(f"Specified log file not found: {config.log_file}")
        return config.log_file

    try:
        latest = find_latest_log_file(config.log_dir)
    except FileNotFoundError as e:
        raise ConfigError(str(e))

    if not latest:
        raise ConfigError(f"No log files found in {config.log_dir}. Nothing to do.")
    return latest


def main():
    """메인 실행 함수"""
    logger = get_logger()
    args = parse_args()

    try:
        config = load_config(args)
        target_log_file = resolve_log_file(config)

        logger.info(f"Processing log file: {target_log_file}")
        parsed_data = parse_log_file(target_log_file)

        report_date = formatted_today()
        summary = generate_summary_with_gemini(
            config.gemini_api_key,
            parsed_data,
            report_date,
            logger,
        )

        subject = f"{report_date} 시스템 업데이트 요약"

        print("--- Generated Summary ---")
        print(summary)
        print("-------------------------")

        if config.dry_run:
            logger.info("Dry run enabled. No email will be sent.")
        else:
            logger.info(f"Sending email summary to {config.smtp.mail_to}...")
            send_email(subject, summary, config.smtp, logger)

    except ConfigError as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
