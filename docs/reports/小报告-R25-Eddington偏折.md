# 小报告:R25 Eddington 光偏折——弱场偏折 = 2.00 因子在冻结静态井上的重放

*车道B,2026-07-24。R25 pre-M3 卡点⑤:在冻结卡点① step 的静态 Newton 井上重放
Eddington 弱场光偏折,补上阶段复盘 §2.4 "Eddington 尚未在 R25 构造上重放"这一缺项。
纯物理测量,跑在被证书的静态井上,不改任何构造。本报告只认领本文件声明的三条证书,
不代表 M3 进展,不宣告涌现;R25 = 存在性构造。*

- 脚本:`experiments/r25_eddington.py`(sha256 `3b391201c31c2ce5ced7c25abed9bc466fb3f8a2da2cb67710a13748bf9529f0`)
- 结果:`data/results/r25_eddington_results.json` — **status: PASS(三证书)**
- 图:`visualizations/figs/r25_eddington.png`(偏折-b、1/b 标度、Eddington 因子三联图)
- 冻结继承(只读 import,不改):
  - `r25_static_newton.static_field_local` / `gaussian_lump` — C3 被证书的静态井(ratio_A=2.0)
  - `r25_realspace_step.trace_reverse_packed` / `step` — 冻结卡点① step(静态不动点绑定)
  - `rulespace_gpu.pathB_spin2._deflection` — 旧 Eddington Born 偏折裁判(原样复用)
  - `cp1_v4_L3.canary_numbers` — 冻结 Newton 读数
- fp64 numpy,确定性,全程 ~16 秒。

---

## 一、结论先行

1. **Eddington 因子 = 2.00(GR 张量值)。** 在 R25 被证书的静态 Newton 井上,弱场 Born
   光偏折的张量/标量比 = **2.0000**(N=64,跨 9 个碰撞参数 b 的散布仅 0.0009;C3 盒 N=24
   得 2.0025)。这与广义相对论一致(纯标量引力只给 1.00),关键判别通过。

2. **因子 2 的物理来源 = 空间度规扰动 hᵢⱼ ≈ h₀₀(张量结构)。** 直接测得
   **hₓₓ/h₀₀ = 1.0048**、空间迹平均 h_space/h₀₀ = 1.000。光子同时感受时间部分(牛顿势,
   给 1)与空间部分(再给 1)。反事实对照:人工置零 hᵢⱼ(纯标量度规)Eddington = **1.00**,
   凸显 2.00 完全来自 R25 度规的张量分量,不是数值巧合。

3. **与卡点① / C3 完全自洽,用同一被证书的井。** Eddington 跑的背景度规就是
   `r25_static_newton` 平衡场,其 Newton 商 ratio_A = 2.0、1/r 尾相关 0.9994,并且是冻结卡点①
   step 的精确源不动点(16 步 drift = 2.18e-14)。没有另造度规、没有调参。

## 二、证书数值表(fp64)

| 证书 | 门线 | 实测 | 判定 |
|---|---|---|---|
| **E5-1** Eddington 因子 | 2.00 ± 0.02 | **2.0000**(N=64,b-散布 0.0009);2.0025(N=24 C3 盒) | PASS |
| **E5-2** 偏折 ∝ 1/b | 相关 > 0.99 | **\|α\| vs 1/b 相关 0.9984**;佐证:势 1/r 尾相关 0.9994 | PASS |
| **E5-3a** ratio_A 自洽 | 2.00 ± 0.02 | **2.0000**(同一 C3 井 canary) | PASS |
| **E5-3b** 1/r 尾自洽 | ≥ 0.999 | **0.9994**(C3 盒)/ 0.9998(N=32) | PASS |
| **E5-3c** 冻结 step 不动点 | drift < 1e-9 | **2.18e-14**(卡点① step,16 步,含源) | PASS |
| 对照(可选) | 纯标量 hᵢⱼ=0 应 → 1.00 | **1.00** | — |

辅助读数:hₓₓ/h₀₀ = 1.0048;A/b 拟合 R² = 0.915(见 §四 系统项说明)。

