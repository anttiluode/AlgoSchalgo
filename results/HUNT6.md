# HUNT6 — ProbePulse32

## Question

Can the AlgoSchalgo ideas be turned into a tiny pulsing recurrent machine where a pulse has one explicit job:

> buy another observation because the current one no longer supports a sufficiently specific state belief?

And can that machine compete with ordinary black-box recurrent models while reading substantially fewer sensors?

## The task

A hidden point moves around a 16-position ring with direction -1/+1.

That gives exactly 32 hidden states:

    unit 0  = (position 0, direction -1)
    unit 1  = (position 0, direction +1)
    ...
    unit 31 = (position 15, direction +1)

Direction usually persists but flips with probability .03.

With probability .02, the hidden point also makes an "alias jump" by +4, +8 or +12 positions.

The free/default sensor is:

    y0 = cos(4 theta) + noise.

Therefore positions separated by four have exactly the same free observation.

An alias jump is not merely hard to notice. It is information-theoretically invisible to the free sensor.

Four optional local receptive-field sensors, centered at positions 0,4,8,12, can disambiguate the quadrant but have explicit read cost.

This forces the sensor question to be real:

> no recurrent black box can infer an invisible alias jump from the free stream alone.

## ProbePulse32 is deliberately not a black box

Its 32 recurrent activations are a probability distribution over the 32 concrete hypotheses.

Training consists only of:

1. count state-to-state transitions;
2. average each sensor response in each state;
3. estimate each sensor's residual noise.

No backpropagation is used.

At runtime:

    predict belief through transition table
        ↓
    observe free sensor
        ↓
    compute explicit position entropy
        ↓
    entropy above threshold?
       no -> continue
       yes -> PULSE
                ↓
          score each optional sensor by

          posterior variance of its
          hypothesis-conditioned means
          -----------------------------
                   sensor noise^2

                ↓
          read best ONE sensor
                ↓
          Bayesian belief update

Every pulse has an inspectable receipt:

- 32 pre-pulse hypothesis probabilities;
- entropy;
- four sensor scores;
- selected sensor;
- 32 post-pulse probabilities.

There is no anonymous learned hidden representation inside this model.

## Data

The receipt below uses:

- 512 training sequences;
- 128 validation sequences;
- 256 test sequences;
- 128 steps per sequence;
- independent fixed train/validation/test RNG seeds.

The transparent transition/sensor tables are estimated from the same labelled training sequences used by the supervised attackers.

Learned noise estimates:

    free sensor sigma     0.07994
    optional mean sigma   ~0.04983

which recover the planted .08/.05 scales without being given them.

## Transparent operating curve

Exact 32-state classification:

| position-entropy pulse threshold | accuracy | optional reads / step | read reduction vs four always-on optional sensors |
|---:|---:|---:|---:|
| .3 | **.95477** | .75754 | **5.28x** |
| .4 | **.94272** | .56708 | **7.05x** |
| .6 | **.91675** | .34970 | **11.44x** |
| .8 | .90039 | .31558 | 12.67x |
| 1.0 | .88120 | .27829 | 14.37x |

Transparent extremes:

    free sensor only        accuracy .11823   reads 0
    all optional sensors    accuracy .99374   reads 4.0 / step

So HUNT6 does not hide the tradeoff. More pulses buy more certainty.

## Black-box attackers

### 32-unit GRU, free sensor only

3 training initializations:

    .12013 +/- .00228 accuracy
    0 optional reads / step
    4416 learned parameters

It essentially matches the transparent cheap-sensor Bayesian filter (.11823).

That is expected. The alias jumps are invisible to this input.

### 32-unit echo-state reservoir, free sensor only

10 random reservoirs:

    .11805 +/- .00087 accuracy
    0 optional reads / step

Again: memory cannot reconstruct information that never entered the observer.

### 32-unit GRU, all five sensors always on

3 training initializations:

    .90156 +/- .00183 accuracy
    4 optional reads / step
    4800 learned parameters

Interesting result: the transparent H=.6 pulser is slightly more accurate:

    ProbePulse32 H=.6   .91675
    GRU32 all sensors   .90156

while reading only .3497 optional sensors per step instead of 4:

    11.44x fewer optional reads.

This is a first-pass training baseline, not a theorem that GRUs cannot catch up with more tuning/data.

### 4-expert x 8-hidden MoE, all sensors

