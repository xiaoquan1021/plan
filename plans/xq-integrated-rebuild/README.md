# XQ Integrated Rebuild Plan Tree

## Start Here

Execution entry:

- [00-execution-entry.md](00-execution-entry.md)

This README no longer mirrors authoritative runtime-position text. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in:

- [audit ledger README](../../ledger/README.md)
- [tasks.json](../../ledger/snapshots/tasks.json)
- [source inventory](../../ledger/source-inventory.md)

Do not resume implementation from historical batch summaries or test-count text. Pick repair or implementation work only from `ledger/snapshots/tasks.json` after ledger reconciliation.

## Purpose

This directory stores the detailed implementation plan for rebuilding XQ as an integrated medical imaging, vascular modeling, meshing, and simulation-preparation application.

Each `.md` file owns exactly one layer or small feature. If a feature fails during implementation, revise the owning file first, then continue. Do not move feature-specific detail into the main plan.

All child planning documents for this rebuild live in this dedicated folder tree:

```text
plans/xq-integrated-rebuild/
```

Do not create rebuild planning notes under `<xq-implementation-workspace>`. That path is an active refactor workspace and may only be used later as an implementation target after the user explicitly chooses the target directory.

## Source Boundary

- XQ record source: `<xq-source-archive>`, extracted as `<xq-source-extract>`.
- Default blank implementation root: `<xq-rebuild-workspace>`.
- Active XQ workspace: `<xq-implementation-workspace>`, future implementation target only after explicit user decision.
- Real acceptance project: `<acceptance-project>`.
- SimVascular role: functional and project-format reference, not source-code migration source.

## Execution Principle

Architecture first, runtime later. Future source code must start from `<xq-rebuild-workspace>` unless this plan is explicitly updated before source changes begin. Before the first complete version, partial code may be incomplete or temporarily unable to run. The unacceptable failure is architectural drift: plugin-style workbench, dual scene ownership, temporary adapters that become permanent, or business code depending directly on external library object models.

## Document Rules

Each child document must stand on its own for its layer or small feature. Before source changes start for that area, the document must define:

- purpose
- inputs
- outputs
- rules
- step plan
- acceptance checks
- failure repair route

Document completion means the planning structure exists and covers the topic. It does not mean source code exists, builds, runs, or passes runtime acceptance.

## Folder Map

| Folder | Responsibility |
| --- | --- |
| `00-execution-entry.md` | Execution entry and ledger pointer. |
| `00-governance` | Source boundary, architecture discipline, repair policy. |
| `01-foundation` | Empty project skeleton, top-level CMake, dependency superbuild. |
| `02-core-data` | XQ-owned project, scene, node, and domain payload types. |
| `03-native-project-io` | Native loading of SimVascular-style project files and XQ save format. |
| `04-medical-image-io` | DICOM and common medical image formats. |
| `05-workbench-visualization` | Integrated Qt workbench, four-pane layout, and VTK visualization. |
| `06-workflow` | Workflow state, source relations, command and undo model. |
| `07-domain-features` | Path, contour, segmentation, modeling, meshing, simulation, ROM, multiphysics. |
| `08-xq-zip-selection` | How to select/rewrite code from `<xq-source-extract>`. |
| `09-acceptance-repair` | Final acceptance and failure routing. |

## Hardening Before Source Changes

Use the planning hardening order in [00-execution-entry.md](00-execution-entry.md) before source changes start. Source changes are allowed only after the owning child document defines exact files, interfaces, commands, tests, acceptance checks, and repair route for that layer or feature.

## Repair Rule

When implementation reveals a wrong assumption:

1. Identify the smallest owning `.md`.
2. Update that `.md`.
3. If the update changes another layer's contract, update only the directly affected upstream/downstream `.md`.
4. Leave the main plan as an index unless the document tree itself changes.
