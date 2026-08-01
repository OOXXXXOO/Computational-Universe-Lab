# v3 设计勘误：metric-support authority v1

*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*

## 0. 裁定与边界

C19 refreeze v2 的 `DynamicsKGridDerivationProtocolV1` 要求 runtime Dynamics grid
同时来自 live transition signed support 和 verified metric signed support。当前仓库只有
raw `StabilityMetricWitness`；它可由 caller 持有，且它的 builder/verifier 绑定历史
`VerifiedPrestructureAuthority`。后置 `VerifiedDynamicsCertificate` 又依赖已建成的
Dynamics grid，不能反向给 grid 提供 metric-support authority。

因此当前不存在无环、不可伪造的 production metric-support 输入。任何直接把
raw witness、support tuple、caller SHA 或后置 certificate 传入 C19 Dynamics grid 的实现
均必须 fail closed。

本 DRAFT 冻结唯一方向：

1. Parent-v3 response contract 预响应递归内嵌 exact
   `MetricSupportDerivationProtocolV1`；
2. Parent-v3 与 Materialization-v3 真实签发后，由一个独立模块从 live lineage
   机械签发 `VerifiedMetricSignedSupportAttestationV1`；
3. V3-bound transition 与 metric-support attestation 必须来自同一 Parent / application /
   scenario / materialization / branch / factory，然后才能派生 Dynamics grid。

本文不实现 production issuer，不使旧 Parent/prestructure 转接进 C19-v3，不改
threshold、实验结果或当前 `HALT-V3M0-WINDOW`。

## 1. 被拒绝的替代方案

### A. 在 `metric.py` 给 raw witness 直接加 opaque wrapper

拒绝。现有 `StabilityMetricWitness` / `MetricOriginManifest` 绑定历史
`VerifiedPrestructureAuthority`，同时保留 public raw build/verify 与大量 raw consumer。局部
套壳会扩大 downgrade、cross-Parent 和 raw-splice 攻击面，且不会产生合法
`parent_freeze_v3_sha`。

### B. 独立 metric-support authority

采用。它只签发“这一 Parent-v3 materialized branch 的 metric signed support”，不冒充
full metric/dynamics certificate，也不污染 executor measurement provenance。

### C. 把 metric support 合并进 `VerifiedTransition`

拒绝。metric 是独立结构先验，transition 是 executor measurement。合并会迫使
metric 变化重测 transition，并把两类 authority 的生命周期、缓存和攻击面耦合。

## 2. Parent-v3 预响应 exact protocol

`CurrentScenarioResponseContractV3` 必须递归内嵌 exact Python body
`MetricSupportDerivationProtocolV1`，schema ID 唯一为：

```text
v3m0.metric-support-derivation-protocol.v1
```

exact fields 唯一为：

```text
protocol_schema_version
metric_kind                    = constant-state-v1
state_schema_id                = v3m0.c19-real-canonical-state.v2
channel_order                  = C19 冻结的 20 实通道顺序
spatial_shape                  = (8,)
spatial_ndim                   = 1
state_metric                   = exact FrozenComplexTensor(I20)
normalization_id               = trace-at-zero-equals-state-dim-v1
support_derivation_id          = constant-kernel-origin-only-v1
metric_support_offsets         = ((0,),)
metric_support_sha             = canonical hash of the complete support body
caller_supplied_support_allowed = False
protocol_sha                   = canonical hash of every preceding field
```

protocol 是 pre-response 派生规则，不是 runtime attestation。它不得包含 future
Parent root、materialization SHA、factory SHA、live grid/body/SHA、observed residual 或 verdict。
`state_metric` 必须与 C19 geometry bundle 内的 exact `I20` 递归相等，不得只比较
label、shape 或一个 caller-supplied SHA。

`metric_support_sha` 继承现有 `v3m0.metric-support.v1` 的 exact canonical body：

```text
{
  "support_schema_version": "v3m0.metric-support.v1",
  "support_offsets": [[0]],
}
```

不新建同义 support schema，也不允许只对裸 tuple 或串接文本求 hash。

## 3. Runtime attestation 与 opaque capability

新模块唯一命名为：

```text
rulespace_v3/metric_support_authority_v1.py
```

raw exact body 唯一为：

```text
MetricSignedSupportAttestationV1(
  attestation_schema_version,
  parent_freeze_v3_sha,
  current_application_authority_v3_sha,
  current_scenario_authority_v3_sha,
  response_contract_v3_sha,
  metric_support_protocol_sha,
  application_scenario_materialization_v3_sha,
  factory_sha,
  factory_role,
  state_schema_id,
  channel_order,
  spatial_shape,
  metric_kind,
  metric_support_offsets,
  metric_support_sha,
  attestation_sha,
)
```

