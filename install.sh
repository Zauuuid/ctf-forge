#!/usr/bin/env bash
# FlagForge bootstrap.
#   Local:   bash install.sh [options]
#   Remote:  curl -fsSL https://raw.githubusercontent.com/Zauuuid/flagforge/main/install.sh | bash
# Options are passed to scripts/setup.py (see --help).
set -euo pipefail

REPO="https://github.com/Zauuuid/flagforge.git"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (3.8+). Install it first." >&2
  exit 1
fi

if [ -z "${DIR}" ] || [ ! -f "${DIR}/scripts/setup.py" ]; then
  command -v git >/dev/null 2>&1 || { echo "git is required." >&2; exit 1; }
  DIR="${HOME}/.flagforge/repo"
  if [ -d "${DIR}/.git" ]; then
    git -C "${DIR}" pull --ff-only
  else
    mkdir -p "${HOME}/.flagforge"
    git clone --depth 1 "${REPO}" "${DIR}"
  fi
fi

exec python3 "${DIR}/scripts/setup.py" "$@"
