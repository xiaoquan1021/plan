# XQ-zip-analysis Source Inventory

Generated: 2026-06-17T16:22:54+00:00

## Scope

Included:

- `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md`
- `plans/xq-integrated-rebuild/00-execution-entry.md`
- `plans/xq-integrated-rebuild/README.md`
- `plans/xq-integrated-rebuild/**/*.md` excluding generated `ledger`, `ledger/private-execution-records`, and `<private-evidence-dir>` directories.

Excluded:

- `<xq-implementation-workspace>`
- `<agent-session-log>`
- `<agent-session-state>`
- old Copilot, Codeium, Windsurf, and external dependency plan files.

## Counts

- Plan documents scanned: 60
- State-source lines: 6
- Test/build/completion claims: 2
- Deferred/not-complete lines: 42
- Execution-flow lines to migrate: 0
- Session red flags: 0

## State Mirrors

| Kind | Classification | Suggested action | File | Line | Excerpt |
| --- | --- | --- | --- | ---: | --- |
| current_cursor | diagnostic-command-reference | ignore-as-status-source | `plans/xq-integrated-rebuild/00-governance/02-document-repair-policy.md` | 47 | bash -lc '! rg -n "Current cursor|Next implementation document|Completed source batch" plans/xq-integrated-rebuild/00-execution-entry.md plans/xq-integrated-rebuild/README.md plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-ma... |
| next_implementation | diagnostic-command-reference | ignore-as-status-source | `plans/xq-integrated-rebuild/00-governance/02-document-repair-policy.md` | 47 | bash -lc '! rg -n "Current cursor|Next implementation document|Completed source batch" plans/xq-integrated-rebuild/00-execution-entry.md plans/xq-integrated-rebuild/README.md plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-ma... |
| completed_source_batch | diagnostic-command-reference | ignore-as-status-source | `plans/xq-integrated-rebuild/00-governance/02-document-repair-policy.md` | 47 | bash -lc '! rg -n "Current cursor|Next implementation document|Completed source batch" plans/xq-integrated-rebuild/00-execution-entry.md plans/xq-integrated-rebuild/README.md plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-ma... |
| current_cursor | diagnostic-command-reference | ignore-as-status-source | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 149 | rg -n "Current cursor|Next implementation document|Next planning-hardening document" \ |
| next_implementation | diagnostic-command-reference | ignore-as-status-source | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 149 | rg -n "Current cursor|Next implementation document|Next planning-hardening document" \ |
| next_hardening | diagnostic-command-reference | ignore-as-status-source | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 149 | rg -n "Current cursor|Next implementation document|Next planning-hardening document" \ |

## Required-Section Gaps

| File | Role | Missing required sections | Unchecked steps | Notes |
| --- | --- | --- | ---: | --- |

## Execution-Flow Content Still In Plan Docs

| File | Line | Suggested action | Excerpt |
| --- | ---: | --- | --- |

## Deferred Lines

Deferred items are preserved as scope boundaries and must not be swallowed by completed-source summaries.

