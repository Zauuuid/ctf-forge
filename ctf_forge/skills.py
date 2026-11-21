"""Fetch the upstream CTF skills and link them into an agent's skills directory."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .core import HOME, STORE, Runner

UPSTREAM_URL = "https://github.com/ljagiello/ctf-skills.git"
KIT_MARKETPLACE = "MysterionRise/ctf-kit"
MARKER = ".ctf-forge-copy"

AGENT_DIRS: Dict[str, Path] = {
    "claude": HOME / ".claude" / "skills",
}


def resolve_target(agent: Optional[str], directory: Optional[str]) -> Path:
    if directory:
        return Path(directory).expanduser()
    return AGENT_DIRS[agent or "claude"]


def store_path(source: str) -> Path:
    name = source.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return STORE / "upstream" / (name or "skills")


def fetch(r: Runner, source: str, ref: Optional[str], update: bool,
          store: Optional[Path] = None) -> Optional[Path]:
    """Clone the source repo, or pull it when it already exists."""
    dest = store or store_path(source)
    if dest.exists():
        if update:
            if not r.run(["git", "-C", str(dest), "pull", "--ff-only"]):
                r.fail("git pull failed in {}".format(dest))
        return dest
    if not r.dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    if not r.run(cmd + [source, str(dest)]):
        r.fail("could not clone {}".format(source))
        return None
    return dest


def skill_dirs(root: Path) -> List[Path]:
    """Directories directly under root, or under root/skills, that hold a SKILL.md."""
    found: List[Path] = []
    for base in (root, root / "skills"):
        if base.is_dir():
            for child in sorted(base.iterdir()):
                if (child / "SKILL.md").is_file() and child not in found:
                    found.append(child)
    return found


def install(r: Runner, target: Path, source: str = UPSTREAM_URL, ref: Optional[str] = None,
            copy: bool = False, update: bool = False,
            store: Optional[Path] = None) -> List[str]:
    """Link (or copy) every upstream skill into the target directory."""
    root = fetch(r, source, ref, update, store)
    if root is None:
        return []
    if r.dry_run and not root.exists():
        r.say("  (dry-run) would link each skill folder into {}".format(target))
        return []
    target.mkdir(parents=True, exist_ok=True)
    installed: List[str] = []
    for skill in skill_dirs(root):
        link = target / skill.name
        if link.is_symlink():
            if link.resolve() == skill.resolve():
                installed.append(skill.name)
                continue
            r.say("  ~ {} points elsewhere, skipped".format(link))
            continue
        if link.exists():
            if (link / MARKER).exists():
                shutil.rmtree(link)
            else:
                r.say("  ~ {} exists and is not managed by ctf-forge, skipped".format(link))
                continue
        if copy:
            _copy(skill, link)
        else:
            try:
                link.symlink_to(skill, target_is_directory=True)
            except OSError:
                _copy(skill, link)
        installed.append(skill.name)
    r.say("  {} skills available in {}".format(len(installed), target))
    return installed


def _copy(src: Path, dest: Path) -> None:
    shutil.copytree(src, dest)
    (dest / MARKER).write_text("managed by ctf-forge\n")


def installed(target: Path) -> List[str]:
    if not target.is_dir():
        return []
    return sorted(p.name for p in target.iterdir()
                  if p.name.startswith("ctf-") or p.name == "solve-challenge")


def install_kit(r: Runner) -> None:
    """Add the ctf-kit Claude Code plugin when the claude CLI is present."""
    if not r.have("claude"):
        r.fail("ctf-kit plugin skipped: claude CLI not found")
        return
    r.run(["claude", "plugin", "marketplace", "add", KIT_MARKETPLACE])
    if not r.run(["claude", "plugin", "install", "ctf-kit@ctf-kit"]):
        r.fail("ctf-kit plugin: inside claude run /plugin marketplace add {} then "
               "/plugin install ctf-kit@ctf-kit".format(KIT_MARKETPLACE))
