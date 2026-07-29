import V3M0.Common

namespace V3M0

open Matrix
open scoped Pointwise

/-!
# Strict locality and symplectic split steps

This file supplies the exact algebraic interfaces needed by the V3-M0
real-space instrument:

* finite-support convolution on `ℤ³`, with a Chebyshev support-radius bound;
* an exact coefficient bridge to a periodic three-torus under an explicit
  no-wrap hypothesis;
* arbitrary finite-dimensional kick, drift, and kick-drift-kick symplectic
  matrices; and
* the standard realification of a complex Hermitian matrix.

No statement below relies on a Fourier projection or on a fixed matrix
dimension.
-/

section Locality

/-- The infinite cubic lattice `ℤ³`, represented by its three coordinates. -/
abbrev Lattice3 := Fin 3 → ℤ

/-- The periodic cubic lattice with side length `L`. -/
abbrev PeriodicLattice3 (L : ℕ) := Fin 3 → ZMod L

/-- A finitely supported, coefficient-valued kernel on `ℤ³`. -/
abbrev LatticeKernel (R : Type*) [Semiring R] :=
  AddMonoidAlgebra R Lattice3

/-- A finitely supported kernel on the periodic three-torus. -/
abbrev PeriodicKernel (R : Type*) [Semiring R] (L : ℕ) :=
  AddMonoidAlgebra R (PeriodicLattice3 L)

/-- Membership in the closed Chebyshev ball of radius `r` in `ℤ³`. -/
def InChebyshevBall (r : ℕ) (x : Lattice3) : Prop :=
  ∀ i, Int.natAbs (x i) ≤ r

/-- Every nonzero coefficient of `f` lies in the Chebyshev ball of radius `r`. -/
def HasChebyshevSupport {R : Type*} [Semiring R]
    (r : ℕ) (f : LatticeKernel R) : Prop :=
  ∀ x ∈ f.coeff.support, InChebyshevBall r x

/--
Finite-support convolution on `ℤ³`.

Multiplication in the additive monoid algebra is precisely the finite
convolution sum, so finiteness is carried by the type rather than by a
separate convergence assumption.
-/
noncomputable def finiteSupportConvolution
    {R G : Type*} [Semiring R] [Add G]
    (f g : AddMonoidAlgebra R G) : AddMonoidAlgebra R G :=
  f * g

/--
The support radius of a finite convolution is at most the sum of the input
radii.
-/
theorem latticeConvolution_support_radius
    {R : Type*} [Semiring R]
    {r s : ℕ} {f g : LatticeKernel R}
    (hf : HasChebyshevSupport r f)
    (hg : HasChebyshevSupport s g) :
    HasChebyshevSupport (r + s) (finiteSupportConvolution f g) := by
  intro z hz i
  have hz' :
      z ∈ f.coeff.support + g.coeff.support :=
    AddMonoidAlgebra.support_coeff_mul_subset f g (by
      simpa [finiteSupportConvolution] using hz)
  obtain ⟨x, hx, y, hy, hxy⟩ := Finset.mem_add.mp hz'
  rw [← hxy]
  simpa only [Pi.add_apply] using
    (Int.natAbs_add_le (x i) (y i)).trans
      (Nat.add_le_add (hf x hx i) (hg y hy i))

/-- Coordinatewise reduction from `ℤ³` to the periodic three-torus. -/
def reduceMod (L : ℕ) : Lattice3 →+ PeriodicLattice3 L where
  toFun x i := (x i : ZMod L)
  map_zero' := by
    ext i
    simp
  map_add' x y := by
    ext i
    simp

/--
If the side length is strictly larger than the diameter `2r`, reduction
modulo `L` is injective on the radius-`r` Chebyshev ball.
-/
theorem reduceMod_injOn_chebyshevBall
    {L r : ℕ} (hL : 2 * r < L) :
    Set.InjOn (reduceMod L) {x : Lattice3 | InChebyshevBall r x} := by
  intro x hx y hy hxy
  funext i
  have hcoord : (x i : ZMod L) = (y i : ZMod L) :=
    congrFun hxy i
  have hdiv : (L : ℤ) ∣ y i - x i :=
    (ZMod.intCast_eq_intCast_iff_dvd_sub (x i) (y i) L).mp hcoord
  have hlt : Int.natAbs (y i - x i) < L := by
    calc
      Int.natAbs (y i - x i)
          ≤ Int.natAbs (y i) + Int.natAbs (x i) :=
            Int.natAbs_sub_le (y i) (x i)
      _ ≤ r + r := Nat.add_le_add (hy i) (hx i)
      _ < L := by simpa [two_mul] using hL
  have hzero : y i - x i = 0 :=
    Int.eq_zero_of_dvd_of_natAbs_lt_natAbs hdiv (by simpa using hlt)
  exact (sub_eq_zero.mp hzero).symm

/--
Periodization sums coefficients over fibers of coordinatewise reduction.
-/
noncomputable def periodize {R : Type*} [Semiring R]
    (L : ℕ) (f : LatticeKernel R) : PeriodicKernel R L :=
  AddMonoidAlgebra.mapDomain (reduceMod L) f

