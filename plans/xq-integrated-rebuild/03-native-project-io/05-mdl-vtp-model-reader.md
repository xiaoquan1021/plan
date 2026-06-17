# MDL and VTP Model Reader

## Purpose

Define native loading of model metadata from `.mdl` and model geometry from `.vtp` into `XQSurfaceModel`.

## Owns

Future source files:

```text
src/io/project/ModelReader.h
src/io/project/ModelReader.cpp
src/io/project/ModelWriter.h
src/io/project/ModelWriter.cpp
tests/io/project/ModelReaderTest.cpp
```

## Inputs

- `XQSurfaceModel` payload.
- VTK XML PolyData file content.
- tinyxml2 dependency role.

## Outputs

- One `XQSurfaceModel` node per model with geometry and face metadata.

## Rules

- `.mdl` and `.vtp` together form a first-version native XQ model load contract.
- `.mdl` owns semantic model metadata when present.
- `.vtp` owns polydata geometry and array data.
- Loaded `.vtp` geometry must enter XQ-owned triangle surface handles when appended zlib Points/Polys data can be decoded.
- Generated `XQTriangleSurfaceGeometryHandle` payloads must be written as first-pass ASCII VTK XML Points/Polys/ModelFaceID arrays and read back into XQ-owned triangle handles.
- Model face ids and cap ids must be preserved.

## Read Contract

From `.mdl` extract:

```text
model name
model type
face names
face ids
wall/inlet/outlet hints
source segmentation hints
unknown XML attributes
```

From `.vtp` extract:

```text
points
polys/connectivity/offsets
point data arrays
cell data arrays
GlobalNodeID
GlobalElementID
ModelFaceID
CapID
```

## Implementation Contract

Public API surface:

```text
ModelReader
ModelWriter
ModelReader::read(modelBasePath)
ModelWriter::write(surfaceModelNode, modelBasePath)
```

Output ownership:

```text
one XQDataNode
one XQSurfaceModel payload
geometry from .vtp
semantic metadata from .mdl and VTP arrays
```

Dependency boundary:

```text
tinyxml2 reads .mdl
tinyxml2 plus controlled static zlib read first-pass appended base64 vtkZLibDataCompressor .vtp payloads
tinyxml2 writes first-pass ASCII VTK XML .vtp payloads for generated XQ-owned triangle geometry
VTK may be used by visualization only, not as model payload ownership
XQSurfaceModel owns the semantic output
```

## Step Plan

- [ ] Match `.mdl` and `.vtp` by base name inside the Models directory.
- [ ] Read `.mdl` metadata with tinyxml2.
- [x] Read `.vtp` metadata and array summaries with tinyxml2.
- [x] Decode `.vtp` appended zlib Points/Polys arrays into `XQTriangleSurfaceGeometryHandle`.
- [x] Write generated `XQTriangleSurfaceGeometryHandle` payloads as ASCII `.vtp` geometry and read them back.
- [x] Build `ModelFace` records from metadata and VTP arrays.
- [x] Add tests using `<acceptance-project>/Models/0090_0001.mdl` and `.vtp`.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R ModelReader --output-on-failure
```

Required fixture:

<acceptance-project>/Models/0090_0001.mdl
<acceptance-project>/Models/0090_0001.vtp

Required cases:

match .mdl and .vtp by base name
read model metadata and VTP geometry
loaded model geometry is an XQTriangleSurfaceGeometryHandle with decoded points and triangle face ids
generated model geometry round-trips through ModelWriter and ModelReader as XQTriangleSurfaceGeometryHandle
preserve GlobalNodeID, GlobalElementID, ModelFaceID, and CapID
build ModelFace records
reject missing paired geometry with diagnostic result

## Acceptance

- The loaded model contains both surface geometry and model face metadata.
- Simulation setup can identify face ids without parsing `.mdl`.
- Saving can preserve known face arrays and names.

## Failure Repair

If model geometry and face metadata become separate scene nodes, merge them back into `XQSurfaceModel`.
