#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2m2_dw_scaling_audit -- M2' 补测一:体对角 Δω(k;L) 标度审计(裁定一预注册)。

授权与血统
==========
  docsv2/v2-裁定-M2轮2三裁-2026-07-27.md 裁定一(车道A 签):
    "加一道预注册补测(轮 3 前,分钟级):体对角 Δω(k;L) 标度审计——预言
     Δω ∝ k²(指数预注册 2.0±0.3,同源于 p=2 推导),拟合口径沿 R37/不变量协议。"
  本件为**诊断级补测**:独立新 JSON,不改 v2m2_coupled_loop.json;判据/预言/
  分支自本头部写死后零回改(红线 4)。

观测量(写死)
==============
  Δω(k) ≡ |ω_walk(k) − ω_shell(k)|,沿体对角射线 k = comp·(1,1,1):
    ω_walk(k)  = 冻结 cp1_v4_L2.walk_symbol(k, th=π/3)(2×2 酉,涌现物质走行
                 xyz 有序乘积符号)的正本征相位;±对称性作为仪器自检入册
                 (轮 2 追因实测双支对称 ±0.8024,无 U(1) 偏移,比较器无病);
    ω_shell(k) = 冻结 r15_walk_dedonder.shell_omega(k, c=cos(π/3)=0.5)
                 (R30 几何手搭调频所依据的 shell 公式)。
  控制列(非门,写死):
    axial (1,0,0)   —— 预言 Δω 位级零(轮 2 实测 1e-16;机器负控);
    face  (1,1,0)   —— 诊断列,同协议拟合入册,不参与分支判定。

预言(先行写死;运行后零回改)
==============================
  ALPHA_PRED = 2.0,窗 ±0.3 ⟹ PASS 窗 [1.7, 2.3]。
  推导(同源 p=2,引 v2m2_candidate P_PRED_DERIVATION 与轮 2 §八-1):
    placed 半角符号 κ_i = 2 sin(k_i/2) 为奇函数,展开无二阶差 ⟹ shell 公式
    连续极限误差 O(k²);涌现走行为 xyz **有序乘积**(Trotter),轴向单因子时
    与 shell 精确同谱(轮 2 实测轴向/Nyquist 位级零),体对角三因子非对易,
    BCH 首阶修正为生成元对易子级 O(k²) ⟹ Δω 体对角首阶 O(k²),指数 2。

拟合协议(沿 R37 冻结协议,常量逐位同源;写死)
==============================================
  格点池 L ∈ {16,24,32,48},射线采样 n=1..floor(L/4),按 n/L 精确分数去重;
  拟合窗 n/L ≤ 1/8(comp ≤ π/4),1/8 < n/L ≤ 1/4 仅入册不拟合;
  k=0 邻域剔点:窗内仅有 n=1 出处的点剔除(excluded_k0_neighbour,R37 同款);
  双模型:M0 常数 y=A(p=1) vs M1 幂律 y=A+B·k^α(α 网格 0.05..4.00 步 0.01,
  逐 α 线性最小二乘,p=3);判据 AIC = m·ln(RSS/m)+2p,决定性 |ΔAIC| ≥ 2。

