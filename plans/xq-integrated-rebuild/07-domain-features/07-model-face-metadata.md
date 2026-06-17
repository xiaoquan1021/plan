# Model Face Metadata

## Purpose

Define creation, preservation, editing, and transfer of model face metadata.

This document treats face metadata as a first-class XQ-owned domain contract. It does not create rendering colors, actor ids, VTK arrays, or meshing output. It edits `XQSurfaceModel` payloads through commands and exposes a deterministic transfer shape for later mesh generation.

## Owns

Current source-pass files:

```text
src/core/XQSurfaceModel.h
src/core/XQSurfaceModel.cpp
src/domain/modeling/XQModelFaceService.h
src/domain/modeling/XQModelFaceService.cpp
tests/domain/modeling/XQModelFaceServiceTest.cpp
```

## Inputs

- `XQSurfaceModel`.
- `XQDataNode` containing a surface model payload.
- Loaded model metadata from existing readers.
- Generated model metadata from `XQModelingService`.

## Outputs

- Stable face ids, names, kinds, cap ids, and boundary loop mappings.
- Undoable commands for face rename and reclassify operations.
- Mesh boundary face rows copied from model faces for later mesh generation.
- Validation diagnostics for duplicate or invalid face records.

## Rules

- Face metadata is a first-class part of `XQSurfaceModel`.
- Loaded arrays such as `ModelFaceID` and `CapID` are preserved.
- User changes to face names or kinds go through commands.
- Meshing and simulation never infer boundary identity from colors.
- Editing must replace `XQSurfaceModel` payloads through the command stack.
- The service must not depend on VTK, OpenCASCADE, Qt, MITK, plugin APIs, or IO-layer readers.
- Transfer output is metadata only; mesh cell ownership remains a later meshing step.

## Face Kinds

```text
Wall
Inlet
Outlet
Cap
Branch
Unknown
```

## Step Plan

- [x] Add `replaceFace(...)` support to `XQSurfaceModel`.
- [x] Validate positive and unique face ids.
- [x] Validate non-empty face names.
- [x] Provide rename command for model face names.
- [x] Provide reclassify command for model face kind and cap id.
- [x] Provide metadata-only transfer from model faces to `MeshBoundaryFace` rows.
- [x] Add tests for generated/loaded-style face metadata, command undo, validation, and transfer.

## Implementation Contract

Core addition:

```text
XQSurfaceModel::replaceFace(ModelFace) -> bool
```

Public service types:

```text
XQModelFaceDiagnostic
XQModelFaceService
```

Minimum public operations:

```text
validateFaces(const XQSurfaceModel&) -> std::vector<XQModelFaceDiagnostic>
renameFaceCommand(const XQDataNode&, int faceId, std::string newName) -> std::unique_ptr<XQCommand>
reclassifyFaceCommand(const XQDataNode&, int faceId, FaceKind newKind, std::optional<int> capId) -> std::unique_ptr<XQCommand>
boundaryFacesForModel(const XQSurfaceModel&) -> std::vector<MeshBoundaryFace>
```

Validation:

```text
face id must be positive
face ids must be unique
face name must not be empty
edit commands require an XQDomainType::SurfaceModel node
edited face id must already exist
```

## Test Plan

Test target:

xq_model_face_service_tests

Test file:

tests/domain/modeling/XQModelFaceServiceTest.cpp

Core scenarios:

XQModelFaceServiceValidatesFaceRecords
XQModelFaceServiceRenamesFaceWithUndoRedo
XQModelFaceServiceReclassifiesFaceWithCapId
XQModelFaceServiceCopiesModelFacesToMeshBoundaryRows
XQModelFaceServiceRejectsInvalidEdits

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_model_face_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQModelFaceService --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_model_face_service_tests
```

failed before implementation because src/domain/modeling/XQModelFaceService.cpp did not exist

## Acceptance

- Model face metadata survives load, edit, mesh generation, and save.
- Simulation setup can bind boundary conditions by face id.
- Mesh boundary transfer has a single source of truth.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If a feature identifies faces by display color, actor id, or list order, replace that logic with explicit face metadata.
