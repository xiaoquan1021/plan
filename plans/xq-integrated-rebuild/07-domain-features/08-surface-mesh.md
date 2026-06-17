# Surface Mesh

## Purpose

Define surface mesh preparation and improvement from `XQSurfaceModel`.

This document converts an XQ-owned triangle surface model into an XQ-owned surface mesh payload. It does not introduce VTK, MMG, TetGen, UI state, or external mesh object ownership.

## Owns

Current source-pass files:

```text
src/core/XQMesh.h
src/core/XQMesh.cpp
src/domain/meshing/XQSurfaceMeshService.h
src/domain/meshing/XQSurfaceMeshService.cpp
tests/domain/meshing/XQSurfaceMeshServiceTest.cpp
```

## Inputs

- `XQSurfaceModel`.
- `XQMesh`.
- `XQTriangleSurfaceGeometryHandle`.
- `XQModelFaceService` boundary metadata transfer.
- Surface meshing parameters owned by this service.

## Outputs

- Surface mesh data attached to an `XQMesh` payload or used as input for volume meshing.
- XQ-owned triangle surface mesh handle.
- Mesh boundary face records with preserved face ids and cell ids.
- Basic mesh quality summary.
- Optional workflow command that adds mesh nodes to `XQScene`.

## Rules

- Surface meshing service owns the algorithm sequence.
- initial contract uses XQ-owned triangle copying and metadata transfer only.
- MMG is a later improvement/remeshing kernel behind the service API.
- Model face metadata must transfer onto surface mesh faces.
- Surface mesh output links to its source model.
- Domain meshing must not depend on VTK, MMG, Qt, MITK, BlueBerry, CTK, OpenCASCADE, or plugin APIs.
- Surface mesh output must be stored in `XQMesh`, not as loose VTK polydata.

## Functional Content

First-version behavior:

```text
accept XQ triangle surface model geometry
copy triangle surface into XQ surface mesh handle
preserve face ids
compute basic mesh quality summary
create mesh boundary records from model face metadata and triangle face ids
create mesh node command
create SurfaceModelToMesh source relation in the same undoable command
reject unsupported non-triangle surface geometry in this document
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Implementation Contract

Core additions:

```text
XQTriangleSurfaceMeshHandle : SurfaceMeshHandle
```

Public service types:

```text
XQSurfaceMeshParameters
XQSurfaceMeshService
```

Minimum public operations:

```text
createSurfaceMesh(const XQSurfaceModel&, XQNodeId, XQSurfaceMeshParameters) -> std::shared_ptr<XQMesh>
createSurfaceMeshNodeCommand(std::string, const XQSurfaceModel&, XQNodeId, XQSurfaceMeshParameters) -> std::unique_ptr<XQCommand>
```

Validation:

```text
source model node id must not be empty
model geometry must be XQTriangleSurfaceGeometryHandle in this document
model face metadata must be valid
triangles must reference valid points
quality summary must be marked invalid for empty triangle sets
```

## Step Plan

- [x] Add XQ-owned triangle surface mesh handle to core.
- [x] Accept `XQSurfaceModel` and meshing parameters.
- [x] Copy XQ triangle model geometry into surface mesh handle.
- [x] Preserve triangle face ids.
- [x] Build boundary records from model faces and triangle face ids.
- [x] Compute basic edge length and aspect summary.
- [x] Add command creation for mesh scene nodes.
- [x] Add tests for face id preservation, boundary cell ids, quality summary, command routing, and unsupported inputs.

## Test Plan

Test target:

xq_surface_mesh_service_tests

Test file:

tests/domain/meshing/XQSurfaceMeshServiceTest.cpp

Core scenarios:

XQSurfaceMeshServiceCreatesMeshFromTriangleModel
XQSurfaceMeshServicePreservesFaceIdsAndBoundaryCells
XQSurfaceMeshServiceComputesQualitySummary
XQSurfaceMeshServiceCreatesMeshNodeCommand
XQSurfaceMeshServiceCreatesSurfaceModelToMeshSourceRelationWithUndoRedo
XQSurfaceMeshServiceRejectsUnsupportedInputs

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_surface_mesh_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQSurfaceMeshService --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_surface_mesh_service_tests
```

failed before implementation because src/domain/meshing/XQSurfaceMeshService.cpp did not exist

## Acceptance

- Surface mesh can be generated without direct UI state.
- Model face ids remain available after surface meshing.
- Output is stored in `XQMesh`, not as loose VTK polydata.
- The initial contract uses XQ-owned mesh data and can later swap in MMG without changing public payloads.

## Failure Repair

If surface mesh output loses face mapping, repair this service before adding volume meshing.
