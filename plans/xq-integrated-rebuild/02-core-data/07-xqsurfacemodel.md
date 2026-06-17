# XQSurfaceModel

## Purpose

Define the vascular surface model payload produced by segmentation or loaded from project model files.

## Owns

Future source files:

```text
src/core/XQSurfaceModel.h
src/core/XQSurfaceModel.cpp
tests/core/XQSurfaceModelTest.cpp
```

## Inputs

- Native `.mdl/.vtp` reader.
- Model lofting and capping feature.
- Model face metadata feature.

## Outputs

- One surface model with VTK polydata backing, named faces, cap ids, and model metadata.

## Rules

- `XQSurfaceModel` owns the semantic model; VTK polydata is the geometry backing.
- Model face ids, cap ids, and array names from SimVascular-style VTP files must be preserved.
- OpenCASCADE may be used by algorithms, but OCCT shapes are not the public payload contract.
- Models from `<acceptance-project>/Models` must load with metadata and surface geometry.

## Data Contract

```text
ModelId modelId
std::shared_ptr<SurfaceGeometryHandle> geometry
std::vector<ModelFace> faces
ModelSource source
std::optional<XQNodeId> sourceContourGroupNode
```

`ModelFace` stores:

```text
int faceId
std::string name
FaceKind kind
std::optional<int> capId
std::vector<int> boundaryLoopIds
```

Preserved VTP arrays:

```text
GlobalNodeID
GlobalElementID
ModelFaceID
CapID
```

## Implementation Contract

Public API surface:

```text
ModelId
ModelFace
FaceKind
SurfaceGeometryHandle
XQSurfaceModel
XQSurfaceModel::geometry()
XQSurfaceModel::faces()
XQSurfaceModel::faceById(faceId)
```

Dependency boundary:

```text
allowed internally: VTK polydata handle, optional OCCT algorithm products
not allowed publicly: raw vtkPolyData ownership, OCCT shape ownership
```

## Step Plan

- [ ] Define surface geometry handle that wraps VTK polydata internally.
- [ ] Define face metadata with face kind and cap id.
- [ ] Add metadata extraction for required VTP arrays.
- [ ] Keep generated model settings separate from loaded model metadata.
- [ ] Add tests that verify face arrays survive load and save.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQSurfaceModel --output-on-failure
```

Required cases:

create a model with wall and cap faces
lookup face by ModelFaceID
preserve GlobalNodeID, GlobalElementID, ModelFaceID, and CapID metadata
keep geometry handle internal
load Models/0090_0001.mdl and .vtp after model reader exists

## Acceptance

- Mesh generation can read model faces without parsing VTP arrays itself.
- Simulation setup can select inlet, outlet, and wall faces from `XQSurfaceModel`.
- Display code can color faces by `ModelFaceID`.

## Failure Repair

If face metadata is stored only in VTK arrays and not exposed through XQ APIs, repair this payload before adding meshing or simulation features.
