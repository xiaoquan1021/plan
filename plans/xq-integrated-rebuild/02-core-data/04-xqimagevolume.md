# XQImageVolume

## Purpose

Define XQ's native volume image payload for DICOM, VTI, NIfTI, NRRD, MetaImage, TIFF stacks, and project image files.

## Owns

Future source files:

```text
src/core/XQImageVolume.h
src/core/XQImageVolume.cpp
tests/core/XQImageVolumeTest.cpp
```

## Inputs

- Medical image IO documents.
- Native project image loading.
- Visualization MPR documents.

## Outputs

- One image payload with geometry, scalar metadata, orientation, and optional VTK image backing.

## Rules

- Public business API uses XQ image concepts: dimensions, spacing, origin, direction, scalar type, components, and intensity range.
- VTK and ITK image objects are internal backing data choices.
- DICOM patient/study/series metadata is stored as image metadata, not as a separate external database object.
- `Images/OSMSC0090-cm.vti` from `<acceptance-project>` must load into this payload.

## Data Contract

```text
ImageId imageId
ImageGeometry geometry
ScalarType scalarType
int componentCount
IntensityRange intensityRange
std::shared_ptr<ImageBufferHandle> buffer
ImageModality modality
std::optional<DicomSeriesIdentity> dicomIdentity
```

`ImageGeometry` stores:

```text
dimensions[3]
spacing[3]
origin[3]
direction[3][3]
coordinateSystem
```

## Implementation Contract

Public API surface:

```text
ImageGeometry
ScalarType
IntensityRange
ImageBufferHandle
DicomSeriesIdentity
XQImageVolume
XQImageVolume::geometry()
XQImageVolume::scalarType()
XQImageVolume::bufferHandle()
XQImageVolume::worldToVoxel(point)
XQImageVolume::voxelToWorld(index)
```

Dependency boundary:

```text
allowed internally: VTK or ITK image backing handles
not allowed publicly: vtkImageData, itk::Image, DICOM dataset classes
```

## Step Plan

- [ ] Define `ImageGeometry` independent of ITK and VTK.
- [ ] Define scalar types used by CT/MR and derived images.
- [ ] Add image buffer handle that can wrap VTK image data without exposing it in project APIs.
- [ ] Preserve modality, window center, window width, rescale slope, and rescale intercept.
- [ ] Add tests using a synthetic volume and the `<acceptance-project>` VTI file path.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R XQImageVolume --output-on-failure
```

Required cases:

construct synthetic 3D image geometry
round-trip voxelToWorld and worldToVoxel
store scalar type, component count, and intensity range
attach DICOM identity metadata without exposing DICOM classes
load Images/OSMSC0090-cm.vti after VTI reader exists

## Acceptance

- MPR and 3D viewers can request geometry from `XQImageVolume`.
- Path and contour tools can transform between voxel, image, and world coordinates.
- DICOM metadata can be attached without requiring a DICOM module in the scene.

## Failure Repair

If image geometry is read separately by every tool, move the common transform and metadata into this payload.
