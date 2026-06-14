$ErrorActionPreference = "Stop"

$root = "$env:TMP\lark-topic-board-smoke-$PID"
$mapStore = "$root\topic-map.json"
$null = New-Item -ItemType Directory -Path $root -Force

Write-Output "Lark topic board smoke: verify event routing and topic lifecycle"

$env:PYTHONPATH = "packages/board-core;packages/principal-sdk;adapters/filesystem;apps/board-interface/lark-topic-board"

# 1. Verify notification routing
python -c @"
from agent_delegation_lark_topic_board import LarkTopicBoard
board = LarkTopicBoard(mapping_store='$mapStore')

events = [
    {'type': 'task_published', 'task_id': 'task-001', 'actor_identity_id': 'principal-codex-pc', 'payload': {'title': 'Test task'}},
    {'type': 'result_submitted', 'task_id': 'task-001', 'actor_identity_id': 'contractor-duoduo', 'payload': {'title': 'Test task'}},
    {'type': 'review_rejected', 'task_id': 'task-001', 'actor_identity_id': 'principal-codex-pc', 'payload': {'title': 'Test task', 'revision_request': 'Missing smoke evidence'}},
    {'type': 'review_approved', 'task_id': 'task-001', 'actor_identity_id': 'principal-codex-pc', 'payload': {'title': 'Test task'}},
    {'type': 'task_closed', 'task_id': 'task-001', 'actor_identity_id': 'board-duoduo', 'payload': {}},
]
tasks = [{'task_id': 'task-001', 'title': 'Test task'}]
notifs = board.batch_process_events(events, tasks=tasks)

assert len(notifs) == 5, f'expected 5 notifications, got {len(notifs)}'
assert notifs[0]['needs_topic_creation']
assert notifs[3]['pending_close']
for n in notifs:
    print(f"  [{n['route']}] -> {n['to']}: {n['title']}")
print('OK notification routing works')
"@

# 2. Verify topic mapping lifecycle
python -c @"
from agent_delegation_lark_topic_board import LarkTopicBoard
board = LarkTopicBoard(mapping_store='$mapStore')
board.assign_topic('task-001', 'oc_example_topic_id')
assert board.is_topic_active('task-001')
board.close_topic('task-001')
assert not board.is_topic_active('task-001')
import json
data = json.loads(open('$mapStore', encoding='utf-8').read())
assert data['task-001']['status'] == 'closed'
print('OK topic lifecycle complete')
print('ALL OK: lark topic board smoke test passed')
"@
