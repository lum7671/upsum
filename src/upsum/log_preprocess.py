"""로그 전처리 파이프라인: cleaner → parser → generator"""
import json
import subprocess
from pathlib import Path


def run_preprocess_pipeline(log_file: Path) -> dict:
    """
    원본 로그를 전처리하고 결과 파일 경로 반환
    
    Returns:
        {
            'cleaned': Path to .001.cleaned.log,
            'events': Path to .002.events.jsonl,
            'summary': Path to .003.summary.md,
        }
    """
    log_stem = log_file.stem  # update_all-20260520_023109.log.001 -> update_all-20260520_023109.log
    if log_stem.endswith('.log'):
        log_stem = log_stem[:-4]  # .log 제거
    
    log_dir = log_file.parent
    
    cleaned_file = log_dir / f"{log_stem}.001.cleaned.log"
    events_file = log_dir / f"{log_stem}.002.events.jsonl"
    summary_file = log_dir / f"{log_stem}.003.summary.md"
    
    # 1. 노이즈 제거
    from .log_cleaner import is_noise
    with log_file.open(encoding="utf-8") as f, cleaned_file.open("w", encoding="utf-8") as out:
        for line in f:
            if not is_noise(line):
                out.write(line)
    
    # 2. 이벤트 구조화
    from .log_event_parser import parse_event
    with cleaned_file.open(encoding="utf-8") as f, events_file.open("w", encoding="utf-8") as out:
        for line in f:
            event = parse_event(line)
            if event:
                out.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    # 3. 요약 생성
    from .log_summary_generator import generate_summary
    generate_summary(events_file, summary_file)
    
    return {
        'cleaned': cleaned_file,
        'events': events_file,
        'summary': summary_file,
    }


def get_reboot_decision(events_file: Path) -> dict:
    """
    .002.events.jsonl에서 재부팅/재시작 필요 여부 판정
    
    Returns:
        {
            'reboot_needed': bool,
            'reboot_items': [list of items],
            'restart_needed': bool,
            'restart_items': [list of items],
        }
    """
    reboot_items = []
    restart_items = []
    
    with events_file.open(encoding="utf-8") as f:
        for line in f:
            event = json.loads(line)
            if event.get('reboot_relevance'):
                reboot_items.append(event)
            if event.get('service_restart_relevance'):
                restart_items.append(event)
    
    return {
        'reboot_needed': len(reboot_items) > 0,
        'reboot_items': reboot_items,
        'restart_needed': len(restart_items) > 0,
        'restart_items': restart_items,
    }


def load_summary_markdown(summary_file: Path) -> str:
    """
    .003.summary.md 읽기
    """
    if summary_file.exists():
        return summary_file.read_text(encoding="utf-8")
    return ""
