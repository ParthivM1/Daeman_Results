#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_aggregate(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "aggregate" not in data:
        raise ValueError(f"aggregate key missing in {path}")
    return data["aggregate"]


def get_slots_by_q_t(slots: list[dict]) -> dict[tuple[int, int], dict]:
    out: dict[tuple[int, int], dict] = {}
    for row in slots:
        out[(int(row["q"]), int(row["t"]))] = row
    return out


def plot_deep_time_decay(slots: list[dict], outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    q_target = max(int(s["q"]) for s in slots)
    rows = sorted((s for s in slots if int(s["q"]) == q_target), key=lambda x: int(x["t"]))
    times = [int(r["t"]) for r in rows]

    arms = ["X", "XY4", "BB1", "CONTOUR"]
    colors = {"X": "#999999", "XY4": "#d62728", "BB1": "#ff7f0e", "CONTOUR": "#1f77b4"}

    plt.figure(figsize=(8.2, 4.8))
    for arm in arms:
        ys = [float(r[arm]) for r in rows]
        plt.plot(times, ys, marker="o", linewidth=2.2, markersize=6, label=arm, color=colors[arm])

    plt.title(f"Deep-Time Decay Curve (q={q_target})")
    plt.xlabel("Memory Window (dt)")
    plt.ylabel("All-Zero Fidelity")
    plt.ylim(0.0, 1.0)
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()

    out_path = outdir / "deep_time_decay_curve.png"
    plt.savefig(out_path, dpi=180)
    plt.close()
    return out_path


def plot_lattice_scaling(slots: list[dict], outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    by = get_slots_by_q_t(slots)
    qs = sorted({int(s["q"]) for s in slots})
    depth = 8000 if any(int(s["t"]) == 8000 for s in slots) else max(int(s["t"]) for s in slots)

    baselines = ["X", "XY4", "BB1"]
    contour_vals = np.array([float(by[(q, depth)]["CONTOUR"]) for q in qs], dtype=float)
    x = np.arange(len(qs), dtype=float)
    width = 0.22

    plt.figure(figsize=(8.4, 4.8))
    plt.bar(x - width, [float(by[(q, depth)]["X"]) for q in qs], width=width, color="#999999", label="X")
    plt.bar(x, [float(by[(q, depth)]["XY4"]) for q in qs], width=width, color="#d62728", label="XY4")
    plt.bar(x + width, contour_vals, width=width, color="#1f77b4", label="CONTOUR")

    plt.title(f"Lattice Scaling at {depth}dt")
    plt.xlabel("Active Qubits")
    plt.ylabel("All-Zero Fidelity")
    plt.xticks(x, [str(q) for q in qs])
    plt.ylim(0.0, max(0.2, float(np.max(contour_vals) * 1.25)))
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()

    out_path = outdir / "lattice_scaling_bar_chart.png"
    plt.savefig(out_path, dpi=180)
    plt.close()
    return out_path


def write_plot_summary(agg: dict, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / "plot_summary.md"
    lines = [
        "# Plot Summary",
        "",
        f"- Slots: {agg['n_slots']}",
        f"- Wins vs X: {agg['wins_vs_X']}/{agg['n_slots']}",
        f"- Wins vs XY4: {agg['wins_vs_XY4']}/{agg['n_slots']}",
        f"- Wins vs BB1: {agg['wins_vs_BB1']}/{agg['n_slots']}",
        f"- Mean dX: {agg['mean_dX']:+.4f}",
        f"- Mean dXY4: {agg['mean_dXY4']:+.4f}",
        f"- Mean dBB1: {agg['mean_dBB1']:+.4f}",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate launch visuals for CONTOUR benchmark data.")
    ap.add_argument(
        "--aggregate",
        default="data/torino/validation3_torino_full_paritylift_aggregate_today.json",
        help="Path to aggregate benchmark JSON.",
    )
    ap.add_argument("--outdir", default="docs/figures", help="Output directory for figures.")
    args = ap.parse_args()

    agg = load_aggregate(Path(args.aggregate))
    slots = agg["slots"]
    outdir = Path(args.outdir)

    p1 = plot_deep_time_decay(slots, outdir)
    p2 = plot_lattice_scaling(slots, outdir)
    p3 = write_plot_summary(agg, outdir)

    print(f"wrote: {p1}")
    print(f"wrote: {p2}")
    print(f"wrote: {p3}")


if __name__ == "__main__":
    main()
