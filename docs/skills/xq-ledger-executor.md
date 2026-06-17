# XQ Ledger Executor Workflow

Use this workflow when executing XQ integrated rebuild tasks with the ledger harness.

## Rules

- Do not resume from Markdown status text, historical summaries, checked boxes, or `tests passed` prose.
- Use the ledger snapshot and private event log as task state authority.
- Do not hand-edit generated task state, event history, leases, or record summaries.
- Do not mark a task complete without fresh runner-backed record.
- Do not complete a task unless the same actor/session owns its active lease.
- Do not use bare `rg` for no-match assertions; wrap it so the expected no-match result exits 0.

## Execution Loop

```bash
python3 harness/ledger_task.py preflight
python3 harness/ledger_task.py claim-next --actor codex --session-id <session-id>
python3 harness/ledger_task.py explain-next --task-id <task-id>
python3 harness/ledger_task.py run-command --task-id <task-id> --actor codex --session-id <session-id> --cwd <cwd> -- <command...>
```

After execution:

```bash
python3 harness/ledger_task.py record-complete --task-id <task-id> --actor codex --session-id <session-id> --evidence <evidence-json> --command-summary <command-summary-json>
```

On failure or unsafe scope:

```bash
python3 harness/ledger_task.py record-fail --task-id <task-id> --actor codex --session-id <session-id> --failure-type <type> --reason <text>
python3 harness/ledger_task.py record-block --task-id <task-id> --actor codex --session-id <session-id> --failure-type <type> --reason <text>
```

Valid failure types are `test-failed`, `build-failed`, `missing-dependency`, `plan-ambiguous`, `source-boundary-risk`, and `harness-error`.

## Public Snapshot Note

This public repository omits private raw record and task-event history. Use it as the clean workflow and plan contract. A private execution environment must provide source archives, acceptance data, event logs, and record artifacts before authoritative completion claims are made.
