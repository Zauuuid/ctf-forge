"""Shared helpers: distro detection and a small command runner."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Union

HOME = Path.home()
STORE = HOME / ".ctf-forge"

Command = Union[str, Sequence[str]]


def detect_distro() -> str:
    """Return arch, debian, macos or unknown."""
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        info = {}
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    info[key] = value.strip().strip('"')
        except OSError:
            pass
        ids = "{} {}".format(info.get("ID", ""), info.get("ID_LIKE", "")).lower()
        if any(x in ids for x in ("arch", "endeavouros", "manjaro")):
            return "arch"
        if any(x in ids for x in ("debian", "ubuntu", "kali")):
            return "debian"
    return "unknown"


class Runner:
    """Runs commands, supports dry-run, and remembers failures."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.failed: List[str] = []
        self.env = os.environ.copy()
        self.env.setdefault("DEBIAN_FRONTEND", "noninteractive")
        self.base_path = self.env.get("PATH", "")
        self.extra_paths: List[str] = []
        self.refresh_path()

    def refresh_path(self) -> None:
        """Add user-level bin directories (pipx, go, gems, Arch perl) to PATH."""
        candidates = [HOME / ".local" / "bin", HOME / "go" / "bin",
                      Path("/usr/bin/vendor_perl")]
        ruby = shutil.which("ruby", path=self.env.get("PATH"))
        if ruby:
            try:
                out = subprocess.run([ruby, "-e", "puts Gem.user_dir"], capture_output=True,
                                     text=True, timeout=15).stdout.strip()
                if out:
                    candidates.append(Path(out) / "bin")
            except (OSError, subprocess.SubprocessError):
                pass
        self.extra_paths = [str(p) for p in candidates if p.is_dir()]
        self.env["PATH"] = os.pathsep.join(self.extra_paths + [self.base_path])

    @property
    def is_root(self) -> bool:
        return hasattr(os, "geteuid") and os.geteuid() == 0

    @property
    def sudo(self) -> List[str]:
        if self.is_root:
            return []
        return ["sudo"] if shutil.which("sudo") else []

    def say(self, msg: str = "") -> None:
        print(msg, flush=True)

    def step(self, title: str) -> None:
        self.say("\n==> {}".format(title))

    def fail(self, what: str) -> None:
        self.failed.append(what)
        self.say("  !! {}".format(what))

    def have(self, binary: str) -> bool:
        return shutil.which(binary, path=self.env["PATH"]) is not None

    def run(self, cmd: Command, shell: bool = False, cwd: Optional[str] = None,
            quiet: bool = False) -> bool:
        shown = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
        if not quiet or self.dry_run:
            self.say("  $ {}".format(shown))
        if self.dry_run:
            return True
        try:
            result = subprocess.run(
                cmd, shell=shell, cwd=cwd, env=self.env,
                stdout=subprocess.DEVNULL if quiet else None,
                stderr=subprocess.DEVNULL if quiet else None,
            )
            return result.returncode == 0
        except (FileNotFoundError, NotADirectoryError):
            return False

    def run_root(self, cmd: Sequence[str], quiet: bool = False) -> bool:
        return self.run(self.sudo + list(cmd), quiet=quiet)
