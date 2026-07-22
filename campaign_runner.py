"""campaign_runner — a resumable, checkpointable, observable long-run rule search.

The *paradigm*, not just a script: start it, stop it, resume it — any time — and a
dashboard can watch it live. The heavy research workload (a tensor-QCA rule search)
plugs into the same harness later; for now the proven workload is the scalar
rule-space survival + equivalence-principle funnel (rulespace_gpu.campaign.sweep),
which we KNOW converges — so the harness is validated against known-good physics.

Design contract (everything the dashboard/server rely on):
  run/state.json    written ATOMICALLY every checkpoint (tmp + os.replace)
  run/control.json  {"command": "run"|"pause"|"stop"} — polled every batch
  run/best_rule.json a representative lawful rule's 6 coefficients (for live viz)

Resume is EXACT: batch i always uses coupling seed = i, so total progress is a pure
function of `batches_done`. Continuous run == chunked run == resumed run.

CLI:
  python campaign_runner.py run [--fresh] [--target N] [--batch B] [--full/--j1]
  python campaign_runner.py pause | resume | stop        (writes control.json)
  python campaign_runner.py status                        (prints state.json)
  python campaign_runner.py reset                         (wipe run/ state)
"""
import os, sys, json, time, signal, argparse, tempfile
import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(DIR, "run")
STATE = os.path.join(RUN, "state.json")
CONTROL = os.path.join(RUN, "control.json")
BEST = os.path.join(RUN, "best_rule.json")
OPS = ["Lap", "(grad)^2", "rho", "J", "th-ref", "damp"]
RESERVOIR = 1500          # capped sample of survivor coeff rows for median|a|
HIST_CAP = 400            # sparkline points

_stop = False
def _sig(*_):                       # graceful: finish the batch, checkpoint, exit
    global _stop; _stop = True
signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)


def atomic_write(path, obj):
    fd, tmp = tempfile.mkstemp(dir=RUN, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f)
        os.replace(tmp, path)       # atomic on POSIX
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def control_command():
    return (read_json(CONTROL, {}) or {}).get("command", "run")


def set_control(cmd):
    os.makedirs(RUN, exist_ok=True)
    atomic_write(CONTROL, {"command": cmd, "t": time.time()})


# ---------------- accumulator (checkpoint-serializable) ----------------
def fresh_acc(target, full):
    z = [0.0] * 6
    return {
        "status": "starting", "full": bool(full), "target": target,
        "started_at": time.time(), "updated_at": time.time(), "wall_seconds": 0.0,
        "batches_done": 0, "rules_done": 0, "batch": None,
        "stable": 0, "j1j3": 0, "lawful": 0, "lawful_endured": 0, "rate": 0.0,
        # exact per-op sums
        "st_active": list(z), "st_pos": list(z), "st_n": 0,
        "lw_active": list(z), "lw_pos": list(z), "lw_n": 0,
        # reservoirs (rows of 6) for median|a|
        "st_res": [], "lw_res": [], "_st_seen": 0, "_lw_seen": 0,
        "best": None, "history": [],
    }


def reservoir_add(res, seen_key, acc, rows, rng):
    """classic reservoir sampling to keep <=RESERVOIR representative rows."""
    seen = acc[seen_key]
    for r in rows:
        seen += 1
        if len(res) < RESERVOIR:
            res.append([float(x) for x in r])
        else:
            j = int(rng.integers(0, seen))
            if j < RESERVOIR:
                res[j] = [float(x) for x in r]
    acc[seen_key] = seen


def manifold_from(active, pos, n, res):
    res = np.array(res) if res else np.zeros((0, 6))
    out = []
    for i, nm in enumerate(OPS):
        col = res[:, i] if len(res) else np.zeros(0)
        a = np.abs(col[col != 0])
        out.append({"op": nm,
                    "active": round(100 * active[i] / n, 1) if n else 0.0,
                    "pos": round(100 * pos[i] / max(active[i], 1), 0) if active[i] else 0.0,
                    "med": round(float(np.median(a)), 4) if len(a) else 0.0})
    return out


