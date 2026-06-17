# XQ Ledger Harness Contract

This document describes the public contract for the XQ plan ledger harness.

## State Model

Tasks are selected from `ledger/snapshots/tasks.json`. Runtime events are append-only records in a private ledger event log when executing real work. Public snapshots omit raw event history and record artifacts.

Primary task states:

- `not-executable-index`: navigation or index document, not claimable work.
- `ready-for-ledger-review`: claimable task whose dependencies are satisfied.
- `claimed`: task lease exists but execution has not completed.
- `in-progress`: task has started under an active lease.
- `completed`: task completed in the private ledger; public record artifacts are omitted.
- `failed-retry-ready`: retryable failure that may be claimed again.
- `blocked`: non-retryable block requiring repair or explicit reopen.
- `stale-completion`: source changed after completion record and must be rerun privately.
- `lease-expired`: claimed task whose lease has expired.

## Event Contract

Private execution uses `task_claimed`, `task_started`, `task_heartbeat`, `task_released`, `task_completed`, `task_failed`, `task_blocked`, `task_reopened`, and `task_override` events. Each event is hash-chained and includes actor/session identity, task id, timestamp, and a typed payload.

Completion events require:

- completion record path and SHA-256
- source Markdown SHA-256
- command summary path and SHA-256
- runner-backed command artifacts
- coverage of every relevant `Test Plan` and `Acceptance` item

## Preflight Gates

`harness/ledger_task.py preflight` combines structural audit, event validation, dependency checks, lease state, task blocking states, and record validation. A hard gate prevents task claiming until repaired.

Hard gates include source-boundary violations, plan-kernel status pollution, actionable unsupported claims, deferred-owner gaps, execution-flow pollution, missing hardening sections, event errors, invalid record, dependency violations, and invalid leases.

## Command Capture

Task commands must run through `harness/ledger_task.py run-command`. The command runner records argv, cwd, timestamps, exit code, stdout/stderr excerpts, output hashes, and a runner artifact hash. Completion cannot rely on handwritten command summaries.

Negative `rg` assertions must exit 0 on success, for example:

```bash
bash -lc '! rg "forbidden pattern" plans ledger harness'
```

## Public Snapshot Boundary

This repository keeps the planning and harness contracts public while excluding private record, private task-event history, command outputs, and session logs. Public task statuses are useful for context, but fresh private record is still required before making new completion claims.
