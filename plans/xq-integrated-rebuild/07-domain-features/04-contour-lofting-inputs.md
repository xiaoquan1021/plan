# Contour Lofting Inputs

## Purpose

Define how contour groups are prepared as clean, ordered input for surface model generation.

This document creates the input preparation service only. It does not generate surfaces, call modeling kernels, or mutate contour payloads.

## Owns

Future source files:

```text
src/domain/modeling/XQContourLoftInputBuilder.h
src/domain/modeling/XQContourLoftInputBuilder.cpp
tests/domain/modeling/XQContourLoftInputBuilderTest.cpp
```

## Inputs

- `XQContourGroup`.
- `XQPath`.
- Centerline frames.

The initial contract reads contour frames already stored in each `XQContour`. It does not require an active viewer, image plane, or surface modeling kernel.

## Outputs

- Loft input sections with consistent point count, orientation, and ordering.
- Diagnostics for contours that cannot be used for lofting.

## Rules

- Lofting input preparation is separate from UI editing.
- Input sections must be deterministic.
- The builder may resample contours, but it must preserve original contour data.
- Problems are returned as diagnostics, not hidden viewer behavior.
- The builder consumes XQ-owned contour payloads and emits XQ-owned value types only.
- Surface generation belongs to later modeling documents.

## Input Contract

Each section contains:

```text
pathArcLength
frame
closed point loop
resampled point loop
section normal
source contour id
```

## Implementation Contract

Implementation Contract owns:

```text
src/domain/modeling/XQContourLoftInputBuilder.h
src/domain/modeling/XQContourLoftInputBuilder.cpp
tests/domain/modeling/XQContourLoftInputBuilderTest.cpp
```

Public types:

```text
xq::XQContourLoftInputOptions
xq::XQContourLoftDiagnostic
xq::XQContourLoftSection
xq::XQContourLoftInput
xq::XQContourLoftInputBuilder
```

Minimum public operation:

```text
build(const XQContourGroup&, XQContourLoftInputOptions) -> XQContourLoftInput
```

Default options:

```text
targetPointCount = 64
minimumSectionCount = 2
```

Section semantics:

```text
sections are sorted by pathArcLength
closedPointLoop contains the contour loop without a duplicate closing endpoint
resampledPointLoop contains targetPointCount points sampled around the closed loop
sectionNormal equals normalized contour.frame.normal
sourceContourId equals contour.contourId
point orientation is counter-clockwise in contour.frame xAxis/yAxis coordinates; clockwise contours are reversed in output only
```

Diagnostics:

```text
non-closed contour
too few points
degenerate contour area
degenerate contour frame
not enough valid sections
invalid target point count
```

Forbidden behavior:

```text
do not mutate XQContourGroup or XQContour
do not call model lofting or meshing kernels
do not depend on Qt, VTK, MITK, BlueBerry, CTK, or plugin APIs
do not hide rejected contours in viewer-only state
```

## Step Plan

- [x] Sort contours by path arc length.
- [x] Ensure contours are closed.
- [x] Normalize point loop orientation relative to contour frame.
- [x] Resample loops to a consistent point count.
- [x] Return diagnostics for rejected contours and insufficient valid sections.
- [x] Add tests for ordering, orientation, point count, original data preservation, and missing/invalid contour handling.

## Test Plan

Test target:

xq_contour_loft_input_builder_tests

Test file:

tests/domain/modeling/XQContourLoftInputBuilderTest.cpp

Core scenarios:

XQContourLoftInputBuilderSortsSectionsByPathArcLength
XQContourLoftInputBuilderNormalizesClockwiseOrientation
XQContourLoftInputBuilderResamplesLoopsToTargetPointCount
XQContourLoftInputBuilderDoesNotMutateSourceContours
XQContourLoftInputBuilderReportsInvalidContours
XQContourLoftInputBuilderReportsInsufficientValidSections

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_contour_loft_input_builder_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQContourLoftInputBuilder --output-on-failure
```

Expected result:

all contour loft input builder tests pass

TDD red check:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_contour_loft_input_builder_tests
```

Observed expected failure before implementation:

Cannot find source file: src/domain/modeling/XQContourLoftInputBuilder.cpp

## Acceptance

- Model lofting receives clean ordered sections.
- Original contour points remain unchanged after loft input creation.
- Diagnostics identify which contour blocks modeling.
- initial contract emits deterministic loft input sections without external modeling or rendering dependencies.

## Failure Repair

If model lofting mutates contour data while preparing inputs, move preparation into this builder and keep source contours stable.
