"""v2m1_guns_r2 -- M1' 炮组全组重跑(炮组重跑令逐条执行;作废版 v2m1_guns.py
与 data/results/v2m1_guns.json 保留不动 = 证据,本脚本另立新件)。

AUTHORITY(判据预注册;本头部运行后不得回改):
  docsv2/v2-复核-车道A-M1轮3判读与炮组重跑令-2026-07-26.md §三(重跑令五条)
    §四(边界骑线禁令——本脚本为其首次执行)
  docsv2/v2-复核包-M1轮3/P1-2-C3元判据8.0到7.5专项.md §6(重跑预注册草案,
    按重跑令修订)
  docsv2/v2-任务书-M1-Maxwell闭环.md §4(炮组四发定义 + P0 正控)§8(红线)
  data/results/v2m1_maxwell_loop_r3.json(轮 3 主跑冻结件,只读引用,零触碰)

== 重跑令五条落实(§三,逐条) =============================================
1. 门线不动:C3 元判据保持预注册线 `末/首 >= 8.0`,一字不改(C3_GROWTH_MIN
   = 8.0;运行后永不动线)。
2. 改实验不改线:C3 注入协议重设计 = 延长注入段一个倍增周期(T_INJ 64->128,
   每步电流 dq = Q/64 不变,总注入 2Q)。预言推导(先算后跑,同 T_cross 纪律):
     每步注入 E[0,c,c,c] += dq => 后向差分 div 在 (c) 得 +dq、(c+1) 得 -dq;
     错符号记账 rho_claimed 在 (c) 与 (c+1) 均 +dq => 失配 |div E - rho| 在
     (c+1) 胞每步累积 2*dq,曲线 g(t) = 2*t*dq/Q = t/32(curl 动力学逐点保
     div,sponge 只作用边界层,内域测量胞不受染;dq = 2^-6 为 fp64 精确值)。
     检查点 stride=8:g_first = g(8) = 0.25;g_end = g(128) = 4.0(注入止后
     平台恒持至 t=192;作废版实测平台漂移 <= 2 ULP)。
     ** 预言:growth = g_end/g_first = 16.0(精确算术);fp64 预期偏差 ~1e-14
     相对(作废版同型偏差 1 ULP)。对 8.0 线 2.0x 裕度,决定性离开边界。**
   击穿判定(两条同时,写死):
     (a) 实测 growth 落预言 ±30%,即 [11.2, 20.8];
     (b) 实测 growth >= 线 1.5x,即 >= 12.0。
3. 全组重跑不许单补:C1 + C2 + C3 + C4 + P0 + endurance 全部执行,种子全新:
     SEED_BAD_R2 = 37(C1;作废版 10)   SEED_PROCA_R2 = 29(C2;作废版 9)
     SEED_TRUE_R2 = 31(P0a;作废版 7)  END_SEED_R2 = 20261777(作废版 20261750)
   排除集(均不取):作废版 {7, 9, 10, 20261750}、件10 {7, 8, 9, 10}、主跑轮 3
   {20261726+L: L=16/24/32/48} 与 {7, 12}、轮 2 {20260726+L}、设计期 pilot
   {901, 903, 905, 907}(pilot 用于裕度标定,见下,不复用)。
   C3/C4 为零背景确定性协议,无随机源,无种子可换(如实声明);C4 协议与
   作废版逐字同 => 预言 = 作废版在册读数逐位复现。
4. 分支写死:C3 实测未同时满足 (a)(b) => 真 FAIL-STOP-toothless,如实入册报
   PI,不得再改实验;C1/C2/C4 任一不击穿或 P0 不全绿 => 同(FAIL-STOP)。
5. 边界骑线禁令自查(§四首次执行):全部判据/元判据"预期信号 vs 阈值"裕度
   声明见下表;预期值来源 = 精确算术推导(C3)、作废版在册读数(C4 确定性
   复现)、设计期 pilot 实测(seed 901/903/905/907,2026-07-27,只用于标定
   预期量级,pilot 种子不进正式判定)。

== 裕度声明表(§四;预期 vs 阈值,>=1.5x 或分离论证) ======================
  C1-i  eval_sick 三 breaks 非空     预期 3 条(pilot)   布尔,由 ii/iii 驱动
  C1-ii Nyquist n_prop == 0          预期 0(pilot 0)    整数通道,分离 >= 1
  C1-iii w_dev_max > 10*bin=0.245    预期 inf(pilot inf) 无穷分离
  C2-i  nprops 全 == 3               预期 [3]*7(pilot)   整数通道,分离 >= 1
  C2-ii m_eff2 偏差 <= 0.02          预期 ~1.20e-3        裕度 16.7x
  C3-i  cont_res >= 1.0              预言 2.0(精确)      裕度 2.0x
  C3-ii g_end >= 0.5                 预言 4.0             裕度 8.0x
  C3-iii 单调(相邻 >= 0.99x)       预言最小相邻比 128/120 = 1.0667;
                                     fp 偏差 ~1e-14 vs 间隙 7.7e-2:分离 ~1e12
  C3-iv growth >= 8.0(线,不动)    预言 16.0            裕度 2.0x
  C3-v  growth >= 12.0(1.5x 线)    预言 16.0            1.33x + 分离论证:
                                     |实测-16| 预期 ~1e-13(作废版同型 1 ULP)
                                     vs 间隙 4.0 => 分离 ~1e13
  C3-vi growth ∈ [11.2, 20.8]        预言 16.0 带中心;偏差 ~1e-13 vs 半宽
                                     4.8 => 分离 ~5e13
  C4    tau 无定义(r_min vs 0.05)  预期 r_min >= 0.8666(在册)分离 17.3x;
        或 resid > 1e-3              预期 resid >= 0.9917(在册)裕度 991x
  P0a-i n_prop 七 k 整数逐位==冻结   预期逐位同(pilot 逐位同)整数通道
  P0a-ii 漂移场 diff <= 1e-12        预期 ~3e-16(pilot 2.6e-16)裕度 ~3800x
  P0a-iii |w_meas-w_yee| < 1 bin     预期 ~3.9e-4(pilot)vs bin 2.45e-2:63x
  P0a-iv transverse_match > 0.95     预期 1-3e-12(pilot)分离 ~1.7e10
  P0b   row2_r23 diff <= 1e-12       预期 ~1.8e-15(符号层,无种子)裕度 560x
  END   报告级(非判定):rms 带 [0.25,4] 预期 ~1.22(pilot 1.2166,在册
        1.2208)带内 3.3x/4.9x;H 漂移预期 ~5e-16。

== P0(a) 判据重设计声明(§四强制,非可选) =================================
作废版 P0(a) 的连续场 1e-12 对拍隐含 seed=SEED_TRUE=7(冻结跑同种子逐位复
现)。重跑令 §三-3 命令全组新种子;实测种子散射:冻结 JSON 内同对称轴 w_meas
散射 ~8e-10,pilot 跨种子散射 ~2.2e-9、transverse_match 散射 ~1.4e-12——新种
子下连续场 1e-12 对拍为负裕度判据,§四 禁止带病预注册,写脚本时即须重设计。
重设计(不引入任何新线,全部沿件10 冻结门线):
  整数判据字段(n_prop 七 k):与冻结值逐位对拍(种子无关,pilot 证实);
  机器零漂移场(divE/divB/H 漂移):与冻结值 diff <= 1e-12(双方均 ~1e-14);
  连续谱场(w_meas / transverse_match):按件10 自身冻结门线判
    (P2 核:|w_meas - w_yee| < 1 FFT bin;P6 核:transverse_match > 0.95),
    与冻结值之差作为种子散射行如实报告,不设线。
P0(b) row2_r23 符号层对拍无种子,判据零改动(diff <= 1e-12)。

其余零改动:C1/C2/C4/endurance 协议、全部门线、冻结 15 件 hash 表、
construction_sha256 逐字继承作废版;C3 主判据 cont>=1.0 / g_end>=0.5 / 单调
不变。主跑冻结 JSON 零触碰(sha256 校验入册,并对拍作废版在册读取值);
作废版两件(脚本 + JSON)保留不动,当前 sha256 先行入册:
  experiments/v2m1_guns.py(作废版):
    855d5a615b6230460e5dd6cebbb313767db6c6176813bef8112955f5731836c0
  data/results/v2m1_guns.json(作废版):
    b94c99b3fcf7de70b01f9aa7ddf22623812d0670e12892f57b36d652a94f91d6

措辞红线:四炮全击穿 + P0 全绿也不宣告 M1' PASS——判定 = 全门 + 全炮 +
epsilon=1 实测 + 双环境 四者同时,收口在车道A 终检 + PI(任务书 §8 红线 10);
C3 若真 toothless 如实报 PI,那是新信息不是失败掩盖。fp64;增量写盘。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m1_guns_r2.py
      (writes data/results/v2m1_guns_r2.json + data/runtime/v2m1_state.json)
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

OUT = os.path.join(ROOT, "data", "results", "v2m1_guns_r2.json")
STATE_OUT = os.path.join(ROOT, "data", "runtime", "v2m1_state.json")
R3_JSON = os.path.join(ROOT, "data", "results", "v2m1_maxwell_loop_r3.json")
CAND_JSON = os.path.join(ROOT, "data", "results", "v2m1_candidate.json")
PREFLIGHT_JSON = os.path.join(ROOT, "data", "results", "v2m1_preflight.json")
VOID_GUNS_PY = os.path.join(ROOT, "experiments", "v2m1_guns.py")
VOID_GUNS_JSON = os.path.join(ROOT, "data", "results", "v2m1_guns.json")

# ---- 判据(写死;运行后不得回改)------------------------------------------
TOL_JUDGE = 1e-12
DT = 0.5
# 新种子(重跑令 §三-3;排除集见头部)
SEED_TRUE_R2 = 31
SEED_PROCA_R2 = 29
SEED_BAD_R2 = 37
END_SEED_R2 = 20261777
# C1
C1_NYQUIST_NPROP_REQ = 0
C1_WDEV_BIN_FACTOR = 10.0
# C2
C2_NPROP_REQ = 3
C2_M2_TRUE = 0.16
C2_M2_TOL = 0.02
# C3(重设计协议;线不动)
C3_L = 16
C3_Q = 1.0
C3_DQ = C3_Q / 64.0             # 每步电流,与作废版同(fp64 精确 2^-6)
C3_T_INJ = 128                  # 重设计:延长一个倍增周期(作废版 64)
C3_T_HOLD = 64
C3_CONT_MIN = 1.0
C3_GAUSS_END_MIN = 0.5
C3_GROWTH_MIN = 8.0             # 预注册线,一字不改(重跑令 §三-1)
C3_GROWTH_PRED = 16.0           # 预言(推导见头部;先算后跑)
C3_PRED_BAND = (0.7 * C3_GROWTH_PRED, 1.3 * C3_GROWTH_PRED)   # ±30%
C3_BREACH_MIN = 1.5 * C3_GROWTH_MIN                           # 12.0
# C4(协议零改动)
C4_L = 16
C4_T = 4000
C4_STRIDE = 8
C4_RESID_MIN = 1e-3
C4_CLEAR_THRESH = 0.05
# P0(a) 连续谱场沿件10 冻结门线(重设计声明见头部)
P0_TM_MIN = 0.95                # 件10 P6 核
# endurance(负控列,报告级)
END_L = 24
END_T = 20000
END_TRIALS = 2
END_RMS_BAND = (0.25, 4.0)
# 冻结件 hash(逐字继承作废版 15 件表)
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
# 主跑冻结 JSON 与作废版两件(零触碰/保留不动证明,先行写死)
R3_JSON_SHA256 = \
    "2cd50d89e5dee3407db911da1a462c14292049559bc2aaa968c04b45951ceb57"
VOID_GUNS_PY_SHA256 = \
    "855d5a615b6230460e5dd6cebbb313767db6c6176813bef8112955f5731836c0"
VOID_GUNS_JSON_SHA256 = \
    "b94c99b3fcf7de70b01f9aa7ddf22623812d0670e12892f57b36d652a94f91d6"

# 裕度声明表(§四首次执行;预期值出处 = 头部推导/在册/pilot)
MARGIN_DECLARATIONS = [
    {"criterion": "C1-ii Nyquist n_prop == 0", "expected": 0, "threshold": 0,
     "margin": "整数通道分离 >= 1(pilot seed=903 实测 0,no_peak)"},
    {"criterion": "C1-iii w_dev_max > 10*bin = 0.2454",
     "expected": "inf(pilot inf)", "threshold": 0.2454, "margin": "无穷分离"},
    {"criterion": "C2-i nprops 全 == 3", "expected": "[3]*7(pilot)",
     "threshold": 3, "margin": "整数通道分离 >= 1"},
    {"criterion": "C2-ii m_eff2 偏差 <= 0.02", "expected": 1.20e-3,
     "threshold": 0.02, "margin": "16.7x"},
    {"criterion": "C3-i cont_res >= 1.0", "expected": 2.0, "threshold": 1.0,
     "margin": "2.0x(精确算术预言)"},
    {"criterion": "C3-ii g_end >= 0.5", "expected": 4.0, "threshold": 0.5,
     "margin": "8.0x"},
    {"criterion": "C3-iii 相邻检查点比 >= 0.99", "expected": 1.0667,
     "threshold": 0.99,
     "margin": "分离论证:fp 偏差 ~1e-14 vs 间隙 7.7e-2 => ~1e12"},
    {"criterion": "C3-iv growth >= 8.0(预注册线,一字不改)",
     "expected": 16.0, "threshold": 8.0, "margin": "2.0x"},
    {"criterion": "C3-v growth >= 12.0(1.5x 线)", "expected": 16.0,
     "threshold": 12.0,
     "margin": "1.33x + 分离论证:|实测-16| 预期 ~1e-13 vs 间隙 4.0 => ~1e13"},
    {"criterion": "C3-vi growth ∈ [11.2, 20.8](预言 ±30%)",
     "expected": 16.0, "threshold": "[11.2, 20.8]",
     "margin": "带中心;偏差 ~1e-13 vs 半宽 4.8 => 分离 ~5e13"},
    {"criterion": "C4 r_min vs CLEAR_THRESH=0.05(tau 无定义)",
     "expected": 0.8666, "threshold": 0.05,
     "margin": "17.3x 分离;或 resid 0.9917 vs 1e-3 = 991x(确定性协议,"
               "预言 = 作废版在册值逐位)"},
    {"criterion": "P0a-i n_prop 七 k 整数逐位 == 冻结", "expected": "逐位同",
     "threshold": "逐位", "margin": "整数通道(pilot seed=901 逐位同)"},
    {"criterion": "P0a-ii 漂移场 diff <= 1e-12", "expected": 3e-16,
     "threshold": 1e-12, "margin": "~3800x"},
    {"criterion": "P0a-iii |w_meas - w_yee| < 1 bin = 2.454e-2",
     "expected": 3.9e-4, "threshold": 2.454e-2, "margin": "63x"},
    {"criterion": "P0a-iv transverse_match > 0.95", "expected": "1 - 3e-12",
     "threshold": 0.95, "margin": "分离 ~1.7e10"},
    {"criterion": "P0b row2_r23 diff <= 1e-12", "expected": 1.8e-15,
     "threshold": 1e-12, "margin": "560x(符号层,无种子)"},
    {"criterion": "END rms_growth ∈ [0.25, 4](报告级,非判定)",
     "expected": 1.22, "threshold": "[0.25, 4]", "margin": "3.3x / 4.9x"},
]


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
        "register": "v2m1-guns-r2 (M1' 炮组全组重跑;重跑令 §三 逐条执行)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": [
            "docsv2/v2-复核-车道A-M1轮3判读与炮组重跑令-2026-07-26.md §三/§四",
            "docsv2/v2-复核包-M1轮3/P1-2-C3元判据8.0到7.5专项.md §6(按令修订)",
            "docsv2/v2-任务书-M1-Maxwell闭环.md §4/§8",
            "data/results/v2m1_maxwell_loop_r3.json (branch A 前提,只读)"],
        "environment": env,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "rerun_order_compliance": {
            "1_line_untouched": "C3_GROWTH_MIN = 8.0(预注册线,一字不改)",
            "2_experiment_redesigned": "C3 注入段延长一个倍增周期 T_INJ "
                                       "64->128;预言 growth=16.0(推导在脚本"
                                       "头,先算后跑);击穿 = 实测∈预言±30% "
                                       "且 >= 12.0 两条同时",
            "3_full_group_new_seeds": {"C1": SEED_BAD_R2, "C2": SEED_PROCA_R2,
                                       "P0a": SEED_TRUE_R2,
                                       "endurance": END_SEED_R2,
                                       "C3_C4": "零背景确定性协议,无随机源"},
            "4_branch_hardcoded": "C3 未同时满足两条 => FAIL-STOP-toothless "
                                  "如实报 PI 不再改实验;其余任一炮不击穿同",
            "5_margin_declarations": "见 margin_declarations(§四首次执行)"},
        "margin_declarations": MARGIN_DECLARATIONS,
        "voided_predecessor": {
            "note": "作废版两件保留不动 = 证据(轮 3 判读 §一);sha256 运行时"
                    "校验入册",
            "experiments/v2m1_guns.py": VOID_GUNS_PY_SHA256,
            "data/results/v2m1_guns.json": VOID_GUNS_JSON_SHA256},
        "wording_redline": (
            "四炮全击穿 + P0 全绿也不宣告 M1' PASS:判定 = 全门 + 全炮 + "
            "epsilon=1 实测 + 双环境 四者同时,收口在车道A 终检 + PI;"
            "C3 若真 toothless 如实报,那是新信息不是失败掩盖"),
    }
    write_json(payload)

    def log(msg):
        print(msg, flush=True)

    log("v2m1 guns r2: 全组重跑(C1-C4 + P0 + endurance,新种子)")
    log("=" * 74)

    # ---- 0. hash + 分支 A 前提 + 作废版保留证明 ---------------------------
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
    r3_sha = sha256_file(R3_JSON)
    with open(R3_JSON, "r", encoding="utf-8") as fh:
        R3 = json.load(fh)
    r3_ok = bool(R3.get("branch") == "A" and R3.get("status") == "DONE"
                 and R3.get("regression_check", {}).get("no_regression"))
    r3_frozen_ok = (r3_sha == R3_JSON_SHA256)
    void_py_sha = sha256_file(VOID_GUNS_PY)
    void_json_sha = sha256_file(VOID_GUNS_JSON)
    void_ok = (void_py_sha == VOID_GUNS_PY_SHA256
               and void_json_sha == VOID_GUNS_JSON_SHA256)
    with open(VOID_GUNS_JSON, "r", encoding="utf-8") as fh:
        VJ = json.load(fh)
    r3_cross_ok = (VJ["hash_verification"]["r3_json_sha256_at_read"] == r3_sha)
    payload["hash_verification"] = {
        "m1_pinned": {"pass": hok, "checked": checked},
        "m0_registry_pass": hz0["pass"],
        "construction_sha256": {"got": cons_got,
                                "expected": CONSTRUCTION_SHA256,
                                "match": cons_ok},
        "r3_json_sha256_at_read": r3_sha,
        "r3_frozen_untouched": {"expected": R3_JSON_SHA256,
                                "match": r3_frozen_ok,
                                "cross_check_vs_voided_record": r3_cross_ok},
        "voided_files_preserved": {"v2m1_guns.py": void_py_sha,
                                   "v2m1_guns.json": void_json_sha,
                                   "match": void_ok},
        "r3_branch_A_precondition": r3_ok}
    write_json(payload)
    log("[cert] pinned(%d): %s; M0'注册表: %s; construction: %s; 主跑冻结零"
        "触碰: %s(交叉 %s); 作废版保留: %s; 分支A前提: %s"
        % (len(checked), hok, hz0["pass"], cons_ok, r3_frozen_ok, r3_cross_ok,
           void_ok, r3_ok))
    if not (hok and hz0["pass"] and cons_ok and r3_ok and r3_frozen_ok
            and r3_cross_ok and void_ok):
        payload["status"] = "HALT-precondition-or-hash"
        write_json(payload)
        return 1

    PC = FZ.mod("photon_control")
    import v2m1_candidate as VC
    dict_step = VC.make_dict_step(PC)
    guns = {}
    payload["guns"] = guns

    # ---- C1 关放置(件10 变体(b) 冻结协议;新种子)-----------------------
    tg = time.time()
    stb = PC.seed_generic(2, SEED_BAD_R2)
    res_b = PC.judge("c1_bad_placement_r2", stb, PC.step_bad,
                     off6=PC.OFF6_ZERO)
    ver_b = PC.eval_sick(res_b)
    nyq = res_b["per_k"][str((8, 0, 0))]
    binw = res_b["per_k"][str((2, 0, 0))]["bin_width"]
    wdev = ver_b["w_dev_max"]
    stb2 = PC.seed_generic(2, SEED_BAD_R2)
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
        "protocol": "件10 step_bad(整数节点+中心差分)seed=%d(新), N=16, "
                    "T=1024" % SEED_BAD_R2,
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
    log("[C1] bad placement (seed %d): nyq N_prop=%d wdev=%s -> %s"
        % (SEED_BAD_R2, nyq["n_prop"], wdev,
           "FAIL(击穿)" if c1_fail else "未击穿!"))

    # ---- C2 Proca m=0.4(件10 变体(a) 冻结协议;新种子)-------------------
    tg = time.time()
    stp = PC.seed_generic(3, SEED_PROCA_R2)
    res_p = PC.judge("c2_proca_r2", stp, PC.make_step_proca(PC.M_PROCA))
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
        "protocol": "件10 make_step_proca(m=0.4) seed=%d(新), N=16, T=1024"
                    % SEED_PROCA_R2,
        "breaks": ver_p["breaks"],
        "nprops": ver_p["nprops"],
        "m_eff2_per_k": gap, "m2_true": C2_M2_TRUE,
        "m_eff2_dev_max": float(max(m2devs)) if m2devs else None,
        "lesion_located": "M1-G1 N_prop=3(第三极化)+ M1-G3 质量隙 "
                          "m_eff^2~0.16 逐点(半角公式定位,非只判红)",
        "FAILS_as_required": c2_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C2] proca (seed %d): nprops=%s m_eff2_devmax=%.4f -> %s"
        % (SEED_PROCA_R2, ver_p["nprops"], max(m2devs) if m2devs else -1,
           "FAIL(击穿)" if c2_fail else "未击穿!"))

    # ---- C3 错符号/非守恒源(重设计协议:T_INJ=128;线 8.0 不动)----------
    tg = time.time()
    L = C3_L
    c = L // 2
    w = 4
    sp_field = SP1.sponge_field(L, w)
    imask = np.zeros((L, L, L), bool)
    imask[(slice(w + 1, L - w - 1),) * 3] = True
    state = (np.zeros((3, 1, L, L, L)), np.zeros((3, 1, L, L, L)))
    rho_claimed = np.zeros((L, L, L))
    dq = C3_DQ
    gauss_hist = []
    cont_res = 0.0
    for t in range(1, C3_T_INJ + C3_T_HOLD + 1):
        E, B = dict_step(state)
        if t <= C3_T_INJ:
            E[0, :, c, c, c] += dq
            # 错符号记账:两胞均 +dq(真配对 = (c)+dq, (c+1)-dq)
            rho_claimed[c, c, c] += dq
            rho_claimed[(c + 1) % L, c, c] += dq        # 错符号
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
    growth = g_end / (g_first + 1e-300)
    c3_line = bool(growth >= C3_GROWTH_MIN)                    # 线(不动)
    c3_band = bool(C3_PRED_BAND[0] <= growth <= C3_PRED_BAND[1])   # 预言±30%
    c3_breach_min = bool(growth >= C3_BREACH_MIN)              # >= 1.5x 线
    c3_fail = bool(cont_res >= C3_CONT_MIN and g_end >= C3_GAUSS_END_MIN
                   and grow_mono and c3_line and c3_band and c3_breach_min)
    guns["C3_nonconserved_source"] = {
        "protocol": "候选 dict_step L=16 零背景;重设计:T_inj=%d(作废版 64,"
                    "延长一个倍增周期)连续注入 dq=%g/步(不变),rho 记账错"
                    "符号((c+1) 胞 +dq 而非 -dq)=> 违连续性;确定性协议无"
                    "种子" % (C3_T_INJ, dq),
        "prediction": {
            "growth_pred": C3_GROWTH_PRED,
            "derivation": "g(t)=2*t*dq/Q=t/32;g_first=g(8)=0.25,g_end="
                          "g(128)=4.0(注入止后平台);growth=16.0 精确算术,"
                          "fp64 预期偏差 ~1e-14 相对(推导冻结在脚本头,"
                          "先算后跑)",
            "line_untouched": C3_GROWTH_MIN,
            "breach_requires": "growth ∈ [%.1f, %.1f](预言±30%%)且 >= %.1f"
                               "(线 1.5x),两条同时"
                               % (C3_PRED_BAND[0], C3_PRED_BAND[1],
                                  C3_BREACH_MIN)},
        "continuity_residual_per_dq": cont_res,
        "gauss_lock_history": gauss_hist,
        "gauss_first_over_Q": g_first,
        "gauss_end_over_Q": g_end,
        "gauss_growth_ratio": growth,
        "growth_vs_prediction": {
            "measured": growth, "predicted": C3_GROWTH_PRED,
            "rel_dev": abs(growth - C3_GROWTH_PRED) / C3_GROWTH_PRED,
            "in_pred_band_pm30": c3_band,
            "ge_line_1p5x_12": c3_breach_min,
            "ge_line_8p0": c3_line,
            "decisively_off_boundary": bool(c3_band and c3_breach_min)},
        "growth_monotone_inj_segment": grow_mono,
        "mainrun_reference": "主跑同列:连续性 0.0、Gauss 锁 <=6.8e-14(门 "
                             "1e-12)——本炮 O(1) 击穿 M1-G5 + G2",
        "lesion_located": "电荷守恒(连续性)机器级击穿 + Gauss 残差随注入段"
                          "单调增长(G2/G5 病灶定位)",
        "FAILS_as_required": c3_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C3] nonconserved src: cont=%.2f gauss_end=%.3f grow=%.13f "
        "(预言 %.1f, 带 [%.1f,%.1f], 1.5x线 %.1f) -> %s"
        % (cont_res, g_end, growth, C3_GROWTH_PRED, C3_PRED_BAND[0],
           C3_PRED_BAND[1], C3_BREACH_MIN,
           "FAIL(击穿)" if c3_fail else "未击穿(toothless)!"))

    # ---- C4 无阻尼(协议零改动;确定性无种子)----------------------------
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
                    "关 sponge,T=%d;确定性协议无种子,预言 = 作废版在册值"
                    "逐位复现" % C4_T,
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

    # ---- P0 正控(新种子;判据重设计声明见脚本头)------------------------
    tg = time.time()
    with open(os.path.join(ROOT, "data", "results",
                           "photon_control_results.json"),
              "r", encoding="utf-8") as fh:
        PCJ = json.load(fh)
    oracles = {nv: PC.yee_oracle(PC.kvec_of(nv)) for nv in PC.KM_ALL}
    st = PC.seed_generic(2, SEED_TRUE_R2)
    res_y = PC.judge("p0_yee_true_r2", st, PC.step_yee, energy=True,
                     oracles=oracles)
    np_bit = True
    wdev_yee_max, tm_min = 0.0, 1.0
    w_scatter, tm_scatter = 0.0, 0.0
    per_k_rows = {}
    for nv in PC.KM_ALL:
        a = res_y["per_k"][str(nv)]
        b = PCJ["yee_true"]["per_k"][str(nv)]
        np_bit = np_bit and (a["n_prop"] == b["n_prop"])
        wdev_yee_max = max(wdev_yee_max, a["w_meas_vs_yee"])
        tm_min = min(tm_min, a["transverse_match"])
        w_scatter = max(w_scatter, abs(a["w_meas"] - b["w_meas"]))
        tm_scatter = max(tm_scatter, abs(a["transverse_match"]
                                         - b["transverse_match"]))
        per_k_rows[str(nv)] = {
            "n_prop": a["n_prop"], "n_prop_frozen": b["n_prop"],
            "w_meas_vs_yee": a["w_meas_vs_yee"],
            "transverse_match": a["transverse_match"],
            "w_meas_seed_scatter_vs_frozen": abs(a["w_meas"] - b["w_meas"]),
            "tm_seed_scatter_vs_frozen": abs(a["transverse_match"]
                                             - b["transverse_match"])}
    binw = res_y["per_k"][str((2, 0, 0))]["bin_width"]
    ma, mb = res_y["monitor"], PCJ["yee_true"]["monitor"]
    drift_diffs = {}
    drift_diff_max = 0.0
    for kk in ("divE_drift_rel", "divB_drift_rel", "yee_energy_drift_rel"):
        drift_diffs[kk] = abs(ma[kk] - mb[kk])
        drift_diff_max = max(drift_diff_max, drift_diffs[kk])
    p0a_ok = bool(np_bit and drift_diff_max <= TOL_JUDGE
                  and wdev_yee_max < binw and tm_min > P0_TM_MIN)
    cand = CandidateV2(**CJ["construction_freeze"]["construction_spec"]["cand"])
    gc = G.evaluate_v2_candidate(cand)
    row = C.row2_r23(gc)
    p0b_ok = bool(row["pass"] and row["max_abs_diff"] <= TOL_JUDGE)
    p0_ok = bool(p0a_ok and p0b_ok)
    guns["P0_positive_control"] = {
        "a_yee_same_pipeline_new_seed": {
            "protocol": "件10 Yee 经同管线重测 seed=%d(新;作废版 7 为冻结跑"
                        "同种子逐位对拍),T=1024, energy" % SEED_TRUE_R2,
            "criteria_note": "判据重设计声明(脚本头,§四强制):整数场逐位"
                             "对拍冻结;机器零漂移场 diff<=1e-12;连续谱场按"
                             "件10 自身冻结门线(P2 <1 bin;P6 tm>0.95);"
                             "种子散射行报告级不设线",
            "n_prop_bitwise": np_bit,
            "drift_diffs_vs_frozen": drift_diffs,
            "drift_diff_max": drift_diff_max,
            "w_meas_vs_yee_max": wdev_yee_max, "bin_width": binw,
            "transverse_match_min": tm_min,
            "seed_scatter_report": {"w_meas_vs_frozen_max": w_scatter,
                                    "tm_vs_frozen_max": tm_scatter,
                                    "note": "报告级(pilot 预期 ~2e-9 / "
                                            "~1e-12 量级)"},
            "per_k": per_k_rows, "pass": p0a_ok},
        "b_row2_r23": {"max_abs_diff": row["max_abs_diff"], "pass": p0b_ok},
        "pass": p0_ok, "seconds": time.time() - tg}
    write_json(payload)
    log("[P0] yee 同管线 seed=%d: n_prop 逐位 %s; drift diff=%.1e; "
        "wdev=%.1e (<bin %.1e); tm_min=%.12f; row2=%.1e -> %s"
        % (SEED_TRUE_R2, np_bit, drift_diff_max, wdev_yee_max, binw, tm_min,
           row["max_abs_diff"], "全绿" if p0_ok else "FAIL"))

    # ---- endurance 负控列(报告级;新种子)-------------------------------
    tg = time.time()
    st = SP1.seed_generic(2, END_SEED_R2, END_L, END_TRIALS)
    kinfos_e = [{"nv": (1, 0, 0), "kl": SP1.kvec_of([1, 0, 0], END_L),
                 "cf": PC.colfac(SP1.kvec_of([1, 0, 0], END_L), PC.OFF6)}]
    rec, mon, st_end = SP1.evolve_record(st, dict_step, kinfos_e, END_T,
                                         END_L, energy=True)
    rms_ok = bool(END_RMS_BAND[0] <= mon["rms_growth"] <= END_RMS_BAND[1])
    endurance = {
        "protocol": "候选 dict_step L=%d trials=%d seed=%d(新)T=%d 纯 rule "
                    "定长跑" % (END_L, END_TRIALS, END_SEED_R2, END_T),
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
    log("[END] seed=%d H=%.1e rms_growth=%.3f max=%.2f (%ds)"
        % (END_SEED_R2, endurance["H_drift_rel"], endurance["rms_growth"],
           endurance["field_max_end"], endurance["seconds"]))

    # ---- 判定(分支写死,重跑令 §三-4)-----------------------------------
    all_guns_fail = all(guns[k]["FAILS_as_required"]
                        for k in ("C1_bad_placement", "C2_proca",
                                  "C3_nonconserved_source", "C4_no_damping"))
    payload["all_guns_fail_as_required"] = all_guns_fail
    payload["p0_all_green"] = p0_ok
    payload["c3_prediction_vs_measured"] = \
        guns["C3_nonconserved_source"]["growth_vs_prediction"]
    payload["verdict"] = (
        ("四炮全部按预期病灶击穿(C3 在预注册线 8.0 不动、实测决定性离开边界"
         "的新协议下击穿)+ P0 正控全绿 + endurance 负控列入册,全组新种子。"
         "按红线 10:不宣告 M1' PASS/收口——判定四者同时(全门+全炮+"
         "epsilon=1 实测+双环境),收口在车道A 终检 + PI。")
        if (all_guns_fail and p0_ok) else
        ("FAIL-STOP:炮组未全击穿或 P0 未全绿(C1=%s C2=%s C3=%s C4=%s "
         "P0=%s)。按重跑令 §三-4 分支写死:如实入册报 PI,不得再改实验;"
         "C3 若为未离开边界/未达 12.0 => 真 FAIL-STOP-toothless。"
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

    # ---- dashboard 泳道数据 v2m1_state.json(任务书 §7 schema;重跑接管)--
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
                "guns_rerun": "炮组数据源 = 全组重跑件 v2m1_guns_r2.json"
                              "(轮 3 炮组作废,重跑令 §三;作废件保留为证据"
                              "不入泳道)"},
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "experiments/v2m1_guns_r2.py(炮组全组重跑交付收拢)",
            "backend": "numpy fp64",
            "environment": env,
            "m1_status": {
                "lane_b": "R3-BRANCH-A-DELIVERED+GUNS-RERUN(全门 PASS + 四炮"
                          "击穿(重跑)+ P0 全绿 + endurance 负控入册,宿主"
                          "单环境)",
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
                                    "n_prop_bitwise": np_bit,
                                    "drift_diff_max": drift_diff_max,
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
                "v2m1_maxwell_loop_r3.json": r3_sha,
                "v2m1_guns_r2.json": jsha,
                "v2m1_guns.json(作废,证据)": VOID_GUNS_JSON_SHA256,
                "construction_sha256": CONSTRUCTION_SHA256,
                "v2m1_guns_r2.py": payload["source_sha256"]},
            "sandbox": {"status": "PENDING"},
        }
        write_json(state_doc, STATE_OUT)
        log("[state] %s 写入(泳道=执行中,非点亮;炮组源=r2)" % STATE_OUT)

    log("=" * 74)
    log("VERDICT: %s" % payload["verdict"])
    log("source  sha256 = %s" % payload["source_sha256"])
    log("results sha256 = %s" % jsha)
    log("total %.0fs" % payload["total_seconds"])
    return 0 if (all_guns_fail and p0_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
