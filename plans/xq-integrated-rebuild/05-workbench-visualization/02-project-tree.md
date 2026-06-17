# Project Tree

## Purpose

Define the project tree view that presents the `XQScene` groups and nodes.

The initial contract created a scene-backed XQ project tree model. The next contract added a Qt `QAbstractItemModel` adapter over that scene-backed model now that Qt6 is resolved from the controlled dependency prefix. The current contracts add a concrete `QTreeView` widget composition around that adapter, route selected-node rename and remove requests through the undoable command stack, and expose stale-row diagnostics plus domain decorations for the Qt tree. The Qt adapter and widget must wrap this contract rather than becoming a second scene graph.

## Owns

Future source files:

```text
src/workbench/XQProjectTreeModel.h
src/workbench/XQProjectTreeModel.cpp
src/workbench/XQProjectTreeQtModel.h
src/workbench/XQProjectTreeQtModel.cpp
src/workbench/XQProjectTreeViewWidget.h
src/workbench/XQProjectTreeViewWidget.cpp
tests/workbench/XQProjectTreeModelTest.cpp
tests/workbench/XQProjectTreeQtModelTest.cpp
tests/workbench/XQProjectTreeViewWidgetTest.cpp
```

## Inputs

- `XQScene` ownership.
- `XQDataNode` metadata.

## Outputs

- A Qt model/view representation of scene groups and nodes.

## Rules

- The tree model is a view of `XQScene`, not a second scene graph.
- Selection emits node ids, not raw payload pointers.
- Visibility and lock toggles call XQ scene or visualization state APIs.
- The tree does not parse files or run algorithms.
- The initial contract must avoid Qt types and expose XQ-owned node ids and group rows.
- The Qt model/view pass may use Qt Core model roles and QtGui/QtWidgets decoration types only in the workbench layer and must keep Qt out of core, project, workflow, and domain payload APIs.
- The Qt adapter must expose node ids through an XQ-owned helper, not by leaking raw payload pointers through Qt indexes.

## Display Groups

```text
Images
Paths
Segmentations
Models
Meshes
Simulations
Results
```

## Implementation Contract

Implementation Contract owns:

```text
src/workbench/XQProjectTreeModel.h
src/workbench/XQProjectTreeModel.cpp
tests/workbench/XQProjectTreeModelTest.cpp
```

Qt adapter contract owns:

```text
src/workbench/XQProjectTreeQtModel.h
src/workbench/XQProjectTreeQtModel.cpp
tests/workbench/XQProjectTreeQtModelTest.cpp
CMakeLists.txt
```

QTreeView widget contract owns:

```text
src/workbench/XQProjectTreeViewWidget.h
src/workbench/XQProjectTreeViewWidget.cpp
tests/workbench/XQProjectTreeViewWidgetTest.cpp
CMakeLists.txt
```

Public class:

```text
xq::XQProjectTreeModel
xq::XQProjectTreeQtModel
xq::XQProjectTreeViewWidget
```

Minimum public operations:

```text
setScene(XQScene*)
clearScene()
scene()
groups()
nodes(XQSceneGroup)
selectNode(XQNodeId)
selectedNode()
setNodeVisible(XQNodeId, bool)
setNodeLocked(XQNodeId, bool)
removeNode(XQNodeId)
XQProjectTreeQtModel::setProjectTreeModel(XQProjectTreeModel*)
XQProjectTreeQtModel::clearProjectTreeModel()
XQProjectTreeQtModel::indexForNode(XQNodeId) -> QModelIndex
XQProjectTreeQtModel::nodeIdForIndex(QModelIndex) -> optional<XQNodeId>
XQProjectTreeQtModel::DiagnosticStateRole
XQProjectTreeQtModel::DiagnosticMessageRole
XQProjectTreeQtModel::DomainIconNameRole
XQProjectTreeViewWidget::setScene(XQScene*)
XQProjectTreeViewWidget::clearScene()
XQProjectTreeViewWidget::treeView() -> QTreeView*
XQProjectTreeViewWidget::setSelectedNode(XQNodeId)
XQProjectTreeViewWidget::selectedNode() -> optional<XQNodeId>
XQProjectTreeViewWidget::setSelectionChangedCallback(callback(optional<XQNodeId>))
XQProjectTreeViewWidget::setCommandContext(XQProject*, XQCommandStack*)
XQProjectTreeViewWidget::clearCommandContext()
XQProjectTreeViewWidget::renameSelectedNode(string) -> bool
XQProjectTreeViewWidget::setRemoveConfirmationCallback(callback(XQNodeId, vector<XQSourceRelation>) -> bool)
XQProjectTreeViewWidget::removeSelectedNode() -> bool
```

