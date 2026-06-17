# MSH, VTU, and VTP Mesh Reader

## Purpose

Define native loading of mesh metadata and mesh geometry into `XQMesh`.

## Owns

Future source files:

```text
src/io/project/MeshReader.h
src/io/project/MeshReader.cpp
src/io/project/MeshWriter.h
src/io/project/MeshWriter.cpp
tests/io/project/MeshReaderTest.cpp
```

## Inputs

- `XQMesh` payload.
- VTK XML UnstructuredGrid and PolyData file content.
- tinyxml2 dependency role for `.msh` metadata when XML-style content is present.

## Outputs

- One coherent `XQMesh` node containing volume grid, surface mesh, and boundary metadata.

## Rules

- `.msh`, `.vtu`, and `.vtp` under a mesh directory are first-version native XQ mesh files.
- Mesh surface and volume data are not loaded as unrelated nodes.
- Boundary identity must be preserved for simulation.
- MMG is not required for loading existing project mesh files.
- Loaded mesh surface `.vtp` geometry must enter XQ-owned triangle surface mesh handles when appended zlib Points/Polys data can be decoded.
- Loaded mesh volume `.vtu` geometry must enter XQ-owned tetrahedral volume mesh handles when inline binary zlib Points/Cells data can be decoded.
- Generated `XQTriangleSurfaceMeshHandle` and `XQTetrahedralVolumeMeshHandle` payloads must be written as first-pass ASCII VTK XML arrays and read back into XQ-owned mesh handles.

## Read Contract

Extract:

```text
mesh name
mesh generation metadata
volume points and tetrahedral cells/connectivity/offsets/types from .vtu
surface points and polys/connectivity/offsets from .vtp
boundary face ids
GlobalNodeID
GlobalElementID
ModelFaceID
CapID
```

## Implementation Contract

Public API surface:

```text
MeshReader
MeshWriter
MeshReader::read(meshBasePath)
MeshWriter::write(meshNode, meshBasePath)
```

Output ownership:

```text
one XQDataNode
one XQMesh payload
volume grid from .vtu
surface boundary from .vtp
metadata from .msh when available
```

Dependency boundary:

```text
tinyxml2 plus controlled static zlib read first-pass vtkZLibDataCompressor VTK XML payloads
.vtp appended base64 Points/Polys data decodes into XQ-owned triangle surface handles
.vtu inline binary base64 Points/Cells data decodes into XQ-owned tetrahedral volume handles
generated surface and volume mesh handles write first-pass ASCII VTK XML Points/Polys/Cells/ModelFaceID arrays
VTK may be used by visualization only, not as mesh payload ownership
MMG is not needed to load existing mesh files
```

## Step Plan

- [x] Match `.msh`, `.vtu`, and `.vtp` files by base name inside the Meshes directory.
- [x] Read `.vtu` metadata and array summaries as first-pass volume mesh counts.
- [x] Decode `.vtu` inline binary zlib Points/Cells arrays into `XQTetrahedralVolumeMeshHandle`.
- [x] Decode `.vtp` appended zlib Points/Polys arrays into `XQTriangleSurfaceMeshHandle`.
- [x] Write generated surface and volume mesh handles as ASCII `.vtp`/`.vtu` geometry and read them back.
- [x] Read `.msh` metadata when present.
- [x] Build boundary face records from arrays and metadata.
- [x] Add tests using `<acceptance-project>/Meshes/0090_0001.*`.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R MeshReader --output-on-failure
```

Required fixture:

<acceptance-project>/Meshes/0090_0001.msh
<acceptance-project>/Meshes/0090_0001.vtp
<acceptance-project>/Meshes/0090_0001.vtu

Required cases:

match mesh files by base name
read volume grid and surface boundary
loaded mesh surface is an XQTriangleSurfaceMeshHandle with decoded points and triangle face ids
loaded mesh volume is an XQTetrahedralVolumeMeshHandle with decoded points and tetrahedra
generated mesh surface and volume geometry round-trips through MeshWriter and MeshReader as XQ-owned handles
preserve GlobalNodeID, GlobalElementID, ModelFaceID, and CapID
build boundary face records
reject missing volume grid with diagnostic result

## Acceptance

- A loaded mesh links to its source model when the model exists.
- Boundary face metadata is available to simulation setup.
- Solver export receives node and element ids from `XQMesh`.
- Loaded surface `.vtp` and volume `.vtu` actors can be derived from XQ-owned mesh handles without VTK ownership in IO or domain payloads.

## Failure Repair

If mesh loading loses `ModelFaceID` or `CapID`, repair this reader before adding solver export behavior.
