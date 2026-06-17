# Lumen Contour Editing

## Purpose

Define 2D lumen contour creation and editing on path-normal image planes.

This document creates a pure domain contour service. It does not add screen event handling, Qt tool panels, VTK overlays, semi-automatic segmentation, or image sampling.

## Owns

Future source files:

```text
src/domain/contour/XQLumenContourService.h
src/domain/contour/XQLumenContourService.cpp
tests/domain/contour/XQLumenContourServiceTest.cpp
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Inputs

- `XQImageVolume`.
- `XQPath`.
- `XQContourGroup`.
- Centerline frames.
- Contour-plane points already converted from UI interaction.
- Command and undo.

## Outputs

- New or edited contours inside an `XQContourGroup`.
- Workflow commands that mutate `XQProject / XQScene / XQDataNode / XQContourGroup`.

## Rules

- Contours are edited in a 2D plane but stored in project world coordinates.
- Manual and semi-automatic contours share the same `XQContour` payload.
- Editing does not parse `.ctgr` files.
- A contour group stays linked to its source path.
- Domain service receives plane-space contour points, not screen pixels.
- Contour mutations are committed through `XQCommandStack` using XQ-owned commands.

## Functional Content

First-version behavior:

```text
create contour at selected path position
edit contour points
move, insert, and delete contour points
support circle, ellipse, polygon, and spline-like contours
copy contour to nearby path positions
show contour in MPR and 3D viewers
```

Implementation Contract covers:

```text
convert contour plane points to world-space points
convert world-space points back to contour plane points
create XQContour from XQCenterlineFrame and plane-space points
create a new XQContourGroup command with one contour
create PathToContourGroup XQScene source relation in the same undoable operation
add a contour to an existing XQContourGroup through ReplacePayloadCommand
replace points on an existing contour through ReplacePayloadCommand
move, insert, and delete individual contour points through ReplacePayloadCommand
preserve contour id, contour type, frame, path arc length, and source path binding during edits
```

## Implementation Contract

Implementation Contract owns:

```text
src/domain/contour/XQLumenContourService.h
src/domain/contour/XQLumenContourService.cpp
tests/domain/contour/XQLumenContourServiceTest.cpp
```

Small core payload extension:

```text
src/core/XQContourGroup.h
src/core/XQContourGroup.cpp
```

Public types:

```text
xq::ContourPlanePoint
xq::XQLumenContourService
```

Minimum public operations:

```text
frameFromCenterlineFrame(const XQCenterlineFrame&) -> ContourFrame
planeToWorld(const ContourFrame&, ContourPlanePoint) -> Point3
worldToPlane(const ContourFrame&, Point3) -> ContourPlanePoint
createContourFromPlanePoints(const XQCenterlineFrame&, std::vector<ContourPlanePoint>, ContourType, bool) -> XQContour
createContourGroupCommand(std::string, XQNodeId, XQContour) -> std::unique_ptr<XQCommand>
addContourCommand(const XQDataNode&, XQContour) -> std::unique_ptr<XQCommand>
replaceContourPointsCommand(const XQDataNode&, ContourId, std::vector<Point3>) -> std::unique_ptr<XQCommand>
moveContourPointCommand(const XQDataNode&, ContourId, std::size_t, Point3) -> std::unique_ptr<XQCommand>
insertContourPointCommand(const XQDataNode&, ContourId, std::size_t, Point3) -> std::unique_ptr<XQCommand>
deleteContourPointCommand(const XQDataNode&, ContourId, std::size_t) -> std::unique_ptr<XQCommand>
```

Core extension:

```text
XQContourGroup::contourById(const ContourId&) const -> const XQContour*
XQContourGroup::replaceContour(XQContour) -> bool
```

Command behavior:

```text
createContourGroupCommand returns AddNodeWithSourceRelationCommand for XQSceneGroup::Segmentations
createContourGroupCommand adds PathToContourGroup source relation during command execute
createContourGroupCommand undo removes the created source relation before removing the created contour group node
addContourCommand returns ReplacePayloadCommand with a copied and extended XQContourGroup
replaceContourPointsCommand returns ReplacePayloadCommand with a copied and edited XQContourGroup
moveContourPointCommand returns ReplacePayloadCommand with one point replaced
insertContourPointCommand returns ReplacePayloadCommand with one point inserted before the requested index
deleteContourPointCommand returns ReplacePayloadCommand with one point removed while preserving closed/open minimum point-count rules
```

Validation:

```text
manual closed contours require at least three points
contour group commands require XQDomainType::ContourGroup and XQContourGroup payload
source path id cannot be empty when creating a contour group
replaceContourPointsCommand rejects unknown contour ids
point-edit commands reject unknown contour ids and out-of-range point indexes
plane axes must be non-degenerate and orthonormal enough for projection
```

Forbidden behavior:

```text
do not depend on Qt, VTK, MITK, BlueBerry, CTK, or plugin APIs
do not keep authoritative contour geometry in viewer overlays
do not parse .ctgr files in the editor service
do not mutate XQScene directly from the service
```

## Step Plan

- [x] Treat UI output as contour-plane coordinates.
- [x] Convert contour-plane coordinates into world-space points.
- [x] Convert world-space points back into contour-plane coordinates.
- [x] Update `XQContourGroup` through commands.
- [x] Preserve contour method/type metadata.
- [x] Add tests for plane/world round-trip, command undo/redo, and validation.
- [x] Add point-level move/insert/delete contour edit commands.

## Test Plan

Test target:

xq_lumen_contour_service_tests

Test file:

tests/domain/contour/XQLumenContourServiceTest.cpp

Core scenarios:

XQLumenContourServiceRoundTripsPlaneAndWorldPoints
XQLumenContourServiceCreatesContourFromCenterlineFrame
XQLumenContourServiceCreatesContourGroupCommand
XQLumenContourServiceCreatesPathToContourGroupSourceRelationWithUndoRedo
XQLumenContourServiceAddsContourWithUndoRedo
XQLumenContourServiceReplacesContourPointsAndPreservesMetadata
XQLumenContourServiceMovesContourPointWithUndoRedo
XQLumenContourServiceInsertsContourPointWithUndoRedo
XQLumenContourServiceDeletesContourPointWithUndoRedo
XQLumenContourServiceRejectsInvalidContourEdits

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_lumen_contour_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQLumenContourService --output-on-failure
```

Expected result:

all lumen contour service tests pass

TDD red check:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_lumen_contour_service_tests
```

Observed expected failure before implementation:

Cannot find source file: src/domain/contour/XQLumenContourService.cpp

## Acceptance

- Loaded `.ctgr` contours and newly drawn contours use the same data model.
- The editor can create contours for the acceptance project's paths.
- Downstream lofting sees ordered contour data.
- initial contract can create and edit world-space `XQContour` payloads through commands without UI or rendering dependencies.

## Failure Repair

If contour editing keeps authoritative geometry in viewer overlays, move it into `XQContourGroup`.
