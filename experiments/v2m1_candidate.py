"""v2m1_candidate -- M1' 候选构造件:D-M1-1 择定记录 + 符号层证书 + 构造冻结
(任务书 §1 交付物 2、§2;lane B 轮 1,2026-07-26)。

AUTHORITY(判据预注册,运行后不得回改;红线 4):
  docsv2/v2-任务书-M1-Maxwell闭环.md §2(候选基线与 D-M1-1)§8(红线十条)
  docs/reports/定理笔记-R17-半格放置算子字典.md(口味选择一行规则)
  docs/reports/定理笔记-R19-staggered-h放置.md(放置=存储语义;时间配对约定)
  docs/reports/小报告-R23-麦克斯韦正控.md(P6:字典特化逐字退化为 Yee 1966)

A 案构造(涌现语义;hand_built=None):
  输入 = 冻结放置字典,不含任何 Maxwell 方程输入:
    (D1) A_mu 放置 x+e_mu/2(R23 P6)=> 场强放置派生:E_i 承 A_i 边点
         (x+e_i/2, 整数 t);B_i=(curl A)_i 落面点 (x+(e_j+e_k)/2, 半 t);
    (D2) R17 口味一行规则:被差分分量在差分方向上偏移为半格 -> 后向差,
         否则 -> 前向差;
    (D3) R19 时间配对约定:leapfrog 切片语义(E 整数 t / B 半 t),dt=0.5
         (承件10 CFL 标定点)。
  组装 = 由 (D1)(D2) 程序化选出每条差分口味并检查"全部项落同一目标点"
  (R17 证书 B 的移植);一阶 (E,B) 旋度-旋度骨架 = 自旋 2 复形的自旋 1 特化
  (R23 对应表),作为特化输入如实声明——hand_built=None 指零 DOF 手搭进
  精确 ker C(D1 口径),不指"没写下任何结构"。

符号层证书(门写死;任一不过 => 停在择定位,记录病灶,不得自行切 B 案):
  CERT0 字典组装结构:每条口味由规则选出;各旋度分量全部项落同一目标点,
        目标点 == 被更新场的声明放置;口味表 == Yee 1966(E-旋度全前向 /
        B-旋度全后向)——逐字核对;
  CERT1 R23 P6 对拍:evaluate_v2_candidate(候选) -> r23 全套证书,
        row2_r23 比对器 PASS 且 max_abs_diff <= 1e-12(组装符号 ≡ i·kappa);
  CERT2 逐字退化为 Yee:字典组装 step 对随机 fp64 态(seed 写死 20260726)
        与冻结 photon_control.step_yee 逐位一致(max abs diff == 0.0,位级);
        七判据 k 一步模式矩阵逐位一致(0.0);
  CERT3 谱层酉性事实(酉性地位声明的实测支撑):
        (a) 七判据 k 实空间模式矩阵 6 本征值 max||lam|-1| <= 1e-12;
        (b) 200 随机 k(seed 写死 2026,|k|>1e-2)符号层一步矩阵同门;
        (c) 七判据 k 符号层谱 vs 实空间模式矩阵谱逐一匹配 <= 1e-12;
        cond(本征向量阵) 报告级入册(可对角化诊断,不设线)。

D-M1-1 择定(记录写入 JSON):PI 已按授权认可默认 A 案;本脚本核验前提 =
  预飞 PASS(读 v2m1_preflight.json)+ CERT0-3 全过,方落 "A-CONFIRMED";
  否则落 "HALTED-AT-DECISION-POINT" 并如实记录病灶。

冻结件 hash(先行写死;逐位不符 = HALT,红线 2):
  experiments/photon_control.py
    38ea5bbf5282209f720c754e1f5b17a802a5e7aae19197a3b030b440402e4263
  data/results/photon_control_results.json
    76d8d120a07e8bc46810fbd78e4d859b34ee2779c4bf5d7cda6bc240c7e6c7f3
  experiments/r23_maxwell_control.py
    807b1f7fd00fc3ed141ab1ac6bc950e1325be61b33a8bf0cb78d98da76292b10
  experiments/r17_placement_operators.py
    957bfa91284815c5223f7b41b7cb6cbd22dbaab4d7343ffe781e938a037340cf
  experiments/r19_staggered_placement.py
    6e67896103d2a7ca483d3721b946c21799f7cbfad07e39910b62fb3a9fa902b3
  data/results/r23_results.json
    4c2ccf59e6cae55e35fd0e2bd55e4a8bb83c050c9859e981181ef8bc8eef969f
  (+ M0' 冻结七件,值同 v2m1_preflight.py 头;r15 经 frozen.py 注册表校验)

措辞红线(§8 红线 10 / 红线 5):本件无任何涌现主张;构造冻结 != 闭环;
G8 的 eps_DOF=1.0 在本件中是 D1 定义锚(hand_built=None),不是实测——
eps_DOF=1 要主跑(轮 2)j_inv 不变量机器实测。构造冻结前禁开主跑:本轮零主跑。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m1_candidate.py
      (writes data/results/v2m1_candidate.json, 增量写盘)
"""
from __future__ import annotations

