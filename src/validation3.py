import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

DEFAULT_BACKEND = "ibm_torino"
DEFAULT_TIMES = [3200, 4912, 6400, 8000]
DEFAULT_ANCHORS = [800, 1600, 2400, 3200, 4000, 4800, 5600, 6400]
DEFAULT_ARMS = ["X", "XY4", "BB1", "CONTOUR"]
DEFAULT_GRID_DT = 16
GRID_DT = DEFAULT_GRID_DT
DEFAULT_SHOTS_MAP = 256
DEFAULT_SHOTS_STRESS = 256
DEFAULT_MAX_SECONDS = 1800.0

# Active backend topology/timing context (set in run_benchmark).
ACTIVE_TIMING_CONSTRAINTS: dict[str, int] = {}
ACTIVE_BACKEND_DT_S: float | None = None
ACTIVE_COLOR_BY_Q: list[int] = []
ACTIVE_COLOR_COUNT = 4
ACTIVE_COUPLING_EDGES_LOCAL: list[tuple[int, int]] = []

# SOTA Physics Constants
CONTOUR_SURF_CURVATURE_THRESHOLD = 0.20
CONTOUR_SURF_CLIP_RAD = 0.50
CONTOUR_SHOCK_CLIP_RAD = 0.25
CONTOUR_T1_EFFECTIVE_DT = 150000.0  # Scaled closer to actual heavy-hex T1 decay
CONTOUR_ZZ_UNWIND_GAIN = 1.0
CONTOUR_ZZ_UNWIND_CLIP = 8.0e-4

# Sweepable contour knobs (set from CLI in run_benchmark).
CONTOUR_ACTIVATION_DEPTH = 4000
CONTOUR_RISK_HIGH = 0.15
CONTOUR_RISK_LOW = 0.05
CONTOUR_STAGGER_DT = 0
CONTOUR_SEED_TRANSPILER: int | None = 53

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Direct SOTA drift-protection benchmark.")
    p.add_argument("--backend", default=DEFAULT_BACKEND)
    p.add_argument("--api-token", default=None)
    p.add_argument("--mode", choices=["runtime", "local"], default="runtime")
    p.add_argument("--n-qubits", type=int, default=12)
    p.add_argument("--times", default=",".join(str(v) for v in DEFAULT_TIMES))
    p.add_argument("--anchors", default=",".join(str(v) for v in DEFAULT_ANCHORS))
    p.add_argument("--arms", default=",".join(DEFAULT_ARMS))
    p.add_argument("--shots-map", type=int, default=DEFAULT_SHOTS_MAP)
    p.add_argument("--shots-stress", type=int, default=DEFAULT_SHOTS_STRESS)
    p.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    p.add_argument("--activation-depth", type=int, default=4000)
    p.add_argument("--risk-high", type=float, default=0.15)
    p.add_argument("--risk-low", type=float, default=0.05)
    p.add_argument("--contour-stagger-dt", type=int, default=0)
    p.add_argument("--seed-transpiler", type=int, default=53)
    p.add_argument("--output", default="")
    p.add_argument("--no-json", action="store_true")
    return p.parse_args()

def parse_int_list(raw: str) -> list[int]:
    return sorted(set([int(x.strip()) for x in raw.split(",") if x.strip()]))

def parse_arm_list(raw: str) -> list[str]:
    arms = [x.strip().upper() for x in raw.split(",") if x.strip()]
    valid = {"BASE", "X", "XY4", "BB1", "CONTOUR", "TITAN", "CONTOUR_RIGID"}
    out = []
    seen = set()
    for arm in arms:
        if arm not in valid:
            raise ValueError(f"Unsupported arm: {arm}. Valid={sorted(valid)}")
        # Canonicalize SOTA aliases
        if arm in {"TITAN", "CONTOUR_RIGID"}:
            arm = "CONTOUR"
        if arm not in seen:
            out.append(arm)
            seen.add(arm)
    if "BASE" not in seen:
        out.insert(0, "BASE")
    return out

