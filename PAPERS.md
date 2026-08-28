# Papers and mathematical attack map

This is a working literature map, not a novelty claim.

## Davis & Kahan — perturbation of invariant subspaces

Chandler Davis and W. M. Kahan, *The Rotation of Eigenvectors by a Perturbation. III*, SIAM Journal on Numerical Analysis, 1970.

https://doi.org/10.1137/0707001

Why it matters:

- eigenvector/eigenspace conditioning depends on spectral separation;
- a cluster of nearby eigenvalues should often be treated through its invariant subspace;
- HUNT0 turns that perturbation distinction into an online state/update rule.

## Szwagier & Pennec — nested subspace learning with flags

Tom Szwagier and Xavier Pennec, *Nested Subspace Learning with Flags*, JMLR 27(106), 2026.

https://jmlr.org/papers/v27/25-0807.html

Why it matters:

- flags naturally represent nested subspaces;
- their projection representation is basis invariant;
- their "flag trick" attacks inconsistency between independently learned subspaces of different dimensions.

## Jin & Coulson — online flag tracking

Dian Jin and Jeremy Coulson, *Online Subspace Learning on Flag Manifolds for System Identification*, L4DC / PMLR 2026.

https://proceedings.mlr.press/v331/jin26a.html

Why it matters:

- current direct prior art for recursive tracking of nested subspaces;
- targets time-varying systems and changing/unknown model order;
- any serious continuation has to compare against this.

## GREAT — online Grassmann tracking

Andras Sasfi, Alberto Padoan, Ivan Markovsky, Florian Doerfler, *Subspace tracking for online system identification* / GREAT.

https://arxiv.org/abs/2412.09052

Why it matters:

- rigorous online tracking of moving subspaces;
- gives rate/noise conditions for reliable tracking;
- useful attacker for the projector/subspace part of HUNT0.

## Eigenvalue multiplicity and flag type

Tom Szwagier's thesis/program makes the key geometric fact explicit:

> eigenspaces of a symmetric matrix form a flag whose type is the sequence of eigenvalue multiplicities.

https://sites.google.com/view/tomszwagier/phd

The associated statistical program asks when close empirical eigenvalues should be equalized and the model reduced from individual principal components to principal subspaces.

This is close to the spirit of HUNT0, which is good: it gives us vocabulary and an attacker.

## Split-Half Eigenvector Matching (SHEM)

*Estimating the number of principal components via Split-Half Eigenvector Matching (SHEM)*.

https://pmc.ncbi.nlm.nih.gov/articles/PMC10371851/

Why it matters:

- independent data halves can reveal which empirical eigenvectors are reproducible;
- HUNT1 instead uses the half-difference as a perturbation-norm proxy;
- "use split halves to decide spectral reliability" is therefore definitely not new.

## Split-half signal covariance

Split-half covariance estimation is also standard in neural signal/noise estimation.

https://doi.org/10.1371/journal.pcbi.1012092

Why it matters:

- supports split-half estimation as an ordinary statistical move;
- HUNT1 should eventually be expressed for an actual finite-sample operator estimator, not Gaussian matrix-noise toys.

## AMUSE / SOBI — the temporal operator itself is old

AMUSE uses a covariance matrix plus a lagged autocovariance matrix to recover sources whose temporal signatures differ.

A useful statistical treatment of AMUSE:

https://users.jyu.fi/~slahola/files/AMUSE.pdf

SOBI generalizes the idea by jointly approximately diagonalizing several lagged covariance matrices:

Adel Belouchrani, Karim Abed-Meraim, Jean-Francois Cardoso, Eric Moulines, *A blind source separation technique using second-order statistics*, IEEE TSP 1997.

https://doi.org/10.1109/78.554307

Why it matters:

- HUNT2's whitened lag operator is intentionally an AMUSE-style object;
- the next obvious attacker is multi-lag SOBI;
- a source pair that collides at one lag may remain distinguishable from its signature across several lags;
- if so, the correct ambiguity block should be defined by **joint temporal identifiability**, not one eigengap.

## Spectral-gap estimation

Michele Benzi, Michele Rinelli, Igor Simunec, *Estimation of spectral gaps for sparse symmetric matrices*, Numerische Mathematik, 2026.

https://doi.org/10.1007/s00211-026-01532-8

Why it matters:

- large problems may not permit full eigendecomposition;
- gaps themselves can be estimated with randomized matrix-free methods;
- scalable ambiguity-block tracking may need to find trustworthy block boundaries without diagonalizing everything.

## GeRoST — robust subspace tracking

Shreyas Bharadwaj et al., *Min-Max Grassmannian Optimization for Online Subspace Tracking*, 2026.

https://arxiv.org/abs/2604.00825

Why it matters:

- explicitly models subspace uncertainty geometrically;
- likely a stronger baseline than a binary gap guard.

## Not currently claimed

- flags are new;
- degenerate eigenvectors should be treated as a subspace is new;
- Procrustes alignment is new;
- split-half reliability is new;
- Davis-Kahan gap/noise reasoning is new.

Candidate synthesis being tested:

> Can a streaming spectral tracker change the granularity of its state online—single vectors when identifiable, ambiguity subspaces when not—and use a live perturbation estimate to decide those transitions without hand-tuned gap thresholds?

If an existing algorithm already does exactly this, adopt it and move on.
