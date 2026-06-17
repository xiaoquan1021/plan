# ROM and Multiphysics

## Purpose

Define the first-version boundary for reduced-order modeling and multiphysics settings without forcing Python or solver-specific frameworks into the core architecture.

## Owns

Current first source-pass files:

```text
src/core/XQSimulationCase.h
src/core/XQSimulationCase.cpp
src/domain/simulation/XQRomMultiphysicsSettingsService.h
src/domain/simulation/XQRomMultiphysicsSettingsService.cpp
src/io/project/SJBSimulationReader.cpp
src/io/project/SJBSimulationWriter.cpp
tests/domain/simulation/XQRomMultiphysicsSettingsTest.cpp
```

## Inputs

- `XQPath`.
- `XQSurfaceModel`.
- `XQMesh`.
- `XQSimulationCase`.
- Solver export service.

## Outputs

- Typed settings attached to `XQSimulationCase` for ROM and multiphysics preparation.
- Optional XQ-owned `.sjb` extension elements that save and reopen typed settings through native project IO.
- Diagnostics for invalid path references, mesh boundary face mappings, material values, coupling ids, or time/output settings.

## Rules

- ROM and multiphysics are first modeled as XQ data contracts.
- Python may be considered after v1 architecture settles; it is not part of the first integrated core.
- Settings must not be stored as untyped scripting dictionaries.
- SimVascular is an algorithm-level reference for expected workflow content.
- `XQSimulationCase` is a core payload, so ROM and multiphysics data structs live in the core payload contract. Domain simulation code may validate and edit them, but core must not depend on domain libraries.
- `.sjb` read/write may preserve first-pass XQ extension elements for native round-trip; it must not require Python, svSolver, svFSI, MITK, BlueBerry, CTK, or plugin classes.
- Missing optional ROM or multiphysics settings is valid for ordinary 3D simulation cases.

## First Data Contracts

ROM settings:

```text
centerline source
branch definitions
inlet/outlet mapping
resistance and capacitance parameters
time settings
output controls
```

Multiphysics settings:

```text
fluid material
wall model
coupling type
boundary coupling ids
solver-prep options
```

## Implementation Contract

Core payload additions:

```text
RomBoundaryRole
RomBranchDefinition
RomBoundaryMapping
RomResistanceCapacitanceParameter
RomOutputControls
RomSettings
MultiphysicsCouplingType
MultiphysicsWallModel
BoundaryCoupling
SolverPrepOptions
MultiphysicsSettings
XQSimulationCase::romSettings()
XQSimulationCase::setRomSettings(...)
XQSimulationCase::clearRomSettings()
XQSimulationCase::multiphysicsSettings()
XQSimulationCase::setMultiphysicsSettings(...)
XQSimulationCase::clearMultiphysicsSettings()
```

Domain validation service:

```text
XQRomMultiphysicsDiagnostic
XQRomMultiphysicsValidationResult
XQRomMultiphysicsSettingsService::validateRomSettings(const XQScene&, const XQMesh&, const XQSimulationCase&)
XQRomMultiphysicsSettingsService::validateMultiphysicsSettings(const XQMesh&, const XQSimulationCase&)
XQRomMultiphysicsSettingsService::validateSettings(const XQScene&, const XQMesh&, const XQSimulationCase&)
```

Validation rules:

```text
ROM centerline and branch source nodes must exist in XQScene and be XQ Path nodes when present.
ROM branches must have non-empty names, positive segment counts, and non-decreasing arc-length ranges.
ROM boundary mappings must reference existing XQMesh boundary face ids and existing ROM branch names.
ROM resistance must be positive and capacitance must be non-negative.
ROM time step and step count must be positive when ROM settings are present.
Multiphysics fluid density and viscosity must be positive.
Multiphysics wall model name must be non-empty; thickness, elastic modulus, and Poisson ratio must be non-negative.
Multiphysics boundary couplings must reference existing XQMesh boundary face ids and non-empty coupling ids.
```

First-pass `.sjb` extension:

```text
job/xq_rom_settings
job/xq_rom_settings/branch
job/xq_rom_settings/boundary_mapping
job/xq_rom_settings/rc_parameter
job/xq_rom_settings/output_field
job/xq_multiphysics_settings
job/xq_multiphysics_settings/fluid
job/xq_multiphysics_settings/wall_model
job/xq_multiphysics_settings/boundary_coupling
job/xq_multiphysics_settings/solver_prep
```

External dependency boundary:

```text
forbidden in public API: Python, Qt, VTK, MITK, BlueBerry, CTK, svSolver, svFSI, SimVascular plugin classes
allowed implementation dependency: tinyxml2 inside project IO only
```

## Step Plan

- [x] Add failing tests in `tests/domain/simulation/XQRomMultiphysicsSettingsTest.cpp`.
- [x] Extend `XQSimulationCase` with optional typed ROM and multiphysics settings.
- [x] Add `XQRomMultiphysicsSettingsService` validation for scene path sources, mesh boundary faces, material values, coupling ids, and time/output settings.
- [x] Extend `SJBSimulationWriter` to write XQ ROM/multiphysics extension elements.
- [x] Extend `SJBSimulationReader` to reopen the XQ extension elements as typed settings.
- [x] Add `xq_rom_multiphysics_settings_tests` to CMake.
- [x] Run focused ROM/multiphysics tests.
- [x] Run adjacent simulation and native IO tests.
- [x] Run full build and full test suite.

## Test Plan

Test target:

xq_rom_multiphysics_settings_tests

Test file:

tests/domain/simulation/XQRomMultiphysicsSettingsTest.cpp

Core scenarios:

XQRomMultiphysicsSettingsAttachTypedContractsToSimulationCase
XQRomMultiphysicsSettingsRoundTripThroughSjb
XQRomMultiphysicsSettingsValidateSceneAndMeshReferences
XQRomMultiphysicsSettingsRejectInvalidReferences

Expected commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_rom_multiphysics_settings_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQRomMultiphysicsSettings --output-on-failure
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build -R 'XQ(RomMultiphysicsSettings|BoundaryConditionService|SolverExportService|NativeProjectFormat)' --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

Expected pass condition:

focused ROM/multiphysics tests pass
adjacent simulation and native project IO tests pass
full test suite passes

Minimum negative case:

invalid ROM source path node, missing boundary face id, negative resistance, empty multiphysics coupling id, or non-positive material/time values returns diagnostics and valid=false

TDD red record:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_rom_multiphysics_settings_tests
```

failed before implementation because tests/domain/simulation/XQRomMultiphysicsSettingsTest.cpp
included domain/simulation/XQRomMultiphysicsSettingsService.h and that service did not
exist yet.

## Acceptance

- ROM and multiphysics data can be saved and reopened as typed XQ settings.
- Future solver integrations can consume these settings without changing core scene architecture.
- No Python dependency is required for first-version project loading.
- Validation diagnostics identify whether the bad reference is a path node, mesh face id, material value, coupling id, or time/output field.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If ROM or multiphysics work starts by embedding a scripting runtime into core project loading, repair this document and model the data contract first.
