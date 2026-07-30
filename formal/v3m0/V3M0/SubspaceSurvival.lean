import V3M0.Common
import Mathlib.Analysis.InnerProductSpace.SingularValues
import Mathlib.Analysis.Matrix.Order

namespace V3M0

open Matrix
open scoped ComplexOrder MatrixOrder

/-!
# Finite-dimensional subspace survival

The columns of `U₀` and `U₁` are orthonormal frames in one ambient complex
space.  The causal-survival kernel is the compression of the orthogonal
projector `U₀ U₀ᴴ` to the second frame.  All dimensions and all nonzero
denominators are explicit.
-/

section Core

variable {m n₀ n₁ : Type*}
variable [Fintype m] [Fintype n₀] [Fintype n₁]
variable [DecidableEq m] [DecidableEq n₀] [DecidableEq n₁]

/-- A finite complex frame has orthonormal columns. -/
def IsIsometricFrame (U : Matrix m n₁ ℂ) : Prop :=
  Uᴴ * U = 1

/-- The orthogonal projector represented by an isometric frame. -/
def frameProjector (U : Matrix m n₁ ℂ) : Matrix m m ℂ :=
  U * Uᴴ

/-- The overlap map from the second frame into the first. -/
def frameOverlap (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    Matrix n₀ n₁ ℂ :=
  U₀ᴴ * U₁

/-- Compression of the first projector to the second subspace. -/
def survivalKernel (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    Matrix n₁ n₁ ℂ :=
  U₁ᴴ * U₀ * U₀ᴴ * U₁

/-- The survival kernel is exactly the Gram matrix of the overlap. -/
theorem survivalKernel_eq_overlap_gram
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    survivalKernel U₀ U₁ =
      (frameOverlap U₀ U₁)ᴴ * frameOverlap U₀ U₁ := by
  simp only [survivalKernel, frameOverlap, conjTranspose_mul,
    conjTranspose_conjTranspose]
  simp [Matrix.mul_assoc]

/-- The survival kernel is Hermitian before any numerical eigensolve. -/
theorem survivalKernel_isHermitian
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    (survivalKernel U₀ U₁).IsHermitian := by
  rw [survivalKernel_eq_overlap_gram]
  exact isHermitian_conjTranspose_mul_self _

/-- The frame projector is Hermitian and idempotent. -/
theorem frameProjector_isHermitian_idempotent
    {U : Matrix m n₁ ℂ} (hU : IsIsometricFrame U) :
    (frameProjector U).IsHermitian ∧
      frameProjector U * frameProjector U = frameProjector U := by
  constructor
  · exact isHermitian_mul_conjTranspose_self U
  · simp only [frameProjector]
    calc
      U * Uᴴ * (U * Uᴴ) = U * (Uᴴ * U) * Uᴴ := by
        simp only [Matrix.mul_assoc]
      _ = U * Uᴴ := by rw [hU, Matrix.mul_one]

/--
Both Loewner bounds are witnessed algebraically:
`K=AᴴA` and `I-K=BᴴB`, where
`B=(I-U₀U₀ᴴ)U₁`.
-/
theorem survivalKernel_loewner_bounds
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (hU₀ : IsIsometricFrame U₀)
    (hU₁ : IsIsometricFrame U₁) :
    0 ≤ survivalKernel U₀ U₁ ∧ survivalKernel U₀ U₁ ≤ 1 := by
  change U₀ᴴ * U₀ = 1 at hU₀
  change U₁ᴴ * U₁ = 1 at hU₁
  constructor
  · rw [Matrix.nonneg_iff_posSemidef, survivalKernel_eq_overlap_gram]
    exact posSemidef_conjTranspose_mul_self _
  · rw [Matrix.le_iff]
    let P₀ : Matrix m m ℂ := frameProjector U₀
    let B : Matrix m n₁ ℂ := (1 - P₀) * U₁
    have hP₀ : P₀ᴴ = P₀ := by
      exact (frameProjector_isHermitian_idempotent hU₀).1.eq
    have hP₀sq : P₀ * P₀ = P₀ :=
      (frameProjector_isHermitian_idempotent hU₀).2
    have hcompSq : (1 - P₀) * (1 - P₀) = 1 - P₀ := by
      noncomm_ring [hP₀sq]
    have hfactor :
        1 - survivalKernel U₀ U₁ = Bᴴ * B := by
      dsimp [B]
      rw [conjTranspose_mul, conjTranspose_sub, conjTranspose_one, hP₀]
      calc
        1 - survivalKernel U₀ U₁ = U₁ᴴ * (1 - P₀) * U₁ := by
          simp only [survivalKernel, P₀, frameProjector,
            Matrix.mul_sub, Matrix.mul_one, Matrix.sub_mul,
            Matrix.mul_assoc]
          rw [hU₁]
        _ = U₁ᴴ * ((1 - P₀) * (1 - P₀)) * U₁ := by
          rw [hcompSq]
        _ = (U₁ᴴ * (1 - P₀)) * ((1 - P₀) * U₁) := by
          simp only [Matrix.mul_assoc]
    rw [hfactor]
    exact posSemidef_conjTranspose_mul_self _

/--
Every eigenvalue of the Hermitian survival kernel lies in the closed unit
interval.  This is the finite-dimensional spectral form of `0 ≤ K ≤ I`.
-/
theorem survivalKernel_eigenvalues_mem_unitInterval
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (hU₀ : IsIsometricFrame U₀)
    (hU₁ : IsIsometricFrame U₁)
    (i : n₁) :
    let hK : (survivalKernel U₀ U₁).PosSemidef :=
      (survivalKernel_loewner_bounds hU₀ hU₁).1.posSemidef
    hK.isHermitian.eigenvalues i ∈ Set.Icc (0 : ℝ) 1 := by
  dsimp only
  let hbounds := survivalKernel_loewner_bounds hU₀ hU₁
  let hK : (survivalKernel U₀ U₁).PosSemidef := hbounds.1.posSemidef
  have hLower : 0 ≤ hK.isHermitian.eigenvalues i :=
    hK.eigenvalues_nonneg i
  have hUpperPSD : (1 - survivalKernel U₀ U₁).PosSemidef :=
    Matrix.le_iff.mp hbounds.2
  let v : n₁ → ℂ := ⇑(hK.isHermitian.eigenvectorBasis i)
  have hvnorm : ‖WithLp.toLp 2 v‖ = 1 :=
    hK.isHermitian.eigenvectorBasis.orthonormal.1 i
  have hquad := hUpperPSD.re_dotProduct_nonneg v
  have heig :
      survivalKernel U₀ U₁ *ᵥ v =
        (hK.isHermitian.eigenvalues i) • v :=
    hK.isHermitian.mulVec_eigenvectorBasis i
  have hUpper : hK.isHermitian.eigenvalues i ≤ 1 := by
    rw [Matrix.sub_mulVec, Matrix.one_mulVec, heig] at hquad
    have hvinner :
        RCLike.re (star v ⬝ᵥ v) = 1 := by
      rw [dotProduct_comm]
      rw [← EuclideanSpace.inner_toLp_toLp]
      rw [inner_self_eq_norm_sq_to_K, hvnorm]
      norm_num
    rw [dotProduct_sub, dotProduct_smul] at hquad
    simp only [map_sub, RCLike.smul_re, hvinner, mul_one] at hquad
    linarith
  exact ⟨hLower, hUpper⟩

/-- The entire real spectrum of the survival kernel is contained in `[0,1]`. -/
theorem survivalKernel_realSpectrum_subset_unitInterval
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (hU₀ : IsIsometricFrame U₀)
    (hU₁ : IsIsometricFrame U₁) :
    spectrum ℝ (survivalKernel U₀ U₁) ⊆ Set.Icc (0 : ℝ) 1 := by
  let hK : (survivalKernel U₀ U₁).PosSemidef :=
    (survivalKernel_loewner_bounds hU₀ hU₁).1.posSemidef
  rw [hK.isHermitian.spectrum_real_eq_range_eigenvalues]
  rintro _ ⟨i, rfl⟩
  exact survivalKernel_eigenvalues_mem_unitInterval hU₀ hU₁ i

/-- Zero overlap implies zero causal survival as a purely algebraic anchor. -/
theorem survivalKernel_zero_anchor
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (horth : frameOverlap U₀ U₁ = 0) :
    survivalKernel U₀ U₁ = 0 := by
  rw [survivalKernel_eq_overlap_gram, horth]
  simp

/--
If the actual frame lies in the range of the reference projector, survival
is full.  Equality of the two frames is not required.
-/
theorem survivalKernel_full_anchor
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (hU₁ : IsIsometricFrame U₁)
    (hcontained : frameProjector U₀ * U₁ = U₁) :
    survivalKernel U₀ U₁ = 1 := by
  change U₁ᴴ * U₁ = 1 at hU₁
  calc
    survivalKernel U₀ U₁ =
        U₁ᴴ * (frameProjector U₀ * U₁) := by
      simp [survivalKernel, frameProjector, Matrix.mul_assoc]
    _ = U₁ᴴ * U₁ := by rw [hcontained]
    _ = 1 := hU₁

/-- An isometric frame projector has rank equal to its explicit column count. -/
theorem frameProjector_rank_eq_card
    {U : Matrix m n₁ ℂ} (hU : IsIsometricFrame U) :
    (frameProjector U).rank = Fintype.card n₁ := by
  change Uᴴ * U = 1 at hU
  rw [frameProjector, rank_self_mul_conjTranspose]
  apply le_antisymm (rank_le_card_width U)
  have hrank := rank_mul_le_right Uᴴ U
  rw [hU, rank_one] at hrank
  exact hrank

/--
With at least one actual degree of freedom, the actual projector and its
rank denominator are nonzero.
-/
theorem frameProjector_rank_nonzero
    {U : Matrix m n₁ ℂ} (hU : IsIsometricFrame U)
    (hcard : Fintype.card n₁ ≠ 0) :
    (frameProjector U).rank ≠ 0 ∧ frameProjector U ≠ 0 := by
  have hrank := frameProjector_rank_eq_card hU
  constructor
  · simpa [hrank] using hcard
  · intro hzero
    have : (frameProjector U).rank = 0 := by rw [hzero, rank_zero]
    exact hcard (hrank ▸ this)

/--
Valid zero anchor: the actual frame has a nonzero rank denominator even
though its overlap with the reference is zero.
-/
theorem survivalKernel_valid_zero_anchor
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (hU₁ : IsIsometricFrame U₁)
    (hcard : Fintype.card n₁ ≠ 0)
    (horth : frameOverlap U₀ U₁ = 0) :
    survivalKernel U₀ U₁ = 0 ∧
      U₁ ≠ 0 ∧ (frameProjector U₁).rank ≠ 0 ∧
        frameProjector U₁ ≠ 0 := by
  have hp := frameProjector_rank_nonzero hU₁ hcard
  have hU₁ne : U₁ ≠ 0 := by
    intro hzero
    apply hp.2
    simp [frameProjector, hzero]
  exact ⟨survivalKernel_zero_anchor horth, hU₁ne, hp⟩

/--
Valid full anchor: the reference is certified as an orthogonal projector,
the actual frame lies in its range, and the rank denominator is nonzero.
-/
theorem survivalKernel_valid_full_anchor
    {U₀ : Matrix m n₀ ℂ} {U₁ : Matrix m n₁ ℂ}
    (hU₀ : IsIsometricFrame U₀)
    (hU₁ : IsIsometricFrame U₁)
    (hcard : Fintype.card n₁ ≠ 0)
    (hcontained : frameProjector U₀ * U₁ = U₁) :
    survivalKernel U₀ U₁ = 1 ∧
      (frameProjector U₁).rank ≠ 0 ∧
      frameProjector U₀ * frameProjector U₀ = frameProjector U₀ := by
  exact ⟨survivalKernel_full_anchor hU₁ hcontained,
    (frameProjector_rank_nonzero hU₁ hcard).1,
    (frameProjector_isHermitian_idempotent hU₀).2⟩

section Invariance

variable {p : Type*} [Fintype p] [DecidableEq p]

/-- The survival kernel is the actual-frame compression of the reference projector. -/
theorem survivalKernel_eq_compressed_projector
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    survivalKernel U₀ U₁ = U₁ᴴ * frameProjector U₀ * U₁ := by
  simp [survivalKernel, frameProjector, Matrix.mul_assoc]

/--
A common left isometric change of ambient coordinates leaves the overlap
and survival kernel exactly unchanged.
-/
theorem survivalKernel_common_left_isometry
    (L : Matrix p m ℂ)
    (hL : Lᴴ * L = 1)
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    survivalKernel (L * U₀) (L * U₁) = survivalKernel U₀ U₁ := by
  have hoverlap :
      frameOverlap (L * U₀) (L * U₁) = frameOverlap U₀ U₁ := by
    simp only [frameOverlap, conjTranspose_mul]
    rw [Matrix.mul_assoc, ← Matrix.mul_assoc Lᴴ L, hL, Matrix.one_mul]
  rw [survivalKernel_eq_overlap_gram,
    survivalKernel_eq_overlap_gram, hoverlap]

/-- Exact scalar factor pulled out of a frame projector. -/
theorem frameProjector_smul
    (c : ℂ) (U : Matrix m n₁ ℂ) :
    frameProjector (c • U) = (star c * c) • frameProjector U := by
  simp only [frameProjector, conjTranspose_smul, Matrix.smul_mul,
    Matrix.mul_smul, smul_smul]

/-- Unit-modulus scalar multiplication leaves a frame projector unchanged. -/
theorem frameProjector_unitScalar
    (c : ℂ) (hc : star c * c = 1) (U : Matrix m n₁ ℂ) :
    frameProjector (c • U) = frameProjector U := by
  rw [frameProjector_smul, hc, one_smul]

/--
Unit-modulus phase changes of either orthonormal frame leave the survival
kernel exactly unchanged.
-/
theorem survivalKernel_unitScalar
    (c₀ c₁ : ℂ)
    (hc₀ : star c₀ * c₀ = 1)
    (hc₁ : star c₁ * c₁ = 1)
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    survivalKernel (c₀ • U₀) (c₁ • U₁) =
      survivalKernel U₀ U₁ := by
  rw [survivalKernel_eq_compressed_projector,
    frameProjector_unitScalar c₀ hc₀,
    survivalKernel_eq_compressed_projector]
  simp only [conjTranspose_smul, Matrix.smul_mul,
    Matrix.mul_smul, smul_smul]
  rw [mul_comm c₁ (star c₁), hc₁, one_smul]

/--
For an arbitrary nonzero complex amplitude, projector normalization removes
the amplitude.  Direct frame/K invariance above is deliberately restricted
to unit-modulus scalars.
-/
noncomputable def normalizedScaledProjector
    (c : ℂ) (U : Matrix m n₁ ℂ) : Matrix m m ℂ :=
  (star c * c)⁻¹ • frameProjector (c • U)

theorem normalizedScaledProjector_eq
    {c : ℂ} (hc : c ≠ 0) (U : Matrix m n₁ ℂ) :
    normalizedScaledProjector c U = frameProjector U := by
  have hnorm : star c * c ≠ 0 := mul_ne_zero (star_ne_zero.mpr hc) hc
  rw [normalizedScaledProjector, frameProjector_smul]
  simp only [smul_smul]
  rw [inv_mul_cancel₀ hnorm, one_smul]

/--
Both arbitrary nonzero frame amplitudes are removed before the survival
kernel is interpreted.
-/
noncomputable def normalizedScaledSurvival
    (c₀ c₁ : ℂ) (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    Matrix n₁ n₁ ℂ :=
  (star c₁ * c₁)⁻¹ •
    ((c₁ • U₁)ᴴ * normalizedScaledProjector c₀ U₀ * (c₁ • U₁))

theorem normalizedScaledSurvival_eq
    {c₀ c₁ : ℂ} (hc₀ : c₀ ≠ 0) (hc₁ : c₁ ≠ 0)
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    normalizedScaledSurvival c₀ c₁ U₀ U₁ =
      survivalKernel U₀ U₁ := by
  have hnorm₁ : star c₁ * c₁ ≠ 0 :=
    mul_ne_zero (star_ne_zero.mpr hc₁) hc₁
  rw [normalizedScaledSurvival, normalizedScaledProjector_eq hc₀,
    survivalKernel_eq_compressed_projector]
  simp only [conjTranspose_smul, Matrix.smul_mul,
    Matrix.mul_smul, smul_smul]
  rw [mul_comm c₁ (star c₁), inv_mul_cancel₀ hnorm₁, one_smul]

/-- A unitary basis change inside the reference frame leaves its projector fixed. -/
theorem frameProjector_right_unitary
    (Q : Matrix n₁ n₁ ℂ) (hQ : Q * Qᴴ = 1)
    (U : Matrix m n₁ ℂ) :
    frameProjector (U * Q) = frameProjector U := by
  simp only [frameProjector, conjTranspose_mul, Matrix.mul_assoc]
  rw [← Matrix.mul_assoc Q Qᴴ, hQ, Matrix.one_mul]

/-- A unitary basis change inside the reference subspace leaves `K` exact. -/
theorem survivalKernel_reference_right_unitary
    (Q : Matrix n₀ n₀ ℂ) (hQ : Q * Qᴴ = 1)
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    survivalKernel (U₀ * Q) U₁ = survivalKernel U₀ U₁ := by
  rw [survivalKernel_eq_compressed_projector,
    frameProjector_right_unitary Q hQ,
    survivalKernel_eq_compressed_projector]

/--
Changing the basis of the actual frame by a square unitary conjugates `K`;
it does not claim entrywise equality.
-/
theorem survivalKernel_actual_right_unitary
    (R : Matrix n₁ n₁ ℂ)
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    survivalKernel U₀ (U₁ * R) =
      Rᴴ * survivalKernel U₀ U₁ * R := by
  simp [survivalKernel, conjTranspose_mul, Matrix.mul_assoc]

/-- Unitary conjugation preserves the complete ordered Hermitian spectrum. -/
theorem hermitian_eigenvalues_unitary_conjugation
    {K : Matrix n₁ n₁ ℂ} (hK : K.IsHermitian)
    (R : Matrix n₁ n₁ ℂ) (hR : R * Rᴴ = 1) :
    (isHermitian_conjTranspose_mul_mul R hK).eigenvalues =
      hK.eigenvalues := by
  apply (IsHermitian.eigenvalues_eq_eigenvalues_iff
    (isHermitian_conjTranspose_mul_mul R hK) hK).2
  calc
    (Rᴴ * K * R).charpoly = (R * (Rᴴ * K)).charpoly := by
      simpa [Matrix.mul_assoc] using
        (Matrix.charpoly_mul_comm (Rᴴ * K) R)
    _ = K.charpoly := by rw [← Matrix.mul_assoc, hR, Matrix.one_mul]

/--
An actual-frame unitary basis change preserves the complete ordered
survival spectrum.
-/
theorem survivalKernel_actual_right_unitary_eigenvalues
    (R : Matrix n₁ n₁ ℂ) (hR : R * Rᴴ = 1)
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    let hChanged := survivalKernel_isHermitian U₀ (U₁ * R)
    let hBase := survivalKernel_isHermitian U₀ U₁
    hChanged.eigenvalues = hBase.eigenvalues := by
  dsimp only
  apply (IsHermitian.eigenvalues_eq_eigenvalues_iff
    (survivalKernel_isHermitian U₀ (U₁ * R))
    (survivalKernel_isHermitian U₀ U₁)).2
  rw [survivalKernel_actual_right_unitary]
  calc
    (Rᴴ * survivalKernel U₀ U₁ * R).charpoly =
        (R * (Rᴴ * survivalKernel U₀ U₁)).charpoly := by
      simpa [Matrix.mul_assoc] using
        (Matrix.charpoly_mul_comm
          (Rᴴ * survivalKernel U₀ U₁) R)
    _ = (survivalKernel U₀ U₁).charpoly := by
      rw [← Matrix.mul_assoc, hR, Matrix.one_mul]

end Invariance

section SingularValues

/--
The first `dim(domain)` entries of mathlib's singular-value sequence,
squared.  Rank deficiency appears as exact trailing zeros, so this is the
required zero-extended list rather than a numerically truncated SVD.
-/
noncomputable def zeroExtendedSquaredSingularValue
    {E F : Type*}
    [NormedAddCommGroup E] [InnerProductSpace ℂ E] [FiniteDimensional ℂ E]
    [NormedAddCommGroup F] [InnerProductSpace ℂ F] [FiniteDimensional ℂ F]
    (T : E →ₗ[ℂ] F) (i : ℕ) : ℝ :=
  T.singularValues i ^ 2

/-- Sum of the genuine zero-extended squared singular values is `Re tr(T†T)`. -/
theorem sum_zeroExtendedSquaredSingularValue_eq_re_trace
    {E F : Type*}
    [NormedAddCommGroup E] [InnerProductSpace ℂ E] [FiniteDimensional ℂ E]
    [NormedAddCommGroup F] [InnerProductSpace ℂ F] [FiniteDimensional ℂ F]
    (T : E →ₗ[ℂ] F) :
    (∑ i : Fin (Module.finrank ℂ E),
        zeroExtendedSquaredSingularValue T i) =
      RCLike.re ((T.adjoint ∘ₗ T).trace ℂ E) := by
  rw [T.isSymmetric_adjoint_comp_self.re_trace_eq_sum_eigenvalues rfl]
  apply Finset.sum_congr rfl
  intro i _
  exact T.sq_singularValues_fin rfl i

/--
For the overlap map, the linear Gram trace above is exactly the matrix
trace of the survival kernel.
-/
theorem sum_overlap_squaredSingularValues_eq_re_trace_survival
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    let T := (frameOverlap U₀ U₁).toEuclideanLin
    (∑ i : Fin (Module.finrank ℂ (EuclideanSpace ℂ n₁)),
        zeroExtendedSquaredSingularValue T i) =
      RCLike.re (survivalKernel U₀ U₁).trace := by
  dsimp only
  let A := frameOverlap U₀ U₁
  let T := A.toEuclideanLin
  have hgram :
      T.adjoint ∘ₗ T = (Aᴴ * A).toEuclideanLin := by
    rw [← Matrix.toEuclideanLin_conjTranspose_eq_adjoint]
    exact (Matrix.toLpLin_mul_same (p := 2) Aᴴ A).symm
  rw [sum_zeroExtendedSquaredSingularValue_eq_re_trace, hgram]
  have htrace :
      ((Aᴴ * A).toEuclideanLin.trace ℂ (EuclideanSpace ℂ n₁)) =
        (Aᴴ * A).trace := by
    change
      LinearMap.trace ℂ _
          (Matrix.toLin (EuclideanSpace.basisFun n₁ ℂ).toBasis
            (EuclideanSpace.basisFun n₁ ℂ).toBasis (Aᴴ * A)) =
        (Aᴴ * A).trace
    exact Matrix.trace_toLin_eq _ _
  rw [htrace, survivalKernel_eq_overlap_gram]

/-- Matrix-specialized zero-extended squared singular value, indexed by `card n₁`. -/
noncomputable def zeroExtendedOverlapSquaredSingularValue
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ)
    (i : Fin (Fintype.card n₁)) : ℝ :=
  ((frameOverlap U₀ U₁).toEuclideanLin.singularValues i) ^ 2

/-- The same zero-extended list with its length reduced to the explicit column count. -/
theorem sum_overlap_squaredSingularValues_card_eq_re_trace_survival
    (U₀ : Matrix m n₀ ℂ) (U₁ : Matrix m n₁ ℂ) :
    (∑ i : Fin (Fintype.card n₁),
        zeroExtendedOverlapSquaredSingularValue U₀ U₁ i) =
      RCLike.re (survivalKernel U₀ U₁).trace := by
  have h :=
    sum_overlap_squaredSingularValues_eq_re_trace_survival U₀ U₁
  rw [finrank_euclideanSpace] at h
  simpa only [zeroExtendedOverlapSquaredSingularValue,
    zeroExtendedSquaredSingularValue] using h

/--
The certified coordinate is exactly the arithmetic mean of the
zero-extended squared singular values.  The actual-projector rank and its
nonzero denominator are derived from frame isometry.
-/
theorem normalized_survival_eq_squaredSingularValue_mean
    {U₁ : Matrix m n₁ ℂ}
    (U₀ : Matrix m n₀ ℂ)
    (hU₁ : IsIsometricFrame U₁)
    (hcard : Fintype.card n₁ ≠ 0) :
    ((frameProjector U₁).rank : ℝ) ≠ 0 ∧
      RCLike.re (survivalKernel U₀ U₁).trace /
          ((frameProjector U₁).rank : ℝ) =
        (∑ i : Fin (Fintype.card n₁),
            zeroExtendedOverlapSquaredSingularValue U₀ U₁ i) /
          (Fintype.card n₁ : ℝ) := by
  constructor
  · exact_mod_cast (frameProjector_rank_nonzero hU₁ hcard).1
  · rw [frameProjector_rank_eq_card hU₁]
    rw [sum_overlap_squaredSingularValues_card_eq_re_trace_survival]

end SingularValues

section DirectSum

variable {a b : Type*}
variable [Fintype a] [Fintype b]
variable [DecidableEq a] [DecidableEq b]

/-- Block embedding of two frames into an orthogonal ambient direct sum. -/
def orthogonalDirectSumFrame
    {mₐ mᵦ nₐ nᵦ : Type*}
    (Uₐ : Matrix mₐ nₐ ℂ) (Uᵦ : Matrix mᵦ nᵦ ℂ) :
    Matrix (mₐ ⊕ mᵦ) (nₐ ⊕ nᵦ) ℂ :=
  Matrix.fromBlocks Uₐ 0 0 Uᵦ

/-- Orthogonal direct sum of two survival kernels. -/
def orthogonalDirectSumKernel
    (Kₐ : Matrix a a ℂ) (Kᵦ : Matrix b b ℂ) :
    Matrix (a ⊕ b) (a ⊕ b) ℂ :=
  Matrix.fromBlocks Kₐ 0 0 Kᵦ

/--
The kernel of block-embedded reference/actual frames is the block diagonal
of their two kernels.  Thus the direct-sum score theorem below is connected
to an actual orthogonal ambient/frame construction.
-/
theorem orthogonalDirectSumFrame_survivalKernel
    {mₐ mᵦ n₀ₐ n₀ᵦ n₁ₐ n₁ᵦ : Type*}
    [Fintype mₐ] [Fintype mᵦ] [Fintype n₀ₐ] [Fintype n₀ᵦ]
    [Fintype n₁ₐ] [Fintype n₁ᵦ]
    (U₀ₐ : Matrix mₐ n₀ₐ ℂ) (U₀ᵦ : Matrix mᵦ n₀ᵦ ℂ)
    (U₁ₐ : Matrix mₐ n₁ₐ ℂ) (U₁ᵦ : Matrix mᵦ n₁ᵦ ℂ) :
    survivalKernel
        (orthogonalDirectSumFrame U₀ₐ U₀ᵦ)
        (orthogonalDirectSumFrame U₁ₐ U₁ᵦ) =
      orthogonalDirectSumKernel
        (survivalKernel U₀ₐ U₁ₐ)
        (survivalKernel U₀ᵦ U₁ᵦ) := by
  simp [survivalKernel, orthogonalDirectSumFrame,
    orthogonalDirectSumKernel, Matrix.fromBlocks_conjTranspose,
    Matrix.fromBlocks_multiply]

/-- A block direct sum of isometric frames is again isometric. -/
theorem orthogonalDirectSumFrame_isometric
    {mₐ mᵦ nₐ nᵦ : Type*}
    [Fintype mₐ] [Fintype mᵦ] [Fintype nₐ] [Fintype nᵦ]
    [DecidableEq nₐ] [DecidableEq nᵦ]
    {Uₐ : Matrix mₐ nₐ ℂ} {Uᵦ : Matrix mᵦ nᵦ ℂ}
    (hUₐ : IsIsometricFrame Uₐ) (hUᵦ : IsIsometricFrame Uᵦ) :
    IsIsometricFrame (orthogonalDirectSumFrame Uₐ Uᵦ) := by
  change Uₐᴴ * Uₐ = 1 at hUₐ
  change Uᵦᴴ * Uᵦ = 1 at hUᵦ
  simp [IsIsometricFrame, orthogonalDirectSumFrame,
    Matrix.fromBlocks_conjTranspose, Matrix.fromBlocks_multiply,
    hUₐ, hUᵦ, Matrix.fromBlocks_one]

/-- The direct-sum characteristic polynomial is the product of block polynomials. -/
theorem orthogonalDirectSumKernel_charpoly
    (Kₐ : Matrix a a ℂ) (Kᵦ : Matrix b b ℂ) :
    (orthogonalDirectSumKernel Kₐ Kᵦ).charpoly =
      Kₐ.charpoly * Kᵦ.charpoly := by
  simp [orthogonalDirectSumKernel]

/-- Trace numerator and DOF denominator both add under an orthogonal sum. -/
theorem orthogonalDirectSum_trace_dof
    (Kₐ : Matrix a a ℂ) (Kᵦ : Matrix b b ℂ) :
    RCLike.re (orthogonalDirectSumKernel Kₐ Kᵦ).trace /
        (Fintype.card (a ⊕ b) : ℝ) =
      (RCLike.re Kₐ.trace + RCLike.re Kᵦ.trace) /
        ((Fintype.card a : ℝ) + Fintype.card b) := by
  simp [orthogonalDirectSumKernel, Matrix.trace, Fintype.card_sum]

/-- The normalized trace score of a square kernel. -/
noncomputable def normalizedSurvivalScore
    {n : Type*} [Fintype n] (K : Matrix n n ℂ) : ℝ :=
  RCLike.re K.trace / Fintype.card n

/--
The direct-sum score is DOF-weighted, not an equally weighted average of
block scores.
-/
theorem orthogonalDirectSum_score_weighted
    (Kₐ : Matrix a a ℂ) (Kᵦ : Matrix b b ℂ)
    (ha : Fintype.card a ≠ 0)
    (hb : Fintype.card b ≠ 0) :
    normalizedSurvivalScore (orthogonalDirectSumKernel Kₐ Kᵦ) =
      ((Fintype.card a : ℝ) * normalizedSurvivalScore Kₐ +
          (Fintype.card b : ℝ) * normalizedSurvivalScore Kᵦ) /
        ((Fintype.card a : ℝ) + Fintype.card b) := by
  rw [normalizedSurvivalScore, orthogonalDirectSum_trace_dof]
  simp only [normalizedSurvivalScore]
  have haR : (Fintype.card a : ℝ) ≠ 0 := by exact_mod_cast ha
  have hbR : (Fintype.card b : ℝ) ≠ 0 := by exact_mod_cast hb
  field_simp

end DirectSum

end Core

end V3M0
