# Execution-Flow Register

Generated: 2026-06-17T16:22:54+00:00

This register tracks historical execution narrative that still lives in plan documents. It is not fresh record and must not drive task state directly.

## Summary

- Execution-flow lines: 0
- Documents with execution-flow lines: 0

## Status Counts

| Status | Count |
| --- | ---: |

## Bucket Counts

| Bucket | Count |
| --- | ---: |

## Highest-Flow Documents

| File | Flow lines | Commands | Results | Behavior | Headings | Source-pass labels | Source-pass narrative |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

## Flow Items

| ID | Bucket | File | Line | Excerpt |
| --- | --- | --- | ---: | --- |

## Policy

- `verified-command-block` and `verified-result-block` are historical records; claims inside them remain unverified until linked record exists.
- `current-behavior-block` and source-pass narrative should be moved out of executable plan kernels or rewritten as future-facing contracts.
- Source Markdown should eventually link to `<private-execution-records>/by-document/` instead of embedding long session history.
