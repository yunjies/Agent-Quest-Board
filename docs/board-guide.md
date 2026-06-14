# Board Development Guide

The Board identity validates identities, transitions state, appends events, routes notifications, and exports observer data.

## Required Capabilities

- `append_event`
- `transition_status`
- `route_notification`

## Zero-Agent Boundary

The board must not call an LLM, interpret task content, execute tasks, or review quality. It only applies deterministic rules.

## Persistence

The board writes task snapshots, event logs, artifact indexes, ratings, and frontend references. Frontend adapters are optional and must not be the source of truth.

