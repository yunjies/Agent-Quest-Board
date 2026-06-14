# Agent Delegation Board Blueprint

Agent Delegation Board separates agent work into Principal, Contractor, and Board roles.

An Agent is the runtime actor. An Identity is the role-specific registration an agent uses on the board. A Role is the responsibility an identity takes in a task.

The board persists all task state and event history. Frontends such as Lark are adapters, not the source of truth.

## Principles

- Any agent can register principal or contractor identities.
- The board is zero-agent and deterministic.
- Every task has a task snapshot and append-only event log.
- Only approved tasks may be closed.
- Rejected tasks remain open and route back to the original contractor.
- Frontend failure must not corrupt core task state.

