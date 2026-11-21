"""Install the command-line tools that CTF challenges commonly need."""
from __future__ import annotations

import sys
import tempfile
from typing import Dict, Iterable, List, Tuple

from .core import STORE, HOME, Runner

BASE: Dict[str, List[str]] = {
    "arch": ["base-devel", "git", "curl", "python", "python-pip", "python-pipx", "go",
             "ruby", "nodejs", "npm", "binutils", "file", "perl-image-exiftool", "unzip",
             "p7zip", "openssl", "imagemagick", "sox", "strace", "ltrace", "gdb", "nmap",
             "whois", "bind", "qrencode", "zbar", "xxd", "openbsd-netcat"],
    "debian": ["build-essential", "git", "curl", "python3", "python3-pip", "python3-venv",
               "pipx", "golang-go", "ruby", "ruby-dev", "nodejs", "npm", "binutils", "file",
               "xxd", "libimage-exiftool-perl", "unzip", "p7zip-full", "openssl",
               "imagemagick", "sox", "strace", "ltrace", "gdb", "nmap", "whois", "dnsutils",
               "qrencode", "zbar-tools", "netcat-openbsd"],
    "macos": ["git", "curl", "python", "pipx", "go", "ruby", "node", "binutils", "exiftool",
              "p7zip", "openssl", "imagemagick", "sox", "nmap", "whois", "bind", "qrencode",
              "zbar"],
}

TOOLS: Dict[str, List[str]] = {
    "arch": ["binwalk", "foremost", "hashcat", "john", "radare2", "wireshark-cli",
             "gobuster", "ffuf", "checksec", "nikto", "fcrackzip", "sqlmap"],
    "debian": ["binwalk", "foremost", "hashcat", "john", "radare2", "tshark", "steghide",
               "gobuster", "ffuf", "checksec", "nikto", "fcrackzip", "sqlmap"],
    "macos": ["binwalk", "foremost", "hashcat", "john-jumbo", "radare2", "wireshark",
              "steghide", "gobuster", "ffuf", "checksec", "nikto"],
}

AUR_ONLY: Dict[str, List[str]] = {"arch": ["bkcrack", "steghide"], "debian": [],
                                   "macos": ["bkcrack"]}

# Binaries installed with `go install` when no package provided them.
GO_FALLBACK: Dict[str, str] = {
    "ffuf": "github.com/ffuf/ffuf/v2@latest",
    "gobuster": "github.com/OJ/gobuster/v3@latest",
}

FULL_EXTRA: Dict[str, List[str]] = {
    "arch": ["ghidra", "sagemath", "wireshark-qt", "audacity", "sonic-visualiser"],
    "debian": ["ghidra", "sagemath", "wireshark", "audacity", "sonic-visualiser"],
    "macos": ["sage", "audacity"],
}

# (pipx package, binary it provides)
PIPX_TOOLS: List[Tuple[str, str]] = [
    ("xortool", "xortool"),
    ("hashid", "hashid"),
    ("ROPGadget", "ROPgadget"),
    ("pwntools", "pwn"),
    ("volatility3", "vol"),
    ("sherlock-project", "sherlock"),
]

VERIFY: List[str] = [
    "file", "strings", "xxd", "exiftool", "binwalk", "foremost", "steghide", "zsteg",
    "xortool", "hashid", "hashcat", "john", "RsaCtfTool", "radare2", "gdb", "checksec",
    "ROPgadget", "pwn", "vol", "tshark", "sqlmap", "gobuster", "ffuf", "nmap", "nc",
]

GROUPS = ("base", "tools", "pipx", "rsactftool", "zsteg")


def aur_helper(r: Runner):
    for name in ("yay", "paru"):
        if r.have(name):
            return name
    return None


def pkg_installed(r: Runner, distro: str, name: str) -> bool:
    if r.dry_run:
        return False
    probe = {"arch": ["pacman", "-Qi", name], "debian": ["dpkg", "-s", name],
             "macos": ["brew", "list", name]}.get(distro)
    return bool(probe) and r.run(probe, quiet=True)


def install_pkg(r: Runner, distro: str, name: str, aur: bool = True) -> bool:
    if pkg_installed(r, distro, name):
        r.say("  = {}".format(name))
        return True
    ok = False
    if distro == "arch":
        ok = r.run_root(["pacman", "-S", "--needed", "--noconfirm", name], quiet=True)
        helper = aur_helper(r)
        if not ok and aur and helper:
            ok = r.run([helper, "-S", "--needed", "--noconfirm", name])
    elif distro == "debian":
        ok = r.run_root(["apt-get", "install", "-y", name])
    elif distro == "macos":
        ok = r.run(["brew", "install", name])
    if ok:
        r.say("  + {}".format(name))
    else:
        r.fail("package {}".format(name))
    return ok


