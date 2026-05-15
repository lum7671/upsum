import glob
import os
import re
from pathlib import Path
from typing import Optional


# 제거할 패턴들 (상수로 관리)
PATTERNS_TO_REMOVE = [
    r"^debconf:.*$",                           # debconf 경고
    r"^\s*\[[  \.OK]*\].*$",                   # 진행 바
    r"^(패키지 목록을|의존성 트리를|상태 정보를).*$",  # 반복 메시지
    r"^(기존|받기):[0-9]+ .*$",                # apt 인덱스 라인
    r"^내려받기 [\d.]+ [a-zA-Z가-힣]+.*$",     # 다운로드 진행
    r"^\(?데이터베이스 읽는중 \.\.\..*$",       # dpkg 진행률 라인
    r"^Copying blob sha256:.*$",              # podman blob 복사 로그
    r"^╔.*╗$",                                # 박스 상단 라인
    r"^╚.*╝$",                                # 박스 하단 라인
    r"^files changed.*$",                     # git diffstat
    r"^insertions\(\+\).*$",                # git diffstat
    r"^deletions\(-\).*$",                   # git diffstat
    r"^create mode.*$",                       # git diffstat
    r"^/usr/local/lib/.*$",                   # 경로 나열
    r"^/usr/local/include/.*$",               # 경로 나열
    r"^\* \[새로운 브랜치\].*$",               # git 브랜치
    r"^\* \[새로운 태그\].*$",                 # git 태그
    r"^\+ [0-9a-f]{7,}.*$",                  # git 강제 업데이트
    r"^─+$",                                  # 단독 ─ 라인
]


# 시작부 반복 문자를 1개로 축약할 대상
LEADING_REPEAT_CHARS = ["-", "=", "─"]


def find_latest_log_file(log_dir: Path) -> Optional[Path]:
    """Return the most recent log file in the given directory."""
    if not log_dir.exists() or not log_dir.is_dir():
        raise FileNotFoundError(f"Log directory not found: {log_dir}")

    list_of_files = glob.glob(str(log_dir / "*"))
    if not list_of_files:
        return None

    latest_file = max(list_of_files, key=os.path.getmtime)
    return Path(latest_file)


def clean_log_content(log_content: str) -> str:
    """Remove unnecessary lines from log content using regex patterns."""
    lines = log_content.splitlines()
    cleaned_lines = []

    for line in lines:
        normalized_line = line.strip()
        # ANSI 색상 이스케이프(ESC 시퀀스) 제거
        normalized_line = re.sub(r"\x1b\[[0-9;]*m", "", normalized_line)
        # 로그 구분선 노이즈를 줄이기 위해 시작부의 반복 문자를 1개로 축약
        for repeat_char in LEADING_REPEAT_CHARS:
            escaped = re.escape(repeat_char)
            normalized_line = re.sub(rf"^({escaped})\1+", r"\1", normalized_line)
        if not normalized_line:
            continue
        # 모든 제거 패턴과 매치되지 않으면 유지
        if not any(re.match(pattern, normalized_line) for pattern in PATTERNS_TO_REMOVE):
            cleaned_lines.append(normalized_line)

    return '\n'.join(cleaned_lines)


def parse_log_file(file_path: Path) -> dict:
    """Parse the log file and return reboot flag and cleaned content."""
    with open(file_path, "r") as f:
        content = f.read()

    # 클리닝 추가
    cleaned_content = clean_log_content(content)

    # 정제된 로그를 .001 파일로 저장
    cleaned_file_path = Path(str(file_path) + ".001")
    with open(cleaned_file_path, "w") as f:
        f.write(cleaned_content)

    reboot_required = "reboot is required" in cleaned_content.lower() or "rebooting" in cleaned_content.lower()

    parsed_data = {
        "reboot_required": reboot_required,
        "log_content": cleaned_content,
    }
    return parsed_data


def summarize_log_for_prompt(log_content: str) -> str:
    """Summarize raw log text for use in the prompt."""
    if "상세 업데이트 내역:" in log_content or "업데이트 내역:" in log_content:
        return log_content

    if len(log_content) > 30000:
        return log_content[:30000] + "\n\n[로그가 30KB 이상 길어 앞부분만 표시됨]"

    return log_content
