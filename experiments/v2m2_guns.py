"""v2m2_guns -- M2' 轮 3:炮组(五主炮 + 降级/退役表 + 三正控)+ endurance
负控列(任务书 §4 交付物 4;轮 2 经三裁 + 两补测落定 8/8 后按编排放行)。

AUTHORITY(判据预注册;本头部运行后不得回改,红线 4):
  docsv2/v2-任务书-M2-自旋2耦合闭环.md §4(五主炮/降级退役/三正控)§9(红线 13 条)
  docsv2/v2-裁定-M2轮2三裁-2026-07-27.md(执行编排:两补测全过 -> 轮 3 放行;
    裁定三:M2' 内不再追加任何双向探测预算——本脚本零双向内容)
  docsv2/v2-纲领-北极星-涌现边界制图.md §四补条/补条二(边界骑线禁令:逐炮逐判据
    预期 vs 阈值裕度 >=1.5x 或分离论证;预期值来源 = 精确算术/在册值/设计期 pilot,
    pilot 不入判定;M1' guns_r2 先例)
  data/results/v2m2_candidate.json(构造冻结;construction_sha256 逐位校验;
    trace_row_processing_present=false -> C5(v1) T 行三元组自动裁定)
  data/results/v2m2_coupled_loop.json(轮 2 主跑冻结件,只读基线,零触碰)
  experiments/v2m1_guns_r2.py(体裁/裕度表/预言纪律范式)

== 轮 2 落定语义(轮 3 放行前提;原始记录不改写)===========================
轮 2 主跑 JSON 原始 status = FAIL-HALT-追因(G1/G6 两 FAIL)保留不动 = 证据;
三裁(2026-07-27)+ 两补测落定:G1 数据级共锥子判据 = 非门(裁定一),按预注册核
判 PASS,Δω 体对角标度补测 branch a:SCALING-CONFIRMED(v2m2_dw_scaling_results
.json);G6 σ-ii 排零按 D-M2-6 口径重判 REJUDGE-PASS(双控制先过,
v2m2_dm26_results.json)=> 轮 2 = 8/8(G6 计数清结、G1 不计数),轮 3 放行。
本脚本运行前提 = 上述三件 hash 逐位 + 状态字段核验。

== 五主炮预期表(任务书 §4.1;预期信号先写死,运行后零回改)=================
C1 tr_sign=0(迹反转关)
   协议:同 L=16 静源段协议(T_RAMP=128 + T_HOLD=128,cos^2 斜坡,零背景确定性
   无随机源——线性系统,与轮 2 "运行减 ref1" 读数精确同物)一次运行;读出层迹
   反转关断:canary tr_sign=0(冻结 L3.canary_numbers 自带炮口)+ Eddington 读
   raw h̄(不做 trace_reverse_packed);另发 evaluator row6(tensor_qca v1 谱系
   记录对拍)。paired 健康读出(tr_sign=1)同跑入册 = 病灶定位(杀点在迹结构,
   非静源机器)。
   预言:ratio_A(tr0) = 4.000000(v1 总账 43c 记录 4.0;M0' row6 在册 4.000119;
   pilot 4.000000);edd_raw = 1.00484(pilot;v1 记录 1.0);击穿 = ratio_A(tr0)
   ∈ 4.0±0.1 且 |ratio_A(tr0)-2|>0.02(G2 带崩,裕度 100x)且 edd_raw ∈ 1.0±0.1
   且 |edd_raw-2|>0.02(G3 带崩,49.8x)且 row6 判 FAIL 落 v1 记录窗。
C2 错符号/on-site 源
   (i) 错符号:同 C1 协议 drive = -lift(井变山)。预言:A_hbar00 =
   -3.95783534073174(线性精确 = -轮 2 在册值;pilot -3.9578);击穿 =
   well_not_hill == False 且 A_hbar00 <= -1.0(3.96x)且 v1 canary gate FAIL。
   (ii) on-site 双线性源代替精确键流(符号层,BZ 12^3 x v∈{0.05,0.15,0.25},
   确定性):T̄_onsite = u u^T(点源,无键流配对)。预言:max_n |κ^m T̄_mn| =
   3.691(pilot;精确键流机器同泛函在册 1.12e-15)。击穿 = resid >= 1e-6
   (3.7e6x;对 G4 源 deDonder 线 1e-10 为 3.7e10x、G5 T̄ 行线 1e-12 为 3.7e12x)
   且 resid/exact >= 100(任务书 "≥100x";预期 3.3e15)。
C3 θ_g≠θ_m 共锥失谐(θ_m = 0.4,c_m = cos 0.4 = 0.9211 vs c_g = 0.5)
   (i) 算子级(确定性精确):min_k |w_walk_op(k;0.4) - w_leap(k;π/3)| 全 6 非
   Nyquist 判据 k。预言 0.33537(精确算术复现;对判据线 0.1 为 3.35x;对 J5 门
   1e-6 为 3.4e5x)。
   (ii) 数据级:物质符号演化(T=320,trials=4,新种子)谱峰 vs 几何 leap 峰,
   逐 k 偏差(bin = 2π/156 = 0.04027)。预言 min 8.23 bins(pilot;峰位结构性,
   种子散布 < 1 bin);击穿 = 全 6 k 偏差 >= 2 bins(G1 共锥线),裕度 4.1x。
   (iii) 锥哨兵连带(精确算术):c_m/c_cone = 1.8421 > 1 => 物质前沿超几何锥,
   共锥纽带(J5 = 主张唯一非平凡纽带)心脏死;分离 1.84x 入册。
C4 整数格放置(拆 div curl = 0 基础;κ_int = r15.kappa_central 冻结负控符号)
   (i) 符号层(确定性精确):null 亏损 |κc·η·κc|/|κp·η·κp=0| 与 |K(κc)@G(κc)|
   —— 整数放置下约束不再湮灭自家 gauge 块(div curl=0 地基拆除)。预言:null
   亏损 ∈ [0.064, 0.267],|Kc@Gc| ∈ [0.051, 0.237](4 方向表);击穿 = null 亏损
   min >= 0.01(6.4x)且 |Kc@Gc| min >= 0.02(2.6x)。|Kc@TTp| 表如实入册
   (v1 炮 6 同型观测 |K@TT|≈0.23 血统;新主语 oracle 重推,不抄 v1 数字)。
   (ii) 构造层:整数框架复形(IC 由 gauge(κc)⊕TT(κc) 搭)真实 L=16 T=320 跑,
   dedonder_darkness(rec, κc)。预言 0.04-0.2(pilot 0.068-0.114);击穿 =
   darkness >= 1e-6(>=4e4x;对 G6 σ-i A=0 线 1e-12 为 ~1e11x)=> 约束线崩。
   (iii) 簿记层:placed 框架正规跑(轮 2 同构造)用整数 κc 簿记判读。预言:
   darkness_int ∈ [0.045, 0.190];N_prop(κc) ≠ 2 于 >=1 判据方向(pilot 2 方向:
   (2,2,0)/(3,1,0);证据 sv3(3,1,0) = 0.115 = 2.3x SV_THRESH >= 1.5x;
   (2,2,0) sv3 = 0.0518 为边界骑线读数,预注册为 as-recorded 诊断不进判定)
   => 计数崩。击穿 = darkness_int >= 1e-6 且 ≥1 方向 N_int ≠ 2。
C5 无清除/无 sponge(v1 炮 2 "无阻尼" 的新主语改造:候选 clearance = R26 双曲
   输运 + L4 sponge;本炮 κ_work = 0 且 sp = None,协议其余 = 构造冻结
   RHO_PROTOCOL 逐字,L=16,方向 {(2,0,0),(2,2,2)},确定性)
   预言:rho_meas/rho_pred = 4.10 与 4.54(pilot 0.409/0.0997、0.186/0.0410);
   b_layer_rel(50 层末端)= 0.487 与 0.461(pilot;线 1e-12)。击穿 = 两方向
   ratio >= 2.0(预注册 ±30% 窗外,预期 min 4.10 对 2.0 线 2.05x)且 b_layer_rel
   >= 1e-3(461x;对门线 1e-12 为 4.6e11x)=> 单层归纳地基(b_layer 超线)击穿。
   G7 有界性列如实报告(酉输运无爆破预期,杀点 = 清除缺失非失稳)。

== 降级/退役表(任务书 §4.2;自动裁定条件照候选证书写死)====================
炮 3 滞后阻尼(hprev 复活):降级回归抽查一发。自动升回主炮条件(写死):耦合层
  任何实现引入时间滞后项(演化更新引用 t-1 层状态)即升回。本候选核验:geo_step
  为 (h,ps) 当前层纯函数、耦合一步符号严格上三角(CERT-C)=> 无滞后项,维持降级。
  回归抽查协议:ε=0.05 滞后项注入,(a) BZ 16^3 三维伴随矩阵 max|λ|-1(预言
  6.23e-3,确定性;对 G7 线 1e-9 为 6.2e6x,判据 >1e-9);(b) 实空间 L=12 T=256
  H 漂移(预言 ~22.8,pilot 种子无关量级;判据 >= 1e-3,~2.3e4x;对 G5 线 1e-12
  为 ~2e13x)——仪器对滞后项有牙的示证。
炮 7 slave 缺 0ν:降级回归抽查,条件 = 物质走行约束装配复用 slave 行时对物质
  扇区抽查。本候选核验:物质载体 = v1 冻结走行物质半裸 walk(无约束装配层、无
  slave 行机器)=> 条件不满足,记名不跑;复活条件保留原文。
炮 8 Z_μ 静止载波:记名退役(候选无 Z_μ 辅助场)。复活条件(v1 评审原话):
  "辅助场是最容易夹带私货的地方"——未来变体引入任何辅助场即强制复活。
C5(v1) T 行三元组(仅W/仅A/W+A):自动裁定(候选证书 CERT-E 原文照写):
  "若 trace_row_processing_present == true,或耦合层任何实现变更引入演化期迹行
  处理,则 C5(v1) T 行三元组自动升格为主炮(预飞先行);若为 false,三元组记名
  退役,仅当变体引入迹行处理时强制复活。"构造冻结字段 = false(CERT-E 三证据:
  几何步与迹投影对易位级 0 + 上三角无回读 + 源侧 η-迹反转为静态源映射非演化期
  迹行)=> 记名退役已自动裁定,本脚本核验字段后照裁执行,不跑。

== 三正控(任务书 §4.3)+ endurance 负控列 =================================
P0a R30 裸几何锚:evaluate_v2_candidate(ctrl_R30) -> row1_r30 比对器。预期:
  n_prop_seq = [2,2,2,2] 整数逐位 + svn 断崖 diff <= 1e-12(预飞在册 0.0)+
  eps_DOF = 0.0 实测。
P0b M1' 闭环产物对拍(D2 血统;引用而非重跑长跑):v2m1 三件 hash 只读逐位
  (candidate/maxwell_loop_r3/guns_r2,pin 表写死)+ row2_r23 同评估器重测
  diff <= 1e-12(预期 1.78e-15,预飞在册,560x)。
P0c 负控:row5 冻结走行族(N_prop = [4,4,5,5] + walk 因子逐位 0.0 + 不变量基
  稳健漂移 <= 1e-12,预飞在册 9.2e-16)+ row4 teeth 裸波(N_prop = [6,6,6,6]
  精确)——G1 对该判死的对象仍判死。
endurance 负控列(报告级,不作 PASS 依据;北极星 §四分层归纳条,M1' 先例):
  L=24 trials=2 T=12000 纯 rule(几何 staggered leapfrog + 物质走行并行),新
  种子;H 漂移(预期 ~1e-14 量级,pilot T=2000 实测 3.4e-15)、rms_growth 报告
  带 [0.25, 4](预期 0.894,pilot)、物质范数增长(预期 1.000000,酉)。

== 种子纪律(全新;排除集:轮 1 {20260727, 250725}、轮 2 {20260728+L,
20260728+500+L}、M1' {7,9,10,29,31,37,20261750,20261777,20260726+L,20261726+L,
901,903,905,907}、R30 {30303}、控制行 {7}、见证 {99}、设计期 pilot
{1,2,3,5,6}(2026-07-27,只用于裕度标定,不入判定))=======================
  SEED_C3_R3  = 20260753(C3 数据级物质谱)
  SEED_C4A_R3 = 20260757(C4 整数框架 IC)
  SEED_C4B_R3 = 20260759(C4 placed 框架 IC,簿记判读)
  SEED_LAG_R3 = 20260763(回归抽查实空间 IC)
  END_SEED_R3 = 20260761(endurance)
  C1/C2/C5/符号表为零背景或确定性协议,无随机源,无种子可换(如实声明)。

== 分支写死(红线 4 + M1' C3 教训)=========================================
任一主炮未同时满足其全部击穿判据,或回归抽查未捕获,或 P0 任一不全绿 =>
status = FAIL-STOP-toothless,如实入册报车道A/PI,不得再改实验、不得调线;
运行后发现任何边界骑线类问题 => 整组停手报车道A,禁止运行后动任何值。

措辞红线(红线 10/11/12):五炮全击穿 + 三正控全绿也不宣告 M2' PASS——判定 =
全门 + 全炮 + eps 分扇区 + 双环境四者同时,收口在车道A 复核四件 + PI;禁句
"自旋 2 涌现"(eps_geo=0,涌现主语不成立);v1 封存主句原样不动;fp64;
增量写盘;沙盒位 PENDING;不碰 git。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m2_guns.py
      (writes data/results/v2m2_guns.json + data/runtime/v2m2_state.json)
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

OUT = os.path.join(ROOT, "data", "results", "v2m2_guns.json")
STATE_OUT = os.path.join(ROOT, "data", "runtime", "v2m2_state.json")
CAND_JSON = os.path.join(ROOT, "data", "results", "v2m2_candidate.json")
CL_JSON = os.path.join(ROOT, "data", "results", "v2m2_coupled_loop.json")
DW_JSON = os.path.join(ROOT, "data", "results", "v2m2_dw_scaling_results.json")
DM_JSON = os.path.join(ROOT, "data", "results", "v2m2_dm26_results.json")
PREFLIGHT_JSON = os.path.join(ROOT, "data", "results", "v2m2_preflight.json")

# ---- 判据(写死;运行后不得回改)------------------------------------------
TOL_JUDGE = 1e-12
# C1
C1_RATIO_TR0_RECORD, C1_RATIO_WIN = 4.0, 0.1        # v1 总账 43c + M0' row6
C1_EDD_RAW_RECORD, C1_EDD_WIN = 1.0, 0.1
C1_G2_BAND = (2.0, 0.02)
C1_G3_BAND = (2.0, 0.02)
# C2
C2_AHB_NEG_MAX = -1.0                               # A_hbar00 <= -1.0(井变山)
C2_ONSITE_MIN = 1e-6                                # on-site 源 deDonder 残差
C2_ONSITE_RATIO_MIN = 100.0                         # 任务书 ">=100x"
# C3
C3_THETA_M = 0.4                                    # c_m = cos 0.4 = 0.9211
C3_OP_MIN = 0.1                                     # 算子级 min |dW| 判据
C3_BIN_FACTOR = 2.0                                 # 数据级 >= 2 bins(G1 线)
C3_T = 320
C3_TRIALS = 4
# C4
C4_NULL_MIN = 0.01
C4_KG_MIN = 0.02
C4_DARK_MIN = 1e-6
C4_KSET = [(2, 0, 0), (2, 2, 0), (3, 1, 0), (2, 2, 2)]
C4_T = 320
C4_TRIALS = 4
SV_SHARE = 0.05                                     # SV_THRESH(共享判据)
# C5
C5_RATIO_MIN = 2.0                                  # rho_meas/rho_pred
C5_BLAYER_MIN = 1e-3
C5_KSET = [(2, 0, 0), (2, 2, 2)]
C5_LAYERS = 50
RHO_PRED_16_PER_DIR = {"(2, 0, 0)": 0.09967797328075316,
                       "(2, 2, 2)": 0.04097024954116829}   # 构造冻结 CERT-F
# 回归抽查(滞后阻尼)
REG_EPS = 0.05
REG_BZ_N = 16
REG_OVERGROWTH_MIN = 1e-9                           # G7 门同线
REG_HDRIFT_MIN = 1e-3
# endurance
END_L = 24
END_T = 12000
END_TRIALS = 2
END_RMS_BAND = (0.25, 4.0)
# 种子(全新;排除集见头部)
SEED_C3_R3 = 20260753
SEED_C4A_R3 = 20260757
SEED_C4B_R3 = 20260759
SEED_LAG_R3 = 20260763
END_SEED_R3 = 20260761

# ---- 冻结 hash(先行写死;逐位不符 = HALT,红线 2)-------------------------
M2_PINNED = {
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
    "rulespace_v2/spin1.py":
        "69317d39ce304740b4e096df63a85ccfd63beb2a3094038ba9ebd2d923b17384",
    "experiments/v2m2_candidate.py":
        "01e647c0e47ec3946a1576c5e4e9d43b96e8d253a0bdb0780cfd41a9084a73ac",
    "experiments/r25_moving_source_symbol.py":
        "babdf2c53a0cbfb4d7a2bf84fe94a298d59a16199d8e43730952f8f272c50118",
    "experiments/r25_moving_source_realspace.py":
        "8023e3b0f106a87c65eab67ef632f3f705adb706646f9d1781e27e6b557eb498",
    "experiments/r25_static_newton.py":
        "79bdefb16219677f9c1d4365cc66f322e7c5b0c9d0b6f0f678efd95b901ca343",
    "experiments/r25_eddington.py":
        "3b391201c31c2ce5ced7c25abed9bc466fb3f8a2da2cb67710a13748bf9529f0",
    "experiments/r26_hyperbolic_constraint.py":
        "f08dffd352243df4f37e784e130d7ac8213e1f0ac16e5fd6078a7ee39d0f6ec8",
    "experiments/r10_current_generator.py":
        "da8c8c49ab323ba14d239a89682f00dfd81b0d8ccfd1b7082ac938a4c06623bd",
    "rulespace_gpu/tensor_coin_feedback.py":
        "c31badcb14b3a005204d92f2149e67ca2a553693c564e9374153a89d993639f7",
    "data/results/v2m2_preflight.json":
        "15bff5f799c1aad00ae0ff85a9674f22d16a61f52d7f621c9f7cefc903e722a9",
    # -- 轮 2/三裁落定链(冻结零触碰证明;轮 2 原始记录不改写)---------------
    "data/results/v2m2_candidate.json":
        "e446363a20e9bf593af36a4abbd46f4df64aa551a021c6a733d2eb6ba8973604",
    "data/results/v2m2_coupled_loop.json":
        "463f194a540a3b26583038093ff50e588e7130698640b7a153389a07f18f761e",
    "data/results/v2m2_dw_scaling_results.json":
        "b9c6269c51edddf144afc9b54ec90ddd9663e0a1f222c80bcb96018a3d5733d1",
    "data/results/v2m2_dm26_results.json":
        "4190ade66868ed9e6d9aaf3e7854122243ccb0a9fe6cf39f22d85d2efc940eb8",
    # -- P0b:M1' 闭环产物三件(只读 hash 对拍,引用而非重跑)----------------
    "data/results/v2m1_candidate.json":
        "4b6db37993ee69cc2e2a452888e510f8b8f1369001c85d03d5ef22e52efc3a31",
    "data/results/v2m1_maxwell_loop_r3.json":
        "2cd50d89e5dee3407db911da1a462c14292049559bc2aaa968c04b45951ceb57",
    "data/results/v2m1_guns_r2.json":
        "e8e9d80dbf77f6a39fc1bd3ca16ef027c6eb459455f6b550d7656cfb651d33ff",
}
CONSTRUCTION_SHA256 = \
    "70f2c1504f1b5cc5c9186700e039993b4c1c3077ca8c2196459984f6cb508eae"

# ---- 裕度声明表(红线 13;逐炮逐判据;预期值来源注明)----------------------
MARGIN_DECLARATIONS_GUNS = [
    {"gun": "C1-i", "criterion": "ratio_A(tr0) ∈ 4.0±0.1", "type": "band",
     "expected": 4.000000, "threshold": "4.0±0.1",
     "margin": "带中心;pilot 散布 ~1e-6 ≪ 半宽 0.1(分离 ~1e5)",
     "basis": "v1 总账 43c 记录 4.0;M0' row6 在册 4.000119;pilot 4.000000"},
    {"gun": "C1-ii", "criterion": "|ratio_A(tr0)-2.0| > 0.02(G2 带崩)",
     "expected": 2.0, "threshold": 0.02, "margin": "100x",
     "basis": "精确:4.0 - 2.0 = 2.0 对带半宽 0.02"},
    {"gun": "C1-iii", "criterion": "edd_raw ∈ 1.0±0.1", "type": "band",
     "expected": 1.00484, "threshold": "1.0±0.1",
     "margin": "偏离带中心 0.005 ≪ 半宽 0.1(20x)",
     "basis": "v1 记录 1.0;pilot 1.00484"},
    {"gun": "C1-iv", "criterion": "|edd_raw-2.0| > 0.02(G3 带崩)",
     "expected": 0.995, "threshold": 0.02, "margin": "49.8x",
     "basis": "精确:2.0 - 1.005"},
    {"gun": "C1-v", "criterion": "row6 evaluator 判 FAIL + v1 记录窗 ±0.1",
     "expected": "h00/phi=4.000119, 偏折=1.0", "threshold": "窗 ±0.1",
     "margin": "在册复现(确定性协议)", "basis": "M0' v2m0_selftest_v2 在册"},
    {"gun": "C2-i", "criterion": "well_not_hill==False 且 A_hbar00 <= -1.0",
     "expected": -3.95783534073174, "threshold": -1.0, "margin": "3.96x",
     "basis": "线性精确 = -轮 2 在册 A_hbar00(3.95783534073174);pilot -3.9578"},
    {"gun": "C2-ii", "criterion": "on-site 源 max|κ^m T̄_mn| >= 1e-6",
     "expected": 3.691, "threshold": 1e-6, "margin": "3.7e6x",
     "basis": "pilot(确定性协议复现);对 G4 线 1e-10 为 3.7e10x、G5 线 1e-12 "
              "为 3.7e12x"},
    {"gun": "C2-iii", "criterion": "resid_onsite/resid_exact >= 100",
     "expected": 3.3e15, "threshold": 100.0, "margin": "3.3e13x",
     "basis": "pilot;exact 机器同泛函在册 1.12e-15(CERT-C)"},
    {"gun": "C3-i", "criterion": "min_k |w_walk_op(0.4) - w_leap| >= 0.1",
     "expected": 0.33537, "threshold": 0.1, "margin": "3.35x(对 J5 门 1e-6 "
     "为 3.4e5x)", "basis": "确定性精确算术(pilot 复核 0.33537)"},
    {"gun": "C3-ii", "criterion": "数据级谱峰偏差全 6k >= 2 bins",
     "expected": "min 8.23 bins", "threshold": "2 bins", "margin": "4.1x",
     "basis": "pilot(峰位结构性,种子散布 < 1 bin)"},
    {"gun": "C3-iii", "criterion": "c_m/c_cone > 1(锥哨兵连带,报告级入册)",
     "expected": 1.8421, "threshold": 1.0, "margin": "1.84x(精确算术)",
     "basis": "cos(0.4)/cos(π/3) 精确"},
    {"gun": "C4-i", "criterion": "null 亏损 min >= 0.01 且 |Kc@Gc| min >= 0.02",
     "expected": "null ∈ [0.064, 0.267];Kc@Gc ∈ [0.051, 0.237]",
     "threshold": "0.01 / 0.02", "margin": "6.4x / 2.6x(min)",
     "basis": "确定性精确(pilot 复现;placed 侧 null = 0 位级)"},
    {"gun": "C4-ii", "criterion": "整数框架跑 darkness >= 1e-6",
     "expected": "0.04-0.2(pilot 0.068-0.114)", "threshold": 1e-6,
     "margin": ">= 4e4x(对 G6 σ-i 线 1e-12 ~1e11x)",
     "basis": "设计期 pilot(seed 2,结构泄漏非噪声)"},
    {"gun": "C4-iii", "criterion": "簿记层 darkness_int >= 1e-6 且 >=1 方向 "
     "N_int != 2", "expected": "darkness 0.045-0.190;2 方向 N=3,证据 "
     "sv3(3,1,0)=0.115", "threshold": "1e-6 / SV_THRESH 0.05",
     "margin": "4.5e4x / 2.3x(sv3 对计数阈)",
     "basis": "设计期 pilot;(2,2,0) sv3=0.0518 边界骑线预注册为 as-recorded "
              "诊断不进判定(§四补条)"},
    {"gun": "C5-i", "criterion": "两方向 rho_meas/rho_pred >= 2.0",
     "expected": "4.10 / 4.54", "threshold": 2.0, "margin": "2.05x(min)",
     "basis": "pilot(确定性协议)vs 构造冻结 CERT-F 逐方向预言"},
    {"gun": "C5-ii", "criterion": "b_layer_rel(50 层)>= 1e-3",
     "expected": "0.487 / 0.461", "threshold": 1e-3,
     "margin": "461x(对门线 1e-12 为 4.6e11x)", "basis": "pilot(确定性协议)"},
    {"gun": "REG-i", "criterion": "滞后注入 BZ max|λ|-1 > 1e-9(G7 门同线)",
     "expected": 6.23e-3, "threshold": 1e-9, "margin": "6.2e6x",
     "basis": "确定性(pilot 复现;三维伴随矩阵谱)"},
    {"gun": "REG-ii", "criterion": "滞后注入实空间 H 漂移 >= 1e-3",
     "expected": 22.8, "threshold": 1e-3, "margin": "2.3e4x(对 G5 线 1e-12 "
     "~2e13x)", "basis": "pilot(量级结构性,种子无关)"},
    {"gun": "P0a", "criterion": "row1_r30:n_prop=[2,2,2,2] 逐位 + diff<=1e-12 "
     "+ eps_DOF=0.0", "expected": 0.0, "threshold": 1e-12,
     "margin": "整数通道 + 预飞在册 diff=0.0", "basis": "预飞 (i) 在册"},
    {"gun": "P0b", "criterion": "v2m1 三件 hash 逐位 + row2_r23 diff <= 1e-12",
     "expected": 1.78e-15, "threshold": 1e-12, "margin": "560x",
     "basis": "预飞 (ii) 在册(符号层,无种子)"},
    {"gun": "P0c", "criterion": "row5([4,4,5,5]+walk 0.0+漂移<=1e-12)+ "
     "row4([6,6,6,6] 精确)", "expected": "逐位/整数;漂移 9.2e-16",
     "threshold": "整数 + 1e-12", "margin": "整数通道 + 漂移 1090x",
     "basis": "预飞 (iv) 在册"},
    {"gun": "END", "criterion": "rms_growth ∈ [0.25, 4](报告级,非判定)",
     "expected": 0.894, "threshold": "[0.25, 4]",
     "margin": "带内(3.6x / 4.5x 到带边);H 漂移预期 ~1e-14;物质范数 1.000000",
     "basis": "设计期 pilot T=2000(seed 5)"},
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
                   separators=(",", ":"), default=_jd)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---- 实空间步进器(轮 2 主跑同款;控制行 c2 已对拍冻结 leap_M)-------------
def neglap(f):
    out = 6.0 * f
    for ax in (-3, -2, -1):
        out = out - np.roll(f, 1, axis=ax) - np.roll(f, -1, axis=ax)
    return out


def make_geo_step(DT):
    def geo_step(h, ps, drive=None):
        ps = ps - DT * neglap(h)
        if drive is not None:
            ps = ps + DT * drive
        h = h + DT * ps
        return h, ps
    return geo_step


def energy_H(h, ps, DT):
    nl = neglap(h)
    pi_int = ps - 0.5 * DT * nl
    nl2 = neglap(nl)
    return float(np.vdot(h, nl).real - 0.25 * DT * DT * np.vdot(h, nl2).real
                 + np.vdot(pi_int, pi_int).real)


def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m2-guns (M2' 轮 3:五主炮 + 降级/退役 + 三正控 + "
                    "endurance;任务书 §4 交付物 4)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": [
            "docsv2/v2-任务书-M2-自旋2耦合闭环.md §4/§9",
            "docsv2/v2-裁定-M2轮2三裁-2026-07-27.md(执行编排 + 裁定三零双向)",
            "docsv2/v2-纲领-北极星-涌现边界制图.md §四补条(边界骑线禁令)",
            "data/results/v2m2_candidate.json(构造冻结 + CERT-E 自动裁定)",
            "data/results/v2m2_coupled_loop.json(轮 2 冻结基线,只读)",
            "experiments/v2m1_guns_r2.py(体裁先例)"],
        "environment": env,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "margin_declarations": MARGIN_DECLARATIONS_GUNS,
        "seeds": {"C3": SEED_C3_R3, "C4A": SEED_C4A_R3, "C4B": SEED_C4B_R3,
                  "LAG": SEED_LAG_R3, "endurance": END_SEED_R3,
                  "deterministic_no_seed": "C1/C2/C5/符号表(零背景确定性协议,"
                                           "无随机源,如实声明)",
                  "exclusions": "轮1/轮2/M1'/R30/控制行/见证/pilot 全排除"
                                "(名单见脚本头)"},
        "two_way_content": "零(裁定三:M2' 内不再追加任何双向探测预算)",
        "wording_redline": (
            "五炮全击穿 + 三正控全绿也不宣告 M2' PASS:判定 = 全门 + 全炮 + "
            "eps 分扇区 + 双环境四者同时,收口在车道A 复核四件 + PI(红线 12);"
            "禁句'自旋 2 涌现'(eps_geo=0,涌现主语不成立);v1 封存主句原样"
            "不动;本件为 lane B 宿主单环境交付状态"),
    }
    write_json(payload)

    def log(msg):
        print(msg, flush=True)

    log("v2m2 guns: M2' 轮 3 炮组(五主炮 + 退役表 + 三正控 + endurance)")
    log("=" * 74)

    # ---- 0. hash + 构造冻结 + 轮 2 落定前提 --------------------------------
    checked, hok = {}, True
    for rel, exp in M2_PINNED.items():
        got = sha256_file(os.path.join(ROOT, rel))
        m = (got == exp)
        hok = hok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    hz0 = FZ.verify_frozen()
    with open(CAND_JSON, "r", encoding="utf-8") as fh:
        CJ = json.load(fh)
    cons_got = sha256_canonical(CJ["construction_freeze"]["construction_spec"])
    cons_ok = (cons_got == CONSTRUCTION_SHA256)
    trace_row = CJ["construction_freeze"]["construction_spec"][
        "trace_row_processing_present"]
    with open(CL_JSON, "r", encoding="utf-8") as fh:
        CL = json.load(fh)
    with open(DW_JSON, "r", encoding="utf-8") as fh:
        DW = json.load(fh)
    with open(DM_JSON, "r", encoding="utf-8") as fh:
        DM = json.load(fh)
    r2_ok = bool(CL.get("status") == "FAIL-HALT-追因"        # 原始记录如实保留
                 and DW.get("status") == "DONE"
                 and DW.get("branch") == "a:SCALING-CONFIRMED"
                 and DM.get("status") == "REJUDGE-PASS")
    payload["hash_verification"] = {
        "m2_pinned": {"pass": hok, "checked": checked},
        "m0_registry_pass": hz0["pass"],
        "construction_sha256": {"got": cons_got,
                                "expected": CONSTRUCTION_SHA256,
                                "match": cons_ok},
        "round2_settlement": {
            "coupled_loop_status_as_recorded": CL.get("status"),
            "dw_scaling_branch": DW.get("branch"),
            "dm26_status": DM.get("status"),
            "semantics": "轮 2 原始 FAIL-HALT 记录保留不改写;三裁 + 两补测落定"
                         " 8/8(G1 按核 PASS 不计数,G6 重判 PASS 计数清结),"
                         "轮 3 据此放行(裁定文执行编排)",
            "pass": r2_ok},
        "trace_row_processing_present": trace_row}
    write_json(payload)
    log(f"[cert] pinned({len(checked)}): {hok}; M0'注册表: {hz0['pass']}; "
        f"construction: {cons_ok}; 轮2落定链: {r2_ok}; trace_row={trace_row}")
    if not (hok and hz0["pass"] and cons_ok and r2_ok):
        payload["status"] = "HALT-precondition-or-hash"
        write_json(payload)
        return 1

    # ---- 冻结机加载 --------------------------------------------------------
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    R36M = FZ.mod("r36_r3_verification")
    R25N = FZ.mod("r25_static_newton")
    MS = FZ.mod("r25_moving_source_symbol")
    RS = FZ.mod("r25_realspace_step")
    L3 = FZ.mod("cp1_v4_L3")
    L2 = FZ.mod("cp1_v4_L2")
    r15 = FZ.mod("r15_walk_dedonder")
    tcf = FZ.mod("rulespace_gpu.tensor_coin_feedback")
    pathB = FZ.mod("rulespace_gpu.pathB_spin2")
    DT = R30M.DT
    ETA = MS.ETA
    geo_step = make_geo_step(DT)
    guns = {}
    payload["guns"] = guns

    L = 16
    x = np.arange(L)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")

    # ---- 静源共用件(C1/C2(i);零背景确定性,轮 2 P2 同协议)---------------
    rho_src = R25N.gaussian_lump(L, 2.5)
    rho_zm = rho_src - rho_src.mean()
    lift = R25N.local_source_lift(rho_zm)
    lift = lift - lift.mean(axis=(1, 2, 3), keepdims=True)
    T_RAMP, T_HOLD = 128, 128

    def static_run(sign):
        hs = np.zeros((10, L, L, L), complex)
        pss = np.zeros_like(hs)
        for t in range(1, T_RAMP + T_HOLD + 1):
            amp = 0.5 * (1 - math.cos(math.pi * min(t, T_RAMP) / T_RAMP))
            hs, pss = geo_step(hs, pss, drive=(sign * amp) * lift)
        return hs

    # ---- C1 tr_sign=0(迹反转关)------------------------------------------
    tg = time.time()
    hs1 = static_run(+1.0)
    hb_phys = np.real(0.5 * (hs1 + np.conjugate(hs1)))
    cn_tr1 = L3.canary_numbers(hb_phys, rho_src, 2.5, tr_sign=1.0)
    cn_tr0 = L3.canary_numbers(hb_phys, rho_src, 2.5, tr_sign=0.0)

    def edd_read(hb, do_tr):
        h_phys = (RS.trace_reverse_packed(hb.astype(complex)).real
                  if do_tr else hb.copy())
        ctr = L // 2
        h00_sl = h_phys[0][..., ctr]
        hxx_sl = h_phys[4][..., ctr]
        scale = 3e-4 / (np.abs(0.5 * h00_sl).max() + 1e-300)
        rows = []
        for b in (4, 5, 6):
            n_t = 1.0 - 0.5 * (h00_sl + hxx_sl) * scale
            n_s = 1.0 - 0.5 * h00_sl * scale
            rows.append(pathB._deflection(n_t, L, b)
                        / pathB._deflection(n_s, L, b))
        return float(np.median(rows))

    edd_tr = edd_read(hb_phys, True)
    edd_raw = edd_read(hb_phys, False)
    cand6 = C.control_candidates()["row6_tr_sign"]
    gc6 = G.evaluate_v2_candidate(cand6)
    row6 = C.row6_tr_sign(gc6)
    c1_fail = bool(
        abs(cn_tr0["ratio_A"] - C1_RATIO_TR0_RECORD) <= C1_RATIO_WIN
        and abs(cn_tr0["ratio_A"] - C1_G2_BAND[0]) > C1_G2_BAND[1]
        and abs(edd_raw - C1_EDD_RAW_RECORD) <= C1_EDD_WIN
        and abs(edd_raw - C1_G3_BAND[0]) > C1_G3_BAND[1]
        and (not cn_tr0["gate_pass"]) and row6["pass"])
    guns["C1_tr_sign_zero"] = {
        "protocol": "L=16 静源段(T_RAMP=128+T_HOLD=128,零背景确定性无随机源)"
                    "一次运行;读出层迹反转关断(canary tr_sign=0 + Eddington "
                    "raw h̄)+ evaluator row6(tensor_qca v1 谱系)",
        "ratio_A_tr0": cn_tr0["ratio_A"],
        "ratio_A_tr1_paired_healthy": cn_tr1["ratio_A"],
        "edd_raw_tr_off": edd_raw,
        "edd_with_tr_paired_healthy": edd_tr,
        "canary_tr0_gate_pass": cn_tr0["gate_pass"],
        "row6_evaluator": {"h00_over_phi": row6["remeasured"]["h00_over_phi"],
                           "deflection_ratio":
                               row6["remeasured"]["deflection_ratio"],
                           "pass_judged_FAIL": row6["pass"]},
        "lesion_located": "M2-G2 比值 2->4(带崩 100x)+ M2-G3 偏折 2->1(带崩 "
                          "49.8x),v1 记录 43c 方向逐一复现;paired 健康读出 "
                          "2.000000/2.0098 => 杀点在迹结构本身,非静源机器",
        "FAILS_as_required": c1_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C1] tr0: ratio_A=%.6f (健康 %.6f) edd_raw=%.5f (健康 %.5f) "
        "row6=%s -> %s" % (cn_tr0["ratio_A"], cn_tr1["ratio_A"], edd_raw,
                           edd_tr, row6["pass"],
                           "FAIL(击穿)" if c1_fail else "未击穿!"))

    # ---- C2 错符号/on-site 源 ---------------------------------------------
    tg = time.time()
    hs2 = static_run(-1.0)
    hb_neg = np.real(0.5 * (hs2 + np.conjugate(hs2)))
    cn_neg = L3.canary_numbers(hb_neg, rho_src, 2.5, tr_sign=1.0)
    # on-site 双线性源(符号层;确定性)
    N_BZ = 12
    worst_on, worst_exact = 0.0, 0.0
    for v in (0.05, 0.15, 0.25):
        vv = np.array([v, 0.0, 0.0])
        for idx in np.ndindex(N_BZ, N_BZ, N_BZ):
            if idx == (0, 0, 0):
                continue
            kk = 2 * np.pi * np.array(idx, float) / N_BZ
            z = complex(np.exp(-1j * float(vv @ kk)))
            hb = MS.hbar_moving(kk, z)[0]
            worst_exact = max(worst_exact, float(np.max(np.abs(
                (ETA @ MS.kappa(kk, z)) @ hb))))
            u = np.array([1.0, v, 0.0, 0.0], complex)
            Tb = np.outer(u, u)
            worst_on = max(worst_on, float(
                np.max(np.abs((ETA @ MS.kappa(kk, z)) @ Tb))
                / (np.max(np.abs(Tb)) + 1e-300)))
    ratio_on = worst_on / max(worst_exact, 1e-300)
    c2_fail = bool(
        (not cn_neg["well_not_hill"]) and cn_neg["A_hbar00"] <= C2_AHB_NEG_MAX
        and (not cn_neg["gate_pass"])
        and worst_on >= C2_ONSITE_MIN and ratio_on >= C2_ONSITE_RATIO_MIN)
    guns["C2_wrong_sign_onsite_source"] = {
        "protocol": "(i) 错符号:同 C1 静源协议 drive=-lift(确定性);(ii) "
                    "on-site 双线性源 T̄=u u^T 代精确键流,κ^m T̄_mn 残差 "
                    "BZ 12^3 x v∈{0.05,0.15,0.25}(确定性)",
        "wrong_sign": {"A_hbar00": cn_neg["A_hbar00"],
                       "well_not_hill": cn_neg["well_not_hill"],
                       "ratio_A": cn_neg["ratio_A"],
                       "gate_pass": cn_neg["gate_pass"]},
        "onsite": {"deDonder_resid_max": worst_on,
                   "exact_machine_same_functional": worst_exact,
                   "ratio_onsite_over_exact": ratio_on},
        "lesion_located": "井变山(A_hbar00 翻号,M2-G2 源链病灶)+ 键流优势"
                          "消失(源 deDonder 残差 O(1) vs 精确机器 1e-15,"
                          "M2-G4 源线/M2-G5 T̄ 行守恒击穿)",
        "FAILS_as_required": c2_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C2] wrong-sign A_hb=%.4f well=%s; onsite resid=%.4f ratio=%.2e -> %s"
        % (cn_neg["A_hbar00"], cn_neg["well_not_hill"], worst_on, ratio_on,
           "FAIL(击穿)" if c2_fail else "未击穿!"))

    # ---- C3 θ_g≠θ_m 共锥失谐 ----------------------------------------------
    tg = time.time()
    NONNYQ = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
              (2, 2, 2)]
    op_rows, op_min = [], float("inf")
    for n16 in NONNYQ:
        k = np.array(n16, float) * (2 * np.pi / L)
        U = L2.walk_symbol(k, C3_THETA_M)
        wm = float(np.min(np.abs(np.angle(np.linalg.eigvals(U)))))
        Lk = R30M.L_placed(k)
        wg = float(np.arccos(np.clip(1 - 0.5 * DT * DT * Lk, -1, 1)))
        op_rows.append({"n16": list(n16), "w_walk_op": wm, "w_leap": wg,
                        "dW": abs(wm - wg)})
        op_min = min(op_min, abs(wm - wg))
    rng3 = np.random.default_rng(SEED_C3_R3)
    binw = 2 * np.pi / (C3_T // 2 - 4)
    data_rows, bins_min = [], float("inf")
    for n16 in NONNYQ:
        k = np.array(n16, float) * (2 * np.pi / L)
        U = L2.walk_symbol(k, C3_THETA_M)
        chi = (rng3.standard_normal((2, C3_TRIALS))
               + 1j * rng3.standard_normal((2, C3_TRIALS)))
        rec_m = np.zeros((C3_T, C3_TRIALS, 2), complex)
        ch = chi.copy()
        for t in range(C3_T):
            ch = U @ ch
            rec_m[t] = ch.T
        T0 = C3_T // 2
        Wn = C3_T - T0
        win = np.hanning(Wn)
        F = np.fft.fft((rec_m[T0:] * win[:, None, None])[2:-2], axis=0)
        freqs = 2 * np.pi * np.fft.fftfreq(Wn - 4)
        P = np.sum(np.abs(F) ** 2, axis=(1, 2))
        lo = max(0.05, 4 * np.pi / len(freqs))
        sel = (freqs > lo) & (freqs <= np.pi / 2)
        pk = int(np.argmax(np.where(sel, P, 0.0)))
        wm_d = abs(float(freqs[pk]))
        Lk = R30M.L_placed(k)
        wg = float(np.arccos(np.clip(1 - 0.5 * DT * DT * Lk, -1, 1)))
        dev_bins = abs(wm_d - wg) / binw
        data_rows.append({"n16": list(n16), "w_peak_matter": wm_d,
                          "w_leap": wg, "dev_bins": dev_bins})
        bins_min = min(bins_min, dev_bins)
    cone_ratio = math.cos(C3_THETA_M) / math.cos(math.pi / 3.0)
    c3_fail = bool(op_min >= C3_OP_MIN
                   and all(r["dev_bins"] >= C3_BIN_FACTOR for r in data_rows))
    guns["C3_cocone_detune"] = {
        "protocol": "θ_m=0.4(c_m=%.4f)vs θ_g=π/3(c_g=0.5);(i) 算子谱相"
                    "(确定性精确);(ii) 数据级符号演化 T=%d trials=%d "
                    "seed=%d;(iii) 锥速比精确算术" % (math.cos(C3_THETA_M),
                                                      C3_T, C3_TRIALS,
                                                      SEED_C3_R3),
        "operator_rows": op_rows, "op_min_dW": op_min,
        "data_rows": data_rows, "data_min_dev_bins": bins_min,
        "fft_bin_width": binw,
        "cone_escape_ratio_cm_over_ccone": cone_ratio,
        "lesion_located": "M2-G1 J5 线崩(min dW=%.4f 对门 1e-6 为 %.1e 倍)+ "
                          "共锥数据级崩(min %.1f bins,线 2)+ G4 锥哨兵连带"
                          "(物质前沿 c_m=%.3f 超几何锥 c=0.5,比 %.2f)——"
                          "直打共锥纽带心脏" % (op_min, op_min / 1e-6, bins_min,
                                               math.cos(C3_THETA_M),
                                               cone_ratio),
        "FAILS_as_required": c3_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C3] op_min=%.5f data_min=%.2f bins cone=%.3f -> %s"
        % (op_min, bins_min, cone_ratio,
           "FAIL(击穿)" if c3_fail else "未击穿!"))

    # ---- C4 整数格放置 -----------------------------------------------------
    tg = time.time()
    sym_rows = []
    null_min, kg_min = float("inf"), float("inf")
    for n16 in C4_KSET:
        k = np.array(n16, float) * (2 * np.pi / L)
        kp = r15.kappa_placed(k)
        kc = r15.kappa_central(k)
        nullp = abs(float(np.real(kp @ ETA @ kp)))
        nullc = abs(float(np.real(kc @ ETA @ kc)))
        K_c = r15.constraint_matrix(kc)
        TTp = r15.tt_basis(kp)
        Gc = r15.gauge_block(kc)
        kg = float(np.max(np.abs(K_c @ Gc)) / (np.max(np.abs(Gc)) + 1e-300))
        ktt = float(np.max(np.abs(K_c @ TTp)) / (np.max(np.abs(TTp)) + 1e-300))
        sym_rows.append({"n16": list(n16), "null_defect_placed": nullp,
                         "null_defect_integer": nullc,
                         "Kc_at_Gc": kg, "Kc_at_TTp_as_recorded": ktt})
        null_min = min(null_min, nullc)
        kg_min = min(kg_min, kg)

    def c4_run(frame, seed):
        rng = np.random.default_rng(seed)
        h = np.zeros((10, C4_TRIALS, L, L, L), complex)
        ps = np.zeros_like(h)
        kin, planes = [], []
        for n16 in C4_KSET:
            k = np.array(n16, float) * (2 * np.pi / L)
            kap_ic = (r15.kappa_central(k) if frame == "integer"
                      else r15.kappa_placed(k))
            h0, pi0 = R30M.make_ic("clean_kerK", kap_ic, k, C4_TRIALS, rng)
            Lk = R30M.L_placed(k)
            psk = pi0 + 0.5 * DT * Lk * h0
            ph = np.exp(1j * (k[0] * X + k[1] * Y + k[2] * Z))
            h += h0.T[:, :, None, None, None] * ph[None, None]
            ps += psk.T[:, :, None, None, None] * ph[None, None]
            kin.append((n16, r15.kappa_central(k)))
            planes.append(ph)
        Pconj = np.stack([np.conj(p).reshape(-1) / L ** 3 for p in planes])
        rec = np.zeros((C4_T, C4_TRIALS, len(kin), 10), complex)
        for t in range(C4_T):
            h, ps = geo_step(h, ps)
            A = (h.reshape(10 * C4_TRIALS, -1) @ Pconj.T)
            rec[t] = A.reshape(10, C4_TRIALS, len(kin)).transpose(1, 2, 0)
        rows = []
        for i, (n16, kc) in enumerate(kin):
            rk = rec[:, :, i, :]
            res = R30M.peak_and_svd_placed(rk, kc)
            dark = R30M.dedonder_darkness(rk[-40:], kc)
            rmean, rmax = R30M.kerK_residual(rk, kc)
            rows.append({"n16": list(n16), "N_prop_int_frame": res["n_prop"],
                         "sv_int": res.get("sv", [])[:6],
                         "darkness_int": dark,
                         "kerK_int_resid_mean": rmean,
                         "kerK_int_resid_max": rmax})
        return rows

    rows_a = c4_run("integer", SEED_C4A_R3)      # 构造层:整数框架复形
    rows_b = c4_run("placed", SEED_C4B_R3)       # 簿记层:整数簿记判读 placed 跑
    dark_a_min = min(r["darkness_int"] for r in rows_a)
    dark_b_min = min(r["darkness_int"] for r in rows_b)
    n_break = [r for r in rows_b if r["N_prop_int_frame"] != 2]
    c4_fail = bool(null_min >= C4_NULL_MIN and kg_min >= C4_KG_MIN
                   and dark_a_min >= C4_DARK_MIN and dark_b_min >= C4_DARK_MIN
                   and len(n_break) >= 1)
    guns["C4_integer_placement"] = {
        "protocol": "κ_int = r15.kappa_central(冻结负控符号);(i) 符号表 4 "
                    "方向;(ii) 整数框架复形 L=16 T=%d trials=%d seed=%d;"
                    "(iii) placed 正规跑整数簿记判读 seed=%d"
                    % (C4_T, C4_TRIALS, SEED_C4A_R3, SEED_C4B_R3),
        "symbol_rows": sym_rows,
        "null_defect_integer_min": null_min, "Kc_at_Gc_min": kg_min,
        "run_integer_frame": rows_a,
        "run_placed_frame_integer_bookkeeping": rows_b,
        "N_break_directions": [r["n16"] for r in n_break],
        "boundary_note": "(2,2,0) sv3 预期 ~0.05 边界骑线,预注册为 "
                         "as-recorded 诊断不进判定;计数判据证据方向 = "
                         "sv3 >= 2x 阈者(预期 (3,1,0))",
        "v1_lineage_note": "|Kc@TTp| 表 = v1 炮 6 同型观测(v1 记录 ≈0.23)"
                           "as-recorded;新主语 oracle 重推,不抄 v1 数字"
                           "(任务书 G5 血统注)",
        "lesion_located": "M2-G6 约束线崩(null 亏损 O(0.1),K@gauge 不湮灭,"
                          "darkness O(0.1) vs A=0 线 1e-12)+ M2-G1 计数崩"
                          "(整数簿记下 N != 2 于 %s)——div curl=0 地基拆除"
                          % [r["n16"] for r in n_break],
        "FAILS_as_required": c4_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C4] null_min=%.3f Kc@Gc_min=%.3f dark_a=%.3f dark_b=%.3f "
        "N_break=%s -> %s" % (null_min, kg_min, dark_a_min, dark_b_min,
                              [r["n16"] for r in n_break],
                              "FAIL(击穿)" if c4_fail else "未击穿!"))

    # ---- C5 无清除/无 sponge ----------------------------------------------
    tg = time.time()
    dTl = int(round(L / DT))
    pad = max(2, int(round(12 * L / 44.0)))
    sig_env = 6.0 * L / 44.0
    envg = np.exp(-(((x - L / 2.0) / sig_env) ** 2))
    env3 = envg[:, None, None] * envg[None, :, None] * envg[None, None, :]

    def bulk(zf):
        b = (slice(pad, -pad),) * 3
        return float(np.abs(zf[b]).sum())

    c5_rows = {}
    ratio_min_c5, blayer_min = float("inf"), float("inf")
    zmax_report = 0.0
    for n16 in C5_KSET:
        kvec = 2 * np.pi * np.array(n16, float) / L
        carrier = np.exp(1j * (kvec[0] * X + kvec[1] * Y + kvec[2] * Z))
        z0 = (env3 * carrier).astype(complex)
        m0 = bulk(z0 - z0.mean())
        zmax0 = float(np.abs(z0).max())
        zf, pz = z0.copy(), np.zeros_like(z0)
        row = {}
        for t in range(1, C5_LAYERS * dTl + 1):
            zf, pz = R36M.hyper_step(zf, pz, 0.0, DT * DT, sp=None)  # 无清除
            if t == dTl:
                row["rho_no_clear"] = bulk(zf - zf.mean()) / m0
            if t == 3 * dTl:
                row["floor_3dT"] = bulk(zf - zf.mean()) / m0
            if t == C5_LAYERS * dTl:
                row["b_layer_rel"] = bulk(zf - zf.mean()) / m0
        row["rho_pred_frozen"] = RHO_PRED_16_PER_DIR[str(tuple(n16))]
        row["ratio_over_pred"] = row["rho_no_clear"] / row["rho_pred_frozen"]
        row["boundedness_max_rel"] = float(np.abs(zf).max()) / (zmax0 + 1e-300)
        zmax_report = max(zmax_report, row["boundedness_max_rel"])
        ratio_min_c5 = min(ratio_min_c5, row["ratio_over_pred"])
        blayer_min = min(blayer_min, row["b_layer_rel"])
        c5_rows[str(tuple(n16))] = row
    c5_fail = bool(ratio_min_c5 >= C5_RATIO_MIN
                   and blayer_min >= C5_BLAYER_MIN)
    guns["C5_no_clearance_no_sponge"] = {
        "protocol": "构造冻结 RHO_PROTOCOL 逐字(L=16, DeltaT=%d, 50 层),"
                    "唯一改动 = κ_work=0 且 sp=None(关 R26 清除 + L4 sponge;"
                    "确定性无随机源)" % dTl,
        "per_dir": c5_rows,
        "ratio_over_pred_min": ratio_min_c5,
        "b_layer_rel_min": blayer_min,
        "g7_boundedness_report": {"max_rel_amplitude": zmax_report,
                                  "note": "酉输运无爆破(如实报告):杀点 = "
                                          "清除缺失(归纳地基),非失稳"},
        "lesion_located": "M2-G6 单层归纳击穿:rho 脱预言窗 %.1f-%.1fx + "
                          "b_layer O(0.5) 超线 %.0e 倍(线 1e-12)——约束违反"
                          "永不清除,分层归纳地基拆除"
                          % (ratio_min_c5,
                             max(r["ratio_over_pred"]
                                 for r in c5_rows.values()),
                             blayer_min / 1e-12),
        "FAILS_as_required": c5_fail, "seconds": time.time() - tg}
    write_json(payload)
    log("[C5] ratio_min=%.2f b_layer_min=%.3f bounded=%.2f -> %s"
        % (ratio_min_c5, blayer_min, zmax_report,
           "FAIL(击穿)" if c5_fail else "未击穿!"))

    # ---- 降级/退役表执行 ---------------------------------------------------
    tg = time.time()
    # 回归抽查一发:滞后阻尼(炮 3 降级)
    gmax = 0.0
    for n in np.ndindex(REG_BZ_N, REG_BZ_N, REG_BZ_N):
        k = np.array(n, float) * (2 * np.pi / REG_BZ_N)
        Lk = R30M.L_placed(k)
        M3 = np.array([[1 - DT * DT * Lk, DT, -DT * DT * REG_EPS],
                       [-DT * Lk, 1.0, -DT * REG_EPS],
                       [1.0, 0.0, 0.0]])
        lam = np.abs(np.linalg.eigvals(M3))
        gmax = max(gmax, float(lam.max()) - 1.0)
    Ll = 12
    rngl = np.random.default_rng(SEED_LAG_R3)
    hl = (rngl.standard_normal((10, Ll, Ll, Ll))
          + 1j * rngl.standard_normal((10, Ll, Ll, Ll)))
    pl = np.zeros_like(hl)
    hprev = hl.copy()
    H0l, driftl = None, 0.0
    for t in range(256):
        pl = pl - DT * neglap(hl) - DT * REG_EPS * hprev
        hn = hl + DT * pl
        hprev = hl
        hl = hn
        e = energy_H(hl, pl, DT)
        if H0l is None:
            H0l = e
        driftl = max(driftl, abs(e - H0l) / (abs(H0l) + 1e-300))
    reg_caught = bool(gmax > REG_OVERGROWTH_MIN and driftl >= REG_HDRIFT_MIN)
    payload["demotion_retirement_table"] = {
        "gun3_lagged_damping": {
            "status": "降级回归抽查(执行一发)",
            "auto_promote_condition": "耦合层任何实现引入时间滞后项(演化更新"
                                      "引用 t-1 层状态)即升回主炮",
            "condition_check": "geo_step = (h,ps) 当前层纯函数;耦合一步符号"
                               "严格上三角(CERT-C 下左块 0.0)=> 无滞后项,"
                               "维持降级",
            "regression_shot": {
                "eps": REG_EPS, "bz_overgrowth_max": gmax,
                "overgrowth_gt_1e-9": bool(gmax > REG_OVERGROWTH_MIN),
                "realspace_H_drift_rel": driftl,
                "H_drift_ge_1e-3": bool(driftl >= REG_HDRIFT_MIN),
                "seed": SEED_LAG_R3,
                "caught_as_required": reg_caught,
                "note": "仪器对滞后项有牙:注入即破酉(G7 线)+ 破 H 不变量"
                        "(G5 线)"}},
        "gun7_slave_0nu": {
            "status": "降级回归抽查——条件不满足,记名不跑",
            "condition": "仅当物质走行约束装配复用 slave 行时对物质扇区抽查",
            "condition_check": "物质载体 = v1 冻结走行物质半裸 walk(无约束"
                               "装配层、无 slave 行机器)=> 不触发",
            "revival": "物质扇区引入 slave 行约束装配即复活"},
        "gun8_Z_mu_carrier": {
            "status": "记名退役",
            "reason": "候选无 Z_μ 辅助场(靶不存在)",
            "revival": "未来变体引入任何辅助场即强制复活(v1 评审原话:辅助场"
                       "是最容易夹带私货的地方)"},
        "c5_v1_trace_row_triplet": {
            "status": "记名退役(自动裁定,candidate CERT-E)",
            "trace_row_processing_present": trace_row,
            "auto_adjudication_verbatim":
                CJ["CERT_E_trace_row_detection"]["auto_adjudication"]
                ["condition_for_guns_header"],
            "verdict": CJ["CERT_E_trace_row_detection"]["auto_adjudication"]
                ["verdict_now"]}}
    write_json(payload)
    log("[REG] lag shot: overgrowth=%.2e H_drift=%.1f -> %s; 退役表照裁入册"
        % (gmax, driftl, "捕获" if reg_caught else "未捕获!"))

    # ---- 三正控 ------------------------------------------------------------
    tg = time.time()
    cand1 = C.control_candidates()["row1_r30"]
    row1 = C.row1_r30(G.evaluate_v2_candidate(cand1))
    p0a_ok = bool(row1["pass"] and row1["max_abs_diff"] <= TOL_JUDGE)
    m1_hashes_ok = all(checked[rel]["match"] for rel in (
        "data/results/v2m1_candidate.json",
        "data/results/v2m1_maxwell_loop_r3.json",
        "data/results/v2m1_guns_r2.json"))
    cand2 = C.control_candidates()["row2_r23"]
    row2 = C.row2_r23(G.evaluate_v2_candidate(cand2))
    p0b_ok = bool(m1_hashes_ok and row2["pass"]
                  and row2["max_abs_diff"] <= TOL_JUDGE)
    cand5 = C.control_candidates()["row5_frozen_walk"]
    row5 = C.row5_frozen_walk(G.evaluate_v2_candidate(cand5))
    cand4 = C.control_candidates()["row4_teeth"]
    row4 = C.row4_teeth(G.evaluate_v2_candidate(cand4))
    p0c_ok = bool(row5["pass"] and row4["pass"])
    p0_ok = bool(p0a_ok and p0b_ok and p0c_ok)
    payload["p0_positive_controls"] = {
        "a_r30_geometry_anchor": {
            "n_prop_seq": row1["remeasured"]["n_prop_seq"],
            "epsilon_dof": row1["remeasured"]["epsilon_dof"],
            "max_abs_diff": row1["max_abs_diff"], "pass": p0a_ok},
        "b_m1_closed_loop_lineage": {
            "hash_readonly_three_files": m1_hashes_ok,
            "row2_r23_max_abs_diff": row2["max_abs_diff"],
            "note": "引用而非重跑长跑(任务书 §4.3):hash 逐位 + 同评估器"
                    "符号层对拍", "pass": p0b_ok},
        "c_negative_controls": {
            "row5_frozen_walk": {
                "N_prop": row5["remeasured"]["N_prop"],
                "walk_factor_max_diff":
                    row5["remeasured"]["walk_factor_max_diff"],
                "basis_drift_max": row5["remeasured"]["basis_drift_max"],
                "pass": row5["pass"]},
            "row4_teeth": {"n_prop_all": row4["remeasured"]["n_prop_all"],
                           "pass": row4["pass"]},
            "pass": p0c_ok},
        "pass": p0_ok, "seconds": time.time() - tg}
    write_json(payload)
    log("[P0] a: n_prop=%s diff=%.1e; b: hash=%s row2=%.1e; c: walk=%s "
        "teeth=%s -> %s"
        % (row1["remeasured"]["n_prop_seq"], row1["max_abs_diff"],
           m1_hashes_ok, row2["max_abs_diff"], row5["remeasured"]["N_prop"],
           row4["remeasured"]["n_prop_all"], "全绿" if p0_ok else "FAIL"))

    # ---- endurance 负控列(报告级)-----------------------------------------
    tg = time.time()
    rnge = np.random.default_rng(END_SEED_R3)
    he = (rnge.standard_normal((10, END_TRIALS, END_L, END_L, END_L))
          + 1j * rnge.standard_normal((10, END_TRIALS, END_L, END_L, END_L)))
    pe = np.zeros_like(he)
    psi = (rnge.standard_normal((2, END_TRIALS, END_L, END_L, END_L))
           + 1j * rnge.standard_normal((2, END_TRIALS, END_L, END_L, END_L)))

    def matter_step(psi):
        a0, b1_0, b2_0, b3_0 = RS.walk_mult(psi[0])
        a1, b1_1, b2_1, b3_1 = RS.walk_mult(psi[1])
        p0 = a0 - 1j * (b3_0 + (b1_1 - 1j * b2_1))
        p1 = a1 - 1j * ((b1_0 + 1j * b2_0) - b3_1)
        return np.stack([p0, p1])

    rms0 = float(np.sqrt(np.mean(np.abs(he) ** 2)))
    nm0 = float(np.sqrt(np.mean(np.abs(psi) ** 2)))
    H0e, drift_e = None, 0.0
    rms_hist = []
    for t in range(1, END_T + 1):
        he, pe = geo_step(he, pe)
        psi = matter_step(psi)
        if t % 1000 == 0 or t == END_T:
            e = energy_H(he, pe, DT)
            if H0e is None:
                H0e = e
            drift_e = max(drift_e, abs(e - H0e) / (abs(H0e) + 1e-300))
            rms_hist.append([t, float(np.sqrt(np.mean(np.abs(he) ** 2)))
                             / rms0])
    rms_growth = rms_hist[-1][1]
    nmE = float(np.sqrt(np.mean(np.abs(psi) ** 2))) / nm0
    rms_ok = bool(END_RMS_BAND[0] <= rms_growth <= END_RMS_BAND[1])
    endurance = {
        "protocol": "L=%d trials=%d T=%d 纯 rule 定长跑(几何 staggered "
                    "leapfrog + 物质走行并行)seed=%d(新)"
                    % (END_L, END_TRIALS, END_T, END_SEED_R3),
        "H_drift_rel": drift_e,
        "rms_growth_geo": rms_growth,
        "rms_checkpoints": rms_hist[::2] + [rms_hist[-1]],
        "matter_norm_growth": nmE,
        "rms_in_band_report": rms_ok,
        "note": "负控列,报告级,不作 PASS 依据(任务书 G7 行;北极星 §四分层"
                "归纳条);异常如实入册",
        "seconds": time.time() - tg}
    payload["endurance_negative_control"] = endurance
    write_json(payload)
    log("[END] H=%.1e rms=%.3f mat_norm=%.6f (%.0fs)"
        % (drift_e, rms_growth, nmE, endurance["seconds"]))

    # ---- 判定(分支写死)---------------------------------------------------
    all_guns_fail = all(guns[k]["FAILS_as_required"] for k in (
        "C1_tr_sign_zero", "C2_wrong_sign_onsite_source", "C3_cocone_detune",
        "C4_integer_placement", "C5_no_clearance_no_sponge"))
    payload["all_guns_fail_as_required"] = all_guns_fail
    payload["regression_shot_caught"] = reg_caught
    payload["p0_all_green"] = p0_ok
    ok = bool(all_guns_fail and reg_caught and p0_ok)
    payload["verdict"] = (
        ("五主炮全部按预期病灶击穿(C1 迹结构 / C2 源链 / C3 共锥纽带 / C4 "
         "div curl=0 地基 / C5 清除归纳地基)+ 滞后阻尼回归抽查捕获 + 退役表"
         "照候选证书自动裁定入册 + 三正控全绿 + endurance 负控入册,全新种子,"
         "零双向内容(裁定三)。按红线 12:不宣告 M2' PASS——判定 = 全门 + "
         "全炮 + eps 分扇区 + 双环境四者同时,收口在车道A 复核四件 + PI。"
         "无任何涌现主张;eps_geo=0 如实记账;v1 封存主句原样不动。")
        if ok else
        ("FAIL-STOP-toothless:炮组未全击穿或回归抽查未捕获或 P0 未全绿"
         "(C1=%s C2=%s C3=%s C4=%s C5=%s REG=%s P0=%s)。按脚本头分支写死:"
         "如实入册报车道A/PI,不得再改实验、不得调线。"
         % (guns["C1_tr_sign_zero"]["FAILS_as_required"],
            guns["C2_wrong_sign_onsite_source"]["FAILS_as_required"],
            guns["C3_cocone_detune"]["FAILS_as_required"],
            guns["C4_integer_placement"]["FAILS_as_required"],
            guns["C5_no_clearance_no_sponge"]["FAILS_as_required"],
            reg_caught, p0_ok)))
    payload["status"] = "DONE" if ok else "FAIL-STOP-toothless"
    payload["sandbox"] = {"status": "PENDING",
                          "note": "双环境判据字段比对归车道A 复核(判据字段 "
                                  "1e-12)"}
    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)

    # ---- dashboard 泳道 v2m2_state.json(任务书 §7 schema;lit:false)-------
    if ok:
        pf = {}
        if os.path.exists(PREFLIGHT_JSON):
            pf = {"status": "DONE(在册)",
                  "sha256": sha256_file(PREFLIGHT_JSON)}
        gate_columns = {}
        for gk, gv in CL["verdict_table"].items():
            gate_columns[gk] = {"verdict": gv}
        gate_columns["M2-G1"] = {
            "verdict": "PASS",
            "note": "轮 2 原始记录 FAIL(数据级共锥子判据)保留不改写;裁定一:"
                    "非门,按预注册核判 PASS;Δω 体对角标度补测 "
                    "a:SCALING-CONFIRMED(v2m2_dw_scaling_results.json)"}
        gate_columns["M2-G6"] = {
            "verdict": "PASS",
            "note": "轮 2 σ-ii 排零原判 FAIL 保留不改写;裁定二 D-M2-6 口径"
                    "双控制过 + 独立重判 REJUDGE-PASS(v2m2_dm26_results.json)"}
        state_doc = {
            "_schema": "v2m2_state v1 (2026-07-27, lane B, M2' 轮 3)",
            "_doc": {
                "purpose": "dashboard_v2 spin2 泳道唯一数据源(任务书 §7;"
                           "文件缺失时泳道保持待点火)",
                "m2_status": "泳道三态:待点火/执行中/点亮;点亮(lit)须 M2' "
                             "PASS 四条齐 + 车道A 复核四件 + PI 收口——本文件"
                             "为 lane B 执行中交付(单环境),lit:false"
                             "(M1' 先例语义)"},
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "experiments/v2m2_guns.py(轮 3 炮组交付收拢)",
            "backend": "numpy fp64",
            "environment": env,
            "lit": False,
            "m2_status": {
                "lane_b": "R3-GUNS-DELIVERED(轮 2 8/8 落定(三裁+两补测)+ "
                          "五主炮击穿 + 回归抽查捕获 + 三正控全绿 + endurance "
                          "负控入册,宿主单环境)",
                "swimlane_state": "执行中(非点亮)",
                "pending": ["双环境(沙盒)判据字段比对", "车道A 复核四件"
                            "(沙盒双跑/炮组重放/同一次运行审计/eps 记账审计)",
                            "PI 收口签字"],
                "wording": "不宣告 M2' PASS;禁句'自旋 2 涌现';v1 封存主句"
                           "原样不动(红线 10/11/12)"},
            "gate_columns": gate_columns,
            "round2_settlement": {
                "original_verdict_table_as_recorded": CL["verdict_table"],
                "adjudication": "v2-裁定-M2轮2三裁-2026-07-27(G1 非门不计数,"
                                "G6 计数清结)+ 补测两件全过 -> 8/8"},
            "guns": [{"name": k, "FAILS_as_required":
                      guns[k]["FAILS_as_required"],
                      "lesion": guns[k]["lesion_located"]}
                     for k in ("C1_tr_sign_zero",
                               "C2_wrong_sign_onsite_source",
                               "C3_cocone_detune", "C4_integer_placement",
                               "C5_no_clearance_no_sponge")],
            "demotion_retirement": {
                "lagged_damping": "降级回归抽查一发(捕获)",
                "slave_0nu": "条件不满足记名不跑",
                "Z_mu": "记名退役",
                "trace_row_triplet": "记名退役(CERT-E 自动裁定,"
                                     "trace_row=false)"},
            "p0_positive_control": {
                "pass": p0_ok,
                "a_r30_diff": row1["max_abs_diff"],
                "b_row2_diff": row2["max_abs_diff"],
                "c_walk_nprop": row5["remeasured"]["N_prop"],
                "c_teeth_nprop": row4["remeasured"]["n_prop_all"]},
            "endurance_negative_control": {
                "H_drift_rel": endurance["H_drift_rel"],
                "rms_growth_geo": endurance["rms_growth_geo"],
                "matter_norm_growth": endurance["matter_norm_growth"]},
            "preflight": pf,
            "epsilon_sigma_point": {
                "eps_geo": 0.0, "eps_mat": 1.0,
                "sigma": {"branch_i_sourcefree": "A=0 精确约束线(轮 2 全 L "
                                                 "darkness <= 1e-12)",
                          "branch_ii_sourced": "D-M2-6 重判 PASS(截断稳健双测"
                                               "同判截断污染;alpha=1.96)"},
                "status": "实测闭环级读数(lane B 轮 2 + 三裁落定);落图动作"
                          "待车道A 复核 + PI 收口(任务书 §7);分扇区记账,"
                          "禁单一混合 eps(红线 11)"},
            "hashes": {
                "v2m2_candidate.json": checked[
                    "data/results/v2m2_candidate.json"]["sha256"],
                "v2m2_coupled_loop.json": checked[
                    "data/results/v2m2_coupled_loop.json"]["sha256"],
                "v2m2_dw_scaling_results.json": checked[
                    "data/results/v2m2_dw_scaling_results.json"]["sha256"],
                "v2m2_dm26_results.json": checked[
                    "data/results/v2m2_dm26_results.json"]["sha256"],
                "v2m2_guns.json": jsha,
                "construction_sha256": CONSTRUCTION_SHA256,
                "v2m2_guns.py": payload["source_sha256"]},
            "sandbox": {"status": "PENDING"},
        }
        write_json(state_doc, STATE_OUT)
        log("[state] %s 写入(泳道=执行中,lit:false)" % STATE_OUT)

    log("=" * 74)
    log("VERDICT: %s" % payload["verdict"])
    log("source  sha256 = %s" % payload["source_sha256"])
    log("results sha256 = %s" % jsha)
    log("total %.0fs" % payload["total_seconds"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