Tree row data:

```text
XQProjectTreeGroupRow: group, label
XQProjectTreeNodeRow: node id, group, name, domain type, visible, locked, stale, stale reason
```

Forbidden ownership:

```text
XQDataNode copies
payload copies
file parser state
Qt model item ownership or copied scene graph
```

Dependency boundary:

```text
No Qt symbols are required in core, project, workflow, domain, or IO public APIs.
The Qt item model is restricted to the workbench layer and uses `XQProjectTreeModel` as its non-owning data source.
```

## Step Plan

- [x] Define a tree model backed by scene group and node ids.
- [x] Expose node name, domain type, visibility, lock state, and stale marker.
- [x] Track current node selection as `XQNodeId`.
- [x] Add actions for show/hide, lock/unlock, and remove.
- [x] Add Qt `QAbstractItemModel` adapter now that the controlled Qt6 UI layer exists.
- [x] Add concrete `QTreeView` widget composition around the scene-backed Qt model adapter.
- [x] Add selected-node rename command integration through `XQCommandStack`.
- [x] Add tests for group ordering, node row projection, selection, visibility, lock, and remove.
- [x] Add Qt adapter tests for group/node projection, node-id lookup, and visibility/lock check-state writes through the scene-backed model.
- [x] Add Qt widget tests for QTreeView composition, node-id selection propagation, and command-routed rename.
- [x] Add stale-row diagnostic tooltip and role markers without copying scene state.
- [x] Add stable domain icon names and Qt decoration icons for node name rows.

## Test Plan

Test target:

xq_workbench_tests
xq_project_tree_model_tests
xq_project_tree_qt_model_tests
xq_project_tree_view_widget_tests

Test file:

tests/workbench/XQProjectTreeModelTest.cpp
tests/workbench/XQProjectTreeQtModelTest.cpp
tests/workbench/XQProjectTreeViewWidgetTest.cpp

Core scenarios:

