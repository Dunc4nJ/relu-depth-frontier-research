/-
Copyright (c) 2026 relu-depth-frontier-research contributors. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: relu-depth-frontier-research contributors
-/
import Formalization.Basic
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Data.Fintype.Prod
import Mathlib.Tactic.Order
import Mathlib.Tactic.Ring

/-! # A skip-free compiler for finite rank-two maximum blocks

This file formalizes the architecture bridge used by the MAX certificates.  Starting with any
finite first ReLU layer, it compiles a finite signed sum of binary maxima of affine readouts of that
layer into an ordinary second ReLU layer with three neurons per block.  In particular, negative
outer coefficients remain ordinary affine output weights; they do not require negative activations
or skip connections.

This theorem does not assert that any certificate identity is true, and it does not construct a
MAX11 identity.
-/

namespace ReluDepth

open scoped BigOperators

/-- A finite affine form. -/
def affine {ι : Type*} [Fintype ι] (w x : ι → ℝ) (b : ℝ) : ℝ :=
  (∑ i, w i * x i) + b

/-- The parameters of one ordinary affine-to-ReLU layer. -/
structure FirstLayer (Input Hidden : Type*) where
  weight : Hidden → Input → ℝ
  bias : Hidden → ℝ

/-- Evaluation of a finite first ReLU layer. -/
def FirstLayer.eval {Input Hidden : Type*} [Fintype Input]
    (layer : FirstLayer Input Hidden) (x : Input → ℝ) (h : Hidden) : ℝ :=
  relu (affine (layer.weight h) x (layer.bias h))

/-- Parameters for a feed-forward affine–ReLU–affine–ReLU–affine architecture.

Finiteness and positive hidden widths are statement-match obligations on the index types; they are
not fields of this bare parameter record.  The pair specialization below proves those obligations
for `n > 0` when the shared-carry second layer is used.
-/
structure TwoHiddenNetwork (Input Hidden₁ Hidden₂ : Type*) where
  first : FirstLayer Input Hidden₁
  secondWeight : Hidden₂ → Hidden₁ → ℝ
  secondBias : Hidden₂ → ℝ
  outputWeight : Hidden₂ → ℝ
  outputBias : ℝ

/-- Evaluation contains no skip connection: the output sees only second-layer activations. -/
def TwoHiddenNetwork.eval {Input Hidden₁ Hidden₂ : Type*}
    [Fintype Input] [Fintype Hidden₁] [Fintype Hidden₂]
    (network : TwoHiddenNetwork Input Hidden₁ Hidden₂) (x : Input → ℝ) : ℝ :=
  affine network.outputWeight
    (fun j ↦ relu (affine (network.secondWeight j) (network.first.eval x)
      (network.secondBias j)))
    network.outputBias

/-- Three disjoint copies of the block index: `U-V`, `V`, and `-V`. -/
abbrev Triple (Block : Type*) := Block ⊕ (Block ⊕ Block)

/-- Compile rank-two affine readouts into three ordinary ReLU neurons per block. -/
def compileRankTwo {Input Hidden Block : Type*}
    (first : FirstLayer Input Hidden)
    (leftWeight rightWeight : Block → Hidden → ℝ)
    (leftBias rightBias outputWeight : Block → ℝ) :
    TwoHiddenNetwork Input Hidden (Triple Block) where
  first := first
  secondWeight
    | Sum.inl q => fun h ↦ leftWeight q h - rightWeight q h
    | Sum.inr (Sum.inl q) => rightWeight q
    | Sum.inr (Sum.inr q) => fun h ↦ -rightWeight q h
  secondBias
    | Sum.inl q => leftBias q - rightBias q
    | Sum.inr (Sum.inl q) => rightBias q
    | Sum.inr (Sum.inr q) => -rightBias q
  outputWeight
    | Sum.inl q => outputWeight q
    | Sum.inr (Sum.inl q) => outputWeight q
    | Sum.inr (Sum.inr q) => -outputWeight q
  outputBias := 0

lemma affine_sub {ι : Type*} [Fintype ι]
    (u v z : ι → ℝ) (a b : ℝ) :
    affine (fun i ↦ u i - v i) z (a - b) = affine u z a - affine v z b := by
  simp only [affine, sub_mul, Finset.sum_sub_distrib]
  ring

