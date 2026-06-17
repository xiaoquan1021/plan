# XQ Zip Code Selection Rules

## Purpose

Define how future implementation may inspect `<xq-source-archive>` and select useful code without copying the old architecture.

## Owns

Future execution practice, not runtime source files.

## Inputs

- Source boundary rules.
- Empty project skeleton.
- Existing extracted audit tree: `<xq-source-extract>`.

## Outputs

- A disciplined rule set for using old XQ code as record and selective implementation material.

## Rules

- XQ record comes only from `<xq-source-archive>`, extracted as `<xq-source-extract>`.
- `<xq-implementation-workspace>` is not an record source.
- Old code may inform behavior, data fields, UI expectations, and algorithm steps.
- Old framework glue, plugin services, MITK data ownership, BlueBerry, CTK, and SWIG code must not be copied.
- Chosen code is rewritten into the new integrated folder structure.

## Selection Categories

Allowed to study:

```text
file format field mappings
algorithm parameter names
tool workflow order
domain math
VTK geometry operations
project data naming conventions
```

Not allowed to migrate:

```text
plugin activators
workbench extension declarations
MITK DataStorage usage
BlueBerry views and perspectives
CTK service registration
SWIG wrappers
external dependency installer assumptions
```

## Current Evidence Inventory

Evidence source root:

```text
<xq-source-extract>
```

Current first inventory from the extracted zip:

| Old XQ area | Selection posture | Owning rewrite area |
| --- | --- | --- |
| `Code/Source/Application` | Reject old BlueBerry/MITK-style startup and safety wrappers; study only command-line or startup intent if a future entrypoint needs it | `src/app`, `05-workbench-visualization/01-main-window-layout.md` |
| `Code/Source/xq4gui/Modules/Common` | Study math, spline, XML, string, and VTK helper behavior; reject MITK/DataStorage convenience flows | `src/domain`, `src/io/project`, `src/visualization` |
| `Code/Source/xq4gui/Modules/ProjectManagement` | Study project folder naming, metadata fields, and legacy reader/writer behavior; reject repository-folder object graph and old node-operation entrypoints | `src/io/project`, `src/core` |
| `Code/Source/xq4gui/Modules/Path` | Study centerline/path math, IO fields, tracer parameters, and workflow order; reject interactors/object factories | `src/domain/path`, `src/io/project`, workbench path panels |
| `Code/Source/xq4gui/Modules/Segmentation` | Study contour/profile/segmentation data fields, lofting inputs, and threshold behavior; reject MITK interactors, operations, mappers, and object factories | `src/domain/contour`, `src/domain/segmentation`, `src/visualization` |
| `Code/Source/xq4gui/Modules/Model` | Study geometry, face metadata, quality checks, and VTK/OCCT algorithm intent; reject MITK data interactors/object factories and unselected OCCT public ownership | `src/domain/modeling`, `src/io/project`, `src/visualization` |
| `Code/Source/xq4gui/Modules/Mesh` | Study grid, boundary, quality, and TetGen/MMG-style parameter intent; reject MITK grid wrappers and mapper/object-factory entrypoints | `src/domain/meshing`, `src/io/project`, `src/visualization` |
| `Code/Source/xq4gui/Modules/Simulation` | Study simulation job fields, boundary condition names, and solver-export intent | `src/domain/simulation`, `src/io/project`, solver export writers |
| `Code/Source/xq4gui/Modules/ROMSimulation` | Study ROM job field names only; reject MITK job wrappers | `07-domain-features/13-rom-and-multiphysics.md` |
| `Code/Source/xq4gui/Modules/MultiPhysics` | Study typed multiphysics equation/domain/settings fields; reject MITK job wrappers | `07-domain-features/13-rom-and-multiphysics.md` |
| `Code/Source/xq4gui/Modules/ImageProcessing` | Study image preprocessing parameter names only when an owning image or segmentation feature asks for them | `04-medical-image-io`, `07-domain-features/05-3d-segmentation.md` |
| `Code/Source/xq4gui/Modules/PythonApi` and `Plugins/org.xq.data.pythonnodes` | Reject for current integrated rebuild; Python/SWIG-style extension surface is not a source-pass dependency | Future explicit scripting document only |
| `Code/Source/xq4gui/Plugins/*` | Study UI workflow labels, action order, panel fields, icons, and resource naming only; reject plugin activators, `plugin.xml`, extension declarations, perspectives, service registration, and old view classes as owners | `src/workbench`, `src/workflow`, feature-specific domain owners |
| `Code/Testing` and `docs` | Study expected behavior, pipeline order, naming guards, and acceptance clues; do not treat docs as source implementation | Owning feature tests and acceptance documents |
| `Code/CMake`, root `build-xq.sh`, `run-xq.sh` | Reject as build-system migration input unless a foundation dependency document explicitly asks to study them | `01-foundation` only |

