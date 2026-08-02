# v3 设计勘误：B7 三路线并行对照与 production 收敛 v9

*Computational Universe Lab · 2026-08-03 · PI 已批准方向 · 书面复核待签 · DESIGN ONLY*

> 基线：`docsv3/v3-设计勘误-Parent-v3-B7至B10-production-chain-v8-2026-08-02.md`
> （raw SHA-256
> `e55445b50c2a885b8cd4a2ab1e9e3066c9632445d6860b508ab56a422f66f3ae`）。
> 实现源基线：commit `18b0d43`；其上 A1–A5、B0–B6 已实现，B7 production
> module 尚不存在。

本文覆盖 v8 的 B7 设计、实施入口以及“B1–B6 不变”的 preservation exception。
B8–B10、V3-M0 科学门、全部阈值、claim ceiling、artifact contract 与 GPU 锁不变。

## 0. 裁定

v8 把以下结构问题留给了实现阶段：

1. reference failure 后禁止产生 shell，但 `PairedResponseAttemptAuditV3.shell_outcome`
   又被声明为必填；
2. V3 顶层复用的 legacy `PairedResponseFailure` 无法表达 reference/shell failure，
   且使用旧 `ablated_*` 命名；
3. phase band、bridge tolerance、readout-calibration SHA、source trials 与 live permit
   identity 没有完整的 current Parent-v3 provenance。

v9 同时删除“V3 必须 branch-atomic 调度”的误读。任务书与 HEAD legacy core
的唯一阶段顺序均为：

```text
reference → shell
→ actual_response_values → matched_ablated_response_values
→ actual_bridge → matched_ablated_bridge
```

所有 response construction/schema 失败必须早于 repeated-executor bridge 失败。A/B/C
只比较同一执行历史的 wire 表示，不比较 scheduler、数值算法或物理 family。

v9 作如下裁定：

- 在任何 production authority 签发前，A/B/C 三种 response wire 可并行作隔离对照；
- 三路共享同一 provenance join、同一固定 scheduler、owner-neutral 数值叶与
  规范化 transcript；
- 三路从 transcript 编码开始隔离，均为 `NON_AUTHORITY`；
- 最迟在 B7 production record catalog、`Verified*` wrapper、B8 consumer 或 response
  artifact SHA 形成前，必须裁定唯一胜者；
- 只有胜者可进入 `rulespace_v3.application_response_v3`；败者只保留为实验反例证据。

三路数值叶必须逐位相同；任何科学读数差异均判为实现错误，不判为
“路线差异”。

## 1. 当前进展与权限

| 范围 | 当前实际状态 | v9 后的义务 |
|---|---|---|
| A1–A5 | 源码已在 `18b0d43` 基线实现 | P0 改写 Parent raw body 后必须 refreeze/replay/review |
| B0–B5 | 源码已实现，至 `5abee6f` | P0 后重放所有递归 SHA 与攻击测试 |
| B6 | 源码已实现于 `18b0d43` | P0 后重建两支 outcome/certificate 并复审 |
| B7 | 被 v9 重新打开 | production module absent |
| B8–B10 | 未实现 | 仍依 v8，在唯一 B7 收敛后才开始 |
| C1–C3 real P/S 与 V3-M0 run | 未执行 | 无 live signed Parent-v3 |
| V3-M1/M2/pilot/M3 preflight | 锁定 | 缺上游 READY/PASS |

`18b0d43` 自此只是 source/legacy-golden 基线，不是 P0 后的 authority root。
权威科学状态仍为：

```text
HALT-V3M0-WINDOW
READY-V3-M1-ANCHOR-CERTIFICATION NOT ISSUED
GPU SCIENCE PERMIT NOT ISSUED
```

`python -m rulespace_gpu.verify` 仍只是 backend smoke，不是 science permit。

## 2. 共享 P0：三路线不得复制的单一基线

### 2.1 Pre-issuance breaking refreeze

P0 是 B7 前的 breaking raw-wire 勘误，不是一个可保持旧 SHA 的 private patch。
精确 catalog operation 为：

