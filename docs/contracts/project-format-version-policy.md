# Project Format Version Policy

## Purpose

Define how XQ native project files evolve.

## Required Manifest Fields

- `schemaVersion`
- `writerVersion`
- `minimumReaderVersion`
- `createdWith`
- `projectId`
- `scene`
- `provenance`

## Rules

- Readers must reject unsupported future major versions with diagnostics.
- Readers may load compatible minor versions when required fields are present.
- Migrations must be explicit and tested.
- Stable node IDs must survive save/reopen unless a migration explicitly remaps them.