def snapshot(acc):
    """the public state.json the dashboard reads."""
    n_st, n_lw = acc["st_n"], acc["lw_n"]
    return {
        "status": acc["status"], "full": acc["full"], "target": acc["target"],
        "started_at": acc["started_at"], "updated_at": acc["updated_at"],
        "wall_seconds": round(acc["wall_seconds"], 1),
        "batches_done": acc["batches_done"], "rules_done": acc["rules_done"],
        "batch": acc["batch"], "rate": round(acc["rate"], 0),
        "stable": acc["stable"], "j1j3": acc["j1j3"], "lawful": acc["lawful"],
        "lawful_endured": acc.get("lawful_endured", 0),
        "stable_pct": round(100 * acc["stable"] / max(acc["rules_done"], 1), 2),
        "lawful_pct": round(100 * acc["lawful"] / max(acc["rules_done"], 1), 3),
        "lawful_endured_pct": round(100 * acc.get("lawful_endured", 0) / max(acc["rules_done"], 1), 3),
        "manifold_stable": manifold_from(acc["st_active"], acc["st_pos"], n_st, acc["st_res"]),
        "manifold_lawful": manifold_from(acc["lw_active"], acc["lw_pos"], n_lw, acc["lw_res"]),
        "best": acc["best"], "history": acc["history"][-HIST_CAP:],
    }


def checkpoint(acc):
    acc["updated_at"] = time.time()
    atomic_write(STATE, snapshot(acc))
    atomic_write(os.path.join(RUN, "_acc.json"), acc)     # full internal state for exact resume
    if acc["best"]:
        atomic_write(BEST, acc["best"])


def probe_alive(coeffs, T=2000):
    """CPU (fp64 reference) ENDURANCE probe for a candidate best rule.

    Guards best-rule selection against two failure modes that the T=400 funnel
    window cannot see:
      (1) degenerate 'perfect' fit -- a frozen field (theta_tt == 0) has
          SS_tot == 0, so r2 = 1 and univ_dist = 0 vacuously; and
      (2) SLOW RUNAWAY -- a rule that looks stable in 400 steps but saturates
          the clamp by ~600-2000 steps. The funnel's J1 (and this probe, when
          it also ran at T=400) shared that blind spot. We now integrate the
          fp64 reference to T=2000 and REJECT if saturation crosses the J1 bar.

    Returns (alive: bool, theta_tt_rms: float).
    """
    try:
        from rulespace.core import run_coupled, TH_MIN, TH_MAX
        out = run_coupled(np.asarray(coeffs, dtype=float), N=256, T=T)
        if out is None:
            return False, 0.0
        if out["sat"] >= 0.01 or out["final_var"] >= 0.25:   # slow runaway over the long horizon
            return False, 0.0
        th = out["theta"]
        tt = th[2:] - 2.0 * th[1:-1] + th[:-2]            # discrete theta_tt
        m = (th[2:] > TH_MIN + 1e-9) & (th[2:] < TH_MAX - 1e-9)
        if m.mean() < 0.05:                               # nearly everything clamped
            return False, 0.0
        rms = float(np.sqrt(np.mean(tt[m] ** 2)))
        return rms > 1e-8, rms
    except Exception as e:                                # probe unavailable: don't block, but say so
        print(f"[runner] warning: best-rule dynamics probe failed ({e}); accepting unverified")
        return True, -1.0


