# Dependency Role Map

## Purpose

Assign each external dependency one primary responsibility so XQ does not become a dependency-driven architecture.

## Inputs

- Industry observations from 3D Slicer, MITK, ITK-SNAP, Orthanc, OsiriX/Horos/Miele-LXIV, and SimVascular.
- User decision to accept a medical-platform dependency stack.

## Outputs

- Required, lightweight-addition, optional, and excluded dependency lists.

## Code Ownership

Current files:

```text
cmake/XQDependencies.cmake
cmake/check-controlled-dependency-boundary.cmake
```

## Rules

- Dependencies are kernels below XQ-owned interfaces.
- No external dependency type appears in `XQProject`, `XQScene`, or workflow public APIs unless explicitly wrapped.
- MITK, BlueBerry, CTK, and SWIG are excluded from the integrated architecture.

## Implementation Contract

`cmake/XQDependencies.cmake` exposes dependency variables only to the layer that owns the kernel:

```text
Qt6 -> app and workbench
VTK -> visualization, image IO, model/mesh geometry internals
ITK -> image IO and image algorithms
DCMTK -> DICOM scanner and metadata IO
GDCM/codecs -> DICOM pixel decoder internals
OpenCASCADE -> modeling algorithms
MMG -> meshing algorithms
tinyxml2 -> project IO
SQLite -> project and DICOM index
Eigen -> core math and algorithms
```

Public core headers must use XQ-owned value types instead of dependency public classes.

The main application build must not download or vendor dependency source through feature-local `FetchContent` once that dependency is part of the controlled superbuild. Current first enforced case:

```text
tinyxml2 -> find_package(tinyxml2 CONFIG REQUIRED) from <xq-rebuild-workspace>/externals/install
```

## Required Dependencies

| Dependency | Primary role |
| --- | --- |
| Qt6 | Application UI and event loop. |
| VTK | Rendering, polydata, image data, mesh data, VTK XML IO. |
| ITK | Medical image algorithms and IO support. |
| DCMTK | DICOM metadata, series scanning, private tags, DICOMDIR, network-ready semantics. |
| GDCM | DICOM pixel decode and transfer-syntax fallback. |
| OpenCASCADE | Modeling kernel for solid/surface operations when VTK is insufficient. |
| MMG | Mesh improvement and remeshing kernel. |
| tinyxml2 | Native `.svproj/.pth/.ctgr/.mdl/.msh/.sjb` XML reading and writing. |
| SQLite | Local project and DICOM series index. |

## Lightweight Medical Additions

| Dependency | Primary role |
| --- | --- |
| CharLS | JPEG-LS decode. |
| libjpeg-turbo | JPEG decode/encode. |
| OpenJPEG | JPEG 2000 decode. |
| libtiff | TIFF and OME-TIFF support. |
| nifti_clib | Explicit NIfTI support if ITK/VTK coverage is insufficient. |
| Eigen | Matrix, transform, frame, and geometry math. |
| libdeflate or zstd | Compression for caches and packaged project data. |

## Optional Later

- HDF5 for large results or future simulation containers.
- Python for automation after v1 architecture settles.
- dcmqi for DICOM SEG and quantitative imaging exchange.
- TetGen or Netgen after licensing and release packaging are decided.

## Step Plan

- [x] Add tinyxml2 through the controlled dependency role table.
- [x] Add a CMake boundary check that rejects tinyxml2 FetchContent in the main application build.
- [ ] Add future dependencies only through the role table.
- [ ] When a new dependency is proposed, assign it a single primary role.
- [ ] If a dependency overlaps another role, decide which one owns the responsibility before implementation.

## Test Plan

Expected command after CMake dependency files exist:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQControlledDependencyBoundary --output-on-failure
bash -lc '! rg -n "find_package\\((MITK|BlueBerry|CTK)|\\b(mitk|berry|ctk)::|\\bSWIG\\b" <xq-rebuild-workspace>/CMakeLists.txt <xq-rebuild-workspace>/cmake/XQDependencies.cmake <xq-rebuild-workspace>/src'
```

Expected result:

XQControlledDependencyBoundary passes
no matches

Expected dependency boundary check after source files exist:

```text
rg -n "vtk|itk|DCMTK|GDCM|TopoDS|MMG" <xq-rebuild-workspace>/src/core
```

Expected result:

only allowed wrapper-handle declarations appear in core payload internals

## Acceptance

- Every dependency has one primary role.
- Excluded dependencies are not configured.
- Core public APIs remain XQ-owned.
- Main application CMake does not use dependency-local source downloads for dependencies that are already owned by the controlled superbuild.

## Failure Repair

If business code starts depending on DCMTK/GDCM/ITK/OCCT/MMG classes directly, repair the owning feature document and move the dependency behind an XQ interface.

## Do Not Add

- MITK.
- BlueBerry.
- CTK.
- SWIG.
- External library object graphs as XQ's project data model.
