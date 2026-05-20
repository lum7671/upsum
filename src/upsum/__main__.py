import sys
from pathlib import Path

from .config import AppConfig, ConfigError, get_logger, load_config, parse_args
from .email_sender import send_email
from .logs import find_latest_log_file
from .report import formatted_today, generate_summary_with_gemini
from .log_preprocess import run_preprocess_pipeline, get_reboot_decision, load_summary_markdown


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
        
        # 1. 로그 전처리 (노이즈 제거 → 이벤트 구조화 → 요약 생성)
        logger.info("Preprocessing log: cleaner → parser → generator")
        preprocess_results = run_preprocess_pipeline(target_log_file)
        cleaned_log = preprocess_results['cleaned']
        events_file = preprocess_results['events']
        summary_file = preprocess_results['summary']
        
        # 2. 재부팅/재시작 판정 추출
        decision = get_reboot_decision(events_file)
        logger.info(f"Reboot needed: {decision['reboot_needed']}, Restart needed: {decision['restart_needed']}")
        
        # 3. 전처리된 로그(.001.cleaned.log) 읽기
        with cleaned_log.open(encoding="utf-8") as f:
            cleaned_log_content = f.read()
        
        # 4. Gemini input 형태로 변환
        parsed_data = {
            "log_content": cleaned_log_content,
            "reboot_required": decision['reboot_needed'],
        }
        
        # 5. Gemini에 전처리된 로그 전달
        report_date = formatted_today()
        summary = generate_summary_with_gemini(
            config.gemini_api_key,
            parsed_data,
            report_date,
            logger,
        )
        
        # 5. 구조화된 요약 추가
        structured_summary = load_summary_markdown(summary_file)
        if structured_summary:
            summary += "\n\n---\n\n## 구조화된 요약\n" + structured_summary
        
        # 6. 재부팅/재시작 필요 여부 추가
        judgment = "\n\n---\n\n## 시스템 판정\n"
        judgment += f"- **재부팅 필요**: {'예' if decision['reboot_needed'] else '아니오'}\n"
        judgment += f"- **서비스 재시작 필요**: {'예' if decision['restart_needed'] else '아니오'}\n"
        summary += judgment

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
