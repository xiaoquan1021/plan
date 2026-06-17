# SJB Simulation Reader

## Purpose

Define native loading of `.sjb` simulation job files and related solver-preparation files into `XQSimulationCase`.

## Owns

Future source files:

```text
src/io/project/SJBSimulationReader.h
src/io/project/SJBSimulationReader.cpp
src/io/project/SJBSimulationWriter.h
src/io/project/SJBSimulationWriter.cpp
tests/io/project/SJBSimulationReaderTest.cpp
```

## Inputs

- `XQSimulationCase` payload.
- Mesh reader.
- tinyxml2 dependency role.

## Outputs

- One `XQSimulationCase` node per simulation job.

## Rules

- `.sjb` is a first-version native XQ simulation setup file.
- Related files in the simulation case directory are loaded as source references and parsed when their data is part of XQ's simulation-prep model.
- Simulation cases bind to mesh nodes through scene relations.
- The reader does not call external solvers.

## Related Files

Known files in `<acceptance-project>/Simulations/0090_0001`:

```text
bct.vtp
rcrt.dat
inflow.flow
solver.inp
*.svpre
```

## Read Contract

Extract:

```text
job name
mesh reference
face ids for boundary conditions
inflow file references and waveform values
RCR/resistance parameters
wall properties
fluid/material settings
time step and output controls
solver-prep source file references
```

## Implementation Contract

Public API surface:

```text
SJBSimulationReader
SJBSimulationWriter
SJBSimulationReader::read(sjbFile, simulationDirectory)
SJBSimulationWriter::write(simulationCaseNode, sjbFile)
```

Output ownership:

```text
one XQDataNode
one XQSimulationCase payload
boundary conditions from .sjb and related files
source file references preserved
```

Dependency boundary:

```text
tinyxml2 reads .sjb
plain text parsers read inflow.flow and rcrt.dat
no solver process is launched by this reader
```

## Step Plan

- [x] Parse `.sjb` XML with tinyxml2.
- [x] Read inflow waveform data and RCR values into boundary condition records.
- [x] Preserve solver input, svpre, inflow, RCR, and related source file references.
- [x] Resolve mesh relation after mesh nodes are loaded.
- [x] Add tests using `<acceptance-project>/Simulations/0090_0001.sjb`.

## Test Plan

Expected command:

```text
ctest --test-dir <xq-rebuild-workspace>/build -R SJBSimulationReader --output-on-failure
```

Required fixture:

<acceptance-project>/Simulations/0090_0001.sjb
<acceptance-project>/Simulations/0090_0001/inflow.flow
<acceptance-project>/Simulations/0090_0001/rcrt.dat

Required cases:

read .sjb simulation metadata
read inflow waveform values
read RCR or resistance values
preserve solver input and svpre source references
reject missing required mesh relation with diagnostic result

## Acceptance

- The loaded simulation case exposes boundary conditions by face id.
- The solver export feature can regenerate output from XQ data.
- Source solver files remain traceable from the simulation case.

## Failure Repair

If simulation loading becomes a raw file browser with no typed case object, repair this reader and `XQSimulationCase`.
