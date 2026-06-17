# VTI, MINC, and TIFF Reader

## Purpose

Define loading of VTK image data and first-pass TIFF image sources into `XQImageVolume`.

MINC remains in this owning document, but it is not part of the current contract because a real MINC reader requires a separate dependency decision around HDF5/netCDF/ITK-style image IO. That decision must be made before source files are added for MINC.

The current contracts extend the VTI reader so the acceptance VTI image, synthetic inline ASCII VTI images, synthetic inline binary VTI images, and synthetic raw appended VTI images create XQ-owned contiguous decoded voxel buffers. The latest VTI implementation contracts also read optional `ImageData Direction` matrices into `ImageGeometry::direction` and reject non-`LittleEndian` VTI `byte_order` values plus non-zlib `VTKFile compressor` values before any scalar payload decode, including inline ASCII inputs. This is the smallest upstream fix required after the MPR rasterizer pass, because slice rasterization now consumes decoded buffers and XQ-owned geometry rather than XML-only VTI metadata handles.

This document adds an XQ-owned unified image-volume dispatch layer for
project directory imports. `XQProjectDirectoryReader` now asks
`XQImageVolumeReader` whether an image path is supported and routes supported
image files through the existing VTI, NIfTI, NRRD, MetaImage, TIFF, and DICOM
first-pass readers instead of hand-written VTI/TIFF-only branches.

This document rejects non-`ImageData` `VTKFile` types, VTI
files whose `VTKFile byte_order` is not `LittleEndian`, VTI files with
non-zlib `VTKFile compressor` values, VTI files with multiple `ImageData`
children, VTI `ImageData` with missing
`WholeExtent`, VTI `ImageData` with multiple `Piece` children, VTI `ImageData`
whose single `Piece Extent` does not match `WholeExtent`, VTI `Piece` elements
with multiple `PointData` children, malformed VTI component-count attributes
including trailing garbage, VTI
`PointData` whose `Scalars` attribute does not match the single `DataArray
Name`, VTI scalar `DataArray` inputs with no active scalar array name, invalid
VTI extent order inputs, VTI extent inputs with extra values, VTI spacing vector
inputs with extra values, malformed VTI appended `DataArray offset` attributes,
VTI files with multiple `AppendedData` children even when the active scalar
array is inline ASCII, and VTI `PointData` with multiple `DataArray` children
during this first-pass scalar reader instead of silently choosing a
compatible-looking child element or misrepresenting an ambiguous image root,
ambiguous appended data, unsupported byte order, unsupported compressor,
malformed appended offset, malformed inline binary base64 padding tails or nonzero pad bits, partial piece, ambiguous point-data element,
inactive scalar array, anonymous scalar array, out-of-range inline ASCII scalar
payloads, or malformed image geometry as a full scalar volume.

## Owns

Future source files:

```text
src/io/image/VtiImageReader.h
src/io/image/VtiImageReader.cpp
src/io/image/TiffImageReader.h
src/io/image/TiffImageReader.cpp
src/io/image/XQImageVolumeReader.h
src/io/image/XQImageVolumeReader.cpp
tests/io/image/VtiImageReaderTests.cpp
tests/io/image/TiffImageReaderTests.cpp
tests/io/project/ProjectDirectoryReaderTests.cpp
```

## Inputs

- `XQImageVolume` payload.
- Existing XQ-owned image payload and decoded image buffer.
- Native project directory reader.

## Outputs

- One `XQImageVolume` for VTI or TIFF image sources.

## Rules

- VTI support is mandatory for `<acceptance-project>/Images/OSMSC0090-cm.vti`.
- TIFF support starts as an XQ-owned baseline reader for uncompressed little-endian grayscale TIFF, including single-strip payloads, multi-strip payloads with LONG strip arrays, and inline SHORT strip arrays.
- Baseline TIFF inputs with zero `ImageWidth` or zero `ImageLength` must be rejected instead of creating empty decoded buffers or fake single-slice image volumes.
- Multi-page TIFF decoding, OME-TIFF, tiled TIFF, BigTIFF, JPEG/LZW/Deflate compression, color images, and vendor metadata semantics are deferred; multi-page inputs must be rejected in this document.
- MINC support is deferred until its dependency boundary is explicitly selected.
- Current VTI decoded-buffer support covers XML `AppendedData encoding="base64"` with `vtkZLibDataCompressor`, raw appended uncompressed binary scalar payloads, inline ASCII scalar `DataArray` payloads with target scalar type range validation, inline uncompressed binary scalar `DataArray` payloads, inline binary base64 canonical padding and zero pad-bit validation, optional `ImageData Direction` matrices, one scalar `PointData` array, `VTKFile byte_order="LittleEndian"` scalar pixels, and a supported XQ scalar type.
- Unsupported VTI file types, non-`LittleEndian` `VTKFile byte_order` values, non-zlib `VTKFile compressor` values, encodings, malformed inline binary base64 padding or nonzero pad bits, malformed component-count attributes, malformed appended offset attributes, malformed extent length/order, malformed spacing/origin vector length, multiple image roots, missing image `WholeExtent`, multiple appended-data elements regardless of the active `DataArray` format, multiple image pieces, multiple point-data elements, mismatched VTI `WholeExtent`/single `Piece Extent`, mismatched VTI `PointData Scalars`/single `DataArray Name`, missing or anonymous scalar `DataArray Name` values, multiple point scalar arrays, or multi-component/vector arrays must fail with diagnostics rather than creating fake decoded buffers.
- TIFF reader must create `XQImageVolume` with `DecodedImageBufferHandle`, not a plugin shell or old framework wrapper.
- Project directory image imports must use the unified `XQImageVolumeReader`
  dispatch contract, not per-format branches inside `XQProjectDirectoryReader`.