| 对象 | operation | canonical owner | schema policy |
|---|---|---|---|
| `CurrentScenarioResponseContractV3` | `REPLACE_EXACT_SHA256` | `rulespace_v3.parent_v3_contracts` | 保留 `v3m0.current-scenario-response-contract.v3`，仅因其状态仍为 `PROVISIONAL_NOT_ISSUED` 且从未进入 P/S/artifact；旧 field-set body 全部拒绝 |
| `CurrentCurvatureNormalizerProtocolV1` | `ADD_ABSENT` | `rulespace_v3.parent_v3_contracts` | `v3m0.current-curvature-normalizer-protocol.v1` |
| `CurrentReadoutCalibrationSpecV3` | `ADD_ABSENT` | `rulespace_v3.parent_v3_contracts` | `v3m0.current-readout-calibration-spec.v3` |
| `_VerifiedApplicationMaterializationViewV3` | `PRIVATE_VIEW_EXTEND` | `rulespace_v3.application_materialization_v3` | 不改 raw materialization wire |
| owner-neutral response leaves | `PRIVATE_REFACTOR` | `rulespace_v3.response` | legacy public wire/schema 不变 |

该 replacement 沿用 v8 patch grammar，不新造 operation：

```text
json_pointer                = /record_catalog/CurrentScenarioResponseContractV3
operation                   = REPLACE_EXACT_SHA256
expected_prior_value_sha256 = 114dc1dad1a0fb24a253177d5daa83ff18acb38765b3bd76da8ed1d6f8d2c1ff
replacement_ref             = /p0_record_catalog_delta/CurrentScenarioResponseContractV3
```

prior digest 使用 v8 的 ordered-JSON 算法从 v6 effective catalog 重算。
`p0_record_catalog_delta` 由第 2.2–2.4 节的完整字段顺序机械生成，两个新 record
分别以标准 `ADD_ABSENT` 操作加入。P0 写代码前必须先以静态 contract test
证明 pointer、prior digest、replacement field order 和 add-absence 全部闭合。

该 replacement 会改变 Parent candidate/review/application/scenario SHA，并继而改变 B1
permit、B2 materialization 与 B3–B6 证据的递归 SHA。因此 P0 完成后必须按新 root
重放 A1–B6 定向测试与双复审；禁止 adapter、promotion、旧 SHA 白名单或兼容重签。

### 2.2 Current response authority

`CurrentScenarioResponseContractV3` 增加并递归自哈希：

```text
preregistered_phase_bands
reference_phase_band_source_id
expected_shell_rank_source_id
source_trial_generation_id
bridge_tolerance
bridge_tolerance_source_id
current_readout_calibration_spec
```

replacement 的完整 field order 固定为：

```text
response_contract_schema_version
contract_state
control_case_id
application_instance_id
scenario_id
basis_contract
dynamics_grid_derivation
metric_support_derivation
response_grid
response_reference_reciprocal_index
preregistered_phase_bands
reference_phase_band_source_id
expected_shell_rank_source_id
source_trial_generation_id
bridge_grid_derivation
bridge_tolerance
bridge_tolerance_source_id
geometry_bundle
current_readout_calibration_spec
runtime_construction_sha
actual_factory_sha
matched_factory_sha
operation_dag_sha
expected_actual_shell_rank
expected_matched_shell_rank
runtime_artifact_state
measurement_state
uses_global_fft_projection
uses_per_k_time_step_projector
response_contract_sha
```

上述顺序同时是 `p0_record_catalog_delta` 与 dataclass/payload 的唯一顺序；不允许
在实现时重排或额外添加 convenience field。

冻结 body 为：

```text
preregistered_phase_bands = ((π/2 - 1/8, π/2 + 1/8),)
lower endpoint fp64 bits  = 3ff721fb54442d18
upper endpoint fp64 bits  = 3ffb21fb54442d18
reference source ID       = analytic-quarter-turn-positive-band-v1
expected-rank source ID   = parent-v3-current-scenario-prophecy-v1
source-trial source ID    = c19-positive-frequency-coordinate-identity-v1

bridge_tolerance          = 1.0e-12
bridge tolerance bits     = 3d719799812dea11
bridge source ID          = v3m0-frozen-thresholds-bridge-tolerance-v1
```

