import os
import re
import time
from typing import Any, List, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# 환경 변수 로드
load_dotenv()


class DynamicGeminiManager:
    def __init__(self, api_key: Optional[str] = None):
        """Gemini Client 초기화 (google-genai SDK 사용)"""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        
        self.client = genai.Client(api_key=self.api_key)

    def fetch_supported_models(self) -> List[str]:
        """API 서버로부터 'generateContent'를 지원하는 전체 모델 ID 목록을 동적 조회합니다."""
        supported_models = []
        try:
            for m in self.client.models.list():
                if hasattr(m, 'supported_actions') and m.supported_actions and "generateContent" in m.supported_actions:
                    clean_name = m.name.replace("models/", "") if m.name.startswith("models/") else m.name
                    if any(exclude in clean_name for exclude in ["-tts", "lyria", "robotics", "computer-use"]):
                        continue
                    supported_models.append(clean_name)
        except Exception as e:
            print(f"[Error] 모델 목록 동적 수집 실패: {e}")
        
        return supported_models

    def _extract_error_code(self, error: Exception) -> Optional[int]:
        """APIError 및 기타 예외 객체에서 HTTP 상태 코드를 안전하게 추출합니다."""
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

    def probe_model_health(self, model_name: str, timeout_sec: float = 5.0) -> bool:
        """단일 모델에 경량 요청(Ping)을 보내 503 및 과부하 상태를 실시간 검증합니다."""
        try:
            start_time = time.time()
            response = self.client.models.generate_content(
                model=model_name,
                contents="ping",
            )
            elapsed = time.time() - start_time
            if response.text and elapsed <= timeout_sec:
                return True
        except APIError as e:
            err_code = self._extract_error_code(e)
            if err_code in [503, 429]:
                print(f"[HealthCheck] 모델 {model_name} 일시적 불능 상태 (HTTP {err_code})")
            else:
                print(f"[HealthCheck] 모델 {model_name} 오류: {e}")
        except Exception as e:
            print(f"[HealthCheck] 모델 {model_name} 응답 실패: {e}")
            
        return False

    def get_healthy_models(self, candidate_models: Optional[List[str]] = None) -> List[str]:
        """동적으로 모델 목록을 가져온 후, 실질적으로 503 에러 없이 응답하는 모델만 선별합니다."""
        if not candidate_models:
            candidate_models = self.fetch_supported_models()

        healthy_models = []
        print(f"총 {len(candidate_models)}개 후보 모델에 대한 Health Check 진행 중...")
        
        for model in candidate_models:
            if self.probe_model_health(model):
                print(f"  ✓ [정상] {model}")
                healthy_models.append(model)
            else:
                print(f"  ✗ [제외] {model}")

        return healthy_models

    def generate_content_with_fallback(
        self, 
        prompt: str, 
        preferred_models: Optional[List[str]] = None,
        config: Optional[Any] = None
    ) -> Tuple[Any, str]:
        """
        503 대응 핵심 메소드:
        우선순위 모델 리스트를 순회하며 503/429/400 발생 시 동적으로 수집된 다음 모델로 Fallback을 수행합니다.
        
        Returns:
            (response_object, 사용된_모델명)
        """
        target_models = preferred_models or self.get_healthy_models()

        if not target_models:
            raise RuntimeError("현재 사용 가능한 정상 상태의 Gemini 모델이 없습니다.")

        attempted_models = set()

        for model_name in target_models:
            attempted_models.add(model_name)
            try:
                print(f"[{model_name}] 호출 시도 중...")
                kwargs = {"model": model_name, "contents": prompt}
                if config is not None:
                    kwargs["config"] = config

                response = self.client.models.generate_content(**kwargs)
                if response.text:
                    return response, model_name
            except APIError as e:
                err_code = self._extract_error_code(e)
                if err_code in [503, 429, 400, 404]:
                    print(f"⚠️ [{model_name}] HTTP {err_code} 에러 발생. 다음 모델로 Fallback합니다.")
                    continue
                else:
                    raise e
            except Exception as e:
                print(f"⚠️ [{model_name}] 오류 발생 ({e}). 다음 모델로 전환합니다.")
                continue

        # 만약 우선순위 모델이 모두 실패한 경우, 전체 동적 모델 탐색 후 Fallback 2차 시도
        print("⚠️ 설정된 우선순위 모델 모두 실패. 동적 헬스체크 모델 목록으로 2차 Fallback 진행...")
        dynamic_healthy = [m for m in self.get_healthy_models() if m not in attempted_models]
        
        for model_name in dynamic_healthy:
            try:
                print(f"[{model_name}] (동적 Fallback) 호출 시도 중...")
                kwargs = {"model": model_name, "contents": prompt}
                if config is not None:
                    kwargs["config"] = config

                response = self.client.models.generate_content(**kwargs)
                if response.text:
                    return response, model_name
            except Exception as e:
                print(f"⚠️ [{model_name}] 동적 Fallback 실패 ({e}).")
                continue

        raise RuntimeError("모든 후보 Gemini 모델 호출이 실패했습니다.")


if __name__ == "__main__":
    manager = DynamicGeminiManager()
    all_models = manager.fetch_supported_models()
    print("동적 수집된 모델 목록 (총 {}개):".format(len(all_models)), all_models)
    
    try:
        response, used_model = manager.generate_content_with_fallback("안녕하세요! 간단한 자기소개 부탁드립니다.")
        print(f"\n=== 성공 (사용 모델: {used_model}) ===")
        print(response.text)
    except Exception as err:
        print(f"처리 실패: {err}")
