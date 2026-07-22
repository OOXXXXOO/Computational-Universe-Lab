"""tensor_campaign_runner — resumable/observable long-run harness for the TENSOR
rule search. Same paradigm & robustness as campaign_runner (scalar), but the
workload is the two-level tensor funnel of TENSOR_CAMPAIGN_INTERFACE.md:

    sample_tensor_prior -> screen_tensor_rules (level 1, batch, cheap)
                        -> survivors -> full re-judge (level 2, tensor_qca/emergence)

The harness does NO physics. Level 1 + level 2 come from lane A / existing judges;
here they are STUBS (rulespace_gpu.tensor_screen_stub) so the orchestration +
checkpoint/resume/control run end-to-end today. Swap the two imports below for the
real kernel when it lands -- nothing else changes.

Resume is EXACT: batch i uses prior seed = i, so progress is a pure function of
batches_done (continuous run == chunked == resumed).

CLI mirrors campaign_runner: run [--fresh --target N --batch B] | pause|resume|stop|status|reset
"""
import os, json, time, signal, argparse, tempfile
import numpy as np

# ---- level 1: lane-A's real batch screen kernel (tensor_batch) ----
from rulespace_gpu.tensor_batch import PARAM_NAMES, sample_tensor_prior, screen_tensor_rules
# ---- level 2: existing full re-judge (tensor_qca 3-judge acceptance) ----
from rulespace_gpu.tensor_qca import evaluate_tensor_rule
# ---- level 2: HIGH-FIDELITY gw gate (spectral graviton group velocity / walker
#      matter speed; receipt clause #3). Replaces the tier-1 gw placeholder. ----
from rulespace_gpu.tier2_gw import tier2_gw, C_MATTER_WALKER


def full_rejudge(params_batch):
    """Level-2 (tier-2) full re-judge on screen survivors: tensor_qca's 3-judge
    acceptance per rule. Robust to per-rule crashes (ill-conditioned diagnostics
    -> not lawful, counted) so one bad rule never kills the campaign."""
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    law, npr, newt, defl, err = [], [], [], [], 0
    for row in P:
        try:
            r = evaluate_tensor_rule(row[None, :], quick=True)
            law.append(bool(r["passes"][0])); npr.append(int(r["tt_dof"][0]))
            newt.append(float(r["newton_ratio"][0])); defl.append(float(r["deflection"][0]))
        except Exception:
            law.append(False); npr.append(6); newt.append(float("nan")); defl.append(float("nan")); err += 1
    return {"lawful_tensor": np.array(law), "n_prop": np.array(npr),
            "newton_ratio": np.array(newt), "deflection": np.array(defl), "n_err": err}

DIR = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(DIR, "run_tensor")
STATE = os.path.join(RUN, "state.json")
CONTROL = os.path.join(RUN, "control.json")
BEST = os.path.join(RUN, "best_rule.json")
ACC = os.path.join(RUN, "_acc.json")
HIST_CAP = 400
TIER2_GW_TOL = 1e-2          # tier-2 gw gate (tighter than tier-1's 0.05); see lawful block

_stop = False
def _sig(*_):
    global _stop; _stop = True
signal.signal(signal.SIGINT, _sig); signal.signal(signal.SIGTERM, _sig)