/--
Periodization is a ring homomorphism, so periodic convolution is the
periodization of the infinite-lattice convolution.
-/
theorem periodize_latticeConvolution
    {R : Type*} [Semiring R]
    (L : ℕ) (f g : LatticeKernel R) :
    periodize L (finiteSupportConvolution f g) =
      finiteSupportConvolution (periodize L f) (periodize L g) := by
  simpa [periodize, finiteSupportConvolution] using
    (AddMonoidAlgebra.mapDomain_mul (reduceMod L) f g)

/--
Under the no-wrap condition, periodization preserves every coefficient in
the supported Chebyshev ball exactly.
-/
theorem periodize_coeff_exact_of_noWrap
    {R : Type*} [Semiring R]
    {L radius : ℕ}
    (hL : 2 * radius < L)
    (f : LatticeKernel R)
    (hf : HasChebyshevSupport radius f)
    (z : Lattice3)
    (hz : InChebyshevBall radius z) :
    (periodize L f).coeff (reduceMod L z) = f.coeff z := by
  change
    Finsupp.mapDomain (reduceMod L) f.coeff (reduceMod L z) =
      f.coeff z
  exact Finsupp.mapDomain_apply'
    {x : Lattice3 | InChebyshevBall radius x}
    f.coeff
    (fun _ hx => hf _ hx)
    (reduceMod_injOn_chebyshevBall hL)
    hz

/--
Exact periodic bridge for a convolution.

The hypothesis `2 * (r + s) < L` is the explicit no-wrap condition
`L > 2(r+s)`.  It prevents distinct points in the entire possible output
support from aliasing on the periodic lattice.
-/
theorem periodic_latticeConvolution_exact_bridge
    {R : Type*} [Semiring R]
    {L r s : ℕ}
    (hL : 2 * (r + s) < L)
    (f g : LatticeKernel R)
    (hf : HasChebyshevSupport r f)
    (hg : HasChebyshevSupport s g)
    (z : Lattice3)
    (hz : InChebyshevBall (r + s) z) :
    (finiteSupportConvolution (periodize L f) (periodize L g)).coeff
        (reduceMod L z) =
      (finiteSupportConvolution f g).coeff z := by
  rw [← periodize_latticeConvolution]
  exact periodize_coeff_exact_of_noWrap hL
    (finiteSupportConvolution f g)
    (latticeConvolution_support_radius hf hg)
    z hz

end Locality

section Symplectic

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- The standard symplectic matrix on position-momentum phase space. -/
def standardJ (ι : Type*) [DecidableEq ι]
    (R : Type*) [CommRing R] :
    Matrix (ι ⊕ ι) (ι ⊕ ι) R :=
  Matrix.J ι R

/--
A potential kick `p ↦ p - τ Vq`.

The matrix dimension and coefficient commutative ring are arbitrary;
symmetry of `V` is the only structural hypothesis needed for symplecticity.
-/
def kick {R : Type*} [CommRing R]
    (τ : R) (V : Matrix ι ι R) :
    Matrix (ι ⊕ ι) (ι ⊕ ι) R :=
  Matrix.fromBlocks 1 0 (-(τ • V)) 1

/-- A free drift `q ↦ q + τp` in arbitrary finite dimension. -/
def drift {R : Type*} [CommRing R]
    (τ : R) :
    Matrix (ι ⊕ ι) (ι ⊕ ι) R :=
  Matrix.fromBlocks 1 (τ • (1 : Matrix ι ι R)) 0 1

/--
The kick is symplectic for every coefficient-ring scalar `τ`.
-/
theorem kick_preserves_standardJ
    {R : Type*} [CommRing R]
    (τ : R) {V : Matrix ι ι R} (hV : V.IsSymm) :
    (kick τ V)ᵀ * standardJ ι R * kick τ V = standardJ ι R := by
  have hC : (-(τ • V)).IsSymm := (hV.smul τ).neg
  have hmem : kick τ V ∈ Matrix.symplecticGroup ι R := by
    apply SymplecticGroup.fromBlocks_mem_iff.mpr
    simp [hC.eq]
  simpa [standardJ] using SymplecticGroup.mem_iff'.mp hmem

/--
The drift is symplectic for every coefficient-ring scalar `τ`.
-/
theorem drift_preserves_standardJ
    {R : Type*} [CommRing R]
    (τ : R) :
    (drift (ι := ι) τ)ᵀ * standardJ ι R * drift (ι := ι) τ =
      standardJ ι R := by
  have hB : (τ • (1 : Matrix ι ι R)).IsSymm :=
    Matrix.isSymm_one.smul τ
  have hmem : drift (ι := ι) τ ∈ Matrix.symplecticGroup ι R := by
    apply SymplecticGroup.fromBlocks_mem_iff.mpr
    simp [hB.eq]
  simpa [standardJ] using SymplecticGroup.mem_iff'.mp hmem

