"""rulespace_v2.spin1 -- M1' 自旋 1 实空间载体(M0' 评估器的自旋 1 扩展;新增文件)。

任务书 §1:"rulespace_v2/ 如需扩自旋 1 载体,只许加文件(如 spin1.py),不改 M0'
已冻结七件的任何一行"。本模块 = 该条款下的自旋 1 实空间机器:同一冻结 rule 在每个 L
上一条运行记录(无源波段 -> R26 清除段 -> 源段(对生/拖拽/静持/动源)-> 波包清除段),
全部门读数从该条记录(及其声明的反事实参考分叉)读出。

判据核继承(红线 3,核不重写;本模块中与冻结核并行的 L 参数化端口在主跑脚本内
对 L=16 做逐位控制行,diff 必须 == 0.0):
  * 谱线计数核 spectral_lines / 横向匹配 transverse_match:photon_control 冻结函数
    直接调用(L 无关,零端口);
  * evolve_record / mode_matrix / yee_oracle / solenoidal_project:photon_control
    冻结体的 L 参数化逐字端口(N -> L、TRIALS -> 推断;L=16 逐位对拍);
  * sponge 场:rulespace_gpu.tensor_coin_feedback._sponge_field 冻结函数直接调用
    (R36 part_C 同一 L4 sponge,gamma_max=0.30 R36 值);
  * 清除判据常数:r36_r3_verification 模块常数直接读取(CLEAR_THRESH/SPREAD_GATE/
    RET_GATE);
  * 不变量机器:rulespace_v2.invariants(M0' 整改产物,G8 j_inv 与 sigma 诊断)。

运行语义(写死):
  * "同一次运行" = 每 L 一条连续运行记录;所有注入(源电流、波包)是该记录内
    预注册事件;
  * 反事实参考分叉(ref1 源段 / ref2 动源段 / ref3 波包段)= 同一冻结 rule 从运行
    态复制后不加注入地演化,是评估器参考计算(与解析色散参考同地位),其唯一用途
    是线性精确的读出减法;线性叠加在 fp64 下的残差由无包对照 trial(6,7)实测入册;
  * 本模块不含任何判定阈值——全部门阈值在 experiments/v2m1_maxwell_loop.py 脚本头
    写死(红线 4)。
"""
from __future__ import annotations

import hashlib

import numpy as np

from . import frozen as FZ
from . import invariants as INV


# ==========================================================================
#  L 参数化基元(photon_control 逐字端口;L=16 逐位控制行在主跑脚本)
# ==========================================================================
def plane(kl, L):
    x = np.arange(L)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))


def kvec_of(nv, L):
    return np.array(nv, float) * (2.0 * np.pi / L)


def n_at_L(n16, L):
    """判据方向 n 随 L 重标(任务书 §3;实采 k 入册)。"""
    return [int(round(c * L / 16.0)) for c in n16]


def mode_matrix(kl, L, step, off6):
    """photon_control.mode_matrix 的 L 参数化逐字端口。"""
    PC = FZ.mod("photon_control")
    ph = plane(kl, L)
    proj = np.conj(ph) / L ** 3
    cf = PC.colfac(kl, off6)
    M = np.zeros((6, 6), complex)
    for c in range(6):
        E = np.zeros((3, L, L, L), complex)
        B = np.zeros((3, L, L, L), complex)
        if c < 3:
            E[c] = ph / cf[c]
        else:
            B[c - 3] = ph / cf[c]
        E2, B2 = step((E, B))
        amp = np.array([np.sum(proj * E2[j]) for j in range(3)]
                       + [np.sum(proj * B2[j]) for j in range(3)])
        M[:, c] = amp * cf
    return M


