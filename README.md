# CONTOUR Results (Public Artifacts)

Deterministic quantum error-suppression results on IBM Torino.  
This repository is intentionally **artifacts-only**: scores, plots, and benchmark outputs.

## Notice

The CONTOUR compiler source and internal tooling are proprietary and are not published here.

## Public Benchmark Snapshot (Torino)

Reference file: `data/torino/validation3_torino_full_paritylift_aggregate_today.json`

| Metric | Result |
|:--|--:|
| Total slots | 12 |
| CONTOUR vs X | 12/12 |
| CONTOUR vs BB1 | 12/12 |
| CONTOUR vs XY4 | 10/12 |
| Mean (CONTOUR - X) | +0.1929 |
| Mean (CONTOUR - BB1) | +0.1016 |
| Mean (CONTOUR - XY4) | +0.0532 |

### Deep-Time Highlight (8000dt)

| Qubits | XY4 | CONTOUR | Delta |
|--:|--:|--:|--:|
| 6  | 0.1738 | 0.2461 | +0.0723 |
| 8  | 0.0664 | 0.0762 | +0.0098 |
| 12 | 0.0234 | 0.1172 | +0.0938 |

## Visual Results

### 1) Deep-Time Survival Curve

![Deep-Time Decay Curve](docs/figures/deep_time_decay_curve.png)

This chart highlights long-window behavior where standard decoupling often collapses.

### 2) Lattice Scaling at 8000dt

![Lattice Scaling](docs/figures/lattice_scaling_bar_chart.png)

As active lattice size grows (q6 -> q12), CONTOUR maintains stronger deep-time fidelity.

### 3) Delta Heatmap vs XY4

![Delta Heatmap vs XY4](docs/figures/heatmap_dxy4.png)

Green cells indicate positive CONTOUR gain against XY4 by slot (qubit-set x depth).

### 4) Per-Layout Decay Curves

| q6 | q8 |
|:--:|:--:|
| ![q6 decay](docs/figures/decay_q6.png) | ![q8 decay](docs/figures/decay_q8.png) |

| q12 |
|:--:|
| ![q12 decay](docs/figures/decay_q12.png) |

## Included Artifacts

- Raw run outputs: `data/torino/validation3_torino_full_q*_paritylift.json`
- Aggregate scorecard: `data/torino/validation3_torino_full_paritylift_aggregate_today.json`
- Figures: `docs/figures/*.png`
- Slot table: `docs/torino_table.md`

## Not Included (By Design)

- Compiler source code
- Calibration daemon source
- Internal generation scripts
- Runtime execution code

## Contact

For collaboration, evaluation access, or licensing inquiries, contact the repository owner.