## Current Hardening Pass

Verified source-boundary facts:

```text
<xq-source-archive> exists
<xq-source-extract> is the extracted record tree symlinked to /tmp/xq-main-zip-extract/XQ-main
<xq-implementation-workspace> is not used as evidence
```

Commands used for the first inventory:

```text
ls -la <xq-source-extract>/
find -L <xq-source-extract>/Code/Source -maxdepth 5 -type d | sort
rg --files <xq-source-extract>/Code/Source
rg --files <xq-source-extract>/docs
```

First applied feature record record:

| Feature document | Old XQ files studied | Rewrite result |
| --- | --- | --- |
| `05-workbench-visualization/02-project-tree.md` | `org.xq.core.datamanager` DataExplorer view/plugin files and `org.xq.data.projectnodes` node-init placeholder | Kept Qt tree-model and visibility check-state behavior; rejected QmitkDataStorageTreeModel, MITK DataStorage ownership, BlueBerry plugin registration, and plugin view ownership; rewrote as `XQProjectTreeQtModel` over XQ-owned scene-backed `XQProjectTreeModel` |
| `05-workbench-visualization/02-project-tree.md` | `org.xq.core.datamanager` DataExplorer `QTreeView` setup and `selectionModel()` wiring | Kept concrete `QTreeView` composition and Qt selection-model tracking; rejected QmitkDataStorageTreeModel payload access, context-menu/plugin actions, rendering-manager refresh hooks, and BlueBerry view ownership; rewrote as `XQProjectTreeViewWidget` that emits optional `XQNodeId` values |
| `05-workbench-visualization/02-project-tree.md` | `org.xq.core.datamanager` DataExplorer rename action intent | Kept selected-node rename as an undoable project command; rejected direct MITK DataNode pointer mutation, plugin context-menu ownership, and old view-owned dialogs as command owners; rewrote as `XQProjectTreeViewWidget::renameSelectedNode` executing `RenameNodeCommand` through `XQCommandStack` |

## Evidence Record Template

Each feature document that studies old XQ code must add:

```text
XQ-main.zip Evidence
Evidence source root: <xq-source-extract>
Files studied:
- exact relative path
Behavior kept:
- concrete behavior, field, parameter, or workflow step
Behavior rejected:
- framework glue, plugin service, dependency ownership, or old entrypoint
Rewrite owner:
- new XQ source owner
Verification:
- test or acceptance check proving the rewritten behavior
```

## Implementation Contract

Planning contract only. This document governs how old XQ code may be studied
and recorded; it does not authorize copying old framework architecture.

Required invariants:

```text
old XQ source is record, not an owner
selected behavior is rewritten into an integrated XQ owner
feature documents record files studied, behavior kept, behavior rejected, rewrite owner, and verification plan
MITK/DataStorage/BlueBerry/CTK/SWIG/plugin glue is rejected unless a future document explicitly owns a new boundary
```

## Test Plan

Document consistency checks:

```text
rg -n "XQ-main.zip Evidence|Evidence source root|Behavior kept|Behavior rejected|Rewrite owner|Verification" plans/xq-integrated-rebuild
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

feature documents that use old XQ behavior contain an record record before source work resumes
historical verification claims remain non-authoritative until linked under _evidence

## Step Plan

- [x] Confirm `<xq-source-archive>` and `<xq-source-extract>` as the only XQ record boundary.
- [x] Inventory top-level old XQ code areas and classify study/reject posture.
- [x] Define the required per-feature `XQ-main.zip Evidence` record.
- [x] Apply the evidence-record rule to the project-tree Qt adapter contract.
- [x] Apply the evidence-record rule to the project-tree QTreeView widget contract.
- [x] Apply the evidence-record rule to the project-tree rename command-integration contract.
- [ ] For each future feature document that studies old XQ code, identify whether old XQ code has useful behavior.
- [ ] Record selected source files in the feature implementation notes before rewriting.
- [ ] Add an `XQ-main.zip Evidence` section to the owning feature document.
- [ ] Rewrite into XQ-owned APIs and payloads.
- [ ] Remove old framework entrypoints during rewrite.
- [ ] Add tests around the new feature contract rather than old class names.

## Acceptance

- A reviewer can trace why old code was studied.
- New code paths compile against the integrated architecture only.
- No old plugin or MITK ownership boundary appears in new business code.

## Failure Repair

If copied code brings old architecture with it, stop implementation for that feature and repair the owning feature document plus this rule document.
