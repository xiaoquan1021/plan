# Simulation Solver Export

## Purpose

Define generation of solver-preparation files from `XQMesh` and `XQSimulationCase`.

The initial contract exports deterministic solver-preparation artifacts from
XQ-owned payloads. It validates mesh boundary rows and typed simulation boundary
conditions before writing. It may preserve old solver files as source
references, but export must be generated from `XQMesh` and `XQSimulationCase`,
not by copying existing SimVascular output.

## Owns

Current source-pass files:

```text
src/domain/simulation/XQSolverExportService.h
src/domain/simulation/XQSolverExportService.cpp
src/io/project/SolverFileWriters.h
src/io/project/SolverFileWriters.cpp
tests/domain/simulation/XQSolverExportServiceTest.cpp
```

## Inputs

- `XQMesh`.
- `XQSimulationCase`.
- Native simulation reader.
- Mesh boundary transfer.
- Simulation boundary condition validation.
- Export options with output directory and job name.

## Outputs

- Solver-preparation files such as mesh files, boundary files, inflow files, RCR files, and solver input files.
- Export diagnostics for missing mesh geometry, missing required boundary
  conditions, unsupported condition types, or write failures.
- A generated-file manifest for the export operation.

## Rules

- Export is generated from XQ payloads.
- Existing solver files may be preserved as source references, but the export service must not depend on editing them manually.
- Export code is separate from UI panels.
- Solver-specific file syntax stays inside writer classes.
- The export service must call the simulation boundary condition validation
  contract before writing files.
- The initial contract writes deterministic text/XML preparation files; final
  svSolver-compatible binary/geombc output may be added later behind the same
  service.
- Export failure must be explicit and diagnostic; do not silently skip missing
  required files.
- Public API must not expose VTK, Qt, MITK, BlueBerry, CTK, svSolver, or old
  plugin objects.

## Export Files

First-version writers:

```text
solver.inp
inflow.flow
rcrt.dat
resistance.dat
bct.vtp
*.svpre
mesh geometry files from XQMesh
export-manifest.txt
```

First-pass file meaning:

```text
solver.inp: density, viscosity, time settings, restart frequency, inflow/RCR/resistance face lists
inflow.flow: sorted time/flow-rate rows from InflowCondition, with scale applied
rcrt.dat: RCR face values in deterministic face-id order
resistance.dat: resistance face values in deterministic face-id order
*.svpre: deterministic preparation commands referencing generated files and mesh boundary face ids
bct.vtp: first-pass XML carrier for inflow face id, period, and waveform sample count
mesh-complete/mesh-complete.mesh.vtu: first-pass XML/text unstructured-grid carrier for XQTetrahedralVolumeMeshHandle
export-manifest.txt: generated file list and source summary
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Implementation Contract

Public service types:

```text
XQSolverExportOptions
XQSolverExportDiagnostic
XQSolverExportResult
XQSolverExportService
```

Minimum public operation:

```text
exportSimulation(const XQMesh&, const XQSimulationCase&, XQSolverExportOptions) -> XQSolverExportResult
```

Writer helpers:

```text
SolverFileWriters::writeSolverInput(...)
SolverFileWriters::writeInflowFile(...)
SolverFileWriters::writeRcrFile(...)
SolverFileWriters::writeResistanceFile(...)
SolverFileWriters::writeBctVtp(...)
SolverFileWriters::writeSvPre(...)
SolverFileWriters::writeVolumeMesh(...)
SolverFileWriters::writeManifest(...)
```

Validation before writing:

```text
output directory must be provided
job name must be non-empty
mesh must contain at least one boundary face
mesh must contain a volume grid handle
simulation boundary conditions must validate against mesh boundary faces
at least one inflow condition must exist
RCR/resistance output is generated only when corresponding typed conditions exist
```

Generated path layout:

```text
<output>/<jobName>/solver.inp
<output>/<jobName>/inflow.flow
<output>/<jobName>/rcrt.dat
<output>/<jobName>/resistance.dat
<output>/<jobName>/<jobName>.svpre
<output>/<jobName>/bct.vtp
<output>/<jobName>/mesh-complete/mesh-complete.mesh.vtu
<output>/<jobName>/export-manifest.txt
```

External dependency boundary:

```text
forbidden in public service/core API: Qt, VTK, MITK, BlueBerry, CTK, svSolver, SimVascular plugin classes
allowed later inside writer implementation only: solver-specific formatting and VTK XML writers
```

## Step Plan

- [x] Add `src/io/project/SolverFileWriters.h`.
- [x] Add `src/io/project/SolverFileWriters.cpp`.
- [x] Add `src/domain/simulation/XQSolverExportService.h`.
- [x] Add `src/domain/simulation/XQSolverExportService.cpp`.
- [x] Extend `xq_domain_simulation` CMake target with solver export sources.
- [x] Add `tests/domain/simulation/XQSolverExportServiceTest.cpp`.
- [x] Validate mesh boundary records and simulation boundary conditions.
- [x] Generate inflow waveform file from typed data.
- [x] Generate RCR/resistance files from typed data.
- [x] Generate first-pass boundary condition XML carrier.
- [x] Generate first-pass mesh geometry carrier from `XQTetrahedralVolumeMeshHandle`.
- [x] Generate solver input, preparation command file, and manifest.
- [x] Add tests comparing generated file structure against acceptance project expectations.

## Test Plan

Test target:

xq_solver_export_service_tests

Test file:

tests/domain/simulation/XQSolverExportServiceTest.cpp

Core scenarios:

XQSolverExportServiceWritesSolverPreparationFiles
XQSolverExportServiceReportsMissingRequiredBoundaryConditions
XQSolverExportServiceRejectsMissingVolumeMesh

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_solver_export_service_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQSolverExportService --output-on-failure
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_solver_export_service_tests
```

failed before implementation because tests/domain/simulation/XQSolverExportServiceTest.cpp
included domain/simulation/XQSolverExportService.h and that service did not
exist yet.

## Acceptance

- A loaded simulation case can be exported without reading raw `.sjb` at export time.
- Generated files are traceable back to mesh face ids and boundary condition records.
- Export failure diagnostics identify the missing payload field.
- First-pass output includes `solver.inp`, `inflow.flow`, `rcrt.dat`,
  `resistance.dat`, `bct.vtp`, `<jobName>.svpre`, mesh geometry carrier, and a
  manifest when the corresponding typed data exists.
- The service rejects missing required boundary conditions or missing volume
  mesh geometry before writing incomplete solver prep.

## Failure Repair

If solver export copies old files without understanding XQ data, repair this service before treating simulation prep as complete.
