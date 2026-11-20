import datetime
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from .logs import summarize_log_for_prompt



class UpdateReportSchema(BaseModel):
    title: str = Field(description="보고서 제목 (예: YYYY년 MM월 DD일 시스템 업데이트 보고서)")
    reboot_required: str = Field(description="재부팅 필요 여부 (예: 시스템 재부팅이 필요하지 않습니다. / 시스템 재부팅이 필요합니다.)")
    summary: str = Field(description="단순 요약(팩트): 주요 업데이트, 버전 변경, 캐시 정리 등")
    analysis: str = Field(description="분석: 버전 최신화 상태, 경고, 운영 영향")
    near_future: str = Field(description="가까운 미래/예상: 모니터링 항목, 예상 업데이트")
    actions: list[str] = Field(description="관리자 액션: 우선순위별 작업")


KST = datetime.timezone(datetime.timedelta(hours=9), "KST")


def formatted_today() -> str:
    """Return today's date in KST formatted as 'YYYY년 MM월 DD일'."""
    today = datetime.datetime.now(KST).date()
    return today.strftime("%Y년 %m월 %d일")


def parse_json_response(json_str: str, logger) -> Optional[dict]:
    """Parse Gemini JSON response, handling code fences."""
    try:
        cleaned = json_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        data = json.loads(cleaned.strip())
        return data
    except json.JSONDecodeError:
        logger.warning("JSON parsing failed; returning raw text fallback")
        return None


def convert_json_to_markdown(json_data: Any):
    """Convert structured JSON to markdown."""
    if not isinstance(json_data, dict):
        return str(json_data)

    markdown = ""

    if "title" in json_data:
        markdown += f"# {json_data['title']}\n\n"

    if "reboot_required" in json_data:
        markdown += f"**재부팅 필요 여부:** {json_data['reboot_required']}\n\n"

    if "summary" in json_data:
        markdown += "## 단순 요약(팩트)\n\n"
        markdown += json_data["summary"] + "\n\n"

    if "analysis" in json_data:
        markdown += "## 분석\n\n"
        markdown += json_data["analysis"] + "\n\n"

    if "near_future" in json_data:
        markdown += "## 가까운 미래/예상\n\n"
        markdown += json_data["near_future"] + "\n\n"

    if "actions" in json_data:
        markdown += "## 관리자 액션\n\n"
        if isinstance(json_data["actions"], list):
            for action in json_data["actions"]:
                markdown += f"- {action}\n"
        else:
            markdown += json_data["actions"]
        markdown += "\n"

    return markdown if markdown else str(json_data)


def _find_antigravity_bin() -> str:
    """Locate the antigravity (or agy) CLI executable."""
    found = shutil.which("antigravity") or shutil.which("agy")
    if found:
        return found
    for candidate in (
        Path.home() / ".local" / "bin" / "antigravity",
        Path.home() / ".local" / "bin" / "agy",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise RuntimeError("Antigravity CLI binary ('antigravity' or 'agy') not found.")


def generate_summary_with_antigravity(
    parsed_data: dict,
    formatted_date: str,
    logger,
) -> str:
    """Generate JSON-structured summary via Antigravity CLI and return markdown."""
    reboot_text = "시스템 재부팅이 필요합니다." if parsed_data["reboot_required"] else "시스템 재부팅이 필요하지 않습니다."

    log_content = summarize_log_for_prompt(parsed_data["log_content"])

    dietpi_update_match = re.search(r"DietPi-Update\s+:\s+v([\d.]+)\s+is\s+now\s+available", log_content)
    dietpi_release_notes = ""
    if dietpi_update_match:
        version = dietpi_update_match.group(1)
        dietpi_release_notes = f"\n\n**DietPi v{version} 업데이트 정보:**\n- 이 버전에 대한 릴리스 정보는 웹사이트를 참조하세요."

    template_path = Path(__file__).parent / "prompt_template.txt"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Prompt template not found: {template_path}")
        raise

    prompt = prompt_template.format(
        formatted_date=formatted_date,
        log_content=log_content,
        reboot_text=reboot_text,
        dietpi_release_notes=dietpi_release_notes,
    )

    antigravity_bin = _find_antigravity_bin()
    schema_json = json.dumps(UpdateReportSchema.model_json_schema(), ensure_ascii=False)
    cmd = [
        antigravity_bin,
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
        "--output-format",
        "json",
        "--json-schema",
        schema_json,
        "--print",
        prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        logger.error("Antigravity CLI timed out while generating summary.")
        raise RuntimeError("Antigravity CLI timed out") from e

    output = result.stdout.strip()
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if not output:
            logger.error(f"Antigravity CLI failed (exit={result.returncode}): {stderr}")
            raise RuntimeError(f"Antigravity CLI failed with exit code {result.returncode}")
        logger.warning(f"Antigravity CLI exited with code {result.returncode}, but produced output: {stderr}")

    logger.info("Antigravity CLI call succeeded")

    response_text = output
    try:
        cli_payload = json.loads(output)
        if isinstance(cli_payload, dict):
            if cli_payload.get("structured_output") is not None:
                report_data = UpdateReportSchema.model_validate(cli_payload["structured_output"])
                return convert_json_to_markdown(report_data.model_dump())
            if "response" in cli_payload and cli_payload["response"] is not None:
                response_text = str(cli_payload["response"]).strip()
    except Exception as e:
        logger.warning(f"Failed to parse Antigravity CLI JSON envelope: {e}. Falling back to response parser.")

    try:
        report_data = UpdateReportSchema.model_validate_json(response_text)
        return convert_json_to_markdown(report_data.model_dump())
    except Exception as e:
        logger.warning(f"Failed to validate response as schema: {e}. Falling back to default parser.")
        json_response = parse_json_response(response_text, logger)
        if json_response:
            return convert_json_to_markdown(json_response)
        return response_text

