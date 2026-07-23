"""cp1_v4_family_eval -- M4 全绿族评估器 payload(车道B,M4 长跑准备件 ②③)。

【定位】主线-CP1v4-装配阶梯与证伪炮组.md §三d 的第 ② 件:把 L1 冻结构造
(cp1_v4_L1.py,sha256 见 FROZEN_L1_SHA256,import 只读、逐位对拍)+ 阻尼模块
(cp1_v4_damping 的定参/证书/率门函数)封装成 tensor harness 可调的
    evaluate_rule(params) -> {"lawful_tensor": bool, 判据分项数值}
即 M1/M3 判据的批量化轻量版:每 rule 秒级(16^3、T=160、trials=4),精度换
吞吐,口径差全部显式声明(见 SCREEN_CALIBER 与 预注册草案-M4-全绿族参数先验.md §四)。

【纪律】本文件不发令、不长跑;自测(__main__)秒级到分钟级。不读取/运行
cp1_v4_L2*(L2 由另一 agent 装配);cp1_v4_L1.py 只 import(冻结只读),
自测含 sha256 对拍与 walk 核/K_placed 的逐位一致断言。

【backend 中立】格点演化全部经 rulespace_gpu.backend 的 B 接口
(B.xp / B.roll / B.asarray / B.to_np)书写——numpy 下自测通过即为验收口径
(拍板);MLX/jax 上跑长跑时同一源码。测量/计数(小张量 SVD、FFT、2x2 本征)
按 engine 惯例在 host(numpy)做。

【参数空间】(与 预注册草案-M4-全绿族参数先验.md 的先验/炮划分一致)
  先验列 FAMILY_PARAM_NAMES = ["dtheta", "damp_margin", "mu_frac", "G"]:
    dtheta      : theta_g - theta_m(共锥微失谐;J5 剪刀的物理横轴)
    damp_margin : 阻尼平台裕量(spectral_calibrate 的 margin;平台坐标之一)
    mu_frac     : mu_z 在平台 [mu_lo, mu_hi] 内的位置(允许越界以画稳定边界)
    G           : 源耦合。L3 未装配 -> 占位冻结 0(evaluate_rule 里非 0 即拒)
  炮开关(离散,不进先验,evaluate_rule kwargs;每项对应证伪炮组一件):
    tr_sign ∈ {1,0}         : 炮1。L1+L2 层无源无牙(声明:恒过,L3 后才咬)
    placement ∈ {"staggered","integer"} : 炮6(整数格放置,K_central)
    slave_cov ∈ {"full","partial"}      : 炮7(只盖 Re(spinor0),R21 病)
    lag ∈ {0,1}             : 炮3(K 输入用 stale 切片,R20 hprev 病)
    carrier ∈ {"comoving","static"}     : 炮8(Z 静止载波,符号层证书侧)
    axis_order ∈ {"xyz","zyx",...}      : 轴序(建议炮/附检,见预注册草案)

【判据(轻量版)】全部同时成立 => lawful_tensor:
  J1_stable  : walk 幺正扇区(空间行)范数漂移 < 1e-8 且全态有限
  Nprop2     : placed-κ Riemann-SVD 计数 = 2 @ {(2,0,0),(2,2,0)}(SV 阈 0.08,
               screen 口径;Z 扇区经符号层 z_sector_certificate 显式扣除)
  J5         : |c_gw/c_matter - 1| < 1e-2(装配算子 2x2 本征相位,bin-free)
  constraint : |K@TT| 在壳证书 < 1e-10 且 演化中 relC 尾段 < 1e-10
               (精确投影使能下应恒机器零;平台非法/炮病 -> stall/溢出)
  SV         : sv3 < 0.08 且 tt_match > 0.90(screen 带;M3 全判据 0.05/0.95)
  Z_sector   : z_sector_certificate(K,ω;μ_z,κ₁) pass(单位模 = dim ker K,
               单位模零 Z 含量;static 载波在此被杀)

【停跑规则(§三d 第 ③ 件,写死;harness/runner 必须遵守)】见 STOP_RULES。

【harness 接线】对齐 TENSOR_CAMPAIGN_INTERFACE.md 的 payload 契约:
    from cp1_v4_family_eval import (PARAM_NAMES, sample_tensor_prior,
                                    screen_tensor_rules, STOP_RULES,
                                    should_stop, append_scan_row)
  即把 tensor_campaign_runner 的 tensor_batch import 换成本模块(一行);
  screen_tensor_rules 逐 rule 调 evaluate_rule(本 payload 的"快筛"就是轻量
  全判据,两级合一;M4 复判 = 流形代表点送 M3 全判据,见预注册草案 §四)。
  每 rule 结果用 append_scan_row 追加到 m4_family_scan.jsonl(dashboard
  J5 剪刀 δ 扫描面板读它;字段 schema 见 SCAN_ROW_FIELDS)。

自测:RULESPACE_BACKEND=numpy .venv/bin/python cp1_v4_family_eval.py
      (~1-2 分钟;冻结点应 lawful,四个炮参数应 not lawful;
       写 cp1_v4_family_eval_selftest.json)
"""
import hashlib
import json
import math
import os
import time

import numpy as np

import cp1_v4_L1 as L1                      # 冻结只读(sha256 对拍见自测)
import cp1_v4_damping as DAMP               # 预写阻尼模块(定参/证书/率门)
import r15_walk_dedonder as r15
from rulespace_gpu import backend as B
from rulespace_gpu import tensor_coin_feedback as tcf

