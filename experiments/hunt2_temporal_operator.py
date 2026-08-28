import argparse
import json

import numpy as np

import hunt0_adaptive_flag as h0


WINDOWS = [128, 256, 512, 1024]


def ar_segment(rho, n, rng, burn=200):
    d = len(rho)
    s = np.zeros((n + burn, d))
    s[0] = rng.normal(size=d)
    innovation = np.sqrt(
        np.maximum(1.0 - rho ** 2, 1e-8)
    )

    for t in range(1, n + burn):
        s[t] = (
            rho * s[t - 1]
            + innovation * rng.normal(size=d)
        )

    return s[burn:]


def lag_operator(X, lag=1, ridge=1e-6):
    X = X - X.mean(axis=0, keepdims=True)
    X0 = X[:-lag]
    X1 = X[lag:]

    C0 = (
        X0.T @ X0 + X1.T @ X1
    ) / (2 * len(X0))

    Ct = (X1.T @ X0) / len(X0)
    Ct = (Ct + Ct.T) / 2

    vals, vecs = np.linalg.eigh(C0)
    vals = np.maximum(vals, ridge)
    invsqrt = (
        vecs
        @ np.diag(vals ** -0.5)
        @ vecs.T
    )

    L = invsqrt @ Ct @ invsqrt
    return (L + L.T) / 2


def temporal_world(
    seed,
    half_window=512,
    steps=161,
    total_rotation=1.5,
    cross_amplitude=0.18,
):
    rng = np.random.default_rng(seed)
    bases = h0._base_frames(
        steps, total_rotation
    )

    truth = []
    prepared = []

    for t in range(steps):
        u = (
            t - (steps - 1) / 2
        ) / ((steps - 1) / 2)

        rho = np.array([
            .72 + cross_amplitude * u,
            .72 - cross_amplitude * u,
            .35,
            .05,
            -.35,
            -.78,
        ])

        Q = bases[t]

        # Two independent finite windows from the
        # same current temporal law.
        S1 = ar_segment(
            rho, half_window, rng
        )
        S2 = ar_segment(
            rho, half_window, rng
        )

        X1 = S1 @ Q.T
        X2 = S2 @ Q.T

        L1 = lag_operator(X1)
        L2 = lag_operator(X2)

        Lbar = (L1 + L2) / 2
        vals, vecs = h0._eigh_desc(Lbar)

        radius = np.linalg.norm(
            (L1 - L2) / 2,
            2,
        )

        truth.append(Q)
        prepared.append(
            (vals, vecs, radius)
        )

    return truth, prepared


def run_methods(world, multiplier=2.0):
    truth, prepared = world

    vals0, vecs0, _ = prepared[0]
    hungarian, _ = h0._match_frame(
        truth[0], vals0, vecs0
    )
    global_guard = hungarian.copy()
    blocks = hungarian.copy()

    scores = {
        "hungarian": [],
        "global_guard": [],
        "adaptive_blocks": [],
    }
    thresholds = []

    for t, (Q, item) in enumerate(
        zip(truth, prepared)
    ):
        vals, vecs, radius = item
        tau = multiplier * radius

        if t:
            hungarian, _ = h0._match_frame(
                hungarian,
                vals,
                vecs,
            )
            global_guard, _ = (
                h0._global_guard_update(
                    global_guard,
                    vals,
                    vecs,
                    tau,
                )
            )
            blocks, _ = (
                h0._adaptive_block_update(
                    blocks,
                    vals,
                    vecs,
                    tau,
                )
            )

        scores["hungarian"].append(
            h0._score(Q, hungarian)
        )
        scores["global_guard"].append(
            h0._score(Q, global_guard)
        )
        scores["adaptive_blocks"].append(
            h0._score(Q, blocks)
        )
        thresholds.append(tau)

    result = {
        key: float(np.mean(value))
        for key, value in scores.items()
    }
    result["mean_threshold"] = float(
        np.mean(thresholds)
    )
    return result


def evaluate(seeds, multiplier=2.0):
    rows = []

    for n in WINDOWS:
        results = [
            run_methods(
                temporal_world(
                    seed,
                    half_window=n,
                ),
                multiplier=multiplier,
            )
            for seed in seeds
        ]

        rows.append({
            "half_window": n,
            "hungarian": float(np.mean([
                r["hungarian"]
                for r in results
            ])),
            "global_guard": float(np.mean([
                r["global_guard"]
                for r in results
            ])),
            "adaptive_blocks": float(
                np.mean([
                    r["adaptive_blocks"]
                    for r in results
                ])
            ),
            "mean_threshold": float(np.mean([
                r["mean_threshold"]
                for r in results
            ])),
        })

    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--seeds",
        type=int,
        default=10,
    )
    p.add_argument(
        "--multiplier",
        type=float,
        default=2.0,
    )
    p.add_argument(
        "--json",
        action="store_true",
    )
    args = p.parse_args()

    rows = evaluate(
        range(args.seeds),
        args.multiplier,
    )

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(
        "HUNT2 — finite-window "
        "temporal operators"
    )
    print(
        f"seeds={args.seeds} "
        f"multiplier={args.multiplier:.2f}"
    )
    print(
        "halfN   hungarian   "
        "global-guard   adaptive-blocks   "
        "mean-tau"
    )

    for row in rows:
        print(
            f"{row['half_window']:5d}   "
            f"{row['hungarian']:.6f}    "
            f"{row['global_guard']:.6f}       "
            f"{row['adaptive_blocks']:.6f}          "
            f"{row['mean_threshold']:.4f}"
        )


if __name__ == "__main__":
    main()
