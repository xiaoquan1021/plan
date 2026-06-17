# Command and Undo

## Purpose

Define a command model for user mutations and undo/redo across the integrated workflow.

This document must create XQ-owned command infrastructure only. It must not bind to Qt actions, VTK actors, plugin action handlers, or old framework command stacks.

## Owns

Future source files:

```text
src/workflow/XQCommand.h
src/workflow/XQCommandStack.h
src/workflow/XQCommandStack.cpp
src/workflow/commands/XQSceneCommands.h
src/workflow/commands/XQSceneCommands.cpp
tests/workflow/XQCommandStackTest.cpp
```

## Inputs

- `XQScene`.
- Workflow state machine.
- Tool panels.

## Outputs

- A command stack for node creation, deletion, rename, metadata changes, geometry edits, and workflow-generated outputs.

## Rules

- User-facing mutations go through commands.
- Algorithms may return new payloads, but scene mutation is committed by commands.
- Undo operates on XQ-owned scene and payload data, not VTK actors or Qt widgets.
- Commands are integrated application infrastructure, not plugin actions.

## First Commands

```text
AddNodeCommand
AddNodeWithSourceRelationCommand
RemoveNodeCommand
RenameNodeCommand
SetNodeVisibilityCommand
ReplacePayloadCommand
```

Deferred scope is tracked in `ledger/deferred-register.md` and must not be used as completion record.

These commands must be implemented in the owning domain-feature document once the related payload editing contract is hardened.

## Implementation Contract

Implementation Contract owns:

```text
src/workflow/XQCommand.h
src/workflow/XQCommandStack.h
src/workflow/XQCommandStack.cpp
src/workflow/commands/XQSceneCommands.h
src/workflow/commands/XQSceneCommands.cpp
tests/workflow/XQCommandStackTest.cpp
```

Public classes:

```text
xq::XQCommand
xq::XQCommandStack
xq::AddNodeCommand
xq::AddNodeWithSourceRelationCommand
xq::RemoveNodeCommand
xq::RenameNodeCommand
xq::SetNodeVisibilityCommand
xq::ReplacePayloadCommand
```

`XQCommand` minimum interface:

```text
description() const -> std::string
execute(XQProject&)
undo(XQProject&)
```

`XQCommandStack` minimum interface:

```text
execute(XQProject&, std::unique_ptr<XQCommand>)
undo(XQProject&) -> bool
redo(XQProject&) -> bool
canUndo() const -> bool
canRedo() const -> bool
undoCount() const -> std::size_t
redoCount() const -> std::size_t
clear()
```

Command stack semantics:

```text
execute runs the command, pushes it to undo history, clears redo history, and marks project modified
undo returns false when no command is available
redo returns false when no command is available
undo and redo mark project modified only when an operation is actually performed
commands mutate XQProject/XQScene/XQDataNode only
commands do not own UI refresh or rendering
```

Scene command semantics:

```text
AddNodeCommand stores the group and XQDataNode value, inserts the node on execute, removes it on undo
AddNodeWithSourceRelationCommand stores the group, XQDataNode value, source node id, and relation kind; execute inserts the node and creates the source relation; undo removes the created source relation before removing the created node
RemoveNodeCommand stores the removed XQDataNode value and affected source-relation state on execute, removes the scene node, and reinserts the same node plus restores pre-remove relation stale flags on undo
RenameNodeCommand stores the old name on execute and restores it on undo
SetNodeVisibilityCommand stores the old visibility on execute and restores it on undo
ReplacePayloadCommand stores the old shared payload on execute, replaces the payload, and restores it on undo
ReplacePayloadCommand rejects null payloads and domain mismatches
```

Current relation restoration:

```text
RemoveNodeCommand undo restores source-relation stale flags and stale reasons to their pre-remove state for relations touching the removed node.
Relation-aware add-node undo now removes relations created by AddNodeWithSourceRelationCommand.
XQScene::removeNode still keeps affected relations inspectable as stale records while the node is absent.
```

Forbidden behavior:

```text
depend on Qt QAction or widget state
depend on VTK actor state
call MITK, BlueBerry, CTK, or plugin APIs
store command state in UI controls
silently edit payloads outside command execution
```

## Step Plan

- [x] Define base command interface with `execute` and `undo`.
- [x] Define command stack with undo and redo lists.
- [x] Implement node add, remove, rename, visibility, and payload replacement commands.
- [x] Implement relation-aware generated-node add command for path and contour creation.
- [x] Add tests for command execution, undo, redo, redo clearing, and modified project state.
- [x] Add tests that command execution reaches `XQProject / XQScene / XQDataNode / XQ-owned payloads`.

## Test Plan

Test target:

xq_command_stack_tests

Test file:

tests/workflow/XQCommandStackTest.cpp

Core scenarios:

XQCommandStackExecutesAddNodeAndUndoRedoThroughXQScene
XQCommandStackClearsRedoAfterNewCommand
XQSceneCommandsRenameAndVisibilityUndoRedo
XQSceneCommandsRemoveNodeRestoresXQDataNode
XQSceneCommandsRemoveNodeUndoRestoresRelationStaleState
XQSceneCommandsReplacePayloadUndoRedo
XQSceneCommandsRejectPayloadDomainMismatch
Domain tests cover AddNodeWithSourceRelationCommand through path and contour create commands

Expected command:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_command_stack_tests
ctest --test-dir <xq-rebuild-workspace>/build -R "XQCommandStack|XQSceneCommands" --output-on-failure
```

Expected result:

all command stack and scene command tests pass

TDD red check:

```text
cmake --build <xq-rebuild-workspace>/build --target xq_command_stack_tests
```

Observed expected failure before implementation:

Cannot find source file: src/workflow/XQCommandStack.cpp

## Acceptance

- Tool panels can mutate scene data without direct ownership.
- Undo mutates XQ-owned scene data so project tree and viewer state layers can observe the updated scene.
- Commands mark project modified state.
- Command tests prove mutations enter `XQProject / XQScene / XQDataNode / XQ-owned payloads`, not UI shells.

## Failure Repair

If a tool edits payload data without command routing, add a specific command before expanding that tool.