xp = B.xp
DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 冻结与常量
FROZEN_L1_SHA256_FULL = \
    "4dad03be4319da896f485d954f0efc97bc0a6f781700f97e3e8120178a5c6035"
TH_M = L1.TH0                               # theta_matter 冻结 = pi/3(L1)
PK, OFFSET, SYM = L1.PK, L1.OFFSET, L1.SYM
SPATIAL = L1.SPATIAL

# ---- screen 口径(与 M3 全判据的差,逐条声明;M4 报告必须引用) ----
SCREEN_CALIBER = {
    "N": 16, "T": 160, "trials": 4,
    "kmodes": [(2, 0, 0), (2, 2, 0)],
    "sv_thresh_screen": 0.08,      # M3 全判据 0.05;screen 放宽防阈值摆动假阴
    "tt_match_min": 0.90,          # M3: 0.95
    "j5_tol": 1e-2,                # = M3 预注册
    "cert_KTT_max": 1e-10,         # 在壳 |K@TT| 证书(M3: 1e-12)
    "drift_max": 1e-8,             # walk 幺正扇区漂移(M3: 1e-10 @T=2000)
    "notes": [
        "J5 由装配算子 2x2 本征相位测(bin-free),非全谱管线",
        "格点约束执行 = 精确投影极限(L1 获准选项;λ∈{0,1} 二值使能):"
        "阻尼参数 (damp_margin,mu_frac) 的牙在符号层——平台合法性(ρ_pred<1)、"
        "z_sector_certificate(单位模记账 + 平台收缩半径 √(1-κ₁))、静止载波全"
        "BZ 谱半径;真 Z4c 格点率动力学是 L2/M3 保真层,screen 不预支",
        "探针 k 集不含体对角 (2,2,2)(walk 核属性,族内不变,L1 §八.4)",
        "screen lawful ≢ M3 全绿;流形代表点须送 M3 全判据复判",
    ],
}

FAMILY_PARAM_NAMES = ["dtheta", "damp_margin", "mu_frac", "G"]
PARAM_NAMES = FAMILY_PARAM_NAMES            # harness 契约别名
FROZEN_POINT = {"dtheta": 0.0, "damp_margin": DAMP.DEFAULT_MARGIN,
                "mu_frac": 0.5, "G": 0.0}

# ---- 停跑规则(§三d 第 ③ 件;评审拍板前不许放松) ----
STOP_RULES = {
    "lawful_target": 1000,        # lawful_tensor 计数 >= 10^3 即停(流形统计够)
    "max_rules": 500_000,         # 安全阀:最大评估数(10^5 起步,上限 5x10^5)
    "max_wall_hours": 48.0,       # 安全阀:最大墙钟
}


def should_stop(lawful_count, rules_done, wall_seconds):
    """runner 每 batch 后必须调用;返回 (stop:bool, reason:str|None)。"""
    if lawful_count >= STOP_RULES["lawful_target"]:
        return True, "lawful_target reached (%d >= %d)" % (
            lawful_count, STOP_RULES["lawful_target"])
    if rules_done >= STOP_RULES["max_rules"]:
        return True, "max_rules safety valve (%d)" % rules_done
    if wall_seconds >= STOP_RULES["max_wall_hours"] * 3600.0:
        return True, "max_wall_hours safety valve (%.1f h)" % (
            wall_seconds / 3600.0)
    return False, None


# ============================================================= B 接口 walk 核
# tcf._axis_sandwich(orient=1) / gw.geom_walk_all 的逐位镜像,写在 B 接口上。
# numpy 后端下自测断言与 gw.geom_walk_all 逐位一致(共核保证的 screen 侧版本)。
_AXIS_OF = {"x": -3, "y": -2, "z": -1}


def _frames_host(th_g):
    """tcf.axis_frames 的复刻(host 小矩阵):Wx=Ad@WX, Wy=Ad@WY, Wz=Ad。"""
    c, s = math.cos(th_g / 2), math.sin(th_g / 2)
    A = np.array([[c, 1j * s], [1j * s, c]])
    Ad = A.conj().T
    return {"x": Ad @ tcf.WX, "y": Ad @ tcf.WY, "z": Ad}


def make_walk(th_g, axis_order="xyz"):
    """返回 walk(chi) -> chi:一个宏步,chi (10, ..., Nx,Ny,Nz, 2) device。
    axis_order: 轴的作用次序(默认 xyz = 冻结约定;炮/附检可换)。"""
    Wh = _frames_host(th_g)
    dev = {a: (B.asarray(Wh[a].T.copy()), B.asarray(Wh[a].conj().copy()))
           for a in "xyz"}
    c, s = math.cos(th_g), math.sin(th_g)
    si = 1j * s

    def _sandwich(psi, ax3, WT, Wc):
        psi = xp.matmul(psi, WT)                       # q = psi @ W.T
        p0, p1 = psi[..., 0], psi[..., 1]
        p0, p1 = c * p0 + si * p1, si * p0 + c * p1    # coin(+th)
        p0 = B.roll(p0, 1, ax3)
        p0, p1 = c * p0 - si * p1, -si * p0 + c * p1   # coin(-th)
        p1 = B.roll(p1, -1, ax3)
        psi = xp.stack([p0, p1], axis=-1)
        return xp.matmul(psi, Wc)                      # psi = q @ W.conj()

    def walk(chi):
        for a in axis_order:
            WT, Wc = dev[a]
            chi = _sandwich(chi, _AXIS_OF[a], WT, Wc)
        return chi

    return walk


