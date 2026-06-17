# MPR Viewers

## Purpose

Define axial, sagittal, coronal, and oblique medical image viewers for path and contour workflows.

Earlier implementation work created the XQ-owned slice controller and deterministic slice raster contracts for decoded image buffers, segmentation mask alpha overlays, path alpha overlays, contour alpha overlays, and contour hit testing. The current contract adds the first Qt/VTK-backed MPR widget that consumes the controller/raster contract, writes grayscale rasters plus segmentation-mask/path/contour overlays into disposable VTK image display products, and keeps image geometry, slice state, and payload data owned by XQ domain objects.
It also exposes a narrow widget-level slice-pixel to world-position bridge so workbench code can feed active MPR tool positions without giving the viewer ownership of contour edits.
The current contour hit-test result also reports an optional contour point index for endpoint hits and an optional insert-before point index for edge hits, so contour-edit commands can distinguish point drags, edge insertions, and non-mutating misses without moving edit ownership into Qt/VTK.
Those lightweight hit-test fields can now be consumed by the workbench tool-panel host and the four-pane MPR mouse/key bridge to same-pane drag selected contour points, Ctrl+left or left-double-click insert contour edge points, Delete the last selected endpoint through command-stack routes only outside open-draft addingContour state, and Escape/right-click-cancel the pending endpoint hit before deletion.
The four-pane bridge also contains failed endpoint-drag command dispatch and cross-pane endpoint-drag cancellation at the UI event boundary, so a missing command context, stale selection, or pointer move into a different MPR pane does not throw through native Qt event processing or mutate contour payloads unexpectedly.
This pass also adds first MPR window/level display state to the XQ-owned slice controller contract, so grayscale rasterization can use caller-selected center/width values before falling back to image payload intensity ranges.
The four-pane Qt bridge now maps unmodified right-button MPR drags into shared XQ-owned MPR window/level updates while leaving active tool-position and contour edit ownership untouched; unmodified right-button presses also clear pending endpoint hits before Delete/Backspace can remove a previously selected point.

## Owns

Source files:

```text
src/visualization/XQSliceController.h
src/visualization/XQSliceController.cpp
src/visualization/XQMprSliceRasterizer.h
src/visualization/XQMprSliceRasterizer.cpp
src/visualization/XQMprViewWidget.h
src/visualization/XQMprViewWidget.cpp
tests/visualization/XQSliceControllerTest.cpp
tests/visualization/XQMprSliceRasterizerTest.cpp
tests/visualization/XQMprViewWidgetTest.cpp
```

## Inputs

- `XQImageVolume`.
- `XQPath`, `XQContourGroup`, and `XQSegmentationMask` display overlays.
- Four-pane layout and crosshair controller.
- VTK dependency role.
- Decoded image buffers from VTI, DICOM, NIfTI, NRRD, MetaImage, TIFF, or core memory-backed image payloads.

## Outputs

- Slice views that display image volume, paths, contour frames, and editable contours.
- First-pass XQ-owned grayscale slice raster for active decoded images.
- First-pass XQ-owned MPR window/level state and grayscale raster mapping from window center/width.
- First-pass native MPR right-button drag bridge that adjusts shared window/level state through `XQFourPaneLayout`.
- First-pass XQ-owned segmentation mask alpha overlay raster for active image slices.
- First-pass XQ-owned path alpha overlay raster for active image slices.
- First-pass XQ-owned contour alpha overlay raster and pixel hit-test result for active image slices and contour-edit planes.
- First-pass XQ-owned path-normal and contour-edit plane state contracts, with deterministic path-normal oblique grayscale, path overlay, segmentation-mask overlay, contour overlay reslicing, and contour hit-test support plus contour-edit contour overlay and hit-test support, plus same-pane endpoint contour drag, cross-pane endpoint-drag cancellation, Ctrl+left edge insertion, left-double-click edge insertion, Delete/Backspace endpoint removal after endpoint-drag release, Delete/Backspace open-draft endpoint-delete suppression, movingPoint right-click drag preservation, Escape/right-click endpoint-hit cancellation, contour-edit blank-click, Ctrl+left blank-click, ProfileGroupInteraction-style AddPointClick ready orthogonal blank-click draft creation, ProfileGroupInteraction-style AddPointClick ordinary orthogonal open-draft endpoint/edge-hit draft point append, and contour-edit ProfileGroupInteraction-style Ctrl+left open-draft endpoint/edge-hit draft point append, contour-edit/ordinary orthogonal Return draft-contour finish, Escape draft-contour cancellation, and Escape/Return endpoint-selection draft-preservation bridges while broader contour-edit interaction modes remain deferred.
- First-pass Qt/VTK MPR widget that displays the XQ-owned grayscale raster and segmentation-mask/path/contour overlays through disposable VTK image data and image actor products.

