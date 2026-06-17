# Model Lofting and Capping

## Purpose

Define surface model generation from contour lofting inputs and cap creation for vascular models.

This document must create an XQ-owned first geometry representation. It must not introduce VTK, OpenCASCADE, or a modeling-kernel object graph into business code.

## Owns

Current source-pass files:

```text
src/core/XQSurfaceModel.h
src/core/XQSurfaceModel.cpp
src/domain/modeling/XQModelingService.h
src/domain/modeling/XQModelingService.cpp
tests/domain/modeling/XQModelingServiceTest.cpp
```

## Inputs

- Contour lofting inputs.
- `XQSurfaceModel`.
- `XQContourLoftInput` built by `XQContourLoftInputBuilder`.
- Source contour-group node id.
- Modeling options owned by this service.

## Outputs

- A generated `XQSurfaceModel` linked to its source contour group.
- An XQ-owned triangle surface geometry handle.
- Stable `ModelFace` records for wall and optional inlet/outlet caps.
- Optional workflow command that adds the model node to `XQScene`.

## Rules

- Modeling service owns the algorithm sequence.
- initial contract uses XQ-owned triangulation only.
- VTK and OpenCASCADE may become later kernels behind XQ service APIs.
- Generated models must include model face metadata.
- Cap generation must create stable inlet, outlet, and wall face identities.
- Domain modeling must not depend on UI, plugin, MITK, VTK, OpenCASCADE, Eigen, or IO-layer model readers.
- The generated payload must be `XQSurfaceModel`, not an external-kernel wrapper.

## Functional Content

First-version behavior:

```text
loft ordered contour sections
stitch section surfaces
cap open boundaries
assign wall and cap face ids
preserve source contour relation
```

Implementation Contract covers:

```text
XQTriangleSurfaceGeometryHandle in core
side-wall triangle generation between adjacent contour sections
optional inlet/outlet fan caps
stable face metadata: wall face id 1, inlet face id 2, outlet face id 3
model-node command creation
ContourGroupToSurfaceModel source relation creation in the same undoable command
validation for section count, per-section point count, and source contour id
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Implementation Contract

Core additions:

```text
SurfaceTriangle
XQTriangleSurfaceGeometryHandle : SurfaceGeometryHandle
```

Public service types:

```text
XQModelingOptions
XQModelingService
```

Minimum public operations:

```text
createLoftedModel(const XQContourLoftInput&, XQNodeId, XQModelingOptions) -> std::shared_ptr<XQSurfaceModel>
createLoftedModelNodeCommand(std::string, const XQContourLoftInput&, XQNodeId, XQModelingOptions) -> std::unique_ptr<XQCommand>
```

Validation:

```text
source contour-group node id must not be empty
loft input must contain at least two sections
all sections must contain the same resampled point count
section point count must be at least three
cap generation requires the same validated section loops
```

## Step Plan

- [x] Add XQ-owned triangle surface geometry handle to core.
- [x] Accept loft input sections from the input builder.
- [x] Generate side-wall triangles from ordered sections.
- [x] Create inlet/outlet caps by fan triangulation when requested.
- [x] Assign stable wall, inlet, and outlet face ids.
- [x] Build `XQSurfaceModel` with geometry and face metadata.
- [x] Add command creation for model scene nodes.
- [x] Add tests for a simple bifurcation-free vessel, cap id assignment, command routing, and invalid inputs.

## Test Plan

Test target:

xq_modeling_service_tests

Test file:

tests/domain/modeling/XQModelingServiceTest.cpp

Core scenarios:

XQModelingServiceCreatesLoftedTriangleSurface
XQModelingServiceAssignsStableWallAndCapFaces
XQModelingServiceCreatesModelNodeCommand
XQModelingServiceCreatesContourGroupToSurfaceModelSourceRelationWithUndoRedo
XQModelingServiceRejectsInvalidLoftInputs

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_modeling_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQModelingService --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_modeling_service_tests
```

failed before implementation because src/domain/modeling/XQModelingService.cpp did not exist

## Acceptance

- A contour group can produce a surface model without UI-specific state.
- Generated face metadata is immediately usable by meshing and simulation setup.
- The service can later swap internal kernels without changing XQ payloads.
- The initial contract produces an XQ-owned geometry handle, not a VTK/OCCT wrapper.

## Failure Repair

If generated caps exist only as VTK cell arrays without `ModelFace` records, repair this service and `XQSurfaceModel`.
