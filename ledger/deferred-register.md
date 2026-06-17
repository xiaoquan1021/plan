# Deferred Register

Generated: 2026-06-17T16:22:54+00:00

This register classifies lines that mention deferred scope so they cannot be lost inside completed-source summaries.

## Summary

- Total deferred-related lines: 42
- Registered boundaries: 7
- Section markers: 2
- Routing policy text: 7
- Not deferred boundaries: 26
- Needs owner confirmation: 0

## Status Counts

| Status | Count |
| --- | ---: |
| not-a-deferred-boundary | 26 |
| registered-boundary | 7 |
| routing-policy | 7 |
| section-marker | 2 |

## Bucket Counts

| Bucket | Count |
| --- | ---: |
| checked-routing-or-plan-step | 1 |
| deferred-register-row | 1 |
| deferred-route-table-header | 1 |
| deferred-routing-policy | 7 |
| deferred-scope-boundary | 6 |
| deferred-section-heading | 1 |
| diagnostic-command-reference | 1 |
| ledger-pointer | 24 |

## Owner Hints

| Owner | Count |
| --- | ---: |
| acceptance repair | 12 |
| domain features | 12 |
| execution-entry | 1 |
| main-plan-index | 1 |
| medical image IO | 4 |
| native project IO | 1 |
| readme-index | 1 |
| workbench visualization | 8 |
| workflow | 1 |
| zip source selection | 1 |

## Highest-Action Documents

