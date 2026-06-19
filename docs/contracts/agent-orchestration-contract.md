# Agent Orchestration Contract

## Agents

### Codex A

Approves ADRs and Epic Contracts, resolves cross-contract conflicts, reviews `epic base..epic head`, and produces Epic Review records. Codex A does not handle routine small-task repair.

### Codex B

Creates Atomic Task Packs from approved contracts, manages task worktrees, checks allowed paths, reruns commands, scans forbidden patterns, and produces Task Gate Results. Codex B does not modify architecture contracts or declare an Epic accepted.

### Flash

Executes only `issued` Atomic Task Packs with `execution_ready: true`. Flash must not modify plan, change acceptance, expand scope, add unapproved dependencies, or continue after a stop condition.

## Atomic Task Boundaries

One task has one main goal, usually changes 1-5 main files, does not cross two domain Epics, includes a deterministic test or static check, and avoids incidental refactors.

Split warning is triggered around 300-500 added/modified code lines or one public interface change. New architecture decisions, new dependencies, allowed-path expansion, or contract/test conflict require stopping and escalation.
