# 3D Scene Viewer

## Purpose

Define the VTK-based 3D viewer for paths, contours, segmentation masks, models, meshes, and simulation boundary context.

The implementation contract includes the XQ-owned 3D presentation model, VTK-free camera state, VTK-free pick-to-node selection target, scene-switch and selected-node-removal stale-selection cleanup, external missing-node selection rejection, payload-derived geometry summaries, VTK actor/prop pick adapter, VTK renderer synchronization layer, a VTK actor factory for generated and loaded triangle surface model, mesh surface, tetrahedral volume mesh, segmentation mask exposed-voxel-face surface, segmentation mask volume render product, segmentation mask smoothed/decimated extracted surface render product, path curve and control-point actors, contour, path/contour overlay display styles, boundary condition marker, face-id coloring, selected-row highlight render products, stale-row dimmed actor opacity, and XQ-main-derived surface-model point/cell normal generation, and a Qt/VTK scene-view widget with camera binding, native camera state back-sync, reset-to-visible-scene camera interaction, selected-node camera reset, reset-to-empty-visible-scene render cleanup, external node selection highlight resynchronization, external missing-node selection rejection without render request, external same-node selection no-op render suppression, disposable actor/prop pick selection, display-position geometric picking through current disposable render products, display-position miss no-op handling, clear-selection highlight resynchronization, pick-triggered selected-highlight resynchronization, render-product cleanup with native render/update request only when presentation-model unbind/switch clears existing disposable products, actor-category visibility/reset no-op render suppression, clear-selection no-op and same-selection no-op render suppression, last render-sync result reporting, native interactor exposure, trackball-camera interactor style configuration, and explicit render-request reporting after presentation synchronization, camera reset, and selection changes. The VTK actor factory, renderer synchronization layer, and Qt widget consume XQ scene rows and XQ-owned payload handles rather than becoming authoritative scene storage.

The Qt/VTK widget contract also translates unmodified native-widget left mouse presses into display-position picks inside the visualization layer, lets modified native-widget left mouse presses such as `Ctrl+LeftButton` propagate without changing selection or requesting native render/update, lets combined native-widget left mouse presses such as `LeftButton+RightButton` propagate without changing selection or requesting native render/update, ignores right mouse presses without changing selection or requesting native render/update, syncs native camera state back into the VTK-free presentation model after native mouse-release and wheel interactions and after later native event filters/default interaction have had a chance to mutate the camera, maps unmodified native-widget `F` key presses to selected-node camera reset when a node is selected or visible-scene camera reset when no node is selected, consumes `F` key visible-scene cleanup events when stale disposable render products are cleared and native render/update is requested, lets no-model native-widget `F` key events propagate without requesting native render/update when no camera reset can run, lets modified native-widget `F` key events such as `Ctrl+F` propagate without changing camera state or requesting native render/update, maps unmodified native-widget `Escape` key presses to clear the current presentation selection, consumes handled native key events so they are not propagated to later filters or default interaction, lets modified native-widget `Escape` key events such as `Ctrl+Escape` propagate without clearing selection or requesting native render/update, and lets no-selection `Escape` key events propagate without rebuilding render products or requesting native render/update.

The repeated native-event Qt/VTK widget contract consumes repeated unmodified native-widget left mouse presses that hit the already-selected render product while preserving selection state, preserving disposable render products, and avoiding native render/update requests.

The latest presentation-model switch disposable render-product cleanup coverage/acceptance requires that switching from one non-null presentation model to another clears old disposable render products, records an empty sync result, binds the new model pointer, and requests native render/update when actual products were cleared.

The path/contour overlay display-style contract applies XQ-main-derived green, opaque path curve and contour ring actor properties, with contour rings using a wider line, while keeping these VTK properties disposable and outside XQScene/domain payload ownership.

The path control-point sphere-glyph contract applies the XQ-main 3D path-control display shape: green, opaque disposable sphere glyphs generated from XQPath control-point positions with visualization-layer VTK filters only.

The surface-model normals contract applies the XQ-main 3D surface-rendering pipeline detail from `xq_SurfaceRenderer3D.cxx`: generated XQ-owned triangle surface-model actors pass through visualization-layer `vtkPolyDataNormals` with point normals, cell normals, splitting off, and consistency on before display, while preserving disposable face-id cell scalars and without mutating `XQSurfaceModel`.

The surface-model face-id cell-field coloring contract applies the XQ-main 3D geometry renderer mapper behavior from `xq_GeomRenderer3D.cxx`: generated XQ-owned triangle surface-model actors keep disposable `xq_face_id` cell arrays and configure the visualization-layer `vtkPolyDataMapper` to use cell field data and select that array for face-id coloring, without mutating `XQSurfaceModel`.

The surface-model face-id lookup-table/range contract applies the adjacent XQ-main 3D geometry renderer mapper behavior from `xq_GeomRenderer3D.cxx`: generated XQ-owned triangle surface-model actors configure a disposable `vtkLookupTable` sized from the model face count plus one and set mapper scalar range to `[0, faceCount]` while preserving cell-field `xq_face_id` coloring, without mutating `XQSurfaceModel`.

The surface-model face-id metadata guard contract applies the adjacent XQ-main 3D geometry renderer mapper guard from `xq_GeomRenderer3D.cxx`: disposable surface-model actors keep geometry-derived `xq_face_id` arrays available, but disable mapper scalar visibility when the XQ-owned model face metadata list is empty, without mutating `XQSurfaceModel`.

The surface-model material lighting defaults contract applies the XQ-main model default properties from `xq_ModelObjectFactory.cxx`: disposable surface-model actors use ambient coefficient `0.08`, diffuse coefficient `0.85`, specular coefficient `0.80`, and specular power `12.0`, without mutating `XQSurfaceModel` and while preserving row-level selected-highlight and stale-opacity overlays.

The surface-model wireframe display metadata contract applies the XQ-main model display property from `xq_ModelObjectFactory.cxx` and `xq_GeomRenderer3D.cxx`: VTK-free surface-model presentation rows read node metadata `wireframe` with default `false`, and disposable surface-model actor products set the visualization-layer `vtkActor` representation to surface by default or wireframe when requested, without mutating `XQSurfaceModel`.

The surface-model color/opacity display metadata contract applies the XQ-main model display properties from `xq_ModelObjectFactory.cxx` and `xq_GeomRenderer3D.cxx`: VTK-free surface-model presentation rows read node metadata `color` with default white `(1.0, 1.0, 1.0)` and `opacity` with default `1.0`, and disposable surface-model actor products apply row-driven opacity while preserving face-id mapper coloring and without mutating `XQSurfaceModel`.

The surface-model selected-face display metadata contract applies the XQ-main model display property from `xq_ModelObjectFactory.cxx` and `xq_GeomRenderer3D.cxx`: VTK-free surface-model presentation rows read node metadata `selectedFaceId` with default `-1`, and disposable surface-model actor products attach yellow `FaceColors` cell scalars for the matching `xq_face_id` while preserving XQ-owned model faces and geometry.

The surface-model display-position face-picking contract applies the XQ-main model interactor behavior from `xq_ModelDataInteractor.cxx`: disposable surface-model picks read `xq_face_id` from picked actor cell data, write `selectedFaceId` into XQ scene-node metadata, and clear it back to `-1` on selection clear without mutating `XQSurfaceModel`.

The same-face display-position pick no-op contract consumes repeated display-position picks on the already selected surface-model face while preserving the selected node, preserving `selectedFaceId`, preserving disposable render products, and avoiding native render/update requests.

