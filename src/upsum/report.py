import datetime
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

import google.genai as genai
from pydantic import BaseModel, Field

from .logs import summarize_log_for_prompt


GEMINI_TIMEOUT_SECONDS = 30
GEMINI_DEFAULT_MODELS = [
    "gemini-3.5-flash",        # 기본 모델
    "gemini-2.5-flash"         # 폴백 모델
]
GEMINI_DEFAULT_ATTEMPTS_PER_MODEL = 3
GEMINI_DEFAULT_RETRY_INTERVAL_SECONDS = 300
GEMINI_DEFAULT_HTTP_RETRY_ATTEMPTS = 2
GEMINI_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class UpdateReportSchema(BaseModel):
    title: str = Field(description="보고서 제목 (예: YYYY년 MM월 DD일 시스템 업데이트 보고서)")
    reboot_required: str = Field(description="재부팅 필요 여부 (예: 시스템 재부팅이 필요하지 않습니다. / 시스템 재부팅이 필요합니다.)")
    summary: str = Field(description="단순 요약(팩트): 주요 업데이트, 버전 변경, 캐시 정리 등")
    analysis: str = Field(description="분석: 버전 최신화 상태, 경고, 운영 영향")
    near_future: str = Field(description="가까운 미래/예상: 모니터링 항목, 예상 업데이트")
    actions: list[str] = Field(description="관리자 액션: 우선순위별 작업")


def formatted_today() -> str:
    """Return today's date formatted as 'YYYY년 MM월 DD일'."""
    today = datetime.date.today()
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


def _extract_status_code(error: Exception) -> Optional[int]:
    """Extract an HTTP-like status code from Gemini SDK exceptions."""
    code = getattr(error, "code", None)
    if isinstance(code, int):
        return code

    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    match = re.search(r"\b([45]\d{2})\b", str(error))
    if match:
        return int(match.group(1))

    return None


def _is_retryable_error(error: Exception) -> bool:
    """Decide whether an error should be retried based on status code."""
    status_code = _extract_status_code(error)
    if status_code is None:
        return True
    if status_code in GEMINI_RETRYABLE_STATUS_CODES:
        return True
    if 400 <= status_code < 500:
        return False
    return status_code >= 500


def generate_summary_with_gemini(
    api_key: str,
    parsed_data: dict,
    formatted_date: str,
    logger,
    *,
    models: Optional[list[str]] = None,
    attempts_per_model: int = GEMINI_DEFAULT_ATTEMPTS_PER_MODEL,
    retry_interval_seconds: int = GEMINI_DEFAULT_RETRY_INTERVAL_SECONDS,
    http_retry_attempts: int = GEMINI_DEFAULT_HTTP_RETRY_ATTEMPTS,
) -> str:
    """Generate JSON-structured summary via Gemini and return markdown."""
    client = genai.Client(api_key=api_key)

    if isinstance(models, str):
        active_models = [m.strip() for m in models.split(",") if m.strip()]
    elif models:
        active_models = models
    else:
        active_models = GEMINI_DEFAULT_MODELS

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

    def _call_gemini(model_name: str):
        config = genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=UpdateReportSchema,
            http_options=genai.types.HttpOptions(
                timeout=GEMINI_TIMEOUT_SECONDS * 1000,
                retry_options=genai.types.HttpRetryOptions(
                    attempts=http_retry_attempts,
                    http_status_codes=sorted(GEMINI_RETRYABLE_STATUS_CODES),
                ),
            ),
        )

        request_kwargs = {
            "model": model_name,
            "contents": prompt,
            "config": config,
        }

        return client.models.generate_content(**request_kwargs)

    started_at = time.monotonic()
    attempt_history: list[str] = []
    last_error: Optional[Exception] = None
    response = None

    for model_index, model_name in enumerate(active_models, start=1):
        logger.info(
            f"Gemini model attempt chain start: {model_name} "
            f"({model_index}/{len(active_models)}), max attempts {attempts_per_model}"
        )

        for attempt_index in range(1, attempts_per_model + 1):
            try:
                response = _call_gemini(model_name)
                elapsed = int(time.monotonic() - started_at)
                logger.info(
                    f"Gemini call succeeded with model {model_name} "
                    f"on attempt {attempt_index}/{attempts_per_model} after {elapsed}s"
                )
                break
            except Exception as error:
                last_error = error
                status_code = _extract_status_code(error)
                retryable = _is_retryable_error(error)
                attempt_history.append(
                    f"{model_name}#{attempt_index}(status={status_code or 'unknown'}, retryable={retryable})"
                )

                if not retryable:
                    logger.error(
                        f"Gemini call failed with non-retryable error "
                        f"on model {model_name}, attempt {attempt_index}/{attempts_per_model}: {error}"
                    )
                    raise

                model_exhausted = attempt_index == attempts_per_model
                all_models_exhausted = model_exhausted and model_index == len(active_models)

                if all_models_exhausted:
                    break

                if model_exhausted:
                    logger.warning(
                        f"Gemini model {model_name} exhausted after {attempts_per_model} attempts; "
                        "falling back to next model"
                    )
                    break

                logger.warning(
                    f"Gemini API call failed (model={model_name}, attempt={attempt_index}/{attempts_per_model}); "
                    f"retrying in {retry_interval_seconds}s: {error}"
                )
                if retry_interval_seconds > 0:
                    time.sleep(retry_interval_seconds)

        if response is not None:
            break

    if response is None:
        elapsed = int(time.monotonic() - started_at)
        history_text = ", ".join(attempt_history) if attempt_history else "no-attempt-history"
        logger.error(
            "Gemini API call failed after model fallback chain "
            f"(elapsed={elapsed}s, history={history_text}): {last_error}"
        )
        raise RuntimeError("Gemini API call failed after model fallback chain") from last_error

    try:
        report_data = UpdateReportSchema.model_validate_json(response.text.strip())
        return convert_json_to_markdown(report_data.model_dump())
    except Exception as e:
        logger.warning(f"Failed to validate response as schema: {e}. Falling back to default parser.")
        json_response = parse_json_response(response.text, logger)
        if json_response:
            return convert_json_to_markdown(json_response)
        return response.text
