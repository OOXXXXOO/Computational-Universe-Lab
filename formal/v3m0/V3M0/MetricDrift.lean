import V3M0.Common

namespace V3M0

/-!
# Iterated metric-drift enclosure

This theorem closes the mathematical step between the normalized one-step
metric residual and the fixed-horizon power audit.  Directed fp64 arithmetic
certifies the two scalar powers separately; the theorem below proves that
those are the correct factors to iterate.
-/

/--
If a nonnegative quadratic observable changes by at most the multiplicative
factors `1±δ` in one step, then after every natural number of steps it lies
between the corresponding powers.
-/
theorem iterate_metric_drift_bounds
    {α : Type*}
    (step : α → α)
    (energy : α → ℝ)
    (δ : ℝ)
    (hδ_nonnegative : 0 ≤ δ)
    (hδ_at_most_one : δ ≤ 1)
    (hone_step : ∀ state,
      (1 - δ) * energy state ≤ energy (step state) ∧
        energy (step state) ≤ (1 + δ) * energy state) :
    ∀ (t : ℕ) (state : α),
      (1 - δ) ^ t * energy state ≤
          energy ((step^[t]) state) ∧
        energy ((step^[t]) state) ≤
          (1 + δ) ^ t * energy state := by
  intro t
  induction t with
  | zero =>
      intro state
      simp
  | succ t induction_hypothesis =>
      intro state
      rw [Function.iterate_succ_apply']
      have prior := induction_hypothesis state
      have next := hone_step ((step^[t]) state)
      constructor
      · calc
          (1 - δ) ^ (t + 1) * energy state =
              (1 - δ) * ((1 - δ) ^ t * energy state) := by ring
          _ ≤ (1 - δ) * energy ((step^[t]) state) :=
            mul_le_mul_of_nonneg_left prior.1 (sub_nonneg.mpr hδ_at_most_one)
          _ ≤ energy (step ((step^[t]) state)) := next.1
      · calc
          energy (step ((step^[t]) state)) ≤
              (1 + δ) * energy ((step^[t]) state) := next.2
          _ ≤ (1 + δ) * ((1 + δ) ^ t * energy state) :=
            mul_le_mul_of_nonneg_left prior.2 (by linarith)
          _ = (1 + δ) ^ (t + 1) * energy state := by ring

end V3M0
