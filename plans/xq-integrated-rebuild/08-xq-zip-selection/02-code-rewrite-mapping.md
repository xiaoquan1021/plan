# XQ Zip Code Rewrite Mapping

## Purpose

Define where useful behavior from `<xq-source-extract>` should land in the new integrated project.

## Owns

Future execution practice and feature-level migration notes.

## Inputs

- Code selection rules.
- All core, IO, workflow, visualization, and domain feature documents.

## Outputs

- A mapping from old-code responsibility to new-code location.

## Rules

- This document maps responsibility only; it does not authorize direct source copying.
- Every rewrite must land in one integrated XQ owner.
- Old framework entrypoints are rejected even when the underlying behavior is kept.
- If an old-code area maps to more than one owner, split behavior by data ownership first, then UI or command routing second.

## Rewrite Map

| Old-code responsibility or old source area | New owner |
| --- | --- |
| `Code/Source/Application` application startup and workbench launch intent | `src/app`, `src/workbench`, and `05-workbench-visualization/01-main-window-layout.md`; reject BlueBerry/MITK application shell |
| Project open/save behavior from `Modules/ProjectManagement` | `src/io/project` and `src/core/XQProject`; folder discovery belongs to `03-native-project-io/01-open-project-directory.md` |
| Project metadata and node metadata IO | `src/core/XQMetadata`, `src/io/project`, and native project reader/writer documents |
| MITK data node use | `src/core/XQDataNode` and `src/core/XQScene`; reject old `DataStorage` ownership |
| Common math, spline, and coordinate utilities | Feature-local helpers in `src/domain`, with tests in the owning domain document |
| XML utility behavior | `src/io/project` or format-specific readers using tinyxml2 |
| VTK helper behavior | `src/visualization` disposable products or domain geometry builders; never expose VTK ownership through core/project/workflow public APIs |
| Path and centerline behavior from `Modules/Path` | `src/domain/path`, `src/io/project` path readers, and workbench path panels |
| Contour/profile behavior from `Modules/Segmentation` | `src/domain/contour`, `src/domain/modeling` loft input, and workbench contour panels |
| 3D segmentation behavior from `Modules/Segmentation` | `src/domain/segmentation` and visualization display products |
| Modeling behavior from `Modules/Model/Common` | `src/domain/modeling`, `src/io/project`, and `src/visualization` |
| OCCT-specific geometry behavior from `Modules/Model/OCCT` | Future modeling-kernel dependency document plus `src/domain/modeling`; reject public OCCT handles until the boundary is selected |
| Meshing behavior from `Modules/Mesh/Common` | `src/domain/meshing`, `src/io/project`, and `src/visualization`; reject MITK grid wrappers |
| Simulation setup behavior | `src/domain/simulation` and `src/io/project` writers |
| Solver export behavior | `07-domain-features/12-simulation-solver-export.md` and solver writer files |
| ROM job behavior | `07-domain-features/13-rom-and-multiphysics.md`; reject MITK ROM job wrappers |
| Multiphysics equation/domain/settings behavior | `07-domain-features/13-rom-and-multiphysics.md`; reject MITK multiphysics job wrappers |
| Image preprocessing helpers | `04-medical-image-io` or `07-domain-features/05-3d-segmentation.md` only when a future feature selects exact behavior |
| Pipeline plugin actions/views/preferences/widgets | Split into `src/workflow`, `src/workbench`, and the owning domain feature; reject plugin activators, `plugin.xml`, perspectives, and service registration |
| Data/project-node plugin icon/name resources | `src/workbench` presentation metadata only after the UI owner selects them |
| Python API and Python-node plugin behavior | Deferred; no current owner in the integrated initial contract |
| External install scripts and old CMake macros | Dependency superbuild/version-lock documents only |
| Old tests and design docs | Owning feature tests and acceptance documents, not runtime source |

## Rewrite Rules

- Preserve domain behavior when it serves the integrated XQ workflow.
- Rename classes to XQ-owned concepts instead of keeping old plugin names.
- Convert raw framework events into workflow commands or scene notifications.
- Convert external-library public types into XQ payloads and service parameters.
- Keep file-format readers near `src/io/project`.

## Applied Rewrite Records

| New owner | Old source behavior kept | Old source behavior rejected |
| --- | --- | --- |
| `src/workbench/XQProjectTreeQtModel.*` | `org.xq.core.datamanager` exposed project data through a Qt tree and represented visibility as a check state | `QmitkDataStorageTreeModel`, MITK `DataNode`/`DataStorage`, BlueBerry view registration, rendering-manager refresh hooks, context-menu extension points, plugin activators |
| `src/workbench/XQProjectTreeViewWidget.*` | `org.xq.core.datamanager` composed a `QTreeView`, attached a tree model, and listened to `selectionModel()` changes | `QmitkDataStorageTreeModel` ownership, selected MITK payload pointer access, context-menu plugin action surface, rendering-manager refresh hooks, BlueBerry view ownership, generated `.ui` view ownership |
| `src/workbench/XQProjectTreeViewWidget.*` plus `workflow/commands/XQSceneCommands.*` | `org.xq.core.datamanager` offered selected-node rename from the project tree | Direct MITK node mutation from the view, plugin-owned context menu command ownership, old view dialog ownership |

## Implementation Contract

Planning contract only. This document maps old-code responsibilities to new
integrated XQ owners; it does not authorize direct source copying.

Required invariants:

```text
every selected old behavior maps to one smallest new owner
framework entrypoints are rejected even when behavior is kept
external-library public objects are converted to XQ payloads or service parameters
file-format readers stay under IO owners
workflow/UI behavior is separated from domain payload ownership
```

## Test Plan

Document consistency checks:

```text
python3 harness/audit_xq_zip_analysis.py
rg -n "MITK|BlueBerry|CTK|plugin|DataStorage" plans/xq-integrated-rebuild/08-xq-zip-selection
```

Expected result:

old framework terms appear only in rejected behavior or boundary language
new owners are explicit before a rewrite starts

## Step Plan

- [x] For the first inventory, assign each top-level old-code area one new owner from the map.
- [x] Move project-tree Qt behavior into the new owner through rewrite, not direct copy.
- [x] Replace project-tree old framework dependencies with XQ-owned inputs and outputs.
- [x] Add project-tree Qt adapter tests against the new owner.
- [x] Add project-tree QTreeView widget tests against the new owner.
- [x] Add project-tree rename command-integration tests against the new owner.
- [x] Document project-tree old/new mismatches in the smallest owning `.md`.
- [ ] Move future selected behavior into its owner through rewrite, not direct copy.
- [ ] Replace future old framework dependencies with XQ-owned inputs and outputs.
- [ ] Add future feature tests against the new owner.
- [ ] Document future mismatches in the smallest owning `.md`.

## Acceptance

- New implementation folders are understandable without reading old plugin layout.
- No feature needs old XQ service registry or MITK data storage.
- Old behavior is represented as integrated XQ services, payloads, readers, or viewers.

## Failure Repair

If a rewrite has no clear new owner, create or revise the smallest feature document before writing source code.
