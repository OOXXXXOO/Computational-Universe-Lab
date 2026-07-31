<p align="center">
  <img src="../visualizations/assets/logo.png" alt="Computational Universe Lab" width="58%">
</p>

# v3 勘误草案：scenario-bound response 与 geometry 合同

*Computational Universe Lab · 2026-07-31 · 状态：DRAFT / 未签发 / 不生效*

## 0. 边界

本草案汇总 V3-M0 application response、causal 与 geometry 控制中已经实证的合同空集，目标
是只做一次 ParentFreeze refreeze。它不改变北极星、三坐标公式、数值阈值、claim ladder
或 GPU 禁行线；在独立复审和签发前，不得据此签 permit、block、threshold calibration 或
READY。

本文件是
`v3-勘误-application-scenario与typed-termination-2026-07-31.md`
（SHA-256
`63bcda7cb83c7d725b546e18fda41bfccfc69f4a204ddd05056ed58b1499577b`）
的增量勘误；除本文件明确修正的 success-scenario response 合同外，前件的 typed
termination、C20 analysis lane 与 fail-closed 条款继续生效。

## 1. 已确认的空集与反例

### 1.1 C15 旧谱不满足 Task 14 公式

Task 14 定义

```text
g = sv((I-P_kerC)S_curv)
kerC = TT ⊕ Gauge
```

且 SVD 按标准非增序保存。以 `H=TT⊕Gauge⊕Row` 的四个 scenario 语义直接计算，解析
理想谱与阈值侧预言必须是：

| scenario | source/curvature sector | ideal `g`（非增序） | ideal `c`（eigvalsh 非减序） |
|---|---|---|---|
| `full-h` | `TT₂⊕Gauge₁⊕Row₁` | `(1,0,0,0)` | `(1,1)` |
| `low-rank-tt` | `TT₁` | `(0)` | `(0,1)` |
| `tt` | `TT₂` | `(0,0)` | `(1,1)` |
| `tt-plus-row` | `TT₂⊕Row₁` | `(1,0,0)` | `(1,1)` |

旧 Parent 中的 `(1,1)`、`(0,1)`、`(1,1)`、`(1,1)` 不只是排序问题，而与
`kerC=TT⊕Gauge` 的语义相反。禁止修改公式或阈值迎合旧 tuple。

ideal `0/1` 只用于派生 below/above side label，不要求有限 `T` 的 measured spectrum
逐位等于 ideal tuple。当前非循环解析 bundle 在 T=256 的预飞给出 full-h 次大
`g≈0.009393`、TT 理想零 `g≈0.001647`；两者均远低于 geometry grey band 下沿
`0.04`。最终证据必须保存实测谱、signed margin 与 side label。

此外，两个 k 点上的 rank-one shell 最多给 direct-sum rank 2，不能承载 `full-h` rank 4。
C15 必须冻结 rank-two shell，同时保留四通道和两个 k 点。

### 1.2 case permit 与 scenario block 数量不一致

application scenario 勘误后，C15/C16/C17 分别有 `4/2/1` 个 `BLOCK_SUCCESS` scenario。
Task 14 的三块 case-level audit 无法逐位匹配七个 block。阈值证据必须是七项
scenario audit；三个 permit 可按 `4/2/1` 复用，但 scenario ID/SHA、construction、
evidence 与 block 必须逐项唯一绑定。

### 1.3 finite-T 泄漏使 identity source/readout 失效

当前 causal Fejér 多项式是单边三角窗。在 `T=256`、相差 `π` 的最远 off-band 模上仍有

```text
|f_256(π)| = 1/257 = 0.00389105058 > τ_sig=0.001
```

现有 C06–C12 identity source/readout 实跑还出现约 `0.00550278` 的 off-band 奇异值，
使 C07/C08/C10 均变成 full rank，原缺模、干涉和 extra-mode 预言失效。C18 的首个
局域候选也复现同一问题：第二奇异值 `0.00550278 > τ_sig`，因此该候选明确是 no-go，
不能签为控制通过。

