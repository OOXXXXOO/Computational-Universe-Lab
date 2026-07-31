# V3-M0 scenario-response 统一重冻结设计

> 状态：**SIGNED / Phase A 仅授权实现**
> 日期：2026-07-31  
> 适用范围：Task 12–17 的 C05–C19 application success lane  
> 不改变：北极星、三坐标定义、既有数值阈值、Fejér 候选阶数、GPU 解锁顺序

## 1. 为什么必须一次重冻结

现有 ParentFreeze 与 production schema 之间存在四个不可通过调阈值修复的接口错误：

1. C05 以 `δ=π/T` 改变单一 eigenphase，并以恒等 source/readout 期待有限阶
   Fejér 响应乘以 `-1`。对全部冻结
   `T∈{256,512,1024,2048,4096,8192}`，
   `|f_T(π/T)+1|>1.5`，所以旧 phase 预言不成立。
2. C07 只有一个 `BLOCK_SUCCESS` scenario，却要求同一个 scalar
   `chi_extra` 和 `d_proc_sq` 同时等于 `(0,1)`；一份 block 无法表达两个实验。
3. C12 要求逐 momentum 的 `inc(k)/ν_inc(k)`、raw/noise/relative-gap 双门；
   现有 `ResponseBlockOperatorSpec` 只有固定 incidence 和字符串 normalizer ID，
   evaluator 也没有保存 raw curvature response。
4. C15 旧 Parent 预言把几何谱写成了不符合冻结公式的值，并把四个 scenario
   压成一个 case audit。正确的 C15–C17 校准共有七份 scenario audit。

因此本次只允许一次 Parent refreeze；禁止连续打补丁形成多个相互不兼容的 authority root。

## 2. 权威 DAG

每个 success scenario 的唯一合法链为：

```text
VerifiedParentFreeze
  + VerifiedWindowThresholdCalibration
  -> VerifiedCalibrationApplicationPermit
  -> VerifiedScenarioMaterialization
     （私下绑定 live actual / matched-ablated VerifiedFactory）
  +  VerifiedScenarioResponseProtocol
  -> actual / matched-ablated VerifiedPrestructureAuthority
  -> actual / matched-ablated VerifiedTransition
  -> actual + matched-ablated VerifiedDynamicsCertificate
  -> VerifiedCertificateBackedQualification
     + actual-only VerifiedEndpointReferenceOutcome
     + actual-only VerifiedEndpointShellOutcome
  -> VerifiedPairedResponseOutcome（两支共享同一 run protocol 与 actual shell）
  -> VerifiedV3M0ControlApplicationEvidence
  -> actual / matched-ablated VerifiedResponseBlock
  -> causal / geometry / sigma audit
  -> Task 17 aggregate
```

任何 digest、raw dataclass、孤立 recipe 或 permit 都不能替代上一层 live opaque capability。
构造失败、动力学证书失败、endpoint shell 不唯一、响应 null/grey 或证据缺字段均按原
typed termination 传播，不得生成 success block。
endpoint reference/shell 只允许从 actual transition/certificate 产生；matched-ablated
不得重寻 shell。paired response 在同一 scenario protocol 上原子消费两支 certificate、
qualification 与这份 actual shell；两支 branch block 必须共享同一
`endpoint_shell_outcome_sha/paired_response_sha`。

## 3. `ApplicationScenarioResponseProtocol`

新 protocol issuer 必须原子消费 live `VerifiedScenarioMaterialization`（其中递归绑定
live permit、精确 scenario DAG、已重放 recipe、两支 factory 与 construction trace），
且在首次时间演化前完整自哈希。至少冻结：

- `materialization_sha/permit_sha/application_spec_sha/scenario_id/scenario_sha/recipe_sha`；
- `construction_trace_sha`、两支 `factory_sha` 与两支 effect digest；这些摘要必须与
  materialization 中递归哈希的对应对象逐位一致，禁止跨 construction splice；
- `selected_fejer_order`、共同 `state_schema_id/channel_order/spatial_shape`、response
  grid、source/readout bridge grid、`source_readout_bridge_steps`、reference reciprocal
  index、`source_trial_vectors` 与 `bridge_tolerance`；
- permit 继续冻结 case-level 公共最大 source/readout basis；scenario protocol 只冻结
  由该公共 basis 机械派生的 `source_injection_isometry` 与
  `readout_coisometry`。两者必须逐列/逐行证明为公共 basis 的子选择或冻结线性组合，
  并绑定共同 state schema；不得把 scenario-specific basis 偷换回 permit；
