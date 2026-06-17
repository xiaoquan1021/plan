# Open Project Directory

## Purpose

Define how XQ opens a project directory such as `<acceptance-project>` as a native XQ project.

## Owns

Future source files:

```text
src/io/project/XQProjectDirectoryReader.h
src/io/project/XQProjectDirectoryReader.cpp
tests/io/project/XQProjectDirectoryReaderTest.cpp
```

## Inputs

- `XQProject` lifecycle.
- `.svproj` manifest reader.
- Native readers for image, path, contour, model, mesh, and simulation files.

## Outputs

- One `XQProject` with a populated `XQScene`.
- Project diagnostics for files that are present but unreadable.

## Rules

- Opening a SimVascular-style directory is a native XQ load path.
- Do not call this layer a compatibility importer.
- Do not require old SimVascular or MITK project services.
- File discovery must be deterministic and based on project directory structure.

## Directory Contract

Recognized directories:

```text
Images
Paths
Segmentations
Models
Meshes
Simulations
```

Recognized project file:

```text
*.svproj
```

## Load Order

```text
project manifest
image volumes
paths
contour groups
surface models
meshes
simulation cases
source relations
diagnostics
```

## Implementation Contract

Public API surface:

```text
XQProjectDirectoryReader
XQProjectDirectoryReader::canOpen(rootDirectory)
XQProjectDirectoryReader::open(rootDirectory)
ProjectDirectoryScanResult
ProjectLoadDiagnostic
```

Reader ownership:

```text
project directory reader orchestrates load order
format-specific readers create payloads and nodes
scene relation resolver connects nodes after all files are scanned
```

Forbidden shortcuts:

```text
UI-driven import sequence
loose imported file list
compatibility project object
old SimVascular project manager
```

## Step Plan

- [ ] Detect the project root and `.svproj` file.
- [ ] Create an `XQProject` with origin `SimVascularDirectory`.
- [ ] Discover files in fixed project subdirectories.
- [ ] Load files in dependency order.
- [ ] Connect source relations after all nodes are present.
- [ ] Record diagnostics for unread files without mutating loaded nodes.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQProjectDirectoryReader --output-on-failure
```

Required fixture:

<acceptance-project>

Required cases:

detect .svproj at project root
discover Images, Paths, Segmentations, Models, Meshes, and Simulations
load nodes in dependency order
resolve source relations after all nodes exist
report diagnostics without replacing XQProject or XQScene ownership

## Acceptance

- `<acceptance-project>` opens through this path.
- The result is a populated XQ scene, not a set of loose imported files.
- A missing optional directory does not change the architecture or create a second load path.

## Failure Repair

If project loading becomes a chain of UI commands or feature-specific import dialogs, repair this document and route all project directory loading through this reader.
