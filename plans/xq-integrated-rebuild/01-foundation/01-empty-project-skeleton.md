# Empty Project Skeleton

## Purpose

Define the blank new XQ project layout before any old code is selected or rewritten.

## Inputs

- Source boundary rules.
- Architecture first discipline.

## Outputs

- A new source tree shape for the integrated XQ application.
- Initial ownership boundaries for source folders.

## Code Ownership

Future implementation root: `<xq-rebuild-workspace>`.

`<xq-implementation-workspace>` is the active refactor workspace. It may be used as the final implementation target only after this plan is explicitly updated before source changes begin. It must not be used as a source tree to continue from.

Planned top-level source folders:

```text
src/app
src/core
src/io
src/algorithms
src/workbench
src/visualization
src/workflow
src/domain
tests
externals
cmake
```

## Rules

- Start from an empty source layout.
- Create files from scratch in `<xq-rebuild-workspace>`.
- Do not copy the old XQ module/plugin tree.
- Do not create `Plugins`, `Modules`, or BlueBerry-style names.
- Keep folders organized by integrated responsibility, not by old framework ownership.

## Implementation Contract

Create only directories and placeholder build files needed by the foundation layer:

```text
<xq-rebuild-workspace>/CMakeLists.txt
<xq-rebuild-workspace>/cmake/XQCompilerOptions.cmake
<xq-rebuild-workspace>/cmake/XQDependencies.cmake
<xq-rebuild-workspace>/src/app
<xq-rebuild-workspace>/src/core
<xq-rebuild-workspace>/src/io
<xq-rebuild-workspace>/src/algorithms
<xq-rebuild-workspace>/src/domain
<xq-rebuild-workspace>/src/workflow
<xq-rebuild-workspace>/src/workbench
<xq-rebuild-workspace>/src/visualization
<xq-rebuild-workspace>/tests
<xq-rebuild-workspace>/externals
```

Do not create feature source files until the owning child document has passed the hardening standard.

## Step Plan

- [ ] Create `<xq-rebuild-workspace>` as the blank implementation root.
- [ ] Confirm the implementation root is not being used as audit record.
- [ ] Create the future project root with only structural directories.
- [ ] Add a single top-level `CMakeLists.txt`.
- [ ] Add `src/app` for executable startup.
- [ ] Add `src/core` for project, scene, data, metadata, and identifiers.
- [ ] Add `src/io` for native project and medical image IO.
- [ ] Add `src/domain` for vascular domain payloads and operations.
- [ ] Add `src/workflow` for stage progression and source relations.
- [ ] Add `src/workbench` and `src/visualization` for Qt/VTK presentation.

## Test Plan

Expected command after the skeleton exists:

```text
test -d <xq-rebuild-workspace>/src/core
test -d <xq-rebuild-workspace>/src/io
test -d <xq-rebuild-workspace>/src/domain
test -d <xq-rebuild-workspace>/src/workbench
test -d <xq-rebuild-workspace>/src/visualization
test ! -d <xq-rebuild-workspace>/Plugins
test ! -d <xq-rebuild-workspace>/Modules
```

Expected result:

all required directories exist
old plugin-style directories do not exist

## Acceptance

- `<xq-rebuild-workspace>` exists and contains only the planned foundation structure.
- No source file is copied from `<xq-source-extract>`.
- No plan or source file is written under `<xq-implementation-workspace>`.

## Failure Repair

If a future folder mirrors `<xq-source-extract>/Code/Source/xq4gui/Plugins`, repair this document and the affected skeleton before adding feature code.

## Do Not Add

- Old plugin folders.
- Generated framework scaffolding.
- Temporary executable-only source trees that cannot absorb the domain model.
- Source files copied into place before their owning feature document is selected.
