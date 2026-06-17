# NRRD and MetaImage Reader

## Purpose

Define loading of NRRD and MetaImage files into `XQImageVolume`.

## Owns

First-pass source files:

```text
src/io/image/NrrdImageReader.h
src/io/image/NrrdImageReader.cpp
src/io/image/MetaImageReader.h
src/io/image/MetaImageReader.cpp
tests/io/image/NrrdMetaImageReaderTests.cpp
```

## Inputs

- `XQImageVolume` payload.
- XQ-owned decoded image buffer.
- ITK and VTK dependency roles for later expansion.

## Outputs

- One `XQImageVolume` for each `.nrrd`, `.nhdr`, `.mha`, or `.mhd` image.

## Rules

- Readers are format-specific internally but return the same XQ image payload.
- Header metadata is preserved in image metadata.
- Detached raw data is resolved relative to the image header path.
- initial contract uses XQ-owned text header readers for raw scalar data.
- Compression support follows selected ITK/VTK backend capability later.

## First Source-Pass Boundary

Implement:

```text
MetaImage .mha with LOCAL embedded raw payload
MetaImage .mhd with detached raw payload relative to header
MetaImage gzip-compressed LOCAL payloads through controlled zlib
NRRD raw encoding with attached payload after blank line
NRRD detached raw payload through data file
NRRD gzip encoding with attached payload
3D scalar images
UInt8, Int16, UInt16, Int32, UInt32, Float32, Float64 where straightforward
```

Defer:

```text
bzip2 compression
ASCII payloads
non-3D images
vector/RGB images
byte-order conversion beyond local little-endian first pass
complex measurement frame semantics
```

## Read Contract

Extract:

```text
dimensions
spacing
origin
direction
scalar type
component count
measurement frame when present
header key-value metadata
detached data file references
```

First source-pass metadata keys:

```text
source.format = metaimage or nrrd
metaimage.* raw header keys
nrrd.* raw header keys
```

## Implementation Contract

Contract owner:

```text
src/io/image/NrrdImageReader.h
src/io/image/NrrdImageReader.cpp
src/io/image/MetaImageReader.h
src/io/image/MetaImageReader.cpp
tests/io/image/NrrdMetaImageReaderTests.cpp
```

Public contract:

```text
NrrdImageReader and MetaImageReader read supported paths into XQDataNode
output payload is XQImageVolume with DecodedImageBufferHandle
attached/detached payload paths resolve relative to the header path
header metadata is preserved through XQ-owned metadata keys
```

Forbidden shortcuts:

```text
no format-specific image payload
no ITK/VTK public object exposure through core payloads
no silent acceptance of unsupported compression, byte order, vector/RGB, or non-3D payloads
```

## Test Plan

Test target:

xq_io_tests or focused NrrdMetaImageReader test target

Test file:

tests/io/image/NrrdMetaImageReaderTests.cpp

Core scenarios:

embedded MetaImage raw payload decodes
detached MetaImage raw payload resolves relative to header
attached/detached NRRD raw payload decodes
gzip MetaImage/NRRD payloads inflate through controlled zlib
missing detached data or unsupported encoding fails with diagnostics

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R 'Nrrd|MetaImage' --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.

## Step Plan

- [x] Add NRRD raw reader path.
- [x] Add MetaImage raw reader path.
- [x] Convert geometry into `ImageGeometry`.
- [x] Preserve header key-value metadata.
- [x] Add tests for embedded raw data headers.
- [x] Add tests for detached data headers.
- [x] Add controlled gzip payload coverage for NRRD/MetaImage without changing the public `XQImageVolume` contract.

## Acceptance

- NRRD and MetaImage volumes participate in the same Image to Path workflow.
- Missing detached data is reported as project diagnostics.
- The readers do not introduce a second image model.
- initial contract proves raw and gzip `.mha`, detached `.mhd`, raw and gzip `.nrrd`, and detached `.nhdr`-style NRRD data enter `XQImageVolume` and `DecodedImageBufferHandle`.

## Failure Repair

If format-specific metadata starts driving workflow behavior outside image metadata, add a typed image metadata key and keep consumers format-neutral.
