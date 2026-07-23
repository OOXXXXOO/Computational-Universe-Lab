"""J5 攻坚探针(车道B,只读 import,不改任何被 import 模块):
宽盒 vs 光锥障碍的追因——green_one 的 J5 慢引力子(c_gw=0.5)是不是因为 3D
几何演化 _geom_step 未子循环(CFL cg2<=1/3),而非结构性不可能?

假设:把 _geom_step 嵌套 n 个子步/外步(每子步 cg2_sub=cg2_phys/n^2,CFL 稳定),
几何每外步多走 n 倍 => c_gw(每外步)=sqrt(cg2_phys),同时空间宽盒 stencil 不变
=> N_prop 应仍为 2。若成立,J5 墙消解,是可标定不是结构。

纯几何测试:G_m=0(无源)、feedback=False => rule.step == 纯 _geom_step。
判据:judge_dof 的 N_prop=[2,2,2,2] 且 stable,v_meas 随 n 提到 ~sqrt(cg2_phys)。
"""
import numpy as np

from rulespace_gpu import green_one as go
from rulespace_gpu import emergence_judge as ej


def _cell_avg_spatial(h):
    """R13 cell-average Ā = A0 A1 A2 on the 3 SPATIAL axes of a packed field
    shaped (..., Nx, Ny, Nz, 10) -> axes -4,-3,-2 (mirrors r13.Aavg=½(f+roll)).
    T7: this identically annihilates the Nyquist (k=π) sector per axis."""
    for ax in (-4, -3, -2):
        h = 0.5 * (h + np.roll(h, 1, ax))
    return h


def make_subcycled_rule(cg2_phys=1.0, n=2, kappa=0.5, th0=0.5, dm=0.25, seed=11):
    """green_one 纯几何 rule,但把单次 _geom_step 换成 n 个子步/外步。
    源=0(G_m=0),feedback=False => step 就是纯宽盒 leapfrog + de-Donder。"""
    base = go.make_green_one_rule(mode="jbar", cg2=cg2_phys, kappa=kappa,
                                  G_m=0.0, th0=th0, dm=dm, feedback=False,
                                  sponge_w=0, seed=seed)
    base_step = base["step"]
    cg2_sub = cg2_phys / (n * n)          # n 子步累积得物理速度 sqrt(cg2_phys)

    # 直接在几何层嵌套:src=0,故 n 个纯 _geom_step 子步即可(不碰 walker cache
    # 逻辑——walker 每外步仍只走一次,几何走 n 次,这正是"几何相对物质子循环")
    def step(state):
        s = state
        z = np.zeros(state[0].shape)      # src=0
        for _ in range(n):
            s = go._geom_step(s, cg2_sub, kappa, z, tr_sign=1.0, damping=True)
        return s

    return {"name": f"subcycle n={n} cg2_phys={cg2_phys}",
            "n_levels": 4, "cg2": cg2_phys, "step": step}


def make_subcycled_Abar_rule(cg2_phys=1.0, n=2, kappa=0.5, th0=0.5, dm=0.25,
                             seed=11, every_substep=True):
    """同上,但每(子)步对几何场施 R13 胞平均 Ā(=A0A1A2),T7 定理保证恒等地
    杀 Nyquist 盲扇区。假设:Ā 压住被子循环唤醒的 stride-2 doubler => N_prop 回 2,
    同时探针模 (k~pi/4) 几乎不受 Ā 影响 => v_meas 仍 ~sqrt(cg2_phys)。"""
    cg2_sub = cg2_phys / (n * n)

    _abar = _cell_avg_spatial

    def step(state):
        s = state
        z = np.zeros(state[0].shape)
        for _ in range(n):
            s = go._geom_step(s, cg2_sub, kappa, z, tr_sign=1.0, damping=True)
            if every_substep:
                s = (_abar(s[0]),) + s[1:]
        if not every_substep:
            s = (_abar(s[0]),) + s[1:]
        return s

    return {"name": f"subcycle+Abar n={n} cg2_phys={cg2_phys}",
            "n_levels": 4, "cg2": cg2_phys, "step": step}


def run(cg2_phys, n, N=16, T=384, trials=6, kind="plain", **kw):
    if kind == "abar":
        rule = make_subcycled_Abar_rule(cg2_phys=cg2_phys, n=n, **kw)
    else:
        rule = make_subcycled_rule(cg2_phys=cg2_phys, n=n)
    r = ej.judge_dof(rule, N=N, T=T, trials=trials)
    vs = [e.get("v_meas", float("nan")) for e in r["per_k"]]
    return {"cg2_phys": cg2_phys, "n": n, "cg2_sub": cg2_phys / (n * n),
            "n_prop_all": r["n_prop_all"], "stable": r["stable"],
            "lightcone_ok": r.get("lightcone_ok"),
            "speed_spread": r.get("speed_spread"),
            "v_meas": [round(float(v), 4) if np.isfinite(v) else None for v in vs]}


if __name__ == "__main__":
    import json
    print(f"backend check via emergence_judge; c_gw target = sqrt(cg2_phys)")
    print("=" * 78)
    cases = [
        (1.0, 1),    # baseline: un-sub-cycled cg2=1 -> EXPECT UNSTABLE (CFL wall)
        (1.0, 2),    # sub-cycle n=2, cg2_sub=0.25 -> EXPECT stable, N_prop=2, v~1
        (1.0, 3),    # n=3, cg2_sub=0.111 -> stable, N_prop=2
        (0.985, 2),  # target c_gw=sqrt(0.985)=0.992 ~ c_matter=0.993
        (0.25, 1),   # green_one's actual setting: slow graviton control (c_gw=0.5)
    ]
    out = []
    for cg2, n in cases:
        res = run(cg2, n)
        res["kind"] = "plain"
        out.append(res)
        print(f"[plain] cg2_phys={cg2:.3f} n={n}  cg2_sub={res['cg2_sub']:.4f}  "
              f"stable={str(res['stable'])[0]}  N_prop={res['n_prop_all']}  "
              f"v_meas={res['v_meas']}  lc_ok={res['lightcone_ok']}")

    print("-" * 78)
    print("ESCAPE CANDIDATE: R13 cell-average Ā each sub-step (T7 kills Nyquist)")
    for cg2, n in [(1.0, 2), (0.985, 2), (1.0, 3)]:
        res = run(cg2, n, kind="abar", every_substep=True)
        res["kind"] = "abar_everysub"
        out.append(res)
        print(f"[Ā/sub] cg2_phys={cg2:.3f} n={n}  "
              f"stable={str(res['stable'])[0]}  N_prop={res['n_prop_all']}  "
              f"v_meas={res['v_meas']}  lc_ok={res['lightcone_ok']}")
    json.dump(out, open("green_one_subcycle_probe_results.json", "w"), indent=1)
    print("\nwrote green_one_subcycle_probe_results.json")
    print("VERDICT: if n>=2 rows give stable + N_prop=[2,2,2,2] + v_meas~sqrt(cg2_phys),")
    print("         the J5 wall is a MISSING-SUBCYCLE artifact, NOT structural.")
