# -*- coding: utf-8 -*-
"""M2′ 补测二:D-M2-6 口径双控制验证 + G6 σ-ii 重判(三裁·裁定二执行件)。

权威文本:docsv2/v2-裁定-M2轮2三裁-2026-07-27.md 裁定二。
被重判对象:data/results/v2m2_coupled_loop.json M2-G6 sigma_branch_ii_sourced
(只读;A=-1.2266e-4=3.4σ_A → 旧口径弱档 FAIL)。

═══════════════ 预注册冻结区(运行前写死,零回改) ═══════════════

D-M2-6 口径(裁定二原文的可执行落地;两测同判"截断污染"方为"A 与 0 一致"):

  [T1] 高阶模型测试:在 R37 冻结幂律协议(ALPHA_GRID=0.05..4.00 步 0.01,
       lstsq,AIC=m·ln(RSS/m)+2p)上加 k^(α+2) 项整体重拟合
       y = A' + B'·x^α + C'·x^(α+2)(α 随高阶模型在同一网格重扫——
       "重拟合"取全模型重拟合读法)。判"截断污染"当且仅当
       ΔAIC = AIC_power − AIC_high ≥ 2.0(高阶模型获支持)
       且 |A'| ≤ |A|/5(截距塌缩 ≥5×)。

  [T2] 半窗塌缩测试:拟合窗上缘收窄——4 点 ray 中去掉最大 x 点,保留 3 个
       最小 x 点(窗 ×2/3;严格 x≤x_max/2 只剩 2 点,3 参数幂律重拟合欠定,
       不可执行;窗 ×2/3 下截断污染预期塌缩 ×(2/3)²≈0.44,仍在 2× 线内侧,
       有牙性由下方双控制实证),幂律模型全网格重拟合得 A_half。
       判"截断污染"当且仅当 |A_half| ≤ |A|/2。

  任一测不判污染 → 排零维持 FAIL,不通融。
  两测同判污染 → σ-ii 排零 PASS(其余 σ-ii 子件沿轮 2 实测:ΔAIC=55.7 决定性、
  α=1.96≥1 → σ-ii 整支 PASS → G6 整门 PASS,因 σ-i/ρ/b_layer/层间引理均已过)。

实现选型入册(由双控制淘汰,先于重判冻结):
  H1(2 点半窗、α 冻结于全窗幂律拟合值)控制 A 塌缩比 0.82–1.05 → 无牙,弃;
  H2(2 点半窗、α 冻结于高阶模型拟合值)控制 B1/B4 误塌缩(0.29/0.23)→ 弃;
  H3(3 点半窗、全网格重拟合)= 唯一双控制幸存实现 → 冻结为 [T2]。

双控制构造(确定性合成级数,参数量级仿 σ-ii 实测:B≈0.236、α≈2、
拟合截距量级 ~1e-4;含 k^(α+4) 尾项仿真实级数高阶结构):
  y(x) = A0 + B·x^α + C·x^(α+2) + D·x^(α+4),x = 2π/L,L ∈ {16,24,32,48}
  控制 A(A0=0,须判污染 → 排零 PASS):
    A1 (0, 2.0, -0.05, +0.01)   A2 (0, 2.0, -0.02, -0.005)
    A3 (0, 2.0, -0.10, +0.02)   A4 (0, 1.9, -0.05, +0.01)
  控制 B(A0≠0 量级 1.2e-4,须不判污染 → 排零 FAIL):
    B1 (-1.2e-4, 2.0, -0.05, +0.01)  B2 (+1.2e-4, 2.0, -0.05, +0.01)
    B3 (-2.4e-4, 2.0, -0.02, -0.005) B4 (-1.2e-4, 1.9, -0.05, +0.01)
  全 8 组判对才算口径有牙;任一失守 → 口径回炉,写盘退出,不做重判。

═══════════════ 预注册冻结区结束 ═══════════════
"""
import hashlib
import json
import math
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROUND2_JSON = os.path.join(ROOT, "data", "results", "v2m2_coupled_loop.json")
OUT_JSON = os.path.join(ROOT, "data", "results", "v2m2_dm26_results.json")

