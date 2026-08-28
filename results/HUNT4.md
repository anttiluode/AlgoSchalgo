# HUNT4 — Block-Local Measurement Selection

## Question

HUNT3 showed that a degeneracy in one operator can disappear when several jointly observable operators are available.

But HUNT3 still chooses one global operator combination for the entire representation.

Why should every ambiguity block want the same view?

HUNT4 asks:

> If different unresolved blocks are best distinguished by different observables, is there an unavoidable cost to forcing one universal measurement combination?

## Constructed family

There are K ambiguity blocks and K observable symmetric operators.

For block p, the joint-signature difference between its two semantic axes is

    d_p = 2 delta e_p

where e_p is coordinate p in operator space.

A single unit-norm global combination alpha gives block-p signal gap

    2 delta |alpha_p|.

Therefore

    min_p 2 delta |alpha_p|
    <= 2 delta / sqrt(K).

The bound is tight. The balanced global projection

    alpha* = (1,...,1) / sqrt(K)

achieves it.

A block-local selector can instead use alpha_p = e_p for block p and gets gap

    2 delta.

So on this family the local-to-global worst-block signal-gap ratio is exactly

    sqrt(K).

This is a theorem about the constructed family, not a universal theorem that local sensing is always better.

## Noisy experiment

Each block carries a moving 2-D semantic frame.

Every observable is estimated twice with independent symmetric noise. The HUNT1 split-half rule supplies an instantaneous noise-normalized identifiability margin:

    margin =
        observed eigengap
        /
        (2 * ||(A1-A2)/2||_2).

### Global attacker

The global method is not random search.

It receives the analytically optimal max-min global projection:

    alpha* = (1,...,1) / sqrt(K).

### Local candidate

For every ambiguity block, maintain an EMA of the split-half margin for every raw observable and choose the observable with the largest accumulated identifiability score.

No block-to-operator label is supplied to the selector.

## Receipt

10 seeds. delta=0.12. Averaged-estimate noise scale=0.06.

| blocks K | global margin | local margin | global safe fraction | local safe fraction | global axis fidelity | local axis fidelity | local chose correct observable |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2  | 1.4184 | **1.8941** | .5774 | **.7776** | .9655 | **.9821** | 1.0000 |
| 3  | 1.2263 | **1.9096** | .4780 | **.7767** | .9512 | **.9824** | .9988 |
| 4  | 1.1454 | **1.9246** | .4346 | **.7765** | .9437 | **.9823** | .9981 |
| 6  | 1.0356 | **1.9160** | .3694 | **.7674** | .9314 | **.9812** | .9952 |
| 8  | .9775 | **1.8765** | .3355 | **.7676** | .9249 | **.9817** | .9962 |
| 12 | .8993 | **1.8972** | .2996 | **.7685** | .9187 | **.9814** | .9970 |

The empirical measured margin is noisy and selection-biased, so it is not expected to follow the exact 1/sqrt(K) signal law.

The structural result is clear:

- the analytically best one-view worst-block signal shrinks as 1/sqrt(K);
- the local signal does not;
- global safe-identification fraction drops from about 58% to 30%;
- local safe-identification fraction stays around 77%;
- global axis fidelity declines as block count grows;
- local fidelity remains near .982.

## Kill control — everyone wants the same view

The local method should provide no advantage if every block is best resolved by the same observable.

So a control makes operator 0 informative for all eight blocks.

The global oracle receives alpha=e0.

10-seed result:

    global mean margin     1.88685
    local mean margin      1.89687

    global axis fidelity   0.98200
    local axis fidelity    0.98154

    local chose operator 0 0.99507

The advantage disappears.

So HUNT4 does not earn:

> local selection beats global measurement.

It earns the narrower statement:

> Local measurement selection earns its keep when distinct ambiguity blocks genuinely require distinct observable directions.

## Interpretation

HUNT3 said:

    one view ambiguous
        -> search the operator family.

HUNT4 sharpens it:

    several blocks ambiguous
        -> do not necessarily search for one universal best view
        -> choose a view per unresolved block.

This is a concrete active-sensing interpretation:

    current ambiguity block
            |
            v
    which available observable maximizes
    noise-normalized identifiability here?
            |
            v
    measure / combine that observable
            |
            v
    refine only this block.

## What is and is not new

Not new:

- active sensing / experiment design;
- sensor selection;
- joint operator families;
- adaptive subspace estimation;
- using different measurements for different estimation goals.

Candidate residue under test:

> combine adaptive ambiguity blocks with online, block-specific operator selection using current empirical identifiability, rather than forcing one global representation or one fixed sensing policy.

Novelty remains unclaimed.

## Next practical experiment

Give measurements an explicit cost.

Example: 32 available lags/frequencies/views, but only four may be evaluated per update.

Then:

1. detect unresolved semantic blocks;
2. choose the four observables expected to separate them best;
3. compare against fixed, random, and all-observable sensing;
4. measure semantic fidelity per unit measurement cost.

That would turn the geometry into an actual resource-allocation algorithm.
