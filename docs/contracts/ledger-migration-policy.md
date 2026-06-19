# Ledger Migration Policy

## Purpose

Migrate the legacy public task snapshot into structured task definitions without falsifying implementation completion.

## Rules

- Preserve original task IDs when feasible.
- Do not modify or delete original private append-only events.
- Do not modify original completion records.
- Map old task IDs to new milestone, epic, and task IDs.
- Use `superseded_by` for replaced tasks.
- Migration must be repeatable and deterministic.
- Migration report records input hash, output hash, mapping count, unmapped items, and status-change reasons.

## Completed Handling

Documentation completion is not implementation completion. Runner-backed evidence enters reconciliation. Missing or stale evidence becomes `stale-completion` or a revalidation requirement.
