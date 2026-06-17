# Tool Panels

## Purpose

Define integrated tool panels for editing the active workflow stage without a plugin tool system.

This document creates the panel host, stage-to-panel selection contract, source-node requirement checks, a command-stack routing contract, and first contour-edit action routing from selected contour nodes plus active MPR world positions into `XQLumenContourService` commands.
It now also creates a thin Qt panel widget that mirrors those host descriptors as clickable `QToolButton` rows, reflects active-stage checked state and enabled/disabled state, and keeps stage switching routed through the host rather than owning workflow mutations itself.
The four-pane widget can now feed active MPR world positions into this host through a non-owning pointer, including valid unmodified MPR child left mouse press and drag events, and can use endpoint contour hit-test point indexes plus edge insert-before indexes to drive selected-point drag, Ctrl+left edge insertion, and Delete endpoint removal. Broader edit-mode dispatch remains deferred.
This document completes the first MPR hit-test-to-edit action bridge: endpoint hits carrying `XQMprSliceContourHit::pointIndex` can be captured on left-button press and moved through the existing command-stack route during drag or deleted by Delete, while edge hits carrying `insertBeforePointIndex` are inserted only through Ctrl+left. If the command route rejects the drag because the command context or selected node is unavailable, the four-pane UI bridge clears the drag without throwing through Qt event processing.

## Owns

Future source files:

```text
src/workbench/XQToolPanelHost.h
src/workbench/XQToolPanelHost.cpp
src/workbench/XQMprToolContext.h
tests/workbench/XQToolPanelHostTest.cpp
```

## Inputs

- Workflow state machine.
- Project tree selection.
- Domain feature services.
- Active MPR tool world positions from the four-pane layout or a future concrete panel widget.
- Optional active MPR tool world positions forwarded by `XQFourPaneLayoutWidget` after slice-pixel to world-position conversion.

## Outputs

- A right-side panel host that shows controls for the current stage and selection.
- Undoable contour point move, insert, and delete actions routed from workbench state into domain commands.

## Rules

- Tool panels are regular integrated UI classes, not discoverable plugins.
- Panels call workflow commands and domain services.
- Panels do not own domain data.
- Each panel has one workflow purpose.
- initial contract exposes panel descriptors, enabled/disabled state, non-owning command routing, active MPR tool-position context, and contour point edit action routing.
- No Qt widget, plugin discovery, direct domain mutation, or command-history ownership is added in this document.

## Tool Panels

```text
Path planning
Contour editing
Model generation
Mesh generation
Simulation setup
```

## Implementation Contract

Implementation Contract owns:

```text
src/workbench/XQToolPanelHost.h
src/workbench/XQToolPanelHost.cpp
src/workbench/XQMprToolContext.h
tests/workbench/XQToolPanelHostTest.cpp
```

Public class:

```text
xq::XQToolPanelHost
```

Public enums and structs:

```text
xq::WorkflowStage
xq::PaneId
xq::XQMprToolWorldPosition
xq::ToolPanelId
xq::XQToolPanelDescriptor
```

Minimum public operations:

```text
panels()
panelForStage(WorkflowStage)
setCurrentStage(WorkflowStage)
currentStage()
activePanel()
setSelectedNode(XQNodeId)
clearSelectedNode()
selectedNode()
setActiveMprToolWorldPosition(PaneId, Point3)
clearActiveMprToolWorldPosition()
activeMprToolPosition()
setPanelEnabled(ToolPanelId, bool)
isPanelEnabled(ToolPanelId)
updatePanelAvailability(const XQScene&)
updatePanelAvailability(const XQWorkflowController&)
setCommandContext(XQProject*, XQCommandStack*)
clearCommandContext()
executePanelCommand(std::unique_ptr<XQCommand>)
moveSelectedContourPoint(ContourId, std::size_t)
moveSelectedContourPointFromHit(const XQMprSliceContourHit&) -> bool
insertSelectedContourPoint(ContourId, std::size_t)
deleteSelectedContourPoint(ContourId, std::size_t)
```

