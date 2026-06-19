# Product Scope V1

## Goal

Build an integrated desktop XQ application for medical imaging, vascular modeling, meshing, and simulation preparation using XQ-owned data objects.

## V1 Must

- Use Qt6 for one integrated desktop application shell.
- Use `XQProject`, `XQScene`, and `XQDataNode` as the authoritative data model.
- Represent image, path, contour, segmentation, surface model, mesh, and simulation case as XQ-owned payloads.
- Open project data into XQ-owned scene nodes.
- Show scene data in a project tree and at least one viewer.
- Save, close, reopen, and verify consistent scene state.
- Preserve diagnostics without leaking private data.

## V1 Must Not

- Use MITK, BlueBerry, CTK, or plugin workbench as architecture owners.
- Expose VTK, ITK, GDCM, DCMTK, OCCT, MMG, or codec-native objects through XQ public business APIs.
- Treat old XQ plugin wiring as new architecture.
- Claim implementation completion without runner-backed evidence and formal gate/review records.

## Deferred

ROM, multiphysics, broad Python bindings, full simulation solving, and all non-V1 readers remain deferred until explicit Epic contracts are approved.