# ---- 冻结常数(零回改) ----------------------------------------------------
ALPHA_GRID = np.arange(0.05, 4.001, 0.01)          # R37 逐字
DAIC_LINE = 2.0                                     # ΔAIC 支持线(R37 惯例)
COLLAPSE_HIGH = 5.0                                 # T1 截距塌缩线
COLLAPSE_HALF = 2.0                                 # T2 半窗塌缩线
LS = [16, 24, 32, 48]
B_SYN = 0.236                                       # 仿 σ-ii 实测 B
CONTROLS = [
    # (name, family, A0, alpha, C, D)
    ("A1", "A", 0.0,      2.0, -0.05, +0.01),
    ("A2", "A", 0.0,      2.0, -0.02, -0.005),
    ("A3", "A", 0.0,      2.0, -0.10, +0.02),
    ("A4", "A", 0.0,      1.9, -0.05, +0.01),
    ("B1", "B", -1.2e-4,  2.0, -0.05, +0.01),
    ("B2", "B", +1.2e-4,  2.0, -0.05, +0.01),
    ("B3", "B", -2.4e-4,  2.0, -0.02, -0.005),
    ("B4", "B", -1.2e-4,  1.9, -0.05, +0.01),
]


# ---- R37 冻结拟合协议(逐字复刻 + 高阶扩展) --------------------------------
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
    return {"A": A, "B": B, "alpha": al, "RSS": rss, "AIC": aic, "p": 3}


def fit_high(x, y):
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
    return {"A": coef[0], "B": coef[1], "C": coef[2], "alpha": al,
            "RSS": rss, "AIC": aic, "p": 4}


def dm26_judge(x, y):
    """D-M2-6 双测。返回全数值 + 排零落点。"""
    mp = fit_power(x, y)
    mh = fit_high(x, y)
    daic = mp["AIC"] - mh["AIC"]
    t1_aic = bool(daic >= DAIC_LINE)
    t1_col = bool(abs(mh["A"]) <= abs(mp["A"]) / COLLAPSE_HIGH)
    t1 = bool(t1_aic and t1_col)
    idx = np.argsort(x)[:3]                          # H3 半窗:3 个最小 x
    mhalf = fit_power(x[idx], y[idx])
    t2 = bool(abs(mhalf["A"]) <= abs(mp["A"]) / COLLAPSE_HALF)
    return {
        "power_full": mp,
        "high_order": mh,
        "T1_dAIC_power_minus_high": float(daic),
        "T1_aic_supported": t1_aic,
        "T1_collapse_ratio": float(abs(mp["A"]) / max(abs(mh["A"]), 1e-300)),
        "T1_pollution": t1,
        "half_window_xs": [float(v) for v in x[idx]],
        "A_half": float(mhalf["A"]),
        "alpha_half": float(mhalf["alpha"]),
        "T2_half_ratio": float(abs(mhalf["A"]) / max(abs(mp["A"]), 1e-300)),
        "T2_pollution": t2,
        "both_pollution": bool(t1 and t2),
        "zero_exclusion": "PASS(A 与 0 一致)" if (t1 and t2)
                          else "FAIL(排零维持)",
    }