C05 通过 eigenphase offset 构造 gain/phase 也会把比例绑到 `T` 相关的 Fejér scalar，
不能作为跨候选 T 的稳定控制。

### 1.4 C07 scalar/tuple 与 C12 per-k 仪器缺口

C07 当前只有一个成功 scenario，但 Parent 同时冻结二元
`chi-extra=(0,1)` 与 `procrustes-residual=(0,1)`；`CausalSpectrum.chi_extra/d_proc_sq`
各为单 scalar，接口为空集。应拆成 constructive/destructive 两个成功 scenario，各自
产生一次独立 scalar audit；不得用一个 scalar 冒充 tuple。

C12 要求逐 k 施加 `inc(k)/ν_inc(k)` 并保存 raw/gap 双门；当前 operator spec 只含固定
二维 incidence matrix 与 `normalizer_id`，k 循环没有施加 `ν_inc`，block 也没有 raw
unnormalized spectrum/gap 字段，因此不能审计该预言。

## 2. 统一修正原则

### 2.1 每个成功 scenario 冻结自己的 response 合同

每个 `BLOCK_SUCCESS` scenario 必须从 Parent operation DAG 机械派生并冻结：

```text
scenario ID/SHA
+ source basis / source trial vectors / source metric
+ readout basis
+ response grid / bridge grid / bridge steps
+ exact run spec
+ expected shell rank and phase band
+ operator/geometry bundle（如适用）
```

case permit 只提供校准、网格和公共最大 source/readout basis authority。每个 scenario
另冻结从公共 basis 机械派生的 source injection isometry/readout coisometry；不得另换
一份未绑定 basis，也不得用 case-level identity 选择覆盖 scenario 语义。actual 与
matched-ablated 必须共享同一冻结 run spec，branch-active selector 由各自 raw response
独立产生，不得复用 actual selector。

readout `BasisManifest` 保存的是 raw row `W`，执行约定仍按任务书取
`B=conj(W)`。scenario selector `C_readout` 左乘可执行 coisometry，
`P_readout=C_readout B`；若落盘 scenario basis，其 raw rows 必须为
`conj(P_readout)`。raw rows、执行共轭、selector 与最终 `P_readout` 均须入 protocol
SHA，不能利用实 identity fixture 省略共轭方向。

### 2.2 比例控制使用等谱 projector orientation

phase/gain、干涉、缺模与 extra-mode 应由等谱 shell sector 的 projector/source/readout
关系构造，使两支共享同一个 Fejér scalar，并让比例在逐 k、任意候选 T 上代数约掉。
禁止用 eigenphase offset 或事后调整 T 制造目标比例。

局域 recipe 中的 scalar runtime shear 只是完整 factory step 的有序 layer，不是独立
物理时间步。结构门必须验证完整 layer composite 的酉性、辛性、reality 与谱；recipe
必须以连续 step ID、有序 tuple 和自哈希冻结共同实现 rotation/swap 的 layer group。
不得截取非辛的中间 scalar update 冒充合法 transition，也不得把 composite 证书写成
逐 scalar-layer 辛性证书。

C05 推荐使用 rank-two 等谱 sector：以固定权重和 target-conditioned orientation 产生
代数可约掉共同 Fejér scalar 的 phase/gain。gain 的方向按任务书固定为
`gain_ratio=||Y₀||_F/||Y₁||_F=2`，其中 `Y₀=matched-ablated`、`Y₁=actual`；
完整系数仍须由独立数值预飞与复审冻结。

### 2.3 C15 rank-two 局域 carrier

当前可复核候选保持四通道、两个冻结 k，所有 primitive 是支撑 `{-1,0,1}` 内的实空间
canonical shear。正频 shell rank 2，两个 k 的 projector stack rank 4；C15 四个
scenario 分别冻结 4/1/2/3 列 source。

真实 `compute_fejer_filtered_response` 在 `T=256…8192` 给：

