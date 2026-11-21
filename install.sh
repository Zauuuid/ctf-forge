#!/usr/bin/env bash
# ctf-forge bootstrap.
#   Local:   bash install.sh [ctf-forge arguments]        (default: all)
#   Remote:  curl -fsSL https://raw.githubusercontent.com/Zauuuid/ctf-forge/main/install.sh | bash
set -euo pipefail

REPO="https://github.com/Zauuuid/ctf-forge.git"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"

command -v python3 >/dev/null 2>&1 || { echo "python3 (3.8+) is required." >&2; exit 1; }

if [ -z "${DIR}" ] || [ ! -d "${DIR}/ctf_forge" ]; then
  command -v git >/dev/null 2>&1 || { echo "git is required." >&2; exit 1; }
  DIR="${HOME}/.ctf-forge/repo"
  if [ -d "${DIR}/.git" ]; then
    git -C "${DIR}" pull --ff-only
  else
    mkdir -p "${HOME}/.ctf-forge"
    git clone --depth 1 "${REPO}" "${DIR}"
  fi
fi

if [ "$#" -eq 0 ]; then
  set -- all
fi
cd "${DIR}"
exec python3 -m ctf_forge "$@"
