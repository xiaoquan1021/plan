# Plan Kernel Policy

Active Markdown under `plans/xq-integrated-rebuild/` is a plan kernel, not an execution record.

## Allowed

- Purpose, Owns, Rules, Implementation Contract, Step Plan, Test Plan, Acceptance, and Failure Repair.
- Stable future-facing contract language such as `must`, `reject`, `preserve`, and `route`.
- Short links to `ledger/snapshots/tasks.json`, `ledger/deferred-register.md`, and generated execution indexes.

## Disallowed

- `## Execution Record` sections or historical execution-record pointers.
- Historical source-pass, verified command, verified result, current-behavior, or test-count text.
- Deferred detail blocks; deferred boundaries are tracked in `ledger/deferred-register.md`.
- Entry-document status summaries such as current cursor, completed batches, or implementation status.
