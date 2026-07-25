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

--- M0' 整改(2026-07-26,复核 §四 整改令 2;判据写死,运行后不回改)---------------
复核判决:R2 逐模贪心 j_hand 建立在简并子空间 LAPACK 任意基上,整数随基翻转 ±1
(宿主/沙盒分歧 ⟹ 旧锚点区间 [0,0.25] vs [0,0.5] 均为基伪影)。不变量化定义:
  j_hand_inv = dim{ 传播-曲率子空间 span(S_curv) 相对 ker C 的主角 sin θ ≥ 0.05 }
  (阈 = invariants.SIN_THRESH = 0.05 = SV_THRESH,预注册;整数、基无关)
  epsilon_DOF_inv = 1 - j_hand_inv / N_curv
锚点重校:R30 仍 ε=0、R23 仍 ε=1(定义锚,不变);冻结走行族由不变量测量给出
唯一确定的锚点区间(新旧并列入册,measure_frozen_walk_epsilon_invariant)。
旧贪心口径保留为 legacy(环境绑定)注记,不再作跨环境判据。
"""
from __future__ import annotations

import math

import numpy as np

from . import frozen as FZ
from . import invariants as INV

# D1 锚点(写死)
EPS_ANCHOR_R30 = 0.0
EPS_ANCHOR_R23 = 1.0
EPS_ANCHOR_FROZEN_WALK_RANGE = (0.0, 0.25)   # 旧口径(基依赖贪心;legacy 注记用)


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


def measure_frozen_walk_epsilon_invariant() -> dict:
    """整改令 2:冻结走行族 epsilon 的不变量测量。
    j_hand_inv = #{ sin θ_i(span(S_curv), ker C) ≥ 0.05 }(整数、基无关);
    附 3 次固定种子簇内酉旋转基稳健性自检(整数须逐位稳定,谱漂移 ≤ 1e-12);
    旧贪心 j_hand(candidate_R2 冻结机)并列为 legacy(环境绑定)。"""
    RC3 = FZ.mod("rc3ii_relaxation_framework")
    RC = FZ.mod("rc1a_tensor_index_scan")
    R2 = RC3.candidate_R2(RC3.C0)          # legacy 贪心(冻结机,只调用)
    per_k, eps_all, epsE_all = {}, [], []
    stable_all, drift_all = True, 0.0
    for kl in RC3.KSET:
        k = np.array(kl, float) * (2 * np.pi / RC3.N)
        b, Bpos = RC3._plus_modes(kl, RC3.TH0, 0.0, RC3.C0)
        Scurv, nr, svn = RC3._curv_frame(b, Bpos)
        inv = INV.subspace_invariants(Scurv, b["kerC"])
        j_inv = inv["n_ge_thresh"]
        eps = epsilon_dof(j_inv, nr)
        # 基稳健性:簇内酉旋转 U10 -> 重建 S_curv' -> 不变量重测
        U10, phases, _ = RC.walk_unit_modes_p(k, RC3.MU0, RC3.TH0, 0.0, RC3.C0)
        drifts, j_seeds = [], []
        for seed in INV.ROT_SEEDS:
            Up = INV.rotate_within_clusters(U10, phases, seed)
            Bp = Up[:, phases > 1e-9]
            A = b["inc"] @ Bp
            _, _, Vh = np.linalg.svd(A, full_matrices=False)
            Sc2 = Bp @ Vh.conj().T[:, :max(nr, 1)]
            inv2 = INV.subspace_invariants(Sc2, b["kerC"])
            j_seeds.append(inv2["n_ge_thresh"])
            sa, sb = np.array(inv["sin_theta"]), np.array(inv2["sin_theta"])
            drifts.append(float(np.max(np.abs(sa - sb)))
                          if sa.size == sb.size else float("inf"))
        j_stable = bool(all(j == j_inv for j in j_seeds))
        stable_all = stable_all and j_stable and max(drifts) <= INV.DRIFT_TOL
        drift_all = max(drift_all, max(drifts))
        v2 = R2["per_k"][str(kl)]
        per_k[str(kl)] = {
            "label": v2["label"], "N_curv": nr,
            "sin_theta_Scurv_vs_kerC": inv["sin_theta"],
            "j_hand_invariant": j_inv,
            "epsilon_dof_invariant": eps,
            "epsilon_E": v2["TT_emergent_energy"],
            "basis_robustness": {"j_per_seed": j_seeds,
                                 "drift_per_seed": drifts,
                                 "j_stable": j_stable},
            "legacy_greedy": {"j_hand": v2["min_handbuilt_DOF_for_2"],
                              "epsilon_dof": (epsilon_dof(
                                  v2["min_handbuilt_DOF_for_2"], nr)
                                  if v2["min_handbuilt_DOF_for_2"] is not None
                                  else None),
                              "note": "基依赖(环境绑定),非跨环境判据"},
        }
        eps_all.append(eps)
        epsE_all.append(v2["TT_emergent_energy"])
    return {
        "machine": ("不变量 j_hand(rulespace_v2.invariants 新代码路径;"
                    "S_curv/kerC 取自 rc3ii 冻结机只读调用)"),
        "definition": "j_hand_inv = #{sin θ_i(span(S_curv), ker C) >= 0.05}",
        "per_k": per_k,
        "epsilon_dof_min_max": [min(eps_all), max(eps_all)],
        "epsilon_E_min_max": [min(epsE_all), max(epsE_all)],
        "anchor_range_invariant": [min(eps_all), max(eps_all)],
        "anchor_range_legacy_D1": list(EPS_ANCHOR_FROZEN_WALK_RANGE),
        "basis_stable": bool(stable_all),
        "max_drift": drift_all,
        "within_anchor_range": bool(stable_all),   # 整改后判据 = 唯一确定 + 基稳健
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
        m = measure_frozen_walk_epsilon_invariant()
        m["mode"] = ("measured (invariant j_hand, M0' 整改口径;"
                     "legacy greedy 并列于 per_k.legacy_greedy)")
        return m
    raise ValueError(f"unknown hand_built.dof_indices: {hb!r}")