phase band 的数学依据是
`docsv3/v3-勘误-application-scenario与typed-termination-2026-07-31.md` 的解析
quarter-turn 先验。运行时权威只是 current response contract 中的 exact fp64
body；文档与 `rulespace_v3.thresholds.BRIDGE_TOLERANCE` 只用于构造期回归对拍。
issuer/verifier graph 须闭包捕获上述 literal，不得在签后重读可重定向模块全局量。

contract 内 `source_trial_vectors` 的唯一 body 仍来自
`basis_contract.source_trial_vectors=I₁₀`；新 source ID 只冻结其解析生成规则。
bridge tolerance 须与两支 B6 `FullStateBridgeSpec.bridge_tolerance` 逐位相等，
但 B6 模块常量不反向成为 B7 权威。

### 2.3 Current readout calibration

`CurrentCurvatureNormalizerProtocolV1` 完整保存：

```text
protocol_schema_version = v3m0.current-curvature-normalizer-protocol.v1
normalizer_id = spin2-lattice-khat2-nonzero-v1
formula_id = nu-inc-4-sum-sin2-half-v1
derivation_id = 2-exp(+ik)-exp(-ik)-centered-second-difference-v1
spatial_shape = (8,)
response_grid_sha
ordered_reciprocal_indices = ((1,),)
ordered_momentum_values = ((0.7853981633974483,),)
ordered_momentum_fp64_bits = ((3fe921fb54442d18,),)
ordered_normalizer_values = (0.585786437626905,)
ordered_normalizer_fp64_bits = (3fe2bec333018867,)
zero_mode_policy = excluded-from-curvature-rank-and-scaling
protocol_sha
```

其复用仓库已冻结的公式/派生 ID，解析量为
`ν_inc(k)=4 Σ_j sin²(k_j/2)`。verifier 按 nested `ResponseKGridManifest` 顺序重建
`k_j=2π n_j/L_j`，逐值比较上述 fp64 bits，并要求 `response_grid_sha` exact
相等。normalizer 只在 `ν_inc(k)≠0` 的 response node 上使用。origin-only bridge
只保存有量纲 raw incidence error，不在 `k=0` 伪造除法；后续 spectrum/evaluator
必须对 response 与误差上界施加同一非零节点 normalizer。

`CurrentReadoutCalibrationSpecV3` 完整保存：

```text
spec_schema_version = v3m0.current-readout-calibration-spec.v3
derivation_id = c19-geometry-bundle-readout-calibration-v1
geometry_bundle_sha
source_metric_whitener
h_metric_whitener
curvature_incidence_operator
curvature_normalizer_protocol
curvature_metric_whitener
spec_sha
```

四个 tensor 分别逐位等于 current C19 geometry bundle 的
`source_whitener/h_whitener/incidence_q/curvature_whitener`。`incidence_q` 形状为
`6×10`，故 V3 raw bridge core 必须支持 `n_curv×n_h`；legacy square 路径的乘法顺序、
遍历顺序、dtype、bytes 与 SHA 不得改变。

```text
SourceReadoutBridgeAudit.source_metric_whitener_sha
    = current_readout_calibration_spec.source_metric_whitener.tensor_sha
SourceReadoutBridgeAudit.readout_calibration_spec_sha
    = current_readout_calibration_spec.spec_sha
```

不得把 `geometry_bundle_sha`、单个 tensor SHA 或 caller 文本代填 spec SHA。

### 2.4 `ResponseRunSpecV3` 的唯一字段来源

v9 覆盖 v8 的 `ResponseRunSpecV3` field catalog。每个字段只能从下表派生：

