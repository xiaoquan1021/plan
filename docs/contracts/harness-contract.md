# XQ Ledger Harness Contract

## Purpose

Define how public task definitions, private runtime truth, and public snapshots interact for the XQ integrated rebuild plan.

## Authoritative Definition Source

Task definitions live under `ledger/task-definitions/` and are registered by `ledger/task-definitions/index.yaml`.

Definitions store planning facts only: task identity, milestone, epic, dependencies, source contracts, allowed logical scopes, forbidden actions, claimability rules, machine acceptance, required evidence, decision metadata, and supersession.

Definitions do not prove implementation completion.

## Runtime Truth Source

Real execution truth comes from private append-only event logs, completion records, command runner artifacts, lease records, workspace reconciliation reports, and hashes of source, contracts, task packs, gate results, and reviews.

Private runtime inputs are never committed directly to this public repository.

## Public Projection

Public snapshots combine:

```text
task definitions
+ sanitized private runtime projection
+ completion record projection
+ workspace reconciliation projection
```

When private inputs are absent, projection may show planning state and dependency claimability only. It must not synthesize new `completed` states.

## Legal Task Runtime States

- `not-executable-index`
- `ready-for-ledger-review`
- `claimed`
- `in-progress`
- `completed`
- `failed-retry-ready`
- `blocked`
- `stale-completion`
- `lease-expired`

Do not add new runtime states without updating schemas, selector, preflight, summary generation, and tests.

## Decision State

Design choices use `decision_state`:

```text
none
open
proposed
approved
rejected
superseded
```

Decision state is not task runtime state.

## Deterministic Snapshot Generation

Definitions-only `generated_at` is derived only from `SOURCE_DATE_EPOCH`; when it is unset, the fixed value is `1970-01-01T00:00:00+00:00`. Definitions-only snapshots must never read Git HEAD commit time.

Full projection `generated_at` is derived from the newest valid timestamp in runtime, completion, and workspace reconciliation inputs; if none exists, it uses `SOURCE_DATE_EPOCH`. Input timestamps are parsed as ISO 8601 with timezone and normalized to UTC. Wall-clock now is forbidden for committed snapshots.

Generator output must use stable JSON key order, stable array ordering, UTF-8, LF newlines, repository-relative logical paths, and redacted private paths.

Atomic Task Pack SHA256 is computed from the parsed Task Pack object after normalizing `task_pack_sha256` to `null`, serializing with sorted JSON keys, UTF-8, and fixed LF. An `issued` pack must declare the computed hash. A `draft` pack must keep `task_pack_sha256: null`.

## Snapshot Check

`harness/generate_snapshots.py --check` regenerates into a temporary directory and compares without overwriting the repository. Differences must report the field/source that changed.

## Milestone Status Rollup

Milestone `contract_status`, `implementation_status`, and `acceptance_status` are generated rollups. Markdown and task definitions do not hand-maintain completed implementation or passed acceptance state.

## Command Capture

Implementation task commands must be captured through runner-backed artifacts before a task can be completed. Handwritten command summaries are not sufficient evidence.
