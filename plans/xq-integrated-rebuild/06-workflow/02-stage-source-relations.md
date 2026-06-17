# Stage Source Relations

## Purpose

Define how workflow stages depend on upstream scene nodes and how downstream data is marked when upstream data changes.

This document creates a workflow-level relation policy that operates on `XQScene` source relations. It does not add payload revision hashing or UI repair prompts yet.

## Owns

Future source files:

```text
src/workflow/XQSourceRelationPolicy.h
src/workflow/XQSourceRelationPolicy.cpp
tests/workflow/XQSourceRelationPolicyTest.cpp
```

## Inputs

- `XQScene` source relation table.
- Workflow state machine.
- Domain payload documents.

## Outputs

- A policy for relation creation, invalidation, and repair prompts.

## Rules

- Source relations are first-class scene data.
- Downstream data is not silently deleted when upstream data changes.
- Dirty and stale states are explicit metadata on affected nodes.
- Each stage declares what source node types it can produce from.
- Relation traversal must use `XQScene` source relations, not filenames.

## Relation Graph

```text
ImageVolume -> Path
ImageVolume -> SegmentationMask
Path -> ContourGroup
ContourGroup -> SurfaceModel
SurfaceModel -> Mesh
Mesh -> SimulationCase
SimulationCase -> Results
```

## Implementation Contract

Implementation Contract owns:

```text
src/workflow/XQSourceRelationPolicy.h
src/workflow/XQSourceRelationPolicy.cpp
tests/workflow/XQSourceRelationPolicyTest.cpp
```

Public class:

```text
xq::XQSourceRelationPolicy
```

Minimum public operations:

```text
linkImageToPath(XQScene&, XQNodeId, XQNodeId)
linkImageToSegmentationMask(XQScene&, XQNodeId, XQNodeId)
linkPathToContourGroup(XQScene&, XQNodeId, XQNodeId)
linkContourGroupToSurfaceModel(XQScene&, XQNodeId, XQNodeId)
linkSurfaceModelToMesh(XQScene&, XQNodeId, XQNodeId)
linkMeshToSimulationCase(XQScene&, XQNodeId, XQNodeId)
markDownstreamStale(XQScene&, XQNodeId, std::string)
```

Propagation first pass:

```text
direct children receive the provided stale reason
deeper descendants receive "Upstream stale: " + provided stale reason
all affected nodes remain in XQScene
missing relation endpoints are ignored during propagation but relation creation still rejects missing nodes through XQScene
```

Forbidden behavior:

```text
delete downstream nodes automatically
search by filenames
edit domain payload geometry or simulation settings
store stale state only in UI
```

## Dirty Propagation

When a source node changes:

```text
mark direct children as stale
mark deeper descendants as upstream-stale
keep nodes visible unless user removes or regenerates them
show diagnostics in project tree and tool panel
```

## Step Plan

- [x] Reuse existing `XQRelationKind` and `XQSourceRelation` records.
- [x] Reuse existing `XQDataNode::markStale` stale state.
- [x] Add relation creation helpers for each workflow stage.
- [x] Add dirty propagation from a changed upstream node through relation graph.
- [x] Add tests for Path edit marking ContourGroup, Model, Mesh, and SimulationCase stale.

## Test Plan

Test target:

xq_source_relation_policy_tests

Test file:

tests/workflow/XQSourceRelationPolicyTest.cpp

Core scenarios:

XQSourceRelationPolicyCreatesStageRelations
XQSourceRelationPolicyCreatesImageToSegmentationMaskRelation
XQSourceRelationPolicyMarksDirectAndDeepDownstreamStale
XQSourceRelationPolicyLeavesUnrelatedBranchesUnchanged
XQSourceRelationPolicyDoesNotDeleteDownstreamNodes

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_source_relation_policy_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQSourceRelationPolicy --output-on-failure
```

Expected result:

all source relation policy tests pass

TDD red check:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_source_relation_policy_tests
```

Observed expected failure before implementation:

tests/workflow/XQSourceRelationPolicyTest.cpp failed to compile because
xq::XQSourceRelationPolicy had no member named linkImageToSegmentationMask.

## Acceptance

- Downstream invalidation is predictable and visible.
- Regenerating a stage updates source relations.
- Project loading can restore relation graph from file metadata or directory structure.
- initial contract can mark downstream nodes stale through `XQScene` relations.

## Failure Repair

If downstream tools directly search by file names instead of scene relations, repair this policy and the owning reader.
