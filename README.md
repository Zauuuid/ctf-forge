# CTF Forge

One command to give your AI coding agent a full CTF toolbox: the
[ctf-skills](https://github.com/ljagiello/ctf-skills) technique library, the command-line tools
those skills call, tool-runner scripts derived from [ctf-kit](https://github.com/MysterionRise/ctf-kit),
and an optional markdown memory vault.

## Install

Supported: Arch/EndeavourOS, Debian/Ubuntu/Kali, macOS. On Windows use WSL2 (Ubuntu).

```bash
git clone https://github.com/Zauuuid/ctf-forge.git
cd ctf-forge
bash install.sh            # installs skills and tools
```

or without cloning first:

```bash
curl -fsSL https://raw.githubusercontent.com/Zauuuid/ctf-forge/main/install.sh | bash
```

Python 3.8+ and git are required. The tool is standard-library only. Run it as a normal user; it
uses `sudo` where needed. Every command accepts `--dry-run`.

## Use with your agent

After installing, open your agent in the folder that holds the challenge files and describe the
challenge. Skills load automatically from context, or call the orchestrator directly:

```text
/solve-challenge Crypto, "baby-rsa". Files: output.txt, chall.py. Hint: e is small.
/solve-challenge https://ctf.example.com/challenges/12
/solve-challenge Unknown category. Files in ./misc1. Flag format: HTB{...}
```

You can name a category skill (`/ctf-crypto`, `/ctf-web`, `/ctf-pwn`, `/ctf-reverse`,
`/ctf-forensics`, `/ctf-osint`, `/ctf-malware`, `/ctf-ai-ml`, `/ctf-misc`) when you already know
the type, or leave it to `/solve-challenge` to identify it. Hints, flag format and event rules go
in the same message. More walk-throughs are in [docs/examples.md](docs/examples.md).

Skills are installed for Claude Code by default (`~/.claude/skills`). For another agent that reads
Agent Skills folders, pass its skills directory: `ctf-forge skills install --dir PATH`.

## Commands

```bash
python3 -m ctf_forge all                       # skills + tools (what install.sh runs)
python3 -m ctf_forge skills install            # fetch ctf-skills, link into ~/.claude/skills
python3 -m ctf_forge skills install --with-kit # also add the ctf-kit Claude Code plugin
python3 -m ctf_forge skills update             # pull upstream and relink
python3 -m ctf_forge skills list
python3 -m ctf_forge tools install [--full] [--no-aur] [--skip pipx,zsteg]
python3 -m ctf_forge tools verify
python3 -m ctf_forge kit list
python3 -m ctf_forge kit run analyze/triage.sh challenge.bin
python3 -m ctf_forge memory init ~/CTFMemory
python3 -m ctf_forge memory log --event picoCTF --name baby-rsa --category crypto \
    --status solved --flag 'picoCTF{...}' --summary 'small e, cube root'
python3 -m ctf_forge memory recall rsa small exponent
python3 -m ctf_forge doctor
```

Install it as a command with `pipx install git+https://github.com/Zauuuid/ctf-forge`, then use
`ctf-forge` instead of `python3 -m ctf_forge`.

## What gets installed

| Part | Source | Where |
|---|---|---|
| Technique skills (`solve-challenge`, `ctf-crypto`, `ctf-web`, ...) | ctf-skills | cloned to `~/.ctf-forge/upstream`, linked into the skills directory |
| System tools (binwalk, hashcat, john, radare2, gdb, tshark, steghide, gobuster, ffuf, sqlmap, ...) | pacman/AUR, apt or Homebrew | system |
| Python tools (xortool, pwntools, volatility3, ROPGadget, hashid, ...) | pipx | `~/.local/bin` |
| RsaCtfTool, zsteg | upstream repos / gem | `~/.ctf-forge`, user gem dir |
| Tool-runner scripts | derived from ctf-kit | `ctf_forge/kit`, run with `ctf-forge kit` |

`tools install --full` adds Ghidra, SageMath and GUI analysis tools. Add `~/.local/bin` and your
gem bin directory to `PATH` if your shell does not already have them.

## Optional memory vault

A plain markdown folder that works well in [Obsidian](https://obsidian.md) but does not require
it. Point your agent at `RULES.md` in the vault, or paste its contents into your agent's
instructions. The agent can then run `memory recall` before a challenge and `memory log` after it,
so techniques and mistakes carry over between sessions.

## Testing

Unit tests run on Linux, macOS and Windows. CI also performs a real tool install on Ubuntu and on
Arch (in a container), installs the skills from upstream, and runs a kit script. Run the unit tests
locally with `python3 -m unittest discover -s tests`.

Not every tool exists in every distro's repositories. Missing packages are reported at the end of
`tools install` instead of stopping the run; use `--strict` to make that an error.

## Layout

```text
ctf_forge/            the CLI (core, tools, skills, kit, memory)
ctf_forge/kit/        tool-runner scripts derived from ctf-kit
ctf_forge/vault_template/  memory vault template
tests/                unit tests
docs/examples.md      usage walk-throughs
install.sh            bootstrap
```

## Responsible use

Use these tools only on CTF challenges and systems you are authorised to test. Several tools send
network traffic to whatever target you give them.

## Credits and license

Built on ctf-skills by Lukasz Jagiello and ctf-kit by MysterionRise, both MIT. See
[NOTICE.md](NOTICE.md). CTF Forge itself is MIT, see [LICENSE](LICENSE).
