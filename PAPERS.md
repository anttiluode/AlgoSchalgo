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

## Randomized joint diagonalization — HUNT3's main prior-art attack

Martin He and Daniel Kressner, *Randomized Joint Diagonalization of Symmetric Matrices*, SIAM Journal on Matrix Analysis and Applications.

https://doi.org/10.1137/22M1541265

Related randomized joint-eigenvalue work uses the same algebraic fact: for commuting matrices, a generic linear combination preserves common eigenvectors while randomly projecting the joint eigenvalue tuples.

https://link.springer.com/article/10.1007/s11075-024-01971-0

Why it matters:

- HUNT3's random linear combinations are **not new**;
- the literature gives perturbation/robustness analysis for nearly commuting noisy families;
- HUNT3's candidate residue is the online policy around that old machinery:
  choose a cheap projection using a split-half noise-normalized identifiability margin, then change ambiguity-block granularity accordingly;
- a stronger attacker is to run a proper randomized/full joint diagonalizer instead of selecting one projection.

The conceptual correction supplied by HUNT3 remains useful regardless of novelty:

> ambiguity is relative to the available operator family. A collision in one lag/view need not be a true information-theoretic ambiguity.

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

## HUNT4 pressure — active sensing and selective fusion

HUNT4's broad idea is not new: choose measurements according to what remains uncertain.

### Online experiment design

Recent system-identification work explicitly chooses informative inputs online while parameter estimates evolve.

- *Adaptive Experiment Design for Nonlinear System Identification With Operational Constraints*, IEEE Signal Processing Letters, 2026.
  https://doi.org/10.1109/LSP.2025.3639512

- *The shortest experiment for linear system identification* develops an online input-design method guided by past measurements and proves sample-length advantages over standard persistency-of-excitation style designs.
  https://doi.org/10.1016/j.sysconle.2025.106197

Pressure on HUNT4:

- "adapt measurement to current uncertainty" is old and broad;
- any novelty claim must live in the specific ambiguity-block / spectral-identifiability formulation, if anywhere.

### Degeneracy-aware selective sensor fusion

Zhang et al., *Fuse only what matters: Degeneracy-aware multi-sensor fusion for LiDAR-Inertial-Visual SLAM*, ISPRS Journal of Photogrammetry and Remote Sensing, 2026.

https://doi.org/10.1016/j.isprsjprs.2026.05.031

This is strikingly close in engineering philosophy:

- detect when and in which directions the primary estimator becomes degenerate;
- inject another sensor only in those directions;
- avoid contaminating already well-constrained dimensions with unnecessary measurements.

That means HUNT4 should not be sold as discovering "direction-specific selective sensing." A better question is whether the **joint-signature + split-half spectral margin + adaptive ambiguity-block** machinery offers a useful generic implementation in domains where the relevant observables are lags, frequencies, covariance operators, or representation views rather than physical sensors.

### Classical online sensor selection

Online sensor selection under processing constraints is much older than this project.

A representative classical reference:

- *Optimal sensor selection strategy for discrete-time state estimators*, IEEE Transactions on Aerospace and Electronic Systems, 1994.
  https://doi.org/10.1109/7.272256

Again: the interesting residue, if any, is not sensor selection itself.

## HUNT5 pressure — dual effect, observability and sensor scheduling

HUNT5 moves from passive representation tracking into closed-loop sensing.

The control output changes the plant state and simultaneously changes the quality of the next observation. This belongs to a large existing control-theory family.

### Dual control

The classic dual-control idea is that an action has both a directing/control effect and an information/probing effect.

A useful survey:

- *Stochastic model predictive control with active uncertainty learning: A Survey on dual control*.
  https://doi.org/10.1016/j.arcontrol.2017.09.001

Pressure on HUNT5:

- "actions affect future information" is emphatically not new;
- the ECG loop is interesting as a tiny deterministic example where the controller accidentally drives its own observer into degeneracy, not as a discovery of dual control.

### Data-driven sensor selection by observability

Fotiadis & Vamvoudakis, *Input-output data-driven sensor selection for cyber-physical systems*, Automatica 186, 2026.

https://doi.org/10.1016/j.automatica.2026.112829

They select sensor subsets for unknown systems using observability-related objectives computed from input-output data.

Pressure on AlgoSchalgo:

- "choose sensors that improve observability" is established;
- a serious comparison should include Gramian/H2/log-det style observability metrics, not only local contrast or eigengaps.

### Dynamic sensor scheduling and epsilon-observability

Liu, Shi, Li & Shi, *Data Scheduling and State Estimation for Large-Scale Event-Based Sensor Arrays*, SIAM Journal on Control and Optimization, 2026.

https://doi.org/10.1137/24M1670792

They jointly study dynamic sensor/data selection and state estimation and derive an epsilon-observability criterion under spatial-temporal scheduling.

This is especially relevant to the next AlgoSchalgo attack:

> when observation choice itself changes over time, what guarantees that the resulting scheduled system remains observable?

### Sparse joint sensor/actuator scheduling

Joint sensor and actuator scheduling with performance guarantees is also established.

https://doi.org/10.1016/j.automatica.2020.109197

The broad lesson for AlgoSchalgo is again restrictive:

> the candidate contribution is not "select informative sensors." It is, if anything, the specific ambiguity-block / operator-family / action-dependent identifiability policy and whether it gives a cheap useful approximation in moving-representation problems.

## Not currently claimed

- flags are new;
- degenerate eigenvectors should be treated as a subspace is new;
- Procrustes alignment is new;
- split-half reliability is new;
- Davis-Kahan gap/noise reasoning is new.

Candidate synthesis being tested:

> Can a streaming spectral tracker change the granularity of its state online—single vectors when identifiable, ambiguity subspaces when not—and use a live perturbation estimate to decide those transitions without hand-tuned gap thresholds?

If an existing algorithm already does exactly this, adopt it and move on.
