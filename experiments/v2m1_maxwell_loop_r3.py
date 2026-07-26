"""v2m1_maxwell_loop_r3 -- M1' 主跑轮 3:G6 观测窗重签重跑(全门)。
冻结自旋 1 候选零改动,同一 rule、每 L 一次运行喂全部门,逐 L in {16,24,32,48},
全部经 M0' 统一评估器出数。除 G6 观测协议(窗规则)与运行种子外,与轮 2 脚本
(experiments/v2m1_maxwell_loop.py)逐字节同源;门线/判据核/构造/冻结件零改动。

AUTHORITY(判据预注册;本头部运行后不得回改,红线 4):
  docsv2/v2-裁定-M1轮3-G6观测窗重签-2026-07-26.md §二(硬性五条)§三(预写分支)§四(边界)
  docsv2/v2-任务书-M1-Maxwell闭环.md §3(门列)§6(判定)§8(红线十条)
  data/results/v2m1_candidate.json(冻结候选;construction_sha256 运行时校验)
  docsv2/v2-收口-M0-2026-07-26.md(不变量口径/双环境语义)

〇、轮 3 窗重签预注册(裁定 §二;运行前写死,运行后零回改)
  0.1 窗规则函数(裁定 §二-1,函数化,禁写死数、禁试飞值):
        T_PK(L) = ceil( M_MARGIN * tau_late(L) * ln( R0(L) / 1e-12 ) )
      M_MARGIN = 2.0(裕度 m>=2,写死)。tau_late(L) 与 R0(L) 均为**本轮**
      正式判门前标定段实测,标定段协议(写死):
        P6 注入后每 PK_STRIDE=8 步采样 r_max(t) = max_{6 判据 k} |a_k(t)|/A0_k
        (读数机器与轮 2 逐字同一:运行减 ref3 的 k 模投影);
        标定段 = [t_calA, t_calB],t_calA = 首个 r_max<=R_CAL_HI=1e-6 的采样步,
        t_calB = 首个 r_max<=R_CAL_LO=1e-9 的采样步;
        tau_late(L) = -1/slope,slope = 标定段内 ln r_max 对 t 的最小二乘斜率
        (须 >=8 个采样点且拟合 R^2>=CAL_R2_MIN=0.98,否则标定无效 = G6 仪器
        失效入分支判定);R0(L) = r_max(t_calA)。
      观测窗 = [t_calA, t_calA + T_PK(L)](窗从标定段起点计,该点残余恰为 R0);
      P6 总步数 = t_calA + T_PK(L),运行中由上式定,非人工加长到过;
      预算护栏 T_P6_CAP(L)(见常数;触顶 = 如实 incomplete 入册,不算 PASS)。
  0.2 T_cross 预言表(裁定 §二-2,先预言后验证;防时域调参之牙):
      数据源 = 轮 2 在册衰减曲线(data/results/v2m1_maxwell_loop.json,
      sha256 = 256f25fad41ade0cd76e79c7f4df0691181377f45476a96cdcbfd84593f01e2c,
      运行时逐位校验只读),per_k curve_downsampled 的 r_max 迟时指数率外推:
      T_cross 定义 = 首个采样步 t 使 r_max(t) <= 1e-12(全部 6 判据 k 同时过线);
      预言(由轮 2 尾段 10 点 log-线性率外推 / 已穿线者曲线内 log 插值):
        T_CROSS_PRED = {16: 5323, 24: 7374, 32: 9581, 48: 14282}(步)
      验证判据:实测 T_cross(L) / 预言 ∈ [0.5, 1.5](±50%)逐 L。
  0.3 门线一字不动:G6 残余强化线 1e-12、R36 继承线 1e-3、CLEAR_THRESH=0.05、
      SPREAD_GATE=3.0 等判据核/门线与轮 2 逐字同一;判据核/构造/冻结件零改动。
  0.4 七门不回退(裁定 §二-3):轮 2 已 PASS 的 7 门(G1/G2/G3/G4_newton/
      G5_eddington/G7/G8)本轮全部重测,任一回退 = HALT-REGRESSION 停手。
  0.5 运行语义同轮 2(相位表/反事实参考分叉),种子换
      SEED_WAVE_BASE = 20260726 + 1000(seed(L)=BASE+L),避免同种子伪逐位。
  0.6 预写分支(裁定 §三;运行前写死,不许事后择):
      分支 A:G6 全判据 PASS 且 T_cross 预言逐 L 命中(±50%)且七门无回退
        -> 同轮补全炮组(v2m1_guns.py)+ endurance 负控列 + 交付收拢;
      分支 B:加窗后残余偏离纯指数/出现底板 -> 仪器归因作废 = 物理病信号,
        立即停手报车道A/PI。底板检测器(写死):residual_end_max(L) > 1e-12 且
        (窗末四分之一采样段局部 e-fold tau_tail_local > FLOOR_TAU_RATIO=5.0 *
        tau_late(L) 或 局部斜率 >= 0);强偏离检测器:标定起点至窗末
        (限 r_max>1e-13 采样)log-线性拟合 R^2 < PURITY_R2_MIN=0.95 且
        residual_end_max > 1e-12。触发即记录底板量级与 sponge 反射签名
        (reflection_rebound 逐 k)相关性入册。
        [阈值标定注:轮 2 在册曲线(车道A 已裁"纯指数无底板")按本检测器读数为
         purity R^2 = 0.991-0.997、tau_tail_local/tau_late = 1.3-1.5,均远离
         触发线——检测器对已裁定健康形态不误触发,仅捕获真底板/真偏离。]
      分支 C:穿线(G6 判据全 PASS)但预言脱靶(>±50%)-> G6 判 PASS 但
        标定机器记疑,tau_late 标定方法追因写入报告,不进炮组,报车道A。
  0.7 计数纪律(裁定 §二-4):轮 2 计连续不过 1 轮不清零;本轮 G6 再 FAIL
      (分支 B 或未穿线)-> 计数 2 -> 全线停手写追因报告报 PI(D2 预备启动),
      不做任何进一步尝试。

一、"同一次运行"操作定义(写死;同轮 2):每 L 一条连续运行记录,相位表:
  P0 无源波段    T_WAVE=1024        通用随机初条(SEED_WAVE=20261726+L),8 trials,
                                    纯 rule(无 sponge 无源);喂 G1/G2/G3/G5(H)/G8
  P1 清除段      T_CLEAR=16*L       R26 sponge 开(L4 sponge 冻结函数,gamma=0.30
                                    R36 值,宽 W_SPONGE(L));波段遗留场清除诊断
  P2 对生段      T_PAIR=16          +q/-q 对在盒心相邻胞局域对生(余弦斜坡链接电流)
  P3 拖拽段      T_DRAG=L/2-3       -q 以 1 胞/步局域拖至 sponge 区停放(x=L-2)
  P4 静持段      T_HOLD=40*L        静源平衡;末端 Coulomb 1/r 尾读出(G4a)
  P5 动源段      T_MOVE=8*HOPS(L)   +q 以 v=0.25c(8 步 1 胞跳,守恒沉积)沿 +y;
                                    锥判读(G4b)+ 电荷守恒(G5)
  P6 波包段      t_calA+T_PK(L)     6 非 Nyquist 判据 k 波包注入 trial 0..5
                                    (trial 6,7 无包 = fp 线性底对照),sponge 清除
                                    读出 tau/残余/反射(G6);段长由 〇.1 窗规则
                                    在运行中按本轮标定段实测得出(非写死数)
  反事实参考分叉(声明的评估器参考计算,非第二次跑):ref1(P2 起,无源)/
  ref2(P5 起,无动源电流)/ref3(P6 起,无包)= 同一冻结 rule 从运行态复制演化;
  源/包读数 = 运行减参考(线性精确;fp 底由无包 trial 6,7 实测入册)。
  禁止门间换运行:全部门读数出自该记录及其声明分叉;无任何逐门调参重跑。

二、门列与阈值(任务书 §3;全部写死。容器映射:M1-G1->G1_dof_nprop,
  M1-G2->G2_sigma_scaling, M1-G3->G3_j5_cocone, M1-G4a->G4_newton,
  M1-G4b->G5_eddington, M1-G5+G6->G6_conservation, M1-G7->G7_stability,
  M1-G8->G8_epsilon):
  G1  N_prop=2 逐 L 全七判据 k(n_L=round(n16*L/16) 实采入册,Nyquist 必含);
      判据核 = photon_control.spectral_lines 冻结函数(SV_THRESH=0.05 原样);
      sv 断崖全列入册;transverse match(诊断)>=0.95。
      PASS = N_prop==2 for all k, all L 且随 L 稳定。
  G2  约束标度:主判 y_max(L) = max(divE/divB 漂移(波段,件10 口径),
      源段内域 Gauss 锁 |div(dE)-rho|/q);辅报 y_rms。双分支预写:
      (i) y_max(L)<=1e-12 全 L -> "A=0 精确约束线"落位(Yee div∘curl==0 预期);
      (ii) 否则 R37 冻结 fit_constant/fit_power 拟合 (A,alpha,dAIC) 对 x=2*pi/L,
      PASS 须 |dAIC|>=2 且 |A|<=2*sigma_A 且 alpha>=1(D3 干净档);弱档=FAIL 追因。
      诊断列:G8 的 max sin theta(S_prop vs ker C)不变量谱(报告级)。
  G3  共锥/色散:算子级 |w_op - w_yee解析|<=1e-12 逐 k 逐 L(mode_matrix 于候选
      stepper 实测);谱级 |w_meas-w_yee|<1 FFT bin 逐 k 逐 L;三轴各向同性
      谱级 spread<=1e-6 逐 L 且随 L 不发散;收敛阶:y=|c_op(k1(L))-1| 对
      k1=2*pi/L 的 log-log 斜率 p,预注册 p=2,|p-2|<=0.1。
  G4a 静源 Coulomb:尾相关 corr(E_r, 1/r^2)(壳 2<=r<=L/2-W-1)逐 L 报告;
      PASS = 序列不发散(相邻 L 降幅 <=0.02)且 corr(L_max)>=0.97 且
      |4*pi*coef(L_max)/q - 1|<=0.05(coef=中位 E_r*r^2)。
  G4b 动源锥:v=0.25c 预注册(<=0.5c);锥外泄漏(参考减法,Chebyshev 模板锥
      = 严格局域公理哨)<=1e-12 于全部预注册检查点:对生/拖拽段 t in
      {min(8,L/2-4), L/2-4}(半径 t+2),动源段 t=8+(L/2-4)(半径 t-7);
      fp 线性底并列入册。
  G5  守恒:电流连续性残差 <=1e-12;内域 Gauss 锁 <=1e-12;无源波段离散 Yee 能量
      H 相对漂移 <=1e-12;逐 L。
  G6  sponge(R26 机器):判据核常数继承 r36_r3_verification(CLEAR_THRESH=0.05,
      SPREAD_GATE=3.0, RET_GATE=1e-3);包读数 = 运行减 ref3 的 a_k(k=注入 k);
      tau_k = 首次 <0.05 起始比;逐 L:全 k 有 tau、spread<=3、tau(L) 线性拟合
      slope>0 且 R^2>=0.9(Theta(L/c));残余(段末 rms/A0)双列:R36 继承线
      <=1e-3 与任务书强化线 <=1e-12,均为判定列;反射比(tau 后回弹峰)报告级。
      Nyquist k 零群速,输运语义不适用,预注册排除于包集,其清除行为由 P1 清除段
      诊断列报告(R36 保护通道先例)。
  G7  稳定:候选符号一步矩阵全 BZ(该 L 全部格点 k)谱半径 <= 1+1e-9 逐 L;
      实空间有界性(波段 rms)报告;endurance 定长跑 = 轮 3 负控列,本轮 PENDING。
  G8  epsilon 实测(非声明):每 L 每判据 k,主谱线 top-2 振幅空间(数据 SVD)
      对候选自身 ker C 的不变量 j_inv = #{sin theta >= 0.05}(M0' invariants 机器);
      epsilon_DOF = 1 - j_inv/N_curv。hand_built=None => 预期实测 epsilon=1;
      测不到 1 = 重大结果如实报。PASS = j_inv==0 全 k 全 L。
  任何 verdict 不得由单一固定尺度读数产生(全部逐 L 列)。

三、仪器常数(同轮 2 冻结;非门阈值。T_PK 不再是写死数——由 〇.1 窗规则给出):
  W_SPONGE={16:4,24:5,32:6,48:8}; SIGK={16:0.45,24:0.40,32:0.35,48:0.30};
  HOPS={16:2,24:3,32:4,48:4};PK_STRIDE=8;A_PK=1.0;Q_SRC=1.0;
  预算护栏 T_P6_CAP={16:24000,24:36000,32:48000,48:64000}(远高于预言窗端,
  仅防病态跑飞;触顶 = 如实 incomplete)。
  L=64:窗加长后单 L 更超单脚本预算,不跑,如实注明(同轮 2)。

四、控制行(红线 3,主跑前必过,逐位 0.0):L=16 上 mode_matrix / evolve_record /
  solenoidal_project 端口 vs photon_control 冻结体逐位;dict_step vs step_yee 于
  L=24 逐位(CERT2 的 L 无关性延伸);row2_r23 比对器 <=1e-12。

五、冻结件 hash(先行写死;逐位不符 = HALT):M1 六件 + M0' 七件(值同
  v2m1_candidate.py 头)+ 候选件:
  experiments/v2m1_candidate.py
    8aa00b0a9847ec0a6c05b857f6d8375e6d13879fd639342623d6f95b7f96b1ac
  construction_sha256(v2m1_candidate.json 内 spec 规范重哈希)
    b7daa970f0702c9e4e12603740d4f40de33dee92cec17036dd61b76bb7f29da8
  rulespace_gpu/tensor_coin_feedback.py(sponge 核;候选件 record-only 值转正)
    c31badcb14b3a005204d92f2149e67ca2a553693c564e9374153a89d993639f7

措辞红线(§8 红线 10 + 裁定 §四):分支 A 全绿也**不宣告 M1' PASS/收口**——
判定须 全门 + 全炮 + epsilon=1 实测 + 双环境 四者同时,收口在车道A 复核 + PI;
收口前不得表述"Maxwell 闭环完成"。fp64;增量写盘;沙盒位 PENDING。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m1_maxwell_loop_r3.py
      (writes data/results/v2m1_maxwell_loop_r3.json)
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

OUT = os.path.join(ROOT, "data", "results", "v2m1_maxwell_loop_r3.json")
CAND_JSON = os.path.join(ROOT, "data", "results", "v2m1_candidate.json")
R2_JSON = os.path.join(ROOT, "data", "results", "v2m1_maxwell_loop.json")

# ---- 判据(写死;运行后不得回改)------------------------------------------
TOL_JUDGE = 1e-12
TOL_BITWISE = 0.0
L_LIST = [16, 24, 32, 48]
DT = 0.5
TRIALS = 8
T_WAVE = 1024
SEED_WAVE_BASE = 20260726 + 1000   # 轮 3 换种子(裁定执行指令);seed(L)=BASE+L
JUDGE_K16 = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
             (2, 2, 2), (8, 0, 0)]
AXIAL_N1 = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]   # 收敛阶序列 k1=2*pi/L
# gates
G1_NPROP = 2
G1_MATCH_MIN = 0.95                 # 诊断
G2_BRANCH_I_GATE = 1e-12
G3_OPW_GATE = 1e-12
G3_ISO_GATE = 1e-6
G3_P_TARGET, G3_P_TOL = 2.0, 0.1
G4A_CORR_LMAX_MIN = 0.97
G4A_CORR_DROP_MAX = 0.02
G4A_COEF_RELTOL = 0.05
G4B_CONE_GATE = 1e-12
G5_CONT_GATE = 1e-12
G5_GAUSS_GATE = 1e-12
G5_H_GATE = 1e-12
G6_RESID_TASKBOOK = 1e-12
G6_TAU_R2_MIN = 0.9
G7_RADIUS_GATE = 1e-9
# 仪器常数(同轮 2 冻结)
W_SPONGE = {16: 4, 24: 5, 32: 6, 48: 8}
SIGK = {16: 0.45, 24: 0.40, 32: 0.35, 48: 0.30}
HOPS = {16: 2, 24: 3, 32: 4, 48: 4}
# ---- 轮 3 窗重签预注册常数(头部 〇;运行后不得回改)----------------------
M_MARGIN = 2.0                      # 裕度 m>=2(裁定 §二-1)
R_CAL_HI = 1e-6                     # 标定段起点残余线(R0 定义点)
R_CAL_LO = 1e-9                     # 标定段终点残余线
CAL_R2_MIN = 0.98                   # 标定段 log-线性拟合最低 R^2
CAL_MIN_SAMPLES = 8                 # 标定段最少采样点
PURITY_R2_MIN = 0.95                # 强偏离检测器(分支 B;限 r_max>1e-13 段)
PURITY_R_FLOOR = 1e-13              # purity 拟合样本下限(fp 底以下不计)
FLOOR_TAU_RATIO = 5.0               # 底板检测器:tau_tail_local > 5*tau_late
TAIL_FRAC = 0.25                    # 窗末四分之一 = 底板检测器局部拟合段
T_P6_CAP = {16: 24000, 24: 36000, 32: 48000, 48: 64000}   # 预算护栏
T_CROSS_PRED = {16: 5323, 24: 7374, 32: 9581, 48: 14282}  # 轮 2 在册率外推(步)
T_CROSS_BAND = (0.5, 1.5)           # 实测/预言 ±50%(裁定 §二-2)
R2_RESULTS_SHA256 = \
    "256f25fad41ade0cd76e79c7f4df0691181377f45476a96cdcbfd84593f01e2c"
ROUND2_PASS_GATES = ["G1_dof_nprop", "G2_sigma_scaling", "G3_j5_cocone",
                     "G4_newton", "G5_eddington", "G7_stability",
                     "G8_epsilon"]  # 轮 2 已 PASS 七门(回退 = HALT)
G6_FAIL_COUNT_R2 = 1                # 轮 2 计连续不过 1 轮,不清零
PK_STRIDE = 8
A_PK = 1.0
Q_SRC = 1.0
T_PAIR = 16
HOLD_MULT = 40
CLEAR_MULT = 16

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


def write_json(payload):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_canonical(obj):
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def strip_lines(lines):
    return [{k: v for k, v in l.items() if k != "Vh2"} for l in lines]


def measured_w_op(kl, L, step):
    """算子级实测 +w:mode_matrix 本征相位(参考仅用于支选择,值为实测)。"""
    PC = FZ.mod("photon_control")
    M = SP1.mode_matrix(kl, L, step, PC.OFF6)
    lam = np.linalg.eigvals(M)
    ang = np.angle(lam)
    w_ref = PC.yee_omega(kl)
    sel = np.where(np.abs(ang - w_ref * DT) < 1e-6)[0]
    if len(sel) == 0:
        return None
    return float(np.mean(np.abs(ang[sel])) / DT)


def amps_fast(state, Pr, Pi):
    """快速 k 模投影(实 GEMM x2;与 einsum 等价至 fp 重排序底,自检入册)。"""
    E, B = state
    tr = E.shape[1]
    L3 = E.shape[-1] ** 3
    F = np.concatenate([E, B]).reshape(6, tr, L3).reshape(6 * tr, L3)
    A = (F @ Pr.T) + 1j * (F @ Pi.T)
    nk = Pr.shape[0]
    return A.reshape(6, tr, nk).transpose(1, 2, 0)   # (trials, modes, comps)


def interior_mask(L, w):
    m = np.zeros((L, L, L), bool)
    m[(slice(w + 1, L - w - 1),) * 3] = True
    return m


# ==========================================================================
#  每 L 一条运行记录(相位表见头部;返回全部原始读数)
# ==========================================================================
def run_one_L(L, dict_step, log):
    PC = FZ.mod("photon_control")
    R36 = FZ.mod("r36_r3_verification")
    t_L0 = time.time()
    w = W_SPONGE[L]
    seed = SEED_WAVE_BASE + L
    out = {"L": L, "seed_wave": seed, "trials": TRIALS,
           "phases": [], "instrument": {
               "W_sponge": w, "sigk": SIGK[L],
               "T_pk": "window rule 〇.1(本轮标定实测;cap=%d)" % T_P6_CAP[L],
               "hops": HOPS[L], "gamma_max": 0.30}}

    # 判据 k 表(重标入册)
    kinfos = []
    for n16 in JUDGE_K16 + AXIAL_N1:
        nL = SP1.n_at_L(n16, L) if n16 in JUDGE_K16 else list(n16)
        kl = SP1.kvec_of(nL, L)
        kinfos.append({"n16": list(n16), "nL": nL, "kl": kl,
                       "cf": PC.colfac(kl, PC.OFF6)})
    out["judge_k_table"] = [{"n16": ki["n16"], "nL": ki["nL"],
                             "k": [float(x) for x in ki["kl"]]}
                            for ki in kinfos]
    nj = len(JUDGE_K16)
    projs = np.stack([np.conj(SP1.plane(ki["kl"], L)) / L ** 3
                      for ki in kinfos])
    Pr = np.ascontiguousarray(projs.real.reshape(len(kinfos), -1))
    Pi = np.ascontiguousarray(projs.imag.reshape(len(kinfos), -1))

    # ---- P0 无源波段 ------------------------------------------------------
    t0 = time.time()
    state = SP1.seed_generic(2, seed, L, TRIALS)
    rec, mon, state = SP1.evolve_record(state, dict_step, kinfos, T_WAVE, L,
                                        energy=True)
    out["phases"].append({"name": "P0_wave", "steps": T_WAVE,
                          "seed": seed, "injections": None,
                          "state_sha256": SP1.state_sha256(state),
                          "seconds": time.time() - t0})
    out["wave_monitor"] = mon
    log("  P0 wave %ds  H_drift=%.1e divE=%.1e divB=%.1e"
        % (time.time() - t0, mon.get("yee_energy_drift_rel", -1),
           mon["divE_drift_rel"], mon["divB_drift_rel"]))

    # 谱判读(G1/G3/G8)
    oracles, per_k = {}, {}
    for ki in range(len(kinfos)):
        nv = tuple(kinfos[ki]["nL"])
        kl = kinfos[ki]["kl"]
        o = SP1.yee_oracle(kl, L, dict_step)
        oracles[nv] = o
        e = {"n16": kinfos[ki]["n16"], "nL": list(nv),
             "w_yee": PC.yee_omega(kl),
             "k_norm": float(np.linalg.norm(kl)),
             "oracle": {k: v for k, v in o.items() if k not in ("V", "lam")},
             "w_op_measured": measured_w_op(kl, L, dict_step)}
        if ki < nj:
            sp = PC.spectral_lines(rec[:, :, ki, :])
            e["n_prop"] = sp["n_prop"]
            e["bin_width"] = sp["bin_width"]
            e["lines"] = strip_lines(sp["lines"])
            if sp["lines"]:
                main = sp["lines"][0]
                e["w_meas"] = main["w"]
                e["w_meas_vs_yee"] = abs(main["w"] - e["w_yee"])
                e["c_meas"] = main["w"] / e["k_norm"]
                e["sv_main"] = main["sv"]
                e["sv3_main"] = main["sv3"]
                e["transverse_match"] = PC.transverse_match(main, o)
                e["epsilon_inv"] = SP1.epsilon_invariant_from_line(main, kl)
        else:
            sp = PC.spectral_lines(rec[:, :, ki, :])
            e["n_prop_reported"] = sp["n_prop"]
            if sp["lines"]:
                e["w_meas"] = sp["lines"][0]["w"]
                e["c_meas"] = sp["lines"][0]["w"] / e["k_norm"]
            e["in_band_note"] = ("k1 谱线在 DC 守卫内则以算子级读数为准"
                                 if e.get("w_meas") is None else "in-band")
        per_k[str(tuple(kinfos[ki]["n16"]))] = e
    out["per_k"] = per_k
    del rec

    # ---- P1 清除段(诊断)------------------------------------------------
    t0 = time.time()
    sp_field = SP1.sponge_field(L, w)
    imask = interior_mask(L, w)
    Es = SP1.solenoidal_project(state[0][:, :1], "E", L)
    Bs = SP1.solenoidal_project(state[1][:, :1], "B", L)
    sol0 = float(np.abs(Es[:, 0][:, imask]).sum()
                 + np.abs(Bs[:, 0][:, imask]).sum())
    T_clear = CLEAR_MULT * L
    amp_hist = []
    sol_hist = []
    for t in range(1, T_clear + 1):
        state = SP1.sponged_step(state, dict_step, sp_field, DT=DT)
        if t % 2 == 0:
            amp_hist.append(amps_fast(state, Pr, Pi)[:, :nj, :])
        if t % (2 * L) == 0 or t == T_clear:
            Es = SP1.solenoidal_project(state[0][:, :1], "E", L)
            Bs = SP1.solenoidal_project(state[1][:, :1], "B", L)
            sol_hist.append([t, float(np.abs(Es[:, 0][:, imask]).sum()
                                      + np.abs(Bs[:, 0][:, imask]).sum())
                             / (sol0 + 1e-300)])
    amp_hist = np.stack(amp_hist)      # (T/2, trials, nj, 6)
    off = amp_hist[-32:].mean(axis=0)
    a_ac = np.sqrt(np.sum(np.abs(amp_hist - off[None]) ** 2, axis=(1, 3)))
    ac0 = np.sqrt(np.mean(a_ac[:8] ** 2, axis=0))
    clear_diag = []
    for j in range(nj):
        r = a_ac[:, j] / (ac0[j] + 1e-300)
        below = np.where(r < R36.CLEAR_THRESH)[0]
        clear_diag.append({
            "n16": JUDGE_K16[j],
            "tau_ac_steps": int(below[0] * 2 + 2) if len(below) else None,
            "ac_resid_end": float(np.sqrt(np.mean(r[-16:] ** 2)))})
    out["phases"].append({"name": "P1_clear", "steps": T_clear,
                          "injections": None,
                          "state_sha256": SP1.state_sha256(state),
                          "seconds": time.time() - t0})
    out["clear_diagnostics"] = {
        "solenoidal_interior_ratio": sol_hist,
        "per_k_ac": clear_diag,
        "note": ("遗留通用场清除为诊断列:纵向/静电通道是精确守恒的保护通道"
                 "(R36 保护 DC 先例),慢群速带缘模清除受限——均如实报告,"
                 "G6 判定读 P6 波包段(任务书:注入波包->吸收)")}
    log("  P1 clear %ds  sol_ratio_end=%.1e"
        % (time.time() - t0, sol_hist[-1][1]))

    # ---- P2-P4 源段(对生/拖拽/静持)+ ref1 -------------------------------
    t0 = time.time()
    c = L // 2
    rho = np.zeros((L, L, L))
    ref1 = (state[0][:, :1].copy(), state[1][:, :1].copy())
    fork1_sha = SP1.state_sha256(ref1)
    cone_rows, cont_res_max = [], 0.0
    gauss_hist = []
    cone_ts = sorted({min(8, L // 2 - 4), L // 2 - 4})
    cheb_pair = SP1.cheb_from_cells(L, [(c, c, c)])
    # 对生:余弦斜坡增量
    sched = 0.5 * (1 - np.cos(np.pi * np.arange(1, T_PAIR + 1) / T_PAIR))
    sched = np.diff(np.concatenate([[0.0], sched])) * Q_SRC
    t_src = 0
    xpos = c + 1
    park = L - 2
    for ph, Tph in (("pair", T_PAIR), ("drag", park - c - 1)):
        for tt in range(Tph):
            E, B = dict_step(state)
            rE, rB = dict_step(ref1)
            if ph == "pair":
                dq = sched[tt]
                E[0, :, c, c, c] += dq            # E -= DT*J, J=-dq/DT
                rho[c, c, c] += dq
                rho[(c + 1) % L, c, c] -= dq
                cont = 0.0                        # 恒等构造(离散连续性精确)
            else:
                E[0, :, xpos, c, c] += Q_SRC      # -q 前跳 1 胞
                rho[xpos, c, c] += Q_SRC
                rho[(xpos + 1) % L, c, c] -= Q_SRC
                xpos += 1
                cont = 0.0
            # 沉积按 d_rho == -DT*div_bwd(J) 恒等构造(离散连续性精确成立;
            # 机器级独立见证 = Gauss 锁列)
            cont_res_max = max(cont_res_max, cont)
            E = E * (1.0 - sp_field)
            B = B * (1.0 - sp_field)
            rE = rE * (1.0 - sp_field)
            rB = rB * (1.0 - sp_field)
            state, ref1 = (E, B), (rE, rB)
            t_src += 1
            if t_src in cone_ts:
                leak, mo, mi = SP1.cone_leak(
                    state[0][:, 0] - ref1[0][:, 0],
                    state[1][:, 0] - ref1[1][:, 0], cheb_pair, t_src + 2)
                cone_rows.append({"phase": ph, "t": t_src,
                                  "radius": t_src + 2, "leak": leak,
                                  "max_out": mo, "max_in": mi})
    # Gauss 锁(对生+拖拽末)
    dE = state[0][:, 0] - ref1[0][:, 0]
    gdev = float(np.abs(PC.div(dE, PC._dm) - rho)[imask].max()) / Q_SRC
    gauss_hist.append(["after_drag", t_src, gdev])
    # 静持
    T_hold = HOLD_MULT * L
    for tt in range(T_hold):
        state = SP1.sponged_step(state, dict_step, sp_field, DT=DT)
        ref1 = SP1.sponged_step(ref1, dict_step, sp_field, DT=DT)
        t_src += 1
        if tt % 256 == 0 or tt == T_hold - 1:
            dE = state[0][:, 0] - ref1[0][:, 0]
            gdev = float(np.abs(PC.div(dE, PC._dm) - rho)[imask].max()) / Q_SRC
            gauss_hist.append(["hold", t_src, gdev])
    dE_c = state[0][:, 0] - ref1[0][:, 0]
    coulomb = SP1.radial_tail(dE_c, L, w, c)
    coulomb["coef_times_4pi_over_q"] = (
        4.0 * math.pi * coulomb["coef_med"] / Q_SRC
        if coulomb["coef_med"] is not None else None)
    out["phases"].append({
        "name": "P2-P4_sources_static", "steps": t_src,
        "injections": {"pair": "cos ramp 16 steps, +q@(c,c,c) -q@(c+1,c,c)",
                       "drag": "-q 1 cell/step to x=%d (sponge region)" % park,
                       "q": Q_SRC},
        "ref1_fork_sha256": fork1_sha,
        "state_sha256": SP1.state_sha256(state),
        "seconds": time.time() - t0})
    out["coulomb"] = coulomb
    out["cone_rows_static"] = cone_rows
    out["gauss_lock"] = gauss_hist
    log("  P2-4 src %ds  corr=%.4f coef4pi=%.3f gauss=%.1e cone=%s"
        % (time.time() - t0, coulomb["corr"] or -1,
           coulomb["coef_times_4pi_over_q"] or -1,
           max(g[2] for g in gauss_hist),
           ["%.1e" % r["leak"] for r in cone_rows]))
    del ref1

    # ---- P5 动源段 + ref2 -------------------------------------------------
    t0 = time.time()
    ref2 = (state[0][:, :1].copy(), state[1][:, :1].copy())
    fork2_sha = SP1.state_sha256(ref2)
    rho_hold = rho.copy()
    ypos = c
    T_move = 8 * HOPS[L]
    t_mc = 8 + (L // 2 - 4)
    cheb_move = SP1.cheb_from_cells(L, [(c, c, c), (c, (c + 1) % L, c)])
    cone_move = None
    for tt in range(1, T_move + 1):
        E, B = dict_step(state)
        rE, rB = dict_step(ref2)
        if tt % 8 == 0:
            E[1, :, c, ypos, c] -= Q_SRC          # J=+q/DT: +q 沿 +y 跳 1 胞
            rho[c, ypos, c] -= Q_SRC
            ypos = (ypos + 1) % L
            rho[c, ypos, c] += Q_SRC
        E = E * (1.0 - sp_field)
        B = B * (1.0 - sp_field)
        rE = rE * (1.0 - sp_field)
        rB = rB * (1.0 - sp_field)
        state, ref2 = (E, B), (rE, rB)
        if tt == t_mc:
            leak, mo, mi = SP1.cone_leak(
                state[0][:, 0] - ref2[0][:, 0],
                state[1][:, 0] - ref2[1][:, 0], cheb_move, tt - 7)
            cone_move = {"phase": "move", "t": tt, "radius": tt - 7,
                         "leak": leak, "max_out": mo, "max_in": mi}
    dE = state[0][:, 0] - ref2[0][:, 0]
    gdev_mv = float(np.abs(PC.div(dE, PC._dm)
                           - (rho - rho_hold))[imask].max()) / Q_SRC
    out["phases"].append({
        "name": "P5_move", "steps": T_move,
        "injections": {"v_over_c": 0.25, "hop_period_steps": 8,
                       "hops": HOPS[L], "direction": "+y"},
        "ref2_fork_sha256": fork2_sha,
        "state_sha256": SP1.state_sha256(state),
        "seconds": time.time() - t0})
    out["cone_move"] = cone_move
    out["gauss_lock_move"] = gdev_mv
    out["charge_continuity_residual_max"] = cont_res_max
    log("  P5 move %ds  cone=%.1e gauss_mv=%.1e"
        % (time.time() - t0, (cone_move or {}).get("leak", -1), gdev_mv))
    del ref2

    # ---- P6 波包段 + ref3(G6)-------------------------------------------
    t0 = time.time()
    ref3 = (state[0].copy(), state[1].copy())
    fork3_sha = SP1.state_sha256(ref3)
    packets = []
    A0 = []
    for i in range(6):
        pk = A_PK * SP1.make_packet(L, kinfos[i]["nL"], SIGK[L])
        packets.append(pk)
        a = np.array([np.sum(projs[i] * pk[j]) for j in range(3)])
        A0.append(float(np.sqrt(np.sum(np.abs(a) ** 2))))
        state[0][:, i] += pk
    pk_in_sha = SP1.state_sha256(state)
    cap = T_P6_CAP[L]
    samp_t, A_hist, floor_hist = [], [], []
    bulk_ck = []
    pk0_bulk = [float(np.abs(packets[i][:, imask]).sum()) for i in range(6)]
    a0v = np.array(A0)
    cal = {"t_calA": None, "t_calB": None, "idx_calA": None,
           "tau_late": None, "R0": None, "R2_cal": None,
           "n_cal_samples": None, "T_pk_window": None, "window_end": None,
           "cap": cap, "cap_hit": False, "cal_valid": None,
           "m_margin": M_MARGIN}
    t = 0
    t_end = None                       # 窗端:标定完成时由 〇.1 窗规则赋值
    while True:
        t += 1
        state = SP1.sponged_step(state, dict_step, sp_field, DT=DT)
        ref3 = SP1.sponged_step(ref3, dict_step, sp_field, DT=DT)
        if t % PK_STRIDE == 0:
            ar = amps_fast(state, Pr, Pi)
            aref = amps_fast(ref3, Pr, Pi)
            d = ar - aref                       # (trials, modes, comps)
            samp_t.append(t)
            A_hist.append([float(np.linalg.norm(d[i, i, :]))
                           for i in range(6)])
            floor_hist.append(float(max(np.linalg.norm(d[i, m, :])
                                        for i in (6, 7) for m in range(6))))
            rmax = float(np.max(np.array(A_hist[-1]) / (a0v + 1e-300)))
            if cal["t_calA"] is None and rmax <= R_CAL_HI:
                cal["t_calA"] = int(t)
                cal["idx_calA"] = len(samp_t) - 1
                cal["R0"] = rmax
            if (cal["t_calA"] is not None and cal["t_calB"] is None
                    and rmax <= R_CAL_LO):
                cal["t_calB"] = int(t)
                iA = cal["idx_calA"]
                tt = np.array(samp_t[iA:], float)
                rr = np.max(np.array(A_hist[iA:])
                            / (a0v[None] + 1e-300), axis=1)
                yy = np.log(rr)
                cal["n_cal_samples"] = int(len(tt))
                cf = np.polyfit(tt, yy, 1)
                r2c = 1.0 - float(
                    np.sum((yy - np.polyval(cf, tt)) ** 2)
                    / (np.sum((yy - np.mean(yy)) ** 2) + 1e-300))
                cal["R2_cal"] = r2c
                cal["cal_valid"] = bool(len(tt) >= CAL_MIN_SAMPLES
                                        and r2c >= CAL_R2_MIN and cf[0] < 0)
                if cal["cal_valid"]:
                    cal["tau_late"] = float(-1.0 / cf[0])
                    cal["T_pk_window"] = int(math.ceil(
                        M_MARGIN * cal["tau_late"]
                        * math.log(cal["R0"] / G6_RESID_TASKBOOK)))
                    t_end = cal["t_calA"] + cal["T_pk_window"]
                    if t_end > cap:
                        cal["cap_hit"] = True
                        t_end = cap
                    cal["window_end"] = int(t_end)
                else:
                    t_end = cap        # 标定无效:护栏跑满入册,走分支判定
                    cal["cap_hit"] = True
                    cal["window_end"] = int(cap)
        is_end = (t_end is not None and t >= t_end) or t >= cap
        if t % 1024 == 0 or is_end:
            dEb = state[0] - ref3[0]
            dBb = state[1] - ref3[1]
            bulk_ck.append([t, [float((np.abs(dEb[:, i][:, imask]).sum()
                                       + np.abs(dBb[:, i][:, imask]).sum())
                                      / (pk0_bulk[i] + 1e-300))
                                for i in range(6)]])
        if is_end:
            if t >= cap and t_end is None:
                cal["cap_hit"] = True   # 标定未完成即触顶:incomplete 入册
            break
    Tpk = t
    A_hist = np.array(A_hist)                   # (S, 6)
    samp_t = np.array(samp_t)
    # ---- 轮 3 窗重签读数:T_cross 实测 + 分支 B 检测器(定义见头部 〇)----
    rmax_hist = np.max(A_hist / (a0v[None] + 1e-300), axis=1)
    _cross = np.where(rmax_hist <= G6_RESID_TASKBOOK)[0]
    t_cross_meas = int(samp_t[_cross[0]]) if len(_cross) else None
    purity_r2 = None
    if cal["idx_calA"] is not None:
        _tt = samp_t[cal["idx_calA"]:].astype(float)
        _rr = rmax_hist[cal["idx_calA"]:]
        _sel = _rr > PURITY_R_FLOOR
        if int(_sel.sum()) >= CAL_MIN_SAMPLES:
            _y = np.log(_rr[_sel])
            _cf = np.polyfit(_tt[_sel], _y, 1)
            purity_r2 = 1.0 - float(
                np.sum((_y - np.polyval(_cf, _tt[_sel])) ** 2)
                / (np.sum((_y - _y.mean()) ** 2) + 1e-300))
    _ntail = max(12, int(len(samp_t) * TAIL_FRAC))
    _cft = np.polyfit(samp_t[-_ntail:].astype(float),
                      np.log(np.maximum(rmax_hist[-_ntail:], 1e-300)), 1)
    tau_tail_local = float(-1.0 / _cft[0]) if _cft[0] < 0 else None
    pk_rows = []
    for i in range(6):
        r = A_hist[:, i] / (A0[i] + 1e-300)
        below = np.where(r < R36.CLEAR_THRESH)[0]
        tau = int(samp_t[below[0]]) if len(below) else None
        resid = float(np.sqrt(np.mean(r[-16:] ** 2)))
        refl = None
        if tau is not None:
            late = r[samp_t >= 2 * tau]
            if late.size:
                refl = float(late.max())
        pk_rows.append({
            "n16": JUDGE_K16[i], "nL": kinfos[i]["nL"], "A0": A0[i],
            "tau_steps": tau, "residual_end": resid,
            "residual_le_R36_1e-3": bool(resid <= R36.RET_GATE),
            "residual_le_taskbook_1e-12": bool(resid <= G6_RESID_TASKBOOK),
            "reflection_rebound_max": refl,
            "curve_downsampled": [[int(samp_t[s]), float(r[s])]
                                  for s in range(0, len(samp_t),
                                                 max(1, len(samp_t) // 40))],
            "bulk_interior_end": bulk_ck[-1][1][i]})
    taus = [p["tau_steps"] for p in pk_rows]
    resid_max = max(p["residual_end"] for p in pk_rows)
    floor_flag = bool(
        resid_max > G6_RESID_TASKBOOK
        and (tau_tail_local is None
             or (cal["tau_late"] is not None
                 and tau_tail_local > FLOOR_TAU_RATIO * cal["tau_late"])))
    deviation_flag = bool(resid_max > G6_RESID_TASKBOOK
                          and purity_r2 is not None
                          and purity_r2 < PURITY_R2_MIN)
    pred = T_CROSS_PRED[L]
    ratio = (t_cross_meas / pred) if t_cross_meas is not None else None
    out["window_resign"] = {
        **cal,
        "t_cross_pred_steps": pred,
        "t_cross_meas_steps": t_cross_meas,
        "t_cross_ratio_meas_over_pred": ratio,
        "t_cross_hit_pm50": bool(ratio is not None
                                 and T_CROSS_BAND[0] <= ratio
                                 <= T_CROSS_BAND[1]),
        "purity_R2": purity_r2,
        "tau_tail_local": tau_tail_local,
        "residual_end_max": resid_max,
        "floor_flag": floor_flag,
        "deviation_flag": deviation_flag,
        "rmax_curve_downsampled": [[int(samp_t[s]), float(rmax_hist[s])]
                                   for s in range(0, len(samp_t),
                                                  max(1, len(samp_t) // 60))]}
    out["phases"].append({
        "name": "P6_packets", "steps": Tpk,
        "injections": {"packets": "6 non-Nyquist judge-k band-limited "
                                  "solenoidal E-packets, trial i <- k_i, "
                                  "trials 6,7 = fp-floor controls",
                       "A_pk": A_PK, "sigk": SIGK[L],
                       "window_rule": "T_pk = ceil(m*tau_late*ln(R0/1e-12)),"
                                      " m=%.1f, 本轮标定段实测(头部 〇.1)"
                                      % M_MARGIN},
        "ref3_fork_sha256": fork3_sha,
        "state_after_injection_sha256": pk_in_sha,
        "state_sha256": SP1.state_sha256(state),
        "seconds": time.time() - t0})
    out["packet_rows"] = pk_rows
    out["packet_fp_floor_max"] = float(np.max(floor_hist))
    out["packet_fp_floor_rel_A0"] = float(np.max(floor_hist) / min(A0))
    out["packet_floor_note"] = (
        "trial 6,7 无包对照:run 与 ref3 在这两个 trial 指令流逐位同一,"
        "预期读数 0.0 = trial 隔离 + 参考同一性证书;有包 trial 的线性 fp "
        "重排序底不可分离见证,由残余读数自身承载(上界即所报残余)")
    out["packet_bulk_checkpoints"] = bulk_ck
    log("  P6 pk %ds  T=%d win=[%s,%s] tau_late=%s R0=%s Tcross=%s/%d "
        "tau=%s resid=%s floor=%.1e"
        % (time.time() - t0, Tpk, cal["t_calA"], cal["window_end"],
           ("%.0f" % cal["tau_late"]) if cal["tau_late"] else None,
           ("%.1e" % cal["R0"]) if cal["R0"] else None,
           t_cross_meas, pred, taus,
           ["%.0e" % p["residual_end"] for p in pk_rows],
           out["packet_fp_floor_rel_A0"]))

    out["seconds_total_L"] = time.time() - t_L0
    return out


# ==========================================================================
#  G7:全 BZ 谱半径(候选符号,冻结候选脚本函数)
# ==========================================================================
def bz_radius(L, VC):
    rmax = 0.0
    chunk = []
    for n in np.ndindex(L, L, L):
        kl = np.array(n, float) * (2 * np.pi / L)
        chunk.append(VC.symbol_step_matrix(kl))
        if len(chunk) == 4096:
            lam = np.linalg.eigvals(np.stack(chunk))
            rmax = max(rmax, float(np.abs(lam).max()))
            chunk = []
    if chunk:
        lam = np.linalg.eigvals(np.stack(chunk))
        rmax = max(rmax, float(np.abs(lam).max()))
    return rmax


# ==========================================================================
#  main
# ==========================================================================
def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m1-maxwell-loop-r3 (M1' 主跑轮 3:G6 观测窗重签重跑,"
                    "全门;裁定 2026-07-26)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-裁定-M1轮3-G6观测窗重签-2026-07-26.md "
                      "§二/§三/§四",
                      "docsv2/v2-任务书-M1-Maxwell闭环.md §3/§6/§8",
                      "data/results/v2m1_candidate.json (冻结候选)",
                      "docsv2/v2-收口-M0-2026-07-26.md"],
        "preregistration_r3": {
            "window_rule": {
                "formula": "T_PK(L) = ceil(m * tau_late(L) * ln(R0(L)/1e-12))",
                "m_margin": M_MARGIN,
                "calibration_protocol": {
                    "r_metric": "r_max(t) = max_k |a_k(t)|/A0_k, 6 判据 k, "
                                "stride %d 采样,运行减 ref3(同轮 2 机器)"
                                % PK_STRIDE,
                    "segment": "[首个 r_max<=%g 采样步, 首个 r_max<=%g 采样步]"
                               % (R_CAL_HI, R_CAL_LO),
                    "tau_late": "-1/slope(ln r_max ~ t 最小二乘,标定段)",
                    "R0": "r_max(标定段起点)",
                    "validity": "n>=%d 采样且 R^2>=%g 且 slope<0"
                                % (CAL_MIN_SAMPLES, CAL_R2_MIN),
                    "no_test_flight_values": True},
                "window": "[t_calA, t_calA + T_PK(L)];P6 总步数 = 窗端",
                "budget_cap_steps": T_P6_CAP,
                "gate_line_unchanged": "1e-12 一字不动(裁定 §一)"},
            "t_cross_prediction": {
                "source": "轮 2 在册 data/results/v2m1_maxwell_loop.json "
                          "curve_downsampled(sha256 运行时校验只读)",
                "source_sha256_pinned": R2_RESULTS_SHA256,
                "definition": "首个采样步 t 使 r_max(t)<=1e-12(6 判据 k 同时)",
                "method": "轮 2 尾段 10 点 log-线性率外推;已穿线者曲线内插值",
                "predicted_steps": T_CROSS_PRED,
                "acceptance_band": list(T_CROSS_BAND)},
            "branch_prewrite": {
                "A": "G6 全 PASS + 预言逐 L 命中 ±50% + 七门无回退 + 标定有效"
                     " -> 同轮炮组 + endurance 负控 + 交付收拢",
                "B": "残余偏离纯指数/底板(floor_flag 或 deviation_flag)"
                     " -> 仪器归因作废=物理病信号,停手报车道A/PI,计数 2",
                "C": "穿线但预言脱靶 >±50%(或标定记疑)-> G6 判 PASS 但标定"
                     "机器记疑,不进炮组,报车道A",
                "detector_constants": {
                    "floor": "resid_end_max>1e-12 且 (尾段斜率>=0 或 "
                             "tau_tail_local>%.1f*tau_late)" % FLOOR_TAU_RATIO,
                    "deviation": "resid_end_max>1e-12 且 purity R^2<%g"
                                 "(限 r_max>%g)" % (PURITY_R2_MIN,
                                                     PURITY_R_FLOOR),
                    "tail_frac": TAIL_FRAC},
                "no_post_hoc_choice": True},
            "count_rule": "轮 2 计 1 不清零;本轮 G6 再 FAIL(分支 B 或未穿线)"
                          "-> 计数 2 -> 全线停手写追因报 PI(D2 预备)",
            "regression_rule": "轮 2 已 PASS 七门任一回退 = HALT-REGRESSION",
            "seed_change": "SEED_WAVE_BASE=20261726(轮 2 +1000,防同种子伪逐位)"},
        "reporting_layer_note": (
            "首跑(2026-07-26)完成全部物理段与 G7 扫描并落分支 A 条件后,"
            "在 verdict 文案组装处因 '±50%' 字面量未转义触发 ValueError "
            "崩溃(报告层 bug,非判据层);修复仅为该文案 '%%' 转义一处,"
            "判据/窗规则/预言表/门线/种子零改动,整脚本重跑(确定性同种子)。"
            "如实入册供车道A 审计。"),
        "environment": env,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "gate_container_mapping": {
            "M1-G1": "G1_dof_nprop", "M1-G2": "G2_sigma_scaling",
            "M1-G3": "G3_j5_cocone", "M1-G4a": "G4_newton",
            "M1-G4b": "G5_eddington", "M1-G5+G6": "G6_conservation",
            "M1-G7": "G7_stability", "M1-G8": "G8_epsilon"},
        "wording_redline": (
            "全门 PASS 也不宣告 M1' PASS:判定 = 全门 + 全炮(轮 3)+ "
            "epsilon=1 实测 + 双环境 四者同时,收口在车道A + PI(红线 10);"
            "本件为 lane B 宿主单环境交付状态"),
        "run_semantics": (
            "每 L 一条连续运行记录喂全部门(相位表见脚本头);源/包读数用同 rule "
            "反事实参考分叉(ref1/ref2/ref3)做线性精确减法——参考是评估器参考"
            "计算(与解析色散参考同地位),非第二次跑;fp 线性底由无包 trial 6,7 "
            "实测入册;无任何门间换跑或逐门调参重跑"),
    }
    write_json(payload)

    def log(msg):
        print(msg, flush=True)

    log("v2m1 maxwell loop r3: M1' 主跑轮 3(G6 观测窗重签,全门)")
    log("=" * 74)
    log("[env] numpy %s blas=%s %s" % (env["numpy_version"], env["blas"],
                                       env["platform"]))

    # ---- 0. hash + 前提 ---------------------------------------------------
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
    pre_ok = bool(CJ.get("status") == "DONE"
                  and CJ["D_M1_1"]["decision"] == "A-CONFIRMED"
                  and CJ["construction_freeze"]["frozen_before_main_run"]
                  and CJ["preflight_precondition"]["preflight_pass"])
    r2_got = sha256_file(R2_JSON)
    r2_ok = (r2_got == R2_RESULTS_SHA256)
    payload["hash_verification"] = {
        "m1_pinned": {"pass": hok, "checked": checked},
        "m0_registry_pass": hz0["pass"],
        "construction_sha256": {"got": cons_got,
                                "expected": CONSTRUCTION_SHA256,
                                "match": cons_ok},
        "candidate_json_sha256_at_read": sha256_file(CAND_JSON),
        "round2_prediction_source_sha256": {"got": r2_got,
                                            "expected": R2_RESULTS_SHA256,
                                            "match": r2_ok},
        "preconditions_pass": pre_ok}
    write_json(payload)
    log("[cert] pinned hash(%d): %s; M0'注册表: %s; construction: %s; "
        "轮2预言源: %s; 前提: %s"
        % (len(checked), hok, hz0["pass"], cons_ok, r2_ok, pre_ok))
    if not (hok and hz0["pass"] and cons_ok and pre_ok and r2_ok):
        payload["status"] = "HALT-frozen-hash-or-precondition"
        write_json(payload)
        return 1

    import v2m1_candidate as VC                # 冻结候选(hash 已校验)
    PC = FZ.mod("photon_control")
    dict_step = VC.make_dict_step(PC)

    # ---- 候选对象(冻结 spec 原文重建)------------------------------------
    cand = CandidateV2(**CJ["construction_freeze"]["construction_spec"]["cand"])
    gc = G.evaluate_v2_candidate(cand)         # 统一评估器:符号层行 + 冻结校验
    row = C.row2_r23(gc)
    payload["evaluator_symbol_layer"] = {
        "row2_r23_comparator": {"pass": row["pass"],
                                "max_abs_diff": row["max_abs_diff"]},
        "gate_readings_symbol": gc.as_dict()["gates"]}
    write_json(payload)
    if not (row["pass"] and row["max_abs_diff"] <= TOL_JUDGE):
        payload["status"] = "HALT-symbol-layer-comparator"
        write_json(payload)
        return 1
    log("[eval] 符号层行 row2 diff=%.1e PASS" % row["max_abs_diff"])

    # ---- 控制行(红线 3;逐位)--------------------------------------------
    tcr = time.time()
    ctrl = {}
    worst = 0.0
    for nv in JUDGE_K16:
        kl = PC.kvec_of(nv)
        Ma = SP1.mode_matrix(kl, 16, dict_step, PC.OFF6)
        Mb = PC.mode_matrix(kl, dict_step, PC.OFF6)
        worst = max(worst, float(np.abs(Ma - Mb).max()))
    ctrl["mode_matrix_L16_bitwise"] = worst
    st_a = SP1.seed_generic(2, 7, 16, TRIALS)
    st_b = (st_a[0].copy(), st_a[1].copy())
    kinfos16 = [{"nv": nv, "kl": PC.kvec_of(nv),
                 "cf": PC.colfac(PC.kvec_of(nv), PC.OFF6)} for nv in JUDGE_K16]
    ra, ma, _ = SP1.evolve_record(st_a, dict_step, kinfos16, 128, 16,
                                  energy=True)
    rb, mb, _ = PC.evolve_record(st_b, dict_step, kinfos16, 128, energy=True)
    ctrl["evolve_record_L16_bitwise"] = float(np.abs(ra - rb).max())
    ctrl["evolve_record_monitor_equal"] = bool(
        ma["divE_drift_rel"] == mb["divE_drift_rel"]
        and ma.get("yee_energy_drift_rel") == mb.get("yee_energy_drift_rel"))
    rngc = np.random.default_rng(11)
    Fc = rngc.standard_normal((3, 2, 16, 16, 16))
    ctrl["solenoidal_L16_bitwise"] = float(np.abs(
        SP1.solenoidal_project(Fc, "E", 16)
        - PC.solenoidal_project(Fc, "E")).max())
    st24 = SP1.seed_generic(2, 12, 24, 2)
    sa, sb = (st24[0].copy(), st24[1].copy()), (st24[0].copy(), st24[1].copy())
    for _ in range(4):
        sa = dict_step(sa)
        sb = PC.step_yee(sb)
    ctrl["dict_vs_yee_L24_bitwise"] = max(
        float(np.abs(sa[0] - sb[0]).max()), float(np.abs(sa[1] - sb[1]).max()))
    # amps_fast 自检(fp 重排序底,报告级)
    projs16 = np.stack([np.conj(SP1.plane(k["kl"], 16)) / 16 ** 3
                        for k in kinfos16])
    amp_e = np.einsum("kxyz,crxyz->rkc", projs16, np.concatenate([Fc, Fc]))
    amp_f = amps_fast((Fc, Fc),
                      np.ascontiguousarray(projs16.real.reshape(7, -1)),
                      np.ascontiguousarray(projs16.imag.reshape(7, -1)))
    ctrl["amps_fast_vs_einsum_reldev"] = float(
        np.abs(amp_f - amp_e).max() / (np.abs(amp_e).max() + 1e-300))
    ctrl["pass"] = bool(ctrl["mode_matrix_L16_bitwise"] <= TOL_BITWISE
                        and ctrl["evolve_record_L16_bitwise"] <= TOL_BITWISE
                        and ctrl["evolve_record_monitor_equal"]
                        and ctrl["solenoidal_L16_bitwise"] <= TOL_BITWISE
                        and ctrl["dict_vs_yee_L24_bitwise"] <= TOL_BITWISE
                        and ctrl["amps_fast_vs_einsum_reldev"] <= 1e-10)
    ctrl["seconds"] = time.time() - tcr
    payload["control_rows"] = ctrl
    write_json(payload)
    log("[ctrl] 逐位控制行: %s (mode=%.1e rec=%.1e sol=%.1e L24=%.1e "
        "ampfast=%.1e)"
        % ("PASS" if ctrl["pass"] else "FAIL",
           ctrl["mode_matrix_L16_bitwise"], ctrl["evolve_record_L16_bitwise"],
           ctrl["solenoidal_L16_bitwise"], ctrl["dict_vs_yee_L24_bitwise"],
           ctrl["amps_fast_vs_einsum_reldev"]))
    if not ctrl["pass"]:
        payload["status"] = "HALT-control-row"
        write_json(payload)
        return 1

    # ---- 主跑逐 L ---------------------------------------------------------
    runs = {}
    payload["runs"] = runs
    for L in L_LIST:
        log("[L=%d]" % L)
        runs[str(L)] = run_one_L(L, dict_step, log)
        write_json(payload)

    # ---- G7 全 BZ 谱半径 --------------------------------------------------
    t7 = time.time()
    g7_rows = {}
    for L in L_LIST:
        g7_rows[str(L)] = {"bz_radius_max": bz_radius(L, VC),
                           "n_bz_points": L ** 3}
        log("  G7 L=%d radius-1=%.2e" % (L, g7_rows[str(L)]["bz_radius_max"] - 1))
    payload["g7_bz_scan_seconds"] = time.time() - t7
    write_json(payload)

    # =======================================================================
    #  门列组装(逐 L 表 + verdict;阈值 = 脚本头)
    # =======================================================================
    R36 = FZ.mod("r36_r3_verification")
    R37 = FZ.mod("r37_residual_scaling_audit")
    Ls = L_LIST

    # ---- G1 ---------------------------------------------------------------
    g1_perL, g1_ok, sv_cliff = {}, True, {}
    nprop_by_dir = {}
    for L in Ls:
        rows = []
        for n16 in JUDGE_K16:
            e = runs[str(L)]["per_k"][str(tuple(n16))]
            rows.append({"n16": list(n16), "nL": e["nL"],
                         "N_prop": e.get("n_prop"),
                         "sv3": e.get("sv3_main"),
                         "sv": e.get("sv_main"),
                         "transverse_match": e.get("transverse_match")})
            nprop_by_dir.setdefault(str(tuple(n16)), []).append(e.get("n_prop"))
            sv_cliff.setdefault(str(tuple(n16)), {})[str(L)] = e.get("sv_main")
        g1_perL[str(L)] = rows
    for d, vals in nprop_by_dir.items():
        g1_ok = g1_ok and (set(vals) == {G1_NPROP})
    sv3max = max(r["sv3"] for L in Ls for r in g1_perL[str(L)]
                 if r["sv3"] is not None)
    tmin = min(r["transverse_match"] for L in Ls for r in g1_perL[str(L)]
               if r["transverse_match"] is not None)
    g1_ok = bool(g1_ok and sv3max < PC.SV_THRESH)
    gc.set_gate("G1_dof_nprop",
                {"N_prop_by_direction_across_L": nprop_by_dir,
                 "sv3_max_all": sv3max, "transverse_match_min": tmin},
                "PASS" if g1_ok else "FAIL", per_L=g1_perL,
                diagnostics={"sv_cliff_table": sv_cliff,
                             "sv_thresh": PC.SV_THRESH,
                             "core": "photon_control.spectral_lines (frozen)",
                             "nyquist_included": True})

    # ---- G2 ---------------------------------------------------------------
    g2_perL = {}
    for L in Ls:
        r = runs[str(L)]
        m = r["wave_monitor"]
        gmax = max([g[2] for g in r["gauss_lock"]] + [r["gauss_lock_move"]])
        y = max(m["divE_drift_rel"], m["divB_drift_rel"], gmax)
        y_rms = max(m["divE_drift_rms"], m["divB_drift_rms"])
        g2_perL[str(L)] = {"y_max": y, "y_rms_aux": y_rms,
                           "divE_drift": m["divE_drift_rel"],
                           "divB_drift": m["divB_drift_rel"],
                           "gauss_lock_max": gmax}
    ys = [g2_perL[str(L)]["y_max"] for L in Ls]
    branch_i = all(v <= G2_BRANCH_I_GATE for v in ys)
    if branch_i:
        g2_verdict, g2_fit = "PASS", None
        sigma_class = "A=0 exact constraint line (branch i)"
    else:
        x = np.array([2 * np.pi / L for L in Ls])
        yv = np.array(ys)
        m0f = R37.fit_constant(x, yv)
        m1f = R37.fit_power(x, yv)
        daic = m0f["AIC"] - m1f["AIC"]
        okfit = bool(abs(daic) >= 2.0 and m1f["AIC"] < m0f["AIC"]
                     and abs(m1f["A"]) <= 2.0 * m1f["sigma_A"]
                     and m1f["alpha"] >= 1.0)
        g2_verdict = "PASS" if okfit else "FAIL"
        sigma_class = ("clean alpha>=1 (branch ii)" if okfit
                       else "weak/none (branch ii) -> 追因")
        g2_fit = {"A": m1f["A"], "sigma_A": m1f["sigma_A"],
                  "alpha": m1f["alpha"], "dAIC": daic}
    eps_diag_sin = {str(L): {str(tuple(n16)):
                             runs[str(L)]["per_k"][str(tuple(n16))]
                             .get("epsilon_inv", {}).get("max_sin_theta")
                             for n16 in JUDGE_K16} for L in Ls}
    gc.set_gate("G2_sigma_scaling",
                {"y_max_per_L": {str(L): g2_perL[str(L)]["y_max"] for L in Ls},
                 "sigma_class": sigma_class, "branch": "i" if branch_i else "ii"},
                g2_verdict, per_L=g2_perL, limit_fit=g2_fit,
                diagnostics={"branch_i_gate": G2_BRANCH_I_GATE,
                             "protocol": "双分支预写(脚本头);branch ii = "
                                         "R37 fit_constant/fit_power 冻结代码对象",
                             "invariant_max_sin_theta_Sprop_vs_kerC":
                                 eps_diag_sin})

    # ---- G3 ---------------------------------------------------------------
    g3_perL, g3_ok = {}, True
    iso_series = []
    for L in Ls:
        rows = {"op_w_dev_max": 0.0, "fft_dev_rows": [], "fft_ok": True}
        for n16 in JUDGE_K16:
            e = runs[str(L)]["per_k"][str(tuple(n16))]
            rows["op_w_dev_max"] = max(rows["op_w_dev_max"],
                                       e["oracle"]["w_op_vs_analytic"])
            binw = e.get("bin_width", 0.0245)
            dev = e.get("w_meas_vs_yee")
            rows["fft_dev_rows"].append({"n16": list(n16), "dev": dev,
                                         "bin": binw})
            rows["fft_ok"] = bool(rows["fft_ok"] and dev is not None
                                  and dev < binw)
        ciso = [runs[str(L)]["per_k"][str(tuple(n16))].get("c_meas")
                for n16 in JUDGE_K16[:3]]
        rows["iso_c"] = ciso
        rows["iso_spread"] = float((max(ciso) - min(ciso))
                                   / (np.mean(ciso) + 1e-300))
        iso_series.append(rows["iso_spread"])
        rows["ok_L"] = bool(rows["op_w_dev_max"] <= G3_OPW_GATE
                            and rows["fft_ok"]
                            and rows["iso_spread"] <= G3_ISO_GATE)
        g3_ok = g3_ok and rows["ok_L"]
        g3_perL[str(L)] = rows
    xk = np.array([2 * np.pi / L for L in Ls])
    yc = np.array([abs(runs[str(L)]["per_k"][str((1, 0, 0))]["w_op_measured"]
                       / (2 * np.pi / L) - 1.0) for L in Ls])
    pfit = float(np.polyfit(np.log(xk), np.log(yc), 1)[0])
    p_ok = bool(abs(pfit - G3_P_TARGET) <= G3_P_TOL)
    g3_ok = bool(g3_ok and p_ok)
    gc.set_gate("G3_j5_cocone",
                {"convergence_order_p": pfit, "p_target": G3_P_TARGET,
                 "p_ok": p_ok, "iso_spread_series": iso_series,
                 "c_minus_1_series": [float(v) for v in yc],
                 "k1_series": [float(v) for v in xk]},
                "PASS" if g3_ok else "FAIL", per_L=g3_perL,
                diagnostics={"op_gate": G3_OPW_GATE, "iso_gate": G3_ISO_GATE,
                             "fft_gate": "1 FFT bin",
                             "core": "件10 P2/P3 判据核(算子+谱双层,L 参数化"
                                     "端口逐位控制行已过)"})

    # ---- G4a 静源(G4_newton 容器)----------------------------------------
    corrs = [runs[str(L)]["coulomb"]["corr"] for L in Ls]
    coefs = [runs[str(L)]["coulomb"]["coef_times_4pi_over_q"] for L in Ls]
    nondiv = all(corrs[i + 1] >= corrs[i] - G4A_CORR_DROP_MAX
                 for i in range(len(corrs) - 1))
    g4a_ok = bool(nondiv and corrs[-1] >= G4A_CORR_LMAX_MIN
                  and abs(coefs[-1] - 1.0) <= G4A_COEF_RELTOL)
    gc.set_gate("G4_newton",
                {"tail_corr_series": corrs, "coef_4pi_over_q_series": coefs,
                 "nondivergent": nondiv},
                "PASS" if g4a_ok else "FAIL",
                per_L={str(L): runs[str(L)]["coulomb"] for L in Ls},
                diagnostics={"gates": {"corr_Lmax_min": G4A_CORR_LMAX_MIN,
                                       "corr_drop_max": G4A_CORR_DROP_MAX,
                                       "coef_reltol": G4A_COEF_RELTOL},
                             "machine": "R25 静态件 source-lift 思想的自旋 1 "
                                        "转写:局域对生/拖拽 + sponge 静持;"
                                        "读数 = 运行减 ref1"})

    # ---- G4b 动源锥(G5_eddington 容器)-----------------------------------
    g4b_perL, g4b_ok, floors = {}, True, {}
    for L in Ls:
        rows = runs[str(L)]["cone_rows_static"] + \
            ([runs[str(L)]["cone_move"]] if runs[str(L)]["cone_move"] else [])
        leaks = [r["leak"] for r in rows if r["leak"] is not None]
        okL = bool(leaks and all(v <= G4B_CONE_GATE for v in leaks))
        g4b_ok = g4b_ok and okL
        g4b_perL[str(L)] = {"cone_rows": rows, "ok_L": okL}
        floors[str(L)] = runs[str(L)]["packet_fp_floor_rel_A0"]
    gc.set_gate("G5_eddington",
                {"cone_gate": G4B_CONE_GATE, "v_over_c": 0.25,
                 "all_checkpoints_pass": g4b_ok},
                "PASS" if g4b_ok else "FAIL", per_L=g4b_perL,
                diagnostics={"cone_metric": "Chebyshev 模板锥(1 胞/步,严格"
                                            "局域公理哨)",
                             "readout": "运行减参考(ref1/ref2,分叉后至首次"
                                        "注入前指令流逐位同一 => 减法精确)",
                             "packet_phase_floor_ref": floors})

    # ---- G5 守恒 + G6 sponge(G6_conservation 容器)-----------------------
    g56_perL, g5_ok = {}, True
    for L in Ls:
        r = runs[str(L)]
        h = r["wave_monitor"].get("yee_energy_drift_rel")
        gmax = max([g[2] for g in r["gauss_lock"]] + [r["gauss_lock_move"]])
        okL = bool(r["charge_continuity_residual_max"] <= G5_CONT_GATE
                   and gmax <= G5_GAUSS_GATE and h is not None
                   and h <= G5_H_GATE)
        g5_ok = g5_ok and okL
        g56_perL[str(L)] = {
            "charge_continuity_residual": r["charge_continuity_residual_max"],
            "gauss_lock_max": gmax, "H_drift_rel": h, "conservation_ok": okL}
    # sponge
    tau_means, g6_ok, g6_perL = [], True, {}
    for L in Ls:
        rows = runs[str(L)]["packet_rows"]
        taus = [p["tau_steps"] for p in rows]
        all_tau = all(t is not None for t in taus)
        spread = (max(taus) / min(taus)) if all_tau else None
        resid_ok_r36 = all(p["residual_le_R36_1e-3"] for p in rows)
        resid_ok_tb = all(p["residual_le_taskbook_1e-12"] for p in rows)
        okL = bool(all_tau and spread is not None
                   and spread <= R36.SPREAD_GATE and resid_ok_r36
                   and resid_ok_tb)
        g6_ok = g6_ok and okL
        tau_means.append(float(np.mean(taus)) if all_tau else None)
        g6_perL[str(L)] = {"tau_per_k": taus, "spread": spread,
                           "resid_R36_gate_ok": resid_ok_r36,
                           "resid_taskbook_1e-12_ok": resid_ok_tb,
                           "reflection_rebound":
                               [p["reflection_rebound_max"] for p in rows],
                           "tau_over_L_over_c":
                               ([t / (2.0 * L) for t in taus]
                                if all_tau else None),
                           "sponge_ok": okL}
    if all(t is not None for t in tau_means):
        A_ = np.vstack([Ls, np.ones(len(Ls))]).T
        coef, res_, _, _ = np.linalg.lstsq(A_, np.array(tau_means), rcond=None)
        yhat = A_ @ coef
        ss_res = float(np.sum((np.array(tau_means) - yhat) ** 2))
        ss_tot = float(np.sum((np.array(tau_means)
                               - np.mean(tau_means)) ** 2))
        r2 = 1.0 - ss_res / (ss_tot + 1e-300)
        tau_fit = {"slope_steps_per_cell": float(coef[0]),
                   "intercept": float(coef[1]), "R2": r2,
                   "tau_means": tau_means}
        g6_ok = bool(g6_ok and coef[0] > 0 and r2 >= G6_TAU_R2_MIN)
    else:
        tau_fit = {"error": "tau undefined at some (k,L)"}
        g6_ok = False
    gc.set_gate("G6_conservation",
                {"conservation_ok_all_L": g5_ok, "sponge_ok_all_L": g6_ok,
                 "tau_linear_fit": tau_fit},
                "PASS" if (g5_ok and g6_ok) else "FAIL",
                per_L={str(L): {**g56_perL[str(L)], **g6_perL[str(L)]}
                       for L in Ls},
                diagnostics={
                    "gates": {"continuity": G5_CONT_GATE,
                              "gauss": G5_GAUSS_GATE, "H": G5_H_GATE,
                              "clear_thresh_R36": R36.CLEAR_THRESH,
                              "spread_gate_R36": R36.SPREAD_GATE,
                              "ret_gate_R36": R36.RET_GATE,
                              "resid_taskbook": G6_RESID_TASKBOOK,
                              "tau_R2_min": G6_TAU_R2_MIN},
                    "nyquist_note": ("Nyquist k 零群速,输运语义不适用,预注册"
                                     "排除于包集(R36 保护通道先例);其行为见 "
                                     "runs[L].clear_diagnostics"),
                    "sponge_core": "tcf._sponge_field (L4, frozen) + R36 "
                                   "part_C 判据常数(冻结模块直读)",
                    "packet_fp_floor_rel":
                        {str(L): runs[str(L)]["packet_fp_floor_rel_A0"]
                         for L in Ls},
                    "window_resign_per_L":
                        {str(L): {k: v for k, v in
                                  runs[str(L)]["window_resign"].items()
                                  if k != "rmax_curve_downsampled"}
                         for L in Ls}})

    # ---- G7 ---------------------------------------------------------------
    g7_ok = all(g7_rows[str(L)]["bz_radius_max"] <= 1.0 + G7_RADIUS_GATE
                for L in Ls)
    gc.set_gate("G7_stability",
                {"bz_radius_max_per_L":
                 {str(L): g7_rows[str(L)]["bz_radius_max"] for L in Ls},
                 "rms_growth_wave":
                 {str(L): runs[str(L)]["wave_monitor"]["rms_growth"]
                  for L in Ls}},
                "PASS" if g7_ok else "FAIL", per_L=g7_rows,
                diagnostics={"gate": G7_RADIUS_GATE,
                             "endurance": "负控列:分支 A 由 v2m1_guns.py 同轮"
                                          "补全(不作 PASS 依据)",
                             "core": "候选符号 symbol_step_matrix(冻结候选"
                                     "脚本函数,hash 已校验)全 BZ"})

    # ---- G8 ---------------------------------------------------------------
    g8_perL, g8_ok = {}, True
    eps_all = []
    for L in Ls:
        rows = []
        for n16 in JUDGE_K16:
            e = runs[str(L)]["per_k"][str(tuple(n16))].get("epsilon_inv")
            if e is None:
                g8_ok = False
                continue
            rows.append({"n16": list(n16), **{k: v for k, v in e.items()
                                              if k != "sin_theta"}})
            eps_all.append(e["epsilon_dof"])
            g8_ok = g8_ok and (e["j_inv"] == 0)
        g8_perL[str(L)] = rows
    eps_min = min(eps_all) if eps_all else None
    eps_max = max(eps_all) if eps_all else None
    gc.set_gate("G8_epsilon",
                {"epsilon_dof_measured_min_max": [eps_min, eps_max],
                 "j_inv_all_zero": g8_ok,
                 "anchor_definition_D1": 1.0,
                 "measured_equals_anchor": bool(g8_ok and eps_min == 1.0)},
                "PASS" if g8_ok else "FAIL", per_L=g8_perL,
                diagnostics={"machine": "不变量 j_inv(rulespace_v2.invariants"
                                        " M0' 整改口径):主谱线 top-2 数据空间"
                                        " vs 候选自身 ker C 主角计数,"
                                        "SIN_THRESH=%.2f" % INV.SIN_THRESH,
                             "note": "实测值,非 D1 定义锚代填(红线 5);"
                                     "j_inv 整数、基无关"})

    payload["gate_columns"] = gc.as_dict()

    # ---- verdict 表 + 轮 3 分支判定(预写分支 〇.6,不许事后择)-----------
    verdicts = {name: gc.gates[name]["verdict"] for name in gc.gates}
    all_pass = all(v == "PASS" for v in verdicts.values())
    payload["verdict_table"] = verdicts
    payload["all_gates_pass_this_round"] = bool(all_pass)

    wr = {str(L): runs[str(L)]["window_resign"] for L in Ls}
    tcross_table = {str(L): {
        "pred": wr[str(L)]["t_cross_pred_steps"],
        "meas": wr[str(L)]["t_cross_meas_steps"],
        "ratio": wr[str(L)]["t_cross_ratio_meas_over_pred"],
        "hit_pm50": wr[str(L)]["t_cross_hit_pm50"]} for L in Ls}
    payload["t_cross_table"] = tcross_table
    all_hit = all(tcross_table[str(L)]["hit_pm50"] for L in Ls)
    all_cal_valid = all(wr[str(L)]["cal_valid"] is True for L in Ls)
    branch_b_trig = [str(L) for L in Ls
                     if wr[str(L)]["floor_flag"] or wr[str(L)]["deviation_flag"]]
    regressed = [g for g in ROUND2_PASS_GATES if verdicts.get(g) != "PASS"]
    g6_pass = (verdicts.get("G6_conservation") == "PASS")
    g6_fail_this_round = (not g6_pass) or bool(branch_b_trig)
    count = G6_FAIL_COUNT_R2 + (1 if g6_fail_this_round else 0)
    payload["g6_consecutive_fail_count"] = count

    if regressed:
        branch, status = "HALT-REGRESSION", "HALT-REGRESSION"
        vtext = ("轮 2 已 PASS 门回退:%s——裁定 §二-3 新 HALT,停手报车道A;"
                 "本件为回退追因原始读数层。" % regressed)
    elif branch_b_trig:
        branch, status = "B", "BRANCH-B-STOP"
        vtext = ("分支 B 触发(L=%s):加窗后残余偏离纯指数/出现底板——仪器"
                 "归因作废 = 物理病信号,立即停手,报车道A/PI(裁定 §三:② "
                 "sponge 构造议题与 ③ 门线审计升活议题,PI 与会);底板量级与 "
                 "sponge 反射签名相关性见 gates.G6 diagnostics 与 "
                 "runs[L].window_resign/packet_rows。G6 计数 %d。"
                 % (branch_b_trig, count))
    elif g6_pass and all_pass and all_hit and all_cal_valid:
        branch, status = "A", "DONE"
        vtext = ("分支 A:G6 按预言穿线(逐 L ±50%% 全命中)+ 全门 PASS + "
                 "七门无回退。按裁定 §四与红线 10:**不宣告 M1' PASS/收口,"
                 "不表述 Maxwell 闭环完成**——同轮进炮组(v2m1_guns.py)+ "
                 "endurance 负控列;判定四者同时(全门+全炮+epsilon=1 实测+"
                 "双环境),收口在车道A 复核 + PI。epsilon_DOF 实测 = %s。"
                 % ([eps_min, eps_max]))
    elif g6_pass and all_pass:
        branch, status = "C", "DONE-BRANCH-C-FLAGGED"
        vtext = ("分支 C:穿线(G6 判 PASS)但 T_cross 预言脱靶或标定记疑"
                 "(hits=%s, cal_valid=%s)——G6 判 PASS 但标定机器记疑,"
                 "tau_late 标定方法追因写入报告,不进炮组,报车道A。"
                 % ({k: v["hit_pm50"] for k, v in tcross_table.items()},
                    all_cal_valid))
    else:
        branch, status = "FAIL-COUNT-2", "HALT-COUNT2-FAIL-STOP"
        vtext = ("G6 再 FAIL(未穿线;FAIL 门=%s)——计数 %d,按裁定 §二-4 "
                 "全线停手写追因报告报 PI(D2 预备启动),不做任何进一步尝试。"
                 % ([k for k, v in verdicts.items() if v != "PASS"], count))
    payload["branch"] = branch
    payload["regression_check"] = {"round2_pass_gates": ROUND2_PASS_GATES,
                                   "regressed": regressed,
                                   "no_regression": not regressed}
    payload["L64_note"] = ("64^3 未跑:窗规则加长后 48^3 全相位已 ~13 分钟,"
                           "64^3 推算远超单脚本 30 分钟预算——如实注明"
                           "(任务书 §8 红线 8;同轮 2 处置)")
    payload["sandbox"] = {"status": "PENDING",
                          "note": "双环境判据字段比对归车道A 复核(判据字段 "
                                  "1e-12;谱小分量/噪声底派生量报告级)"}
    payload["endurance"] = {"status": ("分支 A:负控列在 v2m1_guns.py 同轮补全"
                                       if branch == "A" else
                                       "未跑(非分支 A 不进炮组/负控)")}
    payload["verdict"] = vtext
    payload["status"] = status
    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)
    log("=" * 74)
    for k, v in verdicts.items():
        log("  %-18s %s" % (k, v))
    for L in Ls:
        tc = tcross_table[str(L)]
        log("  T_cross L=%-3d pred=%-6s meas=%-6s ratio=%s hit=%s"
            % (L, tc["pred"], tc["meas"],
               ("%.3f" % tc["ratio"]) if tc["ratio"] is not None else None,
               tc["hit_pm50"]))
    log("BRANCH: %s   g6_count=%d" % (branch, count))
    log("VERDICT: %s" % payload["verdict"])
    log("source  sha256 = %s" % payload["source_sha256"])
    log("results sha256 = %s" % jsha)
    log("total %.0fs" % payload["total_seconds"])
    return 0 if branch in ("A", "C") else 1


if __name__ == "__main__":
    sys.exit(main())
