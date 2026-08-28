# HUNT1 — Self-Calibrating Eigengap Threshold

## Problem

HUNT0 required a hand-chosen ambiguity threshold.

The correct threshold should scale with current estimator uncertainty.

## Split-half trick

Make two independent estimates:

```math
A_1=A+E_1, \qquad A_2=A+E_2.
```

Track their average:

```math
\bar A=\frac{A_1+A_2}{2}.
```

For independent centered Gaussian errors with the same covariance,

```math
\frac{E_1+E_2}{2}
\stackrel{d}{=}
\frac{E_1-E_2}{2}
```

at the covariance level.

Therefore

```math
\hat\epsilon=
\left\|\frac{A_1-A_2}{2}\right\|_2
```

is a plug-in perturbation-scale estimate.

First tested rule:

```math
\text{ambiguity threshold}=2\hat\epsilon.
```

## Receipt

3 seeds. The oracle may sweep a fixed threshold separately at each noise level.

| matrix-noise scale | adaptive | oracle fixed | oracle tau | fixed .16 | fixed .28 |
|---:|---:|---:|---:|---:|---:|
| .005 | .999402 | .999867 | .24 | .999750 | .999799 |
| .010 | .998136 | .999490 | .24 | .999101 | .999489 |
| .020 | .995415 | .998084 | .28 | .997458 | .998084 |
| .040 | .989980 | .992846 | .34 | .944250 | .992066 |
| .080 | .972547 | .976090 | .44 | .576521 | .616420 |

## What survived

One fixed eigengap threshold is brittle across changing estimator noise.

The split-half rule automatically grows ambiguity blocks as uncertainty increases and stays close to the per-noise oracle in this toy world.

## Why factor 2?

Currently a conservative heuristic, not a theorem.

The motivation is Weyl/Davis-Kahan scale logic: once two empirical eigenvalues are separated by only a few perturbation radii, their individual vectors/order are not trustworthy enough to deserve separate semantic identities.

Next job: replace the constant by a declared confidence statement for the actual operator estimator.

## Attacks needed

- non-Gaussian and heteroskedastic matrix noise;
- dependent split halves;
- bootstrap/jackknife perturbation estimates;
- actual covariance and lag-covariance estimators;
- compare to SHEM and formal flag-type model selection;
- large sparse operators where norm/gaps must themselves be sketched.
