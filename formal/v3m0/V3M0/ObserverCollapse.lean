import V3M0.Common

namespace V3M0

open Matrix
open scoped BigOperators ComplexConjugate

/-!
# Conditional observer collapse and gauge quotient

This module separates three logically different facts.

* Surjectivity of the positive-frequency `h` frame only identifies the
  **output** range `range (inc ∘ Bₕ) = range inc`.
* Identifying the right-singular subspace after mapping it back to `h`
  additionally needs the frozen whitening/coisometry bridge
  `Bₕ ∘ Bₕ† = id`.  Surjectivity alone is insufficient: for
  `inc = [1 0]` and `B = [[1,1],[0,1]]`, `B` is invertible but the mapped-back
  right-singular line is `span (2,1)`, not `range inc† = span (1,0)`.
* The squared principal-sine multiplicities are computed from the explicit
  orthogonal `TT₂ ⊕ Gauge₄ ⊕ Row₄` block projectors.  No square root,
  inverse-cosine angle reconstruction, Floquet-stability assertion,
  numerical rank threshold, or SVD gap
  is formalized here.
-/

section OutputRange

variable {E H C : Type*}
variable [NormedAddCommGroup E] [NormedAddCommGroup H] [NormedAddCommGroup C]
variable [InnerProductSpace ℂ E] [InnerProductSpace ℂ H] [InnerProductSpace ℂ C]
variable [FiniteDimensional ℂ E] [FiniteDimensional ℂ H] [FiniteDimensional ℂ C]

omit [FiniteDimensional ℂ E] [FiniteDimensional ℂ H]
  [FiniteDimensional ℂ C] in
/--
A full positive-frequency `h` frame fills the same curvature output range as
`inc`.  This theorem deliberately says nothing about a mapped-back source
subspace.
-/
theorem range_inc_comp_of_surjective
    (inc : H →ₗ[ℂ] C) (B : E →ₗ[ℂ] H)
    (hB : Function.Surjective B) :
    (inc ∘ₗ B).range = inc.range := by
  apply LinearMap.range_comp_of_range_eq_top
  exact LinearMap.range_eq_top_of_surjective B hB

/--
The exact nonzero squared-singular source support of `A` is
`range (A† A) = range A†`.  A numerical SVD implementation still has to
certify that its frozen threshold selected exactly this range.
-/
theorem nonzero_gram_range_eq_adjoint_range (A : E →ₗ[ℂ] C) :
    (A.adjoint ∘ₗ A).range = A.adjoint.range :=
  A.range_adjoint_comp_self

/--
The exact nonzero right-singular support of `inc ∘ B`, mapped back through
`B`.  Encoding the Gram range makes the nonzero-spectrum selection explicit;
it does not introduce a floating-point threshold into Lean.
-/
noncomputable def exactSelectedCurvature
    (inc : H →ₗ[ℂ] C) (B : E →ₗ[ℂ] H) : Submodule ℂ H :=
  let A := inc ∘ₗ B
  (B ∘ₗ (A.adjoint ∘ₗ A)).range

/--
Before any coisometry assumption, exact nonzero-Gram selection maps back to
the range of `(B B†) inc†`.  This is the unconditional third layer between
output-range saturation and observer collapse.
-/
theorem exactSelectedCurvature_eq_mapped_adjoint_range
    (inc : H →ₗ[ℂ] C) (B : E →ₗ[ℂ] H) :
    exactSelectedCurvature inc B =
      ((B ∘ₗ B.adjoint) ∘ₗ inc.adjoint).range := by
  dsimp only [exactSelectedCurvature]
  let A := inc ∘ₗ B
  calc
    (B ∘ₗ (A.adjoint ∘ₗ A)).range =
        (B ∘ₗ A.adjoint).range := by
      rw [LinearMap.range_comp, A.range_adjoint_comp_self,
        ← LinearMap.range_comp]
    _ = ((B ∘ₗ B.adjoint) ∘ₗ inc.adjoint).range := by
      congr 1
      dsimp only [A]
      rw [LinearMap.adjoint_comp, ← LinearMap.comp_assoc]

