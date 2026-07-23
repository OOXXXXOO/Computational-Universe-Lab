"""Round 6a — the C1 "capstone" continuum-limit theorem, restored as a
self-verifying SymPy script.

This is the symbolic-exact half of the sixth-wave result 结果一
(见 战役报告-第六波-封顶与诚实的天花板.md). It was originally derived once
inline in a bash session and never saved — the single most-flagged piece of
lost knowledge in the handoff docs. This file re-establishes it rigorously.

Physics
-------
The split-step Weyl walker (rulespace.core) has, on a homogeneous theta
background, the emergent metric light speed c(theta) = cos(theta) and the
continuum dispersion (walker energy / Hamiltonian, i.e. T00, established in
wave 5 / r5a):

        omega = sqrt(m^2 + cos^2(theta) * p^2) ,   c = cos(theta) .

The self-consistent coin source is the response of the walker energy to the
geometry, F = -d(omega)/d(theta). The capstone identity is

    F = -dE_w/dtheta = tan(theta) * T00 * (1 - m^2/omega^2)
                     = tan(theta) * T00 * (v_g / c)^2 ,        (result 结果一)

with T00 = omega and v_g = d(omega)/dp the group velocity. Three clean facts:
  * massless (m=0): F = tan(theta)*T00 exactly — pure conformal photon coupling,
    kappa = tan(theta);
  * the correction factor (1 - m^2/omega^2) is identically (v_g/c)^2 — slow
    particles couple weakly;
  * on the discrete lattice the massless ratio F/(tan(theta) T00) -> 1 as the
    lattice momentum k = epsilon -> 0, with an O(k^2) "shadow order" lattice
    correction cos^2(theta)/12.

Part 2 closes the previously-OPEN item
  "○ 符号封顶的小ε解析证明 F -> tan(theta)*T00 + O(ε^2) + 阴影阶"
by proving the leading term is exactly 1 analytically and giving the shadow
coefficient in closed form. Part 3 reproduces the report's numeric table
(报告 #32): F/(tan(theta) T00) = 1.002, 1.006, 1.017, 1.045 at k=0.15..0.8.

Run:  source .venv/bin/activate && python r6a_capstone.py
Writes r6a_results.json and prints ALL PASS / SOME FAILED.
"""
import os
import json
import sympy as sp

DIR = os.path.dirname(os.path.abspath(__file__))
TH_REF = 0.45  # rulespace.core.TH_REF


def part1_continuum():
    """Symbolic-exact continuum capstone. Returns (identities, all_ok)."""
    theta, m, p = sp.symbols("theta m p", real=True, positive=True)

    c = sp.cos(theta)                                  # emergent metric light speed
    omega = sp.sqrt(m ** 2 + c ** 2 * p ** 2)          # dispersion = walker energy
    v_g = sp.diff(omega, p)                            # group velocity domega/dp
    F = -sp.diff(omega, theta)                         # self-consistent source
    T00 = omega                                        # walker Hamiltonian energy (r5a)

    # Identity 1:  F - tan(theta) * omega * (1 - m^2/omega^2) == 0
    id1 = sp.simplify(F - sp.tan(theta) * omega * (1 - m ** 2 / omega ** 2))
    # Identity 2:  (1 - m^2/omega^2) - (v_g/c)^2 == 0
    id2 = sp.simplify((1 - m ** 2 / omega ** 2) - (v_g / c) ** 2)
    # Identity 3 (the capstone, both forms):
    #   F - tan(theta) * T00 * (v_g/c)^2 == 0
    id3 = sp.simplify(F - sp.tan(theta) * T00 * (v_g / c) ** 2)

    identities = [
        ("F - tan(theta)*omega*(1 - m^2/omega^2)", id1),
        ("(1 - m^2/omega^2) - (v_g/c)^2", id2),
        ("F - tan(theta)*T00*(v_g/c)^2  [capstone]", id3),
    ]

    print("=" * 70)
    print("PART 1 — continuum capstone (symbolic, exact)")
    print("=" * 70)
    print(f"  c(theta)   = {c}")
    print(f"  omega=T00  = {omega}")
    print(f"  v_g        = {sp.simplify(v_g)}")
    print(f"  F=-domega/dtheta = {sp.simplify(F)}")
    print()
    all_ok = True
    out = []
    for name, val in identities:
        ok = val == 0
        all_ok &= ok
        assert ok, f"identity failed (nonzero): {name} -> {val}"
        print(f"  simplify( {name} ) = {val}   [{'PASS' if ok else 'FAIL'}]")
        out.append({"identity": name, "simplify": str(val), "is_zero": bool(ok)})

    print(f"\n  => F = tan(theta) * T00 * (1 - m^2/omega^2) = tan(theta) * T00 * (v_g/c)^2")
    return out, all_ok


