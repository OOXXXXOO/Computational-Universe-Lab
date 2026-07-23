"""CP1-v4 装配阶梯 L2 预写:Z4c 型约束阻尼模块(车道B,2026-07-23)

【纪律】本文件是 L2 的**预写模块**,不跑 L2 的门(主线三b:L1 运行期间的
不越序任务)。自检只在 R16/R18/R22 的 in-vitro oracle(单 k、在壳、符号空间)
上运行;不 import、不读取、不运行 cp1_v4_L1*。

=========================== 给 L2 装配者的交接段 ===========================

用法:

    from cp1_v4_damping import (spectral_calibrate, ConstraintOp,
                                make_z4c_stepper, z4c_step,
                                z_sector_certificate, placement_gate,
                                rate_gate, z4c_block_moduli)

    # 1) 定参 —— 装配层必须重算,禁抄 R22/本自检的任何数字(R22 §七.2):
    Ks  = [probe_K(k) for k in bz_samples]     # 实装 K_placed 逐 k probe 出矩阵
    cal = spectral_calibrate(Ks)               # -> mu_z, kappa1(平台闭式+裕量)

    # 2) 步进(次序焊死 walk -> 测 C -> 同步阻尼;enforce≡measure 同一 Kop):
    Kop  = ConstraintOp(apply_fn, adjoint_fn)  # 或 ConstraintOp.from_matrix(K)
    step = make_z4c_stepper(walk, carrier, Kop, cal["mu_z"], cal["kappa1"],
                            probe_chi=chi_example)   # 构造时强制 probe 断言
    chi, Z = step(chi, Z)                      # 纯函数;签名里没有任何历史态

    # 3) N_prop 记账(逐 k 谱证书,Z 扇区显式扣除,R22 §五):
    cert = z_sector_certificate(K_at_k, omega_k, cal["mu_z"], cal["kappa1"])

装配层必须自己重算 / 自己提供的(本模块不携带任何默认物理数字):

  * σ² 谱:实装 K_placed 在装配格点 BZ 采样 probe 出矩阵喂 spectral_calibrate;
    (mu_z, kappa1) 全部由传入的 K 算出(margin 默认 4%,R22 §七.2 的 3–5% 带内);
    要刚度余量取 mu_choice="low"(平台低端,收缩率不变、f_max 变大,R22 §四)。
  * walk 与 carrier:carrier 必须用与物质**相同的 walk 核**作用于 Z 的每个分量
    (共动硬要求 = 证伪炮第 8 件;静止载波在本文件负控中复现 rho>1 不稳,
    R22 §二消融)。载波用 walker 实现时取正频支(负频支=反向相位=失败方向)。
  * 场布局(R19 存储语义):chi = 10 个 SYM 分量沿 axis 0,OFFSET 交错存储与
    h_bar_00 fwd / h_bar_0i bwd 的时间配对**都在 K_placed 里**,不在本模块——
    模块对布局透明,只要求 chi/Z 支持 ndarray 算术(分量打包在首轴);
    Z = 4 分量沿 axis 0,存放在 C_nu 行的**落点**上(R19 配对约定:C_i 落整数
    t、C_0 落 t+1/2),零插值。
  * 回退路径:kappa1=1 精确退化为单 gamma(gamma=mu_z);cal["gamma_fallback"]
    给出单 gamma 最优值,调试期可随时切换(R22 §七.4)。

红线(R20 三 bug;本文件自检对三种病各自注入并验证"能检出"):

  * 无 hprev:z4c_step 签名不收历史态(结构性退役);若装配层自己缓存 stale
    场喂 K,rate_gate(实测率 vs 谱预言)检出——率对不上=有滞后/时间槽病
    (R16-D2 / R20 处方 1);
  * 折返写全复数:禁止只写 Re;rate_gate 检出(实测率退化到 ~0.96 级);
  * 时间槽:placement_gate 直查 |K@TT|≈0 且 |K@gauge|≈0(在壳),不许只数
    dim(主线通用工程条款);实空间雅可比压规范属预期(R18 H3),用
    expect_gauge_zero=False 记录、不算 DOF 丢失;
  * enforce≡measure:ConstraintOp 单实例承载测量与折返,probe_adjoint_assert
    在 make_z4c_stepper 构造时强制跑(R20 处方 3 的 probe 模板)。

L2 过门判据与本模块的对应:约束到机器底且尾段率区分地板 vs 慢衰减 ->
rate_gate(tail_rate);TT 保持 =1 -> 自检 dynamics 行;N_prop 显式扣 Z 扇区 ->
z_sector_certificate(单位模计数 + 单位模 Z 含量机器零 + Z 扇区收缩半径断言)。

自检:python cp1_v4_damping.py   (分钟级;写 cp1_v4_damping_selftest.json;
      需要 repo 根目录的 r15/r17/r18 oracle 文件,可选对拍 r22_results.json)
"""
import json
import math
import os

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 24
DEFAULT_MARGIN = 0.04          # b 上浮裕量,R22 §七.2 的 3–5% 带内(方法常数)

__all__ = ["spectral_calibrate", "ConstraintOp", "probe_adjoint_assert",
           "z4c_step", "make_z4c_stepper", "z4c_augmented_matrix",
           "z4c_block_moduli", "z_sector_certificate", "placement_gate",
           "rate_gate", "run_selftest"]