The segmentation mask exposed-surface display-style contract applies the XQ-main 3D segmentation mapper defaults from `xq_MitkSeg3DVtkMapper3D.cxx`: disposable exposed-voxel-face surface actors use yellow-green color `(0.8, 0.8, 0.2)`, opacity `0.8`, edge visibility on, and dark edge color `(0.2, 0.2, 0.2)` without mutating `XQSegmentationMask`.

The segmentation mask surface normals contract applies the XQ-main 3D segmentation/surface mapper pipeline detail from `xq_MitkSeg3DVtkMapper3D.cxx` and `xq_SurfaceRenderer3D.cxx`: disposable exposed-voxel-face mask surface actors pass through visualization-layer `vtkPolyDataNormals` with point normals and cell normals before display, while preserving XQ-owned mask voxel geometry and without mutating `XQSegmentationMask`.

The segmentation mask smoothed-surface display-style contract applies the same XQ-main 3D segmentation mapper defaults from `xq_MitkSeg3DVtkMapper3D.cxx` to disposable smoothed/decimated extracted surface actors: yellow-green color `(0.8, 0.8, 0.2)`, opacity `0.8`, edge visibility on, and dark edge color `(0.2, 0.2, 0.2)`, without mutating `XQSegmentationMask`.

The segmentation mask smoothed-surface normals contract applies the XQ-main 3D segmentation/surface mapper pipeline detail from `xq_MitkSeg3DVtkMapper3D.cxx` and `xq_SurfaceRenderer3D.cxx`: disposable smoothed/decimated extracted mask surface actors pass through visualization-layer `vtkPolyDataNormals` with point normals and cell normals before display, while preserving XQ-owned mask voxel geometry and without mutating `XQSegmentationMask`.

The segmentation mask 3D display metadata contract applies the XQ-main 3D segmentation mapper properties from `xq_MitkSeg3DVtkMapper3D.cxx`: VTK-free segmentation-mask presentation rows read node metadata `color` with default yellow-green `(0.8, 0.8, 0.2)`, `opacity` with default `0.8`, `seg3d.edge visibility` with default `true`, and `seg3d.edge color` with default dark gray `(0.2, 0.2, 0.2)`, and disposable exposed-voxel-face plus smoothed extracted surface actor products apply those row-driven properties without mutating `XQSegmentationMask`.

The segmentation mask volume display metadata contract extends the existing VTK-free segmentation-mask `color` and `opacity` row values to the disposable `vtkVolume` color and scalar-opacity transfer-function endpoints, while keeping the volume mapper, image data, and transfer functions visualization-layer products derived from `XQSegmentationMask`.

The volume mesh grid display-style contract applies the XQ-main grid mapper defaults from `xq_MitkGridMapper3D.cxx`: disposable tetrahedral volume-grid actors use green color `(0.0, 0.8, 0.2)`, opacity `1.0`, surface representation, edge visibility on, and dimmed edge color `(0.0, 0.4, 0.1)` without mutating `XQMesh`.

The mesh surface grid display-style contract applies the same XQ-main grid mapper defaults from `xq_MitkGridMapper3D.cxx` to disposable triangle surface-mesh actors: green color `(0.0, 0.8, 0.2)`, opacity `1.0`, surface representation, edge visibility on, and dimmed edge color `(0.0, 0.4, 0.1)`, while preserving XQ-owned mesh surface geometry and without mutating `XQMesh`.

The mesh wireframe display metadata contract applies the XQ-main grid display property from `xq_MitkGridObjectFactory.cxx` and `xq_MitkGridMapper3D.cxx`: VTK-free mesh presentation rows read node metadata `mesh.wireframe` with default `false`, and disposable mesh surface/volume grid actor products set the visualization-layer `vtkActor` representation to surface by default or wireframe when requested, without mutating `XQMesh`.

The mesh color/opacity display metadata contract applies the XQ-main grid display properties from `xq_MitkGridObjectFactory.cxx` and `xq_MitkGridMapper3D.cxx`: VTK-free mesh presentation rows read node metadata `color` with default green `(0.0, 0.8, 0.2)` and `opacity` with default `1.0`, and disposable mesh surface/volume grid actor products apply row-driven color, opacity, and dimmed half-strength edge color without mutating `XQMesh`.

The path curve tube-pipeline contract applies the XQ-main vessel tracer 3D defaults from `xq_VesselTracer3D.cxx`: disposable path-curve actors render XQPath sample/control-point polylines through visualization-layer `vtkTubeFilter` with radius `0.3`, 12 sides, and capping enabled, while preserving the green overlay actor properties and without mutating `XQPath`.

The path curve segmented-line tube topology contract applies the adjacent XQ-main vessel tracer 3D topology from `xq_VesselTracer3D.cxx`: disposable path-curve tube input inserts one two-point `vtkLine` cell for each adjacent XQPath display-point segment before `vtkTubeFilter`, without mutating `XQPath`.

The contour ring closed line-segment topology contract applies the XQ-main 3D profile renderer behavior from `xq_ProfileRenderer3D.cxx`: disposable contour ring actors insert one two-point `vtkLine` cell for each contour edge plus the closing last-to-first edge, while preserving the green/wider overlay actor properties and without mutating `XQContourGroup`.

The path control-point point-data scalar contract applies the XQ-main vessel tracer 3D behavior from `xq_VesselTracer3D.cxx`: disposable path control-point sphere-glyph actors attach three-component unsigned-char RGB point-data scalars, enable mapper scalar visibility, and set the mapper scalar mode to point data so the green control-point color is carried by disposable VTK point data without mutating `XQPath`.

The path control-point display metadata contract applies the XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows keep path control points visible by default but suppress the `PathControlPoints` actor category when the XQ node metadata `path.show.control.points` is `false`, without mutating `XQPath`.

The path use-tube display metadata contract applies the adjacent XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows keep tube rendering enabled by default but pass `use tube=false` to disposable path-curve actor products so they render XQPath display points as bare segmented `vtkLine` cells instead of a `vtkTubeFilter` surface, without mutating `XQPath`.

The path tube-radius display metadata contract applies the adjacent XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows read node metadata `tube radius` with default `0.3`, disposable path-curve actor products pass that value to visualization-layer `vtkTubeFilter`, and non-positive tube radius falls back to bare segmented `vtkLine` cells without mutating `XQPath`.

The path line-width display metadata contract applies the adjacent XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows read node metadata `line width` with default `1.0`, and disposable path-curve actor products set the visualization-layer `vtkActor` line width from that presentation row without mutating `XQPath`.

The path opacity display metadata contract applies the adjacent XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows read node metadata `opacity` with default `1.0`, and disposable path-curve plus path control-point actor products set the visualization-layer `vtkActor` opacity from that presentation row without mutating `XQPath`.

The path color display metadata contract applies the adjacent XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows read node metadata `color` with default green `(0.0, 1.0, 0.0)`, disposable path-curve actor products set the visualization-layer `vtkActor` color from that row, and disposable path control-point sphere glyph products use the same row color for point-data RGB scalars without mutating `XQPath`.

The path control-point point-size display metadata contract applies the adjacent XQ-main path display property from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: VTK-free presentation rows read node metadata `point size` with default `1.0`, and disposable path control-point sphere glyph products use radius `max(point size * 0.5, 0.2)` without mutating `XQPath`.

The path selected-control-point color contract applies the adjacent XQ-main path display properties from `xq_PathObjectFactory.cxx` and `xq_VesselTracer3D.cxx`: `PathControlPoint` has an XQ-owned `selected` state, VTK-free presentation rows read node metadata `selected color r`, `selected color g`, and `selected color b` with default red `(1.0, 0.0, 0.0)`, and disposable path control-point sphere glyph products color selected control points from that row while leaving unselected controls on the row path color, without mutating `XQPath`.

