# XQDataNode and Metadata

## Purpose

Define the common node wrapper used by the scene for identity, display state, file provenance, and typed payload access.

## Owns

Future source files:

```text
src/core/XQDataNode.h
src/core/XQDataNode.cpp
src/core/XQNodeId.h
src/core/XQMetadata.h
tests/core/XQDataNodeMetadataTest.cpp
```

## Inputs

- `XQScene` ownership.
- Domain payload documents.

## Outputs

- A small, stable node type used by all scene items.
- Metadata storage that preserves SimVascular project attributes and XQ-native attributes.

## Rules

- `XQDataNode` is not `mitk::DataNode`.
- Metadata is typed enough for common access and flexible enough to preserve unknown XML attributes.
- Rendering state belongs to view models or visualization adapters, not to the authoritative payload.
- External-kernel handles are not public node metadata.

## Data Contract

```text
XQNodeId id
std::string name
XQDomainType domainType
std::shared_ptr<XQPayload> payload
XQMetadata metadata
std::filesystem::path sourceFile
bool visible
bool locked
```

`XQMetadata` supports:

```text
string
integer
double
boolean
string list
numeric vector
raw XML attribute map
```

## Required Metadata Keys

Common keys:

```text
source.format
source.relative_path
source.original_name
xq.created_by
xq.modified_by
```

SimVascular-style preservation keys:

```text
sv.project.version
sv.face.id
sv.cap.id
sv.group.name
sv.solver.job_name
```

## Implementation Contract

Public API surface:

```text
XQNodeId
XQDomainType
XQPayload
XQDataNode
XQMetadata
XQMetadataValue
makeImageNode(name, payload)
makePathNode(name, payload)
makeContourGroupNode(name, payload)
makeSurfaceModelNode(name, payload)
makeMeshNode(name, payload)
makeSimulationCaseNode(name, payload)
```

Dependency boundary:

```text
allowed: standard library value types and XQ payload base class
not allowed: external-kernel classes in public metadata values
```

## Step Plan

- [ ] Define node id and domain type enums.
- [ ] Define payload base type with explicit domain kind.
- [ ] Define metadata value type and key validation.
- [ ] Add node creation helpers for image, path, contour group, model, mesh, and simulation case.
- [ ] Add tests proving unknown XML attributes round-trip through metadata.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQDataNodeMetadata --output-on-failure
```

Required cases:

create each domain node type
store and retrieve every supported metadata value kind
preserve unknown XML attributes in raw metadata
reject payload/domain mismatches
confirm external-kernel public classes are absent from metadata values

## Acceptance

- Business code can switch on `XQDomainType` and receive an XQ payload type.
- Known SimVascular attributes are mapped to named metadata keys.
- Unknown attributes are preserved without becoming C++ API surface.

## Failure Repair

If a new feature stores domain state as loosely typed string maps only, create or update the owning payload document instead of expanding metadata into a hidden object model.
