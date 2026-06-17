# XQ Native Save Format

## Purpose

Define the future XQ-native save format while preserving first-version ability to open SimVascular-style project directories.

## Owns

Future source files:

```text
src/io/project/XQNativeProjectWriter.h
src/io/project/XQNativeProjectWriter.cpp
src/io/project/XQNativeProjectReader.h
src/io/project/XQNativeProjectReader.cpp
tests/io/project/XQNativeProjectFormatTest.cpp
```

## Inputs

- `XQProject`, `XQScene`, and all native payload types.
- Existing project-format readers.

## Outputs

- A single XQ-native project directory format for saving new projects.
- Optional preservation of original SimVascular-style files when a project was opened from them.

## Rules

- The native save format belongs to XQ, not to old plugin modules.
- Saving does not require MITK project storage.
- XQ may write VTK XML files for geometry and XML/SQLite for project metadata.
- Save format design must not weaken the requirement to directly open `<acceptance-project>`.

## Proposed Layout

```text
project.xqproj
data/images
data/paths
data/contours
data/segmentations
data/models
data/meshes
data/simulations
index/xq.sqlite
```

## Implementation Contract

Public API surface:

```text
XQNativeProjectWriter
XQNativeProjectReader
XQNativeProjectWriter::write(project, outputDirectory)
XQNativeProjectReader::read(projectDirectory)
```

Save ownership:

```text
project.xqproj stores project identity and scene manifest
initial contract stores stable node keys, metadata, payload paths, and source relations in project.xqproj
index/xq.sqlite is deferred until large-project indexing requires it
data folders store payload files
original source provenance is preserved in metadata
```

Dependency boundary:

```text
tinyxml2 writes and reads project.xqproj in the initial contract
SQLite is reserved for future project IO indexing only
existing VTK XML-shaped writers are used for model and mesh metadata payloads
generated model and mesh geometry handles persist through first-pass ASCII VTK XML `.vtp`/`.vtu` files
old plugin storage is not used
segmentation masks use a small XQ-owned `.xqmask` XML file with geometry,
optional source image node id, and active voxel coordinates; no VTK, ITK, MITK,
or image-overlay widget state is serialized
```

## Step Plan

- [x] Define `project.xqproj` as the root manifest.
- [x] Store scene node identity, metadata, payload file paths, and source relations in `project.xqproj`.
- [x] Store payload files under `data/*` using existing XQ-owned project IO writers.
- [x] Preserve original source metadata for SimVascular-style loaded projects.
- [x] Add round-trip tests for Path -> ContourGroup -> SurfaceModel -> Mesh -> SimulationCase chains.
- [x] Add `.xqmask` save/reopen support for XQ-owned segmentation masks.
- [x] Add `.xqimage` save/reopen support for XQ-owned decoded image buffers.

## Initial Contract Scope

Implement now:

```text
save empty XQ projects
save and reopen XQ-owned paths, contour groups, surface models, meshes, and simulation cases
save and reopen XQ-owned segmentation masks under `data/segmentations/*.xqmask`
save and reopen VTI-backed image volumes created by the current VTI reader
save and reopen decoded image buffers under `data/images/*.xqimage` when there is no copyable `.vti` source
save and reopen generated triangle model geometry plus generated surface/volume mesh geometry through the project IO writers/readers
preserve source relations from the XQScene graph
preserve node metadata, including original SimVascular source provenance
write data folders under data/* instead of old root-level plugin folders
```

Defer:

```text
SQLite index/xq.sqlite
compact compressed/chunked native image payloads for large decoded image volumes
compact compressed/appended writer variants for large generated geometry and exact source-backed loaded VTK payload preservation beyond the current metadata/count scaffold
```

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQNativeProjectFormat --output-on-failure
```

Required cases:

save an empty project
save and reopen a Path -> ContourGroup chain
save and reopen Image -> Path -> ContourGroup -> SurfaceModel -> Mesh -> SimulationCase for supported payloads
preserve source relations
preserve source provenance from a SimVascular-style opened project
preserve relation kind names including image-to-segmentation-mask
round-trip XQSegmentationMask geometry, source image relation, and active voxels through `.xqmask`
round-trip decoded image geometry, scalar type, intensity range, signed voxel bytes, and original source metadata through `.xqimage`
round-trip generated model triangle geometry and generated mesh surface/volume geometry through ASCII VTK XML project IO payload files
preserve generated model and mesh geometry across save -> reopen -> save -> reopen
reject save output that mirrors old plugin folders

## Acceptance

- XQ-created projects save and reopen without old external project managers.
- A loaded SimVascular-style project can be saved as XQ-native while preserving source provenance.
- The save format records source relations explicitly.

## Failure Repair

If the native format becomes a direct mirror of old plugin folders, repair this document and return to XQ-owned scene and payload contracts.
