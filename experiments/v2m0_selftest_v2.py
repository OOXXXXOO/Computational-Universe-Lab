"""v2m0_selftest_v2 -- M0' 整改版控制矩阵自检(M0' 补丁;lane B,2026-07-26)。

AUTHORITY(判据预注册,运行后不得回改):
  docsv2/v2-复核-车道A-M0仪器迁移-2026-07-26.md §三(判决实验与不变量表)
  §四(整改令六条)§五(连带裁定);docsv2/v2-任务书-M0-仪器迁移.md(原判据框架,
  红线七条继续有效)。

整改背景:控制矩阵宿主 8/8,独立环境(沙盒 Linux/OpenBLAS)6/8——行5/行8 失守于
物理层读数。追因(复核 §三,环境无关判决实验):逐模残差统计(resid_min/max)与
逐模贪心 j_hand 建立在 ±ω 精确简并子空间的 LAPACK 任意基上,**不是基不变观测量**;
真观测量 = 主角谱 {sin θ_i}、max sin θ、Frobenius 泄漏、N_prop 秩。本脚本执行
整改令 1-4/6 的判据侧:
  1  σ 读数不变量化(sigma.calibration_16cube_invariant / direction_fits_invariant);
  2  ε_DOF 不变量化(epsilon.measure_frozen_walk_epsilon_invariant;
     j_hand_inv = #{sin θ_i(span(S_curv), ker C) >= 0.05},整数、基无关);
  3  行5/行8 判据改口(controls.py 模块头写死):逐位档只留真逐位量;连续读数改
     不变量;基稳健性自检 = 3 次固定种子簇内酉旋转(seeds 0/1/2),漂移 <= 1e-12;
     跨环境不变量比对(tol 1e-12)由车道A 沙盒双跑执行,本 JSON 入册宿主参考值;
  4  环境入册:numpy 版本 + BLAS/LAPACK 后端 + 平台;R23 行注冻结 JSON 环境谱系。

首个自检(硬门,对不上=实现有错):16³ 三判据 k 的不变量须复现复核 §三判决表
  (2,0,0): max sinθ=1.0000, frob=1.035;(2,2,0): 0.1948, 0.304;(2,2,2): 0.1493, 0.211
  (容差 = 表列显示精度:sin 1e-4 / frob 1e-3)。

措辞红线:整改后宿主侧全过也**不宣告 M0' 收口**——收口须双环境 8/8
(沙盒双跑由车道A 复核时执行)+ PI 签字。

输出:
  data/results/v2m0_selftest_v2.json   (整改版;旧 v2m0_selftest.json 保留不覆盖)
  data/runtime/v2m0_state.json         (dashboard v2 数据源,加不变量字段)

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m0_selftest_v2.py
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
from rulespace_v2 import sigma as SIG                      # noqa: E402
from rulespace_v2 import frozen as FZ                      # noqa: E402
from rulespace_v2 import invariants as INV                 # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m0_selftest_v2.json")
STATE = os.path.join(ROOT, "data", "runtime", "v2m0_state.json")

# 无简并子空间逐模统计入判据的行:基稳健自检记 not-applicable(理由写死)
ROBUSTNESS_NA = {
    "row1_r30": "判据 = 实空间时序 SVD 奇异值谱 + 整数计数(确定性 seed;奇异值谱本身基不变)",
    "row2_r23": "判据 = 秩/维数整数 + 机器零证书(无简并逐模统计;冻结 JSON 沙盒系,宿主差 ULP)",
    "row3_null_damped": "判据 = 整数 N_prop + 时序 SVD 奇异值谱(基不变量)",
    "row4_teeth": "判据 = 整数 N_prop 精确",
    "row6_tr_sign": "判据 = 双裁判 FAIL + 读数窗 ±0.1(标量读数,无简并子空间统计)",
    "row7_r36": "判据 = 整数 tau 列 + 标量证书(确定性;无简并逐模统计)",
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


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


STATE_SCHEMA_NOTE = {
    "_schema": "v2m0_state v2 (2026-07-26, lane B, M0' 整改版)",
    "_doc": {
        "purpose": ("dashboard v2 唯一数据源(任务书 §6;禁止读取旧 tensor "
                    "campaign payload)。整改版:σ/ε 读数不变量化(复核 §四)。"),
        "m0_status": ("整改后口径:host_pass = 宿主 k/8;cross_environment = "
                      "跨环境状态;overall 不宣告收口(须双环境 8/8 + PI 签字)。"),
        "control_matrix[]": ("8 行。行5/行8 新增:basis_robustness_check(3 次"
                             "固定种子酉旋转,漂移<=1e-12)、environment、"
                             "cross_environment_status、legacy_diagnostics_"
                             "basis_dependent(旧口径降级诊断)。"),
        "epsilon_sigma_anchors[]": ("冻结走行族 epsilon_dof_range = 不变量口径"
                                    "(j_hand_inv);legacy 旧口径并列于 "
                                    "epsilon_dof_range_legacy。sigma.by_direction"
                                    " = 不变量拟合(y=max sinθ);旧口径并列于 "
                                    "by_direction_legacy。"),
        "invariants": ("整改令判据摘要:16³ 判决数复现、不变量定义、阈值、"
                       "环境入册。"),
        "sigma_calibration_64": ("交付物 4 整改版(v2m0_sigma_calibration_v2)"
                                 "完成后由该脚本并入;含不变量口径三方向拟合与"
                                 "旧口径并列。"),
    },
}


def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m0-selftest-v2 (M0' 整改版控制矩阵;整改令 1-4/6 判据侧)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-复核-车道A-M0仪器迁移-2026-07-26.md §三/§四",
                      "docsv2/v2-任务书-M0-仪器迁移.md §4(原框架)"],
        "environment": env,
        "tol_table": {k: (v if v is not None else "judged-FAIL")
                      for k, v in C.TOL.items()},
        "review_judgement_reference_16cube":
            {str(k): v for k, v in SIG.REVIEW_JUDGEMENT_16CUBE.items()},
        "invariant_definitions": {
            "sigma_primary": "max sin θ(span(B₊) vs ker C 主角谱;替代 resid_max)",
            "sigma_secondary": "rms sin = frob/sqrt(m)(resid_mean 的严格不变量)",
            "epsilon_j_hand": "j_hand_inv = #{sin θ_i(span(S_curv), ker C) >= 0.05}",
            "thresholds": {"sin_thresh": INV.SIN_THRESH,
                           "basis_drift": INV.DRIFT_TOL,
                           "rot_seeds": list(INV.ROT_SEEDS)}},
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT, payload)

    print("v2m0 selftest v2: 整改版控制矩阵 8 行(不变量判据)")
    print("=" * 74)
    print(f"[env] numpy {env['numpy_version']}  blas={env['blas']}  "
          f"lapack={env['lapack']}  {env['platform']}")

    fz = FZ.verify_frozen()
    payload["frozen_verification"] = fz
    print(f"[cert] frozen sha256 逐位校验: {'PASS' if fz['pass'] else 'FAIL'} "
          f"({len(fz['checked'])} 有记录 + {len(fz['record_only'])} record-only)")
    write_json(OUT, payload)
    if not fz["pass"]:
        payload["status"] = "HALT-frozen-hash-mismatch"
        write_json(OUT, payload)
        return 1

    # ---- 首个自检(硬门):不变量实现须复现复核 §三判决数 -------------------
    calib_inv = SIG.calibration_16cube_invariant()
    payload["judgement_reproduction"] = calib_inv
    ok_rep = calib_inv["reproduces_review_judgement"]
    print("[判决数复现] 16³ 三判据 k 不变量 vs 复核 §三表: "
          + ("PASS" if ok_rep else "FAIL"))
    for kstr, v in calib_inv["per_k"].items():
        print(f"    {kstr}: max sinθ={v['max_sin_theta']:.4f} "
              f"(参照 {v['review_ref']['max_sin_theta']:.4f})  "
              f"frob={v['frob_leak']:.4f} (参照 {v['review_ref']['frob_leak']:.3f})  "
              f"drift={v['basis_robustness']['max_drift']:.1e}")
    write_json(OUT, payload)
    if not ok_rep:
        payload["status"] = "HALT-judgement-reproduction-failed"
        payload["verdict"] = "不变量实现未复现复核判决数:实现有错,先修(纪律)。"
        write_json(OUT, payload)
        return 1

    cands = C.control_candidates()
    rows = {}
    gate_readings = {}
    plan = [
        ("row1_r30", "row1_r30", C.row1_r30),
        ("row2_r23", "row2_r23", C.row2_r23),
        ("row3_null_damped", "row3_null_damped", C.row3_null_damped),
        ("row4_teeth", "row4_teeth", C.row4_teeth),
        ("row5_frozen_walk", "row5_frozen_walk", C.row5_frozen_walk),
        ("row6_tr_sign", "row6_tr_sign", C.row6_tr_sign),
        ("row7_r36", "row7_r36", C.row7_r36),
    ]
    for row_id, cand_key, judge in plan:
        tr = time.time()
        gc = G.evaluate_v2_candidate(cands[cand_key])
        res = judge(gc)
        res["seconds"] = time.time() - tr
        if "basis_robustness_check" not in res:
            res["basis_robustness_check"] = {
                "applicable": False, "reason": ROBUSTNESS_NA[row_id]}
        rows[row_id] = res
        gate_readings[gc.cand_id] = gc.as_dict()
        payload["control_matrix_partial"] = rows
        write_json(OUT, payload)
        brc = res["basis_robustness_check"]
        btxt = (f"drift={brc['max_drift']:.1e}" if "max_drift" in brc
                else "n/a")
        print(f"[{row_id}] {'PASS' if res['pass'] else 'FAIL'}  "
              f"基稳健自检 {btxt}  ({res['seconds']:.1f}s)")

    tr = time.time()
    res8 = C.row8_r37_calib()
    res8["seconds"] = time.time() - tr
    rows["row8_r37_calib"] = res8
    payload["control_matrix"] = rows
    payload.pop("control_matrix_partial", None)
    write_json(OUT, payload)
    print(f"[row8_r37_calib] {'PASS' if res8['pass'] else 'FAIL'}  "
          f"判决数复现 max diff={res8['max_abs_diff']:.2e}  "
          f"基稳健 drift={res8['basis_robustness_check']['max_drift']:.1e}  "
          f"({res8['seconds']:.1f}s)")

    n_pass = sum(1 for r in rows.values() if r["pass"])
    host_all = (n_pass == 8)
    payload["n_pass_host"] = f"{n_pass}/8"
    payload["status"] = ("HOST-PASS-PENDING-SANDBOX" if host_all
                         else "HALT-control-row-failed")
    payload["verdict"] = (
        "整改版控制矩阵宿主 8/8 + 基稳健自检全过(3 种子酉旋转漂移 <=1e-12)。"
        "历史:整改前宿主 8/8 + 跨环境 6/8(行5/行8 失守于基依赖读数);整改后判据"
        "全部不变量化,**收口须双环境 8/8**——沙盒双跑由车道A 复核时执行,本结果"
        "不宣告 M0' 收口。" if host_all else
        "整改版控制矩阵未在宿主 8/8 落位:停手,报车道A(禁调 tol、禁改核)。")

    # ---- dashboard 数据源 v2m0_state.json(整改版 schema v2) ---------------
    fits_inv = rows["row8_r37_calib"]["remeasured"]["fits_invariant"]
    fits_legacy = rows["row8_r37_calib"]["legacy_diagnostics_basis_dependent"][
        "fits_legacy"]
    e5 = rows["row5_frozen_walk"]["remeasured"]
    old_state = {}
    if os.path.exists(STATE):
        try:
            with open(STATE, "r", encoding="utf-8") as fh:
                old_state = json.load(fh)
        except Exception:
            old_state = {}
    state = {
        **STATE_SCHEMA_NOTE,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "experiments/v2m0_selftest_v2.py (M0' 整改版)",
        "backend": "numpy fp64",
        "environment": env,
        "m0_status": {
            "control_matrix_pass": f"{n_pass}/8 (宿主)",
            "host_pass": f"{n_pass}/8",
            "cross_environment": ("整改前:跨环境 6/8(2026-07-26 车道A 沙盒复核,"
                                  "行5/行8 失守于基依赖读数);整改后:待沙盒双跑"),
            "overall": "HOST-PASS-PENDING-SANDBOX" if host_all else "HALT",
            "wording": "宿主 8/8 + 跨环境 6/8 → 整改后须双环境 8/8(整改令 6)"},
        "invariants": {
            "definitions": payload["invariant_definitions"],
            "judgement_reproduction_16cube": {
                k: {"max_sin_theta": v["max_sin_theta"],
                    "frob_leak": v["frob_leak"],
                    "review_ref": v["review_ref"], "ok": v["ok"]}
                for k, v in calib_inv["per_k"].items()},
            "reproduces_review_judgement":
                calib_inv["reproduces_review_judgement"]},
        "control_matrix": [
            {"id": rid, "name": r["name"],
             "gates": {"row1_r30": ["G1", "G8"], "row2_r23": ["G1", "G3", "G8"],
                       "row3_null_damped": ["G1"], "row4_teeth": ["G1"],
                       "row5_frozen_walk": ["G1", "G8"],
                       "row6_tr_sign": ["G4", "G5"],
                       "row7_r36": ["G6", "G7"],
                       "row8_r37_calib": ["G2"]}[rid],
             "status": "green" if r["pass"] else "red",
             "tol": r["tol"], "max_abs_diff": r["max_abs_diff"],
             "basis_robustness_check": r["basis_robustness_check"],
             "cross_environment_status": r.get("cross_environment_status",
                                               "n/a(判据逐位/整数,跨环境已复现)"),
             "remeasured": r["remeasured"], "frozen": r["frozen"],
             "legacy_diagnostics_basis_dependent":
                 r.get("legacy_diagnostics_basis_dependent"),
             "seconds": r.get("seconds")}
            for rid, r in rows.items()],
        "epsilon_sigma_anchors": [
            {"id": "scalar_campaign_44h", "sector": "spin0",
             "swimlane": "spin0", "epsilon_dof": None, "epsilon_E": None,
             "sigma": {"note": "v1 封册事实(54M 规则, endured lawful 4.04%);"
                               "M0' 不重测,泳道留位"},
             "source": "v1 总账 44h(F 类封册)"},
            {"id": "R23_maxwell", "sector": "spin1", "swimlane": "spin1",
             "epsilon_dof": 1.0, "epsilon_E": 1.0,
             "sigma": {"note": "Lorenz 闭合机器零(constraint_decay ~5e-16);"
                               "A=0 边界线上的 eps=1 端锚点"},
             "source": "r23_results.json(控制行 2 重测;冻结 JSON 沙盒系谱系)"},
            {"id": "R30_complex", "sector": "spin2", "swimlane": "spin2",
             "epsilon_dof": 0.0, "epsilon_E": 0.0,
             "sigma": {"note": "de Donder darkness ≤1.4e-14(精确约束);"
                               "A=0 边界线上的 eps=0 端锚点"},
             "source": "r30_results.json(控制行 1 重测)"},
            {"id": "frozen_walk_family", "sector": "spin2", "swimlane": "spin2",
             "epsilon_dof_range": e5["epsilon_dof_min_max_invariant"],
             "epsilon_dof_range_legacy": [0.0, 0.25],
             "epsilon_caliber": ("不变量 j_hand(整改令 2);旧口径(基依赖贪心,"
                                 "宿主 [0,0.25]/沙盒 [0,0.5] 漂移)废止为注记"),
             "epsilon_E_range": gate_readings["ctrl_frozen_walk"]["gates"]
                 ["G8_epsilon"]["raw"]["epsilon_E_min_max"],
             "sigma": {"by_direction": fits_inv,
                       "by_direction_legacy": fits_legacy,
                       "caliber_note": ("by_direction = 不变量口径 y=max sinθ"
                                        "(判据);by_direction_legacy = 旧口径 "
                                        "resid_max(基依赖,仅注记)")},
             "source": "rc3ii/r32/r37 冻结件(控制行 5/8 不变量重测)"},
        ],
        "gate_readings": gate_readings,
        "sigma_calibration_64": (old_state.get("sigma_calibration_64")
                                 if isinstance(old_state.get(
                                     "sigma_calibration_64"), dict)
                                 else {"status": "PENDING"}),
        "hashes": fz,
    }
    # 旧口径校准摘要如存在,标注为旧口径待整改版覆盖
    if state["sigma_calibration_64"].get("status") == "DONE" and \
            "direction_fits_invariant" not in state["sigma_calibration_64"]:
        state["sigma_calibration_64"]["caliber_warning"] = (
            "此块为旧口径(resid_max,基依赖)校准摘要;整改版 "
            "v2m0_sigma_calibration_v2.py 完成后将并入不变量口径并保留此块为注记")
    write_json(STATE, state)
    payload["state_json"] = os.path.relpath(STATE, ROOT)

    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(OUT, payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(OUT, payload)

    print("=" * 74)
    print(f"CONTROL MATRIX (整改版, 宿主): {n_pass}/8  ->  {payload['status']}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"state json -> {payload['state_json']}")
    print(f"total {time.time()-t0:.1f}s")
    return 0 if host_all else 1


if __name__ == "__main__":
    sys.exit(main())
