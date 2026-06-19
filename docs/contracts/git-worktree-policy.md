# Git Worktree Policy

## Codex A

Approves epic base and reviews complete `epic base..epic head` diffs. Codex A does not perform task-worktree repair.

## Codex B

Creates task worktrees from accepted epic HEAD, records base commit, gates results, and integrates accepted task commits into the epic branch. Codex B does not push unless explicitly authorized.

## Flash

Works only in the assigned task worktree. Flash must not switch branches, merge, rebase, push, operate on plan, modify other worktrees, or change task base.

## Default Rules

- One Atomic Task corresponds to one result commit.
- Start and end worktrees must be clean.
- Result commit must descend from base commit.
- Merge commits are forbidden by default.
- Uncommitted changes must not pass to the next task.
- Base commit changes require task reissue.
- Failed gates isolate or discard the task worktree.
