import os
import re
import glob
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from markdown_it import MarkdownIt

def find_latest_log_file(log_dir):
    """지정된 디렉토리에서 가장 최근의 로그 파일을 찾습니다."""
    log_dir_path = Path(log_dir).expanduser()
    if not log_dir_path.exists() or not log_dir_path.is_dir():
        raise FileNotFoundError(f"Log directory not found: {log_dir_path}")

    list_of_files = glob.glob(str(log_dir_path / '*'))
    if not list_of_files:
        return None
    latest_file = max(list_of_files, key=os.path.getmtime)
    return latest_file

def parse_log_file(file_path):
    """로그 파일을 파싱하여 재부팅 필요 여부와 전체 로그 내용을 반환합니다."""
    with open(file_path, 'r') as f:
        content = f.read()

    reboot_required = "reboot is required" in content.lower() or "rebooting" in content.lower()

    parsed_data = {
        "reboot_required": reboot_required,
        "log_content": content,
    }
    return parsed_data

def generate_summary_with_gemini(api_key, parsed_data):
    """Gemini API를 사용하여 요약문을 생성합니다."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    reboot_text = "시스템 재부팅이 필요합니다." if parsed_data["reboot_required"] else "시스템 재부팅이 필요하지 않습니다."
    
    log_content = parsed_data["log_content"]

    # DietPi OS 업데이트 확인
    dietpi_update_match = re.search(r"DietPi-Update\s+:\s+v([\d.]+)\s+is\s+now\s+available", log_content)
    dietpi_release_notes = ""
    if dietpi_update_match:
        version = dietpi_update_match.group(1)
        # Gemini does not have real-time web access, so we'll just add a note.
        dietpi_release_notes = f"\n\n**DietPi v{version} 업데이트 정보:**\n- 이 버전에 대한 릴리스 정보는 웹사이트를 참조하세요."

    prompt = f"""
    당신은 시스템 관리자를 위한 보고서 작성 도우미입니다. 다음은 시스템 업데이트 전체 로그입니다. 이 정보를 바탕으로 상세하고 명확한 한국어 보고서를 작성해주세요.

    **로그 내용:**
    ```
    {log_content}
    ```

    **작성 지침:**

    1.  **재부팅 필요 여부:** 보고서 최상단에 "{reboot_text}" 문구를 명확히 포함해주세요.
    2.  **업데이트 상세 내역:**
        - 로그에서 업데이트된 모든 패키지 또는 스크립트 목록을 추출해주세요.
        - 각 항목에 대해 이전 버전과 새로운 버전 번호를 명확하게 표시해주세요 (예: `openssl 1.1.1w-0+deb11u1 -> 1.1.1w-0+deb11u2`).
        - 단순 패키지 설치, 삭제, 시스템 메시지 등도 의미있게 요약해주세요.
    3.  **DietPi OS 업데이트:**
        - 만약 'DietPi-Update' 관련 로그가 있다면, 어떤 버전으로 업데이트되었는지 명시해주세요.
        - {dietpi_release_notes}
    4.  **형식:**
        - 모든 내용은 한국어로 작성해주세요.
        - 각 섹션을 명확하게 구분하여 가독성을 높여주세요.
        - 최종 보고서는 이메일로 보내기 좋은 형식이어야 합니다.

    **최종 보고서 예시:**

    **제목: 일일 시스템 업데이트 보고서**

    **재부팅 필요 여부:** 시스템 재부팅이 필요합니다.

    **상세 업데이트 내역:**

    *   **OS 업데이트:**
        *   DietPi가 v8.25.1로 업데이트되었습니다. (자세한 변경 사항은 공식 홈페이지를 참고하세요.)

    *   **패키지 업데이트:**
        *   openssl: 1.1.1w-0+deb11u1 -> 1.1.1w-0+deb11u2
        *   libssl1.1: 1.1.1w-0+deb11u1 -> 1.1.1w-0+deb11u2
        *   unattended-upgrades: 2.8 -> 2.9
    
    *   **신규 설치:**
        *   new-package: 1.0.0

    위 지침과 예시를 참고하여, 제공된 로그 내용을 바탕으로 최종 보고서를 생성해주세요.
    """

    response = model.generate_content(prompt)
    return response.text

from email.mime.multipart import MIMEMultipart
from markdown_it import MarkdownIt

def send_email(subject, body, smtp_config):
    """요약된 내용을 이메일로 전송합니다."""
    
    # Convert markdown to HTML
    md = MarkdownIt()
    html_body = md.render(body)

    # Create a multipart message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_config["from"] if smtp_config["from"] else "upsum@example.com"
    msg['To'] = smtp_config["to"]

    # Attach parts
    part1 = MIMEText(body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)

    try:
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            if smtp_config["port"] == 587: # TLS 포트인 경우 starttls 시도
                server.starttls()
            
            if smtp_config["user"] and smtp_config["password"]:
                server.login(smtp_config["user"], smtp_config["password"])
            server.sendmail(msg['From'], [smtp_config["to"]], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise Exception("SMTP 인증 실패. 사용자 이름과 비밀번호를 확인해주세요.")
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP 오류 발생: {e}")
    except Exception as e:
        raise Exception(f"이메일 전송 중 예기치 않은 오류 발생: {e}")

def main():
    """메인 실행 함수"""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Summarize system update logs and send an email.")
    parser.add_argument("--log-dir", default="~/logs", help="Directory where log files are stored.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary to console instead of sending email.")
    parser.add_argument("--log-file", help="Specific log file to process, bypassing log directory search.")
    args = parser.parse_args()

    try:
        # 환경 변수 로드
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        smtp_config = {
            "host": os.getenv("SMTP_HOST"),
            "port": int(os.getenv("SMTP_PORT", 587)),
            "user": os.getenv("SMTP_USER", ""), # 기본값 빈 문자열
            "password": os.getenv("SMTP_PASSWORD", ""), # 기본값 빈 문자열
            "from": os.getenv("MAIL_FROM", ""), # 기본값 빈 문자열
            "to": os.getenv("MAIL_TO"),
        }

        if not gemini_api_key:
            print("Error: GEMINI_API_KEY is not set.")
            print("Please create a .env file based on .env.example and fill in the values.")
            return

        # SMTP_HOST와 MAIL_TO는 필수
        if not smtp_config["host"] or not smtp_config["to"]:
            print("Error: Required environment variables (SMTP_HOST, MAIL_TO) are not set.")
            print("Please create a .env file based on .env.example and fill in the values.")
            return

        # 1. 로그 파일 결정 (지정된 파일 또는 최신 파일 검색)
        target_log_file = None
        if args.log_file:
            target_log_file = Path(args.log_file).expanduser()
            if not target_log_file.exists():
                print(f"Error: Specified log file not found: {target_log_file}")
                return
        else:
            target_log_file = find_latest_log_file(args.log_dir)
            if not target_log_file:
                print(f"No log files found in {args.log_dir}. Nothing to do.")
                return
        
        print(f"Processing log file: {target_log_file}")

        # 2. 로그 파일 파싱
        parsed_data = parse_log_file(target_log_file)

        # 3. Gemini로 요약 생성
        summary = generate_summary_with_gemini(gemini_api_key, parsed_data)
        
        subject = "일일 시스템 업데이트 요약"

        print("--- Generated Summary ---")
        print(summary)
        print("-------------------------")

        # 4. 이메일 전송 또는 드라이런 출력
        if args.dry_run:
            print("Dry run enabled. No email will be sent.")
        else:
            print(f"Sending email summary to {smtp_config['to']}...")
            send_email(subject, summary, smtp_config)
            print("Email sent successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
