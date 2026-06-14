# Development Ownership

This document defines who builds which part of the current v1 implementation.

## Ownership Split

Codex owns:

- Core protocol and schemas.
- Board state machine rules.
- Compatibility matrix and validation.
- Shared test fixtures and automated tests.
- Principal SDK and Codex Principal adapter.
- Local Codex review and acceptance integration.
- Filesystem and AgentOps read/write abstractions that are platform-neutral.

Duoduo owns:

- Lark topic-board adapter.
- Duoduo Contractor identity registration and Hermes execution adapter.
- Duoduo Board runtime hosting, with strict board identity separation.
- Lark notification routing into the delegation board topic group.
- Hermes-side intake and execution plumbing.

Shared contract:

- `board_protocol_version`
- JSON schemas under `protocol/schemas`
- compatibility matrix under `protocol/compatibility.json`
- integration tests under `tests/`

## Boundary Rules

Core protocol must not import Codex, Duoduo, Lark, Hermes, or local AgentOps-specific code.

Adapters may depend on their platform, but they must translate platform behavior into protocol events and task snapshots.

The board identity is zero-agent. Any LLM reasoning belongs to Principal or Contractor identities, never to Board core.

## Current v1 Mapping

```text
principal-codex-pc -> implemented by Codex Principal adapter
contractor-duoduo  -> implemented by Duoduo Hermes adapter
board-duoduo       -> hosted by Duoduo, constrained by Board protocol
```

## Development Sequence

1. Codex completes protocol/core/test scaffold.
2. Codex completes Principal SDK and Codex Principal adapter.
3. Duoduo completes Lark adapter and Contractor/Hermes adapter.
4. Both sides run compatibility tests against the same protocol version.
5. Board accepts tasks only when Principal, Contractor, and Board versions are compatible.