schema ID 唯一为 `v3m0.metric-signed-support-attestation.v1`。opaque type 唯一为
`VerifiedMetricSignedSupportAttestationV1`。

唯一 public issuer 为：

```python
issue_c19_metric_signed_support_attestation_v1(
    parent: VerifiedParentFreezeV3,
    materialization: VerifiedV3M0ApplicationScenarioMaterializationV3,
    factory_role: Literal["actual", "matched_ablated"],
) -> VerifiedMetricSignedSupportAttestationV1
```

issuer 不接收 raw witness、raw attestation、support、points、grid 或任何 caller SHA。不提供
public constructor、hydrator、promoter 或 resign path。它只能从当次 live Parent-v3
的 current application→scenario→response→metric protocol 与同一 live materialization branch 重建
exact attestation，再以 module-private token、weak live registry、immutable seal 签发 wrapper。

private reverifier 每次必须重验 live Parent/materialization/factory，重建 protocol-derived
metric/support/attestation/seal，并返回与 exposed body 隔离的 snapshot view。首版不引入
replay cache。

## 4. 无环运行时拓扑

```text
VerifiedParentFreezeV3
  → VerifiedWindowThresholdCalibrationV3
  → VerifiedCalibrationApplicationPermitV3
  → VerifiedV3M0ApplicationScenarioMaterializationV3
      → actual / matched VerifiedFactory
          ├→ same-branch V3-bound VerifiedTransition
          └→ VerifiedMetricSignedSupportAttestationV1

V3-bound VerifiedTransition
  + VerifiedMetricSignedSupportAttestationV1
  + exact DynamicsKGridDerivationProtocolV1
  → DynamicsKGridManifest
  → full metric/dynamics certificate
```

Dynamics grid derivation 必须从两个 live wrapper 内部权威 view 读取 support，并比较
Parent、application、scenario、materialization、branch role、factory、state schema、channel order 与
spatial shape 全部一致。它不接受 caller role、support、points 或 artifact SHA。

当前 `VerifiedTransition` 路径仍绑历史 `VerifiedPrestructureAuthority`；production C19
必须新建 V3-bound transition issuer，或在不提供 V1/V2 adapter/fallback 的前提下完成
exact V3 迁移。在该迁移完成前，不得把旧 `VerifiedTransition` 与新 attestation 拼接。

## 5. Fail-closed 攻击合同

至少必须拒绝：

- Parent-v1/v2、历史 `VerifiedPrestructureAuthority` 或任何 adapter/fallback；
- raw witness/raw attestation/dict/subclass、`object.__new__`、伪 token、死 registry、seal 篡改；
- exposed body 与 authority snapshot 任一独立篡改；
- protocol 不是 Parent-v3 response contract 内嵌的 exact body；
- metric 非 `I20`、非 constant-state、normalization 漂移、support 非 canonical
  `((0,),)`，或 support 的维数、顺序、重复项、bool/int 类型漂移；
- 任何 cross-Parent/application/scenario/materialization/branch/factory/state/shape splice；
- actual attestation 复用到 matched，或两支 attestation 互换；
- caller-supplied support/grid/points/future artifact SHA；
- transition signed support 或 attested metric support 非零却签 exact singleton；
- 以后置 dynamics certificate/normalized audit 作为 grid 前置产生循环；
- monkeypatch verifier/rebinder，或只查 primitive radius 而不重验 live factory/transition lineage。

## 6. 实施门与当前状态

可以立即实现的只有：

1. Parent-v3 authority-neutral raw contract 中的 exact
   `MetricSupportDerivationProtocolV1`、payload 和 canonical verifier；
2. production issuer 的 RED 攻击合同，前提是不用 fake upstream 制造 GREEN。

能成功返回 `VerifiedMetricSignedSupportAttestationV1` 的 production issuer 必须等待：

```text
VerifiedParentFreezeV3                           NOT ISSUED
VerifiedCalibrationApplicationPermitV3           NOT ISSUED
VerifiedV3M0ApplicationScenarioMaterializationV3  NOT ISSUED
same-branch V3-bound transition authority         NOT IMPLEMENTED
```

因此本 DRAFT 本身不解锁 Dynamics runtime grid、C19 evidence、V3-M1、V3-M2、pilot
或 GPU 正式扫描。
