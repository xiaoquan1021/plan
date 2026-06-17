# PTH Path Reader

## Purpose

Define native reading and writing of SimVascular-style `.pth` vascular path files into `XQPath`.

## Owns

Future source files:

```text
src/io/project/PTHPathReader.h
src/io/project/PTHPathReader.cpp
src/io/project/PTHPathWriter.h
src/io/project/PTHPathWriter.cpp
tests/io/project/PTHPathReaderTest.cpp
```

## Inputs

- `XQPath` payload.
- tinyxml2 dependency role.

## Outputs

- One `XQDataNode` with `XQPath` payload per `.pth` file.

## Rules

- `.pth` files are first-version native XQ path files.
- The reader maps XML path points into XQ control and sample points.
- Original path name and XML attributes are preserved.
- UI tools do not parse `.pth` directly.

## Read Contract

Extract:

```text
path name
control point order
sampled path points
point coordinates
tangent/frame data when present
method/interpolation metadata
unknown XML attributes
```

## Implementation Contract

Public API surface:

```text
PTHPathReader
PTHPathWriter
PTHPathReader::read(pathFile)
PTHPathWriter::write(pathNode, pathFile)
```

Output ownership:

```text
one XQDataNode
one XQPath payload
source.format = pth
source.relative_path = Paths/<name>.pth
```

Dependency boundary:

```text
tinyxml2 stays inside reader and writer
VTK polyline is not the output contract
```

## Step Plan

- [ ] Parse `.pth` XML with tinyxml2.
- [ ] Create `XQPath` control points and sample points.
- [ ] Normalize coordinates into project world space.
- [ ] Attach source file metadata to the resulting node.
- [ ] Add tests for every `.pth` file under `<acceptance-project>/Paths`.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R PTHPathReader --output-on-failure
```

Required fixture:

<acceptance-project>/Paths/*.pth

Required cases:

read every .pth file under Paths
preserve path name and point order
populate XQPath control and sample points
attach source metadata
reject malformed .pth without creating partial scene ownership

## Acceptance

- Each loaded path has stable point order.
- Contour groups can bind to loaded paths by name or source relation.
- Saving a loaded path preserves required SimVascular-style fields.

## Failure Repair

If path loading creates only VTK polylines, repair this reader and `XQPath` before touching contour tools.
