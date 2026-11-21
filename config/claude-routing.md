## FlagForge routing

Two toolsets are installed. Use each for what it does best.

- **ctf-skills** (`/solve-challenge`, `ctf-web`, `ctf-pwn`, `ctf-crypto`, `ctf-reverse`,
  `ctf-forensics`, `ctf-osint`, `ctf-malware`, `ctf-ai-ml`, `ctf-misc`, `ctf-writeup`):
  technique knowledge. Use it to decide which attack fits and how to carry it out.
- **ctf-kit** (`/ctf-kit:analyze`, `:crypto`, `:stego`, `:forensics`, `:flag`, `:status`,
  `:team-solve`, `:compete`): tooling and workflow. Use it for triage output, bundled tool
  runners, flag tracking and multi-agent runs.

Default order for a new challenge:

1. `/ctf-kit:analyze <files>` for category and first findings.
2. Load the matching ctf-skills category skill for technique detail.
3. Run tools through the ctf-kit scripts where one exists.
4. Record the flag with `/ctf-kit:flag`.
5. Write up with `ctf-writeup`.

Only target systems and files that belong to a CTF or an environment you are authorised to test.
