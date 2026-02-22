#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_slots(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    agg = data.get("aggregate", {})
    slots = agg.get("slots", [])
    return slots


def unique_sorted(vals):
    return sorted(set(vals))


def plot_decay(slots, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    qs = unique_sorted([int(s["q"]) for s in slots])
    arms = ["X", "XY4", "BB1", "CONTOUR"]
    for q in qs:
        sub = [s for s in slots if int(s["q"]) == q]
        ts = sorted([int(s["t"]) for s in sub])
        plt.figure(figsize=(7, 4))
        for arm in arms:
            ys = [float(next(x for x in sub if int(x["t"]) == t)[arm]) for t in ts]
            plt.plot(ts, ys, marker="o", label=arm)
        plt.title(f"Fidelity vs Depth (q={q})")
        plt.xlabel("time (dt)")
        plt.ylabel("all-zero fidelity")
        plt.ylim(0.0, 1.0)
        plt.grid(alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / f"decay_q{q}.png", dpi=160)
        plt.close()


def plot_heatmap(slots, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    qs = unique_sorted([int(s["q"]) for s in slots])
    ts = unique_sorted([int(s["t"]) for s in slots])
    mat = np.zeros((len(qs), len(ts)), dtype=float)
    for i, q in enumerate(qs):
        for j, t in enumerate(ts):
            rec = next(s for s in slots if int(s["q"]) == q and int(s["t"]) == t)
            mat[i, j] = float(rec["dXY4"])

    plt.figure(figsize=(8, 3.8))
    im = plt.imshow(mat, cmap="RdYlGn", aspect="auto")
    plt.colorbar(im, label="CONTOUR - XY4")
    plt.xticks(range(len(ts)), ts)
    plt.yticks(range(len(qs)), qs)
    plt.xlabel("time (dt)")
    plt.ylabel("qubit-count test")
    plt.title("Delta Heatmap vs XY4")
    for i in range(len(qs)):
        for j in range(len(ts)):
            plt.text(j, i, f"{mat[i,j]:+.3f}", ha="center", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(outdir / "heatmap_dxy4.png", dpi=160)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregate", required=True)
    ap.add_argument("--outdir", default="docs/figures")
    args = ap.parse_args()

    slots = load_slots(Path(args.aggregate))
    outdir = Path(args.outdir)
    plot_decay(slots, outdir)
    plot_heatmap(slots, outdir)
    print(f"wrote figures to {outdir}")


if __name__ == "__main__":
    main()
