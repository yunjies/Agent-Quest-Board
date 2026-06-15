$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$boardRoot = Join-Path $repoRoot ".local\e2e-board"

$env:PYTHONPATH = @(
    "packages/board-core",
    "packages/principal-sdk",
    "adapters/filesystem",
    "apps/contractor/hermes-contractor",
    "apps/board-interface/lark-topic-board"
) -join ";"

python scripts\local_e2e.py --board-root $boardRoot --clean
if ($LASTEXITCODE -ne 0) { throw "local e2e failed" }
