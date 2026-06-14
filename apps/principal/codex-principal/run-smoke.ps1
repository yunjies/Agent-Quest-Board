$ErrorActionPreference = "Stop"

$root = Join-Path $env:TEMP ("agent-board-codex-principal-" + [guid]::NewGuid().ToString("N"))
$desc = Join-Path $root "task.md"
$taskJson = Join-Path $root "task.json"
$reviewJson = Join-Path $root "review.json"
$board = Join-Path $root "board"
New-Item -ItemType Directory -Force -Path $root | Out-Null
Set-Content -LiteralPath $desc -Encoding UTF8 -Value "Codex principal smoke. Publish a task, review submitted evidence, and approve it."

python adapters\codex-local\codex_principal.py publish `
  --title "Codex principal review smoke" `
  --description-file $desc `
  --principal-id principal-codex-pc `
  --contractor-id contractor-duoduo `
  --board-id board-duoduo `
  --acceptance-test "result_file exists" `
  --acceptance-test "review_file exists" `
  --output $taskJson `
  --board-root $board `
  --register-example-identities

$payload = Get-Content -Raw -Encoding UTF8 $taskJson | ConvertFrom-Json
$env:PYTHONPATH = "packages/board-core;adapters/filesystem"
$env:TASK_ID = $payload.task_id
$env:BOARD_ROOT = $board
@'
import os
from agent_delegation_filesystem import claim_task, start_execution, submit_result, request_review

root = os.environ["BOARD_ROOT"]
task_id = os.environ["TASK_ID"]
claim_task(root, task_id, "contractor-duoduo")
start_execution(root, task_id, "contractor-duoduo")
submit_result(root, task_id, "contractor-duoduo", f"results/{task_id}.md", {"smoke": "passed"})
request_review(root, task_id, "board-duoduo")
'@ | python -

python adapters\codex-local\codex_principal.py review `
  --task-id $payload.task_id `
  --principal-id principal-codex-pc `
  --verdict approved `
  --summary "Submitted result contains smoke evidence." `
  --evidence "result_file exists" `
  --evidence "artifact smoke=passed" `
  --contractor-rating 8 `
  --review-file $reviewJson `
  --board-root $board

@'
import os
from agent_delegation_filesystem import close_task, load_task

root = os.environ["BOARD_ROOT"]
task_id = os.environ["TASK_ID"]
close_task(root, task_id, "board-duoduo")
closed = load_task(root, task_id)
assert closed["status"] == "closed", closed
assert closed["review_verdict"] == "approved", closed
assert closed["review_file"], closed
print(f"OK {task_id}")
'@ | python -
