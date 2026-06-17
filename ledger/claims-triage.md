# Claims Triage

Generated: 2026-06-17T16:22:54+00:00

This report classifies historical test/build/completion text. It does not upgrade any historical claim to verified record.

## Summary

- Total detected claims: 2
- Needs rerun: 0
- Unsupported without linked record: 0
- Not verification claims: 2
- Actionable claims: 0

## Status Counts

| Status | Count |
| --- | ---: |
| not-a-verification-claim | 2 |

## Bucket Counts

| Bucket | Count |
| --- | ---: |
| architecture-policy | 1 |
| source-boundary-policy | 1 |

## Highest-Action Documents

| File | Actionable | Needs rerun | Unsupported | Not verification | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md` | 0 | 0 | 0 | 1 | 1 |
| `plans/xq-integrated-rebuild/README.md` | 0 | 0 | 0 | 1 | 1 |

## High-Risk Test Count Claims

| Claim | File | Line | Status | Excerpt |
| --- | --- | ---: | --- | --- |
| - | - | - | - | No high-risk mechanical test-count claim currently detected in plan files. |

## Policy

- `needs-rerun` means the historical test/build statement must receive fresh command record before it can affect task state.
- `unsupported` means the claim should not drive automation until record is linked or the claim is explicitly downgraded.
- `not-a-verification-claim` means the scanner preserved the line but it is policy, heading, or deferred-scope text rather than proof.
