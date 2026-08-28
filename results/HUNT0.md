# HUNT0 — Adaptive Ambiguity Blocks

## Question

When only part of a spectral frame becomes ill-conditioned, should a tracker freeze the entire frame?

Candidate answer: **no**.

Near a spectral collision, merge only unreliable modes into an ambiguity block. Track the block's subspace and transport the old internal basis through it by orthogonal Procrustes. Continue updating every well-separated mode normally.

## World

Six-dimensional real symmetric operator:

- modes 0 and 1 cross;
- additive symmetric estimator noise;
- the full semantic frame moves continuously;
- modes 4 and 5 rotate relatively quickly while staying spectrally well separated.

That final condition attacks "if any gap is bad, freeze everything."

## Baselines

1. raw sorted eigenvectors;
2. Hungarian maximum-overlap vector tracker;
3. global eigengap guard;
4. adaptive ambiguity blocks.

## Receipt

50 seeds, noise 0.025, threshold 0.16:

```text
sorted           0.848384 ± 0.002721
hungarian        0.914801 ± 0.064057
global_guard     0.944724 ± 0.054545
adaptive_blocks  0.995298 ± 0.001432

ambiguity active 45.1% of steps
```

Threshold sweep:

```text
tau=.06  hung=.9148  guard=.9236  blocks=.9207
tau=.08  hung=.9148  guard=.9388  blocks=.9416
tau=.10  hung=.9148  guard=.9657  blocks=.9666
tau=.12  hung=.9148  guard=.9888  blocks=.9910
tau=.14  hung=.9148  guard=.9756  blocks=.9950
tau=.16  hung=.9148  guard=.9447  blocks=.9953
tau=.18  hung=.9148  guard=.8967  blocks=.9955
tau=.20  hung=.9148  guard=.8764  blocks=.9960
```

## Interpretation

As the threshold becomes conservative, the global guard increasingly freezes healthy modes. The adaptive tracker only suspends internal rotations of the cluster whose eigengap is small.

Positive result:

> **Uncertainty should be localized to the spectral degrees of freedom that actually lost identifiability.**

## Kill test — hidden gauge motion

A second world makes modes 0 and 1 exactly degenerate for an interval and secretly rotates the semantic axes inside that 2-D block.

The observation contains zero information about that hidden internal rotation.

Receipt:

```text
hungarian        overall=.9127  inside=.8827  after=.8489
global_guard     overall=.8498  inside=.8723  after=.6871
adaptive_blocks  overall=.8513  inside=.8779  after=.6873
```

The block tracker fails semantically there, as it must.

Boundary:

> After an exact degeneracy, a reopened statistical frame may still require external consequence to decide which recovered axis inherits which old meaning.

## Next attack

Replace direct matrix perturbations with finite-sample lag/covariance estimates from stochastic streams.
