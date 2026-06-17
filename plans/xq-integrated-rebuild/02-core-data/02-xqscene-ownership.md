# XQScene Ownership

## Purpose

Define the single ownership graph for all loaded project data.

## Owns

Future source files:

```text
src/core/XQScene.h
src/core/XQScene.cpp
src/core/XQSceneIndex.h
tests/core/XQSceneOwnershipTest.cpp
```

## Inputs

- `XQProject` lifecycle.
- Data node and metadata contract.

## Outputs

- One scene tree containing images, paths, contours, models, meshes, and simulation cases.
- Stable lookup by node id, domain type, display group, and source relation.

## Rules

- `XQScene` owns XQ data nodes and source relations.
- VTK, ITK, DCMTK, GDCM, and OCCT objects may be stored only inside payload classes or algorithm internals.
- UI tree rows and renderer props observe `XQScene`; they do not own project data.
- There is no parallel MITK `DataStorage` or external object graph.

## Scene Shape

Top-level groups:

```text
Images
Paths
Segmentations
Models
Meshes
Simulations
Results
```

Each group contains `XQDataNode` objects with typed payloads:

```text
XQImageVolume
XQPath
XQContourGroup
XQSurfaceModel
XQMesh
XQSimulationCase
```

## Source Relations

The scene records provenance explicitly:

```text
Path -> ImageVolume
ContourGroup -> Path
SurfaceModel -> ContourGroup
Mesh -> SurfaceModel
SimulationCase -> Mesh
```

## Implementation Contract

Public API surface:

```text
XQScene::insertNode(group, node)
XQScene::removeNode(nodeId)
XQScene::findNode(nodeId)
XQScene::nodesByDomain(domainType)
XQScene::addSourceRelation(parentNodeId, childNodeId, relationKind)
XQScene::removeSourceRelation(parentNodeId, childNodeId, relationKind)
XQScene::relationsFor(nodeId)
XQScene::markNodeStale(nodeId, reason)
```

Dependency boundary:

```text
allowed: XQDataNode, XQNodeId, XQDomainType, source relation value types
not allowed: Qt item models, VTK actors, external object graphs
```

## Step Plan

- [x] Define `XQScene` with node insertion, removal, lookup, and traversal.
- [x] Define fixed root groups for the vascular workflow.
- [x] Add a source relation table owned by `XQScene`.
- [x] Make source relation creation validate that relations point to existing node ids.
- [x] Add exact source relation removal for undoable generated-node commands.
- [x] Prefer removing live source relations before stale records when an exact
  relation tuple has both, so undo preserves stale relation history.
- [x] Add tests for inserting the full Image to Simulation chain.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQSceneOwnership --output-on-failure
```

Required cases:

insert one node into each fixed group
lookup nodes by id and domain type
create Image -> Path -> ContourGroup -> SurfaceModel -> Mesh -> SimulationCase relations
remove an upstream node and expose affected downstream relations
reject a source relation to a missing node
remove a specific source relation without changing unrelated relations
remove a live source relation while preserving older stale duplicate history
verify full suite after relation removal API integration

## Acceptance

- Every loaded item from `<acceptance-project>` has one owning `XQDataNode`.
- Removing a node exposes affected downstream relations before destructive mutation.
- Workbench and IO code can query scene state without knowing renderer or external-kernel internals.

## Failure Repair

If a feature keeps authoritative state in Qt model items, VTK actors, MITK data storage, or old plugin services, move ownership back into `XQScene`.