- Unified dispatch reuses existing first-pass readers and must not introduce a
  second image payload type or plugin wrapper.
- Project-level DICOM dispatch may scan the image folder and must avoid inserting
  duplicate scene nodes for multiple files from the same DICOM series.

## Implementation Contract

Decoded VTI contract owns:

```text
src/io/image/VtiImageReader.h
src/io/image/VtiImageReader.cpp
tests/io/image/VtiImageReaderTests.cpp
cmake/XQDependencies.cmake
```

Existing TIFF contract owns:

```text
src/io/image/TiffImageReader.h
src/io/image/TiffImageReader.cpp
tests/io/image/TiffImageReaderTests.cpp
```

Unified image dispatch contract owns:

```text
src/io/image/XQImageVolumeReader.h
src/io/image/XQImageVolumeReader.cpp
src/io/project/XQProjectDirectoryReader.cpp
tests/io/project/ProjectDirectoryReaderTests.cpp
CMakeLists.txt
```

Public class:

```text
xq::TiffImageReader::read(std::filesystem::path) -> XQDataNode
xq::XQImageVolumeReader::canReadPath(std::filesystem::path) -> bool
xq::XQImageVolumeReader::read(std::filesystem::path) -> XQDataNode
```

Owned data types:

```text
XQDataNode
XQImageVolume
DecodedImageBufferHandle
ImageGeometry
ScalarType
XQMetadata
```

External dependency boundary:

```text
ZLIB is used only inside `VtiImageReader.cpp` to inflate VTK XML compressed appended data.
ZLIB must resolve through the controlled dependency prefix before the main build consumes it.
The TIFF first pass parses the small baseline TIFF subset directly.
libtiff or ITK may be introduced later only if this document is updated with exact dependency, tests, and ownership boundary.
```

Forbidden shortcuts:

```text
Do not add MITK, BlueBerry, CTK, plugin workbench, SWIG, or compatibility data objects.
Do not expose libtiff/ITK handles through XQ core payloads if those dependencies are added later.
Do not mark TIFF support complete for OME-TIFF, compressed TIFF, tiled TIFF, or multi-page stacks in this document.
```

## Read Contract

Extract:

```text
dimensions
spacing
origin
direction when available
scalar arrays
component count
image metadata
```

TIFF first-pass extraction:

```text
ImageWidth -> dimensions[0]
ImageLength -> dimensions[1]
single slice -> dimensions[2] = 1
BitsPerSample 8 or 16 -> ScalarType::UInt8 or ScalarType::UInt16
SamplesPerPixel 1 -> componentCount = 1
ImageWidth / ImageLength must be nonzero
RowsPerStrip / StripOffsets / StripByteCounts -> raw decoded buffer
XResolution / YResolution / ResolutionUnit -> spacing when available
little-endian magic II + 42 only
Compression 1 only
PhotometricInterpretation 0 or 1 only
```

## Step Plan

