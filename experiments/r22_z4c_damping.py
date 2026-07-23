"""R22 — Z4c 型约束阻尼 vs 单 gamma vs 三级 Chebyshev:R16 in-vitro oracle 同台对比.

任务(P4/R22):数值相对论的 Z4c 思路——把约束破坏提升为辅助动力学场 Z^nu
(与 C_nu = J hbar 同形状),Z 以特征速度传播、以 kappa1 指数衰减,并通过
梯度回授项(系数 mu_z)推回 h——移植到 R16/R18 的 in-vitro 台架(单 k、在壳、
符号空间),回答:是否有资格进 M1 装配。

方案(逐 k 符号层,与 gamma 方案同一台架、同一实空间雅可比 J = dC/dhbar):

  gamma 方案 :  chi(t+1) = e^{-i w} (I - gamma J'J) chi
  Chebyshev  :  同上,gamma 按三级循环 [g1, g2, g3](R18 处方)
  Z4c 型     :  chi_w = e^{-i w} chi                       (walk)
                C    = J chi_w                             (测约束,同步)
                Z'   = e^{-i w} (1-kappa1) Z + C           (共动载波+衰减+源)
                chi' = chi_w - mu_z J' Z'                  (梯度回授,无滞后)

  关键设计:Z 的载波取与物质 walk 同一色散 e^{-i w(k)}(实空间实现 = 用同一
  walk 核载运 Z,"约束破坏以锥速传播")。在 SVD 奇异方向 (v_j, u_j) 上,
  Z4c 步精确分块为 e^{-i w} * M(sigma),M 为实 2x2:
      M = [[1 - mu s^2,  -mu (1-k1) s],
           [    s     ,     1 - k1  ]]        (s^2 = sigma_j^2)
  det M = 1 - kappa1(与 sigma 无关!),tr M = 2 - kappa1 - mu s^2。
  当所有 s^2 落在复特征值区 (1-b)^2 < mu s^2 < (1+b)^2(b = sqrt(1-kappa1)),
  每个模每步收缩恰为 b —— 全 BZ 一致、与刚度无关。可行性要求
  b >= (sqrt(kap)-1)/(sqrt(kap)+1),kap = s2_max/s2_min:这正是重球/动量法
  把条件数 kap 变 sqrt(kap) 的经典加速;kappa1 = 1 退化回单 gamma 方案。
  稳定窗(Jury):0 < kappa1 < 1 且 mu s2_max < 2(2 - kappa1) —— 谱半径定出,
  非试凑。

自由度记账(硬要求):Z 是辅助场,模式计数必须扣除 Z 扇区。本文件给出
谱证书:增广 14 维步算子的单位模特征值全部落在 chi 扇区的 ker J(6 维,
与 gamma/Chebyshev 完全相同);Z 混合扇区 8 个特征值模长 = sqrt(1-kappa1) < 1,
严格收缩。观测量(Riemann 能量等)只读 chi,Z 不进任何观测量。详见报告。

Run:  python .venv/bin/python r22_z4c_damping.py   (分钟级; 写 r22_results.json)
"""
import json
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from r15_walk_dedonder import (shell_omega, kappa_placed, constraint_matrix,
                               gauge_block, tt_basis)
from r18_realspace_damping import jacobian_C
from r16_cp1_invitro import riemann_energy

DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 22