def ensure_aur_helper(r: Runner) -> None:
    """Build yay from the AUR when missing. Skipped as root (makepkg refuses)."""
    if aur_helper(r) or (r.is_root and not r.dry_run):
        return
    r.step("AUR helper (yay)")
    tmp = tempfile.mkdtemp(prefix="yay-")
    ok = r.run(["git", "clone", "https://aur.archlinux.org/yay-bin.git", tmp + "/yay-bin"])
    ok = ok and r.run(["makepkg", "-si", "--noconfirm"], cwd=tmp + "/yay-bin")
    if not ok:
        r.fail("yay could not be installed; AUR packages will be skipped")


def pipx_install(r: Runner, pkg: str, binary: str) -> None:
    if r.have(binary):
        r.say("  = {}".format(binary))
    elif not r.run(["pipx", "install", pkg]):
        r.fail("pipx {}".format(pkg))


def install_rsactftool(r: Runner) -> None:
    if r.have("RsaCtfTool"):
        r.say("  = RsaCtfTool")
        return
    base = STORE / "RsaCtfTool"
    if not base.exists() and not r.run(
        ["git", "clone", "--depth", "1", "https://github.com/RsaCtfTool/RsaCtfTool.git",
         str(base)]
    ):
        r.fail("RsaCtfTool (clone)")
        return
    ok = r.run([sys.executable, "-m", "venv", str(base / ".venv")])
    ok = ok and r.run([str(base / ".venv" / "bin" / "pip"), "install", "-r",
                       str(base / "requirements.txt")])
    if not ok:
        r.fail("RsaCtfTool (dependencies)")
        return
    if not r.dry_run:
        launcher = HOME / ".local" / "bin" / "RsaCtfTool"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(
            '#!/bin/sh\nexec "{0}/.venv/bin/python" "{0}/RsaCtfTool.py" "$@"\n'.format(base))
        launcher.chmod(0o755)


def install_zsteg(r: Runner) -> None:
    if r.have("zsteg"):
        r.say("  = zsteg")
    elif not r.run(["gem", "install", "--user-install", "zsteg"]):
        r.fail("gem zsteg")
    else:
        r.refresh_path()


def install_all(r: Runner, distro: str, full: bool = False, aur: bool = True,
                skip: Iterable[str] = ()) -> None:
    skip = set(skip)
    if "base" not in skip:
        r.step("Package index")
        if distro == "arch":
            r.run_root(["pacman", "-Syu", "--noconfirm"])
        elif distro == "debian":
            r.run_root(["apt-get", "update"])
        elif distro == "macos":
            r.run(["brew", "update"])
        r.step("Base packages")
        for name in BASE[distro]:
            install_pkg(r, distro, name, aur)
    if "tools" not in skip:
        if distro == "arch" and aur:
            ensure_aur_helper(r)
        r.step("CTF tools")
        names = list(TOOLS[distro]) + (list(FULL_EXTRA[distro]) if full else [])
        for name in names:
            install_pkg(r, distro, name, aur)
        if aur:
            for name in AUR_ONLY[distro]:
                install_pkg(r, distro, name, aur)
        elif AUR_ONLY[distro]:
            r.say("  ~ skipped (AUR): {}".format(", ".join(AUR_ONLY[distro])))
        for binary, module in GO_FALLBACK.items():
            if not r.dry_run and r.have(binary):
                continue
            if r.have("go") or r.dry_run:
                r.say("  go fallback for {}".format(binary))
                if r.run(["go", "install", module]) and not r.dry_run:
                    r.refresh_path()
                    if r.failed and r.failed[-1] == "package {}".format(binary):
                        r.failed.pop()
    if "pipx" not in skip:
        r.step("Python tools (pipx)")
        r.run(["pipx", "ensurepath"], quiet=True)
        for pkg, binary in PIPX_TOOLS:
            pipx_install(r, pkg, binary)
    if "rsactftool" not in skip:
        r.step("RsaCtfTool")
        install_rsactftool(r)
    if "zsteg" not in skip:
        r.step("zsteg")
        install_zsteg(r)


def verify(r: Runner) -> Dict[str, bool]:
    found = {name: r.have(name) for name in VERIFY}
    for name, ok in found.items():
        r.say("  [{}] {}".format("x" if ok else " ", name))
    return found