/-- Products of matrices preserving the standard form preserve it again. -/
theorem preserves_standardJ_mul
    {R : Type*} [CommRing R]
    {A B : Matrix (ι ⊕ ι) (ι ⊕ ι) R}
    (hA : Aᵀ * standardJ ι R * A = standardJ ι R)
    (hB : Bᵀ * standardJ ι R * B = standardJ ι R) :
    (A * B)ᵀ * standardJ ι R * (A * B) = standardJ ι R := by
  have hAmem : A ∈ Matrix.symplecticGroup ι R :=
    SymplecticGroup.mem_iff'.mpr (by simpa [standardJ] using hA)
  have hBmem : B ∈ Matrix.symplecticGroup ι R :=
    SymplecticGroup.mem_iff'.mpr (by simpa [standardJ] using hB)
  have hABmem : A * B ∈ Matrix.symplecticGroup ι R :=
    (Matrix.symplecticGroup ι R).mul_mem hAmem hBmem
  simpa [standardJ] using SymplecticGroup.mem_iff'.mp hABmem

/--
Kick-drift-kick (velocity Verlet) with an arbitrary kick half-step `τKick`
and an independent drift step `τDrift`.

Symplecticity does not require an equation relating these two parameters;
the usual choice that the kick is a half-step of the drift is an integrator
convention, not an algebraic prerequisite.
-/
def verlet {R : Type*} [CommRing R]
    (τKick τDrift : R) (V : Matrix ι ι R) :
    Matrix (ι ⊕ ι) (ι ⊕ ι) R :=
  kick τKick V * drift (ι := ι) τDrift * kick τKick V

/--
The arbitrary-dimensional kick-drift-kick Verlet step preserves the
standard symplectic form for independent coefficient-ring scalars.
-/
theorem verlet_preserves_standardJ
    {R : Type*} [CommRing R]
    (τKick τDrift : R)
    {V : Matrix ι ι R}
    (hV : V.IsSymm) :
    (verlet τKick τDrift V)ᵀ * standardJ ι R *
        verlet τKick τDrift V =
      standardJ ι R := by
  unfold verlet
  exact preserves_standardJ_mul
    (preserves_standardJ_mul
      (kick_preserves_standardJ τKick hV)
      (drift_preserves_standardJ (ι := ι) τDrift))
    (kick_preserves_standardJ τKick hV)

end Symplectic

section Realification

variable {ι : Type*}

/-- Entrywise real part of a complex matrix. -/
def matrixRealPart (A : Matrix ι ι ℂ) : Matrix ι ι ℝ :=
  A.map Complex.re

/-- Entrywise imaginary part of a complex matrix. -/
def matrixImagPart (A : Matrix ι ι ℂ) : Matrix ι ι ℝ :=
  A.map Complex.im

/--
The standard realification

`A = X + iY  ↦  [[X, -Y], [Y, X]]`.
-/
def hermitianRealification (A : Matrix ι ι ℂ) :
    Matrix (ι ⊕ ι) (ι ⊕ ι) ℝ :=
  Matrix.fromBlocks
    (matrixRealPart A) (-(matrixImagPart A))
    (matrixImagPart A) (matrixRealPart A)

/-- The real part of a Hermitian matrix is symmetric. -/
theorem matrixRealPart_isSymm
    {A : Matrix ι ι ℂ} (hA : A.IsHermitian) :
    (matrixRealPart A).IsSymm := by
  unfold Matrix.IsSymm
  ext i j
  have h := congrArg Complex.re (hA.apply i j)
  simpa [matrixRealPart, Complex.star_def] using h

/-- The imaginary part of a Hermitian matrix is skew-symmetric. -/
theorem matrixImagPart_transpose
    {A : Matrix ι ι ℂ} (hA : A.IsHermitian) :
    (matrixImagPart A)ᵀ = -(matrixImagPart A) := by
  ext i j
  have h := congrArg Complex.im (hA.apply i j)
  simp [matrixImagPart] at h ⊢
  linarith

/--
The standard realification of every complex Hermitian matrix is a real
symmetric matrix.
-/
theorem hermitianRealification_isSymm
    {A : Matrix ι ι ℂ} (hA : A.IsHermitian) :
    (hermitianRealification A).IsSymm := by
  apply Matrix.IsSymm.fromBlocks
    (matrixRealPart_isSymm hA) ?_ (matrixRealPart_isSymm hA)
  rw [Matrix.transpose_neg, matrixImagPart_transpose hA]
  simp

/--
The Hermitian-to-real bridge feeds directly into the arbitrary-dimensional
kick symplecticity theorem.
-/
theorem hermitianRealification_kick_preserves_standardJ
    [Fintype ι] [DecidableEq ι]
    (τ : ℝ) {A : Matrix ι ι ℂ} (hA : A.IsHermitian) :
    (kick τ (hermitianRealification A))ᵀ *
        standardJ (ι ⊕ ι) ℝ *
        kick τ (hermitianRealification A) =
      standardJ (ι ⊕ ι) ℝ :=
  kick_preserves_standardJ τ (hermitianRealification_isSymm hA)

end Realification

end V3M0
