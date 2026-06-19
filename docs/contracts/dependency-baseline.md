# Dependency Baseline

## Purpose

Record proposed dependency expectations for the integrated rebuild without pretending they are an implementation lock.

## Proposed Baseline

The public proposal lives in `config/dependency-baseline.proposed.json`.

The real implementation lock must be created later in:

```text
IMPLEMENTATION_WORKSPACE/dependencies.lock.json
```

## Required Fields

Each proposed dependency records name, suggested version, official source, SHA-256, license, compiler/ABI, build options, public API rule, runtime packaging rule, role in XQ, and verification status.

## Rules

- Proposed baseline approval does not mean dependency build success.
- Implementation lock mismatch requires Codex A escalation.
- Dependency changes stale downstream task packs and gate results.
- Legacy `Externals` content is evidence only until a new lock is approved.
