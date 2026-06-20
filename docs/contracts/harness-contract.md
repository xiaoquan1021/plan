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

Generator output must use stable JSON object key order, preserve array order, UTF-8, LF newlines, repository-relative logical paths, and redacted private paths. The generic canonical hash function never sorts arrays. Only fields that a contract explicitly declares as set-valued may be sorted by a dedicated field-specific helper.

Atomic Task Pack SHA256 is computed from the parsed Task Pack object after normalizing `task_pack_sha256` to `null`, serializing with sorted JSON keys, UTF-8, and fixed LF. An `issued` pack must declare the computed hash. A `draft` pack must keep `task_pack_sha256: null`.

Epic Contract SHA256 is the hash of the contract's normative content. It excludes runtime-injected fields such as `_path` and `_computed_sha256`; it is not a file path hash, Git blob hash, or mutable in-memory object hash.

Epic Contract Approval SHA256 is a canonical self-hash. The approval record is parsed, `approval_record_sha256` is normalized to `null`, canonical JSON bytes are hashed, and the declared `approval_record_sha256` plus the Epic Contract's `approval_record.record_sha256` must both equal the computed value.

Accepted Epic Reviews must not contain any unresolved risk with `severity: blocking`. Non-blocking risks are allowed only when owner, evidence or follow-up, and non-blocking rationale are present.

Accepted Epic Reviews must match workspace reconciliation: `review_base_commit` equals `epic_base_commit`, `review_head_commit` equals `epic_head_commit`, and each required task's accepted Gate Result `result_commit` is listed in `integrated_task_commits`.

Plan Rewrite Review SHA256 is also a canonical self-hash. The review is parsed, `review_record_sha256` is normalized to `null`, canonical JSON bytes are hashed, and accepted records must declare that computed value. Object key order is ignored; array order remains normative.

Plan rewrite acceptance requires two independent accepted records for the same PR milestone:

- a `Plan Gate` record proving mechanical checks for the reviewed commit;
- a `Codex A` record proving independent plan architecture and contract review.

Both records must bind to `plan_commit_sha`. The commit must exist and be current `HEAD` or an ancestor of `HEAD`. If the review record is added after the reviewed commit, every changed file between `plan_commit_sha` and `HEAD` must be limited to review or evidence paths; changes to harness, schemas, task definitions, workflows, snapshots, contracts, or migration definitions make the review stale.

Accepted plan rewrite records must carry structured CI evidence for the `plan-contracts` workflow, current public snapshot hashes, migration check evidence, and public preflight evidence. Snapshot hashes are compared against the actual committed public snapshot files. CI evidence must bind workflow, run, commit, success conclusion, and job conclusions; arbitrary text is not accepted.

## Snapshot Check

`harness/generate_snapshots.py --check` regenerates into a temporary directory and compares without overwriting the repository. Differences must report the field/source that changed.

## Milestone Status Rollup

Product milestone `contract_status`, `implementation_status`, and `acceptance_status` are generated rollups. Markdown and task definitions do not hand-maintain completed implementation or passed acceptance state. Product acceptance can pass only when contract is approved, implementation status is completed, all required tasks are completed, and a valid accepted Epic Review exists.

Plan rewrite milestones use `contract_readiness_status` and `plan_acceptance_status`. PR-M0 through PR-M3 task completion can make contracts ready for review, but it does not create formal plan acceptance without a valid Plan Rewrite Review record.

## Command Capture

Implementation task commands must be captured through runner-backed artifacts before a task can be completed. Handwritten command summaries are not sufficient evidence.
