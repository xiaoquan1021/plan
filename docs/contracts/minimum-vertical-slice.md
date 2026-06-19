# Minimum Vertical Slice

## XQ-M2A Synthetic Slice

Uses L0 synthetic data to prove project creation, scene nodes, ownership, relations, minimal reader interface, save, close, reopen, and diagnostics.

## XQ-M2B Fixture-Backed Slice

Uses L1 de-identified fixture data with a project manifest, image, path, contour group, and `expected-scene.json`.

## Dependency Rules

```text
XQ-M1 -> XQ-M2A
XQ-M2A -> limited UI/Core follow-up
XQ-M2B -> real-format image/path/contour expansion
L2 -> XQ-M9 only
```

Missing L1 fixture blocks XQ-M2B only. Missing L2 real project blocks XQ-M9 only.
