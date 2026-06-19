# XQ Integrated Rebuild Plan

This repository is the public contract, task-definition, and projection system for the XQ integrated rebuild.

## Start Here

- [Execution entry](plans/xq-integrated-rebuild/00-execution-entry.md)
- [Normative precedence](docs/contracts/normative-precedence.md)
- [Harness contract](docs/contracts/harness-contract.md)
- [Source reconciliation](docs/contracts/source-of-truth-reconciliation.md)
- [Agent orchestration](docs/contracts/agent-orchestration-contract.md)
- [Public state summary](ledger/snapshots/public-state-summary.json)

## Public Contents

- Normative contracts for scope, architecture, data semantics, dependencies, fixtures, privacy, Git/worktree use, and Agent responsibilities.
- Authoritative public task definitions under `ledger/task-definitions/`.
- Public schemas under `ledger/schema/`.
- Deterministic public snapshots under `ledger/snapshots/`.
- Harness scripts used to validate schemas, task graph, migrations, environment bindings, and snapshot generation.

## Private Contents Not Stored Here

Private task event logs, completion records, command artifacts, workspace reconciliation reports, local absolute paths, and medical data are intentionally excluded.

Local-only bindings belong in ignored files:

```text
config/path-bindings.local.json
config/toolchain-bindings.local.json
```

## Snapshot Rule

`ledger/snapshots/*` is generated from:

```text
task definitions
+ sanitized private runtime projection
+ completion record projection
+ workspace reconciliation projection
```

Do not edit snapshots by hand.

## Public CI Equivalent

```bash
python -m pytest harness/tests
python -m py_compile harness/*.py
python harness/validate_schema.py
python harness/validate_task_graph.py
python harness/generate_snapshots.py --definitions-only --check
python harness/migrate_legacy_ledger.py --check
python harness/preflight_environment.py --bindings config/toolchain-bindings.example.json
```
