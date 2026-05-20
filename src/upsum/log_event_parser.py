import re
import json
from pathlib import Path

def parse_event(line):
    # 단순 패턴 기반 구조화 예시 (실제 규칙은 추가 보완 필요)
    # category, target, status, action, reboot_relevance, service_restart_relevance, notes
    # APT
    if 'rpi-eeprom' in line and 'Unpacking' in line:
        return {
            'category': 'apt',
            'target': 'rpi-eeprom',
            'status': 'updated',
            'action': 'unpack',
            'reboot_relevance': True,
            'service_restart_relevance': False,
            'notes': line.strip()
        }
    if 'SUCCESS: APT packages updated' in line:
        return {
            'category': 'apt',
            'target': 'all',
            'status': 'success',
            'action': 'updated',
            'reboot_relevance': False,
            'service_restart_relevance': False,
            'notes': line.strip()
        }
    # git repo
    m = re.match(r'=> Updating (/.+?)/git/([^\.]+)\.\.\.', line)
    if m:
        return {
            'category': 'git',
            'target': m.group(2),
            'status': 'start',
            'action': 'pull',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip()
        }
    if 'Fast-forward' in line:
        return {
            'category': 'git',
            'target': None,
            'status': 'success',
            'action': 'fast-forward',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip()
        }
    if 'error: 리베이스로 풀하기 할 수 없습니다' in line:
        return {
            'category': 'git',
            'target': None,
            'status': 'failed',
            'action': 'rebase_failed',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip()
        }
    if 'SUCCESS: Updated' in line and 'using merge pull fallback' in line:
        return {
            'category': 'git',
            'target': None,
            'status': 'success',
            'action': 'merge_fallback',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip()
        }
    if 'ERROR: Failed to update' in line:
        return {
            'category': 'git',
            'target': None,
            'status': 'failed',
            'action': 'update_failed',
            'reboot_relevance': False,
            'service_restart_relevance': True,
            'notes': line.strip()
        }
    # Podman
    if 'UNCHANGED: docker.io/' in line:
        img = line.split(': ')[-1].strip()
        return {
            'category': 'podman',
            'target': img,
            'status': 'unchanged',
            'action': 'pull',
            'reboot_relevance': False,
            'service_restart_relevance': False,
            'notes': line.strip()
        }
    # 기타
    return None

def main():
    src = Path("logs/update_all-20260520_023109.001.cleaned.log")
    dst = Path("logs/update_all-20260520_023109.002.events.jsonl")
    with src.open(encoding="utf-8") as f, dst.open("w", encoding="utf-8") as out:
        for line in f:
            event = parse_event(line)
            if event:
                out.write(json.dumps(event, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
