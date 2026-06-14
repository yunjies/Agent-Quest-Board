$ErrorActionPreference = "Stop"

$root = "$env:TMP\lark-topic-board-smoke-$PID"
$mapStore = "$root\topic-map.json"
$null = New-Item -ItemType Directory -Path $root -Force

$env:PYTHONPATH = "packages/board-core;packages/principal-sdk;adapters/filesystem;apps/board-interface/lark-topic-board"
$env:MAP_STORE = $mapStore

Write-Output "Lark topic board smoke: verify event routing, topic lifecycle, exit codes"

# Step 1: Notification routing for all event types
$step1 = "$root\step1_notifications.py"
@'
import os
from agent_delegation_lark_topic_board import LarkTopicBoard

board = LarkTopicBoard(mapping_store=os.environ['MAP_STORE'])

events = [
    {'type': 'task_published', 'task_id': 'task-001', 'actor_identity_id': 'principal-codex-pc', 'payload': {'title': 'Test task'}},
    {'type': 'result_submitted', 'task_id': 'task-001', 'actor_identity_id': 'contractor-duoduo', 'payload': {'title': 'Test task'}},
    {'type': 'review_rejected', 'task_id': 'task-001', 'actor_identity_id': 'principal-codex-pc', 'payload': {'title': 'Test task', 'revision_request': 'Missing smoke evidence'}},
    {'type': 'review_approved', 'task_id': 'task-001', 'actor_identity_id': 'principal-codex-pc', 'payload': {'title': 'Test task'}},
    {'type': 'task_closed', 'task_id': 'task-001', 'actor_identity_id': 'board-duoduo', 'payload': {}},
    {'type': 'incident_created', 'task_id': 'task-001', 'actor_identity_id': 'board-duoduo', 'payload': {'error': 'Lark API timeout'}},
]
tasks = [{'task_id': 'task-001', 'title': 'Test task'}]
notifications = board.batch_process_events(events, tasks=tasks)
count = len(notifications)
print('OK generated ' + str(count) + ' notifications from ' + str(len(events)) + ' events')

for n in notifications:
    print("  [" + n['route'] + "] -> " + n['to'] + ": " + n['title'])

assert notifications[0]['needs_topic_creation'], 'first event should request topic creation'
assert notifications[3]['pending_close'], 'review_approved should trigger pending close'
print('OK notification routing works for all event types')
'@ | Set-Content -Path $step1 -Encoding UTF8
python $step1
if ($LASTEXITCODE -ne 0) { throw "Step 1 failed" }

# Step 2: Topic mapping lifecycle
$step2 = "$root\step2_lifecycle.py"
@'
import os, json
from agent_delegation_lark_topic_board import LarkTopicBoard

board = LarkTopicBoard(mapping_store=os.environ['MAP_STORE'])

# Assign topic
board.assign_topic('task-001', 'example-topic-id')
entry = board.get_topic_for_task('task-001')
assert entry['topic_id'] == 'example-topic-id', 'topic_id mismatch: ' + str(entry)
assert board.is_topic_active('task-001'), 'topic should be active'
print('OK topic assigned and active')

# Close topic
board.close_topic('task-001')
assert not board.is_topic_active('task-001'), 'topic should be closed'
closed_entry = board.get_topic_for_task('task-001')
assert closed_entry['status'] == 'closed'
assert 'closed_at' in closed_entry
print('OK topic closed with timestamp')

# Verify persistence
store_path = os.environ['MAP_STORE']
data = json.loads(open(store_path, encoding='utf-8').read())
assert 'task-001' in data, 'topic map should persist'
assert data['task-001']['status'] == 'closed'
print('OK topic map persisted to disk')
print('ALL OK: lark topic board smoke test passed')
'@ | Set-Content -Path $step2 -Encoding UTF8
python $step2
if ($LASTEXITCODE -ne 0) { throw "Step 2 failed" }

# Cleanup
Remove-Item -Path $root -Recurse -Force
