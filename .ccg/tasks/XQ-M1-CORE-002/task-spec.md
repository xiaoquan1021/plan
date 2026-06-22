# XQ-M1-CORE-002 Implementation Task

## Task ID
XQ-M1-CORE-002

## Title
XQProject and XQScene management structure

## Context
- Base commit: bf44820926f6b164e9c8963871b200b6254c0260
- Rollback point: bf44820926f6b164e9c8963871b200b6254c0260
- Repository: C:/Users/OCEAN/Desktop/XIAOQUAN/XQrebuild
- Allowed paths: src/core/**, tests/core/**
- Epic: XQ-M1-CORE-DATA
- Task Pack: docs/contracts/task-packs/XQ-M1-CORE-002.issued.yaml
- Prerequisite: XQ-M1-CORE-001 completed (NodeId and XQDataNode identity)

## Required Outcomes (from Core Data Semantics)
1. XQProject: owns project lifecycle and exactly one XQScene
2. XQScene: owns scene nodes, supports insert and find-by-id
3. Duplicate NodeId handling with deterministic diagnostics
4. No external library public types (no MITK, VTK, ITK, etc. in public API)
5. L0 synthetic tests pass

## Implementation Requirements

### 1. Create src/core/XQProject.h
- Class representing project lifecycle
- Owns exactly one XQScene instance (unique_ptr or similar)
- Constructor, destructor
- Method to access the scene: `XQScene& scene() noexcept` or similar
- No external library types in public API

### 2. Create src/core/XQProject.cpp
- Implementation of XQProject methods
- XQScene construction and ownership management

### 3. Create src/core/XQScene.h
- Class representing scene node container
- Methods:
  - `bool insertNode(std::unique_ptr<XQDataNode> node, std::string& diagnostic)` or similar
  - `XQDataNode* findById(const NodeId& id) const noexcept` or similar
  - Duplicate NodeId detection with diagnostic output
- Internal storage (std::map, std::unordered_map, or vector with search)
- No external library types in public API

### 4. Create src/core/XQScene.cpp
- Implementation of XQScene methods
- Node ownership management (store unique_ptr or shared_ptr)
- Insert logic with duplicate ID check
- Find-by-id implementation

### 5. Create tests/core/test_scene_management.cpp
- L0 synthetic tests (no external data files)
- Test XQProject construction and scene access
- Test XQScene insert: valid node insertion
- Test XQScene find-by-id: returns correct node
- Test duplicate NodeId handling: returns diagnostic, no crash
- Test basic lifecycle (insert multiple nodes, find each)

### 6. Update CMakeLists.txt
- Add XQProject.cpp and XQScene.cpp to xq_core library sources
- Add test_scene_management executable
- Link test_scene_management to xq_core

## Forbidden Actions
- Do NOT modify PLAN_WORKSPACE
- Do NOT add dependencies (MITK, VTK, ITK, Qt, etc.)
- Do NOT modify files outside src/core/ and tests/core/
- Do NOT implement removal or relation cleanup (out of scope for this task)

## Stop Conditions
- If you need files outside allowed_paths → STOP
- If you need external dependencies → STOP
- If you need architecture decisions (coordinate systems, transform representation, relation semantics) → STOP

## Success Criteria
- All 6 files created/updated in correct locations
- Code compiles
- Tests define and check XQProject/XQScene behavior
- Git commit created with changes
- No forbidden actions violated

## Commands to Execute
Work in C:/Users/OCEAN/Desktop/XIAOQUAN/XQrebuild starting from base commit bf44820926f6b164e9c8963871b200b6254c0260.
