# Path Planning

## Purpose

Define interactive vascular path creation, editing, loading, and resampling.

This document creates the domain service contract only. Qt tool panels, mouse interactors, VTK mappers, and rendering are deferred until the owning workbench/visualization documents are ready for runtime UI code.

## Owns

Future source files:

```text
src/domain/path/XQPathPlanningService.h
src/domain/path/XQPathPlanningService.cpp
tests/domain/path/XQPathPlanningServiceTest.cpp
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Inputs

- `XQImageVolume`.
- `XQPath`.
- MPR viewers.
- Command and undo.

## Outputs

- New or edited `XQPath` nodes linked to a source image.
- Workflow commands that mutate `XQProject / XQScene / XQDataNode / XQPath`.

## Rules

- Path planning is an integrated domain service, not a plugin tool.
- UI collects user intent; service computes path changes.
- Path geometry is stored in `XQPath`.
- Path mutations are committed through `XQCommandStack` using XQ-owned commands.
- MPR click positions enter this service as world-space `Point3` values; this document does not own Qt/VTK event conversion.
- SimVascular is a functional reference for vascular path semantics, not a source-code migration source.

## Functional Content

First-version behavior:

```text
create path from control points
insert, move, and delete control points
resample path at a chosen spacing
compute tangent and local frame samples
bind path to source image
show path in MPR and 3D viewers
```

Implementation Contract covers:

```text
create path command from control points
insert, move, and delete control points through replacement commands
resample path at a chosen spacing
compute tangent and local frame samples through XQPath::resample
bind path payload to source image node id
create ImageToPath XQScene source relation in the same undoable operation
```

## Implementation Contract

Implementation Contract owns:

```text
src/domain/path/XQPathPlanningService.h
src/domain/path/XQPathPlanningService.cpp
tests/domain/path/XQPathPlanningServiceTest.cpp
```

Public class:

```text
xq::XQPathPlanningService
```

Minimum public operations:

```text
createPathCommand(std::string, XQNodeId, std::vector<PathControlPoint>, double) -> std::unique_ptr<XQCommand>
moveControlPointCommand(const XQDataNode&, std::size_t, Point3, double) -> std::unique_ptr<XQCommand>
insertControlPointCommand(const XQDataNode&, std::size_t, PathControlPoint, double) -> std::unique_ptr<XQCommand>
deleteControlPointCommand(const XQDataNode&, std::size_t, double) -> std::unique_ptr<XQCommand>
resamplePathCommand(const XQDataNode&, double) -> std::unique_ptr<XQCommand>
```

Command behavior:

```text
createPathCommand returns AddNodeWithSourceRelationCommand for XQSceneGroup::Paths
createPathCommand adds ImageToPath source relation during command execute
createPathCommand undo removes the created source relation before removing the created path node
edit and resample operations return ReplacePayloadCommand
created and edited payloads are std::shared_ptr<XQPath>
created payloads store sourceImageNode
edited payloads preserve existing path id and sourceImageNode by copying the old XQPath payload
all committed changes pass through XQCommandStack
```

Validation:

```text
path creation requires at least two control points
path creation requires positive sample spacing
editing requires a node with XQDomainType::Path and XQPath payload
move/delete indices must exist
insert index may equal control point count
delete must leave at least two control points
```

Forbidden behavior:

```text
do not add Qt, VTK, MITK, BlueBerry, CTK, or plugin dependencies
do not mutate XQScene directly from the service
do not store path geometry in UI state
do not read old XQ source as migration code
```

## Step Plan

- [x] Define service operations for create, edit, delete, and resample.
- [x] Treat MPR click positions as world-space `Point3` service inputs.
- [x] Return path edits as workflow commands.
- [x] Generate sampled path points and frame hints.
- [x] Add tests for control point editing, resampling, undo, and validation.

## Test Plan

Test target:

xq_path_planning_service_tests

Test file:

tests/domain/path/XQPathPlanningServiceTest.cpp

Core scenarios:

XQPathPlanningServiceCreatesPathCommandBoundToSourceImage
XQPathPlanningServiceCreatesImageToPathSourceRelationWithUndoRedo
XQPathPlanningServiceMovesControlPointWithUndoRedo
XQPathPlanningServiceInsertsAndDeletesControlPoints
XQPathPlanningServiceResamplesExistingPath
XQPathPlanningServiceRejectsInvalidPathEdits

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_path_planning_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQPathPlanningService --output-on-failure
```

Expected result:

all path planning service tests pass

TDD red check:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_path_planning_service_tests
```

Observed expected failure before implementation:

Cannot find source file: src/domain/path/XQPathPlanningService.cpp

## Acceptance

- A user can create a path from an image volume.
- Loaded `.pth` paths and newly created paths share the same payload.
- Contour editing can consume the path without reading UI state.
- initial contract can create and edit `XQPath` through commands without Qt/VTK dependencies.

## Failure Repair

If path planning requires a separate tool registry or plugin action system, repair this document and keep the service under the integrated workflow.