| run-spec field | 唯一 owner/source |
|---|---|
| `run_spec_schema_version` | literal `v3m0.response-run-spec.v3` |
| `parent_freeze_v3_sha` | exact Parent-v3 manifest |
| `permit_sha` | `view.permit.permit.permit_sha` |
| `materialization_sha` | B2 raw materialization |
| `window_calibration_v3_sha` | `permit.calibration.calibration_v3_sha` |
| `window_protocol_sha` | `permit.calibration.calibration_outcome.manifest.window_protocol.protocol_sha` |
| `window_selection_sha` | non-null `permit.calibration.calibration_outcome.selection.selection_sha` |
| `current_scenario_response_contract_v3_sha` | B2 materialization 内 exact current contract |
| `control_case_id/application_instance_id/scenario_id` | same current contract |
| `scenario_sha` | `permit.current_scenario_authority.scenario_authority_sha` |
| `selected_fejer_order` | permit 与 window selection 逐位一致的唯一 T |
| `state_schema_id/channel_order/spatial_shape` | current application authority，并与 basis/runtime body exact cross-check |
| `source_basis/readout_basis` | `basis_contract.scenario_source_basis/scenario_readout_basis` |
| `source_injection_isometry/readout_coisometry` | `basis_contract.source_injection/readout_coisometry` |
| `response_grid` | current response contract 内完整 `ResponseKGridManifest` |
| `source_readout_bridge_grid` | 两支 B5 authority 内逐位相等的 nested `BridgeKGridManifest` |
| `source_readout_bridge_steps` | current `BridgeKGridDerivationProtocolV1.bridge_steps`，并与两支 B5 exact cross-check |
| `reference_reciprocal_index` | current response contract |
| `preregistered_phase_bands/reference_phase_band_source_id` | current response contract |
| `expected_shell_rank/expected_shell_rank_source_id` | `expected_shell_rank = current_contract.expected_actual_shell_rank`；同时强制 `expected_actual_shell_rank == expected_matched_shell_rank == len(source_basis.vectors_wire) == len(readout_basis.vectors_wire) == 10`，source ID 取 current contract |
| `source_trial_vectors/source_trial_generation_id` | current basis contract + current response contract source ID |
| `bridge_tolerance/bridge_tolerance_source_id` | current response contract，并与两支 B6 spec exact cross-check |
| `current_readout_calibration_spec` | current response contract 内完整 nested body，不是单 SHA |
| `actual_bridge_grid_authority_sha` | actual B5 live authority body |
| `matched_ablated_bridge_grid_authority_sha` | matched-ablated B5 live authority body |
| `run_spec_sha` | 上述全部 exact body 的 canonical SHA |

caller 不得提交 run spec、grid、basis、T、trial、threshold、normalizer 或任一 SHA。

### 2.5 Live permit 与两支 grid lineage

`_VerifiedApplicationMaterializationViewV3` 增加 private-only `permit` 字段，返回
`_MaterializationAuthorityV3.permit` 的 exact live identity：

```text
view.permit is authority.permit
```

不得返回 raw clone，不改 `ApplicationScenarioMaterializationV3` wire。两支 B5
`BridgeGridAuthorityV3` 因 branch binding 不同而必然不等；只有它们内嵌的
`BridgeKGridManifest` body 必须 exact equal。两个 authority SHA 分别保存；SHA
交换、同形异 lineage 或 cross-graph wrapper 均在 raw B7 artifact 之前以 `CROSS_BRANCH`
失败。

### 2.6 Owner-neutral 数值叶与 legacy freeze

修改 `rulespace_v3.response` 之前，先在 clean `18b0d43` detached worktree 生成
legacy golden corpus。它覆盖 success 及 legacy enum 的全六失败：

```text
qualification_invalid
input_binding_invalid
actual_response_failed
ablated_response_failed
actual_bridge_failed
ablated_bridge_failed
```

每案保存 canonical UTF-8 bytes、literal SHA、callback trace、presence、FP64 bits、
`-0.0` 与 ordered leaf digest。fixture 固定为
`tests/fixtures/v3m0_b7_legacy_response_18b0d43.json`。capture 提交同时创建根层
`tests/test_v3m0_b7_legacy_golden.py`，在该 source-closure-covered test 中硬编码 fixture
raw SHA-256；测试必须先核对未解析 raw bytes SHA，再解析并对拍输出。
capture 提交后，修改 fixture 或其 SHA literal 都是可见的 source-closure 变更；后续
不得用改后代码重生基线。

`rulespace_v3.response` 只抽出：

```text
_select_endpoint_reference_from_raw
_track_endpoint_shell_from_raw
_build_fejer_branch_response_values_from_raw
_audit_source_readout_bridge_from_raw
_assemble_atomic_paired_response_attempt_from_raw
```

第五个 core 只组装已取得的 ordered raw prefix；不调度 callback。唯一 scheduler
固定为本文第 0 节顺序，无 owner profile、caller profile 或 dual scheduler。