lemma affine_neg {ι : Type*} [Fintype ι] (v z : ι → ℝ) (b : ℝ) :
    affine (fun i ↦ -v i) z (-b) = -affine v z b := by
  simp only [affine, neg_mul, Finset.sum_neg_distrib]
  ring

/-- The compiled network is exactly the finite signed sum of the requested binary maxima. -/
theorem compileRankTwo_eval {Input Hidden Block : Type*}
    [Fintype Input] [Fintype Hidden] [Fintype Block]
    (first : FirstLayer Input Hidden)
    (leftWeight rightWeight : Block → Hidden → ℝ)
    (leftBias rightBias outputWeight : Block → ℝ)
    (x : Input → ℝ) :
    (compileRankTwo first leftWeight rightWeight leftBias rightBias outputWeight).eval x =
      ∑ q, outputWeight q *
        max (affine (leftWeight q) (first.eval x) (leftBias q))
          (affine (rightWeight q) (first.eval x) (rightBias q)) := by
  classical
  change (∑ j : Triple Block,
    (compileRankTwo first leftWeight rightWeight leftBias rightBias outputWeight).outputWeight j *
      relu (affine
        ((compileRankTwo first leftWeight rightWeight leftBias rightBias
          outputWeight).secondWeight j)
        (first.eval x)
        ((compileRankTwo first leftWeight rightWeight leftBias rightBias
          outputWeight).secondBias j))) + 0 = _
  simp only [compileRankTwo, Fintype.sum_sum_type]
  simp_rw [affine_sub, affine_neg, max_eq_three_relu]
  rw [← Finset.sum_add_distrib, ← Finset.sum_add_distrib]
  simp only [add_zero]
  apply Finset.sum_congr rfl
  intro q _
  ring

/-- The compiler's second hidden index has exactly three copies of the block index. -/
theorem triple_card (Block : Type*) [Fintype Block] :
    Fintype.card (Triple Block) = 3 * Fintype.card Block := by
  simp [Triple]
  omega

/-- A coordinate selector, used to make every claimed affine weight explicit. -/
def basisWeight {ι : Type*} [DecidableEq ι] (i : ι) (j : ι) : ℝ :=
  if j = i then 1 else 0

@[simp] lemma affine_basisWeight {ι : Type*} [Fintype ι] [DecidableEq ι]
    (i : ι) (z : ι → ℝ) : affine (basisWeight i) z 0 = z i := by
  simp [affine, basisWeight]

lemma affine_basis_sub {ι : Type*} [Fintype ι] [DecidableEq ι]
    (i j : ι) (z : ι → ℝ) :
    affine (fun h ↦ basisWeight i h - basisWeight j h) z 0 = z i - z j := by
  simpa using affine_sub (basisWeight i) (basisWeight j) z 0 0

lemma affine_basis_add_sub {ι : Type*} [Fintype ι] [DecidableEq ι]
    (i j k : ι) (z : ι → ℝ) :
    affine (fun h ↦ basisWeight i h + basisWeight j h - basisWeight k h) z 0 =
      z i + z j - z k := by
  simp only [affine, add_mul, sub_mul, Finset.sum_add_distrib, Finset.sum_sub_distrib]
  simp [basisWeight]