# ============================================================ B 接口 K 算子
def _D_dict(f, mu, comp):
    """R17 字典空间差分(整数 roll,交错子晶格间);f (...,Nx,Ny,Nz)。"""
    ax = mu - 4
    if OFFSET[comp][mu]:
        return f - B.roll(f, 1, ax)
    return B.roll(f, -1, ax) - f


def K_placed_B(Hp, Hc, Hn, cc):
    """L1.K_placed 的 B 接口镜像(numpy 下逐位一致,自测断言)。
    H* (10, ..., Nx,Ny,Nz);返回 (4, ...)。"""
    rows = []
    for nu in range(4):
        acc = None
        for mu in (1, 2, 3):
            comp = PK[(mu, nu)]
            d = _D_dict(Hc[comp], mu, comp)
            acc = d if acc is None else acc + d
        c0 = PK[(0, nu)]
        dt = (Hc[c0] - Hp[c0]) if OFFSET[c0][0] else (Hn[c0] - Hc[c0])
        rows.append(acc - dt / cc)
    return xp.stack(rows, axis=0)


def K_central_B(Hp, Hc, Hn, cc):
    """炮6算子:整数格中心模板(L1.K_central 镜像;CP0/CP1-v1 病)。"""
    rows = []
    for nu in range(4):
        acc = None
        for mu in (1, 2, 3):
            f = Hc[PK[(mu, nu)]]
            d = 0.5 * (B.roll(f, -1, mu - 4) - B.roll(f, 1, mu - 4))
            acc = d if acc is None else acc + d
        c0 = PK[(0, nu)]
        rows.append(acc - 0.5 * (Hn[c0] - Hp[c0]) / cc)
    return xp.stack(rows, axis=0)


# ===================================================== family stepper(纯函数)
def make_family_stepper(th_g, lam, placement="staggered", slave_cov="full",
                        lag=0, axis_order="xyz"):
    """返回 step(chi, hist) -> (chi, hist)。chi (10,R,N,N,N,2) device;
    hist = [[H(t-2), H(t-1)] per spinor](滚动切片缓冲,无 hprev 态)。

    构造 = L1 make_stepper("certified") 的参数化版。lam ∈ {0,1} 二值使能
    (evaluate_rule 由阻尼平台谱预言映射:ρ_pred<1 -> 1(精确投影,L1 获准
    选项),否则 0(平台非法 -> 不执行,应死));0<lam<1 的软执行已实测
    对 walk 闭环不收敛(walk 再生约束与 slave 阻尼同速率竞争),不采用。
    enforce == measure:执行与监视共用同一 K_*_B 函数对象(L1 纪律继承)。"""
    cc = math.cos(th_g)
    walk = make_walk(th_g, axis_order)
    Kfun = K_central_B if placement == "integer" else K_placed_B
    gain = (2.0 * cc) if placement == "integer" else cc

    def _slave_full(Hs, Hp2, Hp1):
        Z = Hs * 0
        if placement == "integer":
            Cc = Kfun(Hp2, Hp1, Hs, cc)
            comps = [Hs[c] for c in range(10)]
            for nu in range(4):
                c0 = PK[(0, nu)]
                comps[c0] = comps[c0] + lam * gain * Cc[nu]
            return xp.stack(comps, axis=0)
        Ct = Kfun(Hp1, Hs, Z, cc)                      # rows 1..3 有效
        comps = [Hs[c] for c in range(10)]
        for i in (1, 2, 3):
            c0 = PK[(0, i)]
            comps[c0] = comps[c0] + lam * gain * Ct[i]
        Hs2 = xp.stack(comps, axis=0)
        C0 = Kfun(Z, Hp1, Hs2, cc)                     # row 0 有效
        comps = [Hs2[c] for c in range(10)]
        comps[PK[(0, 0)]] = comps[PK[(0, 0)]] + lam * gain * C0[0]
        return xp.stack(comps, axis=0)

    def _slave_partial(Hs, Hp1):
        """炮7:只盖 Re(该旋量分量)(1/4 实维;R21 病)。"""
        Z = Hs * 0
        Hr = B.real(Hs) + 0j
        Hp1r = B.real(Hp1) + 0j
        Ct = Kfun(Hp1r, Hr, Z, cc)
        comps = [Hs[c] for c in range(10)]
        for i in (1, 2, 3):
            c0 = PK[(0, i)]
            comps[c0] = (B.real(comps[c0]) + lam * gain * B.real(Ct[i])
                         + 1j * B.imag(comps[c0]))
        Hs2 = xp.stack(comps, axis=0)
        Hr = B.real(Hs2) + 0j
        C0 = Kfun(Z, Hp1r, Hr, cc)
        comps = [Hs2[c] for c in range(10)]
        c0 = PK[(0, 0)]
        comps[c0] = (B.real(comps[c0]) + lam * gain * B.real(C0[0])
                     + 1j * B.imag(comps[c0]))
        return xp.stack(comps, axis=0)

    def step(chi, hist):
        chi = walk(chi)
        newH, newhist = [], []
        for s in range(2):
            Hs = chi[..., s]
            Hp2, Hp1 = hist[s]
            if slave_cov == "partial":
                if s == 0:
                    Hs = _slave_partial(Hs, Hp1)
            elif lag:
                Hs = _slave_full(Hs, Hp2, Hp2)         # 炮3:stale 切片喂 K
            else:
                Hs = _slave_full(Hs, Hp2, Hp1)
            newH.append(Hs)
            newhist.append([Hp1, Hs])
        chi = xp.stack(newH, axis=-1)
        return chi, newhist

    return step, Kfun, cc


