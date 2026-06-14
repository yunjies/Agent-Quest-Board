$ErrorActionPreference = "Stop"

$root = Join-Path $env:TEMP ("agent-board-codex-example-" + [guid]::NewGuid().ToString("N"))
$desc = Join-Path $root "task.md"
$out = Join-Path $root "task.json"
$board = Join-Path $root "board"
New-Item -ItemType Directory -Force -Path $root | Out-Null
Set-Content -LiteralPath $desc -Encoding UTF8 -Value "Codex principal example smoke. Verify task snapshot and event log."

python adapters\codex-local\codex_principal.py `
  --title "Codex principal smoke" `
  --description-file $desc `
  --principal-id principal-codex-pc `
  --contractor-id contractor-duoduo `
  --board-id board-duoduo `
  --acceptance-test "task snapshot exists" `
  --acceptance-test "event log exists" `
  --output $out `
  --board-root $board `
  --register-example-identities

$payload = Get-Content -Raw -Encoding UTF8 $out | ConvertFrom-Json
$taskPath = Join-Path $board "tasks\active\$($payload.task_id).json"
$eventPath = Join-Path $board "events\$($payload.task_id).jsonl"
if (!(Test-Path $taskPath)) { throw "task snapshot missing" }
if (!(Test-Path $eventPath)) { throw "event log missing" }
Write-Output "OK $($payload.task_id)"
