# Core Data Semantics

## Purpose

Freeze the semantics Flash must not guess when implementing core, reader, domain, and visualization tasks.

## Coordinate Systems

- Image index coordinates are integer voxel indices in stored image axis order.
- Physical coordinates are continuous coordinates derived from origin, spacing, and direction.
- World coordinates are the XQ scene coordinates used by viewers and domain relations.
- LPS/RAS convention is `OPEN-DECISION`; readers must not guess until approved.
- Image payloads must store origin, spacing, direction, scalar type, component count, and extent.

## Units

- Length, pressure, flow, time, and derived units are `OPEN-DECISION` until approved by Codex A.
- Readers must preserve declared units when present and emit diagnostics when units are missing or ambiguous.

## Domain Relations

- Ownership relation: node belongs to exactly one `XQScene` group.
- Source relation: node was loaded or derived from another node.
- Derived relation: algorithmic output depends on one or more source nodes and may become stale.
- Stale propagation flows from changed source nodes to derived nodes.

## Path And Contour Semantics

- Path points have an explicit coordinate space.
- Contour planes must reference a path frame or image/world frame.
- Contour-to-path frame behavior is blocked until frame convention is approved.

## Transform Semantics

- Image, model, and mesh transforms must be explicit.
- No reader may silently assume identity transforms when file metadata proves otherwise.

## Identity And Provenance

- Node IDs must be stable across save/reopen unless a migration policy says otherwise.
- Payload versions and provenance must be saved for reproducibility.
- Copy/move/share semantics require explicit ownership and ID rules.

## Threading And Errors

- Core objects are not assumed thread-safe unless a contract says so.
- Public APIs return explicit result/diagnostic information instead of throwing through UI code paths.
- Diagnostics must avoid private patient/institution fields.

## External Objects

External native objects may be held only in private implementation or backend adapter internals. Public XQ APIs must expose XQ-owned value, handle, or payload types.
