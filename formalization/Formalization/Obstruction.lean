/-
Copyright (c) 2026 relu-depth-frontier-research contributors. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: relu-depth-frontier-research contributors
-/
import Formalization.Basic
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.LinearAlgebra.FiniteDimensional.Defs
import Mathlib.LinearAlgebra.Span.Basic

/-! # Abstract obstruction lemmas

This module formalizes two stable logical steps used by the bounded MAX11 obstruction:

* adding the same real-valued term to both branches of a maximum pulls that term outside;
* a real linear functional that kills every member of a finite generator family, but not a target,
  separates the target from the family's real linear span.

The theorems are deliberately abstract.  They do not import or check the campaign's large integer
matrix, its rational dual certificate, the graph-family enumeration, or a MAX11 definition.
-/

namespace ReluDepth

open scoped BigOperators

/-- A common real addend pulls through a binary maximum. -/
theorem max_add_common (u v h : ℝ) :
    max (u + h) (v + h) = h + max u v := by
  by_cases huv : u ≤ v
  · calc
      max (u + h) (v + h) = v + h := max_eq_right (add_le_add_left huv h)
      _ = h + v := add_comm v h
      _ = h + max u v := by rw [max_eq_right huv]
  · have hvu : v ≤ u := le_of_not_ge huv
    calc
      max (u + h) (v + h) = u + h := max_eq_left (add_le_add_left hvu h)
      _ = h + u := add_comm u h
      _ = h + max u v := by rw [max_eq_left hvu]

/-- Pointwise common-addend collapse for real-valued functions. -/
theorem max_add_common_fun {X : Type*} (u v h : X → ℝ) :
    (fun x ↦ max (u x + h x) (v x + h x)) =
      fun x ↦ h x + max (u x) (v x) := by
  funext x
  exact max_add_common (u x) (v x) (h x)

/-- Summing common-addend collapses over any finite index set. -/
theorem sum_max_add_common {ι : Type*} (s : Finset ι) (u v h : ι → ℝ) :
    (∑ i ∈ s, max (u i + h i) (v i + h i)) =
      (∑ i ∈ s, h i) + ∑ i ∈ s, max (u i) (v i) := by
  calc
    (∑ i ∈ s, max (u i + h i) (v i + h i)) =
        ∑ i ∈ s, (h i + max (u i) (v i)) := by
      apply Finset.sum_congr rfl
      intro i _
      exact max_add_common (u i) (v i) (h i)
    _ = (∑ i ∈ s, h i) + ∑ i ∈ s, max (u i) (v i) :=
      Finset.sum_add_distrib

/-- Finite symmetrization of the common-addend identity, as equality of functions. -/
theorem sum_max_add_common_fun {ι X : Type*} (s : Finset ι)
    (u v h : ι → X → ℝ) :
    (fun x ↦ ∑ i ∈ s, max (u i x + h i x) (v i x + h i x)) =
      fun x ↦ (∑ i ∈ s, h i x) + ∑ i ∈ s, max (u i x) (v i x) := by
  funext x
  exact sum_max_add_common s (fun i ↦ u i x) (fun i ↦ v i x) (fun i ↦ h i x)

/--
A real linear separator excludes a target from the span of an indexed generator family.

`Submodule.span ℝ` is the span under arbitrary real coefficients.  The ambient real module and the
index type need not be finite-dimensional or finite; the theorem below specializes it to `Fin n`.
-/
theorem not_mem_span_range_of_linear_separator
    {ι V : Type*} [AddCommGroup V] [Module ℝ V]
    (generator : ι → V) (target : V) (separator : V →ₗ[ℝ] ℝ)
    (h_generator : ∀ i, separator (generator i) = 0)
    (h_target : separator target ≠ 0) :
    target ∉ Submodule.span ℝ (Set.range generator) := by
  intro h_target_mem
  have h_span_ker : Submodule.span ℝ (Set.range generator) ≤ LinearMap.ker separator := by
    rw [Submodule.span_le]
    intro value h_value
    rcases h_value with ⟨i, rfl⟩
    exact h_generator i
  have h_target_zero : separator target = 0 := h_span_ker h_target_mem
  exact h_target h_target_zero

/-- The finite-dimensional specialization of `not_mem_span_range_of_linear_separator`. -/
theorem finiteDimensional_not_mem_span_range_of_linear_separator
    {n : ℕ} {V : Type*} [AddCommGroup V] [Module ℝ V] [FiniteDimensional ℝ V]
    (generator : Fin n → V) (target : V) (separator : V →ₗ[ℝ] ℝ)
    (h_generator : ∀ i, separator (generator i) = 0)
    (h_target : separator target ≠ 0) :
    target ∉ Submodule.span ℝ (Set.range generator) :=
  not_mem_span_range_of_linear_separator generator target separator h_generator h_target

/-- Pointwise-equal indexed families have equal real spans. -/
theorem span_range_eq_of_pointwise_eq
    {ι V : Type*} [AddCommGroup V] [Module ℝ V]
    (left right : ι → V) (h : ∀ i, left i = right i) :
    Submodule.span ℝ (Set.range left) = Submodule.span ℝ (Set.range right) := by
  have h_family : left = right := funext h
  rw [h_family]

/--
Adding a family whose members are pointwise replacements from a base family does not enlarge the
real span.  Taking `V` to be a function space makes the equality one of function spans.
-/
theorem span_union_range_eq_of_replacement
    {α β V : Type*} [AddCommGroup V] [Module ℝ V]
    (base : α → V) (extra : β → V) (replacement : β → α)
    (h_replacement : ∀ b, extra b = base (replacement b)) :
    Submodule.span ℝ (Set.range base ∪ Set.range extra) =
      Submodule.span ℝ (Set.range base) := by
  apply le_antisymm
  · rw [Submodule.span_le]
    intro value h_value
    rcases h_value with h_base | h_extra
    · exact Submodule.subset_span h_base
    · rcases h_extra with ⟨b, rfl⟩
      rw [h_replacement b]
      exact Submodule.subset_span ⟨replacement b, rfl⟩
  · exact Submodule.span_mono Set.subset_union_left

end ReluDepth