V3 raw bridge leaf 的概念签名为：

```text
_audit_source_readout_bridge_from_raw(
  branch, factory_sha, transition_sha, dynamics_certificate_sha,
  run_spec_sha, bridge_grid, bridge_steps, source_trial_vectors,
  current_readout_calibration_spec, ordered_raw_differences
)
```

它不消费 `ControlRegistryEntry`、opaque wrapper 或全局 threshold。对每个 raw difference
`ΔR`，固定计算
`W_h ΔR W_s⁻¹` 与 `W_curv Q ΔR W_s⁻¹`；非零 response node 的
`ν_inc` 归一由后续 readout evaluator 对信号与误差上界同时施加。

legacy public path 仍先完成原 live authority join，再恰好委托同一数值叶一次。
七个 golden case 必须全部 bytes/SHA/trace 零差异。

## 3. 规范化 transcript 与共同 corpus

P0a 由单一 coordinator 在 fork 前冻结以下实验合同：

```text
schema ID       = experimental.v3m0.b7.normalized-transcript.v1
canonical owner = experiments.v3m0_b7_schema_lab.common
hash            = project canonical JSON + SHA-256
```

`NormalizedB7ExecutionTranscript` 的 exact fields 为：

```text
transcript_schema_version
corpus_spec_sha
case_id
environment_manifest_sha
provenance_fixture                    # complete nested raw body
response_run_spec_fixture             # complete nested raw body
reference_outcome                     # required
optional shell_outcome
optional actual_branch_attempt
optional matched_ablated_branch_attempt
optional actual_completed_response
optional matched_ablated_completed_response
terminal_tag                          # six first-failure tags or success
callback_trace
ordered_leaf_digests
experimental_sha
```

三路 encoder 必须保存同一批完整 nested raw bodies；禁止一路保存 body、
另一路只保存 SHA。`ordered_leaf_digests` 的每项固定为
`(leaf_id, call_ordinal, input_body_sha, output_body_sha)`，顺序只能是第 0 节的阶段顺序。
corpus spec 连同全部 case 列表、nested-body 规则、mutation 算法与 canonical
payload 先自哈希，A/B/C 不得修改。

七个 terminal tag 对应七个合法 corpus case。audit 只存在对应 branch attempt
内，不在 transcript 顶层复制。attempt 列中 `none` 表示该
attempt 已存在且 `failure=None`；枚举名表示 attempt 存在且保存该 failure：

| case | ref | shell | A attempt/failure | A values | M attempt/failure | M values | A audit | M audit | A response | M response |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| `reference_failure` | fail | – | – | – | – | – | – | – | – | – |
| `shell_failure` | pass | fail | – | – | – | – | – | – | – | – |
| `actual_response_values_failure` | pass | pass | `actual_response_failed` | – | – | – | – | – | – | – |
| `matched_response_values_failure` | pass | pass | `none` | pass | `matched_ablated_response_failed` | – | – | – | – | – |
| `actual_bridge_failure` | pass | pass | `actual_bridge_failed` | pass | `none` | pass | – | – | – | – |
| `matched_bridge_failure` | pass | pass | `none` | pass | `matched_ablated_bridge_failed` | pass | pass | – | – | – |
| `success` | pass | pass | `none` | pass | `none` | pass | pass | pass | pass | pass |

completed `SourceReadoutResponse` 只在两支 values 与两支 bridge 全部成功后组装。
`bridge_tolerance=1e-12` 在 B7 只是 run-spec provenance 与后续 calibration input，
不是 source/readout bridge 的终止门。合法 bridge audit 中的 dimensional error upper
无论是否超过该数值都进入 response，并在后续以
`noise_ref=max(null_max, bridge_max, eps_fp64·scale_ref)` 标定；只有 executor/type/branch
测量异常才是 `*_bridge_failure`。

transcript 不保存 issuance token、registry identity、`Verified*` wrapper 或 production
schema ID。upstream-invalid 在 transcript 构造前失败，因而不是第八个合法 case。

## 4. 三个并行方向

### 4.1 A：flat presence matrix