The contour display metadata contract applies the XQ-main 3D profile renderer defaults from `xq_ProfileRenderer3D.cxx`: VTK-free contour ring presentation rows read node metadata `color` with default green `(0.0, 1.0, 0.0)`, `opacity` with default `1.0`, and `contour.line width` with default `2.0`, and disposable contour ring actor products set the visualization-layer `vtkActor` color, opacity, and line width from those rows without mutating `XQContourGroup`.

## Owns

Future source files:

```text
src/visualization/XQScene3DPresentationModel.h
src/visualization/XQScene3DPresentationModel.cpp
src/visualization/XQScene3DRenderer.h
src/visualization/XQScene3DRenderer.cpp
src/visualization/XQScene3DViewWidget.h
src/visualization/XQScene3DViewWidget.cpp
src/visualization/XQActorFactory.h
src/visualization/XQActorFactory.cpp
tests/visualization/XQScene3DPresentationModelTest.cpp
tests/visualization/XQScene3DRendererTest.cpp
tests/visualization/XQScene3DViewWidgetTest.cpp
tests/visualization/XQActorFactoryTest.cpp
```

## Inputs

- `XQScene`.
- `XQPath`, `XQContourGroup`, `XQSegmentationMask`, `XQSurfaceModel`, `XQMesh`, and `XQSimulationCase`.
- VTK dependency role.

## Outputs

- A 3D render view that mirrors visible scene nodes.

## Rules

- VTK actors, volumes, and props are visualization products, not project data.
- Render-product lifetime follows scene node visibility and selection.
- Display settings may be stored separately from domain payloads.
- The viewer does not load files or run meshing algorithms.
- Presentation-model implementation contracts avoid VTK types and expose XQ-owned actor category rows only.
- Actor-factory implementation contracts may use VTK only inside the visualization layer.
- VTK polydata and image data produced by the actor factory are disposable render products derived from XQ-owned payload handles.

## Rendered Items

```text
path curves and control points
contour rings
segmentation mask exposed voxel faces
segmentation mask binary volume render product
segmentation mask smoothed/decimated extracted surface render product
surface models colored by face id
surface mesh and volume mesh
boundary condition markers
```

## Implementation Contract

Implementation Contract owns:

```text
src/visualization/XQScene3DPresentationModel.h
src/visualization/XQScene3DPresentationModel.cpp
src/visualization/XQScene3DRenderer.h
src/visualization/XQScene3DRenderer.cpp
tests/visualization/XQScene3DPresentationModelTest.cpp
tests/visualization/XQScene3DRendererTest.cpp
src/visualization/XQScene3DViewWidget.h
src/visualization/XQScene3DViewWidget.cpp
tests/visualization/XQScene3DViewWidgetTest.cpp
src/visualization/XQActorFactory.h
src/visualization/XQActorFactory.cpp
tests/visualization/XQActorFactoryTest.cpp
CMakeLists.txt
cmake/XQDependencies.cmake
```

Public class:

```text
xq::XQScene3DPresentationModel
xq::XQScene3DRenderer
xq::XQScene3DViewWidget
xq::XQActorPickAdapter
```

Public enum:

```text
xq::Scene3DActorCategory
```

Minimum public operations:

```text
setScene(XQScene*)
clearScene()
scene()
setSelectedNode(XQNodeId)
setSelectedNodeIfPresent(XQNodeId)
clearSelectedNode()
selectedNode()
setActorCategoryVisible(Scene3DActorCategory, bool)
isActorCategoryVisible(Scene3DActorCategory)
resetActorCategoryVisibility()
setCameraState(XQScene3DCameraState)
resetCameraState()
cameraState()
selectPickedActor(XQScene3DPickTarget)
actorRows()
actorRowsForNode(XQNodeId)
```

Minimum renderer operations:

```text
setRenderer(vtkRenderer*)
renderer()
sync(XQScene3DPresentationModel)
clear()
actorProducts()
render sync result: actorCount, skippedRowCount, renderRequested
```

Minimum Qt/VTK widget operations:

```text
setPresentationModel(XQScene3DPresentationModel*)
presentationModel()
syncFromPresentationModel()
renderFromPresentationModel()
lastSyncResult()
syncCameraStateToPresentationModel()
resetCameraToVisibleScene()
resetCameraToSelectedNode()
setSelectedNode(XQNodeId)
selectPickedActor(vtkActor*)
selectPickedProp(vtkProp*)
pickDisplayPosition(int, int)
setActorCategoryVisible(Scene3DActorCategory, bool)
toggleActorCategoryVisible(Scene3DActorCategory)
resetActorCategoryVisibility()
clearSelectedNode()
vtkWidget()
nativeRenderer()
nativeInteractor()
sceneRenderer()
```

Actor row data:

```text
node id
domain type
actor category
display name
visible
selected
stale
optional geometry summary:
  geometry backend name
  surface/model point count
  surface/model polygon count
  model face count
  mesh boundary face count
  mesh surface point/polygon count
  mesh volume point/cell count
```

Camera state data:

```text
position
focal point
view-up vector
clipping range
parallel projection flag
parallel scale
```

Pick target data:

```text
node id
actor category
```

Dependency boundary:

