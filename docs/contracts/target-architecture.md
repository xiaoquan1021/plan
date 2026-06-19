# Target Architecture

## Ownership

`XQProject` owns project lifecycle, root identity, diagnostics, modified state, and one authoritative `XQScene`.

`XQScene` owns all domain nodes and relations. UI models, viewers, readers, and algorithms observe or transform scene data; none of them own a parallel business object graph.

`XQDataNode` owns stable node identity, display metadata, domain type, provenance, diagnostics, and an XQ-owned payload.

## Dependency Direction

```text
app/workbench -> workflow -> io/algorithms/visualization -> core
```

Core must not depend on Qt widgets, VTK renderers, ITK images, GDCM/DCMTK datasets, OCCT shapes, MMG meshes, MITK, BlueBerry, CTK, plugin registries, or SWIG-generated objects.

## External Library Rule

External libraries are kernels, codecs, or rendering backends. They may appear behind private implementation boundaries or disposable visualization products, but not in public business APIs.

## SWIG

V1 does not use SWIG. Future bindings require an ADR. Bindings must not own business state or create a second object graph.
