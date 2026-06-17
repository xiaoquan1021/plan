# XQ Integrated Medical Imaging Platform Rebuild Plan

IMPORTANT SOURCE BOUNDARY:
- This document is an external analysis note.
- XQ record comes only from `<xq-source-archive>`, extracted as `<xq-source-extract>`.
- Do not use `<xq-implementation-workspace>` as record for this analysis; it is the active refactor workspace.
- SimVascular is used for functional, project-format, and algorithm-level reference, not for source-code migration.

## 1. Source Boundary

This plan is intentionally stored outside the active XQ workspace:

- Main plan: `plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md`
- Plan tree: `plans/xq-integrated-rebuild/`
- XQ audit source: `<xq-source-archive>`
- XQ extracted audit tree: `<xq-source-extract>`
- Default blank implementation root: `<xq-rebuild-workspace>`
- Active implementation workspace for the future: `<xq-implementation-workspace>`, only after explicit user decision and only as a blank rebuild target
- Required real-world acceptance project: `<acceptance-project>`

`<xq-implementation-workspace>` is not an record source for this analysis. It is only the future place where the accepted plan may be implemented. All plan documents must stay under `<public-or-private-plan-root>/` so the active refactor workspace does not absorb stale or partial planning notes.

All detailed child `.md` files for this rebuild must be stored in the dedicated folder tree:

```text
plans/xq-integrated-rebuild/
```

Do not create loose child plans beside the active XQ source tree.

## 2. Corrected Goal

The goal is no longer "make XQ as lightweight as possible." The goal is to rebuild XQ as an integrated medical imaging, vascular modeling, meshing, and simulation-preparation application.

The new XQ may use common medical imaging dependencies, but the architecture must remain integrated:

```text
XQApplication
  -> XQWorkbench
  -> XQProject
  -> XQScene
  -> XQWorkflow
  -> XQIO
  -> XQAlgorithms
  -> external kernels
```

The first implementation phase may contain incomplete code. It must start from `<xq-rebuild-workspace>` unless this plan is explicitly updated before source changes begin. It must build the structure from scratch and must not contain temporary architecture: no plugin workbench, no dual data model, no compatibility module that hides core requirements, and no fallback web of safety switches added only to make an early demo run.

## 3. Plan Tree

Detailed implementation planning is split by code layer and small feature. The main plan is only the index, dependency map, and repair routing table.

Start with the execution entry:

- [00-execution-entry.md](xq-integrated-rebuild/00-execution-entry.md)
- [xq-integrated-rebuild/README.md](xq-integrated-rebuild/README.md)

This index no longer stores authoritative runtime-position text. The authoritative task state, plan-position policy, audit counts, claims, and deferred boundaries live in:

- [audit ledger README](../ledger/README.md)
- [tasks.json](../ledger/snapshots/tasks.json)
- [source inventory](../ledger/source-inventory.md)

Do not resume implementation from historical batch summaries or test-count text. Pick repair or implementation work only from `ledger/snapshots/tasks.json` after ledger reconciliation.

Governance:

- [00-source-boundary-and-rules.md](xq-integrated-rebuild/00-governance/00-source-boundary-and-rules.md)
- [01-architecture-first-discipline.md](xq-integrated-rebuild/00-governance/01-architecture-first-discipline.md)
- [02-document-repair-policy.md](xq-integrated-rebuild/00-governance/02-document-repair-policy.md)
- [03-child-document-hardening-standard.md](xq-integrated-rebuild/00-governance/03-child-document-hardening-standard.md)

Foundation:

- [01-empty-project-skeleton.md](xq-integrated-rebuild/01-foundation/01-empty-project-skeleton.md)
- [02-top-level-cmake.md](xq-integrated-rebuild/01-foundation/02-top-level-cmake.md)
- [03-superbuild-version-lock.md](xq-integrated-rebuild/01-foundation/03-superbuild-version-lock.md)
- [04-dependency-role-map.md](xq-integrated-rebuild/01-foundation/04-dependency-role-map.md)