/--
The map-level algebra behind observer collapse.  The extra coisometry premise
is essential; bare surjectivity cannot replace it.
-/
theorem selected_nonzero_gram_range
    (inc : H →ₗ[ℂ] C) (B : E →ₗ[ℂ] H)
    (hcoiso : B ∘ₗ B.adjoint = LinearMap.id) :
    exactSelectedCurvature inc B = inc.adjoint.range := by
  rw [exactSelectedCurvature_eq_mapped_adjoint_range, hcoiso,
    LinearMap.id_comp]

omit [FiniteDimensional ℂ C] in
/-- Rank-nullity turns ambient dimension ten and image rank six into a
four-dimensional kernel. -/
theorem ker_finrank_four
    (inc : H →ₗ[ℂ] C)
    (hH : Module.finrank ℂ H = 10)
    (hrange : Module.finrank ℂ inc.range = 6) :
    Module.finrank ℂ inc.ker = 4 := by
  have h := inc.finrank_range_add_finrank_ker
  omega

omit [FiniteDimensional ℂ C] in
/--
If a four-dimensional gauge sector is killed by a rank-six map on a
ten-dimensional metric space, it is the whole kernel.  Thus kernel equality
is derived rather than assumed.
-/
theorem gauge_eq_ker_of_rank
    (inc : H →ₗ[ℂ] C) (gauge : Submodule ℂ H)
    (hH : Module.finrank ℂ H = 10)
    (hrange : Module.finrank ℂ inc.range = 6)
    (hgauge : Module.finrank ℂ gauge = 4)
    (hkilled : gauge ≤ inc.ker) :
    gauge = inc.ker := by
  apply Submodule.eq_of_le_of_finrank_eq hkilled
  rw [hgauge, ker_finrank_four inc hH hrange]

/--
The exact hypotheses carried by the `TT₂ ⊕ Gauge₄ ⊕ Row₄` bridge.  The
orthogonal-complement equality is part of the frozen decomposition
certificate, not a consequence of rank alone.
-/
structure TTGaugeRowDecomposition (H : Type*)
    [NormedAddCommGroup H] [InnerProductSpace ℂ H]
    [FiniteDimensional ℂ H] where
  tt : Submodule ℂ H
  gauge : Submodule ℂ H
  row : Submodule ℂ H
  tt_finrank : Module.finrank ℂ tt = 2
  gauge_finrank : Module.finrank ℂ gauge = 4
  row_finrank : Module.finrank ℂ row = 4
  tt_ortho_gauge : tt ⟂ gauge
  tt_ortho_row : tt ⟂ row
  gauge_ortho_row : gauge ⟂ row
  spans : tt ⊔ gauge ⊔ row = ⊤

/--
The orthogonal complement identity used by observer collapse follows from
the pairwise orthogonality and the frozen `2+4+4=10` dimensions; it is not
stored as an extra conclusion-shaped premise.
-/
theorem TTGaugeRowDecomposition.gauge_orthogonal_eq_tt_sup_row
    (d : TTGaugeRowDecomposition H)
    (hH : Module.finrank ℂ H = 10) :
    d.gaugeᗮ = d.tt ⊔ d.row := by
  have hTR : Module.finrank ℂ ↥(d.tt ⊔ d.row) = 6 := by
    have h := Submodule.finrank_sup_add_finrank_inf_eq d.tt d.row
    rw [d.tt_ortho_row.disjoint.eq_bot, finrank_bot ℂ H,
      d.tt_finrank, d.row_finrank] at h
    omega
  have horthRank : Module.finrank ℂ ↥d.gaugeᗮ = 6 := by
    have h := d.gauge.finrank_add_finrank_orthogonal
    rw [d.gauge_finrank, hH] at h
    omega
  have hle : d.tt ⊔ d.row ≤ d.gaugeᗮ :=
    sup_le d.tt_ortho_gauge.le d.gauge_ortho_row.ge
  exact
    (Submodule.eq_of_le_of_finrank_eq hle
      (hTR.trans horthRank.symm)).symm

