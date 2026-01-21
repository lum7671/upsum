# upsum: Update Summarizer

`upsum`은 시스템 업데이트 로그를 분석하고, Gemini AI를 사용하여 요약한 후, 결과를 이메일로 전송하는 파이썬 기반의 CLI 도구입니다. `crontab`과 함께 사용하여 일일 업데이트 보고서를 자동으로 받아보는 데 유용합니다.

## 주요 기능

-   지정된 디렉토리에서 최신 로그 파일을 자동으로 감지합니다.
-   로그를 분석하여 **재부팅 필요 여부**와 **업데이트된 패키지 목록(버전 포함)**을 추출합니다.
-   Google Gemini API를 통해 자연스러운 한국어 요약문을 생성합니다.
-   SMTP를 통해 지정된 이메일 주소로 요약 보고서를 발송합니다.
-   `--dry-run` 옵션을 통해 이메일을 보내지 않고 결과만 확인할 수 있습니다.

## 시스템 요구사항

-   **Python**: 3.10 이상
-   **운영체제**: Linux, macOS (테스트 환경: DietPi on Raspberry Pi 4B)
-   **패키지 관리자**: [uv](https://docs.astral.sh/uv/) (권장) 또는 pip

## 사전 준비

### Google Gemini API 키 발급

1. [Google AI Studio](https://aistudio.google.com/apikey)에 접속합니다.
2. Google 계정으로 로그인합니다.
3. "Get API Key" 또는 "Create API Key" 버튼을 클릭합니다.
4. 생성된 API 키를 복사하여 안전하게 보관합니다.

> **참고**: API 키는 민감한 정보입니다. 절대 공개 저장소에 커밋하지 마세요.

### Gmail SMTP 설정 (선택사항)

Gmail을 통해 이메일을 보내려면 다음 설정이 필요합니다:

1. **2단계 인증 활성화**
   - [Google 계정 보안 설정](https://myaccount.google.com/security)에서 2단계 인증을 활성화합니다.

2. **앱 비밀번호 생성**
   - [앱 비밀번호 페이지](https://myaccount.google.com/apppasswords)로 이동합니다.
   - "앱 선택" → "메일" 선택
   - "기기 선택" → "기타(맞춤 이름)" 선택 후 "upsum" 입력
   - 생성 버튼을 클릭하고 16자리 비밀번호를 복사합니다.

3. 이 앱 비밀번호를 `.env` 파일의 `SMTP_PASSWORD`에 사용합니다.

> **다른 SMTP 서버 사용**: Gmail 외 다른 SMTP 서버(Naver, Daum, 자체 메일 서버 등)를 사용할 수도 있습니다. 해당 서버의 SMTP 설정 정보를 확인하세요.

## 설치 및 설정

### 1. 프로젝트 클론 및 의존성 설치

이 프로젝트는 [uv](https://docs.astral.sh/uv/)를 사용하여 파이썬 환경 및 의존성을 관리합니다.

```bash
git clone https://github.com/lum7671/upsum.git
cd upsum
uv sync
```

> **참고**: uv가 설치되지 않은 경우, 다음 명령어로 설치하세요:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

### 2. 환경 변수 설정

프로그램은 민감한 정보(API 키, 이메일 계정 등)를 환경 변수로부터 읽어옵니다. 프로젝트 루트 디렉토리에 있는 `.env.example` 파일을 `.env` 파일로 복사한 후, 내용을 자신의 환경에 맞게 수정하세요.

```bash
cp .env.example .env
```

`.env` 파일을 열고 다음 변수들의 값을 채워주세요.

```dotenv
# .env

# Google AI Studio에서 발급받은 Gemini API 키 (필수)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# 이메일 발송을 위한 SMTP 서버 정보
SMTP_HOST="smtp.gmail.com"         # SMTP 서버 주소 (필수)
SMTP_PORT=587                       # SMTP 포트 번호 (기본값: 587)
SMTP_USER="YOUR_EMAIL@gmail.com"   # SMTP 사용자명 (선택사항, 인증 필요시)
SMTP_PASSWORD="YOUR_APP_PASSWORD"  # SMTP 비밀번호 (선택사항, Gmail 앱 비밀번호 사용)

# 이메일 발송자/수신자 정보
MAIL_FROM="upsum@example.com"      # 발신자 주소 (선택사항, 기본값: upsum@example.com)
MAIL_TO="recipient@example.com"    # 수신자 주소 (필수)
```

**환경 변수 설명:**

| 변수명 | 필수 여부 | 설명 |
|--------|----------|------|
| `GEMINI_API_KEY` | ✅ 필수 | Google AI Studio에서 발급받은 API 키 |
| `SMTP_HOST` | ✅ 필수 | SMTP 서버 주소 (예: smtp.gmail.com) |
| `SMTP_PORT` | 선택 | SMTP 포트 (기본값: 587, 1-65535 범위) |
| `SMTP_USER` | 선택 | SMTP 인증 사용자명 (인증 필요시) |
| `SMTP_PASSWORD` | 선택 | SMTP 인증 비밀번호 (Gmail 앱 비밀번호) |
| `MAIL_FROM` | 선택 | 발신자 이메일 주소 |
| `MAIL_TO` | ✅ 필수 | 수신자 이메일 주소 |

## 사용법

프로그램은 `upsum`이라는 CLI 명령어로 실행할 수 있습니다.

### 기본 실행

최신 로그 파일을 요약하고 이메일을 전송합니다. 로그는 기본적으로 `~/logs` 디렉토리에서 찾습니다.

```bash
uv run upsum
```

### Dry Run (테스트 실행)

이메일을 보내지 않고, 생성된 요약문을 터미널에서 확인하고 싶을 때 사용합니다.

```bash
uv run upsum --dry-run
```

### 다른 로그 디렉토리 지정

기본값이 아닌 다른 디렉토리에 있는 로그를 처리하려면 `--log-dir` 옵션을 사용하세요.

```bash
uv run upsum --log-dir /var/log/apt/
```

## 출력 형식

### JSON 구조화된 보고서

`upsum`은 Gemini API의 JSON 모드를 사용하여 구조화된 보고서를 생성합니다. 내부적으로 다음과 같은 JSON 스키마를 사용합니다:

```json
{
  "title": "YYYY년 MM월 DD일 시스템 업데이트 보고서",
  "reboot_required": "시스템 재부팅이 필요합니다 / 필요하지 않습니다",
  "summary": "주요 업데이트·설치·삭제·버전 변경·캐시 정리를 사실만으로 정리",
  "analysis": "로그에 나타난 버전 최신화 상태, 경고, 운영 영향 분석",
  "near_future": "로그에서 추정 가능한 모니터링 항목, 예상 업데이트",
  "actions": [
    "우선순위별 관리자 액션 항목 1",
    "우선순위별 관리자 액션 항목 2",
    ...
  ]
}
```

### Markdown 변환

JSON 응답은 자동으로 Markdown 형식으로 변환되어 이메일로 전송됩니다:

```markdown
# YYYY년 MM월 DD일 시스템 업데이트 보고서

**재부팅 필요 여부:** 시스템 재부팅이 필요합니다

## 단순 요약(팩트)

주요 업데이트 및 변경 사항...

## 분석

버전 최신화 상태 및 운영 영향...

## 가까운 미래/예상

모니터링 필요 항목...

## 관리자 액션

- 액션 항목 1
- 액션 항목 2
```

이메일은 **Plain Text**와 **HTML** 두 가지 형식으로 동시에 전송되어 다양한 이메일 클라이언트에서 올바르게 표시됩니다.

## 작동 원리

### 데이터 처리 흐름

1. **로그 파일 탐색**: 지정된 디렉토리(`~/logs`)에서 가장 최근에 수정된 로그 파일을 자동으로 찾습니다.

2. **로그 파싱**: 
   - 재부팅 필요 여부 감지 (`reboot is required`, `rebooting` 키워드 검색)
   - 로그 내용 전체를 읽어들입니다 (3000자 초과 시 요약)

3. **프롬프트 생성**: 
   - `src/upsum/prompt_template.txt` 템플릿에 로그 데이터 삽입
   - 20년 경력 Linux 시스템 엔지니어 페르소나로 분석 요청
   - DietPi 특화 분석 (Raspberry Pi 4B 환경)

4. **Gemini API 호출**:
   - 모델: `gemini-2.5-flash`
   - JSON 스키마 모드로 구조화된 응답 요청
   - 타임아웃: 30초, 최대 3회 재시도 (지수 백오프)

5. **응답 처리**:
   - JSON 파싱 (코드 펜스 자동 제거)
   - 파싱 실패 시 원본 텍스트로 fallback
   - Markdown 형식으로 변환

6. **이메일 전송**:
   - SMTP를 통해 HTML + Plain Text 멀티파트 메시지 발송
   - 타임아웃: 15초, 최대 3회 재시도
   - 인증 실패 시 즉시 종료 (재시도 없음)

7. **로깅**: 모든 작업을 syslog(`/dev/log`)에 기록 (macOS에서는 stderr로 fallback)

### 에러 처리 및 재시도 로직

**Gemini API 재시도:**
- 최대 3회 시도
- 대기 시간: 1초 → 2초 → 4초 (지수 백오프)
- 타임아웃: 30초

**SMTP 재시도:**
- 최대 3회 시도
- 대기 시간: 1초 → 2초 → 4초 (지수 백오프)
- 타임아웃: 15초
- 인증 오류(`SMTPAuthenticationError`)는 재시도 없이 즉시 실패

모든 오류는 syslog와 표준 에러 출력으로 기록됩니다.

## 고급 설정

### 프롬프트 커스터마이징

보고서 생성 방식을 변경하려면 `src/upsum/prompt_template.txt` 파일을 수정하세요.

**사용 가능한 플레이스홀더:**
- `{formatted_date}`: 보고서 날짜 (예: 2026년 01월 21일)
- `{log_content}`: 로그 파일 내용
- `{reboot_text}`: 재부팅 필요 여부 메시지
- `{dietpi_release_notes}`: DietPi 업데이트 정보 (자동 감지)

**예시 수정:**
```
당신은 보안 전문가입니다. 다음 로그에서 보안 취약점과 업데이트를 중심으로 분석해주세요.

날짜: {formatted_date}
재부팅: {reboot_text}

로그:
{log_content}
```

### 타임아웃 및 재시도 설정 변경

코드에서 다음 상수를 수정하여 동작을 조정할 수 있습니다:

**`src/upsum/report.py`:**
```python
GEMINI_TIMEOUT_SECONDS = 30    # Gemini API 타임아웃 (초)
GEMINI_MAX_RETRIES = 3         # 최대 재시도 횟수
GEMINI_BACKOFF_SECONDS = 2     # 백오프 기본값 (지수 증가)
```

**`src/upsum/email_sender.py`:**
```python
SMTP_TIMEOUT_SECONDS = 15      # SMTP 타임아웃 (초)
SMTP_MAX_RETRIES = 3           # 최대 재시도 횟수
SMTP_BACKOFF_SECONDS = 2       # 백오프 기본값 (지수 증가)
```

### 로그 크기 제한 조정

기본적으로 3000자가 넘는 로그는 자동으로 잘립니다. 이를 변경하려면 `src/upsum/logs.py`의 `summarize_log_for_prompt()` 함수를 수정하세요:

```python
if len(log_content) > 3000:  # 이 값을 변경
    return log_content[:3000] + "\n\n[로그가 길어서 일부만 표시됨]"
```

## 문제 해결 (Troubleshooting)

### 1. `GEMINI_API_KEY` 관련 오류

**오류 메시지:**
```
ERROR Missing required environment variable: GEMINI_API_KEY
```

**해결 방법:**
- `.env` 파일이 프로젝트 루트에 존재하는지 확인
- `GEMINI_API_KEY` 값이 올바르게 설정되었는지 확인
- API 키 앞뒤 공백이 없는지 확인
- [Google AI Studio](https://aistudio.google.com/apikey)에서 API 키를 재확인

### 2. Gemini API 호출 실패

**오류 메시지:**
```
ERROR Gemini API call failed after 3 attempts: Models.generate_content() got an unexpected keyword argument 'generation_config'
```

**원인:** `google-genai` 라이브러리 버전 불일치

**해결 방법:**
```bash
# 라이브러리 업데이트
uv sync --upgrade

# 또는 특정 버전으로 고정
# pyproject.toml에서: "google-genai>=1.56.0,<2.0.0"
```

### 3. SMTP 인증 실패

**오류 메시지:**
```
ERROR SMTP 인증 실패. 사용자 이름과 비밀번호를 확인해주세요.
```

**Gmail 사용 시 확인 사항:**
- 2단계 인증이 활성화되어 있는지 확인
- **일반 비밀번호가 아닌 앱 비밀번호**를 사용하고 있는지 확인
- `SMTP_USER`에 전체 이메일 주소(예: `user@gmail.com`) 입력
- 앱 비밀번호의 공백을 제거했는지 확인

### 4. 로그 파일을 찾을 수 없음

**오류 메시지:**
```
ERROR No log files found in /home/user/logs. Nothing to do.
```

**해결 방법:**
- 로그 디렉토리가 실제로 존재하는지 확인: `ls -la ~/logs`
- `--log-dir` 옵션으로 올바른 경로 지정
- `--log-file` 옵션으로 특정 파일 직접 지정

### 5. JSON 파싱 실패

**경고 메시지:**
```
WARNING JSON parsing failed; returning raw text fallback
```

**영향:** 정상 작동하지만 Markdown 형식이 완벽하지 않을 수 있음

**해결 방법:**
- 프롬프트 템플릿이 JSON 출력을 명확히 요청하는지 확인
- Gemini API 응답을 `--dry-run`으로 확인
- 필요 시 `src/upsum/report.py`의 `parse_json_response()` 함수 디버깅

### 6. Crontab에서 실행 안 됨

**확인 사항:**
- Rye 전체 경로 사용: `which rye`로 확인
- 프로젝트 경로 절대 경로 사용: `-p /full/path/to/upsum`
- 로그 파일 확인: `cat /home/dietpi/logs/upsum_cron.log`
- 환경 변수가 cron 환경에서 로드되는지 확인 (`.env` 파일 사용 권장)

**디버깅:**
```bash
# 수동으로 동일한 명령어 실행
cd /home/dietpi/git/upsum && /home/dietpi/.local/bin/uv run upsum --dry-run
```

## 보안 권장사항

### .env 파일 보호

```bash
# .env 파일 권한 제한 (소유자만 읽기/쓰기)
chmod 600 .env

# .gitignore에 추가되었는지 확인
cat .gitignore | grep .env
```

### API 키 관리

- ✅ API 키를 코드에 하드코딩하지 마세요
- ✅ `.env` 파일을 절대 Git에 커밋하지 마세요
- ✅ 공유 서버에서는 환경 변수 파일 권한을 `600`으로 설정하세요
- ✅ 정기적으로 API 키를 갱신하세요
- ✅ 사용하지 않는 API 키는 즉시 삭제하세요

### SMTP 비밀번호

- ✅ Gmail의 경우 반드시 앱 비밀번호를 사용하세요 (일반 비밀번호 사용 금지)
- ✅ 앱 비밀번호는 각 애플리케이션별로 별도 생성하세요
- ✅ 더 이상 사용하지 않는 앱 비밀번호는 즉시 취소하세요

## crontab에 등록하기

매일 새벽 4시에 자동으로 업데이트 요약을 이메일로 받으려면 `crontab -e`를 실행하고 다음 라인을 추가하세요. `uv`의 경로와 프로젝트 경로를 자신의 환경에 맞게 수정해야 합니다.

```crontab
# 매일 새벽 4시에 upsum 실행
0 4 * * * cd /home/dietpi/git/upsum && /home/dietpi/.local/bin/uv run upsum > /home/dietpi/logs/upsum_cron.log 2>&1
```

**참고:** `crontab`에서 `uv run`을 실행하려면 전체 경로를 명시해주는 것이 안정적입니다. `which uv` 명령어로 `uv`의 설치 경로를 확인할 수 있습니다. `cd` 명령으로 프로젝트 디렉토리로 이동한 후 실행해야 올바르게 작동합니다.