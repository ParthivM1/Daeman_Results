# CONTOUR Quantum Compiler

CONTOUR is a deterministic, low-latency quantum error-suppression compiler for superconducting qubits. It targets deep-time memory windows where default DD templates degrade, and it uses runtime hardware metadata (timing constraints + coupling map) instead of fixed chip assumptions.

## Executive Claim

On IBM Torino (today's calibration), CONTOUR achieved:
- 12/12 wins vs `X`
- 12/12 wins vs `BB1`
- 10/12 wins vs `XY4`
- Mean deltas: `dX=+0.1929`, `dBB1=+0.1016`, `dXY4=+0.0532`

Reference aggregate:
- `data/torino/validation3_torino_full_paritylift_aggregate_today.json`

## Visual Proof

### Deep-Time Survival (Q12)
![Deep-Time Decay](docs/figures/deep_time_decay_curve.png)

### Lattice Scaling at 8000dt
![Lattice Scaling](docs/figures/lattice_scaling_bar_chart.png)

## Core Innovations

1. Symmetric Surfer  
   Maintains echo-compatible timing while applying phase pre-distortion from anchor-measured drift.
2. Topological Z4 Shield  
   Uses a parity-preserving lift from bipartite coloring into four quadrants for robust spatial phase separation at deep time.
3. Thermodynamic Action Selector  
   Chooses pulse count from measured drift action to avoid unnecessary gate tax when curvature is low.

## Repository Layout

- `src/validation3.py`: main benchmark and compiler logic
- `src/validation3_daemon.py`: calibration/selection wrapper
- `data/torino/`: benchmark outputs and aggregate report
- `docs/architecture.md`: architecture and physics summary
- `docs/results.md`: benchmark interpretation
- `docs/torino_table.md`: slot-by-slot comparison table
- `scripts/generate_contour_plots.py`: launch visuals from aggregate JSON
- `scripts/plot_torino_results.py`: per-q decay + heatmap generator
- `scripts/summarize_aggregate.py`: markdown table generator

## Quick Start

```bash
python -m pip install -r requirements.txt
python scripts/generate_contour_plots.py \
  --aggregate data/torino/validation3_torino_full_paritylift_aggregate_today.json \
  --outdir docs/figures
```

Generate supplemental figures:

```bash
python scripts/plot_torino_results.py \
  --aggregate data/torino/validation3_torino_full_paritylift_aggregate_today.json \
  --outdir docs/figures
```

## Runtime Benchmark Command

```bash
python -u src/validation3.py \
  --mode runtime \
  --backend ibm_torino \
  --api-token <YOUR_TOKEN> \
  --n-qubits 12 \
  --times 3200,4912,6400,8000 \
  --anchors 800,1600,2400,3200,4000,4800,5600,6400 \
  --arms BASE,X,XY4,BB1,CONTOUR \
  --shots-map 256 \
  --shots-stress 512 \
  --max-seconds 1800 \
  --output data/torino/validation3_torino_full_q12_runtime.json
```

## Notes

- Results vary by daily calibration, queue pressure, and shot budget.
- Claims in this repo are tied to dated JSON artifacts checked into `data/`.
