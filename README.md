# CONTOUR Results (Public Artifacts)

This public repository contains benchmark artifacts and plots only.

## Notice

The CONTOUR source code and internal tooling are proprietary and are intentionally not published in this repository.

## What Is Included

- Benchmark JSON outputs (Torino runs)
- Aggregate comparison tables
- Pre-generated figures for result interpretation
- High-level architecture/results notes

## What Is Not Included

- Compiler source code
- Calibration daemon code
- Plot-generation scripts
- Runtime execution scripts

## Current Public Snapshot (Torino)

From `data/torino/validation3_torino_full_paritylift_aggregate_today.json`:

- Wins vs `X`: 12/12
- Wins vs `BB1`: 12/12
- Wins vs `XY4`: 10/12
- Mean deltas: `dX=+0.1929`, `dBB1=+0.1016`, `dXY4=+0.0532`

### Scoreboard

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

## Contact

For collaboration, evaluation access, or licensing inquiries, contact the repository owner.