常数分量判据(两口径并列,写死;签发时刻 D-M2-6 双控制件尚未落盘)
================================================================
  口径一(R37 遗留):A 与 0 一致 iff |A| ≤ 2σ_A。
  口径二(D-M2-6,裁定二预注册文本;确定性级数截断稳健双测,两测同判方为
  "A 与 0 一致"):
    (i) 高阶模型测试:y = A' + B·k^α + C·k^(α+2)(α 网格,p=4)重拟合;
        ΔAIC 支持高阶模型(AIC_high < AIC_power − 2)且截距塌缩 ≥5×
        (|A'| ≤ |A|/5)→ 判截断污染;
    (ii) 半窗塌缩测试:拟合窗减半(n/L ≤ 1/16)重拟合;若半窗内在拟合点
        < 3,则纳入半窗内 k0 邻域剔点以保持可拟(此规则在此写死);
        |A_half| ≤ |A|/2 → 判截断污染;
    任一测不判污染 → 排零维持 FAIL。
  分支判定用"常数分量存在" := 口径一失守 且 口径二不判污染(真非截断)。
  (若口径一直接过,两口径一致判无常数分量。)

两分支(写死,不许事后择)
==========================
  (a) α_体对角 ∈ [1.7, 2.3] 且无常数分量 → SCALING-CONFIRMED:发现良性,
      G1 PASS 落定;Δω 各向异性升格 M3′ 硬点(walk 属性;候选族方向:
      按实际 Floquet 壳调频几何);
  (b) 常数分量存在(排零失败且非截断污染)→ TRUE-CONE-SPLIT:真锥分裂,
      候选改频重跑,G1 FAIL 以正当程序回归——停手报车道A,不自行改频;
  其余(指数出窗/拟合不稳/AIC 不决定)→ AMBIGUOUS:如实报,标需会商。

冻结件只读 + hash 校验(红线 1/2)
=================================
  experiments/cp1_v4_L2.py / experiments/r15_walk_dedonder.py 逐位比对
  rulespace_v2.frozen.EXPECTED_SHA256;experiments/v2m2_candidate.py 与
  data/results/v2m2_candidate.json construction_sha256 =
  70f2c1504f1b5cc5c9186700e039993b4c1c3077ca8c2196459984f6cb508eae 见证入册。
  fp64 numpy;任一 hash 失配 → HALT。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from fractions import Fraction

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (ROOT, DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

from rulespace_v2 import frozen as FZ                      # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m2_dw_scaling_results.json")

# ---- 预注册常量(写死;运行后零回改) -------------------------------------
ALPHA_PRED = 2.0
ALPHA_HALF_WINDOW = 0.3                       # PASS 窗 [1.7, 2.3]
LATTICES = [16, 24, 32, 48]
DIRS = {"axial": (1, 0, 0), "face-diagonal": (1, 1, 0),
        "body-diagonal": (1, 1, 1)}
DECISION_DIRECTION = "body-diagonal"          # 分支判定仅用体对角
AXIAL_ZERO_LINE = 1e-12                       # 控制列位级零线(保守)
FIT_RATIO_MAX = Fraction(1, 8)                # R37 冻结:comp <= pi/4
CTX_RATIO_MAX = Fraction(1, 4)                # 仅入册,不拟合
HALF_RATIO_MAX = Fraction(1, 16)              # D-M2-6 (ii) 半窗
ALPHA_GRID = np.arange(0.05, 4.001, 0.01)     # R37 冻结网格
DAIC_DECISIVE = 2.0
SYM_DEV_LINE = 1e-12                          # ±本征相位对称仪器自检线

CONSTRUCTION_SHA256_EXPECTED = (
    "70f2c1504f1b5cc5c9186700e039993b4c1c3077ca8c2196459984f6cb508eae")
FROZEN_CHECK = {                              # 逐位比对 frozen.EXPECTED_SHA256
    "experiments/cp1_v4_L2.py":
        "556e56665766b29c22eedf226645e3530c95c8ddc27e2b99527eb6158a70fb67",
    "experiments/r15_walk_dedonder.py":
        "ce10bc05c5caa487154a72a4169a1095930afe2afd2d84e4f49bba1041bb18cc",
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
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ---- 观测量 ---------------------------------------------------------------
def dw_point(L2, r15, k):
    """返回 (dw, w_walk, w_shell, sym_dev);shell 出带返回 None。"""
    ws = r15.shell_omega(k)
    if ws is None:
        return None
    U = L2.walk_symbol(np.asarray(k, float))
    ph = np.sort(np.angle(np.linalg.eigvals(U)))
    sym_dev = float(abs(ph[0] + ph[1]))                 # ± 对称自检
    ww = float(0.5 * (ph[1] - ph[0]))                   # 正本征相位(稳健)
    return float(abs(ww - ws)), ww, float(ws), sym_dev


def collect_direction(L2, r15, dname, dvec):
    samples = {}
    for L in LATTICES:
        n_max = int(CTX_RATIO_MAX * L)
        for n in range(1, n_max + 1):
            r = Fraction(n, L)
            if r > CTX_RATIO_MAX:
                continue
            if r in samples:
                samples[r]["provenance"].append([L, n])
                continue
            comp = 2.0 * math.pi * float(r)
            k = comp * np.array(dvec, float)
            res = dw_point(L2, r15, k)
            s = {"ratio": [r.numerator, r.denominator], "comp": comp,
                 "kabs": comp * math.sqrt(float(np.dot(dvec, dvec))),
                 "provenance": [[L, n]]}
            if res is None:
                s["off_band"] = True
            else:
                s["off_band"] = False
                s["dw"], s["w_walk"], s["w_shell"], s["sym_dev"] = res
            samples[r] = s
    out = []
    for r in sorted(samples):
        s = samples[r]
        in_window = r <= FIT_RATIO_MAX
        has_n_ge2 = any(n >= 2 for _, n in s["provenance"])
        s["in_fit_window"] = bool(in_window)
        s["excluded_k0_neighbour"] = bool(in_window and not has_n_ge2)
        s["in_fit"] = bool(in_window and has_n_ge2 and not s["off_band"])
        s["in_half_window"] = bool(Fraction(*s["ratio"]) <= HALF_RATIO_MAX
                                   and not s["off_band"])
        out.append(s)
    return out


# ---- R37 冻结双模型拟合 ----------------------------------------------------
def fit_constant(x, y):
    m = len(y)
    A0 = float(np.mean(y))
    rss = float(np.sum((y - A0) ** 2))
    aic = m * math.log(max(rss, 1e-300) / m) + 2 * 1
    sigA = float(np.std(y, ddof=1) / math.sqrt(m)) if m > 1 else float("inf")
    return {"model": "constant", "A": A0, "sigma_A": sigA, "RSS": rss,
            "AIC": aic, "m": m, "p": 1}


def fit_power(x, y):
    m = len(y)
    best = None
    for al in ALPHA_GRID:
        X = np.column_stack([np.ones(m), x ** al])
        coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        rss = float(np.sum((y - X @ coef) ** 2))
        if best is None or rss < best[0]:
            best = (rss, float(al), float(coef[0]), float(coef[1]))
    rss, al, A, B = best
    aic = m * math.log(max(rss, 1e-300) / m) + 2 * 3
    J = np.column_stack([np.ones(m), x ** al, B * np.log(x) * (x ** al)])
    dof = max(m - 3, 1)
    s2 = rss / dof
    try:
        cov = s2 * np.linalg.inv(J.T @ J)
        sigA = float(math.sqrt(max(cov[0, 0], 0.0)))
        sigB = float(math.sqrt(max(cov[1, 1], 0.0)))
        sigAl = float(math.sqrt(max(cov[2, 2], 0.0)))
    except np.linalg.LinAlgError:
        sigA = sigB = sigAl = float("inf")
    return {"model": "power", "A": A, "sigma_A": sigA, "B": B, "sigma_B": sigB,
            "alpha": al, "sigma_alpha": sigAl, "RSS": rss, "AIC": aic,
            "m": m, "p": 3}


def fit_power_high(x, y):
    """D-M2-6 (i):y = A' + B k^α + C k^(α+2),α 网格,p=4。"""
    m = len(y)
    best = None
    for al in ALPHA_GRID:
        X = np.column_stack([np.ones(m), x ** al, x ** (al + 2.0)])
        coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        rss = float(np.sum((y - X @ coef) ** 2))
        if best is None or rss < best[0]:
            best = (rss, float(al), [float(c) for c in coef])
    rss, al, coef = best
    aic = m * math.log(max(rss, 1e-300) / m) + 2 * 4
    return {"model": "power+high", "A": coef[0], "B": coef[1], "C": coef[2],
            "alpha": al, "RSS": rss, "AIC": aic, "m": m, "p": 4}


def judge_direction(dname, pts):
    fitpts = [s for s in pts if s["in_fit"]]
    x = np.array([s["kabs"] for s in fitpts])
    y = np.array([s["dw"] for s in fitpts])
    m0 = fit_constant(x, y)
    m1 = fit_power(x, y)
    daic = m0["AIC"] - m1["AIC"]
    winner = m1 if m1["AIC"] < m0["AIC"] else m0
    decisive = bool(abs(daic) >= DAIC_DECISIVE)
    alpha_in_window = bool(m1["model"] == "power"
                           and abs(m1["alpha"] - ALPHA_PRED)
                           <= ALPHA_HALF_WINDOW)

    # ---- 常数分量:口径一(R37 遗留 2σ) ----------------------------------
    legacy_A_zero = bool(abs(m1["A"]) <= 2.0 * m1["sigma_A"])

    # ---- 常数分量:口径二(D-M2-6 截断稳健双测) --------------------------
    mh = fit_power_high(x, y)
    t1_pollution = bool(mh["AIC"] < m1["AIC"] - DAIC_DECISIVE
                        and abs(mh["A"]) <= abs(m1["A"]) / 5.0)
    halfpts = [s for s in fitpts if s["in_half_window"]]
    half_included_k0 = False
    if len(halfpts) < 3:
        halfpts = [s for s in pts if s["in_half_window"]
                   and s["in_fit_window"]]
        half_included_k0 = True
    xh = np.array([s["kabs"] for s in halfpts])
    yh = np.array([s["dw"] for s in halfpts])
    m1h = fit_power(xh, yh) if len(halfpts) >= 3 else None
    t2_pollution = bool(m1h is not None
                        and abs(m1h["A"]) <= abs(m1["A"]) / 2.0)
    dm26_pollution = bool(t1_pollution and t2_pollution)
    dm26_A_zero = bool(legacy_A_zero or dm26_pollution)

    constant_present = bool((not legacy_A_zero) and (not dm26_pollution))

    return {
        "direction": dname,
        "n_fit_points": len(fitpts),
        "fit_kabs": [float(v) for v in x],
        "fit_dw": [float(v) for v in y],
        "sym_dev_max": max((s["sym_dev"] for s in pts if not s["off_band"]),
                           default=0.0),
        "constant_model": m0,
        "power_model": m1,
        "dAIC_const_minus_power": daic,
        "winner": winner["model"],
        "decisive": decisive,
        "alpha_measured": m1["alpha"],
        "alpha_pred": ALPHA_PRED,
        "alpha_window": [ALPHA_PRED - ALPHA_HALF_WINDOW,
                         ALPHA_PRED + ALPHA_HALF_WINDOW],
        "alpha_in_window": alpha_in_window,
        "A_zero_caliber_legacy_2sigma": {
            "A": m1["A"], "sigma_A": m1["sigma_A"],
            "A_consistent_with_zero": legacy_A_zero},
        "A_zero_caliber_DM26": {
            "high_order_model": mh,
            "test_i_pollution": t1_pollution,
            "half_window_model": m1h,
            "half_window_included_k0_neighbours": half_included_k0,
            "test_ii_pollution": t2_pollution,
            "both_tests_pollution": dm26_pollution,
            "A_consistent_with_zero": dm26_A_zero,
            "note": ("D-M2-6 双控制件签发时刻尚未落盘;两口径并列如实报,"
                     "分支判定用'口径一失守且口径二不判污染'为常数分量存在")},
        "constant_present": constant_present,
    }


def main():
    t0 = time.time()
    payload = {
        "register": "v2m2-dw-scaling (M2' 补测一:体对角 Δω(k;L) 标度审计)",
        "level": "diagnostic-supplement (裁定一预注册;不改 v2m2_coupled_loop.json)",
        "status": "RUNNING",
        "backend": "numpy (fp64)",
        "authority": [
            "docsv2/v2-裁定-M2轮2三裁-2026-07-27.md 裁定一/裁定二(D-M2-6 文本)",
            "docsv2/v2-小报告-M2-轮2草稿.md §七-1/§八-1",
            "experiments/r37_residual_scaling_audit.py(拟合协议冻结血统)",
        ],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": {
            "observable": ("Δω(k) = |eigphase(cp1_v4_L2.walk_symbol(k,π/3)) − "
                           "r15.shell_omega(k,c=0.5)| 沿射线;体对角判定,"
                           "axial 位级零控制,face 诊断列"),
            "alpha_pred": ALPHA_PRED,
            "alpha_window": [ALPHA_PRED - ALPHA_HALF_WINDOW,
                             ALPHA_PRED + ALPHA_HALF_WINDOW],
            "derivation": ("κ_i=2sin(k_i/2) 奇函数无二阶差 ⟹ shell O(k²);"
                           "xyz 有序乘积轴向精确同谱、体对角 BCH 对易子首阶 "
                           "O(k²) ⟹ Δω ∝ k²(同源 p=2 推导)"),
            "fit_protocol": ("R37 冻结:L∈{16,24,32,48} 按 n/L 去重池化;"
                             "拟合窗 n/L≤1/8;k0 邻域(仅 n=1 出处)剔点;"
                             "常数 vs 幂律 A+B·k^α(α 网格 0.05..4.00 步 "
                             "0.01);AIC 决定性 |ΔAIC|≥2"),
            "constant_calibers": "两口径并列(R37 2σ_A;D-M2-6 截断稳健双测)",
            "branches": {
                "a": "α∈[1.7,2.3] 且无常数分量 → SCALING-CONFIRMED(G1 PASS "
                     "落定;Δω 各向异性升格 M3′ 硬点,候选族方向=按实际 "
                     "Floquet 壳调频几何)",
                "b": "常数分量存在 → TRUE-CONE-SPLIT(候选改频重跑;G1 FAIL "
                     "正当程序回归;停手报车道A)",
                "else": "AMBIGUOUS(如实报,标需会商)",
            },
        },
    }

    # ---- 冻结件 hash 校验(失配 => HALT) --------------------------------
    hashes = {}
    ok = True
    for rel, exp in FROZEN_CHECK.items():
        got = sha256_file(os.path.join(ROOT, rel))
        match = (got == exp) and (FZ.EXPECTED_SHA256.get(rel) == exp)
        hashes[rel] = {"sha256": got, "expected": exp, "match": match}
        ok = ok and match
    with open(os.path.join(ROOT, "data", "results",
                           "v2m2_candidate.json")) as fh:
        cj = json.load(fh)
    con_sha = cj["construction_freeze"]["construction_sha256"]
    hashes["v2m2_candidate.json:construction_sha256"] = {
        "sha256": con_sha, "expected": CONSTRUCTION_SHA256_EXPECTED,
        "match": con_sha == CONSTRUCTION_SHA256_EXPECTED}
    ok = ok and hashes["v2m2_candidate.json:construction_sha256"]["match"]
    hashes["experiments/v2m2_candidate.py"] = {
        "sha256": sha256_file(os.path.join(ROOT, "experiments",
                                           "v2m2_candidate.py")),
        "note": "witness (read-only)"}
    hashes["this_script"] = {
        "sha256": sha256_file(os.path.abspath(__file__))}
    payload["frozen_hashes"] = hashes
    if not ok:
        payload["status"] = "HALT-HASH-MISMATCH"
        write_json(payload)
        print("HALT: frozen hash mismatch")
        return 1
    write_json(payload)

    # ---- 采集(增量写盘) -------------------------------------------------
    L2 = FZ.mod("cp1_v4_L2")
    r15 = FZ.mod("r15_walk_dedonder")
    payload["samples"] = {}
    for dname, dvec in DIRS.items():
        payload["samples"][dname] = collect_direction(L2, r15, dname, dvec)
        write_json(payload)

    # ---- 固定 k 复现锚(轮 2 追因数字对拍,非门) -------------------------
    k222 = np.array([math.pi / 4] * 3)
    anchor = dw_point(L2, r15, k222)
    payload["anchor_222_reproduction"] = {
        "k": [math.pi / 4] * 3,
        "dw": anchor[0], "w_walk": anchor[1], "w_shell": anchor[2],
        "sym_dev": anchor[3],
        "expected_from_round2": {"w_walk": 0.8024, "w_shell": 0.6756},
    }

    # ---- 拟合与判定 -------------------------------------------------------
    judges = {}
    for dname in DIRS:
        pts = payload["samples"][dname]
        fitn = sum(1 for s in pts if s["in_fit"])
        if dname == "axial":
            dwmax = max(s["dw"] for s in pts if not s["off_band"])
            judges[dname] = {"direction": dname,
                             "control": "machine-zero",
                             "dw_max": dwmax,
                             "pass_zero_line": bool(dwmax <= AXIAL_ZERO_LINE)}
            # axial 同时入册同协议拟合作诊断(预期退化,不判)
            if fitn >= 4:
                judges[dname]["diagnostic_fit"] = judge_direction(dname, pts)
            continue
        judges[dname] = judge_direction(dname, pts)
    payload["judges"] = judges
    write_json(payload)

    # ---- 分支落点(写死逻辑) ---------------------------------------------
    J = judges[DECISION_DIRECTION]
    axial_ok = judges["axial"]["pass_zero_line"]
    sym_ok = bool(J["sym_dev_max"] <= SYM_DEV_LINE)
    if J["constant_present"]:
        branch = "b:TRUE-CONE-SPLIT"
        verdict = ("真锥分裂:常数分量排零失败且非截断污染 → 候选改频重跑;"
                   "G1 FAIL 以正当程序回归;停手报车道A")
    elif (J["alpha_in_window"] and J["winner"] == "power" and J["decisive"]
          and axial_ok and sym_ok):
        branch = "a:SCALING-CONFIRMED"
        verdict = ("标度证实:发现良性,G1 PASS 落定;Δω 各向异性升格 M3′ "
                   "硬点(walk 属性;候选族方向:按实际 Floquet 壳调频几何)")
    else:
        branch = "ambiguous"
        verdict = "指数出窗/拟合不稳/控制列异常:如实报,标需会商"
    payload["branch"] = branch
    payload["verdict"] = verdict
    payload["instrument_sanity"] = {
        "axial_zero_control_pass": axial_ok,
        "eigenphase_symmetry_pass": sym_ok,
        "sym_dev_max_body": J["sym_dev_max"],
    }
    payload["status"] = "DONE"
    payload["seconds_total"] = time.time() - t0
    write_json(payload)

    m1 = J["power_model"]
    print(f"DW-AUDIT DONE {payload['seconds_total']:.1f}s")
    print(f"  body-diagonal alpha = {m1['alpha']:.4f} (pred 2.0±0.3) "
          f"dAIC={J['dAIC_const_minus_power']:.1f} "
          f"A={m1['A']:.3e} sigma_A={m1['sigma_A']:.3e}")
    print(f"  legacy A-zero: {J['A_zero_caliber_legacy_2sigma']['A_consistent_with_zero']}; "
          f"DM26 A-zero: {J['A_zero_caliber_DM26']['A_consistent_with_zero']}; "
          f"constant_present={J['constant_present']}")
    print(f"  axial control max dw = {judges['axial']['dw_max']:.3e}")
    print(f"  BRANCH: {branch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