```text
XQScene3DPresentationModel has no VTK symbols.
XQActorFactory may expose VTK actor/prop products from the visualization layer only.
XQScene3DRenderer may bind disposable VTK props to an externally owned vtkRenderer.
XQScene3DViewWidget may own a QVTKOpenGLNativeWidget, vtkGenericOpenGLRenderWindow, and vtkRenderer inside the visualization layer only.
XQScene3DViewWidget may sync native vtkCamera state back into XQScene3DPresentationModel as VTK-free camera state.
XQScene3DViewWidget may reset its native vtkCamera to visible disposable render products and write the resulting camera state back to the VTK-free presentation model.
XQScene3DViewWidget may reset its native vtkCamera to disposable render products for the current selected XQ node and write the resulting camera state back to the VTK-free presentation model.
XQScene3DViewWidget may expose its native vtkRenderWindowInteractor from the visualization layer for Qt/VTK integration checks.
XQScene3DViewWidget may configure vtkInteractorStyleTrackballCamera on its native interactor inside the visualization layer only.
XQScene3DViewWidget may perform display-coordinate picking with a visualization-layer geometric VTK picker constrained to current disposable render products, then map the picked prop through XQ-owned pick targets.
XQScene3DViewWidget must not use hardware picking as the required path for display-position selection because headless Qt/OpenGL may be unavailable during automated verification.
XQScene3DViewWidget must consume repeated display-position picks on the already selected surface-model face without rebuilding disposable render products or requesting native render/update.
XQScene3DViewWidget may translate native QVTK left mouse-press coordinates into VTK display coordinates inside the visualization layer and route them through `pickDisplayPosition`.
XQScene3DViewWidget must consume native QVTK left mouse-press events when the display-position pick changes selection so later filters or default interaction do not run a second action for the same event.
XQScene3DViewWidget must consume repeated unmodified native QVTK left mouse-press events that hit the already selected render product without rebuilding disposable render products or requesting native render/update.
XQScene3DViewWidget may let modified native QVTK left mouse-press events such as `Ctrl+LeftButton` continue to later filters/default interaction because viewer display-position selection is bound only to unmodified left mouse press.
XQScene3DViewWidget may let combined native QVTK left mouse-press events such as `LeftButton+RightButton` continue to later filters/default interaction because viewer display-position selection requires left button to be the only pressed mouse button.
XQScene3DViewWidget may ignore non-left native mouse presses without changing selection, rebuilding disposable render products, or requesting native render/update.
XQScene3DViewWidget may sync native vtkCamera state back into the VTK-free presentation model on native QVTK mouse release without requesting an extra render/update.
XQScene3DViewWidget may defer native QVTK mouse-release camera-state sync until later native event filters or default interaction have completed, so the VTK-free presentation model stores the post-interaction camera state.
XQScene3DViewWidget may sync native vtkCamera state back into the VTK-free presentation model on native QVTK wheel events without requesting an extra render/update.
XQScene3DViewWidget may defer native QVTK wheel camera-state sync until later native event filters or default interaction have completed, so the VTK-free presentation model stores the post-interaction camera state.
XQScene3DViewWidget may translate native QVTK `F` key presses into a camera reset inside the visualization layer, preferring selected-node camera reset when a selected XQ node exists and falling back to visible-scene camera reset when no node is selected.
XQScene3DViewWidget may consume native QVTK `F` key presses that clear stale disposable render products and request native render/update while falling back to visible-scene camera reset, even when no camera reset is possible because the scene is now empty.
XQScene3DViewWidget may let native QVTK `F` key presses continue to later filters/default interaction when no presentation model is bound, because the camera-reset command is a no-op and must not request native render/update.
XQScene3DViewWidget may let modified native QVTK `F` key presses such as `Ctrl+F` continue to later filters/default interaction because viewer camera reset is bound only to unmodified `F`.
XQScene3DViewWidget may translate unmodified native QVTK `Escape` key presses into clear-selection inside the visualization layer and request native render/update only when selection state changes.
XQScene3DViewWidget must consume native QVTK key events it handles for viewer commands so later filters or default interaction do not run a second action for the same key event.
XQScene3DViewWidget may let modified native QVTK `Escape` key presses such as `Ctrl+Escape` continue to later filters/default interaction because viewer clear-selection is bound only to unmodified `Escape`.
XQScene3DViewWidget may let native QVTK `Escape` key presses continue to later filters/default interaction when no selection exists, because the clear-selection command is a no-op and must not rebuild disposable render products or request native render/update.
XQScene3DViewWidget may accept an external XQNodeId selection that exists in the bound XQScene and resync disposable render products so selected-highlight actor properties appear.
XQScene3DViewWidget may ignore repeated external XQNodeId selection for the already selected node without rebuilding disposable render products or requesting native render/update.
XQScene3DViewWidget may reject external XQNodeId selections that do not exist in the bound XQScene without storing selection state or requesting native render/update.
XQScene3DViewWidget may clear presentation selection and resync disposable render products so selected-highlight actor properties are removed.
XQScene3DViewWidget may request a native Qt/VTK render/update after synchronizing from the presentation model and report that request through XQ-owned render sync result data.
XQScene3DViewWidget may map picked disposable vtkProp products, including non-actor volume props, back to XQ-owned pick targets without storing VTK handles in XQScene.
XQScene3DViewWidget may switch from one non-null presentation model to another by clearing old disposable render products, recording an empty sync result, binding the new model pointer, and requesting native render/update when actual products were cleared.
XQScene3DViewWidget may unbind a presentation model without requesting native render/update when no disposable render products were present to clear.
XQScene3DViewWidget may ignore actor-category visibility requests that do not change presentation state without rebuilding disposable render products or requesting native render/update.
XQScene3DViewWidget may toggle a VTK-free actor category visibility state, resync disposable render products, and request native render/update without mutating XQScene node visibility or domain payloads.
XQScene3DViewWidget may ignore actor-category visibility toggle requests without a bound presentation model without rebuilding disposable render products or requesting native render/update.
XQScene3DViewWidget may ignore actor-category visibility reset requests when no categories are hidden without rebuilding disposable render products or requesting native render/update.
XQScene3DViewWidget may ignore clear-selection requests when no node is selected without rebuilding disposable render products or requesting native render/update.
Core, project IO, workflow, and domain services must not include VTK headers.
```

Forbidden ownership:

```text
geometry copies
face metadata copies beyond display category rows
payload array copies inside actor rows
VTK actor, volume, or prop handles in XQScene or domain payloads
mesh or model payload edits
```

## Step Plan

