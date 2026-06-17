# DICOM Pixel Decode

## Purpose

Define DICOM pixel decoding and volume assembly for common clinical transfer syntaxes.

## Owns

First-pass source files:

```text
src/io/image/DicomPixelDecoder.h
src/io/image/DicomPixelDecoder.cpp
src/io/image/DicomVolumeReader.h
src/io/image/DicomVolumeReader.cpp
tests/io/image/DicomPixelDecoderTests.cpp
```

## Inputs

- DICOM series scanner.
- `XQImageVolume` payload.
- DCMTK, GDCM, CharLS, libjpeg-turbo, and OpenJPEG dependency roles.

## Outputs

- One `XQImageVolume` per selected DICOM series or time frame.

## Rules

- XQ chooses decoders by transfer syntax, not by guessing from file extension.
- DCMTK owns metadata and dataset access.
- GDCM and codec libraries are used behind `DicomPixelDecoder`.
- The decoded result is converted to XQ image geometry and scalar metadata.

## Transfer Syntax Coverage

Full intended coverage:

```text
Implicit VR Little Endian
Explicit VR Little Endian
Explicit VR Big Endian when available
RLE Lossless
JPEG Baseline
JPEG Lossless
JPEG-LS
JPEG 2000 Lossless
JPEG 2000 Lossy when allowed by user policy
```

First source-pass coverage:

```text
Explicit VR Little Endian, uncompressed, single-frame slices
Implicit VR Little Endian, uncompressed, single-frame slices
8-bit unsigned scalar pixels
16-bit signed and unsigned scalar pixels
multi-slice volume assembly through DicomSeriesScanner ordering
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Volume Assembly

Apply:

```text
record rescale slope
record rescale intercept
photometric interpretation handling
pixel representation signedness
slice order from scanner geometry
direction matrix from DICOM orientation
spacing from pixel spacing and slice geometry
```

First source-pass rule:

```text
Pixel data is copied into an XQ-owned decoded buffer.
Rescale slope/intercept are stored as metadata and not destructively applied to the stored scalar buffer.
Unsupported compressed transfer syntaxes must fail inside DicomPixelDecoder, not in UI or project code.
```

## API Contract

`DicomPixelDecoder` owns file-level pixel extraction:

```text
DicomDecodedSlice decodeFile(path)
```

`DicomVolumeReader` owns series-level assembly:

```text
XQDataNode read(const DicomSeriesCandidate&)
```

Output payload:

```text
XQImageVolume
DecodedImageBufferHandle
```

The business layer must not receive `DcmDataset`, `DcmFileFormat`, `DcmPixelData`, GDCM image objects, or codec-native image objects.

## Implementation Contract

Contract owner:

```text
src/io/image/DicomPixelDecoder.h
src/io/image/DicomPixelDecoder.cpp
src/io/image/DicomVolumeReader.h
src/io/image/DicomVolumeReader.cpp
tests/io/image/DicomPixelDecoderTests.cpp
```

Public contract:

```text
DicomPixelDecoder decodes file-level scalar pixel payloads selected by transfer syntax
DicomVolumeReader assembles DicomSeriesCandidate slices into XQDataNode with XQImageVolume
decoded buffers use DecodedImageBufferHandle
metadata records rescale slope/intercept and transfer syntax diagnostics without exposing DCMTK/GDCM objects to business code
```

Forbidden shortcuts:

```text
no codec selection in UI or project code
no DCMTK/GDCM public objects outside IO boundaries
no fake decoded buffers for unsupported compressed transfer syntaxes
```

## Test Plan

Test target:

xq_io_tests or focused DicomPixelDecoder test target

Test file:

tests/io/image/DicomPixelDecoderTests.cpp

Core scenarios:

uncompressed Explicit VR Little Endian scalar slice decodes
uncompressed Implicit VR Little Endian scalar slice decodes
signed and unsigned scalar metadata is preserved
series slices assemble into one XQImageVolume buffer
unsupported compressed transfer syntax fails with diagnostics

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R DicomPixelDecoder --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.

## Step Plan

- [x] Implement first-pass transfer syntax dispatch for uncompressed Little Endian.
- [x] Decode uncompressed pixel data through DCMTK accessors.
- [ ] Decode compressed pixel data through GDCM or codec-specific backends.
- [x] Assemble slice buffers into one volume buffer.
- [x] Build `XQImageVolume` geometry and scalar metadata.
- [x] Add tests for unsigned CT and signed CT using synthetic DICOM files.
- [ ] Add later tests for JPEG-LS and JPEG 2000 samples when controlled sample files exist.

## Acceptance

- Common vendor CT/MR DICOM series can be decoded into `XQImageVolume`.
- Decoder selection is visible in diagnostics.
- Business code never sees DCMTK or GDCM pixel objects.
- initial contract proves uncompressed CT-style synthetic series can become an XQ-owned image node and decoded buffer.

## Failure Repair

If a new transfer syntax requires adding code outside `DicomPixelDecoder`, repair this document and keep codec dispatch centralized.
