import json
from pathlib import Path


def generate_summary(src_file: Path, dst_file: Path):
    """
    .002.events.jsonl에서 .003.summary.md 생성
    """
    events = []
    with src_file.open(encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line))

    updated, failed, reboot, restart = [], [], [], []
    for e in events:
        if e['status'] in ('updated', 'success', 'fast-forward', 'merge_fallback'):
            updated.append(e)
        if e['status'] in ('failed',):
            failed.append(e)
        if e.get('reboot_relevance'):
            reboot.append(e)
        if e.get('service_restart_relevance'):
            restart.append(e)

    with dst_file.open("w", encoding="utf-8") as out:
        out.write("# 업데이트 요약\n\n")
        out.write("## 업데이트된 항목\n")
        for e in updated:
            out.write(f"- [{e['category']}] {e['target'] or ''} ({e['action']})\n")
        out.write("\n## 실패한 항목\n")
        for e in failed:
            out.write(f"- [{e['category']}] {e['target'] or ''} ({e['action']})\n")
        out.write("\n## 재부팅 후보\n")
        for e in reboot:
            out.write(f"- [{e['category']}] {e['target'] or ''} ({e['action']})\n")
        out.write("\n## 재실행 후보\n")
        for e in restart:
            out.write(f"- [{e['category']}] {e['target'] or ''} ({e['action']})\n")


def main():
    src = Path("logs/update_all-20260520_023109.002.events.jsonl")
    dst = Path("logs/update_all-20260520_023109.003.summary.md")
    generate_summary(src, dst)


if __name__ == "__main__":
    main()
