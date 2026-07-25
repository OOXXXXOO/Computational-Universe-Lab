"""v2m0_selftest -- M0' 仪器迁移控制矩阵一键自检(交付物 3;lane B,2026-07-26)。

AUTHORITY: docsv2/v2-任务书-M0-仪器迁移.md §4(控制矩阵 8 行,判据与 tol 预注册写死,
运行后不得回改)。每行 = rulespace_v2.evaluate_v2_candidate 对该控制对象的**重测**,
与冻结 JSON 已知答案比对(红线 5:v1 证书不得直接填 v2 门列)。

控制矩阵(判据/tol 与 rulespace_v2/controls.py 模块头一致,写死):
  1 R30 复形        N_prop=2 断崖 + eps_DOF=0        G1 svn vs r30_results     tol 1e-12
  2 R23 Yee/Maxwell 光子 2 + Lorenz 闭合 + eps_DOF=1  G1/G3 vs r23_results      tol 1e-12
  3 null_damped     N_prop=2, sv 断崖 ~1e4            G1 vs r28_results PC3     tol 1e-10
  4 teeth 裸波      N_prop=6                          G1 vs 卡点⑦ 结果          精确
  5 冻结走行族      [4,4,5,5] + 泄漏 34-49% + eps∈[0,0.25]  G1/G8 vs r32/rc3ii/r36  tol 1e-13(walk 因子逐位)
  6 tr_sign=0 炮    Newton/偏折按 v1 记录击穿          G4/G5                     判 FAIL
  7 R36 (a) 清除件  tau∈[39,62], 1.59x, AC≤2.3e-15    G6/G7 vs r36_results      tol 1e-12
  8 R37 16^3 校准   三判据 k resid diff=0.0            G2 vs rc3ii_results       0.0 逐位

M0' PASS = 8/8 全落位;任一不落位 => 状态 HALT-追因(禁调 tol、禁改核),报车道A。

输出:
  data/results/v2m0_selftest.json     (增量写盘)
  data/runtime/v2m0_state.json        (dashboard v2 数据源首版;schema 见文件内注释)

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m0_selftest.py
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

OUT = os.path.join(ROOT, "data", "results", "v2m0_selftest.json")
STATE = os.path.join(ROOT, "data", "runtime", "v2m0_state.json")


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


# --------------------------------------------------------------------------
#  state schema(dashboard v2 数据源;第二波 dashboard agent 按此建面板)
# --------------------------------------------------------------------------
STATE_SCHEMA_NOTE = {
    "_schema": "v2m0_state v1 (2026-07-26, lane B)",
    "_doc": {
        "purpose": ("dashboard v2 唯一数据源(任务书 §6;禁止读取旧 tensor "
                    "campaign payload)。面板:(epsilon,sigma) 平面散点 + 三自旋"
                    "测线泳道 + 控制矩阵绿/红牌 + G 列读数表。"),
        "m0_status": "M0' 总状态:control_matrix_pass 'k/8';overall PASS|HALT。",
        "control_matrix[]": ("8 行,每行 {id, name, gates, status: green|red, "
                             "tol, max_abs_diff, remeasured, frozen(含 source), "
                             "seconds}。remeasured=新评估器重测值;frozen=冻结 "
                             "JSON 已知答案;status=green 即该行落位。"),
        "epsilon_sigma_anchors[]": ("(epsilon,sigma) 平面锚点。每项 {id, sector, "
                                    "swimlane(spin0|spin1|spin2), epsilon_dof 或 "
                                    "epsilon_dof_range, epsilon_E, sigma:{"
                                    "by_direction:{A,sigma_A,alpha,dAIC,verdict,"
                                    "band_D3} 或 note}, source}。epsilon 轴取值 "
                                    "[0,1];sigma 轴建议画 (alpha, A) 双坐标或以 "
                                    "A 为半径的标记。spin0 泳道锚点属 v1 封册事实"
                                    "(标量战役),M0' 不重测,泳道留位。"),
        "gate_readings": ("candidate_id -> GateColumns.as_dict();每门 {raw, "
                          "per_L, limit_fit, verdict, diagnostics}。verdict="
                          "CONTROL 表示固定尺度对答案行,非物理判定。"),
        "sigma_calibration_64": "交付物 4(独立脚本/并行 agent)填;此处占位。",
        "hashes": "冻结件 sha256 校验册(checked=有先行记录并逐位比对)。",
    },
}


def main():
    t0 = time.time()
    payload = {
        "register": "v2m0-selftest (M0' 仪器迁移控制矩阵 8 行)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": "docsv2/v2-任务书-M0-仪器迁移.md §4",
        "tol_table": {k: (v if v is not None else "judged-FAIL")
                      for k, v in C.TOL.items()},
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT, payload)

    print("v2m0 selftest: control matrix 8 rows (evaluate_v2_candidate 重测)")
    print("=" * 74)

    # 冻结件校验册(红线 1)
    fz = FZ.verify_frozen()
    payload["frozen_verification"] = fz
    print(f"[cert] frozen sha256 逐位校验: {'PASS' if fz['pass'] else 'FAIL'} "
          f"({len(fz['checked'])} 有记录 + {len(fz['record_only'])} record-only)")
    write_json(OUT, payload)
    if not fz["pass"]:
        payload["status"] = "HALT-frozen-hash-mismatch"
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
        rows[row_id] = res
        gate_readings[gc.cand_id] = gc.as_dict()
        payload["control_matrix_partial"] = rows
        write_json(OUT, payload)
        print(f"[{row_id}] {'PASS' if res['pass'] else 'FAIL'}  "
              f"max_abs_diff={res['max_abs_diff']}  tol={res['tol']}  "
              f"({res['seconds']:.1f}s)")

    tr = time.time()
    res8 = C.row8_r37_calib()
    res8["seconds"] = time.time() - tr
    rows["row8_r37_calib"] = res8
    payload["control_matrix"] = rows
    payload.pop("control_matrix_partial", None)
    write_json(OUT, payload)
    print(f"[row8_r37_calib] {'PASS' if res8['pass'] else 'FAIL'}  "
          f"max_abs_diff={res8['max_abs_diff']}  (逐位)  ({res8['seconds']:.1f}s)")

    n_pass = sum(1 for r in rows.values() if r["pass"])
    all_pass = (n_pass == 8)
    payload["n_pass"] = f"{n_pass}/8"
    payload["status"] = "PASS-8of8" if all_pass else "HALT-control-row-failed"
    payload["verdict"] = (
        "同一个 evaluate_v2_candidate:喂 R30 得 (eps=0, N_prop=2),喂 R23 得 "
        "(eps=1, 光子 2),喂冻结走行族得 [4,4,5,5] 与 34-49% 泄漏,喂炮组得击穿"
        "——八发八中,tol 内逐位。" if all_pass else
        "控制矩阵未 8/8 落位:停手,写追因小报告(禁调 tol、禁改核),报车道A。")

    # -- dashboard 数据源 v2m0_state.json ------------------------------------
    fits = rows["row8_r37_calib"]["remeasured"]["fits"]
    eps5 = rows["row5_frozen_walk"]["remeasured"]["epsilon_dof_min_max"]
    state = {
        **STATE_SCHEMA_NOTE,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "experiments/v2m0_selftest.py",
        "backend": "numpy fp64",
        "m0_status": {"control_matrix_pass": f"{n_pass}/8",
                      "overall": "PASS" if all_pass else "HALT"},
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
             "remeasured": r["remeasured"], "frozen": r["frozen"],
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
             "source": "r23_results.json(控制行 2 重测)"},
            {"id": "R30_complex", "sector": "spin2", "swimlane": "spin2",
             "epsilon_dof": 0.0, "epsilon_E": 0.0,
             "sigma": {"note": "de Donder darkness ≤1.4e-14(精确约束);"
                               "A=0 边界线上的 eps=0 端锚点"},
             "source": "r30_results.json(控制行 1 重测)"},
            {"id": "frozen_walk_family", "sector": "spin2", "swimlane": "spin2",
             "epsilon_dof_range": eps5,
             "epsilon_E_range": gate_readings["ctrl_frozen_walk"]["gates"]
                 ["G8_epsilon"]["diagnostics"]["epsilon_E_min_max"],
             "sigma": {"by_direction": fits},
             "source": "rc3ii/r32/r37 冻结件(控制行 5/8 重测)"},
        ],
        "gate_readings": gate_readings,
        "sigma_calibration_64": {"status": "PENDING",
                                 "note": "交付物 4(v2m0_sigma_calibration.py,"
                                         "并行 agent)完成后填入"},
        "hashes": fz,
    }
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
    print(f"CONTROL MATRIX: {n_pass}/8  ->  {payload['status']}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"state json -> {payload['state_json']}")
    print(f"total {time.time()-t0:.1f}s")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
