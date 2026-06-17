# XQContourGroup

## Purpose

Define the grouped 2D lumen contour payload attached to a vascular path.

## Owns

Future source files:

```text
src/core/XQContourGroup.h
src/core/XQContourGroup.cpp
tests/core/XQContourGroupTest.cpp
```

## Inputs

- Native `.ctgr` reader.
- Lumen contour editing feature.
- Contour lofting inputs feature.

## Outputs

- One contour group per vessel path or segmentation group.
- Ordered contours with path position, plane frame, contour type, and point list.

## Rules

- A contour group is an XQ payload, not a collection of view-only polylines.
- Each contour keeps its path association and local frame.
- Contour points are stored in world coordinates plus enough frame metadata to project into 2D editing space.
- SimVascular `.ctgr` files from `<acceptance-project>/Segmentations` must map into this payload.

## Data Contract

```text
ContourGroupId groupId
std::optional<XQNodeId> sourcePathNode
std::vector<XQContour> contours
ContourGroupLoftSettings loftSettings
```

`XQContour` stores:

```text
ContourId contourId
double pathArcLength
ContourFrame frame
ContourType type
std::vector<Point3> points
bool closed
```

Contour types:

```text
Manual
Circle
Ellipse
SplinePolygon
LevelSetResult
ThresholdResult
```

## Implementation Contract

Public API surface:

```text
ContourGroupId
ContourId
ContourFrame
ContourType
XQContour
XQContourGroup
XQContourGroup::contours()
XQContourGroup::orderedByPathPosition()
XQContourGroup::sourcePathNode()
```

Dependency boundary:

```text
allowed: XQ point/vector/frame value types
not allowed publicly: VTK actors, editor stroke objects, XML elements
```

## Step Plan

- [ ] Define contour group and contour value types.
- [ ] Define frame fields: origin, normal, x axis, y axis.
- [ ] Preserve contour type and method metadata from `.ctgr`.
- [ ] Add operations for contour ordering by path position.
- [ ] Add tests for loading multiple contours tied to one path.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQContourGroup --output-on-failure
```

Required cases:

create manual and ellipse contour records
sort contours by path arc length
round-trip contour frame projection values
bind source path node id
load Segmentations/*.ctgr after CTGR reader exists

## Acceptance

- The lofting feature receives an ordered contour list without reading XML.
- The editor can open a contour in its stored frame.
- The scene relation `ContourGroup -> Path` is explicit.

## Failure Repair

If contour points only exist as VTK actors or temporary editor strokes, move them into this payload before adding modeling logic.