- [x] Build XQ-owned actor category rows for each XQ domain type.
- [x] Maintain selected node id as viewer state.
- [x] Project visibility and stale state from `XQScene`.
- [x] Expose payload-derived model/mesh geometry summaries for future actor factories without copying geometry arrays.
- [x] Defer VTK actor factories until VTK is pinned and found through the controlled dependency prefix.
- [x] Add `XQActorFactory` for generated triangle surface model and mesh payloads using controlled-prefix VTK.
- [x] Add disposable face-id cell scalars for generated model and mesh surface actors.
- [x] Add tests that verify scene nodes create expected actor categories.
- [x] Clear stale selected node ids when `XQScene3DPresentationModel` switches to a scene that does not contain the previous selection.
- [x] Clear stale selected node ids when the selected scene node is removed.
- [x] Add tests that verify loaded/generated model and mesh rows expose XQ-owned payload counts.
- [x] Add tests that verify VTK actor geometry is derived from XQ-owned triangle payload handles without storing actor handles in `XQScene`.
- [x] Add `XQActorFactory` path curve and contour ring actor products derived from XQ-owned path samples/control points and contour points.
- [x] Add `XQActorFactory` tetrahedral volume mesh actor products derived from XQ-owned volume mesh handles.
- [x] Add `XQActorFactory` segmentation mask exposed-voxel-face surface actor products derived from XQ-owned mask geometry.
- [x] Add controlled VTK `RenderingVolume` and `RenderingVolumeOpenGL2` modules plus autoinit wiring for volume rendering overrides.
- [x] Add `XQActorFactory` segmentation mask volume render products derived from XQ-owned mask geometry through disposable `vtkImageData`.
- [x] Apply segmentation-mask `color` and `opacity` display metadata to disposable segmentation mask volume transfer functions without mutating XQ segmentation mask payloads.
- [x] Add controlled VTK `FiltersCore` and `FiltersGeneral` modules for visualization-layer mask surface extraction, smoothing, and decimation.
- [x] Add `XQActorFactory` segmentation mask smoothed/decimated extracted surface actor products derived from XQ-owned mask geometry through disposable VTK pipeline data.
- [x] Add VTK-free 3D camera state to the presentation model for future viewer/widget binding.
- [x] Add VTK-free pick target selection wiring from actor node/category back to selected scene node.
- [x] Add `XQActorFactory` boundary condition marker actor products from explicit simulation-plus-mesh context.
- [x] Add VTK actor/prop pick adapter that maps picked disposable actors and props back to XQ-owned pick targets.
- [x] Add a non-Qt `XQScene3DRenderer` synchronization layer that binds disposable actor/prop products to an externally owned `vtkRenderer`.
- [x] Add tests that verify renderer synchronization adds visible XQ-derived actors and removes stale disposable actors on resync without storing VTK in `XQScene`.
- [x] Extend renderer synchronization from actor-only lifecycle to disposable VTK view-prop lifecycle so segmentation mask surface and volume products can coexist.
- [x] Decode loaded `.vtu` tetrahedral volume geometry into XQ-owned volume mesh handles before 3D actor creation.
- [x] Add controlled Qt6 package verification and VTK `GUISupportQt`/interaction modules required by the Qt/VTK scene widget.
- [x] Add `XQScene3DViewWidget` that embeds `QVTKOpenGLNativeWidget`, owns a disposable `vtkRenderer`, and syncs visible XQ-derived render products through `XQScene3DRenderer`.
- [x] Expose the native render-window interactor and configure `vtkInteractorStyleTrackballCamera` in `XQScene3DViewWidget`.
- [x] Bind VTK-free presentation camera state into the Qt/VTK widget's native `vtkCamera`.
- [x] Sync native `vtkCamera` state back into `XQScene3DPresentationModel` as VTK-free camera state.
- [x] Add `XQScene3DViewWidget` reset-to-visible-scene camera interaction that keeps presentation camera state in sync.
- [x] Add `XQScene3DViewWidget` pick-to-selection wiring that maps a disposable `vtkActor` through `XQActorPickAdapter` back into `XQScene3DPresentationModel`.
- [x] Extend `XQScene3DViewWidget` pick-to-selection wiring from disposable `vtkActor` to disposable `vtkProp` so segmentation mask volume props can select their XQ-owned node.
- [x] Add `XQScene3DViewWidget` display-position picking that uses a geometric VTK picker limited to current disposable render products and reuses the existing prop-to-XQ selection path.
- [x] Avoid native render/update and selection changes when `XQScene3DViewWidget` display-position picking misses all current disposable render products.
- [x] Consume repeated display-position picks on the already selected surface-model face without rebuilding disposable render products or requesting native render/update.
- [x] Add `XQScene3DViewWidget` native-widget left mouse-press event bridge that converts Qt coordinates to VTK display coordinates and reuses display-position picking.
- [x] Consume native-widget left mouse-press events after a successful display-position pick.
- [x] Consume repeated native-widget left mouse-press events that hit the already selected render product without requesting native render/update.
- [x] Avoid consuming modified native-widget left mouse-press events such as `Ctrl+LeftButton` and avoid selection/render requests for those events.
- [x] Avoid consuming combined native-widget left mouse-press events such as `LeftButton+RightButton` and avoid selection/render requests for those events.
- [x] Avoid native render/update and selection changes when `XQScene3DViewWidget` receives a non-left native mouse press.
- [x] Add `XQScene3DViewWidget` native-widget mouse-release event bridge that syncs native camera state back to the VTK-free presentation model.
- [x] Add `XQScene3DViewWidget` native-widget wheel event bridge that syncs native camera state back to the VTK-free presentation model.
- [x] Defer `XQScene3DViewWidget` native-widget mouse-release camera-state sync until later native event filters/default interaction have completed.
- [x] Defer `XQScene3DViewWidget` native-widget wheel camera-state sync until later native event filters/default interaction have completed.
- [x] Add `XQScene3DViewWidget` native-widget `F` key bridge that resets the camera to the selected XQ node when a selection exists.
- [x] Add `XQScene3DViewWidget` native-widget `F` key fallback that resets the camera to the visible scene when no selection exists.
- [x] Avoid consuming modified native-widget `F` key events such as `Ctrl+F` and avoid viewer camera reset/render requests for those events.
- [x] Add `XQScene3DViewWidget` native-widget `Escape` key bridge that clears the current presentation selection.
- [x] Consume handled native-widget key events after the `F` and `Escape` viewer commands are processed.
- [x] Avoid consuming modified native-widget `Escape` key events such as `Ctrl+Escape` and avoid clear-selection/render requests for those events.
- [x] Avoid consuming native-widget `Escape` key events when no selection exists and the clear-selection command is a no-op.
- [x] Clear `XQScene3DViewWidget` disposable render products when the presentation model is switched or unbound.
- [x] Apply selected-row highlight to disposable ActorFactory surface actors without mutating XQ payloads.
- [x] Apply stale-row dimmed opacity to disposable ActorFactory actors without mutating XQ payloads.
- [x] Resync `XQScene3DViewWidget` disposable render products after successful actor pick so selected rows render with highlight properties.
- [x] Add `XQScene3DViewWidget` external node-selection interaction that resyncs disposable render products with selected-highlight properties.
- [x] Reject `XQScene3DViewWidget` external node-selection requests for missing scene nodes without storing selection state or requesting native render/update.
- [x] Add `XQScene3DViewWidget` clear-selection interaction that resyncs disposable render products without selected-highlight properties.
- [x] Add `XQScene3DViewWidget` render-from-presentation interaction that syncs disposable render products and reports a native render/update request.
- [x] Add VTK-free actor-category visibility controls to `XQScene3DPresentationModel`.
- [x] Add tests proving category visibility filters disposable render products without mutating `XQScene` node visibility or domain payloads.
- [x] Add `XQScene3DViewWidget` actor-category visibility bridge that updates presentation state and resyncs disposable render products.
- [x] Request native Qt/VTK render/update after `XQScene3DViewWidget` actor-category visibility changes.
- [x] Add `XQScene3DViewWidget` actor-category visibility reset interaction that restores filtered products and requests native render/update.
- [x] Request native Qt/VTK render/update after `XQScene3DViewWidget` external selection, disposable actor pick, disposable prop pick, and clear-selection interactions.
- [x] Request native Qt/VTK render/update after `XQScene3DViewWidget` reset-to-visible-scene camera interaction.
- [x] Request native Qt/VTK render/update when `XQScene3DViewWidget` reset-to-visible-scene synchronization clears previously visible render products because no visible scene products remain.
- [x] Request native Qt/VTK render/update after `XQScene3DViewWidget` clears disposable render products on presentation-model unbind.
- [x] Avoid native Qt/VTK render/update when `XQScene3DViewWidget` unbinds a presentation model that has no disposable render products to clear.
- [x] Avoid native Qt/VTK render/update when `XQScene3DViewWidget` receives an actor-category visibility request that does not change presentation state.
- [x] Avoid native Qt/VTK render/update when `XQScene3DViewWidget` resets actor-category visibility while no categories are hidden.
- [x] Avoid native Qt/VTK render/update when `XQScene3DViewWidget` clears selection while no node is selected.
- [x] Avoid native Qt/VTK render/update when `XQScene3DViewWidget` receives an external selection request for the already selected node.
- [x] Add `XQScene3DViewWidget` selected-node camera reset that frames only disposable render products for the current selected XQ node.
- [x] Sync the selected-node camera reset back into the VTK-free presentation camera state.
- [x] Request native Qt/VTK render/update after a successful selected-node camera reset.
- [x] Avoid native Qt/VTK render/update when selected-node camera reset has no bound presentation model, no selected node, or no visible render product for the selected node.
- [x] Add `XQScene3DViewWidget` actor-category visibility toggle interaction that hides a visible category and resyncs disposable render products.
- [x] Add `XQScene3DViewWidget` actor-category visibility toggle interaction that restores a hidden category and resyncs disposable render products.
- [x] Request native Qt/VTK render/update after `XQScene3DViewWidget` actor-category visibility toggle changes.
- [x] Avoid native Qt/VTK render/update when actor-category visibility toggle is requested without a bound presentation model.
- [x] Add VTK-free `PathControlPoints` actor category rows for visible XQ path nodes.
- [x] Add `XQActorFactory` path control-point actor products derived from `XQPath::controlPoints()` without mutating or copying path payload ownership into `XQScene`.
- [x] Add pick-target support for path control-point actor products through the existing `XQActorPickAdapter` node/category path.
- [x] Apply XQ-main-derived green overlay display style to `XQActorFactory` path curve actor products without mutating XQ path payloads.
- [x] Apply XQ-main-derived green, wider overlay display style to `XQActorFactory` contour ring actor products without mutating XQ contour payloads.
- [x] Apply XQ-main-derived path control-point sphere glyph display products without mutating XQ path payloads.
- [x] Apply XQ-main-derived `vtkPolyDataNormals` point/cell normal generation to disposable surface-model actor products without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived surface-model face-id cell-field mapper coloring to disposable surface-model actor products without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived surface-model face-id lookup-table/range mapper configuration to disposable surface-model actor products without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived surface-model face-id metadata guard so disposable surface-model actor products disable scalar coloring when XQ model face metadata is empty.
- [x] Apply XQ-main-derived surface-model material lighting defaults to disposable surface-model actor products without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived `wireframe` display metadata to VTK-free surface-model presentation rows and disposable actor representation without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived surface-model `color`/`opacity` display metadata to VTK-free surface-model presentation rows and row-driven actor opacity without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived surface-model `selectedFaceId` display metadata to VTK-free surface-model presentation rows and disposable cell-color face highlighting without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived surface-model display-position face-picking to `XQScene3DViewWidget` so disposable `xq_face_id` picks write `selectedFaceId` node metadata and selection clear resets it to `-1` without mutating XQ surface-model payloads.
- [x] Apply XQ-main-derived 3D segmentation mask surface display style to disposable exposed-voxel-face actor products without mutating XQ segmentation mask payloads.
- [x] Apply XQ-main-derived `vtkPolyDataNormals` point/cell normal generation to disposable segmentation mask exposed-voxel-face surface actor products without mutating XQ segmentation mask payloads.
- [x] Apply XQ-main-derived segmentation mask 3D `color`, `opacity`, `seg3d.edge visibility`, and `seg3d.edge color` display metadata to VTK-free rows and disposable exposed/smoothed surface actor properties without mutating XQ segmentation mask payloads.
- [x] Apply XQ-main-derived volume mesh grid display style to disposable tetrahedral volume-grid actor products without mutating XQ mesh payloads.
- [x] Apply XQ-main-derived mesh grid display style to disposable triangle surface-mesh actor products without mutating XQ mesh payloads.
- [x] Apply XQ-main-derived `mesh.wireframe` display metadata to VTK-free mesh presentation rows and disposable mesh actor representation without mutating XQ mesh payloads.
- [x] Apply XQ-main-derived mesh `color`/`opacity` display metadata to VTK-free mesh presentation rows and disposable mesh surface/volume actor properties without mutating XQ mesh payloads.
- [x] Apply XQ-main-derived path curve tube pipeline to disposable path actor products without mutating XQ path payloads.
- [x] Apply XQ-main-derived path curve segmented-line tube topology to disposable path actor products without mutating XQ path payloads.
- [x] Apply XQ-main-derived `use tube` display metadata to VTK-free path curve presentation rows and disposable path actor products without mutating XQ path payloads.
- [x] Apply XQ-main-derived `tube radius` display metadata to VTK-free path curve presentation rows, disposable tube radius, and non-positive bare-polyline fallback without mutating XQ path payloads.
- [x] Apply XQ-main-derived `line width` display metadata to VTK-free path curve presentation rows and disposable actor line-width property without mutating XQ path payloads.
- [x] Apply XQ-main-derived `opacity` display metadata to VTK-free path curve presentation rows and disposable actor opacity property without mutating XQ path payloads.
- [x] Apply XQ-main-derived contour ring closed line-segment topology to disposable contour actor products without mutating XQ contour payloads.
- [x] Apply XQ-main-derived path control-point point-data RGB scalars and mapper point-data scalar visibility to disposable sphere-glyph actor products without mutating XQ path payloads.
- [x] Apply XQ-main-derived `path.show.control.points` display metadata filtering to VTK-free path control-point presentation rows without mutating XQ path payloads.
- [x] Apply XQ-main-derived `point size` display metadata to VTK-free path control-point presentation rows and disposable sphere-glyph radius/min-radius behavior without mutating XQ path payloads.
- [x] Apply XQ-main-derived `selected color r/g/b` display metadata to VTK-free path control-point presentation rows and disposable selected-control-point RGB scalar coloring from XQ-owned `PathControlPoint::selected` without mutating XQ path payloads.
- [x] Apply XQ-main-derived 3D segmentation mask surface display style to disposable smoothed extracted surface actor products without mutating XQ segmentation mask payloads.
- [x] Apply XQ-main-derived `vtkPolyDataNormals` point/cell normal generation to disposable segmentation mask smoothed extracted surface actor products without mutating XQ segmentation mask payloads.
- [x] Apply XQ-main-derived contour `color`, `opacity`, and `contour.line width` display metadata to VTK-free contour ring presentation rows and disposable actor properties without mutating XQ contour payloads.
- [x] Record XQ-main record for the completed 3D viewer display-style implementation contracts and explicitly reject old mapper behavior that lacks an XQ-owned payload contract.