/--
All conditions needed to identify the evaluator's reported curvature
subspace.  `selection_correct` is the external exact/SVD bridge: it says the
reported nonzero modes equal the exact Gram support, but does not assume the
desired principal spectrum.
-/
structure ObserverCollapseConditions
    (inc : H →ₗ[ℂ] C) (B : E →ₗ[ℂ] H) where
  sectors : TTGaugeRowDecomposition H
  kerC : Submodule ℂ H
  reportedScurv : Submodule ℂ H
  whitened_coisometry : B ∘ₗ B.adjoint = LinearMap.id
  metric_finrank : Module.finrank ℂ H = 10
  inc_rank : Module.finrank ℂ inc.range = 6
  gauge_killed : sectors.gauge ≤ inc.ker
  kerC_eq : kerC = sectors.tt ⊔ sectors.gauge
  selection_correct : reportedScurv = exactSelectedCurvature inc B

/--
The conditional observer-collapse certificate.  It derives, in order:

1. full output range;
2. `ker inc = Gauge₄` by rank-nullity;
3. `range inc† = TT₂ ⊕ Row₄` by the frozen orthogonal decomposition;
4. the reported exact nonzero-spectrum subspace equals `range inc†`;
5. that subspace has rank six.
-/
theorem observerCollapse_subspaces
    (inc : H →ₗ[ℂ] C) (B : E →ₗ[ℂ] H)
    (h : ObserverCollapseConditions inc B) :
    (inc ∘ₗ B).range = inc.range ∧
      inc.ker = h.sectors.gauge ∧
      inc.adjoint.range = h.sectors.tt ⊔ h.sectors.row ∧
      h.reportedScurv = inc.adjoint.range ∧
      h.kerC = h.sectors.tt ⊔ h.sectors.gauge ∧
      Module.finrank ℂ h.reportedScurv = 6 := by
  have hBsurjective : Function.Surjective B := by
    intro y
    refine ⟨B.adjoint y, ?_⟩
    have happly :=
      congrArg (fun f : H →ₗ[ℂ] H => f y) h.whitened_coisometry
    simpa using happly
  have houtput :=
    range_inc_comp_of_surjective inc B hBsurjective
  have hgauge : h.sectors.gauge = inc.ker :=
    gauge_eq_ker_of_rank inc h.sectors.gauge h.metric_finrank h.inc_rank
      h.sectors.gauge_finrank h.gauge_killed
  have hadjoint : inc.adjoint.range = h.sectors.tt ⊔ h.sectors.row := by
    rw [← inc.orthogonal_ker, ← hgauge,
      h.sectors.gauge_orthogonal_eq_tt_sup_row h.metric_finrank]
  have hselected : h.reportedScurv = inc.adjoint.range := by
    rw [h.selection_correct,
      selected_nonzero_gram_range inc B h.whitened_coisometry]
  have hrank : Module.finrank ℂ h.reportedScurv = 6 := by
    rw [hselected, inc.finrank_range_adjoint]
    exact h.inc_rank
  exact ⟨houtput, hgauge.symm, hadjoint, hselected, h.kerC_eq, hrank⟩

end OutputRange

/-! ## Canonical orthogonal block model and squared-sine spectrum -/

abbrev TTIndex := Fin 2
abbrev GaugeIndex := Fin 4
abbrev RowIndex := Fin 4

/-- Canonical metric coordinates: `TT₂ ⊕ (Gauge₄ ⊕ Row₄)`. -/
abbrev MetricSectorIndex := TTIndex ⊕ (GaugeIndex ⊕ RowIndex)

/-- Canonical curvature coordinates: `TT₂ ⊕ Row₄`. -/
abbrev CurvatureSectorIndex := TTIndex ⊕ RowIndex

def ttIndicator : MetricSectorIndex → ℂ
  | Sum.inl _ => 1
  | _ => 0