- active rank 始终为 `4/1/2/3`（`τ_sig=0.001`）；
- 最小 full-h active singular value 从约 `0.541220` 收敛到 `0.541196`；
- endpoint participation 最小约 `0.421281 > 0.25`；
- unitary、Fourier-symplectic、reality residual 均 `≤1e-12`；
- actual/matched-ablated 在 `T=256` 的响应谱范数差 `>0.12`；
- `L=8/16` real-space factory 与 Laurent symbol 对拍 `≤2e-12`，support 与 L 无关。

这些只是 construction/numerical preflight，不是 Task 14 authority。当前诊断函数为检查
可达性会用解析 recipe 的 finite response 构造比较基；该输出**永远不得**复制进最终
geometry bundle。最终 bundle 必须在响应运行前，由 Parent scenario + operation DAG +
解析 semantic basis 先验机械派生，禁止从 `MeasuredTransition`、`ResponseBlock`、
`S_curv`、`g/c` 或 candidate eigenvectors 反推。

### 2.4 C18 replacement：on-site direct-sum unary pair

§1.3 记录的 `0.00550278` 结论仍是首个 C18 候选的有效 no-go，不得删除或改写。替代
构造使用同一四通道状态空间与同一 source/readout：

```text
source J = [e_q0,e_q1]
readout P = [e_p0^T,e_p1^T]
actual M1 = diag(J2,I2)
matched-ablated M0 = diag(J2,J2)
```

其中 blind 层由两个 on-site `+π/2` canonical pair rotations 组成，
target-conditioned 层以 on-site `−π/2` rotation 精确抵消 mode 1；matched branch
机械删除 conditioned 三个 scalar shear。两支 primitive support 均为 `{0}`，与 `L`
无关。`new-axis-amplitude=1`、`observer=geometry-and-sigma`、两个 source axis、
operation kind/dependency/output 必须从 Parent DAG 严格提取；参数只进入 digest 而不控制
source/readout/tooth 的实现明确为失败。当前 closed form 只接受 exact amplitude `1`，
其它即使完整重签也 fail-closed。

对 `T=256…8192` 与 `k=π/4,π/2` 的真实 Fejér response：

- actual endpoint rank 为 `1`，participation 为 `0.5`；
- actual/matched active rank 始终为 `1/2`；
- actual 的第二 source 方向逐位精确为零；
- matched 两个 vertical-stack 奇异值从约 `0.704355` 收敛到 `0.707020`，远离
  `τ_sig=0.001`；
- actual unary `g≈(0)`、`c=(0,1)`，matched unary `g≈(1,0)`、`c=(1,1)`；
- fp64 unitary、symplectic、reality residual 均 `≤1e-12`；
- `L=8/16` real-space factory 与解析 on-site symbol 对拍 `≤2e-12`。

这些只清除 C18 construction/finite-response 可达性阻断，不是
`VerifiedResponseBlock`、unary geometry、`SigmaFit` 或 Task 14/15 authority。

### 2.5 C12 与 geometry bundle

C12 response spec 必须新增可重放的 per-k incidence/`ν_inc` wires（或完整解析 normalizer
spec），block audit 保存 raw/normalized spectra、absolute margin 与 relative gap。

geometry operator bundle 必须 scenario-bound，至少保存：

```text
application_scenario_id / scenario_sha
permit_sha / construction_sha
kernel_basis
physical_quotient_map / metric
target representatives
undressed response representatives / gauge basis / expected graph rank（C17 only）
analytic graph spectrum / Fejér graph formula ID / selected-T expected raw spectrum
derivation source ID / bundle SHA
```

