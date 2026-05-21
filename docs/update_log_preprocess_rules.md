# update_all-20260520_023109.log.001 전처리 규칙 설계

## 1. 섹션 분리 기준
- "==>", "=>", "==================================>", "SUCCESS:", "ERROR:", "UNCHANGED:", "Fast-forward", "fallback" 등 주요 신호로 구분
- APT, DietPi, Homebrew, Zig, uv, Rust, Node, Zsh, git, Podman, cleanup, summary 등 주요 블록별로 분리

## 2. 이벤트 정규화
- 각 줄/이벤트를 아래 필드로 구조화
  - category: apt, git, podman, cleanup, runtime-tool 등
  - target: 패키지명, repo명, image명 등
  - status: success, failed, unchanged, warning, fallback
  - action: updated, pull, rebase_failed, merge_fallback, cache_cleaned 등
  - reboot_relevance: true/false
  - service_restart_relevance: true/false
  - notes: 자유 텍스트

## 3. 노이즈 제거 규칙
- 다운로드 진행률, Fetched, Reading package lists, debconf, (데이터베이스 읽는중 ...), 버전/해시만 긴 줄, 중복된 SUCCESS/UNCHANGED/이미 업데이트 상태입니다 등 반복 메시지 제거
- 상세 경로/URL/해시/카운트 등 핵심 이벤트가 아닌 정보 삭제
- 동일한 성공 메시지의 중복 줄 제거

## 4. 재부팅/재시작 신호 태깅
- rpi-eeprom, 커널, libc, systemd, firmware 등 → reboot_relevance: true
- 일반 패키지 → reboot_relevance: maybe
- git/podman 등 서비스 코드 변경 → service_restart_relevance: true
- podman image UNCHANGED → service_restart_relevance: false

## 5. 출력 포맷
- 구조화된 이벤트별 JSONL/CSV
- human summary(업데이트/실패/재부팅/재시작 후보)

---

이 규칙을 기반으로 파서/전처리 코드를 작성할 것.