Core data:

- [01-xqproject-lifecycle.md](xq-integrated-rebuild/02-core-data/01-xqproject-lifecycle.md)
- [02-xqscene-ownership.md](xq-integrated-rebuild/02-core-data/02-xqscene-ownership.md)
- [03-xqdatanode-and-metadata.md](xq-integrated-rebuild/02-core-data/03-xqdatanode-and-metadata.md)
- [04-xqimagevolume.md](xq-integrated-rebuild/02-core-data/04-xqimagevolume.md)
- [05-xqpath.md](xq-integrated-rebuild/02-core-data/05-xqpath.md)
- [06-xqcontourgroup.md](xq-integrated-rebuild/02-core-data/06-xqcontourgroup.md)
- [07-xqsurfacemodel.md](xq-integrated-rebuild/02-core-data/07-xqsurfacemodel.md)
- [08-xqmesh.md](xq-integrated-rebuild/02-core-data/08-xqmesh.md)
- [09-xqsimulationcase.md](xq-integrated-rebuild/02-core-data/09-xqsimulationcase.md)

Native project IO:

- [01-open-project-directory.md](xq-integrated-rebuild/03-native-project-io/01-open-project-directory.md)
- [02-svproj-project-manifest.md](xq-integrated-rebuild/03-native-project-io/02-svproj-project-manifest.md)
- [03-pth-path-reader.md](xq-integrated-rebuild/03-native-project-io/03-pth-path-reader.md)
- [04-ctgr-contour-reader.md](xq-integrated-rebuild/03-native-project-io/04-ctgr-contour-reader.md)
- [05-mdl-vtp-model-reader.md](xq-integrated-rebuild/03-native-project-io/05-mdl-vtp-model-reader.md)
- [06-msh-vtu-mesh-reader.md](xq-integrated-rebuild/03-native-project-io/06-msh-vtu-mesh-reader.md)
- [07-sjb-simulation-reader.md](xq-integrated-rebuild/03-native-project-io/07-sjb-simulation-reader.md)
- [08-xq-native-save-format.md](xq-integrated-rebuild/03-native-project-io/08-xq-native-save-format.md)

Medical image IO:

- [01-dicom-series-scanner.md](xq-integrated-rebuild/04-medical-image-io/01-dicom-series-scanner.md)
- [02-dicom-pixel-decode.md](xq-integrated-rebuild/04-medical-image-io/02-dicom-pixel-decode.md)
- [03-dicom-private-tags.md](xq-integrated-rebuild/04-medical-image-io/03-dicom-private-tags.md)
- [04-nifti-reader.md](xq-integrated-rebuild/04-medical-image-io/04-nifti-reader.md)
- [05-nrrd-metaimage-reader.md](xq-integrated-rebuild/04-medical-image-io/05-nrrd-metaimage-reader.md)
- [06-vti-minc-tiff-reader.md](xq-integrated-rebuild/04-medical-image-io/06-vti-minc-tiff-reader.md)

Workbench and visualization:

- [01-main-window-layout.md](xq-integrated-rebuild/05-workbench-visualization/01-main-window-layout.md)
- [02-project-tree.md](xq-integrated-rebuild/05-workbench-visualization/02-project-tree.md)
- [03-mpr-viewers.md](xq-integrated-rebuild/05-workbench-visualization/03-mpr-viewers.md)
- [04-3d-scene-viewer.md](xq-integrated-rebuild/05-workbench-visualization/04-3d-scene-viewer.md)
- [05-tool-panels.md](xq-integrated-rebuild/05-workbench-visualization/05-tool-panels.md)
- [06-four-pane-layout.md](xq-integrated-rebuild/05-workbench-visualization/06-four-pane-layout.md)

Workflow:

- [01-workflow-state-machine.md](xq-integrated-rebuild/06-workflow/01-workflow-state-machine.md)
- [02-stage-source-relations.md](xq-integrated-rebuild/06-workflow/02-stage-source-relations.md)
- [03-command-and-undo.md](xq-integrated-rebuild/06-workflow/03-command-and-undo.md)

