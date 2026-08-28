# AlgoSchalgo

https://anttiluode.github.io/AlgoSchalgo/

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

## HUNT3 — ambiguity belongs to the operator family

HUNT0's exact-degeneracy failure was real, but too broadly interpreted.

If several symmetric operators share the same hidden eigenvectors,

```math
A_k=Q\Lambda_kQ^T,
```

then each mode has a vector-valued joint signature across operators. A collision in one operator need not be a collision in the whole family.

A linear combination

```math
B(\alpha)=\sum_k\alpha_k A_k
```

keeps the common eigenvectors while projecting joint signatures to scalar eigenvalues. Random linear combinations are established machinery in randomized joint diagonalization; the experiment therefore treats them as an attacker, not a novelty claim.

HUNT3 adds one small operational wrapper: sample a bank of combinations and choose the one with the largest **split-half-noise-normalized minimum eigengap**.

30 seeds in the HUNT0 hidden-gauge world, but now with three jointly observable operators:

| random projections | single-op overall | single-op after | joint overall | joint inside exact degeneracy | joint after |
|---:|---:|---:|---:|---:|---:|
| 4 | .850781 | .688574 | .899323 | .889041 | .858542 |
| 8 | .850781 | .688574 | .988471 | .990385 | .980643 |
| 16 | .850781 | .688574 | **.996495** | **.996465** | **.996455** |
| 32 | .850781 | .688574 | **.997132** | **.997108** | **.997176** |

So the corrected boundary is:

> **A semantic rotation is unobservable only inside a block that remains degenerate across the entire available operator family.**

That changes the algorithmic policy:

```text
current operator becomes ambiguous
        ↓
do not spend labels/consequence yet
        ↓
search another lag / view / operator combination
for a better-conditioned distinction
        ↓
only if the available family remains ambiguous
declare a true ambiguity block
```

Run:

```bash
python experiments/hunt3_joint_operator_family.py --seeds 30
```

See [results/HUNT3.md](results/HUNT3.md).

## HUNT4 — choose measurements per ambiguity block

HUNT3 still searched for one global observable combination.

HUNT4 asks whether that is itself an unnecessary bottleneck.

Construct a family with K ambiguity blocks and K operators where block p has joint-signature difference

    d_p = 2 delta e_p.

For any one global unit projection alpha,

    worst block gap
      = 2 delta min_p |alpha_p|
      <= 2 delta / sqrt(K).

The balanced projection attains the bound, so this is the strongest possible global max-min attacker.

A block-local view alpha_p=e_p gets gap 2 delta.

Therefore the constructed family has an exact sqrt(K) worst-block signal-gap advantage for local measurement selection.

Noisy 10-seed receipt:

| K | global margin | local margin | global safe | local safe | global fidelity | local fidelity |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1.4184 | **1.8941** | .5774 | **.7776** | .9655 | **.9821** |
| 3 | 1.2263 | **1.9096** | .4780 | **.7767** | .9512 | **.9824** |
| 4 | 1.1454 | **1.9246** | .4346 | **.7765** | .9437 | **.9823** |
| 6 | 1.0356 | **1.9160** | .3694 | **.7674** | .9314 | **.9812** |
| 8 | .9775 | **1.8765** | .3355 | **.7676** | .9249 | **.9817** |
| 12 | .8993 | **1.8972** | .2996 | **.7685** | .9187 | **.9814** |

The local selector is not told which observable belongs to which block. It learns that mapping from a slow EMA of HUNT1 split-half identifiability margins and chooses the intended observable about 99.5–100% of the time after warmup.

Kill control: if all eight blocks really want the same observable, global and local collapse to the same answer (~.982 axis fidelity each).

So HUNT4 earns only:

> **When different unresolved blocks genuinely require different observable directions, forcing one universal measurement incurs a scaling cost.**

Run:

    python experiments/hunt4_block_local_measurement.py --seeds 10

See [results/HUNT4.md](results/HUNT4.md).

## HUNT5 — the ECG loop: observation geometry is causal

HUNT0-HUNT4 used planted synthetic crossings.

HUNT5 takes a pre-existing Perception Laboratory feedback graph that was not designed for AlgoSchalgo and asks whether its strange period-52 "ECG" rhythm is actually organized by observation degeneracy.

Headless reproduction of the supplied five-node loop gives an asymptotic period-52 cycle.

The original observer is only the first four cells of a normalized 16x16 area-downsampled checkerboard.

Two different observation walls occur in the steady cycle:

| square size | feedback | first-4 raw variance | full 16x16 raw variance |
|---:|---:|---:|---:|
| 48 | 1.000000 | .187500 | .249939 |
| 43 | 1.312500 | .166748 | .146172 |
| **84** | **0.000000** | **0.000000** | **.175594** |
| **-12** | **3.157895** | **.009277** | **.005082** |

At q=84 the chosen aperture is blind but the rest of the 16x16 image is still informative.

At q=-12 the whole 16x16 representation is already low contrast and max-normalization amplifies the residual structure.

### Causality test

Keep the controller exactly fixed.

Move only the four-cell readout window along the same 16x16 top row:

| window x | period |
|---:|---:|
| 0 | **52** |
| 1 | 51 |
| 2 | 51 |
| 3 | **1** |
| 4 | **1** |
| 5 | 51 |
| 6 | **2** |
| 7 | 51 |
| 8 | **1** |
| 9 | **1** |
| 10 | 102 |
| 11 | 104 |
| 12 | **2** |

The rhythm is therefore not an invariant of the controller alone.