def main():
    t0 = time.time()
    xs = np.array([2.0 * math.pi / L for L in LS])
    out = {
        "register": "v2m2_dm26_rejudge",
        "authority": "docsv2/v2-裁定-M2轮2三裁-2026-07-27.md 裁定二",
        "backend": "numpy fp64",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frozen_protocol": {
            "T1": "全模型重拟合 A'+B'x^α+C'x^(α+2)(α 同网格重扫);"
                  "ΔAIC=AIC_power−AIC_high≥2 且 |A'|≤|A|/5 → 判截断污染",
            "T2": "半窗 = 去最大 x 点(4→3 点,窗×2/3;x≤x_max/2 仅 2 点欠定"
                  "不可执行),幂律全网格重拟合;|A_half|≤|A|/2 → 判截断污染",
            "combined": "两测同判污染 ⇔ σ-ii 排零 PASS;任一不判 → FAIL 不通融",
            "implementation_selection": "H1(2点/冻结幂律α)控制A无牙弃;"
                                        "H2(2点/冻结高阶α)控制B误塌缩弃;"
                                        "H3(3点/全重拟合)唯一幸存,冻结",
            "alpha_grid": "0.05..4.00 step 0.01 (R37 逐字)",
            "daic_line": DAIC_LINE, "collapse_high": COLLAPSE_HIGH,
            "collapse_half": COLLAPSE_HALF,
        },
    }

    # ---- 第一步:双控制(口径的牙口测试) ---------------------------------
    ctrl_rows, teeth = [], True
    for name, fam, A0, al, C, D in CONTROLS:
        y = A0 + B_SYN * xs ** al + C * xs ** (al + 2) + D * xs ** (al + 4)
        j = dm26_judge(xs, y)
        want = "PASS" if fam == "A" else "FAIL"
        got = "PASS" if j["both_pollution"] else "FAIL"
        ok = bool(got == want)
        teeth = teeth and ok
        ctrl_rows.append({
            "name": name, "family": fam,
            "truth": {"A0": A0, "B": B_SYN, "alpha": al, "C": C, "D": D},
            "A_fit_full": j["power_full"]["A"],
            "alpha_fit_full": j["power_full"]["alpha"],
            "T1_dAIC": j["T1_dAIC_power_minus_high"],
            "T1_A_high": j["high_order"]["A"],
            "T1_collapse_ratio": j["T1_collapse_ratio"],
            "T1_pollution": j["T1_pollution"],
            "A_half": j["A_half"],
            "T2_half_ratio": j["T2_half_ratio"],
            "T2_pollution": j["T2_pollution"],
            "zero_exclusion_got": got, "zero_exclusion_want": want,
            "ok": ok,
        })
        print(f"[ctrl {name}/{fam}] dAIC={j['T1_dAIC_power_minus_high']:.1f} "
              f"col={j['T1_collapse_ratio']:.3g} "
              f"r_half={j['T2_half_ratio']:.2f} -> {got} (want {want}) "
              f"{'OK' if ok else 'BROKEN'}")
    out["double_control"] = {"rows": ctrl_rows, "all_ok": bool(teeth),
                             "verdict": "口径有牙" if teeth else "口径回炉"}
    _write(out)                                       # 增量写盘 1
    if not teeth:
        out["status"] = "CALIBRE-REJECTED-HALT(不做重判,报车道A)"
        _write(out)
        print("双控制失守 → 口径回炉,停手。")
        return

    # ---- 第二步:G6 σ-ii 重判(轮 2 原始 ray 数据,旧 JSON 只读) ---------
    with open(ROUND2_JSON, "r") as f:
        r2 = json.load(f)
    sig = r2["m2_gates"]["M2-G6"]["sigma_branch_ii_sourced"]
    ys = np.array([sig["y_per_L"][str(L)] for L in LS], dtype=np.float64)
    j = dm26_judge(xs, ys)
    # 与轮 2 冻结拟合读数一致性核对(同数据同协议应逐位复现)
    repro = {
        "A_round2": sig["A"], "A_here": j["power_full"]["A"],
        "alpha_round2": sig["alpha"], "alpha_here": j["power_full"]["alpha"],
        "match": bool(abs(sig["A"] - j["power_full"]["A"]) <= 1e-12
                      and abs(sig["alpha"] - j["power_full"]["alpha"]) <= 1e-9),
    }
    sigma_ii_pass = j["both_pollution"]
    # σ-ii 其余子件(轮 2 实测,判据零回改):ΔAIC 决定性 + α>=1
    other = {"dAIC_const_minus_power_round2": sig["dAIC_const_minus_power"],
             "decisive_ge2": bool(abs(sig["dAIC_const_minus_power"]) >= 2.0),
             "alpha_ge1": bool(sig["alpha"] >= 1.0)}
    g6_pass = bool(sigma_ii_pass and other["decisive_ge2"]
                   and other["alpha_ge1"])
    out["rejudge"] = {
        "source": "data/results/v2m2_coupled_loop.json M2-G6 "
                  "sigma_branch_ii_sourced.y_per_L(只读)",
        "xs_2pi_over_L": [float(v) for v in xs],
        "ys": [float(v) for v in ys],
        "round2_fit_reproduction": repro,
        "dm26": j,
        "sigma_ii_other_subgates_round2": other,
        "sigma_ii_verdict": "PASS" if sigma_ii_pass else "FAIL",
        "g6_verdict": "PASS" if g6_pass else "FAIL",
        "g6_basis": "σ-i PASS(6.0e-13)、ρ 全中、b_layer≤1e-12、层间引理 "
                    "Fraction 证书 PASS(轮 2 已过,零回改)+ 本重判 σ-ii",
    }
    out["status"] = ("REJUDGE-PASS" if g6_pass else
                     "REJUDGE-FAIL-HALT(报车道A)")
    out["total_seconds"] = round(time.time() - t0, 3)
    with open(os.path.abspath(__file__), "rb") as f:
        out["source_sha256"] = hashlib.sha256(f.read()).hexdigest()
    _write(out)
    print(f"[rejudge] T1: dAIC={j['T1_dAIC_power_minus_high']:.2f} "
          f"A'={j['high_order']['A']:.3e} col={j['T1_collapse_ratio']:.1f} "
          f"pollution={j['T1_pollution']}")
    print(f"[rejudge] T2: A_half={j['A_half']:.3e} "
          f"ratio={j['T2_half_ratio']:.3f} pollution={j['T2_pollution']}")
    print(f"σ-ii: {out['rejudge']['sigma_ii_verdict']}  →  "
          f"M2-G6: {out['rejudge']['g6_verdict']}")


def _write(out):
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
