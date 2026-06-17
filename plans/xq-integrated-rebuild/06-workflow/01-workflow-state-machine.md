# Workflow State Machine

## Purpose

Define the first-version vascular workflow stages and the allowed transitions between them.

This document moves workflow stage ownership out of the workbench layer and into `xq_workflow`. Workbench components may observe and set workflow stage through a VTK-free, Qt-free state-change listener, but they must not define the authoritative stage enum.

## Owns

Future source files:

```text
src/workflow/XQWorkflowState.h
src/workflow/XQWorkflowState.cpp
src/workflow/XQWorkflowController.h
src/workflow/XQWorkflowController.cpp
tests/workflow/XQWorkflowStateMachineTest.cpp
```

## Inputs

- `XQProject` and `XQScene`.
- Tool panel host.
- Source relation document.

## Outputs

- One workflow controller per open project.
- Deterministic stage transitions and active context.

## Rules

- Workflow is integrated application state, not plugin activation state.
- Stage changes do not create or destroy project data.
- Stages declare required source node types.
- UI controls observe workflow state; they do not define it.
- `XQToolPanelHost` must use the workflow-owned `WorkflowStage` type.

## Stages

```text
NoProject
ImageLoaded
PathPlanning
ContourEditing
Modeling
Meshing
SimulationPrep
ResultsReview
```

## Implementation Contract

Implementation Contract owns:

```text
src/workflow/XQWorkflowState.h
src/workflow/XQWorkflowState.cpp
src/workflow/XQWorkflowController.h
src/workflow/XQWorkflowController.cpp
tests/workflow/XQWorkflowStateMachineTest.cpp
```

Public types:

```text
xq::WorkflowStage
xq::XQWorkflowContext
xq::XQWorkflowState
xq::XQWorkflowController
```

Minimum public operations:

```text
XQWorkflowController::setProject(XQProject*)
XQWorkflowController::clearProject()
XQWorkflowController::state()
XQWorkflowController::canTransitionTo(WorkflowStage)
XQWorkflowController::transitionTo(WorkflowStage)
XQWorkflowController::inferStageFromScene()
XQWorkflowController::setSelectedImage/path/contourGroup/model/mesh/simulationCase(XQNodeId)
XQWorkflowController::addStateChangedListener(StateChangedListener)
```

Context fields:

```text
selected image node id
selected path node id
selected contour group node id
selected model node id
selected mesh node id
selected simulation case node id
```

Transition validation first pass:

```text
NoProject requires no project
ImageLoaded requires at least one ImageVolume node
PathPlanning requires image
ContourEditing requires path
Modeling requires contour group
Meshing requires surface model
SimulationPrep requires mesh
ResultsReview requires simulation case
```

Forbidden ownership:

```text
XQProject value
XQScene value
XQDataNode value
domain payload copies
plugin activation state
UI widget state as authoritative workflow state
```

## Transition Contract

```text
NoProject -> ImageLoaded
ImageLoaded -> PathPlanning
PathPlanning -> ContourEditing
ContourEditing -> Modeling
Modeling -> Meshing
Meshing -> SimulationPrep
SimulationPrep -> ResultsReview
```

Backward transitions are allowed for editing earlier data, but downstream dirty state must be marked by source relations.

## Step Plan

- [x] Define workflow stage enum in `xq_workflow`.
- [x] Define active context with selected image, path, contour group, model, mesh, and simulation case ids.
- [x] Define transition validation by required source nodes.
- [x] Emit workflow state changes to workbench components.
- [x] Add tests for forward and backward transitions.
- [x] Update `XQToolPanelHost` to include the workflow-owned stage header.

## Test Plan

Test target:

xq_workflow_tests

Test file:

tests/workflow/XQWorkflowStateMachineTest.cpp

Core scenarios:

XQWorkflowControllerStartsAtNoProject
XQWorkflowControllerInfersStageFromScene
XQWorkflowControllerValidatesForwardTransitions
XQWorkflowControllerAllowsBackwardTransitions
XQWorkflowControllerTracksSelectedContextIds
XQWorkflowControllerNotifiesStateChangesToWorkbenchObservers

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_workflow_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQWorkflowController --output-on-failure
```

Expected result:

all workflow controller tests pass

## Acceptance

- Loading `<acceptance-project>` can set stage according to available scene data.
- Tool panels can ask workflow state which action is valid.
- Workflow never depends on old plugin activation state.
- Workbench code no longer owns the workflow stage enum.
- Workbench components can observe state changes without Qt, plugin, or widget ownership in the workflow layer.

## Failure Repair

If workflow state is duplicated in multiple panels, move it into this controller.
