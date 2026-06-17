# XQ Integrated Rebuild Execution Entry

## Purpose

This is the fixed entry point for executing the XQ integrated rebuild plan.

Use this document first, then follow the owning child document for the current layer or feature. This file is an entry pointer, not a status ledger.

## Source Boundary

- Plan root: `plans/xq-integrated-rebuild/`
- Main index: `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md`
- XQ record source: `<xq-source-archive>`, extracted as `<xq-source-extract>`
- Active XQ workspace: `<xq-implementation-workspace>`, not an record source
- Acceptance project: `<acceptance-project>`

Do not write execution notes or child plans under `<xq-implementation-workspace>`.

## Ledger Position

Plan-position text is no longer stored in this entry document. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in:

- [audit ledger README](../../ledger/README.md)
- [tasks.json](../../ledger/snapshots/tasks.json)
- [source inventory](../../ledger/source-inventory.md)
- [by-document execution index](../../README.md#what-is-not-included)

Do not resume implementation from historical batch summaries or test-count text. Pick repair or implementation work only from `ledger/snapshots/tasks.json` after ledger reconciliation.

## Anti-Wrapper Acceptance Rule

Runtime acceptance must prove that loaded project data enters XQ-owned core objects:

```text
XQProject
XQScene
XQDataNode
XQImageVolume
XQPath
XQContourGroup
XQSegmentationMask
XQSurfaceModel
XQMesh
XQSimulationCase
```

The acceptance project must not pass by stopping at an import shell, compatibility layer, plugin shell, MITK wrapper, BlueBerry wrapper, CTK wrapper, or old framework facade. The loaded data must be available through the integrated XQ project and scene contracts.

## Issue Handling Policy

Possible issues are recorded but not immediately repaired during normal execution. Repair now only if one of these major conditions appears:

```text
the source boundary is violated
the plan requires old MITK, BlueBerry, CTK, or plugin architecture
the blank-project rebuild rule becomes impossible
the acceptance project cannot be represented by XQ-owned core data
a dependency conflict blocks the selected foundation architecture
```

Otherwise, keep moving through the current owning document. Review accumulated possible issues after the first full implementation pass or when the acceptance phase begins.

## How to Resume Work

When resuming implementation:

1. Open this file.
2. Read `Ledger Position`.
3. Open `ledger/snapshots/tasks.json` and select the next allowed repair or implementation task from the ledger.
4. If the current task fails, use the smallest owning document and `09-acceptance-repair/02-failure-routing.md`.
5. Update this file only when the entry-document policy changes.
