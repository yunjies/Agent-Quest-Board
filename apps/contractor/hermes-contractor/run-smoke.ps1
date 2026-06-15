$ErrorActionPreference = "Stop"

$root = "$env:TMP\hermes-contractor-smoke-$PID"
$results = "$root\results"
$logs = "$root\logs"
$board = "$root\board"
$null = New-Item -ItemType Directory -Path $root -Force

$env:PYTHONPATH = "packages/board-core;packages/principal-sdk;adapters/filesystem;apps/contractor/hermes-contractor"

# 通过环境变量传路径，不拼接到 Python 代码字符串中
$env:BOARD_ROOT = $board
$env:RESULTS_DIR = $results
$env:LOGS_DIR = $logs

Write-Output "Hermes contractor smoke: verify full contractor lifecycle"

# Step 1: Register identities
python -c @"
import os
from agent_delegation_filesystem import init_board, register_identity
from agent_delegation_hermes_contractor import CONTRACTOR_IDENTITY, HermesContractor

board = os.environ['BOARD_ROOT']
init_board(board)
for ident in [
    {
        'identity_id': 'principal-codex-pc',
        'agent_id': 'agent-codex',
        'role_type': 'principal',
        'permissions': ['publish_task', 'review_task', 'approve_task', 'reject_task'],
        'board_protocol_version': '1.0',
        'status': 'active',
    },
    {
        'identity_id': 'board-duoduo',
        'agent_id': 'agent-duoduo',
        'role_type': 'board',
        'permissions': ['append_event', 'transition_status', 'route_notification', 'request_review', 'close_task'],
        'board_protocol_version': '1.0',
        'status': 'active',
    },
]:
    register_identity(board, ident)

c = HermesContractor(board, results_dir=os.environ['RESULTS_DIR'], logs_dir=os.environ['LOGS_DIR'])
ident = c.ensure_registered()
assert ident['role_type'] == 'contractor', f'role mismatch: {ident}'
assert ident['identity_id'] == 'contractor-duoduo', f'id mismatch: {ident}'
print('OK identity registered')
"@
if ($LASTEXITCODE -ne 0) { throw "Step 1 failed" }

# Step 2: Publish task
$env:TASK_ID = "smoke-task-001"
python -c @"
import os
from agent_delegation_filesystem import publish_task

board = os.environ['BOARD_ROOT']
task_id = os.environ['TASK_ID']
task = {
    'task_id': task_id,
    'title': 'Hermes contractor smoke task',
    'principal_identity_id': 'principal-codex-pc',
    'contractor_identity_id': 'contractor-duoduo',
    'board_identity_id': 'board-duoduo',
    'status': 'published',
    'board_protocol_version': '1.0',
}
publish_task(board, task, 'principal-codex-pc')
print('OK task published')
"@
if ($LASTEXITCODE -ne 0) { throw "Step 2 failed" }

# Step 3: Contractor lifecycle
python -c @"
import os, json
from pathlib import Path
from agent_delegation_hermes_contractor import HermesContractor

board = os.environ['BOARD_ROOT']
task_id = os.environ['TASK_ID']
results = os.environ['RESULTS_DIR']
logs = os.environ['LOGS_DIR']

c = HermesContractor(board, results_dir=results, logs_dir=logs)
c.ensure_registered()

c.claim_task(task_id); print('OK claimed')
c.start_execution(task_id); print('OK started')
result = c.execute_task(task_id); print('OK executed')

# Submit with execution_log
c.submit_result(task_id, result_file=result['result_file'],
    artifacts=result['artifacts'], execution_log=result['execution_log'])
print('OK submitted')

# Verify execution_log in task snapshot
snapshot = c.load_task(task_id)
assert snapshot.get('execution_log'), f'execution_log missing in snapshot: {snapshot.keys()}'
print(f'OK execution_log persisted: {snapshot[\"execution_log\"]}')

# Verify events
events_path = Path(board) / 'events' / f'{task_id}.jsonl'
events = [json.loads(l) for l in events_path.read_text(encoding='utf-8').splitlines()]
event_types = [e['type'] for e in events]
assert 'result_submitted' in event_types, f'no result_submitted: {event_types}'

# Verify artifacts in event payload carry execution_log
submitted_events = [e for e in events if e['type'] == 'result_submitted']
assert len(submitted_events) == 1, f'expected 1 result_submitted event, got {len(submitted_events)}'
payload = submitted_events[0].get('payload', {})
assert 'execution_log' in payload.get('artifacts', {}), f'execution_log missing in payload artifacts: {payload}'
print(f'OK events complete')
print('ALL OK: contractor lifecycle complete')
"@
if ($LASTEXITCODE -ne 0) { throw "Step 3 failed" }

# Step 4: Verify result file exists
if (-not (Test-Path "$results\smoke-task-001-result.json")) { throw "result file missing" }
Write-Output "OK result file exists"

Write-Output "ALL OK: contractor smoke test passed"
