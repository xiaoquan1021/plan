# 3D Segmentation

## Purpose

Define first-version 3D segmentation operations for deriving surfaces or masks from image volumes.

This document creates XQ-owned mask segmentation infrastructure only. The visualization layer now derives disposable VTK 3D render products and XQ-owned MPR alpha overlay rasters from masks, including exposed voxel faces, volume props, smoothed/decimated extracted surface actors, and deterministic slice overlays; native project IO persists masks through XQ-owned `.xqmask` XML files; domain segmentation still does not introduce ITK, VTK, widget overlays, or persisted surface extraction.

## Owns

Current source files:

```text
src/core/XQImageVolume.h
src/core/XQImageVolume.cpp
src/core/XQPayload.h
src/core/XQDataNode.h
src/core/XQDataNode.cpp
src/core/XQScene.cpp
src/core/XQSegmentationMask.h
src/core/XQSegmentationMask.cpp
src/domain/segmentation/XQSegmentationService.h
src/domain/segmentation/XQSegmentationService.cpp
tests/domain/segmentation/XQSegmentationServiceTest.cpp
```

## Inputs

- `XQImageVolume`.
- Core-owned in-memory scalar image buffer.

ITK and VTK remain later algorithm kernels behind XQ-owned interfaces. They are not introduced in this document.

## Outputs

- `XQSegmentationMask` payloads.
- Optional workflow commands that add mask nodes to `XQScene`.

## Rules

- ITK may become an algorithm kernel behind `XQSegmentationService`, but initial contract uses XQ-owned code only.
- Segmentation output must become XQ scene data before visualization.
- Mask data and generated surface data must preserve source image relation.
- First version focuses on practical vascular workflow support, not a full segmentation suite.
- Domain segmentation must not depend on IO-layer decoded buffer classes.
- Surface extraction belongs to the later modeling/surface extraction pass.

## Functional Content

First-version operations:

```text
threshold segmentation
region-growing seed segmentation
connected component cleanup
binary morphology cleanup
surface extraction by marching cubes or equivalent VTK algorithm
```

Implementation Contract covers:

```text
core-owned XQMemoryImageBufferHandle for synthetic or decoded scalar buffers
XQSegmentationMask payload
threshold mask creation
seeded 6-connected region growing inside a threshold range
largest connected component cleanup
mask node command creation
undoable ImageToSegmentationMask scene source relation creation for masks that
carry a source image node id
SegmentationMask domain registration in XQPayload/XQDataNode/XQScene
3D presentation row category for segmentation masks
3D scene viewer disposable exposed-face surface, volume, and smoothed/decimated extracted surface render products for masks
MPR viewer XQ-owned segmentation mask alpha overlay raster for active slices
native project writer/reader `.xqmask` persistence for mask geometry, source image id, and active voxels
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Implementation Contract

Implementation Contract owns:

```text
src/core/XQImageVolume.h
src/core/XQSegmentationMask.h
src/core/XQSegmentationMask.cpp
src/domain/segmentation/XQSegmentationService.h
src/domain/segmentation/XQSegmentationService.cpp
tests/domain/segmentation/XQSegmentationServiceTest.cpp
```

Small core extensions:

```text
XQDomainType::SegmentationMask
XQMemoryImageBufferHandle
makeSegmentationMaskNode(...)
groupForDomain(XQDomainType::SegmentationMask) -> XQSceneGroup::Segmentations
```

Public types:

```text
xq::XQSegmentationMask
xq::XQMemoryImageBufferHandle
xq::XQSegmentationThresholdParameters
xq::XQRegionGrowingParameters
xq::XQSegmentationService
```

Minimum public operations:

```text
thresholdMask(const XQImageVolume&, XQSegmentationThresholdParameters) -> std::shared_ptr<XQSegmentationMask>
regionGrowMask(const XQImageVolume&, XQRegionGrowingParameters) -> std::shared_ptr<XQSegmentationMask>
keepLargestConnectedComponent(const XQSegmentationMask&) -> std::shared_ptr<XQSegmentationMask>
createMaskNodeCommand(std::string, std::shared_ptr<XQSegmentationMask>) -> std::unique_ptr<XQCommand>
```

Validation:

```text
input image must have one component
input image must provide XQMemoryImageBufferHandle
buffer byte count must match image dimensions and scalar type
threshold lower value must be <= upper value
region growing seed must be inside image extent
cleanup on an empty mask returns an empty mask with preserved geometry/source id
```

Forbidden behavior:

```text
do not depend on ITK, VTK, Qt, MITK, BlueBerry, CTK, or plugin APIs
do not depend on io/image DecodedImageBufferHandle from domain code
do not create surface models in this document
do not store segmentation mask state only in viewer overlays
```

## Step Plan

- [x] Define segmentation parameter structs.
- [x] Add XQ-owned segmentation mask payload and memory scalar image buffer.
- [x] Implement threshold mask creation.
- [x] Implement seed-based region growing.
- [x] Implement largest connected component cleanup.
- [x] Add command creation for mask scene nodes.
- [x] Add undoable ImageToSegmentationMask source relation creation for mask
  scene nodes with a source image id.
- [x] Add tests on synthetic image volumes.
- [x] Register `SegmentationMask` as an XQ scene domain under `XQSceneGroup::Segmentations`.
- [x] Add first 3D presentation category for mask nodes without introducing VTK actors.
- [x] Add first 3D scene viewer mask surface and volume render products without introducing VTK into domain code.
- [x] Add first 3D scene viewer mask smoothed/decimated extracted surface render product without introducing VTK into domain code.
- [x] Add first MPR mask alpha overlay raster without introducing VTK or Qt into domain code.
- [x] Prevent native project save from silently dropping mask nodes before `.xqmask` persistence exists.
- [x] Add first native `.xqmask` writer/reader for mask geometry, source image id, and active voxels.

## Test Plan

Test target:

xq_segmentation_service_tests

Test file:

tests/domain/segmentation/XQSegmentationServiceTest.cpp

Core scenarios:

XQSegmentationServiceCreatesThresholdMaskFromMemoryImage
XQSegmentationServiceRegionGrowsConnectedVoxelsFromSeed
XQSegmentationServiceKeepsLargestConnectedComponentWithoutMutatingSource
XQSegmentationServiceCreatesMaskNodeCommand
XQSegmentationServiceCreatesImageToSegmentationMaskSourceRelationWithUndoRedo
XQSegmentationServiceRejectsUnsupportedInputs

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_segmentation_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQSegmentationService --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_segmentation_service_tests
```

failed before implementation because src/domain/segmentation/XQSegmentationService.cpp did not exist

XQSegmentationServiceCreatesImageToSegmentationMaskSourceRelationWithUndoRedo
failed before implementation because XQRelationKind did not include
ImageToSegmentationMask and createMaskNodeCommand used AddNodeCommand without a
source relation.

## Acceptance

- Segmentation outputs can preserve an optional source image node id.
- Mask-node commands create an undoable ImageToSegmentationMask XQScene source
  relation when the mask carries a source image node id.
- initial contract can add mask outputs to `XQScene` through commands.
- `XQSegmentationMask` is an XQ-owned payload, not a viewer overlay or external-library object.
- ITK and VTK types do not appear in workflow or UI public APIs.
- Native project save/reopen preserves first-pass mask geometry, source image relation, and active voxels through `.xqmask`.

## Failure Repair

If segmentation parameters become ad hoc UI fields with no domain struct, define the struct here and route the panel through the service.
