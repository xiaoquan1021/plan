# CTGR Contour Reader

## Purpose

Define native reading and writing of `.ctgr` contour group files into `XQContourGroup`.

## Owns

Future source files:

```text
src/io/project/CTGRContourReader.h
src/io/project/CTGRContourReader.cpp
src/io/project/CTGRContourWriter.h
src/io/project/CTGRContourWriter.cpp
tests/io/project/CTGRContourReaderTest.cpp
```

## Inputs

- `XQContourGroup` payload.
- Path reader.
- tinyxml2 dependency role.

## Outputs

- One `XQDataNode` with `XQContourGroup` payload per `.ctgr` file.

## Rules

- `.ctgr` files are first-version native XQ contour group files.
- The reader stores contours as domain data before any viewer opens.
- Contour path binding is resolved by the project directory reader after paths are loaded.
- Unknown XML attributes are preserved as metadata.

## Read Contract

Extract:

```text
group name
contour method/type
path point or path position
plane origin
plane normal
plane x/y axes when present
contour point list
closed/open state
lofting-related metadata
```

## Implementation Contract

Public API surface:

```text
CTGRContourReader
CTGRContourWriter
CTGRContourReader::read(contourFile)
CTGRContourWriter::write(contourGroupNode, contourFile)
```

Output ownership:

```text
one XQDataNode
one XQContourGroup payload
source.format = ctgr
source.relative_path = Segmentations/<name>.ctgr
path relation hint preserved until project relation resolution
```

Dependency boundary:

```text
tinyxml2 stays inside reader and writer
viewer overlays are not output data
```

## Step Plan

- [ ] Parse `.ctgr` XML with tinyxml2.
- [ ] Build ordered `XQContour` records.
- [ ] Preserve contour method and source path hints.
- [ ] Create one `XQContourGroup` node per file.
- [ ] Add tests for contour count, frame integrity, and point order using `<acceptance-project>/Segmentations`.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R CTGRContourReader --output-on-failure
```

Required fixture:

<acceptance-project>/Segmentations/*.ctgr

Required cases:

read every .ctgr file under Segmentations
preserve contour count and point order
preserve contour frame origin and normal
preserve contour method and type metadata
reject malformed .ctgr without creating editor-only state

## Acceptance

- Loaded contours can be edited without re-reading XML.
- Lofting input generation receives ordered contours from `XQContourGroup`.
- Path relation is explicit once the project loader resolves names.

## Failure Repair

If contour group loading depends on active path editor UI state, move that logic into this reader and the scene relation resolver.
