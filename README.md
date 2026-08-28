# AlgoSchalgo

**Algorithm hunt. Mathematics first. Useful if it survives.**

This repository is deliberately not another architecture diary. The rule is:

> Find a mathematical seam, turn it into the smallest executable algorithm, attack it with boring methods, and keep the residue.

No novelty is assumed. If an old numerical-linear-algebra method already solves the problem, that method wins.

## HUNT0 — adaptive ambiguity blocks

The first hunt starts from a standard fact with a useful systems consequence:

> When eigenvalues become nearly degenerate, individual eigenvectors become ill-conditioned before the invariant subspace does.

A tracker that insists on naming every eigenvector independently can therefore destroy identity precisely where the mathematics says the vector is not identifiable.

Candidate rule:

```text
well-separated mode
    -> track the vector normally

near-degenerate cluster
    -> stop pretending its internal axes are observable
    -> track the whole cluster subspace
    -> carry the previous semantic basis through that subspace
       with an orthogonal Procrustes lift

other well-separated modes
    -> continue updating normally
```

This is an adaptive partial-flag interpretation: the granularity of the tracked object changes with spectral multiplicity.

### Crossing receipt

Six moving modes, one noisy crossing pair, and another well-separated pair deliberately rotating quickly so that "freeze the entire frame" is attacked.

50 seeds, threshold 0.16:

| tracker | mean semantic-axis fidelity |
|---|---:|
| sorted eigenvectors | 0.8484 ± 0.0027 |
| Hungarian overlap tracking | 0.9148 ± 0.0641 |
| global eigengap guard | 0.9447 ± 0.0545 |
| **adaptive ambiguity blocks** | **0.9953 ± 0.0014** |

The adaptive block was active about 45% of the trajectory.

The useful difference appears when the ambiguity threshold is intentionally widened:

| gap threshold | overlap | global freeze | adaptive blocks |
|---:|---:|---:|---:|
| 0.12 | 0.9148 | 0.9888 | 0.9910 |
| 0.14 | 0.9148 | 0.9756 | 0.9950 |
| 0.16 | 0.9148 | 0.9447 | 0.9953 |
| 0.18 | 0.9148 | 0.8967 | 0.9955 |
| 0.20 | 0.9148 | 0.8764 | 0.9960 |

A global guard throws away healthy information because one pair is ambiguous. The block tracker only suspends the degrees of freedom that are actually ill-conditioned.

Run:

```bash
python experiments/hunt0_adaptive_flag.py
```

See [results/HUNT0.md](results/HUNT0.md).

## HUNT1 — let the data choose the gap threshold

HUNT0 still cheated slightly: its ambiguity threshold was hand supplied.

HUNT1 removes that knob with a split-half perturbation estimate.

Let two independent half-window estimates be

```math
A_1=A+E_1, \qquad A_2=A+E_2.
```

For independent centered Gaussian estimation errors,

```math
\frac{E_1+E_2}{2}
\quad\text{and}\quad
\frac{E_1-E_2}{2}
```

have the same covariance.

The averaged operator is

```math
\bar A=\frac{A_1+A_2}{2},
```

so

```math
\hat\epsilon=
\left\|\frac{A_1-A_2}{2}\right\|_2
```

is an observable proxy for the perturbation scale affecting the averaged operator.

First rule tested:

```math
\text{merge adjacent modes if }
|\hat\lambda_i-\hat\lambda_j|
\le 2\hat\epsilon.
```

The factor 2 is not claimed optimal. It is a conservative perturbation-scale heuristic.

First receipt, 3 seeds:

| noise | self-calibrated | oracle fixed threshold | best oracle tau | fixed tau=.16 | fixed tau=.28 |
|---:|---:|---:|---:|---:|---:|
| .005 | .99940 | .99987 | .24 | .99975 | .99980 |
| .010 | .99814 | .99949 | .24 | .99910 | .99949 |
| .020 | .99542 | .99808 | .28 | .99746 | .99808 |
| .040 | .98998 | .99285 | .34 | .94425 | .99207 |
| .080 | .97255 | .97609 | .44 | .57652 | .61642 |

