import argparse
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from qiskit_ibm_runtime import QiskitRuntimeService


def parse_int_csv(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def parse_float_csv(raw: str) -> list[float]:
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def parse_str_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass
class Knobs:
    activation_depth: int
    risk_high: float
    risk_low: float
    stagger_dt: int
    seed_transpiler: int

    def tag(self) -> str:
        return (
            f"a{self.activation_depth}_h{self.risk_high:.2f}"
            f"_l{self.risk_low:.2f}_s{self.stagger_dt}_seed{self.seed_transpiler}"
        )


def discover_backends(token: str, requested: list[str]) -> list[str]:
    svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
    available = {b.name: b for b in svc.backends(simulator=False, operational=True)}
    out = []
    for b in requested:
        if b in available:
            out.append(b)
    return out


def run_validation3(
    token: str,
    backend: str,
    n_qubits: int,
    times_csv: str,
    anchors_csv: str,
    shots_map: int,
    shots_stress: int,
    max_seconds: float,
    knobs: Knobs,
    output_path: Path,
) -> tuple[int, str, str]:
    cmd = [
        "python",
        "-u",
        "validation3.py",
        "--mode",
        "runtime",
        "--backend",
        backend,
        "--api-token",
        token,
        "--n-qubits",
        str(n_qubits),
        "--times",
        times_csv,
        "--anchors",
        anchors_csv,
        "--arms",
        "BASE,X,XY4,BB1,CONTOUR",
        "--shots-map",
        str(shots_map),
        "--shots-stress",
        str(shots_stress),
        "--max-seconds",
        str(max_seconds),
        "--activation-depth",
        str(knobs.activation_depth),
        "--risk-high",
        str(knobs.risk_high),
        "--risk-low",
        str(knobs.risk_low),
        "--contour-stagger-dt",
        str(knobs.stagger_dt),
        "--seed-transpiler",
        str(knobs.seed_transpiler),
        "--output",
        str(output_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def extract_rows(report: dict[str, Any]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for rec in report.get("records", []):
        t = int(rec["time_executed_dt"])
        arms = rec["arms"]
        c = float(arms["CONTOUR"]["fidelity"])
        x = float(arms["X"]["fidelity"])
        xy4 = float(arms["XY4"]["fidelity"])
        bb1 = float(arms["BB1"]["fidelity"])
        base = float(arms["BASE"]["fidelity"])
        rows.append(
            {
                "time_dt": float(t),
                "BASE": base,
                "X": x,
                "XY4": xy4,
                "BB1": bb1,
                "CONTOUR": c,
                "dX": c - x,
                "dXY4": c - xy4,
                "dBB1": c - bb1,
            }
        )
    return rows


def calibration_score(rows: list[dict[str, float]]) -> tuple[float, dict[str, float]]:
    if not rows:
        return -1.0e18, {"wins_xy4": 0.0, "mean_dxy4": -1.0e18, "dxy4_3200": -1.0e18}
    wins_xy4 = float(sum(1 for r in rows if float(r["dXY4"]) > 0.0))
    mean_dxy4 = float(np.mean([float(r["dXY4"]) for r in rows]))
    mean_dbb1 = float(np.mean([float(r["dBB1"]) for r in rows]))
    mean_dx = float(np.mean([float(r["dX"]) for r in rows]))
    dxy4_3200 = float(next((float(r["dXY4"]) for r in rows if int(r["time_dt"]) == 3200), mean_dxy4))
    score = float(
        (1000.0 * wins_xy4)
        + (300.0 * dxy4_3200)
        + (120.0 * mean_dxy4)
        + (40.0 * mean_dbb1)
        + (10.0 * mean_dx)
    )
    metrics = {
        "wins_xy4": wins_xy4,
        "mean_dxy4": mean_dxy4,
        "mean_dbb1": mean_dbb1,
        "mean_dx": mean_dx,
        "dxy4_3200": dxy4_3200,
    }
    return score, metrics


def make_grid(
    activation_depths: list[int],
    risk_highs: list[float],
    risk_lows: list[float],
    stagger_options: list[int],
    seed_transpiler: int,
) -> list[Knobs]:
    grid: list[Knobs] = []
    for ad in activation_depths:
        for rh in risk_highs:
            for rl in risk_lows:
                if rh <= rl:
                    continue
                for st in stagger_options:
                    grid.append(
                        Knobs(
                            activation_depth=int(ad),
                            risk_high=float(rh),
                            risk_low=float(rl),
                            stagger_dt=int(st),
                            seed_transpiler=int(seed_transpiler),
                        )
                    )
    return grid


def calibrate_backend(
    token: str,
    backend: str,
    grid: list[Knobs],
    out_dir: Path,
    times_csv: str,
    anchors_csv: str,
    calib_n_qubits: int,
    shots_map: int,
    shots_stress: int,
    max_seconds: float,
) -> tuple[Knobs | None, list[dict[str, Any]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    best_knobs: Knobs | None = None
    best_score = -1.0e18

    for knobs in grid:
        tag = knobs.tag()
        out_file = out_dir / f"{backend}_{tag}.json"
        code, stdout, stderr = run_validation3(
            token=token,
            backend=backend,
            n_qubits=calib_n_qubits,
            times_csv=times_csv,
            anchors_csv=anchors_csv,
            shots_map=shots_map,
            shots_stress=shots_stress,
            max_seconds=max_seconds,
            knobs=knobs,
            output_path=out_file,
        )
        item: dict[str, Any] = {
            "backend": backend,
            "tag": tag,
            "returncode": int(code),
            "output": str(out_file),
        }
        if code == 0 and out_file.exists():
            try:
                report = json.loads(out_file.read_text(encoding="utf-8"))
                rows = extract_rows(report)
                score, metrics = calibration_score(rows)
                item.update(metrics)
                item["score"] = float(score)
                if score > best_score:
                    best_score = float(score)
                    best_knobs = knobs
            except Exception as exc:
                item["parse_error"] = str(exc)
        else:
            item["stdout_tail"] = "\n".join((stdout or "").splitlines()[-15:])
            item["stderr_tail"] = "\n".join((stderr or "").splitlines()[-15:])
        results.append(item)
    return best_knobs, results


def run_full_backend(
    token: str,
    backend: str,
    knobs: Knobs,
    n_qubits_list: list[int],
    times_csv: str,
    anchors_csv: str,
    shots_map: int,
    shots_stress: int,
    max_seconds: float,
    out_dir: Path,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for nq in n_qubits_list:
        out_file = out_dir / f"{backend}_q{nq}_{knobs.tag()}.json"
        code, stdout, stderr = run_validation3(
            token=token,
            backend=backend,
            n_qubits=int(nq),
            times_csv=times_csv,
            anchors_csv=anchors_csv,
            shots_map=shots_map,
            shots_stress=shots_stress,
            max_seconds=max_seconds,
            knobs=knobs,
            output_path=out_file,
        )
        row: dict[str, Any] = {
            "backend": backend,
            "n_qubits": int(nq),
            "output": str(out_file),
            "returncode": int(code),
        }
        if code == 0 and out_file.exists():
            try:
                report = json.loads(out_file.read_text(encoding="utf-8"))
                rows = extract_rows(report)
                row["rows"] = rows
            except Exception as exc:
                row["parse_error"] = str(exc)
        else:
            row["stdout_tail"] = "\n".join((stdout or "").splitlines()[-15:])
            row["stderr_tail"] = "\n".join((stderr or "").splitlines()[-15:])
        out.append(row)
    return out


def aggregate(full_runs: list[dict[str, Any]]) -> dict[str, Any]:
    slots: list[dict[str, Any]] = []
    for run in full_runs:
        backend = str(run.get("backend", "unknown"))
        nq = int(run.get("n_qubits", 0))
        for r in run.get("rows", []):
            d = dict(r)
            d["backend"] = backend
            d["n_qubits"] = nq
            best = max(
                ["BASE", "X", "XY4", "BB1", "CONTOUR"],
                key=lambda k: float(d.get(k, -1.0e9)),
            )
            d["best"] = best
            slots.append(d)

    arr_xy4 = np.asarray([float(s["dXY4"]) for s in slots], dtype=float) if slots else np.asarray([], dtype=float)
    arr_bb1 = np.asarray([float(s["dBB1"]) for s in slots], dtype=float) if slots else np.asarray([], dtype=float)
    arr_x = np.asarray([float(s["dX"]) for s in slots], dtype=float) if slots else np.asarray([], dtype=float)
    best_counts = Counter(str(s["best"]) for s in slots)

    out = {
        "n_slots": int(len(slots)),
        "wins_vs_xy4": int(np.sum(arr_xy4 > 0.0)) if arr_xy4.size else 0,
        "wins_vs_bb1": int(np.sum(arr_bb1 > 0.0)) if arr_bb1.size else 0,
        "wins_vs_x": int(np.sum(arr_x > 0.0)) if arr_x.size else 0,
        "mean_dxy4": float(arr_xy4.mean()) if arr_xy4.size else 0.0,
        "mean_dbb1": float(arr_bb1.mean()) if arr_bb1.size else 0.0,
        "mean_dx": float(arr_x.mean()) if arr_x.size else 0.0,
        "best_counts": {k: int(v) for k, v in sorted(best_counts.items())},
        "slots": slots,
    }
    return out


def claim_text(agg: dict[str, Any], backends: list[str], date_iso: str) -> str:
    n = int(agg.get("n_slots", 0))
    wxy = int(agg.get("wins_vs_xy4", 0))
    wbb = int(agg.get("wins_vs_bb1", 0))
    wx = int(agg.get("wins_vs_x", 0))
    mdxy = float(agg.get("mean_dxy4", 0.0))
    mdbb = float(agg.get("mean_dbb1", 0.0))

    if n <= 0:
        return "No successful full-run slots; no claim."

    if wxy == n and wbb == n and wx == n:
        return (
            f"As of {date_iso}, on tested chips {backends}, CONTOUR achieved a clean sweep "
            f"({n}/{n}) vs X/BB1/XY4 with mean deltas dXY4={mdxy:+.4f}, dBB1={mdbb:+.4f}."
        )
    return (
        f"As of {date_iso}, on tested chips {backends}, CONTOUR leads strongly vs X/BB1 "
        f"({wx}/{n}, {wbb}/{n}) and beats XY4 in {wxy}/{n} slots "
        f"(mean dXY4={mdxy:+.4f}, dBB1={mdbb:+.4f})."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily calibration daemon for validation3 CONTOUR.")
    ap.add_argument("--api-token", required=True)
    ap.add_argument("--backends", default="ibm_torino,ibm_fez,ibm_marrakesh")
    ap.add_argument("--times", default="3200,4912,6400,8000")
    ap.add_argument("--anchors", default="800,1600,2400,3200,4000,4800,5600,6400")
    ap.add_argument("--calibration-n-qubits", type=int, default=12)
    ap.add_argument("--full-n-qubits", default="6,8,12")
    ap.add_argument("--cal-shots-map", type=int, default=64)
    ap.add_argument("--cal-shots-stress", type=int, default=128)
    ap.add_argument("--full-shots-map", type=int, default=256)
    ap.add_argument("--full-shots-stress", type=int, default=512)
    ap.add_argument("--max-seconds", type=float, default=1800.0)
    ap.add_argument("--activation-depths", default="3200,4000,4800")
    ap.add_argument("--risk-highs", default="0.10,0.15,0.20")
    ap.add_argument("--risk-lows", default="0.03,0.05,0.08")
    ap.add_argument("--stagger-options", default="0,16")
    ap.add_argument("--seed-transpiler", type=int, default=53)
    ap.add_argument("--max-calibration-configs", type=int, default=0, help="0 means all")
    ap.add_argument("--output-dir", default="data/daemon")
    args = ap.parse_args()

    times_csv = ",".join(str(x) for x in parse_int_csv(args.times))
    anchors_csv = ",".join(str(x) for x in parse_int_csv(args.anchors))
    req_backends = parse_str_csv(args.backends)
    full_nq = parse_int_csv(args.full_n_qubits)

    discovered = discover_backends(args.api_token, req_backends)
    if not discovered:
        raise RuntimeError(f"No requested backends are currently available: {req_backends}")

    grid = make_grid(
        activation_depths=parse_int_csv(args.activation_depths),
        risk_highs=parse_float_csv(args.risk_highs),
        risk_lows=parse_float_csv(args.risk_lows),
        stagger_options=parse_int_csv(args.stagger_options),
        seed_transpiler=int(args.seed_transpiler),
    )
    if int(args.max_calibration_configs) > 0:
        grid = grid[: int(args.max_calibration_configs)]

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)

    all_calib: list[dict[str, Any]] = []
    all_full: list[dict[str, Any]] = []
    chosen: dict[str, Any] = {}

    for backend in discovered:
        calib_dir = root / "calibration"
        best_knobs, calib_rows = calibrate_backend(
            token=args.api_token,
            backend=backend,
            grid=grid,
            out_dir=calib_dir,
            times_csv=times_csv,
            anchors_csv=anchors_csv,
            calib_n_qubits=int(args.calibration_n_qubits),
            shots_map=int(args.cal_shots_map),
            shots_stress=int(args.cal_shots_stress),
            max_seconds=float(args.max_seconds),
        )
        all_calib.extend(calib_rows)
        if best_knobs is None:
            continue
        chosen[backend] = {
            "activation_depth": int(best_knobs.activation_depth),
            "risk_high": float(best_knobs.risk_high),
            "risk_low": float(best_knobs.risk_low),
            "stagger_dt": int(best_knobs.stagger_dt),
            "seed_transpiler": int(best_knobs.seed_transpiler),
            "tag": best_knobs.tag(),
        }

        full_dir = root / "full"
        full_rows = run_full_backend(
            token=args.api_token,
            backend=backend,
            knobs=best_knobs,
            n_qubits_list=full_nq,
            times_csv=times_csv,
            anchors_csv=anchors_csv,
            shots_map=int(args.full_shots_map),
            shots_stress=int(args.full_shots_stress),
            max_seconds=float(args.max_seconds),
            out_dir=full_dir,
        )
        all_full.extend(full_rows)

    agg = aggregate(all_full)
    now = datetime.now(timezone.utc).isoformat()
    claim = claim_text(agg, list(chosen.keys()), now)

    bundle = {
        "version": "validation3-daemon-v1",
        "timestamp_utc": now,
        "requested_backends": req_backends,
        "used_backends": discovered,
        "chosen_knobs_by_backend": chosen,
        "calibration_rows": all_calib,
        "full_rows": all_full,
        "aggregate": agg,
        "claim_for_today": claim,
    }

    out_json = root / f"daemon_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    out_json.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    out_md = root / f"daemon_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    out_md.write_text(
        "\n".join(
            [
                "# Validation3 Daemon Report",
                f"- UTC: {now}",
                f"- Requested backends: {req_backends}",
                f"- Used backends: {discovered}",
                f"- Claim: {claim}",
                "",
                "## Chosen Knobs",
                json.dumps(chosen, indent=2),
                "",
                "## Aggregate",
                json.dumps(agg, indent=2),
            ]
        ),
        encoding="utf-8",
    )
    print(f"Daemon report saved: {out_json}")
    print(f"Markdown summary: {out_md}")
    print(claim)


if __name__ == "__main__":
    main()

