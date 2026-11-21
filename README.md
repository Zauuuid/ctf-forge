# CTF Arsenal

One installer that sets up an AI-assisted CTF environment for [Claude Code](https://claude.ai/code):
the [ctf-skills](https://github.com/ljagiello/ctf-skills) knowledge base, the
[ctf-kit](https://github.com/MysterionRise/ctf-kit) tooling plugin, the command-line tools they
call, and an [Obsidian](https://obsidian.md) vault that Claude uses as long-term memory.

## Install

Supported: Arch/EndeavourOS, Debian/Ubuntu/Kali, macOS. On Windows, use WSL2 (Ubuntu).

```bash
git clone https://github.com/Zauuuid/ctf-arsenal.git
cd ctf-arsenal
bash install.sh
```

Or in one line:

```bash
curl -fsSL https://raw.githubusercontent.com/Zauuuid/ctf-arsenal/main/install.sh | bash
```

Run it as a normal user. It calls `sudo` where needed and is safe to re-run.

| Option | Effect |
|---|---|
| `--dry-run` | Print what would happen without changing anything |
| `--full` | Add heavy extras (Ghidra, SageMath, Wireshark GUI, audio tools) |
| `--update` | Update ctf-skills, the ctf-kit plugin and the `ctf` CLI |
| `--verify` | Report which tools are installed |
| `--vault PATH` | Vault location (default `~/ClaudeMind`) |
| `--no-obsidian`, `--no-vault` | Skip Obsidian or the vault |
| `--no-agent-teams` | Do not enable Claude Code's experimental agent teams |
| `--distro arch\|debian\|macos` | Override detection (useful with `--dry-run`) |

## What it sets up

1. System packages and CTF tools (pacman and AUR, apt, or Homebrew).
2. Python tools through pipx: xortool, hashid, pwntools, volatility3, ROPGadget and others.
   RsaCtfTool and zsteg are installed separately.
3. Claude Code CLI.
4. ctf-skills, cloned to `~/.ctf-arsenal/upstream` and linked into `~/.claude/skills`.
5. The ctf-kit plugin and `ctf` CLI, plus a workspace at `~/ctf`.
6. Obsidian and a vault from [`vault-template`](vault-template).
7. A routing block in `~/.claude/CLAUDE.md` that tells Claude which toolset to use
   ([`config/claude-routing.md`](config/claude-routing.md)).
8. Merged entries in `~/.claude/settings.json` (a `.bak` copy is kept).

## Usage

```bash
cd ~/ctf
ctf new rsa-challenge
cd rsa-challenge
claude
> /ctf-kit:analyze challenge.txt
> /solve-challenge
```

ctf-skills provides the technique knowledge; ctf-kit provides triage scripts, flag tracking and
multi-agent modes. Claude picks between them using the routing rules.

## Layout

```text
install.sh            bootstrap (local or via curl)
scripts/setup.py      installer
config/               routing rules for Claude
vault-template/       Obsidian vault seed
```

## Notes

- Claude Code is required for the skills and plugin. The knowledge files in ctf-skills follow the
  open Agent Skills format; other agents may load them, but this installer targets Claude Code.
- Use it only on CTF challenges and systems you are authorised to test.
- Third-party projects are downloaded from their original repositories. See [NOTICE.md](NOTICE.md).

## License

MIT. See [LICENSE](LICENSE).
