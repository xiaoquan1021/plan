# ADR-0001: Rebuild Repository Strategy

## Status

Approved by Codex A on 2026-06-22.

## Decision

Create a separate new repository for XQ integrated rebuild (Alternative approach).

The implementation workspace is **XQrebuild**, independent from the legacy XQ repository lineage.

## Approved Policy

- XQrebuild is the clean implementation workspace with no legacy dependencies.
- New integrated build has no dependency on legacy `Code/`, MITK, BlueBerry, CTK, or legacy plugin workbench targets.
- Legacy XQ evidence roots (XQ1, XQ-fresh-ui, XQ-wrong, Externals, etc.) remain read-only references for behavior evidence only.
- Path bindings reflect this decision: `IMPLEMENTATION_WORKSPACE` points to XQrebuild, `LEGACY_EVIDENCE_ROOTS` includes XQ1 and related directories.
- The separate repository strategy eliminates historical coupling and simplifies the new architecture.

## Rejected Alternative

Performing the integrated rebuild in the existing XQ repository lineage was considered but rejected to avoid entanglement with legacy build systems and plugin architectures.

## Consequence

- XQ-M0-001 baseline freeze can proceed with XQrebuild as `IMPLEMENTATION_WORKSPACE`.
- Workspace reconciliation will establish the initial baseline in XQrebuild.
- Legacy evidence is consulted for behavioral reference but does not dictate new architecture ownership.