# ================================================== host 侧测量(numpy,轻量)
def _plane(kl, N):
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    return np.exp(1j * (kl[0] * X + kl[1] * Y + kl[2] * Z))


_EIG_CACHE = {}


def walk_mode_eig(nvec, N, th_g, axis_order="xyz"):
    """装配 walk 算子在格点模 nvec 的 (ω, c) —— 2x2 k-模矩阵本征相位
    (机器精度,bin-free)。用 *本模块的 B 接口 walk*(咬得到装配层的病)。"""
    key = (tuple(nvec), N, round(th_g, 12), axis_order)
    if key in _EIG_CACHE:
        return _EIG_CACHE[key]
    kl = np.array(nvec, float) * (2 * np.pi / N)
    ph = _plane(kl, N)
    proj = np.conj(ph) / N ** 3
    walk = make_walk(th_g, axis_order)
    M = np.zeros((2, 2), complex)
    for s in range(2):
        c0 = np.zeros((1, N, N, N, 2), complex)
        c0[0, ..., s] = ph
        out = B.to_np(walk(B.asarray(c0)))
        for r in range(2):
            M[r, s] = np.sum(proj * out[0, ..., r])
    ev, _ = np.linalg.eig(M)
    w = -np.angle(ev)
    cand = [j for j in range(2) if 1e-9 < w[j] < math.pi - 1e-9]
    wj = min(w[j] for j in cand)
    kch = L1.kchord(kl)
    out = (float(wj), float(wj / (kch + 1e-30)))
    _EIG_CACHE[key] = out
    return out


def count_at_k_screen(rec_k, kl, w_walk, c_cone, sv_thresh):
    """L1.count_at_k 的 screen 版:显式 c_cone(失谐族需要),砍掉 ker 残差
    与白化谱(吞吐);placed-κ Riemann-SVD,无 TT 投影。rec_k (T,R,10) host。"""
    T, R, _ = rec_k.shape
    T0 = T // 2
    W = T - T0
    win = np.hanning(W)
    seg = L1.detrend(rec_k[T0:])
    seg = (seg * win[:, None, None])[2:-2]
    freqs = 2 * np.pi * np.fft.fftfreq(W - 4)
    sel = (np.abs(freqs) > max(0.05, 4 * np.pi / (W - 4))) \
        & (np.abs(freqs) <= np.pi / 2)
    F = np.fft.fft(seg, axis=0)
    P = np.sum(np.abs(F) ** 2, axis=(1, 2))
    if float(P[sel].sum()) < 1e-18:
        return {"n_prop": 0, "sv3": 1.0, "tt_match": 0.0, "no_peak": True}
    pk = int(np.argmax(np.where(sel, P, 0.0)))
    ws = math.copysign(w_walk, float(freqs[pk]))
    k4 = np.array([ws, kl[0], kl[1], kl[2]])
    kap = L1.kappa_of(ws, kl, c_cone)
    cf = L1.colfac(k4)
    A = F[pk] * np.conj(cf)[None, :]
    M = np.stack([L1.riemann_sym(kap, A[r]) for r in range(R)])
    sv = np.linalg.svd(M, compute_uv=False)
    svn = (sv / (sv[0] + 1e-300)).tolist()
    n_prop = int(np.sum(np.array(svn) > sv_thresh))
    U = np.linalg.svd(M.T, full_matrices=False)[0]
    TTb = r15.tt_basis(kap)
    Rtt = np.stack([L1.riemann_sym(kap, TTb[:, j]) for j in range(2)], axis=1)
    Qd, _ = np.linalg.qr(U[:, :2])
    Qt, _ = np.linalg.qr(Rtt)
    ttm = float(np.min(np.linalg.svd(Qd.conj().T @ Qt,
                                     compute_uv=False)) ** 2)
    return {"n_prop": n_prop, "sv3": float(svn[2]) if len(svn) > 2 else 0.0,
            "tt_match": ttm, "w_peak": float(freqs[pk]), "no_peak": False}


def cert_KTT_screen(nvec, N, th_g, Kapply, cc):
    """在壳 |K@TT| mini 证书(R19 gateA 精神):交错种子切片喂装配 K。"""
    kl = np.array(nvec, float) * (2 * np.pi / N)
    w = r15.shell_omega(kl, cc)
    if w is None:
        return float("nan")
    k4 = np.array([w, kl[0], kl[1], kl[2]])
    kap = L1.kappa_of(w, kl, cc)
    TT = r15.tt_basis(kap)
    worst = 0.0
    base = _plane(kl, N)
    for p in range(2):
        a = TT[:, p] / (np.linalg.norm(TT[:, p]) + 1e-300)
        Hs = L1.seed_slices(a, k4, N, 3, base)
        Hd = [B.asarray(h) for h in Hs]
        out = B.to_np(Kapply(Hd[0], Hd[1], Hd[2], cc))
        worst = max(worst, float(np.abs(out).max()))
    return worst


# ------------------------------------------------ 阻尼平台定参(host,缓存)
_CAL_CACHE = {}


