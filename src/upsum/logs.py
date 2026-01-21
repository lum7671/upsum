import glob
import os
from pathlib import Path
from typing import Optional


def find_latest_log_file(log_dir: Path) -> Optional[Path]:
    """Return the most recent log file in the given directory."""
    if not log_dir.exists() or not log_dir.is_dir():
        raise FileNotFoundError(f"Log directory not found: {log_dir}")

    list_of_files = glob.glob(str(log_dir / "*"))
    if not list_of_files:
        return None

    latest_file = max(list_of_files, key=os.path.getmtime)
    return Path(latest_file)


def parse_log_file(file_path: Path) -> dict:
    """Parse the log file and return reboot flag and raw content."""
    with open(file_path, "r") as f:
        content = f.read()

    reboot_required = "reboot is required" in content.lower() or "rebooting" in content.lower()

    parsed_data = {
        "reboot_required": reboot_required,
        "log_content": content,
    }
    return parsed_data


def summarize_log_for_prompt(log_content: str) -> str:
    """Summarize raw log text for use in the prompt."""
    if "상세 업데이트 내역:" in log_content or "업데이트 내역:" in log_content:
        return log_content

    if len(log_content) > 3000:
        return log_content[:3000] + "\n\n[로그가 길어서 일부만 표시됨]"

    return log_content
