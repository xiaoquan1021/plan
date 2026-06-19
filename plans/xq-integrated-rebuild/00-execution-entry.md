# XQ Integrated Rebuild Execution Entry

## Purpose

This is the stable public entry point for the XQ integrated rebuild plan.

## Logical Workspaces

- `PLAN_WORKSPACE`: this public plan repository.
- `IMPLEMENTATION_WORKSPACE`: the integrated XQ rebuild implementation checkout/worktree.
- `LEGACY_EVIDENCE_ROOTS`: old XQ and related local evidence roots.
- `ACCEPTANCE_PROJECT`: private or de-identified L2 acceptance project binding.

Concrete local paths are stored only in ignored local bindings.

## Normative Order

Follow `docs/contracts/normative-precedence.md`. Reports and chat summaries are non-normative.

## Execution Rule

Do not start implementation until XQ-M0 Repository Execution Readiness is satisfied:

- repository strategy ADR approved
- implementation baseline frozen
- stable `base_commit`
- rollback point
- valid local path/toolchain bindings
- first task pack issued with `execution_ready: true`

## Anti-Wrapper Acceptance Rule

Loaded project data must enter XQ-owned objects:

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

Passing through an import shell, compatibility facade, plugin shell, MITK wrapper, BlueBerry wrapper, CTK wrapper, or external library object graph is not acceptance.
