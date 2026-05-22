"""로그 전처리 파이프라인: cleaner"""
import re
from pathlib import Path


def _repo_name_from_path(path_text: str):
    cleaned = path_text.strip()
    cleaned = re.sub(r'\s*\(as [^)]+\)$', '', cleaned)
    cleaned = cleaned.rstrip('/')
    if not cleaned:
        return None
    return Path(cleaned).name or None


def _parse_event(line: str, current_git_target=None):
    if 'rpi-eeprom' in line and 'Unpacking' in line:
        return {
            'category': 'apt',
            'target': 'rpi-eeprom',
            'status': 'updated',
            'action': 'unpack',
            'reboot_relevance': True,
            'service_restart_relevance': False,
            'notes': line.strip(),
        }
    if 'SUCCESS: APT packages updated' in line:
        return {
            'category': 'apt',
            'target': 'all',
            'status': 'success',
            'action': 'updated',
            'reboot_relevance': False,
            'service_restart_relevance': False,
            'notes': line.strip(),
        }
    m = re.match(r'=> Updating (/.+?)\.\.\.', line)
    if m:
        return {
            'category': 'git',
            'target': _repo_name_from_path(m.group(1)),
            'status': 'start',
            'action': 'pull',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    if 'Fast-forward' in line:
        return {
            'category': 'git',
            'target': current_git_target,
            'status': 'success',
            'action': 'fast-forward',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    if 'error: 리베이스로 풀하기 할 수 없습니다' in line:
        return {
            'category': 'git',
            'target': current_git_target,
            'status': 'failed',
            'action': 'rebase_failed',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    m = re.match(r'SUCCESS: Updated (.+?) using merge pull fallback', line)
    if m:
        return {
            'category': 'git',
            'target': _repo_name_from_path(m.group(1)),
            'status': 'success',
            'action': 'merge_fallback',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    if 'SUCCESS: Updated' in line and 'using merge pull fallback' in line:
        return {
            'category': 'git',
            'target': current_git_target,
            'status': 'success',
            'action': 'merge_fallback',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    m = re.match(r'ERROR: Failed to update (.+)$', line)
    if m:
        return {
            'category': 'git',
            'target': _repo_name_from_path(m.group(1)),
            'status': 'failed',
            'action': 'update_failed',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    if 'ERROR: Failed to update' in line:
        return {
            'category': 'git',
            'target': current_git_target,
            'status': 'failed',
            'action': 'update_failed',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip(),
        }
    if 'UNCHANGED: docker.io/' in line:
        img = line.split(': ')[-1].strip()
        return {
            'category': 'podman',
            'target': img,
            'status': 'unchanged',
            'action': 'pull',
            'reboot_relevance': False,
            'service_restart_relevance': False,
            'notes': line.strip(),
        }
    return None


def run_preprocess_pipeline(log_file: Path) -> dict:
    """
    원본 로그를 전처리하고 결과 파일 경로 반환
    
    Returns:
        {
            'cleaned': Path to .001.cleaned.log,
        }
    """
    log_stem = log_file.stem  # update_all-20260520_023109.log.001 -> update_all-20260520_023109.log
    if log_stem.endswith('.log'):
        log_stem = log_stem[:-4]  # .log 제거
    
    log_dir = log_file.parent
    
    cleaned_file = log_dir / f"{log_stem}.001.cleaned.log"
    
    # 1. 노이즈 제거
    from .logs import clean_log_content
    raw_content = log_file.read_text(encoding="utf-8")
    cleaned_content = clean_log_content(raw_content)
    cleaned_file.write_text(cleaned_content, encoding="utf-8")
    
    return {
        'cleaned': cleaned_file,
    }


def get_reboot_decision(cleaned_file: Path) -> dict:
    """
    .001.cleaned.log에서 재부팅/재시작 필요 여부 판정
    
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

    current_git_target = None
    with cleaned_file.open(encoding="utf-8") as f:
        for line in f:
            event = _parse_event(line, current_git_target=current_git_target)
            if not event:
                continue
            if event.get('category') == 'git' and event.get('status') == 'start' and event.get('action') == 'pull':
                current_git_target = event.get('target') or current_git_target
            elif event.get('category') == 'git' and not event.get('target') and current_git_target:
                event['target'] = current_git_target
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
