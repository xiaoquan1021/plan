# Document Repair Policy

## Purpose

Define how to update the plan tree when a small feature plan is wrong or incomplete.

## Inputs

- Main plan tree.
- Child feature plans.

## Outputs

- A deterministic repair path for rebuild work.

## Code Ownership

This document owns planning workflow only.

## Rules

- Repair the smallest owning document first.
- Do not patch the main plan with implementation detail unless the tree structure changes.
- Do not spread one feature's rules across unrelated documents.
- A child document may reference upstream contracts, but it must not redefine them.

## Implementation Contract

Planning contract only. This document owns how plan defects are repaired; it
does not own runtime source files.

Required invariants:

```text
repair starts in the smallest owning document
adjacent documents change only when their interface contract changes
main plan remains index and routing, not feature implementation detail
source work resumes only after the repaired document states files, interfaces, tests, acceptance, and failure route
```

## Test Plan

Document consistency checks:

```text
python3 harness/audit_xq_zip_analysis.py
bash -lc '! rg -n "Current cursor|Next implementation document|Completed source batch" plans/xq-integrated-rebuild/00-execution-entry.md plans/xq-integrated-rebuild/README.md plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md'
```

Expected result:

state-source lines remain 0 except diagnostic command references
repair work is selected from ledger/snapshots/tasks.json

## Acceptance

- A failed feature has one primary repair document.
- The plan tree does not regain duplicated status mirrors.
- Repaired documents become more executable without moving feature details into the main plan.

## Step Plan

- [ ] Identify the failing feature or layer.
- [ ] Find the owning `.md` in this plan tree.
- [ ] Update that file's `Rules`, `Step Plan`, or `Failure Repair`.
- [ ] Update adjacent layer documents only if their explicit interface changes.
- [ ] Resume implementation from the repaired document.

## Failure Repair

If multiple documents claim ownership of the same small feature, split or rename them so one document has primary ownership.

## Do Not Add

- Global notes that belong in a feature document.
- Duplicate requirements in several sibling documents.
- A second master plan.
