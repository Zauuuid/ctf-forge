"""Optional markdown memory vault. Works with Obsidian but needs nothing special."""
from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

TEMPLATE = Path(__file__).resolve().parent / "vault_template"


def slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "-", text.strip(), flags=re.UNICODE).strip("-")
    return cleaned or "untitled"


def init(vault: Path) -> int:
    """Copy the vault template without overwriting existing files. Returns files created."""
    created = 0
    for src in sorted(TEMPLATE.rglob("*")):
        if not src.is_file():
            continue
        dest = vault / src.relative_to(TEMPLATE)
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        created += 1
    return created


def log(vault: Path, event: str, name: str, category: str = "", status: str = "unsolved",
        flag: str = "", summary: str = "") -> Path:
    """Create or extend a challenge note and add a line to today's journal."""
    today = date.today().isoformat()
    note = vault / "Challenges" / "{}-{}.md".format(slug(event), slug(name))
    note.parent.mkdir(parents=True, exist_ok=True)
    if note.exists():
        with note.open("a", encoding="utf-8") as fh:
            fh.write("\n## Update {}\n\n- status: {}\n".format(today, status))
            if flag:
                fh.write("- flag: `{}`\n".format(flag))
            if summary:
                fh.write("\n{}\n".format(summary))
    else:
        body = (
            "---\nevent: {event}\ncategory: {category}\nstatus: {status}\ndate: {today}\n---\n"
            "# {name}\n\n## Summary\n\n{summary}\n\n## Flag\n\n{flag}\n\n## Lessons\n\n"
        ).format(event=event, category=category, status=status, today=today, name=name,
                 summary=summary, flag="`{}`".format(flag) if flag else "")
        note.write_text(body, encoding="utf-8")
    journal = vault / "Journal" / "{}.md".format(today)
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as fh:
        fh.write("- [[Challenges/{}|{}]] ({}) {}\n".format(note.stem, name, status, category))
    return note


def recall(vault: Path, words: List[str], limit: int = 5) -> List[Tuple[Path, int, List[str]]]:
    """Rank notes by keyword hits. Returns (path, score, matching lines)."""
    needles = [w.lower() for w in words if w.strip()]
    results: List[Tuple[Path, int, List[str]]] = []
    if not needles:
        return results
    for path in sorted(vault.rglob("*.md")):
        if "Templates" in path.parts or ".obsidian" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lowered = text.lower()
        score = sum(lowered.count(n) for n in needles)
        score += 3 * sum(1 for n in needles if n in path.stem.lower())
        if score == 0:
            continue
        lines = [ln.strip() for ln in text.splitlines()
                 if any(n in ln.lower() for n in needles)][:3]
        results.append((path, score, lines))
    results.sort(key=lambda item: (-item[1], str(item[0])))
    return results[:limit]


def resolve_vault(arg: Optional[str]) -> Path:
    return Path(arg).expanduser() if arg else Path.home() / "CTFMemory"
