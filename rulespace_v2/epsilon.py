"""rulespace_v2.epsilon -- G8 涌现度 epsilon 机器(D1 裁定口径,判据核不重写)。

D1(docsv2/v2-裁定-D1D5-2026-07-26.md):
  主判 epsilon_DOF = 1 - j_hand / N_curv
    j_hand : 达到目标 N_prop 所需手搭进精确 ker C 的传播-曲率 DOF 数
             -- 来源 = RC3-(ii) R2 冻结手搭计数机(rc3ii_relaxation_framework.candidate_R2,
             只调用,不重写);
    N_curv : 该扇区传播-曲率 DOF 总数(同机器的 N_prop_raw)。
  辅报 epsilon_E(能量加权:未手搭扇区在传播带内的曲率能量占比)-- 仅诊断入册,
    不参与判定。frozen_walk 的实现 = R2 机器的 TT_emergent_energy(S_curv 各列在
    TT 扇区的平均能量占比,即无须手搭的曲率能量);锚点候选取定义值。

锚点校准(D1 写死,不许调):
  R30 复形      epsilon_DOF = 0    (hand_built = all:全部传播-曲率 DOF 手搭)
  R23 Maxwell   epsilon_DOF = 1    (hand_built = None:零手搭)
  冻结走行族    epsilon_DOF ∈ [0, 0.25](判据 k 处;R2 实测 j_hand=3-4, N_curv=4)
"""
from __future__ import annotations

import math

from . import frozen as FZ

# D1 锚点(写死)
EPS_ANCHOR_R30 = 0.0
EPS_ANCHOR_R23 = 1.0
EPS_ANCHOR_FROZEN_WALK_RANGE = (0.0, 0.25)


def epsilon_dof(j_hand: int, n_curv: int) -> float:
    """主判 epsilon_DOF = 1 - j_hand/N_curv(D1)。"""
    if n_curv <= 0:
        raise ValueError("N_curv must be positive")
    return 1.0 - float(j_hand) / float(n_curv)


def measure_frozen_walk_epsilon() -> dict:
    """冻结走行族 epsilon:调用 RC3-(ii) R2 冻结手搭计数机(核不重写)。
    返回逐 k 的 j_hand / N_curv / epsilon_DOF(主判)与 epsilon_E(辅报)。"""
    RC3 = FZ.mod("rc3ii_relaxation_framework")
    R2 = RC3.candidate_R2(RC3.C0)
    per_k = {}
    eps_all, epsE_all = [], []
    for kstr, v in R2["per_k"].items():
        j = v["min_handbuilt_DOF_for_2"]
        n = v["N_prop_raw"]
        eps = epsilon_dof(j, n) if j is not None else float("nan")
        epsE = v["TT_emergent_energy"]
        per_k[kstr] = {"label": v["label"], "j_hand": j, "N_curv": n,
                       "epsilon_dof": eps, "epsilon_E": epsE,
                       "reaches_2": v["reaches_2"]}
        if j is not None:
            eps_all.append(eps)
        epsE_all.append(epsE)
    return {
        "machine": "rc3ii_relaxation_framework.candidate_R2 (冻结 I 类,只调用)",
        "per_k": per_k,
        "epsilon_dof_min_max": [min(eps_all), max(eps_all)] if eps_all else None,
        "epsilon_E_min_max": [min(epsE_all), max(epsE_all)] if epsE_all else None,
        "anchor_range_D1": list(EPS_ANCHOR_FROZEN_WALK_RANGE),
        "within_anchor_range": bool(
            eps_all and EPS_ANCHOR_FROZEN_WALK_RANGE[0] - 1e-12 <= min(eps_all)
            and max(eps_all) <= EPS_ANCHOR_FROZEN_WALK_RANGE[1] + 1e-12),
    }


def epsilon_for_candidate(cand) -> dict:
    """按 CandidateV2.hand_built 约定给出 epsilon 读数(见 candidate.py 模块头)。"""
    hb = (cand.hand_built or {}).get("dof_indices", None)
    if hb == "all":
        return {"mode": "anchor-definition (hand_built=all)",
                "epsilon_dof": EPS_ANCHOR_R30, "epsilon_E": 0.0,
                "note": "全部传播-曲率 DOF 手搭(R30 类)=> epsilon_DOF=0,D1 写死"}
    if hb is None:
        return {"mode": "anchor-definition (hand_built=None)",
                "epsilon_dof": EPS_ANCHOR_R23, "epsilon_E": 1.0,
                "note": "零手搭(R23 类)=> epsilon_DOF=1,D1 写死"}
    if hb == "measure_rc3ii_R2":
        m = measure_frozen_walk_epsilon()
        m["mode"] = "measured (RC3-(ii) R2 frozen counter)"
        return m
    raise ValueError(f"unknown hand_built.dof_indices: {hb!r}")
