$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "packages/board-core;packages/principal-sdk;adapters/filesystem"
python -m unittest discover -s tests -p "test_*.py"