import hashlib
import json
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

from rulespace_v2 import controls as C                     # noqa: E402
from rulespace_v2 import gates as G                        # noqa: E402
from rulespace_v2 import frozen as FZ                      # noqa: E402
from rulespace_v2 import invariants as INV                 # noqa: E402
from rulespace_v2.candidate import CandidateV2             # noqa: E402

OUT = os.path.join(ROOT, "data", "results", "v2m1_candidate.json")
PREFLIGHT_JSON = os.path.join(ROOT, "data", "results", "v2m1_preflight.json")

# ---- 判据(写死;运行后不得回改) -----------------------------------------
TOL_JUDGE = 1e-12          # CERT1 / CERT3(a)(b)(c)
TOL_BITWISE = 0.0          # CERT2(逐位)
SEED_STATE = 20260726      # CERT2 随机态种子
SEED_RANDK = 2026          # CERT3(b) 随机 k 种子
N_RANDK = 200
DT = 0.5                   # (D3) 承件10 CFL 标定点

M1_FROZEN_SHA256 = {
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
}
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

JUDGE_K_SET = [[2, 0, 0], [0, 2, 0], [0, 0, 2], [2, 2, 0], [3, 1, 0],
               [2, 2, 2], [8, 0, 0]]      # 件10 七 k 集(任务书 §3)


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
                   separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ===========================================================================
#  A 案构造:从冻结字典程序化组装自旋 1 rule(不手写 Maxwell 差分口味)
# ===========================================================================
# (D1) 放置派生(A_mu at x+e_mu/2 -> 场强放置;半格单位 = 0.5)
OFF_A_SP = np.eye(3) * 0.5                 # A_i 空间偏移 e_i/2
OFF_E_DICT = OFF_A_SP.copy()               # E_i = F_{0i} 承 A_i 边点
OFF_B_DICT = np.array([OFF_A_SP[j] + OFF_A_SP[k]
                       for j, k in ((1, 2), (2, 0), (0, 1))])  # B_i = (curl A)_i


def flavor_from_dict(off_comp, ax):
    """(D2) R17 口味一行规则:被差分分量在方向 ax 上偏移为半格 -> 后向差
    (bwd, -1/2);整数 -> 前向差(fwd, +1/2)。返回 ("bwd"|"fwd", 读出点移位)。"""
    if abs(off_comp[ax] - 0.5) < 1e-12:
        return "bwd", -0.5
    return "fwd", +0.5