- 每个 momentum 的 phase band 与 `expected_shell_rank`；
- source、h、curvature metric whiteners；
- `curvature_incidence_by_k`；
- 正的、有限的 `curvature_normalizer_by_k` 以及解析 derivation ID；
- C15–C19 所需的可选几何 bundle：
  `kernel_basis/physical_quotient_map/physical_quotient_metric/
  target_physical_representatives`；C16 还必须冻结 `coverage_control`，C17 还必须冻结
  `undressed_response_representatives/gauge_basis/gauge_amplitude/
  expected_graph_rank/analytic_graph_singular_values/
  fejer_graph_slope_formula_id/expected_actual_raw_graph_singular_values/
  expected_ablated_raw_graph_singular_values`；C17 的 target representatives 必须由两支
  共享，禁止把 response dressing 偷换成 target dressing；这些字段全部进入 geometry
  bundle SHA，并由 protocol SHA 递归绑定；
- protocol body SHA。

protocol 不得读取响应值、奇异值、审计 verdict 或 caller 数字。同一 scenario 的
actual-only endpoint reference/shell 与两支 paired response 必须共享同一
`J/P_h/run spec`；禁止另造未参与 response 的高参与 probe 掏空 participation 门。几何
bundle 必须先于响应冻结；允许从 Parent 参数和解析 recipe 公式派生，禁止从 measured
response 反推。

公共 basis 与 scenario selector 的矩阵方向固定为：

```text
B_source : (n_common_source, n_state)       # permit rows
C_source : (n_common_source, n_scenario_source)
J_source = B_sourceᵀ C_source               # state injection

W_readout : (n_common_readout, n_state)      # permit BasisManifest raw rows
B_readout = conj(W_readout)                  # executable permit coisometry
C_readout : (n_scenario_readout, n_common_readout)
P_readout = C_readout B_readout              # executable state coisometry
```

并逐次验证
`C_source†C_source=I`、`C_readout C_readout†=I`，谱范数残差均 `≤1e-12`。
`C_readout` 明确定义在可执行 coisometry 上，不直接作用于 raw manifest row；若同时保存
scenario `BasisManifest`，其 raw rows 必须机械等于 `conj(P_readout)`。`W_readout`、
`B_readout`、selector 与派生后的 `J_source/P_readout` 都进入 protocol SHA，禁止用当前
实 identity basis 恰好看不出共轭差异来省略这一步。

## 4. `ResponseBlock` v2

每个 block 仍只对应一个 branch，但新增不可省略的 authority binding：

- `control_case_id/scenario_id/scenario_sha/permit_sha`；
- `application_evidence_sha/scenario_response_protocol_sha`；
- `endpoint_shell_outcome_sha/paired_response_sha`；
- 逐 `k` 的 raw h response；
- 逐 `k` 的 raw curvature response
  `inc(k)·H(k)`；
- 逐 `k` 的 normalized curvature response
  `inc(k)·H(k)/ν_inc(k)`；
- raw norm、noise norm、relative gap、active/curvature rank；
- scenario 几何 bundle（若该 scenario 需要），并绑定其 SHA。

五个派生矩阵必须保持任务书冻结的机械链，不得全部改由 curvature response 产生：

```text
canonical scenario sources + source metric
  -> Q_all
raw h response + physical-h metric + absolute h signal gate
  -> Q_active (=Q1)
raw/normalized curvature response + raw-noise/relative-gap gates
  -> V_curv
Q_curv = Q_active V_curv
S_curv = orth(W_h R_h Q_curv)
```

因此 raw/normalized curvature 只支配 curvature rank 与 `V_curv`；它不能替代独立的 h
activation gate，也不能重定义 `Q_all/Q_active/S_curv`。C12 的
absolute/raw-noise/relative-gap 三项均需有数值 margin；任何一项 grey 或不满足均不得
签发 block。

## 5. Parent scenario 修正

### 5.1 C05

保留 phase 与 scalar-gain 两个 scenario，但删除“单 eigenphase offset”规则。
新规则使用等谱 shell 内的 projector orientation：

- phase scenario：两个 branch 的响应子空间相同，选择相反 orientation，使辅报响应比
  为 `-1`；
- gain scenario：冻结 evaluator 约定
  `gain_ratio=||Y₀||_F/||Y₁||_F`
  （`Y₀=matched-ablated`、`Y₁=actual`），并令该比值为 `2`；不得只写一个无分子分母
  方向的“投影权重比 2”；
- 两者的主 survival 谱均为全 `1`。

