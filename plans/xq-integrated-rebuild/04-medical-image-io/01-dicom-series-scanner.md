# DICOM Series Scanner

## Purpose

Define DICOM directory scanning, study/series grouping, and metadata indexing before pixel decoding.

## Owns

Source files:

```text
src/io/image/DicomSeriesScanner.h
src/io/image/DicomSeriesScanner.cpp
src/io/image/DicomSeriesIndex.h
tests/io/image/DicomSeriesScannerTests.cpp
```

## Inputs

- `XQImageVolume` payload.
- DCMTK dependency role.
- SQLite dependency role.

## Outputs

- Series candidates that can be opened as `XQImageVolume`.
- A local scan index for large DICOM folders.

## Rules

- Scanning uses DCMTK for metadata and file structure.
- Scanning does not decode pixel data.
- Private tags are collected and passed to the private tag policy document.
- DICOM series are grouped by patient, study, series, frame of reference, orientation, spacing, and temporal dimension where present.

## Current Dependency Note

During the first medical image IO contract, local CMake discovery reported:

```text
DCMTK not found
GDCM not found
```

Do not replace DCMTK with an ad hoc production DICOM parser just to make early code compile. The initial contract now uses the controlled dependency prefix.

Current foundation progress:

```text
externals/CMakeLists.txt exists
externals/versions.cmake pins XQ_DCMTK_VERSION=3.6.8 and XQ_GDCM_VERSION=3.0.10
externals/build-dcmtk.cmake and externals/build-gdcm.cmake configure controlled ExternalProject entries
build-externals builds DCMTK/GDCM into <xq-rebuild-workspace>/externals/install
GDCM uses the GitHub tag tarball to avoid fetching external testing-data submodules
```

## Current Source Status

Contract scope:

```text
src/io/image/DicomSeriesIndex.h
src/io/image/DicomSeriesScanner.h
src/io/image/DicomSeriesScanner.cpp
tests/io/image/DicomSeriesScannerTests.cpp
```

## Scan Contract

For each file, collect:

```text
SOPInstanceUID
StudyInstanceUID
SeriesInstanceUID
FrameOfReferenceUID
Modality
Manufacturer
ImageType
InstanceNumber
AcquisitionNumber
ImagePositionPatient
ImageOrientationPatient
PixelSpacing
SliceThickness
SpacingBetweenSlices
TransferSyntaxUID
Rows
Columns
BitsAllocated
BitsStored
PixelRepresentation
private creator blocks
```

## Implementation Contract

Contract owner:

```text
src/io/image/DicomSeriesIndex.h
src/io/image/DicomSeriesScanner.h
src/io/image/DicomSeriesScanner.cpp
tests/io/image/DicomSeriesScannerTests.cpp
```

Public contract:

```text
DicomSeriesScanner scans file trees for DICOM metadata without decoding pixels
DicomSeriesIndex groups records into series candidates
scanner output is XQ-owned metadata records, not DCMTK dataset objects
```

Forbidden shortcuts:

```text
no UI progress ownership
no immediate pixel decode inside the scanner
no DCMTK object exposure outside the IO scanner/reader boundary
```

## Test Plan

Test target:

xq_io_tests or focused DicomSeriesScanner test target

Test file:

tests/io/image/DicomSeriesScannerTests.cpp

Core scenarios:

multiple files group into series candidates
scanner records transfer syntax before pixel decode
synthetic vendor/private creator blocks are captured for downstream policy
non-DICOM files are ignored or diagnosed without UI dependencies

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R DicomSeriesScanner --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.

## Step Plan

- [x] Walk a directory tree and identify DICOM files with DCMTK.
- [x] Read metadata only and store records in memory.
- [x] Group files into series candidates.
- [x] Sort slices by image position and orientation, then instance number when geometry is incomplete.
- [ ] Save scan summaries to SQLite for repeat project opens.
- [x] Add tests using synthetic DICOM headers and vendor-like private tag samples.

## Acceptance

- Scanner can distinguish multiple series in one folder.
- Scanner reports transfer syntax before pixel decoding.
- Scanner output is independent of Qt widgets and VTK renderers.
- Scanner output is `DicomSeriesIndex` / `DicomInstanceRecord` owned by XQ, not DCMTK dataset objects.

## Failure Repair

If DICOM scanning is tied to immediate image creation or UI progress dialogs, split it back into this scanner and let the image reader consume scan results.
