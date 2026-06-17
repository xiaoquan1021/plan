# Volume Mesh

## Purpose

Define volume mesh generation from a prepared surface mesh or surface model.

This document creates an XQ-owned volume mesh payload from closed
triangle surface input. It must keep tetrahedral generation behind
`XQVolumeMeshService`, preserve boundary face metadata for solver setup, and avoid
exposing VTK, MMG, TetGen, or any other mesher object model to business code.

## Owns

Current source-pass files:

```text
src/core/XQMesh.h
src/core/XQMesh.cpp
src/domain/meshing/XQVolumeMeshService.h
src/domain/meshing/XQVolumeMeshService.cpp
tests/domain/meshing/XQVolumeMeshServiceTest.cpp
```

## Inputs

- `XQSurfaceModel`.
- `XQMesh`.
- `XQTriangleSurfaceGeometryHandle`.
- `XQTriangleSurfaceMeshHandle`.
- Existing `MeshBoundaryFace` records from the surface mesh path.
- Volume meshing parameters owned by this service.

## Outputs

- A volume `XQMesh` with unstructured grid, boundary surface, and face mappings.
- XQ-owned tetrahedral volume mesh handle.
- Surface mesh data retained on the output mesh when available.
- Mesh boundary face records with preserved face ids, cap ids, and boundary cell ids.
- Basic volume mesh quality summary.
- Optional workflow command that adds mesh nodes to `XQScene`.

## Rules

- Volume meshing is an XQ service with replaceable kernel internals.
- initial contract uses an XQ-owned tetrahedral fan generated from a closed
  triangle surface. It does not introduce VTK, MMG, TetGen, UI state, plugin
  state, or external mesh object ownership.
- VTK/MMG/TetGen or another tetrahedral kernel may be introduced later only
  behind the service API.
- Boundary face metadata must survive into the volume mesh.
- Mesh generation parameters are typed XQ structs.
- The output mesh links to its source model.
- Volume mesh output must be stored in `XQMesh`, not as a loose kernel object.
- Unsupported, open, degenerate, or non-triangle input must fail loudly.

## Functional Content

First-version behavior:

```text
accept XQ triangle surface model geometry or XQ triangle surface mesh input
validate non-empty closed triangle surface
reject non-manifold/open boundary edges
generate one interior point and tetrahedral cells fan-connected to surface triangles
attach stable point ids and element ids through the XQ-owned volume handle
attach boundary face ids
compute quality summary
link mesh to source model
create mesh node command
create SurfaceModelToMesh source relation in the same undoable command
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Implementation Contract

Core additions:

```text
VolumeTetrahedron
XQTetrahedralVolumeMeshHandle : VolumeMeshHandle
```

Public service types:

```text
XQVolumeMeshParameters
XQVolumeMeshService
```

Minimum public operations:

```text
createVolumeMesh(const XQSurfaceModel&, XQNodeId, XQVolumeMeshParameters) -> std::shared_ptr<XQMesh>
createVolumeMesh(const XQMesh&, XQNodeId, XQVolumeMeshParameters) -> std::shared_ptr<XQMesh>
createVolumeMeshNodeCommand(std::string, const XQSurfaceModel&, XQNodeId, XQVolumeMeshParameters) -> std::unique_ptr<XQCommand>
```

Owned data:

```text
std::vector<Point3> points
std::vector<VolumeTetrahedron> tetrahedra
per-tetrahedron boundary/source face id
producer name
```

Validation:

```text
source model node id must not be empty
model geometry must be XQTriangleSurfaceGeometryHandle in this document
mesh input must contain XQTriangleSurfaceMeshHandle in this document
surface must have at least four points and four triangles
each triangle index must reference an existing point
every undirected surface edge must be used exactly twice
closed surface centroid must not create zero-volume tetrahedra
quality summary must be marked invalid when no valid tetrahedra exist
quality improvement request must be rejected until a real kernel is selected
```

External dependency boundary:

```text
forbidden in public service/core API: VTK, MMG, TetGen, Qt, MITK, BlueBerry, CTK, OpenCASCADE
allowed later inside service implementation only: tetrahedral meshing kernel adapters
```

## Step Plan

- [x] Add XQ-owned tetrahedral volume mesh handle to core.
- [x] Define `XQVolumeMeshParameters`.
- [x] Accept `XQSurfaceModel` and existing surface `XQMesh` inputs.
- [x] Validate closed triangle surface topology.
- [x] Generate first-pass tetrahedra through an XQ-owned internal path.
- [x] Attach stable point and element ids through handle ordering.
- [x] Attach model face and cap ids to boundary records.
- [x] Compute basic tetrahedral edge length and aspect summary.
- [x] Add command creation for mesh scene nodes.
- [x] Add tests for closed-surface generation, surface-mesh input, boundary metadata,
  command routing, and unsupported/open inputs.

## Test Plan

Test target:

xq_volume_mesh_service_tests

Test file:

tests/domain/meshing/XQVolumeMeshServiceTest.cpp

Core scenarios:

XQVolumeMeshServiceCreatesTetrahedralMeshFromClosedSurfaceModel
XQVolumeMeshServiceCreatesVolumeMeshFromSurfaceMeshInput
XQVolumeMeshServicePreservesBoundaryFaceMetadata
XQVolumeMeshServiceComputesQualitySummary
XQVolumeMeshServiceCreatesMeshNodeCommand
XQVolumeMeshServiceCreatesSurfaceModelToMeshSourceRelationWithUndoRedo
XQVolumeMeshServiceRejectsOpenOrUnsupportedInputs

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_volume_mesh_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQVolumeMeshService --output-on-failure
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_volume_mesh_service_tests
```

failed before implementation because tests/domain/meshing/XQVolumeMeshServiceTest.cpp
included domain/meshing/XQVolumeMeshService.h and that service did not exist yet.

## Acceptance

- The resulting `XQMesh` contains both volume and boundary information.
- Solver export can read elements and boundary ids from one payload.
- Kernel-specific objects stay inside the service implementation.
- The initial contract uses XQ-owned tetrahedral mesh data and can later swap in
  a real tetrahedral kernel without changing public payloads.
- Boundary face records preserve model face id, face name, face kind, cap id, and
  generated boundary cell ids.
- The service rejects open surfaces instead of manufacturing a plausible mesh.

## Failure Repair

If volume mesh generation requires business code to know a mesher-specific object model, wrap that object model in this service.