def part2_small_epsilon():
    """Massless lattice sector: prove F/(tan th T00) -> 1 with O(k^2) shadow term.

    Exact discrete dispersion: w(k) = arccos(cos^2(th) cos k + sin^2(th)).
    Returns (leading, shadow_coeff, ok).
    """
    theta = sp.symbols("theta", real=True, positive=True)
    k = sp.symbols("k", real=True, positive=True)
    delta = sp.symbols("delta", positive=True)  # = cos^2(th)*(1 - cos k), O(k^2)

    # Exact discrete quantities (massless sector).
    u = sp.cos(theta) ** 2 * sp.cos(k) + sp.sin(theta) ** 2
    W = sp.acos(u)                       # T00_discrete = w(k)
    F_disc = -sp.diff(W, theta)          # F_discrete = -dw/dtheta
    R_exact = F_disc / (sp.tan(theta) * W)

    # Both W and F_disc vanish like sqrt(k^2) at k=0, so R is a 0/0 whose
    # naive series is a singular Puiseux. Factor the shared sqrt(2*delta):
    #   W       = arccos(1-delta),  with delta = cos^2(th)(1-cos k)
    #   F_disc  = tan(th) * sqrt(2*delta) / sqrt(1 - delta/2)
    # so   R = [1/sqrt(1-delta/2)] / [arccos(1-delta)/sqrt(2*delta)] ,
    # and both factors are ANALYTIC in delta. Series in delta, then in k.
    h = 1 / sp.sqrt(1 - delta / 2)             # = F_disc / (tan(th) sqrt(2 delta))
    g = sp.acos(1 - delta) / sp.sqrt(2 * delta)  # = W / sqrt(2 delta)
    R_delta = sp.series(h / g, delta, 0, 3).removeO()

    # Substitute delta = cos^2(th)(1 - cos k) and expand in the lattice momentum k.
    delta_k = sp.cos(theta) ** 2 * (1 - sp.cos(k))
    R_k = sp.series(R_delta.subs(delta, delta_k), k, 0, 4)

    leading = R_k.removeO().subs(k, 0)             # k^0 term
    leading = sp.simplify(leading)
    shadow = sp.simplify(R_k.removeO().coeff(k, 2))  # O(k^2) shadow coefficient

    ok_lead = sp.simplify(leading - 1) == 0
    assert ok_lead, f"small-eps leading term != 1: {leading}"

    print("\n" + "=" * 70)
    print("PART 2 — small-epsilon (lattice) analytic proof")
    print("=" * 70)
    print(f"  w(k)      = arccos(cos^2(th) cos k + sin^2(th))   (T00_discrete)")
    print(f"  R(k)      = F_discrete / (tan(th) * T00_discrete)")
    print(f"  R(k)      = {R_k}")
    print(f"  leading term (k^0)         = {leading}   [{'PASS' if ok_lead else 'FAIL'}]")
    print(f"  O(k^2) shadow coefficient  = {shadow}")
    print(f"  => F -> tan(theta)*T00 + O(k^2),  shadow order = {shadow} * k^2")

    return {
        "R_exact": str(R_exact),
        "R_series_in_k": str(R_k),
        "leading_term": str(leading),
        "leading_is_one": bool(ok_lead),
        "shadow_coeff_k2": str(shadow),
    }, ok_lead, shadow, R_exact, theta, k


def part3_numeric(R_exact, theta, k):
    """Reproduce report #32: R(k) at theta=TH_REF for k = 0.15,0.30,0.50,0.80."""
    ks = [0.15, 0.30, 0.50, 0.80]
    expected = [1.002, 1.006, 1.017, 1.045]
    tol = 2e-3

    print("\n" + "=" * 70)
    print(f"PART 3 — numerical cross-check (report #32) at theta = {TH_REF}")
    print("=" * 70)
    print(f"  {'k':>6} {'R(k) discrete':>16} {'report':>10} {'|diff|':>10}  status")

    table = []
    all_ok = True
    for kk, exp in zip(ks, expected):
        val = float(R_exact.subs({theta: TH_REF, k: kk}))
        diff = abs(val - exp)
        ok = diff <= tol
        all_ok &= ok
        print(f"  {kk:>6.2f} {val:>16.6f} {exp:>10.3f} {diff:>10.2e}  {'PASS' if ok else 'FAIL'}")
        table.append({"k": kk, "R": val, "report": exp, "abs_diff": diff, "match": bool(ok)})

    return table, all_ok


if __name__ == "__main__":
    ids, ok1 = part1_continuum()
    part2, ok2, shadow, R_exact, theta, k = part2_small_epsilon()
    table, ok3 = part3_numeric(R_exact, theta, k)

    results = {
        "part1_continuum_identities": ids,
        "part2_small_epsilon": part2,
        "part3_numeric_R_table": table,
        "shadow_coeff_k2": str(shadow),
        "capstone": "F = tan(theta)*T00*(1 - m^2/omega^2) = tan(theta)*T00*(v_g/c)^2",
    }
    json.dump(results, open(os.path.join(DIR, "r6a_results.json"), "w"), indent=1)

    all_pass = ok1 and ok2 and ok3
    print("\n" + "=" * 70)
    print(f"  part1 symbolic identities == 0 : {'PASS' if ok1 else 'FAIL'}")
    print(f"  part2 small-eps leading == 1   : {'PASS' if ok2 else 'FAIL'}")
    print(f"  part3 numeric matches report   : {'PASS' if ok3 else 'FAIL'}")
    print("=" * 70)
    print("\nALL PASS" if all_pass else "\nSOME FAILED")