def assemble_curl_table(offs, name):
    """按字典规则组装 (curl F)_i 的口味表 + 目标点着陆检查(R17 证书 B 移植)。
    (curl F)_i = d_j F_k - d_k F_j,j=(i+1)%3, k=(i+2)%3。"""
    table, targets_ok = [], True
    for i in range(3):
        j, k = (i + 1) % 3, (i + 2) % 3
        fl1, mv1 = flavor_from_dict(offs[k], j)   # d_j F_k
        fl2, mv2 = flavor_from_dict(offs[j], k)   # d_k F_j
        t1 = offs[k].copy(); t1[j] += mv1
        t2 = offs[j].copy(); t2[k] += mv2
        same = bool(np.allclose(t1, t2, atol=1e-12))
        targets_ok = targets_ok and same
        table.append({"component": i,
                      "term1": {"d_axis": j, "of": f"{name}[{k}]",
                                "flavor": fl1, "lands_at": t1.tolist()},
                      "term2": {"d_axis": k, "of": f"{name}[{j}]",
                                "flavor": fl2, "lands_at": t2.tolist()},
                      "terms_land_same_target": same})
    return table, targets_ok


def make_dict_step(PC):
    """由口味表生成实空间 step(与 photon_control 同一差分原语,同一项序,
    使 CERT2 的位级对拍有意义;口味本身由字典规则选出,非手写)。"""
    D = {"fwd": PC._dp, "bwd": PC._dm}

    def dict_curl(F, offs):
        ax = (-3, -2, -1)
        rows = []
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            dj = D[flavor_from_dict(offs[k], j)[0]]
            dk = D[flavor_from_dict(offs[j], k)[0]]
            rows.append(dj(F[k], ax[j]) - dk(F[j], ax[k]))
        return np.stack(rows)

    def dict_step(state):
        E, B = state
        B = B - DT * dict_curl(E, OFF_E_DICT)   # B 半 t 切片(D3 配对)
        E = E + DT * dict_curl(B, OFF_B_DICT)   # E 整数 t 切片
        return (E, B)
    return dict_step


def symbol_step_matrix(kl):
    """(CERT3b/3c) 同一字典在符号层的一步 6x6 矩阵(存储帧)。
    fwd 符号 e^{ik_j}-1,bwd 符号 1-e^{-ik_j};leapfrog 消元:
      B' = B - DT*Cf E;E' = E + DT*Cb B'。"""
    def dsym(flavor, kj):
        return (np.exp(1j * kj) - 1.0) if flavor == "fwd" \
            else (1.0 - np.exp(-1j * kj))

    def curl_sym(offs):
        M = np.zeros((3, 3), complex)
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            M[i, k] += dsym(flavor_from_dict(offs[k], j)[0], kl[j])
            M[i, j] -= dsym(flavor_from_dict(offs[j], k)[0], kl[k])
        return M
    Cf = curl_sym(OFF_E_DICT)                  # 作用于 E,更新 B
    Cb = curl_sym(OFF_B_DICT)                  # 作用于 B,更新 E
    S = np.zeros((6, 6), complex)
    S[3:, :3] = -DT * Cf
    S[3:, 3:] = np.eye(3)
    S[:3, :3] = np.eye(3) - DT * DT * (Cb @ Cf)
    S[:3, 3:] = DT * Cb
    return S


def spectra_match(lamA, lamB):
    """两组本征值逐一最近邻匹配的最大距离。"""
    lamB = list(lamB)
    worst = 0.0
    for a in lamA:
        d = [abs(a - b) for b in lamB]
        i = int(np.argmin(d))
        worst = max(worst, d[i])
        lamB.pop(i)
    return worst


