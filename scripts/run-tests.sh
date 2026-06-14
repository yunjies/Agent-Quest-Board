#!/usr/bin/env sh
set -eu

export PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem"
python -m unittest discover -s tests -p "test_*.py"