一份 paired attempt 直接保存 transcript 的 nullable slots、terminal failure 与 self-SHA。
优点是 record/hash 层最少、B8 解包最直接；风险是 raw dataclass 可构造较多非法
presence 组合，必须靠 exhaustive verifier 全部拒绝。

### 4.2 B：raw branch progress

因为 matched values 先于 actual bridge，B 不得伪造 branch-atomic outcome。其非 capability
raw record 为 `ResponseBranchProgressV3`：

```text
branch
optional response_values
optional bridge_audit
optional completed_response
optional branch_failure
progress_sha
```

pair 外层仍保存唯一 terminal failure。不得存在 `VerifiedResponseBranchProgressV3`
或单支 issuer；否则形成 half-pair capability。B 必须承担 outer failure、branch failure 与
progress presence 的额外一致性义务。

### 4.3 C：closed discriminated union

C 只保存七个闭合 terminal variant。每个 variant 的 payload shape 必须逐字段
等于第 3 节 presence 表。开放 append-only event list 明确禁止。

三路均使用隔离 domain：

```text
experimental.v3m0.b7.a-flat.*
experimental.v3m0.b7.b-progress.*
experimental.v3m0.b7.c-union.*
```

禁止占用路线相关的 `v3m0.*.v3` production ID。

## 5. P0a/P0b、D0 与 D1

### 5.1 并行依赖图

P0 拆成：

- `P0a-LAB-CONTRACT`：单一 coordinator 冻结 common transcript、corpus、mutation、
  comparison schema 与 B8 consumer skeleton；
- `P0b1-PROVENANCE`：唯一 production implementer 修改 Parent contract 与 materialization
  private view；
- `P0b2-NEUTRAL-LEAVES`：另一 implementer 在 golden 已捕获后抽取
  `response.py` private raw leaves。

P0b1/P0b2 文件不重叠，可与 P0a 并行。D0 只依赖 P0a；D1 必须等待
P0a、P0b1、P0b2 以及 P0 后 A1–B6 refreeze/replay/review 全部完成。

### 5.2 D0：wire semantics

D0 对七个合法 case 及同一冻结 mutation universe 运行三个 encoder，至少覆盖：

- 全部单字段 presence/tag mutation；
- outer/branch failure splice；
- 删除 first-failure 之前已成功的 raw body；
- 在 first-failure 之后注入下游证据；
- canonical round-trip/repeat 与 nested-body 换 SHA；
- synthetic upstream-invalid zero-transcript probe。

D0 不调用 authority issuer、不修改 `rulespace_v3`、不产生科学结果。

### 5.3 D1：owner-neutral leaf replay

D1 不使用尚不存在的 live signed Parent。它使用 fresh-process、test-private closed
graph，根为 P0 重放后的自洽 synthetic Parent/B1–B6 fixture。该私有 graph 中
`calibration_outcome.selection.selected_fejer_order`、permit、materialization 与 B3–B6 的 T
全部 exact 等于 `256`；任何不一致均 fail closed。这是一个完整自洽但非 production、
非 authority 的 synthetic selection，不是真实 window calibration 结果。D1 不回写
calibration，不解除 `WINDOW_UNRESOLVED`，不允许该 fixture 进入 P/S/artifact。

common harness 在固定 Python/NumPy/SciPy 版本、fp64、BLAS threads=`1` 与同一
environment manifest 下独立 capture 三次。每份 immutable transcript 再广播给全部
surviving encoder，形成 `capture × encoder` 交叉矩阵。encoder 永不直接调用 leaf
provider，因而 provider 波动不会被错归因于某路线。跨 worktree 只比较 raw
root/SHA/bytes，不比较 Python object identity。

## 6. 隔离、文件所有权与结果路径

所有 `git worktree` 命令只从主仓库根执行。实施计划的单 worktree 规则仅对
`NON_AUTHORITY` schema lab 开一次明示例外；production 修改仍只在
`.worktrees/v3m0-instrument` 进行。

coordinator 唯一拥有：

```text
experiments/v3m0_b7_schema_lab/common.py
experiments/v3m0_b7_schema_lab/compare.py
tests/fixtures/v3m0_b7_schema_lab_corpus.json
tests/test_v3m0_b7_schema_lab_common.py
```

三路只能分别修改：

