# upsum: Update Summarizer

`upsum`은 시스템 업데이트 로그를 분석하고, Gemini AI를 사용하여 요약한 후, 결과를 이메일로 전송하는 파이썬 기반의 CLI 도구입니다. `crontab`과 함께 사용하여 일일 업데이트 보고서를 자동으로 받아보는 데 유용합니다.

---

## 주요 기능 및 고도화 항목

- **동적 Gemini 모델 탐색 및 503/429 장애 대응 (`sysutils.gemini`)**:
  `sysutils` 공통 유틸리티 라이브러리를 활용해 가용 모델 목록을 동적으로 조회하고 헬스체크를 수행합니다. 특정 모델 장애 시 **정상 상태의 다음 Gemini 모델로 자동 Fallback**을 지원합니다.
- **로그 자동 정제 및 토큰 절약**:
  ANSI 터미널 색상 코드, diffstat/경로 나열, 중복 구분선을 자동 제거하여 토큰을 절약하고 요약 품질을 극대화합니다.
- **구조화된 요약 보고서**:
  Gemini AI의 JSON 스키마 모드를 사용하여 **재부팅 필요 여부**, **단순 요약**, **분석**, **예상 항목**, **관리자 액션**을 구조화된 마크다운 형태로 반환합니다.
- **멀티파트 이메일 리포팅**:
  SMTP를 통해 Plain Text 및 HTML 두 가지 포맷으로 깔끔하게 렌더링된 메일을 전송합니다.
- **안전한 실행 옵션**:
  `--dry-run` 옵션을 통해 이메일을 전송하지 않고 결과를 콘솔로 테스트할 수 있습니다.

---

## 📂 프로젝트 구조

```text
upsum/
├── docs/
│   └── architecture_review.md
├── src/
│   └── upsum/
│       ├── __init__.py
│       ├── __main__.py           # CLI 실행 및 전체 워크플로우 제어
│       ├── config.py             # Pydantic Settings 기반 환경변수 검증
│       ├── logs.py               # 최신 로그 탐색 및 텍스트 축약
│       ├── report.py             # Gemini AI 연동 및 보고서 렌더링
│       └── email_sender.py       # SMTP 메일 발송 유틸리티
├── .env.example                  # 환경 변수 샘플 가이드
├── .env                          # API 키 및 SMTP 자격 증명 (비공개)
└── pyproject.toml                # uv 의존성 설정 파일
```

---

## 🛠️ 설치 및 설정

### 1. 프로젝트 클론 및 의존성 설치

이 프로젝트는 [uv](https://docs.astral.sh/uv/)를 사용하여 파이썬 환경 및 의존성을 관리합니다.

```bash
git clone https://github.com/lum7671/upsum.git
cd upsum
uv sync
```

### 2. 환경 변수 설정

`.env.example` 파일을 `.env` 파일로 복사한 후, 자신의 환경에 맞게 수정하세요.

```bash
cp .env.example .env
```

`.env` 예시:

```dotenv
# Google AI Studio에서 발급받은 Gemini API 키 (필수)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# "auto" 또는 "dynamic" 지정 시 사용 가능 모델 동적 헬스체크 수행
GEMINI_MODELS="gemini-3.5-flash,gemini-2.5-flash"
GEMINI_MODEL_ATTEMPTS_PER_MODEL=3
GEMINI_RETRY_INTERVAL_SECONDS=300
GEMINI_HTTP_RETRY_ATTEMPTS=2

# 이메일 발송을 위한 SMTP 서버 정보
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="YOUR_EMAIL@gmail.com"
SMTP_PASSWORD="YOUR_APP_PASSWORD"

# 이메일 발송자/수신자 정보
MAIL_FROM="upsum@example.com"
MAIL_TO="recipient@example.com"
```

---

## 💻 사용법

```bash
# 기본 실행 (최신 로그 파싱 및 이메일 발송)
uv run upsum

# Dry Run (이메일 발송 없이 콘솔 출력)
uv run upsum --dry-run

# 다른 로그 디렉토리 지정
uv run upsum --log-dir /var/log/apt/
```

---

## 📅 crontab 등록하기

매일 새벽 4시에 자동으로 업데이트 요약을 이메일로 받으려면 `crontab -e`에 추가하세요:

```cron
0 4 * * * cd /home/dietpi/git/upsum && /home/dietpi/.local/bin/uv run upsum >> /home/dietpi/logs/upsum_cron.log 2>&1
```