纯二维解析核
`M_θ=iP_θ-i(I-P_θ)` 已给出有限 `T` 恒等比值；production 仍必须把它编译为
支撑半径与 `L` 无关的实局域 canonical shear，而不能把投影写进时间步。

这里的 runtime `Primitive` 是
`destination(x) += coefficient·source(x+offset)` 的**标量有序更新层**，不是可单独
观测或重复执行的一次物理时间步。`realspace_step_factory` 的一步严格定义为 recipe
冻结顺序中的完整 layer composite；酉性、辛性、reality 与谱门均对该完整一步及其
Laurent symbol 判定。若干 scalar layers 共同实现一个 canonical rotation/swap 时，
必须由连续 step ID、完整有序 tuple 与 recipe SHA 绑定；禁止截取中间层后宣称得到
另一条合法动力学，也禁止把“完整 composite 辛”误报为“每个 scalar layer 分别辛”。

### 5.2 C07

拆成两个 success scenario：

- `constructive`：`survival=1`、`chi_extra=0`、`d_proc_sq=0`；
- `destructive`：actual 与 matched-ablated 都必须越过 signal line，且两者 observer
  子空间正交，从而 `survival=0`、`chi_extra=1`、`d_proc_sq=1`。不得用 ablated
  null response 冒充 destructive；该情形会得到 `chi_extra=0` 且 Procrustes undefined。

两个 scenario 各自拥有从 permit 公共 basis 派生的 source injection/readout
coisometry、protocol 与 block，不得另换一份未绑定 basis，也不得在 case-level scalar
中保存二元向量。

### 5.3 C12

scenario operation DAG 必须显式冻结：

- response momentum 列表；
- 每个 `k` 必须非零并在冻结的第一 Brillouin 域内；
- `inc(k)` 的解析 family ID；
- 显式公式 `ν_inc(k)=4Σ_j sin²(k_j/2)>0`、解析 formula ID 与逐 `k` fp64 wire；
- `k→0` 时 normalized operator 的 IR 极限证书；
- 预期 curvature mode count；
- raw-noise absolute threshold 与 relative-gap threshold 的既有冻结引用；
- 逐 `k` raw spectrum、raw bridge noise、absolute margin 与 relative-gap margin。

不得用 `normalizer_id="synthetic-identity-v1"` 冒充逐 `k` 除法。

### 5.4 C15–C17

C15 的**解析理想谱与阈值侧预言**为：

| scenario | active rank | ideal `g` spectrum | ideal `c` spectrum |
|---|---:|---|---|
| full-h | 4 | `(1,0,0,0)` | `(1,1)` |
| low-rank-tt | 1 | `(0)` | `(0,1)` |
| tt | 2 | `(0,0)` | `(1,1)` |
| tt-plus-row | 3 | `(1,0,0)` | `(1,1)` |

C16 的 low/high 各是一份 unary scenario audit；C17 quotient-gauge 是一份 paired
before/after scenario audit。Task 14 calibration 因而严格消费七份 scenario audits：
C15 四份 unary、C16 两份 unary、C17 一份 paired。它们至少消费八个 branch blocks
（C15/C16 各一块，C17 两块）和三个 live case permits（按 `4/2/1` 复用），不消费三个
case-level 数值摘要。每份 block 的 scenario protocol 必须给出自己的 basis
子选择/coisometry。

有限 `T` 下允许出现远离 grey band 的窗口泄漏；Parent 的 ideal `0/1` 只生成
`below/above` side label，不能被当成 measured spectrum 的逐位相等断言。以当前非循环
解析 bundle 做的 T=256 预飞中，full-h 次大 `g≈0.009393`、TT 的理想零
`g≈0.001647`，均仍严格落在 `g<0.04` 的 below 安全侧。

C15–C17 只共用四通道 state schema 与 rank-2 shell 合同。C15/C16 共用非循环
rank-2 positive-frequency carrier；C17 使用同一状态空间内
专用的 on-site `diag(J,-J)` rank-2 blind carrier，再由 `θ=atan(8)` 的 on-site
two-mode canonical conjugation产生 graph dressing。三者的 Parent
`expected_shell_rank` 都必须由旧值修正为 `2`。两 k 仍逐位实跑，C17 不得因 symbol
k-independent 而省略任一点；所有候选 T 必须逐项通过 rank/graph 合同、两支完整
composite 的 unitary/symplectic/reality 门，以及 `L=8/16` realspace factory↔symbol
对拍。几何 target 与 quotient 在运行前冻结。

