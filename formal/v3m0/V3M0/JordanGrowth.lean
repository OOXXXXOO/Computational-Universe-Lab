import V3M0.Common

namespace V3M0

/-!
# Exact Jordan growth counter-witness

This file proves the universal integer power law used by the sole V3-M0
instability counter-profile.  The action below is exactly the matrix
`[[1, 1], [0, 1]]` on a two-component integer state.
-/

/-- The nilpotent part `N(x,y)=(y,0)` of the closed Jordan profile. -/
def jordanNilpotent (v : ℤ × ℤ) : ℤ × ℤ :=
  (v.2, 0)

/-- The exact Jordan action `(I+N)(x,y)=(x+y,y)`. -/
def jordanStep (v : ℤ × ℤ) : ℤ × ℤ :=
  (v.1 + v.2, v.2)

/-- The nilpotent part is nonzero. -/
theorem jordanNilpotent_ne_zero :
    jordanNilpotent (0, 1) ≠ (0, 0) := by
  norm_num [jordanNilpotent]

/-- The nilpotent part squares to zero on every integer state. -/
theorem jordanNilpotent_sq_zero (v : ℤ × ℤ) :
    jordanNilpotent (jordanNilpotent v) = (0, 0) := by
  simp [jordanNilpotent]

/-- Universal integer power formula `J^t(x,y)=(x+t y,y)`. -/
theorem jordanStep_iterate (t : ℕ) (v : ℤ × ℤ) :
    (jordanStep^[t]) v = (v.1 + (t : ℤ) * v.2, v.2) := by
  induction t with
  | zero =>
      simp
  | succ t ih =>
      rw [Function.iterate_succ_apply, ih]
      simp only [jordanStep]
      constructor <;> simp_all
      ring

/-- Exact squared Euclidean norm on the integer two-state witness lane. -/
def jordanNormSquared (v : ℤ × ℤ) : ℤ :=
  v.1 * v.1 + v.2 * v.2

/-- For `e₂`, the squared norm after `t` steps is exactly `t²+1`. -/
theorem jordan_e2_norm_squared (t : ℕ) :
    jordanNormSquared ((jordanStep^[t]) (0, 1)) =
      (t : ℤ) * (t : ℤ) + 1 := by
  rw [jordanStep_iterate]
  simp [jordanNormSquared]

/--
At the frozen macro-step, the exact growth exceeds the registered strict
threshold.  Both numerals are the values serialized by the Python witness.
-/
theorem jordan_t16384_growth :
    jordanNormSquared ((jordanStep^[16384]) (0, 1)) = 268435457 ∧
      (100000001 : ℤ) <
        jordanNormSquared ((jordanStep^[16384]) (0, 1)) := by
  constructor
  · norm_num [jordan_e2_norm_squared]
  · norm_num [jordan_e2_norm_squared]

end V3M0
