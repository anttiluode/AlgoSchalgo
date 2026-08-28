import argparse
import json

import numpy as np

import hunt0_adaptive_flag as h0


NOISE_LEVELS = [0.005, 0.01, 0.02, 0.04, 0.08]
FIXED_THRESHOLDS = [0.08, 0.12, 0.16, 0.20, 0.28]
ORACLE_GRID = np.linspace(0.04, 0.50, 24)


def split_estimate_world(
    seed,
    noise,
    steps=201,
    total_rotation=2.0,
    cross_amplitude=0.18,
):
    rng = np.random.default_rng(seed)
    bases = h0._base_frames(steps, total_rotation)
    truth, prepared = [], []

    for t in range(steps):
        u = (t - (steps - 1) / 2) / ((steps - 1) / 2)
        latent_vals = np.array([
            .72 + cross_amplitude * u,
            .72 - cross_amplitude * u,
            .35,
            .05,
            -.35,
            -.80,
        ])
        Q = bases[t]
        A = Q @ np.diag(latent_vals) @ Q.T

        # Each half is noisier by sqrt(2), so averaging restores
        # the requested noise scale.
        scale = noise * np.sqrt(2.0)
        E1 = rng.normal(size=(6, 6))
        E2 = rng.normal(size=(6, 6))
        E1 = (E1 + E1.T) / 2
        E2 = (E2 + E2.T) / 2

        A1 = A + scale * E1
        A2 = A + scale * E2
        Abar = (A1 + A2) / 2
        vals, vecs = h0._eigh_desc(Abar)

        # For independent centered Gaussian half-errors:
        #   (E1 + E2)/2 and (E1 - E2)/2
        # have the same covariance. This is an observable proxy
        # for the perturbation scale of Abar.
        radius = np.linalg.norm((A1 - A2) / 2, 2)

        truth.append(Q)
        prepared.append((vals, vecs, radius))

    return truth, prepared


def run_prepared(
    truth,
    prepared,
    multiplier=2.0,
    fixed_threshold=None,
):
    vals0, vecs0, _ = prepared[0]
    frame, _ = h0._match_frame(truth[0], vals0, vecs0)

    scores = []
    thresholds = []

    for t, (Q, item) in enumerate(zip(truth, prepared)):
        vals, vecs, radius = item
        tau = (
            float(fixed_threshold)
            if fixed_threshold is not None
            else multiplier * radius
        )

        if t:
            frame, _ = h0._adaptive_block_update(
                frame,
                vals,
                vecs,
                tau,
            )

        scores.append(h0._score(Q, frame))
        thresholds.append(tau)

    return (
        float(np.mean(scores)),
        float(np.mean(thresholds)),
    )


def evaluate(seeds, multiplier=2.0):
    rows = []

    for noise in NOISE_LEVELS:
        worlds = [
            split_estimate_world(seed, noise)
            for seed in seeds
        ]

        adaptive_scores = [
            run_prepared(
                *world,
                multiplier=multiplier,
            )[0]
            for world in worlds
        ]

        fixed_scores = {}
        for tau in FIXED_THRESHOLDS:
            fixed_scores[tau] = float(np.mean([
                run_prepared(
                    *world,
                    fixed_threshold=tau,
                )[0]
                for world in worlds
            ]))

        oracle_best = (-np.inf, None)
        for tau in ORACLE_GRID:
            score = float(np.mean([
                run_prepared(
                    *world,
                    fixed_threshold=float(tau),
                )[0]
                for world in worlds
            ]))
            if score > oracle_best[0]:
                oracle_best = (score, float(tau))

        _, mean_tau = run_prepared(
            *worlds[0],
            multiplier=multiplier,
        )

        rows.append({
            "noise": noise,
            "adaptive": float(np.mean(adaptive_scores)),
            "adaptive_std": float(
                np.std(adaptive_scores)
            ),
            "mean_adaptive_threshold_seed0": mean_tau,
            "fixed": {
                str(k): v
                for k, v in fixed_scores.items()
            },
            "oracle_fixed": {
                "fidelity": oracle_best[0],
                "threshold": oracle_best[1],
            },
        })

    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--multiplier", type=float, default=2.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    rows = evaluate(
        range(args.seeds),
        args.multiplier,
    )

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print("HUNT1 — self-calibrating eigengap threshold")
    print(
        f"seeds={args.seeds} "
        f"multiplier={args.multiplier:.2f}"
    )
    print(
        "noise    adaptive    oracle-fixed   "
        "oracle-tau   fixed(.16) fixed(.28)"
    )

    for r in rows:
        print(
            f"{r['noise']:5.3f}    "
            f"{r['adaptive']:.6f}    "
            f"{r['oracle_fixed']['fidelity']:.6f}      "
            f"{r['oracle_fixed']['threshold']:.3f}       "
            f"{r['fixed']['0.16']:.6f}   "
            f"{r['fixed']['0.28']:.6f}"
        )


if __name__ == "__main__":
    main()
