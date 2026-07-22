"""tensor_screen_stub — STUB fast-screen kernel per TENSOR_CAMPAIGN_INTERFACE.md.

Lets the harness (tensor_campaign_runner) run end-to-end BEFORE lane-A's real
batch kernel lands. Swap the import in the runner for the real
`screen_tensor_rules` when it exists; the harness code does not change.

Everything here is a cheap heuristic placeholder -- NOT physics. It only exercises
the two-level orchestration (screen -> survivors -> full re-judge) + the column
contract (incl. the J5 gw_speed column that must exist from day one).
"""
import numpy as np

PARAM_NAMES = ["cg2", "gamma", "G", "tr_sign", "sigma"]   # placeholder = tensor_qca's params


def sample_tensor_prior(n, seed=0):
    """physics-shaped sparse prior over tensor-rule params. (n, len(PARAM_NAMES))."""
    rng = np.random.default_rng(seed)
    P = np.zeros((n, 5))
    P[:, 0] = 10 ** rng.uniform(-1.2, -0.3, n)                     # cg2  (< 0.5 for CFL)
    P[:, 1] = 10 ** rng.uniform(-2.5, -0.8, n)                     # gamma (de-Donder damping)
    P[:, 2] = 10 ** rng.uniform(-1.5, 0.0, n)                      # G
    P[:, 3] = np.where(rng.random(n) < 0.85, 1.0, 0.0)            # tr_sign (broken -> not gravity)
    P[:, 4] = rng.uniform(2.5, 4.5, n)                            # sigma
    return P


def screen_tensor_rules(params_batch, quick=True):
    """STUB cheap screen. Deterministic given the batch (resume-exact).
    Returns per-rule arrays per the contract; passes_screen picks survivors."""
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    Bn = len(P)
    seed = int(abs(np.sin(P.sum()) * 1e9)) % (2 ** 32)            # deterministic per identical batch
    rng = np.random.default_rng(seed)
    cg2, gamma, G, tr, sigma = P.T
    stable = (cg2 < 0.5) & (gamma > 0)                            # CFL + has damping
    tt_dof = np.where(stable & (rng.random(Bn) < 0.35), 2, 6).astype(int)
    gw = 1.0 + 0.04 * (rng.random(Bn) - 0.5) * np.where(tr > 0, 1.0, 5.0)  # J5: broken tr -> off c
    gw_ok = np.abs(gw - 1.0) < 1e-2
    passes = stable & (tt_dof == 2) & gw_ok
    return {"passes_screen": passes, "stable": stable, "tt_dof": tt_dof,
            "gw_speed": gw, "gw_speed_ok": gw_ok,
            "newton_proxy": np.where(tr > 0, 2.0, 4.0),
            "emergence_proxy": tt_dof.astype(float)}


def full_rejudge_stub(params_batch):
    """STUB level-2 full re-judge (stands in for tensor_qca.evaluate_tensor_rule +
    emergence_judge.judge_emergence). Deterministic per rule. Returns lawful_tensor bool
    + the acceptance numbers the real judges would give."""
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    out = {"lawful_tensor": [], "n_prop": [], "newton_ratio": [], "gw_speed": []}
    for row in P:
        s = int(abs(np.cos(row.sum()) * 1e9)) % (2 ** 32)
        rng = np.random.default_rng(s)
        n_prop = 2 if rng.random() < 0.45 else 6                  # most screen-survivors still fail full
        newton = 2.0 if rng.random() < 0.6 else 1.4
        gw = 1.0 + 0.005 * (rng.random() - 0.5)
        lawful = (n_prop == 2) and abs(newton - 2.0) < 0.05 and abs(gw - 1.0) < 1e-2
        out["lawful_tensor"].append(lawful); out["n_prop"].append(n_prop)
        out["newton_ratio"].append(newton); out["gw_speed"].append(gw)
    return {k: np.array(v) for k, v in out.items()}