Stronger intervention: preserve the original observer exactly until its four raw samples become locally indistinguishable. Only then choose another four-cell window at the same 16x16 resolution.

Result:

    original observer  -> period 52
    ambiguity rescue   -> period 1

The rescued loop settles at q=84 with feedback 1.75. No controller parameter changed.

A second intervention repairs only whole-16x16 contrast collapse while deliberately leaving the q=84 local-aperture zero intact:

    original observer       -> period 52
    resolution-only rescue  -> period 51

So both observation failures alter the return map, while the q=84 aperture wall is the decisive kill point in this saved configuration.

### Important correction to HUNT1 intuition

Split-half disagreement is not itself an observability measure.

A deterministic sensor can report the same information-free vector perfectly twice:

    low disagreement != informative observation.

HUNT5 therefore separates:

- estimator uncertainty / repeatability;
- distinction strength / observability.

It also exposes an action-dependent problem: the current vector can remain perfectly healthy until the controller itself jumps into a blind measurement regime.

A one-step warning therefore needs the outgoing action/control or a learned model of how action changes future observer identifiability.

Run:

    python experiments/hunt5_ecg_observer_causality.py

See [results/HUNT5.md](results/HUNT5.md).

## HUNT6 — ProbePulse32: a transparent pulsing recurrent network

HUNT5 suggested a network whose pulse is an information-seeking action rather than an opaque activation.

HUNT6 builds the first one.

The recurrent state has exactly 32 units, but every unit has a declared meaning:

    unit i = P(hidden ring position, hidden direction | observations)

The task contains an exactly aliased free sensor plus four optional local observers. Rare hidden jumps are invisible to the free stream, so no amount of black-box memory can reconstruct them without buying another observation.

ProbePulse32 is fitted only by transition counts, sensor means and residual noise estimates. No gradient descent is used in the pulse machine.

Runtime:

    predict explicit 32-state belief
        ↓
    read free sensor
        ↓
    compute position entropy
        ↓
    ambiguous?
      no -> continue
      yes -> PULSE
              ↓
            score 4 optional sensors by
            posterior hypothesis separation / noise
              ↓
            read best ONE
              ↓
            update belief

First receipt:

| model / policy | exact-state accuracy | optional reads / step |
|---|---:|---:|
| Reservoir32, free sensor | .11805 ± .00087 | 0 |
| GRU32, free sensor | .12013 ± .00228 | 0 |
| ProbePulse32 H=.6 | **.91675** | **.34970** |
| GRU32, all sensors | .90156 ± .00183 | 4.0 |
| ProbePulse32 H=.3 | .95477 | .75754 |
| MoE 4x8, all sensors | **.96734 ± .00070** | 4.0 |
| transparent Bayes, all sensors | .99374 | 4.0 |

So the strongest learned attacker still wins raw accuracy. But ProbePulse32 H=.3 gives up about 1.26 percentage points versus the MoE while reading 5.28x fewer optional sensors.

At H=.6 it slightly beats the first-pass all-sensor GRU while using 11.44x fewer optional reads.

More importantly, matched-budget attacks split the effect:

    H=.4 ProbePulse best timing + best sensor       .94272
    H=.4 entropy timing + RANDOM sensor             .91868
    H=.4 RANDOM timing + random sensor              .85199
    H=.4 PERIODIC timing + random sensor            .85402

On this first task, knowing **when the current belief has become too ambiguous** matters more than choosing the perfect observer; HUNT4-style sensor choice adds another smaller gain.

This is intentionally not black-box AI. A pulse can print the 32 hypotheses, entropy, four sensor scores, selected sensor and posterior after measurement.

Important caveat: the pulse network gets a strong discrete-state prior. HUNT7 must remove that privilege.

Run:

    python experiments/hunt6_probe_pulse32.py

See [results/HUNT6.md](results/HUNT6.md).

## The actual remaining failure

HUNT0 also contains an exact-degeneracy attack.

During an interval where two eigenvalues are exactly equal, the experiment secretly rotates the semantic axes inside that 2-D eigenspace.

The observed symmetric operator is invariant to that hidden internal rotation.

Therefore no observation-only tracker can know it happened.

The adaptive-block method correctly refuses to invent information, but semantic fidelity drops. When the gap reopens, statistics can identify axes again, while the semantic permutation/orientation may still require external task consequence.

This is the one-operator boundary. HUNT3 sharpens it:

> **A stable subspace does not identify a privileged basis inside a block that is exactly degenerate across every observable operator available to the tracker.**

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

1. Remove HUNT6's hand-enumerated 32-state hypothesis dictionary: continuous recurrent state, explicit ambiguity layer, learned observation operators.
2. Train an equally budgeted learned sensor-gating GRU/RNN attacker, not only cheap-only/all-sensor black boxes.
3. Learn action -> future-identifiability on the ECG loop so a probe can be issued before the controller enters a blind region.
4. Give observer actions explicit compute/energy/latency cost and optimize accuracy per measurement.
5. Keep estimation uncertainty separate from distinction strength; do not let repeatable collapse masquerade as confidence.
6. Move from synthetic ring/checker worlds to an actual temporal/audio/sensor task once the continuous-state pulse survives.

See [PAPERS.md](PAPERS.md).

## Install

```bash
pip install -r requirements.txt
```

Python 3.10+.

## Status

**GO, but narrow.**

Current positive result:

> The useful object is broader than a spectral tracker: estimate what distinctions are currently supportable, change representation granularity when they are not, search other observables locally, and in closed loop account for the fact that actions can change the observability of the next state.
