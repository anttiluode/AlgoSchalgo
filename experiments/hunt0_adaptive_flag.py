import argparse
import itertools
import json
import math
from functools import lru_cache

import numpy as np
from scipy.linalg import expm
from scipy.optimize import linear_sum_assignment


def _score(true_frame, est_frame):
    """Mean absolute cosine of same-labelled semantic axes."""
    return float(np.mean(np.abs(np.sum(true_frame * est_frame, axis=0))))


def _eigh_desc(A):
    vals, vecs = np.linalg.eigh(A)
    order = np.argsort(vals)[::-1]
    return vals[order], vecs[:, order]


def _match_frame(previous, vals, vecs):
    """Nearest-overlap eigenvector tracker (Hungarian + sign alignment)."""
    rows, cols = linear_sum_assignment(-np.abs(previous.T @ vecs))
    out = np.zeros_like(previous)
    out_vals = np.zeros(len(vals))
    for r, c in zip(rows, cols):
        v = vecs[:, c].copy()
        if previous[:, r] @ v < 0:
            v *= -1
        out[:, r] = v
        out_vals[r] = vals[c]
    return out, out_vals


def _closest_basis_in_subspace(U, previous_block):
    """Basis of span(U) closest to old semantic block."""
    left, _, right_t = np.linalg.svd(
        U.T @ previous_block, full_matrices=False
    )
    return U @ (left @ right_t)


def _spectral_clusters(vals, threshold):
    clusters = []
    start = 0
    for j in range(len(vals) - 1):
        if abs(vals[j] - vals[j + 1]) >= threshold:
            clusters.append(list(range(start, j + 1)))
            start = j + 1
    clusters.append(list(range(start, len(vals))))
    return clusters


def _adaptive_block_update(previous, vals, vecs, threshold):
    """
    Treat a near-degenerate cluster as one identifiable subspace.

    A current spectral cluster is assigned to the same number of previous
    semantic axes by maximum projector overlap. A singleton gets ordinary
    vector tracking. A multi-mode block receives a Procrustes basis that
    moves with the measured subspace but does not chase the unidentifiable
    rotation inside it.
    """
    d = len(vals)
    clusters = _spectral_clusters(vals, threshold)
    remaining = set(range(d))
    out = np.zeros_like(previous)
    block_sizes = []

    for inds in sorted(clusters, key=len, reverse=True):
        U = vecs[:, inds]
        m = len(inds)
        best = None
        for subset in itertools.combinations(sorted(remaining), m):
            overlap = np.linalg.norm(
                U.T @ previous[:, subset], "fro"
            ) ** 2
            if best is None or overlap > best[0]:
                best = (overlap, subset)
        labels = sorted(best[1])

        if m == 1:
            label = labels[0]
            v = U[:, 0].copy()
            if previous[:, label] @ v < 0:
                v *= -1
            out[:, label] = v
        else:
            out[:, labels] = _closest_basis_in_subspace(
                U, previous[:, labels]
            )

        for label in labels:
            remaining.remove(label)
        block_sizes.append(m)

    return out, block_sizes


def _global_guard_update(previous, vals, vecs, threshold):
    """If any eigengap is bad, freeze the entire frame."""
    if np.min(np.abs(np.diff(vals))) < threshold:
        return previous.copy(), True
    out, _ = _match_frame(previous, vals, vecs)
    return out, False


def _generator():
    K = np.zeros((6, 6))
    for i, j, a in [
        (0, 2, .18),
        (1, 3, -.16),
        (2, 3, .12),
        (4, 5, 1.20),
    ]:
        K[i, j] = a
        K[j, i] = -a
    return K


@lru_cache(maxsize=None)
def _base_frames(steps, total_rotation):
    K = _generator()
    return tuple(
        expm(total_rotation * (t / (steps - 1)) * K)
        for t in range(steps)
    )