```text
experiments/v3m0_b7_schema_lab/a_flat.py
experiments/v3m0_b7_schema_lab/b_progress.py
experiments/v3m0_b7_schema_lab/c_union.py
tests/test_v3m0_b7_schema_lab_a.py
tests/test_v3m0_b7_schema_lab_b.py
tests/test_v3m0_b7_schema_lab_c.py
```

D0 可从同一 P0a lab commit 建 A/B/C 独立 worktree。D1 则从“P0b 新 root + P0a
lab common”的单一 lab-integration commit 重建三 worktree。实验提交不合并到
production preparation branch；production 模块不 import 实验代码。
三个工作树路径固定为
`.worktrees/v3m0-b7-a`、`.worktrees/v3m0-b7-b`、`.worktrees/v3m0-b7-c`。

结果唯一路径为：

```text
data/results/experimental/v3m0_b7_schema_lab/
  d0_comparison.json
  d1_comparison.json
  selection_review.json
```

每份 JSON 都必须有 schema ID、route commit SHA、common corpus SHA、environment SHA、
metric-script SHA 与 self-SHA。

## 7. 分层 hard gates 与预冻结比较器

### 7.1 P0 hard gates（共同责任）

| ID | 判据 |
|---|---|
| P01 | pre-issuance replacement 后旧 field-set body 全部拒绝 |
| P02 | A1–B6 在新 root 上全链 replay，两支 B6 证据递归闭合 |
| P03 | phase/rank/trial/tolerance/readout provenance 全部从 current contract 派生 |
| P04 | live permit identity 与两支 B5/B6 lineage 拒绝 cross-graph/splice |
| P05 | legacy success + 六 failure 的 bytes/SHA/trace/FP64 bits 零差异 |
| P06 | raw leaves 调用顺序/次数固定，无 caller/global 数值权威 |

### 7.2 Encoder hard gates（A/B/C 公平比较）

| ID | 判据 |
|---|---|
| E01 | 六 first-failure + success 的七个 legal case 全部 exact replay |
| E02 | 共同 mutation universe 接受数为零 |
| E03 | first-failure 前所有成功阶段的完整 raw body 保留率 100% |
| E04 | outer failure、branch failure、attempt failure 与 presence 逐项映射唯一 |
| E05 | 每个 capture 的 ordered leaf/body digest 在三 encoder 间逐位相同 |
| E06 | canonical round-trip/repeat 确定，nested-body/tag/SHA splice 全部拒绝 |
| E07 | 无 half-pair wrapper、raw hydration、issuer、registry 或 caller profile |
| E08 | production import DAG 增量为零，实验代码不进 source closure |

### 7.3 Production-only gates（选定唯一路线后）

| ID | 判据 |
|---|---|
| R01 | upstream invalid 在 raw artifact 前失败，registry mutation/capability mint 为零 |
| R02 | 只有完整 pair success 才在一个临界区签一个 opaque pair capability |
| R03 | v8 B7 攻击矩阵 + v9 attempt/presence 矩阵全过 |
| R04 | B8 consumer 只消费唯一 production schema，无 adapter/dual issuer |
| R05 | B7–B10 完成后、P 之前以真实 live Parent 复放上述门 |

P0 门不计入 A/B/C 分数；D0 也不得将“没有 issuer”冒充为 R01/R02 PASS。

### 7.4 预冻结 comparison schema

`compare.py` 与 common corpus 同由 coordinator 在 route fork 前冻结。选择时先淘汰
任一 encoder hard-gate failure，然后按以下全数 tuple 字典序取最小：

```text
(
  mutation_accept_count,
  evidence_loss_count,
  constructible_invalid_presence_count,
  half_pair_state_count,
  b8_consumer_assertion_count,
  b8_consumer_changed_loc,
  verifier_branch_count,
  route_record_count,
  route_hash_layer_count,
  canonical_wire_bytes
)
```

presence count 在冻结 optional/tag 枚举空间上穷尽；branch/record/LOC 由冻结
AST/diff 计数器实测，不允许人工“估计”。B8 使用同一 test-only consumer skeleton。
路线本身的 self-SHA 数值不作指标。

wall time 与 peak memory 只作辅报，不参与裁定；辅报固定 warm-up=`5`、
repeat=`30`、报 median/p95 及 `tracemalloc` peak，并保存 environment manifest。

