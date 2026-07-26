"""v2m1_preflight -- M1' 预飞对拍行(任务书 §5;lane B 轮 1,2026-07-26)。

AUTHORITY(判据预注册,运行后不得回改;红线 4):
  docsv2/v2-任务书-M1-Maxwell闭环.md §5(预飞)§8(红线十条)
  docsv2/v2-收口-M0-2026-07-26.md(M0' 终态:不变量口径、双环境语义、可移植性 spec)

预飞 = 主跑前的控制行,两行:
  (i)  R23 符号层:M0' 控制矩阵行 2 复跑 -- evaluate_v2_candidate(ctrl_R23) ->
       controls.row2_r23 比对器,判据字段 diff <= 1e-12 vs 冻结 r23_results.json;
  (ii) 件10 Yee 实空间件接入统一评估器管线:photon_control(冻结 I 类判据核,
       只读 import,hash 先行写死逐位校验)的 oracle + yee_true(seed 7, T=1024)
       + solenoidal 行原样重跑,判据字段对拍 photon_control_results.json 冻结值。

判据/口径(脚本头写死;失败走追因,禁调 tol -- 任务书 §5"禁调 tol"):
  TOL_JUDGE = 1e-12          # 判据字段跨对拍门(M0' 可移植性 spec 终态)
  判据字段(整数逐位):n_prop 七 k 列、oracle n_eig_plus/minus、布尔 PASS 位
  判据字段(<=1e-12):w_meas 七 k、transverse_match 七 k、divE/divB drift、
    solenoidal divE/divB max、Yee 能量漂移、oracle w_op_vs_analytic /
    eig_absdev_max / eigmode_gauss_resid;R23 行 = row2_r23 八标量 + dims/ranks
  报告级(不设线,M0' spec:谱小分量与噪声底派生量):sv3_main、rms_growth、
    c 派生比值、iso spread、inband power

冻结件 hash(先行写死;逐位不符 = HALT,红线 2):
  experiments/photon_control.py
    38ea5bbf5282209f720c754e1f5b17a802a5e7aae19197a3b030b440402e4263
    (交叉证:photon_control_results.json 内 script_sha256 同值)
  data/results/photon_control_results.json
    76d8d120a07e8bc46810fbd78e4d859b34ee2779c4bf5d7cda6bc240c7e6c7f3
  experiments/r23_maxwell_control.py
    807b1f7fd00fc3ed141ab1ac6bc950e1325be61b33a8bf0cb78d98da76292b10
  rulespace_v2 冻结七件(v2-收口-M0-2026-07-26.md §二 现值):
    invariants.py 5d51e9733b076a71e66ab29dcb67837ada813b43f15d369617c1dbf8e1b696b3
    sigma.py      5e68622ecd46fd084993cadb0e904875e3b57d2f45f35ca2fa5832c18e29ee3b
    epsilon.py    10fbfed89436bf0f1dd1996d7c1b03b10aa5d5e5c4756f1b674e199fc8cd881c
    controls.py   8785a70e5defe89399c1c39e3deae0042ab08a0aeb1cddf8af599aa4d69c2d1f
    gates.py      f29f4cb8cd1a2d3e0c3730d4428c4870d151ba50eaa31a47f227135f981fcf68
    candidate.py  1d56818709d9ae3f0f265460c82f3b5f24699645cb35900265596b36d45f1b23
    frozen.py     45a31ecd7bd47c769da837a83b1cf6146fa249c10ff20af11e6fc0ca0c024d2f

双环境语义(M0' 终态):本脚本 = 宿主跑;JSON 留沙盒位(sandbox.status=PENDING),
沙盒双跑由车道A 复核执行。预飞不过 => 禁开主跑,停手追因报车道A。
措辞红线:预飞无任何涌现主张;PASS 只解锁"构造冻结后可开主跑"。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m1_preflight.py
      (writes data/results/v2m1_preflight.json, 增量写盘)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

from rulespace_v2 import controls as C                     # noqa: E402
from rulespace_v2 import gates as G                        # noqa: E402
from rulespace_v2 import frozen as FZ                      # noqa: E402
from rulespace_v2 import invariants as INV                 # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m1_preflight.json")

TOL_JUDGE = 1e-12                       # 写死;运行后不得回改(红线 4)

# ---- 先行写死的冻结 hash(红线 2:逐位校验只读) --------------------------
M1_FROZEN_SHA256 = {
    "experiments/photon_control.py":
        "38ea5bbf5282209f720c754e1f5b17a802a5e7aae19197a3b030b440402e4263",
    "data/results/photon_control_results.json":
        "76d8d120a07e8bc46810fbd78e4d859b34ee2779c4bf5d7cda6bc240c7e6c7f3",
    "experiments/r23_maxwell_control.py":
        "807b1f7fd00fc3ed141ab1ac6bc950e1325be61b33a8bf0cb78d98da76292b10",
}
M0_SEVEN_SHA256 = {                     # v2-收口-M0-2026-07-26.md §二 现值
    "rulespace_v2/invariants.py":
        "5d51e9733b076a71e66ab29dcb67837ada813b43f15d369617c1dbf8e1b696b3",
    "rulespace_v2/sigma.py":
        "5e68622ecd46fd084993cadb0e904875e3b57d2f45f35ca2fa5832c18e29ee3b",
    "rulespace_v2/epsilon.py":
        "10fbfed89436bf0f1dd1996d7c1b03b10aa5d5e5c4756f1b674e199fc8cd881c",
    "rulespace_v2/controls.py":
        "8785a70e5defe89399c1c39e3deae0042ab08a0aeb1cddf8af599aa4d69c2d1f",
    "rulespace_v2/gates.py":
        "f29f4cb8cd1a2d3e0c3730d4428c4870d151ba50eaa31a47f227135f981fcf68",
    "rulespace_v2/candidate.py":
        "1d56818709d9ae3f0f265460c82f3b5f24699645cb35900265596b36d45f1b23",
    "rulespace_v2/frozen.py":
        "45a31ecd7bd47c769da837a83b1cf6146fa249c10ff20af11e6fc0ca0c024d2f",
}


def _jd(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        f = float(o)
        return f if np.isfinite(f) else str(f)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def write_json(payload):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def verify_m1_hashes():
    """先行写死 hash 逐位校验(M1' 引用件 + M0' 冻结七件)。"""
    checked, ok = {}, True
    for rel, exp in {**M1_FROZEN_SHA256, **M0_SEVEN_SHA256}.items():
        got = sha256_file(os.path.join(ROOT, rel))
        m = (got == exp)
        ok = ok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    return {"pass": bool(ok), "checked": checked}


def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m1-preflight (M1' 预飞对拍行;任务书 §5;lane B 轮 1)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-任务书-M1-Maxwell闭环.md §5/§8",
                      "docsv2/v2-收口-M0-2026-07-26.md(可移植性 spec 终态)"],
        "tol_judge": TOL_JUDGE,
        "environment": env,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "wording_redline": ("预飞无任何涌现主张;PASS 只解锁'构造冻结后可开主跑'"
                            "(任务书 §8 红线 10 继承)"),
        "sandbox": {"status": "PENDING",
                    "note": ("双环境语义(M0' 终态):判据字段宿主+沙盒双跑 "
                             "diff <= 1e-12;沙盒侧由车道A 复核执行,本 JSON "
                             "为宿主参考值")},
    }
    write_json(payload)

    print("v2m1 preflight: M1' 预飞两行(R23 符号层 + 件10 Yee 实空间)")
    print("=" * 74)
    print(f"[env] numpy {env['numpy_version']}  blas={env['blas']}  "
          f"lapack={env['lapack']}  {env['platform']}")

    # ---- 0. 冻结件 hash 逐位校验(红线 2) --------------------------------
    hz1 = verify_m1_hashes()
    hz0 = FZ.verify_frozen()
    payload["hash_verification"] = {"m1_pinned": hz1,
                                    "m0_registry_pass": hz0["pass"]}
    write_json(payload)
    print(f"[cert] M1' 先行写死 hash({len(hz1['checked'])} 件): "
          f"{'PASS' if hz1['pass'] else 'FAIL'};"
          f"M0' 冻结注册表: {'PASS' if hz0['pass'] else 'FAIL'}")
    if not (hz1["pass"] and hz0["pass"]):
        payload["status"] = "HALT-frozen-hash-mismatch"
        payload["verdict"] = "冻结件 hash 不符:仪器变更嫌疑,停手报车道A(红线 2)。"
        write_json(payload)
        return 1

    # ---- (i) R23 符号层:M0' 控制矩阵行 2 复跑 ----------------------------
    tr = time.time()
    cand = C.control_candidates()["row2_r23"]
    gc = G.evaluate_v2_candidate(cand)
    row_i = C.row2_r23(gc)
    row_i["seconds"] = time.time() - tr
    ok_i = bool(row_i["pass"] and row_i["max_abs_diff"] <= TOL_JUDGE)
    payload["preflight_i_r23_symbol"] = {
        "row2_r23": row_i, "pass": ok_i,
        "judge_fields": ("八标量(null/cg/dist_transverse/F_gauge/"
                         "F_transverse_min/transverse_retention/"
                         "constraint_decay/operator_err)diff<=1e-12 + "
                         "dims/ranks 整数逐位 + eps_DOF 锚定义值 1.0"),
        "note_epsilon": ("此处 eps_DOF=1.0 是 D1 定义锚(hand_built=None),"
                         "非 M1'-G8 实测;实测在主跑(红线 5)")}
    write_json(payload)
    print(f"[(i) R23 行2 复跑] {'PASS' if ok_i else 'FAIL'}  "
          f"max_abs_diff={row_i['max_abs_diff']:.2e} <= {TOL_JUDGE:.0e}  "
          f"({row_i['seconds']:.1f}s)")
    if not ok_i:
        payload["status"] = "HALT-preflight-i-failed"
        payload["verdict"] = ("预飞 (i) R23 对拍不落位:停手追因(禁调 tol),"
                              "报车道A;禁开主跑(任务书 §5)。")
        write_json(payload)
        return 1

    # ---- (ii) 件10 Yee 实空间件:冻结判据核原样重跑 + 对拍 ----------------
    tr = time.time()
    PC = FZ.mod("photon_control")               # 只读 import(hash 已校验)
    with open(os.path.join(ROOT, "data", "results",
                           "photon_control_results.json"),
              "r", encoding="utf-8") as fh:
        FRZ = json.load(fh)
    # 交叉证:冻结 JSON 内嵌 script_sha256 == 磁盘文件 hash(先行记录逐位)
    cross = (FRZ["script_sha256"]
             == hz1["checked"]["experiments/photon_control.py"]["sha256"])
    print(f"[(ii)] photon_control 冻结核 import;JSON 内嵌 script_sha256 "
          f"交叉证: {'PASS' if cross else 'FAIL'}")
    if not cross:
        payload["status"] = "HALT-lineage-mismatch"
        write_json(payload)
        return 1

    KM = [tuple(v) for v in FRZ["k_probes"]]
    # oracle(算子级,七 k)
    oracles = {nv: PC.yee_oracle(PC.kvec_of(nv)) for nv in KM}
    # yee_true(seed=SEED_TRUE=7,T=1024,generic IC,冻结协议原样)
    st = PC.seed_generic(2, PC.SEED_TRUE)
    res_true = PC.judge("yee_true", st, PC.step_yee, energy=True,
                        oracles=oracles)
    # solenoidal 行(seed=SEED_SOL=8,256 步,冻结协议原样)
    E0, B0 = PC.seed_generic(2, PC.SEED_SOL)
    E0 = PC.solenoidal_project(E0, "E")
    B0 = PC.solenoidal_project(B0, "B")
    sc = float(np.abs(E0).max())
    dEm = dBm = 0.0
    stt = (E0, B0)
    for t in range(256):
        stt = PC.step_yee(stt)
        if t % 32 == 0 or t == 255:
            dEm = max(dEm, float(np.abs(PC.div(stt[0], PC._dm)).max()) / sc)
            dBm = max(dBm, float(np.abs(PC.div(stt[1], PC._dp)).max()) / sc)
    res_sol = {"divE_max_rel": dEm, "divB_max_rel": dBm}
    gates = PC.eval_positive_gates(res_true, oracles, res_sol)
    sec_ii = time.time() - tr

    # ---- 对拍:判据字段 vs 冻结值 -----------------------------------------
    fP = FRZ["yee_true"]["per_k"]
    fM = FRZ["yee_true"]["monitor"]
    fS = FRZ["yee_solenoidal"]
    fO = FRZ["oracle"]
    P = res_true["per_k"]
    int_ok, judge_diffs, report_level = True, {}, {}
    for nv in KM:
        kk = str(nv)
        e, f = P[kk], fP[kk]
        int_ok = int_ok and (e["n_prop"] == f["n_prop"] == 2)
        judge_diffs[f"w_meas@{kk}"] = abs(e["w_meas"] - f["w_meas"])
        judge_diffs[f"transverse_match@{kk}"] = abs(
            e["transverse_match"] - f["transverse_match"])
        report_level[f"sv3_main@{kk}"] = {
            "remeasured": e["sv3_main"], "frozen": f["sv3_main"],
            "diff": abs(e["sv3_main"] - f["sv3_main"])}
        o, fo = oracles[nv], fO[kk]
        int_ok = int_ok and (o["n_eig_plus"] == fo["n_eig_plus"]
                             and o["n_eig_minus"] == fo["n_eig_minus"])
        judge_diffs[f"w_op_vs_analytic@{kk}"] = abs(
            o["w_op_vs_analytic"] - fo["w_op_vs_analytic"])
        judge_diffs[f"eig_absdev@{kk}"] = abs(
            o["eig_absdev_max"] - fo["eig_absdev_max"])
        judge_diffs[f"eigmode_gauss_resid@{kk}"] = abs(
            o["eigmode_gauss_resid"] - fo["eigmode_gauss_resid"])
    m = res_true["monitor"]
    judge_diffs["divE_drift_rel"] = abs(m["divE_drift_rel"]
                                        - fM["divE_drift_rel"])
    judge_diffs["divB_drift_rel"] = abs(m["divB_drift_rel"]
                                        - fM["divB_drift_rel"])
    judge_diffs["yee_energy_drift_rel"] = abs(
        m["yee_energy_drift_rel"] - fM["yee_energy_drift_rel"])
    judge_diffs["sol_divE_max_rel"] = abs(dEm - fS["divE_max_rel"])
    judge_diffs["sol_divB_max_rel"] = abs(dBm - fS["divB_max_rel"])
    bool_ok = bool(gates["ALL_PASS"]
                   and FRZ["positive_gates"]["ALL_PASS"]
                   and all(o["PASS"] for o in oracles.values()))
    report_level["rms_growth"] = {"remeasured": m["rms_growth"],
                                  "frozen": fM["rms_growth"]}
    report_level["c_vs_cyee_reldev_max"] = {
        "remeasured": gates["P2_c_vs_cyee_reldev_max"],
        "frozen": FRZ["positive_gates"]["P2_c_vs_cyee_reldev_max"]}
    report_level["iso_spread"] = {
        "remeasured": gates["P3_iso_spread"],
        "frozen": FRZ["positive_gates"]["P3_iso_spread"]}
    worst = max(judge_diffs.values())
    ok_ii = bool(int_ok and bool_ok and worst <= TOL_JUDGE)

    payload["preflight_ii_yee_realspace"] = {
        "protocol": ("photon_control 冻结核只读 import:yee_oracle 七 k + "
                     "judge(yee_true, seed 7, T=1024, trials 8, 16^3) + "
                     "solenoidal(seed 8, 256 步) + eval_positive_gates;"
                     "判据核零重写(红线 3)"),
        "n_prop_sevenk": {str(nv): P[str(nv)]["n_prop"] for nv in KM},
        "n_prop_frozen": {str(nv): fP[str(nv)]["n_prop"] for nv in KM},
        "integers_bitwise_ok": bool(int_ok),
        "booleans_ok": bool_ok,
        "judge_field_diffs": judge_diffs,
        "judge_field_diff_max": worst,
        "report_level_no_gate": report_level,
        "positive_gates_remeasured": {
            k: v for k, v in gates.items()
            if not isinstance(v, (dict, list))},
        "seconds": sec_ii, "pass": ok_ii}
    write_json(payload)
    print(f"[(ii) 件10 Yee 实空间] {'PASS' if ok_ii else 'FAIL'}  "
          f"整数逐位={'OK' if int_ok else 'MISMATCH'}  "
          f"判据字段 max diff={worst:.2e} <= {TOL_JUDGE:.0e}  "
          f"({sec_ii:.1f}s)")
    for kk, dv in judge_diffs.items():
        if dv > TOL_JUDGE:
            print(f"    !! 超线: {kk} diff={dv:.3e}")

    # ---- 判定 --------------------------------------------------------------
    all_ok = bool(ok_i and ok_ii)
    payload["preflight_pass"] = all_ok
    payload["status"] = "DONE" if all_ok else "HALT-preflight-ii-failed"
    payload["verdict"] = (
        "预飞 PASS(宿主):(i) R23 符号层行 2 复跑判据字段全 <=1e-12;"
        "(ii) 件10 Yee 实空间件经冻结判据核重跑,整数逐位 + 判据字段全 <=1e-12 "
        "对拍冻结值。主跑解锁前提之一达成;本轮不开主跑(轮 1 纪律:构造冻结先行);"
        "沙盒双跑位留待车道A。无任何涌现主张。" if all_ok else
        "预飞不落位:停手追因(禁调 tol),报车道A;禁开主跑(任务书 §5)。")

    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)
    print("=" * 74)
    print(f"PREFLIGHT: {'PASS' if all_ok else 'HALT'}  ->  {payload['status']}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
