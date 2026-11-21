"""Bundled tool-runner scripts (derived from ctf-kit) that print JSON summaries."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Sequence

KIT_DIR = Path(__file__).resolve().parent / "kit"


def list_scripts() -> List[str]:
    names: List[str] = []
    for script in sorted(KIT_DIR.glob("*/*.sh")):
        if script.parent.name != "_lib":
            names.append("{}/{}".format(script.parent.name, script.name))
    return names


def run_script(name: str, args: Sequence[str]) -> int:
    script = (KIT_DIR / name).resolve()
    if KIT_DIR.resolve() not in script.parents or not script.is_file():
        print("unknown script: {} (see `ctf-forge kit list`)".format(name))
        return 2
    return subprocess.call(["bash", str(script)] + list(args))