def gaugeIndicator : MetricSectorIndex → ℂ
  | Sum.inr (Sum.inl _) => 1
  | _ => 0

def rowIndicator : MetricSectorIndex → ℂ
  | Sum.inr (Sum.inr _) => 1
  | _ => 0

def ttSectorProjector : Matrix MetricSectorIndex MetricSectorIndex ℂ :=
  Matrix.diagonal ttIndicator

def gaugeSectorProjector : Matrix MetricSectorIndex MetricSectorIndex ℂ :=
  Matrix.diagonal gaugeIndicator

def rowSectorProjector : Matrix MetricSectorIndex MetricSectorIndex ℂ :=
  Matrix.diagonal rowIndicator

/--
The canonical sector projectors are pairwise orthogonal and resolve the
identity.  Together with the index types `Fin 2`, `Fin 4`, `Fin 4`, this is
the explicit `TT₂ ⊕ Gauge₄ ⊕ Row₄` orthogonal decomposition used below.
-/
theorem canonicalSectorProjectors_decompose :
    ttSectorProjector * gaugeSectorProjector = 0 ∧
      ttSectorProjector * rowSectorProjector = 0 ∧
      gaugeSectorProjector * rowSectorProjector = 0 ∧
      ttSectorProjector + gaugeSectorProjector + rowSectorProjector = 1 := by
  constructor
  · ext i j
    rcases i with i | (i | i) <;> rcases j with j | (j | j) <;>
      simp [ttSectorProjector, gaugeSectorProjector, Matrix.mul_apply,
        Matrix.diagonal, ttIndicator, gaugeIndicator]
  constructor
  · ext i j
    rcases i with i | (i | i) <;> rcases j with j | (j | j) <;>
      simp [ttSectorProjector, rowSectorProjector, Matrix.mul_apply,
        Matrix.diagonal, ttIndicator, rowIndicator]
  constructor
  · ext i j
    rcases i with i | (i | i) <;> rcases j with j | (j | j) <;>
      simp [gaugeSectorProjector, rowSectorProjector, Matrix.mul_apply,
        Matrix.diagonal, gaugeIndicator, rowIndicator]
  · ext i j
    rcases i with i | (i | i) <;> rcases j with j | (j | j) <;>
      simp [ttSectorProjector, gaugeSectorProjector, rowSectorProjector,
        Matrix.diagonal, ttIndicator, gaugeIndicator, rowIndicator,
        Matrix.one_apply]

theorem canonicalSector_dimensions :
    Fintype.card TTIndex = 2 ∧
      Fintype.card GaugeIndex = 4 ∧
      Fintype.card RowIndex = 4 := by
  norm_num

/-- The curvature frame includes TT and Row coordinates and excludes Gauge. -/
def canonicalCurvatureFrame :
    Matrix MetricSectorIndex CurvatureSectorIndex ℂ
  | Sum.inl i, Sum.inl j => if i = j then 1 else 0
  | Sum.inr (Sum.inr i), Sum.inr j => if i = j then 1 else 0
  | _, _ => 0

/-- The canonical TT/Row columns form an isometric frame. -/
theorem canonicalCurvatureFrame_isometric :
    canonicalCurvatureFrameᴴ * canonicalCurvatureFrame = 1 := by
  ext i j
  rcases i with i | i <;> rcases j with j | j
  · by_cases hij : i = j
    · subst j
      simp [canonicalCurvatureFrame, Matrix.mul_apply]
    · have hji : j ≠ i := Ne.symm hij
      simp [canonicalCurvatureFrame, Matrix.mul_apply, hij, hji]
  · simp [canonicalCurvatureFrame, Matrix.mul_apply]
  · simp [canonicalCurvatureFrame, Matrix.mul_apply]
  · by_cases hij : i = j
    · subst j
      simp [canonicalCurvatureFrame, Matrix.mul_apply]
    · have hji : j ≠ i := Ne.symm hij
      simp [canonicalCurvatureFrame, Matrix.mul_apply, hij, hji]

