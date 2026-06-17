# 0007 Project Acceptance

## Purpose

Define the real project that proves the first integrated XQ version can load SimVascular-style vascular workflow data as native XQ data.

## Acceptance Project

```text
<acceptance-project>
```

## Owns

Acceptance source and test contract:

```text
src/app/main.cpp
tests/acceptance/XQ0007ProjectAcceptanceTest.cpp
CMakeLists.txt
```

Acceptance data boundary:

```text
<acceptance-project>
```

## Inputs

- Hardened native project IO readers.
- Hardened core data payloads.
- Hardened four-pane workbench and visualization contracts.
- Hardened workflow source relation contracts.
- `<acceptance-project>`.

## Outputs

- One loaded `XQProject`.
- One loaded `XQScene`.
- Scene nodes for image, paths, contour groups, surface model, mesh, and simulation case.
- Source relations for the Image to SimulationPrep chain.
- Diagnostics for non-fatal missing optional data.
- A command-line `XQ` startup path that opens the same project through `XQProjectDirectoryReader` or `XQNativeProjectReader`, not only `XQProject::openExisting`.

## Required Files

Expected project contents:

```text
.svproj
Images/OSMSC0090-cm.vti
Paths/*.pth
Segmentations/*.ctgr
Models/0090_0001.mdl
Models/0090_0001.vtp
Meshes/0090_0001.msh
Meshes/0090_0001.vtp
Meshes/0090_0001.vtu
Simulations/0090_0001.sjb
Simulations/0090_0001/bct.vtp
Simulations/0090_0001/rcrt.dat
Simulations/0090_0001/inflow.flow
Simulations/0090_0001/solver.inp
Simulations/0090_0001/*.svpre
```

## Required Scene Result

Opening the project directory must create:

```text
one XQProject
one XQScene
one or more XQImageVolume nodes
XQPath nodes from Paths
XQContourGroup nodes from Segmentations
XQSurfaceModel nodes from Models
XQMesh nodes from Meshes
XQSimulationCase nodes from Simulations
source relations across the chain
project diagnostics for any non-fatal missing optional data
```

## Rules

- This is a native load acceptance target.
- Do not satisfy this by adding a separate compatibility module.
- Do not require SimVascular source code at runtime.
- Do not use `<xq-implementation-workspace>` as record for expected behavior.
- Do not pass acceptance by stopping at an import shell, compatibility layer, plugin shell, MITK wrapper, BlueBerry wrapper, CTK wrapper, or old framework facade.
- Acceptance requires loaded project data to be available through `XQProject`, `XQScene`, `XQDataNode`, and XQ-owned payload types.
- `XQProject::openExisting` is only a lightweight core lifecycle probe; app/runtime acceptance must use IO readers that populate the scene.
- The command-line `XQ <project-root>` smoke path must report a non-zero scene node count for `<acceptance-project>`.

## Implementation Contract

Source files:

```text
src/app/main.cpp
tests/acceptance/XQ0007ProjectAcceptanceTest.cpp
CMakeLists.txt
```

Existing loader contracts:

```text
XQProjectDirectoryReader::open(const std::filesystem::path&) -> XQProject
XQNativeProjectReader::read(const std::filesystem::path&) -> XQProject
```

Acceptance helper behavior:

```text
If root contains project.xqproj, app startup uses XQNativeProjectReader.
Otherwise, if root contains .svproj, app startup uses XQProjectDirectoryReader.
Otherwise, startup may create/open an empty project through core lifecycle.
```

Forbidden shortcuts:

```text
no MITK, BlueBerry, CTK, plugin, compatibility, or SimVascular source-code path
no acceptance-only hardcoded node creation
no bypass of XQProject/XQScene/XQDataNode payload contracts
```

## Step Plan

- [x] Add failing acceptance tests in `tests/acceptance/XQ0007ProjectAcceptanceTest.cpp`.
- [x] Open the project directory through `XQProjectDirectoryReader`.
- [x] Verify image node from `OSMSC0090-cm.vti`.
- [x] Verify path nodes from `.pth`.
- [x] Verify contour group nodes from `.ctgr`.
- [x] Verify model node from `.mdl/.vtp`.
- [x] Verify mesh node from `.msh/.vtu/.vtp`.
- [x] Verify simulation case from `.sjb` and related files.
- [x] Verify source relations and project tree groups.
- [x] Verify native project save/reopen preserves the acceptance chain.
- [x] Verify `XQ <acceptance-project>` reports scene nodes from the real loader.
- [x] Run focused acceptance tests, full build, and full test suite.

## Test Plan

Test target:

xq_acceptance_tests

Test file:

tests/acceptance/XQ0007ProjectAcceptanceTest.cpp

Core scenarios:

XQ0007ProjectAcceptanceLoadsIntegratedProject
XQ0007ProjectAcceptancePreservesWorkflowRelations
XQ0007ProjectAcceptanceNativeRoundTripPreservesImplementedPayloads
XQ0007ProjectAcceptanceAppStartupUsesProjectReaders

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_acceptance_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQ0007ProjectAcceptance --output-on-failure
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

Required checks:

project root is <acceptance-project>
one XQProject exists
one XQScene exists
image node exists for Images/OSMSC0090-cm.vti
path nodes exist for Paths/*.pth
contour group nodes exist for Segmentations/*.ctgr
surface model node exists for Models/0090_0001.mdl and .vtp
mesh node exists for Meshes/0090_0001.msh, .vtp, and .vtu
simulation case node exists for Simulations/0090_0001.sjb
source relations connect Image -> Path -> ContourGroup -> SurfaceModel -> Mesh -> SimulationCase
data is accessible through XQProject, XQScene, XQDataNode, and XQ-owned payload types
XQ executable prints a scene-node count greater than zero for <acceptance-project>

Minimum negative case:

XQProject::openExisting alone is insufficient for app acceptance if scene node count remains zero for a SimVascular project directory.

TDD red record:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQ0007ProjectAcceptance --output-on-failure
```

failed before implementation because XQ0007ProjectAcceptanceAppStartupUsesProjectReaders
observed `XQ <acceptance-project>` printing `Scene nodes: 0`.
The acceptance test also tightened relation coverage and exposed that loaded
SimVascular model sources must be represented by scene relations from all
contour groups, not by a single payload source id.

## Acceptance

- The project opens into XQ-owned objects.
- The workflow chain Image to SimulationPrep is visible in the workbench.
- Model and mesh arrays such as `GlobalNodeID`, `GlobalElementID`, `ModelFaceID`, and `CapID` are preserved.
- Loaded image, path, contour, model, mesh, and simulation data are accessible through the integrated XQ project and scene contracts.
- `XQ <acceptance-project>` opens through project readers and reports 14 scene nodes.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

Use `02-failure-routing.md` to identify the smallest owning document before changing code.
