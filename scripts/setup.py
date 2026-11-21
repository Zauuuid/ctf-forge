#!/usr/bin/env python3
"""CTF Forge installer.

Sets up, on Arch/EndeavourOS, Debian/Ubuntu/Kali or macOS:
  * system packages and CTF tooling
  * Claude Code CLI
  * ljagiello/ctf-skills (cloned, linked into ~/.claude/skills)
  * MysterionRise/ctf-kit (Claude Code plugin + `ctf` CLI)
  * Obsidian and a vault that Claude uses as long-term memory
  * routing rules so Claude knows which toolset to use

The script is idempotent. Run it as a normal user; it calls sudo when needed.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
ROOT = Path(__file__).resolve().parent.parent
FORGE_HOME = HOME / ".ctf-forge"
UPSTREAM_DIR = FORGE_HOME / "upstream"
CLAUDE_DIR = HOME / ".claude"

CTF_SKILLS_REPO = "https://github.com/ljagiello/ctf-skills.git"
CTF_KIT_MARKETPLACE = "MysterionRise/ctf-kit"
CTF_KIT_GIT = "git+https://github.com/MysterionRise/ctf-kit.git"

BLOCK = ("# >>> ctf-forge >>>", "# <<< ctf-forge <<<")
MD_BLOCK = ("<!-- >>> ctf-forge >>> -->", "<!-- <<< ctf-forge <<< -->")

FAILED: list[str] = []
DRY = False
DISTRO = "unknown"

ENV = os.environ.copy()
ENV["PATH"] = os.pathsep.join(
    [str(HOME / ".local/bin"), str(HOME / "go/bin"), ENV.get("PATH", "")]
)

# --------------------------------------------------------------------------
# Package sets, per package manager family: arch | debian | macos
# --------------------------------------------------------------------------
BASE = {
    "arch": ["base-devel", "git", "curl", "python", "python-pip", "python-pipx", "uv",
             "go", "ruby", "nodejs", "npm", "binutils", "file", "perl-image-exiftool",
             "unzip", "p7zip", "openssl", "imagemagick", "sox", "strace", "ltrace",
             "gdb", "nmap", "whois", "bind", "qrencode", "zbar"],
    "debian": ["build-essential", "git", "curl", "python3", "python3-pip", "python3-venv",
               "pipx", "golang-go", "ruby", "ruby-dev", "nodejs", "npm", "binutils",
               "file", "xxd", "libimage-exiftool-perl", "unzip", "p7zip-full", "openssl",
               "imagemagick", "sox", "strace", "ltrace", "gdb", "nmap", "whois",
               "dnsutils", "qrencode", "zbar-tools"],
    "macos": ["git", "curl", "python", "pipx", "uv", "go", "ruby", "node", "binutils",
              "file-formula", "exiftool", "p7zip", "openssl", "imagemagick", "sox",
              "nmap", "whois", "bind", "qrencode", "zbar"],
}

TOOLS = {
    "arch": ["binwalk", "foremost", "hashcat", "john", "radare2", "wireshark-cli",
             "steghide", "gobuster", "ffuf", "checksec", "bkcrack", "nikto",
             "fcrackzip", "sqlmap"],
    "debian": ["binwalk", "foremost", "hashcat", "john", "radare2", "tshark",
               "steghide", "gobuster", "ffuf", "checksec", "nikto", "fcrackzip",
               "sqlmap"],
    "macos": ["binwalk", "foremost", "hashcat", "john-jumbo", "radare2", "wireshark",
              "steghide", "gobuster", "ffuf", "checksec", "bkcrack", "nikto"],
}

FULL_EXTRA = {
    "arch": ["ghidra", "sagemath", "wireshark-qt", "audacity", "sonic-visualiser"],
    "debian": ["ghidra", "sagemath", "wireshark", "audacity", "sonic-visualiser"],
    "macos": ["sage", "audacity"],
}

# (pipx package, resulting binary)
PIPX_TOOLS = [
    ("xortool", "xortool"),
    ("hashid", "hashid"),
    ("ROPGadget", "ROPgadget"),
    ("pwntools", "pwn"),
    ("volatility3", "vol"),
    ("sherlock-project", "sherlock"),
    ("theHarvester", "theHarvester"),
]

VERIFY_BINARIES = [
    "claude", "ctf", "xortool", "zsteg", "steghide", "binwalk", "vol", "hashcat",
    "john", "RsaCtfTool", "radare2", "checksec", "gobuster", "ffuf", "sqlmap", "pwn",
    "ROPgadget", "exiftool", "tshark",
]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(title: str) -> None:
    say(f"\n==> {title}")


def fail(what: str) -> None:
    FAILED.append(what)
    say(f"  !! {what}")


def have(binary: str) -> bool:
    return shutil.which(binary, path=ENV["PATH"]) is not None


def run(cmd, shell: bool = False, cwd=None, quiet: bool = False) -> bool:
    shown = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
    if not quiet:
        say(f"  $ {shown}")
    if DRY:
        return True
    try:
        res = subprocess.run(
            cmd, shell=shell, cwd=cwd, env=ENV,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
        )
        return res.returncode == 0
    except FileNotFoundError:
        return False


def detect_distro() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        info: dict[str, str] = {}
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k] = v.strip().strip('"')
        except OSError:
            pass
        ids = f"{info.get('ID', '')} {info.get('ID_LIKE', '')}".lower()
        if any(x in ids for x in ("arch", "endeavouros", "manjaro")):
            return "arch"
        if any(x in ids for x in ("debian", "ubuntu", "kali")):
            return "debian"
    return "unknown"


# --------------------------------------------------------------------------
# Package installation
# --------------------------------------------------------------------------
def aur_helper() -> str | None:
    for helper in ("yay", "paru"):
        if have(helper):
            return helper
    return None


def ensure_aur_helper() -> None:
    if DISTRO != "arch" or aur_helper():
        return
    step("Installing yay (AUR helper)")
    tmp = tempfile.mkdtemp(prefix="yay-")
    ok = run(["git", "clone", "https://aur.archlinux.org/yay-bin.git", f"{tmp}/yay-bin"])
    ok = ok and run(["makepkg", "-si", "--noconfirm"], cwd=f"{tmp}/yay-bin")
    if not ok:
        fail("yay could not be installed; AUR packages will be skipped")


def pkg_installed(name: str) -> bool:
    if DRY:
        return False
    if DISTRO == "arch":
        return run(["pacman", "-Qi", name], quiet=True)
    if DISTRO == "debian":
        return run(["dpkg", "-s", name], quiet=True)
    if DISTRO == "macos":
        return run(["brew", "list", name], quiet=True)
    return False


def install_pkg(name: str) -> bool:
    if pkg_installed(name):
        say(f"  = {name}")
        return True
    ok = False
    if DISTRO == "arch":
        ok = run(["sudo", "pacman", "-S", "--needed", "--noconfirm", name], quiet=True)
        if not ok and aur_helper():
            ok = run([aur_helper(), "-S", "--needed", "--noconfirm", name])
    elif DISTRO == "debian":
        ok = run(["sudo", "apt-get", "install", "-y", name])
    elif DISTRO == "macos":
        ok = run(["brew", "install", name])
    if ok:
        say(f"  + {name}")
    else:
        fail(f"package {name}")
    return ok


def system_update() -> None:
    step("System package index")
    if DISTRO == "arch":
        run(["sudo", "pacman", "-Syu", "--noconfirm"])
    elif DISTRO == "debian":
        run(["sudo", "apt-get", "update"])
    elif DISTRO == "macos":
        run(["brew", "update"])


def install_obsidian() -> None:
    step("Obsidian")
    if DISTRO == "arch":
        install_pkg("obsidian")
    elif DISTRO == "macos":
        if not run(["brew", "install", "--cask", "obsidian"]):
            fail("Obsidian (brew cask)")
    elif DISTRO == "debian":
        if have("flatpak"):
            if not run(["flatpak", "install", "-y", "flathub", "md.obsidian.Obsidian"]):
                fail("Obsidian (flatpak)")
        else:
            fail("Obsidian: install flatpak or download the .deb from https://obsidian.md/download")


# --------------------------------------------------------------------------
# Python / Ruby tools
# --------------------------------------------------------------------------
def pipx_install(pkg: str, binary: str) -> None:
    if have(binary):
        say(f"  = {binary}")
        return
    if not run(["pipx", "install", pkg]):
        fail(f"pipx {pkg}")


def install_uv_if_missing() -> None:
    if have("uv"):
        return
    if not run(["pipx", "install", "uv"]):
        fail("uv (needed for the ctf CLI)")


def install_rsactftool() -> None:
    if have("RsaCtfTool") or have("rsactftool"):
        say("  = RsaCtfTool")
        return
    base = FORGE_HOME / "RsaCtfTool"
    if not base.exists() and not run(
        ["git", "clone", "--depth", "1", "https://github.com/RsaCtfTool/RsaCtfTool.git", str(base)]
    ):
        fail("RsaCtfTool (clone)")
        return
    ok = run([sys.executable, "-m", "venv", str(base / ".venv")])
    ok = ok and run([str(base / ".venv/bin/pip"), "install", "-r", str(base / "requirements.txt")])
    if not ok:
        fail("RsaCtfTool (dependencies)")
        return
    if not DRY:
        launcher = HOME / ".local/bin/RsaCtfTool"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(
            f'#!/bin/sh\nexec "{base}/.venv/bin/python" "{base}/RsaCtfTool.py" "$@"\n'
        )
        launcher.chmod(0o755)


def install_zsteg() -> None:
    if have("zsteg"):
        say("  = zsteg")
        return
    if not run(["gem", "install", "--user-install", "zsteg"]):
        fail("gem zsteg")


# --------------------------------------------------------------------------
# Shell PATH and config blocks
# --------------------------------------------------------------------------
def append_block(path: Path, markers: tuple[str, str], body: str) -> None:
    start, end = markers
    block = f"{start}\n{body.rstrip()}\n{end}\n"
    if DRY:
        say(f"  (dry-run) would write block to {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if start in text:
        head, _, rest = text.partition(start)
        _, _, tail = rest.partition(end)
        text = head.rstrip("\n") + ("\n" if head.strip() else "") + tail.lstrip("\n")
    sep = "\n" if text and not text.endswith("\n") else ""
    path.write_text(text + sep + block, encoding="utf-8")
    say(f"  + updated {path}")


def setup_shell_path() -> None:
    step("Shell PATH")
    body = ('export PATH="$HOME/.local/bin:$HOME/go/bin:'
            "$(ruby -e 'puts Gem.user_dir' 2>/dev/null)/bin:$PATH\"")
    for rc in (".bashrc", ".zshrc"):
        if (HOME / rc).exists() or rc == ".bashrc":
            append_block(HOME / rc, BLOCK, body)


# --------------------------------------------------------------------------
# Claude Code, ctf-skills, ctf-kit
# --------------------------------------------------------------------------
def install_claude_code() -> None:
    step("Claude Code CLI")
    if have("claude"):
        say("  = claude")
        return
    ok = run("curl -fsSL https://claude.ai/install.sh | bash", shell=True)
    if not ok or (not DRY and not have("claude")):
        ok = run(["sudo", "npm", "install", "-g", "@anthropic-ai/claude-code"])
    if not ok:
        fail("Claude Code CLI: install manually from https://claude.ai/code")


def install_ctf_skills(update: bool = False) -> None:
    step("ctf-skills (ljagiello)")
    target = UPSTREAM_DIR / "ctf-skills"
    if target.exists():
        if update:
            run(["git", "-C", str(target), "pull", "--ff-only"])
    else:
        UPSTREAM_DIR.mkdir(parents=True, exist_ok=True) if not DRY else None
        if not run(["git", "clone", "--depth", "1", CTF_SKILLS_REPO, str(target)]):
            fail("ctf-skills clone")
            return
    skills_dir = CLAUDE_DIR / "skills"
    if DRY:
        say(f"  (dry-run) would link each skill folder into {skills_dir}")
        return
    skills_dir.mkdir(parents=True, exist_ok=True)
    linked = 0
    for skill in sorted(target.iterdir()):
        if not (skill / "SKILL.md").is_file():
            continue
        link = skills_dir / skill.name
        if link.is_symlink() and link.resolve() == skill.resolve():
            linked += 1
            continue
        if link.exists() or link.is_symlink():
            say(f"  ~ {link} exists and is not ours, skipped")
            continue
        try:
            link.symlink_to(skill, target_is_directory=True)
            linked += 1
        except OSError:
            shutil.copytree(skill, link)
            linked += 1
    say(f"  {linked} skills available in {skills_dir}")


def install_ctf_kit(update: bool = False) -> None:
    step("ctf-kit (MysterionRise)")
    if have("claude"):
        run(["claude", "plugin", "marketplace", "add", CTF_KIT_MARKETPLACE])
        if update:
            run(["claude", "plugin", "marketplace", "update", "ctf-kit"])
        if not run(["claude", "plugin", "install", "ctf-kit@ctf-kit"]):
            fail("ctf-kit plugin: inside `claude` run /plugin marketplace add "
                 f"{CTF_KIT_MARKETPLACE} then /plugin install ctf-kit@ctf-kit")
    else:
        fail("ctf-kit plugin skipped (claude not found)")
    if have("ctf"):
        if update:
            run(["uv", "tool", "upgrade", "ctf-kit"])
        else:
            say("  = ctf CLI")
    else:
        install_uv_if_missing()
        if not run(["uv", "tool", "install", "ctf-kit", "--from", CTF_KIT_GIT]):
            fail("ctf CLI (uv tool install)")
    workspace = HOME / "ctf"
    if not DRY:
        workspace.mkdir(exist_ok=True)
        if have("ctf") and not (workspace / ".ctf-kit").exists():
            run(["ctf", "init", "--repo"], cwd=str(workspace))
    say(f"  CTF workspace: {workspace}")


# --------------------------------------------------------------------------
# Vault, routing rules, Claude settings
# --------------------------------------------------------------------------
def create_vault(vault: Path) -> None:
    step(f"Obsidian vault: {vault}")
    template = ROOT / "vault-template"
    if not template.is_dir():
        fail("vault-template folder not found next to the installer")
        return
    created = 0
    for src in sorted(template.rglob("*")):
        if not src.is_file():
            continue
        dest = vault / src.relative_to(template)
        if dest.exists():
            continue
        created += 1
        if DRY:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    say(f"  {created} new files" + (" (dry-run)" if DRY else ""))


def install_routing(vault: Path | None) -> None:
    step("Claude routing rules")
    rules = (ROOT / "config" / "claude-routing.md").read_text(encoding="utf-8")
    if vault is not None:
        rules += (
            f"\n## Memory vault\nYour Obsidian vault is at `{vault}`. Read `{vault}/CLAUDE.md` "
            f"and `{vault}/Home.md` before CTF work, and record challenges, techniques and "
            "lessons there.\n"
        )
    append_block(CLAUDE_DIR / "CLAUDE.md", MD_BLOCK, rules)


def merge_settings(vault: Path | None, agent_teams: bool) -> None:
    step("Claude settings")
    path = CLAUDE_DIR / "settings.json"
    if DRY:
        say(f"  (dry-run) would merge into {path}")
        return
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.exists():
        shutil.copy2(path, path.with_name("settings.json.bak"))
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            fail(f"{path} is not valid JSON and was left untouched")
            return
    dirs = data.setdefault("permissions", {}).setdefault("additionalDirectories", [])
    wanted = [str(HOME / "ctf")] + ([str(vault)] if vault else [])
    for d in wanted:
        if d not in dirs:
            dirs.append(d)
    if agent_teams:
        data.setdefault("env", {})["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    say(f"  + merged {path} (backup: settings.json.bak)")


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------
def verify() -> None:
    step("Installed tools")
    for b in VERIFY_BINARIES:
        say(f"  [{'x' if have(b) else ' '}] {b}")
    skills = CLAUDE_DIR / "skills"
    count = len(list(skills.glob("ctf-*"))) if skills.is_dir() else 0
    say(f"  ctf-skills linked: {count}")


def main() -> int:
    global DRY, DISTRO
    ap = argparse.ArgumentParser(description="CTF Forge installer")
    ap.add_argument("--full", action="store_true", help="also install heavy extras")
    ap.add_argument("--dry-run", action="store_true", help="print actions, change nothing")
    ap.add_argument("--update", action="store_true", help="update upstream repos and plugin")
    ap.add_argument("--verify", action="store_true", help="only report what is installed")
    ap.add_argument("--vault", default=str(HOME / "ClaudeMind"), help="vault location")
    ap.add_argument("--no-obsidian", action="store_true")
    ap.add_argument("--no-vault", action="store_true")
    ap.add_argument("--no-agent-teams", action="store_true")
    ap.add_argument("--distro", choices=["arch", "debian", "macos"],
                    help="override detection (useful with --dry-run)")
    args = ap.parse_args()
    DRY = args.dry_run
    DISTRO = args.distro or detect_distro()

    if sys.platform == "win32" and not DRY:
        sys.exit("Windows is not supported directly. Install WSL2 (Ubuntu) and run this there.")
    if hasattr(os, "geteuid") and os.geteuid() == 0 and not DRY:
        sys.exit("Run as a normal user, not root.")
    if DISTRO == "unknown":
        sys.exit("Unsupported system. Supported: Arch/EndeavourOS, Debian/Ubuntu/Kali, macOS.")

    say(f"CTF Forge on {DISTRO} ({platform.system()})" + (" [dry-run]" if DRY else ""))

    if args.verify:
        verify()
        return 0

    vault = None if args.no_vault else Path(args.vault).expanduser()

    if args.update:
        install_ctf_skills(update=True)
        install_ctf_kit(update=True)
        verify()
        return 0

    system_update()
    step("Base packages")
    for p in BASE[DISTRO]:
        install_pkg(p)
    ensure_aur_helper()

    step("CTF tools")
    for p in TOOLS[DISTRO] + (FULL_EXTRA[DISTRO] if args.full else []):
        install_pkg(p)

    step("Python tools (pipx)")
    run(["pipx", "ensurepath"], quiet=True)
    for pkg, binary in PIPX_TOOLS:
        pipx_install(pkg, binary)
    install_rsactftool()
    step("Ruby tools")
    install_zsteg()

    setup_shell_path()
    install_claude_code()
    install_ctf_skills()
    install_ctf_kit()

    if not args.no_obsidian:
        install_obsidian()
    if vault is not None:
        create_vault(vault)
    install_routing(vault)
    merge_settings(vault, not args.no_agent_teams)

    verify()
    if FAILED:
        step("Needs manual attention")
        for item in FAILED:
            say(f"  - {item}")
    say(f"""
Next:
  1. Open a new terminal so PATH changes apply.
  2. Run `claude` once and sign in.
  3. {'Open Obsidian, choose "Open folder as vault", select ' + str(vault) if vault else 'Vault skipped.'}
  4. cd ~/ctf && ctf new my-challenge && claude
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
