#!/usr/bin/env sh
set -eu

root="${TMPDIR:-/tmp}/agent-board-codex-example-$$"
desc="$root/task.md"
out="$root/task.json"
board="$root/board"
mkdir -p "$root"
printf '%s\n' "Codex principal example smoke. Verify task snapshot and event log." > "$desc"

python adapters/codex-local/codex_principal.py \
  --title "Codex principal smoke" \
  --description-file "$desc" \
  --principal-id principal-codex-pc \
  --contractor-id contractor-duoduo \
  --board-id board-duoduo \
  --acceptance-test "task snapshot exists" \
  --acceptance-test "event log exists" \
  --output "$out" \
  --board-root "$board" \
  --register-example-identities

task_id="$(python -c "import json;print(json.load(open('$out', encoding='utf-8'))['task_id'])")"
test -f "$board/tasks/active/$task_id.json"
test -f "$board/events/$task_id.jsonl"
printf 'OK %s\n' "$task_id"
