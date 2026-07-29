import V3M0.Common

namespace V3M0

/-!
# Legacy epsilon complement

The two historical epsilon conventions count complementary parts of the same
mode total.  These statements deliberately use one shared `j` and `N`; they do
not assert that independently produced historical artifacts used identical
mode selections.
-/

def legacyEpsilonAℚ (N j : ℚ) : ℚ :=
  1 - j / N

def legacyEpsilonBℚ (N j : ℚ) : ℚ :=
  j / N

noncomputable def legacyEpsilonAℝ (N j : ℝ) : ℝ :=
  1 - j / N

noncomputable def legacyEpsilonBℝ (N j : ℝ) : ℝ :=
  j / N

theorem epsilon_complement
  (N j : ℚ) (hN : N ≠ 0) :
    legacyEpsilonAℚ N j + legacyEpsilonBℚ N j = 1 := by
  unfold legacyEpsilonAℚ legacyEpsilonBℚ
  field_simp [hN]
  ring

theorem epsilon_complement_bounded
    (N j : ℚ)
    (hN : 0 < N)
    (hj0 : 0 ≤ j)
    (hjN : j ≤ N) :
    legacyEpsilonAℚ N j + legacyEpsilonBℚ N j = 1 := by
  have _hjSemantic : j ∈ Set.Icc (0 : ℚ) N := ⟨hj0, hjN⟩
  exact epsilon_complement N j (ne_of_gt hN)

theorem epsilon_complement_real
  (N j : ℝ) (hN : N ≠ 0) :
    legacyEpsilonAℝ N j + legacyEpsilonBℝ N j = 1 := by
  unfold legacyEpsilonAℝ legacyEpsilonBℝ
  field_simp [hN]
  ring

theorem epsilon_complement_real_bounded
    (N j : ℝ)
    (hN : 0 < N)
    (hj0 : 0 ≤ j)
    (hjN : j ≤ N) :
    legacyEpsilonAℝ N j + legacyEpsilonBℝ N j = 1 := by
  have _hjSemantic : j ∈ Set.Icc (0 : ℝ) N := ⟨hj0, hjN⟩
  exact epsilon_complement_real N j (ne_of_gt hN)

end V3M0