# ===========================================================================
#  酉性地位声明(强制项;任务书 §2 择定材料必含。原文写死,运行后不回改)
# ===========================================================================
UNITARITY_STATEMENT = (
    "自旋 1 候选在 (E,B) 场表象下走辛演化(Yee leapfrog 辛格式),不是对存储场 "
    "L2 范数的严格酉演化;与 v2 纲领'局域酉 QCA'基底公理的关系,如实分三层:"
    "(1) 谱层事实(本件 CERT3 实测):一步模式矩阵 M(k) 在 CFL 内(dt=0.5,"
    "dt*sqrt(3)<1)对全部判据 k 与 200 随机 k,6 个本征值全部落单位圆"
    "(max||lambda|-1| 见 CERT3 读数,机器精度),守恒二次型为 Yee 能量 "
    "H=|E|^2+B(-)·B(+) 而非 |E|^2+|B|^2——即 M(k) 逐 k 酉等价于酉矩阵"
    "(k 依赖相似变换;可对角化诊断 cond(V) 报告级入册)。"
    "(2) 未证部分(诚实边界):该 k 依赖相似变换非局域;本轮未构造、也不主张"
    "任何严格局域酉 QCA 膨胀实现该步进。'酉等价正规形式'仅在逐 k 符号层成立,"
    "地位 = 符号层假设(任务书 §2 允许的如实标注分支,非证书)。"
    "(3) 关系裁定:候选以'辛格式 + 逐 k 单位圆谱'身份进入 M1' 门列;M1' 各门"
    "(N_prop/sigma/共锥/源/守恒/sponge/稳定/epsilon)均为该表象下可观测判据,"
    "不以基底酉性公理为前提;若纲领后续要求基底严格酉,升级路径 = B 案谱系的"
    "局域酉化(Dirac-QCA 型)或显式酉膨胀,属新裁定,不在 M1' 范围。附注:"
    "R23 符号层阻尼 (I-gamma*K^dag*K) 为收缩映射,是 in-vitro 判据仪器而非"
    "候选本体,不进入本声明的候选演化。")


# ===========================================================================
#  D-M1-1 两案对照材料(择定记录;材料为文档性内容,写死入 JSON)
# ===========================================================================
DM11_MATERIAL = {
    "A": {
        "name": "R23 放置字典组装路线(默认首选)",
        "construction": ("R17/R19 放置字典特化到 A_mu(偏移 e_mu/2、口味一行"
                         "规则、时间配对约定)程序化组装实空间 step;"
                         "P6 证书:特化逐字退化为 Yee 1966"),
        "certificate_chain": [
            "R15 零性/横向机器(kappa 同壳)",
            "R17 字典 4/4(算子级 kappa 组装 4.9e-16)",
            "R19 staggered 放置硬门(实空间 K_placed 7.8e-15)",
            "R23 P1-P6 6/6(P6 组装符号≡i·kappa 2.8e-16)",
            "M0' 控制矩阵行 2 双环境(diff 1.8e-15,谱系已注)",
            "件10 对答案仪器 PASS(七 k 正控 + 双病变体击穿)",
            "本件 CERT0-3(结构/符号/逐位退化/谱层酉性)"],
        "emergence_semantics": ("中强:'自旋 2 机器的自旋 1 特化自行落在教科书"
                                "答案上'——字典不含 Maxwell 差分口味输入,输出"
                                "= Yee 1966;但一阶 (E,B) 旋度-旋度骨架是自旋 2 "
                                "复形的特化输入,如实声明"),
        "risks": [
            "酉性地位 = 辛非严格酉(见酉性地位声明;已如实标注)",
            "候选与件10 判据仪器同属 Yee 家族 => 主跑对拍谱系相关性高,"
            "判据的牙必须由轮 3 炮组(C1-C4)独立保证",
            "涌现语义强度弱于'从宽规则空间被 QA 剪出'(L4 语境;M1' 本就"
            "不授权 L4,任务书 §0)"],
    },
    "B": {
        "name": "QCA Maxwell 独立构造(exp1 Dirac-QCA 谱系;备选)",
        "construction": ("局域酉 Maxwell QCA(Dirac-QCA 规范场类比或格点幺正"
                         "元胞自动机),严格满足局域酉基底公理"),
        "certificate_chain": [
            "exp1 Dirac-QCA 谱系存在(色散/局域性先例)",
            "无 P1-P6 级符号层证书;无 M0' 控制行;无放置字典血统;"
            "全部证书链需从零建"],
        "emergence_semantics": ("酉性语义强(基底公理直接满足);但与已冻结"
                                "判据仪器无谱系连接,'同一台机器'论证断裂"),
        "risks": [
            "证书链完备度最低;判据管线(七 k/oracle/门列)需重新适配与校准",
            "周期不可控,且启用 = 新裁定(任务书 §2:仅当 A 案暴露病灶)"],
    },
    "decision_rule": ("任务书 §2:A 案默认首选,PI 已按授权认可;前提 = A 案"
                      "预飞与符号证书层无病灶。lane B 发现病灶时停在择定位"
                      "如实报告,不得自行切 B 案。"),
}


