"""v2m2_candidate -- M2' 候选构造件:三件套装配 + 符号证书 + 构造冻结
(任务书 §2/§2.4 交付物 2;lane B 轮 1,2026-07-27)。

构造冻结 = M2' 的"预言时点"(审定 R6):本件四要素同批交付 --
  [1] rho 预言(审定 R1):单层压缩比 rho_pred 逐 L 标定 + 推导(见 CERT-F 与
      RHO_* 常量;预言规则脚本头写死,数值于本件冻结,轮 2 主跑脚本头引用);
  [2] G2/G3 收敛阶 p 预注册(审定 R6/D-M2-3):P_PRED_G2 = P_PRED_G3 = 2.0
      (推导:placed kappa_i = 2 sin(k_i/2) = k_i + O(k_i^3) => 符号误差 O(a^2)
      => 静源 Green 函数与测试场偏折读数二阶收敛;同阶差分家族 M1' 实测先例
      p = 2.0019);
  [3] margin_declarations 全表(审定 R2,逐门 M2-G1..G8;单边阈分离 >= 1.5x,
      带型判据预期散布 << 半带宽 -- 操作化写死为 <= 半带宽/10;零裕度当场
      HALT 重设计,M1' P0(a) 先例);
  [4] trace_row_processing_present 布尔字段(审定 R6/D-M2-2):检测规则写死
      (见 TRACE_ROW_RULE),如实检测填写;自动裁定条件(升炮/记名退役)原文
      给出,签发进 v2m2_guns.py 头(轮 3)。

AUTHORITY(判据预注册,运行后不得回改;红线 4):
  docsv2/v2-任务书-M2-自旋2耦合闭环.md §1(主语边界)§2(三件套与 D-M2-1 已裁)
    §2.4(构造冻结四要素)§3(门列)§9(红线十三条)
  docsv2/v2-审定-M2任务书-2026-07-27.md(R1-R6 原文)
  docsv2/v2-纲领-北极星-涌现边界制图.md §四补条(边界骑线禁令,裕度口径)

三件套(任务书 §1.1 写死;D-M2-1 已裁 = 审定 R4):
  几何扇区 = R30 手搭复形(r30_tensor_complex_dynamical 谱系,只读):放置半角
    kappa 微积分 + placed Riemann/inc + 张量 div curl = 0 多项式恒等式 +
    Stormer-Verlet leapfrog(dt = c = cos(pi/3) = 0.5),ker K = gauge(4)+TT(2)
    按构造保持。eps_geo = 0,如实记账:几何扇区全部传播-曲率 DOF 手搭,零涌现。
  物质扇区 = v1 冻结走行物质半(cp1_v4_L2.walk_symbol / r25_realspace_step 冻结
    宏走行标量 a, b_i;I 类资产,证书链最全 -- 审定 R4 裁定);theta_m = pi/3
    与几何共 theta(J5 按构造瞄准,实测判定)。
  耦合层 = 源链(R10 精确键流 + R25 source-lift 静态件 + R25-E2 运动源镜像
    sector,保 h̄0i 语义:reality 生成镜像,非 Re(h̄+)):弱场单向源耦合 +
    测试场读数(审定 R4 批准基线);物质 T̄ 以 de Donder 相容方式作 R30 复形
    的源(kappa^m T̄_mn = 0 算子恒等式,本件 CERT-C 复证)。

符号层证书(门写死;任一不过 => HALT,如实记录病灶,不得自行改构造):
  CERT-A 几何基座:R30 Yee 证书(|eig|=1 / det=1 / 辛 / freq==shell,全部
         <= 1e-12,CFL ok)+ Bianchi 恒等式(BZ 扫 <1e-12,实空间 <1e-10);
  CERT-B 物质扇区:rc1a 忠实性证书 PASS + 走行 SU(2) 严格酉(U†U-I 与
         a^2+b.b-1 <= 1e-12,300 随机 k,种子写死)+ 物质传播支恰 2(判据 k
         逐点 |lam|=1 整数计数)+ J5 共锥全 theta 线 {0.4, pi/3, 1.0, 1.2}
         (冻结 rc3ii 机器,阈 1e-6);
  CERT-C 耦合结构 = 块三角单向,谱证书:耦合一步符号 A(k,z) = [[M_geo, B],
         [0, z_v]] 严格上三角(下左块恒 0,单向按构造);spec(A) = spec(M_geo)
         ∪ {z_v} 逐判据 k 数值复证(<=1e-10);共振间隙 gap = min|z_v -
         e^{±i w_geo}| 全 BZ x 预注册 v 集严格正(S3 resolvent 血统);
         + 源相容 kappa.eta.hbar <= 1e-12(BZ 12^3 x v 集)+ E2 镜像 oracle
         <= 1e-11 + Re-collapse 负控击穿(>=0.1,镜像 sector 承重有牙);
  CERT-D "无 Cherenkov 相配"声明(审定 R3):源速上限 v/c <= 0.5 即格点
         v <= 0.25(c = cos theta_g = 0.5);亚声速论证 = (a) 对锥速分离 2.0x;
         (b) 格点最坏相速 min_k w(k)/|k| 数值下界 与 v_max 的分离比;(c) 相位
         匹配间隙 min gap > 0 严格(数值),三项同册 => 无相位匹配增长通道;
  CERT-E trace_row 检测(规则 TRACE_ROW_RULE):演化期迹行处理三证据检测,
         如实填写布尔;
  CERT-F rho 标定(R1):冻结 R26 清除机(r36.hyper_step + tcf._sponge_field,
         kappa_work = 冻结规则 win_max/25)按 L 等比协议(RHO_PROTOCOL)逐 L
         逐判据方向测单层压缩 rho_L = bulk_AC(DeltaT_L)/bulk_AC(0),
         DeltaT_L = round(L/c) = 2L(R26 已证清除时标 ~L/c 且 k-无关);
         rho_pred 逐 L 冻结,要求 max <= 0.67(对 1 分离 >= 1.5x),
         主跑实测落 rho_pred ±30%(逐 L)方计该列 PASS;b_layer 预期量级 =
         机器底(r36 血统 retained AC <= 2.33e-15),线 1e-12(相对)。

eps 分扇区记账(任务书 §1.3 诚实条款;禁混合 eps):
  (eps_geo, eps_mat) 二元组。eps_geo = 0:定义属性(hand_built = all,几何扇区
  全手搭),主跑轮 2 由 j_inv 机器实测落位(j_inv = N_curv,整数逐位,不引锚点
  定义值代填 -- 红线 5)。eps_mat:目标 1;本件预飞级小格验证 = 物质传播支恰 2
  (实测整数)+ 物质扇区手搭 DOF 清单为空 + 耦合列不向物质块注入(上三角结构)
  => j_inv_mat = 0(预飞级);主跑轮 2 数据 SVD j_inv 全 L 全 k 实测。

措辞红线(红线 10/11/12):本件无任何涌现主张;不使用"自旋 2 涌现";v1 封存
主句原样不动,本件不含任何弱化/改写/"有望重开"暗示;构造冻结 != 闭环;
构造冻结前禁开主跑 -- 本轮零主跑零炮组。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m2_candidate.py
      (writes data/results/v2m2_candidate.json, 增量写盘)
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
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

from rulespace_v2 import frozen as FZ                      # noqa: E402
from rulespace_v2 import invariants as INV                 # noqa: E402
from rulespace_v2.candidate import CandidateV2             # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m2_candidate.json")
PREFLIGHT_JSON = os.path.join(ROOT, "data", "results", "v2m2_preflight.json")

# ---- 判据与协议常量(写死;运行后不得回改,红线 4) -----------------------
TOL_JUDGE = 1e-12
TOL_ORACLE = 1e-11          # E2 镜像 sector 符号层 oracle(任务书 §5-3)
TOL_RS_ID = 1e-10           # Bianchi 实空间算子恒等式(r30 冻结口径)
TOL_SPEC_UNION = 1e-10      # CERT-C 谱并集数值复证
RE_COLLAPSE_MIN = 0.1       # Re-collapse 负控必须击穿(冻结 E2-1 实测 2.328)
SEED_UNITARY = 20260727     # CERT-B 随机 k 种子
N_RANDK_MATTER = 300
SEED_STATIC = 250725        # 静态逐位退化(S2(b) 冻结协议种子谱系)
N_RANDK_STATIC = 200

THETA_SHARED = math.pi / 3.0            # theta_g = theta_m 共 theta(写死)
C_CONE = math.cos(THETA_SHARED)         # = 0.5;dt = c(R30 冻结标定点)
DT = C_CONE
V_MAX_LATTICE = 0.25                    # 审定 R3 钉死:格点 v <= 0.25
V_OVER_C_MAX = 0.5                      # = V_MAX_LATTICE / C_CONE
V_LATTICE_SET = (0.05, 0.15, 0.25)      # 预注册运动源 v 集(= v/c {0.1,0.3,0.5})
ETA_BASELINE = 1.0                      # 弱场单向线性响应基线耦合强度
BZ_N_CHER = 16                          # CERT-C/D 共振间隙 BZ 网格
BZ_N_SRC = 12                           # CERT-C 源相容 BZ 网格(候选自证行)
E2_N = 12
E2_MODES = [(1, 0, 0), (1, 1, 0), (2, 1, 0), (1, 2, -1), (2, 2, 1),
            (3, 1, -2), (1, 3, 2), (2, -1, 3)]   # cert_E2_1 冻结名单

L_LIST = [16, 24, 32, 48]
# D-M2-4 终版判据 k 集(只许收紧):3 轴向 + 面斜 + 棱斜 + 体对角(必含)
# + Nyquist;n 随 L 重标 n_L = round(n16*L/16),实采 k 入册。
JUDGE_K_SET_M2 = [[2, 0, 0], [0, 2, 0], [0, 0, 2], [2, 2, 0], [3, 1, 0],
                  [2, 2, 2], [8, 0, 0]]
RAY_DIRECTIONS = [[1, 0, 0], [1, 1, 0], [1, 1, 1]]

# ---- [1] rho 预言协议(审定 R1;规则写死,数值于本件标定后冻结) ----------
RHO_KSET16 = [(2, 0, 0), (0, 3, 0), (2, 2, 0), (2, 2, 2)]   # R32/R36 判据方向
RHO_PROTOCOL = {
    "machine": ("冻结 R26 清除机:r36_r3_verification.hyper_step(双曲输运,"
                "kappa_work 阻尼)+ tensor_coin_feedback._sponge_field(L4 "
                "sponge)-- 全部只读 import,判据核零重写"),
    "kappa_work_rule": "r36.recompute_kappa_window(c=0.5) 冻结规则 win_max/25",
    "layer_rule": "DeltaT_L = round(L/c) = 2L(R26 清除时标 ~L/c, k-无关)",
    "lattice_scaling": ("sponge 宽 w_sp = max(3, round(10*L/44)),sp_max = "
                        "0.30;pad = max(2, round(12*L/44));包络 sigma = "
                        "6*L/44;k = 2*pi*n_L/L,n_L = round(n16*L/16);"
                        "全部与 r36 part_C(NA=44)等比"),
    "observable": ("rho_L,k = bulk_AC(DeltaT)/bulk_AC(0),bulk = pad 内 |z| "
                   "总量,AC = 去 DC(R26/A2 受保护守恒零模按正控记账,"
                   "r36 冻结口径);floor_L,k = bulk_AC(3*DeltaT)/bulk_AC(0) "
                   "入册为 b_layer 预期量级参考"),
    "prediction_rule": ("rho_pred 逐 L = max_k rho_L,k(本件冻结);"
                        "全局 rho_pred_max <= 0.67 必须成立(R1:对 1 分离 "
                        ">= 1.5x),否则 HALT 重设计;主跑 G6(a) 以同一协议"
                        "同一方向集实测,逐 L 落 rho_pred_L ±30% 方计 PASS"),
    "b_layer": ("预期量级 = 机器底(r36 part_C 血统:T→inf retained "
                "clearable AC <= 2.33e-15);线 = 1e-12(相对);主跑长段"
                "末端读取"),
}
RHO_WINDOW_REL = 0.30
RHO_MAX_ALLOWED = 0.67

# ---- [2] G2/G3 收敛阶 p 预注册(审定 R6/D-M2-3;写死) ---------------------
P_PRED_G2 = 2.0
P_PRED_G3 = 2.0
P_PRED_DERIVATION = (
    "placed 半角符号 kappa_i = 2 sin(k_i/2) = k_i + O(k_i^3)(奇函数,无二阶"
    "项)=> 连续极限符号误差 O(a^2);静源 Newton 井 h00/phi 与测试场偏折比的"
    "格点读数误差由该二阶符号误差主导 => 收敛阶 p = 2(G2 与 G3 同)。同阶"
    "差分家族先例:M1' 光速各向同性实测 p = 2.0019(v2-收口-M1)。主跑逐 L "
    "序列以此 p 预注册拟合,不得运行后改 p。")

# ---- [4] trace_row 检测规则与自动裁定条件(审定 R6/D-M2-2;写死) ----------
TRACE_ROW_RULE = (
    "trace_row_processing_present := 候选在演化期对演化态执行任何迹行读取/"
    "回馈处理(v1 CP1v4-L3 走行约束装配层 T 行语义)。检测三证据(全部数值/"
    "结构,本件 CERT-E):(1) 几何步与迹投影算子严格对易(component-diagonal "
    "标量 leapfrog,对易子 == 0 位级);(2) 单向结构:耦合一步符号严格上三角,"
    "几何态不回读(下左块恒 0)=> 演化期不存在对几何态迹的任何处理;(3) 源"
    "构造使用 eta-迹反转(trace-reversed T̄,R16 约定)-- 静态源侧映射,与 "
    "v1 走行装配层 T 行不同物(任务书 §3 G5 血统注),如实申报不计入本字段。")
TRACE_ROW_AUTO_ADJUDICATION = (
    "自动裁定条件(签发进 v2m2_guns.py 头,同滞后阻尼炮先例):若 "
    "trace_row_processing_present == true,或耦合层任何实现变更引入演化期"
    "迹行处理,则 C5(v1) T 行三元组(仅W/仅A/W+A)自动升格为主炮(预飞先行);"
    "若为 false,三元组记名退役,仅当变体引入迹行处理时强制复活。")

# ---- [3] margin_declarations 静态行(审定 R2;运行时并入 rho/Cherenkov 值)
BAND_SPREAD_FACTOR = 0.1    # "预期散布 << 半带宽" 操作化:<= 半带宽/10(写死)
MARGIN_MIN = 1.5

# ---- 先行写死的冻结 hash(红线 2;与 v2m2_preflight.py 同册) --------------
M0_SEVEN_SHA256 = {
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
M1_CHAIN_SHA256 = {
    "rulespace_v2/spin1.py":
        "69317d39ce304740b4e096df63a85ccfd63beb2a3094038ba9ebd2d923b17384",
    "data/results/v2m1_candidate.json":
        "4b6db37993ee69cc2e2a452888e510f8b8f1369001c85d03d5ef22e52efc3a31",
    "data/results/v2m1_maxwell_loop_r3.json":
        "2cd50d89e5dee3407db911da1a462c14292049559bc2aaa968c04b45951ceb57",
    "data/results/v2m1_guns_r2.json":
        "e8e9d80dbf77f6a39fc1bd3ca16ef027c6eb459455f6b550d7656cfb651d33ff",
}
SRC_CHAIN_SHA256 = {
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
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_canonical(obj):
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"), default=_jd)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def leap_omega(R30M, k):
    """几何 leapfrog 本征相位 w(k) = arccos(1 - dt^2 L(kappa)/2)(CFL 内)。"""
    Lp = R30M.L_placed(k)
    x = 1.0 - 0.5 * DT * DT * Lp
    return float(np.arccos(np.clip(x, -1.0, 1.0)))


def spectra_match(lamA, lamB):
    """两组本征值多重集最近邻匹配的最大距离(v2m1_candidate 同款比较器;
    简并拷贝按实部排序会被 LAPACK 噪声交错,故禁用 sort 逐位对齐)。"""
    lamB = list(lamB)
    worst = 0.0
    for a in lamA:
        d = [abs(a - b) for b in lamB]
        i = int(np.argmin(d))
        worst = max(worst, d[i])
        lamB.pop(i)
    return worst


# ===========================================================================
#  margin_declarations 全表(审定 R2;静态数值 = 冻结血统实测,写死)
# ===========================================================================
def build_margin_table(rho_pred_max, cherenkov):
    """逐门一行:预期信号值/阈值(或带宽)/裕度/依据。运行时只并入本件标定的
    rho_pred_max 与 Cherenkov 数值(规则见头部常量),其余数字为写死血统值。"""
    T = []

    def single(gate, criterion, expected, threshold, basis):
        T.append({"gate": gate, "criterion": criterion, "type": "single-sided",
                  "expected": expected, "threshold": threshold,
                  "margin_factor": threshold / expected,
                  "basis": basis})

    def band(gate, criterion, expected_value, expected_spread, center,
             half_band, basis):
        T.append({"gate": gate, "criterion": criterion, "type": "band",
                  "expected_value": expected_value,
                  "expected_spread": expected_spread,
                  "band_center": center, "half_band": half_band,
                  "spread_over_halfband": expected_spread / half_band,
                  "basis": basis})

    def integer(gate, criterion, expected, basis):
        T.append({"gate": gate, "criterion": criterion, "type": "integer",
                  "expected": expected, "threshold": "整数逐位(散布 0)",
                  "margin_factor": "exact", "basis": basis})

    integer("M2-G1", "N_prop(k;L) == 2 逐 L 全判据 k(体对角必含)",
            "[2,2,2,2] 全 k 稳定",
            "r30_results.json decisive_run n_prop_seq(冻结)+ 预飞 (i) 复跑")
    single("M2-G1", "svn 断崖 sv3/sv1(计数阈之下)", 1.7e-15, 0.05,
           "r30 冻结 sv 列 max sv3 = 1.64e-15;阈 = SV_THRESH 0.05(共享判据)")
    single("M2-G1", "J5 共锥 |w_geo - w_shell| 全 theta 线", 3.1e-16, 1e-6,
           "rc3ii j5_cocone 冻结 worst 3.05e-16;r30 freq-shell 2.22e-16")
    band("M2-G2", "静源 h00/phi", 2.0000015, 1.6e-6, 2.0, 0.02,
         "v1 tensor_qca 冻结 judge_fact2 h00_over_phi = 2.0000015373975284;"
         "p 预注册 = 2.0(本件 [2])")
    band("M2-G3", "偏折比(置零 h_ij 反事实)", 1.9999866, 1.4e-5, 2.0, 0.02,
         "v1 tensor_qca 冻结 judge3 evolved_field_ratio = 1.999986572093466;"
         "p 预注册 = 2.0(本件 [2])")
    single("M2-G4", "锥外分量(严格局域公理哨兵)", 1e-15, 1e-12,
           "整数 roll 支撑半径 1 结构 + M1' 动源段锥外实测位级零(先例);"
           "预期报位级零,声明 1e-15 为保守上界")
    single("M2-G4", "h̄0i 对符号层 oracle", 2.9e-15, 1e-11,
           "E2-1 冻结 2.59e-15;本件预飞 (iii) 实测 2.9e-15")
    single("M2-G4", "源处 de Donder 残差", 1.5e-15, 1e-10,
           "S2 冻结 1.40e-15;本件预飞 (iii) kappa.eta.hbar 实测 1.3e-15")
    single("M2-G5", "T̄ 行守恒残差 kappa^m T̄_mn", 1.5e-15, 1e-12,
           "kappa.eta.hbar == 0 为多项式恒等式(S2/本件 CERT-C 机器实测 "
           "~1.4e-15);新主语 oracle 本件重推,不抄 v1 数字(G5 血统注)")
    single("M2-G5", "无源段离散能量 H 相对漂移", 1e-14, 1e-12,
           "辛 leapfrog 无长期漂移:件10 Yee 能量漂移实测 2.97e-16;"
           "R30 |eig|-1 = 2.22e-16;声明 1e-14 为保守上界")
    T.append({"gate": "M2-G6", "criterion": "单层压缩 rho < 1(R1 预言先行)",
              "type": "single-sided",
              "expected": rho_pred_max, "threshold": 1.0,
              "margin_factor": (1.0 / rho_pred_max) if rho_pred_max > 0
              else float("inf"),
              "window_rule": "主跑实测 rho 逐 L 落 rho_pred_L ±30% 方计 PASS",
              "basis": "本件 CERT-F 冻结 R26 机按 L 等比标定(协议 RHO_PROTOCOL)"})
    single("M2-G6", "b_layer(相对)", 2.4e-15, 1e-12,
           "r36 part_C 冻结 retained clearable AC <= 2.33e-15(机器底血统)")
    single("M2-G6", "sigma 外壳 A=0 分支:无源段 resid", 1.4e-14, 1e-12,
           "r30 冻结 deDonder darkness max 1.33e-14(恒等式护约束);有源段"
           "非机器零则走 D3 两档预写分支(不降档通融)")
    single("M2-G7", "BZ 谱半径超增长", 2.3e-16, 1e-9,
           "R30 严格酉 |eig|-1 = 2.22e-16(冻结);哨兵定量线 = 审定 R5 "
           "D-M2-5(基线段与门同线 1e-9)")
    T.append({"gate": "M2-G7", "criterion": "受迫共振哨兵(线性包络,审定 R3)",
              "type": "structural-separation",
              "expected": ("有界稳态响应:共振间隙 min|z_v - e^{±i w_geo}| = "
                           f"{cherenkov['gap_min']:.4f} 严格正(全 BZ x v 集)"),
              "threshold": "超线性增长 = FAIL(哨兵)",
              "margin_factor": "结构性(间隙严格正 => 无 Jordan 增长通道)",
              "basis": ("本件 CERT-C/D 数值 + S3 冻结 resolvent 间隙血统"
                        "(no secular growth)")})
    integer("M2-G8", "eps 分扇区:j_inv_geo == N_curv 且 j_inv_mat == 0",
            "(eps_geo, eps_mat) = (0, 1),整数逐位,双环境",
            "M0' j_inv 不变量口径(整数、基稳健);主跑实测,不引锚点定义值"
            "代填(红线 5);本件预飞级小格验证见 CERT-B/epsilon 节")
    T.append({"gate": "CERT-D", "criterion": "无 Cherenkov 相配(声明)",
              "type": "structural-separation",
              "expected": {"v_over_c_max": V_OVER_C_MAX,
                           "v_lattice_max": V_MAX_LATTICE,
                           "cone_separation": C_CONE / V_MAX_LATTICE,
                           "min_phase_speed_lattice":
                               cherenkov["min_phase_speed"],
                           "phase_speed_separation":
                               cherenkov["min_phase_speed"] / V_MAX_LATTICE,
                           "gap_min": cherenkov["gap_min"]},
              "threshold": "间隙 > 0 严格(相位匹配通道不存在)",
              "margin_factor": "分离论证(§四补条允许的明示分离形式)",
              "basis": "审定 R3 原文口径;本件 CERT-D 数值"})
    return T


def margin_table_ok(T):
    """边界骑线禁令扫描:单边阈 >= 1.5x;带型散布 <= 半带宽/10;整数/结构行
    按各自口径。零裕度 => False(HALT 重设计,M1' P0(a) 先例)。"""
    worst = {"single_min_factor": float("inf"), "band_max_ratio": 0.0}
    ok = True
    for row in T:
        if row["type"] == "single-sided":
            f = row["margin_factor"]
            worst["single_min_factor"] = min(worst["single_min_factor"], f)
            ok = ok and (f >= MARGIN_MIN)
        elif row["type"] == "band":
            r = row["spread_over_halfband"]
            worst["band_max_ratio"] = max(worst["band_max_ratio"], r)
            ok = ok and (r <= BAND_SPREAD_FACTOR)
    return bool(ok), worst


# ===========================================================================
#  main
# ===========================================================================
def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m2-candidate (M2' 候选构造件;任务书 §2/§2.4;lane B 轮 1)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-任务书-M2-自旋2耦合闭环.md §1/§2/§3/§9",
                      "docsv2/v2-审定-M2任务书-2026-07-27.md(R1-R6)",
                      "docsv2/v2-纲领-北极星-涌现边界制图.md §四补条"],
        "environment": env,
        "tol": {"judge": TOL_JUDGE, "oracle_e2": TOL_ORACLE,
                "bianchi_realspace": TOL_RS_ID,
                "spec_union": TOL_SPEC_UNION,
                "re_collapse_teeth_min": RE_COLLAPSE_MIN,
                "seed_unitary": SEED_UNITARY, "seed_static": SEED_STATIC},
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "wording_redline": ("本件无任何涌现主张;'自旋 2 涌现'为禁句(几何扇区 "
                            "eps=0,涌现主语不成立);v1 封存主句原样不动;"
                            "构造冻结 != 闭环;eps 实测在主跑轮 2(红线 5/10/11)"),
        "sealed_v1_boundary": ("v1 封存主句 -- '纲领四承诺全要时,自旋 2 的 M3 "
                               "结构性不可达,死于极化计数与稳定性死锁' -- 原样"
                               "不动;本候选是封存文档 §八 选项 A(RC3-(ii) R2 "
                               "落点)的正面化:手搭正确几何 + 涌现物质耦合,"
                               "eps 轴 eps_geo=0 端的耦合闭环点,非任何位移"),
    }
    write_json(payload)

    print("v2m2 candidate: 三件套装配 + 符号证书 + 构造冻结(四要素同批)")
    print("=" * 74)
    print(f"[env] numpy {env['numpy_version']}  blas={env['blas']}  "
          f"{env['platform']}")

    # ---- 0. hash 校验 + 预飞前提 ------------------------------------------
    checked, hok = {}, True
    for rel, exp in {**M0_SEVEN_SHA256, **M1_CHAIN_SHA256,
                     **SRC_CHAIN_SHA256}.items():
        got = sha256_file(os.path.join(ROOT, rel))
        m = (got == exp)
        hok = hok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    hz0 = FZ.verify_frozen()
    payload["hash_verification"] = {"m2_pinned": {"pass": hok,
                                                  "checked": checked},
                                    "m0_registry_pass": hz0["pass"]}
    write_json(payload)
    print(f"[cert] 先行写死 hash({len(checked)} 件): "
          f"{'PASS' if hok else 'FAIL'};M0' 注册表: "
          f"{'PASS' if hz0['pass'] else 'FAIL'}")
    if not (hok and hz0["pass"]):
        payload["status"] = "HALT-frozen-hash-mismatch"
        write_json(payload)
        return 1

    with open(PREFLIGHT_JSON, "r", encoding="utf-8") as fh:
        PF = json.load(fh)
    pf_ok = bool(PF.get("preflight_pass"))
    payload["preflight_precondition"] = {
        "file": "data/results/v2m2_preflight.json",
        "sha256_at_read": sha256_file(PREFLIGHT_JSON),
        "preflight_pass": pf_ok}
    write_json(payload)
    print(f"[前提] 预飞 PASS: {pf_ok}")
    if not pf_ok:
        payload["status"] = "HALT-preflight-not-passed"
        payload["verdict"] = "预飞未 PASS:禁构造冻结禁主跑(任务书 §5),报车道A。"
        write_json(payload)
        return 1

    R30M = FZ.mod("r30_tensor_complex_dynamical")
    RC = FZ.mod("rc1a_tensor_index_scan")
    RC3 = FZ.mod("rc3ii_relaxation_framework")
    R36M = FZ.mod("r36_r3_verification")
    MS = FZ.mod("r25_moving_source_symbol")
    RSM = FZ.mod("r25_moving_source_realspace")
    R25W = FZ.mod("r25_auxiliary_wilson_complex")
    L2 = FZ.mod("cp1_v4_L2")
    R15 = FZ.mod("r15_walk_dedonder")
    tcf = FZ.mod("rulespace_gpu.tensor_coin_feedback")
    ETA = MS.ETA

    # ---- CERT-A 几何基座(R30,只读复证) ----------------------------------
    tr = time.time()
    kbroad = [tuple(n) for n in JUDGE_K_SET_M2] + \
        [(1, 3, 2), (4, 1, 0), (5, 0, 0), (3, 3, 3), (1, 0, 0),
         (6, 2, 1), (0, 5, 2), (2, 4, 3)]
    yc = R30M.yee_certificates(kbroad)
    ci = R30M.complex_identities_bz()
    ci_rs = R30M.complex_identity_realspace()
    certA_ok = bool(yc["max_abs_eig_minus_1"] <= TOL_JUDGE
                    and yc["max_det_minus_1"] <= TOL_JUDGE
                    and yc["max_symplectic_defect"] <= TOL_JUDGE
                    and yc["max_freq_minus_shell"] <= TOL_JUDGE
                    and yc["cfl_ok"]
                    and ci["div_inc_contracted_Bianchi_kappaG"] <= TOL_JUDGE
                    and ci["div_inc_full_second_Bianchi"] <= TOL_JUDGE
                    and ci["inc_D_riemann_of_gauge"] <= TOL_JUDGE
                    and ci_rs <= TOL_RS_ID)
    payload["CERT_A_geometry_base"] = {
        "yee_certificates": {k: v for k, v in yc.items() if k != "locality"},
        "bianchi_identities": {**ci,
                               "div_inc_realspace_operator_identity": ci_rs},
        "dt_equals_c": DT, "theta_g": THETA_SHARED,
        "epsilon_geo_declaration": ("eps_geo = 0:几何扇区全部传播-曲率 DOF "
                                    "手搭(hand_built=all),零涌现,如实记账"
                                    "(任务书 §1.1);主跑 j_inv 实测落位"),
        "seconds": time.time() - tr, "pass": certA_ok}
    write_json(payload)
    print(f"[CERT-A 几何基座] {'PASS' if certA_ok else 'FAIL'}  "
          f"|eig|-1={yc['max_abs_eig_minus_1']:.1e}  "
          f"Bianchi={ci['div_inc_contracted_Bianchi_kappaG']:.1e}  "
          f"({time.time()-tr:.1f}s)")

    # ---- CERT-B 物质扇区(v1 冻结走行物质半) ------------------------------
    tr = time.time()
    faith = RC.faithfulness_certificate()
    rng = np.random.default_rng(SEED_UNITARY)
    uni_dev, su2_dev = 0.0, 0.0
    for _ in range(N_RANDK_MATTER):
        k = rng.uniform(-np.pi, np.pi, 3)
        U = L2.walk_symbol(k)
        uni_dev = max(uni_dev, float(np.max(np.abs(
            U.conj().T @ U - np.eye(2)))))
        a = np.trace(U) / 2.0
        b = np.array([1j * np.trace(s @ U) / 2.0 for s in MS.PAULI])
        su2_dev = max(su2_dev, abs(complex(a * a + b @ b) - 1.0))
    n_mat_prop = {}
    mat_prop_ok = True
    for n16 in JUDGE_K_SET_M2:
        k = np.array(n16, float) * (2 * np.pi / 16)
        lam = np.linalg.eigvals(L2.walk_symbol(k))
        n = int(np.sum(np.abs(np.abs(lam) - 1.0) <= TOL_JUDGE))
        n_mat_prop[str(tuple(n16))] = n
        mat_prop_ok = mat_prop_ok and (n == 2)
    j5rows = RC3.j5_cocone_across_theta()
    j5_worst = max(r["max_abs_w_leapfrog_minus_walkshell"] for r in j5rows)
    j5_thetas = [r["theta"] for r in j5rows]
    theta_shared_in_line = any(abs(t - THETA_SHARED) < 1e-12 for t in j5_thetas)
    certB_ok = bool(faith["PASS"] and uni_dev <= TOL_JUDGE
                    and su2_dev <= TOL_JUDGE and mat_prop_ok
                    and j5_worst < 1e-6 and theta_shared_in_line)
    payload["CERT_B_matter_sector"] = {
        "rc1a_faithfulness": faith,
        "walk_unitarity_max_dev": uni_dev,
        "su2_identity_a2_plus_bb_minus_1": su2_dev,
        "n_randk": N_RANDK_MATTER,
        "matter_n_prop_per_judge_k": n_mat_prop,
        "j5_cocone_across_theta": j5rows,
        "j5_worst": j5_worst,
        "theta_m_equals_theta_g": {"theta": THETA_SHARED,
                                   "in_j5_line": bool(theta_shared_in_line)},
        "carrier_decision": ("D-M2-1 已裁(审定 R4):基线物质载体 = v1 冻结"
                             "走行物质半(I 类资产,证书链最全);其他局域酉 "
                             "Dirac 载体归 M3' 族参数,不进 M2'"),
        "seconds": time.time() - tr, "pass": certB_ok}
    write_json(payload)
    print(f"[CERT-B 物质扇区] {'PASS' if certB_ok else 'FAIL'}  "
          f"酉性={uni_dev:.1e}  SU(2)={su2_dev:.1e}  物质支={list(n_mat_prop.values())}  "
          f"J5={j5_worst:.1e}  ({time.time()-tr:.1f}s)")

    # ---- CERT-C 耦合结构:块三角单向 + 谱证书 + 源相容 + 镜像 oracle -------
    tr = time.time()
    # (a) 谱并集数值复证(判据 7k x v=0.25,21x21 显式块三角)
    union_dev, lower_left = 0.0, 0.0
    for n16 in JUDGE_K_SET_M2:
        k = np.array(n16, float) * (2 * np.pi / 16)
        w = leap_omega(R30M, k)
        M2x2 = R30M.leap_M(k)
        Mgeo = np.kron(np.eye(10), M2x2)
        z = complex(np.exp(-1j * V_MAX_LATTICE * k[0]))
        D10 = MS.normal_h_packed(k, z)
        B = np.zeros((20, 1), complex)
        B[1::2, 0] = ETA_BASELINE * D10          # 驱动注入 pi 行(力项)
        A = np.block([[Mgeo.astype(complex), B],
                      [np.zeros((1, 20), complex),
                       np.array([[z]], complex)]])
        lower_left = max(lower_left, float(np.max(np.abs(A[20, :20]))))
        lam = np.linalg.eigvals(A)
        expect = np.array([np.exp(1j * w)] * 10 + [np.exp(-1j * w)] * 10 + [z])
        union_dev = max(union_dev, spectra_match(lam, expect))
    # (b) 共振间隙(全 BZ x 预注册 v 集)+ 格点最坏相速
    gap_min, minph = float("inf"), float("inf")
    for idx in np.ndindex(BZ_N_CHER, BZ_N_CHER, BZ_N_CHER):
        if idx == (0, 0, 0):
            continue
        k = 2 * np.pi * np.array(idx, float) / BZ_N_CHER
        k = np.where(k > np.pi, k - 2 * np.pi, k)        # 折回第一 BZ
        w = leap_omega(R30M, k)
        nk = float(np.linalg.norm(k))
        if nk > 1e-12:
            minph = min(minph, w / nk)
        for v in V_LATTICE_SET:
            z = np.exp(-1j * v * k[0])
            gap_min = min(gap_min,
                          float(min(abs(z - np.exp(1j * w)),
                                    abs(z - np.exp(-1j * w)))))
    # (c) 源相容 kappa.eta.hbar == 0(候选自证行,BZ 12^3 x {0} ∪ v 集)
    dd_worst = 0.0
    for v in (0.0,) + V_LATTICE_SET:
        vv = np.array([v, 0.0, 0.0])
        for idx in np.ndindex(BZ_N_SRC, BZ_N_SRC, BZ_N_SRC):
            if idx == (0, 0, 0):
                continue
            k = 2 * np.pi * np.array(idx, float) / BZ_N_SRC
            z = complex(np.exp(-1j * float(vv @ k)))
            hb, _ = MS.hbar_moving(k, z)
            dd_worst = max(dd_worst, float(np.max(np.abs(
                (ETA @ MS.kappa(k, z)) @ hb))))
    # (d) 静态极限逐位 + E2 镜像 oracle + Re-collapse 负控
    rng = np.random.default_rng(SEED_STATIC)
    static_dev = 0.0
    for _ in range(N_RANDK_STATIC):
        k = rng.uniform(-np.pi, np.pi, 3)
        U = L2.walk_symbol(k)
        static_dev = max(static_dev, float(np.max(np.abs(
            MS.normal_h_packed(k, 1.0) - R25W.static_newton_lift(U)))))
    oracle_dev, re_dd, re_imcur = 0.0, 0.0, 0.0
    for v in V_LATTICE_SET:
        vv = np.array([v, 0.0, 0.0])
        for nv in E2_MODES:
            k = 2 * np.pi * np.array(nv, float) / E2_N
            z = complex(np.exp(-1j * float(vv @ k)))
            ph = RSM.plane(k, E2_N)
            hb = MS.hbar_moving(k, z)[0]
            oracle_dev = max(oracle_dev, float(np.max(np.abs(
                RSM.hbar0i_realspace(ph, z) - hb[0, 1:]))))
            hb_re = np.real(hb)
            re_imcur = max(re_imcur, float(np.max(np.abs(
                np.imag(hb_re[0, 1:])))))
            re_dd = max(re_dd, float(np.max(np.abs(
                (ETA @ MS.kappa(k, z)) @ hb_re))))
    certC_ok = bool(lower_left == 0.0 and union_dev <= TOL_SPEC_UNION
                    and gap_min > 0.0 and dd_worst <= TOL_JUDGE
                    and static_dev <= TOL_JUDGE and oracle_dev <= TOL_ORACLE
                    and re_dd >= RE_COLLAPSE_MIN and re_imcur == 0.0)
    payload["CERT_C_coupling_block_triangular"] = {
        "structure": ("一步耦合符号 A(k, z_v) = [[M_geo(20x20, kron(I10, "
                      "leap_M)), B(源注入 pi 行)], [0, z_v]] -- 严格上三角,"
                      "单向按构造(几何 -> 物质回授不存在,基线);测试场 "
                      "Eddington 读数在 h 背景上(置零 h_ij 反事实),不进演化"),
        "lower_left_block_max": lower_left,
        "spectrum_union_dev_max": union_dev,
        "spectrum_statement": ("spec(A) = spec(M_geo) ∪ {z_v};几何谱严格单位圆"
                               "(酉),z_v 单位圆;共振间隙严格正 => A 可对角化,"
                               "响应有界(S3 resolvent 血统),无新增长模"),
        "resonance_gap_min_over_BZ_and_v": gap_min,
        "min_phase_speed_lattice": minph,
        "source_compat_kappa_eta_hbar_max": dd_worst,
        "static_z1_bitwise_vs_static_newton": static_dev,
        "e2_mirror_oracle_dev": oracle_dev,
        "re_collapse_negative_control": {"deDonder_residual": re_dd,
                                         "momentum_current_annihilated":
                                             re_imcur,
                                         "min_required": RE_COLLAPSE_MIN},
        "eta_baseline": ETA_BASELINE,
        "two_way_probe_policy": ("双向反作用仅记名探测项(审定 R4):预算 <= "
                                 "单轮计算时间 10%、哨兵必备(D-M2-5 定量线)、"
                                 "任何不稳即停,结果只入册不进判定;基线全绿"
                                 "前不试跑 -- 本轮不含任何双向内容"),
        "seconds": time.time() - tr, "pass": certC_ok}
    write_json(payload)
    print(f"[CERT-C 耦合谱证书] {'PASS' if certC_ok else 'FAIL'}  "
          f"下左块={lower_left:.1e}  谱并集={union_dev:.1e}  "
          f"间隙={gap_min:.4f}  相容={dd_worst:.1e}  oracle={oracle_dev:.1e}  "
          f"({time.time()-tr:.1f}s)")

    # ---- CERT-D 无 Cherenkov 相配声明(审定 R3) ---------------------------
    cherenkov = {
        "v_over_c_max": V_OVER_C_MAX, "v_lattice_max": V_MAX_LATTICE,
        "c_cone": C_CONE, "v_lattice_set": list(V_LATTICE_SET),
        "min_phase_speed": minph, "gap_min": gap_min,
        "cone_separation_ratio": C_CONE / V_MAX_LATTICE,
        "phase_speed_separation_ratio": minph / V_MAX_LATTICE,
        "declaration": (
            "无 Cherenkov 相配:源速上限 v/c <= 0.5(即格点单位 v <= 0.25,"
            "c = cos theta_g = 0.5,审定 R3 钉死)。亚声速论证三项:(a) 对几何"
            f"锥速分离 {C_CONE / V_MAX_LATTICE:.2f}x;(b) 几何带格点最坏相速 "
            f"min_k w(k)/|k| = {minph:.4f} > v_max = {V_MAX_LATTICE}(分离比 "
            f"{minph / V_MAX_LATTICE:.3f},明示分离论证,§四补条允许形式);"
            f"(c) 相位匹配间隙 min|z_v - e^{{±i w}}| = {gap_min:.4f} > 0 严格"
            "(全 BZ 16^3 x 预注册 v 集)=> 不存在 w(k) = v.k 的相位匹配增长"
            "通道;受迫响应有界于线性包络(稳态辐射 + 传播,G7 哨兵语言)。")}
    certD_ok = bool(gap_min > 0.0 and minph > V_MAX_LATTICE)
    payload["CERT_D_no_cherenkov"] = {**cherenkov, "pass": certD_ok}
    write_json(payload)
    print(f"[CERT-D 无 Cherenkov] {'PASS' if certD_ok else 'FAIL'}  "
          f"min相速={minph:.4f} > v_max={V_MAX_LATTICE}  间隙={gap_min:.4f}")

    # ---- CERT-E trace_row 检测(审定 R6/D-M2-2) ---------------------------
    tr = time.time()
    # 证据 (1):几何步与迹投影严格对易(判据 k 逐点,位级)
    tvec = np.zeros(10)
    for j, (m, n) in enumerate(R15.SYM):
        if m == n:
            tvec[j] = R15.ETA[m, m]
    tvec = tvec / np.linalg.norm(tvec)
    P10 = np.outer(tvec, tvec)
    comm_max = 0.0
    for n16 in JUDGE_K_SET_M2:
        k = np.array(n16, float) * (2 * np.pi / 16)
        Mgeo = np.kron(np.eye(10), R30M.leap_M(k))
        P20 = np.kron(P10, np.eye(2))
        comm_max = max(comm_max, float(np.max(np.abs(
            Mgeo @ P20 - P20 @ Mgeo))))
    evidence = {
        "1_geometry_step_trace_commutator_bitwise": comm_max,
        "2_one_way_no_state_readback": ("耦合一步符号严格上三角(CERT-C 下左块"
                                        " == 0)=> 演化期几何态(含其迹行)"
                                        "不被读取/回馈"),
        "3_source_side_trace_reversal_declared": (
            "源构造使用 eta-迹反转(trace-reversed T̄,R16 约定,de Donder "
            "相容源形式)-- 静态源侧映射,非演化期迹行处理;与 v1 走行装配层 "
            "T 行不同物(任务书 §3 G5 血统注:凡涉迹处理,oracle 新主语重推,"
            "不抄 v1 数字)")}
    trace_row_processing_present = bool(comm_max != 0.0)   # 如实检测填写
    certE_ok = bool(comm_max == 0.0)
    payload["CERT_E_trace_row_detection"] = {
        "rule": TRACE_ROW_RULE,
        "evidence": evidence,
        "trace_row_processing_present": trace_row_processing_present,
        "auto_adjudication": {
            "condition_for_guns_header": TRACE_ROW_AUTO_ADJUDICATION,
            "verdict_now": ("C5(v1) T 行三元组:记名退役(字段 false);"
                            "变体引入迹行处理即强制复活升主炮"
                            if not trace_row_processing_present else
                            "C5(v1) T 行三元组:升格为主炮(字段 true)")},
        "seconds": time.time() - tr, "pass": certE_ok}
    write_json(payload)
    print(f"[CERT-E trace_row] 检测值 = {trace_row_processing_present}  "
          f"(对易子={comm_max:.1e};自动裁定:"
          f"{'记名退役' if not trace_row_processing_present else '升主炮'})")

    # ---- CERT-F rho 标定(审定 R1;冻结 R26 机,按 L 等比协议) -------------
    tr = time.time()
    kw = R36M.recompute_kappa_window(C_CONE)
    kappa_work = kw["kappa_work"]
    c2 = C_CONE * C_CONE
    rho_per_L, floor_per_L = {}, {}
    for L in L_LIST:
        dT = int(round(L / C_CONE))                       # = 2L
        w_sp = max(3, int(round(10 * L / 44.0)))
        pad = max(2, int(round(12 * L / 44.0)))
        sigma = 6.0 * L / 44.0
        sp = tcf._sponge_field(L, w_sp, 0.30)
        x = np.arange(L)
        envg = np.exp(-(((x - L / 2.0) / sigma) ** 2))
        env = envg[:, None, None] * envg[None, :, None] * envg[None, None, :]

        def bulk(z):
            b = (slice(pad, -pad),) * 3
            return float(np.abs(z[b]).sum())

        rows_rho, rows_floor = {}, {}
        for n16 in RHO_KSET16:
            nL = [int(round(c * L / 16.0)) for c in n16]
            kvec = 2 * np.pi * np.array(nL, float) / L
            grids = np.meshgrid(*[np.arange(L)] * 3, indexing="ij")
            carrier = np.exp(1j * sum(kvec[i] * grids[i] for i in range(3)))
            z0 = (env * carrier).astype(complex)
            m0_ac = bulk(z0 - z0.mean())
            z, pz = z0.copy(), np.zeros_like(z0)
            rho_v, floor_v = None, None
            for t in range(1, 3 * dT + 1):
                z, pz = R36M.hyper_step(z, pz, kappa_work, c2, sp=sp)
                if t == dT:
                    rho_v = bulk(z - z.mean()) / m0_ac
                if t == 3 * dT:
                    floor_v = bulk(z - z.mean()) / m0_ac
            rows_rho[str(tuple(n16))] = rho_v
            rows_floor[str(tuple(n16))] = floor_v
        rho_per_L[str(L)] = rows_rho
        floor_per_L[str(L)] = rows_floor
    rho_pred_L = {L: max(v.values()) for L, v in rho_per_L.items()}
    rho_pred_max = max(rho_pred_L.values())
    sep_ok = bool(rho_pred_max <= RHO_MAX_ALLOWED)
    payload["CERT_F_rho_calibration"] = {
        "protocol": RHO_PROTOCOL,
        "kappa_window": kw,
        "rho_per_L_per_k": rho_per_L,
        "rho_pred_per_L": rho_pred_L,
        "rho_pred_max": rho_pred_max,
        "rho_window_rel": RHO_WINDOW_REL,
        "rho_max_allowed": RHO_MAX_ALLOWED,
        "separation_vs_1": (1.0 / rho_pred_max) if rho_pred_max > 0
        else float("inf"),
        "floor_3dT_per_L_per_k": floor_per_L,
        "b_layer_prediction": RHO_PROTOCOL["b_layer"],
        "derivation": (
            "推导:约束违反以共享锥速 c 双曲输运至 L4 sponge 吸收(R26 四证书"
            ";R36 part_C 复认证 tau_clear ∈ [39,62] @ NA=44 < DeltaT = "
            "2*NA/2 = NA/c,k-无关 1.59x);层长取 DeltaT_L = round(L/c) = 2L "
            "一个满穿越 => 单层保留分数 rho_L 远小于 1;本件按 L 等比协议"
            "直接标定逐 L 数值并冻结为预言;主跑 G6(a) 同协议实测,"
            "落 ±30% 方计 PASS(R1)"),
        "seconds": time.time() - tr, "pass": sep_ok}
    write_json(payload)
    print(f"[CERT-F rho 标定] {'PASS' if sep_ok else 'FAIL-HALT'}  "
          f"rho_pred/L = " + str({L: f"{v:.3e}" for L, v in rho_pred_L.items()})
          + f"  max={rho_pred_max:.3e} <= {RHO_MAX_ALLOWED}  "
          f"({time.time()-tr:.1f}s)")

    # ---- eps 分扇区记账(预飞级小格验证;主跑实测) -------------------------
    eps_account = {
        "convention": ("D1 口径 + M0' j_inv 不变量整改口径;报告一律 "
                       "(eps_geo, eps_mat) 二元组,禁单一混合 eps(红线 11)"),
        "eps_geo": {
            "declared": 0.0,
            "mode": "定义属性(hand_built=all,几何扇区全部传播-曲率 DOF 手搭)",
            "main_run_measurement": ("主跑轮 2:j_inv = N_curv 整数逐位实测"
                                     "(宿主+沙盒),不引 R30 锚点定义值代填"
                                     "(红线 5)")},
        "eps_mat": {
            "target": 1.0,
            "preflight_small_grid": {
                "matter_n_prop_measured": n_mat_prop,
                "hand_built_matter_dof_inventory": [],
                "coupling_column_into_matter_block": 0.0,
                "j_inv_mat_preflight": 0,
                "eps_mat_preflight": 1.0,
                "note": ("预飞级:物质传播支恰 2(判据 k 逐点 |lam|=1 整数"
                         "计数)+ 手搭清单空 + 上三角结构不向物质块注入 => "
                         "j_inv_mat = 0;非主跑实测")},
            "main_run_measurement": ("主跑轮 2:数据 SVD 主谱线振幅空间对物质"
                                     "扇区的 j_inv 全 L 全判据 k 实测(整数、"
                                     "双环境逐位);测不到 1 = 重大结果如实报")},
    }
    payload["epsilon_sector_accounting"] = eps_account
    write_json(payload)

    # ---- margin_declarations 全表 + 骑线禁令扫描 ---------------------------
    margins = build_margin_table(rho_pred_max, cherenkov)
    m_ok, m_worst = margin_table_ok(margins)
    payload["margin_declarations"] = {
        "rules": {"single_sided_min_factor": MARGIN_MIN,
                  "band_spread_operationalized": ("预期散布 <= 半带宽 x "
                                                  f"{BAND_SPREAD_FACTOR}"
                                                  "('<<' 的写死口径)"),
                  "zero_margin_action": ("HALT 重设计(M1' P0(a) 先例;"
                                         "北极星 §四补条边界骑线禁令)")},
        "table": margins,
        "scan": {"pass": m_ok, **m_worst},
        "note": ("本表 = 交付物 3/4 脚本头 margin_declarations 的构造冻结版;"
                 "v2m2_coupled_loop.py 与 v2m2_guns.py 脚本头须原样携带"
                 "(guns 增列逐炮行)")}
    write_json(payload)
    print(f"[margin 全表] {'PASS' if m_ok else 'FAIL-HALT'}  行数={len(margins)}  "
          f"单边最小裕度={m_worst['single_min_factor']:.1f}x  "
          f"带型最大散布/半带宽={m_worst['band_max_ratio']:.2e}")

    # ---- D-M2-1 择定记录(审定 R4 已裁;本件核验前提) ----------------------
    certs_ok = bool(certA_ok and certB_ok and certC_ok and certD_ok
                    and certE_ok and sep_ok and m_ok)
    decision = "R4-CONFIRMED" if certs_ok else "HALTED-AT-DECISION-POINT"
    payload["D_M2_1"] = {
        "decision": decision,
        "decision_record": (
            "D-M2-1 已由车道A 审定 R4 裁定:基线物质载体 = v1 冻结走行物质半;"
            "单向 + 测试场基线批准;双向反作用仅记名探测(预算 <=10%、哨兵必备"
            "、不稳即停、只入册不进判定)。本件核验其前提成立:预飞 PASS + "
            "CERT-A..F 全过 + margin 全表无零裕度,故落 R4-CONFIRMED。"
            if certs_ok else
            "符号层证书或裕度表未全过:停在择定位,病灶见各 CERT 块;如实报"
            "车道A,不自行改构造(红线 4)。")}
    write_json(payload)
    print(f"[D-M2-1] 择定: {decision}")

    # ---- 构造冻结 ----------------------------------------------------------
    cand = CandidateV2(
        sector="spin2", cand_id="v2m2_spin2_r30geo_walkmatter_sourcelink",
        geometry={"family": "R30",
                  "params": {"dt": DT, "theta_g": THETA_SHARED,
                             "role": ("几何扇区 = R30 手搭复形(eps_geo=0 "
                                      "定义属性);placed kappa 微积分 + "
                                      "leapfrog,ker K 按构造保持")}},
        coupling={"variant": "one_way_source_testfield",
                  "eta_baseline": ETA_BASELINE,
                  "v_lattice_max": V_MAX_LATTICE,
                  "v_lattice_set": list(V_LATTICE_SET),
                  "matter": {"carrier": "v1 冻结走行物质半(审定 R4)",
                             "symbol": "cp1_v4_L2.walk_symbol(theta_m=pi/3)",
                             "realspace": "r25_realspace_step step/step_minus",
                             "theta_m": THETA_SHARED},
                  "source_chain": ["R10 精确键流(de Donder 相容按放置)",
                                   "R25 source-lift 静态件 -> Newton 井",
                                   "R25-E2 运动源镜像 sector(保 h̄0i;"
                                   "reality 生成镜像,非 Re(h̄+))"],
                  "clearance": "R26 双曲输运 + L4 sponge(C5 炮的靶机制)",
                  "readout": ("测试场/零测地 Eddington 于 h 背景"
                              "(置零 h_ij 反事实,同一次运行内)"),
                  "two_way": "仅记名探测项,不进判定(审定 R4)"},
        hand_built={"dof_indices": "all",
                    "scope_note": "hand_built 仅指几何扇区;物质扇区手搭清单空"},
        lattice={"L": L_LIST, "judge_k_set": JUDGE_K_SET_M2,
                 "ray_directions": RAY_DIRECTIONS},
        backend="numpy",
        frozen_refs={k: v["sha256"] for k, v in checked.items()})
    construction_spec = {
        "cand": json.loads(cand.to_json()),
        "three_piece_assembly": {
            "geometry": "R30 复形(r30_tensor_complex_dynamical,只读)",
            "matter": "v1 冻结走行物质半(cp1_v4_L2 / r25_realspace_step)",
            "coupling": "源链(R10 + R25 static + R25-E2 镜像 sector),弱场单向"},
        "shared_theta": {"theta_g": THETA_SHARED, "theta_m": THETA_SHARED,
                         "dt_equals_c": DT},
        "judge_k_rescale_rule": "n_L = round(n16 * L / 16),实采 k 入册",
        "rho_prediction": {"per_L": rho_pred_L, "max": rho_pred_max,
                           "window_rel": RHO_WINDOW_REL,
                           "protocol": RHO_PROTOCOL},
        "p_preregistration": {"G2": P_PRED_G2, "G3": P_PRED_G3,
                              "derivation": P_PRED_DERIVATION},
        "no_cherenkov": cherenkov,
        "trace_row_processing_present": trace_row_processing_present,
        "trace_row_rule": TRACE_ROW_RULE,
        "trace_row_auto_adjudication": TRACE_ROW_AUTO_ADJUDICATION,
        "margin_declarations": margins,
        "g6_probe_protocol": RHO_PROTOCOL,
        "seeds": {"unitary": SEED_UNITARY, "static": SEED_STATIC},
        "epsilon_accounting": eps_account,
    }
    payload["candidate_v2"] = json.loads(cand.to_json())
    payload["construction_freeze"] = {
        "construction_spec": construction_spec,
        "construction_sha256": sha256_canonical(construction_spec),
        "frozen_before_main_run": True,
        "prediction_timepoint": ("构造冻结 = M2' 预言时点(审定 R6):rho 预言 "
                                 "+ p 预注册 + margin 全表 + trace_row 字段"
                                 "四要素本件同批交付"),
        "note": ("主跑(轮 2)唯一合法输入 = 本 construction_spec + 本脚本 "
                 "source_sha256;构造冻结前禁开主跑已遵守(本轮零主跑零炮组)。")}
    payload["sandbox"] = {"status": "PENDING",
                          "note": ("双环境语义:符号层证书判据字段沙盒双跑由"
                                   "车道A 复核执行;本 JSON 为宿主参考值")}
    all_ok = certs_ok
    payload["status"] = "DONE" if all_ok else "HALTED-AT-DECISION-POINT"
    payload["verdict"] = (
        "候选构造冻结完成(宿主):三件套装配 CERT-A..F 全过;四要素同批落位 "
        "-- rho 预言(逐 L 冻结,max 对 1 分离达标)、G2/G3 收敛阶 p=2 预注册、"
        "margin_declarations 全表(无零裕度)、trace_row_processing_present "
        "如实检测(自动裁定已出);D-M2-1 落 R4-CONFIRMED;构造 sha256 冻结。"
        "本件无任何涌现主张;eps_geo=0 如实记账;eps 实测在主跑;主跑(轮 2)"
        "自此解锁(预飞 PASS + 构造冻结双前提齐)。" if all_ok else
        "符号层病灶或裕度不达标:停在择定位,报车道A;禁开主跑。")

    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)
    print("=" * 74)
    print(f"CANDIDATE: {'DONE' if all_ok else 'HALT'}  construction_sha256="
          f"{payload['construction_freeze']['construction_sha256']}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