# ============================================================= 1. 定参(闭式)
def _collect_sigma2(K, tol=1e-12):
    """K: 若为 1-D 数组 = 实测 sigma^2 列表;否则视为可迭代的约束矩阵,
    逐个 SVD 收集非零 sigma^2。"""
    if isinstance(K, np.ndarray) and K.ndim == 1:
        s2 = np.asarray(K, dtype=float)
    else:
        parts = []
        for M in K:
            M = np.asarray(M)
            if M.ndim == 1:
                parts.append(np.asarray(M, dtype=float))
            else:
                parts.append(np.linalg.svd(M, compute_uv=False) ** 2)
        if not parts:
            raise ValueError("spectral_calibrate: 空的 K 列表")
        s2 = np.concatenate(parts)
    s2 = s2[s2 > tol]
    if s2.size == 0:
        raise ValueError("spectral_calibrate: 没有非零 sigma^2(K 全零?)")
    return s2


def spectral_calibrate(K, margin=DEFAULT_MARGIN, mu_choice="mid"):
    """R22 §七.2 平台闭式定参。数字全部由传入的 K(装配层实测约束雅可比 /
    实测 sigma^2 谱)算出——不携带、不默认任何 R22 数字。

    K         : 约束矩阵列表(装配层逐 k probe 出的矩阵)或 1-D sigma^2 数组
    margin    : b 相对闭式最优 (sqrt(kap)-1)/(sqrt(kap)+1) 的上浮裕量(3–5%)
    mu_choice : "mid" 取平台中点;"low" 取平台低端(白拿刚度余量,收缩率不变)

    返回 dict:mu_z, kappa1, rho_step_pred(=b,平台内全 BZ 一致)、
    mu_plateau、mu_stab_max、sigma2_min/max、kappa_cond、beta_star、
    gamma_fallback(kappa1=1 回退的单 gamma 最优值)。
    """
    s2 = _collect_sigma2(K)
    a, b_max = float(s2.min()), float(s2.max())
    kap = b_max / a
    beta_star = (math.sqrt(kap) - 1.0) / (math.sqrt(kap) + 1.0)
    b = max(beta_star * (1.0 + margin), margin)     # 裕量;kap=1 时给最小窗
    if not (0.0 < b < 1.0):
        raise ValueError(f"spectral_calibrate: 收缩目标 b={b:.4f} 不在 (0,1)")
    kappa1 = 1.0 - b * b
    mu_lo = (1.0 - b) ** 2 / a
    mu_hi = (1.0 + b) ** 2 / b_max
    if mu_lo > mu_hi:
        raise ValueError("spectral_calibrate: mu 平台为空——margin 太小或谱病态")
    mu_z = {"mid": 0.5 * (mu_lo + mu_hi), "low": mu_lo * 1.02}[mu_choice]
    mu_stab = 2.0 * (2.0 - kappa1) / b_max          # Jury 稳定上界
    assert mu_z < mu_stab, "spectral_calibrate: mu_z 超 Jury 稳定上界(不应发生)"
    # 平台自洽断言:平台内每个模每步收缩恰为 b(det M = 1-kappa1 恒等式)
    s2_dense = np.linspace(a, b_max, 2048)
    mods = z4c_block_moduli(mu_z, kappa1, s2_dense)
    assert abs(float(mods.max()) - b) < 1e-9 and abs(float(mods.min()) - b) < 1e-9, \
        "spectral_calibrate: 平台平坦性自洽断言失败"
    return {"mu_z": float(mu_z), "kappa1": float(kappa1),
            "rho_step_pred": float(b), "beta_star": float(beta_star),
            "margin": float(margin), "mu_choice": mu_choice,
            "mu_plateau": [float(mu_lo), float(mu_hi)],
            "mu_stab_max": float(mu_stab),
            "sigma2_min": a, "sigma2_max": b_max, "kappa_cond": float(kap),
            "n_sigma2": int(s2.size),
            "gamma_fallback": float(2.0 / (a + b_max))}


def z4c_block_moduli(mu_z, kappa1, s2, phase=None):
    """Z4c 2x2 奇异方向块的特征值模长(R22 §二闭式,向量化;诊断用)。
    phase=None: 共动载波(实矩阵,模长与 omega 无关);
    phase=omega 数组: 静止载波消融(证伪炮第 8 件的谱侧)。"""
    s2 = np.asarray(s2, dtype=float)
    s = np.sqrt(s2)
    if phase is None:
        tr = (2.0 - kappa1 - mu_z * s2).astype(complex)
        det = np.full_like(tr, 1.0 - kappa1)
    else:
        ph = np.exp(-1j * np.asarray(phase))
        tr = ph * (1.0 - mu_z * s2) + (1.0 - kappa1)
        det = ph * (1.0 - kappa1) * np.ones_like(s2)
    sq = np.sqrt(tr * tr - 4.0 * det)
    l1, l2 = 0.5 * (tr + sq), 0.5 * (tr - sq)
    return np.maximum(np.abs(l1), np.abs(l2))