C17 的 `a=8` 是 graph slope，不是未归一化 raw response 差。对两 k 的 unitary Fejér
response 与 isometric source/readout，每支 vertical-stack operator 满足
`||Y_branch||₂≤√2`，所以单位 gauge direction 下
`||Y_actual-Y_ablated||₂≤2√2<8`；要求 raw `ΔY=8g` 会把合同变成空集。合法构造必须令
`θ=atan(a)`（或逐位等价、由 Parent `a` 机械派生的解析参数）进入 actual 的
target-conditioned 局域 canonical graph rotation；matched-ablated 删除这些 slots，其
解析 shell 给出 undressed graph，但 finite response 仍须保留并审计 Fejér leakage。审计
从两支**真实** finite response 的 active subspace 构造
basis-invariant graph operator。本次 Parent 必须把旧 rank-1 `3×2` logical gauge effect
重冻结为 `expected_graph_rank=2`，并在 response 前冻结正交满秩
`T∈ℂ^{8×2}`、`G∈ℂ^{8×2}`，满足 `T†T=G†G=I`、`T†G=0`、`Π_phys G=0`。解析
positive-shell frame 必须满足 `U_shell=(T+8G)/√65`，故
`sv(A_shell)=(8,8)`。

scenario 的共同 source 必须冻结为 actual analytic shell
`J=U_shell=(T+8G)/√65`；因此 actual endpoint participation 为 `1`，不需要也不允许另造
endpoint probe。有限 Fejér 窗的负频带系数 `r_T=f_T(π)=1/(T+1)` 使两支 raw slope
严格预言为

```text
actual:          a₁,T = 8
matched-ablated: a₀,T = 8r_T = 8/(T+1).
```

这不把 matched analytic shell 的 graph rank `0` 改写成有限窗 `0`；后者有确定 leakage。
公式、derivation ID 和 selected-T 两支 fp64 wire 在 response 前冻结。对两支实际
finite-response active frame `U_b,T∈ℂ^{8×2}`，分别先过
`max_i|σ_i(T†U_b,T)-1/√(1+a_b,T²)|≤1e-12`，再机械计算
`A_b,T=(G†U_b,T)(T†U_b,T)⁻¹`；要求两支
`max_i|sv_i(A_b,T)-a_b,T|≤1e-12`，并要求
quotient 后 `c` 谱逐位漂移 `≤1e-12`。`target_physical_representatives` 在两支间必须
逐位相同。`(T+8G)/√65` 是解析正交 frame，而 `T+8G` 只是 physical-normalized canonical
graph representative，二者都不是 raw `Y`；bundle 只能从 Parent/DAG/解析 projector
预响应派生 `T/G/A`，不得把 measured `U` 写回 bundle。不得通过只更换 target
representative、逐列相位对齐或 metadata amplitude 冒充该 paired 审计。
本 scenario 的 `kernel_basis` 必须机械等于 `orth([T,G])`（`T=TT`、`G=gauge`），而
`Π_phys` 只商掉 `G` 并保留 `T`，防止 coverage 不变但 `g` 谱语义漂移。

## 6. 其余 success lane 的最小预言

| case | scenario 级必须复现的量 |
|---|---|
| C06 | full-rank 非标量内部混合；survival 全 1，`kappa_map<1` |
| C08 | matched ablation 精确少一维；survival 恰有一个补零 |
| C09 | quotient 前后 pure-gauge dressing 不改变 survival 谱 |
| C10 | full-source readout 捕获 actual-inactive 的正交新模式，`chi_extra=1` |
| C11 | null/grey 仍走 typed termination；signal success 的主 survival 为 1 |
| C18 | actual 与 ablated 分别做 unary geometry/σ；独立 ablated source 方向不得漏报 |
| C19 | full-positive shell 通过白化/coisometry 前提后触发 observer-collapse |

C18 的新方向若在冻结窗口下落入 off-band，则本 scenario 失败，不得仅凭 transition
存在而签 PASS。C19 也必须由实际 endpoint shell 和 response 证明，不接受 recipe 标签。

## 7. 实施顺序

签发分成两个明确阶段，禁止互相等待或把 provisional root 当 authority：

1. 阶段 A：本设计经独立复审后可单独改为 `SIGNED`，它只授权实现，不签发增量勘误或
   Parent root；
2. 依本设计生成带 `PROVISIONAL_NOT_ISSUED` 状态的完整 Parent candidate diff、raw
   preflight 与攻击测试；此时增量勘误继续保持 `DRAFT`，candidate 不得被 permit issuer
   接受；
3. 独立复审 candidate Parent diff 后，在**同一个原子提交**中将增量勘误改为 `SIGNED`、
   把其最终 SHA 写入 Parent，并完成唯一一次 Parent root refreeze；提交后重放
   doc/Parent SHA 与 negative tests，禁止保留中间权威 root；
