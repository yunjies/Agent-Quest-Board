# Codex Local Adapter

The Codex local adapter is intended for local Codex CLI based review or principal workflows.

It must rely on local authentication and must not require API keys in repository configuration.

## Current Scope

This adapter provides a local Principal task builder. It does not write to a
real AgentOps instance by default and does not include personal paths.

Example:

```bash
python adapters/codex-local/codex_principal.py \
  --title "Implement board adapter smoke test" \
  --description-file task.md \
  --principal-id principal-codex-pc \
  --contractor-id contractor-duoduo \
  --board-id board-duoduo \
  --acceptance-test "Unit tests pass" \
  --acceptance-test "Result file contains smoke evidence" \
  --output out/task.json
```

The generated JSON can be handed to a Board adapter that implements
`publish_task`.