# ------------------------------------------------------------------ BZ scan
def bz_grid(n=16):
    """R18 的同一 BZ 采样(16^3 格可分辨模,正八分体,去零模)。"""
    kk = [2 * np.pi * np.array([a, b, d]) / n
          for a in range(0, n // 2) for b in range(0, n // 2)
          for d in range(0, n // 2)]
    return [k for k in kk if np.linalg.norm(k) > 1e-9]


def collect_spectra(kk):
    """每个 k:J 的非零 sigma^2 列表 + 在壳 w(k)。"""
    out = []
    for k in kk:
        J = jacobian_C(k)
        s2 = np.linalg.svd(J, compute_uv=False) ** 2
        s2 = s2[s2 > 1e-12]
        w = shell_omega(k)
        out.append((k, w, s2))
    return out


# ------------------------------------------- per-mode contraction (spectral)
def rho_gamma(g, s2):
    return np.abs(1.0 - g * s2)


def rho_cheb_cycle(gs, s2):
    r = np.ones_like(s2)
    for g in gs:
        r = r * (1.0 - g * s2)
    return np.abs(r)


def z4c_eig_moduli(mu, k1, s2, phase=None):
    """Z4c 2x2 块特征值模长(向量化)。phase=None: 共动载波(实矩阵,
    模长与 w 无关);phase=w 数组: 静止 Z 载波消融,块为
    [[e^{-iw}(1-mu s2), -e^{-iw} mu (1-k1) s], [s, 1-k1]]。"""
    s2 = np.asarray(s2, dtype=float)
    s = np.sqrt(s2)
    if phase is None:
        tr = (2.0 - k1 - mu * s2).astype(complex)
        det = np.full_like(tr, 1.0 - k1)
    else:
        ph = np.exp(-1j * np.asarray(phase))
        tr = ph * (1.0 - mu * s2) + (1.0 - k1)
        det = ph * (1.0 - k1) * np.ones_like(s2)
    sq = np.sqrt(tr * tr - 4.0 * det)
    l1 = 0.5 * (tr + sq)
    l2 = 0.5 * (tr - sq)
    return np.maximum(np.abs(l1), np.abs(l2))


def z4c_rho_worst(mu, k1, s2grid):
    return float(z4c_eig_moduli(mu, k1, s2grid).max())


# ----------------------------------------------------------- step operators
def step_gamma(J, w, g):
    return np.exp(-1j * w) * (np.eye(10) - g * (J.conj().T @ J))


def step_z4c(J, w, mu, k1):
    ph = np.exp(-1j * w)
    A = np.zeros((14, 14), dtype=complex)
    A[:10, :10] = ph * (np.eye(10) - mu * (J.conj().T @ J))
    A[:10, 10:] = -mu * (1.0 - k1) * ph * J.conj().T
    A[10:, :10] = ph * J
    A[10:, 10:] = (1.0 - k1) * ph * np.eye(4)
    return A


def transient_amp(M, T=60):
    """max_t ||M^t||_2(瞬态放大,非正规性代价)。"""
    P = np.eye(M.shape[0], dtype=complex)
    amp = 1.0
    for _ in range(T):
        P = M @ P
        amp = max(amp, float(np.linalg.svd(P, compute_uv=False)[0]))
    return amp


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    print("R22  Z4c 型约束阻尼 vs 单 gamma vs Chebyshev — in-vitro 同台对比")
    print("=" * 72)

    # ================================================= 一、基线复现(R18)
    kk = bz_grid(16)
    spec = collect_spectra(kk)
    s2_all = np.concatenate([s2 for (_, _, s2) in spec])
    a, b = float(s2_all.min()), float(s2_all.max())
    kap = b / a
    g_max = 2.0 / b
    g_opt = 2.0 / (a + b)
    s2_lin = np.linspace(a, b, 2000)
    r1 = float(rho_gamma(g_opt, s2_lin).max())          # 单 gamma /步
    r1_3 = r1 ** 3
    cheb = [2.0 / (a + b - (b - a) * math.cos((2 * j + 1) * math.pi / 6.0))
            for j in range(3)]
    rc_3 = float(rho_cheb_cycle(cheb, s2_lin).max())    # Chebyshev /3步
    rc_1 = rc_3 ** (1.0 / 3.0)
    print(f"[一] 全 BZ sigma^2 = [{a:.4f}, {b:.4f}]  (R18: [3.0124, 27.1999])"
          f"   刚度比 kap = {kap:.3f}")
    print(f"     gamma_max = {g_max:.4f}  gamma* = {g_opt:.4f}"
          f"   (R18: 0.0735 / 0.0662)")
    print(f"     单 gamma* 最坏收缩: {r1:.4f}/步  {r1_3:.4f}/3步  (验证 0.513)")
    print(f"     Chebyshev {np.round(cheb, 4).tolist()} 最坏 {rc_3:.4f}/3步"
          f"  (验证 0.247)   等效 {rc_1:.4f}/步")
    base_ok = (abs(a - 3.0124) < 2e-3 and abs(b - 27.1999) < 2e-3
               and abs(r1_3 - 0.5131) < 2e-3 and abs(rc_3 - 0.2470) < 2e-3)
    print(f"     基线复现: {'PASS' if base_ok else 'FAIL'}")

    # ====================================== 二、Z4c 谱分析:闭式 + 数值 minimax
    beta_star = (math.sqrt(kap) - 1.0) / (math.sqrt(kap) + 1.0)
    k1_star = 1.0 - beta_star ** 2
    mu_star = (1.0 + beta_star) ** 2 / b
    print(f"\n[二] Z4c 闭式最优(重球极限): b* = (sqrt(kap)-1)/(sqrt(kap)+1) = "
          f"{beta_star:.4f}/步")
    print(f"     kappa1* = 1-b*^2 = {k1_star:.4f}   mu* = (1+b*)^2/s2_max = "
          f"{mu_star:.4f}  (下界 (1-b*)^2/s2_min = {(1-beta_star)**2/a:.4f})")

    # 数值 minimax(粗网格 + 局部加密),不依赖闭式
    def minimax(mu_lo, mu_hi, k1_lo, k1_hi, nm=81, nk=81, ns=201):
        mus = np.linspace(mu_lo, mu_hi, nm)
        k1s = np.linspace(k1_lo, k1_hi, nk)
        s2g = np.linspace(a, b, ns)
        best = (None, None, np.inf)
        for k1 in k1s:
            mod = z4c_eig_moduli(mus[:, None], k1, s2g[None, :])
            worst = mod.max(axis=1)
            i = int(np.argmin(worst))
            if worst[i] < best[2]:
                best = (float(mus[i]), float(k1), float(worst[i]))
        return best
    mu_n, k1_n, rho_n = minimax(0.01, 0.12, 0.05, 0.99)
    mu_n, k1_n, rho_n = minimax(max(0.01, mu_n - 0.01), mu_n + 0.01,
                                max(0.05, k1_n - 0.05), min(0.999, k1_n + 0.05))
    print(f"     数值 minimax: mu = {mu_n:.4f}  kappa1 = {k1_n:.4f}  "
          f"rho = {rho_n:.4f}/步   (闭式 {beta_star:.4f}: "
          f"{'一致' if abs(rho_n - beta_star) < 5e-3 else '不一致!'}")

    # 工作点:留裕量(最优点是平台的收缩点,mu 窗宽为零;退一步换窗)
    beta_op = 0.52
    k1_op = 1.0 - beta_op ** 2
    mu_pl_lo = (1.0 - beta_op) ** 2 / a
    mu_pl_hi = (1.0 + beta_op) ** 2 / b
    mu_op = 0.5 * (mu_pl_lo + mu_pl_hi)
    rho_op = z4c_rho_worst(mu_op, k1_op, s2_lin)
    rho_op_disc = z4c_rho_worst(mu_op, k1_op, s2_all)
    mu_stab = 2.0 * (2.0 - k1_op) / b
    print(f"     工作点(留裕量): kappa1 = {k1_op:.4f}  mu = {mu_op:.4f}"
          f"  -> rho = {rho_op:.4f}/步 = {rho_op**3:.4f}/3步")
    print(f"       mu 平台(rho 恒 = {beta_op}) = [{mu_pl_lo:.4f}, {mu_pl_hi:.4f}]"
          f"  (半宽 ±{100*(mu_pl_hi-mu_pl_lo)/(mu_pl_hi+mu_pl_lo):.1f}%)"
          f"   稳定上界 mu < {mu_stab:.4f}")
    print(f"       离散 BZ 上实际最坏 rho = {rho_op_disc:.4f}")

    # 消融:静止 Z 载波(相位不匹配)
    ws = np.concatenate([np.full(len(s2), w) for (_, w, s2) in spec])
    rho_static_op = float(z4c_eig_moduli(mu_op, k1_op, s2_all, phase=ws).max())
    best_static = (None, None, np.inf)
    for k1 in np.linspace(0.05, 0.99, 60):
        for mu in np.linspace(0.005, min(0.12, 2 * (2 - k1) / b), 60):
            r = float(z4c_eig_moduli(mu, k1, s2_all, phase=ws).max())
            if r < best_static[2]:
                best_static = (float(mu), float(k1), r)
    print(f"     消融(静止 Z 载波): 工作点参数下 rho = {rho_static_op:.4f}/步;"
          f" 重新优化后最好 {best_static[2]:.4f}/步 "
          f"(mu={best_static[0]:.4f}, k1={best_static[1]:.4f})"
          f"  -> 共动载波(相位匹配)是增益的必要条件")

    # ===================================== 三、鲁棒性:参数窗 + 刚度低估余量
    # (1) 阻尼强度整体标度 s
    def worst_at_scale(scheme, s):
        if scheme == "gamma":
            return float(rho_gamma(s * g_opt, s2_lin).max() ** 3)
        if scheme == "cheb":
            return float(rho_cheb_cycle([s * g for g in cheb], s2_lin).max())
        return float(z4c_rho_worst(s * mu_op, k1_op, s2_lin) ** 3)

    def s_limit(scheme):
        lo, hi = 1.0, 3.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if worst_at_scale(scheme, mid) <= 1.0:
                lo = mid
            else:
                hi = mid
        return lo
    scale_rows = []
    for s in (0.8, 0.9, 1.0, 1.1, 1.15, 1.2):
        scale_rows.append({"s": s,
                           "gamma": worst_at_scale("gamma", s),
                           "cheb": worst_at_scale("cheb", s),
                           "z4c": worst_at_scale("z4c", s)})
    s_lim = {sch: s_limit(sch) for sch in ("gamma", "cheb", "z4c")}
    print(f"\n[三] 阻尼强度标度稳定极限 s_max: 单 gamma {s_lim['gamma']:.3f}"
          f"   Chebyshev {s_lim['cheb']:.3f}   Z4c(mu) {s_lim['z4c']:.3f}")

    # (2) sigma2_max 低估余量(装配的真实风险):真实刚度 = f * b
    def worst_at_stiff(scheme, f):
        s2g = np.linspace(a, f * b, 2000)
        if scheme == "gamma":
            return float(rho_gamma(g_opt, s2g).max() ** 3)
        if scheme == "cheb":
            return float(rho_cheb_cycle(cheb, s2g).max())
        return float(z4c_rho_worst(mu_op, k1_op, s2g) ** 3)

    def f_limit(scheme):
        lo, hi = 1.0, 2.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if worst_at_stiff(scheme, mid) <= 1.0:
                lo = mid
            else:
                hi = mid
        return lo
    stiff_rows = []
    for f in (1.0, 1.05, 1.10, 1.15, 1.20):
        stiff_rows.append({"f": f,
                           "gamma": worst_at_stiff("gamma", f),
                           "cheb": worst_at_stiff("cheb", f),
                           "z4c": worst_at_stiff("z4c", f)})
    f_lim = {sch: f_limit(sch) for sch in ("gamma", "cheb", "z4c")}
    mu_low = mu_pl_lo * 1.02
    f_lim_z4c_low = 2.0 * (2.0 - k1_op) / (mu_low * b)
    print(f"     刚度低估余量 f_max: 单 gamma {f_lim['gamma']:.3f}"
          f"   Chebyshev {f_lim['cheb']:.3f}   Z4c {f_lim['z4c']:.3f}"
          f"   (Z4c 取平台低端 mu={mu_low:.4f} 时 {f_lim_z4c_low:.3f},"
          f" 收缩率不变)")
    # (3) kappa1 方向鲁棒性
    k1_rows = [{"k1": float(k1),
                "rho3": float(z4c_rho_worst(mu_op, float(k1), s2_lin) ** 3)}
               for k1 in np.linspace(0.55, 0.90, 8)]
    k1_ok_lo = min(r["k1"] for r in k1_rows if r["rho3"] < rc_3)
    k1_ok_hi = max(r["k1"] for r in k1_rows if r["rho3"] < rc_3)
    print(f"     kappa1 在 [{k1_ok_lo:.2f}, {k1_ok_hi:.2f}] 内 3 步收缩仍 "
          f"< Chebyshev 0.247 (mu 固定 {mu_op:.4f})")

    # ========================= 四、全 BZ 逐 k 谱半径(精确步算子,主指标核对)
    worst = {"gamma": 0.0, "cheb": 0.0, "z4c": 0.0}
    amp = {"gamma": 1.0, "cheb": 1.0, "z4c": 1.0}
    sub = spec[:: max(1, len(spec) // 96)]
    for (k, w, s2) in sub:
        J = jacobian_C(k)
        row = np.linalg.svd(J, compute_uv=False)
        nz = row[row ** 2 > 1e-12] ** 2
        worst["gamma"] = max(worst["gamma"], float(rho_gamma(g_opt, nz).max()) ** 3)
        worst["cheb"] = max(worst["cheb"], float(rho_cheb_cycle(cheb, nz).max()))
        worst["z4c"] = max(worst["z4c"],
                           float(z4c_eig_moduli(mu_op, k1_op, nz).max()) ** 3)
        # 瞬态放大(约束扇区):Chebyshev 循环内 / Z4c 非正规性
        M1 = step_gamma(J, w, g_opt)
        Mc = [step_gamma(J, w, g) for g in cheb]
        Az = step_z4c(J, w, mu_op, k1_op)
        # 约束扇区放大:施加在行空间上的最大范数增长
        U, S, Vh = np.linalg.svd(J)
        V4 = Vh[:4].conj().T                        # 行空间基 (10,4)
        P = V4.copy()
        for t in range(6):
            P = Mc[t % 3] @ P
            amp["cheb"] = max(amp["cheb"],
                              float(np.linalg.svd(J @ P, compute_uv=False)[0]
                                    / S[0]))
        Pz = np.vstack([V4, np.zeros((4, 4))]).astype(complex)
        Q = Pz.copy()
        for t in range(6):
            Q = Az @ Q
            amp["z4c"] = max(amp["z4c"],
                             float(np.linalg.svd(J @ Q[:10], compute_uv=False)[0]
                                   / S[0]))
        Pg = V4.copy()
        for t in range(6):
            Pg = M1 @ Pg
            amp["gamma"] = max(amp["gamma"],
                               float(np.linalg.svd(J @ Pg, compute_uv=False)[0]
                                     / S[0]))
    print(f"\n[四] 离散 BZ 逐 k 精确步算子最坏收缩/3步: 单 gamma "
          f"{worst['gamma']:.4f}  Chebyshev {worst['cheb']:.4f}  "
          f"Z4c {worst['z4c']:.4f}")
    print(f"     约束范数瞬态放大 max_t ||C_t||/||C_0||: 单 gamma "
          f"{amp['gamma']:.2f}  Chebyshev {amp['cheb']:.2f}  Z4c {amp['z4c']:.2f}")

    # =============================== 五、动力学验证(在壳单 k,R16 三个 k)
    kvecs = [np.array([0.5, 0.0, 0.0]), np.array([0.35, 0.35, 0.35]),
             np.array([0.7, 0.2, -0.4])]
    T = 240
    dyn_rows = []
    print(f"\n[五] 在壳单 k 动力学对拍 (T={T}, 种子 {SEED}):")
    for kx in kvecs:
        w = shell_omega(kx)
        J = jacobian_C(kx)
        kapv = kappa_placed(kx)
        TT = tt_basis(kapv)
        G = gauge_block(kapv)
        U, S, Vh = np.linalg.svd(J)
        V4 = Vh[:4].conj().T
        # 在壳混合初条:TT + gauge + 行空间 junk(R16 更正栏纪律)
        cTT = TT @ (rng.normal(size=2) + 1j * rng.normal(size=2))
        cG = G @ (rng.normal(size=4) + 1j * rng.normal(size=4))
        junk = V4 @ (rng.normal(size=4) + 1j * rng.normal(size=4))
        chi0 = cTT + cG + 0.5 * junk
        row = {"k": kx.tolist(), "omega": float(w)}
        for name in ("gamma", "cheb", "z4c"):
            if name == "z4c":
                A = step_z4c(J, w, mu_op, k1_op)
                psi = np.concatenate([chi0, np.zeros(4, complex)])
            else:
                psi = chi0.copy()
            cn = [float(np.linalg.norm(J @ (psi[:10] if name == "z4c" else psi)))]
            tt0 = float(np.linalg.norm(TT.conj().T @ chi0))
            for t in range(T):
                if name == "gamma":
                    psi = step_gamma(J, w, g_opt) @ psi
                elif name == "cheb":
                    psi = step_gamma(J, w, cheb[t % 3]) @ psi
                else:
                    psi = A @ psi
                chi = psi[:10] if name == "z4c" else psi
                cn.append(float(np.linalg.norm(J @ chi)))
            chi = psi[:10] if name == "z4c" else psi
            tt_err = abs(np.linalg.norm(TT.conj().T @ chi) / tt0 - 1.0)
            # 收缩率测量窗:早段 [6, 42](36 步,3 的倍数),避开初始瞬态,
            # 也避开 fp64 舍入地板(~1e-16*|chi|,240 步后约束必然坐底)
            t0, t1 = 6, 42
            meas = ((cn[t1] / cn[t0]) ** (1.0 / (t1 - t0))
                    if cn[t0] > 1e-13 * cn[0] and cn[t1] > 1e-13 * cn[0]
                    else 0.0)
            pred = {"gamma": r1, "cheb": rc_1,
                    "z4c": float(z4c_eig_moduli(
                        mu_op, k1_op, S[S ** 2 > 1e-12] ** 2).max())}[name]
            floored = cn[t1] < 1e-13 * cn[0]
            row[name] = {"tt_err": tt_err, "rate_meas": meas, "rate_pred": pred,
                         "C_final_over_C0": cn[T] / cn[0],
                         "C_floor_rel": cn[T] / cn[0], "floored": floored}
        # 规范模口径:纯规范初条的范数走向(三方案同:压到 ker J 分量平台)
        Pker = np.eye(10) - V4 @ V4.conj().T
        gnorm0 = float(np.linalg.norm(cG))
        gker = float(np.linalg.norm(Pker @ cG))
        psi = cG.copy()
        for t in range(90):
            psi = step_gamma(J, w, g_opt) @ psi
        row["gauge_plateau_pred"] = gker / gnorm0
        row["gauge_plateau_meas_gamma"] = float(np.linalg.norm(psi)) / gnorm0
        # Riemann:末态(z4c)能量应只在 TT + ker 方向;规范模 Riemann 恒零
        rg = max(riemann_energy(kapv, G[:, i]) for i in range(4))
        rtt = riemann_energy(kapv, TT[:, 0])
        row["riemann_gauge"] = float(rg)
        row["riemann_TT"] = float(rtt)
        dyn_rows.append(row)
        print(f"  k={np.round(kx, 2)}: TT保真 |Δ| g/c/z = "
              f"{row['gamma']['tt_err']:.1e}/{row['cheb']['tt_err']:.1e}/"
              f"{row['z4c']['tt_err']:.1e} | 实测收缩率(6-42步窗) vs 预言: "
              f"z4c {row['z4c']['rate_meas']:.4f}/{row['z4c']['rate_pred']:.4f}"
              f"{' (坐底)' if row['z4c']['floored'] else ''}"
              f" | 规范平台 {row['gauge_plateau_meas_gamma']:.3f}"
              f" (预言 {row['gauge_plateau_pred']:.3f})")

    dyn_ok = all(max(r[n]["tt_err"] for n in ("gamma", "cheb", "z4c")) < 1e-12
                 for r in dyn_rows)
    rate_ok = all(r["z4c"]["floored"] or
                  abs(r["z4c"]["rate_meas"] - r["z4c"]["rate_pred"]) < 0.03
                  for r in dyn_rows)
    print(f"     TT 保真 < 1e-12 三方案全过: {'PASS' if dyn_ok else 'FAIL'};"
          f" Z4c 实测=谱预言: {'PASS' if rate_ok else 'FAIL'}")

    # ======================= 六、Z 扇区自由度记账(谱证书,报告单列一节)
    kx = kvecs[2]
    w = shell_omega(kx)
    J = jacobian_C(kx)
    kapv = kappa_placed(kx)
    TT = tt_basis(kapv)
    Az = step_z4c(J, w, mu_op, k1_op)
    ev = np.abs(np.linalg.eigvals(Az))
    n_unit = int(np.sum(ev > 1.0 - 1e-9))
    n_damped = int(np.sum(ev < 1.0 - 1e-9))
    zmix_max = float(np.sort(ev)[::-1][n_unit]) if n_damped else 0.0
    Mg = step_gamma(J, w, g_opt)
    evg = np.abs(np.linalg.eigvals(Mg))
    n_unit_g = int(np.sum(evg > 1.0 - 1e-9))
    # 单位模模式全部属于 chi 扇区的 ker J:验证特征向量的 Z 分量为零
    lam, vec = np.linalg.eig(Az)
    zc = float(max(np.linalg.norm(vec[10:, i])
                   for i in range(14) if abs(lam[i]) > 1.0 - 1e-9))
    # ker J 的非 TT 方向是否携带 Riemann 能量(三方案共有口径,诚实入册)
    U, S, Vh = np.linalg.svd(J)
    ker = Vh[4:].conj().T                              # (10,6)
    Qtt, _ = np.linalg.qr(TT)
    kerp = ker - Qtt @ (Qtt.conj().T @ ker)
    uq, sq, _ = np.linalg.svd(kerp, full_matrices=False)
    nonTT = uq[:, :4]
    riem_nonTT = float(max(riemann_energy(kapv, nonTT[:, i]) for i in range(4)))
    print(f"\n[六] Z 扇区记账(k={np.round(kx,2)}): 增广谱单位模模式 {n_unit} 个"
          f"(= gamma 方案的 {n_unit_g},全在 chi 的 ker J);"
          f"其特征向量 Z 分量 max = {zc:.1e}(机器零)")
    print(f"     Z 混合扇区 {n_damped} 个特征值,模长 max = {zmix_max:.4f}"
          f" = sqrt(1-kappa1) = {math.sqrt(1-k1_op):.4f} < 1(严格收缩,"
          f"不进任何 N_prop 计数)")
    print(f"     [共有口径] ker J 非 TT 方向 Riemann 能量 max = {riem_nonTT:.3f}"
          f"(非零:实空间 ker J ≠ TT⊕gauge,三方案相同,在壳初条纪律下不激发)")
    acct_ok = (n_unit == n_unit_g == 6 and zc < 1e-10
               and abs(zmix_max - math.sqrt(1 - k1_op)) < 1e-6)

    # ============================================= 七、开销(操作计数,粗略)
    nnzJ = int(np.sum(np.abs(J) > 1e-12))
    ops = {
        "gamma": {"stencil_passes": 2, "aux_fields": 0,
                  "cmul_per_site": 4 * nnzJ + 10},
        "cheb": {"stencil_passes": 2, "aux_fields": 0,
                 "cmul_per_site": 4 * nnzJ + 10,
                 "note": "同 gamma,系数按 3 步循环"},
        "z4c": {"stencil_passes": 2, "aux_fields": 4,
                "carrier_fields": 8,
                "cmul_per_site": 4 * nnzJ + 10 + 4 * 8 + 8,
                "note": "J 与 J' 各一遍 + Z 载波(4 分量标量 walk)+ 衰减/源"},
    }
    ratio = ops["z4c"]["cmul_per_site"] / ops["gamma"]["cmul_per_site"]
    print(f"\n[七] 开销: nnz(J) = {nnzJ}; 每格点复乘 gamma/cheb ≈ "
          f"{ops['gamma']['cmul_per_site']}, z4c ≈ {ops['z4c']['cmul_per_site']}"
          f" (x{ratio:.2f}); z4c 额外存储 4 个 Z 复场 + 载波(~8 复场)")

    # ==================================================== 八、汇总 + JSON
    z4c_wins_rate = rho_op ** 3 < rc_3 - 1e-3
    z4c_wider = (f_lim["z4c"] > f_lim["gamma"] + 1e-3
                 and f_lim["z4c"] > f_lim["cheb"] + 1e-3)
    all_pass = bool(base_ok and dyn_ok and rate_ok and acct_ok)
    print("\n" + "=" * 72)
    print(f"主指标(全 BZ 最坏收缩/3步): 单 gamma {r1_3:.3f}  Chebyshev "
          f"{rc_3:.3f}  Z4c {rho_op**3:.3f}"
          f"   -> Z4c {'显著占优' if z4c_wins_rate else '不占优'}")
    print(f"刚度余量 f_max: {f_lim['gamma']:.2f}/{f_lim['cheb']:.2f}/"
          f"{f_lim['z4c']:.2f} (Z4c 平台低端可到 {f_lim_z4c_low:.2f})"
          f"   -> 稳定窗 {'更宽' if z4c_wider else '相当'}")
    print(f"体检: 基线 {'PASS' if base_ok else 'FAIL'} | TT/动力学 "
          f"{'PASS' if (dyn_ok and rate_ok) else 'FAIL'} | Z 记账 "
          f"{'PASS' if acct_ok else 'FAIL'}")

    out = {
        "seed": SEED,
        "baseline": {"sigma2_range": [a, b], "stiffness_kappa": kap,
                     "gamma_max": g_max, "gamma_opt": g_opt,
                     "single_gamma_rate_step": r1,
                     "single_gamma_rate_3step": r1_3,
                     "cheb_gammas": cheb, "cheb_cycle_worst": rc_3,
                     "cheb_rate_step_equiv": rc_1, "reproduced_r18": base_ok},
        "z4c": {"closed_form": {"beta_star": beta_star, "k1_star": k1_star,
                                "mu_star": mu_star},
                "numeric_minimax": {"mu": mu_n, "k1": k1_n, "rho_step": rho_n},
                "op_point": {"mu": mu_op, "k1": k1_op, "rho_step": rho_op,
                             "rho_3step": rho_op ** 3,
                             "rho_step_discreteBZ": rho_op_disc},
                "mu_plateau": [mu_pl_lo, mu_pl_hi], "mu_stab_max": mu_stab,
                "static_carrier_ablation": {
                    "rho_at_op": rho_static_op,
                    "best": {"mu": best_static[0], "k1": best_static[1],
                             "rho_step": best_static[2]}}},
        "robustness": {"scale_rows": scale_rows, "s_limit": s_lim,
                       "stiffness_rows": stiff_rows, "f_limit": f_lim,
                       "f_limit_z4c_mu_low": f_lim_z4c_low,
                       "k1_rows": k1_rows,
                       "k1_beats_cheb_range": [k1_ok_lo, k1_ok_hi]},
        "exact_perk": {"worst_3step": worst, "transient_amp": amp},
        "dynamics": dyn_rows,
        "accounting": {"n_unit_modes": n_unit, "n_unit_modes_gamma": n_unit_g,
                       "unit_mode_Z_component_max": zc,
                       "z_sector_eig_mod_max": zmix_max,
                       "z_sector_pred": math.sqrt(1 - k1_op),
                       "kerJ_nonTT_riemann_max": riem_nonTT},
        "cost": ops,
        "verdict": {"z4c_beats_cheb_rate": bool(z4c_wins_rate),
                    "z4c_wider_stability": bool(z4c_wider),
                    "all_pass": all_pass,
                    "recommendation": ("Z4c 有资格进 M1 装配(条件:Z 载波与"
                                       "物质 walk 共锥;N_prop 扣 Z 扇区;装配层"
                                       "重测 sigma^2 后按平台公式重定参)"
                                       if z4c_wins_rate else
                                       "现行方案够用,Z4c 不进装配")},
    }
    json.dump(out, open(os.path.join(DIR, "r22_results.json"), "w"), indent=1)
    print("wrote r22_results.json")

    # ------------------------------------------------------------- figure
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    ax = axes[0]
    s2p = np.linspace(a, b, 600)
    ax.plot(s2p, rho_gamma(g_opt, s2p) ** 3, label="single gamma*", lw=2)
    ax.plot(s2p, rho_cheb_cycle(cheb, s2p), label="Chebyshev-3 cycle", lw=2)
    ax.plot(s2p, z4c_eig_moduli(mu_op, k1_op, s2p) ** 3, label="Z4c (op)", lw=2)
    ax.axhline(rc_3, color="gray", ls=":", lw=1)
    ax.set_xlabel(r"$\sigma^2$"); ax.set_ylabel("contraction / 3 steps")
    ax.set_title("per-mode worst contraction"); ax.legend(); ax.set_ylim(0, 1.05)
    ax = axes[1]
    mus = np.linspace(0.02, 0.115, 140)
    k1s = np.linspace(0.3, 1.0, 140)
    Zr = np.array([[z4c_rho_worst(m, k1, np.linspace(a, b, 160))
                    for m in mus] for k1 in k1s])
    im = ax.pcolormesh(mus, k1s, np.minimum(Zr, 1.2), cmap="viridis",
                       shading="auto")
    ax.contour(mus, k1s, Zr, levels=[rc_1], colors="w", linewidths=1.5)
    ax.contour(mus, k1s, Zr, levels=[1.0], colors="r", linewidths=1.5)
    ax.plot([mu_op], [k1_op], "r*", ms=14)
    ax.set_xlabel(r"$\mu_z$"); ax.set_ylabel(r"$\kappa_1$")
    ax.set_title(r"Z4c worst $\rho$/step (white: Cheb equiv, red: stability)")
    fig.colorbar(im, ax=ax)
    ax = axes[2]
    fs = np.linspace(1.0, 1.3, 60)
    for sch, lab in (("gamma", "single gamma*"), ("cheb", "Chebyshev-3"),
                     ("z4c", "Z4c (op)")):
        ax.plot(fs, [min(worst_at_stiff(sch, f), 3) for f in fs], label=lab, lw=2)
    ax.axhline(1.0, color="r", ls="--", lw=1)
    ax.set_xlabel(r"true $\sigma^2_{max}$ / estimated"); ax.set_ylim(0, 2)
    ax.set_ylabel("worst contraction / 3 steps")
    ax.set_title("robustness to stiffness underestimate"); ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(DIR, "figs", "r22_z4c_damping.png"), dpi=140)
    print("wrote figs/r22_z4c_damping.png")