def platform_calibrate(cc, margin):
    """σ² 谱 probe(r15 符号约束矩阵,BZ 采样)-> spectral_calibrate 平台。
    遵守"装配层重算、禁抄数字"条款:全部由传入锥速 cc 的谱现算。"""
    key = (round(cc, 12), round(float(margin), 8))
    if key in _CAL_CACHE:
        return _CAL_CACHE[key]
    ks = [np.array(v, float) * (2 * np.pi / 16) for v in
          [(1, 0, 0), (2, 0, 0), (3, 0, 0), (2, 2, 0), (3, 1, 0), (1, 1, 1),
           (2, 2, 2), (4, 1, 1), (3, 3, 0), (5, 2, 1), (6, 1, 0), (4, 4, 2)]]
    Ks = []
    for k in ks:
        w = r15.shell_omega(k, cc)
        if w is None:
            continue
        Ks.append(r15.constraint_matrix(L1.kappa_of(w, k, cc)))
    cal = DAMP.spectral_calibrate(Ks, margin=float(margin))
    s2 = np.linspace(cal["sigma2_min"], cal["sigma2_max"], 512)
    _CAL_CACHE[key] = (cal, s2)
    return _CAL_CACHE[key]


# ================================================================ 评估器本体
def evaluate_rule(params, tr_sign=1, placement="staggered", slave_cov="full",
                  lag=0, carrier="comoving", axis_order="xyz", seed=7,
                  N=None, T=None, trials=None):
    """一条 family 规则 -> 判据分项 + lawful_tensor(轻量版,口径见 SCREEN_CALIBER)。

    params: dict 或按 FAMILY_PARAM_NAMES 排序的向量。
    炮开关(kwargs)不进先验;tr_sign 现阶段声明无牙(L3 后才咬)。"""
    if not isinstance(params, dict):
        params = dict(zip(FAMILY_PARAM_NAMES, [float(v) for v in params]))
    p = dict(FROZEN_POINT)
    p.update(params)
    cal_n = SCREEN_CALIBER
    N = N or cal_n["N"]
    T = T or cal_n["T"]
    R = trials or cal_n["trials"]
    kmodes = cal_n["kmodes"]
    th_g = TH_M + float(p["dtheta"])
    cc = math.cos(th_g)
    out = {"params": p, "switches": {"tr_sign": tr_sign, "placement": placement,
                                    "slave_cov": slave_cov, "lag": lag,
                                    "carrier": carrier,
                                    "axis_order": axis_order}}

    # G 占位(L3 未装配):非 0 直接拒 —— 防止先验偷跑未装配的部件
    if abs(float(p["G"])) > 0:
        out.update({"lawful_tensor": False, "reject": "G!=0 (L3 not assembled)"})
        return out
    # tr_sign 声明:L1+L2 层(无源)无动力学效应,恒过;L3 后进牙(预注册草案 §二.4)
    out["tr_sign_note"] = "no dynamical teeth pre-L3 (declared)"

    # ---- 阻尼平台定参 -> λ = 1 - ρ(谱预言) ----
    try:
        cal, s2 = platform_calibrate(cc, p["damp_margin"])
    except Exception as e:
        out.update({"lawful_tensor": False, "reject": "calibrate: %s" % e})
        return out
    mu_lo, mu_hi = cal["mu_plateau"]
    mu_z = mu_lo + float(p["mu_frac"]) * (mu_hi - mu_lo)
    k1 = cal["kappa1"]
    if mu_z <= 0:
        rho_pred = 1.0
    else:
        rho_pred = float(DAMP.z4c_block_moduli(mu_z, k1, s2).max())
    # 二值使能:平台合法(ρ_pred<1)-> 精确投影(λ=1,L1 获准选项);
    # 非法 -> 不执行(λ=0,该 rule 应死于约束/计数门)。软 λ 不采用(见
    # make_family_stepper docstring)。
    lam = 1.0 if rho_pred < 1.0 else 0.0
    out["damping"] = {"mu_z": float(mu_z), "kappa1": float(k1),
                      "rho_pred": float(rho_pred), "lam": float(lam),
                      "mu_plateau": [float(mu_lo), float(mu_hi)],
                      "rho_plateau": float(cal["rho_step_pred"])}

    # ---- Z 扇区记账(符号层证书,逐探针 k;R22 §五 / 炮8) ----
    z_ok = True
    zrows = []
    for nv in kmodes:
        kl = np.array(nv, float) * (2 * np.pi / N)
        w = r15.shell_omega(kl, cc)
        K = r15.constraint_matrix(L1.kappa_of(w, kl, cc))
        cert = DAMP.z_sector_certificate(K, w, mu_z, k1)
        row = {"k": list(nv), "pass": bool(cert["pass"]),
               "n_unit": cert["n_unit_modes"], "dim_ker": cert["dim_kerK"]}
        z_ok = z_ok and row["pass"]
        zrows.append(row)
    if carrier == "static":
        # 炮8:静止载波必须在全 BZ 采样上验稳(不稳模逐 k,R22 §二消融/
        # cp1_v4_damping 自检 [C]:最不稳 k 不一定是探针 k)。
        rho_worst, kw = 0.0, None
        for v in [(1, 0, 0), (2, 0, 0), (3, 0, 0), (2, 2, 0), (3, 1, 0),
                  (1, 1, 1), (2, 2, 2), (4, 1, 1), (3, 3, 0), (5, 2, 1),
                  (6, 1, 0), (4, 4, 2), (7, 1, 0), (5, 5, 3)]:
            kl = np.array(v, float) * (2 * np.pi / N)
            w = r15.shell_omega(kl, cc)
            if w is None:
                continue
            K = r15.constraint_matrix(L1.kappa_of(w, kl, cc))
            A = DAMP.z4c_augmented_matrix(K, w, mu_z, k1, comoving=False)
            r_ = float(np.abs(np.linalg.eigvals(A)).max())
            if r_ > rho_worst:
                rho_worst, kw = r_, v
        zrows.append({"k": "static_carrier_worst_" + str(kw),
                      "rho_static_worst": rho_worst,
                      "pass": bool(rho_worst <= 1.0 + 1e-9)})
        z_ok = z_ok and zrows[-1]["pass"]
    out["z_sector"] = zrows

    # ---- J5(装配算子本征相位;bin-free) ----
    j5_ratios = []
    for nv in kmodes:
        _, cg = walk_mode_eig(nv, N, th_g, axis_order)
        _, cm = walk_mode_eig(nv, N, TH_M, "xyz")      # 物质参考:冻结口径
        j5_ratios.append(cg / (cm + 1e-300))
    j5_dev = float(max(abs(r - 1.0) for r in j5_ratios))
    out["j5_dev"] = j5_dev
    out["j5_ratio"] = float(max(j5_ratios, key=lambda r: abs(r - 1.0)))

    # ---- 在壳 |K@TT| mini 证书(放置牙) ----
    _, Kfun, _ = make_family_stepper(th_g, lam, placement, slave_cov, lag,
                                     axis_order)
    certs = [cert_KTT_screen(nv, N, th_g, Kfun, cc) for nv in kmodes]
    cert_worst = float(np.nanmax(certs))
    out["cert_KTT"] = cert_worst

    # ---- 格点演化(B 接口;raw 随机初条,judge 忠实口径) ----
    step, _, _ = make_family_stepper(th_g, lam, placement, slave_cov, lag,
                                     axis_order)
    chi_h = L1.seed_raw(N, R, seed)                    # (10,R,N,N,N,2) host
    chi = B.asarray(chi_h)
    hist = [[chi[..., s], chi[..., s]] for s in range(2)]
    kinfos = []
    for nv in kmodes:
        kl = np.array(nv, float) * (2 * np.pi / N)
        ph = _plane(kl, N)
        kinfos.append((kl, B.asarray(np.conj(ph) / N ** 3)))
    rec = [[] for _ in kmodes]
    cn = []                                            # 约束范数(绝对)
    norm_sp0 = None
    drift = 0.0
    buf = [hist[0][1]]
    for t in range(T):
        chi, hist = step(chi, hist)
        H0 = hist[0][1]
        for ki, (kl, projd) in enumerate(kinfos):
            rec[ki].append(xp.sum(H0 * projd[None, None], axis=(2, 3, 4)))
        buf.append(H0)
        if len(buf) > 3:
            buf.pop(0)
        if len(buf) == 3 and t % 2 == 0:
            Kfun2 = K_central_B if placement == "integer" else K_placed_B
            Cr = B.to_np(Kfun2(buf[0], buf[1], buf[2], cc))
            hn = float(np.sqrt(np.mean(np.abs(B.to_np(buf[1])) ** 2)))
            cn.append(float(np.sqrt(np.mean(np.abs(Cr) ** 2))) / (hn + 1e-300))
        if t % 8 == 0 or t == T - 1:
            nsp = float(np.sqrt(np.sum(np.abs(B.to_np(chi[SPATIAL])) ** 2)))
            if norm_sp0 is None:
                norm_sp0 = nsp
            drift = max(drift, abs(nsp / (norm_sp0 + 1e-300) - 1.0))
    finite = bool(np.isfinite(B.to_np(xp.sum(xp.abs(chi)))))
    out["stability"] = {"walk_sector_drift": drift, "finite": finite}

    # ---- 约束门(relC 尾段机器零;精确投影下应为恒机器零) ----
    cn = np.asarray(cn)
    if len(cn) < 8 or not np.all(np.isfinite(cn)):
        relC_tail = float("inf")
    else:
        relC_tail = float(cn[int(0.75 * len(cn)):].max())
    out["constraint_monitor"] = {
        "relC_first": float(cn[0]) if len(cn) else float("nan"),
        "relC_tail_max": relC_tail,
        "relC_max": float(cn.max()) if len(cn) and
        np.all(np.isfinite(cn)) else float("inf")}

    # ---- placed-κ 计数(host) ----
    perk = {}
    npmax, sv3max, ttmin = 0, 0.0, 1.0
    for ki, nv in enumerate(kmodes):
        kl = kinfos[ki][0]
        w_walk, _ = walk_mode_eig(nv, N, th_g, axis_order)
        rk = np.stack([B.to_np(a) for a in rec[ki]])   # (T,10,R)
        rk = np.moveaxis(rk, 1, 2)                     # (T,R,10)
        e = count_at_k_screen(rk, kl, w_walk, cc,
                              cal_n["sv_thresh_screen"])
        perk[str(tuple(nv))] = e
        npmax = max(npmax, e["n_prop"])
        sv3max = max(sv3max, e["sv3"])
        ttmin = min(ttmin, e["tt_match"])
    out["per_k"] = perk

    # ---- 门表 ----
    gates = {
        "J1_stable": bool(finite and drift < cal_n["drift_max"]),
        "Nprop2": bool(all(perk[str(tuple(nv))]["n_prop"] == 2
                           for nv in kmodes)),
        "J5": bool(j5_dev < cal_n["j5_tol"]),
        "constraint": bool(cert_worst < cal_n["cert_KTT_max"]
                           and relC_tail < 1e-10),
        "SV": bool(sv3max < cal_n["sv_thresh_screen"]
                   and ttmin > cal_n["tt_match_min"]),
        "Z_sector": bool(z_ok),
    }
    out["gates"] = gates
    out["others_pass"] = bool(all(v for k, v in gates.items() if k != "J5"))
    out["lawful_tensor"] = bool(all(gates.values()))
    out["n_prop"] = npmax
    out["sv3"] = sv3max
    out["tt_match"] = ttmin
    out["relC_last"] = float(cn[-1]) if len(cn) else float("nan")
    return out


