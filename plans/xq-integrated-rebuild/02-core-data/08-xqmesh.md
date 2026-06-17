# XQMesh

## Purpose

Define the mesh payload used for surface mesh, volume mesh, boundary transfer, and solver export.

## Owns

Future source files:

```text
src/core/XQMesh.h
src/core/XQMesh.cpp
tests/core/XQMeshTest.cpp
```

## Inputs

- Native `.msh/.vtu/.vtp` reader.
- Surface mesh and volume mesh features.
- Simulation solver export.

## Outputs

- One mesh payload with volume grid, surface boundary data, face mappings, and solver arrays.

## Rules

- `XQMesh` is an XQ mesh model with VTK unstructured grid and polydata backing.
- Boundary face identity must be preserved from model through mesh.
- Mesh files from `<acceptance-project>/Meshes` must load as native XQ mesh payloads.
- MMG is a mesh kernel behind algorithms, not the public mesh type.

## Data Contract

```text
MeshId meshId
std::shared_ptr<VolumeMeshHandle> volumeGrid
std::shared_ptr<SurfaceMeshHandle> surfaceMesh
std::vector<MeshRegion> regions
std::vector<MeshBoundaryFace> boundaryFaces
std::optional<XQNodeId> sourceModelNode
MeshQualitySummary quality
```

`MeshBoundaryFace` stores:

```text
int faceId
std::string name
FaceKind kind
std::optional<int> capId
std::vector<int> cellIds
```

Preserved arrays:

```text
GlobalNodeID
GlobalElementID
ModelFaceID
CapID
```

## Implementation Contract

Public API surface:

```text
MeshId
MeshRegion
MeshBoundaryFace
MeshQualitySummary
VolumeMeshHandle
SurfaceMeshHandle
XQMesh
XQMesh::volumeGrid()
XQMesh::surfaceMesh()
XQMesh::boundaryFaces()
XQMesh::boundaryFaceById(faceId)
```

Dependency boundary:

```text
allowed internally: VTK unstructured grid and polydata handles
not allowed publicly: mesher-specific object models
```

## Step Plan

- [ ] Define mesh handles for VTK unstructured grid and VTK polydata.
- [ ] Define mesh boundary face records.
- [ ] Add source relation from mesh to surface model.
- [ ] Preserve solver-relevant ids and arrays.
- [ ] Add tests for model face to mesh boundary transfer.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQMesh --output-on-failure
```

Required cases:

create volume and surface mesh handles
create wall, inlet, and outlet boundary face records
preserve GlobalNodeID, GlobalElementID, ModelFaceID, and CapID
bind source model node id
load Meshes/0090_0001.* after mesh reader exists

## Acceptance

- Solver export can use `XQMesh` without opening model files.
- Mesh visualization can show volume, exterior surface, and boundary faces.
- Loading `.msh`, `.vtu`, and `.vtp` from the acceptance project creates one coherent mesh payload.

## Failure Repair

If volume grid, boundary surface, and face names are loaded as unrelated scene nodes, repair this payload and the native mesh reader.