The conventional MoE gets an 8-step five-sensor history. Four experts x eight hidden units gives 32 hidden expert units total. The gate and experts see every sensor, so it saves routing computation but **not sensing cost**.

3 initializations:

    .96734 +/- .00070 accuracy
    4 optional reads / step
    2628 learned parameters

This is the strongest learned attacker in HUNT6.

It beats the pulse network in raw accuracy.

But compare the high-accuracy transparent operating point:

    MoE all sensors       .96734 accuracy   4.000 reads/step
    ProbePulse32 H=.3     .95477 accuracy   .758 reads/step

The transparent system gives up about 1.26 percentage points while using:

    5.28x fewer optional sensor reads.

That is a meaningful trade, not a win on every axis.

## Matched-budget attacks

This is the more informative attack.

### Budget ~.567 reads/step

ProbePulse32 H=.4:

    best timing + best sensor       .94272

Same entropy-triggered timing, RANDOM optional sensor:

    .91868 +/- .00199

Same average budget, RANDOM pulse timing + random sensor:

    .85199 +/- .00363

Same average budget, PERIODIC timing + random sensor:

    .85402 +/- .00146

### Budget ~.350 reads/step

ProbePulse32 H=.6:

    best timing + best sensor       .91675

Entropy timing + random sensor:

    .89811 +/- .00153

Random timing + random sensor:

    .76356 +/- .00696

Periodic timing + random sensor:

    .78259 +/- .00668

## What this says

The first task does **not** say sensor selection is the whole magic.

In fact the decomposition is quite revealing:

    knowing WHEN information is needed
        gives the largest gain;

    choosing WHICH observer is most discriminative
        gives an additional smaller gain.

That makes sense in this ring world because several local sensors often carry some information about the aliased quadrant.

So the pulse itself has already earned a job:

> **uncertainty-triggered acquisition beats equally expensive blind acquisition.**

And HUNT4-style local sensor selection adds value on top.

## Why the non-black-box property matters

For the GRU, an internal unit changing from .31 to -.72 has no predefined semantic interpretation.

For ProbePulse32:

    belief[17] = .31

literally means:

    P(position=8, direction=+1 | observations) = .31.

Likewise a pulse is not an arbitrary learned activation.

The machine can print:

    position entropy = 1.27 bits
    sensor scores =
        [3.1, 17.4, 2.8, 5.0]
    chose optional sensor 1
    entropy after read = .22 bits

The computation can be inspected as computation.

## Important honesty

ProbePulse32 receives a stronger structural prior than a generic GRU:

- it knows that its 32 units are hypotheses;
- transition and emission tables are estimated explicitly;
- Bayesian normalization is built in.

That is intentional.

The question is not:

> can a hand-structured Bayes filter beat neural networks on data generated from its own model class?

Of course it can.

The useful question is:

> can this transparent active-sensing primitive retain its measurement-efficiency advantage when the observation model is no longer handed such a clean discrete state space?

That is the next attack.

## Prior-art boundary

Belief-state active sensing, information-gain sensor selection and POMDP sensor control are old fields.

HUNT6 is therefore not a novelty claim for:

- belief filters;
- Bayesian active sensing;
- entropy-triggered measurement;
- expected-information sensor selection;
- recurrent hypothesis tracking.

The reason to keep ProbePulse32 is architectural and practical:

> it gives AlgoSchalgo a concrete, fully inspectable neural-like primitive in which recurrence, ambiguity and information-seeking pulses have explicit meanings, and it exposes the accuracy/sensor-cost curve directly against black-box attackers.

## Run

Core transparent/reservoir experiment:

    python experiments/hunt6_probe_pulse32.py --no-neural

Full attack including PyTorch GRU/MoE:

    python experiments/hunt6_probe_pulse32.py

Machine-readable:

    python experiments/hunt6_probe_pulse32.py --json

## Next kill

Make the hidden world continuous and stop giving the pulse system a predefined 32-state hypothesis dictionary.

Candidate HUNT7:

- 32 ordinary continuous recurrent units;
- four learned-but-inspectable observation operators;
- an explicit ambiguity statistic computed from local response geometry;
- pulse chooses an observer;
- downstream task trained normally.

If the explicit ambiguity/pulse machinery loses to an equally budgeted GRU with learned sensor gating, the "special neural layer" branch dies.

If sparse information-seeking pulses survive without a hand-enumerated state table, then the idea has moved beyond a clever Bayes filter.
