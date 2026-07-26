"""v2m2_preflight -- M2' 预飞对拍行(任务书 §5;lane B 轮 1,2026-07-27)。

AUTHORITY(判据预注册,运行后不得回改;红线 4):
  docsv2/v2-任务书-M2-自旋2耦合闭环.md §5(预飞四行)§9(红线十三条)
  docsv2/v2-审定-M2任务书-2026-07-27.md(R1-R6;R3 源速口径 v/c<=0.5 即格点 v<=0.25)
  docsv2/v2-收口-M0-2026-07-26.md(不变量口径、双环境语义、可移植性 spec 终态)
  docsv2/v2-收口-M1-2026-07-27.md(M1' 收口 = D2 串行硬门解除的依据)

预飞 = 主跑前的控制行,四行(任务书 §5 逐条):
  (i)   R30 几何锚(eps_geo=0 端):M0' 控制矩阵行 1 复跑(evaluate_v2_candidate
        -> controls.row1_r30,N_prop=2 断崖 svn 列 vs r30_results.json 冻结值)
        + Bianchi 恒等式符号证书复证(r30 冻结函数原样重跑 + 对拍冻结值);
  (ii)  M1' 产物锚(eps=1 端,已收口 7466d44/15469d5):v2m1 冻结证书链 hash
        只读校验(缺一 = 预飞不完整 = 禁开主跑,D2 硬门脚本层落地)+ 判据字段
        对拍:evaluate_v2_candidate(ctrl_R23) -> row2_r23 比对器(vs 冻结
        r23_results.json)且八标量+整数+eps 对拍 v2m1_candidate.json CERT1
        冻结值 diff <= 1e-12;引用而非重跑长跑(任务书 §4.3 P0b 口径);
  (iii) 耦合层符号证书:源相容 kappa(z).eta.hbar(z) == 0 算子级(全 BZ 16^3,
        v 格点单位 {0, 0.05, 0.15, 0.25},上限 = 审定 R3 钉死的 0.25)
        + 静态极限 z=1 逐位退化 r25_static_newton.static_newton_lift
        + R25-E2 镜像 sector 对拍:实空间 hbar0i(平面波)vs 符号层 oracle
        < 1e-11(任务书 §5-3 写死)+ 镜像配对残差 <= 1e-12 + Re-collapse
        负控必须击穿(deDonder O(1),镜像 sector 承重性有牙);
  (iv)  负控行:冻结走行族(row5:N_prop=[4,4,5,5] + walk 因子逐位 + 不变量
        基稳健)+ teeth 裸波(row4:N_prop=[6,6,6,6] 精确)。

判据/口径(脚本头写死;失败走追因,禁调 tol -- 任务书 §5):
  TOL_JUDGE  = 1e-12   # 判据字段对拍门(M0' 可移植性 spec 终态)
  TOL_ORACLE = 1e-11   # (iii) E2 镜像 sector 符号层 oracle(任务书 §5-3 原文)
  TOL_RS_ID  = 1e-10   # Bianchi 实空间算子恒等式(r30 冻结 verdict 同值)
  RE_COLLAPSE_MIN = 0.1  # (iii) 负控:Re-collapse deDonder 残差必须 >= 此值
                         # (冻结 E2-1 实测 2.328;判"有牙",非精度门)
  V_LATTICE_SET = (0.0, 0.05, 0.15, 0.25)   # 格点单位;= v/c {0,0.1,0.3,0.5},
                                            # c = cos(pi/3) = 0.5(审定 R3)
  BZ_N_SRC = 16        # (iii)(a) 源相容 BZ 网格(冻结 S2 协议同值)
  N_RANDK_STATIC = 200 # (iii)(b) 静态逐位退化随机 k 数(冻结 S2(b) 协议同值)
  SEED_STATIC = 250725 # 同冻结 cert_S2 的 rng 种子谱系
  E2_MODES = 8 组 (cert_E2_1 冻结名单), E2_N = 12, 镜像配对 N=8/T=8(冻结协议)

冻结件 hash(先行写死;逐位不符 = HALT,红线 2):
  [M0' 冻结七件 + M1' 新增件 rulespace_v2/spin1.py](收口终态现值)
  [v2m1 有效证书链五件 .py + 五件 .json](v2-收口-M1-2026-07-27.md §三 名单)
  [源链/清除冻结件:r25_moving_source_symbol / r25_moving_source_realspace /
   r25_static_newton / r25_eddington / r26_hyperbolic_constraint /
   r10_current_generator](构造冻结时点取值先行写死;其余经 frozen.py 注册表)

双环境语义(M0' 终态):本脚本 = 宿主跑;JSON 留沙盒位(sandbox.status=PENDING),
沙盒双跑由车道A 复核执行。预飞任一行不落位 => 禁开主跑,停手追因报车道A。
措辞红线(红线 10/11/12):预飞无任何涌现主张;eps_geo=0 是候选定义属性;
不使用"自旋 2 涌现"表述;PASS 只解锁"构造冻结后可开主跑"。

Run:  RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m2_preflight.py
      (writes data/results/v2m2_preflight.json, 增量写盘)
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

OUT = os.path.join(ROOT, "data", "results", "v2m2_preflight.json")

# ---- 判据(写死;运行后不得回改,红线 4) ---------------------------------
TOL_JUDGE = 1e-12
TOL_ORACLE = 1e-11
TOL_RS_ID = 1e-10
RE_COLLAPSE_MIN = 0.1
V_LATTICE_SET = (0.0, 0.05, 0.15, 0.25)     # 格点单位(审定 R3:上限 0.25)
BZ_N_SRC = 16
N_RANDK_STATIC = 200
SEED_STATIC = 250725
E2_N = 12
E2_MODES = [(1, 0, 0), (1, 1, 0), (2, 1, 0), (1, 2, -1), (2, 2, 1),
            (3, 1, -2), (1, 3, 2), (2, -1, 3)]   # cert_E2_1 冻结名单
PAIR_N, PAIR_T = 8, 8                            # cert_E2_2(b) 冻结协议

# ---- 先行写死的冻结 hash(红线 2:逐位校验只读) --------------------------
M0_SEVEN_SHA256 = {                     # v2-收口-M0-2026-07-26.md §二 现值
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
M1_CHAIN_SHA256 = {                     # v2-收口-M1-2026-07-27.md §三 证书链
    "rulespace_v2/spin1.py":
        "69317d39ce304740b4e096df63a85ccfd63beb2a3094038ba9ebd2d923b17384",
    "experiments/v2m1_preflight.py":
        "3dfef16aac712d2726226185cf03ed2638ce15abcd76ac37358809598fe8d563",
    "experiments/v2m1_candidate.py":
        "8aa00b0a9847ec0a6c05b857f6d8375e6d13879fd639342623d6f95b7f96b1ac",
    "experiments/v2m1_maxwell_loop_r3.py":
        "d8535f912ed3d18521c681b1846cd98a0adf4bf1e1999e69549f804c911f2ce1",
    "experiments/v2m1_guns_r2.py":
        "b9743ae56a786fe68fdadfcdf2578dcb2d80cf7b491368fa2dd3666fd428d5ea",
    "experiments/v2m1_verdict_probe.py":
        "81da853a1261fc36a85d8254a4cfcd71214497252acae3d42675f640125168e6",
    "data/results/v2m1_preflight.json":
        "6736cd758b3dffbebdbb0a6ae6f687e053feeba42688846eb603da9833e55284",
    "data/results/v2m1_candidate.json":
        "4b6db37993ee69cc2e2a452888e510f8b8f1369001c85d03d5ef22e52efc3a31",
    "data/results/v2m1_maxwell_loop_r3.json":
        "2cd50d89e5dee3407db911da1a462c14292049559bc2aaa968c04b45951ceb57",
    "data/results/v2m1_guns_r2.json":
        "e8e9d80dbf77f6a39fc1bd3ca16ef027c6eb459455f6b550d7656cfb651d33ff",
    "data/results/v2m1_verdict_probe.json":
        "1bd30d7dbd0b27b7245e0996b6bb660eb8b5b2c76c10ca2a1feca707ada9478d",
}
SRC_CHAIN_SHA256 = {                    # 源链/清除冻结件(构造冻结时点取值)
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

V2M1_CONSTRUCTION_SHA256 = \
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
    raise TypeError(type(o))


def write_json(payload):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_jd)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def verify_pinned():
    checked, ok, missing = {}, True, []
    for rel, exp in {**M0_SEVEN_SHA256, **M1_CHAIN_SHA256,
                     **SRC_CHAIN_SHA256}.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            missing.append(rel)
            ok = False
            checked[rel] = {"sha256": None, "expected": exp, "match": False,
                            "missing": True}
            continue
        got = sha256_file(p)
        m = (got == exp)
        ok = ok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    return {"pass": bool(ok), "missing": missing, "checked": checked}


def main():
    t0 = time.time()
    env = INV.environment_record()
    payload = {
        "register": "v2m2-preflight (M2' 预飞对拍行;任务书 §5;lane B 轮 1)",
        "status": "RUNNING", "backend": "numpy (fp64)",
        "authority": ["docsv2/v2-任务书-M2-自旋2耦合闭环.md §5/§9",
                      "docsv2/v2-审定-M2任务书-2026-07-27.md(R3 源速口径)",
                      "docsv2/v2-收口-M0-2026-07-26.md(可移植性 spec 终态)",
                      "docsv2/v2-收口-M1-2026-07-27.md(D2 硬门解除依据)"],
        "tol": {"judge": TOL_JUDGE, "oracle_e2": TOL_ORACLE,
                "bianchi_realspace": TOL_RS_ID,
                "re_collapse_teeth_min": RE_COLLAPSE_MIN},
        "v_lattice_set": list(V_LATTICE_SET),
        "v_speed_convention": ("审定 R3 钉死:源速上限 v/c <= 0.5 即格点单位 "
                               "v <= 0.25(c = cos theta_g = 0.5);本预飞 v 集 "
                               "= 格点 {0, 0.05, 0.15, 0.25}"),
        "environment": env,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "wording_redline": ("预飞无任何涌现主张;eps_geo=0 是候选定义属性,"
                            "不是待测项;PASS 只解锁'构造冻结后可开主跑'"
                            "(任务书 §9 红线 10/11/12)"),
        "sandbox": {"status": "PENDING",
                    "note": ("双环境语义(M0' 终态):判据字段宿主+沙盒双跑 "
                             "diff <= 1e-12;沙盒侧由车道A 复核执行,本 JSON "
                             "为宿主参考值")},
    }
    write_json(payload)

    print("v2m2 preflight: M2' 预飞四行(R30 锚 + M1' 锚 + 耦合符号证书 + 负控)")
    print("=" * 74)
    print(f"[env] numpy {env['numpy_version']}  blas={env['blas']}  "
          f"{env['platform']}")

    # ---- 0. 冻结件 hash 逐位校验(红线 2;缺件 = D2 硬门未满足) ------------
    hz1 = verify_pinned()
    hz0 = FZ.verify_frozen()
    payload["hash_verification"] = {
        "m2_pinned": {"pass": hz1["pass"], "missing": hz1["missing"],
                      "checked": hz1["checked"]},
        "m0_registry_pass": hz0["pass"],
        "m0_registry": hz0}
    write_json(payload)
    print(f"[cert] 先行写死 hash({len(hz1['checked'])} 件): "
          f"{'PASS' if hz1['pass'] else 'FAIL'};M0' 注册表: "
          f"{'PASS' if hz0['pass'] else 'FAIL'}")
    if not (hz1["pass"] and hz0["pass"]):
        payload["status"] = "HALT-frozen-hash-mismatch"
        payload["verdict"] = ("冻结件 hash 不符或 M1' 收口件缺失:仪器变更/"
                              "D2 硬门未满足,停手报车道A(红线 2/9);禁开主跑。")
        write_json(payload)
        return 1

    # ---- (i) R30 几何锚:控制矩阵行 1 复跑 + Bianchi 复证 ------------------
    tr = time.time()
    cand1 = C.control_candidates()["row1_r30"]
    gc1 = G.evaluate_v2_candidate(cand1)
    row1 = C.row1_r30(gc1)
    R30M = FZ.mod("r30_tensor_complex_dynamical")
    ci = R30M.complex_identities_bz()
    ci_rs = R30M.complex_identity_realspace()
    with open(os.path.join(ROOT, "data", "results", "r30_results.json"),
              "r", encoding="utf-8") as fh:
        R30F = json.load(fh)
    cif = R30F["complex_identities"]
    ci_diffs = {k: abs(ci[k] - cif[k]) for k in
                ("div_inc_contracted_Bianchi_kappaG",
                 "div_inc_full_second_Bianchi",
                 "inc_D_riemann_of_gauge",
                 "maxwell_divcurl_baseline")}
    ci_diffs["div_inc_realspace_operator_identity"] = abs(
        ci_rs - cif["div_inc_realspace_operator_identity"])
    bianchi_ok = (ci["div_inc_contracted_Bianchi_kappaG"] < TOL_JUDGE
                  and ci["div_inc_full_second_Bianchi"] < TOL_JUDGE
                  and ci["inc_D_riemann_of_gauge"] < TOL_JUDGE
                  and ci_rs < TOL_RS_ID
                  and max(ci_diffs.values()) <= TOL_JUDGE)
    j5_diff = abs(gc1.gates["G3_j5_cocone"]["raw"]["max_freq_minus_shell"]
                  - R30F["yee_certificates"]["max_freq_minus_shell"])
    ok_i = bool(row1["pass"] and row1["max_abs_diff"] <= TOL_JUDGE
                and bianchi_ok and j5_diff <= TOL_JUDGE)
    payload["preflight_i_r30_anchor"] = {
        "row1_r30": row1,
        "bianchi_recert": {"recomputed": {**ci,
                                          "div_inc_realspace_operator_identity":
                                              ci_rs},
                           "frozen": cif, "per_key_diff": ci_diffs,
                           "pass": bool(bianchi_ok)},
        "j5_freq_minus_shell_diff_vs_frozen": j5_diff,
        "epsilon_note": ("此处 eps_DOF=0 是 D1 定义锚(hand_built=all),"
                         "非 M2-G8 实测;实测在主跑轮 2(红线 5)"),
        "seconds": time.time() - tr, "pass": ok_i}
    write_json(payload)
    print(f"[(i) R30 锚] {'PASS' if ok_i else 'FAIL'}  "
          f"row1 diff={row1['max_abs_diff']:.2e}  N_prop={row1['remeasured']['n_prop_seq']}  "
          f"Bianchi max={max(ci['div_inc_contracted_Bianchi_kappaG'], ci['div_inc_full_second_Bianchi']):.1e}  "
          f"({time.time()-tr:.1f}s)")
    if not ok_i:
        payload["status"] = "HALT-preflight-i-failed"
        payload["verdict"] = ("预飞 (i) R30 锚不落位:停手追因(禁调 tol),"
                              "报车道A;禁开主跑(任务书 §5)。")
        write_json(payload)
        return 1

    # ---- (ii) M1' 产物锚(eps=1 端;引用 + 判据字段对拍,不重跑长跑) -------
    tr = time.time()
    with open(os.path.join(ROOT, "data", "results", "v2m1_candidate.json"),
              "r", encoding="utf-8") as fh:
        M1C = json.load(fh)
    with open(os.path.join(ROOT, "data", "runtime", "v2m1_state.json"),
              "r", encoding="utf-8") as fh:
        M1S = json.load(fh)
    lineage_ok = (M1C["status"] == "DONE"
                  and M1C["construction_freeze"]["construction_sha256"]
                  == V2M1_CONSTRUCTION_SHA256
                  and M1S.get("lit") is True)
    cand2 = C.control_candidates()["row2_r23"]
    gc2 = G.evaluate_v2_candidate(cand2)
    row2 = C.row2_r23(gc2)
    frozen_cert1 = M1C["CERT1_r23_p6_symbol"]["row2_r23_comparator"]["remeasured"]
    keys8 = ["null", "cg", "dist_transverse", "F_gauge", "F_transverse_min",
             "transverse_retention", "constraint_decay", "operator_err"]
    m1_diffs = {k: abs(row2["remeasured"][k] - frozen_cert1[k]) for k in keys8}
    ints_ok = (row2["remeasured"]["dims"] == frozen_cert1["dims"]
               and row2["remeasured"]["ranks"] == frozen_cert1["ranks"]
               and bool(row2["remeasured"]["all_pass"])
               and bool(frozen_cert1["all_pass"])
               and row2["remeasured"]["epsilon_dof"]
               == frozen_cert1["epsilon_dof"] == 1.0)
    ok_ii = bool(lineage_ok and row2["pass"]
                 and row2["max_abs_diff"] <= TOL_JUDGE
                 and ints_ok and max(m1_diffs.values()) <= TOL_JUDGE)
    payload["preflight_ii_m1_anchor"] = {
        "m1_lineage": {"v2m1_candidate_status": M1C["status"],
                       "v2m1_construction_sha256":
                           M1C["construction_freeze"]["construction_sha256"],
                       "expected_construction_sha256": V2M1_CONSTRUCTION_SHA256,
                       "v2m1_state_lit": M1S.get("lit"),
                       "v2m1_state_sha256_at_read": sha256_file(
                           os.path.join(ROOT, "data", "runtime",
                                        "v2m1_state.json")),
                       "pass": bool(lineage_ok)},
        "row2_r23_vs_r23_frozen": row2,
        "judge_field_diffs_vs_v2m1_candidate": m1_diffs,
        "integers_booleans_ok": bool(ints_ok),
        "note": ("D2 串行硬门脚本层落地:M1' 证书链五件 .py + 五件 .json hash "
                 "逐位在册(见 hash_verification);判据字段对拍 = 引用件级,"
                 "不重跑 M1' 长跑(任务书 §4.3 P0b 口径)"),
        "seconds": time.time() - tr, "pass": ok_ii}
    write_json(payload)
    print(f"[(ii) M1' 锚] {'PASS' if ok_ii else 'FAIL'}  "
          f"row2 diff={row2['max_abs_diff']:.2e}  "
          f"vs v2m1 CERT1 diff={max(m1_diffs.values()):.2e}  lit={M1S.get('lit')}  "
          f"({time.time()-tr:.1f}s)")
    if not ok_ii:
        payload["status"] = "HALT-preflight-ii-failed"
        payload["verdict"] = ("预飞 (ii) M1' 锚不落位(D2 硬门/判据字段):"
                              "停手追因,报车道A;禁开主跑。")
        write_json(payload)
        return 1

    # ---- (iii) 耦合层符号证书 ----------------------------------------------
    tr = time.time()
    MS = FZ.mod("r25_moving_source_symbol")
    RSM = FZ.mod("r25_moving_source_realspace")
    R25W = FZ.mod("r25_auxiliary_wilson_complex")
    L2 = FZ.mod("cp1_v4_L2")
    ETA = MS.ETA

    # (a) 源相容 kappa(z).eta.hbar(z) == 0 -- 全 BZ x 预注册 v 集(算子级)
    dd_worst = 0.0
    for v in V_LATTICE_SET:
        vv = np.array([v, 0.0, 0.0])
        for idx in np.ndindex(BZ_N_SRC, BZ_N_SRC, BZ_N_SRC):
            if idx == (0, 0, 0):
                continue
            k = 2 * np.pi * np.array(idx, float) / BZ_N_SRC
            z = complex(np.exp(-1j * float(vv @ k)))
            hb, _ = MS.hbar_moving(k, z)
            dd_worst = max(dd_worst, float(np.max(np.abs(
                (ETA @ MS.kappa(k, z)) @ hb))))
    # (b) 静态极限 z=1 逐位退化 r25_static_newton(S2(b) 冻结协议)
    rng = np.random.default_rng(SEED_STATIC)
    static_dev = 0.0
    for _ in range(N_RANDK_STATIC):
        k = rng.uniform(-np.pi, np.pi, 3)
        U = L2.walk_symbol(k)
        static_dev = max(static_dev, float(np.max(np.abs(
            MS.normal_h_packed(k, 1.0) - R25W.static_newton_lift(U)))))
    # (c) E2 镜像 sector:实空间 hbar0i(平面波)vs 符号层 oracle
    oracle_dev, re_dd, re_imcur = 0.0, 0.0, 0.0
    for v in V_LATTICE_SET[1:]:
        vv = np.array([v, 0.0, 0.0])
        for nv in E2_MODES:
            k = 2 * np.pi * np.array(nv, float) / E2_N
            z = complex(np.exp(-1j * float(vv @ k)))
            ph = RSM.plane(k, E2_N)
            hb0i_rs = RSM.hbar0i_realspace(ph, z)
            hb = MS.hbar_moving(k, z)[0]
            oracle_dev = max(oracle_dev, float(np.max(np.abs(
                hb0i_rs - hb[0, 1:]))))
            kup = ETA @ MS.kappa(k, z)
            hb_re = np.real(hb)
            re_imcur = max(re_imcur, float(np.max(np.abs(
                np.imag(hb_re[0, 1:])))))
            re_dd = max(re_dd, float(np.max(np.abs(kup @ hb_re))))
    # (d) 镜像配对残差(冻结步 step/step_minus,E2-2(b) 协议 N=8/T=8)
    RS = FZ.mod("r25_realspace_step")
    rng2 = np.random.default_rng(RSM.SEED + 1)   # 态种子(独立协议,种子写死)
    v = 0.15                    # 预注册区间内点(格点单位;冻结协议用 0.3)
    nv = (1, 1, 0)
    k = 2 * np.pi * np.array(nv, float) / PAIR_N
    z = complex(np.exp(-1j * v * k[0]))
    ph = RSM.plane(k, PAIR_N)
    hp = (rng2.normal(size=(RS.NF, PAIR_N, PAIR_N, PAIR_N))
          + 1j * rng2.normal(size=(RS.NF, PAIR_N, PAIR_N, PAIR_N)))
    pp = (rng2.normal(size=(RS.NF, PAIR_N, PAIR_N, PAIR_N))
          + 1j * rng2.normal(size=(RS.NF, PAIR_N, PAIR_N, PAIR_N)))
    hm, pm = np.conjugate(hp), np.conjugate(pp)
    pair = 0.0
    for t in range(PAIR_T):
        D = RSM.moving_drive14(k, z, ph) * (z ** t)
        hp, pp = RS.step(hp, pp, drive=D)
        hm, pm = RS.step_minus(hm, pm, drive=D)
        pair = max(pair, float(max(np.max(np.abs(hm - np.conjugate(hp))),
                                   np.max(np.abs(pm - np.conjugate(pp))))))
    teeth_ok = bool(re_dd >= RE_COLLAPSE_MIN and re_imcur == 0.0)
    ok_iii = bool(dd_worst <= TOL_JUDGE and static_dev <= TOL_JUDGE
                  and oracle_dev <= TOL_ORACLE and pair <= TOL_JUDGE
                  and teeth_ok)
    payload["preflight_iii_coupling_symbol_certs"] = {
        "a_source_compat_kappa_eta_hbar_max": dd_worst,
        "b_static_z1_bitwise_vs_static_newton": static_dev,
        "c_e2_mirror_hbar0i_realspace_vs_symbol_oracle": oracle_dev,
        "d_mirror_pairing_residual": pair,
        "e_re_collapse_negative_control": {
            "deDonder_residual": re_dd, "min_required": RE_COLLAPSE_MIN,
            "momentum_current_annihilated": re_imcur,
            "note": ("负控有牙判据:Re(hbar_+) 塌缩必须湮灭动量流(==0)且"
                     "击穿 deDonder(>=0.1;冻结 E2-1 实测 2.328)——镜像 "
                     "sector 承重,h̄0i 语义由镜像 sector 保持")},
        "protocol": ("(a) BZ 16^3 x v 格点 {0,0.05,0.15,0.25}(审定 R3 口径)"
                     ";(b) S2(b) 冻结协议 200 随机 k;(c) cert_E2_1(a) 冻结"
                     "模式名单 N=12;(d) cert_E2_2(b) 冻结步配对 N=8/T=8,"
                     "v 取预注册区间内点 0.15;判据核全部只读 import"),
        "seconds": time.time() - tr, "pass": ok_iii}
    write_json(payload)
    print(f"[(iii) 耦合符号证书] {'PASS' if ok_iii else 'FAIL'}  "
          f"kappa.eta.hbar={dd_worst:.1e}  静态逐位={static_dev:.1e}  "
          f"E2 oracle={oracle_dev:.1e}  镜像配对={pair:.1e}  "
          f"Re-collapse 击穿={re_dd:.2f}  ({time.time()-tr:.1f}s)")
    if not ok_iii:
        payload["status"] = "HALT-preflight-iii-failed"
        payload["verdict"] = ("预飞 (iii) 耦合层符号证书不落位:停手追因"
                              "(禁调 tol),报车道A;禁开主跑。")
        write_json(payload)
        return 1

    # ---- (iv) 负控行:冻结走行族 + teeth ----------------------------------
    tr = time.time()
    cand5 = C.control_candidates()["row5_frozen_walk"]
    gc5 = G.evaluate_v2_candidate(cand5)
    row5 = C.row5_frozen_walk(gc5)
    cand4 = C.control_candidates()["row4_teeth"]
    gc4 = G.evaluate_v2_candidate(cand4)
    row4 = C.row4_teeth(gc4)
    ok_iv = bool(row5["pass"] and row4["pass"])
    payload["preflight_iv_negative_controls"] = {
        "row5_frozen_walk": row5, "row4_teeth": row4,
        "seconds": time.time() - tr, "pass": ok_iv}
    write_json(payload)
    print(f"[(iv) 负控行] {'PASS' if ok_iv else 'FAIL'}  "
          f"冻结走行 N_prop={row5['remeasured']['N_prop']}(期望 [4,4,5,5])  "
          f"teeth N_prop={row4['remeasured']['n_prop_all']}(期望 [6,6,6,6])  "
          f"({time.time()-tr:.1f}s)")

    # ---- 判定 --------------------------------------------------------------
    all_ok = bool(ok_i and ok_ii and ok_iii and ok_iv)
    payload["preflight_pass"] = all_ok
    payload["status"] = "DONE" if all_ok else "HALT-preflight-iv-failed"
    payload["verdict"] = (
        "预飞 PASS(宿主):(i) R30 几何锚行 1 复跑 + Bianchi 恒等式复证全 "
        "<=1e-12;(ii) M1' 产物锚 hash 链齐 + 判据字段对拍 <=1e-12(D2 硬门"
        "满足);(iii) 耦合层符号证书四项落位(源相容/静态逐位/E2 oracle/镜像"
        "配对)+ Re-collapse 负控有牙;(iv) 冻结走行族与 teeth 负控按冻结值"
        "落位。构造冻结(v2m2_candidate)解锁;本轮零主跑零炮组(轮 1 纪律);"
        "沙盒双跑位留待车道A。无任何涌现主张;eps_geo=0 为候选定义属性。"
        if all_ok else
        "预飞不落位:停手追因(禁调 tol),报车道A;禁开主跑(任务书 §5)。")

    payload["source_sha256"] = sha256_file(os.path.abspath(__file__))
    payload["total_seconds"] = time.time() - t0
    write_json(payload)
    with open(OUT, "rb") as fh:
        jsha = hashlib.sha256(fh.read()).hexdigest()
    payload["results_sha256"] = jsha
    write_json(payload)
    print("=" * 74)
    print(f"PREFLIGHT: {'PASS' if all_ok else 'HALT'}  ->  {payload['status']}")
    print(payload["verdict"])
    print(f"source  sha256 = {payload['source_sha256']}")
    print(f"results sha256 = {jsha}")
    print(f"total {time.time()-t0:.1f}s")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
