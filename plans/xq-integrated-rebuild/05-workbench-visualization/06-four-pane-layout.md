# Four Pane Layout

## Purpose

Define the integrated medical imaging four-pane layout using Qt, VTK, and XQ-owned project data.

This document creates the XQ-owned four-pane state model, crosshair controller, `XQViewLinkController`-backed shared MPR crosshair/window-level display state, explicit path-normal and contour-edit MPR pane mode switching, active MPR tool world-position contract, a thin Qt widget composition that consumes this state model by pointer and owns only child view widgets, a native MPR child mouse/key-event bridge into the active tool context, a native right-button MPR window/level drag bridge, and the first endpoint contour drag/Delete plus Ctrl+left edge insertion bridge into the non-owning tool-panel host. The widget bridge contains rejected endpoint-drag commands at the Qt event boundary, keeping command-context or stale-selection failures from escaping native event processing.

## Owns

Source files:

```text
src/workbench/XQFourPaneLayout.h
src/workbench/XQFourPaneLayout.cpp
src/workbench/XQFourPaneLayoutWidget.h
src/workbench/XQFourPaneLayoutWidget.cpp
src/visualization/XQCrosshairController.h
src/visualization/XQCrosshairController.cpp
src/visualization/XQViewLinkController.h
src/visualization/XQViewLinkController.cpp
tests/workbench/XQFourPaneLayoutTest.cpp
tests/workbench/XQFourPaneLayoutWidgetTest.cpp
tests/visualization/XQCrosshairControllerTest.cpp
tests/visualization/XQViewLinkControllerTest.cpp
```

## Inputs

- Main window layout.
- MPR viewers.
- 3D scene viewer.
- `XQImageVolume`.
- `XQScene`.
- `XQDataNode` selection.
- Qt6 and VTK dependency roles.

## Outputs

- One workbench center layout with three 2D slice views and one 3D scene view.
- Shared crosshair, slice position, window/level, selection, and overlay synchronization.

## Rules

- The four-pane layout is display and interaction infrastructure only.
- It must not own project data, image data, paths, contours, models, meshes, or simulation cases.
- It must not use MITK, BlueBerry, CTK, or any old workbench framework.
- It observes `XQProject`, `XQScene`, and selected `XQDataNode` ids.
- 2D and 3D views share interaction state through XQ-owned controllers, not through VTK actor ownership.
- initial contract must avoid Qt and VTK types.
- The Qt widget composition pass may own `XQMprViewWidget` and `XQScene3DViewWidget` children only; it must not own project data, scene data, image buffers, or independent slice/presentation state.

## Layout Contract

Default panes:

```text
top-left: axial MPR
top-right: sagittal MPR
bottom-left: coronal MPR
bottom-right: 3D scene
```

Allowed mode changes:

```text
maximize one pane
restore four panes
swap 3D pane with one MPR pane
show path-normal oblique slice in the active MPR pane
show contour-edit plane in the active MPR pane
```

## Interaction Contract

Shared state:

```text
world crosshair position
active image node id
active path node id
active contour group node id
selected scene node id
active MPR tool world position and source pane id
window center
window width
slice orientation
camera reset request
```

Interaction flow:

```text
MPR click or drag
-> XQCrosshairController updates world position
-> all MPR panes update slice position
-> 3D pane updates crosshair marker
-> active tool panel receives selected world point
```

3D selection flow:

```text
3D pick
-> selected XQNodeId
-> project tree selection updates
-> tool panel context updates
-> related MPR overlays highlight matching data
```

## Implementation Contract

Public classes:

```text
XQFourPaneLayout
XQFourPaneLayoutWidget
XQCrosshairController
XQViewLinkController
```

Minimum public operations:

```text
setScene(XQScene*)
setActiveImage(std::shared_ptr<const XQImageVolume>)
setSelectedNode(XQNodeId)
setCrosshairWorldPosition(Point3)
setMprWindowLevel(double center, double width)
clearMprWindowLevel()
XQViewLinkController::attachMprSliceController(XQSliceController*)
XQViewLinkController::detachMprSliceController(XQSliceController*)
XQViewLinkController::setCrosshairWorldPosition(Point3)
XQViewLinkController::setMprWindowLevel(double center, double width)
XQViewLinkController::clearMprWindowLevel()
showPathNormalPlaneInMprPane(PaneId, XQSlicePlane)
showContourEditPlaneInMprPane(PaneId, XQSlicePlane)
restoreOrthogonalMprPane(PaneId)
swapScene3DWithMprPane(PaneId)
setActiveMprToolWorldPosition(PaneId, Point3)
clearActiveMprToolWorldPosition()
activeMprToolPosition()
maximizePane(PaneId)
restoreFourPaneLayout()
XQFourPaneLayoutWidget::setFourPaneLayout(XQFourPaneLayout*)
XQFourPaneLayoutWidget::fourPaneLayout()
XQFourPaneLayoutWidget::setToolPanelHost(XQToolPanelHost*)
XQFourPaneLayoutWidget::toolPanelHost()
XQFourPaneLayoutWidget::setActiveMprToolPositionFromSlicePixel(PaneId, int column, int row) -> bool
XQFourPaneLayoutWidget::showPathNormalPlaneInMprPane(PaneId, XQSlicePlane) -> bool
XQFourPaneLayoutWidget::showContourEditPlaneInMprPane(PaneId, XQSlicePlane) -> bool
XQFourPaneLayoutWidget::restoreOrthogonalMprPane(PaneId) -> bool
XQFourPaneLayoutWidget::swapScene3DWithMprPane(PaneId) -> bool
XQFourPaneLayoutWidget::mprView(PaneId)
XQFourPaneLayoutWidget::scene3DView()
```