## Test Plan

Test target:

xq_visualization_tests
xq_scene_3d_view_widget_tests

Test file:

tests/visualization/XQScene3DPresentationModelTest.cpp
tests/visualization/XQScene3DRendererTest.cpp
tests/visualization/XQScene3DViewWidgetTest.cpp
tests/visualization/XQActorFactoryTest.cpp

Core scenarios:

XQScene3DPresentationModelCreatesActorRowsForSceneDomains
XQScene3DPresentationModelCreatesControlPointRowsForPaths
XQScene3DPresentationModelPathControlPointRowsFollowNodeDisplayMetadata
XQScene3DPresentationModelPathCurveRowsFollowUseTubeDisplayMetadata
XQScene3DPresentationModelPathCurveRowsFollowTubeRadiusDisplayMetadata
XQScene3DPresentationModelPathCurveRowsFollowLineWidthDisplayMetadata
XQScene3DPresentationModelPathCurveRowsFollowOpacityDisplayMetadata
XQScene3DPresentationModelPathCurveRowsFollowColorDisplayMetadata
XQScene3DPresentationModelPathControlPointRowsFollowPointSizeDisplayMetadata
XQScene3DPresentationModelContourRowsFollowDisplayMetadata
XQScene3DPresentationModelSurfaceModelRowsFollowWireframeDisplayMetadata
XQScene3DPresentationModelSurfaceModelRowsFollowColorOpacityDisplayMetadata
XQScene3DPresentationModelSegmentationMaskRowsFollow3DDisplayMetadata
XQScene3DPresentationModelMeshRowsFollowWireframeDisplayMetadata
XQScene3DPresentationModelMeshRowsFollowColorOpacityDisplayMetadata
XQScene3DPresentationModelSkipsInvisibleNodes
XQScene3DPresentationModelMarksSelectedNodeRows
XQScene3DPresentationModelReflectsSceneRemoval
XQScene3DPresentationModelClearsSelectionWhenSelectedNodeIsRemoved
XQScene3DPresentationModelClearsStaleSelectionWhenSceneChanges
XQScene3DPresentationModelCreatesActorRowsForSegmentationMask
XQScene3DPresentationModelReportsGeometrySummaryForSurfaceModelPayload
XQScene3DPresentationModelReportsGeometrySummaryForMeshPayload
XQScene3DPresentationModelStoresCameraStateWithoutVTK
XQScene3DPresentationModelCameraStateSurvivesSceneClearAndCanReset
XQScene3DPresentationModelSelectsNodeFromVisiblePickTarget
XQScene3DPresentationModelRejectsPickTargetWithoutVisibleActorRow
XQScene3DPresentationModelFiltersActorRowsByCategoryVisibility
XQScene3DPresentationModelRejectsPickTargetForHiddenActorCategory
XQScene3DPresentationModelSetSelectedNodeIfPresentWithoutChangeReportsNoStateChange
XQActorFactoryCreatesSurfaceModelActorFromTriangleGeometry
XQActorFactoryCreatesMeshSurfaceActorFromTriangleMesh
XQActorFactoryCreatesSurfaceActorFaceIdCellScalars
XQActorFactorySurfaceModelActorUsesFaceIdCellFieldColoring
XQActorFactorySurfaceModelActorUsesFaceIdLookupTableRange
XQActorFactorySurfaceModelActorDisablesFaceIdColoringWithoutFaceMetadata
XQActorFactorySurfaceModelActorComputesPointAndCellNormals
XQActorFactorySelectedSurfaceActorUsesHighlightPropertyWithoutMutatingPayload
XQActorFactoryStaleSurfaceActorUsesDimmedOpacityWithoutMutatingPayload
XQActorFactorySurfaceModelActorUsesMaterialLightingDefaults
XQActorFactorySurfaceModelActorUsesWireframeFromPresentationRow
XQActorFactorySurfaceModelActorUsesOpacityFromPresentationRow
XQActorFactoryCreatesMeshActorFaceIdCellScalars
XQActorFactoryMeshSurfaceActorUsesGridDisplayStyle
XQActorFactoryCreatesVolumeMeshActorFromTetrahedralGrid
XQActorFactoryVolumeMeshActorUsesGridDisplayStyle
XQActorFactoryMeshActorUsesWireframeFromPresentationRow
XQActorFactoryMeshActorsUseColorOpacityFromPresentationRow
XQActorFactoryCreatesSegmentationMaskActorFromActiveVoxels
XQActorFactoryCreatesSegmentationMaskSurfaceActorFromExposedVoxelFaces
XQActorFactorySegmentationMaskSurfaceActorUses3DDisplayStyle
XQActorFactorySegmentationMaskSurfaceActorsUseDisplayPropertiesFromPresentationRow
XQActorFactorySegmentationMaskSurfaceActorComputesPointAndCellNormals
XQActorFactoryCreatesSegmentationMaskVolumeRenderProduct
XQActorFactorySegmentationMaskVolumeUsesDisplayPropertiesFromPresentationRow
XQActorFactoryCreatesSegmentationMaskSmoothedSurfaceActor
XQActorFactorySegmentationMaskSmoothedSurfaceActorUses3DDisplayStyle
XQActorFactorySegmentationMaskSmoothedSurfaceActorComputesPointAndCellNormals
XQActorFactoryRejectsEmptySegmentationMaskActor
XQActorFactoryCreatesBoundaryConditionMarkerActorFromMeshContext
XQActorFactoryRejectsBoundaryConditionMarkersWithoutTriangleCellContext
XQActorPickAdapterMapsPickedActorToScenePickTarget
XQActorPickAdapterRejectsUnknownOrNullActor
XQScene3DRendererSyncsVisibleActorsIntoVtkRenderer
XQScene3DRendererSyncsSegmentationMaskSurfaceAndVolumeProps
XQScene3DRendererRemovesPreviousActorsOnResync
XQActorFactoryRejectsUnsupportedPayloadGeometry
XQActorFactoryCreatesPathCurveActorFromPathSamples
XQActorFactoryPathCurveActorUsesTubePipeline
XQActorFactoryPathCurveActorUsesSegmentedLineTubeTopology
XQActorFactoryPathCurveActorUsesTubeRadiusFromPresentationRow
XQActorFactoryPathCurveActorUsesLineWidthFromPresentationRow
XQActorFactoryPathCurveActorUsesOpacityFromPresentationRow
XQActorFactoryPathCurveActorCanUseBarePolylineWhenTubeDisabled
XQActorFactoryPathCurveActorUsesBarePolylineWhenTubeRadiusIsNotPositive
XQActorFactoryCreatesPathControlPointActorFromControlPoints
XQActorFactoryPathControlPointActorUsesSphereGlyphOverlayStyle
XQActorFactoryPathControlPointActorUsesPointSizeForSphereRadius
XQActorFactoryPathControlPointActorUsesMinimumSphereRadius
XQActorFactoryPathControlPointActorUsesPointDataScalars
XQActorFactoryCreatesContourRingActorFromContourPoints
XQActorFactoryContourRingActorUsesClosedLineSegments
XQActorFactoryContourRingActorUsesOverlayDisplayStyle
XQActorFactoryContourRingActorUsesDisplayPropertiesFromPresentationRow
XQActorFactoryRejectsMismatchedPathAndContourRows
XQScene3DViewWidgetOwnsNativeQvtkWidgetAndRendererBridge
XQScene3DViewWidgetConfiguresNativeTrackballCameraInteractor
XQScene3DViewWidgetBindsPresentationModelWithoutOwningSceneData
XQScene3DViewWidgetAppliesPresentationCameraStateToNativeRenderer
XQScene3DViewWidgetSyncsNativeRendererCameraStateBackToPresentationModel
XQScene3DViewWidgetResetCameraToVisibleSceneSyncsPresentationModelCameraState
XQScene3DViewWidgetResetCameraToVisibleSceneRequestsNativeRender
XQScene3DViewWidgetResetCameraToEmptyVisibleSceneClearsProductsAndRequestsNativeRender
XQScene3DViewWidgetResetCameraToSelectedNodeSyncsPresentationModelCameraState
XQScene3DViewWidgetResetCameraToSelectedNodeRequestsNativeRender
XQScene3DViewWidgetResetCameraToSelectedNodeWithoutSelectionDoesNotRequestNativeRender
XQScene3DViewWidgetResetCameraToSelectedNodeWithoutVisibleProductDoesNotRequestNativeRender
XQScene3DViewWidgetSelectsPresentationNodeFromDisposableVtkActor
XQScene3DViewWidgetSelectPickedActorResyncsRendererWithSelectedHighlight
XQScene3DViewWidgetSelectPickedActorRequestsNativeRender
XQScene3DViewWidgetPickDisplayPositionSelectsVisibleActorThroughNativePicker
XQScene3DViewWidgetPickDisplayPositionWithoutHitDoesNotChangeSelectionOrRequestRender
XQScene3DViewWidgetMousePressOnNativeWidgetSelectsVisibleActor
XQScene3DViewWidgetHandledMousePickOnNativeWidgetIsConsumed
XQScene3DViewWidgetRepeatedMousePressOnNativeWidgetIsConsumedWithoutRenderRequest
XQScene3DViewWidgetModifiedLeftMousePressOnNativeWidgetDoesNotSelectOrConsume
XQScene3DViewWidgetCombinedLeftMousePressOnNativeWidgetDoesNotSelectOrConsume
XQScene3DViewWidgetRightMousePressOnNativeWidgetDoesNotSelectOrRequestRender
XQScene3DViewWidgetMouseReleaseOnNativeWidgetSyncsCameraStateToPresentationModel
XQScene3DViewWidgetWheelOnNativeWidgetSyncsCameraStateToPresentationModel
XQScene3DViewWidgetMouseReleaseCameraSyncRunsAfterNativeEventFilters
XQScene3DViewWidgetWheelCameraSyncRunsAfterNativeEventFilters
XQScene3DViewWidgetFKeyOnNativeWidgetResetsCameraToSelectedNode
XQScene3DViewWidgetFKeyOnNativeWidgetWithoutSelectionResetsCameraToVisibleScene
XQScene3DViewWidgetModifiedFKeyOnNativeWidgetDoesNotResetOrConsume
XQScene3DViewWidgetEscapeKeyOnNativeWidgetClearsSelectedNode
XQScene3DViewWidgetHandledKeyOnNativeWidgetIsConsumed
XQScene3DViewWidgetModifiedEscapeKeyOnNativeWidgetDoesNotClearOrConsume
XQScene3DViewWidgetEscapeKeyWithoutSelectionDoesNotConsumeOrRequestNativeRender
XQScene3DViewWidgetSelectPickedPropSelectsSegmentationMaskVolume
XQScene3DViewWidgetSelectPickedPropRequestsNativeRender
XQScene3DViewWidgetSetSelectedNodeResyncsRendererWithSelectedHighlight
XQScene3DViewWidgetSetSelectedNodeRequestsNativeRender
XQScene3DViewWidgetSetSelectedNodeWithoutStateChangeDoesNotRequestNativeRender
XQScene3DViewWidgetRejectsExternalSelectionForMissingNode
XQScene3DViewWidgetRenderFromPresentationModelSyncsRendererAndRequestsRender
XQScene3DViewWidgetRenderFromPresentationModelWithoutModelDoesNotRequestRender
XQScene3DViewWidgetClearSelectedNodeResyncsRendererWithoutSelectedHighlight
XQScene3DViewWidgetClearSelectedNodeRequestsNativeRender
XQScene3DViewWidgetClearSelectedNodeWithoutSelectionDoesNotRequestNativeRender
XQScene3DViewWidgetClearsDisposableRenderProductsWhenPresentationModelUnbinds
XQScene3DViewWidgetPresentationModelUnbindRequestsNativeRenderAfterClearingProducts
XQScene3DViewWidgetPresentationModelUnbindWithoutProductsDoesNotRequestNativeRender
XQScene3DViewWidgetSetActorCategoryVisibleRequestsNativeRender
XQScene3DViewWidgetSetActorCategoryVisibleWithoutStateChangeDoesNotRequestNativeRender
XQScene3DViewWidgetToggleActorCategoryVisibleHidesVisibleCategoryAndRequestsNativeRender
XQScene3DViewWidgetToggleActorCategoryVisibleRestoresHiddenCategoryAndRequestsNativeRender
XQScene3DViewWidgetToggleActorCategoryVisibleWithoutModelDoesNotRequestNativeRender
XQScene3DViewWidgetResetActorCategoryVisibilityResyncsProductsAndRequestsNativeRender
XQScene3DViewWidgetResetActorCategoryVisibilityWithoutStateChangeDoesNotRequestNativeRender
MeshReaderDecodesVtuTetrahedralVolume
XQScene3DRendererRespectsPresentationCategoryVisibility

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_visualization_scene_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQScene3DPresentationModel --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_scene_3d_view_widget_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQScene3DViewWidget --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_visualization_vtk_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQActorFactory --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build -R XQScene3DRenderer --output-on-failure
```

Expected result:

presentation model tests pass without requiring VTK
actor factory tests pass with VTK resolved from <xq-rebuild-workspace>/externals/install
scene view widget tests pass with Qt6 and VTK `GUISupportQt` resolved from <xq-rebuild-workspace>/externals/install

## Acceptance

- Loaded model and mesh from `<acceptance-project>` display as scene-owned data.
- Selection in the project tree highlights the corresponding 3D item.
- Deleting a node removes render props without touching other scene data.
- The initial contract proves 3D display categories come from `XQScene` and node ids, not external actor storage.

## XQ-main.zip Evidence

Evidence source root: `<xq-source-extract>`

Files studied:

```text
Code/Source/xq4gui/Modules/Path/xq_PathObjectFactory.cxx
Code/Source/xq4gui/Modules/Path/xq_VesselTracer3D.cxx
Code/Source/xq4gui/Modules/Segmentation/xq_ProfileRenderer3D.cxx
Code/Source/xq4gui/Modules/Segmentation/xq_SurfaceRenderer3D.cxx
Code/Source/xq4gui/Modules/Segmentation/xq_MitkSeg3DVtkMapper3D.cxx
Code/Source/xq4gui/Modules/Model/Common/xq_ModelObjectFactory.cxx
Code/Source/xq4gui/Modules/Model/Common/xq_GeomRenderer3D.cxx
Code/Source/xq4gui/Modules/Mesh/Common/xq_MitkGridObjectFactory.cxx
Code/Source/xq4gui/Modules/Mesh/Common/xq_MitkGridMapper3D.cxx
```

Behavior kept:

```text
Path curve/control-point rows and disposable actors keep XQ-main display metadata:
  path.show.control.points, use tube, tube radius, line width, opacity, color, and point size.