/-- The frozen constraint-compatible projector keeps `TT₂ ⊕ Gauge₄`. -/
def canonicalKerCIndicator : MetricSectorIndex → ℂ
  | Sum.inl _ => 1
  | Sum.inr (Sum.inl _) => 1
  | Sum.inr (Sum.inr _) => 0

def canonicalKerCProjector :
    Matrix MetricSectorIndex MetricSectorIndex ℂ :=
  Matrix.diagonal canonicalKerCIndicator

/--
Only squared principal sines are represented: zero on the shared TT block
and one on the Row block.
-/
def fixedPrincipalSinSq : CurvatureSectorIndex → ℝ
  | Sum.inl _ => 0
  | Sum.inr _ => 1

/--
Frozen squared-sine projector
`I - S_curv† P_kerC S_curv`.
-/
def canonicalPrincipalSinSqKernel :
    Matrix CurvatureSectorIndex CurvatureSectorIndex ℂ :=
  1 - canonicalCurvatureFrameᴴ * canonicalKerCProjector *
    canonicalCurvatureFrame

def fixedPrincipalSinSqMatrix :
    Matrix CurvatureSectorIndex CurvatureSectorIndex ℂ :=
  Matrix.diagonal (fun i => (fixedPrincipalSinSq i : ℂ))

/--
The frozen projector compression is exactly the block diagonal
`0_(Fin 2) ⊕ I_(Fin 4)`.  This is the calculation from which the spectrum is
derived; the target eigenvalue list is not a hypothesis.
-/
theorem canonicalPrincipalSinSqKernel_eq_diagonal :
    canonicalPrincipalSinSqKernel = fixedPrincipalSinSqMatrix := by
  ext i j
  rcases i with i | i <;> rcases j with j | j
  · by_cases hij : i = j
    · simp [canonicalPrincipalSinSqKernel, canonicalCurvatureFrame,
        canonicalKerCProjector, canonicalKerCIndicator,
        fixedPrincipalSinSqMatrix, fixedPrincipalSinSq, Matrix.mul_apply,
        Matrix.diagonal, hij]
    · have hji : j ≠ i := Ne.symm hij
      simp [canonicalPrincipalSinSqKernel, canonicalCurvatureFrame,
        canonicalKerCProjector, canonicalKerCIndicator,
        fixedPrincipalSinSqMatrix, fixedPrincipalSinSq, Matrix.mul_apply,
        Matrix.diagonal, hij, hji]
  · simp [canonicalPrincipalSinSqKernel, canonicalCurvatureFrame,
      canonicalKerCProjector, fixedPrincipalSinSqMatrix,
      fixedPrincipalSinSq, Matrix.mul_apply, Matrix.diagonal]
  · simp [canonicalPrincipalSinSqKernel, canonicalCurvatureFrame,
      canonicalKerCProjector, fixedPrincipalSinSqMatrix,
      fixedPrincipalSinSq, Matrix.mul_apply, Matrix.diagonal]
  · by_cases hij : i = j
    · simp [canonicalPrincipalSinSqKernel, canonicalCurvatureFrame,
        canonicalKerCProjector, canonicalKerCIndicator,
        fixedPrincipalSinSqMatrix, fixedPrincipalSinSq, Matrix.mul_apply,
        Matrix.diagonal, hij]
    · simp [canonicalPrincipalSinSqKernel, canonicalCurvatureFrame,
        canonicalKerCProjector, canonicalKerCIndicator,
        fixedPrincipalSinSqMatrix, fixedPrincipalSinSq, Matrix.mul_apply,
        Matrix.diagonal, hij]

theorem fixedPrincipalSinSqMatrix_isHermitian :
    fixedPrincipalSinSqMatrix.IsHermitian := by
  unfold fixedPrincipalSinSqMatrix
  rw [Matrix.isHermitian_diagonal_iff]
  intro i
  rcases i with i | i <;> simp [fixedPrincipalSinSq]

