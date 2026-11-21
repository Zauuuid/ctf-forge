# Third-party projects

CTF Forge builds on the work below. Each project keeps its own license and authorship.

| Project | Author | License | How it is used |
|---|---|---|---|
| [ctf-skills](https://github.com/ljagiello/ctf-skills) | Lukasz Jagiello | MIT | Downloaded from its repository at install time and linked into the agent's skills directory. Not copied into this repository. |
| [ctf-kit](https://github.com/MysterionRise/ctf-kit) | MysterionRise | MIT | The tool-runner scripts in `ctf_forge/kit` are derived from ctf-kit. Its license is in `ctf_forge/kit/LICENSE-ctf-kit`. Changes: moved out of the plugin layout so they run standalone through `ctf-forge kit`. |
| [RsaCtfTool](https://github.com/RsaCtfTool/RsaCtfTool) | RsaCtfTool contributors | MIT | Downloaded at install time into `~/.ctf-forge`. |

Tools installed through system package managers and pipx are covered by their own licenses.
