import os
import re
import glob
import smtplib
import argparse
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

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
    """로그 파일을 파싱하여 재부팅 필요 여부와 업데이트된 패키지 목록을 추출합니다."""
    with open(file_path, 'r') as f:
        content = f.read()

    reboot_required = "reboot is required" in content.lower() or "rebooting" in content.lower()

    # Debian/Ubuntu apt 로그 형식에 맞는 정규식
    # 예: "Upgrade: package-name (1.0.0, 1.1.0)"
    # 예: "Install: package-name (1.0.0)"
    package_pattern = re.compile(r"(?:Upgrade|Install): ([\w.-]+)(?::\w+)? \((?:([\d.:~+-]+))? ?-> ?([\d.:~+-]+)\)")
    upgrades = package_pattern.findall(content)
    
    parsed_data = {
        "reboot_required": reboot_required,
        "upgraded_packages": [{"name": name, "from": old, "to": new} for name, old, new in upgrades],
    }
    return parsed_data

def generate_summary_with_gemini(api_key, parsed_data):
    """Gemini API를 사용하여 요약문을 생성합니다."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    reboot_text = "시스템 재부팅이 필요합니다." if parsed_data["reboot_required"] else "시스템 재부팅이 필요하지 않습니다."
    
    packages_texts = []
    for pkg in parsed_data["upgraded_packages"]:
        packages_texts.append(f"- {pkg['name']}: {pkg['from']} -> {pkg['to']}")
    
    if not packages_texts:
        packages_texts.append("- 업데이트된 패키지가 없습니다.")

    package_info = "\n".join(packages_texts)

    prompt = f"""
    당신은 시스템 관리자를 위한 보고서 작성 도우미입니다. 다음은 시스템 업데이트 로그 분석 결과입니다. 이 정보를 바탕으로 간결하고 명확한 한국어 요약 보고서를 작성해주세요.

    1.  **재부팅 필요 여부:** {reboot_text}
    2.  **주요 업데이트 내역:**
        {package_info}

    위 내용을 바탕으로, 이메일로 보내기 좋은 형식의 최종 요약문을 생성해주세요. 가장 중요한 재부팅 필요 여부를 첫 문장에 명시적으로 언급해주세요.
    """

    response = model.generate_content(prompt)
    return response.text

def send_email(subject, body, smtp_config):
    """요약된 내용을 이메일로 전송합니다."""
    msg = MIMEText(body, _charset="utf-8")
    msg['Subject'] = subject
    msg['From'] = smtp_config["from"] if smtp_config["from"] else "upsum@example.com" # From 주소가 없으면 에러 발생 가능성 있어 기본값 설정
    msg['To'] = smtp_config["to"]

    try:
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            if smtp_config["port"] == 587: # TLS 포트인 경우 starttls 시도
                server.starttls()
            elif smtp_config["port"] == 465: # SMTPS 포트인 경우 SSL 컨텍스트 사용 (여기서는 일반 SMTP 사용하므로 587만 처리)
                # smtplib.SMTP_SSL 을 사용해야 하지만, 현재 SMTP만 사용하므로 이 부분은 필요시 추가
                pass 
            
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