def yee_oracle(kl, L, step):
    """photon_control.yee_oracle 的 L 参数化逐字端口(候选 stepper 上探测)。"""
    PC = FZ.mod("photon_control")
    M = mode_matrix(kl, L, step, PC.OFF6)
    lam, V = np.linalg.eig(M)
    ang = np.angle(lam)
    w_ref = PC.yee_omega(kl)
    out = {"w_yee_analytic": w_ref}
    out["eig_absdev_max"] = float(np.abs(np.abs(lam) - 1.0).max())
    sel_p = np.where(np.abs(ang - w_ref * PC.DT) < 1e-6)[0]
    sel_m = np.where(np.abs(ang + w_ref * PC.DT) < 1e-6)[0]
    out["n_eig_plus"], out["n_eig_minus"] = len(sel_p), len(sel_m)
    out["w_op_vs_analytic"] = float(
        np.abs(np.abs(ang[sel_p]) / PC.DT - w_ref).max()) \
        if len(sel_p) else float("nan")
    cf = PC.colfac(kl, PC.OFF6)
    ph = plane(kl, L)
    worst_div = 0.0
    for j in list(sel_p) + list(sel_m):
        v = V[:, j]
        E = np.stack([(v[c] / cf[c]) * ph for c in range(3)])
        B = np.stack([(v[c + 3] / cf[c + 3]) * ph for c in range(3)])
        dE = float(np.abs(PC.div(E, PC._dm)).max()) / (np.abs(E).max() + 1e-300)
        dB = float(np.abs(PC.div(B, PC._dp)).max()) / (np.abs(B).max() + 1e-300)
        worst_div = max(worst_div, dE, dB)
    out["eigmode_gauss_resid"] = worst_div
    out["V"], out["lam"] = V, lam
    out["PASS"] = bool(len(sel_p) == 2 and len(sel_m) == 2
                       and out["w_op_vs_analytic"] < 1e-12
                       and worst_div < 1e-12
                       and out["eig_absdev_max"] < 1e-12)
    return out


def seed_generic(nfield, seed, L, trials):
    """photon_control.seed_generic 的 L/trials 参数化逐字端口。"""
    rng = np.random.default_rng(seed)
    return tuple(rng.standard_normal((3, trials, L, L, L))
                 for _ in range(nfield))


def solenoidal_project(F, kind, L):
    """photon_control.solenoidal_project 的 L 参数化逐字端口(诊断用)。"""
    k1 = 2.0 * np.pi * np.fft.fftfreq(L)
    KX, KY, KZ = np.meshgrid(k1, k1, k1, indexing="ij")
    if kind == "E":
        d = np.stack([1.0 - np.exp(-1j * KX), 1.0 - np.exp(-1j * KY),
                      1.0 - np.exp(-1j * KZ)])
    else:
        d = np.stack([np.exp(1j * KX) - 1.0, np.exp(1j * KY) - 1.0,
                      np.exp(1j * KZ) - 1.0])
    d2 = np.sum(np.abs(d) ** 2, axis=0)
    d2[d2 == 0] = 1.0
    Fh = np.fft.fftn(F, axes=(-3, -2, -1))
    dv = np.einsum("jxyz,jrxyz->rxyz", d, Fh)
    Fh = Fh - np.conj(d)[:, None] * (dv / d2)[None]
    return np.real(np.fft.ifftn(Fh, axes=(-3, -2, -1)))


def evolve_record(state, step, kinfos, T, L, energy=False):
    """photon_control.evolve_record 的 L 参数化逐字端口(无源波段)。"""
    PC = FZ.mod("photon_control")
    trials = state[0].shape[1]
    nk = len(kinfos)
    projs = np.stack([np.conj(plane(ki["kl"], L)) / L ** 3 for ki in kinfos])
    cfs = np.stack([ki["cf"] for ki in kinfos])
    rec = np.zeros((T, trials, nk, 6), complex)
    divE0 = PC.div(state[0], PC._dm).copy()
    divB0 = PC.div(state[1], PC._dp).copy()
    sc_E = float(np.abs(state[0]).max()) + 1e-300
    dE_drift = dB_drift = 0.0
    dE_rms_list, dB_rms_list = [], []
    rms0 = float(np.sqrt(np.mean(state[0] ** 2 + state[1] ** 2)))
    Hs = []
    for t in range(T):
        if energy:
            E_old, B_old = state[0], state[1]
        state = step(state)
        E, B = state[0], state[1]
        F6 = np.concatenate([E, B])
        rec[t] = np.einsum("kxyz,crxyz->rkc", projs, F6) * cfs[None]
        if energy:
            Hs.append(float(np.sum(E_old * E_old) + np.sum(B_old * B)))
        if t % 64 == 0 or t == T - 1:
            dE = np.abs(PC.div(E, PC._dm) - divE0)
            dB = np.abs(PC.div(B, PC._dp) - divB0)
            dE_drift = max(dE_drift, float(dE.max()) / sc_E)
            dB_drift = max(dB_drift, float(dB.max()) / sc_E)
            dE_rms_list.append(float(np.sqrt(np.mean(dE ** 2))) / sc_E)
            dB_rms_list.append(float(np.sqrt(np.mean(dB ** 2))) / sc_E)
    rms_end = float(np.sqrt(np.mean(state[0] ** 2 + state[1] ** 2)))
    mon = {"divE_drift_rel": dE_drift, "divB_drift_rel": dB_drift,
           "divE_drift_rms": float(np.max(dE_rms_list)),
           "divB_drift_rms": float(np.max(dB_rms_list)),
           "rms_first": rms0, "rms_last": rms_end,
           "rms_growth": rms_end / (rms0 + 1e-300),
           "stable": bool(np.isfinite(rms_end) and rms_end < 1e3 * rms0)}
    if energy and len(Hs) > 2:
        Hs = np.array(Hs)
        mon["yee_energy_drift_rel"] = float(
            np.abs(Hs - Hs[0]).max() / (abs(Hs[0]) + 1e-300))
    return rec, mon, state