| File | Deferred | Registered | Section markers | Routing policy | Not boundary | Needs owner |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 3 | 2 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/05-workbench-visualization/03-mpr-viewers.md` | 2 | 1 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/05-workbench-visualization/05-tool-panels.md` | 2 | 1 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/01-path-planning.md` | 2 | 1 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/03-native-project-io/08-xq-native-save-format.md` | 1 | 1 | 0 | 0 | 0 | 0 |
| `plans/xq-integrated-rebuild/08-xq-zip-selection/02-code-rewrite-mapping.md` | 1 | 1 | 0 | 0 | 0 | 0 |
| `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 11 | 0 | 2 | 7 | 2 | 0 |
| `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/00-execution-entry.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/04-medical-image-io/02-dicom-pixel-decode.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/05-workbench-visualization/01-main-window-layout.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/05-workbench-visualization/02-project-tree.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/05-workbench-visualization/04-3d-scene-viewer.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/05-workbench-visualization/06-four-pane-layout.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/06-workflow/03-command-and-undo.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/03-lumen-contour-editing.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/05-3d-segmentation.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/06-model-lofting-and-capping.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/07-model-face-metadata.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/08-surface-mesh.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/09-volume-mesh.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/10-mesh-boundary-transfer.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/11-simulation-boundary-conditions.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/12-simulation-solver-export.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/07-domain-features/13-rom-and-multiphysics.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/09-acceptance-repair/01-0007-project-acceptance.md` | 1 | 0 | 0 | 0 | 1 | 0 |
| `plans/xq-integrated-rebuild/README.md` | 1 | 0 | 0 | 0 | 1 | 0 |

## Registered Boundaries

| ID | Owner hint | File | Line | Bucket | Excerpt |
| --- | --- | --- | ---: | --- | --- |
| deferred-00003 | native project IO | `plans/xq-integrated-rebuild/03-native-project-io/08-xq-native-save-format.md` | 66 | deferred-scope-boundary | index/xq.sqlite is deferred until large-project indexing requires it |
| deferred-00005 | medical image IO | `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 69 | deferred-scope-boundary | - Multi-page TIFF decoding, OME-TIFF, tiled TIFF, BigTIFF, JPEG/LZW/Deflate compression, color images, and vendor metadata semantics are deferred; multi-page inputs must be rejected in this document. |
| deferred-00006 | medical image IO | `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 70 | deferred-scope-boundary | - MINC support is deferred until its dependency boundary is explicitly selected. |
| deferred-00010 | workbench visualization | `plans/xq-integrated-rebuild/05-workbench-visualization/03-mpr-viewers.md` | 48 | deferred-scope-boundary | - First-pass XQ-owned path-normal and contour-edit plane state contracts, with deterministic path-normal oblique grayscale, path overlay, segmentation-mask overlay, contour overlay reslicing, and contour hit-test support plus contour-edi... |
| deferred-00013 | workbench visualization | `plans/xq-integrated-rebuild/05-workbench-visualization/05-tool-panels.md` | 9 | deferred-scope-boundary | The four-pane widget can now feed active MPR world positions into this host through a non-owning pointer, including valid unmodified MPR child left mouse press and drag events, and can use endpoint contour hit-test point indexes plus edg... |
| deferred-00017 | domain features | `plans/xq-integrated-rebuild/07-domain-features/01-path-planning.md` | 7 | deferred-scope-boundary | This document creates the domain service contract only. Qt tool panels, mouse interactors, VTK mappers, and rendering are deferred until the owning workbench/visualization documents are ready for runtime UI code. |
| deferred-00029 | zip source selection | `plans/xq-integrated-rebuild/08-xq-zip-selection/02-code-rewrite-mapping.md` | 51 | deferred-register-row | | Python API and Python-node plugin behavior | Deferred; no current owner in the integrated initial contract | |

## Non-Boundary Deferred Mentions

| ID | Status | Bucket | File | Line | Excerpt |
| --- | --- | --- | --- | ---: | --- |
| deferred-00001 | not-a-deferred-boundary | ledger-pointer | `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md` | 59 | This index no longer stores authoritative runtime-position text. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in: |
| deferred-00002 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/00-execution-entry.md` | 21 | Plan-position text is no longer stored in this entry document. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in: |
| deferred-00004 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/04-medical-image-io/02-dicom-pixel-decode.md` | 62 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00007 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md` | 327 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00008 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/05-workbench-visualization/01-main-window-layout.md` | 214 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00009 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/05-workbench-visualization/02-project-tree.md` | 285 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00011 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/05-workbench-visualization/03-mpr-viewers.md` | 386 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00012 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/05-workbench-visualization/04-3d-scene-viewer.md` | 716 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00014 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/05-workbench-visualization/05-tool-panels.md` | 206 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00015 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/05-workbench-visualization/06-four-pane-layout.md` | 301 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00016 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/06-workflow/03-command-and-undo.md` | 50 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00018 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/01-path-planning.md` | 19 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00019 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/03-lumen-contour-editing.md` | 19 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00020 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/05-3d-segmentation.md` | 78 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00021 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/06-model-lofting-and-capping.md` | 70 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00022 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/07-model-face-metadata.md` | 139 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00023 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/08-surface-mesh.md` | 62 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00024 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/09-volume-mesh.md` | 73 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00025 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/10-mesh-boundary-transfer.md` | 173 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00026 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/11-simulation-boundary-conditions.md` | 77 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00027 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/12-simulation-solver-export.md` | 85 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00028 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/07-domain-features/13-rom-and-multiphysics.md` | 203 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00030 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/09-acceptance-repair/01-0007-project-acceptance.md` | 209 | Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record. |
| deferred-00031 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 7 | After the 0007 acceptance implementation, this document also owns the routing of remaining deferred fidelity work back to the smallest implementation document. |
| deferred-00032 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 25 | - Deferred issue register in `00-execution-entry.md`. |
| deferred-00033 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 31 | - A post-acceptance deferred issue route table. |
| deferred-00034 | section-marker | deferred-section-heading | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 81 | ## Post-Acceptance Deferred Issue Routing |
| deferred-00035 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 83 | Route the current known deferred work as follows: |
| deferred-00036 | section-marker | deferred-route-table-header | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 85 | | Deferred issue | Primary owning document | Adjacent document only if contract changes | |
| deferred-00037 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 120 | post-acceptance deferred work ownership; it does not own runtime source files. |
| deferred-00038 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 127 | deferred fidelity work has a primary owner before implementation resumes |
| deferred-00039 | not-a-deferred-boundary | checked-routing-or-plan-step | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 134 | - [x] Route current deferred issues to primary owning documents. |
| deferred-00040 | not-a-deferred-boundary | diagnostic-command-reference | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 154 | rg -n "Post-Acceptance Deferred Issue Routing|01-foundation/03-superbuild-version-lock.md" \ |
| deferred-00041 | routing-policy | deferred-routing-policy | `plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md` | 168 | - Current deferred fidelity work has a primary owner before implementation resumes. |
| deferred-00042 | not-a-deferred-boundary | ledger-pointer | `plans/xq-integrated-rebuild/README.md` | 9 | This README no longer mirrors authoritative runtime-position text. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in: |

## Policy

- `registered-boundary` means the line describes scope that still must remain visible in the ledger.
- `section-marker` means the line is structural text, not a standalone deferred work item.
- `routing-policy` means the line describes how deferred work should be routed, not the deferred work itself.
- `not-a-deferred-boundary` means the line mentions deferred wording but belongs with another ledger stream.
