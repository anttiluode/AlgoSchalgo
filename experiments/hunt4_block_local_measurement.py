import argparse
import json
import math
import numpy as np

def rotation(theta):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=float)

def eig_desc(A):
    vals, vecs = np.linalg.eigh(A)
    order = np.argsort(vals)[::-1]
    return vals[order], vecs[:, order]

def basis_fidelity(true_basis, est_basis):
    corr = np.abs(true_basis.T @ est_basis)
    direct = (corr[0, 0] + corr[1, 1]) / 2
    swapped = (corr[0, 1] + corr[1, 0]) / 2
    return float(max(direct, swapped))

def split_margin(A1, A2):
    Abar = (A1 + A2) / 2
    vals, vecs = eig_desc(Abar)
    gap = abs(vals[0] - vals[1])
    radius = np.linalg.norm((A1 - A2) / 2, 2)
    return gap / (2 * radius + 1e-12), vecs

def make_block_halves(rng, Q, block_index, K, delta, noise, shared_view=False):
    first, second = [], []
    target = 0 if shared_view else block_index
    for k in range(K):
        split = delta if k == target else 0.0
        signal = Q @ np.diag([split, -split]) @ Q.T
        scale = noise * math.sqrt(2.0)
        E1 = rng.normal(size=(2, 2))
        E2 = rng.normal(size=(2, 2))
        E1 = (E1 + E1.T) / 2
        E2 = (E2 + E2.T) / 2
        first.append(signal + scale * E1)
        second.append(signal + scale * E2)
    return first, second, target

def combine(operators, alpha):
    out = np.zeros_like(operators[0])
    for a, op in zip(alpha, operators):
        out += a * op
    return out

def run_world(seed, K, steps=200, delta=0.12, noise=0.06,
              evidence_decay=0.95, warmup=30, shared_view=False):
    rng = np.random.default_rng(seed)
    if shared_view:
        global_alpha = np.zeros(K)
        global_alpha[0] = 1.0
    else:
        global_alpha = np.ones(K) / math.sqrt(K)

    evidence = np.zeros((K, K))
    gm, lm, gf, lf, correct = [], [], [], [], []

    for t in range(steps):
        frac = t / max(1, steps - 1)
        for p in range(K):
            theta = 0.90 * frac + 0.35 * math.sin(2 * math.pi * frac + 0.40 * p)
            Q = rotation(theta)
            first, second, target = make_block_halves(
                rng, Q, p, K, delta, noise, shared_view=shared_view
            )

            inst = np.zeros(K)
            raw_vecs = []
            for k in range(K):
                margin, vecs = split_margin(first[k], second[k])
                inst[k] = margin
                raw_vecs.append(vecs)

            evidence[p] = evidence_decay * evidence[p] + (1 - evidence_decay) * inst
            local_k = int(np.argmax(evidence[p]))

            B1 = combine(first, global_alpha)
            B2 = combine(second, global_alpha)
            global_margin, global_vecs = split_margin(B1, B2)

            if t >= warmup:
                gm.append(global_margin)
                lm.append(inst[local_k])
                gf.append(basis_fidelity(Q, global_vecs))
                lf.append(basis_fidelity(Q, raw_vecs[local_k]))
                correct.append(local_k == target)

    gm, lm = np.asarray(gm), np.asarray(lm)
    return {
        "blocks": K,
        "global_mean_margin": float(np.mean(gm)),
        "local_mean_margin": float(np.mean(lm)),
        "global_safe_fraction": float(np.mean(gm > 1.0)),
        "local_safe_fraction": float(np.mean(lm > 1.0)),
        "global_fidelity": float(np.mean(gf)),
        "local_fidelity": float(np.mean(lf)),
        "local_choice_accuracy": float(np.mean(correct)),
    }

def theoretical_bound(K, delta=0.12):
    global_gap = 2 * delta / math.sqrt(K)
    local_gap = 2 * delta
    return {
        "global_best_worst_gap": global_gap,
        "local_block_gap": local_gap,
        "local_to_global_ratio": local_gap / global_gap,
    }

def evaluate(seeds):
    rows = []
    for K in [2, 3, 4, 6, 8, 12]:
        receipts = [run_world(seed, K) for seed in seeds]
        row = {"blocks": K}
        for key in [
            "global_mean_margin", "local_mean_margin",
            "global_safe_fraction", "local_safe_fraction",
            "global_fidelity", "local_fidelity", "local_choice_accuracy"
        ]:
            vals = [r[key] for r in receipts]
            row[key] = float(np.mean(vals))
            row[key + "_std"] = float(np.std(vals))
        row.update(theoretical_bound(K))
        rows.append(row)

    controls = [run_world(seed, 8, shared_view=True) for seed in seeds]
    control = {"blocks": 8}
    for key in [
        "global_mean_margin", "local_mean_margin",
        "global_fidelity", "local_fidelity", "local_choice_accuracy"
    ]:
        control[key] = float(np.mean([r[key] for r in controls]))
    return rows, control

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    rows, control = evaluate(range(args.seeds))

    if args.json:
        print(json.dumps({
            "orthogonal_signature_world": rows,
            "shared_view_control": control
        }, indent=2))
        return

    print("HUNT4 — block-local measurement selection")
    print(f"seeds={args.seeds}")
    print("K   global-margin local-margin global-safe local-safe global-fid local-fid local-choice")
    for r in rows:
        print(
            f"{r['blocks']:2d}  "
            f"{r['global_mean_margin']:.5f}       "
            f"{r['local_mean_margin']:.5f}      "
            f"{r['global_safe_fraction']:.5f}    "
            f"{r['local_safe_fraction']:.5f}   "
            f"{r['global_fidelity']:.5f}   "
            f"{r['local_fidelity']:.5f}  "
            f"{r['local_choice_accuracy']:.5f}"
        )

    print("\nAnalytic signal-gap penalty")
    for r in rows:
        print(
            f"K={r['blocks']:2d}: "
            f"global={r['global_best_worst_gap']:.5f}, "
            f"local={r['local_block_gap']:.5f}, "
            f"ratio={r['local_to_global_ratio']:.3f}x"
        )

    print("\nShared-view kill control, K=8")
    for key, value in control.items():
        if key != "blocks":
            print(f"  {key:24s} {value:.6f}")

if __name__ == "__main__":
    main()
