"""r25_family_eval -- R25 参数族统一评估器(阶段B恢复研究仪器,件②)。

【定位】阶段复盘-2026-07-24 §4.3/§七阶段B 规定的三件接口之一:
    evaluate_r25_candidate(params) -> gate columns
把 R25 已通过的符号证书链(r25_laurent / r25_walk_dedonder / r25_detour /
r25_uv_exceptional_audit / r25_auxiliary_wilson / r25_static_newton /
r25_dynamic_symbol)封装成一个参数化候选族上的统一列输出。任何候选只有
同时具备符号证书、实空间 evaluator、可视化 schema,才允许从 R 升 M。

【措辞纪律】(复盘 §五)R25 = 约束合成/存在性构造。本评估器输出的
symbol_green 只代表"符号层证书列全绿",不是 M3,更不是"涌现";
"涌现"表述必须等 M4(含非 GR 候选的族中存活等价类非空、非孤点)。

【参数族】(预注册草案-R25-参数族.md,草案待评审拍板)
  连续先验列 R25_PARAM_NAMES = ["alpha_W", "sel_gain", "sel_trace", "mu_damp"]:
    alpha_W  : Wilson 权重 r(k)=alpha_W*q(k)(基点 0.5;alpha_W=0 是族内
               非 GR 方向 -> UV 第二节点不提升,uv_audit 列应红)
    sel_gain : auxiliary selector h0i 耦合系数(基点 0.75;偏移 -> Newton
               lift 失暗,static_newton 列应红 -> 非 GR 静态响应方向)
    sel_trace: selector 迹行系数(基点 3.0;同上,static_newton 列的牙)
    mu_damp  : 直接收缩阻尼强度(基点 1.995e-3 = r25_dynamic_symbol 选点;
               占位待卡点②预条件化胜者拍板;过大 -> contraction_rate 列红)
  离散开关(炮/附检,不进先验;kwargs):
    wilson_form     ∈ {"q","q2"}         : Wilson 标量形状(附检)
    selector_family ∈ {"cubic","none"}   : 炮:无消除 syzygy -> 商维 6 ≠ 2
    pairing         ∈ {"conjugate","single"} : 炮:单手征扇区 -> 复度规
    axis_order      ∈ {"xyz","zyx",...}  : 炮/附检:几何走子轴序(物质冻结 xyz)
    damp_order      ∈ {"contract_then_free","free_then_contract"} : 炮:
                      反序 F-μQ 注能(r25_dynamic_symbol 登记的负控)

【列】符号层(现在可算,全部有 r25 证书脚本背书):
    shell_J5 / cohomology / uv_audit / static_newton / contraction_rate /
    reality_pairing
  实空间层(留槽,PENDING 卡点①,接口签名已定死,见 REALSPACE_INTERFACE):
    dof_dynamic / constraint_floor_rate / moving_source / newton_dynamic /
    eddington / conservation / sponge_endurance / cannons_replay

【schema】统一证据 schema 第一版(复盘 §4.3 run_r25/state.json 的约定)
  由 write_schema() 写到 data/runtime/r25_eval_schema.json;dashboard_r25
  轮询 data/runtime/run_r25/state.json(缺文件显示"待实空间列")。

【纪律】不发令、不长跑;自测分钟级;fp64(numpy 后端);不修改任何现有
科学脚本(全部只 import,provenance sha256 入册)。

自测:RULESPACE_BACKEND=numpy .venv/bin/python r25_family_eval.py
      (基点符号列全绿;六个族内非 GR/炮方向各在预期列上红;
       写 data/results/r25_family_eval_selftest.json 与
       data/runtime/r25_eval_schema.json)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
import warnings

import numpy as np

# 与 r25_dynamic_symbol 相同:macOS Accelerate 的 matmul 边界告警,非病灶
warnings.filterwarnings("ignore", message=".*encountered in matmul")

import cp1_v4_L2 as L2
import r25_auxiliary_wilson_complex as R25W
import r25_detour_complex as R25D
import r25_walk_dedonder_complex as R25B1
from rulespace_gpu import tensor_coin_feedback as tcf

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
OUT_SELFTEST = os.path.join(ROOT, "data", "results",
                            "r25_family_eval_selftest.json")
OUT_SCHEMA = os.path.join(ROOT, "data", "runtime", "r25_eval_schema.json")
STATE_JSON_CONVENTION = "data/runtime/run_r25/state.json"

C = L2.C                      # 冻结锥速 1/2
TH = L2.TH                    # 冻结 theta = pi/3
ETA = R25D.ETA
I4 = np.eye(4, dtype=complex)
PAULI = [np.array(s.tolist(), complex) for s in R25B1.SIGMA]
NFIELD = 14                   # 10 物理 + 4 auxiliary
KUV = np.array([-1.714143895700328, 0.0, -1.714143895700328])  # 冻结物质 UV 节点
GATE_NVECS = ((2, 0, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0), (2, 2, 2), (1, 1, 1))
GATE_N = 32

SCHEMA_VERSION = "r25_eval/v1"
CLAIM_DISCIPLINE = ("R25 = 约束合成/存在性构造;symbol_green ≠ M3;"
                    "'涌现'表述须待 M4(含非 GR 候选的族去孤岛)")

R25_PARAM_NAMES = ["alpha_W", "sel_gain", "sel_trace", "mu_damp"]
BASE_POINT = {"alpha_W": 0.5, "sel_gain": 0.75, "sel_trace": 3.0,
              "mu_damp": 1.995262314968879e-3}
BASE_SWITCHES = {"wilson_form": "q", "selector_family": "cubic",
                 "pairing": "conjugate", "axis_order": "xyz",
                 "damp_order": "contract_then_free"}

SYMBOL_COLUMNS = ["shell_J5", "cohomology", "uv_audit", "static_newton",
                  "contraction_rate", "reality_pairing"]
REALSPACE_COLUMNS = ["dof_dynamic", "constraint_floor_rate", "moving_source",
                     "newton_dynamic", "eddington", "conservation",
                     "sponge_endurance", "cannons_replay"]

# 实空间列接口(卡点①所有者对接;签名现在定死,内容 pending)
REALSPACE_INTERFACE = {
    "entry": "evaluate_r25_candidate(params, ..., realspace_hook=hook)",
    "hook_signature": ("hook(candidate_spec: dict) -> dict,键 ⊆ "
                       "REALSPACE_COLUMNS,值 = {'status': 'PASS'|'FAIL', "
                       "...数值字段}"),
    "candidate_spec": "{'params': {...}, 'switches': {...}}(本评估器传入)",
    "provider": ("r25_realspace_step / r25_precond / r25_moving_source"
                 "(卡点①/②所有者,另 agent;本文件不实现、不修改)"),
    "state_json": STATE_JSON_CONVENTION,
    "note": ("hook 缺省时全部实空间列 status='PENDING',阻塞 m3_ready;"
             "m3_ready 只有当符号列+实空间列全部 PASS 才为 True"),
}


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def provenance():
    """上游证书脚本 sha256(只读入册,不修改)。"""
    names = ["r25_laurent_complex.py", "r25_walk_dedonder_complex.py",
             "r25_detour_complex.py", "r25_uv_exceptional_audit.py",
             "r25_auxiliary_wilson_complex.py", "r25_static_newton.py",
             "r25_dynamic_symbol.py", "cp1_v4_L2.py"]
    return {n: _sha256(os.path.join(DIR, n)) for n in names}


# =========================================================== 参数化符号构件
def walk_symbol_order(kl, axis_order="xyz", th=TH):
    """L2.walk_symbol 的轴序参数化版(xyz 下与冻结实现逐位一致,自测断言)。"""
    Wx, Wy, Wz = tcf.axis_frames(th)
    Wd = {"x": Wx, "y": Wy, "z": Wz}
    kd = {"x": kl[0], "y": kl[1], "z": kl[2]}
    U = np.eye(2, dtype=complex)
    for a in axis_order:
        kc, Wm = kd[a], Wd[a]
        D1 = np.diag([np.exp(-1j * kc), 1.0])
        D2 = np.diag([1.0, np.exp(1j * kc)])
        U = (Wm.conj().T @ D2 @ tcf._coin_mat(-th) @ D1
             @ tcf._coin_mat(th) @ Wm) @ U
    return U


def q_spatial(k):
    return sum(math.sin(float(x) / 2) ** 2 for x in k) / 3.0


def wilson_r(k, alpha, form="q"):
    q = q_spatial(k)
    return alpha * (q * q if form == "q2" else q)


def selector_H(U, gain, trace):
    """auxiliary selector(基点 gain=0.75, trace=3.0 恰使 Newton lift 全暗;
    偏移即族内非 GR 方向 -> static_newton 列红)。"""
    a = np.trace(U) / 2
    b = np.array([1j * np.trace(s @ U) / 2 for s in PAULI])
    H = np.zeros((4, 10), complex)
    for row, (i, j, hij, h0i, h0j) in enumerate(
            ((0, 1, 5, 1, 2), (0, 2, 6, 1, 3), (1, 2, 8, 2, 3))):
        H[row, hij] = 1 + a
        H[row, h0i] = 1j * gain * b[j]
        H[row, h0j] = 1j * gain * b[i]
    H[3, 0] = -trace
    H[3, [4, 7, 9]] = 1
    return H


def base_kappa(U, z):
    a = np.trace(U) / 2
    b = np.array([1j * np.trace(s @ U) / 2 for s in PAULI])
    return np.concatenate([[z - a], 1j * b]) / C


def candidate_data(k, p, sw):
    """一点 k 上的 (U_geom, tr, r, a_W)。物质走子恒冻结 xyz;几何走子
    的轴序是开关(基点 = 同一走子)。"""
    U = walk_symbol_order(np.asarray(k, float), sw["axis_order"])
    tr = float(np.real(np.trace(U)))
    r = wilson_r(k, p["alpha_W"], sw["wilson_form"])
    return U, tr, r, 2.0 - tr + r * r


def geometry_root(k, branch, p, sw):
    _, tr, r, aw = candidate_data(k, p, sw)
    arg = np.clip((tr - r * r) / 2, -1.0, 1.0)
    omega = math.acos(arg)
    return np.exp(-1j * branch * omega), omega, aw


def augmented_maps_at_z(k, z, p, sw):
    """(G+, K+, Pw):参数化的 mapping cone(r25_auxiliary_wilson 的族版)。
    selector_family='none' 时 K+ 只有 C+ 四行(无消除 syzygy 的炮)。"""
    U, _, r, _ = candidate_data(k, p, sw)
    kap = base_kappa(U, z)
    G = R25D.gauge_matrix(kap)
    Cm = R25D.dedonder_matrix(kap)
    s = r / C
    Gp = np.vstack([G, s * I4])
    Cp = np.hstack([Cm, -z * s * I4])
    if sw["selector_family"] == "none":
        Kp = Cp
    else:
        H = selector_H(U, p["sel_gain"], p["sel_trace"])
        Dp = np.hstack([s * H, -H @ G])
        Kp = np.vstack([Cp, Dp])
    P0 = z * z - np.trace(U) * z + 1
    return Gp, Kp, Cp, P0 + z * r * r


def _rank(A, tol=1e-9):
    s = np.linalg.svd(A, compute_uv=False)
    return int(np.sum(s > tol * max(float(s[0]), 1.0))) if s.size else 0


# ================================================================== 各符号列
def col_shell_j5(p, sw):
    """壳/J5 列:几何根(Wilson 变形壳)对冻结物质走子频率,门 k 集。"""
    rows, worst = [], 0.0
    for nv in GATE_NVECS:
        k = 2 * np.pi * np.array(nv, float) / GATE_N
        Um = L2.walk_symbol(k)                       # 物质参考:冻结 xyz
        wm = math.acos(np.clip(float(np.real(np.trace(Um))) / 2, -1, 1))
        _, wg, _ = geometry_root(k, 1, p, sw)
        dev = abs(wg / wm - 1) if wm > 1e-12 else 0.0
        worst = max(worst, dev)
        rows.append({"index": list(nv), "omega_matter": wm,
                     "omega_geometry": wg, "relative_J5": dev})
    return {"layer": "symbol", "status": "PASS" if worst < 1e-2 else "FAIL",
            "max_relative_J5": worst, "threshold": 1e-2, "gate_rows": rows,
            "certificate": "r25_auxiliary_wilson_results.json/formal_gate"}


def col_cohomology(p, sw, n_shell, rng):
    """同调列:一般壳点 rank(G+,K+) 与商维;mapping cone 恒等残差。"""
    kset = [2 * np.pi * np.array(nv, float) / GATE_N for nv in GATE_NVECS]
    kset += [rng.uniform(-math.pi, math.pi, 3) for _ in range(n_shell)]
    ranks_g, ranks_k, cohs = set(), set(), set()
    worst = {"KG": 0.0, "CG_plus_PwI": 0.0, "Pw_on_shell": 0.0}
    s8_min = float("inf")
    for branch in (-1, 1):
        for k in kset:
            z, _, _ = geometry_root(k, branch, p, sw)
            Gp, Kp, Cp, Pw = augmented_maps_at_z(k, z, p, sw)
            rg, rk = _rank(Gp), _rank(Kp)
            ranks_g.add(rg)
            ranks_k.add(rk)
            cohs.add(NFIELD - rk - rg)
            worst["KG"] = max(worst["KG"], float(np.max(np.abs(Kp @ Gp))))
            worst["CG_plus_PwI"] = max(worst["CG_plus_PwI"], float(
                np.max(np.abs(Cp @ Gp + Pw * I4 / C ** 2))))
            worst["Pw_on_shell"] = max(worst["Pw_on_shell"], float(abs(Pw)))
            sk = np.linalg.svd(Kp, compute_uv=False)
            if sk.size >= 8:
                s8_min = min(s8_min, float(sk[7]))
    ok = (ranks_g == {4} and ranks_k == {8} and cohs == {2}
          and max(worst.values()) < 1e-11)
    return {"layer": "symbol", "status": "PASS" if ok else "FAIL",
            "points_per_branch": len(kset), "rank_G_plus": sorted(ranks_g),
            "rank_K_plus": sorted(ranks_k), "quotient_dim": sorted(cohs),
            "expected": {"rank_G_plus": 4, "rank_K_plus": 8,
                         "quotient_dim": 2},
            "worst_identity_residuals": worst,
            "smallest_eighth_singular_value_K":
                None if s8_min == float("inf") else s8_min,
            "certificate": "r25_auxiliary_wilson_results.json/on_shell_census"}


def col_uv_audit(p, sw):
    """UV exceptional 列:冻结物质 +I 节点必须被 Wilson mapping cone 提升
    (rank(G,K)=(4,8)、商维 2);alpha_W=0 时秩崩塌 -> 红。"""
    rows = []
    ok = True
    for branch in (-1, 1):
        z, omega, aw = geometry_root(KUV, branch, p, sw)
        Gp, Kp, _, Pw = augmented_maps_at_z(KUV, z, p, sw)
        rg, rk = _rank(Gp), _rank(Kp)
        coh = NFIELD - rk - rg
        rows.append({"branch": branch, "omega_geometry": omega,
                     "r": wilson_r(KUV, p["alpha_W"], sw["wilson_form"]),
                     "a_W": aw, "Pw_abs": float(abs(Pw)),
                     "rank_G": rg, "rank_K": rk, "cohomology": coh})
        ok = ok and rg == 4 and rk == 8 and coh == 2 and abs(Pw) < 1e-9
    return {"layer": "symbol", "status": "PASS" if ok else "FAIL",
            "node_k": KUV.tolist(), "rows": rows,
            "expected": {"rank_G": 4, "rank_K": 8, "cohomology": 2},
            "certificate": ("r25_uv_exceptional_results.json + "
                            "r25_auxiliary_wilson_results.json/old_UV_node")}


def col_static_newton(p, sw, n_dark, bz_N, rng):
    """静态 Newton 符号列:全 BZ 0<a_W<4;Newton lift 对全部约束行全暗;
    冻结 canary 比 h00/hbar00 = 2。"""
    amin, amax = float("inf"), 0.0
    for idx in np.ndindex(bz_N, bz_N, bz_N):
        if idx == (0, 0, 0):
            continue
        k = 2 * np.pi * np.array(idx, float) / bz_N
        aw = candidate_data(k, p, sw)[3]
        amin, amax = min(amin, aw), max(amax, aw)
    dark_worst, ratio_worst = 0.0, 0.0
    for _ in range(n_dark):
        k = rng.uniform(-math.pi, math.pi, 3)
        U = candidate_data(k, p, sw)[0]
        hn = R25W.static_newton_lift(U)          # lift 由走子唯一确定(冻结)
        Gp, Kp, _, _ = augmented_maps_at_z(k, 1.0, p, sw)
        xn = np.concatenate([hn, np.zeros(4)])[:Kp.shape[1]]
        dark_worst = max(dark_worst, float(np.max(np.abs(Kp @ xn))))
        # 冻结 canary:normal h00 = hbar00/2(恒等;r25_static_newton D0)
        a = np.trace(U) / 2
        hbar00 = (1 + a) ** 2 / (2 * C)
        if abs(hbar00) > 1e-9:
            ratio_worst = max(ratio_worst,
                              abs(float(np.real(hbar00 / hn[0])) - 2.0))
    ok = (amin > 0 and amax < 4 and dark_worst < 1e-11 and ratio_worst < 1e-9)
    return {"layer": "symbol", "status": "PASS" if ok else "FAIL",
            "bz_N": bz_N, "min_nonzero_a_W": amin, "max_a_W": amax,
            "stability_window": "0 < a_W < 4",
            "newton_lift_constraint_dark_worst": dark_worst,
            "dark_threshold": 1e-11,
            "h00bar_over_h00_minus_2_worst": ratio_worst,
            "certificate": ("r25_static_newton_results.json(实空间 canary "
                            "ratio_A=2.000000、尾相关 0.9994/0.9998 为其 D0 "
                            "对应件)")}


def _free_pair(a):
    Im = np.eye(NFIELD)
    return np.block([[(1 - a) * Im, Im], [-a * Im, Im]]).astype(complex)


def _k_state(k, p, sw):
    K0 = augmented_maps_at_z(k, 0.0, p, sw)[1]
    K1 = augmented_maps_at_z(k, 1.0, p, sw)[1] - K0
    a = candidate_data(k, p, sw)[3]
    return np.hstack([K0 + (1 - a) * K1, K1]), a


def col_contraction(p, sw, n_rate, rng):
    """直接收缩率界列:M = F(I-μK*K) 全部本征 ≤1、单位模恰 12
    (2 支 × (4 gauge + 2 物理));最慢收缩率照实报告为界。
    damp_order='free_then_contract' 是登记负控(注能,应红)。"""
    mu = p["mu_damp"]
    kset = [2 * np.pi * np.array(nv, float) / GATE_N for nv in GATE_NVECS]
    kset += [rng.uniform(-math.pi, math.pi, 3) for _ in range(n_rate)]
    worst_mod, rate = 0.0, 0.0
    unitsets = set()
    for k in kset:
        K, a = _k_state(k, p, sw)
        F = _free_pair(a)
        Q = np.eye(2 * NFIELD) - mu * (K.conj().T @ K)
        M = F @ Q if sw["damp_order"] == "contract_then_free" else F - mu * (
            K.conj().T @ K)
        eig = np.linalg.eigvals(M)
        mod = np.abs(eig)
        units = int(np.sum(np.abs(mod - 1) < 2e-9))
        unitsets.add(units)
        worst_mod = max(worst_mod, float(mod.max()))
        sub = mod[mod < 1 - 2e-9]
        if sub.size:
            rate = max(rate, float(sub.max()))
    ok = worst_mod <= 1 + 1e-10 and unitsets == {12}
    return {"layer": "symbol", "status": "PASS" if ok else "FAIL",
            "mu": mu, "points": len(kset), "max_modulus": worst_mod,
            "unit_counts": sorted(unitsets), "expected_unit_count": 12,
            "slowest_contracting_bound": rate,
            "rate_note": ("直接收缩率界;基点 ~0.9999994/步,达机器底需不可"
                          "接受步数 -> 实际率列 pending 卡点②预条件化胜者"),
            "certificate": "r25_dynamic_symbol_results.json"}


def col_reality(p, sw, n_pts, rng):
    """reality pairing 列:物理度规 = (h_+ + conj(h_+))/2(共轭/镜像扇区
    配对)必须实;单手征扇区(pairing='single')是炮,应红。"""
    worst_imag, worst_scale = 0.0, 0.0
    for _ in range(n_pts):
        k = rng.uniform(-math.pi, math.pi, 3)
        U = candidate_data(k, p, sw)[0]
        hn = R25W.static_newton_lift(U)
        if sw["pairing"] == "conjugate":
            phys = 0.5 * (hn + np.conjugate(hn))
        else:
            phys = hn                              # 单扇区:直接当物理(炮)
        worst_imag = max(worst_imag, float(np.max(np.abs(phys.imag))))
        worst_scale = max(worst_scale, float(np.max(np.abs(hn))))
    rel = worst_imag / (worst_scale + 1e-300)
    ok = rel < 1e-12
    return {"layer": "symbol", "status": "PASS" if ok else "FAIL",
            "points": n_pts, "physical_metric_relative_imag": rel,
            "threshold": 1e-12,
            "structure": ("有序 xyz 走子是手征复 stencil;物理实度规 = 与"
                          "共轭/镜像扇区直和后取 (h+conj h)/2,不翻倍 gauge "
                          "rank 或偏振数"),
            "certificate": "r25_static_newton_results.json/reality_structure"}


# =============================================================== 评估器本体
def evaluate_r25_candidate(params, *, wilson_form="q", selector_family="cubic",
                           pairing="conjugate", axis_order="xyz",
                           damp_order="contract_then_free",
                           n_shell=48, n_rate=24, n_dark=32, bz_N=24,
                           seed=250730, realspace_hook=None):
    """一条 R25 族候选 -> 统一 gate columns(schema r25_eval/v1)。

    params: dict 或按 R25_PARAM_NAMES 排序的向量(连续先验列);
    离散开关(炮/附检)走 kwargs,不进先验。
    realspace_hook: 卡点①所有者提供的实空间列钩子(REALSPACE_INTERFACE);
    缺省时实空间列全部 PENDING,m3_ready 恒 False。
    """
    t0 = time.time()
    if not isinstance(params, dict):
        params = dict(zip(R25_PARAM_NAMES, [float(v) for v in params]))
    p = dict(BASE_POINT)
    p.update(params)
    sw = {"wilson_form": wilson_form, "selector_family": selector_family,
          "pairing": pairing, "axis_order": axis_order,
          "damp_order": damp_order}
    rng = np.random.default_rng(seed)

    cols = {}
    cols["shell_J5"] = col_shell_j5(p, sw)
    cols["cohomology"] = col_cohomology(p, sw, n_shell, rng)
    cols["uv_audit"] = col_uv_audit(p, sw)
    cols["static_newton"] = col_static_newton(p, sw, n_dark, bz_N, rng)
    cols["contraction_rate"] = col_contraction(p, sw, n_rate, rng)
    cols["reality_pairing"] = col_reality(p, sw, 16, rng)

    # ---- 实空间列:留槽(卡点①),接口签名定死 ----
    spec = {"params": p, "switches": sw}
    hooked = {}
    if realspace_hook is not None:
        hooked = realspace_hook(spec) or {}
    for name in REALSPACE_COLUMNS:
        if name in hooked:
            row = dict(hooked[name])
            row["layer"] = "realspace"
            cols[name] = row
        else:
            cols[name] = {"layer": "realspace", "status": "PENDING",
                          "blocked_by": "卡点①(实空间 time-step/伴随桥)",
                          "interface": REALSPACE_INTERFACE["hook_signature"]}

    symbol_green = all(cols[n]["status"] == "PASS" for n in SYMBOL_COLUMNS)
    realspace_green = all(cols[n]["status"] == "PASS"
                          for n in REALSPACE_COLUMNS)
    return {
        "schema": SCHEMA_VERSION,
        "params": p, "switches": sw,
        "columns": cols,
        "symbol_green": bool(symbol_green),
        "realspace_green": bool(realspace_green),
        "m3_ready": bool(symbol_green and realspace_green),
        "claim_discipline": CLAIM_DISCIPLINE,
        "seconds": time.time() - t0,
    }


# =============================================== 先验采样器(草案,待拍板)
def sample_r25_prior(n, seed=0):
    """(n,4) host float,按 R25_PARAM_NAMES;范围 = 预注册草案-R25-参数族.md
    的建议值(冻结权在评审):
      alpha_W   ~ U(0.0, 0.9)   (含 0 端 -> 族含非 GR 候选:UV 节点不提升)
      sel_gain  ~ U(0.55, 0.95) (基点 0.75;偏移 = 非 GR 静态响应方向)
      sel_trace ~ U(2.0, 4.0)   (基点 3.0;同上)
      mu_damp   ~ 10^U(-5, -2.5)(占位,卡点②胜者拍板后收紧)
    """
    rng = np.random.default_rng(seed)
    return np.stack([
        rng.uniform(0.0, 0.9, n),
        rng.uniform(0.55, 0.95, n),
        rng.uniform(2.0, 4.0, n),
        10.0 ** rng.uniform(-5.0, -2.5, n),
    ], axis=1)


# ================================================================= schema 件
def write_schema(path=OUT_SCHEMA):
    """统一证据 schema 第一版(复盘 §4.3;dashboard_r25 与卡点①共用)。"""
    schema = {
        "schema": SCHEMA_VERSION,
        "written_by": "experiments/r25_family_eval.py",
        "state_json_convention": {
            "path": STATE_JSON_CONVENTION,
            "producer": "统一实空间运行(卡点①落地后)",
            "shape": {
                "schema": SCHEMA_VERSION,
                "params": "R25_PARAM_NAMES 字典",
                "switches": "离散开关字典",
                "columns": "{列名: {layer, status, ...数值}}",
                "symbol_green/realspace_green/m3_ready": "bool 三层判定",
            },
            "dashboard": ("visualizations/dashboards/dashboard_r25.html 轮询"
                          "本文件;缺失时显示'待实空间列'并回退到静态证书"),
        },
        "claim_discipline": CLAIM_DISCIPLINE,
        "param_names": R25_PARAM_NAMES,
        "base_point": BASE_POINT,
        "base_switches": BASE_SWITCHES,
        "prior_draft": {
            "alpha_W": "U(0.0, 0.9)", "sel_gain": "U(0.55, 0.95)",
            "sel_trace": "U(2.0, 4.0)", "mu_damp": "10^U(-5, -2.5)",
            "note": "草案待评审拍板(预注册草案-R25-参数族.md);拍板后只许收紧",
        },
        "switch_domains": {
            "wilson_form": ["q", "q2"], "selector_family": ["cubic", "none"],
            "pairing": ["conjugate", "single"],
            "axis_order": ["xyz", "zyx", "..."],
            "damp_order": ["contract_then_free", "free_then_contract"],
        },
        "columns": {
            "shell_J5": {"layer": "symbol", "gate": "max_relative_J5 < 1e-2",
                         "source": "r25_auxiliary_wilson_results.json"},
            "cohomology": {"layer": "symbol",
                           "gate": "rank(G+,K+)=(4,8) ∧ 商维=2 ∧ 恒等<1e-11",
                           "source": "r25_auxiliary_wilson_results.json"},
            "uv_audit": {"layer": "symbol",
                         "gate": "冻结 +I 节点提升:rank(4,8)、商维 2",
                         "source": "r25_uv_exceptional_results.json"},
            "static_newton": {"layer": "symbol",
                              "gate": ("0<a_W<4 全 BZ ∧ lift 全暗 <1e-11 ∧ "
                                       "hbar00/h00 = 2"),
                              "source": "r25_static_newton_results.json"},
            "contraction_rate": {"layer": "symbol",
                                 "gate": "谱模 ≤1 ∧ 单位模恰 12;率照实报告",
                                 "source": "r25_dynamic_symbol_results.json"},
            "reality_pairing": {"layer": "symbol",
                                "gate": "配对物理度规相对虚部 < 1e-12",
                                "source": "r25_static_newton_results.json"},
            **{name: {"layer": "realspace", "gate": "PENDING 卡点①",
                      "interface": REALSPACE_INTERFACE["hook_signature"]}
               for name in REALSPACE_COLUMNS},
        },
        "provenance_sha256": provenance(),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(schema, fh, ensure_ascii=False, indent=2)
    return schema


# ======================================================================= 自测
def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_san(v) for v in o]
    if isinstance(o, np.ndarray):
        return _san(o.tolist())
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if np.isfinite(f) else str(f)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def run_selftest(write_json=True):
    t0 = time.time()
    out = {"schema": SCHEMA_VERSION, "provenance_sha256": provenance()}
    print("r25_family_eval -- R25 参数族统一评估器自测(不发令、不长跑)")
    print("=" * 72)

    # [0] 构造保真:参数化 walk 符号在 xyz 下与冻结 L2.walk_symbol 逐位一致
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(32):
        k = rng.uniform(-math.pi, math.pi, 3)
        worst = max(worst, float(np.max(np.abs(
            walk_symbol_order(k, "xyz") - L2.walk_symbol(k)))))
    ok_fid = worst < 1e-14
    out["fidelity_walk_symbol_maxdiff"] = worst
    print(f"[0] 构造保真(xyz vs 冻结 L2.walk_symbol): Δ={worst:.1e} -> "
          f"{'PASS' if ok_fid else 'FAIL'}")

    # [1] 基点应符号列全绿
    r0 = evaluate_r25_candidate(BASE_POINT)
    out["base_eval"] = r0
    print(f"[1] 基点 evaluate({r0['seconds']:.1f}s): "
          f"symbol_green={r0['symbol_green']}  m3_ready={r0['m3_ready']}"
          f"(实空间列 PENDING 卡点① -> 恒 False)")
    for n in SYMBOL_COLUMNS:
        print(f"    {n:18s} {r0['columns'][n]['status']}")

    # [2] 族内非 GR 方向 / 炮:各应在预期列上红
    tests = [
        ("N1_no_wilson_alpha0", dict(params=dict(BASE_POINT, alpha_W=0.0)),
         "uv_audit"),
        ("N2_selector_trace_off", dict(params=dict(BASE_POINT, sel_trace=2.0)),
         "static_newton"),
        ("N3_no_elimination_syzygy", dict(params=BASE_POINT,
                                          selector_family="none"),
         "cohomology"),
        ("N4_single_chiral_sector", dict(params=BASE_POINT, pairing="single"),
         "reality_pairing"),
        ("N5_axis_order_zyx", dict(params=BASE_POINT, axis_order="zyx"),
         "shell_J5"),
        ("N6_overdamped_mu", dict(params=dict(BASE_POINT, mu_damp=0.03)),
         "contraction_rate"),
    ]
    cann = {}
    all_fire = True
    for name, kw, want in tests:
        pa = kw.pop("params")
        r = evaluate_r25_candidate(pa, bz_N=12, n_shell=24, **kw)
        red = [n for n in SYMBOL_COLUMNS if r["columns"][n]["status"] != "PASS"]
        fired = (not r["symbol_green"]) and (want in red)
        all_fire &= fired
        cann[name] = {"symbol_green": r["symbol_green"], "red_columns": red,
                      "want_red": want, "fired": fired}
        print(f"[2] {name}: red={red}(要求含 {want})-> "
              f"{'红 as required' if fired else '炮哑!'}")
    out["negative_controls"] = cann

    # [3] schema 件落盘
    schema = write_schema()
    out["schema_written"] = OUT_SCHEMA
    print(f"[3] schema 写入 {os.path.relpath(OUT_SCHEMA, ROOT)}"
          f"(列 {len(schema['columns'])} 个,其中实空间 "
          f"{len(REALSPACE_COLUMNS)} 个 PENDING 卡点①)")

    ok = bool(ok_fid and r0["symbol_green"] and (not r0["m3_ready"])
              and all_fire)
    out["selftest_PASS"] = ok
    out["total_seconds"] = time.time() - t0
    out["claim_discipline"] = CLAIM_DISCIPLINE
    print("=" * 72)
    print(f"自测总判定: {'PASS' if ok else 'FAIL'}({out['total_seconds']:.0f}s)")
    if write_json:
        os.makedirs(os.path.dirname(OUT_SELFTEST), exist_ok=True)
        with open(OUT_SELFTEST, "w", encoding="utf-8") as fh:
            json.dump(_san(out), fh, ensure_ascii=False, indent=1)
        print(f"wrote {os.path.relpath(OUT_SELFTEST, ROOT)}")
    return out


if __name__ == "__main__":
    res = run_selftest()
    raise SystemExit(0 if res["selftest_PASS"] else 1)