Path curves use segmented vtkLine topology, optional vtkTubeFilter radius 0.3 by default,
  12 tube sides, tube capping, and bare-polyline fallback when tube rendering is disabled
  or the radius is non-positive.
Path control points render as disposable sphere glyphs with point-data RGB scalars,
  point-data mapper coloring, opacity, row-driven color, and radius max(point size * 0.5, 0.2).
Selected path control points use XQ-owned PathControlPoint::selected plus
  row-driven selected color r/g/b metadata, defaulting to red, while unselected
  controls keep the row path color.
Contour rings use closed per-edge vtkLine topology plus row-driven color, opacity,
  and contour.line width defaults.
Surface-model actors use XQ-main model defaults for color, opacity, wireframe,
  selectedFaceId, face-id cell-field mapper coloring, face-id lookup-table/range,
  selected-face FaceColors highlighting, point/cell normal generation, and material
  ambient/diffuse/specular/specular-power defaults.
Segmentation-mask exposed and smoothed surface actors use XQ-main color, opacity,
  seg3d.edge visibility, seg3d.edge color, and point/cell normal generation.
Segmentation-mask volume render products use the same VTK-free color/opacity
  presentation row values for disposable VTK transfer-function endpoints.
Mesh surface and volume actors use XQ-main mesh.wireframe, color, opacity, surface
  representation, edge visibility, and half-strength edge color defaults.
