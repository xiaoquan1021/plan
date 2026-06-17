# SVProj Project Manifest

## Purpose

Define native reading and writing of the `.svproj` project manifest.

## Owns

Future source files:

```text
src/io/project/SVProjectManifestReader.h
src/io/project/SVProjectManifestReader.cpp
src/io/project/SVProjectManifestWriter.h
src/io/project/SVProjectManifestWriter.cpp
tests/io/project/SVProjectManifestTest.cpp
```

## Inputs

- Project directory reader.
- tinyxml2 dependency role.

## Outputs

- Project-level metadata and expected project subdirectories.

## Rules

- `.svproj` is part of XQ's native first-version load contract.
- XML parsing uses tinyxml2 behind `src/io/project`.
- Unknown manifest attributes are preserved in project metadata.
- No code may depend on old SimVascular project manager classes.

## Read Contract

The reader extracts:

```text
project display name
project version if present
relative data directories
group names
original XML attributes
```

## Write Contract

The writer emits:

```text
XQ-native project identity
relative paths for scene data
preserved SimVascular-style metadata when loaded from such a project
```

## Implementation Contract

Public API surface:

```text
SVProjectManifestReader
SVProjectManifestWriter
SVProjectManifest
SVProjectManifest::projectName
SVProjectManifest::relativeDirectories
SVProjectManifest::rawAttributes
```

Dependency boundary:

```text
tinyxml2 is used only inside src/io/project
manifest parsing does not create scene nodes
manifest parsing does not require Qt widgets
```

## Step Plan

- [ ] Parse the XML document with tinyxml2.
- [ ] Map known fields into `XQProject` metadata.
- [ ] Preserve unrecognized attributes and elements in metadata.
- [ ] Expose normalized relative project paths to the directory reader.
- [ ] Add tests using the `.svproj` file from `<acceptance-project>`.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R SVProjectManifest --output-on-failure
```

Required fixture:

<acceptance-project>/*.svproj

Required cases:

read project display name and version when present
read relative project directories
preserve unknown XML attributes
reject malformed XML with diagnostic result
write a manifest without requiring old project managers

## Acceptance

- The manifest reader can run without Qt widgets.
- Manifest parsing does not create scene nodes directly.
- The project directory reader controls when scene nodes are created.

## Failure Repair

If manifest parsing starts opening files from every project subdirectory, move file loading back to the project directory reader.