theorem canonicalPrincipalSinSqKernel_isHermitian :
    canonicalPrincipalSinSqKernel.IsHermitian := by
  rw [canonicalPrincipalSinSqKernel_eq_diagonal]
  exact fixedPrincipalSinSqMatrix_isHermitian

/--
Polynomial form of the conditional squared-sine spectrum: zero has
multiplicity two and one has multiplicity four.
-/
theorem canonicalPrincipalSinSqKernel_charpoly :
    Matrix.charpoly canonicalPrincipalSinSqKernel =
      Polynomial.X ^ 2 * (Polynomial.X - 1) ^ 4 := by
  rw [canonicalPrincipalSinSqKernel_eq_diagonal]
  unfold fixedPrincipalSinSqMatrix
  rw [Matrix.charpoly_diagonal]
  simp only [Fintype.prod_sum_type, fixedPrincipalSinSq]
  norm_num

noncomputable def fixedPrincipalSinSqEigenvalues : Multiset ℝ :=
  Multiset.map fixedPrincipalSinSqMatrix_isHermitian.eigenvalues
    Finset.univ.val

def fixedPrincipalSinSqMultiset : Multiset ℝ :=
  Multiset.map fixedPrincipalSinSq Finset.univ.val

open Polynomial in
theorem fixedPrincipalSinSqEigenvalues_eq_values :
    fixedPrincipalSinSqEigenvalues = fixedPrincipalSinSqMultiset := by
  apply Multiset.map_injective (RCLike.ofReal_injective (K := ℂ))
  simp only [fixedPrincipalSinSqEigenvalues, fixedPrincipalSinSqMultiset,
    Multiset.map_map]
  rw [← fixedPrincipalSinSqMatrix_isHermitian.roots_charpoly_eq_eigenvalues]
  rw [fixedPrincipalSinSqMatrix, Matrix.charpoly_diagonal,
    Polynomial.roots_prod]
  · simp
  · simp [Finset.prod_ne_zero_iff, Polynomial.X_sub_C_ne_zero]

/--
The squared principal-sine multiset is exactly
`{0,0,1,1,1,1}`.  This theorem deliberately does not infer unsquared sines
via `sqrt`, nor reconstruct principal angles.
-/
theorem fixedPrincipalSinSqMultiset_eq :
    fixedPrincipalSinSqMultiset = {0, 0, 1, 1, 1, 1} := by
  unfold fixedPrincipalSinSqMultiset
  rw [← Finset.univ_disjSum_univ, Finset.val_disjSum]
  simp [Multiset.disjSum, fixedPrincipalSinSq]
  rfl

theorem fixedPrincipalSinSqEigenvalues_eq :
    fixedPrincipalSinSqEigenvalues = {0, 0, 1, 1, 1, 1} :=
  fixedPrincipalSinSqEigenvalues_eq_values.trans
    fixedPrincipalSinSqMultiset_eq

noncomputable def canonicalPrincipalSinSqEigenvalues : Multiset ℝ :=
  Multiset.map canonicalPrincipalSinSqKernel_isHermitian.eigenvalues
    Finset.univ.val

/-- The literal eigenvalue multiset of the frozen compressed projector. -/
theorem canonicalPrincipalSinSqEigenvalues_eq :
    canonicalPrincipalSinSqEigenvalues = {0, 0, 1, 1, 1, 1} := by
  have heigs :
      canonicalPrincipalSinSqKernel_isHermitian.eigenvalues =
        fixedPrincipalSinSqMatrix_isHermitian.eigenvalues := by
    apply
      (Matrix.IsHermitian.eigenvalues_eq_eigenvalues_iff
        canonicalPrincipalSinSqKernel_isHermitian
        fixedPrincipalSinSqMatrix_isHermitian).2
    rw [canonicalPrincipalSinSqKernel_eq_diagonal]
  rw [canonicalPrincipalSinSqEigenvalues, heigs]
  exact fixedPrincipalSinSqEigenvalues_eq

