# Main Window Layout

## Purpose

Define the integrated Qt main window that hosts project navigation, image viewers, 3D scene, and tool panels.

This document creates the XQ-owned main-window composition contract, a non-owning workflow-command routing contract, and a thin Qt main-window widget shell. The Qt shell composes the workflow toolbar, project tree widget, four-pane widget, tool-panel widget, and diagnostics/status strip without owning project data, scene data, command history, or domain payloads.

## Owns

Source files:

```text
src/workbench/XQMainWindow.h
src/workbench/XQMainWindow.cpp
src/workbench/XQMainWindowWidget.h
src/workbench/XQMainWindowWidget.cpp
src/app/main.cpp
tests/workbench/XQMainWindowStructureTest.cpp
tests/workbench/XQMainWindowWidgetTest.cpp
```

## Inputs

- `XQApplication` startup from the foundation layer.
- `XQProject` lifecycle.
- Project tree, MPR viewers, 3D scene viewer, and tool panels.
- Four-pane layout.

## Outputs

- One integrated desktop window for the XQ workflow.

## Rules

- The main window owns UI composition only.
- The main window does not own project data; it binds to an `XQProject`.
- No BlueBerry, CTK, plugin perspective, extension registry, or workbench part system.
- Partial first-version UI may be incomplete, but layout should already match the integrated architecture.
- initial contract may be a non-Qt composition/state class, but the public contract must map directly to the future Qt main window.
- Do not introduce a fake UI shell that stores project data outside `XQProject` or `XQScene`.

## Layout Contract

Main regions:

```text
left: project tree
center: MPR viewers and 3D scene
right: active tool panel
top: workflow toolbar and common actions
bottom: diagnostics/status strip
```

## Implementation Contract

Implementation Contract owns:

```text
src/workbench/XQMainWindow.h
src/workbench/XQMainWindow.cpp
src/workbench/XQMainWindowWidget.h
src/workbench/XQMainWindowWidget.cpp
tests/workbench/XQMainWindowStructureTest.cpp
tests/workbench/XQMainWindowWidgetTest.cpp
```

Public class:

```text
xq::XQMainWindow
xq::XQMainWindowWidget
```

Minimum public operations:

```text
setProject(XQProject*)
clearProject()
project()
setSelectedNode(XQNodeId)
clearSelectedNode()
selectedNode()
regions()
hasRegion(MainWindowRegion)
setToolPanel(std::string)
activeToolPanel()
setCommandStack(XQCommandStack*)
clearCommandStack()
executeWorkflowCommand(std::unique_ptr<XQCommand>)
diagnostics()
XQMainWindowWidget::setProject(XQProject*)
XQMainWindowWidget::clearProject()
XQMainWindowWidget::project()
XQMainWindowWidget::setCommandStack(XQCommandStack*)
XQMainWindowWidget::clearCommandStack()
XQMainWindowWidget::mainWindowState()
XQMainWindowWidget::projectTreeView()
XQMainWindowWidget::fourPaneWidget()
XQMainWindowWidget::toolPanelWidget()
XQMainWindowWidget::toolPanelHost()
XQMainWindowWidget::fourPaneLayout()
XQMainWindowWidget::workflowToolbar()
XQMainWindowWidget::contentSplitter()
XQMainWindowWidget::diagnosticsStatusLabel()
XQMainWindowWidget::diagnosticsStatusText()
```

Owned data:

```text
non-owning XQProject pointer
non-owning XQCommandStack pointer
selected XQNodeId
main-window region declarations
active tool panel id
diagnostic strings
```

Forbidden data ownership:

```text
XQProject value
XQScene value
XQDataNode value
XQCommandStack value
command history
domain payload copies
external UI framework node wrappers
project data inside XQMainWindowWidget
command history inside XQMainWindowWidget
domain payload copies inside XQMainWindowWidget
```

Dependency boundary:

```text
No Qt symbols are required by `XQMainWindow`.
The Qt widget shell may compose Qt child widgets after Qt6 is pinned, but it must keep the same XQ-owned project binding contract.
Menu and toolbar mutations must route `XQCommand` instances into `XQCommandStack` and must not mutate `XQScene` directly.
```

## Step Plan

- [x] Create `XQMainWindow` as the XQ-owned main-window composition/state contract.
- [x] Add setters for current `XQProject` and selected `XQNodeId`.
- [x] Declare project tree, viewer area, tool panel area, toolbar, and diagnostics regions.
- [x] Reserve center viewer area for `XQFourPaneLayout`.
- [x] Add a thin Qt widget shell that composes the project tree, four-pane, and tool-panel widgets.
- [x] Compose the first-version workflow toolbar from integrated tool-panel workflow stages.
- [x] Compose the diagnostics/status strip and summarize project scene/diagnostic state.
- [x] Add rendered full-shell layout acceptance for top toolbar, center content splitter, bottom status strip, and left/center/right content regions.
- [x] Keep project and command-stack binding order-independent for child widgets and panel hosts.
- [x] Synchronize project-tree selection into main-window state, four-pane state, and active tool-panel stage.
- [x] Route menu and toolbar actions into workflow commands.
- [x] Add structure tests that instantiate the window with an empty project.
- [x] Add Qt shell tests for child composition, project binding, command-context propagation, and tree-selection synchronization.

## Test Plan

Test target:

xq_workbench_tests
xq_main_window_widget_tests

Test file:

tests/workbench/XQMainWindowStructureTest.cpp
tests/workbench/XQMainWindowWidgetTest.cpp

Core scenarios:

XQMainWindowDeclaresIntegratedRegions
XQMainWindowBindsProjectWithoutOwningSceneData
XQMainWindowTracksSelectedNodeId
XQMainWindowClearsSelectionWhenProjectClears
XQMainWindowRoutesToolbarActionsThroughCommandStack
XQMainWindowWidgetComposesIntegratedWorkbenchWidgets
XQMainWindowWidgetComposesWorkflowToolbarAndDiagnosticsStrip
XQMainWindowWidgetRendersFullShellRegionsWithStableGeometry
XQMainWindowWidgetBindingProjectPropagatesSceneAndCommandContext
XQMainWindowWidgetWorkflowToolbarActionSwitchesToolPanelStage
XQMainWindowWidgetCommandStackBoundBeforeProjectStillEnablesTreeCommands
XQMainWindowWidgetCommandStackBoundBeforeProjectStillEnablesToolPanelCommands
XQMainWindowWidgetTreeSelectionSynchronizesWorkbenchState

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_workbench_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQMainWindow --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_main_window_widget_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQMainWindowWidget --output-on-failure
```

Expected result:

all XQMainWindow structure tests pass without requiring Qt6
all XQMainWindowWidget shell tests pass with Qt6

## Acceptance

- The window can bind and unbind an `XQProject`.
- UI panels observe project and scene state through XQ APIs.
- No project data is stored only in widget state.
- The initial contract preserves a direct path to a future Qt main window without adding plugin architecture.
- Menu and toolbar actions enter the workflow command stack instead of mutating scene data directly.
- The Qt shell composes existing integrated widgets and state objects without becoming a second project model.
- Binding `XQCommandStack` before or after `XQProject` still gives project tree and tool-panel commands a live project context.
- The workflow toolbar exposes enabled first-version workflow stages and switches the active tool-panel stage through XQ-owned state.
- The diagnostics/status strip reports no-project state and summarizes bound project scene-node and diagnostic counts.
- Showing the full Qt shell assigns stable positive geometry to the top toolbar, center content splitter, bottom status strip, left project tree, center four-pane viewer, and right tool panel.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If a feature requires creating a new plugin view or perspective, repair this document and place the UI under the integrated main window.
