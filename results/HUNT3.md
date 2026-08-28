# HUNT3 — Ambiguity Is Operator-Family Relative

## Question

HUNT0 found an exact-degeneracy failure:

> if one symmetric operator has a repeated eigenvalue, rotation inside that eigenspace is invisible.

But that statement is only about the information contained in **that operator**.

What if several simultaneously observable operators share the same hidden eigenvectors but carry different eigenvalue signatures?

## Algebra

Suppose

```math
A_k = Q \Lambda_k Q^T
```

for several commuting symmetric operators.

Each semantic mode `i` then has a vector-valued joint signature

```math
\lambda_i =
(\lambda_i^{(1)},\ldots,\lambda_i^{(K)}).
```

A collision in operator 1,

```math
\lambda_i^{(1)}=\lambda_j^{(1)},
```

does not imply a joint collision.

For any coefficient vector `alpha`,

```math
B(\alpha)=\sum_k \alpha_k A_k
       =Q\left(\sum_k \alpha_k\Lambda_k\right)Q^T.
```

So the eigenvectors are unchanged while the joint signatures are projected to scalar eigenvalues

```math
\mu_i=\alpha^T\lambda_i.
```

If two signature vectors differ, a generic random projection separates them with probability one in exact arithmetic.

That random-linear-combination idea is established randomized joint diagonalization / joint eigenvalue machinery. HUNT3 does **not** claim it as new.

## Candidate wrapper

HUNT3 generates a small random bank of coefficient vectors.

For every split-half observation pair and every candidate projection:

1. form `B1(alpha)` and `B2(alpha)`;
2. average them;
3. compute the minimum observed eigengap;
4. estimate perturbation radius from the split-half difference;
5. score
   ```math
   \frac{\text{minimum eigengap}}
        {2\,\hat\epsilon};
   ```
6. use the projection with the best noise-normalized separation.

So the machine does not merely accept whatever operator it was handed. It searches for a cheap observable combination in which the current semantic distinctions are best conditioned.

## World

Three jointly diagonalizable symmetric operators share one moving semantic frame.

- Operator 0 becomes **exactly degenerate** for modes 0/1 during a plateau.
- During that plateau the semantic basis rotates by 90 degrees inside the degenerate plane.
- Operators 1 and 2 retain distinct signatures for those same modes.
- Every operator is observed through two noisy split estimates.

Single-operator HUNT1 therefore faces the HUNT0 impossibility.

The joint family does not.

## Receipt

30 seeds:

| random projections | single overall | single inside | single after | joint overall | joint inside | joint after |
|---:|---:|---:|---:|---:|---:|---:|
| 4  | .850781 | .874393 | .688574 | .899323 | .889041 | .858542 |
| 8  | .850781 | .874393 | .688574 | .988471 | .990385 | .980643 |
| 16 | .850781 | .874393 | .688574 | **.996495** | **.996465** | **.996455** |
| 32 | .850781 | .874393 | .688574 | **.997132** | **.997108** | **.997176** |

## The corrected boundary

HUNT0's hidden-gauge failure was real, but its interpretation was too broad.

Correct statement:

> **A semantic rotation is unobservable only inside a block that remains degenerate across the entire available operator family.**

One operator can be ambiguous while the joint measurement family is not.

That changes the resource-allocation story:

```text
one observable becomes ambiguous
        ↓
do not spend labels yet
        ↓
look for another lag / view / operator
that breaks the symmetry
        ↓
only if the full available family remains ambiguous
spend task consequence
```

## Prior art pressure

The core random-combination trick is established.

He & Kressner analyze randomized joint diagonalization of nearly commuting symmetric matrices and show robust recovery from random linear combinations under perturbation.

So the candidate residue here is narrower:

> **select among cheap joint-operator projections using a live, split-half, noise-normalized identifiability margin, then feed that choice into the adaptive ambiguity-block tracker.**

Novelty remains unclaimed.

## Next attacks

- replace synthetic commuting matrices with several empirical lag operators from one continuous time series;
- compare against full SOBI / approximate joint diagonalization;
- optimize the projection direction instead of relying on a random bank;
- allow some operators to be noncommuting / misspecified;
- ask whether the best projection for all modes is inferior to several local projections for different ambiguity blocks.