XQProjectTreeModelReturnsFixedGroupOrder
XQProjectTreeModelProjectsSceneNodesWithoutOwningThem
XQProjectTreeModelTracksSelectionByNodeId
XQProjectTreeModelUpdatesVisibilityAndLockOnSceneNode
XQProjectTreeModelRemovesNodeThroughScene
XQProjectTreeQtModelProjectsGroupsAndNodesForQtViews
XQProjectTreeQtModelWritesVisibilityAndLockThroughSceneBackedModel
XQProjectTreeQtModelFindsIndexByNodeId
XQProjectTreeQtModelProvidesDiagnosticMarkerForStaleNodes
XQProjectTreeQtModelExposesStableDomainIconNames
XQProjectTreeViewWidgetComposesTreeViewWithSceneBackedModel
XQProjectTreeViewWidgetSelectionModelSelectionEmitsNodeId
XQProjectTreeViewWidgetRenamesSelectedNodeThroughCommandStack
XQProjectTreeViewWidgetRemoveSelectedNodeRequiresConfirmationWithAffectedRelations
XQProjectTreeViewWidgetNameColumnProvidesDomainDecorationIcons

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_workbench_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQProjectTreeModel --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_project_tree_qt_model_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQProjectTreeQtModel --output-on-failure
cmake --build <xq-rebuild-workspace>/build --target xq_project_tree_view_widget_tests
ctest --test-dir <xq-rebuild-workspace>/build -R XQProjectTreeViewWidget --output-on-failure
```

Expected result:

all project tree model tests pass without requiring Qt6
all Qt adapter tests pass while keeping project data in XQScene/XQProjectTreeModel
all Qt widget tests pass while emitting only XQ-owned node ids for selection
selected-node rename uses XQCommandStack and can be undone
selected-node remove is confirmation-gated with affected source relations and remains undoable
stale rows expose diagnostic tooltip and role data without leaving XQScene as source of truth
node name rows expose domain icon names and GUI-only decoration icons in the workbench layer

## Acceptance

- Loading `<acceptance-project>` shows all project data under expected groups.
- Selecting a tree row drives viewer and tool context through node ids.
- Removing a node uses `XQScene` relation checks.
- The initial contract proves the project tree is backed by `XQScene`, not a copied tree.
- The Qt adapter exposes the same tree to Qt views without adding a second owner for nodes or payloads.
- The concrete Qt widget hosts the tree through `QTreeView` and propagates selection as `XQNodeId`.
- Rename requests from the concrete tree widget execute `RenameNodeCommand` through `XQCommandStack`.
- Remove requests from the concrete tree widget execute `RemoveNodeCommand` through `XQCommandStack` after relation-aware confirmation.
- Stale nodes expose diagnostic marker role data and a stale tooltip in the Qt tree.
- Domain nodes expose stable domain icon names and GUI-only name-column decoration icons.

## XQ-main.zip Evidence

Evidence source root: `<xq-source-extract>`

Files studied:

```text
Code/Source/xq4gui/Plugins/org.xq.core.datamanager/src/internal/xq_DataExplorerView.h
Code/Source/xq4gui/Plugins/org.xq.core.datamanager/src/internal/xq_DataExplorerView.cxx
Code/Source/xq4gui/Plugins/org.xq.core.datamanager/plugin.xml
Code/Source/xq4gui/Plugins/org.xq.data.projectnodes/src/internal/xq_DataNodeInit.cxx
```

Behavior kept:

```text
Project data is exposed to Qt as a tree model.
Visibility is represented as a Qt check-state and writes back to the underlying project node state.
Rows expose user-facing labels, node type/status columns, stale diagnostics, and domain decorations for QTreeView composition.
QTreeView selection-model changes are treated as project-node selection events.
The old rename action intent is preserved as an undoable XQ command, not as direct node mutation.
```

Behavior rejected:

```text
QmitkDataStorageTreeModel, MITK DataStorage ownership, QmitkAbstractView, BlueBerry plugin.xml registration, context-menu extension points, rendering-manager updates, copied MITK DataNode pointers, and plugin activator/view ownership.
```

Rewrite owner:

```text
src/workbench/XQProjectTreeQtModel.h
src/workbench/XQProjectTreeQtModel.cpp
src/workbench/XQProjectTreeViewWidget.h
src/workbench/XQProjectTreeViewWidget.cpp
tests/workbench/XQProjectTreeQtModelTest.cpp
tests/workbench/XQProjectTreeViewWidgetTest.cpp
```

Verification:

```text
XQProjectTreeQtModelProjectsGroupsAndNodesForQtViews
XQProjectTreeQtModelWritesVisibilityAndLockThroughSceneBackedModel
XQProjectTreeQtModelFindsIndexByNodeId
XQProjectTreeQtModelProvidesDiagnosticMarkerForStaleNodes
XQProjectTreeQtModelExposesStableDomainIconNames
XQProjectTreeViewWidgetComposesTreeViewWithSceneBackedModel
XQProjectTreeViewWidgetSelectionModelSelectionEmitsNodeId
XQProjectTreeViewWidgetRenamesSelectedNodeThroughCommandStack
XQProjectTreeViewWidgetRemoveSelectedNodeRequiresConfirmationWithAffectedRelations
XQProjectTreeViewWidgetNameColumnProvidesDomainDecorationIcons
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

## Failure Repair

If the tree stores nodes independently from `XQScene`, remove that ownership and rebuild it as a scene-backed model.
