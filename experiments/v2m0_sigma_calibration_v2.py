"""V2M0 -- SIGMA CALIBRATION PIECE, RECTIFIED (M0' 整改令 5;lane B, 2026-07-26).

AUTHORITY (判据预注册,运行后不回改):
  docsv2/v2-复核-车道A-M0仪器迁移-2026-07-26.md §三(判决实验)§四整改令 1/5;
  docsv2/v2-任务书-M0-仪器迁移.md §5(原件框架);v1 件 = v2m0_sigma_calibration.py
  (旧口径,保留不覆盖)。

WHY REDONE: 复核判决(环境无关)——旧件主判 y = resid_max 是 ±ω 精确简并子空间
LAPACK 任意基上的逐模统计,**不是观测量**(随机酉旋转下漂移:0.276→0.263-0.313);
旧件 96³ 结论("三方向排零、面斜小底了结 1.95σ")建立在非观测量上,不能成立,
整件在不变量口径下重做。不变量 = 主角谱:max sinθ(主判,替代 resid_max)、
rms sinθ = frob/√m(辅报,resid_mean 的严格不变量)、frob 泄漏、≥0.05 主角计数。

PROTOCOL: R37 拟合协议原样保留(窗 = 分量 ≤π/4、剔 n=1、按比值去重、双模型
M0 常数 vs M1 幂律 A+B|k|^α(α 网格 0.05..4.00 步 0.01)、AIC 决定性 |ΔAIC|≥2、
方向分层不跨向平均;fit_constant/fit_power 为 R37 冻结代码对象直接调用)。
唯一变化 = y 值换不变量(整改令 1 明文)。格子系列 16/24/32/48/64/96(同旧件)。

D3 归档规则(写死,同旧件):
  * 幂律胜出 iff ΔAIC(const-power) >= +2(决定性);
  * 截距排零 iff |A| <= 2*sigma_A;
  * 档位:α>=1 clean-scaling;0<α<1 weak-scaling;幂律不决定 → undecided。
稳健性(车道A 口径,预先承诺):LOO(逐点剔除,报 A 范围与排零翻转)+
扩窗诊断(纳入被剔 n=1 点;仅诊断,永不判定)。
面斜"真常数底"模型无关上界(写死定义):|A| + 2*sigma_A(幂律拟合截距的
95% 量级上界;直接读数,不作模型选择)。

CERTIFICATES(缺一 ABORT):
  1. rc3ii 三冻结输入 + R37 脚本 sha256 逐位;
  2. RC1a faithfulness PASS;
  3. 16³ 判决数复现:三判据 k 不变量 vs 复核 §三表(max sinθ 1.0000/0.1948/0.1493,
     frob 1.035/0.304/0.211;容差 = 表列显示精度 sin 1e-4 / frob 1e-3)+
     基稳健自检(3 固定种子簇内酉旋转,漂移 <= 1e-12);
  4. 不变量 16-48 旧系列自洽:与 v2m0_selftest_v2.json row8 fits_invariant
     diff <= 1e-13(同机器同环境应逐位;证明这是同一台不变量机器);
  5. legacy 对照通道完好(宿主谱系诊断,非跨环境判据):旧口径 resid_max 16-48
     再推导 vs r37_results.json 逐位 diff=0.0——证明 legacy 对照列可信;
     此证书环境绑定(沙盒重跑本脚本时该列预期漂移,而这正是复核结论本身)。

PRE-WRITTEN BRANCHES(只填数,不改字):
  FACE-Z : 面斜幂律决定性胜出 且 |A|<=2σ_A → "旧件 1.95σ 面斜小底为基伪影,
           不变量口径下截距与 0 一致;悬案了结(机制 = 复核 §三)"。
  FACE-NZ: 否则 → "面斜小底在不变量口径下仍存,A=.. ± ..(如实入册,不预设)"。
  AXIAL-O1: 轴向若 max sinθ 为 O(1) 常数(常数胜出且 |A|>=0.05 排零失败)→
           "轴向 +ω 支含一个完全在 ker C 外的主角方向(sinθ=1):R29 轴向病灶的
           不变量形态——非标度问题,是精确 O(1) 遮挡;旧口径把它涂抹成 0.18-0.31
           的基依赖读数"。反之按实测入册。
两侧分支均只产出 v1 封存文档 §五 措辞更新建议(交车道A,只加不改史);
不改任何 v1 判定,不触发任何 v2 物理门(仪器校准,非物理门)。

RED LINES: 冻结件只读(hash 入册);fp64 numpy;单脚本 <<30 分钟;增量写盘;
不碰 git;不改 v1 文件;本头判据运行后不回改。旧件 JSON 保留不覆盖。

Run: RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m0_sigma_calibration_v2.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore")

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (ROOT, DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

from rulespace_v2 import sigma as SIG                        # noqa: E402
from rulespace_v2 import invariants as INV                   # noqa: E402
from rulespace_v2 import frozen as FZ                        # noqa: E402

import r37_residual_scaling_audit as R37                     # noqa: E402
import rc1a_tensor_index_scan as RC                          # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m0_sigma_calibration_v2.json")
OLD = os.path.join(ROOT, "data", "results", "v2m0_sigma_calibration.json")
R37_JSON = os.path.join(ROOT, "data", "results", "r37_results.json")
SELF2 = os.path.join(ROOT, "data", "results", "v2m0_selftest_v2.json")
STATE = os.path.join(ROOT, "data", "runtime", "v2m0_state.json")

R37_SCRIPT_SHA256 = "b847808c96ef8c64c72973d0e415db202497beb0236575d351a91c1fa9508df0"
LATTICES_V2 = [16, 24, 32, 48, 64, 96]
DAIC_DECISIVE = R37.DAIC_DECISIVE                            # 2.0
CONSISTENCY_TOL = 1e-13                                      # 证书 4(写死)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


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
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def fit_pair(x, y):
    m0 = R37.fit_constant(x, y)
    m1 = R37.fit_power(x, y)
    return m0, m1, m0["AIC"] - m1["AIC"]


def d3_archive(m0, m1, daic):
    power_decisive = bool(daic >= DAIC_DECISIVE)
    zero_ok = bool(abs(m1["A"]) <= 2.0 * m1["sigma_A"])
    if power_decisive and m1["alpha"] >= 1.0:
        tier = "clean-scaling (alpha>=1)"
    elif power_decisive and 0.0 < m1["alpha"] < 1.0:
        tier = "weak-scaling (0<alpha<1)"
    else:
        tier = "undecided (power law not decisive)"
    const_wins_decisive = bool(daic <= -DAIC_DECISIVE)
    o1_constant = bool(const_wins_decisive and abs(m0["A"]) >= R37.A_O1_THRESH)
    return {"power_decisive_dAIC_ge_2": power_decisive,
            "const_decisive_dAIC_le_-2": const_wins_decisive,
            "O1_constant": o1_constant,
            "dAIC_const_minus_power": daic,
            "intercept_zero_consistent_|A|<=2sigmaA": zero_ok,
            "d3_tier": ("O(1)-constant (no scaling)" if o1_constant else tier)}


def judge_direction_full(dname, pts, y_key):
    fitpts = [s for s in pts if s["in_fit"]]
    x = np.array([s["kabs"] for s in fitpts])
    y = np.array([s[y_key] for s in fitpts])
    m0, m1, daic = fit_pair(x, y)
    arch = d3_archive(m0, m1, daic)
    loo = []
    for i in range(len(x)):
        xi = np.delete(x, i)
        yi = np.delete(y, i)
        l0, l1, ldaic = fit_pair(xi, yi)
        loo.append({"dropped_kabs": float(x[i]), "A": l1["A"],
                    "sigma_A": l1["sigma_A"], "alpha": l1["alpha"],
                    "dAIC": ldaic,
                    "zero_consistent": bool(abs(l1["A"]) <= 2.0 * l1["sigma_A"])})
    wpts = [s for s in pts if s["in_fit_window"] and not s.get("off_band")]
    xw = np.array([s["kabs"] for s in wpts])
    yw = np.array([s[y_key] for s in wpts])
    w0, w1, wdaic = fit_pair(xw, yw)
    return {
        "direction": dname, "y_observable": y_key,
        "n_fit_points": len(fitpts),
        "fit_kabs": [float(v) for v in x],
        "fit_y": [float(v) for v in y],
        "constant_model": m0, "power_model": m1,
        "d3_archive": arch,
        "loo": {"rows": loo,
                "A_range": ([min(r["A"] for r in loo),
                             max(r["A"] for r in loo)] if loo else None),
                "zero_consistent_all": bool(all(r["zero_consistent"]
                                                for r in loo)),
                "zero_flips": "%d/%d" % (sum(1 for r in loo
                                             if not r["zero_consistent"]),
                                         len(loo))},
        "widened_window_diagnostic": {
            "note": "纳入被剔 n=1 点;窗规则不变,仅诊断,永不判定",
            "n_points": len(wpts), "power": w1,
            "dAIC_const_minus_power": wdaic,
            "zero_consistent": bool(abs(w1["A"]) <= 2.0 * w1["sigma_A"])},
    }


def main():
    t0 = time.time()
    payload = {
        "register": ("V2M0 sigma calibration RECTIFIED: 16³-96³ 不变量口径标度审计"
                     "(整改令 5;仪器校准,非物理门)"),
        "status": "RUNNING", "backend": "numpy", "fp": "fp64",
        "authority": ["docsv2/v2-复核-车道A-M0仪器迁移-2026-07-26.md §三/§四",
                      "docsv2/v2-任务书-M0-仪器迁移.md §5"],
        "environment": INV.environment_record(),
        "caliber": {"primary_y": "max_sin_theta (span(B₊) vs ker C 主角谱最大值)",
                    "secondary_y": "rms_sin = frob/sqrt(m)",
                    "legacy_y": "resid_max/resid_mean(基依赖,仅对照)",
                    "protocol": "R37 拟合协议原样(冻结代码对象);唯一变化 = y 值"},
        "lattices": LATTICES_V2,
        "d3_rules": {"power_decisive": "dAIC(const-power) >= 2",
                     "zero_exclusion": "|A| <= 2*sigma_A",
                     "tiers": "alpha>=1 clean; 0<alpha<1 weak; O(1)-constant 另档",
                     "model_free_floor_bound": "|A| + 2*sigma_A(幂律截距 95% 上界)"},
        "red_lines": ("仪器校准,非物理门;两分支均只产出封存 §五 措辞建议"
                      "(交车道A,只加不改史);无 v1 判定更改;判据运行后不回改"),
    }
    write_json(payload)
    print("V2M0 sigma calibration RECTIFIED: 不变量口径 16³-96³")
    print("=" * 74)

    # -- cert 1: hashes
    hashes = {f: sha256_file(os.path.join(DIR, f)) for f in R37.RC3II_HASHES}
    ok1 = hashes == R37.RC3II_HASHES
    h37 = sha256_file(os.path.join(DIR, "r37_residual_scaling_audit.py"))
    ok2 = h37 == R37_SCRIPT_SHA256
    payload["frozen_inputs_sha256"] = dict(hashes,
                                           **{"r37_residual_scaling_audit.py": h37})
    payload["frozen_hash_match"] = {"rc3ii_inputs": bool(ok1),
                                    "r37_script": bool(ok2)}
    print("[cert1] frozen hashes: %s" % ("MATCH" if (ok1 and ok2) else "MISMATCH"))
    write_json(payload)
    if not (ok1 and ok2):
        payload["status"] = "ABORT-frozen-hash-mismatch"
        write_json(payload)
        return

    # -- cert 2: faithfulness
    cert = RC.faithfulness_certificate()
    payload["faithfulness_certificate"] = cert
    print("[cert2] RC1a faithfulness: %s" % ("PASS" if cert["PASS"] else "FAIL"))
    write_json(payload)
    if not cert["PASS"]:
        payload["status"] = "ABORT-faithfulness-failed"
        write_json(payload)
        return

    # -- cert 3: 判决数复现 + 基稳健
    calib_inv = SIG.calibration_16cube_invariant()
    payload["judgement_reproduction"] = calib_inv
    ok3 = calib_inv["reproduces_review_judgement"]
    print("[cert3] 16³ 判决数复现(复核 §三)+ 基稳健: %s"
          % ("PASS" if ok3 else "FAIL"))
    write_json(payload)
    if not ok3:
        payload["status"] = "ABORT-judgement-reproduction-failed"
        write_json(payload)
        return

    # -- cert 4: 不变量 16-48 与 selftest_v2 row8 自洽
    with open(SELF2, "r", encoding="utf-8") as fh:
        self2 = json.load(fh)
    row8fits = self2["control_matrix"]["row8_r37_calib"]["remeasured"][
        "fits_invariant"]
    fits_1648 = SIG.direction_fits_invariant()
    ok4, cons = True, {}
    for d, f in fits_1648.items():
        g = row8fits[d]
        dmax = max(abs(f["A"] - g["A"]), abs(f["alpha"] - g["alpha"]),
                   abs(f["dAIC_const_minus_power"] - g["dAIC"]))
        cons[d] = dmax
        ok4 = ok4 and dmax <= CONSISTENCY_TOL
    payload["invariant_1648_consistency_vs_selftest_v2"] = {
        "diff": cons, "tol": CONSISTENCY_TOL, "ok": bool(ok4)}
    print("[cert4] 不变量 16-48 vs selftest_v2 row8 自洽: %s (max %.1e)"
          % ("PASS" if ok4 else "FAIL", max(cons.values())))
    write_json(payload)
    if not ok4:
        payload["status"] = "ABORT-invariant-consistency-failed"
        write_json(payload)
        return

    # -- cert 5: legacy 对照通道(宿主谱系,环境绑定诊断)
    with open(R37_JSON, "r", encoding="utf-8") as fh:
        r37res = json.load(fh)
    old_fits_1648 = {J["direction"]: J for J in r37res["direction_fits"]}
    ok5, rederive = True, {}
    for dname, dvec in R37.DIRS.items():
        pts = SIG.collect_direction_invariant(dname, dvec, list(R37.LATTICES))
        fitpts = [s for s in pts if s["in_fit"]]
        x = np.array([s["kabs"] for s in fitpts])
        y = np.array([s["legacy_resid_max"] for s in fitpts])
        m0, m1, daic = fit_pair(x, y)
        J = old_fits_1648[dname]
        dmax = max(
            float(np.max(np.abs(x - np.array(J["fit_kabs"])))),
            float(np.max(np.abs(y - np.array(J["fit_resid_max"])))),
            abs(m1["A"] - J["power_model"]["A"]),
            abs(m1["alpha"] - J["power_model"]["alpha"]),
            abs(daic - J["dAIC_const_minus_power"]))
        rederive[dname] = dmax
        ok5 = ok5 and dmax == 0.0
    payload["legacy_rederivation_host_lineage"] = {
        "diff": rederive, "ok_bit_for_bit": bool(ok5),
        "environment_bound": True,
        "note": ("legacy y=resid_max 对照通道 vs r37_results.json 逐位;宿主谱系"
                 "证书——沙盒重跑时此列预期漂移(复核 §三:非观测量),不变量列"
                 "才是跨环境判据")}
    print("[cert5] legacy 对照通道 16-48 vs r37_results 逐位: %s"
          % ("BIT-FOR-BIT" if ok5 else "MISMATCH"))
    write_json(payload)
    if not ok5:
        payload["status"] = "ABORT-legacy-channel-mismatch"
        write_json(payload)
        return

    # -- 测量:三方向,16-96,不变量 + legacy 并列
    data = {}
    for dname, dvec in R37.DIRS.items():
        print("[scan] %s ray (lattices %s) ..." % (dname, LATTICES_V2))
        data[dname] = SIG.collect_direction_invariant(dname, dvec, LATTICES_V2)
    payload["ray_data"] = data
    write_json(payload)

    # -- 逐格最小 |k| 原始读数(必报)
    min_k_raw = {}
    for dname, pts in data.items():
        rows = {}
        for L in LATTICES_V2:
            s = next(p for p in pts if [L, 1] in p["provenance"])
            rows["L=%d" % L] = {
                "kabs": s["kabs"], "max_sin_theta": s.get("max_sin_theta"),
                "frob_leak": s.get("frob_leak"), "rms_sin": s.get("rms_sin"),
                "n_ge_thresh": s.get("n_ge_thresh"),
                "legacy_resid_max": s.get("legacy_resid_max")}
        min_k_raw[dname] = rows
    payload["min_k_raw_readings"] = min_k_raw
    write_json(payload)
    print("[raw] 最小 |k| 读数 (max sinθ):")
    for dname, rows in min_k_raw.items():
        print("    %s: %s" % (dname, "  ".join(
            "%s %.4f" % (Lk, v["max_sin_theta"]) for Lk, v in rows.items())))

    # -- 基稳健性抽检:每方向取全部拟合合格点,3 种子酉旋转漂移
    rob_rows, worst_drift = {}, 0.0
    for dname, dvec in R37.DIRS.items():
        drs = []
        for s in data[dname]:
            if not s["in_fit"]:
                continue
            k = s["comp"] * np.array(dvec, float)
            rob = INV.plus_branch_basis_robustness(k, R37.C0)
            drs.append({"kabs": s["kabs"], "max_drift": rob["max_drift"]})
            worst_drift = max(worst_drift, rob["max_drift"])
        rob_rows[dname] = drs
    rob_ok = bool(worst_drift <= INV.DRIFT_TOL)
    payload["basis_robustness_fit_set"] = {
        "per_direction": rob_rows, "worst_drift": worst_drift,
        "tol": INV.DRIFT_TOL, "pass": rob_ok}
    print("[robust] 拟合集全点 3 种子酉旋转: worst drift %.1e -> %s"
          % (worst_drift, "PASS" if rob_ok else "FAIL"))
    write_json(payload)
    if not rob_ok:
        payload["status"] = "ABORT-basis-robustness-failed"
        write_json(payload)
        return

    # -- 拟合(不变量主判 + rms 辅报)
    judges = [judge_direction_full(d, pts, "max_sin_theta")
              for d, pts in data.items()]
    judges_rms = [judge_direction_full(d, pts, "rms_sin")
                  for d, pts in data.items()]
    payload["direction_fits_invariant"] = judges
    payload["direction_fits_rms_secondary"] = judges_rms
    write_json(payload)

    # -- 新旧对照(旧件 16-96 resid_max + R37 16-48)
    with open(OLD, "r", encoding="utf-8") as fh:
        oldres = json.load(fh)
    old_96 = {J["direction"]: J for J in oldres["direction_fits_new"]}
    compare = {}
    for J in judges:
        d = J["direction"]
        Jo48 = old_fits_1648[d]
        Jo96 = old_96[d]
        m1 = J["power_model"]
        compare[d] = {
            "legacy_16_48_resid_max": {
                "A": Jo48["power_model"]["A"],
                "sigma_A": Jo48["power_model"]["sigma_A"],
                "alpha": Jo48["power_model"]["alpha"],
                "dAIC": Jo48["dAIC_const_minus_power"],
                "note": "R37 冻结(基依赖旧口径)"},
            "legacy_16_96_resid_max": {
                "A": Jo96["power_model"]["A"],
                "sigma_A": Jo96["power_model"]["sigma_A"],
                "alpha": Jo96["power_model"]["alpha"],
                "dAIC": Jo96["d3_archive"]["dAIC_const_minus_power"],
                "zero_consistent":
                    Jo96["d3_archive"]["intercept_zero_consistent_|A|<=2sigmaA"],
                "note": "旧件(基依赖旧口径;其排零结论经复核不能成立)"},
            "invariant_16_96_max_sin": {
                "m": J["n_fit_points"], "A": m1["A"], "sigma_A": m1["sigma_A"],
                "B": m1["B"], "alpha": m1["alpha"],
                "sigma_alpha": m1["sigma_alpha"],
                "constant_A": J["constant_model"]["A"],
                "dAIC": J["d3_archive"]["dAIC_const_minus_power"]},
            "d3_archive_invariant": J["d3_archive"],
            "loo_invariant": {"A_range": J["loo"]["A_range"],
                              "zero_flips": J["loo"]["zero_flips"]},
            "model_free_floor_bound_|A|+2sigmaA":
                abs(m1["A"]) + 2.0 * m1["sigma_A"],
        }
    payload["old_vs_new"] = compare
    write_json(payload)

    for J in judges:
        m1, m0, a = J["power_model"], J["constant_model"], J["d3_archive"]
        print("[fit] %-14s m=%d  A=%.5f±%.5f  α=%.2f  ΔAIC=%+.1f  排零=%s  %s"
              % (J["direction"], J["n_fit_points"], m1["A"], m1["sigma_A"],
                 m1["alpha"], a["dAIC_const_minus_power"],
                 a["intercept_zero_consistent_|A|<=2sigmaA"], a["d3_tier"]))
        print("      const A=%.5f±%.5f | LOO A∈[%s] 排零翻转 %s | 扩窗排零 %s"
              % (m0["A"], m0["sigma_A"],
                 ("%.5f, %.5f" % tuple(J["loo"]["A_range"])
                  if J["loo"]["A_range"] else "-"),
                 J["loo"]["zero_flips"],
                 J["widened_window_diagnostic"]["zero_consistent"]))

    # -- 预写分支(只填数)
    face = next(J for J in judges if J["direction"] == "face-diagonal")
    axial = next(J for J in judges if J["direction"] == "axial")
    fa = face["d3_archive"]
    face_zero = bool(fa["power_decisive_dAIC_ge_2"]
                     and fa["intercept_zero_consistent_|A|<=2sigmaA"])
    axial_o1 = bool(fa is not None and axial["d3_archive"]["O1_constant"])
    if face_zero:
        face_branch = "FACE-Z"
        face_txt = ("面斜:不变量口径(y=max sinθ)下幂律决定性胜出且截距与 0 一致"
                    "(A=%.5f±%.5f);旧件 1.95σ 面斜小底为**基伪影**(机制=复核 §三:"
                    "resid_max 非观测量),悬案了结。"
                    % (face["power_model"]["A"], face["power_model"]["sigma_A"]))
    else:
        face_branch = "FACE-NZ"
        face_txt = ("面斜:不变量口径下小底仍存,A=%.5f±%.5f(ΔAIC=%.1f,排零=%s);"
                    "如实入册,不预设。"
                    % (face["power_model"]["A"], face["power_model"]["sigma_A"],
                       fa["dAIC_const_minus_power"],
                       fa["intercept_zero_consistent_|A|<=2sigmaA"]))
    if axial_o1:
        axial_txt = ("轴向:max sinθ ≡ %.4f——+ω 支含一个完全在 ker C 外的主角方向"
                     "(sinθ=1),即 R29 轴向病灶的不变量形态:非标度问题,是精确 "
                     "O(1) 遮挡;旧口径 resid_max 把它涂抹成 0.18-0.31 的基依赖读数"
                     "(旧件轴向 A=0.003 '排零' 是同一伪影的另一面)。"
                     % axial["constant_model"]["A"])
    else:
        axial_txt = ("轴向:不变量口径 A=%.5f±%.5f, α=%.2f, ΔAIC=%.1f(按实测入册)。"
                     % (axial["power_model"]["A"], axial["power_model"]["sigma_A"],
                        axial["power_model"]["alpha"],
                        axial["d3_archive"]["dAIC_const_minus_power"]))
    payload["calibration_branch"] = face_branch
    payload["axial_O1_invariant_obstruction"] = axial_o1
    payload["face_small_floor_verdict_invariant"] = face_txt
    payload["axial_verdict_invariant"] = axial_txt
    payload["wording_update_suggestion"] = (
        "建议(交车道A,只加不改史):封存文档 §五 标度证据节措辞按不变量口径更新——"
        + face_txt + " " + axial_txt +
        " 体对角按 d3_archive 如实并注。旧件(resid_max 口径)结论整体废止为注记;"
        "封存主句(死于计数+稳定性死锁,非残差本身)不受影响(其三重支撑均为基不变量)。")
    payload["nature_reminder"] = ("instrument calibration; NOT a physics gate; "
                                  "no v1 verdict changed; no v2 gate triggered")
    write_json(payload)

    # -- state 并入(dashboard 数据源;整改令 6)
    try:
        with open(STATE, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except Exception:
        state = {}
    old_block = state.get("sigma_calibration_64")
    dirblock = {}
    for J in judges:
        d = J["direction"]
        m1 = J["power_model"]
        cmpd = compare[d]
        dirblock[d] = {
            "new_16_96": {"A": m1["A"], "sigma_A": m1["sigma_A"],
                          "alpha": m1["alpha"],
                          "dAIC": J["d3_archive"]["dAIC_const_minus_power"]},
            "old_16_48": cmpd["legacy_16_48_resid_max"],
            "legacy_16_96_resid_max": cmpd["legacy_16_96_resid_max"],
            "zero_excluded_|A|<=2sigmaA":
                J["d3_archive"]["intercept_zero_consistent_|A|<=2sigmaA"],
            "zero_sigma_level": (round(abs(m1["A"]) / m1["sigma_A"], 2)
                                 if m1["sigma_A"] > 0 else None),
            "d3_tier": J["d3_archive"]["d3_tier"],
            "loo_zero_flips": J["loo"]["zero_flips"]}
    state["sigma_calibration_64"] = {
        "status": "DONE",
        "register": ("σ 机器校准件整改版(16³-96³ 不变量口径;仪器校准,非物理门;"
                     "整改令 5)"),
        "caliber": "invariant: y = max sinθ(主判)/ rms sinθ(辅报)",
        "calibration_branch": face_branch,
        "axial_O1_invariant_obstruction": axial_o1,
        "face_small_floor": {
            "verdict": face_txt,
            "zero_consistent": face_zero,
            "model_free_upper_bound":
                compare["face-diagonal"]["model_free_floor_bound_|A|+2sigmaA"]},
        "axial_note": axial_txt,
        "backend": "numpy fp64",
        "lattices": LATTICES_V2,
        "direction_fits": dirblock,
        "results_file": "data/results/v2m0_sigma_calibration_v2.json",
        "old_caliber_block_legacy": old_block,
        "old_caliber_note": ("old_caliber_block_legacy = 旧口径(resid_max,基依赖)"
                             "校准摘要,经复核其排零/小底结论不能成立;保留为注记"),
    }
    state["generated_utc"] = payload.get("started_utc",
                                         state.get("generated_utc"))
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, default=_jd)
    payload["state_merged"] = os.path.relpath(STATE, ROOT)

    payload["peak_rss_mb"] = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss / 1e6
    payload["status"] = "DONE"
    payload["source_sha256"] = sha256_file(__file__)
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)

    print("=" * 74)
    print("BRANCH = %s   axial O(1) invariant obstruction = %s"
          % (face_branch, axial_o1))
    print(face_txt)
    print(axial_txt)
    print("source  sha256 = %s" % payload["source_sha256"])
    print("results sha256 = %s" % jsha)
    print("total %.1fs, peak RSS %.0f MB" % (time.time() - t0,
                                             payload["peak_rss_mb"]))


if __name__ == "__main__":
    main()
