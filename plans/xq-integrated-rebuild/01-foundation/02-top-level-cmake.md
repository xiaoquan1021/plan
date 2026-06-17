# Top-Level CMake

## Purpose

Define a single integrated build entrypoint for XQ.

## Inputs

- Empty project skeleton.
- Dependency role map.

## Outputs

- A top-level CMake structure that builds one integrated application and internal libraries.

## Code Ownership

Future files:

```text
CMakeLists.txt
cmake/XQDependencies.cmake
cmake/XQCompilerOptions.cmake
```

## Rules

- Do not recreate old XQ external install assumptions.
- Do not add MITK, BlueBerry, CTK, or SWIG.
- Do not create per-feature plugin targets.
- Keep targets coarse and integrated: core, io, algorithms, workbench, app.

## Implementation Contract

Top-level targets:

```text
xq_core
xq_io
xq_algorithms
xq_workflow
xq_visualization
xq_workbench
XQ
```

Target dependency direction:

```text
xq_core
xq_io -> xq_core
xq_algorithms -> xq_core
xq_workflow -> xq_core
xq_visualization -> xq_core
xq_workbench -> xq_core, xq_io, xq_algorithms, xq_workflow, xq_visualization
XQ -> xq_workbench
```

Forbidden target patterns:

```text
plugin bundles
runtime extension registries
MITK/BlueBerry/CTK targets
per-feature executable targets
```

## Step Plan

- [ ] Define project name and C++ standard.
- [ ] Include dependency configuration from `cmake/XQDependencies.cmake`.
- [ ] Define `xq_core`.
- [ ] Define `xq_io`.
- [ ] Define `xq_algorithms`.
- [ ] Define `xq_workflow`.
- [ ] Define `xq_visualization`.
- [ ] Define `xq_workbench`.
- [ ] Define the `XQ` executable.
- [ ] Link domain feature code through integrated libraries, not plugins.

## Test Plan

Expected commands after CMake files exist:

```text
cmake -S <xq-rebuild-workspace> -B <xq-rebuild-workspace>/build -G Ninja
cmake --build <xq-rebuild-workspace>/build
ctest --test-dir <xq-rebuild-workspace>/build --output-on-failure
```

Expected result:

CMake configures from the blank rebuild root
integrated targets are generated
no MITK, BlueBerry, CTK, or plugin target is configured

## Acceptance

- `CMakeLists.txt` defines the integrated targets and target dependency direction.
- `cmake/XQDependencies.cmake` is the only dependency entrypoint.
- No old external install path from the zip tree is required.

## Failure Repair

If a new target exists only to mimic a old plugin bundle, move its code into the owning integrated library and update this document.

## Do Not Add

- `find_package(MITK)`.
- `find_package(BlueBerry)`.
- `find_package(CTK)`.
- Plugin discovery code.
- Build flags that switch between old and new architecture.
