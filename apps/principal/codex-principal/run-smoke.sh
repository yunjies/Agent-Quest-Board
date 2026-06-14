#!/usr/bin/env sh
set -eu

root="${TMPDIR:-/tmp}/agent-board-codex-principal-$$"
desc="$root/task.md"
task_json="$root/task.json"
review_json="$root/review.json"
board="$root/board"
mkdir -p "$root"
printf '%s\n' "Codex principal smoke. Publish a task, review submitted evidence, and approve it." > "$desc"

python adapters/codex-local/codex_principal.py publish \
  --title "Codex principal review smoke" \
  --description-file "$desc" \
  --principal-id principal-codex-pc \
  --contractor-id contractor-duoduo \
  --board-id board-duoduo \
  --acceptance-test "result_file exists" \
  --acceptance-test "review_file exists" \
  --output "$task_json" \
  --board-root "$board" \
  --register-example-identities

task_id="$(python -c "import json;print(json.load(open('$task_json', encoding='utf-8'))['task_id'])")"
PYTHONPATH="packages/board-core:adapters/filesystem" BOARD_ROOT="$board" TASK_ID="$task_id" python - <<'PY'
import os
from agent_delegation_filesystem import claim_task, start_execution, submit_result, request_review

root = os.environ["BOARD_ROOT"]
task_id = os.environ["TASK_ID"]
claim_task(root, task_id, "contractor-duoduo")
start_execution(root, task_id, "contractor-duoduo")
submit_result(root, task_id, "contractor-duoduo", f"results/{task_id}.md", {"smoke": "passed"})
request_review(root, task_id, "board-duoduo")
PY

python adapters/codex-local/codex_principal.py review \
  --task-id "$task_id" \
  --principal-id principal-codex-pc \
  --verdict approved \
  --summary "Submitted result contains smoke evidence." \
  --evidence "result_file exists" \
  --evidence "artifact smoke=passed" \
  --contractor-rating 8 \
  --review-file "$review_json" \
  --board-root "$board"

PYTHONPATH="packages/board-core:adapters/filesystem" BOARD_ROOT="$board" TASK_ID="$task_id" python - <<'PY'
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
PY