# ---------------- the run loop ----------------
def run(args):
    os.makedirs(RUN, exist_ok=True)
    from rulespace_gpu import backend as B
    from rulespace_gpu.campaign import sweep, random_couplings

    acc = None if args.fresh else read_json(os.path.join(RUN, "_acc.json"))
    if acc is None:
        acc = fresh_acc(args.target, args.full)
    else:
        acc["target"] = args.target if args.target else acc.get("target")
        acc["full"] = args.full
    acc["batch"] = args.batch
    set_control("run")
    acc["status"] = "running"
    rng = np.random.default_rng(20260719)
    saved_rng = acc.get("_rng")                            # exact-resume: reservoir rng continues
    if saved_rng is not None:
        try:
            rng.bit_generator.state = saved_rng
        except Exception:
            pass
    if acc.get("best"):                                    # re-validate a checkpointed best
        ok, rms = probe_alive(acc["best"]["coeffs"])
        if not ok:
            print("[runner] dropping checkpointed best: degenerate (frozen-field) fit")
            acc["best"] = None
        else:
            acc["best"]["theta_tt_rms"] = round(rms, 8)
            try:                                           # legacy checkpoints rounded univ_dist
                rs = sweep(np.array([acc["best"]["coeffs"]]), N=args.N, T=args.T_endure, full=True)
                acc["best"]["univ_dist"] = float(rs["univ_dist"][0])
                acc["best"]["r2"] = float(rs["r2_reduced_min"][0])
                acc["best"]["saturation"] = round(float(rs["saturation"][0]), 5)
            except Exception:
                pass
    print(f"[runner] backend={B.NAME} {B.device_info()}  resuming at "
          f"batch {acc['batches_done']} ({acc['rules_done']} rules), full={acc['full']}")

    t_mark, r_mark = time.time(), acc["rules_done"]
    checkpoint(acc)
    while not _stop:
        cmd = control_command()
        if cmd == "stop":
            break
        if cmd == "pause":
            if acc["status"] != "paused":
                acc["status"] = "paused"; checkpoint(acc)
            elif time.time() - acc["updated_at"] > 2.0:
                checkpoint(acc)          # heartbeat: dashboard keeps seeing a live (paused) process
            time.sleep(0.5)
            t_mark = time.time()         # pause time must NOT pollute wall_seconds / rate
            continue
        if acc["status"] != "running":
            acc["status"] = "running"; checkpoint(acc)   # flip state.json promptly on resume
        if acc["target"] and acc["rules_done"] >= acc["target"]:
            acc["status"] = "done"; checkpoint(acc); break

        i = acc["batches_done"]
        cpl = random_couplings(args.batch, seed=i)         # deterministic per batch -> exact resume
        res = sweep(cpl, N=args.N, T=args.T, full=acc["full"])
        st = res["stable"]
        acc["stable"] += int(st.sum()); acc["st_n"] += int(st.sum())
        sv = cpl[st]
        for i_op in range(6):
            acc["st_active"][i_op] += int((sv[:, i_op] != 0).sum())
            acc["st_pos"][i_op] += int((sv[:, i_op] > 0).sum())
        reservoir_add(acc["st_res"], "_st_seen", acc, sv, rng)
        if acc["full"]:
            j3 = st & res["J3"]; law = res["lawful"]
            acc["j1j3"] += int(j3.sum()); acc["lawful"] += int(law.sum())   # raw T=400 lawful
            lv = cpl[law]
            # ENDURANCE re-judge: rerun the full funnel at T_endure on the (rare) lawful
            # survivors. ~30% of T=400-lawful rules are slow-runaway false positives that
            # only saturate the clamp by ~T=2000; lawful_endured is the honest statistic.
            if len(lv) and args.T_endure > args.T:
                er = sweep(lv, N=args.N, T=args.T_endure, full=True)
                endured = er["lawful"]
            else:                                          # endurance off (T_endure<=T): index res->lv
                er = {kk: res[kk][law] for kk in ("univ_dist", "r2_reduced_min", "saturation")}
                endured = np.ones(len(lv), bool)
            ev = lv[endured]
            acc["lawful_endured"] = acc.get("lawful_endured", 0) + int(endured.sum())
            acc["lw_n"] += len(ev)
            for i_op in range(6):                          # manifold from ENDURED survivors
                acc["lw_active"][i_op] += int((ev[:, i_op] != 0).sum())
                acc["lw_pos"][i_op] += int((ev[:, i_op] > 0).sum())
            reservoir_add(acc["lw_res"], "_lw_seen", acc, ev, rng)
            # best = smallest T_endure univ_dist among ENDURED survivors, gated by the
            # T=2000 dynamics/endurance probe. univ_dist stored at full precision.
            if endured.any():
                ud_arr = np.asarray(er["univ_dist"])
                eloc = np.where(endured)[0]
                order = eloc[np.argsort(ud_arr[eloc])]
                cur_ud = acc["best"]["univ_dist"] if acc["best"] else float("inf")
                probes = 0
                for k in order:
                    ud = float(ud_arr[k])
                    if ud >= cur_ud or probes >= 8:       # bounded probe cost per batch
                        break
                    probes += 1
                    alive, rms = probe_alive(lv[k])
                    if alive:
                        acc["best"] = {"coeffs": [float(x) for x in lv[k]],
                                       "univ_dist": ud,
                                       "r2": float(np.asarray(er["r2_reduced_min"])[k]),
                                       "saturation": round(float(np.asarray(er["saturation"])[k]), 5),
                                       "theta_tt_rms": round(rms, 8),
                                       "found_at_rules": acc["rules_done"]}
                        break

        acc["batches_done"] += 1
        acc["rules_done"] += args.batch
        now = time.time()
        acc["wall_seconds"] += now - t_mark
        acc["rate"] = (acc["rules_done"] - r_mark) / max(now - t_mark, 1e-6)
        t_mark, r_mark = now, acc["rules_done"]
        acc["history"].append({"t": round(acc["wall_seconds"], 1),
                               "rules": acc["rules_done"], "stable": acc["stable"],
                               "lawful": acc["lawful"], "rate": round(acc["rate"], 0)})
        acc["history"] = acc["history"][-HIST_CAP:]
        acc["_rng"] = rng.bit_generator.state             # reservoir rng survives stop/resume
        checkpoint(acc)

    acc["status"] = "stopped" if not (acc["target"] and acc["rules_done"] >= acc["target"]) else "done"
    checkpoint(acc)
    print(f"[runner] {acc['status']} at batch {acc['batches_done']} "
          f"({acc['rules_done']} rules)  stable={acc['stable']} lawful={acc['lawful']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fresh", action="store_true")
    r.add_argument("--target", type=int, default=0, help="stop after N rules (0 = unbounded)")
    r.add_argument("--batch", type=int, default=4096)
    r.add_argument("--N", type=int, default=256)
    r.add_argument("--T", type=int, default=400)
    r.add_argument("--T-endure", dest="T_endure", type=int, default=2000,
                   help="endurance re-judge horizon for lawful survivors + best "
                        "(default 2000; ~30%% of T=400-lawful are slow-runaway false positives; "
                        "set <= --T to disable)")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--full", dest="full", action="store_true", help="J1+J3+J4 funnel (default)")
    g.add_argument("--j1", dest="full", action="store_false", help="J1-only (faster)")
    r.set_defaults(full=True)
    for c in ("pause", "resume", "stop", "status", "reset"):
        sub.add_parser(c)
    a = ap.parse_args()

    if a.cmd == "run":
        run(a)
    elif a.cmd in ("pause", "stop"):
        set_control(a.cmd); print(f"[ctl] -> {a.cmd}")
    elif a.cmd == "resume":
        set_control("run"); print("[ctl] -> run")
    elif a.cmd == "status":
        s = read_json(STATE)
        print(json.dumps(s, indent=2) if s else "no state yet (run/ empty)")
    elif a.cmd == "reset":
        for p in (STATE, CONTROL, BEST, os.path.join(RUN, "_acc.json")):
            if os.path.exists(p):
                os.remove(p)
        print("[ctl] run/ state wiped")


if __name__ == "__main__":
    main()
