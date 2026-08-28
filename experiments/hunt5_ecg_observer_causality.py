"""
HUNT5 — ECG observer causality test

Faithful headless transcription of the supplied five-node Perception
Laboratory loop. No Qt and no learning code are required.

Graph:
    coupler -> checkerboard -> ImageToVector -> VectorSplitter
       ^                                      |
       +------------ first four --------------+

The controller is never changed between observer experiments.
Only the readout geometry changes.
"""

import argparse
import json
import math
from collections import deque
import numpy as np


IMAGE_SIZE = 256
DOWNSAMPLED_SIDE = 16
OUTPUT_DIM = 256
CONNECTED_CHANNELS = 4

SETPOINT = 0.5
SETPOINT_MOD = 1.0
SHARPNESS = 3.0
TARGET_VARIANCE = 0.1
VARIANCE_WINDOW = 50

INITIAL_FEEDBACK = 1.375

AMBIGUITY_THRESHOLD = 0.01
RESOLUTION_SIDES = (16, 32, 64, 128, 256)


def checker_from_square_size(square_size, size=IMAGE_SIZE):
    """Reproduce CheckerboardNode, including the q=0 NumPy behavior."""
    y, x = np.mgrid[0:size, 0:size]
    with np.errstate(divide="ignore", invalid="ignore"):
        image = ((x // square_size) + (y // square_size)) % 2
    return image.astype(np.float64)


def square_size_from_signal(signal_out):
    return int(5 + signal_out * 50)


def downsample_area(image, side):
    """
    Exact INTER_AREA equivalent for the resolutions used here because
    each side divides 256 exactly.
    """
    if side == image.shape[0]:
        return image.copy()
    n = image.shape[0]
    if n % side:
        raise ValueError("side must divide image size exactly")
    block = n // side
    return image.reshape(side, block, side, block).mean(axis=(1, 3))


def normalized_flat(tiny):
    flat = tiny.ravel().copy()
    max_value = float(np.max(np.abs(flat)))
    if max_value > 0:
        flat /= max_value
    return flat


def fixed_aperture_observation(square_size, side=16, y=0, x=0):
    """
    Return exactly four contiguous normalized cells from one row.

    Original graph is side=16, y=0, x=0.
    """
    image = checker_from_square_size(square_size)
    tiny = downsample_area(image, side)
    normalized = normalized_flat(tiny)
    raw = tiny.ravel()

    index = y * side + x
    raw4 = raw[index:index + CONNECTED_CHANNELS]
    out4 = normalized[index:index + CONNECTED_CHANNELS]

    return float(np.sum(out4)), {
        "side": side,
        "y": y,
        "x": x,
        "aperture_variance": float(np.var(raw4)),
        "full_variance": float(np.var(tiny)),
        "raw4": raw4.tolist(),
        "normalized4": out4.tolist(),
    }


def best_four_cell_window(square_size, side):
    """
    Find the contiguous four-cell aperture with largest raw variance.
    This is deliberately a simple identifiability proxy, not a novelty claim.
    """
    image = checker_from_square_size(square_size)
    tiny = downsample_area(image, side)
    normalized = normalized_flat(tiny).reshape(side, side)

    best = None
    for y in range(side):
        for x in range(side - CONNECTED_CHANNELS + 1):
            raw4 = tiny[y, x:x + CONNECTED_CHANNELS]
            variance = float(np.var(raw4))
            candidate = (
                variance,
                float(np.sum(normalized[y, x:x + CONNECTED_CHANNELS])),
                y,
                x,
                float(np.var(tiny)),
            )
            if best is None or candidate[0] > best[0]:
                best = candidate

    variance, value, y, x, full_variance = best
    return value, {
        "side": side,
        "y": y,
        "x": x,
        "aperture_variance": variance,
        "full_variance": full_variance,
    }


class EdgeOfChaosCoupler:
    """
    Headless copy of the signal path used by HomeostaticCouplerNode.

    The JSON supplies ConstantSignal=1.0 to setpoint_mod, so the
    effective setpoint is 0.5 + 0.1 = 0.6.
    """

    def __init__(self):
        self.history = deque(maxlen=200)

    def step(self, signal_in):
        effective_setpoint = SETPOINT + SETPOINT_MOD * 0.1

        self.history.append(float(signal_in))
        if len(self.history) > 10:
            recent = np.asarray(list(self.history)[-VARIANCE_WINDOW:])
            current_variance = float(np.var(recent))
        else:
            current_variance = 0.0

        variance_error = current_variance - TARGET_VARIANCE
        error = float(signal_in) - effective_setpoint

        if variance_error > 0:
            # Damping branch.
            z = error * SHARPNESS
            sigmoid = 2.0 / (1.0 + np.exp(-z)) - 1.0
            output = effective_setpoint + sigmoid / SHARPNESS
            regime = -1
        else:
            # Exciting branch.
            amplified = (
                effective_setpoint
                + error * (1.0 + abs(variance_error) * 10.0)
            )
            output = (
                effective_setpoint
                + np.tanh((amplified - effective_setpoint) * 2.0)
            )
            regime = +1

        return float(output), {
            "current_variance": current_variance,
            "variance_error": variance_error,
            "regime": regime,
        }


def original_observer(square_size):
    value, info = fixed_aperture_observation(
        square_size, side=16, y=0, x=0
    )
    info["mode"] = "original"
    return value, info


def make_fixed_observer(x):
    def observer(square_size):
        value, info = fixed_aperture_observation(
            square_size, side=16, y=0, x=x
        )
        info["mode"] = "fixed"
        return value, info
    return observer


def aperture_rescue_observer(square_size):
    """
    Causal coarse-wall intervention.

    Behave exactly like the original observer whenever the original
    four-cell aperture has raw variance >= threshold.

    Only when that aperture becomes locally indistinguishable, search
    another four-cell window at the SAME 16x16 resolution.

    If the entire 16x16 representation is also too flat, escalate to
    the cheapest finer resolution with an informative four-cell window.
    """
    original_value, original_info = fixed_aperture_observation(
        square_size, side=16, y=0, x=0
    )

    if original_info["aperture_variance"] >= AMBIGUITY_THRESHOLD:
        original_info["mode"] = "original"
        return original_value, original_info

    value, info = best_four_cell_window(square_size, 16)
    if info["aperture_variance"] >= AMBIGUITY_THRESHOLD:
        info["mode"] = "shift_same_resolution"
        return value, info

    for side in RESOLUTION_SIDES[1:]:
        value, info = best_four_cell_window(square_size, side)
        if info["aperture_variance"] >= AMBIGUITY_THRESHOLD:
            info["mode"] = "finer_resolution"
            return value, info

    original_info["mode"] = "unresolved"
    return original_value, original_info


def resolution_only_rescue_observer(square_size):
    """
    Fine-wall intervention.

    Leave the original aperture untouched unless the ENTIRE 16x16
    representation loses contrast. Then escalate resolution.

    This deliberately does not repair the q≈84 aperture wall.
    """
    original_value, original_info = fixed_aperture_observation(
        square_size, side=16, y=0, x=0
    )

    if original_info["full_variance"] >= AMBIGUITY_THRESHOLD:
        original_info["mode"] = "original"
        return original_value, original_info

    for side in RESOLUTION_SIDES[1:]:
        value, info = best_four_cell_window(square_size, side)
        if info["aperture_variance"] >= AMBIGUITY_THRESHOLD:
            info["mode"] = "finer_resolution"
            return value, info

    original_info["mode"] = "unresolved"
    return original_value, original_info


def run_loop(observer, steps=3000):
    coupler = EdgeOfChaosCoupler()
    feedback = INITIAL_FEEDBACK
    rows = []

    for t in range(steps):
        signal_out, controller = coupler.step(feedback)
        square_size = square_size_from_signal(signal_out)
        next_feedback, observer_info = observer(square_size)

        rows.append({
            "t": t,
            "signal_out": signal_out,
            "square_size": square_size,
            "feedback": next_feedback,
            "controller_variance": controller["current_variance"],
            "variance_error": controller["variance_error"],
            "regime": controller["regime"],
            "observer": observer_info,
        })
        feedback = next_feedback

    return rows


def minimal_period(values, max_period=300, window=1000, tolerance=1e-12):
    values = np.asarray(values[-window:], dtype=float)
    for period in range(1, max_period + 1):
        if np.max(np.abs(values[period:] - values[:-period])) <= tolerance:
            return period
    return None


def summarize(rows):
    tail = rows[-1000:]
    period = minimal_period([r["feedback"] for r in rows])
    return {
        "period": period,
        "signal_min": min(r["signal_out"] for r in tail),
        "signal_max": max(r["signal_out"] for r in tail),
        "square_min": min(r["square_size"] for r in tail),
        "square_max": max(r["square_size"] for r in tail),
        "feedback_values": sorted({
            round(r["feedback"], 12) for r in tail
        }),
        "observer_modes": sorted({
            r["observer"]["mode"] for r in tail
        }),
    }


def fixed_aperture_sweep(steps=2500):
    rows = []
    for x in range(13):
        run = run_loop(make_fixed_observer(x), steps=steps)
        summary = summarize(run)
        rows.append({
            "x": x,
            **summary,
        })
    return rows


def cycle_signature(rows, period):
    if period is None:
        return []
    return [
        {
            "square_size": int(r["square_size"]),
            "feedback": float(r["feedback"]),
        }
        for r in rows[-period:]
    ]


def observability_receipt(square_sizes):
    receipt = []
    for q in square_sizes:
        value, info = fixed_aperture_observation(q, 16, 0, 0)
        row = {
            "square_size": q,
            "feedback": value,
            "aperture_variance": info["aperture_variance"],
            "full16_variance": info["full_variance"],
        }

        finer = {}
        for side in RESOLUTION_SIDES:
            candidate_value, candidate = best_four_cell_window(q, side)
            finer[str(side)] = {
                "best_aperture_variance": candidate["aperture_variance"],
                "feedback": candidate_value,
            }
        row["resolution_probe"] = finer
        receipt.append(row)
    return receipt


def run_all(steps=3000):
    baseline = run_loop(original_observer, steps=steps)
    aperture_rescue = run_loop(aperture_rescue_observer, steps=steps)
    resolution_rescue = run_loop(
        resolution_only_rescue_observer, steps=steps
    )

    baseline_summary = summarize(baseline)
    aperture_summary = summarize(aperture_rescue)
    resolution_summary = summarize(resolution_rescue)

    return {
        "baseline": {
            "summary": baseline_summary,
            "cycle": cycle_signature(
                baseline, baseline_summary["period"]
            ),
        },
        "aperture_rescue": {
            "summary": aperture_summary,
            "cycle": cycle_signature(
                aperture_rescue, aperture_summary["period"]
            ),
        },
        "resolution_only_rescue": {
            "summary": resolution_summary,
            "cycle": cycle_signature(
                resolution_rescue, resolution_summary["period"]
            ),
        },
        "fixed_aperture_sweep": fixed_aperture_sweep(
            steps=max(2500, steps)
        ),
        "observability_receipt": observability_receipt(
            [48, 43, 84, -14, -12, -7, -1, 0, 1]
        ),
    }


def print_report(result):
    print("HUNT5 — ECG observer causality")
    print()

    for key in [
        "baseline",
        "aperture_rescue",
        "resolution_only_rescue",
    ]:
        s = result[key]["summary"]
        print(
            f"{key:24s} "
            f"period={str(s['period']):>4s} "
            f"signal=[{s['signal_min']:.6f},{s['signal_max']:.6f}] "
            f"square=[{s['square_min']},{s['square_max']}]"
        )

    print()
    print("Fixed 16x16 top-row aperture sweep")
    print("x   period   square-range")
    for row in result["fixed_aperture_sweep"]:
        print(
            f"{row['x']:2d}  "
            f"{str(row['period']):>6s}   "
            f"[{row['square_min']},{row['square_max']}]"
        )

    print()
    print("Baseline period-52 square-size cycle")
    print([
        row["square_size"]
        for row in result["baseline"]["cycle"]
    ])

    print()
    print("Observability receipt")
    print("q     feedback   aperture-var   full16-var")
    for row in result["observability_receipt"]:
        print(
            f"{row['square_size']:4d}  "
            f"{row['feedback']:9.6f}   "
            f"{row['aperture_variance']:.9f}   "
            f"{row['full16_variance']:.9f}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_all(steps=args.steps)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