# ============================================== 2. enforce≡measure 载体 + 步进
class ConstraintOp:
    """约束算子载体:测量(apply)与折返(adjoint)必须共用**同一实例**——
    这是 R20 处方 3 "enforce == measure 同函数" 的接口化。装配层不许分别
    构造两个算子再各喂一半;probe_adjoint_assert 会抓出伴随不匹配。"""

    def __init__(self, apply_fn, adjoint_fn, name="K"):
        self._apply = apply_fn
        self._adjoint = adjoint_fn
        self.name = name

    def apply(self, chi):
        return self._apply(chi)

    def adjoint(self, C):
        return self._adjoint(C)

    @classmethod
    def from_matrix(cls, K):
        K = np.asarray(K)
        Kd = K.conj().T
        return cls(lambda x: K @ x, lambda C: Kd @ C, name="matrix")


def probe_adjoint_assert(Kop, chi_example, n_probe=6, rtol=1e-10, rng=None):
    """probe 断言(构造期强制):
    (i) 伴随一致性 <u, K v> == <K^dag u, v>(随机复 probe)——伴随若来自
        另一个算子(R18 H4 非对称执行 / R20 嫌疑 2)在这里被抓;
    (ii) 纯函数性:同输入两次调用逐位相同(有内部状态/hprev 的实现被抓)。"""
    rng = np.random.default_rng(0) if rng is None else rng
    chi_example = np.asarray(chi_example, dtype=complex)
    C0 = np.asarray(Kop.apply(chi_example), dtype=complex)
    worst = 0.0
    for _ in range(n_probe):
        v = rng.normal(size=chi_example.shape) + 1j * rng.normal(size=chi_example.shape)
        u = rng.normal(size=C0.shape) + 1j * rng.normal(size=C0.shape)
        Kv = np.asarray(Kop.apply(v), dtype=complex)
        Ku = np.asarray(Kop.adjoint(u), dtype=complex)
        lhs = np.vdot(u, Kv)
        rhs = np.vdot(Ku, v)
        scale = max(1.0, np.linalg.norm(u.ravel()) * np.linalg.norm(Kv.ravel()))
        worst = max(worst, abs(lhs - rhs) / scale)
    assert worst < rtol, (f"probe_adjoint_assert: enforce != measure "
                          f"(伴随失配 {worst:.2e} >= {rtol:.0e})")
    y1 = np.asarray(Kop.apply(chi_example))
    y2 = np.asarray(Kop.apply(chi_example))
    assert np.array_equal(y1, y2), "probe_adjoint_assert: K 非纯函数(内部状态?)"
    return {"adjoint_mismatch_max": float(worst), "pure": True}


def z4c_step(chi, Z, walk, carrier, Kop, mu_z, kappa1):
    """一个宏步的 Z4c 阻尼(R22 §二离散化;次序焊死 = R18 处方 4):

        chi_w = walk(chi)                      # 物质/度规场 walk
        Z_c   = carrier(Z)                     # Z 共动载波(同一 walk 核!)
        C     = Kop.apply(chi_w)               # 测约束(measure)
        Z'    = (1-kappa1) Z_c + C             # 衰减 + 源(同步,无滞后)
        chi'  = chi_w - mu_z Kop.adjoint(Z')   # 梯度折返(enforce,同一 Kop)

    纯函数:无 in-place 写、无历史态(hprev 结构性退役);折返写全复数
    (禁止只写 Re——见模块红线与自检回归)。kappa1=1 时精确退化为单 gamma。"""
    chi_w = walk(chi)
    Z_c = carrier(Z)
    C = Kop.apply(chi_w)
    Z_new = (1.0 - kappa1) * Z_c + C
    chi_new = chi_w - mu_z * Kop.adjoint(Z_new)
    return chi_new, Z_new


def make_z4c_stepper(walk, carrier, Kop, mu_z, kappa1, probe_chi=None, rng=None):
    """闭包工厂:参数校验 + (若给 probe_chi)构造期强制 probe 断言,返回
    纯函数 step(chi, Z) -> (chi, Z)。装配层应总是提供 probe_chi。"""
    if not (0.0 < kappa1 <= 1.0):
        raise ValueError(f"kappa1={kappa1} 不在 (0,1](=1 为单 gamma 回退)")
    if mu_z <= 0.0:
        raise ValueError(f"mu_z={mu_z} 必须为正")
    if not isinstance(Kop, ConstraintOp):
        raise TypeError("Kop 必须是 ConstraintOp——enforce≡measure 单实例纪律")
    report = None
    if probe_chi is not None:
        report = probe_adjoint_assert(Kop, probe_chi, rng=rng)

    def step(chi, Z):
        return z4c_step(chi, Z, walk, carrier, Kop, mu_z, kappa1)

    step.probe_report = report
    step.params = {"mu_z": float(mu_z), "kappa1": float(kappa1)}
    return step