# ============================================== 先验采样器(预注册草案 §二)
def sample_family_prior(n, seed=0):
    """(n, 4) host float:dtheta ~ U(-0.02,0.02);damp_margin ~ 10^U(-2,-0.52);
    mu_frac ~ U(-0.2,1.2)(故意越出平台画稳定边界);G = 0(L3 占位)。
    冻结权在评审(预注册草案-M4-全绿族参数先验.md,草案待拍板)。"""
    rng = np.random.default_rng(seed)
    dth = rng.uniform(-0.02, 0.02, n)
    marg = 10.0 ** rng.uniform(-2.0, math.log10(0.3), n)
    muf = rng.uniform(-0.2, 1.2, n)
    G = np.zeros(n)
    return np.stack([dth, marg, muf, G], axis=1)


sample_tensor_prior = sample_family_prior              # harness 契约别名


def screen_tensor_rules(params_batch, quick=True, **_ignored):
    """TENSOR_CAMPAIGN_INTERFACE 契约列(harness 依赖这些名字)。
    本 payload 的"快筛"就是轻量全判据(两级合一,M4 复判走 M3 全表)。"""
    P = np.atleast_2d(np.asarray(params_batch, dtype=float))
    n = len(P)
    cols = {"passes_screen": np.zeros(n, bool), "stable": np.zeros(n, bool),
            "tt_dof": np.full(n, -1, int), "gw_speed": np.full(n, np.nan),
            "gw_speed_ok": np.zeros(n, bool),
            "newton_proxy": np.full(n, np.nan),        # L3 后才有
            "emergence_proxy": np.full(n, np.nan),
            "lawful_tensor": np.zeros(n, bool),
            "j5_dev": np.full(n, np.nan), "sv3": np.full(n, np.nan),
            "tt_match": np.full(n, np.nan), "others_pass": np.zeros(n, bool)}
    for i, row in enumerate(P):
        try:
            r = evaluate_rule(row)
        except Exception:
            continue
        g = r.get("gates", {})
        cols["passes_screen"][i] = r.get("lawful_tensor", False)
        cols["lawful_tensor"][i] = r.get("lawful_tensor", False)
        cols["stable"][i] = g.get("J1_stable", False)
        cols["tt_dof"][i] = r.get("n_prop", -1)
        cols["gw_speed"][i] = 1.0 + r.get("j5_dev", np.nan)
        cols["gw_speed_ok"][i] = g.get("J5", False)
        cols["emergence_proxy"][i] = r.get("n_prop", np.nan)
        cols["j5_dev"][i] = r.get("j5_dev", np.nan)
        cols["sv3"][i] = r.get("sv3", np.nan)
        cols["tt_match"][i] = r.get("tt_match", np.nan)
        cols["others_pass"][i] = r.get("others_pass", False)
    return cols