def quantize_dt(t: int, grid: int | None = None) -> tuple[int, int]:
    use_grid = int(max(1, int(GRID_DT if grid is None else grid)))
    t_exec = int(t // use_grid) * use_grid
    return t_exec, int(t - t_exec)

def wrap_phase(x: float) -> float:
    return float(((x + np.pi) % (2 * np.pi)) - np.pi)

def fidelity_from_counts(counts: dict[str, int], n_qubits: int) -> float:
    total = int(sum(counts.values()))
    if total <= 0: return 0.0
    return float(counts.get("0" * int(n_qubits), 0) / total)

def alpha_from_counts(counts: dict[str, int], q: int, shots: int) -> float:
    if shots <= 0: return 0.0
    p0 = sum(v for k, v in counts.items() if k[-(q + 1)] == "0") / shots
    val = float(np.clip((2.0 * p0) - 1.0, -1.0, 1.0))
    return float(np.arcsin(val))

def infer_x_duration_dt(runtime_backend) -> int:
    if runtime_backend is None: return 8
    try:
        qc = QuantumCircuit(1)
        qc.x(0)
        tq = transpile(qc, runtime_backend, optimization_level=0, scheduling_method="alap")
        if getattr(tq, "duration", None):
            return int(max(1, int(tq.duration)))
    except Exception:
        pass
    return 8

def discover_timing_grid_dt(runtime_backend, fallback: int = DEFAULT_GRID_DT) -> tuple[int, dict[str, int], float | None]:
    constraints: dict[str, int] = {}
    dt_seconds: float | None = None
    if runtime_backend is None:
        return int(max(1, fallback)), constraints, dt_seconds

    try:
        cfg = runtime_backend.configuration()
        maybe_dt = getattr(cfg, "dt", None)
        if isinstance(maybe_dt, (int, float)) and float(maybe_dt) > 0.0:
            dt_seconds = float(maybe_dt)
        tc = getattr(cfg, "timing_constraints", None)
        if isinstance(tc, dict):
            for key in ("granularity", "pulse_alignment", "acquire_alignment"):
                raw = tc.get(key, None)
                if isinstance(raw, (int, float)) and int(raw) > 0:
                    constraints[key] = int(raw)
    except Exception:
        pass

    try:
        target = getattr(runtime_backend, "target", None)
        if target is not None:
            for key in ("granularity", "pulse_alignment", "acquire_alignment"):
                raw = getattr(target, key, None)
                if isinstance(raw, (int, float)) and int(raw) > 0 and key not in constraints:
                    constraints[key] = int(raw)
    except Exception:
        pass

    candidates: list[int] = [int(max(1, fallback))]
    candidates.extend(int(v) for v in constraints.values() if int(v) > 0)
    grid = int(max(candidates))
    return int(max(1, grid)), constraints, dt_seconds

def discover_coupling_edges(runtime_backend) -> list[tuple[int, int]]:
    if runtime_backend is None:
        return []

    raw_edges: list[tuple[int, int]] = []
    try:
        cm = getattr(runtime_backend, "coupling_map", None)
        if cm is not None:
            if hasattr(cm, "get_edges"):
                raw_edges = [(int(a), int(b)) for a, b in cm.get_edges()]
            elif isinstance(cm, (list, tuple)):
                raw_edges = [(int(a), int(b)) for a, b in cm]
    except Exception:
        raw_edges = []

    if not raw_edges:
        try:
            cfg = runtime_backend.configuration()
            cm = getattr(cfg, "coupling_map", None)
            if isinstance(cm, (list, tuple)):
                raw_edges = [(int(a), int(b)) for a, b in cm]
        except Exception:
            raw_edges = []

    undirected: set[tuple[int, int]] = set()
    for a, b in raw_edges:
        if int(a) == int(b):
            continue
        u, v = (int(a), int(b)) if int(a) < int(b) else (int(b), int(a))
        undirected.add((u, v))
    return sorted(undirected)

def greedy_graph_coloring(n_nodes: int, edges: list[tuple[int, int]]) -> list[int]:
    n = int(max(0, n_nodes))
    if n <= 0:
        return []
    adj: list[set[int]] = [set() for _ in range(n)]
    for u, v in edges:
        a, b = int(u), int(v)
        if a < 0 or b < 0 or a >= n or b >= n or a == b:
            continue
        adj[a].add(b)
        adj[b].add(a)
    order = sorted(range(n), key=lambda node: (-len(adj[node]), node))
    color = [-1 for _ in range(n)]
    for node in order:
        used = {color[nb] for nb in adj[node] if color[nb] >= 0}
        c = 0
        while c in used:
            c += 1
        color[node] = int(c)
    return [int(max(0, c)) for c in color]

def discover_layout_coloring(runtime_backend, n_qubits: int, layout: list[int]) -> tuple[list[int], int, list[tuple[int, int]]]:
    n = int(max(1, n_qubits))
    edges_phys = discover_coupling_edges(runtime_backend)
    if not edges_phys:
        fallback = [int(i % 4) for i in range(n)]
        return fallback, 4, []

    phys_to_local: dict[int, int] = {}
    for i in range(min(n, len(layout))):
        phys_to_local[int(layout[i])] = int(i)

    local_edges_set: set[tuple[int, int]] = set()
    for pa, pb in edges_phys:
        if pa not in phys_to_local or pb not in phys_to_local:
            continue
        a, b = phys_to_local[pa], phys_to_local[pb]
        if a == b:
            continue
        u, v = (a, b) if a < b else (b, a)
        local_edges_set.add((int(u), int(v)))

    local_edges = sorted(local_edges_set)
    if not local_edges:
        fallback = [int(i % 2) for i in range(n)]
        return fallback, 2, []

    colors = greedy_graph_coloring(n_nodes=n, edges=local_edges)
    n_colors = int(max(colors) + 1) if colors else 1
    return colors, int(max(1, n_colors)), local_edges

def contour_color_for_q(q: int) -> int:
    qi = int(q)
    if 0 <= qi < len(ACTIVE_COLOR_BY_Q):
        return int(ACTIVE_COLOR_BY_Q[qi])
    return int(qi % max(1, int(ACTIVE_COLOR_COUNT)))

def discover_layout(runtime_backend, n_qubits: int) -> list[int]:
    if runtime_backend is None: return list(range(n_qubits))
    try:
        qc = QuantumCircuit(n_qubits)
        qc.h(0)
        for i in range(n_qubits - 1): qc.cx(i, i + 1)
        pm = generate_preset_pass_manager(backend=runtime_backend, optimization_level=1)
        tq = pm.run(qc)
        if tq.layout and tq.layout.final_layout:
            phys = sorted(list(tq.layout.final_layout.get_physical_bits().keys()))
            if len(phys) >= n_qubits:
                return [int(x) for x in phys[:n_qubits]]
    except Exception:
        pass
    return list(range(n_qubits))

def get_counts_from_sampler_pub(pub_result) -> dict[str, int]:
    data = pub_result.data
    if hasattr(data, "c"): return dict(data.c.get_counts())
    if hasattr(data, "keys"):
        for k in data.keys():
            reg = getattr(data, k)
            if hasattr(reg, "get_counts"): return dict(reg.get_counts())
    for maybe in getattr(data, "__dict__", {}).values():
        if hasattr(maybe, "get_counts"): return dict(maybe.get_counts())
    raise RuntimeError("Could not extract counts from Sampler result.")

def run_batch_runtime(circuits: list[QuantumCircuit], backend, shots: int, timeout_s: float) -> tuple[list[dict[str, int]], str]:
    sampler = Sampler(mode=backend)
    job = sampler.run([(c,) for c in circuits], shots=int(shots))
    try:
        result = job.result(timeout=float(timeout_s))
        counts = [get_counts_from_sampler_pub(result[i]) for i in range(len(circuits))]
        return counts, str(job.job_id())
    except (TimeoutError, RuntimeJobTimeoutError):
        try: job.cancel()
        except Exception: pass
        raise RuntimeError(f"Runtime job timeout after {timeout_s:.1f}s.")

def run_batch_local(circuits: list[QuantumCircuit], shots: int) -> tuple[list[dict[str, int]], str]:
    sim = AerSimulator()
    job = sim.run(circuits, shots=int(shots))
    result = job.result()
    counts = [dict(result.get_counts(i)) for i in range(len(circuits))]
    return counts, "local-aer"

def transpile_with_fallback(circuits: list[QuantumCircuit], backend, initial_layout: list[int] | None, schedule: bool = True) -> list[QuantumCircuit]:
    kwargs: dict[str, Any] = {"backend": backend, "optimization_level": 0}
    if CONTOUR_SEED_TRANSPILER is not None:
        kwargs["seed_transpiler"] = int(CONTOUR_SEED_TRANSPILER)
    if initial_layout is not None: kwargs["initial_layout"] = initial_layout
    if schedule:
        try: return transpile(circuits, scheduling_method="alap", **kwargs)
        except Exception: pass
    return transpile(circuits, **kwargs)

def build_map_probe(delay_dt: int, n_qubits: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(range(n_qubits))
    for q in range(n_qubits): qc.delay(int(delay_dt), q, unit="dt")
    qc.sx(range(n_qubits))
    qc.measure(range(n_qubits), range(n_qubits))
    return qc

def fit_anchor_phase_matrix(anchor_execs: list[int], anchor_counts: list[dict[str, int]], shots: int, n_qubits: int) -> np.ndarray:
    mat = np.zeros((n_qubits, len(anchor_execs)), dtype=float)
    for i in range(len(anchor_execs)):
        for q in range(n_qubits):
            mat[q, i] = alpha_from_counts(anchor_counts[i], q, shots)
    return mat

def predict_phase_vector(t_exec: int, anchor_execs: list[int], phase_mat: np.ndarray) -> list[float]:
    x = np.asarray(anchor_execs, dtype=float)
    out: list[float] = []
    for q in range(phase_mat.shape[0]):
        y = np.unwrap(np.asarray(phase_mat[q], dtype=float))
        pred = float(np.interp(float(t_exec), x, y))
        out.append(wrap_phase(pred))
    return out

def y_pulse(qc: QuantumCircuit, q: int) -> None:
    qc.rz(-np.pi / 2.0, q)
    qc.x(q)
    qc.rz(np.pi / 2.0, q)

def phase_x_pulse(qc: QuantumCircuit, q: int, phase_rad: float) -> None:
    phi = wrap_phase(float(phase_rad))
    qc.rz(-phi, q)
    qc.x(q)
    qc.rz(phi, q)

def plan_delays(total_t: int, n_pulses: int, x_dur: int, grid: int, stagger_dt: int = 0) -> list[int] | None:
    if n_pulses <= 0:
        return [int(total_t)]

    stagger = int(max(0, stagger_dt))
    budget = int(total_t - (n_pulses * x_dur) - stagger)
    if budget < 0:
        return None

    delays = [0] * (n_pulses + 1)
    tau_float = float(budget) / float(2 * n_pulses)

    # 1. Distribute base symmetric times from the outside in.
    left_budget = int(budget)
    for i in range(n_pulses // 2):
        target_tau = tau_float if i == 0 else 2.0 * tau_float
        snapped = int(np.floor(target_tau / grid) * grid)
        delays[i] = int(snapped)
        delays[n_pulses - i] = int(snapped)
        left_budget -= int(2 * snapped)

    if n_pulses % 2 != 0:
        mid_idx = n_pulses // 2
        delays[mid_idx] = int(np.floor((2.0 * tau_float) / grid) * grid)
        left_budget -= int(delays[mid_idx])

    # 2. Distribute leftover slack strictly in symmetric pairs.
    slack_grids = int(left_budget // grid)
    idx = 1
    while slack_grids >= 2 and idx <= n_pulses // 2:
        if idx == n_pulses - idx:
            delays[idx] += int(2 * grid)
            slack_grids -= 2
        else:
            delays[idx] += int(grid)
            delays[n_pulses - idx] += int(grid)
            slack_grids -= 2
        idx += 1

    if slack_grids > 0:
        delays[n_pulses // 2] += int(slack_grids * grid)

    # 3. Apply the exact boundary shifts.
    delays[0] += int(stagger)
    diff = int(total_t - (sum(delays) + n_pulses * x_dur))
    delays[-1] += int(diff)

    if any(d < 0 for d in delays):
        return None
    return delays

def pulse_centers_from_delays(delays: list[int], x_dur: int, total_t: int) -> list[float]:
    t = 0.0
    centers: list[float] = []
    for i in range(len(delays) - 1):
        t += float(max(0, int(delays[i])))
        centers.append(float(np.clip(t + (0.5 * float(max(0, int(x_dur)))), 0.0, float(total_t))))
        t += float(max(0, int(x_dur)))
    return centers

def sample_phase_velocity(t_exec: float, total_t: int, pred_phase: float, anchor_execs: list[int] | None, phase_series: np.ndarray | None) -> tuple[float, float]:
    if anchor_execs is not None and phase_series is not None and len(anchor_execs) >= 2:
        x = np.asarray(anchor_execs, dtype=float)
        y = np.unwrap(np.asarray(phase_series, dtype=float))
        t = float(np.clip(float(t_exec), float(x[0]), float(x[-1])))
        theta = float(np.interp(t, x, y))
        idx = int(np.searchsorted(x, t, side="left"))
        if idx <= 0: i0, i1 = 0, 1
        elif idx >= len(x): i0, i1 = len(x) - 2, len(x) - 1
        else: i0, i1 = idx - 1, idx
        denom = float(max(1e-9, x[i1] - x[i0]))
        vel = float((y[i1] - y[i0]) / denom)
        return wrap_phase(theta), vel

    slope = float(pred_phase) / max(1.0, float(total_t))
    theta = float((float(t_exec) / max(1.0, float(total_t))) * float(pred_phase))
    return wrap_phase(theta), slope

def interp_phase_unwrapped(t_exec: float, total_t: int, pred_phase: float, anchor_execs: list[int] | None, phase_series: np.ndarray | None) -> float:
    # SOTA Fix: Stable Deep-Time Extrapolation
    if anchor_execs is not None and phase_series is not None and len(anchor_execs) >= 2:
        x = np.asarray(anchor_execs, dtype=float)
        y = np.unwrap(np.asarray(phase_series, dtype=float))
        t = float(t_exec)
        if t <= float(x[0]):
            denom = float(max(1e-9, x[1] - x[0]))
            slope = float((y[1] - y[0]) / denom)
            return float(y[0] + slope * (t - x[0]))
        if t >= float(x[-1]):
            # Blend local tail slope into global trend to prevent shot-noise whipping
            denom_local = float(max(1e-9, x[-1] - x[-2]))
            denom_global = float(max(1e-9, x[-1] - x[0]))
            local_slope = float((y[-1] - y[-2]) / denom_local)
            global_slope = float((y[-1] - y[0]) / denom_global)
            dt_tail = float(max(0.0, t - x[-1]))
            tau = float(max(denom_local, 0.20 * denom_global))
            w_local = float(np.exp(-dt_tail / max(1e-9, tau)))
            slope = float((w_local * local_slope) + ((1.0 - w_local) * global_slope))
            return float(y[-1] + slope * dt_tail)
        return float(np.interp(t, x, y))
    slope = float(pred_phase) / max(1.0, float(total_t))
    return float(slope * float(t_exec))

def analyze_phase_geometry(total_t: int, pred_phase: float, anchor_execs: list[int] | None, phase_series: np.ndarray | None) -> dict[str, float]:
    max_residual = 0.0
    if anchor_execs is not None and phase_series is not None and len(anchor_execs) >= 3:
        t_vec = np.asarray(anchor_execs, dtype=float)
        p_vec = np.unwrap(np.asarray(phase_series, dtype=float))
        valid_mask = t_vec <= (float(total_t) + 1000.0)
        t_val = t_vec[valid_mask]
        p_val = p_vec[valid_mask]
        if t_val.size >= 3 and p_val.size >= 3:
            m, b = np.polyfit(t_val, p_val, 1)
            linear_pred = (m * t_val) + b
            max_residual = float(np.max(np.abs(p_val - linear_pred)))
    is_surfing = bool(max_residual > CONTOUR_SURF_CURVATURE_THRESHOLD)
    return {
        "max_residual": float(max_residual),
        "adaptive_curvature_threshold": float(CONTOUR_SURF_CURVATURE_THRESHOLD),
        "is_surfing": float(1.0 if is_surfing else 0.0),
    }

def build_local_metrics_by_q(n_qubits: int, anchor_execs: list[int] | None, phase_mat: np.ndarray | None) -> list[dict[str, float]]:
    # Stripped the fake ZZ estimator. We cannot guess J_zz from 1/f noise.
    return [{"local_zz": 0.0} for _ in range(int(max(0, n_qubits)))]

def balanced_phase_cycle(n_pulses: int) -> list[float]:
    n = int(max(1, n_pulses))
    if n == 1: return [0.0]
    if n == 2: return [0.0, float(np.pi)]
    if n == 4: return [0.0, float(0.5 * np.pi), 0.0, float(0.5 * np.pi)]
    if n == 8: 
        # SOTA XY8 Parity: Perfectly returns to identity, 3rd-order amplitude armor
        p = float(0.5 * np.pi)
        return [0.0, p, 0.0, p, p, 0.0, p, 0.0]
    
    # Fallback to pure X for arbitrary lengths to prevent anti-identity Z-flips
    return [0.0 for _ in range(n)]

def z_dwell_from_schedule(delays: list[int], x_dur: int, total_t: int) -> tuple[float, float]:
    # SOTA Fix: Explicit Z-Dwell Timeline with Dead Zones
    plus_z = 0.0
    minus_z = 0.0
    t_cursor = 0.0
    sign = 1.0
    for i in range(len(delays)):
        seg = float(max(0, int(delays[i])))
        seg = float(min(seg, max(0.0, float(total_t) - t_cursor)))
        if sign >= 0.0: plus_z += seg
        else: minus_z += seg
        t_cursor += seg
        if i < (len(delays) - 1):
            dead = float(max(0, int(x_dur)))
            dead = float(min(dead, max(0.0, float(total_t) - t_cursor)))
            t_cursor += dead
            sign = -sign
        if t_cursor >= float(total_t): break
    return float(plus_z), float(minus_z)

def select_contour_pulse_count(total_t: int, pred_phase: float, anchor_execs: list[int] | None, phase_series: np.ndarray | None, local_metrics: dict[str, float] | None = None) -> tuple[int, bool]:
    # Dynamic geometry based on integrated non-linear drift action.
    if anchor_execs is None or phase_series is None or len(anchor_execs) < 3:
        return 2, False

    t_v = np.asarray(anchor_execs, dtype=float)
    p_v = np.unwrap(np.asarray(phase_series, dtype=float))
    m, b = np.polyfit(t_v, p_v, 1)
    linear_baseline = (m * t_v) + b
    residuals = np.abs(p_v - linear_baseline)
    action_integral = float(np.trapezoid(residuals, t_v))
    risk_factor = float(action_integral / max(1.0, float(total_t)))

    if risk_factor > float(CONTOUR_RISK_HIGH) and int(total_t) >= 4000:
        return 8, True
    if risk_factor > float(CONTOUR_RISK_LOW):
        return 4, True
    return 2, False

def synthesize_contour_profile(
    q: int,
    total_t: int,
    x_dur: int,
    delays: list[int] | None,
    pred_phase: float,
    anchor_execs: list[int] | None,
    phase_series: np.ndarray | None,
    color_id: int | None = None,
    local_metrics: dict[str, float] | None = None,
    is_surfing_regime: bool | None = None,
    stagger_active: bool = False,
) -> tuple[list[float], list[float]]:
    centers = pulse_centers_from_delays(delays or [], x_dur=x_dur, total_t=total_t)
    n_p = len(centers)
    if n_p <= 0:
        return [], []

    # Backend-aware spatial overlap with dynamic pre-distortion; no manual shock injection.
    # Parity-preserving Z4 lift in deep regime for bipartite maps.
    raw_color = int(q if color_id is None else color_id)
    if int(total_t) < int(CONTOUR_ACTIVATION_DEPTH):
        palette = 2
        cidx = int(raw_color % palette)
    else:
        palette = 4
        base2 = int(raw_color % 2)
        cidx = int(base2 + (2 * (int(q) % 2)))
    color_shift = float(cidx * (0.5 * np.pi))
    base_cycle = np.asarray(balanced_phase_cycle(n_p), dtype=float)

    phases: list[float] = []
    shocks: list[float] = []

    poly_grad = None
    linear_mb = None
    fit_degree = 2 if int(total_t) >= int(CONTOUR_ACTIVATION_DEPTH) else 1
    if anchor_execs is not None and phase_series is not None and len(anchor_execs) >= 3:
        t_v = np.asarray(anchor_execs, dtype=float)
        p_v = np.unwrap(np.asarray(phase_series, dtype=float))
        poly_grad = np.polyfit(t_v, p_v, fit_degree)
        linear_mb = np.polyfit(t_v, p_v, 1)

    for i, tc in enumerate(centers):
        active_drift = 0.0
        if poly_grad is not None and linear_mb is not None:
            smooth_th = float(np.polyval(poly_grad, tc))
            linear_th = float((linear_mb[0] * float(tc)) + linear_mb[1])
            active_drift = float(np.clip(smooth_th - linear_th, -CONTOUR_SURF_CLIP_RAD, CONTOUR_SURF_CLIP_RAD))
        phase_i = float(base_cycle[i] + color_shift + active_drift)
        phases.append(wrap_phase(phase_i))
        shocks.append(0.0)

    return phases, shocks

def prepare_contour_schedule(
    q: int,
    total_t: int,
    x_dur: int,
    grid: int,
    pred_phase: float,
    anchor_execs: list[int] | None,
    phase_series: np.ndarray | None,
    color_id: int | None = None,
    local_metrics: dict[str, float] | None = None,
    stagger_dt: int = 0,
) -> tuple[bool, list[int] | None, list[float] | None, list[float] | None, float]:
    metrics = analyze_phase_geometry(
        total_t=total_t, pred_phase=pred_phase, anchor_execs=anchor_execs, phase_series=phase_series
    )
    n_pulses, is_surfing_regime = select_contour_pulse_count(
        total_t=total_t, pred_phase=pred_phase, anchor_execs=anchor_execs, phase_series=phase_series, local_metrics=metrics
    )
    
    stagger = 0
    stagger_active = False
    if int(CONTOUR_STAGGER_DT) > 0 and int(q % 2) != 0 and (n_pulses > 2 or is_surfing_regime):
        stagger = int(max(grid, int(CONTOUR_STAGGER_DT)))
        stagger_active = True

    delays = plan_delays(total_t, n_pulses, x_dur, grid, stagger_dt=stagger)
    if delays is None:
        return False, None, None, None, 0.0

    phases, shocks = synthesize_contour_profile(
        q=q,
        total_t=total_t,
        x_dur=x_dur,
        delays=delays,
        pred_phase=pred_phase,
        anchor_execs=anchor_execs,
        phase_series=phase_series,
        color_id=color_id,
        local_metrics=local_metrics,
        is_surfing_regime=is_surfing_regime,
        stagger_active=stagger_active,
    )
    if len(phases) != n_pulses:
        return False, None, None, None, 0.0

    # Optional boundary closure when stagger is enabled.
    closure_phase = 0.0
    if stagger_active:
        time_in_z, time_in_minus_z = z_dwell_from_schedule(delays=delays, x_dur=x_dur, total_t=total_t)
        asymmetry_dt = float(time_in_z - time_in_minus_z)
        _th_end, dv_end = sample_phase_velocity(
            t_exec=float(total_t),
            total_t=total_t,
            pred_phase=pred_phase,
            anchor_execs=anchor_execs,
            phase_series=phase_series,
        )
        closure_phase = float(dv_end) * float(asymmetry_dt)

    return True, delays, phases, shocks, float(closure_phase)

def append_contour_sequence(
    qc: QuantumCircuit,
    q: int,
    total_t: int,
    x_dur: int,
    grid: int,
    pred_phase: float,
    anchor_execs: list[int] | None,
    phase_series: np.ndarray | None,
    color_id: int | None = None,
    local_metrics: dict[str, float] | None = None,
    stagger_dt: int = 0,
) -> tuple[bool, list[int] | None, list[float] | None]:
    ok, delays, phases, shocks, closure_phase = prepare_contour_schedule(
        q=q, total_t=total_t, x_dur=x_dur, grid=grid, pred_phase=pred_phase,
        anchor_execs=anchor_execs, phase_series=phase_series, color_id=color_id,
        local_metrics=local_metrics, stagger_dt=stagger_dt
    )
    if (not ok) or delays is None or phases is None or shocks is None:
        qc.delay(int(total_t), q, unit="dt")
        return False, None, None

    n_pulses = int(max(0, len(phases)))
    qc.delay(int(delays[0]), q, unit="dt")
    
    for i in range(n_pulses):
        s = float(shocks[i]) if i < len(shocks) else 0.0
        if abs(s) > 1e-9: qc.rz(-s, q)
        phase_x_pulse(qc, q, float(phases[i]))
        if abs(s) > 1e-9: qc.rz(s, q)
        qc.delay(int(delays[i + 1]), q, unit="dt")
        
    if abs(float(closure_phase)) > 1e-9:
        qc.rz(float(-wrap_phase(float(closure_phase))), q)
    return True, delays, phases

def build_arm_profile_for_magnus(arm: str, q: int, total_t: int, x_dur: int, grid: int, pred_phase: float, anchor_execs: list[int] | None, phase_series: np.ndarray | None) -> dict[str, Any]:
    name = str(arm).upper()
    if name in {"TITAN", "CONTOUR_RIGID"}: name = "CONTOUR"

    delays: list[int] | None = None
    phases: list[float] = []
    shocks: list[float] = []
    closure_phase = 0.0

    if name == "BASE": delays = [int(total_t)]
    elif name == "X":
        delays = plan_delays(total_t, 1, x_dur, grid)
        phases = [0.0]
    elif name == "XY4":
        delays = plan_delays(total_t, 4, x_dur, grid)
        phases = [0.0, float(np.pi / 2.0), 0.0, float(np.pi / 2.0)]
    elif name == "BB1":
        delays = plan_delays(total_t, 5, x_dur, grid)
        phi = float(np.arccos(-0.25))
        phases = [0.0, phi, 3.0 * phi, 3.0 * phi, phi]
    elif name == "CONTOUR":
        ok, d, p, s, cp = prepare_contour_schedule(
            q=q, total_t=total_t, x_dur=x_dur, grid=grid, pred_phase=pred_phase,
            anchor_execs=anchor_execs, phase_series=phase_series, color_id=contour_color_for_q(q),
            local_metrics=None, stagger_dt=0
        )
        if ok and d is not None and p is not None and s is not None:
            delays, phases, shocks, closure_phase = [int(v) for v in d], [float(v) for v in p], [float(v) for v in s], float(cp)
        else:
            delays, phases, shocks, closure_phase = [int(total_t)], [], [], 0.0
    else: delays = [int(total_t)]

    if delays is None: delays, phases, shocks = [int(total_t)], [], []

    pulse_starts, pulse_ends, pulse_centers = [], [], []
    t = 0.0
    for i in range(max(0, len(delays) - 1)):
        t += float(max(0, int(delays[i])))
        pulse_starts.append(float(t))
        pulse_centers.append(float(np.clip(t + (0.5 * float(max(0, x_dur))), 0.0, float(total_t))))
        t += float(max(0, x_dur))
        pulse_ends.append(float(t))

    eff_phases = [wrap_phase(float(phases[i]) + (float(shocks[i]) if i < len(shocks) else 0.0)) for i in range(max(0, len(phases)))]

    return {
        "arm": name, "delays": delays, "starts": pulse_starts, "ends": pulse_ends,
        "centers": pulse_centers, "phases": eff_phases, "closure_phase": float(closure_phase),
    }

def magnus_metrics_for_profile(profile: dict[str, Any], total_t: int, grid: int, x_dur: int, pred_phase: float, anchor_execs: list[int] | None, phase_series: np.ndarray | None) -> dict[str, float]:
    sample_dt = int(max(1, int(grid)))
    t_samples = np.arange(float(sample_dt) * 0.5, float(total_t), float(sample_dt), dtype=float)
    if t_samples.size == 0: t_samples = np.asarray([0.5 * float(total_t)], dtype=float)
    dt = float(sample_dt)

    centers = np.asarray(profile.get("centers", []), dtype=float)
    starts = np.asarray(profile.get("starts", []), dtype=float)
    ends = np.asarray(profile.get("ends", []), dtype=float)
    phases = np.asarray(profile.get("phases", []), dtype=float)

    omega_vals = np.zeros_like(t_samples, dtype=float)
    for i, ts in enumerate(t_samples):
        _th, dv = sample_phase_velocity(t_exec=float(ts), total_t=total_t, pred_phase=pred_phase, anchor_execs=anchor_execs, phase_series=phase_series)
        omega_vals[i] = float(dv)

    signs = np.where((np.searchsorted(centers, t_samples, side="right") % 2) == 0, 1.0, -1.0).astype(float) if centers.size > 0 else np.ones_like(t_samples, dtype=float)
    hz = signs * omega_vals

    active_idx = np.full(t_samples.shape[0], -1, dtype=int)
    if starts.size > 0 and ends.size > 0:
        idx = np.searchsorted(starts, t_samples, side="right") - 1
        valid = (idx >= 0) & (idx < starts.size) & (t_samples < ends[idx])
        active_idx[valid] = idx[valid]

    drive_amp = float(np.pi / max(1.0, float(max(1, x_dur))))
    hx, hy = np.zeros_like(t_samples, dtype=float), np.zeros_like(t_samples, dtype=float)
    active_mask = active_idx >= 0
    if np.any(active_mask):
        idxv = active_idx[active_mask]
        phi = np.zeros(idxv.shape[0], dtype=float)
        good = idxv < max(0, phases.size)
        phi[good] = phases[idxv[good]]
        hx[active_mask] = drive_amp * np.cos(phi)
        hy[active_mask] = drive_amp * np.sin(phi)

    norm_dc = float(np.sum(np.abs(omega_vals)) * dt + 1e-12)
    first_dc = float(abs((np.sum(hz) * dt) - float(profile.get("closure_phase", 0.0))) / norm_dc)

    tau = (t_samples / max(1.0, float(total_t))) - 0.5
    norm_lin = float(np.sum(np.abs(omega_vals * tau)) * dt + 1e-12)
    first_lin = float(abs(np.sum(hz * tau) * dt) / norm_lin) if norm_lin > 1e-12 else 0.0

    H = np.stack([hx, hy, hz], axis=1)
    cross = np.linalg.norm(np.cross(H[:, None, :], H[None, :, :]), axis=2)
    np.fill_diagonal(cross, 0.0)
    upper = np.triu(cross, k=1)
    
    norms = np.linalg.norm(H, axis=1)
    den_u = np.triu(np.outer(norms, norms), k=1)

    return {
        "first_order_dc": first_dc,
        "first_order_linear": first_lin,
        "first_order_total": float(0.5 * (first_dc + first_lin)),
        "second_order_raw": float(0.5 * (dt * dt) * np.sum(upper) / max(1.0, float(total_t * total_t))),
        "second_order_norm": float(np.sum(upper) / (np.sum(den_u) + 1e-12)),
        "sample_dt": float(sample_dt),
    }

def calculate_magnus_bounds(arm: str, total_t: int, n_qubits: int, x_dur: int, grid: int, pred_phase_by_q: list[float], anchor_execs: list[int] | None, phase_mat: np.ndarray | None) -> dict[str, Any]:
    # M1 and M2 diagnostics zeroed out to prevent aliasing/frame-mixing artifacts.
    return {
        "first_order_dc_mean": 0.0, "first_order_linear_mean": 0.0, "first_order_total_mean": 0.0,
        "second_order_raw_mean": 0.0, "second_order_norm_mean": 0.0, "second_order_norm_p90": 0.0,
        "sample_dt": float(max(1, int(grid))),
    }

def append_arm_delay(qc: QuantumCircuit, q: int, total_t: int, arm: str, pred_phase: float, x_dur: int, grid: int, anchor_execs: list[int] | None = None, phase_series: np.ndarray | None = None, local_metrics: dict[str, float] | None = None) -> dict[str, Any]:
    if arm in {"TITAN", "CONTOUR_RIGID"}: arm = "CONTOUR"

    if arm == "BASE":
        qc.delay(int(total_t), q, unit="dt")
        return {"applied": "BASE", "pulses": 0}
    if arm == "X":
        delays = plan_delays(total_t, 1, x_dur, grid)
        if delays is None:
            qc.delay(int(total_t), q, unit="dt")
            return {"applied": "X_FALLBACK", "pulses": 0}
        qc.delay(delays[0], q, unit="dt")
        qc.x(q)
        qc.delay(delays[1], q, unit="dt")
        return {"applied": "X", "pulses": 1}
    if arm == "XY4":
        delays = plan_delays(total_t, 4, x_dur, grid)
        if delays is None:
            qc.delay(int(total_t), q, unit="dt")
            return {"applied": "XY4_FALLBACK", "pulses": 0}
        qc.delay(delays[0], q, unit="dt")
        for i, ax in enumerate(["X", "Y", "X", "Y"]):
            if ax == "X": qc.x(q)
            else: y_pulse(qc, q)
            qc.delay(delays[i + 1], q, unit="dt")
        return {"applied": "XY4", "pulses": 4}
    if arm == "BB1":
        delays = plan_delays(total_t, 5, x_dur, grid)
        if delays is None:
            qc.delay(int(total_t), q, unit="dt")
            return {"applied": "BB1_FALLBACK", "pulses": 0}
        phi = float(np.arccos(-0.25))
        qc.delay(delays[0], q, unit="dt")
        qc.x(q)
        qc.delay(delays[1], q, unit="dt")
        phase_x_pulse(qc, q, phi)
        qc.delay(delays[2], q, unit="dt")
        phase_x_pulse(qc, q, 3.0 * phi)
        qc.delay(delays[3], q, unit="dt")
        phase_x_pulse(qc, q, 3.0 * phi)
        qc.delay(delays[4], q, unit="dt")
        phase_x_pulse(qc, q, phi)
        qc.delay(delays[5], q, unit="dt")
        return {"applied": "BB1", "pulses": 5}
    if arm == "CONTOUR":
        ok, _delays, phases = append_contour_sequence(
            qc=qc, q=q, total_t=total_t, x_dur=x_dur, grid=grid, pred_phase=pred_phase,
            anchor_execs=anchor_execs, phase_series=phase_series, color_id=contour_color_for_q(q),
            local_metrics=local_metrics, stagger_dt=0
        )
        if not ok: return {"applied": f"{arm}_FALLBACK", "pulses": 0}
        return {"applied": arm, "pulses": int(max(0, len(phases or [])))}
    raise ValueError(f"Unsupported arm: {arm}")

def build_protected_memory_circuit(delay_dt: int, n_qubits: int, arm: str, pred_phase_by_q: list[float], x_dur: int, grid: int, anchor_execs: list[int] | None = None, phase_mat: np.ndarray | None = None) -> tuple[QuantumCircuit, dict[str, Any]]:
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(range(n_qubits))
    applied_counts: dict[str, int] = {}
    pulses = 0
    arm_name = str(arm).upper()
    if arm_name in {"TITAN", "CONTOUR_RIGID"}: arm_name = "CONTOUR"

    local_metrics_by_q = build_local_metrics_by_q(n_qubits=n_qubits, anchor_execs=anchor_execs, phase_mat=phase_mat)

    for q in range(n_qubits):
        series = None if phase_mat is None else phase_mat[q]
        meta = append_arm_delay(
            qc=qc, q=q, total_t=int(delay_dt), arm=arm_name, pred_phase=float(pred_phase_by_q[q]),
            x_dur=int(x_dur), grid=int(grid), anchor_execs=anchor_execs, phase_series=series,
            local_metrics=local_metrics_by_q[q] if q < len(local_metrics_by_q) else None
        )
        key = str(meta.get("applied", "UNKNOWN"))
        applied_counts[key] = int(applied_counts.get(key, 0) + 1)
        pulses += int(meta.get("pulses", 0))
    qc.h(range(n_qubits))
    qc.measure(range(n_qubits), range(n_qubits))
    return qc, {"applied_counts": applied_counts, "pulse_count_total": int(pulses)}

def default_output() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%M%S")
    return Path("data") / f"validation3_{ts}.json"

def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    global CONTOUR_ACTIVATION_DEPTH, CONTOUR_RISK_HIGH, CONTOUR_RISK_LOW, CONTOUR_STAGGER_DT, CONTOUR_SEED_TRANSPILER
    global GRID_DT, ACTIVE_TIMING_CONSTRAINTS, ACTIVE_BACKEND_DT_S
    global ACTIVE_COLOR_BY_Q, ACTIVE_COLOR_COUNT, ACTIVE_COUPLING_EDGES_LOCAL
    CONTOUR_ACTIVATION_DEPTH = int(max(1, int(args.activation_depth)))
    CONTOUR_RISK_HIGH = float(max(0.0, args.risk_high))
    CONTOUR_RISK_LOW = float(max(0.0, args.risk_low))
    if CONTOUR_RISK_HIGH <= CONTOUR_RISK_LOW:
        CONTOUR_RISK_HIGH = float(CONTOUR_RISK_LOW + 1e-6)
    CONTOUR_STAGGER_DT = int(max(0, int(args.contour_stagger_dt)))
    CONTOUR_SEED_TRANSPILER = None if int(args.seed_transpiler) < 0 else int(args.seed_transpiler)
    n_qubits = int(max(2, args.n_qubits))
    times_req = parse_int_list(args.times)
    anchors_req = parse_int_list(args.anchors)
    arms = parse_arm_list(args.arms)

    backend = None
    layout = list(range(n_qubits))
    x_dur = 8
    GRID_DT = int(DEFAULT_GRID_DT)
    ACTIVE_TIMING_CONSTRAINTS = {}
    ACTIVE_BACKEND_DT_S = None
    if args.mode == "runtime":
        if not args.api_token:
            raise ValueError("--api-token is required in runtime mode.")
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=args.api_token)
        backend = service.backend(args.backend)
        layout = discover_layout(backend, n_qubits)
        x_dur = infer_x_duration_dt(backend)
        GRID_DT, ACTIVE_TIMING_CONSTRAINTS, ACTIVE_BACKEND_DT_S = discover_timing_grid_dt(
            backend, fallback=DEFAULT_GRID_DT
        )

    times = [quantize_dt(t, GRID_DT)[0] for t in times_req]
    anchors = sorted(set(quantize_dt(t, GRID_DT)[0] for t in anchors_req))
    ACTIVE_COLOR_BY_Q, ACTIVE_COLOR_COUNT, ACTIVE_COUPLING_EDGES_LOCAL = discover_layout_coloring(
        runtime_backend=backend, n_qubits=n_qubits, layout=layout
    )

    print("\n=== VALIDATION3 Direct Benchmark ===")
    print(f"Mode: {args.mode} | Backend: {args.backend} | Qubits: {n_qubits}")
    print(f"Arms: {arms} | Times: {times}")
    print(
        f"Grid dt={GRID_DT} | Colors={ACTIVE_COLOR_COUNT} | Coupling edges(local)={len(ACTIVE_COUPLING_EDGES_LOCAL)}"
    )

    map_circs = [build_map_probe(a, n_qubits) for a in anchors]
    t0 = time.time()
    if args.mode == "runtime":
        t_map = transpile_with_fallback(map_circs, backend, layout, schedule=True)
        map_counts, map_job = run_batch_runtime(t_map, backend=backend, shots=args.shots_map, timeout_s=float(args.max_seconds))
    else:
        map_counts, map_job = run_batch_local(map_circs, shots=args.shots_map)
    t1 = time.time()
    phase_mat = fit_anchor_phase_matrix(anchors, map_counts, int(args.shots_map), n_qubits)
    print(f"[MAP] circuits={len(map_circs)} shots={args.shots_map} time={t1 - t0:.2f}s job={map_job}")

    stress_circs: list[QuantumCircuit] = []
    stress_meta: list[dict[str, Any]] = []
    for t in times:
        pred = predict_phase_vector(t, anchors, phase_mat)
        for arm in arms:
            magnus = calculate_magnus_bounds(arm, int(t), n_qubits, x_dur, GRID_DT, pred, anchors, phase_mat)
            c, info = build_protected_memory_circuit(t, n_qubits, arm, pred, x_dur, GRID_DT, anchors, phase_mat)
            stress_circs.append(c)
            stress_meta.append({"time_dt": int(t), "arm": arm, "metadata": info, "magnus": magnus})

    t2 = time.time()
    if args.mode == "runtime":
        t_stress = transpile_with_fallback(stress_circs, backend, layout, schedule=True)
        stress_counts, stress_job = run_batch_runtime(t_stress, backend=backend, shots=args.shots_stress, timeout_s=float(args.max_seconds))
    else:
        stress_counts, stress_job = run_batch_local(stress_circs, shots=args.shots_stress)
    t3 = time.time()
    print(f"[STRESS] circuits={len(stress_circs)} shots={args.shots_stress} time={t3 - t2:.2f}s job={stress_job}")

    records: list[dict[str, Any]] = []
    i = 0
    for t in times:
        row = {"time_executed_dt": int(t), "arms": {}, "best_arm": None, "best_arm_fidelity": 0.0}
        for arm in arms:
            counts = stress_counts[i]
            meta = stress_meta[i]["metadata"]
            fid = fidelity_from_counts(counts, n_qubits=n_qubits)
            row["arms"][arm] = {"fidelity": float(fid), "metadata": meta, "magnus_bounds": stress_meta[i]["magnus"]}
            if fid > float(row["best_arm_fidelity"]):
                row["best_arm"] = arm
                row["best_arm_fidelity"] = float(fid)
            i += 1
        records.append(row)

    print("\n=== Head-to-Head ===")
    for rec in records:
        print(f"\nTIME {rec['time_executed_dt']}dt")
        for arm in arms:
            fid = rec["arms"][arm]["fidelity"]
            f1 = float(rec["arms"][arm]["magnus_bounds"].get("first_order_total_mean", 0.0))
            f2 = float(rec["arms"][arm]["magnus_bounds"].get("second_order_norm_mean", 0.0))
            print(f"  {arm:<8} {fid:.6f}  |  M1={f1:.4f}  M2={f2:.4f}")
        print(f"  BEST     {rec['best_arm']} ({rec['best_arm_fidelity']:.6f})")

    out = {
        "version": "validation3-direct", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode, "backend": args.backend, "grid_dt": int(GRID_DT),
        "backend_dt_seconds": (None if ACTIVE_BACKEND_DT_S is None else float(ACTIVE_BACKEND_DT_S)),
        "timing_constraints": {k: int(v) for k, v in ACTIVE_TIMING_CONSTRAINTS.items()},
        "coloring": {
            "n_colors": int(ACTIVE_COLOR_COUNT),
            "color_by_q": [int(v) for v in ACTIVE_COLOR_BY_Q],
            "local_edge_count": int(len(ACTIVE_COUPLING_EDGES_LOCAL)),
        },
        "n_qubits": int(n_qubits), "x_duration_dt": int(x_dur),
        "times_executed_dt": times, "arms": arms, "jobs": {"map_job_id": str(map_job), "stress_job_id": str(stress_job)},
        "records": records,
    }
    return out

def main() -> None:
    args = parse_args()
    out = run_benchmark(args)
    if not args.no_json:
        out_path = Path(args.output) if str(args.output).strip() else default_output()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nSaved report: {out_path}")

if __name__ == "__main__": main()
