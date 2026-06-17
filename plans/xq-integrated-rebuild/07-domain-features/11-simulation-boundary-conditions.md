# Simulation Boundary Conditions

## Purpose

Define editing and validation of simulation boundary conditions against mesh boundary faces.

The initial contract creates an XQ-owned domain service for editing typed
`BoundaryCondition` records in `XQSimulationCase`. The mesh boundary table is
the authoritative face list. This work must not edit `.sjb` raw XML, solver
deck text, or UI private state as the source of truth.

## Owns

Current source-pass files:

```text
src/core/XQSimulationCase.h
src/core/XQSimulationCase.cpp
src/domain/simulation/XQBoundaryConditionService.h
src/domain/simulation/XQBoundaryConditionService.cpp
tests/domain/simulation/XQBoundaryConditionServiceTest.cpp
```

Later UI-owned files:

```text
src/workbench/tools/XQSimulationToolPanel.h
src/workbench/tools/XQSimulationToolPanel.cpp
```

## Inputs

- `XQMesh`.
- `XQSimulationCase`.
- `MeshBoundaryFace` rows produced by mesh boundary transfer.
- Command and undo.

## Outputs

- Boundary condition records bound to mesh face ids.
- Validation diagnostics for missing faces, invalid numeric fields, or missing
  required boundary types.
- Undoable commands that mutate `XQSimulationCase` through the XQ project and
  scene.

## Rules

- Boundary conditions are edited as `XQSimulationCase` data.
- UI panels do not store solver settings as private widget state.
- The mesh is the authoritative source for available boundary faces.
- RCR, resistance, inflow, wall, and coupled boundary types are explicit variants.
- Boundary condition assignment must validate the target mesh face id before
  returning a command.
- Editing must not require VTK, Qt, MITK, BlueBerry, CTK, svSolver objects, or
  old plugin registries.
- Boundary condition assignment/removal works directly against an existing
  simulation node and mesh payload.
- Mesh-to-simulation scene source relation creation is explicit through
  `createBindSimulationToMeshCommand(meshNodeId, simulationNodeId)`, not implicit
  in boundary-condition assignment.

## Functional Content

First-version behavior:

```text
assign inflow to inlet face
assign resistance or RCR to outlet faces
assign wall condition
load and edit inflow waveform values
load and edit RCR values
validate that required faces have conditions
preserve existing boundary condition order except when replacing a condition for the same face
support undo/redo through XQCommandStack
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Implementation Contract

Public service types:

```text
XQBoundaryConditionDiagnostic
XQBoundaryConditionValidationResult
XQBoundaryConditionService
```

Minimum public operations:

```text
validateBoundaryConditions(const XQMesh&, const XQSimulationCase&) -> XQBoundaryConditionValidationResult
createAssignBoundaryConditionCommand(XQNodeId simulationNodeId, const XQMesh&, BoundaryCondition) -> std::unique_ptr<XQCommand>
createBindSimulationToMeshCommand(XQNodeId meshNodeId, XQNodeId simulationNodeId) -> std::unique_ptr<XQCommand>
createRemoveBoundaryConditionCommand(XQNodeId simulationNodeId, std::string boundaryName) -> std::unique_ptr<XQCommand>
```

Core support:

```text
XQSimulationCase::setBoundaryConditions(std::vector<BoundaryCondition>)
```

Validation rules:

```text
every boundary condition must reference a positive face id
every referenced face id must exist in XQMesh::boundaryFaces()
at least one inlet face must have an InflowCondition
each outlet face must have either ResistanceCondition, RcrCondition, PrescribedPressureCondition, or CoupledCondition
wall faces may use WallCondition; missing wall condition is not fatal in the initial contract
inflow scale must be positive
inflow period must be non-negative
inflow waveform samples, when present, must be sorted by non-decreasing time
resistance must be positive
RCR proximal resistance, capacitance, and distal resistance must be positive
prescribed pressure must be finite
wall model must not be empty
coupling name must not be empty
duplicate conditions for the same face id are diagnostic errors unless the edit command replaces the existing face condition
```

Command behavior:

```text
assign command replaces any existing condition for the same face id
assign command preserves conditions for other face ids
remove command removes by boundary condition name
undo restores the previous complete boundary condition vector
redo reapplies the edit
commands reject missing simulation nodes or non-simulation payloads
bind command sets XQSimulationCase::sourceMeshNode and creates a live MeshToSimulationCase XQScene relation
bind command is idempotent for an already-live same mesh relation
bind undo removes only the relation created by that command and preserves older stale relation records
```

External dependency boundary:

```text
forbidden in public service/core API: Qt, VTK, MITK, BlueBerry, CTK, svSolver, SimVascular plugin classes
allowed later inside export layer only: solver deck formatting helpers
```

## Step Plan

- [x] Add `src/domain/simulation/XQBoundaryConditionService.h`.
- [x] Add `src/domain/simulation/XQBoundaryConditionService.cpp`.
- [x] Add `XQSimulationCase::setBoundaryConditions(...)` for command-level
  atomic replacement and undo restoration.
- [x] Add `xq_domain_simulation` CMake target linked to `xq_core` and `xq_workflow`.
- [x] Add `tests/domain/simulation/XQBoundaryConditionServiceTest.cpp`.
- [x] Define boundary condition validation diagnostics.
- [x] Validate face id existence against `XQMesh`.
- [x] Validate required numeric fields for inflow, RCR, resistance, pressure, wall,
  and coupled conditions.
- [x] Validate required inlet/outlet condition coverage from mesh face kind.
- [x] Apply assign/remove edits through command and undo.
- [x] Apply explicit mesh-to-simulation binding through command and undo.
- [x] Add tests for inflow, RCR, resistance, wall, duplicate conditions, missing
  faces, and undo/redo.
- [x] Add tests for explicit MeshToSimulationCase relation creation, same-mesh
  idempotency, and undo beside stale relation history.

## Test Plan

Test target:

xq_boundary_condition_service_tests

Test file:

tests/domain/simulation/XQBoundaryConditionServiceTest.cpp

Core scenarios:

XQBoundaryConditionServiceValidatesCompleteBoundarySet
XQBoundaryConditionServiceReportsMissingRequiredFaceConditions
XQBoundaryConditionServiceRejectsUnknownFaceIdsAndInvalidNumbers
XQBoundaryConditionServiceAssignsBoundaryConditionWithUndoRedo
XQBoundaryConditionServiceBindsSimulationToMeshWithSourceRelationUndoRedo
XQBoundaryConditionServiceBindingSimulationToSameMeshDoesNotDuplicateSourceRelation
XQBoundaryConditionServiceUndoBindingRemovesLiveRelationWhenStaleRelationAlreadyExists
XQBoundaryConditionServiceReplacesExistingFaceCondition
XQBoundaryConditionServiceRemovesBoundaryConditionWithUndoRedo

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_boundary_condition_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQBoundaryConditionService --output-on-failure
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_boundary_condition_service_tests
```

failed before implementation because tests/domain/simulation/XQBoundaryConditionServiceTest.cpp
included domain/simulation/XQBoundaryConditionService.h and that service did
not exist yet.

XQBoundaryConditionServiceBindsSimulationToMeshWithSourceRelationUndoRedo failed
before implementation because XQBoundaryConditionService had no
createBindSimulationToMeshCommand API.

XQBoundaryConditionServiceBindingSimulationToSameMeshDoesNotDuplicateSourceRelation
failed before idempotency repair because binding to the same mesh created a
duplicate source relation.

XQBoundaryConditionServiceUndoBindingRemovesLiveRelationWhenStaleRelationAlreadyExists
failed before XQScene relation-removal repair because undo removed the stale
relation instead of the live relation created by the command.

## Acceptance

- Loaded `.sjb` data appears as editable boundary condition records.
- Simulation panel can list mesh faces and assigned conditions.
- Solver export receives complete typed settings.
- Boundary condition validation uses `XQMesh::boundaryFaces()` as the source of
  available faces.
- Explicit mesh binding leaves `XQSimulationCase::sourceMeshNode()` and the
  XQScene `MeshToSimulationCase` relation in sync.
- Assign/remove edits are undoable and leave `XQSimulationCase` as the single
  source of simulation settings.

## Failure Repair

If boundary settings are edited as raw text files only, promote the required fields into `XQSimulationCase`.