# ==================================================== 3. Z 扇区记账(谱证书)
def z4c_augmented_matrix(K, omega, mu_z, kappa1, comoving=True):
    """单 k 增广步算子 ((n+m)x(n+m)),n=chi 维、m=Z 维。comoving=False 给
    静止载波消融(负控/证伪炮第 8 件)。"""
    K = np.asarray(K, dtype=complex)
    m, n = K.shape
    Kd = K.conj().T
    ph = np.exp(-1j * omega)
    A = np.zeros((n + m, n + m), dtype=complex)
    A[:n, :n] = ph * (np.eye(n) - mu_z * (Kd @ K))
    A[n:, :n] = ph * K
    if comoving:
        A[:n, n:] = -mu_z * (1.0 - kappa1) * ph * Kd
        A[n:, n:] = (1.0 - kappa1) * ph * np.eye(m)
    else:
        A[:n, n:] = -mu_z * (1.0 - kappa1) * Kd
        A[n:, n:] = (1.0 - kappa1) * np.eye(m)
    return A


def z_sector_certificate(K, omega, mu_z, kappa1, unit_tol=1e-9, z_tol=1e-10):
    """Z 扇区记账谱证书(R22 §五;主线 L2 门的 N_prop 扣除件)。逐 k 验证:
      (1) 单位模模式数 == dim ker K(全部属于 chi 扇区,与单 gamma 方案相同);
      (2) 单位模特征向量的 Z 分量为机器零(单位模圆上没有任何 Z 含量);
      (3) 其余(Z 混合扇区)谱半径 == sqrt(1-kappa1) < 1(严格收缩,瞬态存在
          渐近为零,不得计入任何 N_prop 类计数)。
    观测量纪律(证书之外、装配层执行):Riemann 能量 / T00 / 涌现判据只读
    chi;Z 不进任何观测量。"""
    K = np.asarray(K, dtype=complex)
    m, n = K.shape
    s = np.linalg.svd(K, compute_uv=False)
    rank = int(np.sum(s > 1e-10 * max(float(s[0]), 1e-300)))
    dim_ker = n - rank
    A = z4c_augmented_matrix(K, omega, mu_z, kappa1, comoving=True)
    lam, vec = np.linalg.eig(A)
    mod = np.abs(lam)
    unit = mod > 1.0 - unit_tol
    n_unit = int(unit.sum())
    zc = 0.0
    for i in range(n + m):
        if unit[i]:
            zc = max(zc, float(np.linalg.norm(vec[n:, i])))
    nonunit = mod[~unit]
    zrad = float(nonunit.max()) if nonunit.size else 0.0
    zpred = math.sqrt(max(0.0, 1.0 - kappa1))
    ok = (n_unit == dim_ker and zc < z_tol
          and (kappa1 >= 1.0 - 1e-12 or abs(zrad - zpred) < 1e-6))
    return {"n_unit_modes": n_unit, "dim_kerK": dim_ker,
            "n_contracting": int((~unit).sum()),
            "unit_mode_Z_component_max": float(zc),
            "z_sector_radius": zrad, "z_sector_radius_pred": float(zpred),
            "note": "N_prop 只在 chi 扇区的单位模里数;"
                    f"{int((~unit).sum())} 个收缩模(含 Z 扇区)不得计入",
            "pass": bool(ok)}


# ======================================================== 4. 装配层自检门件
def placement_gate(K, TT_basis, gauge_basis, tol=1e-10, expect_gauge_zero=True):
    """主线通用条款:直查 |K@TT| 与 |K@gauge|,不许只数 dim。
    在壳 oracle meter:两项都必须机器零;实空间雅可比:TT 必须机器零,
    规范被压属预期(R18 H3)——用 expect_gauge_zero=False 记录口径。"""
    K = np.asarray(K, dtype=complex)
    ttr = float(np.abs(K @ TT_basis).max())
    gr = float(np.abs(K @ gauge_basis).max())
    tt_ok = ttr < tol
    g_ok = (gr < tol) if expect_gauge_zero else True
    return {"K_at_TT": ttr, "K_at_gauge": gr, "tt_ok": bool(tt_ok),
            "gauge_ok": bool(g_ok), "expect_gauge_zero": bool(expect_gauge_zero),
            "pass": bool(tt_ok and g_ok)}


def rate_gate(cn, rho_pred, window=(6, 42), tol=0.03, floor_rel=1e-13,
              tail_len=8, tail_thresh=0.995, stall_level=1e-10):
    """实测收缩率 vs 谱预言 + 尾段率(R16-D2 装配 bug 定位器;R20 处方 5.ii
    "地板 vs 慢衰减必须用尾段率区分")。
    cn: 约束范数序列(逐宏步);rho_pred: 谱预言(每步)。
    判定:floored(到机器底)或 |实测-预言|<tol 且 未 stall。
    stalled = 尾段率 ~1 且水平远高于机器底(真地板/不稳,均 FAIL)。"""
    cn = np.asarray(cn, dtype=float)
    t0, t1 = window
    c0 = cn[0]
    floored = bool(cn[t1] < floor_rel * c0 or cn[t0] < floor_rel * c0)
    meas = None if floored else float((cn[t1] / cn[t0]) ** (1.0 / (t1 - t0)))
    tail = (float((cn[-1] / cn[-1 - tail_len]) ** (1.0 / tail_len))
            if cn[-1 - tail_len] > 0 else 0.0)
    stalled = bool(cn[-1] / c0 > stall_level and tail > tail_thresh)
    rate_ok = floored or (meas is not None and abs(meas - rho_pred) < tol)
    return {"rate_meas": meas, "rate_pred": float(rho_pred),
            "floored": floored, "tail_rate": float(tail), "stalled": stalled,
            "final_over_initial": float(cn[-1] / c0),
            "ok": bool(rate_ok and not stalled)}