/--
The eigenvalue multiset theorem stated directly for the frozen projector
kernel, rather than only for its computed diagonal normal form.
-/
theorem canonicalPrincipalSinSqKernel_eigenvalues_eq :
    ∃ hK : canonicalPrincipalSinSqKernel.IsHermitian,
      Multiset.map hK.eigenvalues Finset.univ.val =
        {0, 0, 1, 1, 1, 1} := by
  exact ⟨canonicalPrincipalSinSqKernel_isHermitian,
    canonicalPrincipalSinSqEigenvalues_eq⟩

section CoordinateTransport

variable {m : Type*} [Fintype m] [DecidableEq m]

/--
An arbitrary frozen orthonormal coordinate frame transports the canonical
`TT/Gauge/Row` coordinates into the evaluator's ambient coordinates.
-/
def transportedCurvatureFrame
    (W : Matrix m MetricSectorIndex ℂ) :
    Matrix m CurvatureSectorIndex ℂ :=
  W * canonicalCurvatureFrame

def transportedKerCProjector
    (W : Matrix m MetricSectorIndex ℂ) :
    Matrix m m ℂ :=
  W * canonicalKerCProjector * Wᴴ

/--
Squared principal-sine kernel measured after transporting both subspaces by
the same frozen orthonormal coordinate frame.
-/
def transportedPrincipalSinSqKernel
    (W : Matrix m MetricSectorIndex ℂ) :
    Matrix CurvatureSectorIndex CurvatureSectorIndex ℂ :=
  1 - (transportedCurvatureFrame W)ᴴ * transportedKerCProjector W *
    transportedCurvatureFrame W

omit [DecidableEq m] in
/--
Common isometric coordinate transport leaves the compressed projector
exactly equal to the canonical `0₂ ⊕ I₄` kernel.
-/
theorem transportedPrincipalSinSqKernel_eq_canonical
    (W : Matrix m MetricSectorIndex ℂ)
    (hW : Wᴴ * W = 1) :
    transportedPrincipalSinSqKernel W =
      canonicalPrincipalSinSqKernel := by
  simp only [transportedPrincipalSinSqKernel, transportedCurvatureFrame,
    transportedKerCProjector, conjTranspose_mul]
  rw [show
      canonicalCurvatureFrameᴴ * Wᴴ *
          (W * canonicalKerCProjector * Wᴴ) *
          (W * canonicalCurvatureFrame) =
        canonicalCurvatureFrameᴴ * (Wᴴ * W) *
          canonicalKerCProjector * (Wᴴ * W) *
          canonicalCurvatureFrame by
    simp only [Matrix.mul_assoc]]
  rw [hW]
  simp [canonicalPrincipalSinSqKernel]

omit [DecidableEq m] in
/-- Isometric coordinate transport preserves the orthonormality of `S_curv`. -/
theorem transportedCurvatureFrame_isometric
    (W : Matrix m MetricSectorIndex ℂ)
    (hW : Wᴴ * W = 1) :
    (transportedCurvatureFrame W)ᴴ *
        transportedCurvatureFrame W = 1 := by
  simp only [transportedCurvatureFrame, conjTranspose_mul]
  rw [show canonicalCurvatureFrameᴴ * Wᴴ *
      (W * canonicalCurvatureFrame) =
      canonicalCurvatureFrameᴴ * (Wᴴ * W) *
        canonicalCurvatureFrame by
    simp only [Matrix.mul_assoc]]
  rw [hW, Matrix.mul_one, canonicalCurvatureFrame_isometric]

omit [DecidableEq m] in
/--
Consequently the actual transported squared-sine spectrum is conditionally
fixed to two zeros and four ones.  This is still a statement only about
`sin²`; no `sqrt` or inverse-cosine angle bridge is asserted.
-/
theorem transportedPrincipalSinSqKernel_eigenvalues_eq
    (W : Matrix m MetricSectorIndex ℂ)
    (hW : Wᴴ * W = 1) :
    ∃ hK : (transportedPrincipalSinSqKernel W).IsHermitian,
      Multiset.map hK.eigenvalues Finset.univ.val =
        {0, 0, 1, 1, 1, 1} := by
  rw [transportedPrincipalSinSqKernel_eq_canonical W hW]
  exact canonicalPrincipalSinSqKernel_eigenvalues_eq