两名独立 reviewer 必须分别复放 corpus 和 metric script。若 tuple 完全并列或
reviewer 结论分歧，不签 production schema，先产生追因报告。对照 JSON 必须保留所有
失败路线，禁止只存胜者。

## 8. Production 收敛门

对照报告可记录非状态、非 capability 的 engineering disposition：

```text
B7_UNIQUE_SCHEMA_SELECTED_FOR_IMPLEMENTATION
```

该文本只存在 `selection_review.json` 与设计报告，不得进入 `V3M0State`、
runtime artifact 或 checkpoint。只在它通过双复核后才允许：

- 创建 `rulespace_v3/application_response_v3.py`；
- 为胜者使用路线相关的 `v3m0.*.v3` schema ID 与 canonical owner；
- 创建 opaque paired `Verified*` outcome、weak registry 与 public issuer/verifier；
- 修改 B8 consumer；
- 把 B7 source 加入 Parent preparation closure；
- 冻结 response artifact 或 checkpoint SHA。

B7 单元阶段只用 test-private graph。真实 live Parent 攻击复放在 B7–B10 都存在之后、
preparation `P` 之前完成。败者不得保留 production adapter、dual issuer、promotion、
raw hydrate 或兼容重签路径。

## 9. 失败语义

production 候选使用独立 `PairedResponseFailureV3`：

```text
reference_failed
shell_failed
actual_response_failed
matched_ablated_response_failed
actual_bridge_failed
matched_ablated_bridge_failed
```

bridge failure 只表示 executor/type/branch 测量异常，异常支不保存 audit。
有效 `SourceReadoutBridgeAudit` 的数值不在 B7 被 threshold 转成 failure，而是连同
response 进入后续 noise calibration。outer failure 与 branch attempt failure 必须机械一致。

`ControlCandidateFailure → BlockStatus.reason` 保持任务书唯一映射：

```text
reference/shell        → ENDPOINT_SHELL_AMBIGUOUS
response construction → PAIRED_RESPONSE_FAILED
executor bridge        → RESPONSE_BRIDGE_FAILED
```

`UPSTREAM_INVALID`、`CROSS_PARENT_ROOT` 与 `CROSS_BRANCH` 是 raw outcome 前异常，必须
零 artifact、零 registry mutation、零 capability。

## 10. 执行顺序与最大并行度

```text
V9-DOC-REVIEW
→ LEGACY-GOLDEN-CAPTURE@18b0d43
→ [ P0a-LAB-CONTRACT → (D0-A || D0-B || D0-C) → D0-REVIEW ]
  || P0b1-PROVENANCE
  || P0b2-NEUTRAL-LEAVES-AND-LEGACY-REGRESSION
→ P0-UPSTREAM-REFREEZE
→ A1-B6-REPLAY-AND-DUAL-REVIEW
→ P0-D1-LAB-INTEGRATION-BASE
→ D1-CAPTURE-MATRIX × (D1-A || D1-B || D1-C)   [仅 D0 survivors]
→ COMPARISON-REPORT-AND-DUAL-REVIEW
→ UNIQUE-PRODUCTION-SCHEMA-FREEZE
→ B7-PRODUCTION-TDD → B7-SPEC-REVIEW → B7-QUALITY-REVIEW
→ B8
```

因此三路完全可并行，但它们不得并行创建 production authority。关键墙钟路径是
`golden → max(P0b+refreeze, P0a+D0) → D1 slowest → review → unique B7`，
不是 A+B+C 顺序相加。

## 11. 非目标与状态上限

- 不改变任何科学阈值或 control verdict；
- 不修改 v1/v2 evidence；
- 不把 A/B/C 称为 physical family；
- 不运行 V3-M1、Round 0、pilot 或 GPU 正式扫描；
- 不签 `READY-V3-M1-ANCHOR-CERTIFICATION`；
- 不把 D0/D1 PASS 当作 B7 production PASS；
- 不在真实 P/S 后继续修改 B7 code。

本文不新增、不签发任何 run-state 或 capability literal。仓库权威状态仍为
`HALT-V3M0-WINDOW`；B8、V3-M1、family、pilot 与 GPU 锁均不解除。
