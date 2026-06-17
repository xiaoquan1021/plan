# Failure Routing

## Purpose

Define how to repair the plan and implementation when a feature fails, without letting fixes spread across unrelated layers.

After the 0007 acceptance implementation, this document also owns the routing of remaining deferred fidelity work back to the smallest implementation document.

## Owns

Planning files only:

```text
plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md
plans/xq-integrated-rebuild/00-execution-entry.md
plans/xq-integrated-rebuild/README.md
plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md
```

## Inputs

- All child plan documents.
- Acceptance project.
- Verification failures during implementation.
- Deferred issue register in `00-execution-entry.md`.
- Current 0007 acceptance result.

## Outputs

- A routing table from failure type to owning `.md`.
- A post-acceptance deferred issue route table.
- A next execution cursor when no immediate acceptance failure remains.

## Historical 0007 Result

The historical 0007 acceptance result was moved to
`<private-execution-records>/by-document/archived-flow-blocks/plan-system-repair-2026-06-16-historical-verification-claims.md`.
It is not fresh record. Re-run acceptance and store the new command output
under `<private-evidence-dir>/` before using it to change `ledger/snapshots/tasks.json`.

## Rules

- Route to the smallest owning document first.
- Do not repair acceptance failures by adding compatibility shells.
- Do not hide architecture failures behind runtime switches.
- If one failure maps to multiple documents, update the upstream data contract first, then the downstream consumer.
- If the failure is a missing dependency or controlled-prefix issue, repair `01-foundation/03-superbuild-version-lock.md` or `01-foundation/04-dependency-role-map.md` before changing feature code.
- If the failure is missing generated payload persistence, repair the native save-format owner before changing acceptance tests.
- If the failure is missing rendered UI behavior, repair the foundation dependency owner before adding Qt or VTK widget code.
- If the 0007 command-line path regresses to zero scene nodes, repair `09-acceptance-repair/01-0007-project-acceptance.md` plus the smallest failing reader or payload document.
- Do not use `<xq-implementation-workspace>` as record while routing a failure.

## General Failure Routing Table

| Failure | Owning document |
| --- | --- |
| Wrong record source used | `00-governance/00-source-boundary-and-rules.md` |
| New project starts from old plugin layout | `01-foundation/01-empty-project-skeleton.md` |
| Unwanted dependency added | `01-foundation/04-dependency-role-map.md` |
| Project object lifecycle unclear | `02-core-data/01-xqproject-lifecycle.md` |
| Scene data has two owners | `02-core-data/02-xqscene-ownership.md` |
| Node metadata cannot preserve file attributes | `02-core-data/03-xqdatanode-and-metadata.md` |
| VTI or DICOM volume cannot become XQ image | `02-core-data/04-xqimagevolume.md` and the relevant `04-medical-image-io` document |
| `.svproj` directory does not open | `03-native-project-io/01-open-project-directory.md` |
| `.pth` load fails | `03-native-project-io/03-pth-path-reader.md` |
| `.ctgr` load fails | `03-native-project-io/04-ctgr-contour-reader.md` |
| `.mdl/.vtp` model load fails | `03-native-project-io/05-mdl-vtp-model-reader.md` |
| `.msh/.vtu/.vtp` mesh load fails | `03-native-project-io/06-msh-vtu-mesh-reader.md` |
| `.sjb` simulation load fails | `03-native-project-io/07-sjb-simulation-reader.md` |
| DICOM series grouping fails | `04-medical-image-io/01-dicom-series-scanner.md` |
| DICOM pixel decode fails | `04-medical-image-io/02-dicom-pixel-decode.md` |
| Vendor private DICOM variant fails | `04-medical-image-io/03-dicom-private-tags.md` |
| Workbench starts becoming plugin-based | `05-workbench-visualization/01-main-window-layout.md` |
| Tool state bypasses workflow | `06-workflow/01-workflow-state-machine.md` |
| Downstream stale state is unclear | `06-workflow/02-stage-source-relations.md` |
| User edit cannot undo | `06-workflow/03-command-and-undo.md` |
| Path, contour, model, mesh, or simulation behavior fails | The matching `07-domain-features` document |
| Old XQ code copied with framework dependencies | `08-xq-zip-selection/01-code-selection-rules.md` |
| Acceptance project cannot fully load | `09-acceptance-repair/01-0007-project-acceptance.md` plus the smallest failing feature document |

## Post-Acceptance Deferred Issue Routing

Route the current known deferred work as follows:

| Deferred issue | Primary owning document | Adjacent document only if contract changes |
| --- | --- | --- |
| Qt6, VTK, ITK, OpenCASCADE, MMG, codec, SQLite, Eigen, or tinyxml2 controlled-prefix gaps | `01-foundation/03-superbuild-version-lock.md` | `01-foundation/04-dependency-role-map.md` |
| Dependency role or business-layer exposure conflict | `01-foundation/04-dependency-role-map.md` | exact feature document that exposed the dependency |
| Additional VTI raw appended/non-zlib variants or VTK image-reader integration | `04-medical-image-io/06-vti-minc-tiff-reader.md` | `02-core-data/04-xqimagevolume.md` |
| Compressed DICOM transfer syntax support | `04-medical-image-io/02-dicom-pixel-decode.md` | `01-foundation/03-superbuild-version-lock.md` |
| Vendor private DICOM semantic interpretation | `04-medical-image-io/03-dicom-private-tags.md` | `04-medical-image-io/01-dicom-series-scanner.md` |
| NIfTI-2, 4D, vector images, or compressed NIfTI variants beyond the current `.nii.gz` path | `04-medical-image-io/04-nifti-reader.md` | `02-core-data/04-xqimagevolume.md` |
| NRRD/MetaImage bzip2, ASCII, non-3D, vector/RGB, or byte-order variants beyond the current raw/gzip path | `04-medical-image-io/05-nrrd-metaimage-reader.md` | `02-core-data/04-xqimagevolume.md` |
| MINC reader or expanded TIFF/OME-TIFF support | `04-medical-image-io/06-vti-minc-tiff-reader.md` | `01-foundation/03-superbuild-version-lock.md` |
| Unified image reader dispatch for project directory imports | `04-medical-image-io/06-vti-minc-tiff-reader.md` | `03-native-project-io/01-open-project-directory.md` |
| Qt/VTK rendered MPR widgets | `05-workbench-visualization/03-mpr-viewers.md` | `01-foundation/03-superbuild-version-lock.md` |
| Qt/VTK rendered 3D scene widgets | `05-workbench-visualization/04-3d-scene-viewer.md` | `01-foundation/03-superbuild-version-lock.md` |
| Four-pane runtime widget composition | `05-workbench-visualization/06-four-pane-layout.md` | `05-workbench-visualization/01-main-window-layout.md` |
| Segmentation mask native persistence | `03-native-project-io/08-xq-native-save-format.md` | `07-domain-features/05-3d-segmentation.md` |
| Qt/VTK rendered segmentation mask overlay compositing or persisted extracted model output | `07-domain-features/05-3d-segmentation.md` | `05-workbench-visualization/03-mpr-viewers.md` / `05-workbench-visualization/04-3d-scene-viewer.md` |
| Generated model full geometry persistence | `03-native-project-io/08-xq-native-save-format.md` | `03-native-project-io/05-mdl-vtp-model-reader.md` |
| Generated surface mesh full geometry persistence | `03-native-project-io/08-xq-native-save-format.md` | `03-native-project-io/06-msh-vtu-mesh-reader.md` |
| Relation-aware stale propagation or undo restoration is insufficient | `06-workflow/02-stage-source-relations.md` | `06-workflow/03-command-and-undo.md` |
| Volume meshing needs a stronger tetrahedral kernel decision | `07-domain-features/09-volume-mesh.md` | `01-foundation/03-superbuild-version-lock.md` |
| Full svSolver-compatible `geombc.dat.1`, `bct.dat`, VTU/VTP arrays, partitions, or restart files | `07-domain-features/12-simulation-solver-export.md` | `03-native-project-io/06-msh-vtu-mesh-reader.md` |
| External solver execution path | `07-domain-features/12-simulation-solver-export.md` | `01-foundation/04-dependency-role-map.md` |
| ROM network generation or 1D solver export | `07-domain-features/13-rom-and-multiphysics.md` | `07-domain-features/12-simulation-solver-export.md` |
| Multiphysics solver-specific export or execution | `07-domain-features/13-rom-and-multiphysics.md` | `07-domain-features/12-simulation-solver-export.md` |

## Repair Rules

- Repair the smallest owning document first.
- Update directly affected upstream or downstream documents only when their contracts change.
- Do not patch the main plan with feature-specific code instructions.
- Do not add runtime switches or temporary architecture to hide a contract failure.

## Implementation Contract

Planning contract only. This document owns failure-to-document routing and
post-acceptance deferred work ownership; it does not own runtime source files.

Required invariants:

```text
failure repair starts from the smallest owning document
compatibility shells and runtime switches are not acceptable acceptance repairs
deferred fidelity work has a primary owner before implementation resumes
historical acceptance results are execution records, not fresh evidence
```

## Step Plan

- [x] Record the current 0007 acceptance result.
- [x] Route current deferred issues to primary owning documents.
- [x] Select the next execution cursor after acceptance repair, the VTK actor/renderer passes, the minimal Qt/VTK 3D widget pass, unified project image dispatch, and native decoded-image persistence.
- [ ] For each future failure, record the exact failing file, feature, or workflow stage.
- [ ] For each future failure, select the owning document from the routing table.
- [ ] Amend the owning document with the corrected contract.
- [ ] Update only adjacent contract documents when needed.
- [ ] Resume implementation from the corrected document.

## Test Plan

No source test is required for this document-only routing update.

Document consistency checks:

```text
rg -n "Current cursor|Next implementation document|Next planning-hardening document" \
  plans/xq-integrated-rebuild/00-execution-entry.md \
  plans/xq-integrated-rebuild/README.md \
  plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md

rg -n "Post-Acceptance Deferred Issue Routing|01-foundation/03-superbuild-version-lock.md" \
  plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md
```

Expected result:

the post-acceptance routing pass recorded 04-medical-image-io/06-vti-minc-tiff-reader.md as the then-current image-fidelity owner
the failure routing document contains the post-acceptance routing table

## Acceptance

- Failures have one primary owner.
- Fixes remain localized.
- The plan tree stays navigable as implementation grows.
- Current deferred fidelity work has a primary owner before implementation resumes.
- The post-acceptance repair route can hand off to `04-medical-image-io/06-vti-minc-tiff-reader.md` when additional VTI/MINC/TIFF coverage is again the smallest remaining owner after project image dispatch, native decoded-image persistence, NIfTI `.nii.gz` decode, and NRRD/MetaImage raw/gzip payload coverage.

## Failure Repair

If failure routing itself becomes ambiguous, add a more specific row to the routing table before changing feature documents.