def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m1-candidate (M1' 候选构造件;任务书 §2;lane B 轮 1)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-任务书-M1-Maxwell闭环.md §2/§8",
                      "docs/reports/定理笔记-R17-半格放置算子字典.md",
                      "docs/reports/定理笔记-R19-staggered-h放置.md",
                      "docs/reports/小报告-R23-麦克斯韦正控.md"],
        "environment": env,
        "tol": {"judge": TOL_JUDGE, "bitwise": TOL_BITWISE,
                "seed_state": SEED_STATE, "seed_randk": SEED_RANDK},
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "wording_redline": ("本件无任何涌现主张;构造冻结 != 闭环;G8 的 "
                            "eps_DOF=1.0 是 D1 定义锚(hand_built=None),"
                            "非实测——实测在主跑轮 2(红线 5/10)"),
    }
    write_json(payload)

    print("v2m1 candidate: A 案字典组装 + D-M1-1 择定 + 构造冻结")
    print("=" * 74)
    print(f"[env] numpy {env['numpy_version']}  blas={env['blas']}  "
          f"{env['platform']}")

    # ---- 0. hash 校验 + 预飞前提 ------------------------------------------
    checked, hok = {}, True
    for rel, exp in {**M1_FROZEN_SHA256, **M0_SEVEN_SHA256}.items():
        got = sha256_file(os.path.join(ROOT, rel))
        m = (got == exp)
        hok = hok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    hz0 = FZ.verify_frozen()
    payload["hash_verification"] = {"m1_pinned": {"pass": hok,
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
        "file": "data/results/v2m1_preflight.json",
        "sha256_at_read": sha256_file(PREFLIGHT_JSON),
        "preflight_pass": pf_ok}
    write_json(payload)
    print(f"[前提] 预飞 PASS: {pf_ok}")
    if not pf_ok:
        payload["status"] = "HALTED-AT-DECISION-POINT"
        payload["verdict"] = "预飞未 PASS:停在择定位(任务书 §2),报车道A。"
        write_json(payload)
        return 1

    PC = FZ.mod("photon_control")               # 冻结判据核只读 import

    # ---- CERT0 字典组装结构 ------------------------------------------------
    tabE, okE = assemble_curl_table(OFF_E_DICT, "E")   # 用于 B 更新
    tabB, okB = assemble_curl_table(OFF_B_DICT, "B")   # 用于 E 更新
    placement_ok = bool(np.allclose(OFF_E_DICT, PC.OFF_E)
                        and np.allclose(OFF_B_DICT, PC.OFF_B))
    # 口味表逐字 == Yee 1966:E-旋度全前向 / B-旋度全后向
    flavE = {t["term1"]["flavor"] for t in tabE} | \
        {t["term2"]["flavor"] for t in tabE}
    flavB = {t["term1"]["flavor"] for t in tabB} | \
        {t["term2"]["flavor"] for t in tabB}
    yee_verbatim = bool(flavE == {"fwd"} and flavB == {"bwd"})
    # 目标点 == 被更新场的声明放置(mod 1;fwd 的 +1/2 与 bwd 的 -1/2 在
    # 整数格上同点差整移,按 R19 存储语义取 mod 1 比对)
    def _land_ok(tab, offs_target):
        ok = True
        for t in tab:
            land = np.array(t["term1"]["lands_at"]) % 1.0
            ok = ok and bool(np.allclose(
                land, offs_target[t["component"]] % 1.0, atol=1e-12))
        return ok
    land_ok = bool(_land_ok(tabE, OFF_B_DICT) and _land_ok(tabB, OFF_E_DICT))
    cert0_ok = bool(okE and okB and placement_ok and yee_verbatim and land_ok)
    payload["CERT0_dictionary_assembly"] = {
        "curl_of_E_table_for_B_update": tabE,
        "curl_of_B_table_for_E_update": tabB,
        "terms_land_same_target_all": bool(okE and okB),
        "derived_placements_match_yee1966": placement_ok,
        "flavor_table_verbatim_yee": yee_verbatim,
        "targets_equal_updated_field_placement_mod1": land_ok,
        "pass": cert0_ok}
    write_json(payload)
    print(f"[CERT0 字典组装结构] {'PASS' if cert0_ok else 'FAIL'}  "
          f"(同目标点={okE and okB}, 放置派生=Yee {placement_ok}, "
          f"口味逐字=Yee {yee_verbatim})")

    # ---- CERT1 R23 P6 对拍(evaluate_v2_candidate 统一评估器) -------------
    tr = time.time()
    cand = CandidateV2(
        sector="spin1", cand_id="v2m1_spin1_yee_dict_A",
        geometry={"family": "yee_maxwell",
                  "params": {
                      "construction": "A案:R17/R19 放置字典特化到 A_mu",
                      "representation": "(E,B) 场强表象(Yee 1966,字典派生)",
                      "dt": DT,
                      "placement_E": OFF_E_DICT.tolist(),
                      "placement_B": OFF_B_DICT.tolist(),
                      "flavor_rule": "R17 一行规则:半格->bwd,整数->fwd",
                      "time_pairing": "R19 leapfrog 切片语义(E 整数 t/B 半 t)",
                      "stepper": "experiments/v2m1_candidate.py:make_dict_step",
                  }},
        coupling=None,
        hand_built=None,                     # 零 DOF 手搭(D1 口径)
        lattice={"L": [16, 24, 32, 48],
                 "judge_k_set": JUDGE_K_SET,
                 "ray_directions": [[1, 0, 0], [1, 1, 0], [1, 1, 1]]},
        backend="numpy",
        frozen_refs={**{k: v["sha256"] for k, v in checked.items()},
                     "experiments/r15_walk_dedonder.py":
                         hz0["checked"]["experiments/r15_walk_dedonder.py"]
                         ["sha256"]})
    gc = G.evaluate_v2_candidate(cand)
    row = C.row2_r23(gc)
    cert1_ok = bool(row["pass"] and row["max_abs_diff"] <= TOL_JUDGE
                    and gc.certificates["r23_full"]["operator_err"]
                    <= TOL_JUDGE)
    payload["CERT1_r23_p6_symbol"] = {
        "row2_r23_comparator": row,
        "operator_err_P6": gc.certificates["r23_full"]["operator_err"],
        "seconds": time.time() - tr, "pass": cert1_ok,
        "note_epsilon": ("gate_readings 中 G8 eps_DOF=1.0 为 D1 定义锚"
                         "(hand_built=None),非实测(红线 5)")}
    payload["gate_readings_symbol_layer"] = gc.as_dict()
    write_json(payload)
    print(f"[CERT1 R23 P6 对拍] {'PASS' if cert1_ok else 'FAIL'}  "
          f"row2 diff={row['max_abs_diff']:.2e}  "
          f"P6 err={gc.certificates['r23_full']['operator_err']:.2e}")

    # ---- CERT2 逐字退化为 Yee(位级) --------------------------------------
    tr = time.time()
    dict_step = make_dict_step(PC)
    rng = np.random.default_rng(SEED_STATE)
    worst_state = 0.0
    for _ in range(4):
        E0 = rng.standard_normal((3, 2, PC.N, PC.N, PC.N))
        B0 = rng.standard_normal((3, 2, PC.N, PC.N, PC.N))
        sA, sB = (E0.copy(), B0.copy()), (E0.copy(), B0.copy())
        for _t in range(8):
            sA = dict_step(sA)
            sB = PC.step_yee(sB)
        worst_state = max(worst_state,
                          float(np.abs(sA[0] - sB[0]).max()),
                          float(np.abs(sA[1] - sB[1]).max()))
    worst_mode = 0.0
    for nv in JUDGE_K_SET:
        kl = PC.kvec_of(tuple(nv))
        Md = PC.mode_matrix(kl, dict_step, PC.OFF6)
        My = PC.mode_matrix(kl, PC.step_yee, PC.OFF6)
        worst_mode = max(worst_mode, float(np.abs(Md - My).max()))
    cert2_ok = bool(worst_state <= TOL_BITWISE and worst_mode <= TOL_BITWISE)
    payload["CERT2_verbatim_yee_degeneration"] = {
        "state_bitwise_max_diff": worst_state,
        "mode_matrix_bitwise_max_diff_sevenk": worst_mode,
        "protocol": ("4 随机 fp64 态 x 8 步逐位;七判据 k 一步模式矩阵逐位;"
                     "对照 = 冻结 photon_control.step_yee(hash 已校验)"),
        "seconds": time.time() - tr, "pass": cert2_ok}
    write_json(payload)
    print(f"[CERT2 逐字退化 Yee] {'PASS' if cert2_ok else 'FAIL'}  "
          f"态位级 diff={worst_state:.1e}  模式矩阵 diff={worst_mode:.1e}")

    # ---- CERT3 谱层酉性事实 ------------------------------------------------
    tr = time.time()
    unimod_lattice, spectra_dev, cond_max = 0.0, 0.0, 0.0
    for nv in JUDGE_K_SET:
        kl = PC.kvec_of(tuple(nv))
        Md = PC.mode_matrix(kl, dict_step, PC.OFF6)
        lamM, VM = np.linalg.eig(Md)
        unimod_lattice = max(unimod_lattice,
                             float(np.abs(np.abs(lamM) - 1.0).max()))
        cond_max = max(cond_max, float(np.linalg.cond(VM)))
        S = symbol_step_matrix(kl)
        lamS = np.linalg.eigvals(S)
        spectra_dev = max(spectra_dev, spectra_match(lamM, lamS))
    rng = np.random.default_rng(SEED_RANDK)
    unimod_rand = 0.0
    n_used = 0
    while n_used < N_RANDK:
        kl = rng.uniform(-np.pi, np.pi, 3)
        if np.linalg.norm(kl) < 1e-2:
            continue
        S = symbol_step_matrix(kl)
        lam, V = np.linalg.eig(S)
        unimod_rand = max(unimod_rand, float(np.abs(np.abs(lam) - 1.0).max()))
        cond_max = max(cond_max, float(np.linalg.cond(V)))
        n_used += 1
    cert3_ok = bool(unimod_lattice <= TOL_JUDGE and unimod_rand <= TOL_JUDGE
                    and spectra_dev <= TOL_JUDGE)
    payload["CERT3_spectral_unitarity_facts"] = {
        "a_unimodularity_sevenk_realspace": unimod_lattice,
        "b_unimodularity_200randk_symbol": unimod_rand,
        "c_spectra_symbol_vs_realspace_sevenk": spectra_dev,
        "cond_eigvec_max_report_only": cond_max,
        "n_rand_k": n_used, "seconds": time.time() - tr, "pass": cert3_ok}
    write_json(payload)
    print(f"[CERT3 谱层酉性] {'PASS' if cert3_ok else 'FAIL'}  "
          f"||lam|-1| 七k={unimod_lattice:.1e} 随机k={unimod_rand:.1e}  "
          f"谱对拍={spectra_dev:.1e}  cond(V)max={cond_max:.2f}(报告级)")

    # ---- D-M1-1 择定记录 + 酉性地位声明 -----------------------------------
    certs_ok = bool(cert0_ok and cert1_ok and cert2_ok and cert3_ok)
    decision = ("A-CONFIRMED" if certs_ok else "HALTED-AT-DECISION-POINT")
    payload["D_M1_1"] = {
        "material_two_cases": DM11_MATERIAL,
        "preflight_pass": pf_ok,
        "symbol_layer_certs_pass": certs_ok,
        "decision": decision,
        "decision_record": (
            "择定 = A 案(R23 放置字典组装路线)。PI 已按授权认可默认 A 案;"
            "lane B 核验其前提成立:预飞 PASS(宿主)+ CERT0-3 全过,"
            "无符号层病灶,故落 A-CONFIRMED。" if certs_ok else
            "A 案符号层证书未全过:停在择定位,病灶见各 CERT 块;"
            "不自行切 B 案(任务书 §2:启用 B 案 = 新裁定)。"),
        "unitarity_status_statement": UNITARITY_STATEMENT,
        "unitarity_measured_support": {
            "unimodularity_max": max(unimod_lattice, unimod_rand),
            "cond_eigvec_max": cond_max},
    }
    write_json(payload)
    print(f"[D-M1-1] 择定: {decision}")

    # ---- 构造冻结 ----------------------------------------------------------
    construction_spec = {
        "cand": json.loads(cand.to_json()),
        "dictionary_inputs": {
            "D1_placement": {"A_mu": "x+e_mu/2 (R23 P6)",
                             "E_derived": OFF_E_DICT.tolist(),
                             "B_derived": OFF_B_DICT.tolist()},
            "D2_flavor_rule": "半格->后向差, 整数->前向差 (R17 一行规则)",
            "D3_time_pairing": f"leapfrog 切片语义, dt={DT} (R19/件10 CFL 点)"},
        "flavor_tables": {"curl_E": tabE, "curl_B": tabB},
        "judge_k_set": JUDGE_K_SET,
    }
    payload["candidate_v2"] = json.loads(cand.to_json())
    payload["construction_freeze"] = {
        "construction_spec": construction_spec,
        "construction_sha256": sha256_canonical(construction_spec),
        "frozen_before_main_run": True,
        "note": ("主跑(轮 2)唯一合法输入 = 本 construction_spec + 本脚本 "
                 "source_sha256;冻结前禁开主跑已遵守(本轮零主跑)。")}
    payload["sandbox"] = {"status": "PENDING",
                          "note": ("双环境语义:符号层证书判据字段沙盒双跑"
                                   "由车道A 复核执行;本 JSON 为宿主参考值")}
    all_ok = bool(certs_ok)
    payload["status"] = "DONE" if all_ok else "HALTED-AT-DECISION-POINT"
    payload["verdict"] = (
        "候选构造冻结完成(宿主):A 案字典组装 CERT0-3 全过;D-M1-1 落 "
        "A-CONFIRMED;酉性地位声明入册;构造 sha256 已冻结。本件无任何涌现"
        "主张;eps_DOF=1 待主跑实测;主跑(轮 2)自此解锁(预飞 PASS + 构造"
        "冻结双前提齐)。" if all_ok else
        "A 案符号层病灶:停在择定位,报车道A;禁开主跑。")

    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)
    print("=" * 74)
    print(f"CANDIDATE: {'DONE' if all_ok else 'HALT'}  "
          f"construction_sha256={payload['construction_freeze']['construction_sha256']}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
