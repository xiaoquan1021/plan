# DICOM Private Tags

## Purpose

Define how XQ preserves and uses common vendor private DICOM variants without making vendor-specific code leak across the application.

## Owns

First-pass source files:

```text
src/io/image/DicomPrivateTagPolicy.h
src/io/image/DicomPrivateTagPolicy.cpp
src/io/image/DicomVendorProfile.h
tests/io/image/DicomPrivateTagPolicyTests.cpp
```

## Inputs

- DICOM series scanner.
- DICOM pixel decode.
- `XQImageVolume` metadata.

## Outputs

- Vendor profile classification.
- Preserved private tag metadata.
- Selected private tag interpretation for geometry or acquisition details when needed.
- XQ-owned metadata keys attached to DICOM image nodes.

## Rules

- Private tags are preserved by default as metadata.
- Interpretation is limited to known vendor profiles and documented keys.
- Unknown private tags do not become hard failures during project opening.
- Vendor-specific logic stays in this policy layer.
- First-pass policy consumes `DicomSeriesCandidate` / `DicomPrivateCreatorBlock`; it must not expose DCMTK objects.

## Vendor Profiles

First-version profiles:

```text
Siemens CT/MR common private creator blocks
GE CT/MR common private creator blocks
Philips CT/MR common private creator blocks
Canon/Toshiba CT/MR common private creator blocks
United Imaging CT/MR common private creator blocks
```

First-pass classification keys:

```text
manufacturer text contains Siemens, GE, Philips, Canon, Toshiba, United Imaging, or UIH
private creator text contains Siemens, GE, Philips, Canon, Toshiba, United Imaging, or UIH
otherwise Unknown
```

First-pass metadata keys:

```text
dicom.vendor.profile
dicom.private_creators
dicom.private_creator_count
dicom.private_tag_policy
```

## Use Cases

Private tags may assist with:

```text
mosaic image unpacking where applicable
enhanced MR/CT acquisition metadata
diffusion and cardiac timing metadata
vendor-specific slice timing or spacing hints
series display naming
diagnostics for unsupported variants
```

## Implementation Contract

Contract owner:

```text
src/io/image/DicomPrivateTagPolicy.h
src/io/image/DicomPrivateTagPolicy.cpp
src/io/image/DicomVendorProfile.h
tests/io/image/DicomPrivateTagPolicyTests.cpp
```

Public contract:

```text
DicomPrivateTagPolicy classifies vendor profile from manufacturer and private creator metadata
known private creators are preserved as XQ metadata
unknown private tags remain diagnostics/preserved metadata, not hard failures
domain and workbench code consume typed XQ metadata only
```

Forbidden shortcuts:

```text
no vendor-specific checks inside path, contour, modeling, meshing, or workbench code
no DCMTK private tag objects outside medical image IO
no private-tag semantics that mutate core data ownership
```

## Test Plan

Test target:

xq_io_tests or focused DicomPrivateTagPolicy test target

Test file:

tests/io/image/DicomPrivateTagPolicyTests.cpp

Core scenarios:

known vendor manufacturer/private creator maps to expected profile
unknown vendor remains Unknown without load failure
private creator metadata is attached to XQImageVolume/XQDataNode metadata
domain code does not receive DCMTK private tag objects

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R DicomPrivateTagPolicy --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.

## Step Plan

- [x] Capture private creator blocks during series scanning.
- [x] Classify manufacturer and private creator names into a vendor profile.
- [x] Preserve raw private tag values in `XQImageVolume` metadata.
- [x] Interpret only keys that affect first-version loading or display; first pass records diagnostics only.
- [x] Add tests for unknown private tags and known vendor profile detection.

## Acceptance

- Common vendor private DICOM variants can be loaded when pixel data and geometry are otherwise supported.
- Unsupported private semantics produce diagnostics, not architectural branches.
- No domain feature directly reads DCMTK private tag objects.
- initial contract proves vendor profile and private creator metadata are attached to `XQDataNode` / `XQImageVolume` metadata without changing core data ownership.

## Failure Repair

If vendor-specific checks appear in path, contour, model, mesh, or workbench code, move them back into this policy layer.
