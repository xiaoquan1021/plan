# NIfTI Reader

## Purpose

Define NIfTI image loading into `XQImageVolume` for common research and clinical export workflows.

## Owns

First-pass source files:

```text
src/io/image/DecodedImageBufferHandle.h
src/io/image/DecodedImageBufferHandle.cpp
src/io/image/NiftiImageReader.h
src/io/image/NiftiImageReader.cpp
tests/io/image/NiftiImageReaderTests.cpp
```

## Inputs

- `XQImageVolume` payload.
- XQ-owned decoded image buffer.
- ITK, VTK, or nifti_clib dependency role for later expansion.

## Outputs

- One `XQImageVolume` per `.nii` or `.nii.gz` file in the initial contract.
- `.nii.gz` support through the controlled zlib dependency.

## Rules

- Public output is `XQImageVolume`.
- initial contract uses an XQ-owned NIfTI-1 header reader for uncompressed `.nii`.
- Later reader internals may use ITK, VTK, or nifti_clib according to the dependency role map.
- Orientation, spacing, origin, and scalar type are mandatory.
- NIfTI support does not replace DICOM support.

## First Source-Pass Boundary

Implement:

```text
NIfTI-1 single-file .nii
little-endian header
uncompressed scalar voxel payload
3D image dimensions
datatype UInt8, Int16, UInt16, Int32, UInt32, Float32, Float64 when straightforward
sform-based origin/direction/spacing when sform_code > 0
pixdim fallback when sform is absent
DecodedImageBufferHandle as the XQ-owned payload buffer
```

Defer:

```text
NIfTI-2
4D time series
RGB/vector images
complex numbers
qform quaternion reconstruction beyond storing raw metadata
writer support
```

## Read Contract

Extract:

```text
dimensions
spacing
origin
qform/sform orientation
scalar type
component count
intent metadata when useful
compression source
```

First source-pass metadata keys:

```text
source.format = nifti
source.relative_path
nifti.compression
nifti.magic
nifti.datatype
nifti.bitpix
nifti.qform_code
nifti.sform_code
nifti.vox_offset
```

## Implementation Contract

Contract owner:

```text
src/io/image/DecodedImageBufferHandle.h
src/io/image/DecodedImageBufferHandle.cpp
src/io/image/NiftiImageReader.h
src/io/image/NiftiImageReader.cpp
tests/io/image/NiftiImageReaderTests.cpp
```

Public contract:

```text
NiftiImageReader reads supported .nii and .nii.gz paths into XQDataNode
output payload is XQImageVolume with DecodedImageBufferHandle
geometry, scalar type, qform/sform metadata, and compression source are stored through XQ-owned types
```

Forbidden shortcuts:

```text
no format-specific image payload
no ITK/VTK/nifti_clib public objects exposed through core payloads
no silent acceptance of unsupported dimensionality or vector/RGB payloads
```

## Test Plan

Test target:

xq_io_tests or focused NiftiImageReader test target

Test file:

tests/io/image/NiftiImageReaderTests.cpp

Core scenarios:

uncompressed .nii scalar payload enters XQImageVolume
.nii.gz inflates through controlled zlib and enters the same payload type
sform geometry converts to ImageGeometry
unsupported NIfTI-2, 4D, vector/RGB, or complex payloads fail with diagnostics

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R NiftiImageReader --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.

## Step Plan

- [x] Keep the first-pass reader backend XQ-owned; do not add ITK/VTK/nifti_clib for this pass.
- [x] Read uncompressed `.nii`.
- [x] Convert sform orientation into XQ image geometry.
- [x] Preserve qform and sform metadata.
- [x] Add tests for scalar type, geometry conversion, and decoded buffer ownership.
- [x] Add `.nii.gz` gzip inflate through controlled zlib while still returning `XQImageVolume` and `DecodedImageBufferHandle`.

## Acceptance

- NIfTI images appear in the same scene group as DICOM and VTI images.
- MPR views use the same `XQImageVolume` API for NIfTI.
- Path tools do not know which image file format created the volume.
- initial contract proves `.nii` and `.nii.gz` scalar data enter `XQImageVolume` and `DecodedImageBufferHandle`, not a format-specific payload.

## Failure Repair

If NIfTI loading creates a separate image payload, merge it back into `XQImageVolume`.
