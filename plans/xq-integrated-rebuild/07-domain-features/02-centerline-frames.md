# Centerline Frames

## Purpose

Define computation of stable local frames along a vascular path for contour placement, oblique slicing, and lofting.

This document creates a pure domain geometry service. It does not add viewer code, oblique reslice widgets, contour editors, or lofting consumers.

## Owns

Future source files:

```text
src/domain/path/XQCenterlineFrameService.h
src/domain/path/XQCenterlineFrameService.cpp
tests/domain/path/XQCenterlineFrameServiceTest.cpp
```

## Inputs

- `XQPath`.
- Existing `Point3`, `Vector3`, and vector helpers from `XQCoreTypes`.
- Optional preferred initial normal.

Eigen is not introduced in this document. Add Eigen only if later algorithms need matrix decomposition or numerical routines that exceed `XQCoreTypes`.

## Outputs

- Frame samples with origin, tangent, normal, binormal, and arc length.

## Rules

- Frame generation is algorithmic domain code, not viewer code.
- Frames are computed from `XQPath` and optional image orientation.
- Avoid sudden normal flips along the path.
- Store enough frame metadata for contour editing and contour file round-trip.
- Do not compute frames independently inside contour, viewer, or lofting tools.

## Frame Contract

```text
origin
tangent
normal
binormal
arcLength
pathPointIndex
```

## Implementation Contract

Implementation Contract owns:

```text
src/domain/path/XQCenterlineFrameService.h
src/domain/path/XQCenterlineFrameService.cpp
tests/domain/path/XQCenterlineFrameServiceTest.cpp
```

Public types:

```text
xq::XQCenterlineFrame
xq::XQCenterlineFrameOptions
xq::XQCenterlineFrameService
```

Minimum public operation:

```text
computeFrames(const XQPath&, XQCenterlineFrameOptions) -> std::vector<XQCenterlineFrame>
```

Frame semantics:

```text
one frame is emitted per XQPath sample point
tangent is normalized from sample tangent
initial normal is the preferred normal projected onto the tangent plane, or a stable world-axis fallback
subsequent normals are propagated by projecting the previous normal onto the next tangent plane
if projection degenerates, previous binormal or a stable world-axis fallback is used
normal and binormal are re-orthogonalized
normal and binormal are flipped when needed to keep consecutive normals aligned
pathPointIndex equals the sample point index
```

Validation:

```text
XQPath must contain at least one sample point
zero-length sample tangent is rejected
degenerate preferred normal falls back instead of failing
```

Forbidden behavior:

```text
do not depend on Qt, VTK, MITK, BlueBerry, CTK, or plugin APIs
do not store frame state in viewer widgets
do not add Eigen for this initial contract
```

## Step Plan

- [x] Normalize path sample tangents.
- [x] Compute initial normal from preferred normal or a stable world axis.
- [x] Propagate frames along path with minimal twist.
- [x] Re-orthogonalize frame axes.
- [x] Add tests for straight, curved, and near-axis-aligned paths.

## Test Plan

Test target:

xq_centerline_frame_service_tests

Test file:

tests/domain/path/XQCenterlineFrameServiceTest.cpp

Core scenarios:

XQCenterlineFrameServiceComputesOrthonormalStraightFrames
XQCenterlineFrameServiceUsesPreferredInitialNormal
XQCenterlineFrameServiceAvoidsNormalFlipsOnCurvedPath
XQCenterlineFrameServiceHandlesNearAxisAlignedPath
XQCenterlineFrameServiceRejectsUnsampledPath

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_centerline_frame_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQCenterlineFrameService --output-on-failure
```

Expected result:

all centerline frame service tests pass

TDD red check:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_centerline_frame_service_tests
```

Observed expected failure before implementation:

Cannot find source file: src/domain/path/XQCenterlineFrameService.cpp

## Acceptance

- Contour planes are stable as the user moves along a path.
- Oblique MPR uses the same frame contract as contour editing.
- Lofting receives ordered frames with matching contour positions.
- initial contract can produce orthonormal, low-flip frames from XQ-owned path samples without external math dependencies.

## Failure Repair

If different tools compute incompatible frames, consolidate them into this service.
