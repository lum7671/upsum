# Copilot Instructions for upsum

이 문서는 upsum 저장소에서 AI 코딩 에이전트가 빠르게 작업을 시작하기 위한 최소 지침입니다.
상세 사용자 문서는 README를 우선 확인하고, 여기에는 코드 작업 시 바로 필요한 규칙만 유지합니다.

## 1) 프로젝트 한 줄 요약

upsum은 시스템 업데이트 로그를 정제하고, Gemini로 한국어 요약 보고서를 생성해 SMTP로 메일 발송하는 Python CLI입니다.

## 2) 빠른 실행 명령

```bash
# 의존성 동기화
uv sync

# 기본 실행
uv run upsum

# 메일 미발송 테스트
uv run upsum --dry-run

# 특정 로그 파일 테스트
uv run upsum --log-file /absolute/path/to/log.log --dry-run
```

## 3) 코드 경계 (수정 위치 가이드)

- src/upsum/__main__.py: 메인 오케스트레이션 (arg -> config -> logs -> report -> email)
- src/upsum/config.py: 인자 파싱, .env 로딩, ConfigError, 로거 생성
- src/upsum/logs.py: 로그 탐색/정제, reboot 감지, 프롬프트 입력용 로그 요약
- src/upsum/report.py: Gemini 호출, JSON 파싱/검증, Markdown 변환
- src/upsum/email_sender.py: SMTP 전송, HTML/Plain 멀티파트 구성, 재시도
- src/upsum/prompt_template.txt: 요약 프롬프트 템플릿

## 4) 변경 시 반드시 지킬 규칙

- 사용자 메시지는 한국어 중심으로 유지합니다.
- 민감정보(API 키, SMTP 비밀번호)를 로그로 남기지 않습니다.
- 설정 실패는 ConfigError로 처리해 종료 코드 1을 보장합니다.
- 재시도 정책은 기존 지수 백오프 패턴을 유지합니다.
- 파일 경로는 Path 기반으로 처리하고, 템플릿은 모듈 기준 상대 경로를 사용합니다.

## 5) 자주 깨지는 포인트

- prompt_template.txt에서 중괄호는 str.format 충돌을 일으킬 수 있습니다.
  - 템플릿 본문에서 리터럴 중괄호가 필요하면 {{ 및 }} 로 이스케이프합니다.
- logs.py의 정규식 정제 규칙 변경 시 핵심 업데이트 라인이 삭제되지 않는지 확인합니다.
- JSON 파싱 실패 fallback 동작(response.text 반환)을 제거하지 않습니다.

## 6) 빠른 검증 체크리스트

코드 변경 후 최소 아래를 확인합니다.

1. uv run upsum --dry-run
2. 오류 발생 시 로그에 원인과 재시도 횟수가 드러나는지 확인
3. 생성된 요약 Markdown 구조(제목/섹션/액션 목록) 확인

## 7) 참조 문서 (링크 우선)

- 사용자 설치/운영 가이드: [README.md](../README.md)
- 작업 백로그: [TODO.md](../TODO.md)
- 로그 샘플: [logs/update_all-20260515_023109.log.001](../logs/update_all-20260515_023109.log.001)
- 샘플 보고서: [src/upsum/sample_report.md](../src/upsum/sample_report.md)

## 8) 에이전트 작업 원칙

- 큰 리팩터링보다 작은 단위 변경을 우선합니다.
- 기존 공개 인터페이스(CLI 옵션, env 변수명)를 불필요하게 바꾸지 않습니다.
- README와 동작이 어긋나는 변경을 하면 README도 함께 업데이트합니다.