Implementation Contract owns:

```text
src/workbench/XQFourPaneLayout.h
src/workbench/XQFourPaneLayout.cpp
src/workbench/XQFourPaneLayoutWidget.h
src/workbench/XQFourPaneLayoutWidget.cpp
src/visualization/XQCrosshairController.h
src/visualization/XQCrosshairController.cpp
src/visualization/XQViewLinkController.h
src/visualization/XQViewLinkController.cpp
tests/workbench/XQFourPaneLayoutTest.cpp
tests/workbench/XQFourPaneLayoutWidgetTest.cpp
tests/visualization/XQCrosshairControllerTest.cpp
tests/visualization/XQViewLinkControllerTest.cpp
```

Public enum:

```text
xq::PaneId
xq::XQMprToolWorldPosition
```

Owned state:

```text
three XQSliceController instances
one XQScene3DPresentationModel instance
one XQViewLinkController instance linking the three MPR XQSliceController instances
one XQCrosshairController instance inside XQViewLinkController
shared MPR window/level display state held by XQViewLinkController and applied to the three XQSliceController instances
explicit path-normal or contour-edit plane state held by the selected MPR XQSliceController
active pane id
active MPR tool world position
maximized pane id
selected node id
non-owning XQScene pointer
```

Forbidden ownership:

```text
XQProject value
XQScene value
XQDataNode value
image/path/contour/model/mesh/simulation payload copies
Qt widget handles inside XQFourPaneLayout state
VTK renderer, actor, or interactor handles inside XQFourPaneLayout state
image/path/contour/model/mesh/simulation payload pointers beyond child viewer bindings
```

## Step Plan

- [x] Create `XQFourPaneLayout` to compose three `XQSliceController` instances and one `XQScene3DPresentationModel`.
- [x] Create `XQCrosshairController` to own world crosshair position and slice synchronization.
- [x] Create `XQViewLinkController` to link MPR crosshair and window/level state across attached slice controllers.
- [x] Connect selected node id to all four pane state objects.
- [x] Connect contour and path tools to active MPR world positions.
- [x] Synchronize first MPR window/level display state across the axial, sagittal, and coronal slice controllers.
- [x] Switch individual MPR panes into path-normal oblique and contour-edit explicit plane modes, and restore their default orthogonal orientation.
- [x] Swap the 3D pane with an MPR pane without changing pane-owned XQ state.
- [x] Connect widget-level MPR slice-pixel world-position conversion to the four-pane active tool context and optional tool panel host.
- [x] Dispatch unmodified native MPR left mouse press and left-button drag events through the slice-pixel tool-position bridge while preserving event propagation.
- [x] Dispatch unmodified native MPR right-button drags into shared MPR window/level state without changing active tool-position context.
- [x] Capture endpoint contour hits on unmodified native MPR left mouse press and route same-pane drags through the tool-panel command path while leaving edge hits non-mutating.
- [x] Route Ctrl+left native MPR edge hits to command-stack contour point insertion and Delete key presses to the last selected endpoint deletion.
- [x] Contain endpoint contour drag command failures inside the widget event bridge while keeping active MPR tool-position updates and event propagation.
- [x] Add tests for pane creation, crosshair propagation, node selection propagation, and maximize/restore behavior.
- [x] Add first Qt four-pane widget composition around three `XQMprViewWidget` children and one `XQScene3DViewWidget`.

## Test Plan

Test target:

xq_four_pane_layout_tests
xq_four_pane_layout_widget_tests
xq_crosshair_controller_tests
xq_view_link_controller_tests

Test files:

tests/workbench/XQFourPaneLayoutTest.cpp
tests/workbench/XQFourPaneLayoutWidgetTest.cpp
tests/visualization/XQCrosshairControllerTest.cpp
tests/visualization/XQViewLinkControllerTest.cpp

