# ADR-0001: Rebuild Repository Strategy

## Status

Draft, requires Codex A approval before XQ-M0 can execute implementation work.

## Decision

The current proposal is to perform the integrated rebuild in the existing XQ repository lineage using `IMPLEMENTATION_WORKSPACE`, while keeping legacy `Code/` read-only until an explicit archive/delete decision is approved.

## Required Policy If Approved

- New integrated build entry points must not depend on `Code/`.
- New CMake must not call `add_subdirectory(Code)`.
- New targets must not link MITK, BlueBerry, CTK, or legacy plugin workbench targets.
- Legacy and rebuild presets, targets, and tests must be isolated.
- Old `Code/` is historical evidence and compatibility reference only until a later archival ADR.
- Deleting or archiving legacy code requires a separate acceptance-backed decision.

## Alternative

Create a separate new repository for XQ integrated rebuild. This remains an open decision until Codex A approves or rejects it.

## Consequence

Skeleton implementation must not move from contract readiness to execution readiness until this ADR is approved.
