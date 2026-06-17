#!/usr/bin/env python3
"""Add missing canonical section headings to executable plan documents.

This is a plan-system repair migration. It adds contract/test/ownership sections
only where the current audit ledger reports missing executable-plan sections.
It does not change XQ source code and does not mark historical execution as
verified.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TREE_ROOT = ROOT / "plans" / "xq-integrated-rebuild"
TASKS_JSON = ROOT / "ledger" / "snapshots" / "tasks.json"


CONTRACT_SECTIONS = {
    "plans/xq-integrated-rebuild/00-governance/00-source-boundary-and-rules.md": """## Implementation Contract

Planning contract only. This document owns evidence-boundary rules and forbidden
architecture drift for all child documents; it does not own runtime source files.

Required invariants:

```text
XQ record source remains <xq-source-archive> extracted at <xq-source-extract>
active <xq-implementation-workspace> is not record for this analysis
planning files remain under plans/xq-integrated-rebuild
future implementation starts from the selected blank target root
MITK, BlueBerry, CTK, plugin workbench, and compatibility shells remain forbidden architecture owners
```

## Test Plan

Document consistency checks:

```text
rg -n "<xq-implementation-workspace>" plans/xq-integrated-rebuild plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

```text
<xq-implementation-workspace> appears only as a non-evidence active/future implementation boundary
scope_violations remains 0 in the separate scope check
```

## Acceptance

- The record boundary is unambiguous before any source or plan work starts.
- No child document may cite `<xq-implementation-workspace>` as audit record.
- Future implementation remains integrated XQ architecture, not an old framework bridge.
""",
    "plans/xq-integrated-rebuild/00-governance/01-architecture-first-discipline.md": """## Implementation Contract

Planning contract only. This document governs source-shape decisions before
feature implementation begins; it does not own runtime source files.

Required invariants:

```text
public XQ contracts precede convenience implementation details
partial code may exist only when it preserves the final integrated architecture
missing implementation fails explicitly instead of using fake fallback behavior
UI, IO, workflow, and algorithms share XQProject and XQScene ownership
external libraries remain kernels behind XQ-owned contracts
```

## Test Plan

Document consistency checks:

```text
rg -n "MITK|BlueBerry|CTK|plugin workbench|compatibility shell" plans/xq-integrated-rebuild
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

```text
old-framework wording appears only in forbidden-boundary or rejection text
the audit ledger keeps implementation_resume_allowed false until executable plan gates are clear
```

## Acceptance

- A future executor can tell incomplete-but-acceptable code from architecture drift.
- No plan step asks for a temporary second project, scene, workflow, or plugin platform.
- Feature documents route missing behavior back to the smallest owning document.
""",
    "plans/xq-integrated-rebuild/00-governance/02-document-repair-policy.md": """## Implementation Contract

Planning contract only. This document owns how plan defects are repaired; it
does not own runtime source files.

Required invariants:

```text
repair starts in the smallest owning document
adjacent documents change only when their interface contract changes
main plan remains index and routing, not feature implementation detail
source work resumes only after the repaired document states files, interfaces, tests, acceptance, and failure route
```

## Test Plan

Document consistency checks:

```text
python3 harness/audit_xq_zip_analysis.py
rg -n "Current cursor|Next implementation document|Completed source batch" plans/xq-integrated-rebuild/00-execution-entry.md plans/xq-integrated-rebuild/README.md plans/2026-06-11-xq-lightweight-dependency-refactor-from-XQ-main-zip.md
```

Expected result:

```text
state-source lines remain 0 except diagnostic command references
repair work is selected from ledger/snapshots/tasks.json
```

## Acceptance

- A failed feature has one primary repair document.
- The plan tree does not regain duplicated status mirrors.
- Repaired documents become more executable without moving feature details into the main plan.
""",
    "plans/xq-integrated-rebuild/08-xq-zip-selection/01-code-selection-rules.md": """## Implementation Contract

