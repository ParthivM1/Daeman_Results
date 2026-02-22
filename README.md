# CONTOUR: Enterprise Quantum Error Suppression

![Torino](https://img.shields.io/badge/Backend-IBM%20Torino-0a66c2)
![vs X](https://img.shields.io/badge/CONTOUR%20vs%20X-12%2F12-success)
![vs BB1](https://img.shields.io/badge/CONTOUR%20vs%20BB1-12%2F12-success)
![vs XY4](https://img.shields.io/badge/CONTOUR%20vs%20XY4-10%2F12-success)
![Mean dXY4](https://img.shields.io/badge/Mean%20dXY4-%2B0.0532-success)

**CONTOUR** (Continuous Topological Phase Surfer) is a proprietary, deterministic quantum compiler for suppressing deep-time decoherence and lattice crosstalk on superconducting processors.

CONTOUR is designed for low-latency operation and benchmarked against standard dynamic decoupling baselines (`X`, `XY4`, `BB1`) on IBM heavy-hex hardware.

> This repository is the **public benchmark showcase** only.  
> The core CONTOUR transpilation engine and calibration daemon are proprietary commercial IP.

---

## The Technology: Why CONTOUR Wins

Standard decoupling often trades off between symmetric timing (amplitude robustness) and asymmetric timing (phase-drift tracking). CONTOUR combines both while preserving lattice stability.

CONTOUR is built on three core pillars:

1. **Symmetric Phase Surfer**  
   Maintains Hahn-echo-compatible time-reversal structure to suppress commutator buildup, while applying bounded phase pre-distortion to track macroscopic drift.

2. **Parity-Preserving $Z_4$ Topological Shield**  
   Lifts spatial scheduling from bipartite $Z_2$ structure into a parity-safe $Z_4$ phase family (`X, Y, -X, -Y`) to reduce higher-order spectator crosstalk while preserving edge orthogonality.

3. **Thermodynamic Action Integral**  
   Selects pulse volume from measured non-linear drift action, avoiding unnecessary microwave tax when lower pulse counts are sufficient.

---

## Benchmark Results (IBM Torino)

Evaluation matrix:
- Lattice sizes: Q6, Q8, Q12
- Memory windows: 3200dt, 4912dt, 6400dt, 8000dt
- Baselines: `X`, `XY4`, `BB1`

Primary artifact:
- `data/torino/validation3_torino_full_paritylift_aggregate_today.json`

### Latest Deep Validation (Today)

Deep-only confirmation rerun (`6400dt`, `8000dt`) across Q6/Q8/Q12:
- Artifact: `data/torino/validation3_torino_deep_aggregate_today2.json`
- **vs X:** 6 / 6 wins (`+0.1768` mean absolute gain)
- **vs BB1:** 6 / 6 wins (`+0.1312` mean absolute gain)
- **vs XY4:** 6 / 6 wins (`+0.0843` mean absolute gain)

![Latest Deep Check dXY4](docs/figures/deep_check_today2_dxy4.png)

Detailed deep slot table:
- `docs/deep_check_today2.md`

Quick links:
- Slot table: `docs/torino_table.md`
- Deep-time curve: `docs/figures/deep_time_decay_curve.png`
- Scaling chart: `docs/figures/lattice_scaling_bar_chart.png`
- Delta heatmap: `docs/figures/heatmap_dxy4.png`

### Deep-Time Rescue at 8000dt

| Lattice Density | XY4 Baseline | CONTOUR | Relative Gain |
|:--|--:|--:|--:|
| Sparse (6-Qubit) | 17.4% | **24.6%** | **1.4x** |
| Medium (8-Qubit) | 6.6% | **7.6%** | **1.1x** |
| Dense (12-Qubit) | 2.3% | **11.7%** | **5.0x** |

In the dense Q12 deep-time regime, CONTOUR shows the largest uplift (about **5x** relative gain versus XY4).

### Aggregate Sweep Performance (12 Slots)

- **vs X:** 12 / 12 wins (`+0.1929` mean absolute gain)
- **vs BB1:** 12 / 12 wins (`+0.1016` mean absolute gain)
- **vs XY4:** 10 / 12 wins (`+0.0532` mean absolute gain)

### Q12 Deep-Window Trace (CONTOUR vs XY4)

| Window (dt) | XY4 | CONTOUR | Delta |
|--:|--:|--:|--:|
| 3200 | 0.2852 | 0.2480 | -0.0371 |
| 4912 | 0.1113 | 0.1641 | +0.0527 |
| 6400 | 0.0684 | 0.1445 | +0.0762 |
| 8000 | 0.0234 | 0.1172 | +0.0938 |

---

## Visualizing the Results

### 1) Deep-Time Survival (Q12)
![Deep-Time Decay Curve](docs/figures/deep_time_decay_curve.png)

CONTOUR maintains stronger fidelity at long windows where baseline methods degrade.

### 2) Lattice Scaling at 8000dt
![Lattice Scaling](docs/figures/lattice_scaling_bar_chart.png)

As active lattice density increases, CONTOUR preserves a larger fraction of usable signal in deep-time operation.

### 3) Slot-Wise Delta vs XY4
![Delta Heatmap vs XY4](docs/figures/heatmap_dxy4.png)

Positive cells represent per-slot CONTOUR uplift against XY4.

### 4) Per-Lattice Decay Curves

| q6 | q8 |
|:--:|:--:|
| ![q6 decay](docs/figures/decay_q6.png) | ![q8 decay](docs/figures/decay_q8.png) |

| q12 |
|:--:|
| ![q12 decay](docs/figures/decay_q12.png) |

---

## Included Public Artifacts

- Raw run outputs: `data/torino/validation3_torino_full_q*_paritylift.json`
- Aggregate scorecard: `data/torino/validation3_torino_full_paritylift_aggregate_today.json`
- Deep rerun outputs: `data/torino/validation3_torino_deep_q*_today2.json`
- Deep rerun aggregate: `data/torino/validation3_torino_deep_aggregate_today2.json`
- Figures: `docs/figures/*.png`
- Slot table: `docs/torino_table.md`
- Deep table: `docs/deep_check_today2.md`

## Not Included (Proprietary)

- Compiler source code
- Calibration daemon code
- Internal generation and runtime scripts

---

## Commercial Access

For benchmark verification, partnership inquiries, or evaluation access, contact the repository owner.