# ==========================================================================
#  sponge / 源 / 波包 机构
# ==========================================================================
def sponge_field(L, width):
    """L4 sponge 冻结函数直接调用(gamma_max=0.30 = R36 part_C 值)。"""
    tcf = FZ.mod("rulespace_gpu.tensor_coin_feedback")
    return tcf._sponge_field(L, width, 0.30)


def sponged_step(state, step, sp, J=None, DT=0.5):
    """一步:候选 step -> 源电流沉积(E -= DT*J,Yee 源约定)-> sponge 乘子。
    sp=None 时为纯 rule 步;J=None 时无源。"""
    E, B = step(state)
    if J is not None:
        E = E - DT * J
    if sp is not None:
        E = E * (1.0 - sp)
        B = B * (1.0 - sp)
    return (E, B)


def make_packet(L, nvec, sigk):
    """带限螺线管 E 波包:k 空间高斯 × 截断球(|dk|<=3 sigk,杀带缘慢模)×
    螺线管投影(候选自身 E-div 符号),固定极化 = 与 k_j 分量最小的轴,
    包中心 = 盒中心。max-norm 归一。"""
    k1 = 2.0 * np.pi * np.fft.fftfreq(L)
    KX, KY, KZ = np.meshgrid(k1, k1, k1, indexing="ij")
    kj = 2.0 * np.pi * np.array(nvec, float) / L

    def dk(a, b):
        return np.angle(np.exp(1j * (a - b)))

    D2 = dk(KX, kj[0]) ** 2 + dk(KY, kj[1]) ** 2 + dk(KZ, kj[2]) ** 2
    G = np.exp(-D2 / (2 * sigk ** 2)) * (D2 <= (3 * sigk) ** 2)
    d = np.stack([1.0 - np.exp(-1j * KX), 1.0 - np.exp(-1j * KY),
                  1.0 - np.exp(-1j * KZ)])
    d2 = np.sum(np.abs(d) ** 2, axis=0)
    d2[d2 == 0] = 1.0
    ax = int(np.argmin(np.abs(kj) + 1e-9 * np.arange(3)))
    u = np.zeros(3)
    u[ax] = 1.0
    Fh = np.stack([u[j] * G for j in range(3)]).astype(complex)
    dv = np.einsum("jxyz,jxyz->xyz", d, Fh)
    Fh = Fh - np.conj(d) * (dv / d2)[None]
    x0 = L // 2
    Fh = Fh * np.exp(-1j * x0 * (KX + KY + KZ))
    E = np.real(np.fft.ifftn(Fh, axes=(-3, -2, -1)))
    m = float(np.abs(E).max())
    return E / (m + 1e-300)


def mode_amp(field6, projs):
    """物理帧 6 分量 k 模投影(与 evolve_record 同一 einsum;cf 由调用方乘)。"""
    return np.einsum("kxyz,crxyz->rkc", projs, field6)