Owned state:

```text
current workflow stage
selected node id
active MPR tool world position
panel descriptors
enabled/disabled flags
source-node availability derived from XQScene by domain type or XQWorkflowController transition validation
non-owning project and command stack pointers for panel action routing
```

Forbidden ownership:

```text
XQProject value
XQScene value
XQDataNode value
XQCommandStack value
command history
domain payload copies
Qt widgets in this initial contract
plugin descriptors or extension registry
```

Dependency boundary:

```text
No Qt symbols are required in this initial contract.
The later Qt panel widgets must consume these descriptors and selected node ids.
Mutating panel actions must enter `XQCommandStack` through `executePanelCommand` and must not bypass workflow commands.
Contour edit actions must use selected `XQDataNode` ids plus active MPR world positions and delegate payload mutation to `XQLumenContourService`.
MPR contour hit-test results may be consumed only as lightweight workbench inputs; endpoint moves still mutate through `XQCommandStack` and `XQLumenContourService`.
```

## Step Plan

- [x] Create a panel host keyed by workflow stage.
- [x] Create one descriptor per first-version panel.
- [x] Pass selected node ids into panel host state.
- [x] Route mutating actions through command and undo.
- [x] Defer Qt panel classes to a later concrete widget pass.
- [x] Add source-node requirement checks for first-version panels.
- [x] Add tests for panel selection by workflow state and disablement.
- [x] Add workflow-controller-driven panel availability checks.
- [x] Add first contour-edit point move/insert/delete action routing from active MPR world position through `XQLumenContourService`.
- [x] Add first MPR contour hit-test endpoint move/delete and edge insert routing while rejecting the wrong hit type for each command.

## Test Plan

Test target:

xq_tool_panel_host_tests

Test file:

tests/workbench/XQToolPanelHostTest.cpp

Core scenarios:

XQToolPanelHostProvidesIntegratedPanelDescriptors
XQToolPanelHostSelectsPanelByWorkflowStage
XQToolPanelHostTracksSelectedNodeId
XQToolPanelHostDisablesPanelWithoutChangingStage
XQToolPanelHostUpdatesPanelAvailabilityFromSceneRequirements
XQToolPanelHostUpdatesPanelAvailabilityFromWorkflowControllerTransitions
XQToolPanelHostRoutesMutatingActionsThroughCommandStack
XQToolPanelHostMovesSelectedContourPointFromActiveMprPosition
XQToolPanelHostInsertsSelectedContourPointFromActiveMprPosition
XQToolPanelHostDeletesSelectedContourPointThroughCommandStack
XQToolPanelHostMovesSelectedContourPointFromMprHitPointIndex
XQToolPanelHostIgnoresContourEdgeHitWithoutPointIndex

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_tool_panel_host_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQToolPanelHost --output-on-failure
```

Expected result:

all tool panel host tests pass without requiring Qt6

## Acceptance

- Switching workflow stage replaces the active panel without plugin activation.
- Panel actions mutate `XQScene` through commands or domain services.
- A panel can be disabled when required source nodes are absent.
- The initial contract proves panel selection is integrated workbench state, not plugin activation.
- The current contract proves panel enablement is derived from XQScene node domains, not plugin discovery or copied payloads.
- The current contract proves panel enablement can be driven by `XQWorkflowController::canTransitionTo` so workbench code can avoid duplicating stage source-node rules.
- The current contract proves panel-produced commands enter `XQCommandStack` and remain undoable/redoable through `XQProject`.
- The current contract proves contour point move, insert, and delete actions can be routed from selected contour group node ids and active MPR world positions into undoable domain commands without direct payload mutation.
- The current contract proves MPR endpoint hit-test results can route selected contour point drag movement and Delete removal, and MPR edge hit-test results can route Ctrl+left insertion without treating edge hits as point edits.
- The current contract proves rejected MPR endpoint drag commands remain contained at the four-pane widget event boundary while active tool-position tracking still updates.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If a panel hides persistent state not represented in `XQScene`, move that state into the owning payload or workflow context.
