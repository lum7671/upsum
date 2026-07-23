import datetime
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from google.genai import types
from pydantic import BaseModel, Field
from sysutils.gemini import DynamicGeminiManager

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


def generate_summary_with_gemini(
    parsed_data: dict,
    formatted_date: str,
    logger,
) -> str:
    """Generate JSON-structured summary via Gemini and return markdown."""
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

    call_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=UpdateReportSchema,
    )

    manager = DynamicGeminiManager()

    try:
        response, used_model = manager.generate_content_with_fallback(
            prompt=prompt,
            config=call_config
        )
        logger.info(f"Gemini call succeeded using model {used_model}")
    except Exception as e:
        logger.error(f"Gemini API call failed after dynamic model fallback chain: {e}")
        raise RuntimeError("Gemini API call failed after dynamic model fallback chain") from e

    try:
        report_data = UpdateReportSchema.model_validate_json(response.text.strip())
        return convert_json_to_markdown(report_data.model_dump())
    except Exception as e:
        logger.warning(f"Failed to validate response as schema: {e}. Falling back to default parser.")
        json_response = parse_json_response(response.text, logger)
        if json_response:
            return convert_json_to_markdown(json_response)
        return response.text