# =================================================== m4_family_scan.jsonl 追加
M4_SCAN_JSONL = os.path.join(DIR, "m4_family_scan.jsonl")
SCAN_ROW_FIELDS = {
    # dashboard J5 剪刀 δ 扫描面板(dashboard_ladder.html)读的 schema:
    "t": "unix 时间戳", "param_names": "FAMILY_PARAM_NAMES",
    "params": "参数向量(list)",
    "lawful_tensor": "bool,全部门(含 J5@1e-2)通过",
    "others_pass": "bool,除 J5 外全部门通过(δ 扫描的分母)",
    "j5_dev": "float,|c_gw/c_matter - 1|(δ 扫描的横轴量)",
    "n_prop": "int", "sv3": "float", "tt_match": "float",
    "relC_last": "float", "stable": "bool",
}


def append_scan_row(result, path=M4_SCAN_JSONL):
    """每 rule 评完追加一行(jsonl;dashboard 面板轮询它)。"""
    row = {"t": time.time(), "param_names": FAMILY_PARAM_NAMES,
           "params": [float(result["params"][k]) for k in FAMILY_PARAM_NAMES],
           "lawful_tensor": bool(result.get("lawful_tensor", False)),
           "others_pass": bool(result.get("others_pass", False)),
           "j5_dev": float(result.get("j5_dev", float("nan"))),
           "n_prop": int(result.get("n_prop", -1)),
           "sv3": float(result.get("sv3", float("nan"))),
           "tt_match": float(result.get("tt_match", float("nan"))),
           "relC_last": float(result.get("relC_last", float("nan"))),
           "stable": bool(result.get("gates", {}).get("J1_stable", False))}
    with open(path, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


# ======================================================================= 自测
def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run_selftest(write_json=True):
    t0 = time.time()
    out = {"backend": B.NAME, "screen_caliber": SCREEN_CALIBER,
           "stop_rules": STOP_RULES}
    print(f"backend = {B.NAME}")
    print("cp1_v4_family_eval -- M4 全绿族评估器自测(不发令、不长跑)")
    print("=" * 72)

    # -- 0) 冻结 hash 对拍 --------------------------------------------------
    sha = _sha256(os.path.join(DIR, "cp1_v4_L1.py"))
    ok_hash = (sha == FROZEN_L1_SHA256_FULL)
    out["frozen_L1_sha256"] = {"measured": sha, "expected":
                               FROZEN_L1_SHA256_FULL, "match": ok_hash}
    print(f"[0] cp1_v4_L1.py sha256 对拍: {'PASS' if ok_hash else 'FAIL'} "
          f"({sha[:12]}…)")

    # -- 1) 构造保真:B 接口 walk / K 与冻结实现逐位一致(numpy 口径) ------
    fid = {}
    if B.NAME == "numpy":
        from rulespace_gpu import green_one_walk as gw
        rng = np.random.default_rng(3)
        chi = (rng.standard_normal((10, 2, 8, 8, 8, 2))
               + 1j * rng.standard_normal((10, 2, 8, 8, 8, 2)))
        ref = gw.geom_walk_all(chi.copy(), TH_M, TH_M, TH_M, TH_M)
        mine = B.to_np(make_walk(TH_M, "xyz")(B.asarray(chi.copy())))
        fid["walk_maxdiff"] = float(np.abs(ref - mine).max())
        Hs = [rng.standard_normal((10, 8, 8, 8))
              + 1j * rng.standard_normal((10, 8, 8, 8)) for _ in range(3)]
        refK = L1.K_placed(Hs[0], Hs[1], Hs[2], math.cos(TH_M))
        mineK = B.to_np(K_placed_B(*[B.asarray(h) for h in Hs], math.cos(TH_M)))
        fid["K_placed_maxdiff"] = float(np.abs(refK - mineK).max())
        fid["PASS"] = bool(fid["walk_maxdiff"] < 1e-13
                           and fid["K_placed_maxdiff"] < 1e-13)
        print(f"[1] 构造保真(vs 冻结实现): walk Δ={fid['walk_maxdiff']:.1e} "
              f"K Δ={fid['K_placed_maxdiff']:.1e} -> "
              f"{'PASS' if fid['PASS'] else 'FAIL'}")
    else:
        fid["PASS"] = True
        print("[1] 构造保真: 非 numpy 后端,跳过逐位对拍(验收口径在 numpy)")
    out["fidelity"] = fid

    # -- 2) 冻结点应 lawful --------------------------------------------------
    t1 = time.time()
    r0 = evaluate_rule(FROZEN_POINT)
    dt_rule = time.time() - t1
    out["frozen_eval"] = r0
    out["seconds_per_rule"] = dt_rule
    print(f"[2] 冻结点 evaluate({dt_rule:.1f}s/rule): "
          f"lawful={r0['lawful_tensor']}  gates={r0['gates']}")
    print(f"    λ={r0['damping']['lam']:.1f} (ρ_pred="
          f"{r0['damping']['rho_pred']:.4f})  j5_dev={r0['j5_dev']:.2e}  "
          f"certKTT={r0['cert_KTT']:.1e}  sv3={r0['sv3']:.3f}  "
          f"ttm={r0['tt_match']:.4f}  "
          f"relC尾={r0['constraint_monitor']['relC_tail_max']:.1e}")

    # -- 3) 炮参数应 not lawful ---------------------------------------------
    cann = {}
    tests = [
        ("F1_double_cone", dict(params=dict(FROZEN_POINT, dtheta=0.4)),
         "J5"),
        ("F2_integer_placement", dict(params=FROZEN_POINT,
                                      placement="integer"), "constraint"),
        ("F3_partial_slave", dict(params=FROZEN_POINT, slave_cov="partial"),
         "constraint"),
        ("F8_static_carrier", dict(params=FROZEN_POINT, carrier="static"),
         "Z_sector"),
    ]
    all_fire = True
    for name, kw, want in tests:
        pa = kw.pop("params")
        r = evaluate_rule(pa, **kw)
        broken = [g for g, v in r["gates"].items() if not v]
        fired = (not r["lawful_tensor"]) and (want in broken)
        all_fire &= fired
        cann[name] = {"lawful": r["lawful_tensor"], "broken_gates": broken,
                      "want_broken": want, "fired": fired}
        print(f"[3] {name}: lawful={r['lawful_tensor']} broken={broken} "
              f"(要求含 {want}) -> {'FAIL as required' if fired else '炮哑!'}")
    out["cannons"] = cann

    ok = bool(ok_hash and fid["PASS"] and r0["lawful_tensor"] and all_fire)
    out["selftest_PASS"] = ok
    out["total_seconds"] = time.time() - t0
    print("=" * 72)
    print(f"自测总判定: {'PASS' if ok else 'FAIL'}   "
          f"({out['total_seconds']:.0f}s;{dt_rule:.1f}s/rule)")
    if write_json:
        def _san(o):
            if isinstance(o, dict):
                return {k: _san(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [_san(v) for v in o]
            if isinstance(o, np.ndarray):
                return _san(o.tolist())
            if isinstance(o, (float, np.floating)):
                f = float(o)
                return f if np.isfinite(f) else str(f)
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.bool_,)):
                return bool(o)
            return o
        path = os.path.join(DIR, "cp1_v4_family_eval_selftest.json")
        json.dump(_san(out), open(path, "w"), indent=1, ensure_ascii=False)
        print(f"wrote {os.path.basename(path)}")
    return out


if __name__ == "__main__":
    res = run_selftest()
    raise SystemExit(0 if res["selftest_PASS"] else 1)
