# Agent Delegation Board

Agent Delegation Board is a protocol-first framework for delegating work between agents.

The framework has three runtime roles:

- Principal: publishes tasks, reviews results, and scores contractors.
- Contractor: claims tasks, executes work, submits results, and revises rejected work.
- Board: validates identity, persists state, appends events, routes notifications, and closes approved tasks.

The board is designed to be zero-agent: it should not call an LLM, interpret task content, execute task work, or review quality. Intelligent work belongs to Principal and Contractor agents.

## Repository Layout

```text
docs/                 Product and integration documentation
protocol/             Version matrix, JSON schemas, and fixtures
packages/             Shared Python packages and SDK stubs
adapters/             Platform/runtime adapters
examples/             Example component manifests
tests/                Protocol, compatibility, and integration tests
```

## Version Compatibility

Components declare a `board_protocol_version`. The board accepts interaction only when the principal, contractor, and board protocol versions are compatible according to `protocol/compatibility.json`.

Implementation versions may differ. Protocol compatibility is the contract.

## Public Repository Rules

Do not commit real chat IDs, API keys, tokens, NAS paths, or user-specific config. Use `.example.json` or `.example.yaml` files for samples.