## Rules

- Viewers consume `XQImageVolume` geometry and buffer handles.
- Viewers do not own image, path, or contour data.
- Viewer state stores camera, slice, window/level, and interaction mode only.
- VTK is used for rendering and slicing internals.
- Crosshair and linked-view state are owned by the four-pane layout controllers.
- Core controller/raster source files avoid VTK and Qt types and expose XQ-owned geometry/raster state only.
- The MPR widget may use Qt and VTK internally but must consume `XQSliceController` and `XQMprSliceRasterizer` rather than owning slice geometry or image payloads.
- Rasterization may consume contiguous XQ-owned decoded image buffers but must return a diagnostic for non-contiguous or unsupported image handles.
- Mask overlay rasterization consumes `XQSegmentationMask` only when its image geometry matches the active image geometry.

## Viewer Modes

```text
axial
sagittal
coronal
path-normal oblique
contour-edit plane
```

## Implementation Contract

Implementation Contract owns:

```text
src/visualization/XQSliceController.h
src/visualization/XQSliceController.cpp
src/visualization/XQMprSliceRasterizer.h
src/visualization/XQMprSliceRasterizer.cpp
src/visualization/XQMprViewWidget.h
src/visualization/XQMprViewWidget.cpp
tests/visualization/XQSliceControllerTest.cpp
tests/visualization/XQMprSliceRasterizerTest.cpp
tests/visualization/XQMprViewWidgetTest.cpp
```

Public class:

```text
xq::XQSliceController
xq::XQMprSliceRasterizer
xq::XQMprViewWidget
```

Public enum:

```text
xq::SliceOrientation
```

Minimum public operations:

```text
setImage(std::shared_ptr<const XQImageVolume>)
clearImage()
image()
setOrientation(SliceOrientation)
orientation()
setPathNormalPlane(XQSlicePlane)
setContourEditPlane(XQSlicePlane)
explicitPlane()
setSliceIndex(double)
sliceIndex()
setWindowLevel(double center, double width)
clearWindowLevel()
windowLevel()
setCrosshairWorldPosition(Point3)
crosshairWorldPosition()
crosshairVoxelIndex()
sliceNormal()
sliceOrigin()
clampSliceIndex()
XQMprSliceRasterizer::rasterize(const XQSliceController&) -> XQMprSliceRasterResult
XQMprSliceRasterizer::rasterizeMaskOverlay(const XQSliceController&, const XQSegmentationMask&) -> XQMprSliceMaskOverlayResult
XQMprSliceRasterizer::rasterizePathOverlay(const XQSliceController&, const XQPath&) -> XQMprSlicePathOverlayResult
XQMprSliceRasterizer::rasterizeContourOverlay(const XQSliceController&, const XQContourGroup&) -> XQMprSliceContourOverlayResult
XQMprSliceRasterizer::hitTestContourOverlay(const XQSliceController&, const XQContourGroup&, int column, int row, double tolerancePixels) -> XQMprSliceContourHitTestResult
XQMprViewWidget::setSliceController(XQSliceController*)
XQMprViewWidget::sliceController()
XQMprViewWidget::setSegmentationMaskOverlay(const XQSegmentationMask*)
XQMprViewWidget::setPathOverlay(const XQPath*)
XQMprViewWidget::setContourOverlay(const XQContourGroup*)
XQMprViewWidget::syncFromSliceController() -> XQMprViewRenderResult
XQMprViewWidget::renderFromSliceController() -> XQMprViewRenderResult
XQMprViewWidget::lastRenderResult()
XQMprViewWidget::worldPositionForSlicePixel(int column, int row) -> std::optional<Point3>
XQMprViewWidget::hitTestContourOverlayAtSlicePixel(int column, int row, double tolerancePixels) -> XQMprSliceContourHitTestResult
XQMprViewWidget::vtkWidget()
XQMprViewWidget::nativeRenderer()
XQMprViewWidget::displayImageData()
XQMprViewWidget::displayImageActor()
XQMprViewWidget::displayMaskOverlayData()
XQMprViewWidget::displayMaskOverlayActor()
XQMprViewWidget::displayPathOverlayData()
XQMprViewWidget::displayPathOverlayActor()
XQMprViewWidget::displayContourOverlayData()
XQMprViewWidget::displayContourOverlayActor()
```

Raster result contract:

```text
XQMprSliceRasterImage
  width
  height
  grayscale8 row-major pixels

XQMprSliceRasterDiagnostic
  message

XQMprSliceRasterResult
  bool valid
  optional raster image
  diagnostics

XQMprSliceMaskOverlay
  width
  height
  alpha8 row-major pixels

XQMprSliceMaskOverlayResult
  bool valid
  optional mask overlay image
  diagnostics

XQMprSlicePathOverlay
  width
  height
  alpha8 row-major pixels

XQMprSlicePathOverlayResult
  bool valid
  optional path overlay image
  diagnostics

XQMprSliceContourOverlay
  width
  height
  alpha8 row-major pixels

XQMprSliceContourOverlayResult
  bool valid
  optional contour overlay image
  diagnostics

XQMprSliceContourHit
  contour id
  distancePixels
  optional pointIndex
  optional insertBeforePointIndex

XQMprSliceContourHitTestResult
  bool valid
  optional contour hit
  diagnostics

XQMprViewRenderResult
  bool valid
  width
  height
  bool renderRequested
  diagnostics
```

Owned state:

```text
shared_ptr<const XQImageVolume>
SliceOrientation
slice index on the active orientation axis
optional explicit path-normal or contour-edit slice plane
optional MPR window/level display state
world crosshair point
row-major grayscale slice pixels derived from XQ-owned image buffers and optional MPR window/level state
row-major alpha overlay pixels derived from XQSegmentationMask
row-major alpha overlay pixels derived from XQPath sample/control points
row-major alpha overlay pixels and hit-test ids derived from XQContourGroup contour points
non-owning XQSliceController pointer in the Qt/VTK widget
disposable VTK image data and image actor products derived from the current raster result
```

Forbidden ownership:

```text
image voxel buffer ownership
path or contour payload copies
segmentation mask payload copies
independent slice geometry inside the Qt/VTK widget
path, contour, or segmentation mask payload ownership inside the Qt/VTK widget
```

Dependency boundary:

```text
No VTK or Qt symbols are required by the controller/rasterizer source files.
`XQMprViewWidget` uses Qt/VTK internally but keeps `XQSliceController` and `XQMprSliceRasterizer` as the XQ-owned state and deterministic pixel-test boundary.
```

## Step Plan