/-- Canonically oriented non-loop coordinate pairs. -/
abbrev StrictPair (n : ℕ) := {p : Fin n × Fin n // p.1 < p.2}

/-- Shared first-layer neurons: one per unordered non-loop pair and two per coordinate. -/
abbrev PairFirstIndex (n : ℕ) := StrictPair n ⊕ (Fin n ⊕ Fin n)

/-- The explicit shared first layer.

The three summands respectively compute `ReLU(xᵢ-xⱼ)` for `i<j`, `ReLU(xᵢ)`,
and `ReLU(-xᵢ)`.  Every bias is zero.
-/
def pairFirstLayer (n : ℕ) : FirstLayer (Fin n) (PairFirstIndex n) where
  weight
    | Sum.inl p => fun i ↦ basisWeight p.1.1 i - basisWeight p.1.2 i
    | Sum.inr (Sum.inl j) => basisWeight j
    | Sum.inr (Sum.inr j) => fun i ↦ -basisWeight j i
  bias := fun _ ↦ 0

@[simp] theorem pairFirstLayer_strict_eval (n : ℕ) (x : Fin n → ℝ) (p : StrictPair n) :
    (pairFirstLayer n).eval x (Sum.inl p) = relu (x p.1.1 - x p.1.2) := by
  rw [FirstLayer.eval]
  simp only [pairFirstLayer, affine_basis_sub]

@[simp] theorem pairFirstLayer_pos_eval (n : ℕ) (x : Fin n → ℝ) (i : Fin n) :
    (pairFirstLayer n).eval x (Sum.inr (Sum.inl i)) = relu (x i) := by
  rw [FirstLayer.eval]
  simp only [pairFirstLayer, affine_basisWeight]

@[simp] theorem pairFirstLayer_neg_eval (n : ℕ) (x : Fin n → ℝ) (i : Fin n) :
    (pairFirstLayer n).eval x (Sum.inr (Sum.inr i)) = relu (-x i) := by
  rw [FirstLayer.eval]
  simp [pairFirstLayer, affine, basisWeight]

/-- Linear readout weights that recover `max(xₐ,xᵦ)` from the shared first layer.

The definition accepts loops and either endpoint order.  A loop uses only the positive/negative
coordinate transport neurons.
-/
def pairReadoutWeight {n : ℕ} (a b : Fin n) : PairFirstIndex n → ℝ :=
  if hab : a < b then
    fun h ↦ basisWeight (Sum.inl ⟨(a, b), hab⟩) h +
      basisWeight (Sum.inr (Sum.inl b)) h - basisWeight (Sum.inr (Sum.inr b)) h
  else if hba : b < a then
    fun h ↦ basisWeight (Sum.inl ⟨(b, a), hba⟩) h +
      basisWeight (Sum.inr (Sum.inl a)) h - basisWeight (Sum.inr (Sum.inr a)) h
  else
    fun h ↦ basisWeight (Sum.inr (Sum.inl a)) h - basisWeight (Sum.inr (Sum.inr a)) h

/-- The corresponding affine readout; its bias is zero. -/
def pairReadout {n : ℕ} (a b : Fin n) (z : PairFirstIndex n → ℝ) : ℝ :=
  affine (pairReadoutWeight a b) z 0

/-- A pairwise maximum is exactly recovered for loops and both endpoint orders. -/
theorem pairReadout_pairFirstLayer_eq_max {n : ℕ} (a b : Fin n) (x : Fin n → ℝ) :
    pairReadout a b ((pairFirstLayer n).eval x) = max (x a) (x b) := by
  classical
  by_cases hab : a < b
  · rw [pairReadout, pairReadoutWeight, dif_pos hab,
      affine_basis_add_sub, pairFirstLayer_strict_eval,
      pairFirstLayer_pos_eval, pairFirstLayer_neg_eval]
    calc
      relu (x a - x b) + relu (x b) - relu (-x b) =
          relu (x a - x b) + (relu (x b) - relu (-x b)) := by ring
      _ = max (x a) (x b) := (max_eq_three_relu (x a) (x b)).symm
  · by_cases hba : b < a
    · rw [pairReadout, pairReadoutWeight, dif_neg hab, dif_pos hba,
        affine_basis_add_sub, pairFirstLayer_strict_eval,
        pairFirstLayer_pos_eval, pairFirstLayer_neg_eval]
      calc
        relu (x b - x a) + relu (x a) - relu (-x a) =
            relu (x b - x a) + (relu (x a) - relu (-x a)) := by ring
        _ = max (x b) (x a) := (max_eq_three_relu (x b) (x a)).symm
        _ = max (x a) (x b) := max_comm _ _
    · have heq : a = b := le_antisymm (not_lt.mp hba) (not_lt.mp hab)
      subst b
      rw [pairReadout, pairReadoutWeight, dif_neg (lt_irrefl a),
        dif_neg (lt_irrefl a), affine_basis_sub,
        pairFirstLayer_pos_eval, pairFirstLayer_neg_eval,
        relu_sub_relu_neg, max_self]

/-- Sum the readout weights for a list of pairs; lists intentionally retain repetitions. -/
def pairSideWeight {n : ℕ} : List (Fin n × Fin n) → PairFirstIndex n → ℝ
  | [], _ => 0
  | p :: ps, h => pairReadoutWeight p.1 p.2 h + pairSideWeight ps h

/-- The semantic side sum, retaining repetitions and allowing the empty list. -/
def pairSideValue {n : ℕ} (pairs : List (Fin n × Fin n)) (x : Fin n → ℝ) : ℝ :=
  (pairs.map fun p ↦ max (x p.1) (x p.2)).sum

lemma affine_add_zero {ι : Type*} [Fintype ι] (u v z : ι → ℝ) :
    affine (fun i ↦ u i + v i) z 0 = affine u z 0 + affine v z 0 := by
  simp [affine, add_mul, Finset.sum_add_distrib]

/-- The summed first-layer readout is exactly the requested repeated-pair side sum. -/
theorem pairSideWeight_pairFirstLayer_eq {n : ℕ}
    (pairs : List (Fin n × Fin n)) (x : Fin n → ℝ) :
    affine (pairSideWeight pairs) ((pairFirstLayer n).eval x) 0 = pairSideValue pairs x := by
  induction pairs with
  | nil => simp [pairSideWeight, pairSideValue, affine]
  | cons p ps ih =>
      simp only [pairSideWeight]
      rw [affine_add_zero]
      change pairReadout p.1 p.2 ((pairFirstLayer n).eval x) +
        affine (pairSideWeight ps) ((pairFirstLayer n).eval x) 0 = _
      rw [pairReadout_pairFirstLayer_eq_max, ih]
      simp [pairSideValue]

/-- Compile a finite signed family of pairwise-maximum atoms into the two-layer parameter record.

For an empty block family its modular `Triple Block` second index is empty.  Use
`compilePairAtomsSharedCarry` below when the campaign's strictly positive-width convention must hold
without assuming a nonempty block family.
-/
def compilePairAtoms {n : ℕ} {Block : Type*}
    (leftPairs rightPairs : Block → List (Fin n × Fin n))
    (outputWeight : Block → ℝ) :
    TwoHiddenNetwork (Fin n) (PairFirstIndex n) (Triple Block) :=
  compileRankTwo (pairFirstLayer n)
    (fun q ↦ pairSideWeight (leftPairs q))
    (fun q ↦ pairSideWeight (rightPairs q))
    (fun _ ↦ 0) (fun _ ↦ 0) outputWeight

/-- Fully expanded semantic correctness of the pair-atom compiler. -/
theorem compilePairAtoms_eval {n : ℕ} {Block : Type*} [Fintype Block]
    (leftPairs rightPairs : Block → List (Fin n × Fin n))
    (outputWeight : Block → ℝ) (x : Fin n → ℝ) :
    (compilePairAtoms leftPairs rightPairs outputWeight).eval x =
      ∑ q, outputWeight q *
        max (pairSideValue (leftPairs q) x) (pairSideValue (rightPairs q) x) := by
  change (compileRankTwo (pairFirstLayer n)
    (fun q ↦ pairSideWeight (leftPairs q))
    (fun q ↦ pairSideWeight (rightPairs q))
    (fun _ ↦ 0) (fun _ ↦ 0) outputWeight).eval x = _
  rw [compileRankTwo_eval]
  simp_rw [pairSideWeight_pairFirstLayer_eq]

/-- The shared first hidden index is the strict-pair index plus two copies of the coordinates. -/
theorem pairFirstIndex_card_decompose (n : ℕ) :
    Fintype.card (PairFirstIndex n) = Fintype.card (StrictPair n) + 2 * n := by
  simp [PairFirstIndex, StrictPair]
  omega

/-- There is one strict-pair feature for each two-element coordinate subset. -/
theorem strictPair_card (n : ℕ) :
    Fintype.card (StrictPair n) = n.choose 2 := by
  classical
  rw [Fintype.card_subtype]
  simpa using (Fintype.card_product_filter_lt (α := Fin n))

/-- Exact first-layer width of the modular pair-atom compiler. -/
theorem pairFirstIndex_card (n : ℕ) :
    Fintype.card (PairFirstIndex n) = n.choose 2 + 2 * n := by
  rw [pairFirstIndex_card_decompose, strictPair_card]

/-- For every target arity `n ≥ 1`, the pair compiler's first hidden layer has positive width. -/
theorem pairFirstIndex_card_pos {n : ℕ} (hn : 0 < n) :
    0 < Fintype.card (PairFirstIndex n) := by
  rw [pairFirstIndex_card]
  omega

/-! ## A smaller scalar-output compiler

The modular construction above exposes every atom as a separate reusable three-neuron block.  For a
single scalar signed sum, the affine carry terms can instead be combined before the second ReLU
layer.  Two neurons transport that one combined affine value, and only one hinge neuron is needed
per block.  This reduces the second width from `3 * card Block` to `card Block + 2` without changing
the represented function.
-/

/-- Weighted sum of a finite family of affine weight rows. -/
def weightedFamilyWeight {Hidden Block : Type*} [Fintype Block]
    (coefficient : Block → ℝ) (weight : Block → Hidden → ℝ) : Hidden → ℝ :=
  fun h ↦ ∑ q, coefficient q * weight q h

/-- Weighted sum of the corresponding biases. -/
def weightedFamilyBias {Block : Type*} [Fintype Block]
    (coefficient bias : Block → ℝ) : ℝ :=
  ∑ q, coefficient q * bias q

lemma affine_weightedFamily {Hidden Block : Type*} [Fintype Hidden] [Fintype Block]
    (coefficient : Block → ℝ) (weight : Block → Hidden → ℝ) (bias : Block → ℝ)
    (z : Hidden → ℝ) :
    affine (weightedFamilyWeight coefficient weight) z
        (weightedFamilyBias coefficient bias) =
      ∑ q, coefficient q * affine (weight q) z (bias q) := by
  classical
  simp only [affine, weightedFamilyWeight, weightedFamilyBias, Finset.sum_mul,
    Finset.mul_sum, mul_add, Finset.sum_add_distrib]
  rw [Finset.sum_comm]
  apply congrArg₂ (· + ·)
  · apply Finset.sum_congr rfl
    intro q _
    apply Finset.sum_congr rfl
    intro h _
    ring
  · rfl

/-- Two global carry neurons plus one block-specific hinge neuron. -/
abbrev SharedCarryIndex (Block : Type*) := Fin 2 ⊕ Block

/-- Compile the same signed rank-two family using a shared affine carry.

The two `Fin 2` neurons compute `ReLU(R)` and `ReLU(-R)` for the combined right-side affine
readout `R = sum_q outputWeight_q * V_q`.  Each remaining neuron computes `ReLU(U_q-V_q)`.
-/
def compileRankTwoSharedCarry {Input Hidden Block : Type*} [Fintype Block]
    (first : FirstLayer Input Hidden)
    (leftWeight rightWeight : Block → Hidden → ℝ)
    (leftBias rightBias outputWeight : Block → ℝ) :
    TwoHiddenNetwork Input Hidden (SharedCarryIndex Block) where
  first := first
  secondWeight
    | Sum.inl i => if i = 0 then
        weightedFamilyWeight outputWeight rightWeight
      else
        fun h ↦ -weightedFamilyWeight outputWeight rightWeight h
    | Sum.inr q => fun h ↦ leftWeight q h - rightWeight q h
  secondBias
    | Sum.inl i => if i = 0 then
        weightedFamilyBias outputWeight rightBias
      else
        -weightedFamilyBias outputWeight rightBias
    | Sum.inr q => leftBias q - rightBias q
  outputWeight
    | Sum.inl i => if i = 0 then 1 else -1
    | Sum.inr q => outputWeight q
  outputBias := 0

/-- Exact semantic correctness of the shared-carry compiler. -/
theorem compileRankTwoSharedCarry_eval {Input Hidden Block : Type*}
    [Fintype Input] [Fintype Hidden] [Fintype Block]
    (first : FirstLayer Input Hidden)
    (leftWeight rightWeight : Block → Hidden → ℝ)
    (leftBias rightBias outputWeight : Block → ℝ)
    (x : Input → ℝ) :
    (compileRankTwoSharedCarry first leftWeight rightWeight leftBias rightBias
      outputWeight).eval x =
      ∑ q, outputWeight q *
        max (affine (leftWeight q) (first.eval x) (leftBias q))
          (affine (rightWeight q) (first.eval x) (rightBias q)) := by
  classical
  let rightCarry := ∑ q, outputWeight q *
    affine (rightWeight q) (first.eval x) (rightBias q)
  change (∑ j : SharedCarryIndex Block,
    (compileRankTwoSharedCarry first leftWeight rightWeight leftBias rightBias
      outputWeight).outputWeight j *
      relu (affine
        ((compileRankTwoSharedCarry first leftWeight rightWeight leftBias rightBias
          outputWeight).secondWeight j)
        (first.eval x)
        ((compileRankTwoSharedCarry first leftWeight rightWeight leftBias rightBias
          outputWeight).secondBias j))) + 0 = _
  simp only [compileRankTwoSharedCarry, Fintype.sum_sum_type, Fin.sum_univ_two,
    if_neg (by decide : (1 : Fin 2) ≠ 0), if_true, one_mul, neg_mul, add_zero]
  rw [affine_weightedFamily]
  rw [affine_neg]
  rw [affine_weightedFamily]
  simp_rw [affine_sub]
  change relu rightCarry - relu (-rightCarry) +
      (∑ q, outputWeight q *
        relu (affine (leftWeight q) (first.eval x) (leftBias q) -
          affine (rightWeight q) (first.eval x) (rightBias q))) = _
  rw [relu_sub_relu_neg]
  change (∑ q, outputWeight q *
      affine (rightWeight q) (first.eval x) (rightBias q)) + _ = _
  rw [← Finset.sum_add_distrib]
  apply Finset.sum_congr rfl
  intro q _
  rw [max_eq_relu_sub_add]
  ring

/-- The smaller compiler always has two carry neurons, including for an empty block family. -/
theorem sharedCarryIndex_card (Block : Type*) [Fintype Block] :
    Fintype.card (SharedCarryIndex Block) = Fintype.card Block + 2 := by
  simp [SharedCarryIndex]
  omega

/-- The shared-carry second hidden layer has positive width even for an empty block family. -/
theorem sharedCarryIndex_card_pos (Block : Type*) [Fintype Block] :
    0 < Fintype.card (SharedCarryIndex Block) := by
  rw [sharedCarryIndex_card]
  omega

/-- Pair-atom specialization of the shared-carry construction. -/
def compilePairAtomsSharedCarry {n : ℕ} {Block : Type*} [Fintype Block]
    (leftPairs rightPairs : Block → List (Fin n × Fin n))
    (outputWeight : Block → ℝ) :
    TwoHiddenNetwork (Fin n) (PairFirstIndex n) (SharedCarryIndex Block) :=
  compileRankTwoSharedCarry (pairFirstLayer n)
    (fun q ↦ pairSideWeight (leftPairs q))
    (fun q ↦ pairSideWeight (rightPairs q))
    (fun _ ↦ 0) (fun _ ↦ 0) outputWeight

/-- Fully expanded correctness of the smaller pair-atom compiler. -/
theorem compilePairAtomsSharedCarry_eval {n : ℕ} {Block : Type*} [Fintype Block]
    (leftPairs rightPairs : Block → List (Fin n × Fin n))
    (outputWeight : Block → ℝ) (x : Fin n → ℝ) :
    (compilePairAtomsSharedCarry leftPairs rightPairs outputWeight).eval x =
      ∑ q, outputWeight q *
        max (pairSideValue (leftPairs q) x) (pairSideValue (rightPairs q) x) := by
  change (compileRankTwoSharedCarry (pairFirstLayer n)
    (fun q ↦ pairSideWeight (leftPairs q))
    (fun q ↦ pairSideWeight (rightPairs q))
    (fun _ ↦ 0) (fun _ ↦ 0) outputWeight).eval x = _
  rw [compileRankTwoSharedCarry_eval]
  simp_rw [pairSideWeight_pairFirstLayer_eq]

end ReluDepth
