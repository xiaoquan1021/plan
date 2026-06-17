# XQ Integrated Rebuild Public Plan Snapshot

This repository is a public planning and automation snapshot for the XQ integrated rebuild: an integrated medical imaging, vascular modeling, meshing, and simulation-preparation application.

Start here:

- [Execution entry](plans/xq-integrated-rebuild/00-execution-entry.md)
- [Plan tree README](plans/xq-integrated-rebuild/README.md)
- [Harness contract](docs/contracts/harness-contract.md)
- [Ledger executor workflow](docs/skills/xq-ledger-executor.md)
- [Public state summary](ledger/snapshots/public-state-summary.json)

## What Is Included

- Public plan Markdown for the integrated rebuild.
- Ledger and harness source code used to enforce task selection, preflight checks, command capture, and record validation.
- JSON schemas for task events and completion record.
- Sanitized task and state snapshots with counts and task selection fields.
- Public contract and workflow documentation.

## What Is Not Included

Private source archives, private acceptance datasets, raw command artifacts, task event history, execution records, session logs, and record JSON are intentionally not included. Placeholder paths such as `<xq-source-archive>`, `<xq-rebuild-workspace>`, `<acceptance-project>`, and `<private-evidence-dir>` must be configured in a private working environment before running a full implementation ledger.

## Public Snapshot Notes

The published task statuses are a sanitized derived snapshot. They preserve planning context, but the private runner-backed artifacts that originally justified completion claims remain private. Treat this repository as a clean public planning system, not as a complete audit record archive.

## Local Harness Smoke Checks

```bash
python3 -m pytest harness/tests
python3 -m py_compile harness/*.py
```

A full `harness/ledger_task.py preflight` run needs a private record/event setup if you want completion provenance checks beyond this public snapshot.