/-- Principal squared-sine kernel built from evaluator-supplied matrices. -/
def actualPrincipalSinSqKernel
    (S : Matrix m CurvatureSectorIndex ℂ)
    (P : Matrix m m ℂ) :
    Matrix CurvatureSectorIndex CurvatureSectorIndex ℂ :=
  1 - Sᴴ * P * S

omit [DecidableEq m] in
/--
The actual evaluator matrices inherit the canonical kernel only under the
explicit common orthonormal-coordinate bridge `hS` and `hP`.
-/
theorem actualPrincipalSinSqKernel_eq_canonical
    (S : Matrix m CurvatureSectorIndex ℂ)
    (P : Matrix m m ℂ)
    (W : Matrix m MetricSectorIndex ℂ)
    (hW : Wᴴ * W = 1)
    (hS : S = transportedCurvatureFrame W)
    (hP : P = transportedKerCProjector W) :
    actualPrincipalSinSqKernel S P =
      canonicalPrincipalSinSqKernel := by
  subst S
  subst P
  exact transportedPrincipalSinSqKernel_eq_canonical W hW

omit [DecidableEq m] in
/--
Literal conditional eigenvalue multiset for the evaluator's actual
projector compression.
-/
theorem actualPrincipalSinSqKernel_eigenvalues_eq
    (S : Matrix m CurvatureSectorIndex ℂ)
    (P : Matrix m m ℂ)
    (W : Matrix m MetricSectorIndex ℂ)
    (hW : Wᴴ * W = 1)
    (hS : S = transportedCurvatureFrame W)
    (hP : P = transportedKerCProjector W) :
    ∃ hK : (actualPrincipalSinSqKernel S P).IsHermitian,
      Multiset.map hK.eigenvalues Finset.univ.val =
        {0, 0, 1, 1, 1, 1} := by
  rw [actualPrincipalSinSqKernel_eq_canonical S P W hW hS hP]
  exact canonicalPrincipalSinSqKernel_eigenvalues_eq

end CoordinateTransport

/-! ## Gauge quotient invariance -/

section GaugeQuotient

variable {R X H Q : Type*}
variable [Semiring R]
variable [AddCommMonoid X] [Module R X]
variable [AddCommMonoid H] [Module R H]
variable [AddCommMonoid Q] [Module R Q]

/--
An arbitrary gauge displacement in a submodule killed by the physical
projector does not change the quotient representative.
-/
theorem gaugeQuotient_add_invariant
    (proj : H →ₗ[R] Q) (gauge : Submodule R H)
    (hgauge : gauge ≤ proj.ker)
    (t δ : H) (hδ : δ ∈ gauge) :
    proj (t + δ) = proj t := by
  rw [map_add, LinearMap.mem_ker.mp (hgauge hδ), add_zero]

/--
Task-book scalar form: if `Π_phys g = 0`, then
`Π_phys (t + a • g) = Π_phys t` for every scalar `a`.
-/
theorem gaugeDressing_invariant
    (proj : H →ₗ[R] Q) (t g : H) (a : R)
    (hg : proj g = 0) :
    proj (t + a • g) = proj t := by
  simp [hg]

/--
Map-level form: every column of a response perturbation may carry an
independent gauge dressing.  Quotienting erases the whole perturbation map,
not merely one chosen vector.
-/
theorem gaugeResponse_invariant
    (proj : H →ₗ[R] Q) (T D : X →ₗ[R] H)
    (hD : D.range ≤ proj.ker) :
    proj ∘ₗ (T + D) = proj ∘ₗ T := by
  ext x
  simp only [LinearMap.comp_apply, LinearMap.add_apply, map_add]
  rw [LinearMap.mem_ker.mp (hD (LinearMap.mem_range_self D x)), add_zero]

end GaugeQuotient

end V3M0