public evaluator 不接受 caller matrices。C17 的两支必须共享同一
`target_physical_representatives`；dressed response graph 只能由 Parent 的 gauge
amplitude/sector 与解析局域 recipe 机械生成，且 quotient 前后 `c` 谱漂移 `≤1e-12`。
这里的 `a=8` 是 response subspace 相对冻结 physical/gauge decomposition 的
basis-invariant graph slope：actual 局域 canonical graph rotation 使用
`θ=atan(a)`（或解析等价参数），matched-ablated 给 undressed graph。解析 positive-shell
graph 的两条 slope 必须逐位为 `8`。它不是 raw
absolute difference `Y_actual-Y_ablated=8g`；后者与两 k unitary Fejér contraction 的
`||ΔY||₂≤2√2` 上界矛盾。只改 target representative 或只保存 amplitude metadata 均不算
C17 通过。

本次 C17 `expected_graph_rank=2`：预响应冻结
`T,G∈ℂ^{8×2}`，验证两者各自正交、`T†G=0`、`Π_phys G=0`，并验证解析
`U_shell=(T+8G)/√65`。同一 source/readout/run spec 必须用于 endpoint 与两支 response；
C17 共同 source 冻结为 actual analytic shell `J=U_shell`，所以 actual endpoint
participation 为 `1`。当前 Fejér 窗的负频带系数为 `r_T=1/(T+1)`，因此 actual raw
graph slope 保持 `(8,8)`，matched-ablated raw slope 为
`(8/(T+1),8/(T+1))`；matched analytic shell graph rank 仍为 `0`，不得把两者混写。
formula ID 与 selected-T 两支 expected wire 必须在 response 前冻结。对两支实测 active
frame `U_b,T`，必须先保存并通过
`max_i|σ_i(T†U_b,T)-1/√(1+a_b,T²)|≤1e-12`，再以
`A_b,T=(G†U_b,T)(T†U_b,T)⁻¹` 重算
`max_i|sv_i(A_b,T)-a_b,T|≤1e-12`。C17 `kernel_basis=orth([T,G])`，其中
`T=TT`、`G=gauge`；
`Π_phys` 只杀 `G` 并保留 `T`。旧 Parent
logical effect 的 rank-1 `3×2` gauge row 与该合同不一致，必须在唯一 Parent candidate
中显式 refreeze 为 rank-2 graph，不能只由 recipe 偷换。解析
`(T+8G)/√65` 与 physical-normalized `T+8G` 必须和 raw response 分字段保存；measured
active frame 不得反向进入预响应 bundle。

## 3. 预定迁移

本文件只在阶段 B 签发；此前 Parent 修改必须显式标成
`PROVISIONAL_NOT_ISSUED`，不得被 permit issuer 接受。签发版至少需要：

1. Parent refreeze C05、C07、C08、C10、C12、C15–C19 的 scenario response 合同；
2. C07 拆为 constructive/destructive 两个成功 scenario；destructive 两支都必须为
   signal 且 observer 子空间正交，禁止以 null branch 代替；
3. C15 shell rank 改为 2，并采用 §1.1 的 `g/c` tuple；
4. C15–C17 阈值校准改为七项 scenario audit：C15 四 unary、C16 两 unary、C17 一
   paired；至少消费八个 branch blocks，三 permit 按 `4/2/1` 复用；
5. ResponseBlock 绑定 permit、scenario、construction、application evidence 与 geometry
   bundle，paired branches 上述 authority 字段逐位相同；
6. 重新运行所有候选 T 的 endpoint、bridge、raw/gap、finite response 与 C15–C19
   geometry/unary/collapse 预飞；
7. 独立复审 raw 表、勘误正文、Parent diff 与 verifier negative tests 后，才允许签发。

签发动作与 Parent root refreeze 必须位于同一个原子提交：先以 provisional candidate
完成第 7 项复审，再把本文件最终 `SIGNED` SHA 写入 Parent 并只生成一个最终 root；禁止
在仓库历史中发布引用 DRAFT SHA 的中间 authority root。

## 4. 当前状态

本文件仍是 DRAFT。现有 ParentFreeze、permit、block、threshold calibration 与 V3-M0
READY 状态均不变；V3-M1、V3-M2、V3-M3 与 GPU 长跑继续锁定。
