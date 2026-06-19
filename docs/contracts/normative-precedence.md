# Normative Precedence

## Purpose

Define which XQ plan source wins when contracts, task packs, historical documents, reports, or chat summaries disagree.

## Precedence Order

1. Approved ADRs.
2. Product Scope and Final Acceptance Contract.
3. Target Architecture and Core Data Semantics.
4. Dependency, Project Format, Fixture, and Privacy Contracts.
5. Approved Epic Contract.
6. Atomic Task Pack.
7. Current active child plan.
8. Superseded or archived historical documents.
9. Informal reports, chat records, and historical summaries.

## Rules

- Lower-precedence documents must not override higher-precedence contracts.
- When an agent finds a conflict, it must stop and escalate to Codex A.
- Codex B and Flash must not choose the convenient interpretation.
- Contract changes must increment `contract_version` and trigger stale checks for downstream task packs, gate results, and epic reviews.
- `deep-research-report.md` is reference evidence only.
- Legacy XQ evidence describes historical behavior; it does not define new XQ architecture ownership.
