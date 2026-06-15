#!/usr/bin/env sh
set -eu

root="${TMPDIR:-/tmp}/hermes-contractor-smoke-$$"
results="$root/results"
logs="$root/logs"
board="$root/board"
task_id='smoke-task-001'

export BOARD_ROOT="$board"
export RESULTS_DIR="$results"
export LOGS_DIR="$logs"
export TASK_ID="$task_id"

PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/contractor/hermes-contractor"
export PYTHONPATH

printf 'Hermes contractor smoke: verify full contractor lifecycle, execution_log, exit codes\n'

# Step 1: Register identities
python3 << 'PYEOF'
import os
from agent_delegation_filesystem import init_board, register_identity
from agent_delegation_hermes_contractor import CONTRACTOR_IDENTITY, HermesContractor

board = os.environ["BOARD_ROOT"]
init_board(board)
for ident in [
    {
        "identity_id": "principal-codex-pc",
        "agent_id": "agent-codex",
        "role_type": "principal",
        "permissions": ["publish_task", "review_task", "approve_task", "reject_task"],
        "board_protocol_version": "1.0",
        "status": "active",
    },
    {
        "identity_id": "board-duoduo",
        "agent_id": "agent-duoduo",
        "role_type": "board",
        "permissions": ["append_event", "transition_status", "route_notification", "request_review", "close_task"],
        "board_protocol_version": "1.0",
        "status": "active",
    },
]:
    register_identity(board, ident)

c = HermesContractor(board, results_dir=os.environ["RESULTS_DIR"], logs_dir=os.environ["LOGS_DIR"])
ident = c.ensure_registered()
assert ident["role_type"] == "contractor", f"role mismatch: {ident}"
assert ident["identity_id"] == "contractor-duoduo", f"id mismatch: {ident}"
print("OK identity registered")
PYEOF

# Step 2: Publish task
python3 << 'PYEOF'
import os
from agent_delegation_filesystem import publish_task

board = os.environ["BOARD_ROOT"]
task_id = os.environ["TASK_ID"]
task = {
    "task_id": task_id,
    "title": "Hermes contractor smoke task",
    "principal_identity_id": "principal-codex-pc",
    "contractor_identity_id": "contractor-duoduo",
    "board_identity_id": "board-duoduo",
    "status": "published",
    "board_protocol_version": "1.0",
}
publish_task(board, task, "principal-codex-pc")
print("OK task published")
PYEOF

# Step 3: Contractor full lifecycle with execution_log verification
python3 << 'PYEOF'
import os, json
from pathlib import Path
from agent_delegation_hermes_contractor import HermesContractor

board = os.environ["BOARD_ROOT"]
task_id = os.environ["TASK_ID"]
results = os.environ["RESULTS_DIR"]
logs = os.environ["LOGS_DIR"]

c = HermesContractor(board, results_dir=results, logs_dir=logs)
c.ensure_registered()

c.claim_task(task_id); print("OK claimed")
c.start_execution(task_id); print("OK started")
result = c.execute_task(task_id); print("OK executed")

# Submit with execution_log
c.submit_result(task_id, result_file=result["result_file"],
    artifacts=result["artifacts"], execution_log=result["execution_log"])
print("OK submitted")

# Verify execution_log in task snapshot
snapshot = c.load_task(task_id)
assert snapshot.get("execution_log"), "execution_log missing in snapshot: " + str(list(snapshot.keys()))
print("OK execution_log persisted: " + snapshot["execution_log"])

# Verify events carry execution_log in artifacts
events_path = Path(board) / "events" / (task_id + ".jsonl")
events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines()]
event_types = [e["type"] for e in events]
assert "result_submitted" in event_types, "no result_submitted: " + str(event_types)
submitted_events = [e for e in events if e["type"] == "result_submitted"]
assert len(submitted_events) == 1, "expected 1 result_submitted event, got " + str(len(submitted_events))
payload = submitted_events[0].get("payload", {})
artifacts = payload.get("artifacts", {})
assert "execution_log" in artifacts, "execution_log missing in event payload artifacts: " + str(payload)
print("OK events complete, execution_log in artifacts")
print("ALL OK: contractor lifecycle complete for " + task_id)
PYEOF

# Step 4: Verify result file exists
test -f "$results/smoke-task-001-result.json"
printf 'OK result file exists\n'
printf 'ALL OK: contractor smoke test passed\n'
