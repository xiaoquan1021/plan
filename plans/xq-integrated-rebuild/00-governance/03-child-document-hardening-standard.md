# Child Document Hardening Standard

## Purpose

Define the minimum detail required before a child document can guide source changes for its layer or small feature.

## Owns

Planning workflow only. This document owns the checklist that decides whether a
child document is ready for source changes; it does not own runtime source
files.

## Test Plan

Document consistency checks:

```text
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

executable child/support/governance documents missing canonical sections are listed in ledger/snapshots/tasks.json
main-plan, README, and execution-entry remain not-executable indexes rather than fake implementation tasks

## Inputs

- Source boundary and rules.
- Architecture first discipline.
- Document repair policy.
- The current child document being hardened.

## Outputs

- A repeatable hardening checklist for each child document.
- A clear distinction between first-pass planning and source-change readiness.

## Rules

- First-pass structure is not enough for source changes.
- Each child document must define one owner, one responsibility, and one repair route.
- Each child document must state exact files, interfaces, commands, tests, and acceptance checks before source changes start for that area.
- Broad phrases such as "add tests" or "implement reader" must be replaced with concrete test names, commands, and expected results during hardening.
- If source behavior is selected from `<xq-source-extract>`, the child document must include an `XQ-main.zip Evidence` section.
- Do not move feature-specific detail into the main plan.

## Required Sections

Each source-change child document must contain:

```text
Purpose
Owns or Code Ownership
Inputs
Outputs
Rules
Implementation Contract
Step Plan
Test Plan
Acceptance
Failure Repair
```

Optional sections are allowed when useful:

```text
Data Contract
Read Contract
Write Contract
XQ-main.zip Evidence
Dependency Notes
Open Risks
```

## Implementation Contract

The implementation contract must define:

```text
future source files
future test files
public classes or functions
owned data types
external dependency boundary
forbidden dependency or ownership shortcuts
```

## Test Plan Standard

The test plan must define:

```text
test target name
test file path
required fixture data
command to run the test
expected pass condition
minimum negative case
```

If runtime tests cannot exist yet, the document must state the first source milestone that makes the test possible.

## XQ-main.zip Evidence Template

Use this template when old XQ behavior is studied:

```text
Evidence source root: <xq-source-extract>
Files studied:
- path/to/file
Behavior kept:
- concrete behavior or data field
Behavior rejected:
- old framework or dependency behavior
Rewrite owner:
- new XQ source owner
Verification:
- test or acceptance check proving the rewritten behavior
```

## Step Plan

- [ ] Add missing required sections to the child document.
- [ ] Replace vague steps with concrete files, interfaces, commands, tests, and expected results.
- [ ] Add `XQ-main.zip Evidence` when old XQ behavior is used.
- [ ] Add a negative case to the test plan.
- [ ] Confirm the child document does not require MITK, BlueBerry, CTK, SWIG, plugin workbench, or a compatibility shell.
- [ ] Confirm the child document routes failures to the smallest owning document.

## Acceptance

- A child document that passes this standard can be used for source changes without returning to the main plan for missing decisions.
- The child document states what to create, what to test, and how to know the result is correct.
- The child document preserves the integrated XQ architecture and source boundary.

## Failure Repair

If source changes reveal missing decisions, repair the owning child document first, then resume from that document.
