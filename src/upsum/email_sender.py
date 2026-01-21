import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from markdown_it import MarkdownIt

from .config import SmtpConfig


SMTP_TIMEOUT_SECONDS = 15
SMTP_MAX_RETRIES = 3
SMTP_BACKOFF_SECONDS = 2


def send_email(subject: str, body: str, smtp_config: SmtpConfig, logger) -> None:
    """Send the summary email as both plain text and HTML."""
    md = MarkdownIt()
    html_body = md.render(body)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_config.mail_from if smtp_config.mail_from else "upsum@example.com"
    msg["To"] = smtp_config.mail_to

    part1 = MIMEText(body, "plain", "utf-8")
    part2 = MIMEText(html_body, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    last_error = None
    for attempt in range(SMTP_MAX_RETRIES):
        try:
            with smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if smtp_config.port == 587:
                    server.starttls()

                if smtp_config.user and smtp_config.password:
                    server.login(smtp_config.user, smtp_config.password)

                server.sendmail(msg["From"], [smtp_config.mail_to], msg.as_string())
                logger.info("Email sent successfully via SMTP")
                return
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP 인증 실패. 사용자 이름과 비밀번호를 확인해주세요.")
            raise
        except smtplib.SMTPException as e:
            last_error = e
            if attempt == SMTP_MAX_RETRIES - 1:
                logger.error(f"SMTP 오류 발생(최대 재시도 초과): {e}")
                raise
            wait_seconds = SMTP_BACKOFF_SECONDS ** attempt
            logger.warning(
                f"SMTP 오류 발생 (attempt {attempt + 1}/{SMTP_MAX_RETRIES}); {wait_seconds}s 후 재시도: {e}"
            )
            time.sleep(wait_seconds)
        except Exception as e:
            last_error = e
            if attempt == SMTP_MAX_RETRIES - 1:
                logger.error(f"이메일 전송 중 예기치 않은 오류 발생(최대 재시도 초과): {e}")
                raise
            wait_seconds = SMTP_BACKOFF_SECONDS ** attempt
            logger.warning(
                f"이메일 전송 오류 (attempt {attempt + 1}/{SMTP_MAX_RETRIES}); {wait_seconds}s 후 재시도: {e}"
            )
            time.sleep(wait_seconds)