- [x] Create a slice controller that maps world and image coordinates.
- [x] Render the active decoded `XQImageVolume` into an XQ-owned grayscale slice raster.
- [x] Add optional MPR window/level display state and use it during grayscale rasterization.
- [x] Render a matching `XQSegmentationMask` into an XQ-owned slice alpha overlay raster.
- [x] Add path overlay rendering.
- [x] Add contour overlay rendering and hit testing.
- [x] Add old XQ `xq_ProfileRenderer2D`-style contour frame-plane culling for overlay rasterization and hit testing.
- [x] Add first-pass path-normal oblique and contour-edit plane state to the slice controller.
- [x] Add deterministic nearest-neighbor path-normal oblique grayscale reslicing from XQ-owned image buffers.
- [x] Add deterministic path overlay projection on path-normal oblique slice planes.
- [x] Add diagnostics that reject remaining non-orthogonal overlays and contour-edit rasters until expanded oblique reslice/edit support exists.
- [x] Expose MPR widget slice-pixel to world-position conversion for orthogonal, path-normal, and contour-edit planes.
- [x] Bridge native right-button MPR drags to shared four-pane MPR window/level state without changing active tool positions.
- [x] Bridge native right-button MPR presses to pending endpoint-hit cancellation without changing active tool positions or blocking window/level drag setup.
- [x] Add ProfileGroupInteraction-style SelectPointClick 4.0 endpoint-selection tolerance fallback while preserving the 1.0 edge-edit hit guard.
- [x] Expose slice and world-position updates to `XQCrosshairController`.
- [x] Add tests for coordinate transforms using synthetic image geometry.
- [x] Add tests for axial, sagittal, and coronal grayscale rasterization using synthetic decoded image buffers.
- [x] Add a negative test for active images without decoded contiguous voxel buffers.
- [x] Add a Qt/VTK MPR view widget that consumes `XQSliceController` and `XQMprSliceRasterizer`.
- [x] Add tests for non-owning controller binding, VTK image-data pixels, native render request reporting, segmentation/path/contour overlay compositing, and invalid-raster cleanup.

## Test Plan

Test target:

xq_visualization_tests
xq_mpr_slice_rasterizer_tests
xq_mpr_view_widget_tests

Test file:

tests/visualization/XQSliceControllerTest.cpp
tests/visualization/XQMprSliceRasterizerTest.cpp
tests/visualization/XQMprViewWidgetTest.cpp

Core scenarios:

