# HUNT5 — ECG Observer Causality

## Origin

This hunt uses the five-node Perception Laboratory loop that originally helped motivate the Geometric Neuron line:

    Homeostatic Coupler
        -> Checkerboard
        -> ImageToVector
        -> VectorSplitter
        -> first four channels back to Coupler

The experiment is a headless transcription of the supplied node code and saved JSON state. Qt is removed; the signal path is retained.

The purpose is not to claim anything cardiac or neural.

The question is narrower:

> Is the period-52 "ECG" rhythm causally organized by the observation geometry, or is observability merely a poetic description attached after the fact?

## Exact baseline reproduction

The saved configuration gives:

- image: 256 x 256;
- ImageToVector: 256 outputs = 16 x 16 area averages;
- VectorSplitter: 16 outputs, therefore the 256-vector is truncated to its first 16 values;
- only outputs 0..3 feed the coupler;
- ConstantSignal=1.0 shifts the coupler setpoint from .5 to .6;
- edge-of-chaos mode uses a 50-sample input-variance window with target variance .1.

The headless recurrence converges to a period-52 limit cycle.

Steady-cycle square sizes:

    48 43 48 43 48 43 48 43 48 43 48 43 48 43 48 43
    48 43 48 43 48 43 84 -12 51 40 49 42
    48 43 48 43 48 43 48 43 48 43 48 43 48 43 48 43
    48 43 48 43 48 43 48 43 48 43 48 43

Signal range:

    -0.342664735 .. 1.584779282

The plateau is the familiar 43/48 alternation.

## What the two wall frames actually are

The original observer is the first four cells of the normalized 16x16 area-downsampled image.

| square size | feedback | raw variance of first 4 cells | raw variance of full 16x16 image |
|---:|---:|---:|---:|
| 48 | 1.000000 | .187500 | .249939 |
| 43 | 1.312500 | .166748 | .146172 |
| **84** | **0.000000** | **0.000000** | **.175594** |
| **-12** | **3.157895** | **.009277** | **.005082** |
| 51 | .812500 | .123779 | .151843 |
| 40 | 1.500000 | .171875 | .165035 |
| 49 | .937500 | .164795 | .167706 |
| 42 | 1.375000 | .166992 | .133396 |

These are two different failures.

### Wall A — aperture blindness at q=84

The chosen four-cell aperture is completely flat:

    aperture variance = 0

but the full 16x16 representation still has substantial contrast:

    full variance = .175594

Therefore q=84 is not globally unobservable at 16x16.

The chosen aperture is blind.

Another four-cell window at the same resolution can see it. The best one has:

    raw four-cell variance = .199219
    normalized feedback    = 1.75

This is the HUNT3/HUNT4 case:

> one measurement is degenerate; the available operator family is not.

### Wall B — representation collapse around q=-12

At q=-12:

    aperture variance = .009277
    full 16x16 variance = .005082

Now the whole 16x16 area-averaged representation has become low contrast.

Global max-normalization then amplifies this weak residual structure to feedback 3.157895.

So the reset contains both:

1. a local-aperture zero at q=84;
2. a broad low-contrast / alias regime on the next excursion.

This corrects an earlier overstatement that the steady cycle itself reaches q=+/-1 and produces exactly all ones.

Those states are real analytic boundary probes:

| q | original feedback | full 16x16 variance |
|---:|---:|---:|
| -1 | 4.0 | 0.0 |
| 0 | 0.0 | 0.0 |
| +1 | 4.0 | 0.0 |

At q=+/-1 every 16x16 area cell averages to .5; max normalization turns the field into all ones.

At q=0 the unguarded NumPy integer division returns zeros under warning, so the checker image becomes black.

But these are not members of the asymptotic period-52 orbit of the supplied saved state.

## Causal test 1 — change only the fixed aperture

The controller, checker plant, downsampling resolution and normalization are unchanged.

Only the top-row four-cell window is shifted.

| window x | asymptotic period | square-size range |
|---:|---:|---:|
| 0  | **52** | -12 .. 84 |
| 1  | 51 | -10 .. 84 |
| 2  | 51 | 38 .. 84 |
| 3  | **1** | 84 .. 84 |
| 4  | **1** | 84 .. 84 |
| 5  | 51 | 43 .. 79 |
| 6  | **2** | 40 .. 51 |
| 7  | 51 | 49 .. 84 |
| 8  | **1** | 84 .. 84 |
| 9  | **1** | 84 .. 84 |
| 10 | 102 | 25 .. 84 |
| 11 | 104 | -13 .. 84 |
| 12 | **2** | 40 .. 51 |

