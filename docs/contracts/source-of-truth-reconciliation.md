# Source Of Truth Reconciliation

## Purpose

Classify the evidence available to the XQ rebuild without writing machine-specific absolute paths into public contracts.

## Logical Bindings

- `PLAN_WORKSPACE`: public plan repository.
- `IMPLEMENTATION_WORKSPACE`: XQ integrated rebuild implementation checkout/worktree.
- `LEGACY_EVIDENCE_ROOTS`: local roots used as historical behavior and source evidence.
- `ACCEPTANCE_PROJECT`: private or de-identified project used for L2 acceptance.
- `PRIVATE_RUNTIME_LEDGER`: private append-only task events or sanitized projection input.
- `PRIVATE_COMPLETION_RECORDS`: private completion records or sanitized projection input.
- `WORKSPACE_RECONCILIATION_REPORT`: private implementation baseline report.

Concrete local paths live only in `config/path-bindings.local.json`, which is ignored by Git.

## Evidence Trust Classes

### Product Behavior Facts

Preferred sources:

1. Approved product requirements.
2. Real acceptance projects.
3. Observable legacy XQ behavior.
4. Explicit user confirmation.

### File Format Facts

Preferred sources:

1. Real files.
2. Official format definitions.
3. Golden fixtures.
4. Verified reader output.

### New Architecture Facts

Only these sources define the new architecture:

1. Approved ADRs.
2. Target Architecture.
3. Core Data Semantics.
4. Final Acceptance Contract.

### Algorithm References

Legacy XQ, SimVascular, papers, and official algorithm documentation may guide behavior, but they do not decide XQ object ownership or module boundaries.

### Current Implementation Facts

Only frozen `IMPLEMENTATION_WORKSPACE` base commits, runner-backed build/test evidence, Codex B Gate Results, and Codex A Epic Reviews count as current implementation facts.

## Current Local Classification

- `XQ1`: primary legacy XQ source and behavior evidence.
- `XQ-fresh-ui`: experimental legacy-derived attempt; reference only.
- `XQ-wrong`: negative/incorrect attempt; reference only.
- root `Code`: partial historical source material; reference only.
- `_refs/svExternals`: SimVascular dependency reference; not an XQ architecture source.
- `Externals`: legacy XQ dependency evidence; not the new rebuild lock.
- `deep-research-report.md`: research reference; not normative.

## Open Evidence Items

- `ACCEPTANCE_PROJECT` for L2 real project acceptance is not approved.
- L1 de-identified fixture strategy is open.
