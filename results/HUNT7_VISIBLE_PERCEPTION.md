# HUNT7 — Visible Perception Cycle

## Why this exists

AlgoSchalgo repeatedly rediscovered a broad old idea:

> spend scarce evidence / computation only when the current state is insufficient.

HUNT7 stops trying to rename that idea and instead asks whether a particular transparent implementation is useful.

It fuses two historically separate Perception Lab branches:

1. predictive memory / transition learning / surprise / finite ATP;
2. AlgoSchalgo support / observability / selective extra work.

The fusion is deliberately inspectable.

## The cycle

    learned visible memory P
              +
    learned transition model T
              |
              v
          prediction
              |
              v
        messy observation
              |
              v
      support / ambiguity
              |
      sufficiently clear?
        /           \
      yes            no
       |              |
     HOLD      score explicit transforms
       |        by support gain / ATP
       |              |
       |            PULSE
       |              |
       +------> cleaned recall
                      |
                      v
             surprise residual
            recall - prediction

The prediction does not choose the transform.

That is a critical rule.

If a clear observation violates the learned sequence, the system should say:

> unexpected, but clearly seen.

It should not manipulate the image until it resembles the expectation.

## What is visible

The GitHub Pages demo exposes:

- predicted image;
- raw observed image;
- current transformed image;
- recalled prototype image;
- surprise residual image;
- four candidate support probabilities;
- support margin and ambiguity;
- ATP budget;
- HOLD / SCAN / REST state;
- every candidate transform, its predicted support gain and ATP cost;
- complete transform trajectory;
- learned image prototypes P;
- learned transition matrix T;
- execution log.

The internal state is therefore closer to an algorithm trace than to a conventional latent neural representation.

## Two different reasons for difficulty

### 1. Clear but surprising

The observation strongly supports one class, but the learned temporal model predicted another.

    support high
    prediction error high

Correct response:

    report surprise
    HOLD
    spend no image-processing ATP

This is a world-model failure, not an observability failure.

### 2. Ambiguous but unsurprising

The expected kind of image arrives, but translation / rotation / blur / noise makes the current class distinction weak.

    support low
    prediction error may be modest

Correct response:

    buy a named image transform
    re-evaluate support
    stop when sufficient or ATP exhausted

This is an observation / representation problem.

That separation is more useful than one generic confidence scalar.

## ATP has a concrete meaning here

In the older Perception Lab workflow ATP was a biological metaphor implemented as a finite hysteretic resource.

Here ATP is simply:

> finite optional computation budget.

For example:

    contrast       .05 ATP
    sharpen        .07 ATP
    rotate 8 deg   .08 ATP
    recenter       .10 ATP
    zoom           .11 ATP
    rotate 18 deg  .12 ATP

The exact numbers are demo-scale relative costs, not physical energy claims.

The important property is architectural:

    easy image -> zero optional work
    hard image -> some work
    still unresolved + no budget -> return unresolved

## What may actually be useful

The broad ingredients are old. The candidate useful object is a transparent control plane around perception.

A practical version could sit in front of an arbitrary image model:

    cheap image / cheap model
          |
          v
    is the needed distinction supported?
          |
    yes --+--> return
          |
          no
          v
    choose explicit extra work:
        higher resolution
        crop
        alternate sensor
        another frame
        another model
        expensive feature pass
          |
          v
    audit exactly what was bought and why

Potential value:

- edge vision where high-resolution / depth / large-model calls have real cost;
- industrial inspection where a decision needs an audit trail;
- debugging representation failures in a trained neural network;
- human-facing systems where "unresolved" is preferable to fabricated precision;
- model cascades where the expensive model should be called for a specific unresolved distinction, not merely low scalar confidence.

## A possibly stronger use: representation firewall

The layer need not replace a neural network.

It could sit around one.

The black box supplies candidate scores or a representation.

The support layer supplies:

- which alternatives remain unresolved;
- whether current image manipulations preserve or destroy the decision;
- which explicit extra observation would discriminate them;
- when the computation budget is exhausted.

Then the neural network remains a function approximator while the resource / observability policy stays inspectable.

This is closer to a control plane than to a new neural architecture.

## What is not new

The general ideas have strong prior art:

- spatial transformers explicitly manipulate images inside neural networks;
- adaptive computation time varies how much computation a network spends;
- active sensing / visual attention chooses where to look;
- current adaptive-computation work explicitly rations perceptual computation;
- recent entropy-driven visual-attention work allocates visual processing according to task need;
- foveation-based explanation methods iteratively transform visual input.

So HUNT7 does not claim:

- iterative image transforms are new;
- adaptive compute is new;
- prediction error is new;
- resource-bounded perception is new;
- active vision is new.

## Candidate residue

What is still worth testing is narrower:

> Can a small architecture-agnostic support layer make an ordinary vision system more measurement/computation efficient while preserving a human-readable causal trace of why extra work was requested?

And a second question:

> Does separating "unexpected" from "not currently distinguishable" prevent wasted computation and prediction-driven confirmation errors compared with one generic confidence gate?

Those are empirical questions.

## Provenance

Perception Laboratory predates AlgoSchalgo and contains many different visual-memory and predictive-processing variants.

Earlier discussion associated part of that ancestry with a "Fable AI" idea, but the exact code lineage is not established.

The accidental ECG workflow in fall 2025 was the actual birth point of the Geometric Neuron line.

The predictive-cortex / ATP / surprise workflow is a separate later branch.

AlgoSchalgo's ambiguity / observability line arrived independently in August 2026.

HUNT7 is a deliberate fusion of those branches, not a claim that all earlier versions were one continuous implementation.

## Demo

Open:

    index.html

or serve the repository with GitHub Pages.

The page is pure browser JavaScript and has no external model or library dependency.

## Next serious attack

Do not build another synthetic architecture first.

Wrap the same support/control logic around an already-trained ordinary image classifier.

Give it real optional costs:

- low-res vs high-res crop;
- one frame vs extra frame;
- small model vs large model;
- RGB vs depth / second modality if available.

Compare against:

1. always-cheap;
2. always-expensive;
3. scalar confidence threshold;
4. random escalation at matched budget;
5. support-aware explicit escalation.

Measure:

    task quality
    versus
    actual compute / bytes / sensor reads.

If a scalar confidence gate matches the Pareto frontier, use the scalar gate and stop.