This is strong causal evidence that the observed rhythm is not an invariant of the controller alone.

Changing only observation location can:

- preserve a relaxation cycle but change its period;
- double the period;
- collapse it to period 2;
- kill it into a fixed point.

## Causal test 2 — repair only the ambiguity event

A stronger intervention leaves the original observer untouched whenever its four raw cells have variance >= .01.

Only when the original aperture becomes locally indistinguishable does the observer select the most contrastive four-cell window at the same 16x16 resolution.

If the entire 16x16 representation is also flat, it may escalate to a finer resolution.

Result:

    original observer       period 52
    ambiguity rescue        period 1

The rescued system converges to:

    signal_out   = 1.599797942
    square_size  = 84
    feedback     = 1.75

and uses a shifted 16x16 aperture.

No controller parameter changed.

The large reset disappears.

This makes the q=84 aperture wall causal, not merely correlated with the spike.

## Causal test 3 — repair only global resolution collapse

To isolate the second wall, another observer deliberately does NOT repair the q=84 local-aperture failure.

It behaves exactly like the original observer whenever the full 16x16 field has variance >= .01.

Only when the whole 16x16 field becomes too flat does it switch to the cheapest finer resolution with an informative four-cell aperture.

Result:

    original              period 52
    resolution-only rescue period 51

The new steady excursion includes:

    ... 43, 48, 71, -10, 84, 23, 49, 42, ...

The coarse q=84 zero remains, so the relaxation event survives, but changing the fine-resolution observer changes the return map and period.

Thus both observer failures participate, but the q=84 aperture wall is the decisive kill point in this configuration.

## Multi-resolution probe

The geometry itself predicts which measurement scales can rescue fine structure.

Best four-cell raw variance by resolution:

### q=-12

| side | best 4-cell variance |
|---:|---:|
| 16 | .009277 |
| 32 | .148438 |
| 64 | .199219 |
| 128 | .171875 |
| 256 | .250000 |

### q=+/-1

| side | best 4-cell variance |
|---:|---:|
| 16 | 0 |
| 32 | 0 |
| 64 | 0 |
| 128 | 0 |
| 256 | .25 |

So the "use another aperture" and "use another resolution" responses are genuinely different operations.

## Important negative result — epsilon alone is not an early-warning signal here

The earlier proposed AmbiguityBlockNode was going to use split-half disagreement epsilon-hat and predict that epsilon-hat rises before the spike.

HUNT5 rejects that as a general prediction.

This loop is deterministic. A representation can become perfectly repeatable and simultaneously lose the distinctions we care about.

At q=84, the first four raw cells are exactly:

    [0, 0, 0, 0]

Two repeated measurements can agree perfectly.

At q=+/-1, the entire 16x16 raw field is exactly uniform .5.

Again, two measurements can agree perfectly.

Therefore:

    low estimator disagreement != high identifiability

and:

    high confidence != informative representation.

The useful diagnostic needs at least two concepts:

1. estimation uncertainty / repeatability;
2. distinction strength / observability.

For this graph, raw aperture contrast and full-field contrast expose the two walls directly.

## Another negative result — passive one-frame warning is not guaranteed

The plateau states q=43 and q=48 remain strongly contrasted right until the coupler changes regime and jumps to q=84.

So a node that sees only the current incoming 16-vector need not contain a gradual precursor.

The wall is crossed abruptly by the controller action.

To predict the loss BEFORE the bad observation arrives, the guard needs one of:

- the outgoing control/action;
- a known observation model;
- an online learned map from action/state to future identifiability.

That is an important extension beyond HUNT0-HUNT4:

> observability can be action-dependent.

The controller changes not only the plant state but the quality of its own next observation.

## What HUNT5 earns

Not:

- cardiac dynamics;
- neural dynamics;
- edge-of-chaos novelty;
- a new theory of relaxation oscillators.

It earns:

> In this real pre-existing feedback graph, observation geometry is a causal state variable of the closed loop. A controller with fixed parameters can change from period 52 to period 1 solely because the observer switches away from a locally degenerate aperture.

And it gives AlgoSchalgo its first naturally generated ambiguity crossing rather than a hand-planted matrix crossing.

## Run

    python experiments/hunt5_ecg_observer_causality.py

or machine-readable:

    python experiments/hunt5_ecg_observer_causality.py --json

## Next question

The next algorithm should not merely detect a bad observation after it arrives.

It should learn:

    action / current state
        -> expected identifiability of each available observer next step

and choose the cheapest observer that keeps the relevant ambiguity blocks separated.

That is the active closed-loop version of HUNT4.