Planning contract only. This document governs how old XQ code may be studied
and recorded; it does not authorize copying old framework architecture.

Required invariants:

```text
old XQ source is record, not an owner
selected behavior is rewritten into an integrated XQ owner
feature documents record files studied, behavior kept, behavior rejected, rewrite owner, and verification plan
MITK/DataStorage/BlueBerry/CTK/SWIG/plugin glue is rejected unless a future document explicitly owns a new boundary
```

## Test Plan

Document consistency checks:

```text
rg -n "XQ-main.zip Evidence|Evidence source root|Behavior kept|Behavior rejected|Rewrite owner|Verification" plans/xq-integrated-rebuild
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

```text
feature documents that use old XQ behavior contain an record record before source work resumes
historical verification claims remain non-authoritative until linked under _evidence
```
""",
    "plans/xq-integrated-rebuild/08-xq-zip-selection/02-code-rewrite-mapping.md": """## Implementation Contract

Planning contract only. This document maps old-code responsibilities to new
integrated XQ owners; it does not authorize direct source copying.

Required invariants:

```text
every selected old behavior maps to one smallest new owner
framework entrypoints are rejected even when behavior is kept
external-library public objects are converted to XQ payloads or service parameters
file-format readers stay under IO owners
workflow/UI behavior is separated from domain payload ownership
```

## Test Plan

Document consistency checks:

```text
python3 harness/audit_xq_zip_analysis.py
rg -n "MITK|BlueBerry|CTK|plugin|DataStorage" plans/xq-integrated-rebuild/08-xq-zip-selection
```

Expected result:

```text
old framework terms appear only in rejected behavior or boundary language
new owners are explicit before a rewrite starts
```
""",
    "plans/xq-integrated-rebuild/09-acceptance-repair/02-failure-routing.md": """## Implementation Contract

Planning contract only. This document owns failure-to-document routing and
post-acceptance deferred work ownership; it does not own runtime source files.

Required invariants:

```text
failure repair starts from the smallest owning document
compatibility shells and runtime switches are not acceptable acceptance repairs
deferred fidelity work has a primary owner before implementation resumes
historical acceptance results are execution records, not fresh evidence
```
""",
}


MEDICAL_CONTRACTS = {
    "plans/xq-integrated-rebuild/04-medical-image-io/01-dicom-series-scanner.md": """## Implementation Contract

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

```text
xq_io_tests or focused DicomSeriesScanner test target
```

Test file:

```text
tests/io/image/DicomSeriesScannerTests.cpp
```

Core scenarios:

```text
multiple files group into series candidates
scanner records transfer syntax before pixel decode
synthetic vendor/private creator blocks are captured for downstream policy
non-DICOM files are ignored or diagnosed without UI dependencies
```

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R DicomSeriesScanner --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.
""",
    "plans/xq-integrated-rebuild/04-medical-image-io/02-dicom-pixel-decode.md": """## Implementation Contract

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

```text
xq_io_tests or focused DicomPixelDecoder test target
```

Test file:

```text
tests/io/image/DicomPixelDecoderTests.cpp
```

Core scenarios:

```text
uncompressed Explicit VR Little Endian scalar slice decodes
uncompressed Implicit VR Little Endian scalar slice decodes
signed and unsigned scalar metadata is preserved
series slices assemble into one XQImageVolume buffer
unsupported compressed transfer syntax fails with diagnostics
```

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R DicomPixelDecoder --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.
""",
    "plans/xq-integrated-rebuild/04-medical-image-io/03-dicom-private-tags.md": """## Implementation Contract

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

```text
xq_io_tests or focused DicomPrivateTagPolicy test target
```

Test file:

```text
tests/io/image/DicomPrivateTagPolicyTests.cpp
```

Core scenarios:

```text
known vendor manufacturer/private creator maps to expected profile
unknown vendor remains Unknown without load failure
private creator metadata is attached to XQImageVolume/XQDataNode metadata
domain code does not receive DCMTK private tag objects
```

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R DicomPrivateTagPolicy --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.
""",
    "plans/xq-integrated-rebuild/04-medical-image-io/04-nifti-reader.md": """## Implementation Contract

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

```text
xq_io_tests or focused NiftiImageReader test target
```

Test file:

```text
tests/io/image/NiftiImageReaderTests.cpp
```

Core scenarios:

```text
uncompressed .nii scalar payload enters XQImageVolume
.nii.gz inflates through controlled zlib and enters the same payload type
sform geometry converts to ImageGeometry
unsupported NIfTI-2, 4D, vector/RGB, or complex payloads fail with diagnostics
```

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R NiftiImageReader --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.
""",
    "plans/xq-integrated-rebuild/04-medical-image-io/05-nrrd-metaimage-reader.md": """## Implementation Contract

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

```text
xq_io_tests or focused NrrdMetaImageReader test target
```

Test file:

```text
tests/io/image/NrrdMetaImageReaderTests.cpp
```

Core scenarios:

```text
embedded MetaImage raw payload decodes
detached MetaImage raw payload resolves relative to header
attached/detached NRRD raw payload decodes
gzip MetaImage/NRRD payloads inflate through controlled zlib
missing detached data or unsupported encoding fails with diagnostics
```

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_io_tests
ctest --test-dir <xq-rebuild-workspace>/build -R 'Nrrd|MetaImage' --output-on-failure
```

