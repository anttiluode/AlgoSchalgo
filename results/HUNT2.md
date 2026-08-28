# HUNT2 — Finite-Window Temporal Operators

## Why this exists

HUNT0/HUNT1 could have been an artifact of adding friendly symmetric noise directly to a matrix.

HUNT2 removes that shortcut.

The observed object is now a finite multivariate time series.

Six independent AR(1) sources have time-varying autocorrelations. Two source autocorrelations cross. A moving orthogonal mixing frame hides the sources.

For each current state, two independent finite windows are generated. Each half produces a whitened symmetrized lag operator:

```math
L =
C_0^{-1/2}
\frac{C_1+C_1^T}{2}
C_0^{-1/2}.
```

This is the AMUSE / second-order-BSS style object. In the population limit its eigenvectors are the source/mixing axes and its eigenvalues encode the lag signatures.

The two finite-window estimates `L1,L2` supply the same split-half perturbation proxy:

```math
\hat\epsilon=
\left\|\frac{L_1-L_2}{2}\right\|_2,
\qquad
\tau=2\hat\epsilon.
```

## Receipt

5 seeds:

| samples per half | overlap tracker | global guard | adaptive blocks | mean adaptive tau |
|---:|---:|---:|---:|---:|
| 128 | .87550 | .86589 | **.98468** | .3260 |
| 256 | .88664 | .92188 | **.98929** | .2287 |
| 512 | .89897 | .99078 | **.99549** | .1612 |
| 1024 | .93108 | .99476 | **.99699** | .1139 |

## What changed

The main HUNT0 result survives finite-sample temporal estimation.

At short windows, estimator uncertainty is large. The self-calibrated rule responds by making larger ambiguity blocks. The global guard then freezes too much of the healthy frame and can become worse than ordinary overlap tracking.

The local block rule keeps following well-conditioned modes and preserves only the unresolved internal orientations.

As sample count grows:

```text
split-half disagreement decreases
        ↓
ambiguity threshold decreases
        ↓
more individual axes become identifiable
        ↓
adaptive blocks shrink naturally
```

That is exactly the behavior wanted from HUNT1.

## What this still does NOT prove

- AMUSE is new;
- the lag operator is the best temporal estimator;
- independent windows are a realistic online protocol;
- the factor 2 is theoretically calibrated;
- this beats SOBI / joint diagonalization;
- semantic labels are recoverable through exact hidden rotations.

## Next attacker

Use one continuous stream and contiguous split halves, then compare:

1. one-lag operator;
2. multi-lag SOBI / joint diagonalization;
3. adaptive block tracking on the joint spectral structure.

The interesting question is whether ambiguity blocks become **smaller** when several lags jointly distinguish sources that collide at one lag.