# ================================================================ 5. 自检套件
def _bz_grid(n=16):
    """R18/R22 的同一 BZ 采样(16^3 可分辨模,正八分体,去零模)。"""
    kk = [2 * np.pi * np.array([a, b, d]) / n
          for a in range(0, n // 2) for b in range(0, n // 2)
          for d in range(0, n // 2)]
    return [k for k in kk if np.linalg.norm(k) > 1e-9]


def _evolve_symbol(K_run, K_judge, w, chi0, T, mu, k1, variant="normal"):
    """oracle 符号层动力学。variant="normal" 走模块 API(z4c_step);
    三种病态 variant 只能在这里手写注入——z4c_step 的签名结构上做不出
    这些病,这正是接口红线的意义:
      "hprev"          : 测 C 用上一宏步(已阻尼)的场(stale,R20 结论 1b)
      "refold_re"      : 折返只写 Re(R20 结论 1c)
      "static_carrier" : Z 载波不随 walk 共动(R22 消融/证伪炮第 8 件)"""
    K_run = np.asarray(K_run, dtype=complex)
    Kd = K_run.conj().T
    ph = np.exp(-1j * w)
    m = K_run.shape[0]
    cn = [float(np.linalg.norm(K_judge @ chi0))]
    if variant == "normal":
        Kop = ConstraintOp.from_matrix(K_run)
        step = make_z4c_stepper(lambda x: ph * x, lambda z: ph * z, Kop,
                                mu, k1, probe_chi=chi0)
        chi = chi0.astype(complex)
        Z = np.zeros(m, dtype=complex)
        for _ in range(T):
            chi, Z = step(chi, Z)
            cn.append(float(np.linalg.norm(K_judge @ chi)))
        return np.array(cn), chi
    chi = chi0.astype(complex)
    Z = np.zeros(m, dtype=complex)
    for _ in range(T):
        prev = chi                                     # 上一宏步输出
        chi_w = ph * chi
        Z_c = Z if variant == "static_carrier" else ph * Z
        src = prev if variant == "hprev" else chi_w    # 病:stale 场喂 K
        Z = (1.0 - k1) * Z_c + K_run @ src
        corr = mu * (Kd @ Z)
        if variant == "refold_re":
            corr = corr.real.astype(complex)           # 病:折返只写 Re
        chi = chi_w - corr
        cn.append(float(np.linalg.norm(K_judge @ chi)))
    return np.array(cn), chi


def _mixed_seed(TT, G, junk_basis, rng):
    """在壳混合初条(R16 更正栏纪律):TT + gauge + 0.5 * 行空间 junk。"""
    cTT = TT @ (rng.normal(size=TT.shape[1]) + 1j * rng.normal(size=TT.shape[1]))
    cG = G @ (rng.normal(size=G.shape[1]) + 1j * rng.normal(size=G.shape[1]))
    nj = junk_basis.shape[1]
    junk = junk_basis @ (rng.normal(size=nj) + 1j * rng.normal(size=nj))
    return cTT + cG + 0.5 * junk


def run_selftest(write_json=True, verbose=True):
    """自检(在 R16/R18/R22 oracle 上;不是 L2 的门):
      A 定参 + 对拍 r22 收缩率预言(谱 + 动力学 + r22_results.json 交叉);
      B R20 三 bug 回归断言(注入三种病,各自必须被检出;健康路径必须无假警);
      C 静止载波负控(必须不稳/劣于单 gamma,复现 R22 消融);
      D Z 扇区谱证书。"""
    from r15_walk_dedonder import (shell_omega, kappa_placed, constraint_matrix,
                                   gauge_block, tt_basis)
    from r18_realspace_damping import jacobian_C

    rng = np.random.default_rng(SEED)
    out = {"meta": {"seed": SEED, "module": "cp1_v4_damping",
                    "oracle": "R16/R18/R22 in-vitro(单 k、在壳、符号空间)",
                    "discipline": "预写自检,不跑 L2 门,不触 cp1_v4_L1*"}}
    P = print if verbose else (lambda *a, **k: None)
    P("CP1-v4 L2 预写:Z4c 阻尼模块自检(oracle 台架,非 L2 门)")
    P("=" * 72)

    # ---------------- A. 定参 + 对拍 r22 --------------------------------
    kk = _bz_grid(16)
    Js, ws_per_s2 = [], []
    for k in kk:
        J = jacobian_C(k)
        Js.append(J)
        s2 = np.linalg.svd(J, compute_uv=False) ** 2
        ws_per_s2.append(np.full(int((s2 > 1e-12).sum()), shell_omega(k)))
    cal = spectral_calibrate(Js)
    s2_all = _collect_sigma2(Js)
    ws_all = np.concatenate(ws_per_s2)
    a, b_max = cal["sigma2_min"], cal["sigma2_max"]
    mu_op, k1_op, b_op = cal["mu_z"], cal["kappa1"], cal["rho_step_pred"]
    # 参考方案(同谱重算,不抄数字)
    g_opt = cal["gamma_fallback"]
    s2_lin = np.linspace(a, b_max, 2000)
    r1 = float(np.abs(1.0 - g_opt * s2_lin).max())
    cheb = [2.0 / (a + b_max - (b_max - a) * math.cos((2 * j + 1) * math.pi / 6.0))
            for j in range(3)]
    rc3 = float(max(abs(np.prod([1 - g * s for g in cheb])) for s in s2_lin))
    rho_disc = float(z4c_block_moduli(mu_op, k1_op, s2_all).max())
    P(f"[A] 定参(由 {len(kk)} 个 k 的 J 谱算出): sigma^2=[{a:.4f},{b_max:.4f}] "
      f"kap={cal['kappa_cond']:.2f}")
    P(f"    mu_z={mu_op:.4f}  kappa1={k1_op:.4f}  rho_pred={b_op:.4f}/步 "
      f"(平台 [{cal['mu_plateau'][0]:.4f},{cal['mu_plateau'][1]:.4f}], "
      f"稳定上界 {cal['mu_stab_max']:.4f}, gamma 回退 {g_opt:.4f})")
    P(f"    参考: 单 gamma {r1:.4f}/步 ({r1**3:.4f}/3步)  Chebyshev {rc3:.4f}/3步"
      f"  Z4c {b_op**3:.4f}/3步  离散 BZ 实测最坏 {rho_disc:.4f}/步")
    beats = bool(b_op ** 3 < rc3 - 1e-3 and abs(rho_disc - b_op) < 1e-9)
    out["calibration"] = dict(cal)
    out["calibration"]["reference"] = {"gamma_rate_step": r1, "cheb_gammas": cheb,
                                       "cheb_rate_3step": rc3,
                                       "rho_discreteBZ": rho_disc}
    # r22_results.json 交叉对拍(若在)
    r22_path = os.path.join(DIR, "r22_results.json")
    xc = {"skipped": not os.path.exists(r22_path)}
    if not xc["skipped"]:
        r22 = json.load(open(r22_path))
        op = r22["z4c"]["op_point"]
        xc.update({
            "sigma2_delta": [abs(a - r22["baseline"]["sigma2_range"][0]),
                             abs(b_max - r22["baseline"]["sigma2_range"][1])],
            "mu_delta": abs(mu_op - op["mu"]), "k1_delta": abs(k1_op - op["k1"]),
            "rho_delta": abs(b_op - op["rho_step"]),
            "r22_op": {"mu": op["mu"], "k1": op["k1"], "rho": op["rho_step"]}})
        xc["ok"] = bool(max(xc["sigma2_delta"]) < 2e-3 and xc["mu_delta"] < 2e-3
                        and xc["k1_delta"] < 1e-2 and xc["rho_delta"] < 5e-3)
        P(f"    r22 交叉: |Δmu|={xc['mu_delta']:.1e} |Δk1|={xc['k1_delta']:.1e} "
          f"|Δrho|={xc['rho_delta']:.1e} -> {'PASS' if xc['ok'] else 'FAIL'}")
    else:
        P("    r22_results.json 不在,交叉对拍跳过")
    out["r22_crosscheck"] = xc
    xc_ok = xc.get("ok", True)

    # 动力学对拍(R16 的三个 k,在壳混合初条)
    kvecs = [np.array([0.5, 0.0, 0.0]), np.array([0.35, 0.35, 0.35]),
             np.array([0.7, 0.2, -0.4])]
    T = 240
    dyn_rows, dyn_ok = [], True
    for kx in kvecs:
        w = shell_omega(kx)
        J = jacobian_C(kx)
        kap = kappa_placed(kx)
        TT, G = tt_basis(kap), gauge_block(kap)
        U, S, Vh = np.linalg.svd(J)
        V4 = Vh[:4].conj().T
        chi0 = _mixed_seed(TT, G, V4, rng)
        cn, chi_f = _evolve_symbol(J, J, w, chi0, T, mu_op, k1_op, "normal")
        s2k = S[S ** 2 > 1e-12] ** 2
        pred = float(z4c_block_moduli(mu_op, k1_op, s2k).max())
        gate = rate_gate(cn, pred)
        tt0 = np.linalg.norm(TT.conj().T @ chi0)
        tt_err = float(abs(np.linalg.norm(TT.conj().T @ chi_f) / tt0 - 1.0))
        ok = bool(gate["ok"] and tt_err < 1e-12)
        dyn_ok &= ok
        dyn_rows.append({"k": kx.tolist(), "omega": float(w), "gate": gate,
                         "tt_err": tt_err, "ok": ok})
        P(f"    动力学 k={np.round(kx, 2)}: 实测 "
          f"{gate['rate_meas'] if gate['rate_meas'] is None else round(gate['rate_meas'], 4)}"
          f" vs 预言 {pred:.4f} | TT保真 |Δ|={tt_err:.1e} | "
          f"{'PASS' if ok else 'FAIL'}")
    out["dynamics"] = dyn_rows
    A_ok = bool(beats and xc_ok and dyn_ok)
    P(f"    [A 小结] 谱+动力学+交叉对拍: {'PASS' if A_ok else 'FAIL'}")

    # ---------------- B. R20 三 bug 回归断言 -----------------------------
    P(f"\n[B] R20 三 bug 回归(注入必须被检出;健康路径必须无假警):")
    kx = kvecs[2]
    w = shell_omega(kx)
    kap = kappa_placed(kx)
    Kc = constraint_matrix(kap)
    TT, G = tt_basis(kap), gauge_block(kap)
    reg = {}

    # (b1) 时间槽错:kappa_0 残留半相位 e^{-i w/2}(R19:错放置=数据里少了
    # 被吸收的半相位;R20:h00 槽 fwd/bwd 用错 -> Delta K_00 = O(0.4))
    pg_base = placement_gate(Kc, TT, G, expect_gauge_zero=True)
    kb = kap.astype(complex)
    kb[0] *= np.exp(-1j * w / 2.0)
    Kb = constraint_matrix(kb)
    pg_bug = placement_gate(Kb, TT, G, expect_gauge_zero=True)
    cal_b = spectral_calibrate([Kb])
    chi0 = _mixed_seed(TT, G, np.linalg.svd(Kb)[2][:4].conj().T, rng)
    cn_b, _ = _evolve_symbol(Kb, Kc, w, chi0, T, cal_b["mu_z"], cal_b["kappa1"])
    gate_b = rate_gate(cn_b, cal_b["rho_step_pred"])
    # 健康对照:certified 算子自身,同一门必须全绿
    cal_c = spectral_calibrate([Kc])
    chi0c = _mixed_seed(TT, G, np.linalg.svd(Kc)[2][:4].conj().T, rng)
    cn_c, _ = _evolve_symbol(Kc, Kc, w, chi0c, T, cal_c["mu_z"], cal_c["kappa1"])
    gate_c = rate_gate(cn_c, cal_c["rho_step_pred"])
    det1_static = not pg_bug["pass"]
    det1_dyn = not gate_b["ok"]
    reg["timeslot"] = {"baseline_gate": pg_base, "bug_gate": pg_bug,
                       "bug_dyn_gate": gate_b, "healthy_dyn_gate": gate_c,
                       "detected_static": det1_static, "detected_dyn": det1_dyn,
                       "no_false_alarm": bool(pg_base["pass"] and gate_c["ok"]),
                       "detected": bool(det1_static or det1_dyn)}
    P(f"    (1) 时间槽错: |K@gauge| {pg_base['K_at_gauge']:.1e} -> "
      f"{pg_bug['K_at_gauge']:.3f}; certified-meter 残留 "
      f"{gate_b['final_over_initial']:.2e} (尾段率 {gate_b['tail_rate']:.4f}) | "
      f"静态检出 {det1_static} 动态检出 {det1_dyn} 假警 "
      f"{not reg['timeslot']['no_false_alarm']}")

    # (b2) hprev 滞后:测 C 用上一宏步(stale)场
    kx2 = kvecs[2]
    J = jacobian_C(kx2)
    S2k = np.linalg.svd(J, compute_uv=False) ** 2
    s2k = S2k[S2k > 1e-12]
    pred_k = float(z4c_block_moduli(mu_op, k1_op, s2k).max())
    kapv = kappa_placed(kx2)
    TTv, Gv = tt_basis(kapv), gauge_block(kapv)
    V4 = np.linalg.svd(J)[2][:4].conj().T
    chi0 = _mixed_seed(TTv, Gv, V4, rng)
    cn_h, _ = _evolve_symbol(J, J, shell_omega(kx2), chi0, T, mu_op, k1_op,
                             "hprev")
    gate_h = rate_gate(cn_h, pred_k)
    healthy_ref = dyn_rows[2]["gate"]
    reg["hprev"] = {"bug_gate": gate_h, "healthy_gate": healthy_ref,
                    "detected": not gate_h["ok"],
                    "no_false_alarm": bool(healthy_ref["ok"])}
    P(f"    (2) hprev 滞后: 实测率 "
      f"{gate_h['rate_meas'] if gate_h['rate_meas'] is None else round(gate_h['rate_meas'], 4)}"
      f" vs 预言 {pred_k:.4f}, 尾段率 {gate_h['tail_rate']:.4f}, "
      f"末值/初值 {gate_h['final_over_initial']:.2e} | 检出 {not gate_h['ok']}")

    # (b3) 折返只写 Re
    chi0 = _mixed_seed(TTv, Gv, V4, rng)
    cn_r, chi_r = _evolve_symbol(J, J, shell_omega(kx2), chi0, T, mu_op, k1_op,
                                 "refold_re")
    gate_r = rate_gate(cn_r, pred_k)
    tt0 = np.linalg.norm(TTv.conj().T @ chi0)
    tt_err_r = float(abs(np.linalg.norm(TTv.conj().T @ chi_r) / tt0 - 1.0))
    reg["refold_re"] = {"bug_gate": gate_r, "tt_err": tt_err_r,
                        "detected": not gate_r["ok"],
                        "no_false_alarm": bool(healthy_ref["ok"])}
    P(f"    (3) 折返只写 Re: 实测率 "
      f"{gate_r['rate_meas'] if gate_r['rate_meas'] is None else round(gate_r['rate_meas'], 4)}"
      f" vs 预言 {pred_k:.4f} (TT|Δ|={tt_err_r:.1e} -> 只有率门能抓它) | "
      f"检出 {not gate_r['ok']}")

    # (b4) 附加:enforce != measure 的 probe 牙(R18 H4 / R20 嫌疑 2)
    J_spatial = jacobian_C(kx2, time_coeff=False)
    Kop_bad = ConstraintOp(lambda x: J @ x,
                           lambda C: J_spatial.conj().T @ C, name="mismatched")
    try:
        probe_adjoint_assert(Kop_bad, chi0)
        probe_teeth = False
    except AssertionError:
        probe_teeth = True
    reg["probe_mismatch"] = {"detected": probe_teeth}
    P(f"    (附) enforce!=measure probe 牙: 检出 {probe_teeth}")
    B_ok = bool(reg["timeslot"]["detected"] and reg["timeslot"]["no_false_alarm"]
                and reg["hprev"]["detected"] and reg["hprev"]["no_false_alarm"]
                and reg["refold_re"]["detected"] and probe_teeth)
    out["regressions"] = reg
    P(f"    [B 小结] 三 bug 各自检出 + 无假警 + probe 牙: "
      f"{'PASS' if B_ok else 'FAIL'}")

    # ---------------- C. 静止载波负控(证伪炮第 8 件) --------------------
    P(f"\n[C] 静止载波负控(应不稳/劣于单 gamma,复现 R22 消融):")
    rho_static_op = float(z4c_block_moduli(mu_op, k1_op, s2_all,
                                           phase=ws_all).max())
    best_static = np.inf
    best_pt = (None, None)
    for k1 in np.linspace(0.05, 0.99, 40):
        mu_cap = min(0.12, 2.0 * (2.0 - k1) / b_max)
        for mu in np.linspace(0.005, mu_cap, 40):
            r = float(z4c_block_moduli(mu, k1, s2_all, phase=ws_all).max())
            if r < best_static:
                best_static, best_pt = r, (float(mu), float(k1))
    # 动力学负控在"谱侧最不稳的 k"上做(不稳模是逐 k 的,别的 k 可能稳)
    kw, rho_kw = None, 0.0
    for k in kk:
        Jk = jacobian_C(k)
        s2 = np.linalg.svd(Jk, compute_uv=False) ** 2
        s2 = s2[s2 > 1e-12]
        r = float(z4c_block_moduli(mu_op, k1_op, s2,
                                   phase=np.full(s2.size, shell_omega(k))).max())
        if r > rho_kw:
            kw, rho_kw = k, r
    Jw = jacobian_C(kw)
    kapw = kappa_placed(kw)
    V4w = np.linalg.svd(Jw)[2][:4].conj().T
    chi0 = _mixed_seed(tt_basis(kapw), gauge_block(kapw), V4w, rng)
    cn_s, _ = _evolve_symbol(Jw, Jw, shell_omega(kw), chi0, 80, mu_op, k1_op,
                             "static_carrier")
    growth = float(cn_s[-1] / cn_s[0])
    C_ok = bool(rho_static_op > 1.0 and best_static > 0.95 * r1
                and growth > 10.0)
    out["negative_control_static_carrier"] = {
        "rho_at_op": rho_static_op, "worst_k": kw.tolist(),
        "rho_at_worst_k": rho_kw, "dyn_growth_80steps": growth,
        "best_reopt": {"mu": best_pt[0], "k1": best_pt[1],
                       "rho_step": best_static},
        "single_gamma_rate": r1, "pass": C_ok}
    P(f"    工作点参数: 全 BZ rho={rho_static_op:.4f} (>1 不稳, 最不稳 "
      f"k={np.round(kw, 2)} rho={rho_kw:.4f}) | 该 k 80 步实测增长 "
      f"x{growth:.1e} | 重优化最好 {best_static:.4f}/步 vs 单 gamma {r1:.4f}"
      f" | {'PASS(负控成立)' if C_ok else 'FAIL'}")

    # ---------------- D. Z 扇区谱证书 ------------------------------------
    cert = z_sector_certificate(J, shell_omega(kx2), mu_op, k1_op)
    out["z_certificate"] = cert
    P(f"\n[D] Z 扇区证书 k={np.round(kx2, 2)}: 单位模 {cert['n_unit_modes']} "
      f"(= dim ker K = {cert['dim_kerK']}), 单位模 Z 含量 "
      f"{cert['unit_mode_Z_component_max']:.1e}, Z 扇区半径 "
      f"{cert['z_sector_radius']:.4f} = sqrt(1-kappa1) = "
      f"{cert['z_sector_radius_pred']:.4f} | "
      f"{'PASS' if cert['pass'] else 'FAIL'}")

    all_pass = bool(A_ok and B_ok and C_ok and cert["pass"])
    out["all_pass"] = all_pass
    P("\n" + "=" * 72)
    P(f"自检总判定: {'PASS' if all_pass else 'FAIL'}"
      f"  (A 对拍 {'P' if A_ok else 'F'} | B 三回归 {'P' if B_ok else 'F'} | "
      f"C 负控 {'P' if C_ok else 'F'} | D 证书 {'P' if cert['pass'] else 'F'})")
    if write_json:
        path = os.path.join(DIR, "cp1_v4_damping_selftest.json")
        json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
        P(f"wrote {os.path.basename(path)}")
    return out


if __name__ == "__main__":
    res = run_selftest()
    raise SystemExit(0 if res["all_pass"] else 1)
