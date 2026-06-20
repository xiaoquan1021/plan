# Status Aggregation Policy

## Purpose

Define milestone rollup status as generated data, not hand-maintained Markdown state.

## Product Milestones

Product milestones use:

- `contract_status`
- `implementation_status`
- `acceptance_status`

## Plan Rewrite Milestones

PR-M0 through PR-M3 use:

- `contract_readiness_status`
- `plan_acceptance_status`

Plan rewrite task completion can make a contract ready for approval, but it does not make a product implementation complete and does not create formal plan acceptance.

## Contract Status

Values: `not-started`, `draft`, `approved`, `superseded`, `blocked`.

`approved` requires a valid Codex A contract approval record. Contract SHA changes invalidate prior approval. Child plan completion does not approve a contract.

## Implementation Status

Values: `not-started`, `in-progress`, `completed`, `stale`, `blocked`.

`in-progress` comes from runtime event projection. `completed` requires all required implementation tasks to have valid Codex B Gate Results. Documentation-only completion never implies implementation completion.

## Acceptance Status

Values: `not-run`, `in-progress`, `passed`, `failed`, `stale`, `blocked`.

`passed` requires `contract_status == approved`, `implementation_status == completed`, all required implementation tasks completed without stale evidence, and a valid Codex A Epic Review with decision `accepted`. Contract, base commit, dependency lock, or acceptance evidence changes stale the status. A milestone with implementation `not-started`, `in-progress`, or `blocked` can never have acceptance `passed`.

Accepted Epic Reviews are valid only when they contain no blocking unresolved risks, their review base/head match workspace reconciliation, and every required task result commit is integrated into the reviewed Epic head.

## Plan Acceptance Status

Values: `not-run`, `in-progress`, `accepted`, `repair-required`, `blocked`, `stale`.

`accepted` requires valid Plan Gate and Plan Rewrite Review evidence bound to the current plan commit, current snapshot hashes, migration check evidence, schema validation evidence, and public preflight evidence. PR task completion alone does not imply formal plan acceptance.

The Plan Gate and Codex A Plan Rewrite Review are separate accepted records. A single completed plan task, a single review record, or free-form CI text is insufficient. If either record is absent the status stays `not-run`, `in-progress`, or `blocked` according to runtime state. If either record is present but hash, commit, snapshot, migration, public preflight, or CI evidence is invalid, the status is `stale`.

Plan review commit binding avoids self-reference: `plan_commit_sha` is the reviewed target commit, not necessarily the commit that stores the review record. Later commits may add only review/evidence files. Any later change to evaluated plan content, schemas, harness, workflows, snapshots, contracts, task definitions, or migration definitions invalidates the review.

## Generator Rule

Snapshot generator computes these values. Markdown describes rules only.
