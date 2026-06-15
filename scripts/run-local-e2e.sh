#!/usr/bin/env sh
set -eu

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BOARD_ROOT="$REPO_ROOT/.local/e2e-board"

PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/contractor/hermes-contractor:apps/board-interface/lark-topic-board"
export PYTHONPATH

python scripts/local_e2e.py --board-root "$BOARD_ROOT" --clean