Fresh command output must be linked under `<private-evidence-dir>/` before task state changes.
""",
}


OWNERSHIP_SECTIONS = {
    "plans/xq-integrated-rebuild/00-governance/03-child-document-hardening-standard.md": """## Owns

Planning workflow only. This document owns the checklist that decides whether a
child document is ready for source changes; it does not own runtime source
files.

## Test Plan

Document consistency checks:

```text
python3 harness/audit_xq_zip_analysis.py
```

Expected result:

```text
executable child/support/governance documents missing canonical sections are listed in ledger/snapshots/tasks.json
main-plan, README, and execution-entry remain not-executable indexes rather than fake implementation tasks
```
""",
    "plans/xq-integrated-rebuild/09-acceptance-repair/01-0007-project-acceptance.md": """## Owns

Acceptance source and test contract:

```text
src/app/main.cpp
tests/acceptance/XQ0007ProjectAcceptanceTest.cpp
CMakeLists.txt
```

Acceptance data boundary:

```text
<acceptance-project>
```
""",
}


def insert_before_heading(text: str, heading: str, block: str) -> str:
    marker = f"\n{heading}\n"
    index = text.find(marker)
    if index == -1:
        return text.rstrip() + "\n\n" + block.rstrip() + "\n"
    return text[: index + 1] + block.rstrip() + "\n\n" + text[index + 1 :]


def add_block(path: Path, block: str, before: str = "## Step Plan") -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    first_heading = block.splitlines()[0]
    if first_heading in text:
        return False
    updated = insert_before_heading(text, before, block)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def tasks_needing_hardening() -> list[dict[str, object]]:
    data = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    return [task for task in data["tasks"] if task.get("status") == "needs-hardening"]


def main() -> int:
    changed: list[str] = []
    for task in tasks_needing_hardening():
        rel = str(task["source_md"])
        path = ROOT / rel
        if rel in CONTRACT_SECTIONS:
            if add_block(path, CONTRACT_SECTIONS[rel]):
                changed.append(rel)
        if rel in MEDICAL_CONTRACTS:
            if add_block(path, MEDICAL_CONTRACTS[rel]):
                changed.append(rel)
        if rel in OWNERSHIP_SECTIONS:
            before = "## Inputs" if "09-acceptance-repair/01-0007-project-acceptance.md" in rel else "## Inputs"
            if add_block(path, OWNERSHIP_SECTIONS[rel], before=before):
                changed.append(rel)
    for rel in changed:
        print(rel)
    print(f"changed={len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
