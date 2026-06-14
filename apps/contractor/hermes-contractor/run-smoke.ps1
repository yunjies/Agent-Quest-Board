$ErrorActionPreference = "Stop"

$root = "$env:TMP\hermes-contractor-smoke-$PID"
$results = "$root\results"
$logs = "$root\logs"
$board = "$root\board"
$null = New-Item -ItemType Directory -Path $root -Force

Write-Output "Hermes contractor smoke: verify full contractor lifecycle"

$env:PYTHONPATH = "packages/board-core;packages/principal-sdk;adapters/filesystem;apps/contractor/hermes-contractor"
$taskId = "smoke-task-001"

# 1. Register identities and contractor
python -c @"
from agent_delegation_filesystem import init_board, register_identity
from agent_delegation_hermes_contractor import CONTRACTOR_IDENTITY, HermesContractor

init_board('$board')
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

c = HermesContractor('$board', results_dir='$results', logs_dir='$logs')
ident = c.ensure_registered()
assert ident['role_type'] == 'contractor', f'role mismatch: {ident}'
assert ident['identity_id'] == 'contractor-duoduo', f'id mismatch: {ident}'
print('OK identity registered')
"@

# 2. Publish task
python -c @"
from agent_delegation_filesystem import publish_task
task = {
    'task_id': '$taskId',
    'title': 'Hermes contractor smoke task',
    'principal_identity_id': 'principal-codex-pc',
    'contractor_identity_id': 'contractor-duoduo',
    'board_identity_id': 'board-duoduo',
    'status': 'published',
    'board_protocol_version': '1.0',
}
publish_task('$board', task, 'principal-codex-pc')
print('OK task published')
"@

# 3. Contractor claims, starts, executes, submits
python -c @"
import json
from pathlib import Path
from agent_delegation_hermes_contractor import HermesContractor

c = HermesContractor('$board', results_dir='$results', logs_dir='$logs')
c.claim_task('$taskId'); print('OK claimed')
c.start_execution('$taskId'); print('OK started')
result = c.execute_task('$taskId'); print('OK executed')
c.submit_result('$taskId', result_file=result['result_file'], artifacts=result['artifacts']); print('OK submitted')

events_path = Path('$board') / 'events' / '$taskId.jsonl'
events = [json.loads(l) for l in events_path.read_text(encoding='utf-8').splitlines()]
event_types = [e['type'] for e in events]
assert 'result_submitted' in event_types, f'no result_submitted: {event_types}'
print(f'OK events: {\" -> \".join(event_types)}')
print('ALL OK: contractor lifecycle complete')
"@

Write-Output "ALL OK: contractor smoke test passed"
