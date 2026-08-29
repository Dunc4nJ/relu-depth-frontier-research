/-
Copyright (c) 2026 relu-depth-frontier-research contributors. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: relu-depth-frontier-research contributors
-/
import Mathlib.Data.Real.Basic

/-! # Known-answer ReLU identities

This module is a smoke test for the pinned Lean/Mathlib rail. It proves elementary scalar identities
used by the eventual skip-free compiler and makes no claim about any retained certificate or MAX11.
-/

namespace ReluDepth

/-- Scalar ReLU, pinned to the convention used by this campaign. -/
def relu (x : ℝ) : ℝ := max x 0

/-- Known-answer smoke theorem: a binary maximum is one ReLU plus an affine skip. -/
theorem max_eq_relu_sub_add (x y : ℝ) :
    max x y = relu (x - y) + y := by
  by_cases h : y ≤ x
  · rw [max_eq_left h]
    simp [relu, max_eq_left (sub_nonneg.mpr h)]
  · have hxy : x ≤ y := le_of_not_ge h
    rw [max_eq_right hxy]
    simp [relu, max_eq_right (sub_nonpos.mpr hxy)]

/-- A scalar affine value can be transported through a ReLU layer without a skip connection. -/
theorem relu_sub_relu_neg (x : ℝ) : relu x - relu (-x) = x := by
  by_cases h : 0 ≤ x
  · have hn : -x ≤ 0 := neg_nonpos.mpr h
    simp [relu, max_eq_left h, max_eq_right hn]
  · have hx : x ≤ 0 := le_of_not_ge h
    have hnx : 0 ≤ -x := neg_nonneg.mpr hx
    simp [relu, max_eq_right hx, max_eq_left hnx]

/-- Skip-free binary maximum: three ReLU outputs followed by an affine combination. -/
theorem max_eq_three_relu (x y : ℝ) :
    max x y = relu (x - y) + (relu y - relu (-y)) := by
  calc
    max x y = relu (x - y) + y := max_eq_relu_sub_add x y
    _ = relu (x - y) + (relu y - relu (-y)) :=
      congrArg (fun z : ℝ ↦ relu (x - y) + z) (relu_sub_relu_neg y).symm

end ReluDepth
