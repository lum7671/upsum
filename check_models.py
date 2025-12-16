import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY를 찾을 수 없습니다. .env 파일을 확인해주세요.")
else:
    genai.configure(api_key=api_key)
    print("사용 가능한 모델 목록:")
    try:
        for model in genai.list_models():
            # 'generateContent'를 지원하는 모델만 필터링하여 출력
            if 'generateContent' in model.supported_generation_methods:
                print(f"- {model.name}")
    except Exception as e:
        print(f"모델 목록을 가져오는 중 오류가 발생했습니다: {e}")