| File | Line | Status | Bucket | Owner hint | Excerpt |
| --- | ---: | --- | --- | --- | --- |
| `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md` | 59 | not-a-deferred-boundary | ledger-pointer | main-plan-index | This index no longer stores authoritative runtime-position text. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in: |
| `plans/xq-integrated-rebuild/00-execution-entry.md` | 21 | not-a-deferred-boundary | ledger-pointer | execution-entry | Plan-position text is no longer stored in this entry document. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in: |
| `plans/xq-integrated-rebuild/03-native-project-io/08-xq-native-save-format.md` | 66 | registered-boundary | deferred-scope-boundary | native project IO | index/xq.sqlite is deferred until large-project indexing requires it |
| `plans/xq-integrated-rebuild/04-medical-image-io/02-dicom-pixel-decode.md` | 62 | not-a-deferred-boundary | ledger-pointer | medical image IO | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 69 | registered-boundary | deferred-scope-boundary | medical image IO | - Multi-page TIFF decoding, OME-TIFF, tiled TIFF, BigTIFF, JPEG/LZW/Deflate compression, color images, and vendor metadata semantics are deferred; multi-page inputs must be rejected in this document. |
| `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 70 | registered-boundary | deferred-scope-boundary | medical image IO | - MINC support is deferred until its dependency boundary is explicitly selected. |
| `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 327 | not-a-deferred-boundary | ledger-pointer | medical image IO | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/05-workbench-visualization/01-main-window-layout.md` | 214 | not-a-deferred-boundary | ledger-pointer | workbench visualization | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/05-workbench-visualization/02-project-tree.md` | 285 | not-a-deferred-boundary | ledger-pointer | workbench visualization | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/05-workbench-visualization/03-mpr-viewers.md` | 48 | registered-boundary | deferred-scope-boundary | workbench visualization | - First-pass XQ-owned path-normal and contour-edit plane state contracts, with deterministic path-normal oblique grayscale, path overlay, segmentation-mask overlay, contour overlay reslicing, and contour hit-test support plus contour-edi... |
| `plans/xq-integrated-rebuild/05-workbench-visualization/03-mpr-viewers.md` | 386 | not-a-deferred-boundary | ledger-pointer | workbench visualization | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/05-workbench-visualization/04-3d-scene-viewer.md` | 716 | not-a-deferred-boundary | ledger-pointer | workbench visualization | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/05-workbench-visualization/05-tool-panels.md` | 9 | registered-boundary | deferred-scope-boundary | workbench visualization | The four-pane widget can now feed active MPR world positions into this host through a non-owning pointer, including valid unmodified MPR child left mouse press and drag events, and can use endpoint contour hit-test point indexes plus edg... |
| `plans/xq-integrated-rebuild/05-workbench-visualization/05-tool-panels.md` | 206 | not-a-deferred-boundary | ledger-pointer | workbench visualization | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/05-workbench-visualization/06-four-pane-layout.md` | 301 | not-a-deferred-boundary | ledger-pointer | workbench visualization | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/06-workflow/03-command-and-undo.md` | 50 | not-a-deferred-boundary | ledger-pointer | workflow | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/01-path-planning.md` | 7 | registered-boundary | deferred-scope-boundary | domain features | This document creates the domain service contract only. Qt tool panels, mouse interactors, VTK mappers, and rendering are deferred until the owning workbench/visualization documents are ready for runtime UI code. |
| `plans/xq-integrated-rebuild/07-domain-features/01-path-planning.md` | 19 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/03-lumen-contour-editing.md` | 19 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/05-3d-segmentation.md` | 78 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/06-model-lofting-and-capping.md` | 70 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/07-model-face-metadata.md` | 139 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/08-surface-mesh.md` | 62 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/09-volume-mesh.md` | 73 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/10-mesh-boundary-transfer.md` | 173 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/11-simulation-boundary-conditions.md` | 77 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/12-simulation-solver-export.md` | 85 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/07-domain-features/13-rom-and-multiphysics.md` | 203 | not-a-deferred-boundary | ledger-pointer | domain features | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/08-xq-zip-selection/02-code-rewrite-mapping.md` | 51 | registered-boundary | deferred-register-row | zip source selection | | Python API and Python-node plugin behavior | Deferred; no current owner in the integrated initial contract | |
| `plans/xq-integrated-rebuild/09-acceptance-repair/01-0007-project-acceptance.md` | 209 | not-a-deferred-boundary | ledger-pointer | acceptance repair | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 7 | routing-policy | deferred-routing-policy | acceptance repair | After the 0007 acceptance implementation, this document also owns the routing of remaining deferred fidelity work back to the smallest implementation document. |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 25 | routing-policy | deferred-routing-policy | acceptance repair | - Deferred issue register in `00-execution-entry.md`. |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 31 | routing-policy | deferred-routing-policy | acceptance repair | - A post-acceptance deferred issue route table. |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 81 | section-marker | deferred-section-heading | acceptance repair | ## Post-Acceptance Deferred Issue Routing |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 83 | routing-policy | deferred-routing-policy | acceptance repair | Route the current known deferred work as follows: |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 85 | section-marker | deferred-route-table-header | acceptance repair | | Deferred issue | Primary owning document | Adjacent document only if contract changes | |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 120 | routing-policy | deferred-routing-policy | acceptance repair | post-acceptance deferred work ownership; it does not own runtime source files. |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 127 | routing-policy | deferred-routing-policy | acceptance repair | deferred fidelity work has a primary owner before implementation resumes |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 134 | not-a-deferred-boundary | checked-routing-or-plan-step | acceptance repair | - [x] Route current deferred issues to primary owning documents. |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 154 | not-a-deferred-boundary | diagnostic-command-reference | acceptance repair | rg -n "Post-Acceptance Deferred Issue Routing|01-foundation/03-superbuild-version-lock.md" \ |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 168 | routing-policy | deferred-routing-policy | acceptance repair | - Current deferred fidelity work has a primary owner before implementation resumes. |
| `plans/xq-integrated-rebuild/README.md` | 9 | not-a-deferred-boundary | ledger-pointer | readme-index | This README no longer mirrors authoritative runtime-position text. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in: |