def _rotation01(phi):
    R = np.eye(6)
    c, s = math.cos(phi), math.sin(phi)
    R[0, 0] = c
    R[0, 1] = -s
    R[1, 0] = s
    R[1, 1] = c
    return R


def crossing_world(
    seed,
    steps=201,
    noise=0.025,
    total_rotation=2.0,
    cross_amplitude=0.18,
):
    rng = np.random.default_rng(seed)
    bases = _base_frames(steps, total_rotation)
    true_frames, observations = [], []

    for t in range(steps):
        u = (t - (steps - 1) / 2) / ((steps - 1) / 2)
        vals = np.array([
            .72 + cross_amplitude * u,
            .72 - cross_amplitude * u,
            .35,
            .05,
            -.35,
            -.80,
        ])
        Q = bases[t]
        A = Q @ np.diag(vals) @ Q.T
        E = rng.normal(size=(6, 6))
        E = (E + E.T) / 2
        true_frames.append(Q)
        observations.append(A + noise * E)

    return true_frames, observations


def hidden_gauge_world(
    seed,
    steps=201,
    noise=0.020,
    total_rotation=1.0,
    plateau=(75, 125),
    hidden_turn=math.pi / 2,
):
    """
    During the plateau lambda0 == lambda1 exactly. We secretly rotate the
    semantic axes inside that degenerate 2-D subspace. The observed operator
    is invariant to that rotation, so no observation-only algorithm can know.
    """
    rng = np.random.default_rng(seed)
    bases = _base_frames(steps, total_rotation)
    true_frames, observations, plateau_mask = [], [], []
    a, b = plateau

    for t in range(steps):
        base = bases[t]
        if t < a:
            phi = 0.0
            pair = np.array([.80, .64])
            inside = False
        elif t <= b:
            frac = (t - a) / max(1, b - a)
            phi = hidden_turn * frac
            pair = np.array([.72, .72])
            inside = True
        else:
            phi = hidden_turn
            pair = np.array([.80, .64])
            inside = False

        Qsemantic = base @ _rotation01(phi)
        vals = np.array([
            pair[0],
            pair[1],
            .35,
            .05,
            -.35,
            -.80,
        ])
        A = Qsemantic @ np.diag(vals) @ Qsemantic.T
        E = rng.normal(size=(6, 6))
        E = (E + E.T) / 2

        true_frames.append(Qsemantic)
        observations.append(A + noise * E)
        plateau_mask.append(inside)

    return (
        true_frames,
        observations,
        np.array(plateau_mask, dtype=bool),
    )


def run_tracker(true_frames, observations, threshold):
    vals0, vecs0 = _eigh_desc(observations[0])
    hungarian, _ = _match_frame(true_frames[0], vals0, vecs0)
    blocks = hungarian.copy()
    guard = hungarian.copy()

    traces = {
        k: []
        for k in [
            "sorted",
            "hungarian",
            "global_guard",
            "adaptive_blocks",
        ]
    }
    ambiguous = []

    for t, (truth, A) in enumerate(
        zip(true_frames, observations)
    ):
        vals, vecs = _eigh_desc(A)

        if t:
            hungarian, _ = _match_frame(hungarian, vals, vecs)
            blocks, block_sizes = _adaptive_block_update(
                blocks, vals, vecs, threshold
            )
            guard, _ = _global_guard_update(
                guard, vals, vecs, threshold
            )
        else:
            block_sizes = [1] * len(vals)

        traces["sorted"].append(_score(truth, vecs))
        traces["hungarian"].append(_score(truth, hungarian))
        traces["global_guard"].append(_score(truth, guard))
        traces["adaptive_blocks"].append(_score(truth, blocks))
        ambiguous.append(max(block_sizes) > 1)

    return (
        {k: np.asarray(v) for k, v in traces.items()},
        np.asarray(ambiguous),
    )