```

Behavior rejected:

```text
MITK DataNode/DataStorage ownership, CoreObjectFactory registration, mapper local
storage, BaseRenderer-time-step coupling, BlueBerry/CTK/plugin entrypoints, and
framework-level visibility are not migrated.
Segmentation seed-point rendering and seg3d.seed point size are not implemented in
the 3D viewer pass because XQSegmentationMask does not yet define XQ-owned seed-point
payload contract.
Contour loft-surface display from contour.show surface and contour.surface opacity
is not implemented in the viewer pass because XQContourGroup stores contours
and loft settings, not a generated loft-surface payload.
Per-face model color/opacity from old FaceInfo is not copied into XQSurfaceModel
display state because current model face metadata is an XQ-owned domain/boundary
contract, not a rendering-color contract.
```

Rewrite owner:

```text
src/visualization/XQScene3DPresentationModel.h
src/visualization/XQScene3DPresentationModel.cpp
src/visualization/XQActorFactory.h
src/visualization/XQActorFactory.cpp
src/visualization/XQScene3DRenderer.h
src/visualization/XQScene3DRenderer.cpp
src/visualization/XQScene3DViewWidget.h
src/visualization/XQScene3DViewWidget.cpp
tests/visualization/XQScene3DPresentationModelTest.cpp
tests/visualization/XQActorFactoryTest.cpp
tests/visualization/XQScene3DRendererTest.cpp
tests/visualization/XQScene3DViewWidgetTest.cpp
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If VTK actors become authoritative storage for geometry or face metadata, repair the relevant payload and actor factory.
