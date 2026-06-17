# XQ-zip-analysis Audit Ledger

Generated: 2026-06-17T16:22:54+00:00

This directory is the current audit ledger for `XQ-zip-analysis`. It exists to stop future work from resuming directly out of long, mirrored Markdown status text.

## Ground Rules

- Scope is only `<public-or-private-plan-root>` plan state, plus the archived `<private-session-id>` session for forensic indexing.
- Do not treat historical `tests passed`, `full suite passed`, or `x/y` text as true until a fresh record file is linked.
- Do not continue implementation from old Markdown cursor text; choose work from the derived `ledger/snapshots/tasks.json` snapshot after reconciliation.
- Do not edit source code as part of this audit pass.

## Generated Files

- `audit-summary.json`: compact machine summary.
- `task-events.jsonl`: append-only historical truth source for task events.
- `tasks.json`: derived task-selection snapshot and plan position during repair.
- `claims.jsonl`: every detected test/build/completion claim with triage status.
- `claim-triage.json` and `claims-triage.md`: grouped claim repair queues.
- `deferred-items.jsonl`: deferred or not-complete boundaries with triage status.
- `deferred-register.json` and `deferred-register.md`: grouped deferred repair queues and owner hints.
- `execution-flow-items.jsonl`: plan lines that look like session流水账 and should move into execution records.
- `execution-flow-register.json` and `execution-flow-register.md`: grouped execution-flow cleanup queues.
- `plan-docs.json`: structural inventory of scanned plan documents.
- `source-inventory.md`: human-readable source inventory and state mirror list.
- `repair-backlog.md`: prioritized cleanup queue.
- `../ledger/private-execution-records/by-document/index.json`: per-document counters for claims/deferred/flow/status risk.
- `../ledger/private-execution-records/sessions/<private-session-id>/session-index.json`: structured session index.

## Current Counts

- Plan documents scanned: 60
- Scope violations: 0
- Active plan-kernel violations: 0
- Active execution-record sections: 0
- Active execution-record pointers: 0
- Active deferred detail blocks: 0
- Active status-language lines: 0
- Active historical-record lines: 0
- True Markdown status-source lines: 0
- Diagnostic command references containing status keywords: 6
- Test/build/completion claims detected: 2
- Claim triage actionable items: 0
- Claim triage needs rerun: 0
- Claim triage unsupported: 0
- Claim triage not verification text: 2
- Deferred/not-complete lines: 42
- Deferred register registered boundaries: 7
- Deferred register needs owner confirmation: 0
- Execution-flow lines to migrate: 0
- Execution-flow documents with generated records: 0
- Documents missing canonical sections: 0
- Task event errors: 0
- Missing record links: 0
- Invalid record files: 0
- Stale completed tasks: 0
- Active task leases: 0
- Expired task leases: 0
- Blocked tasks: 0
- Dependency violations: 0
- Override events: 0
- private session red flags: 0
- private session test/build commands captured: 0

## Next Repair Order

1. Only after the gates above, select the next implementation task from the derived `tasks.json` snapshot.
