import argparse
import json
import math

import numpy as np

import hunt0_adaptive_flag as h0


def joint_hidden_world(
    seed,
    steps=201,
    noise=0.020,
    total_rotation=1.0,
    plateau=(75, 125),
    hidden_turn=math.pi / 2,
):
    """
    Operator 0 becomes exactly degenerate for semantic modes 0/1.
    Operators 1/2 remain nondegenerate and share the same semantic frame.

    Therefore the internal rotation is unobservable from operator 0 alone
    but observable from the joint commuting family.
    """
    rng = np.random.default_rng(seed)
    bases = h0._base_frames(steps, total_rotation)
    truth, halves, mask = [], [], []
    a, b = plateau

    for t in range(steps):
        base = bases[t]

        if t < a:
            phi = 0.0
            pair0 = [.80, .64]
            inside = False
        elif t <= b:
            frac = (t - a) / max(1, b - a)
            phi = hidden_turn * frac
            pair0 = [.72, .72]
            inside = True
        else:
            phi = hidden_turn
            pair0 = [.80, .64]
            inside = False

        Q = base @ h0._rotation01(phi)

        # Rows are semantic modes, columns are jointly diagonalizable
        # operators. Operator 0 loses the distinction on the plateau.
        # Operators 1 and 2 retain distinct signatures.
        signatures = np.array([
            [pair0[0], .45, .10],
            [pair0[1], -.20, .60],
            [.35, .15, -.40],
            [.05, -.55, .25],
            [-.35, .70, -.15],
            [-.80, -.35, -.65],
        ])

        scale = noise * np.sqrt(2.0)
        first, second = [], []

        for k in range(signatures.shape[1]):
            A = Q @ np.diag(signatures[:, k]) @ Q.T

            E1 = rng.normal(size=(6, 6))
            E2 = rng.normal(size=(6, 6))
            E1 = (E1 + E1.T) / 2
            E2 = (E2 + E2.T) / 2

            first.append(A + scale * E1)
            second.append(A + scale * E2)

        truth.append(Q)
        halves.append((first, second))
        mask.append(inside)

    return truth, halves, np.array(mask, dtype=bool)


def _projection_bank(nproj, seed):
    rng = np.random.default_rng(seed)
    alpha = rng.normal(size=(nproj, 3))
    alpha /= np.linalg.norm(
        alpha,
        axis=1,
        keepdims=True,
    )
    return alpha


def _best_projection(first, second, bank):
    best = None

    for alpha in bank:
        B1 = sum(
            alpha[k] * first[k]
            for k in range(len(alpha))
        )
        B2 = sum(
            alpha[k] * second[k]
            for k in range(len(alpha))
        )
        B = (B1 + B2) / 2

        vals, vecs = h0._eigh_desc(B)
        radius = np.linalg.norm(
            (B1 - B2) / 2,
            2,
        )

        # Select a random projection whose weakest observed eigengap
        # is largest relative to its split-half perturbation scale.
        margin = np.min(
            np.abs(np.diff(vals))
        ) / (2 * radius + 1e-12)

        if best is None or margin > best[0]:
            best = (margin, vals, vecs)

    return best


def run(world, nproj=16, bank_seed=1234):
    truth, halves, mask = world
    bank = _projection_bank(nproj, bank_seed)

    single = None
    joint = None
    single_scores = []
    joint_scores = []
    margins = []

    for t, (Q, pair) in enumerate(
        zip(truth, halves)
    ):
        first, second = pair

        # One-operator candidate from HUNT0/HUNT1.
        A = (first[0] + second[0]) / 2
        vals0, vecs0 = h0._eigh_desc(A)
        radius0 = np.linalg.norm(
            (first[0] - second[0]) / 2,
            2,
        )

        if t == 0:
            single, _ = h0._match_frame(
                Q, vals0, vecs0
            )
        else:
            single, _ = h0._adaptive_block_update(
                single,
                vals0,
                vecs0,
                2 * radius0,
            )

        single_scores.append(
            h0._score(Q, single)
        )

        # Randomized joint-diagonalization attacker.
        margin, vals, vecs = _best_projection(
            first,
            second,
            bank,
        )

        if t == 0:
            joint, _ = h0._match_frame(
                Q, vals, vecs
            )
        else:
            joint, _ = h0._match_frame(
                joint, vals, vecs
            )

        joint_scores.append(
            h0._score(Q, joint)
        )
        margins.append(margin)

    single_scores = np.asarray(single_scores)
    joint_scores = np.asarray(joint_scores)

    post = (
        np.arange(len(mask))
        > np.where(mask)[0][-1]
    )

    return {
        "single": {
            "overall": float(
                np.mean(single_scores)
            ),
            "inside": float(
                np.mean(single_scores[mask])
            ),
            "after": float(
                np.mean(single_scores[post])
            ),
        },
        "joint": {
            "overall": float(
                np.mean(joint_scores)
            ),
            "inside": float(
                np.mean(joint_scores[mask])
            ),
            "after": float(
                np.mean(joint_scores[post])
            ),
            "mean_margin": float(
                np.mean(margins)
            ),
        },
    }


def evaluate(seeds, projections):
    rows = []

    for nproj in projections:
        receipts = [
            run(
                joint_hidden_world(seed),
                nproj=nproj,
                bank_seed=1000 + seed,
            )
            for seed in seeds
        ]

        row = {"projections": nproj}
        for method in ["single", "joint"]:
            for region in [
                "overall",
                "inside",
                "after",
            ]:
                row[
                    f"{method}_{region}"
                ] = float(np.mean([
                    r[method][region]
                    for r in receipts
                ]))
        rows.append(row)

    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--seeds",
        type=int,
        default=30,
    )
    p.add_argument(
        "--json",
        action="store_true",
    )
    args = p.parse_args()

    rows = evaluate(
        range(args.seeds),
        [4, 8, 16, 32],
    )

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(
        "HUNT3 — ambiguity is "
        "operator-family relative"
    )
    print(f"seeds={args.seeds}")
    print(
        "proj  single-overall single-inside "
        "single-after  joint-overall "
        "joint-inside joint-after"
    )

    for r in rows:
        print(
            f"{r['projections']:4d}  "
            f"{r['single_overall']:.6f}       "
            f"{r['single_inside']:.6f}      "
            f"{r['single_after']:.6f}      "
            f"{r['joint_overall']:.6f}     "
            f"{r['joint_inside']:.6f}    "
            f"{r['joint_after']:.6f}"
        )


if __name__ == "__main__":
    main()
