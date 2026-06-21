# Agent Orchestration Contract

## Agents

### Codex A

Approves ADRs and Epic Contracts, resolves cross-contract conflicts, reviews `epic base..epic head`, and produces Epic Review records. Codex A does not handle routine small-task repair.

### Codex B

Creates Atomic Task Packs from approved contracts, manages task worktrees, checks allowed paths, reruns commands, scans forbidden patterns, and produces Task Gate Results. Codex B does not modify architecture contracts or declare an Epic accepted.

### Flash

Executes only `issued` Atomic Task Packs with `execution_ready: true`. Flash must not modify plan, change acceptance, expand scope, add unapproved dependencies, or continue after a stop condition.

Flash eligibility is read from public projection fields `issuance_status` and `execution_ready`. The projection computes Task Pack SHA256 by normalizing `task_pack_sha256` to `null` before canonical JSON hashing. Canonical JSON sorts object keys but preserves array order, so command, acceptance, workflow, and stop-condition order is part of the task contract. Issued packs must declare that computed hash, while draft packs keep it `null`.

Codex A Epic approval records use the same canonical self-hash pattern: normalize `approval_record_sha256` to `null`, hash the normative record content, and require both the record and Epic Contract approval reference to match the computed value. Moving the approval file does not change the approval content hash.

Codex A Epic Reviews must review the final integrated Epic head. The review head must match workspace reconciliation `epic_head_commit`, and every required task Gate Result commit must be listed as integrated for that head. Blocking unresolved risks invalidate an accepted Epic Review.

## Atomic Task Boundaries

One task has one main goal, usually changes 1-5 main files, does not cross two domain Epics, includes a deterministic test or static check, and avoids incidental refactors.

Split warning is triggered around 300-500 added/modified code lines or one public interface change. New architecture decisions, new dependencies, allowed-path expansion, or contract/test conflict require stopping and escalation.
