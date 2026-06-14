#!/usr/bin/env sh
set -eu

root="${TMPDIR:-/tmp}/lark-topic-board-smoke-$$"
map_store="$root/topic-map.json"
mkdir -p "$root"

printf 'Lark topic board smoke: verify event routing and topic lifecycle\n'

# 1. Verify notification routing for all event types
PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/board-interface/lark-topic-board" \
python -c "
import json, tempfile
from agent_delegation_lark_topic_board import LarkTopicBoard

board = LarkTopicBoard(mapping_store='$map_store')

# Simulate events
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
print(f'OK generated {len(notifications)} notifications from {len(events)} events')

# Check each notification
for notif in notifications:
    print(f'  [{notif[\"route\"]}] → {notif[\"to\"]}: {notif[\"title\"]}')

# Verify task_published needs topic creation
assert notifications[0]['needs_topic_creation'], 'first event should request topic creation'
assert notifications[3]['pending_close'], 'review_approved should trigger pending close'

print('OK notification routing works for all event types')
" 2>&1

# 2. Verify topic mapping lifecycle
PYTHONPATH="packages/board-core:packages/principal-sdk:adapters/filesystem:apps/board-interface/lark-topic-board" \
python -c "
from agent_delegation_lark_topic_board import LarkTopicBoard
import json

board = LarkTopicBoard(mapping_store='$map_store')

# Assign topic
board.assign_topic('task-001', 'oc_example_topic_id')
assert board.get_topic_for_task('task-001')['topic_id'] == 'oc_example_topic_id'
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
store_path = '$map_store'
data = json.loads(open(store_path, encoding='utf-8').read())
assert 'task-001' in data, 'topic map should persist'
assert data['task-001']['status'] == 'closed'
print('OK topic map persisted to disk')
print('ALL OK: lark topic board smoke test passed')
" 2>&1
