# Mesh Boundary Transfer

## Purpose

Define transfer of boundary identity from surface model faces to surface and volume mesh boundaries.

This document centralizes deterministic boundary mapping for both
surface and volume mesh generation. It takes XQ face metadata and mesh cell
assignments and returns XQ-owned `MeshBoundaryFace` records. It must not expose
VTK, MMG, TetGen, or simulation-specific boundary objects to business code.

## Owns

Current source-pass files:

```text
src/domain/modeling/XQModelFaceService.h
src/domain/modeling/XQModelFaceService.cpp
src/domain/meshing/XQMeshBoundaryTransfer.h
src/domain/meshing/XQMeshBoundaryTransfer.cpp
src/domain/meshing/XQSurfaceMeshService.h
src/domain/meshing/XQSurfaceMeshService.cpp
src/domain/meshing/XQVolumeMeshService.h
src/domain/meshing/XQVolumeMeshService.cpp
tests/domain/modeling/XQModelFaceServiceTest.cpp
tests/domain/meshing/XQMeshBoundaryTransferTest.cpp
tests/domain/meshing/XQSurfaceMeshServiceTest.cpp
tests/domain/meshing/XQVolumeMeshServiceTest.cpp
```

## Inputs

- `XQSurfaceModel`.
- `XQMesh`.
- Model face metadata.
- Triangle or tetrahedral cell-face assignments produced by meshing services.

## Outputs

- Mesh boundary records with face id, face name, face kind, cap id, and cell ids.
- Diagnostics for unmatched, ambiguous, or missing boundary cells.

## Rules

- Boundary identity is semantic data, not display coloring.
- Transfer must be deterministic and testable.
- Loaded mesh arrays and generated mesh mappings use the same `MeshBoundaryFace` contract.
- Simulation setup depends on transferred boundary data.
- Boundary transfer is an XQ-owned service concern, not a scene or UI concern.
- Surface mesh and volume mesh services may reuse the transfer logic but should
  not duplicate mapping policy.

## Transfer Contract

For each model face:

```text
find corresponding surface mesh cells
assign ModelFaceID
assign CapID when present
create MeshBoundaryFace record
preserve face name and kind
record unmatched or ambiguous cells as diagnostics
```

For generated volume meshes:

```text
propagate face ids from source surface triangles to tetrahedra
preserve cap ids when available
keep empty boundary cell lists only when the service has no better mapping data
```

For loaded meshes:

```text
preserve boundary faces from existing arrays and metadata
do not invent missing model metadata
diagnose missing or duplicate face ids
```

## Step Plan

- [x] Define deterministic model-face-to-boundary-row mapping.
- [x] Preserve loaded array-based boundary mappings.
- [x] Reuse model-face mapping from surface meshing and volume meshing.
- [x] Validate that inlet/outlet faces expose boundary cell ids.
- [x] Add diagnostics for missing, duplicate, or ambiguous boundary assignments.
- [x] Add tests for wall, inlet, outlet, and cap face transfer.

## Implementation Contract

Current ownership:

```text
XQModelFaceService::boundaryFacesForModel(...)
XQMeshBoundaryTransferService::transferFromModel(...)
XQMeshBoundaryTransferService::transferFromSurfaceMesh(...)
XQMeshBoundaryTransferService::transferFromVolumeMesh(...)
XQMeshBoundaryTransferService::preserveLoadedBoundaryFaces(...)
```

Public boundary records:

```text
MeshBoundaryFace
MeshQualitySummary
```

Diagnostics:

```text
missing boundary face ids
duplicate boundary face ids
faces with no mapped cells
ambiguous cell-to-face assignments
```

Forbidden shortcuts:

```text
direct dependence on mesh kernel face objects
UI-layer boundary coloring as source of truth
plugin-based boundary registries
simulation boundary objects as boundary model owners
```

## Test Plan

Test targets:

xq_model_face_service_tests
xq_mesh_boundary_transfer_tests
xq_surface_mesh_service_tests
xq_volume_mesh_service_tests

Primary assertions:

model faces become MeshBoundaryFace rows with preserved names/kinds/cap ids
surface mesh generation preserves face ids and cell ids
volume mesh generation preserves face ids, cap ids, and tetrahedral cell ids
inlet/outlet faces reject missing boundary cell mappings
loaded mesh metadata round-trips boundary rows

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_mesh_boundary_transfer_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQMeshBoundaryTransfer --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_model_face_service_tests xq_surface_mesh_service_tests xq_volume_mesh_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R 'XQ(ModelFaceService|SurfaceMeshService|VolumeMeshService)' --output-on-failure
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_mesh_boundary_transfer_tests
```

failed before implementation because tests/domain/meshing/XQMeshBoundaryTransferTest.cpp
included domain/meshing/XQMeshBoundaryTransfer.h and that service did not exist yet.

## Acceptance

- Simulation boundary conditions can bind to mesh boundaries by face id.
- Model and mesh face identity agree after mesh generation.
- Diagnostics identify missing or ambiguous boundary mappings.
- The same boundary row contract is used by model, surface mesh, volume mesh,
  and later simulation boundary setup.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If simulation setup looks up boundaries from model metadata while using mesh geometry, repair boundary transfer and use `XQMesh` as the simulation source.
