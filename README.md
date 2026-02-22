# CONTOUR: Enterprise Quantum Error Suppression

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

---

## Included Public Artifacts

- Raw run outputs: `data/torino/validation3_torino_full_q*_paritylift.json`
- Aggregate scorecard: `data/torino/validation3_torino_full_paritylift_aggregate_today.json`
- Figures: `docs/figures/*.png`
- Slot table: `docs/torino_table.md`

## Not Included (Proprietary)

- Compiler source code
- Calibration daemon code
- Internal generation and runtime scripts

---

## Commercial Access

For benchmark verification, partnership inquiries, or evaluation access, contact the repository owner.
