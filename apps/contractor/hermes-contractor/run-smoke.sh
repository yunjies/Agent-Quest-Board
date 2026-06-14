#!/usr/bin/env sh
set -eu

root="${TMPDIR:-/tmp}/hermes-contractor-smoke-$$"
results="$root/results"
logs="$root/logs"
board="$root/board"

printf 'Hermes contractor smoke: verify full contractor lifecycle\n'

# 1. Init board
PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/contractor/hermes-contractor" \
python -c "
from agent_delegation_filesystem import init_board, register_identity
from agent_delegation_hermes_contractor import CONTRACTOR_IDENTITY, HermesContractor
init_board('$board')

# Register identities
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
    register_identity('$board', ident)

# Register and verify contractor
c = HermesContractor('$board', results_dir='$results', logs_dir='$logs')
ident = c.ensure_registered()
assert ident['role_type'] == 'contractor', f'role mismatch: {ident}'
assert ident['identity_id'] == 'contractor-duoduo', f'id mismatch: {ident}'
print('OK identity registered')
" 2>&1

# 2. Publish a task (simulate principal)
task_id='smoke-task-001'
PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/contractor/hermes-contractor" \
python -c "
from agent_delegation_filesystem import publish_task

task = {
    'task_id': '$task_id',
    'title': 'Hermes contractor smoke task',
    'principal_identity_id': 'principal-codex-pc',
    'contractor_identity_id': 'contractor-duoduo',
    'board_identity_id': 'board-duoduo',
    'status': 'published',
    'board_protocol_version': '1.0',
}
publish_task('$board', task, 'principal-codex-pc')
print('OK task published')
" 2>&1

# 3. Contractor claims and executes
PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/contractor/hermes-contractor" \
python -c "
import json
from pathlib import Path
from agent_delegation_hermes_contractor import HermesContractor

c = HermesContractor('$board', results_dir='$results', logs_dir='$logs')
c.ensure_registered()

# Claim
c.claim_task('$task_id')
print('OK claimed')

# Start
c.start_execution('$task_id')
print('OK started')

# Execute (mock: just write result)
result = c.execute_task('$task_id')
print('OK executed')

# Submit
c.submit_result('$task_id', result_file=result['result_file'], artifacts=result['artifacts'])
print('OK submitted')

# Verify events
events_path = Path('$board') / 'events' / '$task_id.jsonl'
events = [json.loads(l) for l in events_path.read_text(encoding='utf-8').splitlines()]
event_types = [e['type'] for e in events]
assert 'status_changed' in event_types, f'no status_changed: {event_types}'
assert 'result_submitted' in event_types, f'no result_submitted: {event_types}'
print(f'OK events complete: {\" -> \".join(event_types)}')
print(f'ALL OK: contractor lifecycle complete for $task_id')
" 2>&1

# 4. Verify result file exists
test -f "$results/smoke-task-001-result.json"
printf 'OK result file exists\n'

# 5. Verify assigned tasks can be scanned
PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/contractor/hermes-contractor" \
python -c "
from agent_delegation_hermes_contractor import HermesContractor
c = HermesContractor('$board', results_dir='$results', logs_dir='$logs')
tasks = c.get_assigned_tasks()
assert len(tasks) >= 1, f'no assigned tasks found: {tasks}'
assert tasks[0]['task_id'] == '$task_id'
print(f'OK scan assigned tasks: {len(tasks)} found')
print(f'ALL OK: contractor identity, claim, execute, submit, scan all work')
" 2>&1