def summarize_crossing(seeds, threshold):
    keys = [
        "sorted",
        "hungarian",
        "global_guard",
        "adaptive_blocks",
    ]
    bucket = {k: [] for k in keys}
    worst = {k: [] for k in keys}
    ambiguous_fraction = []

    for seed in seeds:
        truth, obs = crossing_world(seed)
        traces, amb = run_tracker(truth, obs, threshold)
        ambiguous_fraction.append(np.mean(amb))

        for k in keys:
            bucket[k].append(np.mean(traces[k]))
            worst[k].append(np.min(traces[k]))

    return {
        "threshold": threshold,
        "mean_fidelity": {
            k: {
                "mean": float(np.mean(bucket[k])),
                "std": float(np.std(bucket[k])),
            }
            for k in keys
        },
        "mean_worst_step": {
            k: float(np.mean(worst[k])) for k in keys
        },
        "ambiguous_fraction": float(
            np.mean(ambiguous_fraction)
        ),
    }


def threshold_sweep(seeds):
    rows = []
    for tau in [
        0.06,
        0.08,
        0.10,
        0.12,
        0.14,
        0.16,
        0.18,
        0.20,
    ]:
        s = summarize_crossing(seeds, tau)
        rows.append({
            "threshold": tau,
            "hungarian": s["mean_fidelity"]["hungarian"]["mean"],
            "global_guard": s["mean_fidelity"]["global_guard"]["mean"],
            "adaptive_blocks": s["mean_fidelity"][
                "adaptive_blocks"
            ]["mean"],
            "ambiguous_fraction": s["ambiguous_fraction"],
        })
    return rows


def hidden_gauge_attack(seeds, threshold=0.16):
    methods = [
        "hungarian",
        "global_guard",
        "adaptive_blocks",
    ]
    overall = {k: [] for k in methods}
    inside = {k: [] for k in methods}
    after = {k: [] for k in methods}

    for seed in seeds:
        truth, obs, mask = hidden_gauge_world(seed)
        traces, _ = run_tracker(truth, obs, threshold)
        post = np.arange(len(mask)) > np.where(mask)[0][-1]

        for k in methods:
            overall[k].append(np.mean(traces[k]))
            inside[k].append(np.mean(traces[k][mask]))
            after[k].append(np.mean(traces[k][post]))

    return {
        k: {
            "overall": float(np.mean(overall[k])),
            "inside_unobservable_plateau": float(
                np.mean(inside[k])
            ),
            "after_reopening": float(np.mean(after[k])),
        }
        for k in methods
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=50)
    p.add_argument("--threshold", type=float, default=0.16)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    seeds = range(args.seeds)
    result = {
        "crossing": summarize_crossing(
            seeds, args.threshold
        ),
        "threshold_sweep": threshold_sweep(seeds),
        "hidden_gauge_attack": hidden_gauge_attack(
            seeds, args.threshold
        ),
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    c = result["crossing"]
    print("HUNT0 — adaptive ambiguity blocks")
    print(
        f"seeds={args.seeds} "
        f"threshold={args.threshold:.3f}"
    )
    print("\nCrossing world: mean semantic-axis fidelity")
    for k, v in c["mean_fidelity"].items():
        print(
            f"  {k:16s} "
            f"{v['mean']:.6f} ± {v['std']:.6f}"
        )
    print(
        f"  ambiguity active "
        f"{100*c['ambiguous_fraction']:.1f}% of steps"
    )

    print("\nThreshold sweep")
    for row in result["threshold_sweep"]:
        print(
            f"  tau={row['threshold']:.2f} "
            f"hung={row['hungarian']:.4f} "
            f"guard={row['global_guard']:.4f} "
            f"blocks={row['adaptive_blocks']:.4f}"
        )

    print(
        "\nHidden-gauge attack "
        "(exact degeneracy + invisible semantic rotation)"
    )
    for k, v in result["hidden_gauge_attack"].items():
        print(
            f"  {k:16s} "
            f"overall={v['overall']:.4f} "
            f"inside={v['inside_unobservable_plateau']:.4f} "
            f"after={v['after_reopening']:.4f}"
        )


if __name__ == "__main__":
    main()