- [x] Implement VTI loading through a first-pass VTI XML image reader.
- [x] Implement baseline TIFF loading through an XQ-owned first-pass parser.
- [x] Decode the acceptance VTI appended zlib scalar payload into `DecodedImageBufferHandle`.
- [x] Decode inline ASCII VTI scalar payloads into `DecodedImageBufferHandle`.
- [x] Extract optional VTI `ImageData Direction` matrices into `ImageGeometry`.
- [x] Decode inline uncompressed binary VTI scalar payloads into `DecodedImageBufferHandle`.
- [x] Decode raw appended uncompressed binary VTI scalar payloads into `DecodedImageBufferHandle`.
- [x] Defer MINC until dependency boundary is selected.
- [x] Convert VTI result into `XQImageVolume`.
- [x] Add acceptance test for `OSMSC0090-cm.vti`.
- [x] Add acceptance VTI decoded-buffer test.
- [x] Add multiple VTI `AppendedData` rejection test.
- [x] Add invalid VTI appended `DataArray offset` rejection test.
- [x] Add multiple VTI `AppendedData` rejection test for inline ASCII scalar inputs.
- [x] Add malformed VTI component-count rejection test.
- [x] Add trailing-garbage VTI component-count rejection test.
- [x] Add multiple VTI `PointData` array rejection test.
- [x] Add multiple VTI `PointData` element rejection test.
- [x] Add multiple VTI `Piece` rejection test.
- [x] Add multiple VTI `ImageData` rejection test.
- [x] Add non-ImageData `VTKFile` type rejection test.
- [x] Add missing VTI `WholeExtent` rejection test.
- [x] Add mismatched VTI `WholeExtent` and single `Piece Extent` rejection test.
- [x] Add invalid VTI extent order rejection test.
- [x] Add VTI extent extra-value rejection test.
- [x] Add VTI spacing vector extra-value rejection test.
- [x] Add out-of-range inline ASCII scalar rejection test.
- [x] Add mismatched VTI `PointData Scalars` and single `DataArray Name` rejection test.
- [x] Add missing VTI scalar array name rejection test.
- [x] Add VTI `PointData Scalars` naming anonymous `DataArray` rejection test.
- [x] Add VTI non-`LittleEndian` `byte_order` rejection test, including inline ASCII inputs.
- [x] Add VTI non-zlib `compressor` rejection test, including inline ASCII inputs.
- [x] Add VTI inline binary base64 trailing-garbage rejection test.
- [x] Add VTI inline binary base64 excessive-padding rejection test.
- [x] Add VTI inline binary base64 missing-padding rejection test.
- [x] Add VTI inline binary base64 nonzero-pad-bits rejection test.
- [x] Add synthetic uncompressed single-strip, multi-strip, inline SHORT strip-array, and multi-page rejection TIFF tests.
- [x] Add TIFF zero image dimension rejection test.
- [x] Add unified image-volume dispatch for existing first-pass VTI, NIfTI,
  NRRD, MetaImage, TIFF, and DICOM readers.
- [x] Route project directory image loading through unified dispatch and discover
  `.nii.gz` as an image path that decodes through the NIfTI reader.
- [x] Add project directory tests proving NIfTI, NRRD, and MetaImage project
  images enter `XQImageVolume` through the unified dispatch path.

## Test Plan

Test target:

xq_image_io_tests
xq_tiff_image_tests
xq_io_tests

Test file:

tests/io/image/VtiImageReaderTests.cpp
tests/io/image/TiffImageReaderTests.cpp
tests/io/project/ProjectDirectoryReaderTests.cpp

Required fixture data:

Synthetic little-endian TIFF files written by the test into the system temporary directory.

