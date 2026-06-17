# XQSimulationCase

## Purpose

Define the simulation-preparation payload for boundary conditions, solver settings, and export files.

## Owns

Future source files:

```text
src/core/XQSimulationCase.h
src/core/XQSimulationCase.cpp
tests/core/XQSimulationCaseTest.cpp
```

## Inputs

- Native `.sjb` reader.
- Simulation boundary condition feature.
- Simulation solver export feature.

## Outputs

- A native XQ simulation case linked to one mesh.
- Boundary condition records for inflow, outlets, wall, material, solver, and output controls.

## Rules

- `XQSimulationCase` stores simulation-prep semantics, not only paths to solver files.
- Files under `<acceptance-project>/Simulations` must load into this payload as direct project data.
- Solver export is generated from this payload and `XQMesh`.
- ROM and multiphysics settings extend this case through XQ-owned structs, not Python dictionaries.

## Data Contract

```text
SimulationCaseId caseId
std::optional<XQNodeId> sourceMeshNode
std::vector<BoundaryCondition> boundaryConditions
MaterialModel material
SolverSettings solver
TimeSettings time
OutputSettings output
std::vector<SimulationFileReference> sourceFiles
```

Boundary kinds:

```text
Inflow
Resistance
RCR
PrescribedPressure
Wall
Coupled
```

Known source files:

```text
.sjb
solver.inp
.svpre
inflow.flow
rcrt.dat
bct.vtp
```

## Implementation Contract

Public API surface:

```text
SimulationCaseId
BoundaryCondition
MaterialModel
SolverSettings
TimeSettings
OutputSettings
SimulationFileReference
XQSimulationCase
XQSimulationCase::boundaryConditions()
XQSimulationCase::sourceMeshNode()
XQSimulationCase::solverSettings()
```

Dependency boundary:

```text
allowed: XQ simulation value types and file references
not allowed publicly: raw XML nodes, Python dictionaries, solver-specific mutable globals
```

## Step Plan

- [ ] Define boundary condition variants with face id binding.
- [ ] Define material, solver, time, and output settings.
- [ ] Preserve source file references for loaded SimVascular-style cases.
- [ ] Link simulation case to mesh node through scene relations.
- [ ] Add tests for loading RCR and inflow settings from acceptance project files.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQSimulationCase --output-on-failure
```

Required cases:

create inflow, resistance, RCR, and wall boundary conditions
bind boundary conditions to face ids
store material, time, solver, and output settings
preserve source file references
load Simulations/0090_0001.sjb after SJB reader exists

## Acceptance

- The simulation panel can show all boundary conditions without parsing `.sjb`.
- Solver export can regenerate solver-preparation files from XQ data.
- Missing source files are reported in project diagnostics while the simulation case remains inspectable.

## Failure Repair

If simulation settings are stored only as raw XML or loose text files, promote the required fields into this payload before adding export logic.
