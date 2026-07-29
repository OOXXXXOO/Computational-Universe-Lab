import V3M0.Common

namespace V3M0

universe u v w

/-- A construction history retains both its compiled operator and provenance. -/
structure History (Operator : Type u) (Provenance : Type v) where
  operator : Operator
  provenance : Provenance

/-- Compilation erases provenance and exposes only the final operator. -/
def compile {Operator : Type u} {Provenance : Type v}
    (history : History Operator Provenance) : Operator :=
  history.operator

/-- The provenance label retained by a construction history. -/
def label {Operator : Type u} {Provenance : Type v}
    (history : History Operator Provenance) : Provenance :=
  history.provenance

/--
Any extensional observer of the final operator gives equal outputs on histories
that compile to the same operator.
-/
theorem extensional_observer_equal
    {Operator : Type u}
    {Provenance : Type v}
    {α : Type w}
    (h₁ h₂ : History Operator Provenance)
    (hop : h₁.operator = h₂.operator)
    (obs : Operator → α) :
    obs h₁.operator = obs h₂.operator := by
  exact congrArg obs hop

/-- The compiled-operator form used by the provenance no-go theorem. -/
theorem extensional_compiled_observer_equal
    {Operator : Type u}
    {Provenance : Type v}
    {α : Type w}
    (h₁ h₂ : History Operator Provenance)
    (hop : compile h₁ = compile h₂)
    (obs : Operator → α) :
    obs (compile h₁) = obs (compile h₂) := by
  exact congrArg obs hop

/--
No observer of only the final operator can recover two distinct provenance
labels from histories that compile to that same operator.
-/
theorem extensional_observer_no_go
    {Operator : Type u}
    {Provenance : Type v}
    (h₁ h₂ : History Operator Provenance)
    (hop : compile h₁ = compile h₂)
    (hlabel : label h₁ ≠ label h₂)
    (obs : Operator → Provenance)
    (recovers₁ : obs (compile h₁) = label h₁)
    (recovers₂ : obs (compile h₂) = label h₂) :
    False := by
  apply hlabel
  calc
    label h₁ = obs (compile h₁) := recovers₁.symm
    _ = obs (compile h₂) := extensional_compiled_observer_equal h₁ h₂ hop obs
    _ = label h₂ := recovers₂

end V3M0