4. 实现 scenario protocol 与 materialization hydration/attack tests；
5. 实现 endpoint、paired response、application evidence 与 permitted block issuer；
6. 实现 C05–C19 scenario 数值预言；
7. 重校准 survival 与 geometry/coverage threshold authority；
8. Task 17 逐 scenario 聚合并执行 20 controls、9 invariants；
9. 全量 V3-M0 验证后才可写 `READY-V3-M1-ANCHOR-CERTIFICATION`。

## 8. 必须保持 RED 的攻击

- raw/resigned protocol、evidence 或 block 替代 live capability；
- scenario/permit/Parent/T/grid/branch 交叉拼接；
- endpoint participation 使用不同于 paired response 的 `J/P_h/run spec`；
- 从 measured response 构造 geometry target；
- caller 传入 incidence、normalizer、metric、threshold 或预言值；
- C05 旧 `π/T` phase-offset 方案；
- C07 单 scenario 承载两套 scalar 结果；
- C12 固定 incidence、未除 `ν_inc(k)` 或未保存 raw-gap；
- C15 rank-1 shell；
- C18 off-band 新方向；
- 逐 `k` 投影或全局 FFT 投影进入时间步。

## 9. 签发条件

本设计只有同时满足下列条件才可改为 `SIGNED`：

- C05 有纯矩阵有限阶解析/数值回归，并有可编译的局域 real-space recipe；
- C06–C12、C15–C19 的 transition-only recipes 全部明确不签 scientific evidence；
- C15 rank-2 carrier 在所有冻结 `T` 上给出正确 response ranks；非循环、预响应冻结的
  解析 geometry bundle 在所有冻结 `T` 上给出正确 side labels 和正 margin；
- C16 low/high 必须产生不同、可重放的 coverage 几何语义；C17 的 gauge amplitude
  必须按 §5.4 的解析/有限窗 graph-slope 合同进入实际 dressed/undressed operator 与
  response，而不是只写 metadata、用极限值冒充有限 T 值，或要求不可达的 raw
  `ΔY=8g`；
- geometry recipe verifier 覆盖 resigned tensor、scenario/control 交叉拼接和
  Parent/recipe 重签攻击；
- 至少一名独立 reviewer 对 authority DAG、Parent 修正和无循环性给出 PASS；
- `ruff`、定向单测、`compileall` 与 `git diff --check` 通过。

## 10. Phase A 独立复审与签发记录

2026-07-31，独立 reviewer 对本设计、增量勘误 DRAFT、C05 构造提交
`e250555..e04b99e` 与 geometry 提交 `5cd31e1` 完成复审，裁定为
**PASS（仅授权实现）**：

- authority DAG 保持单向；geometry bundle、共同 source `J`、`T/G` 与 targets 均在
  response 前由 Parent、scenario DAG 和解析局域 recipe 派生，未从 measured response
  反推；
- C05 的完整局域 composite 通过 fp64 酉性、辛性、reality、endpoint participation、
  `L` 无关支撑与敌对容器/重签/splice 审计；
- C15/C16 的 rank-2 shell、有限窗 side/margin、不同 coverage target 与
  realspace↔symbol 对拍通过；
- C17 独立重算覆盖 `T=256…8192` 与两个冻结 `k`：actual endpoint participation
  最小为 `0.99999999999999978`；actual graph 为 `(8,8)`，matched graph 为
  `(8/(T+1),8/(T+1))`，最大 graph residual 为 `1.243e-14`；两支 physical-block
  residual `≤6.661e-16`；两支 coverage 谱均为 `(0.25,0.75)`，最大漂移
  `≤1.221e-15`；
- unknown/resigned tensor、Parent/control/scenario/rule、amplitude/raw/prediction、
  selected-T、target-from-dressed 与 raw-branch-swap 攻击均被拒绝；
- 独立 fresh 命令
  `python -m unittest tests.test_v3m0_geometry_application_recipes -v`
  为 `17/17 OK`，耗时 `141.064s`；实现者复跑为 `17/17 OK`，耗时
  `147.420s`，并通过两文件 `ruff`、`compileall rulespace_v3` 与
  `git diff --check`。

本签发只解锁 `PROVISIONAL_NOT_ISSUED` Parent candidate 的实现和攻击测试。增量勘误仍为
`DRAFT`，现有 Parent root、permit authority、scientific PASS、V3-M1/V3-M2、pilot 与
GPU 权限均不改变。