Core scenarios:

construct layout with four panes
set active image and verify all MPR panes receive the same image node id
move crosshair in axial pane and verify sagittal, coronal, and 3D state updates
link MPR crosshair state through XQViewLinkController and verify attached controllers update
set active MPR tool world position and verify path/contour tool context can read the pane id and world point
synchronize MPR window/level center and width across axial, sagittal, and coronal panes
link MPR window/level state through XQViewLinkController, including attach/detach behavior
switch an MPR pane into path-normal oblique mode without changing the other panes or losing active image/window-level state
switch an MPR pane into contour-edit mode and restore it to its default orthogonal orientation
reject path-normal, contour-edit, and restore requests on the 3D pane
swap the 3D pane with an MPR pane and verify only display order changes
swap the 3D pane with an MPR child through the Qt widget and verify child widgets move to the expected grid cells
select a model node in 3D and verify selected node id is propagated
maximize one pane and restore four-pane layout without changing project data
compose three MPR child widgets and one 3D child widget
bind child widgets to non-owning controllers and presentation model from XQFourPaneLayout
map a valid MPR slice pixel into active layout/tool-panel MPR world-position context
reject invalid MPR slice pixels without changing active tool context
switch an MPR child widget into path-normal oblique mode and restore it through the bound non-owning layout state
switch an MPR child widget into contour-edit mode through the bound non-owning layout state
dispatch unmodified native MPR left mouse press and left-button drag events into active layout/tool-panel MPR world-position context
dispatch unmodified native MPR right-button drags into shared window/level state while preserving active tool context and event propagation
ignore unsupported modified native MPR mouse events and right-button presses that do not become window/level drags, and reject out-of-range native MPR mouse events without changing active tool context
drag an endpoint contour hit through the tool host command stack while ignoring contour edge drags that have no point index
insert a contour point from a Ctrl+left edge hit and delete the last selected endpoint with Delete through the tool host command stack
ignore endpoint drag command failures without throwing through native Qt event processing

Expected command after source files exist:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_four_pane_layout_tests xq_crosshair_controller_tests
cmake --build <xq-rebuild-workspace>/build --target xq_view_link_controller_tests
cmake --build <xq-rebuild-workspace>/build --target xq_four_pane_layout_widget_tests
ctest --test-dir <xq-rebuild-workspace>/build -R "XQFourPaneLayout|XQCrosshairController|XQViewLinkController" --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build -R "XQFourPaneLayout|XQCrosshairController|XQViewLinkController|XQMprViewWidget|XQScene3DViewWidget" --output-on-failure
```

## Acceptance

- The workbench can show axial, sagittal, coronal, and 3D views together.
- Crosshair movement in one 2D pane updates the other 2D panes and the 3D marker.
- Selection uses `XQNodeId` and never depends on external framework node ownership.
- Four-pane display works with `XQImageVolume` from `Images/OSMSC0090-cm.vti`.
- The initial contract proves four-pane state is integrated through XQ-owned controllers without Qt or VTK ownership.
- `XQViewLinkController` synchronizes shared MPR crosshair and window/level state across attached MPR controllers without Qt, VTK, or project-data ownership.
- Shared MPR window/level state updates the axial, sagittal, and coronal `XQSliceController` instances without storing image data or VTK display objects in the four-pane layout.
- Path-normal oblique and contour-edit pane mode switching updates only the selected MPR `XQSliceController`, preserves active image/window-level state, rejects the 3D pane, and restores the pane's default axial/sagittal/coronal orientation on request.
- Pane swapping moves the 3D view and selected MPR view between layout cells without changing their `PaneId`, controller, presentation-model, project-data, image-data, or VTK ownership.
- The Qt widget composition proves axial/sagittal/coronal MPR widgets and the 3D widget consume `XQFourPaneLayout` state without copying project data or creating parallel state.
- Native MPR child left mouse press and left-button drag events can update the active MPR tool world position and optional tool-panel host through XQ-owned slice-pixel mapping while unsupported modified and out-of-range events, plus right-button presses that do not become window/level drags, do not mutate context.
- Native MPR child endpoint contour drags can move selected contour points through the optional tool-panel host and command stack while contour edge drags without point indexes remain non-mutating.
- Native MPR child Ctrl+left edge hits can insert contour points through the optional tool-panel host and command stack, and Delete key presses can remove the last selected endpoint hit through the same route.
- Native MPR child endpoint contour drags do not throw through the Qt event path when the optional tool-panel host rejects command dispatch; the drag is cleared and active MPR tool-position tracking remains available.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If four-pane behavior starts owning project data, move ownership back to `XQScene` and keep this layout as presentation infrastructure.