Domain features:

- [01-path-planning.md](xq-integrated-rebuild/07-domain-features/01-path-planning.md)
- [02-centerline-frames.md](xq-integrated-rebuild/07-domain-features/02-centerline-frames.md)
- [03-lumen-contour-editing.md](xq-integrated-rebuild/07-domain-features/03-lumen-contour-editing.md)
- [04-contour-lofting-inputs.md](xq-integrated-rebuild/07-domain-features/04-contour-lofting-inputs.md)
- [05-3d-segmentation.md](xq-integrated-rebuild/07-domain-features/05-3d-segmentation.md)
- [06-model-lofting-and-capping.md](xq-integrated-rebuild/07-domain-features/06-model-lofting-and-capping.md)
- [07-model-face-metadata.md](xq-integrated-rebuild/07-domain-features/07-model-face-metadata.md)
- [08-surface-mesh.md](xq-integrated-rebuild/07-domain-features/08-surface-mesh.md)
- [09-volume-mesh.md](xq-integrated-rebuild/07-domain-features/09-volume-mesh.md)
- [10-mesh-boundary-transfer.md](xq-integrated-rebuild/07-domain-features/10-mesh-boundary-transfer.md)
- [11-simulation-boundary-conditions.md](xq-integrated-rebuild/07-domain-features/11-simulation-boundary-conditions.md)
- [12-simulation-solver-export.md](xq-integrated-rebuild/07-domain-features/12-simulation-solver-export.md)
- [13-rom-and-multiphysics.md](xq-integrated-rebuild/07-domain-features/13-rom-and-multiphysics.md)

Code selection and acceptance:

- [01-code-selection-rules.md](xq-integrated-rebuild/08-xq-zip-selection/01-code-selection-rules.md)
- [02-code-rewrite-mapping.md](xq-integrated-rebuild/08-xq-zip-selection/02-code-rewrite-mapping.md)
- [01-0007-project-acceptance.md](xq-integrated-rebuild/09-acceptance-repair/01-0007-project-acceptance.md)
- [02-failure-routing.md](xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md)

## 4. How to Execute and Repair

Work on one child document at a time. Each child document owns exactly one layer or small feature. If an implementation step fails, update the owning child document first, then continue. Do not patch the main plan with feature-specific details.

Before source changes start for a layer or feature, harden the owning child document so it independently defines purpose, inputs, outputs, rules, exact files, interfaces, commands, tests, acceptance checks, and failure repair route. Document first-pass completion does not mean source code exists, builds, runs, or passes runtime acceptance.

The planning hardening order is governed by dependencies, not by forcing every early step to run:

1. Governance rules.
2. Project skeleton and dependency superbuild.
3. Core data model.
4. Native project and medical image IO.
5. Workbench and visualization.
6. Workflow state and source relations.
7. Domain features.
8. XQ zip code selection.
9. Acceptance and repair routing.

## 5. Development Discipline

- Architecture first, runtime later.
- Stage-level incomplete code is acceptable before v1.
- Do not add safety switches, fallback paths, mock business objects, or compatibility plugins only to make an early step run.
- Do not introduce MITK, BlueBerry, CTK, or a plugin workbench.
- Do not create dual ownership between an external library object graph and `XQScene`.
- Business code should use XQ-owned types. External dependencies are implementation kernels only.

## 6. Final Acceptance

The first full version is accepted when the integrated application can directly open `<acceptance-project>` and recover:

- image volume from `Images/OSMSC0090-cm.vti`
- paths from `Paths/*.pth`
- contour groups from `Segmentations/*.ctgr`
- model metadata and surface from `Models/*.mdl` and `Models/*.vtp`
- mesh metadata and grid data from `Meshes/*.msh`, `Meshes/*.vtu`, and `Meshes/*.vtp`
- simulation setup from `Simulations/*.sjb` and solver-preparation files

The acceptance target is an integrated XQ project and scene, not a chain of import adapters.
