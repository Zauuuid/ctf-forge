# Memory vault rules

A plain markdown vault that an AI agent (or you) reads before CTF work and writes after it.
It works with Obsidian but does not require it.

## Before a challenge
- Read `Home.md`.
- Search for related notes: `ctf-forge memory recall <keywords>`.

## During a challenge
- Keep scratch reasoning in `Thoughts/`.

## After a challenge
- Record it: `ctf-forge memory log --event <ctf> --name <challenge> --category <cat> --status solved --flag '<flag>' --summary '<one line>'`.
- Move reusable steps into `Techniques/<topic>.md` and mistakes into `Lessons/<lesson>.md`.
- Link notes with `[[wikilinks]]`. One idea per note. Update instead of duplicating.
- Do not store live credentials or secrets.

## Folders
| Folder | Purpose |
|---|---|
| `Inbox/` | quick captures to sort later |
| `Challenges/` | one note per challenge |
| `Techniques/` | reusable how-tos by category |
| `Lessons/` | mistakes and rules of thumb |
| `Tools/` | per-tool cheat sheets |
| `Thoughts/` | free reasoning |
| `Journal/` | dated logs, one file per day |
| `Templates/` | note templates |
