# Source Boundary And Rules

## Purpose

Define the record boundary and non-negotiable rebuild rules for all child plans.

## Inputs

- `<xq-source-archive>`
- `<xq-source-extract>`
- `<acceptance-project>`
- `<xq-rebuild-workspace>`
- SimVascular behavior and project-format observations

## Outputs

- A stable record rule for rebuild work.
- A stable prohibition list for architecture drift.

## Code Ownership

This document does not own future source code. It governs all planned source directories.

## Rules

- Do not use `<xq-implementation-workspace>` as audit record.
- Do not write plan files under `<xq-implementation-workspace>`.
- Keep all child `.md` files for this rebuild under `plans/xq-integrated-rebuild`.
- Future source implementation must start from `<xq-rebuild-workspace>` unless this plan is explicitly updated before source changes begin.
- Do not copy SimVascular source or ThirdParty code into XQ.
- Do not build the new XQ around MITK, BlueBerry, CTK, or a plugin workbench.
- Do not rename compatibility into "native" unless the code is inside the integrated core path and uses XQ-owned data types.

## Implementation Contract

Planning contract only. This document owns evidence-boundary rules and forbidden
architecture drift for all child documents; it does not own runtime source files.

Required invariants:

```text
XQ record source remains <xq-source-archive> extracted at <xq-source-extract>
active <xq-implementation-workspace> is not record for this analysis
planning files remain under plans/xq-integrated-rebuild
future implementation starts from the selected blank target root
MITK, BlueBerry, CTK, plugin workbench, and compatibility shells remain forbidden architecture owners
```

## Test Plan

Document consistency checks:

```text
rg -n "<xq-implementation-workspace>" plans/xq-integrated-rebuild plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

<xq-implementation-workspace> appears only as a non-evidence active/future implementation boundary
scope_violations remains 0 in the separate scope check

## Acceptance

- The record boundary is unambiguous before any source or plan work starts.
- No child document may cite `<xq-implementation-workspace>` as audit record.
- Future implementation remains integrated XQ architecture, not an old framework bridge.

## Step Plan

- [ ] Confirm `<xq-source-archive>` exists before auditing old XQ behavior.
- [ ] Confirm `<xq-source-extract>` is the only extracted XQ record tree.
- [ ] Confirm `<acceptance-project>` remains the real project acceptance sample.
- [ ] Confirm `<xq-rebuild-workspace>` is the default blank implementation root.
- [ ] Keep all planning documents under `plans/xq-integrated-rebuild`.
- [ ] During implementation, create files only in a blank target root; `<xq-implementation-workspace>` can be that target only after the user explicitly chooses it and accepts that implementation will be rebuilt from empty structure.

## Failure Repair

If an implementation decision cites active `<xq-implementation-workspace>` as record, repair this document and the affected child document before continuing.

## Do Not Add

- Active-workspace audit notes.
- SimVascular source migration steps.
- "Temporary" MITK/BlueBerry/CTK bridge plans.
- Loose `.md` files outside the dedicated plan tree.
