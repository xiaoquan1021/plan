# Architecture First Discipline

## Purpose

Prevent the first implementation phase from becoming a collection of small runnable fragments that do not fit together.

## Inputs

- Main plan architecture chain.
- User preference: integrated architecture over early runnable fragments.

## Outputs

- Development discipline for all implementation steps.
- Shared vocabulary for acceptable incomplete code.

## Code Ownership

All future XQ source code.

## Rules

- One integrated application kernel is preferred over many optional modules.
- One `XQScene` owns project data.
- One `XQWorkflow` owns stage progression.
- External libraries are kernels, not the architecture.
- Partial implementations are acceptable before v1 if public contracts are coherent.

## Implementation Contract

Planning contract only. This document governs source-shape decisions before
feature implementation begins; it does not own runtime source files.

Required invariants:

```text
public XQ contracts precede convenience implementation details
partial code may exist only when it preserves the final integrated architecture
missing implementation fails explicitly instead of using fake fallback behavior
UI, IO, workflow, and algorithms share XQProject and XQScene ownership
external libraries remain kernels behind XQ-owned contracts
```

## Test Plan

Document consistency checks:

```text
rg -n "MITK|BlueBerry|CTK|plugin workbench|compatibility shell" plans/xq-integrated-rebuild
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

old-framework wording appears only in forbidden-boundary or rejection text
the audit ledger keeps implementation_resume_allowed false until executable plan gates are clear

## Acceptance

- A future executor can tell incomplete-but-acceptable code from architecture drift.
- No plan step asks for a temporary second project, scene, workflow, or plugin platform.
- Feature documents route missing behavior back to the smallest owning document.

## Step Plan

- [ ] Define public XQ types before filling algorithm bodies.
- [ ] Add empty method bodies only when they preserve the final class shape.
- [ ] Let code fail loudly at missing implementation points instead of adding fake fallback behavior.
- [ ] Keep UI, IO, workflow, and algorithms wired through the same XQ project and scene objects.
- [ ] Delay convenience wrappers until the owning data flow is clear.

## Failure Repair

If a short-term runnable path bypasses `XQProject`, `XQScene`, or `XQWorkflow`, repair the owning feature document and remove that path from the plan.

## Do Not Add

- Mock business objects for the real application.
- Safety switches that select between old and new architectures.
- Per-feature registries that recreate a plugin platform.
- Hidden fallback data stores.
