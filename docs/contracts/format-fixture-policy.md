# Format Fixture Policy

## Purpose

Require reader validation to compare canonical results, not just avoid crashes.

## Fixture Manifest

Fixtures are registered in `ledger/fixtures/fixture-manifest.json`; the manifest records logical bindings and hashes, not sensitive content.

## Coverage Targets

- project manifest / `.svproj`
- `.pth`
- `.ctgr`
- `.mdl/.vtp`
- `.msh/.vtu`
- `.sjb`
- DICOM
- XQ native save format

## Required Fixture Fields

Each fixture records fixture ID, format, format version, visibility, content binding, sensitivity flag, de-identification status, input SHA-256, expected result binding, expected result SHA-256, approved usage, and owner.
