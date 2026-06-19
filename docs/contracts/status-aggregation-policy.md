# Status Aggregation Policy

## Purpose

Define milestone rollup status as generated data, not hand-maintained Markdown state.

## Contract Status

Values: `not-started`, `draft`, `approved`, `superseded`, `blocked`.

`approved` requires a valid Codex A contract approval record. Contract SHA changes invalidate prior approval. Child plan completion does not approve a contract.

## Implementation Status

Values: `not-started`, `in-progress`, `completed`, `stale`, `blocked`.

`in-progress` comes from runtime event projection. `completed` requires all required implementation tasks to have valid Codex B Gate Results. Documentation-only completion never implies implementation completion.

## Acceptance Status

Values: `not-run`, `in-progress`, `passed`, `failed`, `stale`, `blocked`.

`passed` requires a valid Codex A Epic Review with decision `accepted`. Contract, base commit, dependency lock, or acceptance evidence changes stale the status.

## Generator Rule

Snapshot generator computes these values. Markdown describes rules only.