XQSliceControllerComputesAxialSliceOriginAndNormal
XQSliceControllerComputesSagittalAndCoronalNormals
XQSliceControllerStoresPathNormalObliquePlane
XQSliceControllerStoresContourEditPlane
XQSliceControllerMapsWorldCrosshairToVoxelIndex
XQSliceControllerClampsSliceIndexToImageExtent
XQSliceControllerStoresAndClearsWindowLevel
XQSliceControllerRejectsSliceOperationsWithoutImage
XQMprSliceRasterizerRendersAxialSliceFromMemoryImage
XQMprSliceRasterizerRendersSagittalAndCoronalSlices
XQMprSliceRasterizerRendersUInt8SliceUsingComputedRange
XQMprSliceRasterizerRendersSliceUsingWindowLevel
XQMprSliceRasterizerRendersInt16SliceUsingSignedRange
XQMprSliceRasterizerRejectsImagesWithoutDecodedBuffer
XQMprSliceRasterizerRendersSegmentationMaskOverlayForActiveSlice
XQMprSliceRasterizerRendersPathOverlayForActiveSlice
XQMprSliceRasterizerRendersContourOverlayForActiveSlice
XQMprSliceRasterizerRendersPathNormalObliqueRasterFromExplicitPlane
XQMprSliceRasterizerRendersPathOverlayOnPathNormalObliquePlane
XQMprSliceRasterizerRendersSegmentationMaskOverlayOnPathNormalObliquePlane
XQMprSliceRasterizerRendersContourOverlayOnPathNormalObliquePlane
XQMprSliceRasterizerRejectsPathNormalObliquePathOverlayWithoutPixelSpacing
XQMprSliceRasterizerRendersContourOverlayOnContourEditPlane
XQMprSliceRasterizerSkipsContourOverlayWhenFramePlaneDoesNotMatchActiveSlice
XQMprSliceRasterizerRejectsContourEditOverlayWithoutOutputDimensions
XQMprSliceRasterizerHitTestsContourOverlayInSlicePixels
XQMprSliceRasterizerHitTestsContourEdgeInsertIndexInSlicePixels
XQMprSliceRasterizerHitTestsContourPointIndexInSlicePixels
XQMprSliceRasterizerHitTestsContourOverlayOnContourEditPlane
XQMprSliceRasterizerHitTestsContourOverlayOnPathNormalObliquePlane
XQMprSliceRasterizerSkipsContourHitWhenFramePlaneDoesNotMatchActiveSlice
XQMprSliceRasterizerHitTestsContourEdgeInsertIndexOnContourEditPlane
XQMprSliceRasterizerHitTestsContourPointIndexOnContourEditPlane
XQFourPaneLayoutWidgetSelectsEndpointWithinOldProfileGroupTolerance
XQMprViewWidgetOwnsNativeQvtkWidgetAndRendererBridge
XQMprViewWidgetBindsSliceControllerWithoutOwningImage
XQMprViewWidgetRendersRasterizedSliceIntoVtkImageData
XQMprViewWidgetRendersSegmentationMaskOverlayIntoVtkImageData
XQMprViewWidgetRendersPathOverlayIntoVtkImageData
XQMprViewWidgetRendersContourOverlayIntoVtkImageData
XQMprViewWidgetRendersPathNormalObliqueSliceIntoVtkImageData
XQMprViewWidgetRendersPathOverlayOnPathNormalObliqueSliceIntoVtkImageData
XQMprViewWidgetRendersSegmentationMaskOverlayOnPathNormalObliqueSliceIntoVtkImageData
XQMprViewWidgetRendersContourOverlayOnPathNormalObliqueSliceIntoVtkImageData
XQMprViewWidgetRendersContourOverlayOnContourEditSliceIntoVtkImageData
XQMprViewWidgetMapsSlicePixelToWorldPosition
XQMprViewWidgetMapsContourEditSlicePixelToWorldPosition
XQMprViewWidgetClearsDisplayAndReportsDiagnosticForInvalidRaster

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_visualization_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQSliceController --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_mpr_slice_rasterizer_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQMprSliceRasterizer --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_mpr_view_widget_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQMprViewWidget --output-on-failure
```

Expected result:

all slice controller tests pass without requiring VTK
all MPR slice rasterizer tests pass without requiring VTK or Qt
all MPR view widget tests pass while using Qt/VTK only inside the visualization widget layer

## Acceptance

- The acceptance VTI image can be viewed in orthogonal slices.
- Decoded image payloads can produce deterministic orthogonal grayscale rasters through XQ-owned contracts.
- Optional MPR window/level state can be stored in `XQSliceController` without moving image ownership out of `XQImageVolume`.
- MPR grayscale rasterization can map decoded scalar values through caller-selected window center/width values.
- Segmentation mask payloads can produce deterministic orthogonal alpha overlay rasters through XQ-owned contracts.
- Path payloads can produce deterministic orthogonal alpha overlay rasters through XQ-owned contracts.
- Contour payloads can produce deterministic orthogonal alpha overlay rasters and pixel-space hit-test results through XQ-owned contracts.
- Contour hit-test results can report optional contour point indexes for endpoint hits and optional insert-before point indexes for edge hits.
- Contour overlay rasterization and hit testing skip contours whose stored `XQContour.frame` plane does not match the active orthogonal, path-normal, or contour-edit slice plane, following old XQ `xq_ProfileRenderer2D` tolerance behavior from `<xq-source-extract>` without importing MITK/Qt ownership.
- Unmodified left-button endpoint selection on MPR contour overlays uses the old XQ `SelectPointClick` 4.0 pixel fallback only after the 1.0 pixel edge-edit hit test misses, so endpoint selection widens only when it would not widen edge-drag hits.
- Endpoint contour hit results can be handed to the workbench tool-panel host and four-pane widget drag/Delete/Backspace bridge for same-pane selected contour point movement and removal after the active left-button drag is released, while Delete/Backspace during the active drag is ignored to match the old XQ `movingPoint` state and Delete/Backspace is suppressed while the selected contour group still contains an open manual draft, matching old XQ `addingContour` where `DeleteKey` has no transition; edge hits route only through explicit Ctrl+left insertion or unmodified left double-click insertion; unmodified Escape or an unmodified right-click cancels the pending endpoint hit before Delete/Backspace can remove it.
- Unmodified contour-edit blank left clicks and Ctrl+left blank clicks with valid explicit-plane world positions can create or append open manual draft contour points through tool-panel command-stack routing when a contour group is selected, and ProfileGroupInteraction-style Ctrl+left blank clicks on ordinary axial/sagittal/coronal MPR panes can create or append open manual draft contour points on the current orthogonal slice frame.
- ProfileGroupInteraction-style Ctrl+left hits on existing open manual draft contour endpoints or edges on ordinary axial/sagittal/coronal MPR panes append new draft contour points through tool-panel command-stack routing instead of treating the hit as an insert/no-op branch.
- ProfileGroupInteraction-style Ctrl+left hits on existing open manual draft contour endpoints or edges on contour-edit planes append new draft contour points through tool-panel command-stack routing instead of inserting into the open draft edge.
- Unmodified Return or Enter on a contour-edit or ordinary axial/sagittal/coronal MPR pane can finish the current open manual draft contour through tool-panel command-stack routing, can be undone, and prevents later Escape from treating the finished contour as cancelable draft state, while Return/Enter on closed endpoint selections keeps the non-mutating pending-hit cancellation behavior and does not finish an unrelated open draft contour in the selected group, matching old XQ where `FinishContourKey` only exists in `addingContour`, not `ready` or `movingPoint`.
- Unmodified Escape on a contour-edit pane can cancel the current open manual draft contour through tool-panel command-stack routing and can be undone, while Escape on closed endpoint selections keeps the non-mutating pending-hit cancellation behavior and does not cancel an unrelated open draft contour in the selected group, matching old XQ where `CancelKey` only exists in `addingContour`, not `ready` or `movingPoint`.
- Endpoint contour drag command failures and cross-pane drag moves remain contained inside the four-pane UI event bridge while active MPR tool world-position tracking and event propagation continue.
- Path-normal oblique and contour-edit plane state can be expressed in XQ-owned slice controllers without falling back to fake axial pixels.
- Path-normal oblique grayscale slices can produce deterministic nearest-neighbor rasters from XQ-owned decoded image buffers.
- Path-normal oblique path overlays can project XQPath sample/control points into explicit XQ-owned slice plane pixels.
- Path-normal oblique path overlays reject zero pixel-spacing explicit planes with diagnostics.
- Contour-edit plane hit tests can project XQContourGroup contour points into explicit XQ-owned slice plane pixels without Qt or VTK ownership.
- Viewer code never parses `.ctgr` or `.pth` files.
- The current contract proves slice state and first-pass raster pixels come from `XQImageVolume` geometry and buffers, not external rendering objects.
- The Qt/VTK MPR widget displays grayscale slice pixels plus segmentation-mask/path/contour overlay alpha pixels derived from the XQ-owned rasterizer and clears disposable display products with diagnostics for invalid rasters.
- The Qt/VTK MPR widget can convert orthogonal, path-normal oblique, and contour-edit slice pixels into XQ-owned world points for workbench tool context without mutating contour payloads.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If a viewer computes domain state that belongs to path or contour payloads, move that state back to core data or algorithms.
