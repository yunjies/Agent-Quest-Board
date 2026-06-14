# Principal SDK

Principal identity helpers:

- build task specifications
- score delegation quality
- choose acceptance level
- publish task
- submit review
- score contractor

Core protocol logic must remain in `packages/board-core`.

The current package implements deterministic local helpers for task creation:

- `score_delegation`
- `choose_acceptance_level`
- `build_task_spec`

Low-score tasks cannot be published without explicit acceptance tests. This
keeps underspecified delegation from becoming silent contractor guesswork.
