# V3-M0 scenario-response 统一重冻结设计

> 状态：**DRAFT / 待独立复审**  
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
  -> VerifiedScenarioResponseProtocol
  -> actual / matched-ablated DynamicsCertificate
  -> actual / matched-ablated EndpointShellOutcome
  -> VerifiedPairedResponseOutcome
  -> VerifiedV3M0ControlApplicationEvidence
  -> actual / matched-ablated VerifiedResponseBlock
  -> causal / geometry / sigma audit
  -> Task 17 aggregate
```

任何 digest、raw dataclass、孤立 recipe 或 permit 都不能替代上一层 live opaque capability。
构造失败、动力学证书失败、endpoint shell 不唯一、响应 null/grey 或证据缺字段均按原
typed termination 传播，不得生成 success block。

## 3. `ApplicationScenarioResponseProtocol`

新 protocol 必须由 live permit、精确 scenario DAG 与已重放 recipe 机械派生，且在首次
时间演化前完整自哈希。至少冻结：

- `permit_sha/application_spec_sha/scenario_id/scenario_sha/recipe_sha`；
- `selected_fejer_order`、response grid、bridge grid、reference reciprocal index；
- scenario-specific `source_injection` 与 `readout`，两者必须绑定共同 state schema；
- 每个 momentum 的 phase band 与 `expected_shell_rank`；
- source、h、curvature metric whiteners；
- `curvature_incidence_by_k`；
- 正的、有限的 `curvature_normalizer_by_k` 以及解析 derivation ID；
- C15–C19 所需的可选几何 bundle：
  `kernel_basis/physical_quotient_map/physical_quotient_metric/
  target_physical_representatives`；
- protocol body SHA。

protocol 不得读取响应值、奇异值、审计 verdict 或 caller 数字。几何 bundle 必须先于
响应冻结；允许从 Parent 参数和解析 recipe 公式派生，禁止从 measured response 反推。

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

`q_all/q_active/v_curv/q_curv/s_curv` 只从 normalized curvature response 与冻结 metric
重算。C12 的 absolute/raw-noise/relative-gap 三项均需有数值 margin；任何一项 grey
或不满足均不得签发 block。

## 5. Parent scenario 修正

### 5.1 C05

保留 phase 与 scalar-gain 两个 scenario，但删除“单 eigenphase offset”规则。
新规则使用等谱 shell 内的 projector orientation：

- phase scenario：两个 branch 的响应子空间相同，选择相反 orientation，使辅报响应比
  为 `-1`；
- gain scenario：两个 orientation 的投影权重比为 `2`；
- 两者的主 survival 谱均为全 `1`。

纯二维解析核
`M_θ=iP_θ-i(I-P_θ)` 已给出有限 `T` 恒等比值；production 仍必须把它编译为
支撑半径与 `L` 无关的实局域 canonical shear，而不能把投影写进时间步。

### 5.2 C07

拆成两个 success scenario：

- `constructive`：`survival=1`、`chi_extra=0`、`d_proc_sq=0`；
- `destructive`：`survival=0`、`chi_extra=1`、`d_proc_sq=1`。

两个 scenario 各自拥有 source/readout/protocol/block，不得在 case-level scalar 中保存
二元向量。

### 5.3 C12

scenario operation DAG 必须显式冻结：

- response momentum 列表；
- `inc(k)` 的解析 family ID；
- `ν_inc(k)>0` 的解析 formula ID；
- 预期 curvature mode count；
- raw-noise absolute threshold 与 relative-gap threshold 的既有冻结引用。

不得用 `normalizer_id="synthetic-identity-v1"` 冒充逐 `k` 除法。

### 5.4 C15–C17

C15 正确预言为：

| scenario | active rank | `g` spectrum | `c` spectrum |
|---|---:|---|---|
| full-h | 4 | `(1,0,0,0)` | `(1,1)` |
| low-rank-tt | 1 | `(0)` | `(0,1)` |
| tt | 2 | `(0,0)` | `(1,1)` |
| tt-plus-row | 3 | `(1,0,0)` | `(1,1)` |

C16 的 low/high 各是一份 scenario audit；C17 quotient-gauge 是一份 before/after
scenario audit。Task 14 calibration 因而严格消费七份 live blocks/permits，不消费三个
case-level 摘要。

C15–C17 的 common carrier 使用 rank-2 positive-frequency shell；Parent 的
`expected_shell_rank` 必须由旧值修正为 `2`。几何 target 与 quotient 在运行前冻结。

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

1. 将本设计经独立复审改为 `SIGNED`；
2. 一次更新 Parent specs、prediction profiles、scenario IDs 与 Parent root；
3. 实现 scenario protocol 与 materialization hydration/attack tests；
4. 实现 endpoint、paired response、application evidence 与 permitted block issuer；
5. 实现 C05–C19 scenario 数值预言；
6. 重校准 survival 与 geometry/coverage threshold authority；
7. Task 17 逐 scenario 聚合并执行 20 controls、9 invariants；
8. 全量 V3-M0 验证后才可写 `READY-V3-M1-ANCHOR-CERTIFICATION`。

## 8. 必须保持 RED 的攻击

- raw/resigned protocol、evidence 或 block 替代 live capability；
- scenario/permit/Parent/T/grid/branch 交叉拼接；
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
- C15 rank-2 carrier 在所有冻结 `T` 上给出正确 response ranks 与正确 `g/c`；
- 至少一名独立 reviewer 对 authority DAG、Parent 修正和无循环性给出 PASS；
- `ruff`、定向单测、`compileall` 与 `git diff --check` 通过。
