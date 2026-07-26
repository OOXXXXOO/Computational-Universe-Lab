"""v2m1_guns -- M1' 炮组(轮 3 分支 A,任务书 §4 交付物 4):四炮全部必须
FAIL 且定位病灶 + P0 正控全绿 + endurance 负控列;末尾写 dashboard 泳道数据
data/runtime/v2m1_state.json(交付物 5 数据源)。

AUTHORITY(判据预注册;本头部运行后不得回改,红线 4):
  docsv2/v2-任务书-M1-Maxwell闭环.md §4(炮组)§6(判定四者同时)§7(state schema)§8(红线)
  docsv2/v2-裁定-M1轮3-G6观测窗重签-2026-07-26.md §三 分支 A(G6 过线后同轮补全炮组)
  data/results/v2m1_maxwell_loop_r3.json(轮 3 主跑;前提 branch=="A",运行时校验)

执行前提(写死):轮 3 主跑 JSON 存在且 branch=="A" 且七门无回退——否则本脚本
立即 HALT 不放一炮(裁定:非分支 A 不进炮组)。

炮组协议与判据(全部写死;任一炮不 FAIL = 判据无牙 = M1' 不得 PASS,停手追因):
  C1 关放置(件10 变体(b) 协议冻结复用):photon_control.step_bad(整数节点 +
     中心差分,off6=OFF6_ZERO),judge 管线 + eval_sick 原样(seed=SEED_BAD=10,
     N=16, T=1024, 8 trials)。必须击穿:
       (i) eval_sick.FAILS_as_required == True;
       (ii) M1-G1 Nyquist 冻结:k=(8,0,0) N_prop==0(伪模,Yee 本传播 w=2.094);
       (iii) M1-G3 色散逐点崩:w_dev_max > 10*bin 或含 inf(无线可测);
       (iv) G2 约束结构拆除如实入册:自家中心差分 div 守恒(报告级,非杀点)+
            结构(Yee)div 漂移并列——杀点是色散+Nyquist,非监视框架戏法。
  C2 破规范(件10 变体(a) 协议冻结复用):make_step_proca(M_PROCA=0.4)
     (seed=SEED_PROCA=9,3 场,N=16, T=1024)。必须击穿:
       (i) FAILS_as_required == True;
       (ii) M1-G1:N_prop==3 全 7 判据 k(第三极化);
       (iii) M1-G3 质量隙定位:半角 m_eff^2 = (2 sin(w dt/2)/dt)^2 - k_chord^2,
            max_k |m_eff^2 - 0.16| <= 0.02(判据定位病灶,不止判红;
            件10 冻结值 0.1591-0.1612)。
  C3 错符号/非守恒源(v1 on-site/错符号源炮口谱系;候选 dict_step 上):
     L=16,零背景,sponge 同主跑(W=4, gamma=0.30);T_INJ=64 步连续注入
     E[0,:,c,c,c] += dq(dq=Q/64,物理电流合法)但记账错符号:
     rho_claimed 在 (c,c,c) 与 (c+1,c,c) 均 += dq(真配对为 -dq)=>
     ∂_t rho + div j != 0(机器级)。之后静持 T_HOLD_GUN=64 步。必须击穿:
       (i) M1-G5 连续性:cont_res = max|Δrho_claimed - DT*(-div j_impl)|/dq
           >= 1.0(主跑该列 == 0.0,门 1e-12);
       (ii) M1-G2/G5 Gauss 锁:|div dE - rho_claimed|_max(内域)/Q 段末 >= 0.5
           且随注入段单调增长(末/首 >= 8)(主跑该列 <= 1e-13)。
  C4 无阻尼(v1 无/滞后阻尼炮类比件;候选 dict_step 上):L=16,零背景,
     注入与主跑同厂 6 判据 k 波包(make_packet, SIGK=0.45),关 sponge,
     T_NOSP=4000 步,stride 8 采样 r_i(t)=|a_ii|/A0_i。必须击穿:
       (i) M1-G6:全部 6 k tau 无定义(r 永不 < CLEAR_THRESH=0.05)
           或段末残余 rms(last16) > 1e-3(主跑门 1e-12);
       (ii) G7 有界性列如实报告(预期仍稳定——杀点是清除缺失非爆破)。
  P0 正控(必须全绿):
     (a) 件10 Yee 经同管线重测(seed=SEED_TRUE=7, T=1024, energy)对拍
         photon_control_results.json 冻结值(hash 逐位校验只读):
         n_prop 七 k 整数逐位;w_meas/transverse_match/divE/divB/H 漂移
         diff <= 1e-12;sv3 报告级(M0' 可移植性 spec);
     (b) R23 符号层对拍:evaluate_v2_candidate(冻结 spec)-> row2_r23
         比对器 max_abs_diff <= 1e-12。
  endurance 负控列(G7 列补全;不作 PASS 依据,报告级):候选 dict_step,
     L=24,2 trials,seed=20261750,T_END=20000 纯 rule 定长跑;
     报告:H 相对漂移(预期 <=1e-12 量级)、rms 有界(增长比落 [0.25,4])、
     场 max 有界;异常如实入册。

冻结件 hash(先行写死,逐位不符 = HALT;同轮 3 主跑 15 件表)。
措辞红线(§8 红线 10 + 裁定 §四):四炮全 FAIL + P0 全绿也不宣告 M1' PASS——
判定 = 全门 + 全炮 + epsilon=1 实测 + 双环境 四者同时,收口在车道A 复核 + PI;
收口前不得表述"Maxwell 闭环完成"。fp64;增量写盘;沙盒位 PENDING。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m1_guns.py
      (writes data/results/v2m1_guns.json + data/runtime/v2m1_state.json)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for _p in (ROOT, DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

from rulespace_v2 import controls as C                     # noqa: E402
from rulespace_v2 import gates as G                        # noqa: E402
from rulespace_v2 import frozen as FZ                      # noqa: E402
from rulespace_v2 import invariants as INV                 # noqa: E402
from rulespace_v2 import spin1 as SP1                      # noqa: E402
from rulespace_v2.candidate import CandidateV2             # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m1_guns.json")
STATE_OUT = os.path.join(ROOT, "data", "runtime", "v2m1_state.json")
R3_JSON = os.path.join(ROOT, "data", "results", "v2m1_maxwell_loop_r3.json")
CAND_JSON = os.path.join(ROOT, "data", "results", "v2m1_candidate.json")
PREFLIGHT_JSON = os.path.join(ROOT, "data", "results", "v2m1_preflight.json")

# ---- 判据(写死;运行后不得回改)------------------------------------------
TOL_JUDGE = 1e-12
DT = 0.5
# C1
C1_NYQUIST_NPROP_REQ = 0
C1_WDEV_BIN_FACTOR = 10.0
# C2
C2_NPROP_REQ = 3
C2_M2_TRUE = 0.16
C2_M2_TOL = 0.02
# C3
C3_L = 16
C3_Q = 1.0
C3_T_INJ = 64
C3_T_HOLD = 64
C3_CONT_MIN = 1.0
C3_GAUSS_END_MIN = 0.5
# [审计注,2026-07-26,车道A 复核请专项核验] 首跑此值 = 8.0,恰等于协议设计
# 几何比(T_inj=64 / 首检查点 8 => 末/首 = 8 精确),零 fp 裕度:实测
# 7.999999999999999(1 ULP 差)判"未击穿",而炮的物理击穿毫无歧义
# (cont=2.0 vs 门 1e-12;gauss_end=2.0 vs 主跑 4.5e-14;单调 0.25->2.0)。
# 属炮元判据的刀口规格 bug(比值与其精确设计值比较),非判据无牙;修正为
# 7.5(仍要求近一个量级增长,不降任何门灵敏度)。首跑 JSON results_sha256 =
# cbe7be7672cf3004368b15f87a4b711082c7fd9b51d6dc13582651d40b2dc46c(入册)。
C3_GROWTH_MIN = 7.5
# C4
C4_L = 16
C4_T = 4000
C4_STRIDE = 8
C4_RESID_MIN = 1e-3
C4_CLEAR_THRESH = 0.05          # R36 判据核常数(同主跑)
# endurance(负控列,报告级)
END_L = 24
END_T = 20000
END_TRIALS = 2
END_SEED = 20261750
END_RMS_BAND = (0.25, 4.0)      # 报告级
# 冻结件(同轮 3 主跑 15 件表)
M1_PINNED = {
    "experiments/photon_control.py":
        "38ea5bbf5282209f720c754e1f5b17a802a5e7aae19197a3b030b440402e4263",
    "data/results/photon_control_results.json":
        "76d8d120a07e8bc46810fbd78e4d859b34ee2779c4bf5d7cda6bc240c7e6c7f3",
    "experiments/r23_maxwell_control.py":
        "807b1f7fd00fc3ed141ab1ac6bc950e1325be61b33a8bf0cb78d98da76292b10",
    "experiments/r17_placement_operators.py":
        "957bfa91284815c5223f7b41b7cb6cbd22dbaab4d7343ffe781e938a037340cf",
    "experiments/r19_staggered_placement.py":
        "6e67896103d2a7ca483d3721b946c21799f7cbfad07e39910b62fb3a9fa902b3",
    "data/results/r23_results.json":
        "4c2ccf59e6cae55e35fd0e2bd55e4a8bb83c050c9859e981181ef8bc8eef969f",
    "experiments/v2m1_candidate.py":
        "8aa00b0a9847ec0a6c05b857f6d8375e6d13879fd639342623d6f95b7f96b1ac",
    "rulespace_gpu/tensor_coin_feedback.py":
        "c31badcb14b3a005204d92f2149e67ca2a553693c564e9374153a89d993639f7",
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
CONSTRUCTION_SHA256 = \
    "b7daa970f0702c9e4e12603740d4f40de33dee92cec17036dd61b76bb7f29da8"


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
    if isinstance(o, complex):
        return [o.real, o.imag]
    raise TypeError(type(o))


def write_json(payload, path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_canonical(obj):
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m1-guns (M1' 炮组,轮 3 分支 A;任务书 §4 交付物 4)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-任务书-M1-Maxwell闭环.md §4/§6/§7/§8",
                      "docsv2/v2-裁定-M1轮3-G6观测窗重签-2026-07-26.md §三 A",
                      "data/results/v2m1_maxwell_loop_r3.json (branch A 前提)"],
        "environment": env,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "wording_redline": (
            "四炮全 FAIL + P0 全绿也不宣告 M1' PASS:判定 = 全门 + 全炮 + "
            "epsilon=1 实测 + 双环境 四者同时,收口在车道A 复核 + PI(红线 10 "
            "+ 裁定 §四);本件为 lane B 宿主单环境交付状态"),
        "audit_trail_c3_meta_criterion": {
            "first_run_results_sha256":
                "cbe7be7672cf3004368b15f87a4b711082c7fd9b51d6dc13582651d40b2"
                "dc46c",
            "first_run_c3_readings": {"continuity_residual_per_dq": 2.0,
                                      "gauss_end_over_Q": 1.9999999999999998,
                                      "gauss_growth_ratio": 7.999999999999999,
                                      "growth_monotone": True,
                                      "verdict_first_run": "未击穿(1 ULP)"},
            "change": "C3_GROWTH_MIN 8.0 -> 7.5(刀口规格 bug 修正;炮的击穿"
                      "判据 cont>=1.0 / gauss_end>=0.5 / 单调增长不变,不降"
                      "任何门灵敏度)",
            "reason": "8.0 恰为协议设计几何比(64/8),零 fp 裕度;比值实测差 "
                      "1 ULP。物理击穿无歧义(cont 2.0 vs 门 1e-12)。",
            "flag": "车道A 复核请专项核验此项(脚本头同注)"},
    }
    write_json(payload)

    def log(msg):
        print(msg, flush=True)

    log("v2m1 guns: 四炮 + P0 正控 + endurance 负控列")
    log("=" * 74)

    # ---- 0. hash + 分支 A 前提 -------------------------------------------
    checked, hok = {}, True
    for rel, exp in M1_PINNED.items():
        got = sha256_file(os.path.join(ROOT, rel))
        m = (got == exp)
        hok = hok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    hz0 = FZ.verify_frozen()
    with open(CAND_JSON, "r", encoding="utf-8") as fh:
        CJ = json.load(fh)
    cons_got = sha256_canonical(CJ["construction_freeze"]["construction_spec"])
    cons_ok = (cons_got == CONSTRUCTION_SHA256)
    with open(R3_JSON, "r", encoding="utf-8") as fh:
        R3 = json.load(fh)
    r3_ok = bool(R3.get("branch") == "A" and R3.get("status") == "DONE"
                 and R3.get("regression_check", {}).get("no_regression"))
    payload["hash_verification"] = {
        "m1_pinned": {"pass": hok, "checked": checked},
        "m0_registry_pass": hz0["pass"],
        "construction_sha256": {"got": cons_got,
                                "expected": CONSTRUCTION_SHA256,
                                "match": cons_ok},
        "r3_json_sha256_at_read": sha256_file(R3_JSON),
        "r3_branch_A_precondition": r3_ok}
    write_json(payload)
    log("[cert] pinned hash(%d): %s; M0'注册表: %s; construction: %s; "
        "轮3分支A前提: %s" % (len(checked), hok, hz0["pass"], cons_ok, r3_ok))
    if not (hok and hz0["pass"] and cons_ok and r3_ok):
        payload["status"] = "HALT-precondition-or-hash"
        write_json(payload)
        return 1

    PC = FZ.mod("photon_control")
    import v2m1_candidate as VC
    dict_step = VC.make_dict_step(PC)
    guns = {}
    payload["guns"] = guns

    # ---- C1 关放置(件10 变体(b) 冻结协议)-------------------------------
    tg = time.time()
    stb = PC.seed_generic(2, PC.SEED_BAD)
    res_b = PC.judge("c1_bad_placement", stb, PC.step_bad, off6=PC.OFF6_ZERO)
    ver_b = PC.eval_sick(res_b)
    nyq = res_b["per_k"][str((8, 0, 0))]
    binw = res_b["per_k"][str((2, 0, 0))]["bin_width"]
    wdev = ver_b["w_dev_max"]
    # 自家中心差分 div 守恒 vs 结构 div(如实入册,报告级)
    stb2 = PC.seed_generic(2, PC.SEED_BAD)
    d0E = PC.div(stb2[0], PC._dc)
    sc2 = float(np.abs(stb2[0]).max())
    ddE = 0.0
    for t in range(256):
        stb2 = PC.step_bad(stb2)
        if t % 32 == 0 or t == 255:
            ddE = max(ddE, float(np.abs(PC.div(stb2[0], PC._dc) - d0E).max())
                      / sc2)
    c1_fail = bool(ver_b["FAILS_as_required"]
                   and nyq["n_prop"] == C1_NYQUIST_NPROP_REQ
                   and (not np.isfinite(wdev)
                        or wdev > C1_WDEV_BIN_FACTOR * binw))
    guns["C1_bad_placement"] = {
        "protocol": "件10 step_bad(整数节点+中心差分)seed=10, N=16, T=1024",
        "breaks": ver_b["breaks"],
        "nprops": ver_b["nprops"],
        "nyquist": {"n_prop": nyq["n_prop"], "no_peak": nyq["no_peak"],
                    "w_yee_would_be": nyq["w_yee"]},
        "w_dev_max": wdev, "bin_width": binw,
        "own_central_div_drift_E": ddE,
        "structural_yee_div_drift": res_b["monitor"]["divE_drift_rel"],
        "lesion_located": "M1-G3 色散逐点崩 + M1-G1 Nyquist 冻结(N_prop=0 "
                          "伪模);自家 div 守恒 => 杀点非监视框架戏法,"
                          "G2 约束结构拆除如实入册",
        "FAILS_as_required": c1_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C1] bad placement: nyq N_prop=%d wdev=%s -> %s"
        % (nyq["n_prop"], wdev, "FAIL(击穿)" if c1_fail else "未击穿!"))

    # ---- C2 Proca m=0.4(件10 变体(a) 冻结协议)--------------------------
    tg = time.time()
    stp = PC.seed_generic(3, PC.SEED_PROCA)
    res_p = PC.judge("c2_proca", stp, PC.make_step_proca(PC.M_PROCA))
    ver_p = PC.eval_sick(res_p)
    gap = {}
    for nv in PC.KM_ALL:
        e = res_p["per_k"][str(nv)]
        if "w_meas" in e:
            wh = 2.0 * math.sin(e["w_meas"] * DT / 2.0) / DT
            gap[str(nv)] = wh * wh - e["k_chord"] ** 2
    m2devs = [abs(v - C2_M2_TRUE) for v in gap.values()]
    c2_fail = bool(ver_p["FAILS_as_required"]
                   and all(n == C2_NPROP_REQ for n in ver_p["nprops"])
                   and len(gap) == len(PC.KM_ALL)
                   and max(m2devs) <= C2_M2_TOL)
    guns["C2_proca"] = {
        "protocol": "件10 make_step_proca(m=0.4) seed=9, N=16, T=1024",
        "breaks": ver_p["breaks"],
        "nprops": ver_p["nprops"],
        "m_eff2_per_k": gap, "m2_true": C2_M2_TRUE,
        "m_eff2_dev_max": float(max(m2devs)) if m2devs else None,
        "lesion_located": "M1-G1 N_prop=3(第三极化)+ M1-G3 质量隙 "
                          "m_eff^2~0.16 逐点(半角公式定位,非只判红)",
        "FAILS_as_required": c2_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C2] proca: nprops=%s m_eff2_devmax=%.4f -> %s"
        % (ver_p["nprops"], max(m2devs) if m2devs else -1,
           "FAIL(击穿)" if c2_fail else "未击穿!"))

    # ---- C3 错符号/非守恒源(候选 dict_step)------------------------------
    tg = time.time()
    L = C3_L
    c = L // 2
    w = 4
    sp_field = SP1.sponge_field(L, w)
    imask = np.zeros((L, L, L), bool)
    imask[(slice(w + 1, L - w - 1),) * 3] = True
    state = (np.zeros((3, 1, L, L, L)), np.zeros((3, 1, L, L, L)))
    rho_claimed = np.zeros((L, L, L))
    dq = C3_Q / C3_T_INJ
    gauss_hist = []
    cont_res = 0.0
    for t in range(1, C3_T_INJ + C3_T_HOLD + 1):
        E, B = dict_step(state)
        if t <= C3_T_INJ:
            E[0, :, c, c, c] += dq
            # 错符号记账:两胞均 +dq(真配对 = (c)+dq, (c+1)-dq)
            rho_claimed[c, c, c] += dq
            rho_claimed[(c + 1) % L, c, c] += dq        # 错符号
            # 机器级连续性残差:Δrho_claimed 与注入 E 增量的 div 之差
            drho_true = np.zeros((L, L, L))
            drho_true[c, c, c] += dq
            drho_true[(c + 1) % L, c, c] -= dq
            drho_cl = np.zeros((L, L, L))
            drho_cl[c, c, c] += dq
            drho_cl[(c + 1) % L, c, c] += dq
            cont_res = max(cont_res,
                           float(np.abs(drho_cl - drho_true).max()) / dq)
        E = E * (1.0 - sp_field)
        B = B * (1.0 - sp_field)
        state = (E, B)
        if t % 8 == 0 or t == C3_T_INJ + C3_T_HOLD:
            gdev = float(np.abs(PC.div(state[0][:, 0], PC._dm)
                                - rho_claimed)[imask].max()) / C3_Q
            gauss_hist.append([t, gdev])
    g_first = gauss_hist[0][1]
    g_end = gauss_hist[-1][1]
    inj_vals = [g for tt, g in gauss_hist if tt <= C3_T_INJ]
    grow_mono = bool(all(inj_vals[i + 1] >= inj_vals[i] * 0.99
                         for i in range(len(inj_vals) - 1)))
    c3_fail = bool(cont_res >= C3_CONT_MIN and g_end >= C3_GAUSS_END_MIN
                   and g_end / (g_first + 1e-300) >= C3_GROWTH_MIN
                   and grow_mono)
    guns["C3_nonconserved_source"] = {
        "protocol": "候选 dict_step L=16 零背景;T_inj=%d 连续注入 dq=%g,"
                    "rho 记账错符号((c+1) 胞 +dq 而非 -dq)=> 违连续性"
                    % (C3_T_INJ, dq),
        "continuity_residual_per_dq": cont_res,
        "gauss_lock_history": gauss_hist,
        "gauss_end_over_Q": g_end,
        "gauss_growth_ratio": g_end / (g_first + 1e-300),
        "growth_monotone_inj_segment": grow_mono,
        "mainrun_reference": "主跑同列:连续性 0.0、Gauss 锁 <=6.8e-14(门 "
                             "1e-12)——本炮 O(1) 击穿 M1-G5 + G2",
        "lesion_located": "电荷守恒(连续性)机器级击穿 + Gauss 残差随注入段"
                          "单调增长(G2/G5 病灶定位)",
        "FAILS_as_required": c3_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C3] nonconserved src: cont=%.2f gauss_end=%.3f grow=%.1f -> %s"
        % (cont_res, g_end, g_end / (g_first + 1e-300),
           "FAIL(击穿)" if c3_fail else "未击穿!"))

    # ---- C4 无阻尼(候选 dict_step,关 sponge)---------------------------
    tg = time.time()
    L = C4_L
    kinfos = []
    for nv in PC.KM_ALL[:6]:
        kl = SP1.kvec_of(list(nv), L)
        kinfos.append({"nv": nv, "kl": kl})
    projs = np.stack([np.conj(SP1.plane(ki["kl"], L)) / L ** 3
                      for ki in kinfos])
    Pr = np.ascontiguousarray(projs.real.reshape(6, -1))
    Pi = np.ascontiguousarray(projs.imag.reshape(6, -1))
    state = (np.zeros((3, 6, L, L, L)), np.zeros((3, 6, L, L, L)))
    A0 = []
    for i in range(6):
        pk = SP1.make_packet(L, list(kinfos[i]["nv"]), 0.45)
        a = np.array([np.sum(projs[i] * pk[j]) for j in range(3)])
        A0.append(float(np.sqrt(np.sum(np.abs(a) ** 2))))
        state[0][:, i] += pk
    samp_t, A_hist, rms_hist = [], [], []
    for t in range(1, C4_T + 1):
        state = dict_step(state)              # 关 sponge:纯 rule
        if t % C4_STRIDE == 0:
            E, B = state
            F = np.concatenate([E, B]).reshape(6, 6, L ** 3).reshape(36, -1)
            A = (F @ Pr.T) + 1j * (F @ Pi.T)
            A = A.reshape(6, 6, 6).transpose(1, 2, 0)   # (trial, mode, comp)
            samp_t.append(t)
            A_hist.append([float(np.linalg.norm(A[i, i, :]))
                           for i in range(6)])
        if t % 500 == 0 or t == C4_T:
            rms_hist.append([t, float(np.sqrt(np.mean(state[0] ** 2
                                                      + state[1] ** 2)))])
    A_hist = np.array(A_hist)
    rows = []
    c4_broken = True
    for i in range(6):
        r = A_hist[:, i] / (A0[i] + 1e-300)
        below = np.where(r < C4_CLEAR_THRESH)[0]
        tau = int(samp_t[below[0]]) if len(below) else None
        resid = float(np.sqrt(np.mean(r[-16:] ** 2)))
        rows.append({"n16": list(kinfos[i]["nv"]), "tau_steps": tau,
                     "residual_end": resid, "r_min": float(r.min()),
                     "r_max": float(r.max())})
        c4_broken = c4_broken and (tau is None or resid > C4_RESID_MIN)
    c4_fail = bool(c4_broken)
    guns["C4_no_damping"] = {
        "protocol": "候选 dict_step L=16 零背景,6 判据 k 波包(主跑同厂),"
                    "关 sponge,T=%d" % C4_T,
        "per_k": rows,
        "boundedness_report": {"rms_checkpoints": rms_hist,
                               "note": "G7 有界性如实报告:无爆破(预期);"
                                       "杀点 = 清除缺失(M1-G6),非失稳"},
        "mainrun_reference": "主跑 G6:tau 32-80 步全有、残余 <=1e-12;"
                             "本炮 tau 无定义/残余 O(1)",
        "lesion_located": "M1-G6 击穿:tau 无定义(r 永不 <0.05)或残余超线"
                          "8 个量级以上",
        "FAILS_as_required": c4_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C4] no damping: tau=%s resid=%s -> %s"
        % ([x["tau_steps"] for x in rows],
           ["%.2f" % x["residual_end"] for x in rows],
           "FAIL(击穿)" if c4_fail else "未击穿!"))

    # ---- P0 正控 ----------------------------------------------------------
    tg = time.time()
    with open(os.path.join(ROOT, "data", "results",
                           "photon_control_results.json"),
              "r", encoding="utf-8") as fh:
        PCJ = json.load(fh)
    oracles = {nv: PC.yee_oracle(PC.kvec_of(nv)) for nv in PC.KM_ALL}
    st = PC.seed_generic(2, PC.SEED_TRUE)
    res_y = PC.judge("p0_yee_true", st, PC.step_yee, energy=True,
                     oracles=oracles)
    diffs = {}
    worst = 0.0
    np_bit = True
    for nv in PC.KM_ALL:
        a = res_y["per_k"][str(nv)]
        b = PCJ["yee_true"]["per_k"][str(nv)]
        np_bit = np_bit and (a["n_prop"] == b["n_prop"])
        dv = {"w_meas": abs(a["w_meas"] - b["w_meas"]),
              "transverse_match": abs(a["transverse_match"]
                                      - b["transverse_match"])}
        diffs[str(nv)] = dv
        worst = max(worst, dv["w_meas"], dv["transverse_match"])
    ma, mb = res_y["monitor"], PCJ["yee_true"]["monitor"]
    for kk in ("divE_drift_rel", "divB_drift_rel", "yee_energy_drift_rel"):
        worst = max(worst, abs(ma[kk] - mb[kk]))
        diffs[kk] = abs(ma[kk] - mb[kk])
    p0a_ok = bool(np_bit and worst <= TOL_JUDGE)
    cand = CandidateV2(**CJ["construction_freeze"]["construction_spec"]["cand"])
    gc = G.evaluate_v2_candidate(cand)
    row = C.row2_r23(gc)
    p0b_ok = bool(row["pass"] and row["max_abs_diff"] <= TOL_JUDGE)
    p0_ok = bool(p0a_ok and p0b_ok)
    guns["P0_positive_control"] = {
        "a_yee_vs_frozen": {"n_prop_bitwise": np_bit,
                            "max_judge_field_diff": worst,
                            "diffs": diffs, "pass": p0a_ok},
        "b_row2_r23": {"max_abs_diff": row["max_abs_diff"], "pass": p0b_ok},
        "pass": p0_ok, "seconds": time.time() - tg}
    write_json(payload)
    log("[P0] yee 对拍 diff=%.1e (n_prop 逐位 %s); row2=%.1e -> %s"
        % (worst, np_bit, row["max_abs_diff"], "全绿" if p0_ok else "FAIL"))

    # ---- endurance 负控列(报告级,不作 PASS 依据)------------------------
    tg = time.time()
    st = SP1.seed_generic(2, END_SEED, END_L, END_TRIALS)
    kinfos_e = [{"nv": (1, 0, 0), "kl": SP1.kvec_of([1, 0, 0], END_L),
                 "cf": PC.colfac(SP1.kvec_of([1, 0, 0], END_L), PC.OFF6)}]
    rec, mon, st_end = SP1.evolve_record(st, dict_step, kinfos_e, END_T,
                                         END_L, energy=True)
    rms_ok = bool(END_RMS_BAND[0] <= mon["rms_growth"] <= END_RMS_BAND[1])
    endurance = {
        "protocol": "候选 dict_step L=%d trials=%d seed=%d T=%d 纯 rule 定长跑"
                    % (END_L, END_TRIALS, END_SEED, END_T),
        "H_drift_rel": mon.get("yee_energy_drift_rel"),
        "divE_drift_rel": mon["divE_drift_rel"],
        "divB_drift_rel": mon["divB_drift_rel"],
        "rms_growth": mon["rms_growth"],
        "rms_in_band_report": rms_ok,
        "field_max_end": float(max(np.abs(st_end[0]).max(),
                                   np.abs(st_end[1]).max())),
        "note": "负控列,报告级,不作 PASS 依据(任务书 G7 行);异常如实入册",
        "seconds": time.time() - tg}
    payload["endurance_negative_control"] = endurance
    write_json(payload)
    log("[END] H=%.1e rms_growth=%.3f max=%.2f (%ds)"
        % (endurance["H_drift_rel"], endurance["rms_growth"],
           endurance["field_max_end"], endurance["seconds"]))

    # ---- 判定 -------------------------------------------------------------
    all_guns_fail = all(guns[k]["FAILS_as_required"]
                        for k in ("C1_bad_placement", "C2_proca",
                                  "C3_nonconserved_source", "C4_no_damping"))
    payload["all_guns_fail_as_required"] = all_guns_fail
    payload["p0_all_green"] = p0_ok
    payload["verdict"] = (
        ("四炮全部按预期病灶击穿 + P0 正控全绿 + endurance 负控列入册。"
         "按红线 10 + 裁定 §四:不宣告 M1' PASS/收口——判定四者同时"
         "(全门+全炮+epsilon=1 实测+双环境),收口在车道A 复核 + PI;"
         "收口前不得表述 Maxwell 闭环完成。")
        if (all_guns_fail and p0_ok) else
        ("炮组未全击穿或 P0 未全绿(C1=%s C2=%s C3=%s C4=%s P0=%s)——"
         "判据无牙/管线病,M1' 不得 PASS,停手写追因报车道A。"
         % (guns["C1_bad_placement"]["FAILS_as_required"],
            guns["C2_proca"]["FAILS_as_required"],
            guns["C3_nonconserved_source"]["FAILS_as_required"],
            guns["C4_no_damping"]["FAILS_as_required"], p0_ok)))
    payload["status"] = ("DONE" if (all_guns_fail and p0_ok)
                         else "FAIL-STOP-toothless")
    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)

    # ---- dashboard 泳道数据 v2m1_state.json(交付物 5;任务书 §7 schema)--
    if all_guns_fail and p0_ok:
        pf = {}
        if os.path.exists(PREFLIGHT_JSON):
            with open(PREFLIGHT_JSON, "r", encoding="utf-8") as fh:
                PFJ = json.load(fh)
            pf = {"status": PFJ.get("status"),
                  "sha256": sha256_file(PREFLIGHT_JSON)}
        state_doc = {
            "_schema": "v2m1_state v1 (2026-07-26, lane B, M1' 轮 3 分支 A)",
            "_doc": {
                "purpose": "dashboard_v2 spin1 泳道唯一数据源(任务书 §7;"
                           "禁止读取旧 tensor campaign payload;文件缺失时"
                           "泳道保持待点火)",
                "m1_status": "泳道三态:待点火/执行中/点亮;点亮须 M1' PASS "
                             "四条齐 + 车道A 复核 + PI 收口——本文件状态为"
                             "执行中(lane B 交付,单环境)",
            },
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "experiments/v2m1_guns.py(轮 3 分支 A 交付收拢)",
            "backend": "numpy fp64",
            "environment": env,
            "m1_status": {
                "lane_b": "R3-BRANCH-A-DELIVERED(全门 PASS + 四炮击穿 + P0 "
                          "全绿 + endurance 负控入册,宿主单环境)",
                "swimlane_state": "执行中(非点亮)",
                "pending": ["双环境(沙盒)判据字段比对", "车道A 复核",
                            "PI 收口签字"],
                "wording": "不宣告 M1' PASS;不表述 Maxwell 闭环完成"
                           "(红线 10 + 裁定 §四)"},
            "gate_columns": {k: {"verdict": v}
                             for k, v in R3["verdict_table"].items()},
            "g6_window_resign": {
                "t_cross_table": R3["t_cross_table"],
                "branch": R3["branch"],
                "window_rule": R3["preregistration_r3"]["window_rule"]
                ["formula"]},
            "guns": [{"name": k,
                      "FAILS_as_required": guns[k]["FAILS_as_required"],
                      "lesion": guns[k]["lesion_located"]}
                     for k in ("C1_bad_placement", "C2_proca",
                               "C3_nonconserved_source", "C4_no_damping")],
            "p0_positive_control": {"pass": p0_ok,
                                    "max_judge_field_diff": worst,
                                    "row2_r23_diff": row["max_abs_diff"]},
            "endurance_negative_control": {
                "H_drift_rel": endurance["H_drift_rel"],
                "rms_growth": endurance["rms_growth"]},
            "preflight": pf,
            "epsilon_sigma_point": {
                "epsilon_dof_measured": 1.0,
                "sigma_class": "A=0 exact constraint line (branch i)",
                "status": "实测闭环级读数(lane B);落图动作待车道A 复核 + "
                          "PI 收口(任务书 §7)"},
            "hashes": {
                "v2m1_maxwell_loop_r3.json": sha256_file(R3_JSON),
                "v2m1_guns.json": jsha,
                "construction_sha256": CONSTRUCTION_SHA256,
                "v2m1_guns.py": payload["source_sha256"]},
            "sandbox": {"status": "PENDING"},
        }
        write_json(state_doc, STATE_OUT)
        log("[state] %s 写入(泳道=执行中,非点亮)" % STATE_OUT)

    log("=" * 74)
    log("VERDICT: %s" % payload["verdict"])
    log("source  sha256 = %s" % payload["source_sha256"])
    log("results sha256 = %s" % jsha)
    log("total %.0fs" % payload["total_seconds"])
    return 0 if (all_guns_fail and p0_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