## 三、方法学——复用旧 Eddington Born 裁判,不重新发明

一句话:**把 `r25_static_newton` 的平衡度规(reality-paired 后再 trace-reverse 回物理法向
度规 h)喂进旧的 `pathB_spin2._deflection`(Eddington Born 直线路径偏折 α = −∫ d(ln n)/dy dx),
Eddington 因子 = α(张量 n = 1−(h₀₀+hₓₓ)/2) / α(标量 n = 1−h₀₀/2)。**

- 背景度规:`hbar = static_field_local(ρ_zm)` → reality pairing `½(hbar+conj hbar)` →
  `h = trace_reverse_packed(·)` 得物理法向度规;取中心 z-切片。
- 张量折射率 n_t = 1 − ½(h₀₀+hₓₓ)·scale(光子感受时间+空间度规);
  标量折射率 n_s = 1 − ½h₀₀·scale(只感受时间/牛顿部分)。scale 把场压到弱场线性区
  (max|½h₀₀·scale| = 3e-4),Born 线性,比值与 scale 无关。
- 偏折用 `pathB_spin2._deflection`(注释 "Eddington Born, deflection")原样计算,
  Eddington = α_t/α_s。这正是 green_one `cp_newton` 里 `eddington_ratio` 的同一方法学,
  只是把背景度规从旧 leapfrog 几何核换成 R25 冻结静态井。

## 四、诚实边界与系统项

- **E5-2 的形状**:周期环面上远尾是屏蔽/Ewald Green 函数,不是纯 Coulomb,故 α·b 在窗口内
  漂移约 20%(A/b 拟合 R² = 0.915)。**认领的是单调 1/b 标度相关 0.9984 > 0.99**,并以 C3
  已证书的势 1/r 尾相关 0.9994 佐证;两者都过 0.99 门线。这是有限盒系统项,非病理。
- **测的是静态弱场**:Eddington 只在冻结静态井 + Born 近似上成立。**不含**动态 Newton、
  运动源、非线性 GR、近日点。不宣告 M3,不宣告涌现。
- **张量结构真实**:因子 2 不是硬编码——hₓₓ/h₀₀ = 1.0048 是直接测量,置零空间分量即回落
  到 1.00,证明 2.00 来自 R25 度规本身的 spin-2 分量。

## 五、给卡点④(联验合流)的接口

Eddington 测量已参数化为"背景度规 → 因子"的纯函数,可直接接卡点④的动态井:

```
experiments/r25_eddington.py
  build_frozen_well(N, sig) -> {h_phys, hbar, drive, ρ, ...}   # 可换成动态平衡场
  eddington_at_b(h_phys, N, b, ctr_z) -> (α_tensor, α_scalar, ratio)
  cert_E5(N, sig, b_list, frozen_step_bind) -> {eddington_median, checks, ...}
```

- **卡点④拿到动态 Newton 不动点 / 运动源平衡场后**,把该场的物理法向度规 `h_phys`
  (同样 reality-pair 后 trace-reverse)直接喂 `eddington_at_b` / `cert_E5(frozen_step_bind=False)`,
  即可在活体场上复验 E5-1/E5-2,无需改裁判。
- **运动源注意**:据卡点③符号层报告,运动源的实性不能用静态 `Re(h̄₊)` 收拢(会抹掉 h̄0i)。
  卡点④若用运动/动态场,须先按其镜像 sector 配方得到物理度规,再进本裁判——`build_frozen_well`
  的 reality-pairing 一行是唯一需要替换的接口点,`eddington_at_b` 之后不变。
- **联验合流**:E5(Eddington)与卡点①的 C3(Newton/不动点)、C4(稳定)在同一冻结 step、
  同一静态井上已互洽;卡点④只需把"静态井"升级为"同一次运行的动态井",三者即在一次运行内合流。

---

*认领范围:仅本文件三条证书(E5-1/2/3)。Eddington = 2.00 是 R25 冻结静态构造在弱场 Born 下
的实证张量-引力签名,不等于 M3、不等于规则空间涌现。R25 仍为 pre-M3 存在性构造。*
