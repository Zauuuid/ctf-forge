"""Command-line interface for ctf-forge."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, kit, memory, skills, tools
from .core import Runner, detect_distro


def _common() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--dry-run", action="store_true",
                        help="print actions without changing anything")
    parent.add_argument("--distro", choices=["arch", "debian", "macos"],
                        help="override distro detection")
    return parent


def _skills_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--agent", choices=sorted(skills.AGENT_DIRS), default="claude",
                   help="agent whose skills directory to use (default: claude)")
    p.add_argument("--dir", help="skills directory to use instead of --agent")
    p.add_argument("--source", default=skills.UPSTREAM_URL, help="skills git repository")
    p.add_argument("--ref", help="branch or tag of the skills repository")
    p.add_argument("--copy", action="store_true", help="copy instead of symlink")
    p.add_argument("--with-kit", action="store_true",
                   help="also install the ctf-kit Claude Code plugin")


def build_parser() -> argparse.ArgumentParser:
    common = _common()
    parser = argparse.ArgumentParser(
        prog="ctf-forge", description="Install and manage a complete CTF toolchain.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", metavar="command")

    p_all = sub.add_parser("all", parents=[common], help="install skills and tools")
    _skills_args(p_all)
    p_all.add_argument("--full", action="store_true", help="include heavy extras")
    p_all.add_argument("--no-aur", action="store_true", help="never use the AUR (Arch)")
    p_all.add_argument("--skip", default="", help="comma list: " + ",".join(tools.GROUPS))
    p_all.add_argument("--strict", action="store_true", help="exit 1 if anything failed")

    p_skills = sub.add_parser("skills", help="manage the CTF skills").add_subparsers(
        dest="action", metavar="action")
    for name, text in (("install", "fetch and link the skills"),
                       ("update", "pull the skills repository and relink")):
        p = p_skills.add_parser(name, parents=[common], help=text)
        _skills_args(p)
    p = p_skills.add_parser("list", help="list linked skills")
    p.add_argument("--agent", choices=sorted(skills.AGENT_DIRS), default="claude")
    p.add_argument("--dir")

    p_tools = sub.add_parser("tools", help="manage CTF command-line tools").add_subparsers(
        dest="action", metavar="action")
    p = p_tools.add_parser("install", parents=[common], help="install the tools")
    p.add_argument("--full", action="store_true", help="include heavy extras")
    p.add_argument("--no-aur", action="store_true", help="never use the AUR (Arch)")
    p.add_argument("--skip", default="", help="comma list: " + ",".join(tools.GROUPS))
    p.add_argument("--strict", action="store_true", help="exit 1 if anything failed")
    p_tools.add_parser("verify", help="report which tools are installed")

    p_kit = sub.add_parser("kit", help="bundled tool-runner scripts").add_subparsers(
        dest="action", metavar="action")
    p_kit.add_parser("list", help="list scripts")
    p = p_kit.add_parser("run", help="run a script, e.g. analyze/triage.sh FILE")
    p.add_argument("script")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p_mem = sub.add_parser("memory", help="optional markdown memory vault").add_subparsers(
        dest="action", metavar="action")
    p = p_mem.add_parser("init", help="create the vault from the template")
    p.add_argument("vault", nargs="?")
    p = p_mem.add_parser("log", help="record a challenge")
    p.add_argument("--vault")
    p.add_argument("--event", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--category", default="")
    p.add_argument("--status", default="unsolved")
    p.add_argument("--flag", default="")
    p.add_argument("--summary", default="")
    p = p_mem.add_parser("recall", help="search notes by keyword")
    p.add_argument("words", nargs="+")
    p.add_argument("--vault")
    p.add_argument("--limit", type=int, default=5)

    sub.add_parser("doctor", help="show what is installed")
    return parser


def _skills_install(args, update: bool) -> int:
    runner = Runner(args.dry_run)
    target = skills.resolve_target(args.agent, args.dir)
    runner.step("Skills -> {}".format(target))
    skills.install(runner, target, args.source, args.ref, args.copy, update)
    if args.with_kit:
        runner.step("ctf-kit plugin")
        skills.install_kit(runner)
    _report(runner)
    return 0


def _tools_install(args) -> int:
    distro = args.distro or detect_distro()
    if distro == "unknown":
        print("Unsupported system. Supported: Arch/EndeavourOS, Debian/Ubuntu/Kali, macOS "
              "(Windows: use WSL2).")
        return 2
    runner = Runner(args.dry_run)
    runner.say("ctf-forge tools on {}{}".format(distro, " [dry-run]" if args.dry_run else ""))
    skip = [s.strip() for s in args.skip.split(",") if s.strip()]
    tools.install_all(runner, distro, args.full, not args.no_aur, skip)
    runner.step("Installed tools")
    tools.verify(runner)
    _report(runner)
    return 1 if args.strict and runner.failed else 0


def _report(runner: Runner) -> None:
    if runner.failed:
        runner.step("Needs attention")
        for item in runner.failed:
            runner.say("  - {}".format(item))


def _doctor() -> int:
    runner = Runner()
    runner.say("ctf-forge {}".format(__version__))
    runner.say("system: {}".format(detect_distro()))
    runner.step("Skills")
    target = skills.resolve_target("claude", None)
    found = skills.installed(target)
    runner.say("  {} linked in {}".format(len(found), target))
    runner.step("Tools")
    tools.verify(runner)
    runner.step("Kit scripts")
    runner.say("  {} bundled".format(len(kit.list_scripts())))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    if args.command in ("skills", "tools", "kit", "memory") and not getattr(args, "action", None):
        parser.parse_args([args.command, "--help"])
        return 0

    if args.command == "all":
        code = _skills_install(args, update=False)
        return code or _tools_install(args)
    if args.command == "skills":
        if args.action == "list":
            target = skills.resolve_target(args.agent, args.dir)
            for name in skills.installed(target):
                print(name)
            return 0
        return _skills_install(args, update=args.action == "update")
    if args.command == "tools":
        if args.action == "verify":
            found = tools.verify(Runner())
            return 0 if any(found.values()) else 1
        return _tools_install(args)
    if args.command == "kit":
        if args.action == "list":
            for name in kit.list_scripts():
                print(name)
            return 0
        return kit.run_script(args.script, args.args)
    if args.command == "memory":
        if args.action == "init":
            vault = memory.resolve_vault(args.vault)
            count = memory.init(vault)
            print("vault ready at {} ({} new files)".format(vault, count))
            return 0
        if args.action == "log":
            note = memory.log(memory.resolve_vault(args.vault), args.event, args.name,
                              args.category, args.status, args.flag, args.summary)
            print("wrote {}".format(note))
            return 0
        hits = memory.recall(memory.resolve_vault(args.vault), args.words, args.limit)
        if not hits:
            print("no matching notes")
            return 1
        for path, score, lines in hits:
            print("{}  (score {})".format(path, score))
            for line in lines:
                print("    {}".format(line))
        return 0
    if args.command == "doctor":
        return _doctor()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