Commands:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_tiff_image_tests
cmake --build <xq-rebuild-workspace>/build --target xq_image_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R VtiImageReader --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build -R TiffImageReader --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build -R 'XQProjectDirectoryReader(UsesUnifiedImageDispatch|DiscoversCompressedNiftiAsImageVolume)' --output-on-failure
```

Expected pass condition:

VtiImageReaderReadsAcceptanceGeometry
VtiImageReaderReadsAcceptanceScalarMetadata
VtiImageReaderPreservesSourceMetadata
VtiImageReaderDecodesAcceptanceAppendedVoxels
VtiImageReaderDecodesInlineAsciiVoxels
VtiImageReaderReadsDirectionMatrix
VtiImageReaderDecodesInlineBinaryVoxels
VtiImageReaderDecodesRawAppendedVoxels
VtiImageReaderRejectsMissingVti
VtiImageReaderRejectsMultipleAppendedData
VtiImageReaderRejectsInvalidAppendedOffset
VtiImageReaderRejectsMultipleAppendedDataForInlineAscii
VtiImageReaderRejectsInlineAsciiBigEndian
VtiImageReaderRejectsInlineAsciiNonZlibCompressor
VtiImageReaderRejectsInlineBinaryBase64TrailingGarbage
VtiImageReaderRejectsInlineBinaryBase64ExcessPadding
VtiImageReaderRejectsInlineBinaryBase64MissingPadding
VtiImageReaderRejectsInlineBinaryBase64NonzeroPadBits
VtiImageReaderRejectsInvalidComponentCount
VtiImageReaderRejectsTrailingGarbageComponentCount
VtiImageReaderRejectsMultiplePointDataArrays
VtiImageReaderRejectsMultiplePointDataElements
VtiImageReaderRejectsMultiplePieces
VtiImageReaderRejectsWrongVtkFileType
VtiImageReaderRejectsMismatchedPieceExtent
VtiImageReaderRejectsMissingWholeExtent
VtiImageReaderRejectsInvalidExtentOrder
VtiImageReaderRejectsExtentWithExtraValues
VtiImageReaderRejectsSpacingWithExtraValues
VtiImageReaderRejectsOutOfRangeInlineAsciiUInt8
VtiImageReaderRejectsMismatchedPointDataScalars
VtiImageReaderRejectsMissingScalarArrayName
VtiImageReaderRejectsAnonymousDataArrayWithPointDataScalars
VtiImageReaderRejectsMultipleImageData
TiffImageReaderReadsUncompressedGrayscaleUInt16
TiffImageReaderReadsUncompressedMultiStripGrayscaleUInt16
TiffImageReaderReadsInlineShortStripArrays
TiffImageReaderRejectsCompressedTiff
TiffImageReaderRejectsMultiPageTiff
TiffImageReaderRejectsZeroImageDimension
XQProjectDirectoryReaderUsesUnifiedImageDispatch
XQProjectDirectoryReaderDiscoversCompressedNiftiAsImageVolume

Minimum negative case:

Compression != 1 must throw and must not create an XQDataNode.
Next IFD offset != 0 must throw and must not create a fake single-slice XQDataNode.
ImageWidth == 0 or ImageLength == 0 must throw and must not create an empty decoded-buffer XQDataNode.
Multiple VTI AppendedData elements must throw and must not silently choose the first appended payload.
Malformed VTI appended DataArray offset attributes must throw with a reader diagnostic and must not leak standard-library parsing exceptions.
Multiple VTI AppendedData elements beside inline ASCII scalar data must throw and must not silently ignore ambiguous appended payloads.
Malformed VTI NumberOfComponents must throw and must not silently default to a scalar image.
Malformed VTI NumberOfComponents values with trailing non-integer values must throw and must not silently truncate to a scalar image.
Multiple VTI PointData DataArray entries must throw and must not silently choose the first array.
Multiple VTI PointData elements must throw and must not silently choose the first element.
Multiple VTI ImageData entries must throw and must not silently choose the first image root.
Multiple VTI ImageData Piece entries must throw and must not silently choose the first piece.
Non-ImageData VTKFile types must throw and must not read compatible-looking ImageData children.
Missing VTI WholeExtent must throw and must not infer image geometry only from a Piece Extent.
Mismatched VTI WholeExtent and single Piece Extent must throw and must not represent a partial piece as a full image.
Invalid VTI extent order must throw and must not attempt decoded-buffer allocation from an underflowed dimension.
VTI extent values with extra values must throw and must not silently ignore malformed extent fields.
VTI spacing vectors with extra values must throw and must not silently ignore malformed geometry fields.
VTI inline ASCII scalar values outside the target scalar type range must throw and must not silently truncate into decoded buffers.
Mismatched VTI PointData Scalars and single DataArray Name must throw and must not silently read an inactive scalar array.
Missing VTI scalar array name must throw and must not silently read an anonymous scalar array.
VTI PointData Scalars must not be allowed to name an anonymous DataArray whose own Name is missing.
VTI files whose VTKFile byte_order is not LittleEndian must throw before decoded-buffer creation, including inline ASCII scalar inputs.
VTI files whose VTKFile compressor is neither empty nor vtkZLibDataCompressor must throw before decoded-buffer creation, including inline ASCII scalar inputs.
Inline binary VTI base64 payloads with non-padding garbage after padding must throw before decoded-buffer creation.
Inline binary VTI base64 payloads with excessive padding characters must throw before decoded-buffer creation.
Inline binary VTI base64 payloads with missing required padding must throw before decoded-buffer creation.
Inline binary VTI base64 payloads with nonzero pad bits must throw before decoded-buffer creation.

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Acceptance

- The acceptance project image loads before any path or contour data is displayed.
- VTI image geometry, including optional direction matrices when present, is available to path and contour tools.
- The acceptance VTI image owns a decoded contiguous voxel buffer for downstream MPR rasterization.
- TIFF creates the same `XQImageVolume` payload type as VTI, DICOM, NIfTI, NRRD, and MetaImage.
- Project directory image loading routes existing supported image formats through
  one XQ-owned image-volume dispatch contract.
- MINC does not create an alternative image payload when implemented later.

## Failure Repair

If VTI is treated only as a visualization file and not as project image data, repair this reader and `XQImageVolume`.

If baseline TIFF data stops at an importer object rather than entering `XQImageVolume` with `DecodedImageBufferHandle`, repair `TiffImageReader` before expanding TIFF coverage.
