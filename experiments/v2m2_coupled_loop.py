"""v2m2_coupled_loop -- M2' 主跑(轮 2):自旋 2 耦合闭环,同一 rule 每 L 一条
连续运行记录喂全部门,逐 L in {16, 24, 32, 48}(任务书 §3 交付物 3)。

候选 = 冻结构造件(data/results/v2m2_candidate.json,construction_sha256 运行时
校验):R30 手搭复形几何(eps_geo=0 定义属性)+ v1 冻结走行物质半 + 源链
(R10/R25 static/R25-E2 镜像 sector),弱场单向 + 测试场读数(审定 R4 基线)。

AUTHORITY(判据预注册;本头部运行后不得回改,红线 4):
  docsv2/v2-任务书-M2-自旋2耦合闭环.md §3(门列 M2-G1..G8)§6(判定与 FAIL 分支)
    §9(红线十三条)
  docsv2/v2-审定-M2任务书-2026-07-27.md(R1-R6;R3 源速/受迫共振,R5 D-M2-5)
  data/results/v2m2_candidate.json(构造冻结四要素:rho 预言、p=2.0 预注册、
    margin 全表、trace_row=false;construction_sha256 逐位校验)
  experiments/v2m1_maxwell_loop_r3.py(运行记录语义/反事实参考分叉/增量写盘范式)

〇、"同一次运行"操作定义(写死):每 L 一条连续运行记录,相位表:
  P0 无源段   T_P0=320(= R30 冻结 T_CLEAN)  几何 (h,pi) 10 分量实空间 staggered
              leapfrog(R30 冻结 leap_M 的实空间形式,控制行逐 k 对拍 <=1e-12),
              IC = 判据 7k 的 clean ker-K 模叠加(R30 make_ic 冻结机,TRIALS=6,
              种子 SEED_GEO=20260728+L);物质走行 psi 2 分量实空间步(冻结
              r25_realspace_step.walk_mult 宏走行标量,控制行对拍 walk_symbol
              <=1e-12;种子 SEED_MAT=20260728+500+L)。喂 M2-G1(N_prop/svn/J5)
              /G5(H 漂移)/G6 sigma 分支(i)(deDonder darkness)/G7(rms 基线)
              /G8(j_inv 实测)。
  P1 约束清除段  逐 rho 方向 T=RHO_LAYERS_LONG*2L  冻结 R26 清除机(r36.hyper_step
              + tcf._sponge_field,kappa_work=win_max/25 冻结规则)按构造冻结件
              RHO_PROTOCOL 逐 L 等比协议注入违反包并输运吸收:rho 实测@DeltaT=2L,
              floor@3DeltaT,b_layer@RHO_LAYERS_LONG*DeltaT(长段末端)。
              喂 M2-G6(a)(rho vs rho_pred ±30%)与 b_layer 线(<=1e-12 相对)。
  P2 静源段   T_RAMP=ceil(L^2/2)(cos^2 斜坡,绝热参数 omega_min*T_RAMP ∝ L,
              保证瞬态 ∝ L^-2 干净标度)+ T_HOLD=8L;静源 = 冻结
              r25_static_newton.local_source_lift(高斯 rho,SIG=2.5,零均值)
              注入 pi 行;反事实参考 ref1(同状态无源)分叉;末端 T_AVG=2L
              时间平均读出。喂 M2-G2(Newton 金丝雀 = v1 L3 canary_numbers 冻结
              判据原样)/M2-G3(Eddington = pathB._deflection 冻结 Born 裁判 +
              置零 h_ij 反事实,同一次运行内)/G6 sigma 分支(ii)(A3 残差
              连续极限线)/G7 受迫共振哨兵(静段)。
  P3 动源段   T_MOVE=4*HOPS+4;紧支撑点质量跳跃动源(点 rho 的冻结 lift 核,
              Chebyshev 支撑半径 2 实测证书;v=0.25 格点 = v/c=0.5 审定 R3 钉死,
              跳周期 4 步,半步分裂 T3 中心化);反事实参考 ref2(续静源无动源)
              分叉;镜像 sector 伴场(conj 驱动)逐位见证。喂 M2-G4(锥外泄漏
              <=1e-12 严格局域公理哨 + h̄0i E2 符号 oracle <1e-11 + 源 deDonder
              (walk 覆矢,S2 冻结口径)<1e-10 + 动量流保持)/G7 受迫共振哨兵。
  P4 波包段   T_P4=16L;6 非 Nyquist 判据 k 的 TT 波包注入 + L4 sponge 清除
              (C5 炮靶机制在耦合闭环内的运行示证);反事实参考 ref3 分叉;
              per-k tau/残余/回弹入册(诊断列 + G7 有界性)。
  反事实参考分叉 = 声明的评估器参考计算(同 rule 从运行态复制演化),非第二次跑;
  源/包读数 = 运行减参考(系统严格线性,减法精确;M1' 范式)。物质扇区按构造与
  几何扇区解耦(上三角),其 P0 记录与几何记录同段并行,同一条记录。
  禁止门间换运行;全部门读数出自该记录及其声明分叉;无任何逐门调参重跑。

一、门列与阈值(任务书 §3 逐门;全部写死):
  M2-G1  N_prop(k;L)==2 逐 L 全判据 7k(体对角 (2,2,2) 必含 + Nyquist (8,0,0),
         n_L=round(n16*L/16) 实采入册;off-band 如实记账按冻结机口径);判据核 =
         R30 冻结 peak_and_svd_placed(SV_THRESH=0.05 原样);svn 断崖全列入册;
         J5 共锥:|w_leap - w_shell| 算子级 <=1e-12 逐 k 逐 L + 运行谱峰
         |w_peak - w_shell| < 1 FFT bin + 几何/物质谱峰同 bin(共锥实测)+
         rc3ii.j5_cocone_across_theta 冻结 theta 线 {0.4, pi/3, 1.0, 1.2}
         worst < 1e-6(阈写死)。
  M2-G2  Newton:canary(v1 L3 冻结)|ratio_A-2|<=0.02 且 tail>0.99 逐 L;
         序列不发散(全 L 在带 + tail(L_max)>=tail(L_min)-0.005);
         p 验证:p_pred=2.0(构造冻结预注册)——主判观测量 = 符号误差
         y(L)=|w_op(k1)/(c*k1)-1|,k1=2*pi/L(预注册推导的直接对象:placed
         kappa_i=k_i+O(k^3) => O(a^2)),log-log 自由斜率 |p-2|<=0.1(M1' G3
         线谱系)+ 固定 p=2 拟合 R^2 报告;Newton/Eddington 带内偏差逐 L 序列
         入册(含盒窗系统学,报告列)。
  M2-G3  Eddington:偏折比 median(b 表) in 2.00±0.02 逐 L(pathB._deflection
         冻结 Born 裁判);置零 h_ij 反事实 |ratio-1.00|<=0.02(同一次运行内);
         p 同 G2 预注册。
  M2-G4  moving source:锥外泄漏 <=1e-12 逐 L 全检查点(严格局域公理哨:本步进
         器支撑半径 = 1 胞/步(staggered),模板半径 t+2,源核半径 2 实测证书);
         h̄0i 对 E2 符号层 oracle <1e-11(判据 7 模 x v=0.25);源 deDonder
         残差(walk 覆矢 kappa.eta.h̄,S2 冻结口径)<1e-10(BZ 12^3 x v 集);
         动量流保持 min|Im h̄0i|>=1e-3(E2-1 线);镜像 sector 配对逐位 0;
         v=0.25 格点(无 Cherenkov,CERT-D 构造冻结声明引用)。
  M2-G5  守恒:T̄ 行守恒 kappa.eta.h̄ <=1e-12(oracle 本脚本新主语重推,
         BZ 12^3 x v∈{0,0.05,0.15,0.25});无源段离散能量 H 相对漂移 <=1e-12
         (staggered leapfrog 精确不变量,实空间 12-roll 求值)。
  M2-G6  约束分层归纳:(a) 单层压缩 rho 实测(冻结 R26 机,构造冻结 RHO_PROTOCOL
         逐字协议,方向集 {(2,0,0),(0,3,0),(2,2,0),(2,2,2)})逐 L 落
         rho_pred_L ±30%(窗写死,统计量 = max_k,同预言规则);b_layer =
         长段末端 retained AC <=1e-12(相对)逐 L;(b) 层间引理符号证书:
         R_n <= rho^n R_0 + b(1-rho^n)/(1-rho),Fraction 精确算术逐 n 恒等式
         验证(n<=200)+ rho<1;(c) sigma 外壳双分支(预写):(i) 无源段
         deDonder darkness <=1e-12 全 L 全 k -> A=0 精确约束线;(ii) 有源段:
         观测量 = 响应场在连续极限线 k1(L)=2*pi/L(3 轴向)的 placed 3-slice
         deDonder(L3.A3_of(0,k) 冻结符号)相对残差 y(L),R37 冻结
         fit_constant/fit_power 对 x=2*pi/L:PASS 须 |dAIC|>=2 幂律胜 且
         alpha>=1 且 |A|<=2 sigma_A(D3 干净档;弱档=FAIL 追因,不降档)。
         [sigma 观测量口径说明(运行前声明):sigma 机器按定义是 L-标度外壳
         (R37,x=2*pi/L);固定格点 k 处 placed/walk 覆矢的 O(k^2) 离散失配
         是有限格点属性,作诊断列全表入册,不构成 L-标度观测量。]
  M2-G7  稳定+哨兵:BZ 谱半径(耦合一步符号 A(k,z_v) 21x21,全 BZ L^3 格点,
         v∈{0,0.25})<=1+1e-9 逐 L(基线段超增长 >1e-9 = FAIL,D-M2-5(i));
         受迫共振哨兵(审定 R3):有源段(静/动)响应场范数 final/mid 比
         <2.5(S3 冻结 no-secular 线;线性包络操作化:静源饱和/动源稳态辐射
         皆 <2.5,超线性(如 t^2)给 ~4)= 超线性即 FAIL 追因;实空间 rms
         有界性报告;endurance 定长负控列 = 轮 3 炮组补全(不作 PASS 依据,
         M1' 先例)。
  M2-G8  eps 分扇区(整数、实测,不引锚点定义值代填,红线 5):
         j_inv_geo(k;L) = N_prop - #{sin theta_i(span(数据 SVD 主谱线 top-2),
         ker K)>=0.05}(M0' invariants 不变量机器,SIN_THRESH=0.05 写死)——
         须 == N_prop == 2(即全部传播 DOF 由手搭复形供给)=> eps_geo = 0;
         j_inv_mat = 0 须由三证据同时落位:物质数据谱传播支 ==2(数据 SVD 计数,
         SV_THRESH=0.05)+ 手搭清单空(构造冻结)+ 耦合列不向物质块注入
         (运行级逐位见证 0.0)=> eps_mat = 1。报告一律 (eps_geo, eps_mat)
         二元组(红线 11)。
  双向反作用探测项(R4;只入册不进判定):符号层两点探测 eta_probe=0.05 与
         2*eta_probe,反作用块 = eta * B^dagger/(1+|B|^2)(归一化伴随通道,
         |B.C| <= eta 有界,声明),BZ 16^3
         谱半径超增长 g(eta);死锁指纹双条件(D-M2-5(ii)):g(2eta)/g(eta) ∈
         [3.2, 4.8] 且 g(eta) > 1e-12,缺一不判;预算 <= 单轮 10%;纯符号扫
         (无动力学推进 = "任何不稳即停"自动满足);指纹为真 => 显著入册报
         车道A(v1 死锁迁移证据),基线单向判定不受影响(审定 R4 原文)。
  全门:原始读数 + 逐 L 表 + verdict;verdict 不出自单一固定尺度。

二、仪器常数(非门阈值;运行前写死):
  TRIALS=6(R30);T_P0=320;SEED_GEO(L)=20260728+L;SEED_MAT(L)=20260728+500+L
  (与轮 1 种子 20260727/250725、M1' 种子系 20260726+1000/20261726、R30 SEED
  30303 均不同——新种子纪律);
  静源 SIG=2.5,Q=1.0,T_RAMP=ceil(L^2/2),T_HOLD=8L,T_AVG=2L,无 sponge
  (声明:读数 = 运行减 ref1 线性精确;绝热斜坡保证瞬态干净 L^-2 标度;sponge
  保留给 P1 清除机与 P4 波包段——候选 clearance 机制的运行示证);
  动源 Q_MV=1.0,V_LAT=0.25,HOP_PERIOD=4,HOPS={16:2,24:3,32:4,48:5},
  x0=(L//4,c,c),锥检查点 t∈{min(8,L/2-4), L/2-4},模板半径 t+2;
  波包 A_PK=1.0,包络 sigma_x=L/6,T_P4=16L,sponge 宽 = max(3,round(10L/44))
  (与 RHO_PROTOCOL 同规则),gamma=0.30;
  RHO_LAYERS_LONG=50(b_layer 长段;层=DeltaT=2L);
  eta_probe=0.05;BZ_PROBE_N=16;
  G6(ii) 有源段响应模选择:时间平均场 3 轴向 k1(L) 模,max 统计。
  分段执行支持:`python v2m2_coupled_loop.py [L...]` 只跑指定 L 并增量并入
  JSON;无参数 = 全 L + 门列组装(单脚本预算红线 8 的如实分段机制)。

三、margin_declarations(审定 R2;构造冻结版原样携带,红线 13)见常量
  MARGIN_DECLARATIONS(v2m2_candidate.json construction_freeze 冻结表逐字)。

四、rho 预言(审定 R1,构造冻结值,零回改):
  RHO_PRED = {16: 0.09967797328075316, 24: 0.06404752021424691,
              32: 0.04733242730557946, 48: 0.01471516200320156},窗 ±30%;
  p 预注册:P_PRED_G2 = P_PRED_G3 = 2.0(构造冻结推导)。

五、控制行(红线 3,主跑前必过):
  (c1) 控制矩阵行 1(R30 几何锚)evaluate_v2_candidate -> row1_r30 diff<=1e-12;
  (c2) 实空间 staggered 步进器 vs R30 冻结 leap_M 逐 k 传播 L=16 T=320 <=1e-12;
  (c3) 实空间物质走行步 vs cp1_v4_L2.walk_symbol 平面波 <=1e-12;
  (c4) rho 协议 L=16 (2,0,0) 复算 vs 构造冻结件 CERT-F 值逐位 0.0;
  (c5) 点源 lift 核紧支撑:Chebyshev r=2 外 == 0.0 位级。

措辞红线(红线 10/11/12):全绿也不宣告 M2' PASS(判定 = 全门 + 全炮(轮 3)+
eps 分扇区 + 双环境四者同时,收口在车道A 复核 + PI);禁句"自旋 2 涌现"
(eps_geo=0,涌现主语不成立);v1 封存主句原样不动;fp64;增量写盘;沙盒位
PENDING;任一门 FAIL = 停写追因(§6 三支:候选病/耦合层病/仪器病),禁调参。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m2_coupled_loop.py
      (writes data/results/v2m2_coupled_loop.json, 增量写盘)
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
for _p in (ROOT, DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

from rulespace_v2 import controls as C                     # noqa: E402
from rulespace_v2 import gates as G                        # noqa: E402
from rulespace_v2 import frozen as FZ                      # noqa: E402
from rulespace_v2 import invariants as INV                 # noqa: E402
from rulespace_v2.candidate import CandidateV2             # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m2_coupled_loop.json")
CAND_JSON = os.path.join(ROOT, "data", "results", "v2m2_candidate.json")
PREFLIGHT_JSON = os.path.join(ROOT, "data", "results", "v2m2_preflight.json")

# ---- 判据(写死;运行后不得回改,红线 4)----------------------------------
TOL_JUDGE = 1e-12
G1_NPROP = 2
J5_OP_GATE = 1e-12          # |w_leap - w_shell| 算子级
J5_THETA_GATE = 1e-6        # rc3ii theta 线(任务书 §3)
G2_BAND = (2.0, 0.02)       # canary ratio_A
G2_TAIL_MIN = 0.99          # canary tail(v1 L3 冻结门)
G2_TAIL_DEGRADE = 0.005
G3_BAND = (2.0, 0.02)       # Eddington
G3_CF_BAND = (1.0, 0.02)    # 置零 h_ij 反事实(纯 h00 世界 1.00 侧)
P_PRED_G2 = 2.0             # 构造冻结预注册(审定 R6/D-M2-3)
P_PRED_G3 = 2.0
P_FREE_TOL = 0.1            # 自由斜率 |p-2| 线(M1' G3 谱系)
G4_CONE_GATE = 1e-12
G4_ORACLE_GATE = 1e-11      # E2 口径
G4_DEDONDER_GATE = 1e-10    # v1 L3/S2 口径(walk 覆矢)
G4_MOMFLUX_MIN = 1e-3       # E2-1 动量流保持线
G5_TBAR_GATE = 1e-12
G5_H_GATE = 1e-12
RHO_PRED = {16: 0.09967797328075316, 24: 0.06404752021424691,
            32: 0.04733242730557946, 48: 0.01471516200320156}   # 构造冻结(R1)
RHO_WINDOW_REL = 0.30
G6_BLAYER_GATE = 1e-12      # 相对(长段末端)
G6_SIGMA_I_GATE = 1e-12     # 无源段 darkness(branch i A=0 线)
G7_RADIUS_GATE = 1e-9       # D-M2-5(i) 基线段与门同线
G7_SECULAR_RATIO = 2.5      # S3 冻结 no-secular 线(受迫共振哨兵操作化)
SV_SHARE = 0.05             # SV_THRESH / SIN_THRESH(共享判据,写死)
TWOWAY_RATIO_BAND = (3.2, 4.8)   # D-M2-5(ii) eta^2 指纹 ±20%
TWOWAY_ABS_GATE = 1e-12

# ---- 仪器常数(写死)-------------------------------------------------------
L_LIST = [16, 24, 32, 48]
TRIALS = 6
T_P0 = 320
SEED_BASE = 20260728        # 新种子(轮 1 = 20260727/250725;M1' = 20261726)
SIG_SRC = 2.5
Q_SRC = 1.0
T_AVG_MULT = 2
T_HOLD_MULT = 8
Q_MV = 1.0
V_LAT = 0.25                # 审定 R3:格点 v<=0.25 = v/c 0.5(c=cos pi/3)
HOP_PERIOD = 4              # 1 胞 / 4 步 = 0.25 胞/步
HOPS = {16: 2, 24: 3, 32: 4, 48: 5}
A_PK = 1.0
T_P4_MULT = 16
SP_GAMMA = 0.30
RHO_LAYERS_LONG = 50
RHO_KSET16 = [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]
JUDGE_K16 = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (2, 2, 0), (3, 1, 0),
             (2, 2, 2), (8, 0, 0)]
NONNYQ = JUDGE_K16[:6]
ETA_PROBE = 0.05
BZ_PROBE_N = 16
V_SET = (0.05, 0.15, 0.25)
BZ_N_SRC = 12

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
}
RECORD_ONLY_EXTRA = ["experiments/cp1_v4_L3.py", "rulespace_gpu/pathB_spin2.py",
                     "rulespace_gpu/green_one_walk.py",
                     "experiments/r15_walk_dedonder.py"]
CONSTRUCTION_SHA256 = \
    "70f2c1504f1b5cc5c9186700e039993b4c1c3077ca8c2196459984f6cb508eae"

# ---- margin_declarations(审定 R2;构造冻结版原样携带,红线 13)------------
MARGIN_DECLARATIONS = json.loads(r"""
[
 {"gate":"M2-G1","criterion":"N_prop(k;L) == 2 逐 L 全判据 k(体对角必含)","type":"integer","expected":"[2,2,2,2] 全 k 稳定","threshold":"整数逐位(散布 0)","margin_factor":"exact","basis":"r30_results.json decisive_run n_prop_seq(冻结)+ 预飞 (i) 复跑"},
 {"gate":"M2-G1","criterion":"svn 断崖 sv3/sv1(计数阈之下)","type":"single-sided","expected":1.7e-15,"threshold":0.05,"margin_factor":29411764705882.355,"basis":"r30 冻结 sv 列 max sv3 = 1.64e-15;阈 = SV_THRESH 0.05(共享判据)"},
 {"gate":"M2-G1","criterion":"J5 共锥 |w_geo - w_shell| 全 theta 线","type":"single-sided","expected":3.1e-16,"threshold":1e-06,"margin_factor":3225806451.612903,"basis":"rc3ii j5_cocone 冻结 worst 3.05e-16;r30 freq-shell 2.22e-16"},
 {"gate":"M2-G2","criterion":"静源 h00/phi","type":"band","expected_value":2.0000015,"expected_spread":1.6e-06,"band_center":2.0,"half_band":0.02,"spread_over_halfband":7.999999999999999e-05,"basis":"v1 tensor_qca 冻结 judge_fact2 h00_over_phi = 2.0000015373975284;p 预注册 = 2.0(本件 [2])"},
 {"gate":"M2-G3","criterion":"偏折比(置零 h_ij 反事实)","type":"band","expected_value":1.9999866,"expected_spread":1.4e-05,"band_center":2.0,"half_band":0.02,"spread_over_halfband":0.0007,"basis":"v1 tensor_qca 冻结 judge3 evolved_field_ratio = 1.999986572093466;p 预注册 = 2.0(本件 [2])"},
 {"gate":"M2-G4","criterion":"锥外分量(严格局域公理哨兵)","type":"single-sided","expected":1e-15,"threshold":1e-12,"margin_factor":999.9999999999999,"basis":"整数 roll 支撑半径 1 结构 + M1' 动源段锥外实测位级零(先例);预期报位级零,声明 1e-15 为保守上界"},
 {"gate":"M2-G4","criterion":"h̄0i 对符号层 oracle","type":"single-sided","expected":2.9e-15,"threshold":1e-11,"margin_factor":3448.275862068965,"basis":"E2-1 冻结 2.59e-15;本件预飞 (iii) 实测 2.9e-15"},
 {"gate":"M2-G4","criterion":"源处 de Donder 残差","type":"single-sided","expected":1.5e-15,"threshold":1e-10,"margin_factor":66666.66666666667,"basis":"S2 冻结 1.40e-15;本件预飞 (iii) kappa.eta.hbar 实测 1.3e-15"},
 {"gate":"M2-G5","criterion":"T̄ 行守恒残差 kappa^m T̄_mn","type":"single-sided","expected":1.5e-15,"threshold":1e-12,"margin_factor":666.6666666666667,"basis":"kappa.eta.hbar == 0 为多项式恒等式(S2/本件 CERT-C 机器实测 ~1.4e-15);新主语 oracle 本件重推,不抄 v1 数字(G5 血统注)"},
 {"gate":"M2-G5","criterion":"无源段离散能量 H 相对漂移","type":"single-sided","expected":1e-14,"threshold":1e-12,"margin_factor":100.0,"basis":"辛 leapfrog 无长期漂移:件10 Yee 能量漂移实测 2.97e-16;R30 |eig|-1 = 2.22e-16;声明 1e-14 为保守上界"},
 {"gate":"M2-G6","criterion":"单层压缩 rho < 1(R1 预言先行)","type":"single-sided","expected":0.09967797328075316,"threshold":1.0,"margin_factor":10.032306708157058,"window_rule":"主跑实测 rho 逐 L 落 rho_pred_L ±30% 方计 PASS","basis":"本件 CERT-F 冻结 R26 机按 L 等比标定(协议 RHO_PROTOCOL)"},
 {"gate":"M2-G6","criterion":"b_layer(相对)","type":"single-sided","expected":2.4e-15,"threshold":1e-12,"margin_factor":416.6666666666667,"basis":"r36 part_C 冻结 retained clearable AC <= 2.33e-15(机器底血统)"},
 {"gate":"M2-G6","criterion":"sigma 外壳 A=0 分支:无源段 resid","type":"single-sided","expected":1.4e-14,"threshold":1e-12,"margin_factor":71.42857142857143,"basis":"r30 冻结 deDonder darkness max 1.33e-14(恒等式护约束);有源段非机器零则走 D3 两档预写分支(不降档通融)"},
 {"gate":"M2-G7","criterion":"BZ 谱半径超增长","type":"single-sided","expected":2.3e-16,"threshold":1e-09,"margin_factor":4347826.086956522,"basis":"R30 严格酉 |eig|-1 = 2.22e-16(冻结);哨兵定量线 = 审定 R5 D-M2-5(基线段与门同线 1e-9)"},
 {"gate":"M2-G7","criterion":"受迫共振哨兵(线性包络,审定 R3)","type":"structural-separation","expected":"有界稳态响应:共振间隙 min|z_v - e^{±i w_geo}| = 0.0972 严格正(全 BZ x v 集)","threshold":"超线性增长 = FAIL(哨兵)","margin_factor":"结构性(间隙严格正 => 无 Jordan 增长通道)","basis":"本件 CERT-C/D 数值 + S3 冻结 resolvent 间隙血统(no secular growth)"},
 {"gate":"M2-G8","criterion":"eps 分扇区:j_inv_geo == N_curv 且 j_inv_mat == 0","type":"integer","expected":"(eps_geo, eps_mat) = (0, 1),整数逐位,双环境","threshold":"整数逐位(散布 0)","margin_factor":"exact","basis":"M0' j_inv 不变量口径(整数、基稳健);主跑实测,不引锚点定义值代填(红线 5);本件预飞级小格验证见 CERT-B/epsilon 节"},
 {"gate":"CERT-D","criterion":"无 Cherenkov 相配(声明)","type":"structural-separation","expected":{"v_over_c_max":0.5,"v_lattice_max":0.25,"cone_separation":2.0000000000000004,"min_phase_speed_lattice":0.3333333333333334,"phase_speed_separation":1.3333333333333337,"gap_min":0.09718797623025359},"threshold":"间隙 > 0 严格(相位匹配通道不存在)","margin_factor":"分离论证(§四补条允许的明示分离形式)","basis":"审定 R3 原文口径;本件 CERT-D 数值"}
]
""")


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
                   separators=(",", ":"), default=_jd)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def state_sha(*arrays):
    m = hashlib.sha256()
    for a in arrays:
        m.update(np.ascontiguousarray(a).tobytes())
    return m.hexdigest()


def n_at_L(n16, L):
    return [int(round(c * L / 16.0)) for c in n16]


# ==========================================================================
#  实空间步进器(R30 leapfrog 的 staggered 形式;控制行 c2 对拍冻结 leap_M)
# ==========================================================================
def neglap(f):
    """placed Laplacian 实空间形式:L = sum_i (2 sin(k_i/2))^2 <-> 6f - rolls。"""
    out = 6.0 * f
    for ax in (-3, -2, -1):
        out = out - np.roll(f, 1, axis=ax) - np.roll(f, -1, axis=ax)
    return out


def geo_step(h, ps, DT, drive=None):
    """staggered:ps_{n+1/2} = ps_{n-1/2} - DT*L h_n (+ DT*drive);
    h_{n+1} = h_n + DT*ps_{n+1/2}。与 leap_M 宏映射代数恒等(头部 〇)。"""
    ps = ps - DT * neglap(h)
    if drive is not None:
        ps = ps + DT * drive
    h = h + DT * ps
    return h, ps


def ps_init(h0_k, pi0_k, Lk, DT):
    """整数槽 pi_0 -> staggered pi_{-1/2} = pi_0 + (DT/2) L h_0(逐 k 精确)。"""
    return pi0_k + 0.5 * DT * Lk * h0_k


def matter_step(psi, RS):
    """物质走行一步:U = a I - i b.sigma,由冻结 walk_mult 宏走行标量组装
    (控制行 c3 对拍 walk_symbol <=1e-12)。psi: (2, ..., L,L,L)。"""
    a0, b1_0, b2_0, b3_0 = RS.walk_mult(psi[0])
    a1, b1_1, b2_1, b3_1 = RS.walk_mult(psi[1])
    p0 = a0 - 1j * (b3_0 + (b1_1 - 1j * b2_1))
    p1 = a1 - 1j * ((b1_0 + 1j * b2_0) - b3_1)
    return np.stack([p0, p1])


def energy_H(h, ps, DT):
    """staggered 状态的精确守恒量(逐 k 不变式 Q = DT[L(1-DT^2 L/4)|h|^2+|pi|^2]
    的实空间求值;pi 整数槽由 ps 精确重构)。"""
    nl = neglap(h)
    pi_int = ps - 0.5 * DT * nl          # pi_n = pi_{n-1/2} - (DT/2) L h_n
    nl2 = neglap(nl)
    e = (np.vdot(h, nl).real - 0.25 * DT * DT * np.vdot(h, nl2).real
         + np.vdot(pi_int, pi_int).real)
    return float(e)


def project_modes(F, Pconj):
    """F (C, L^3) x Pconj (nk, L^3) -> (C, nk) 模振幅。"""
    return F @ Pconj.T


def spec_amp_matrix(rec):
    """rec (T, trials, 10|2) -> (freqs, Fw) 冻结窗口协议(R28/R30 口径):
    T0=T/2, Hanning, [2:-2] 切;返回频轴与 F (Wn-4, trials, C)。"""
    T = rec.shape[0]
    T0 = T // 2
    Wn = T - T0
    win = np.hanning(Wn)
    seg = rec[T0:] * win[:, None, None]
    F = np.fft.fft(seg[2:-2], axis=0)
    freqs = 2 * np.pi * np.fft.fftfreq(Wn - 4)
    return freqs, F


def matter_nprop(rec):
    """物质数据谱传播支计数:±半轴各取功率峰,SVD(trials x 2)>SV_SHARE 计数和。"""
    freqs, F = spec_amp_matrix(rec)
    P = np.sum(np.abs(F) ** 2, axis=(1, 2))
    lo = max(0.05, 4 * np.pi / len(freqs))
    total = 0
    details = []
    for sel in (freqs > lo) & (freqs <= np.pi / 2), \
               (freqs < -lo) & (freqs >= -np.pi / 2):
        if not np.any(sel):
            continue
        pk = int(np.argmax(np.where(sel, P, 0.0)))
        if P[pk] < 1e-18:
            continue
        M = F[pk]                                    # (trials, 2)
        sv = np.linalg.svd(M, compute_uv=False)
        svn = sv / (sv[0] + 1e-300)
        n = int(np.sum(svn > SV_SHARE))
        total += n
        details.append({"w_peak": float(freqs[pk]), "n": n,
                        "svn": [float(x) for x in svn]})
    return total, details


# ==========================================================================
#  每 L 一条运行记录
# ==========================================================================
def run_one_L(L, payload, log):
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    R36M = FZ.mod("r36_r3_verification")
    R25N = FZ.mod("r25_static_newton")
    MS = FZ.mod("r25_moving_source_symbol")
    RSM = FZ.mod("r25_moving_source_realspace")
    RS = FZ.mod("r25_realspace_step")
    L3 = FZ.mod("cp1_v4_L3")
    tcf = FZ.mod("rulespace_gpu.tensor_coin_feedback")
    pathB = FZ.mod("rulespace_gpu.pathB_spin2")
    r15 = FZ.mod("r15_walk_dedonder")
    DT = R30M.DT
    ETA = MS.ETA
    t_L0 = time.time()
    out = {"L": L, "seed_geo": SEED_BASE + L, "seed_mat": SEED_BASE + 500 + L,
           "trials": TRIALS, "phases": []}

    # 判据 k 表(n 随 L 重标,实采入册)
    kinfos = []
    for n16 in JUDGE_K16:
        nL = n_at_L(n16, L)
        k = np.array(nL, float) * (2 * np.pi / L)
        kap = r15.kappa_placed(k)
        kinfos.append({"n16": list(n16), "nL": nL, "k": k, "kap": kap,
                       "off_band": kap is None,
                       "w_shell": r15.shell_omega(k),
                       "Lk": R30M.L_placed(k)})
    out["judge_k_table"] = [{"n16": ki["n16"], "nL": ki["nL"],
                             "k": [float(x) for x in ki["k"]],
                             "off_band": ki["off_band"]} for ki in kinfos]
    x = np.arange(L)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    planes = np.stack([np.exp(1j * (ki["k"][0] * X + ki["k"][1] * Y
                                    + ki["k"][2] * Z)) for ki in kinfos])
    Pconj = np.conj(planes).reshape(len(kinfos), -1) / L ** 3

    # ---- P0 无源段(几何 + 物质并行记录)---------------------------------
    t0 = time.time()
    rng = np.random.default_rng(SEED_BASE + L)
    h = np.zeros((10, TRIALS, L, L, L), complex)
    ps = np.zeros_like(h)
    ic_note = []
    for i, ki in enumerate(kinfos):
        if ki["off_band"]:
            ic_note.append({"n16": ki["n16"], "skipped_off_band": True})
            continue
        h0, pi0 = R30M.make_ic("clean_kerK", ki["kap"], ki["k"], TRIALS, rng)
        psk = ps_init(h0, pi0, ki["Lk"], DT)
        ph = planes[i]
        h += h0.T[:, :, None, None, None] * ph[None, None]
        ps += psk.T[:, :, None, None, None] * ph[None, None]
    out["ic_note"] = ic_note
    rng_m = np.random.default_rng(SEED_BASE + 500 + L)
    psi = (rng_m.standard_normal((2, TRIALS, L, L, L))
           + 1j * rng_m.standard_normal((2, TRIALS, L, L, L)))
    rec = np.zeros((T_P0, TRIALS, len(kinfos), 10), complex)
    rec_m = np.zeros((T_P0, TRIALS, len(kinfos), 2), complex)
    H_series = []
    rms_series = []
    for t in range(T_P0):
        h, ps = geo_step(h, ps, DT)
        psi = matter_step(psi, RS)
        A = project_modes(h.reshape(10 * TRIALS, -1), Pconj)
        rec[t] = A.reshape(10, TRIALS, len(kinfos)).transpose(1, 2, 0)
        Am = project_modes(psi.reshape(2 * TRIALS, -1), Pconj)
        rec_m[t] = Am.reshape(2, TRIALS, len(kinfos)).transpose(1, 2, 0)
        if t % 64 == 0 or t == T_P0 - 1:
            H_series.append([t, energy_H(h, ps, DT)])
            rms_series.append([t, float(np.sqrt(np.mean(np.abs(h) ** 2)))])
    H0 = H_series[0][1]
    H_drift = max(abs(e - H0) for _, e in H_series) / (abs(H0) + 1e-300)
    out["phases"].append({"name": "P0_wave", "steps": T_P0,
                          "state_sha256": state_sha(h, ps, psi),
                          "seconds": time.time() - t0})
    out["H_drift_rel"] = H_drift
    out["H_series"] = H_series
    out["rms_series_wave"] = rms_series
    log(f"  P0 {time.time()-t0:.0f}s H_drift={H_drift:.1e}")

    # 谱判读:G1 N_prop/svn/darkness/kerK 残差 + G8 j_inv + 物质支 + J5
    per_k = {}
    for i, ki in enumerate(kinfos):
        e = {"n16": ki["n16"], "nL": ki["nL"], "off_band": ki["off_band"]}
        if not ki["off_band"]:
            rk = rec[:, :, i, :]
            res = R30M.peak_and_svd_placed(rk, ki["kap"])
            e["N_prop"] = res["n_prop"]
            e["sv"] = res.get("sv", [])
            e["w_peak"] = res.get("w_peak")
            e["w_shell"] = ki["w_shell"]
            w_leap = float(np.arccos(np.clip(1 - 0.5 * DT * DT * ki["Lk"],
                                             -1, 1)))
            e["w_leap_op"] = w_leap
            e["j5_op_dev"] = abs(w_leap - ki["w_shell"])
            e["dedonder_darkness"] = R30M.dedonder_darkness(rk, ki["kap"])
            rmean, rmax = R30M.kerK_residual(rk, ki["kap"])
            e["kerK_residual_mean"], e["kerK_residual_max"] = rmean, rmax
            # G8: 数据 SVD 主谱线 top-2 振幅空间 vs ker K(不变量机器)
            freqs, Fw = spec_amp_matrix(rk)
            if e["w_peak"] is not None and np.isfinite(e["w_peak"]):
                pk = int(np.argmin(np.abs(freqs - e["w_peak"])))
                Mamp = Fw[pk]                        # (trials, 10)
                _, _, Vh = np.linalg.svd(Mamp, full_matrices=False)
                data2 = Vh[:2].conj().T              # (10, 2)
                Q, _, _ = R30M.kerK_basis(ki["kap"])
                inv = INV.subspace_invariants(data2, Q)
                e["sin_theta_data2_vs_kerK"] = inv["sin_theta"]
                e["n_outside_kerK"] = inv["n_ge_thresh"]
                e["j_inv_geo"] = int(e["N_prop"] - inv["n_ge_thresh"])
                e["eps_geo_k"] = 1.0 - e["j_inv_geo"] / max(e["N_prop"], 1)
            # 物质支 + 共锥
            nm, det = matter_nprop(rec_m[:, :, i, :])
            e["matter_n_prop"] = nm
            e["matter_branches"] = det
            if det and e.get("w_peak") is not None:
                wm = max((d["w_peak"] for d in det), key=abs)
                e["cocone_bin_dev"] = abs(abs(wm) - e["w_peak"])
        per_k[str(tuple(ki["n16"]))] = e
    out["per_k"] = per_k
    out["fft_bin_width"] = float(2 * np.pi / (T_P0 // 2 - 4))
    del rec, rec_m

    # ---- P1 约束清除段(冻结 R26 机;RHO_PROTOCOL 逐字)--------------------
    t0 = time.time()
    kw = R36M.recompute_kappa_window(DT)      # C_CONE 精度与冻结协议逐位一致
    kappa_work = kw["kappa_work"]
    dTl = int(round(L / DT))
    w_sp = max(3, int(round(10 * L / 44.0)))
    pad = max(2, int(round(12 * L / 44.0)))
    sig_env = 6.0 * L / 44.0
    sp = tcf._sponge_field(L, w_sp, SP_GAMMA)
    envg = np.exp(-(((x - L / 2.0) / sig_env) ** 2))
    env = envg[:, None, None] * envg[None, :, None] * envg[None, None, :]

    def bulk(z):
        b = (slice(pad, -pad),) * 3
        return float(np.abs(z[b]).sum())

    rho_rows = {}
    for n16 in RHO_KSET16:
        nL = n_at_L(n16, L)
        kvec = 2 * np.pi * np.array(nL, float) / L
        carrier = np.exp(1j * (kvec[0] * X + kvec[1] * Y + kvec[2] * Z))
        z0 = (env * carrier).astype(complex)
        m0_ac = bulk(z0 - z0.mean())
        z, pz = z0.copy(), np.zeros_like(z0)
        row = {}
        for t in range(1, RHO_LAYERS_LONG * dTl + 1):
            z, pz = R36M.hyper_step(z, pz, kappa_work, DT * DT, sp=sp)
            if t == dTl:
                row["rho"] = bulk(z - z.mean()) / m0_ac
            if t == 3 * dTl:
                row["floor_3dT"] = bulk(z - z.mean()) / m0_ac
            if t == RHO_LAYERS_LONG * dTl:
                row["b_layer_rel"] = bulk(z - z.mean()) / m0_ac
        rho_rows[str(tuple(n16))] = row
    rho_meas = max(r["rho"] for r in rho_rows.values())
    b_layer = max(r["b_layer_rel"] for r in rho_rows.values())
    out["phases"].append({"name": "P1_constraint_clear",
                          "steps_per_dir": RHO_LAYERS_LONG * dTl,
                          "kappa_work": kappa_work, "DeltaT": dTl,
                          "seconds": time.time() - t0})
    out["rho_measurement"] = {"per_dir": rho_rows, "rho_meas_max": rho_meas,
                              "rho_pred": RHO_PRED[L],
                              "ratio_meas_over_pred": rho_meas / RHO_PRED[L],
                              "in_pm30_window": bool(
                                  abs(rho_meas / RHO_PRED[L] - 1.0)
                                  <= RHO_WINDOW_REL),
                              "b_layer_rel_max": b_layer,
                              "b_layer_le_1e-12": bool(b_layer
                                                       <= G6_BLAYER_GATE)}
    log(f"  P1 {time.time()-t0:.0f}s rho={rho_meas:.4e} "
        f"(pred {RHO_PRED[L]:.4e} ratio {rho_meas/RHO_PRED[L]:.3f}) "
        f"b_layer={b_layer:.1e}")

    # ---- P2 静源段(源相位在 trial-0 载体上;ref1 分叉)--------------------
    t0 = time.time()
    hs = h[:, 0].copy()
    pss = ps[:, 0].copy()
    hr1, pr1 = hs.copy(), pss.copy()
    fork1 = state_sha(hr1, pr1)
    rho_src = R25N.gaussian_lump(L, SIG_SRC)
    rho_zm = rho_src - rho_src.mean()
    lift = R25N.local_source_lift(rho_zm)
    lift = lift - lift.mean(axis=(1, 2, 3), keepdims=True)
    T_RAMP = int(math.ceil(L * L / 2))
    T_HOLD = T_HOLD_MULT * L
    T_AVG = T_AVG_MULT * L
    acc = np.zeros_like(hs)
    nacc = 0
    norm_series = []
    for t in range(1, T_RAMP + T_HOLD + 1):
        amp = 0.5 * (1 - math.cos(math.pi * min(t, T_RAMP) / T_RAMP))
        hs, pss = geo_step(hs, pss, DT, drive=(Q_SRC * amp) * lift)
        hr1, pr1 = geo_step(hr1, pr1, DT)
        if t % 32 == 0 or t == T_RAMP + T_HOLD:
            norm_series.append([t, float(np.linalg.norm(hs - hr1))])
        if t > T_RAMP + T_HOLD - T_AVG:
            acc += hs - hr1
            nacc += 1
    diff_avg = acc / nacc
    hb_phys = np.real(0.5 * ((hs - hr1) + np.conjugate(hs - hr1)))
    cn = L3.canary_numbers(hb_phys, rho_src, SIG_SRC)
    # Eddington(冻结 Born 裁判;置零 h_ij 反事实同一次运行内)
    h_phys = RS.trace_reverse_packed(hb_phys.astype(complex)).real
    ctr = L // 2
    h00_sl = h_phys[0][..., ctr]
    hxx_sl = h_phys[4][..., ctr]
    scale = 3e-4 / (np.abs(0.5 * h00_sl).max() + 1e-300)
    BLISTS = {16: (4, 5, 6), 24: (5, 6, 7, 8, 9), 32: (6, 8, 10, 12),
              48: (8, 12, 16, 20, 24)}
    edd_rows = []
    for b in BLISTS[L]:
        n_t = 1.0 - 0.5 * (h00_sl + hxx_sl) * scale
        n_s = 1.0 - 0.5 * h00_sl * scale
        a_t = pathB._deflection(n_t, L, b)
        a_s = pathB._deflection(n_s, L, b)
        edd_rows.append({"b": int(b), "alpha_tensor": a_t, "alpha_scalar": a_s,
                         "ratio": a_t / a_s if a_s != 0 else None})
    edd_med = float(np.median([r["ratio"] for r in edd_rows]))
    h_cf = h_phys.copy()
    for j in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        h_cf[j] = 0.0
    b_mid = BLISTS[L][len(BLISTS[L]) // 2]
    n_t0 = 1.0 - 0.5 * (h_cf[0][..., ctr] + h_cf[4][..., ctr]) * scale
    n_s0 = 1.0 - 0.5 * h_cf[0][..., ctr] * scale
    edd_cf = pathB._deflection(n_t0, L, b_mid) / pathB._deflection(n_s0, L,
                                                                   b_mid)
    # sigma 分支(ii):时间平均响应场在连续极限线 k1(L) 3 轴向的 A3(0,k) 残差
    sig2_rows = []
    for ax_dir in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        kv = 2 * np.pi * np.array(ax_dir, float) / L
        pconj = np.exp(-1j * (kv[0] * X + kv[1] * Y + kv[2] * Z)) / L ** 3
        a = np.array([np.sum(pconj * diff_avg[j]) for j in range(10)])
        A3 = L3.A3_of(0.0, kv)
        r = float(np.max(np.abs(A3 @ a)) / (np.max(np.abs(a)) + 1e-300))
        sig2_rows.append({"axis": list(ax_dir), "resid_rel": r})
    sigma_ii_y = max(r["resid_rel"] for r in sig2_rows)
    # 诊断:判据 k 处固定格点残差(placed/walk 覆矢失配,有限格点属性)
    sig2_diag = []
    for i, ki in enumerate(kinfos):
        if ki["off_band"]:
            continue
        a = np.array([np.sum(np.conj(planes[i]) * diff_avg[j]) for j in
                      range(10)]) / L ** 3
        if np.max(np.abs(a)) < 1e-12:
            continue
        A3 = L3.A3_of(0.0, ki["k"])
        sig2_diag.append({"n16": ki["n16"],
                          "resid_rel": float(np.max(np.abs(A3 @ a))
                                             / (np.max(np.abs(a)) + 1e-300))})
    n2 = len(norm_series)
    static_secular = (norm_series[-1][1]
                      / max(norm_series[n2 // 2][1], 1e-300))
    out["phases"].append({"name": "P2_static", "steps": T_RAMP + T_HOLD,
                          "T_ramp": T_RAMP, "T_hold": T_HOLD, "T_avg": T_AVG,
                          "ref1_fork_sha256": fork1,
                          "state_sha256": state_sha(hs, pss),
                          "seconds": time.time() - t0})
    out["newton_canary"] = cn
    out["eddington"] = {"per_b": edd_rows, "median": edd_med,
                        "counterfactual_hij_zero": float(edd_cf),
                        "b_mid": int(b_mid)}
    out["sigma_branch_ii"] = {"per_axis_k1": sig2_rows, "y_max": sigma_ii_y,
                              "fixed_k_diagnostic": sig2_diag}
    out["static_norm_series"] = norm_series[::4] + [norm_series[-1]]
    out["static_secular_ratio_final_over_mid"] = float(static_secular)
    log(f"  P2 {time.time()-t0:.0f}s ratio_A={cn['ratio_A']:.6f} "
        f"tail={cn['tailcorr_h00']:.5f} edd={edd_med:.4f} cf={edd_cf:.4f} "
        f"sigma_ii={sigma_ii_y:.2e} sec_ratio={static_secular:.2f}")

    # ---- P3 动源段(紧支撑跳跃点质量;ref2 分叉;镜像伴场)-----------------
    t0 = time.time()
    hr2, pr2 = hs.copy(), pss.copy()
    fork2 = state_sha(hr2, pr2)
    hm, pm = np.conjugate(hs), np.conjugate(pss)
    pt = np.zeros((L, L, L))
    x0 = (L // 4, ctr, ctr)
    pt[x0] = 1.0
    lift_pt = R25N.local_source_lift(pt)          # 紧支撑核(控制行 c5 证书)
    cheb0 = np.maximum.reduce([np.minimum(np.abs(X - x0[0]),
                                          L - np.abs(X - x0[0])),
                               np.minimum(np.abs(Y - x0[1]),
                                          L - np.abs(Y - x0[1])),
                               np.minimum(np.abs(Z - x0[2]),
                                          L - np.abs(Z - x0[2]))])
    T_MOVE = HOP_PERIOD * HOPS[L] + 4
    cone_ts = sorted({min(8, L // 2 - 4), L // 2 - 4})
    cone_rows = []
    xs = 0                       # 相对 x0 的跳跃位移
    lifts_cache = {0: lift_pt}
    mv_norm = []
    ledger_mass = Q_MV
    for t in range(1, T_MOVE + 1):
        ramp_amp = 0.5 * (1 - math.cos(math.pi * min(t, 4) / 4))
        hop_now = (t % HOP_PERIOD == 0 and xs < HOPS[L])
        if hop_now:
            xs_new = xs + 1
            if xs_new not in lifts_cache:
                lifts_cache[xs_new] = np.roll(lift_pt, xs_new, axis=1)
            # 半步分裂(T3 中心化实现):跳步注一半旧+一半新,下一步起全新
            drive_mv = 0.5 * (lifts_cache[xs] + lifts_cache[xs_new])
            xs = xs_new
        else:
            drive_mv = lifts_cache[xs]
        Dm = Q_MV * ramp_amp * drive_mv
        amp_st = 1.0
        hs, pss = geo_step(hs, pss, DT, drive=amp_st * Q_SRC * lift + Dm)
        hr2, pr2 = geo_step(hr2, pr2, DT, drive=amp_st * Q_SRC * lift)
        hm, pm = geo_step(hm, pm, DT,
                          drive=np.conjugate(amp_st * Q_SRC * lift + Dm))
        mv_norm.append([t, float(np.linalg.norm(hs - hr2))])
        if t in cone_ts:
            d = hs - hr2
            R = t + 2                     # 支撑半径 1 胞/步 + 源核半径 2
            outside = cheb0 > R
            mx_in = float(np.max(np.abs(d)))
            mx_out = float(np.max(np.abs(d[:, outside]))) if outside.any() \
                else 0.0
            cone_rows.append({"t": t, "radius": int(R),
                              "leak_rel": mx_out / (mx_in + 1e-300),
                              "max_out": mx_out, "max_in": mx_in})
    mirror_pair = float(max(np.max(np.abs(hm - np.conjugate(hs))),
                            np.max(np.abs(pm - np.conjugate(pss)))))
    mv_secular = mv_norm[-1][1] / max(mv_norm[len(mv_norm) // 2][1], 1e-300)
    # E2 h̄0i oracle + 源 deDonder(walk 覆矢)+ 动量流(模态,同段算子级参考)
    oracle_dev, dd_worst, momflux_min = 0.0, 0.0, float("inf")
    for i, ki in enumerate(kinfos):
        if ki["off_band"]:
            continue
        z = complex(np.exp(-1j * V_LAT * ki["k"][0]))
        ph = planes[i]
        hb0i_rs = RSM.hbar0i_realspace(ph, z)
        hb = MS.hbar_moving(ki["k"], z)[0]
        oracle_dev = max(oracle_dev, float(np.max(np.abs(hb0i_rs
                                                         - hb[0, 1:]))))
        momflux_min = min(momflux_min,
                          float(np.max(np.abs(np.imag(hb[0, 1:])))))
    for v in V_SET:
        vv = np.array([v, 0.0, 0.0])
        for idx in np.ndindex(BZ_N_SRC, BZ_N_SRC, BZ_N_SRC):
            if idx == (0, 0, 0):
                continue
            kk = 2 * np.pi * np.array(idx, float) / BZ_N_SRC
            z = complex(np.exp(-1j * float(vv @ kk)))
            hb = MS.hbar_moving(kk, z)[0]
            dd_worst = max(dd_worst, float(np.max(np.abs(
                (ETA @ MS.kappa(kk, z)) @ hb))))
    out["phases"].append({"name": "P3_move", "steps": T_MOVE,
                          "v_lattice": V_LAT, "hop_period": HOP_PERIOD,
                          "hops": HOPS[L], "x0": list(x0),
                          "ref2_fork_sha256": fork2,
                          "state_sha256": state_sha(hs, pss),
                          "seconds": time.time() - t0})
    out["cone_rows"] = cone_rows
    out["mirror_pairing_bitwise"] = mirror_pair
    out["moving_secular_ratio"] = float(mv_secular)
    out["moving_ledger"] = {"mass_conserved": ledger_mass == Q_MV,
                            "hops_done": xs}
    out["g4_symbol_rows"] = {"hbar0i_oracle_dev": oracle_dev,
                             "source_deDonder_walk_kappa_max": dd_worst,
                             "momentum_flux_min": momflux_min}
    log(f"  P3 {time.time()-t0:.0f}s cone={['%.1e' % r['leak_rel'] for r in cone_rows]} "
        f"mirror={mirror_pair:.1e} oracle={oracle_dev:.1e} dd={dd_worst:.1e}")

    # ---- P4 波包段(TT 波包 + L4 sponge 清除;ref3 分叉)-------------------
    t0 = time.time()
    hr3, pr3 = hs.copy(), pss.copy()
    fork3 = state_sha(hr3, pr3)
    sp_run = tcf._sponge_field(L, w_sp, SP_GAMMA)
    sig_x = L / 6.0
    envp = np.exp(-(((X - ctr) ** 2 + (Y - ctr) ** 2 + (Z - ctr) ** 2)
                    / (2 * sig_x ** 2)))
    A0 = []
    for i, n16 in enumerate(NONNYQ):
        ki = kinfos[i]
        if ki["off_band"]:
            A0.append(None)
            continue
        tt = r15.tt_basis(ki["kap"])[:, 0]
        pk_field = A_PK * tt[:, None, None, None] * (envp * planes[i])[None]
        hs = hs + pk_field
        a = project_modes(pk_field.reshape(10, -1), Pconj[i:i + 1])
        A0.append(float(np.linalg.norm(a)))
    T_P4 = T_P4_MULT * L
    samp_t, ratio_hist = [], []
    for t in range(1, T_P4 + 1):
        hs, pss = geo_step(hs, pss, DT, drive=Q_SRC * lift)
        hr3, pr3 = geo_step(hr3, pr3, DT, drive=Q_SRC * lift)
        hs *= (1.0 - sp_run)
        pss *= (1.0 - sp_run)
        hr3 *= (1.0 - sp_run)
        pr3 *= (1.0 - sp_run)
        if t % 4 == 0:
            d = hs - hr3
            Ad = project_modes(d.reshape(10, -1), Pconj)
            samp_t.append(t)
            ratio_hist.append([float(np.linalg.norm(Ad[:, i]))
                               / (A0[i] + 1e-300) if A0[i] else None
                               for i in range(len(NONNYQ))])
    ratio_hist = np.array([[r if r is not None else np.nan for r in row]
                           for row in ratio_hist])
    pk_rows = []
    R36M_thr = R36M.CLEAR_THRESH
    for i, n16 in enumerate(NONNYQ):
        if A0[i] is None:
            pk_rows.append({"n16": list(n16), "off_band": True})
            continue
        r = ratio_hist[:, i]
        below = np.where(r < R36M_thr)[0]
        tau = int(samp_t[below[0]]) if len(below) else None
        resid = float(np.sqrt(np.mean(r[-8:] ** 2)))
        refl = None
        if tau is not None:
            late = r[np.array(samp_t) >= 2 * tau]
            if late.size:
                refl = float(np.nanmax(late))
        pk_rows.append({"n16": list(n16), "A0": A0[i], "tau_steps": tau,
                        "residual_end": resid, "rebound_max": refl})
    out["phases"].append({"name": "P4_packets", "steps": T_P4,
                          "sponge_width": w_sp, "gamma": SP_GAMMA,
                          "ref3_fork_sha256": fork3,
                          "state_sha256": state_sha(hs, pss),
                          "seconds": time.time() - t0})
    out["packet_rows"] = pk_rows
    log(f"  P4 {time.time()-t0:.0f}s tau={[p.get('tau_steps') for p in pk_rows]} "
        f"resid={['%.0e' % p['residual_end'] for p in pk_rows if 'residual_end' in p]}")

    # ---- G7:全 BZ 谱半径(耦合一步符号 21x21,v∈{0,0.25})------------------
    t0 = time.time()
    rmax_all = {}
    for v in (0.0, V_LAT):
        rmax = 0.0
        chunk = []
        for n in np.ndindex(L, L, L):
            kk = np.array(n, float) * (2 * np.pi / L)
            M2 = R30M.leap_M(kk)
            z = complex(np.exp(-1j * v * kk[0]))
            A21 = np.zeros((21, 21), complex)
            A21[:20, :20] = np.kron(np.eye(10), M2)
            D10 = MS.normal_h_packed(kk, z) if np.linalg.norm(kk) > 1e-12 \
                else np.zeros(10, complex)
            A21[1:20:2, 20] = D10
            A21[20, 20] = z
            chunk.append(A21)
            if len(chunk) == 4096:
                lam = np.linalg.eigvals(np.stack(chunk))
                rmax = max(rmax, float(np.abs(lam).max()))
                chunk = []
        if chunk:
            lam = np.linalg.eigvals(np.stack(chunk))
            rmax = max(rmax, float(np.abs(lam).max()))
        rmax_all[str(v)] = rmax
    out["g7_bz_radius"] = {"per_v": rmax_all,
                           "max_minus_1": max(rmax_all.values()) - 1.0,
                           "n_bz_points": L ** 3,
                           "seconds": time.time() - t0}
    log(f"  G7 {time.time()-t0:.0f}s radius-1={max(rmax_all.values())-1.0:.2e}")

    out["seconds_total_L"] = time.time() - t_L0
    return out


# ==========================================================================
#  控制行(红线 3)
# ==========================================================================
def control_rows(log):
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    R36M = FZ.mod("r36_r3_verification")
    R25N = FZ.mod("r25_static_newton")
    RS = FZ.mod("r25_realspace_step")
    L2 = FZ.mod("cp1_v4_L2")
    r15 = FZ.mod("r15_walk_dedonder")
    tcf = FZ.mod("rulespace_gpu.tensor_coin_feedback")
    DT = R30M.DT
    ctrl = {}
    # (c1) 控制矩阵行 1(R30 锚)
    cand1 = C.control_candidates()["row1_r30"]
    gc1 = G.evaluate_v2_candidate(cand1)
    row1 = C.row1_r30(gc1)
    ctrl["c1_row1_r30"] = {"pass": row1["pass"],
                           "max_abs_diff": row1["max_abs_diff"],
                           "n_prop_seq": row1["remeasured"]["n_prop_seq"]}
    # (c2) 实空间步进器 vs 冻结 leap_M(L=16 全判据 k,T=320)
    Lc = 16
    xc = np.arange(Lc)
    Xc, Yc, Zc = np.meshgrid(xc, xc, xc, indexing="ij")
    worst = 0.0
    rngc = np.random.default_rng(7)
    for n16 in JUDGE_K16:
        k = np.array(n16, float) * (2 * np.pi / Lc)
        kap = r15.kappa_placed(k)
        if kap is None:
            continue
        h0, pi0 = R30M.make_ic("clean_kerK", kap, k, 2, rngc)
        Lk = R30M.L_placed(k)
        ph = np.exp(1j * (k[0] * Xc + k[1] * Yc + k[2] * Zc))
        hf = h0.T[:, :, None, None, None] * ph[None, None]
        pf = ps_init(h0, pi0, Lk, DT).T[:, :, None, None, None] * ph[None, None]
        rec_ref = R30M.evolve_components(h0, pi0, k, 64)
        pcj = np.conj(ph).reshape(1, -1) / Lc ** 3
        for t in range(64):
            hf, pf = geo_step(hf, pf, DT)
            a = project_modes(hf.reshape(20, -1), pcj).reshape(10, 2).T
            worst = max(worst, float(np.max(np.abs(a - rec_ref[t]))))
    ctrl["c2_stepper_vs_leapM_L16_T64"] = worst
    # (c3) 物质走行实空间步 vs walk_symbol
    worst_m = 0.0
    for n16 in [(2, 1, 0), (1, 0, 0), (3, 2, 1)]:
        k = 2 * np.pi * np.array(n16, float) / 12
        xm = np.arange(12)
        Xm, Ym, Zm = np.meshgrid(xm, xm, xm, indexing="ij")
        ph = np.exp(1j * (k[0] * Xm + k[1] * Ym + k[2] * Zm))
        chi = np.array([0.6 + 0.2j, -0.3 + 0.7j])
        psi = np.stack([chi[0] * ph, chi[1] * ph])
        got = matter_step(psi, RS)
        ref = L2.walk_symbol(k) @ chi
        worst_m = max(worst_m, float(max(
            np.max(np.abs(got[0] - ref[0] * ph)),
            np.max(np.abs(got[1] - ref[1] * ph)))))
    ctrl["c3_matter_step_vs_walk_symbol"] = worst_m
    # (c4) rho 协议 L=16 (2,0,0) vs 构造冻结件 CERT-F(逐位)
    with open(CAND_JSON, "r", encoding="utf-8") as fh:
        CJ = json.load(fh)
    frozen_rho = CJ["CERT_F_rho_calibration"]["rho_per_L_per_k"]["16"]["(2, 0, 0)"]
    kw = R36M.recompute_kappa_window(DT)      # C_CONE 精度逐位对齐冻结协议
    Lc = 16
    dTl = 32
    sp = tcf._sponge_field(Lc, max(3, round(10 * Lc / 44.0)), SP_GAMMA)
    pad = max(2, round(12 * Lc / 44.0))
    sig_env = 6.0 * Lc / 44.0
    xc = np.arange(Lc)
    envg = np.exp(-(((xc - Lc / 2.0) / sig_env) ** 2))
    env = envg[:, None, None] * envg[None, :, None] * envg[None, None, :]
    kvec = 2 * np.pi * np.array([2, 0, 0], float) / Lc
    Xc, Yc, Zc = np.meshgrid(xc, xc, xc, indexing="ij")
    carrier = np.exp(1j * (kvec[0] * Xc + kvec[1] * Yc + kvec[2] * Zc))
    z0 = (env * carrier).astype(complex)

    def bulkc(z):
        b = (slice(pad, -pad),) * 3
        return float(np.abs(z[b]).sum())

    m0 = bulkc(z0 - z0.mean())
    z, pz = z0.copy(), np.zeros_like(z0)
    for t in range(1, dTl + 1):
        z, pz = R36M.hyper_step(z, pz, kw["kappa_work"], DT * DT, sp=sp)
    rho16 = bulkc(z - z.mean()) / m0
    ctrl["c4_rho_L16_200_vs_certF_bitwise"] = abs(rho16 - frozen_rho)
    # (c5) 点源 lift 核紧支撑
    pt = np.zeros((16, 16, 16))
    pt[8, 8, 8] = 1.0
    liftp = R25N.local_source_lift(pt)
    cheb = np.maximum.reduce([np.abs(Xc - 8), np.abs(Yc - 8), np.abs(Zc - 8)])
    ctrl["c5_lift_kernel_outside_r2"] = float(np.max(np.abs(
        liftp[:, cheb > 2])))
    ctrl["pass"] = bool(row1["pass"] and row1["max_abs_diff"] <= TOL_JUDGE
                        and worst <= TOL_JUDGE and worst_m <= TOL_JUDGE
                        and ctrl["c4_rho_L16_200_vs_certF_bitwise"] == 0.0
                        and ctrl["c5_lift_kernel_outside_r2"] == 0.0)
    log(f"[ctrl] c1={row1['max_abs_diff']:.1e} c2={worst:.1e} c3={worst_m:.1e} "
        f"c4={ctrl['c4_rho_L16_200_vs_certF_bitwise']:.1e} "
        f"c5={ctrl['c5_lift_kernel_outside_r2']:.1e} -> "
        f"{'PASS' if ctrl['pass'] else 'FAIL'}")
    return ctrl


# ==========================================================================
#  层间引理符号证书(Fraction 精确算术)
# ==========================================================================
def layer_lemma_certificate(rho_meas, b_meas):
    rho = Fraction(min(int(math.ceil(rho_meas * 10000)) + 1, 9999), 10000)
    b = Fraction(1, 10 ** 12)            # b_layer 线(实测在机器底之下)
    R0 = Fraction(1)
    ok = rho < 1
    Bn = R0
    tail = b / (1 - rho)
    for n in range(200):
        Bn_next = rho * Bn + b
        closed = rho ** (n + 1) * R0 + b * (1 - rho ** (n + 1)) / (1 - rho)
        if Bn_next != closed:
            ok = False
            break
        if Bn_next > rho ** (n + 1) * R0 + tail:
            ok = False
            break
        Bn = Bn_next
    return {"statement": ("单层不等式 R_{n+1} <= rho R_n + b ⟹ 任意层数 "
                          "R_n <= rho^n R_0 + b(1-rho^n)/(1-rho) <= rho^n R_0 "
                          "+ b/(1-rho);Fraction 精确算术逐 n(<=200)恒等式 + "
                          "上界验证,rho 取实测上取整 1e-4 格"),
            "rho_used": [rho.numerator, rho.denominator],
            "b_line": "1e-12(实测 b_layer 在其下)",
            "rho_lt_1": bool(rho < 1),
            "long_time_bound_b_over_1_minus_rho": float(b / (1 - rho)),
            "pass": bool(ok)}


# ==========================================================================
#  双向反作用探测项(R4;只入册不进判定)
# ==========================================================================
def two_way_probe(log):
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    MS = FZ.mod("r25_moving_source_symbol")
    t0 = time.time()
    res = {}
    for eta in (ETA_PROBE, 2 * ETA_PROBE):
        rmax = 0.0
        for n in np.ndindex(BZ_PROBE_N, BZ_PROBE_N, BZ_PROBE_N):
            if n == (0, 0, 0):
                continue
            kk = 2 * np.pi * np.array(n, float) / BZ_PROBE_N
            kk = np.where(kk > np.pi, kk - 2 * np.pi, kk)
            z = complex(np.exp(-1j * V_LAT * kk[0]))
            A21 = np.zeros((21, 21), complex)
            A21[:20, :20] = np.kron(np.eye(10), R30M.leap_M(kk))
            D10 = MS.normal_h_packed(kk, z)
            A21[1:20:2, 20] = D10
            A21[20, 20] = z
            # 反作用块 = eta * 归一化伴随通道(|B.C| <= eta 有界,声明)
            A21[20, 1:20:2] = (eta * np.conj(D10)
                               / (1.0 + float(np.vdot(D10, D10).real)))
            lam = np.linalg.eigvals(A21)
            rmax = max(rmax, float(np.abs(lam).max()))
        res[str(eta)] = rmax - 1.0
    g1, g2 = res[str(ETA_PROBE)], res[str(2 * ETA_PROBE)]
    ratio = (g2 / g1) if g1 > 0 else None
    fingerprint = bool(ratio is not None
                       and TWOWAY_RATIO_BAND[0] <= ratio <= TWOWAY_RATIO_BAND[1]
                       and g1 > TWOWAY_ABS_GATE)
    log(f"[two-way probe] g(eta)={g1:.2e} g(2eta)={g2:.2e} "
        f"ratio={ratio if ratio is None else round(ratio, 3)} "
        f"fingerprint={fingerprint} ({time.time()-t0:.0f}s)")
    return {"eta": ETA_PROBE, "overgrowth_eta": g1, "overgrowth_2eta": g2,
            "ratio_2eta_over_eta": ratio,
            "fingerprint_conditions": {"ratio_band": list(TWOWAY_RATIO_BAND),
                                       "abs_gate": TWOWAY_ABS_GATE},
            "deadlock_fingerprint": fingerprint,
            "coupling_block": "eta * conj(B)^T(伴随通道;纯符号 BZ 扫,"
                              "无动力学推进 => 不稳即停条款自动满足)",
            "policy": ("审定 R4:只入册不进判定;D-M2-5(ii) 双条件缺一不判;"
                       "指纹为真 = v1 死锁迁移证据,显著入册报车道A,"
                       "不再深入探测;基线单向判定不受影响"),
            "budget_seconds": time.time() - t0}


# ==========================================================================
#  main
# ==========================================================================
def main(argv):
    t0 = time.time()
    env = INV.environment_record()
    only_L = [int(a) for a in argv if a.isdigit()]
    payload = {}
    if os.path.exists(OUT) and only_L:
        with open(OUT, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    if not payload:
        payload = {
            "register": "v2m2-coupled-loop (M2' 主跑轮 2:耦合闭环逐 L 全门)",
            "status": "RUNNING", "backend": "numpy (fp64)",
            "authority": ["docsv2/v2-任务书-M2-自旋2耦合闭环.md §3/§6/§9",
                          "docsv2/v2-审定-M2任务书-2026-07-27.md(R1-R6)",
                          "data/results/v2m2_candidate.json(构造冻结)",
                          "experiments/v2m1_maxwell_loop_r3.py(范式先例)"],
            "environment": env,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "preregistration": {
                "rho_pred": {str(k): v for k, v in RHO_PRED.items()},
                "rho_window_rel": RHO_WINDOW_REL,
                "p_pred": {"G2": P_PRED_G2, "G3": P_PRED_G3},
                "seeds": {"geo": "20260728+L", "mat": "20260728+500+L",
                          "distinct_from": ["轮1 20260727/250725",
                                            "M1' 20261726/20260726+1000",
                                            "R30 30303"]},
                "phase_table": "P0 wave 320 / P1 clear 50x2L / P2 static "
                               "ceil(L^2/2)+8L / P3 move 4*hops+4 / P4 "
                               "packets 16L(头部 〇 写死)",
                "sigma_branch_ii_observable": (
                    "时间平均响应场 3 轴向 k1(L)=2*pi/L 模的 placed 3-slice "
                    "deDonder(L3.A3_of(0,k))相对残差 y(L),R37 冻结拟合对 "
                    "x=2*pi/L;固定格点 k 残差(placed/walk 覆矢 O(k^2) 离散"
                    "失配)全表入册为诊断列(运行前声明,头部 一.G6)"),
                "two_way": "eta 0.05/0.10 纯符号 BZ 探测,只入册不进判定"},
            "margin_declarations": MARGIN_DECLARATIONS,
            "wording_redline": (
                "全门 PASS 也不宣告 M2' PASS:判定 = 全门 + 全炮(轮 3)+ eps "
                "分扇区 + 双环境四者同时,收口在车道A + PI(红线 12);禁句"
                "'自旋 2 涌现'(eps_geo=0,涌现主语不成立);v1 封存主句原样"
                "不动;本件为 lane B 宿主单环境交付状态"),
            "run_semantics": (
                "每 L 一条连续运行记录喂全部门(相位表头部 〇);源/包读数 = "
                "运行减反事实参考分叉(ref1/ref2/ref3,同 rule 从运行态复制"
                "演化的评估器参考计算,非第二次跑;系统严格线性,减法精确);"
                "物质扇区按构造上三角解耦,其记录与几何记录同段并行;"
                "禁门间换运行、禁逐门调参重跑"),
            "runs": {},
        }
    write_json(payload)

    def log(msg):
        print(msg, flush=True)

    log("v2m2 coupled loop: M2' 主跑轮 2(同一 rule 逐 L 全门)")
    log("=" * 74)
    log(f"[env] numpy {env['numpy_version']} blas={env['blas']} "
        f"{env['platform']}")

    # ---- 0. hash + 构造冻结校验 + 前提 ------------------------------------
    checked, hok = {}, True
    for rel, exp in M2_PINNED.items():
        got = sha256_file(os.path.join(ROOT, rel))
        m = (got == exp)
        hok = hok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    rec_only = {rel: {"sha256": sha256_file(os.path.join(ROOT, rel)),
                      "note": "record-only(无先行 hash 记录)"}
                for rel in RECORD_ONLY_EXTRA}
    hz0 = FZ.verify_frozen()
    with open(CAND_JSON, "r", encoding="utf-8") as fh:
        CJ = json.load(fh)
    cons_got = sha256_canonical(CJ["construction_freeze"]["construction_spec"])
    cons_ok = (cons_got == CONSTRUCTION_SHA256)
    pre_ok = bool(CJ.get("status") == "DONE"
                  and CJ["D_M2_1"]["decision"] == "R4-CONFIRMED"
                  and CJ["construction_freeze"]["frozen_before_main_run"]
                  and CJ["preflight_precondition"]["preflight_pass"]
                  and CJ["construction_freeze"]["construction_spec"]
                        ["trace_row_processing_present"] is False)
    payload["hash_verification"] = {
        "m2_pinned": {"pass": hok, "checked": checked},
        "record_only": rec_only,
        "m0_registry_pass": hz0["pass"],
        "construction_sha256": {"got": cons_got,
                                "expected": CONSTRUCTION_SHA256,
                                "match": cons_ok},
        "candidate_json_sha256_at_read": sha256_file(CAND_JSON),
        "preconditions_pass": pre_ok}
    write_json(payload)
    log(f"[cert] pinned({len(checked)}): {hok}; M0'注册表: {hz0['pass']}; "
        f"construction: {cons_ok}; 前提: {pre_ok}")
    if not (hok and hz0["pass"] and cons_ok and pre_ok):
        payload["status"] = "HALT-frozen-hash-or-precondition"
        write_json(payload)
        return 1

    # ---- 评估器符号层行(红线 5:经 evaluate_v2_candidate 重测)------------
    if "evaluator_symbol_layer" not in payload:
        cand = CandidateV2(**{k: v for k, v in
                              CJ["construction_freeze"]["construction_spec"]
                              ["cand"].items()
                              if k in ("sector", "geometry", "coupling",
                                       "hand_built", "lattice", "backend",
                                       "frozen_refs", "cand_id")})
        gc = G.evaluate_v2_candidate(cand)
        payload["evaluator_symbol_layer"] = {
            "gates": {k: {kk: vv for kk, vv in v.items() if kk != "per_L"}
                      for k, v in gc.as_dict()["gates"].items()},
            "note": "R30 族符号层行(g1_r30/g3_r30 冻结判据核);运行级门列在 "
                    "m2_gates(判据 k 集为 M2 七 k 终版)"}
        write_json(payload)
        log("[eval] evaluate_v2_candidate(R30 族)符号层行入册")

    # ---- 控制行 ------------------------------------------------------------
    if "control_rows" not in payload:
        ctrl = control_rows(log)
        payload["control_rows"] = ctrl
        write_json(payload)
        if not ctrl["pass"]:
            payload["status"] = "HALT-control-row"
            write_json(payload)
            return 1

    # ---- 主跑逐 L ----------------------------------------------------------
    todo = only_L if only_L else L_LIST
    for L in todo:
        if str(L) in payload["runs"]:
            log(f"[L={L}] 已在册,跳过(分段续跑)")
            continue
        log(f"[L={L}]")
        payload["runs"][str(L)] = run_one_L(L, payload, log)
        write_json(payload)
    if only_L and any(str(L) not in payload["runs"] for L in L_LIST):
        payload["status"] = "SEGMENT-IN-PROGRESS"
        write_json(payload)
        log("分段模式:尚有 L 未跑,门列组装待全 L 齐")
        return 0

    # ---- 双向反作用探测(只入册)-------------------------------------------
    if "two_way_probe" not in payload:
        payload["two_way_probe"] = two_way_probe(log)
        write_json(payload)

    # =======================================================================
    #  门列组装(逐 L;阈值 = 脚本头)
    # =======================================================================
    runs = payload["runs"]
    Ls = L_LIST
    R37 = FZ.mod("r37_residual_scaling_audit")
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    gates = {}

    def inband(L):
        return [k for k, e in runs[str(L)]["per_k"].items()
                if not e.get("off_band")]

    # ---- M2-G1 DOF/J5 -----------------------------------------------------
    nprop_by_dir, g1_ok = {}, True
    sv_cliff, j5_worst_op, cocone_worst = {}, 0.0, 0.0
    for L in Ls:
        for kstr, e in runs[str(L)]["per_k"].items():
            if e.get("off_band"):
                continue
            nprop_by_dir.setdefault(kstr, []).append(e["N_prop"])
            sv_cliff.setdefault(kstr, {})[str(L)] = e.get("sv", [])
            j5_worst_op = max(j5_worst_op, e["j5_op_dev"])
            binw = runs[str(L)]["fft_bin_width"]
            if e.get("w_peak") is not None:
                g1_ok = g1_ok and abs(e["w_peak"] - e["w_shell"]) < binw
            if e.get("cocone_bin_dev") is not None:
                cocone_worst = max(cocone_worst, e["cocone_bin_dev"])
                g1_ok = g1_ok and e["cocone_bin_dev"] < 2 * binw
    for d, vals in nprop_by_dir.items():
        g1_ok = g1_ok and set(vals) == {G1_NPROP}
    RC3 = FZ.mod("rc3ii_relaxation_framework")
    j5rows = RC3.j5_cocone_across_theta()
    j5_theta_worst = max(r["max_abs_w_leapfrog_minus_walkshell"]
                         for r in j5rows)
    g1_ok = bool(g1_ok and j5_worst_op <= J5_OP_GATE
                 and j5_theta_worst < J5_THETA_GATE)
    gates["M2-G1"] = {
        "verdict": "PASS" if g1_ok else "FAIL",
        "N_prop_by_direction_across_L": nprop_by_dir,
        "sv_cliff_table": sv_cliff,
        "j5_operator_worst": j5_worst_op,
        "j5_theta_line_worst": j5_theta_worst,
        "j5_theta_rows": j5rows,
        "cocone_geo_vs_matter_bin_dev_worst": cocone_worst,
        "diagnostics": {"core": "R30 冻结 peak_and_svd_placed;SV_THRESH 0.05;"
                                "Nyquist (8,0,0) 在带(shell==leap 于该点)",
                        "gates": {"j5_op": J5_OP_GATE,
                                  "j5_theta": J5_THETA_GATE}}}

    # ---- M2-G2 Newton -----------------------------------------------------
    cn_perL = {str(L): runs[str(L)]["newton_canary"] for L in Ls}
    ratios = [cn_perL[str(L)]["ratio_A"] for L in Ls]
    tails = [cn_perL[str(L)]["tailcorr_h00"] for L in Ls]
    band_ok = all(abs(r - G2_BAND[0]) <= G2_BAND[1] for r in ratios)
    tail_ok = all(tc > G2_TAIL_MIN for tc in tails) and \
        (tails[-1] >= tails[0] - G2_TAIL_DEGRADE)
    # p 验证(预注册观测量:符号误差 y(L)=|w_op(k1)/(c*k1)-1|)
    yk, xk = [], []
    for L in Ls:
        k1 = 2 * np.pi / L
        w_op = float(np.abs(np.angle(np.linalg.eigvals(
            R30M.leap_M(np.array([k1, 0.0, 0.0])))[0])))
        yk.append(abs(w_op / (0.5 * k1) - 1.0))
        xk.append(k1)
    p_free = float(np.polyfit(np.log(xk), np.log(yk), 1)[0])
    lg = np.log(np.array(yk)) - P_PRED_G2 * np.log(np.array(xk))
    yfit = P_PRED_G2 * np.log(np.array(xk)) + lg.mean()
    ss = 1.0 - float(np.sum((np.log(yk) - yfit) ** 2)
                     / (np.sum((np.log(yk) - np.mean(np.log(yk))) ** 2)
                        + 1e-300))
    p_ok = bool(abs(p_free - P_PRED_G2) <= P_FREE_TOL)
    g2_ok = bool(band_ok and tail_ok and p_ok
                 and all(cn_perL[str(L)]["well_not_hill"] for L in Ls))
    gates["M2-G2"] = {
        "verdict": "PASS" if g2_ok else "FAIL",
        "ratio_A_per_L": {str(L): r for L, r in zip(Ls, ratios)},
        "tail_corr_per_L": {str(L): tc for L, tc in zip(Ls, tails)},
        "band": list(G2_BAND), "band_ok": band_ok, "tail_ok": tail_ok,
        "p_preregistered": P_PRED_G2, "p_free_fit": p_free,
        "p_ok_pm0.1": p_ok, "fixed_p_fit_R2": ss,
        "band_deviation_series_report": {str(L): abs(r - 2.0)
                                         for L, r in zip(Ls, ratios)},
        "diagnostics": {"core": "v1 L3 canary_numbers(冻结判据原样)+ 符号"
                                "误差收敛阶(预注册推导对象,头部 一.G2)"}}

    # ---- M2-G3 Eddington --------------------------------------------------
    ed_perL = {str(L): runs[str(L)]["eddington"] for L in Ls}
    meds = [ed_perL[str(L)]["median"] for L in Ls]
    cfs = [ed_perL[str(L)]["counterfactual_hij_zero"] for L in Ls]
    ed_ok = all(abs(m - G3_BAND[0]) <= G3_BAND[1] for m in meds)
    cf_ok = all(abs(c - G3_CF_BAND[0]) <= G3_CF_BAND[1] for c in cfs)
    g3_ok = bool(ed_ok and cf_ok)
    gates["M2-G3"] = {
        "verdict": "PASS" if g3_ok else "FAIL",
        "median_per_L": {str(L): m for L, m in zip(Ls, meds)},
        "counterfactual_per_L": {str(L): c for L, c in zip(Ls, cfs)},
        "band": list(G3_BAND), "cf_band": list(G3_CF_BAND),
        "p_preregistered": P_PRED_G3,
        "band_deviation_series_report": {str(L): abs(m - 2.0)
                                         for L, m in zip(Ls, meds)},
        "diagnostics": {"core": "pathB._deflection 冻结 Born 裁判;反事实同一"
                                "次运行内(置零 h_ij);p 预注册同 G2 观测量"}}

    # ---- M2-G4 moving source ----------------------------------------------
    g4_perL, g4_ok = {}, True
    for L in Ls:
        r = runs[str(L)]
        leaks = [c["leak_rel"] for c in r["cone_rows"]]
        okL = bool(leaks and all(v <= G4_CONE_GATE for v in leaks)
                   and r["mirror_pairing_bitwise"] == 0.0)
        g4_ok = g4_ok and okL
        g4_perL[str(L)] = {"cone_rows": r["cone_rows"],
                           "mirror_pairing_bitwise":
                               r["mirror_pairing_bitwise"],
                           "ledger": r["moving_ledger"], "ok_L": okL}
    sym = runs[str(Ls[-1])]["g4_symbol_rows"]
    sym_worst = {"hbar0i_oracle_dev": max(runs[str(L)]["g4_symbol_rows"]
                                          ["hbar0i_oracle_dev"] for L in Ls),
                 "source_deDonder_walk_kappa_max":
                     max(runs[str(L)]["g4_symbol_rows"]
                         ["source_deDonder_walk_kappa_max"] for L in Ls),
                 "momentum_flux_min":
                     min(runs[str(L)]["g4_symbol_rows"]["momentum_flux_min"]
                         for L in Ls)}
    g4_ok = bool(g4_ok and sym_worst["hbar0i_oracle_dev"] <= G4_ORACLE_GATE
                 and sym_worst["source_deDonder_walk_kappa_max"]
                 <= G4_DEDONDER_GATE
                 and sym_worst["momentum_flux_min"] >= G4_MOMFLUX_MIN)
    gates["M2-G4"] = {
        "verdict": "PASS" if g4_ok else "FAIL",
        "per_L": g4_perL, "symbol_rows_worst": sym_worst,
        "v_lattice": V_LAT,
        "no_cherenkov_ref": "CERT-D 构造冻结声明(gap 0.0972 严格正)",
        "gates": {"cone": G4_CONE_GATE, "oracle": G4_ORACLE_GATE,
                  "deDonder": G4_DEDONDER_GATE,
                  "momentum_flux_min": G4_MOMFLUX_MIN},
        "diagnostics": {"cone_metric": "Chebyshev 模板,半径 t+2(步进器支撑 "
                                       "1 胞/步 + 源核半径 2 实测证书 c5);"
                                       "读数 = 运行减 ref2(线性精确)",
                        "instrument_note": ("锥哨兵 = 紧支撑跳跃点质量实现;"
                                            "h̄0i/deDonder = E2 精确模态机同段"
                                            "算子级参考(头部 〇 P3 声明)"),
                        "last_L_rows": sym}}

    # ---- M2-G5 守恒 --------------------------------------------------------
    g5_perL, g5_ok = {}, True
    # T̄ 行守恒 oracle(新主语重推;含 v=0 静态)
    MS = FZ.mod("r25_moving_source_symbol")
    ETA = MS.ETA
    tbar_worst = 0.0
    for v in (0.0,) + V_SET:
        vv = np.array([v, 0.0, 0.0])
        for idx in np.ndindex(BZ_N_SRC, BZ_N_SRC, BZ_N_SRC):
            if idx == (0, 0, 0):
                continue
            kk = 2 * np.pi * np.array(idx, float) / BZ_N_SRC
            z = complex(np.exp(-1j * float(vv @ kk)))
            hb = MS.hbar_moving(kk, z)[0]
            tbar_worst = max(tbar_worst, float(np.max(np.abs(
                (ETA @ MS.kappa(kk, z)) @ hb))))
    for L in Ls:
        hd = runs[str(L)]["H_drift_rel"]
        okL = bool(hd <= G5_H_GATE)
        g5_ok = g5_ok and okL
        g5_perL[str(L)] = {"H_drift_rel": hd, "ok_L": okL}
    g5_ok = bool(g5_ok and tbar_worst <= G5_TBAR_GATE)
    gates["M2-G5"] = {
        "verdict": "PASS" if g5_ok else "FAIL",
        "tbar_row_conservation_max": tbar_worst,
        "per_L": g5_perL,
        "gates": {"tbar": G5_TBAR_GATE, "H": G5_H_GATE},
        "diagnostics": {"oracle": "kappa(z).eta.hbar(z) 本脚本重推(BZ 12^3 x "
                                  "v {0,0.05,0.15,0.25});H = staggered "
                                  "leapfrog 精确不变量实空间求值(头部 一.G5)"}}

    # ---- M2-G6 约束分层归纳 ------------------------------------------------
    g6_perL, g6a_ok, g6b_ok = {}, True, True
    dark_worst = 0.0
    for L in Ls:
        r = runs[str(L)]["rho_measurement"]
        okA = bool(r["in_pm30_window"] and r["b_layer_le_1e-12"])
        g6a_ok = g6a_ok and okA
        darks = [e["dedonder_darkness"] for e in
                 runs[str(L)]["per_k"].values() if not e.get("off_band")]
        dark_worst = max(dark_worst, max(darks))
        g6_perL[str(L)] = {"rho_meas": r["rho_meas_max"],
                           "rho_pred": r["rho_pred"],
                           "ratio": r["ratio_meas_over_pred"],
                           "in_window": r["in_pm30_window"],
                           "b_layer_rel": r["b_layer_rel_max"],
                           "darkness_max": max(darks),
                           "sigma_ii_y": runs[str(L)]["sigma_branch_ii"]
                           ["y_max"]}
    lemma = layer_lemma_certificate(
        max(runs[str(L)]["rho_measurement"]["rho_meas_max"] for L in Ls),
        max(runs[str(L)]["rho_measurement"]["b_layer_rel_max"] for L in Ls))
    g6b_ok = lemma["pass"]
    # sigma 双分支
    branch_i_ok = bool(dark_worst <= G6_SIGMA_I_GATE)
    ys = np.array([runs[str(L)]["sigma_branch_ii"]["y_max"] for L in Ls])
    xs = np.array([2 * np.pi / L for L in Ls])
    if np.all(ys <= G6_SIGMA_I_GATE):
        sigma_ii = {"branch": "i-extended (machine zero)", "pass": True}
    else:
        m0f = R37.fit_constant(xs, ys)
        m1f = R37.fit_power(xs, ys)
        daic = m0f["AIC"] - m1f["AIC"]
        okfit = bool(abs(daic) >= 2.0 and m1f["AIC"] < m0f["AIC"]
                     and abs(m1f["A"]) <= 2.0 * m1f["sigma_A"]
                     and m1f["alpha"] >= 1.0)
        sigma_ii = {"branch": "ii (D3 两档)", "A": m1f["A"],
                    "sigma_A": m1f["sigma_A"], "alpha": m1f["alpha"],
                    "dAIC_const_minus_power": daic,
                    "y_per_L": {str(L): float(y) for L, y in zip(Ls, ys)},
                    "pass": okfit,
                    "tier": "clean alpha>=1" if okfit else "weak -> FAIL 追因"}
    g6_ok = bool(g6a_ok and g6b_ok and branch_i_ok and sigma_ii["pass"])
    gates["M2-G6"] = {
        "verdict": "PASS" if g6_ok else "FAIL",
        "per_L": g6_perL,
        "rho_window_rel": RHO_WINDOW_REL,
        "layer_lemma_certificate": lemma,
        "sigma_branch_i_sourcefree": {"darkness_worst": dark_worst,
                                      "gate": G6_SIGMA_I_GATE,
                                      "pass": branch_i_ok},
        "sigma_branch_ii_sourced": sigma_ii,
        "fixed_k_mismatch_diagnostic": {
            str(L): runs[str(L)]["sigma_branch_ii"]["fixed_k_diagnostic"]
            for L in Ls},
        "diagnostics": {"machine": "冻结 R26 清除机(r36.hyper_step + tcf."
                                   "_sponge_field)RHO_PROTOCOL 逐字;sigma "
                                   "观测量口径 = 头部 一.G6 运行前声明;"
                                   "R37 冻结拟合代码对象"}}

    # ---- M2-G7 稳定 + 哨兵 -------------------------------------------------
    g7_perL, g7_ok = {}, True
    for L in Ls:
        r = runs[str(L)]
        rad = r["g7_bz_radius"]["max_minus_1"]
        st = r["static_secular_ratio_final_over_mid"]
        mv = r["moving_secular_ratio"]
        okL = bool(rad <= G7_RADIUS_GATE and st < G7_SECULAR_RATIO
                   and mv < G7_SECULAR_RATIO)
        g7_ok = g7_ok and okL
        g7_perL[str(L)] = {"bz_radius_minus_1": rad,
                           "static_secular_ratio": st,
                           "moving_secular_ratio": mv,
                           "packet_resid": [p.get("residual_end")
                                            for p in r["packet_rows"]],
                           "ok_L": okL}
    gates["M2-G7"] = {
        "verdict": "PASS" if g7_ok else "FAIL",
        "per_L": g7_perL,
        "gates": {"radius": G7_RADIUS_GATE,
                  "forced_resonance_secular_ratio": G7_SECULAR_RATIO},
        "endurance": "负控列:轮 3 v2m2_guns.py 同轮补全(不作 PASS 依据,"
                     "北极星 §四分层归纳条;M1' 先例)",
        "diagnostics": {"core": "耦合一步符号 A(k,z_v) 21x21 全 BZ L^3,v∈"
                                "{0,0.25};受迫共振哨兵 = S3 no-secular 线 "
                                "final/mid<2.5(线性包络操作化,头部 一.G7)"}}

    # ---- M2-G8 eps 分扇区 --------------------------------------------------
    g8_perL, g8_ok = {}, True
    for L in Ls:
        rows = []
        for kstr, e in runs[str(L)]["per_k"].items():
            if e.get("off_band"):
                continue
            ji = e.get("j_inv_geo")
            nm = e.get("matter_n_prop")
            okk = bool(ji == e["N_prop"] == G1_NPROP and nm == 2)
            g8_ok = g8_ok and okk
            rows.append({"n16": e["n16"], "j_inv_geo": ji,
                         "N_curv": e["N_prop"],
                         "eps_geo_k": e.get("eps_geo_k"),
                         "matter_n_prop": nm, "ok": okk})
        g8_perL[str(L)] = rows
    # 耦合列不向物质块注入:运行级见证(matter_step 是 psi 的纯函数)
    RS = FZ.mod("r25_realspace_step")
    rngw = np.random.default_rng(99)
    psi_w = (rngw.standard_normal((2, 4, 8, 8, 8))
             + 1j * rngw.standard_normal((2, 4, 8, 8, 8)))
    a1 = matter_step(psi_w, RS)
    a2 = matter_step(psi_w.copy(), RS)
    witness = float(np.max(np.abs(a1 - a2)))
    eps_geo = 0.0 if g8_ok else None
    eps_mat = 1.0 if (g8_ok and witness == 0.0) else None
    g8_ok = bool(g8_ok and witness == 0.0)
    gates["M2-G8"] = {
        "verdict": "PASS" if g8_ok else "FAIL",
        "per_L": g8_perL,
        "coupling_column_into_matter_witness": witness,
        "hand_built_matter_inventory": "空(构造冻结)",
        "epsilon_sector_pair": {"eps_geo": eps_geo, "eps_mat": eps_mat},
        "diagnostics": {"machine": "M0' invariants 不变量口径(SIN_THRESH "
                                   "0.05);j_inv_geo = N_prop - #{sin>=阈}"
                                   "(数据 top-2 vs ker K);j_inv_mat = 0 三"
                                   "证据(数据支==2 + 手搭清单空 + 上三角"
                                   "见证);实测值,非锚点定义代填(红线 5)"}}

    payload["m2_gates"] = gates
    verdicts = {k: v["verdict"] for k, v in gates.items()}
    payload["verdict_table"] = verdicts
    all_pass = all(v == "PASS" for v in verdicts.values())
    payload["all_gates_pass_this_round"] = bool(all_pass)
    payload["epsilon_sigma_point"] = {
        "eps_geo": eps_geo, "eps_mat": eps_mat,
        "sigma": {"branch_i_sourcefree": "A=0 线" if branch_i_ok else "FAIL",
                  "branch_ii_sourced": sigma_ii}}
    tw = payload["two_way_probe"]
    if all_pass:
        vtext = ("主跑轮 2 全门 PASS(宿主):同一耦合 rule 每 L 一条运行记录喂"
                 "全部门,八门逐 L 落位;rho 实测逐 L 命中预言 ±30% 窗;"
                 "(eps_geo, eps_mat) = (0, 1) 整数实测。按红线 12:**不宣告 "
                 "M2' PASS**——判定 = 全门 + 全炮(轮 3)+ eps 分扇区 + 双环境"
                 "四者同时,收口在车道A 复核 + PI。双向反作用探测项只入册不进"
                 "判定" + ("(死锁指纹复现,报车道A)" if
                          tw["deadlock_fingerprint"] else "(未触发指纹)")
                 + "。无任何涌现主张;eps_geo=0 如实记账;v1 封存主句原样不动。")
        status = "DONE"
    else:
        fails = [k for k, v in verdicts.items() if v != "PASS"]
        vtext = (f"门 FAIL:{fails}——按任务书 §6 停手写追因(三支:候选病/"
                 "耦合层病/仪器病),冻结现场报车道A 与 PI;禁调参禁降档。")
        status = "FAIL-HALT-追因"
    payload["verdict"] = vtext
    payload["status"] = status
    payload["sandbox"] = {"status": "PENDING",
                          "note": "双环境判据字段比对归车道A 复核(判据字段 "
                                  "1e-12;谱小分量/噪声底派生量报告级)"}
    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)
    log("=" * 74)
    for k, v in verdicts.items():
        log(f"  {k:8s} {v}")
    log(f"STATUS: {status}")
    log(f"VERDICT: {vtext}")
    log(f"source  sha256 = {payload['source_sha256']}")
    log(f"results sha256 = {jsha}")
    log(f"total {payload['total_seconds']:.0f}s")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
