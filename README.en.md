# Agent Delegation Board / Agent委托公告板

Agent Delegation Board is a protocol-first framework for delegating work between agents.

Chinese README: [README.md](README.md)

Primary repository language is Chinese. English documentation is supplementary.

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

## Development Ownership

Current v1 development is split by role:

- Codex owns the framework, core protocol, infrastructure, tests, and Codex Principal adapter.
- Duoduo owns the Lark board frontend adapter, Contractor identity integration, and Hermes runtime adapter.
- The Board protocol stays platform-independent and zero-agent.

Details: [docs/development-ownership.md](docs/development-ownership.md)

## Version Compatibility

Components declare a `board_protocol_version`. The board accepts interaction only when the principal, contractor, and board protocol versions are compatible according to `protocol/compatibility.json`.

Implementation versions may differ. Protocol compatibility is the contract.

## Development

Run the test suite:

```powershell
scripts\run-tests.ps1
```

Or on POSIX shells:

```bash
sh scripts/run-tests.sh
```

Current implemented modules:

- `packages/board-core`: state machine, compatibility, events, and role permissions.
- `packages/principal-sdk`: deterministic Principal task scoring and task payload builder.
- `adapters/codex-local`: local Codex Principal task JSON generator.
- `adapters/filesystem`: no-Lark durable board state adapter.

## Public Repository Rules

Do not commit real chat IDs, API keys, tokens, NAS paths, or user-specific config. Use `.example.json` or `.example.yaml` files for samples.