def atomic_write(path, obj):
    fd, tmp = tempfile.mkstemp(dir=RUN, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

def read_json(p, d=None):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def control_command():
    return (read_json(CONTROL, {}) or {}).get("command", "run")

def set_control(cmd):
    os.makedirs(RUN, exist_ok=True); atomic_write(CONTROL, {"command": cmd, "t": time.time()})


def fresh_acc(target):
    P = len(PARAM_NAMES)
    return {"status": "starting", "target": target, "started_at": time.time(),
            "updated_at": time.time(), "wall_seconds": 0.0, "batches_done": 0, "rules_done": 0,
            "batch": None, "rate": 0.0,
            "screened_pass": 0,          # level-1 survivors (passes_screen)
            "stable": 0, "tt2": 0, "gw_ok": 0,
            "gw2_ok": 0,                 # tier-2 high-fidelity gw gate passes (group velocity)
            "lawful_tensor": 0,          # level-2 survivors (full re-judge) = the honest number
            "tier2_err": 0,              # per-rule tier-2 crashes caught (ill-conditioned diagnostics)
            # survival manifold over params: running mean of survivor param vectors
            "surv_sum": [0.0] * P, "surv_n": 0,
            "best": None, "history": []}


def snapshot(acc):
    r = max(acc["rules_done"], 1)
    surv_mean = [round(s / acc["surv_n"], 4) for s in acc["surv_sum"]] if acc["surv_n"] else [0.0] * len(PARAM_NAMES)
    return {"status": acc["status"], "target": acc["target"], "started_at": acc["started_at"],
            "updated_at": acc["updated_at"], "wall_seconds": round(acc["wall_seconds"], 1),
            "batches_done": acc["batches_done"], "rules_done": acc["rules_done"],
            "batch": acc["batch"], "rate": round(acc["rate"], 0),
            "param_names": PARAM_NAMES,
            "screened_pass": acc["screened_pass"], "stable": acc["stable"],
            "tt2": acc["tt2"], "gw_ok": acc["gw_ok"], "gw2_ok": acc.get("gw2_ok", 0),
            "lawful_tensor": acc["lawful_tensor"],
            "tier2_err": acc.get("tier2_err", 0),
            "screen_pct": round(100 * acc["screened_pass"] / r, 3),
            "lawful_tensor_pct": round(100 * acc["lawful_tensor"] / r, 4),
            "surv_param_mean": surv_mean, "best": acc["best"], "history": acc["history"][-HIST_CAP:]}


def checkpoint(acc):
    acc["updated_at"] = time.time()
    atomic_write(STATE, snapshot(acc)); atomic_write(ACC, acc)
    if acc["best"]: atomic_write(BEST, acc["best"])


def run(args):
    os.makedirs(RUN, exist_ok=True)
    acc = None if args.fresh else read_json(ACC)
    if acc is None:
        acc = fresh_acc(args.target)
    else:
        acc["target"] = args.target if args.target else acc.get("target")
    acc["batch"] = args.batch
    set_control("run"); acc["status"] = "running"
    print(f"[tensor-runner] resuming at batch {acc['batches_done']} ({acc['rules_done']} rules); "
          f"level1={screen_tensor_rules.__module__}")
    t_mark = time.time(); r_mark = acc["rules_done"]; checkpoint(acc)

    while not _stop:
        cmd = control_command()
        if cmd == "stop": break
        if cmd == "pause":
            if acc["status"] != "paused": acc["status"] = "paused"; checkpoint(acc)
            elif time.time() - acc["updated_at"] > 2.0: checkpoint(acc)
            time.sleep(0.5); t_mark = time.time(); continue
        if acc["status"] != "running": acc["status"] = "running"; checkpoint(acc)
        if acc["target"] and acc["rules_done"] >= acc["target"]:
            acc["status"] = "done"; checkpoint(acc); break

        i = acc["batches_done"]
        P = sample_tensor_prior(args.batch, seed=i)            # deterministic -> exact resume
        # ---- level 1: batch fast screen ----
        s = screen_tensor_rules(P)
        acc["stable"] += int(np.sum(s["stable"]))
        acc["tt2"] += int(np.sum(s["tt_dof"] == 2))
        acc["gw_ok"] += int(np.sum(s["gw_speed_ok"]))
        surv = np.asarray(s["passes_screen"], bool)
        acc["screened_pass"] += int(surv.sum())
        # ---- level 2: full re-judge on the (rare) screen survivors ----
        if surv.any():
            Psurv = P[surv]
            fr = full_rejudge(Psurv)
            acc["tier2_err"] = acc.get("tier2_err", 0) + fr["n_err"]
            # tier-2 = evaluate_tensor_rule (3 judges) AND a HIGH-FIDELITY gw gate.
            # The gw gate is now the receipt clause #3 quantity (tier2_gw): the
            # SPECTRAL graviton group velocity c_gw divided by the walker matter
            # speed c_matter (0.993), gated |c_gw/c_matter - 1| < 1e-2.  This
            # REPLACES the old placeholder (reusing tier-1's packet-centroid gw,
            # whose 1e-2 band was measurement-floor NOISE -> noise selection).
            # tier2_gw is a deterministic pure function of params -> exact resume.
            gw = tier2_gw(Psurv, c_matter=C_MATTER_WALKER, tol=TIER2_GW_TOL)
            gw_surv = np.asarray(gw["gw_speed"])               # measured c_gw
            gw_ratio = np.asarray(gw["gw_ratio"])
            gw_ok = np.asarray(gw["gw_ok"], bool)
            acc["gw2_ok"] = acc.get("gw2_ok", 0) + int(gw_ok.sum())
            law = np.asarray(fr["lawful_tensor"], bool) & gw_ok
            lawful_P = Psurv[law]
            acc["lawful_tensor"] += int(law.sum())
            for v in lawful_P:                                 # survival manifold
                for j in range(len(PARAM_NAMES)): acc["surv_sum"][j] += float(v[j])
                acc["surv_n"] += 1
            # best = tightest lawful: newton closest to 2 AND deflection closest to 2
            if law.any():
                newt = np.asarray(fr["newton_ratio"])[law]; defl = np.asarray(fr["deflection"])[law]
                gwl = gw_surv[law]; gwr = gw_ratio[law]
                score = np.abs(newt - 2.0) + np.abs(defl - 2.0)
                k = int(np.argmin(score)); cand_score = float(score[k])
                if acc["best"] is None or cand_score < acc["best"].get("score", float("inf")):
                    acc["best"] = {"params": [float(x) for x in lawful_P[k]],
                                   "param_names": PARAM_NAMES,
                                   "n_prop": int(np.asarray(fr["n_prop"])[law][k]),
                                   "newton_ratio": float(newt[k]), "deflection": float(defl[k]),
                                   "gw_speed": float(gwl[k]), "gw_ratio": float(gwr[k]),
                                   "score": cand_score, "found_at_rules": acc["rules_done"]}

        acc["batches_done"] += 1; acc["rules_done"] += args.batch
        now = time.time(); acc["wall_seconds"] += now - t_mark
        acc["rate"] = (acc["rules_done"] - r_mark) / max(now - t_mark, 1e-6)
        t_mark = now; r_mark = acc["rules_done"]
        acc["history"].append({"t": round(acc["wall_seconds"], 1), "rules": acc["rules_done"],
                               "screened": acc["screened_pass"], "lawful": acc["lawful_tensor"],
                               "rate": round(acc["rate"], 0)})
        acc["history"] = acc["history"][-HIST_CAP:]
        checkpoint(acc)

    acc["status"] = "stopped" if not (acc["target"] and acc["rules_done"] >= acc["target"]) else "done"
    checkpoint(acc)
    print(f"[tensor-runner] {acc['status']} at batch {acc['batches_done']} ({acc['rules_done']} rules) "
          f"screened={acc['screened_pass']} lawful_tensor={acc['lawful_tensor']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fresh", action="store_true")
    r.add_argument("--target", type=int, default=0)
    r.add_argument("--batch", type=int, default=4096)
    for c in ("pause", "resume", "stop", "status", "reset"):
        sub.add_parser(c)
    a = ap.parse_args()
    if a.cmd == "run": run(a)
    elif a.cmd in ("pause", "stop"): set_control(a.cmd); print(f"[ctl] -> {a.cmd}")
    elif a.cmd == "resume": set_control("run"); print("[ctl] -> run")
    elif a.cmd == "status":
        s = read_json(STATE); print(json.dumps(s, indent=2, ensure_ascii=False) if s else "no state yet")
    elif a.cmd == "reset":
        for p in (STATE, CONTROL, BEST, ACC):
            if os.path.exists(p): os.remove(p)
        print("[ctl] run_tensor/ wiped")


if __name__ == "__main__":
    main()
