/-
Copyright (c) 2026 relu-depth-frontier-research contributors. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: relu-depth-frontier-research contributors
-/
import Formalization.Obstruction
import Mathlib.Data.Nat.Choose.Sum
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring

/-! # The alternating-binomial obstruction at MAX11

On the ordered chamber `x_(1) ≤ ... ≤ x_(11)`, the symmetric subset-maximum

`F_m = ∑_{|S| = m} max_{i ∈ S} x_i`

has coefficient `choose (r - 1) (m - 1)` on `x_(r)`.  This file kernel-checks the exact
11-dimensional linear-algebra obstruction used in G-0047: the alternating-binomial functional
kills all ten proper-subset coefficient vectors, but takes value one on the MAX11 coefficient
vector.  The result therefore excludes MAX11 from their real span.

This is deliberately a coefficient-space theorem.  It does not assert that every two-hidden-layer
ReLU representation belongs to this span, and hence is not an unrestricted MAX11 lower bound.
-/

namespace ReluDepth

open scoped BigOperators

/-- The G-0047 alternating-binomial functional, in increasing order-statistic rank. -/
def max11AlternatingBinomial : Fin 11 → ℝ :=
  fun r ↦ (-1 : ℝ) ^ (10 - r.val) * Nat.choose 10 r.val

/-- Ordered-chamber coefficients of `F_(m+1)`; `m : Fin 10` indexes proper subset sizes. -/
def max11SubsetMaxCoeff (m : Fin 10) : Fin 11 → ℝ :=
  fun r ↦ (Nat.choose r.val m.val : ℝ)

/-- Ordered-chamber coefficient vector of MAX11 itself. -/
def max11TargetCoeff : Fin 11 → ℝ :=
  fun r ↦ if r.val = 10 then 1 else 0

/-- Dot product with the alternating-binomial vector. -/
def max11AlternatingFunctional : (Fin 11 → ℝ) →ₗ[ℝ] ℝ where
  toFun v := ∑ i, max11AlternatingBinomial i * v i
  map_add' x y := by
    simp only [Pi.add_apply, mul_add, Finset.sum_add_distrib]
  map_smul' c x := by
    simp only [RingHom.id_apply, Pi.smul_apply, smul_eq_mul]
    calc
      (∑ i, max11AlternatingBinomial i * (c * x i)) =
          ∑ i, c * (max11AlternatingBinomial i * x i) := by
        apply Finset.sum_congr rfl
        intro i _
        ring
      _ = c * ∑ i, max11AlternatingBinomial i * x i :=
        (Finset.mul_sum _ _ _).symm

private theorem max11AlternatingInt_subsetMaxCoeff_zero (m : Fin 10) :
    (∑ i : Fin 11,
      ((-1 : ℤ) ^ (10 - i.val) * (Nat.choose 10 i.val : ℤ)) *
        (Nat.choose i.val m.val : ℤ)) = 0 := by
  fin_cases m <;> decide

private theorem max11AlternatingInt_targetCoeff :
    (∑ i : Fin 11,
      ((-1 : ℤ) ^ (10 - i.val) * (Nat.choose 10 i.val : ℤ)) *
        (if i.val = 10 then 1 else 0)) = 1 := by
  decide

/-- The alternating-binomial functional annihilates every proper subset-maximum vector. -/
theorem max11AlternatingFunctional_subsetMaxCoeff_zero (m : Fin 10) :
    max11AlternatingFunctional (max11SubsetMaxCoeff m) = 0 := by
  change (∑ i : Fin 11,
    ((-1 : ℝ) ^ (10 - i.val) * (Nat.choose 10 i.val : ℝ)) *
      (Nat.choose i.val m.val : ℝ)) = 0
  exact_mod_cast max11AlternatingInt_subsetMaxCoeff_zero m

/-- The same functional evaluates to one on the MAX11 coefficient vector. -/
theorem max11AlternatingFunctional_targetCoeff :
    max11AlternatingFunctional max11TargetCoeff = 1 := by
  change (∑ i : Fin 11,
    ((-1 : ℝ) ^ (10 - i.val) * (Nat.choose 10 i.val : ℝ)) *
      (if i.val = 10 then 1 else 0)) = 1
  exact_mod_cast max11AlternatingInt_targetCoeff

/-- MAX11's ordered-chamber coefficient vector is outside the span of all proper subset maxima. -/
theorem max11TargetCoeff_not_mem_properSubsetMaxSpan :
    max11TargetCoeff ∉
      Submodule.span ℝ (Set.range max11SubsetMaxCoeff) := by
  apply not_mem_span_range_of_linear_separator
    max11SubsetMaxCoeff max11TargetCoeff max11AlternatingFunctional
  · exact max11AlternatingFunctional_subsetMaxCoeff_zero
  · rw [max11AlternatingFunctional_targetCoeff]
    norm_num

end ReluDepth
