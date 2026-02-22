# Architecture

## Control Flow

1. Probe phase anchors with Ramsey-style map circuits.
2. Fit per-qubit phase series from counts.
3. For each arm (`BASE`, `X`, `XY4`, `BB1`, `CONTOUR`), build protected memory circuits.
4. Execute stress circuits and score all-zero fidelity.

## Hardware-Aware Runtime Layer

- `GRID_DT` is derived from backend timing constraints.
- Physical layout is discovered through transpiler/preset PM.
- Coupling map is projected into local qubit indices.
- Graph coloring is computed from local edges, then lifted in deep regime to parity-preserving Z4 quadrants.

## CONTOUR Actuator

- Pulse count is selected from drift action integral.
- Deep regime uses parity-preserving Z4 phase families.
- Pulse-axis phase includes bounded drift pre-distortion.
- Optional boundary closure activates only when stagger is active.

## Why Deterministic

No RL or optimal-control solver is required at runtime.
The compiler computes schedules and phases analytically from measured anchors.