def cheb_from_cells(L, cells):
    """到给定 cell 集(整数三元组列表)的周期 Chebyshev 距离场。"""
    idx = np.arange(L)
    X, Y, Z = np.meshgrid(idx, idx, idx, indexing="ij")

    def per(a, b):
        d = np.abs(a - b)
        return np.minimum(d, L - d)

    out = None
    for (cx, cy, cz) in cells:
        ch = np.maximum(np.maximum(per(X, cx), per(Y, cy)), per(Z, cz))
        out = ch if out is None else np.minimum(out, ch)
    return out


def cone_leak(dE, dB, cheb, radius):
    """锥判读:outside = cheb > radius;leak = max|dF|_out / max|dF|_in。"""
    dF = np.maximum(np.abs(dE).max(axis=0), np.abs(dB).max(axis=0))
    outside = cheb > radius
    if not outside.any() or outside.all():
        return None, None, None
    mi = float(dF[~outside].max())
    mo = float(dF[outside].max())
    return mo / (mi + 1e-300), mo, mi


def radial_tail(E_run_minus_ref, L, w, center):
    """静源 1/r 尾读出:E 分量插值到胞心 -> 径向分量 -> 壳 2<=r<=L/2-w-1 上
    与 1/r^2 的 Pearson 相关 + 中位 E_r*r^2 系数(-> q/4pi 对拍)。"""
    c = center
    Ec = np.stack([0.5 * (E_run_minus_ref[i] + np.roll(E_run_minus_ref[i], 1,
                                                       axis=i))
                   for i in range(3)])
    x = np.arange(L)
    X, Y, Z = np.meshgrid(x - c, x - c, x - c, indexing="ij")
    r = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
    rhat = np.stack([X, Y, Z]) / np.maximum(r, 1e-300)
    Er = np.sum(Ec * rhat, axis=0)
    rmax = L // 2 - w - 1
    sel = (r >= 2.0) & (r <= rmax)
    if sel.sum() < 4:
        return {"n_shell": int(sel.sum()), "corr": None, "coef_med": None,
                "r_range": [2, int(rmax)]}
    a, b = Er[sel], 1.0 / r[sel] ** 2
    corr = float(np.corrcoef(a, b)[0, 1])
    coef = float(np.median(a * r[sel] ** 2))
    return {"n_shell": int(sel.sum()), "corr": corr, "coef_med": coef,
            "r_range": [2, int(rmax)]}


def constraint_row_phys(kl):
    """候选自身约束符号(Gauss div_bwd E / div_fwd B)在物理帧的 2x6 行;
    ker C 的 4 维正交基(SVD 零空间;子空间,基无关)。"""
    PC = FZ.mod("photon_control")
    cf = PC.colfac(kl, PC.OFF6)
    dE = np.array([1.0 - np.exp(-1j * k) for k in kl])
    dB = np.array([np.exp(1j * k) - 1.0 for k in kl])
    C = np.zeros((2, 6), complex)
    C[0, :3] = dE / cf[:3]
    C[1, 3:] = dB / cf[3:]
    _, s, Vh = np.linalg.svd(C)
    rank = int(np.sum(s > 1e-12 * s[0]))
    Q = Vh.conj().T[:, rank:]
    return C, Q


def epsilon_invariant_from_line(line, kl):
    """G8 实测:主谱线 top-2 振幅空间(物理帧,数据 SVD)对 ker C 的不变量
    j_inv = #{sin theta >= INV.SIN_THRESH};epsilon_DOF = 1 - j_inv/N_curv。"""
    _, Q = constraint_row_phys(kl)
    S = np.asarray(line["Vh2"]).T          # (6, 2) 物理帧列空间
    inv = INV.subspace_invariants(S, Q)
    j_inv = int(inv["n_ge_thresh"])
    n_curv = int(line["rank"])
    return {"j_inv": j_inv, "N_curv": n_curv,
            "epsilon_dof": 1.0 - j_inv / max(n_curv, 1),
            "max_sin_theta": inv["max_sin_theta"],
            "sin_theta": inv["sin_theta"],
            "frob_leak": inv["frob_leak"], "rms_sin": inv["rms_sin"]}


def state_sha256(state):
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(state[0]).tobytes())
    h.update(np.ascontiguousarray(state[1]).tobytes())
    return h.hexdigest()
