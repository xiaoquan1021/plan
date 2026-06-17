# XQPath

## Purpose

Define the vascular path payload used for centerline planning and downstream contour frame generation.

## Owns

Future source files:

```text
src/core/XQPath.h
src/core/XQPath.cpp
tests/core/XQPathTest.cpp
```

## Inputs

- Native `.pth` reader.
- Path planning feature.
- Centerline frame feature.

## Outputs

- A path object with control points, sampled curve points, tangents, and source image relation.

## Rules

- `XQPath` stores vascular path semantics, not only a VTK polyline.
- Control points and sampled points must remain distinguishable.
- Path coordinates are in project world space.
- SimVascular `.pth` data from `<acceptance-project>/Paths` must map directly into this payload.

## Data Contract

```text
PathId pathId
std::vector<PathControlPoint> controlPoints
std::vector<PathSamplePoint> samplePoints
PathInterpolation interpolation
double sampleSpacing
std::optional<XQNodeId> sourceImageNode
```

`PathSamplePoint` stores:

```text
position[3]
tangent[3]
normal[3]
binormal[3]
arcLength
```

## Implementation Contract

Public API surface:

```text
PathId
PathControlPoint
PathSamplePoint
PathInterpolation
XQPath
XQPath::controlPoints()
XQPath::samplePoints()
XQPath::resample(sampleSpacing)
XQPath::frameAtArcLength(arcLength)
```

Dependency boundary:

```text
allowed: XQ point/vector value types
not allowed publicly: VTK polydata, UI control point handles
```

## Step Plan

- [ ] Define control point and sample point structs.
- [ ] Define interpolation mode values for polyline and spline paths.
- [ ] Add path resampling operation under XQ algorithms, not under UI code.
- [ ] Add source relation to the image volume when available.
- [ ] Add tests for ordered control points and monotonic sample arc length.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQPath --output-on-failure
```

Required cases:

preserve control point order
resample a simple path with monotonic arc length
compute frame at a path position
bind source image node id
load every acceptance .pth file after PTH reader exists

## Acceptance

- Contour editing can ask the path for a frame at a path position.
- Path display can render control and sampled curves separately.
- Loading `.pth` files preserves names, point order, and path geometry.

## Failure Repair

If a contour feature recomputes path frames from unrelated UI state, move the frame source back through `XQPath` and the centerline frame document.