A fixed threshold is excellent only in the noise regime for which it happens to be suitable. The split-half rule tracks the required threshold automatically and stays close to an oracle allowed to retune separately at every noise level.

Run:

```bash
python experiments/hunt1_self_calibrating_gap.py --seeds 3
```

See [results/HUNT1.md](results/HUNT1.md).

## HUNT2 — replace matrix noise with actual temporal estimation

HUNT0/HUNT1 might still have been artifacts of adding friendly symmetric noise directly to a matrix.

HUNT2 removes that shortcut.

Six independent AR(1) sources are hidden by a moving orthogonal frame. Two source autocorrelations cross. For each current state, two finite windows produce whitened, symmetrized lag operators of the AMUSE/second-order-BSS form:

```math
L=C_0^{-1/2}\frac{C_1+C_1^T}{2}C_0^{-1/2}.
```

The same split-half disagreement chooses the ambiguity threshold.

Five-seed receipt:

| samples per half | overlap tracker | global guard | adaptive blocks | mean adaptive tau |
|---:|---:|---:|---:|---:|
| 128 | .87550 | .86589 | **.98468** | .3260 |
| 256 | .88664 | .92188 | **.98929** | .2287 |
| 512 | .89897 | .99078 | **.99549** | .1612 |
| 1024 | .93108 | .99476 | **.99699** | .1139 |

So the result survives finite-window temporal estimation.

The pleasing part is the scaling: shorter/noisier windows disagree more, which automatically grows the ambiguity blocks. As sample count rises, split-half disagreement shrinks and individual axes are released again.

```text
more estimator uncertainty
        -> coarser identifiable object

more data
        -> smaller uncertainty
        -> finer flag / more individual axes
```

Run:

```bash
python experiments/hunt2_temporal_operator.py --seeds 5
```

See [results/HUNT2.md](results/HUNT2.md).

## The important failure

HUNT0 also contains an exact-degeneracy attack.

During an interval where two eigenvalues are exactly equal, the experiment secretly rotates the semantic axes inside that 2-D eigenspace.

The observed symmetric operator is invariant to that hidden internal rotation.

Therefore no observation-only tracker can know it happened.

The adaptive-block method correctly refuses to invent information, but semantic fidelity drops. When the gap reopens, statistics can identify axes again, while the semantic permutation/orientation may still require external task consequence.

This is the boundary:

> **A stable subspace does not identify a privileged basis inside an exactly degenerate block.**

## Why flags showed up

For a real symmetric matrix, eigenspaces form mutually orthogonal blocks whose dimensions are the eigenvalue multiplicities. That is naturally a flag-manifold object.

This hunt did not invent that geometry. Recent work makes the connection explicit:

- Szwagier & Pennec, *Nested Subspace Learning with Flags*, JMLR 2026.
- Jin & Coulson, *Online Subspace Learning on Flag Manifolds for System Identification*, L4DC 2026.
- Classical Davis–Kahan perturbation theory explains why clustered eigenspaces can remain stable while individual vectors become ill-conditioned.

What may be useful is the operational synthesis:

```text
estimate current perturbation scale
        ↓
infer which spectral distinctions are currently trustworthy
        ↓
change ambiguity blocks accordingly
        ↓
update only identifiable degrees of freedom
        ↓
preserve old internal orientation where the data cannot re-estimate it
```

Novelty is currently **unclaimed**.

## Next attacks

1. Replace independent finite windows with contiguous halves from one continuous nonstationary stream.
2. Compare one-lag AMUSE-style tracking against multi-lag SOBI / joint diagonalization.
3. Compare against Kato/projector parallel transport and proper manifold trackers.
4. Replace the Gaussian split-half assumption with bootstrap / robust perturbation estimates.
5. Let ambiguity blocks merge and split repeatedly in rank 32–256 streams.
6. Add a tiny task-consequence budget only at block-split events and measure calibration cost.

See [PAPERS.md](PAPERS.md).

## Install

```bash
pip install -r requirements.txt
```

Python 3.10+.

## Status

**GO, but narrow.**

Current positive result:

> A spectral tracker can become substantially more robust by changing the granularity of what it claims to identify, locally and online, according to the relationship between spectral gaps and current estimation uncertainty.
