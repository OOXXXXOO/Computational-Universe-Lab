# v3 设计勘误：Parent-v3 prestructure production chain v7

*Computational Universe Lab · Projective Rule-Space Program · 2026-08-02 · 状态：DRAFT / v7 delta 设计冻结 / 未签发*

> 视觉与品牌权威资产：`visualizations/assets/logo.png`、
> `visualizations/assets/repo_cover.png`、`visualizations/dashboards/program_atlas.html`；
> 本文不新建视觉语言，也不用状态色表达科学 PASS/FAIL。

> 任务：V3-M0 Phase B / B0 v7 delta
> 基线：`docsv3/v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md`
> （registry v6，raw SHA-256
> `fd654e76ea143503916b45e1eec6456eab3f014e1e8ba02b826f6c62bb42e91f`）。

## 0. 裁定与边界

v6 中 B3 要求从 live Parent-v3 + B2 materialization + branch role 内部派生
prestructure，却把 B6 的 full body 类型钉在 legacy `PrestructureAuthority`。这条路线不可实现：

- legacy `PrestructureAuthority` 强制携带 historical `ParentFreezeManifest`，其
  synthetic-application 分支只接受旧 `V3M0SyntheticControlApplicationSpec` 与
  `ApplicationScenarioExecutionSpec`；
- historical synthetic application 是 4-channel，current C19 已冻结为
  `v3m0.c19-real-canonical-state.v2`、20-channel `q0,p0,...,q9,p9`、spatial shape `(8,)`；
- legacy adapter body 的 canonical payload 明确未实现，且 classical-adapter 语义不是
  current synthetic C19；
- `dynamics._remeasure_transition` 直接硬绑 legacy
  `VerifiedPrestructureAuthority`。

因此，v7 只作以下最小 delta：

1. 新增并行的 full raw `ParentV3ApplicationPrestructure` 及 owner-internal opaque
   `VerifiedParentV3ApplicationPrestructure`，不改 legacy v1 wire；
2. `TransitionAuthorityV3` 递归携带该 full prestructure，
   `MeasuredTransition.prestructure_authority_sha` 必须精确等于它的 self-hash；
3. `rulespace_v3.dynamics` 抽出唯一 owner-internal authority-neutral
   real-space measurement core，legacy 与 Parent-v3 两条路线共同委托；
4. B6 的 `DynamicsCertificateV3.prestructure_authority` 改为新 full record，并且
   只消费 `VerifiedTransitionAuthorityV3` private view 中同一个 live prestructure，
   不复制构造算法。

本文是 `DESIGN_ONLY_NO_AUTHORITY`：不签发 Parent、materialization、prestructure、
transition 或 certificate，不改阈值，不作科学 PASS/FAIL。v6 原文保留为历史设计冻结，
不在原文上追改。

## 1. 权威流与 full-body 语义

```text
exact live VerifiedParentFreezeV3
  + exact live VerifiedV3M0ApplicationScenarioMaterializationV3
  + exact role
        |
        v
owner-internal VerifiedParentV3ApplicationPrestructure
  [full binding + full pair snapshot + full basis + derived block-J]
        |
        +--> dynamics shared real-space full-state measurement core
        |
        v
VerifiedTransitionAuthorityV3
  [full materialization + full binding + full prestructure + full transition]
        |
        v
certificate_v3 consumes the same live prestructure identity
  [DynamicsCertificateV3 stores that same full raw body again]
```

`ParentV3ApplicationPrestructure` 不是 SHA 占位。它保存完整 selected
`FactoryBranchBindingV3`、完整 `AblationPairSnapshot`、完整 `C19BasisContractV2`
和从 20 个 ordered canonical channel 机械派生的 20×20 block-J
`FrozenComplexTensor`。Parent/permit/materialization/application/scenario/response 根和
factory role/SHA 在同一 body 中直接绑定。

新 prestructure 的 raw body 是可序列化证据，不是 capability。只有 owner-token 和
live identity registry 中的 `VerifiedParentV3ApplicationPrestructure` 是运行时 capability；
它不是 public API 的参数或返回值。公开 B3 仍只返回
`VerifiedTransitionAuthorityV3`。

`_verify_parent_v3_application_prestructure` 名字中的 `verify` 不表示允许 raw
hydration。raw body 只是待比较证据；exact live Parent-v3 和 exact live
materialization 始终必填。owner 必须先调用 B2 唯一 seam
`_require_v3m0_application_scenario_materialization_v3_for_parent(parent, materialization)`
递归重验 Parent/materialization/permit/two-factory pair，再派生 expected full body；只有
raw 与 expected exact 相等时才能进入 owner live registry。裸 raw、equal copy 或
self-hash 都不能签发 capability。新 owner 因此不直接 import
`parent_authority_v3`；Parent 的 exact type、identity 与 root 由 B2 owner seam 封闭重验。
B2 replay 可以重铸新的 `VerifiedFactory` 子包装器；B3/B6 不得比较该包装器的 object
identity，而必须保存 owner seam 返回的 fresh child，并比较其 exact raw factory body、完整
`FactoryBranchBindingV3`、branch role 与 factory SHA。same-live identity 只覆盖 Parent、
materialization 与新 prestructure capability。

## 2. dynamics shared core

`rulespace_v3.dynamics` 新增唯一 private core：

```python
def _measure_bound_realspace_transition(
    factory: VerifiedFactory,
    *,
    parent_freeze_sha: str,
    prestructure_authority_sha: str,
) -> MeasuredTransition:
    ...
```

该 core 先重验 exact live factory，从 factory immutable body 取 role、state schema、
channel order、shape、`dt` 与 periodic boundary；从
`factory_support_offsets(factory, 1)` 派生 signed support；然后在 canonical origin 上对
每个 full-state channel 各跑一次 real-space unit impulse。它固定
`channel-identity-v1`、`macro_steps=1`、`complex128` full kernel，并验证
support 外 bit-exact `+0.0`。

legacy `_remeasure_transition` 先完成原有
`VerifiedFactory`/`VerifiedPrestructureAuthority` join，再委托该 core 一次。B3 则先完成
Parent-v3/B2/new-prestructure join，再委托一次。core 不进入 `dynamics.__all__`，
旧 `MeasuredTransition` fields/schema 与公开 dynamics API 的签名、语义不变。

## 3. B6 同一 live prestructure 原子连接

`_VerifiedTransitionAuthorityV3View.prestructure` 保存签发 B3 transition 时的同一
`VerifiedParentV3ApplicationPrestructure`。B6 只能通过
`_reverify_verified_transition_authority_v3` 取得该 view；不能从 raw SHA、
materialization 或 factory 再造第二个 prestructure 算法分支。

`DynamicsCertificateV3.prestructure_authority` 保存该 live capability 暴露的完整 raw
`ParentV3ApplicationPrestructure`。它必须同时等于
`certificate.transition_authority.prestructure_authority`，其 self-hash 必须同时等于
`measured_transition.prestructure_authority_sha`。Parent/materialization/prestructure 必须保持
same-live identity；factory wrapper 可以由 B2 replay 重铸，但 raw body、binding、role 与 SHA
必须精确相等。任一连接断裂都失败关闭。

## 4. B6 全 judge-chain 的 owner-neutral 数值缝

现有 `structure`、`metric`、`bridge`、`laurent` 与 `spectral` 的公开入口都从
legacy `VerifiedPrestructureAuthority` 或 `VerifiedTransition` 起步；因此把 Parent-v3
transition 偷登记进 legacy `VerifiedTransition` registry 既不合法，也不能真正打通下游。
v7 明确禁止扩大该 registry 的 authority 类型或注入 replay callback。B3 只签发自己的
`VerifiedTransitionAuthorityV3`；B6 在完整重验 V3 live view 后，只把其中的 raw
`MeasuredTransition` 交给 canonical owner 的 private neutral core。

neutral core 不是新公开入口。旧公开函数必须先完成原来的 exact live authority join，再恰好
委托同一 core；B6 则先完成 Parent-v3、materialization、transition、metric attestation 与两个
grid authority 的原子 join，再委托该 core。候选证据的验证一律从 live-derived 输入重构 expected
raw record 并做 exact equality，不以 self-hash 单独签发。`structure`、`metric`、`bridge`、
`laurent`、`spectral` 不得反向 import Parent-v3 owner 或 `certificate_v3`。

全链最小缝为：structure manifest、reality、identity metric、bridge spec/audit、Laurent resource
preflight/residual、spectral coverage、normalized residual 与 power drift。已有的 raw transition
symbol、exact Jordan raw witness、fp64 protocol 及 directed power arithmetic 原样复用。B6 不使用
legacy `VerifiedNormalizedMetricResidualAudit`，因为它的 registry 也递归保存 legacy
`VerifiedTransition`；normalized 与 power 在 V3 顶层 live certificate authority 内由 raw expected
bodies 重构。

metric 的 V3 origin 绑定固定为：
`MetricOriginManifest.derivation_or_preregistration_sha ==
MetricSignedSupportAttestationV1.metric_support_protocol_sha`。metric kernel 与 support 分别取同一
live materialization 中 frozen protocol 的 bit-exact `I20` 与 B4 attestation 的 origin singleton；
caller 不得提供二者。

## 5. V3 runtime 私有 authority

B6 公共 API 不接受 caller runtime。现有 `rulespace_v3.runtime` 的 legacy public authority、
evaluator id、root list、source closure 与 manifest SHA 必须保持位级不变，不能把
`certificate_v3` 直接追加到 `_MODULE_RUNTIME_AUTHORITY`。
这里的“位级不变”精确指 wire、evaluator、root set、transitive inventory 规则和
canonical hash 算法，以及同一 source snapshot 上的确定性；它不要求源文件改动后历史
manifest 的值继续有效。任一被盘点源文件变化后，历史 manifest 必须在 fresh
reverification 中失效，新快照必须重新签发。

同一 `RuntimeEvidenceManifest` raw schema 上新增并行 private `_V3_RUNTIME_AUTHORITY`：其
evaluator id 为 `rulespace-v3m0-parent-v3-certificate-closure-v1`，fresh-process 唯一 import root
为 `rulespace_v3.certificate_v3`，并盘点由该 root 实际加载的全部 repository-local transitive
source。private payload、zero-argument issuer 与 verifier 都不进 `__all__`；B6 在内部签发并立即
重验。runtime 或 fp64 环境探针失败属于 evaluator infrastructure failure：不得伪装为科学
FAIL，不得签发 outcome/certificate，直接 fail closed。

fresh-process root 是子进程探针配置，不是父进程静态 import edge；因此
`certificate_v3 -> runtime` 保持静态 DAG 无环，`runtime` 不在父进程反向 import
`certificate_v3`。

## 6. B6 first-failure 与攻击面

B6 必须先在 attempt/outcome/certificate 构造之外原子重验六个 live upstream authority，并
从 transition private view 重验其中嵌套的新 prestructure。任一 raw/dead/forged/tampered 或
cross-authority 输入都抛出公开 typed `DynamicsCertificationUpstreamJoinFailure`；此路径不生成
attempt audit、outcome、certificate 或 opaque registry side effect。只有原子连接完成后，六个
SHA root 才能写入 attempt audit。
该 eager join 只裁定 input capability validity 与 cross-authority 一致性，不提前运行或裁定
derived scientific judges。因而，valid joined inputs 之后仍可由真实派生计算签发
`metric_raw_unresolved`、`spectral_coverage_unresolved` 或 `full_state_bridge_failed`；这与上游
typed raise 路径不冲突。

v6 的 `DynamicsCertificationFailure` 枚举值及声明顺序保持不变，但
`prestructure_invalid` 与 `transition_invalid` 仅保留 wire compatibility，不能作为 outcome 的
`failure` 签发；对应上游错误由上述 typed raise 表达。可签发 first-failure 执行顺序为 reality →
Laurent resource → exact Jordan counterwitness → structure → metric → spectral → normalized →
bridge → power。Jordan 检查必须位于 structure/metric 之前，否则唯一合法的 UNSTABLE 反证会先被
后续稳定性门遮蔽。只有 existing raw exact-Jordan seam 可签发 counterwitness；近似 Jordan、
自签名或错误 support 一律拒绝。

legacy wrapper 的签名、`__all__`、authority exact type、wire 与每个递归 SHA 均须回归锁定；
抽缝前后同一 legacy fixture 的 raw record/SHA 必须 byte-identical，并证明 old join 先于且只
调用 neutral core 一次。

## 7. 失败语义与攻击面

B3 保留 v6 的七个 typed failure ID，但 v7 要求每个 ID 都有代表性死亡路径；
不允许用统一 `ValueError` 或仅测试 failure 构造器代替路由。必须拒绝 legacy
prestructure/transition opaque，裸 raw body，caller factory/pair/basis/structure/SHA/kernel/support/grid，
analytic/FFT/reduced-state/per-k projector 代测，self-resigned mutation，actual/matched
swap/duplicate/half/cross-pair，cross-parent，dead/forged/tampered wrapper，以及 public closure/global redirect。

v7 的有效合同由 v6 registry 的深拷贝开始，只应用机器注册表列出的两个 exact JSON-pointer
replacement，再叠加 v7 delta；任何未列出的 v6 值都不得变化。这一合并规则取代自然语言
“歧义解释”，使 B6 的 wire-only 枚举与实际可签发 outcome 顺序不存在双重权威。

## 8. 机器可读 v7 delta registry

<!-- BEGIN V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->
```json
{
  "registry_schema_version": "v3m0.parent-v3-prestructure-production-chain-delta.v7",
  "document_authority": "DESIGN_ONLY_NO_AUTHORITY",
  "production_status": "EXPECTED-MISSING_AT_V7_FREEZE",
  "issued_statuses": [],
  "threshold_values": {},
  "threshold_policy": "REFERENCE_EXISTING_FROZEN_VALUES_ONLY",
  "base_contract": {
    "path": "docsv3/v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md",
    "registry_schema_version": "v3m0.parent-v3-downstream-contract-registry.v6",
    "raw_sha256": "fd654e76ea143503916b45e1eec6456eab3f014e1e8ba02b826f6c62bb42e91f",
    "mutation_allowed": false,
    "delta_scope": [
      "Parent-v3 application prestructure ownership",
      "B3 transition measurement seam and recursive wire",
      "B6 prestructure field and live authority joins",
      "B3/B6 import DAG correction",
      "B6 owner-neutral judge seams and legacy delegation locks",
      "B4/B5 private live views and fresh B2 child semantics",
      "parallel private V3 runtime authority",
      "B6 upstream atomic precondition and effective outcome failure order"
    ]
  },
  "effective_merge": {
    "algorithm": "COPY_V6_THEN_APPLY_EXACT_JSON_POINTER_REPLACEMENTS_THEN_ADD_V7_DELTA",
    "unlisted_v6_mutation_allowed": false,
    "v7_delta_additions_apply_after_overrides": true,
    "json_pointer_overrides": [
      {
        "json_pointer": "/tasks/B6/invariants/0",
        "operation": "REPLACE_EXACT",
        "expected_v6_value": "failure order is exactly DynamicsCertificationFailure enum order",
        "replacement_value": "DynamicsCertificationFailure declaration order is wire compatibility only; prestructure_invalid and transition_invalid are nonissuable upstream typed raises, while issuable outcome first-failure execution follows the v7 failure contract"
      },
      {
        "json_pointer": "/tasks/B6/typed_failures",
        "operation": "REPLACE_EXACT",
        "expected_v6_value": [
          "prestructure_invalid",
          "transition_invalid",
          "reality_invalid",
          "laurent_resource_exceeded",
          "structure_raw_unresolved",
          "metric_raw_unresolved",
          "spectral_coverage_unresolved",
          "normalized_metric_unresolved",
          "full_state_bridge_failed",
          "power_drift_unresolved",
          "certified_instability_counterwitness"
        ],
        "replacement_value": [
          "reality_invalid",
          "laurent_resource_exceeded",
          "certified_instability_counterwitness",
          "structure_raw_unresolved",
          "metric_raw_unresolved",
          "spectral_coverage_unresolved",
          "normalized_metric_unresolved",
          "full_state_bridge_failed",
          "power_drift_unresolved"
        ]
      }
    ]
  },
  "record_catalog_delta": {
    "ParentV3ApplicationPrestructure": {
      "operation": "ADD_V7_RECORD",
      "schema_id": "v3m0.parent-v3-application-prestructure.v1",
      "canonical_owner": "rulespace_v3.parent_v3_application_prestructure",
      "field_specs": [
        {"name": "prestructure_schema_version", "wire_type": "str", "presence": "required", "literal_domain": ["v3m0.parent-v3-application-prestructure.v1"], "tuple_cardinality": null, "nested_record": null, "constraints": ["exact schema literal"]},
        {"name": "parent_freeze_v3_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "permit_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "materialization_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "current_application_authority_v3_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "current_scenario_authority_v3_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "current_scenario_response_contract_v3_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "factory_binding", "wire_type": "FactoryBranchBindingV3", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "FactoryBranchBindingV3", "constraints": ["full recursive raw body"]},
        {"name": "factory_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "factory_role", "wire_type": "Literal[actual,matched_ablated]", "presence": "required", "literal_domain": ["actual", "matched_ablated"], "tuple_cardinality": null, "nested_record": null, "constraints": []},
        {"name": "ablation_pair_snapshot", "wire_type": "AblationPairSnapshot", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "AblationPairSnapshot", "constraints": ["full recursive raw body"]},
        {"name": "basis_contract", "wire_type": "C19BasisContractV2", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "C19BasisContractV2", "constraints": ["full recursive raw body"]},
        {"name": "evidence_lane", "wire_type": "Literal[synthetic-classical]", "presence": "required", "literal_domain": ["synthetic-classical"], "tuple_cardinality": null, "nested_record": null, "constraints": []},
        {"name": "target_spec_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]},
        {"name": "state_schema_id", "wire_type": "Literal[v3m0.c19-real-canonical-state.v2]", "presence": "required", "literal_domain": ["v3m0.c19-real-canonical-state.v2"], "tuple_cardinality": null, "nested_record": null, "constraints": ["exact current C19 state schema"]},
        {"name": "channel_order", "wire_type": "tuple[str,...]", "presence": "required", "literal_domain": [], "tuple_cardinality": {"kind": "exact", "value": 20}, "nested_record": null, "constraints": ["exact ordered q0,p0,q1,p1,...,q9,p9"]},
        {"name": "canonical_channel_pairs", "wire_type": "tuple[tuple[str,str],...]", "presence": "required", "literal_domain": [], "tuple_cardinality": {"kind": "exact", "value": 10}, "nested_record": null, "constraints": ["exact adjacent q/p pairs covering channel_order once"]},
        {"name": "fourier_adjoint_convention_id", "wire_type": "Literal[minus-k-transpose-v1]", "presence": "required", "literal_domain": ["minus-k-transpose-v1"], "tuple_cardinality": null, "nested_record": null, "constraints": []},
        {"name": "structure_form", "wire_type": "FrozenComplexTensor", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "FrozenComplexTensor", "constraints": ["full recursive raw body", "exact derived 20x20 canonical block-J"]},
        {"name": "reality_convention_id", "wire_type": "Literal[real-kernel-positive-zero-v1]", "presence": "required", "literal_domain": ["real-kernel-positive-zero-v1"], "tuple_cardinality": null, "nested_record": null, "constraints": []},
        {"name": "prestructure_authority_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]}
      ],
      "record_invariants": [
        "issued only from one exact live Parent-v3 plus one exact live B2 materialization and one frozen factory role",
        "all Parent, permit, materialization, application, scenario, response, branch and factory roots rejoin exactly",
        "factory_binding is the full selected B2 branch body and its branch/factory/root equal the direct fields",
        "ablation_pair_snapshot and basis_contract are the exact full bodies already nested in the same materialization",
        "state schema is v3m0.c19-real-canonical-state.v2; channel_order is exact q0,p0 through q9,p9 and spatial shape remains (8,) in the bound factory",
        "canonical_channel_pairs are the ten adjacent q/p pairs and structure_form is the exact derived 20x20 canonical block-J",
        "no caller supplies a prestructure body, structure form, basis, pair snapshot, factory or SHA",
        "prestructure_authority_sha is SHA-256 of the complete canonical body excluding only itself"
      ]
    },
    "TransitionAuthorityV3": {
      "operation": "REPLACE_V6_RECORD",
      "schema_id": "v3m0.transition-authority.v3",
      "canonical_owner": "rulespace_v3.transition_authority_v3",
      "field_specs": [
        {"name": "transition_authority_schema_version", "wire_type": "str", "presence": "required", "literal_domain": ["v3m0.transition-authority.v3"], "tuple_cardinality": null, "nested_record": null, "constraints": ["exact schema literal"]},
        {"name": "materialization", "wire_type": "ApplicationScenarioMaterializationV3", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "ApplicationScenarioMaterializationV3", "constraints": ["full recursive raw body"]},
        {"name": "factory_binding", "wire_type": "FactoryBranchBindingV3", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "FactoryBranchBindingV3", "constraints": ["full recursive raw body"]},
        {"name": "prestructure_authority", "wire_type": "ParentV3ApplicationPrestructure", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "ParentV3ApplicationPrestructure", "constraints": ["full recursive raw body"]},
        {"name": "measured_transition", "wire_type": "MeasuredTransition", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": "MeasuredTransition", "constraints": ["full recursive raw body"]},
        {"name": "transition_authority_sha", "wire_type": "sha256", "presence": "required", "literal_domain": [], "tuple_cardinality": null, "nested_record": null, "constraints": ["64 lowercase hexadecimal SHA-256"]}
      ],
      "record_invariants": [
        "materialization, factory_binding and prestructure_authority are full recursive raw bodies from one live B2 branch",
        "measured_transition.prestructure_authority_sha equals prestructure_authority.prestructure_authority_sha exactly",
        "factory binding branch/factory/root equals prestructure and measured transition branch/factory/root",
        "verification reconstructs the prestructure and remeasures every full-state impulse; self hashes alone never hydrate authority"
      ]
    }
  },
  "dynamics_certificate_v3_field_replacement": {
    "record": "DynamicsCertificateV3",
    "field": "prestructure_authority",
    "operation": "REPLACE_V6_FIELD_TYPE",
    "old_wire_type": "PrestructureAuthority",
    "old_nested_record": "PrestructureAuthority",
    "new_wire_type": "ParentV3ApplicationPrestructure",
    "new_nested_record": "ParentV3ApplicationPrestructure",
    "presence": "required",
    "constraints": [
      "full recursive raw body",
      "exactly equals transition_authority.prestructure_authority",
      "obtained from the same live VerifiedParentV3ApplicationPrestructure stored by VerifiedTransitionAuthorityV3",
      "B6 must not reconstruct, adapt or independently hash a prestructure"
    ]
  },
  "private_capabilities": {
    "VerifiedParentV3ApplicationPrestructure": {
      "canonical_owner": "rulespace_v3.parent_v3_application_prestructure",
      "raw_body": "ParentV3ApplicationPrestructure",
      "constructibility": "owner-token-only-live-identity-registry",
      "exported_publicly": false,
      "required_b2_owner_seam": "rulespace_v3.application_materialization_v3._require_v3m0_application_scenario_materialization_v3_for_parent",
      "raw_verification_policy": "raw body is comparison evidence only; exact live Parent-v3 and materialization are mandatory and the B2 owner seam is replayed before owner registration",
      "private_view": {
        "name": "_VerifiedParentV3ApplicationPrestructureView",
        "fields": [
          {"name": "prestructure", "wire_type": "ParentV3ApplicationPrestructure"},
          {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
          {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
          {"name": "factory", "wire_type": "VerifiedFactory"},
          {"name": "factory_binding", "wire_type": "FactoryBranchBindingV3"}
        ]
      }
    },
    "VerifiedTransitionAuthorityV3": {
      "canonical_owner": "rulespace_v3.transition_authority_v3",
      "raw_body": "TransitionAuthorityV3",
      "constructibility": "owner-token-only-live-identity-registry",
      "exported_publicly": true,
      "required_prestructure_reverifier": "rulespace_v3.parent_v3_application_prestructure._reverify_verified_parent_v3_application_prestructure",
      "private_view": {
        "name": "_VerifiedTransitionAuthorityV3View",
        "fields": [
          {"name": "transition_authority", "wire_type": "TransitionAuthorityV3"},
          {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
          {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
          {"name": "factory", "wire_type": "VerifiedFactory"},
          {"name": "prestructure", "wire_type": "VerifiedParentV3ApplicationPrestructure"}
        ]
      }
    }
  },
  "private_apis": [
    {
      "owner": "rulespace_v3.parent_v3_application_prestructure",
      "name": "_issue_parent_v3_application_prestructure",
      "args": [
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
        {"name": "factory_role", "wire_type": "Literal[actual,matched_ablated]"}
      ],
      "returns": "VerifiedParentV3ApplicationPrestructure",
      "raw_hydration_allowed": false
    },
    {
      "owner": "rulespace_v3.parent_v3_application_prestructure",
      "name": "_verify_parent_v3_application_prestructure",
      "args": [
        {"name": "prestructure", "wire_type": "ParentV3ApplicationPrestructure"},
        {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
        {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"}
      ],
      "returns": "VerifiedParentV3ApplicationPrestructure",
      "raw_hydration_allowed": false
    },
    {
      "owner": "rulespace_v3.parent_v3_application_prestructure",
      "name": "_reverify_verified_parent_v3_application_prestructure",
      "args": [
        {"name": "prestructure", "wire_type": "VerifiedParentV3ApplicationPrestructure"}
      ],
      "returns": "_VerifiedParentV3ApplicationPrestructureView",
      "raw_hydration_allowed": false
    },
    {
      "owner": "rulespace_v3.transition_authority_v3",
      "name": "_reverify_verified_transition_authority_v3",
      "args": [
        {"name": "transition", "wire_type": "VerifiedTransitionAuthorityV3"}
      ],
      "returns": "_VerifiedTransitionAuthorityV3View",
      "raw_hydration_allowed": false
    }
  ],
  "public_api_freeze": {
    "B3": [
      {
        "name": "issue_transition_authority_v3",
        "args": [
          {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
          {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
          {"name": "factory_role", "wire_type": "Literal[actual,matched_ablated]"}
        ],
        "returns": "VerifiedTransitionAuthorityV3",
        "raw_hydration_allowed": false
      },
      {
        "name": "verify_transition_authority_v3",
        "args": [
          {"name": "transition", "wire_type": "TransitionAuthorityV3"},
          {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
          {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"}
        ],
        "returns": "VerifiedTransitionAuthorityV3",
        "raw_hydration_allowed": false
      },
      {
        "name": "verify_transition_pair_v3",
        "args": [
          {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
          {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
          {"name": "actual_transition", "wire_type": "VerifiedTransitionAuthorityV3"},
          {"name": "matched_ablated_transition", "wire_type": "VerifiedTransitionAuthorityV3"}
        ],
        "returns": "tuple[VerifiedTransitionAuthorityV3,VerifiedTransitionAuthorityV3]",
        "raw_hydration_allowed": false
      }
    ],
    "dynamics_v1": [
      "measure_transition(factory,authority)",
      "verify_measured_transition(transition,factory,authority)",
      "transition_kernel_array(transition)",
      "transition_symbol(transition,momentum)"
    ],
    "prestructure_v1": [
      "issue_synthetic_prestructure_authority",
      "verify_synthetic_prestructure_authority",
      "issue_v3m0_application_prestructure_authority"
    ]
  },
  "dynamics_shared_core": {
    "owner": "rulespace_v3.dynamics",
    "name": "_measure_bound_realspace_transition",
    "visibility": "owner-internal",
    "signature": {
      "args": [
        {"name": "factory", "wire_type": "VerifiedFactory"},
        {"name": "parent_freeze_sha", "wire_type": "sha256"},
        {"name": "prestructure_authority_sha", "wire_type": "sha256"}
      ],
      "keyword_only_after": "factory",
      "returns": "MeasuredTransition"
    },
    "delegates": [
      "rulespace_v3.dynamics._remeasure_transition",
      "rulespace_v3.transition_authority_v3 B3 measurement route"
    ],
    "semantics": [
      "reverify the exact live VerifiedFactory and derive role/state/channel/shape/dt/boundary from its immutable body",
      "derive canonical signed support from factory_support_offsets(factory,1), enforce no wrap, sorted uniqueness and bit-exact +0.0 outside support",
      "rerun one periodic real-space unit impulse for every full state channel at the canonical origin",
      "freeze the complete (n_state,n_state,*spatial_shape) complex128 kernel and macro_steps=1",
      "accept no caller kernel, support, state schema, channel order, spatial shape, dt, boundary, basis, grid, FFT, per-k projector or analytic substitute"
    ],
    "legacy_delegate_order": "legacy _remeasure_transition first performs its unchanged VerifiedFactory/VerifiedPrestructureAuthority join, then delegates once",
    "v3_delegate_order": "B3 first reverifies Parent-v3/B2/new prestructure branch join, then delegates once"
  },
  "legacy_transition_registry_policy": {
    "decision": "FORBID_V3_REGISTRATION_IN_LEGACY_VERIFIED_TRANSITION_REGISTRY",
    "legacy_registry_record": "rulespace_v3.dynamics._TransitionAuthority",
    "legacy_prestructure_type": "VerifiedPrestructureAuthority",
    "generalized_union_or_callback_registry_allowed": false,
    "required_v3_route": "B3 owns VerifiedTransitionAuthorityV3; B6 consumes its raw MeasuredTransition only after the V3 private reverifier succeeds",
    "reasons": [
      "legacy registration and replay are identity-bound to VerifiedPrestructureAuthority",
      "legacy structure, metric, Laurent, spectral and normalized replay dereference the legacy prestructure",
      "sharing numerical cores must not broaden the authority accepted by VerifiedTransition"
    ]
  },
  "owner_neutral_judge_cores": {
    "policy": {
      "visibility": "private-not-in-__all__",
      "authority_precondition": "legacy callers complete their old live joins and B6 completes all V3 live joins before entering a neutral core",
      "candidate_verification": "reconstruct the expected raw record from live-derived inputs and require exact record equality; never trust a self-hash alone",
      "caller_raw_entry_allowed": false,
      "algorithm_copy_allowed": false,
      "forbidden_owner_imports": [
        "rulespace_v3.parent_v3_application_prestructure",
        "rulespace_v3.transition_authority_v3",
        "rulespace_v3.certificate_v3"
      ]
    },
    "cores": [
      {
        "owner": "rulespace_v3.structure",
        "name": "_build_bound_synthetic_structure_manifest",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "structure_form", "wire_type": "FrozenComplexTensor"},
            {"name": "target_spec_sha", "wire_type": "sha256"},
            {"name": "state_schema_id", "wire_type": "str"},
            {"name": "channel_order", "wire_type": "tuple[str,...]"},
            {"name": "canonical_channel_pairs", "wire_type": "tuple[tuple[str,str],...]"},
            {"name": "prestructure_authority_sha", "wire_type": "sha256"}
          ],
          "keyword_only_after": "structure_form",
          "returns": "StructureManifest"
        },
        "legacy_delegate": "_expected_structure completes its legacy factory/prestructure join and field selection before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "synthetic-classical/symplectic/minus-k-transpose/reality literals are owner-frozen",
          "canonical pairs cover channel_order exactly once and structure_form is exact block-J"
        ]
      },
      {
        "owner": "rulespace_v3.structure",
        "name": "_build_reality_certificate_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "factory", "wire_type": "VerifiedFactory"},
            {"name": "transition", "wire_type": "MeasuredTransition"},
            {"name": "structure", "wire_type": "StructureManifest"}
          ],
          "keyword_only_after": null,
          "returns": "RealityCertificate"
        },
        "legacy_delegate": "_expected_reality completes its legacy transition and structure joins before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "factory is reverified and exactly joins transition factory/state/channel/shape",
          "all factory coefficient and transition kernel imaginary wires are bit-exact positive zero"
        ]
      },
      {
        "owner": "rulespace_v3.metric",
        "name": "_build_bound_synthetic_identity_metric",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "factory", "wire_type": "VerifiedFactory"},
            {"name": "structure", "wire_type": "StructureManifest"},
            {"name": "state_metric", "wire_type": "FrozenComplexTensor"},
            {"name": "parent_freeze_sha", "wire_type": "sha256"},
            {"name": "prestructure_authority_sha", "wire_type": "sha256"},
            {"name": "derivation_or_preregistration_sha", "wire_type": "sha256"},
            {"name": "metric_support_offsets", "wire_type": "tuple[tuple[int,...],...]"}
          ],
          "keyword_only_after": "state_metric",
          "returns": "StabilityMetricWitness"
        },
        "legacy_delegate": "_expected_metric completes its legacy factory/prestructure/structure join and derives old inputs before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "state_metric is bit-exact I_N with trace N and condition one",
          "metric support is the exact origin singleton of factory spatial_ndim",
          "V3 derivation_or_preregistration_sha equals the live B4 metric_support_protocol_sha"
        ]
      },
      {
        "owner": "rulespace_v3.bridge",
        "name": "_build_bound_full_state_bridge_spec",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "factory", "wire_type": "VerifiedFactory"},
            {"name": "bridge_grid", "wire_type": "BridgeKGridManifest"},
            {"name": "parent_freeze_sha", "wire_type": "sha256"},
            {"name": "prestructure_authority_sha", "wire_type": "sha256"}
          ],
          "keyword_only_after": "bridge_grid",
          "returns": "FullStateBridgeSpec"
        },
        "legacy_delegate": "_expected_spec completes its legacy factory/prestructure join, derives the same unique grid, then calls once",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "bridge_grid is verified against live factory signed support and spatial shape",
          "B6 bridge_grid is exact-equal to the live BridgeGridAuthorityV3 body",
          "trials, seed, macro steps, resource caps and tolerance remain owner-frozen"
        ]
      },
      {
        "owner": "rulespace_v3.bridge",
        "name": "_audit_full_state_bridge_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "transition", "wire_type": "MeasuredTransition"},
            {"name": "factory", "wire_type": "VerifiedFactory"},
            {"name": "spec", "wire_type": "FullStateBridgeSpec"}
          ],
          "keyword_only_after": null,
          "returns": "BridgeAudit"
        },
        "legacy_delegate": "_expected_audit completes its legacy transition/factory/prestructure/spec join before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "symbol evaluation delegates to dynamics._transition_symbol_from_raw",
          "every frozen grid x macro-step x full-state trial executor case is replayed"
        ]
      },
      {
        "owner": "rulespace_v3.laurent",
        "name": "_preflight_laurent_resources_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "transition", "wire_type": "MeasuredTransition"},
            {"name": "stability_metric", "wire_type": "StabilityMetricWitness"}
          ],
          "keyword_only_after": null,
          "returns": "None"
        },
        "legacy_delegate": "certificate._preflight_laurent_resources reverifies the legacy transition before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "both canonical-structure and stability-metric convolution chains are resource-preflighted",
          "support, state count and dimension are read only from reconstructed raw bodies"
        ]
      },
      {
        "owner": "rulespace_v3.laurent",
        "name": "_build_laurent_residual_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "transition", "wire_type": "MeasuredTransition"},
            {"name": "structure", "wire_type": "StructureManifest"},
            {"name": "metric", "wire_type": "StabilityMetricWitness"},
            {"name": "protocol", "wire_type": "Fp64EnclosureProtocol"},
            {"name": "kind", "wire_type": "Literal[canonical-structure,stability-metric]"}
          ],
          "keyword_only_after": "protocol",
          "returns": "LaurentResidualCertificate"
        },
        "legacy_delegate": "_build_residual completes legacy transition/structure/metric verification before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "the existing exact convolution and fp64 outward-enclosure algorithm is single-owned",
          "operand SHAs bind the raw transition and reconstructed structure or metric"
        ]
      },
      {
        "owner": "rulespace_v3.spectral",
        "name": "_build_spectral_margin_coverage_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "transition", "wire_type": "MeasuredTransition"},
            {"name": "stability_metric", "wire_type": "StabilityMetricWitness"},
            {"name": "fp64_protocol", "wire_type": "Fp64EnclosureProtocol"},
            {"name": "dynamics_grid", "wire_type": "DynamicsKGridManifest"}
          ],
          "keyword_only_after": "fp64_protocol",
          "returns": "SpectralMarginCoverage"
        },
        "legacy_delegate": "legacy coverage builders reverify transition/structure/metric, derive the unique old grid, then call once",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "exact-zero singleton and full-64 paths share the same raw dispatcher",
          "B6 qualification and diagnostic grids both exact-equal the live DynamicsGridAuthorityV3 body",
          "Root64 hard columns, resource caps and spectral gates remain unchanged"
        ]
      },
      {
        "owner": "rulespace_v3.spectral",
        "name": "_build_normalized_metric_residual_audit_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "metric_residual", "wire_type": "LaurentResidualCertificate"},
            {"name": "spectral_margins", "wire_type": "SpectralMarginCoverage"}
          ],
          "keyword_only_after": null,
          "returns": "NormalizedMetricResidualAudit"
        },
        "legacy_delegate": "_expected_normalized_audit verifies all legacy source bodies before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "inputs are exact expected bodies reconstructed earlier in the same authority replay",
          "metric residual kind, fp64 protocol join, outward division and 1e-12 gate remain unchanged"
        ]
      },
      {
        "owner": "rulespace_v3.spectral",
        "name": "_build_power_drift_audit_from_raw",
        "visibility": "private-not-in-__all__",
        "signature": {
          "args": [
            {"name": "normalized", "wire_type": "NormalizedMetricResidualAudit"}
          ],
          "keyword_only_after": null,
          "returns": "PowerDriftAudit"
        },
        "legacy_delegate": "_expected_power_drift_audit reverifies the legacy normalized capability before one call",
        "b6_consumer": "rulespace_v3.certificate_v3",
        "invariants": [
          "normalized raw audit is exact-equal to the same replay's expected body",
          "directed repeated squaring delegates to fp64.compute_power_drift_bounds"
        ]
      }
    ],
    "already_owner_neutral_reuse": [
      {"owner": "rulespace_v3.dynamics", "name": "_transition_symbol_from_raw", "consumed_by": ["rulespace_v3.bridge"]},
      {"owner": "rulespace_v3.instability", "name": "_build_instability_growth_counter_witness_from_raw", "consumed_by": ["rulespace_v3.certificate_v3"]},
      {"owner": "rulespace_v3.instability", "name": "verify_instability_growth_counter_witness_arithmetic", "consumed_by": ["rulespace_v3.certificate_v3"]},
      {"owner": "rulespace_v3.fp64_protocol", "name": "build_fp64_enclosure_protocol", "consumed_by": ["rulespace_v3.certificate_v3"]},
      {"owner": "rulespace_v3.fp64_protocol", "name": "verify_fp64_enclosure_protocol", "consumed_by": ["rulespace_v3.certificate_v3"]},
      {"owner": "rulespace_v3.fp64", "name": "compute_power_drift_bounds", "consumed_by": ["rulespace_v3.spectral"]}
    ]
  },
  "b6_upstream_private_views": [
    {
      "owner": "rulespace_v3.transition_authority_v3",
      "name": "_reverify_verified_transition_authority_v3",
      "input": "VerifiedTransitionAuthorityV3",
      "returns": "_VerifiedTransitionAuthorityV3View",
      "required_fields": ["transition_authority", "parent", "materialization", "factory", "prestructure"],
      "exported_in___all__": false
    },
    {
      "owner": "rulespace_v3.metric_support_authority_v1",
      "name": "_reverify_verified_metric_signed_support_attestation_v1",
      "input": "VerifiedMetricSignedSupportAttestationV1",
      "returns": "_VerifiedMetricSupportAttestationV1View",
      "required_fields": ["attestation", "parent", "materialization", "factory", "factory_binding"],
      "exported_in___all__": false
    },
    {
      "owner": "rulespace_v3.runtime_grids_v3",
      "name": "_reverify_verified_bridge_grid_authority_v3",
      "input": "VerifiedBridgeGridAuthorityV3",
      "returns": "_VerifiedBridgeGridAuthorityV3View",
      "required_fields": ["grid_authority", "parent", "materialization", "factory", "factory_binding"],
      "exported_in___all__": false
    },
    {
      "owner": "rulespace_v3.runtime_grids_v3",
      "name": "_reverify_verified_dynamics_grid_authority_v3",
      "input": "VerifiedDynamicsGridAuthorityV3",
      "returns": "_VerifiedDynamicsGridAuthorityV3View",
      "required_fields": ["grid_authority", "parent", "transition", "metric_attestation"],
      "exported_in___all__": false
    }
  ],
  "fresh_b2_child_semantics": {
    "b2_owner_seam": "rulespace_v3.application_materialization_v3._require_v3m0_application_scenario_materialization_v3_for_parent",
    "replay_may_remint_factory_wrapper": true,
    "factory_wrapper_identity_comparison_allowed": false,
    "required_factory_equivalence": [
      "exact VerifiedFactory.factory raw body equality",
      "exact FactoryBranchBindingV3 equality",
      "exact branch role and factory SHA equality"
    ],
    "same_live_identity_scope": [
      "VerifiedParentFreezeV3",
      "VerifiedV3M0ApplicationScenarioMaterializationV3",
      "VerifiedParentV3ApplicationPrestructure"
    ],
    "operation_contracts": [
      "issue_transition_authority_v3 saves the B2 owner-seam child and compares only frozen factory equivalence",
      "verify_transition_authority_v3 replays B2, saves the fresh child and compares only frozen factory equivalence",
      "_reverify_verified_transition_authority_v3 returns the fresh child and preserves live Parent/materialization/prestructure identity",
      "verify_transition_pair_v3 permits distinct fresh factory wrappers while requiring exact body/binding/role/SHA joins",
      "all three B6 public APIs permit distinct fresh factory wrappers while requiring exact body/binding/role/SHA joins"
    ]
  },
  "b6_upstream_atomic_precondition": {
    "position": "BEFORE_ATTEMPT_AUDIT_OR_OUTCOME_CONSTRUCTION",
    "scope": "INPUT_CAPABILITY_VALIDITY_AND_CROSS_AUTHORITY_JOIN_ONLY",
    "applies_to": [
      "certify_transition_dynamics_v3",
      "verify_dynamics_certificate_v3",
      "verify_dynamics_certification_outcome_v3"
    ],
    "required_live_authorities": [
      "VerifiedParentFreezeV3",
      "VerifiedV3M0ApplicationScenarioMaterializationV3",
      "VerifiedTransitionAuthorityV3",
      "VerifiedMetricSignedSupportAttestationV1",
      "VerifiedBridgeGridAuthorityV3",
      "VerifiedDynamicsGridAuthorityV3"
    ],
    "attempt_sha_fields_populated_only_after_join": [
      "parent_freeze_v3_sha",
      "materialization_sha",
      "transition_authority_sha",
      "metric_attestation_sha",
      "bridge_grid_authority_sha",
      "dynamics_grid_authority_sha"
    ],
    "typed_exception": {
      "name": "DynamicsCertificationUpstreamJoinFailure",
      "reason_id_field": "reason_id",
      "detail_field": "detail",
      "reason_id_domain": [
        "PARENT_INVALID",
        "MATERIALIZATION_INVALID",
        "PRESTRUCTURE_INVALID",
        "TRANSITION_INVALID",
        "METRIC_ATTESTATION_INVALID",
        "BRIDGE_GRID_INVALID",
        "DYNAMICS_GRID_INVALID",
        "CROSS_AUTHORITY_JOIN"
      ],
      "exported_in___all__": true
    },
    "atomic_join_rules": [
      "reverify all six live upstream authorities before reading roots into an attempt audit",
      "reverify the nested Parent-v3 application prestructure through the transition private view",
      "join Parent/materialization/prestructure by live identity and factory branches by exact body/binding/role/SHA equivalence",
      "any invalid, dead, forged, tampered or cross-authority input raises one typed upstream join failure"
    ],
    "valid_join_does_not_prejudge_derived_scientific_evidence": true,
    "derived_judge_failures_after_valid_join": [
      "metric_raw_unresolved",
      "spectral_coverage_unresolved",
      "full_state_bridge_failed"
    ],
    "no_artifact_on_failure": [
      "DynamicsCertificationAttemptAuditV3",
      "DynamicsCertificationOutcomeV3",
      "DynamicsCertificateV3",
      "VerifiedDynamicsCertificationOutcomeV3",
      "VerifiedDynamicsCertificateV3"
    ],
    "opaque_registry_side_effect_allowed": false,
    "wire_only_nonissuable_failure_enum_values": [
      "prestructure_invalid",
      "transition_invalid"
    ],
    "issuable_outcome_failure_enum_values": [
      "reality_invalid",
      "laurent_resource_exceeded",
      "certified_instability_counterwitness",
      "structure_raw_unresolved",
      "metric_raw_unresolved",
      "spectral_coverage_unresolved",
      "normalized_metric_unresolved",
      "full_state_bridge_failed",
      "power_drift_unresolved"
    ],
    "enum_catalog_mutation_allowed": false
  },
  "runtime_v3_private_authority": {
    "owner": "rulespace_v3.runtime",
    "raw_record": "RuntimeEvidenceManifest",
    "raw_record_schema": "v3m0.runtime-evidence-manifest.v1",
    "authority_symbol": "_V3_RUNTIME_AUTHORITY",
    "evaluator_id": "rulespace-v3m0-parent-v3-certificate-closure-v1",
    "fresh_process_import_roots": ["rulespace_v3.certificate_v3"],
    "transitive_loaded_module_inventory": true,
    "caller_import_roots_allowed": false,
    "caller_runtime_manifest_allowed": false,
    "private_apis_exported_in___all__": false,
    "private_apis": [
      {"name": "_runtime_evidence_manifest_v3_payload", "args": [{"name": "manifest", "wire_type": "RuntimeEvidenceManifest"}], "returns": "dict[str,object]"},
      {"name": "_issue_runtime_evidence_manifest_v3", "args": [], "returns": "RuntimeEvidenceManifest"},
      {"name": "_verify_runtime_evidence_manifest_v3", "args": [{"name": "manifest", "wire_type": "RuntimeEvidenceManifest"}], "returns": "RuntimeEvidenceManifest"}
    ],
    "legacy_public_authority_unchanged": {
      "evaluator_id": "rulespace-v3m0-certificate-closure-v1",
      "public_apis": ["runtime_evidence_manifest_payload", "issue_runtime_evidence_manifest", "verify_runtime_evidence_manifest"],
      "import_roots": [
        "rulespace_v3.bridge",
        "rulespace_v3.certificate",
        "rulespace_v3.dynamics",
        "rulespace_v3.fp64_protocol",
        "rulespace_v3.grids",
        "rulespace_v3.instability",
        "rulespace_v3.laurent",
        "rulespace_v3.metric",
        "rulespace_v3.parent_freeze",
        "rulespace_v3.prestructure",
        "rulespace_v3.qualification",
        "rulespace_v3.registry",
        "rulespace_v3.runtime",
        "rulespace_v3.spectral",
        "rulespace_v3.structure"
      ],
      "wire_evaluator_roots_inventory_and_hash_algorithm_bit_identity_required": true,
      "same_source_snapshot_manifest_determinism_required": true,
      "historical_manifest_value_persistence_across_source_edits": false,
      "historical_manifest_after_source_edit": "MUST_FAIL_FRESH_REVERIFICATION"
    },
    "failure_semantics": "runtime or fp64 infrastructure failure raises without issuing a scientific outcome or certificate",
    "subprocess_edge_semantics": "fresh-process import root is not a parent-process static import edge"
  },
  "legacy_delegation_and_regression_locks": {
    "global_invariants": [
      "legacy public signatures, __all__, exact authority types and wire schemas do not change",
      "every legacy wrapper completes its original live authority join before one neutral-core call",
      "legacy reconstructed raw records and every recursive SHA remain byte-identical",
      "neutral cores are closure-captured or otherwise protected from public-global redirect",
      "V3 code never mints or accepts legacy VerifiedTransition or VerifiedPrestructureAuthority"
    ],
    "delegation_map": [
      {"owner": "rulespace_v3.dynamics", "legacy_functions": ["_remeasure_transition"], "neutral_cores": ["_measure_bound_realspace_transition"]},
      {"owner": "rulespace_v3.structure", "legacy_functions": ["_expected_structure", "_expected_reality"], "neutral_cores": ["_build_bound_synthetic_structure_manifest", "_build_reality_certificate_from_raw"]},
      {"owner": "rulespace_v3.metric", "legacy_functions": ["_expected_metric"], "neutral_cores": ["_build_bound_synthetic_identity_metric"]},
      {"owner": "rulespace_v3.bridge", "legacy_functions": ["_expected_spec", "_expected_audit"], "neutral_cores": ["_build_bound_full_state_bridge_spec", "_audit_full_state_bridge_from_raw"]},
      {"owner": "rulespace_v3.laurent", "legacy_functions": ["_build_residual"], "neutral_cores": ["_build_laurent_residual_from_raw"]},
      {"owner": "rulespace_v3.certificate", "legacy_functions": ["_preflight_laurent_resources"], "neutral_cores": ["_preflight_laurent_resources_from_raw"]},
      {"owner": "rulespace_v3.spectral", "legacy_functions": ["_expected_exact_zero_coverage", "_expected_nonzero_coverage", "_expected_normalized_audit", "_expected_power_drift_audit"], "neutral_cores": ["_build_spectral_margin_coverage_from_raw", "_build_normalized_metric_residual_audit_from_raw", "_build_power_drift_audit_from_raw"]}
    ],
    "required_tests": [
      "legacy output record and SHA golden equality before versus after extraction",
      "legacy public signature and __all__ snapshot",
      "old live join happens before the neutral core and the core is called exactly once",
      "forged/dead/tampered old opaque rejection remains unchanged",
      "post-freeze global redirect cannot bypass a captured authority or neutral core",
      "legacy runtime wire, evaluator, roots, inventory rules and hash algorithm stay bit-identical",
      "the same source snapshot reproduces the same manifest; any source edit invalidates the historical manifest"
    ]
  },
  "task_delta": {
    "B3": {
      "file_boundary": {
        "create": [
          "rulespace_v3/parent_v3_application_prestructure.py",
          "tests/test_v3m0_parent_v3_application_prestructure.py",
          "rulespace_v3/transition_authority_v3.py",
          "tests/test_v3m0_transition_authority_v3.py"
        ],
        "modify": [
          "rulespace_v3/dynamics.py",
          "tests/test_v3m0_dynamics.py"
        ]
      },
      "owned_records": [
        "ParentV3ApplicationPrestructure",
        "MeasuredTransition",
        "TransitionAuthorityV3"
      ],
      "public_opaque_wrappers": ["VerifiedTransitionAuthorityV3"],
      "owner_internal_opaque_wrappers": ["VerifiedParentV3ApplicationPrestructure"],
      "public_apis": [
        {
          "name": "issue_transition_authority_v3",
          "args": [
            {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
            {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
            {"name": "factory_role", "wire_type": "Literal[actual,matched_ablated]"}
          ],
          "returns": "VerifiedTransitionAuthorityV3",
          "raw_hydration_allowed": false
        },
        {
          "name": "verify_transition_authority_v3",
          "args": [
            {"name": "transition", "wire_type": "TransitionAuthorityV3"},
            {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
            {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"}
          ],
          "returns": "VerifiedTransitionAuthorityV3",
          "raw_hydration_allowed": false
        },
        {
          "name": "verify_transition_pair_v3",
          "args": [
            {"name": "parent", "wire_type": "VerifiedParentFreezeV3"},
            {"name": "materialization", "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"},
            {"name": "actual_transition", "wire_type": "VerifiedTransitionAuthorityV3"},
            {"name": "matched_ablated_transition", "wire_type": "VerifiedTransitionAuthorityV3"}
          ],
          "returns": "tuple[VerifiedTransitionAuthorityV3,VerifiedTransitionAuthorityV3]",
          "raw_hydration_allowed": false
        }
      ],
      "typed_failures": [
        "MATERIALIZATION_INVALID",
        "PRESTRUCTURE_INVALID",
        "EXECUTOR_FAILED",
        "TRANSITION_MEASUREMENT_FAILED",
        "SUPPORT_INVALID",
        "BRANCH_JOIN_FAILED",
        "CROSS_PARENT_ROOT"
      ],
      "invariants": [
        "current C19 measurement is exact 20-channel full-state, never a four-channel stand-in",
        "new prestructure is owner-derived before measurement and recursively retained",
        "actual/matched pair is atomically reverified under one live Parent and materialization"
      ]
    },
    "B6": {
      "file_boundary": {
        "create": [
          "rulespace_v3/certificate_v3.py",
          "tests/test_v3m0_certificate_v3.py"
        ],
        "modify": [
          "rulespace_v3/structure.py",
          "tests/test_v3m0_structure.py",
          "rulespace_v3/metric.py",
          "tests/test_v3m0_metric.py",
          "rulespace_v3/bridge.py",
          "tests/test_v3m0_bridge.py",
          "rulespace_v3/laurent.py",
          "tests/test_v3m0_laurent.py",
          "rulespace_v3/spectral.py",
          "tests/test_v3m0_spectral.py",
          "tests/test_v3m0_spectral_nonzero.py",
          "rulespace_v3/runtime.py",
          "tests/test_v3m0_runtime.py",
          "rulespace_v3/certificate.py",
          "tests/test_v3m0_certificate.py"
        ]
      },
      "record_field_replacements": [
        "DynamicsCertificateV3.prestructure_authority: PrestructureAuthority -> ParentV3ApplicationPrestructure"
      ],
      "consume_private_api": "rulespace_v3.transition_authority_v3._reverify_verified_transition_authority_v3",
      "consume_private_view_field": "prestructure",
      "consume_private_apis": [
        "rulespace_v3.transition_authority_v3._reverify_verified_transition_authority_v3",
        "rulespace_v3.metric_support_authority_v1._reverify_verified_metric_signed_support_attestation_v1",
        "rulespace_v3.runtime_grids_v3._reverify_verified_bridge_grid_authority_v3",
        "rulespace_v3.runtime_grids_v3._reverify_verified_dynamics_grid_authority_v3",
        "rulespace_v3.runtime._issue_runtime_evidence_manifest_v3",
        "rulespace_v3.runtime._verify_runtime_evidence_manifest_v3"
      ],
      "owner_neutral_core_names": [
        "_build_bound_synthetic_structure_manifest",
        "_build_reality_certificate_from_raw",
        "_build_bound_synthetic_identity_metric",
        "_build_bound_full_state_bridge_spec",
        "_audit_full_state_bridge_from_raw",
        "_preflight_laurent_resources_from_raw",
        "_build_laurent_residual_from_raw",
        "_build_spectral_margin_coverage_from_raw",
        "_build_normalized_metric_residual_audit_from_raw",
        "_build_power_drift_audit_from_raw"
      ],
      "same_live_parent_materialization_prestructure_identity_required": true,
      "factory_wrapper_identity_required": false,
      "copy_or_rederive_algorithm_allowed": false,
      "legacy_opaque_use_allowed": false,
      "caller_runtime_allowed": false,
      "metric_origin_binding": "MetricOriginManifest.derivation_or_preregistration_sha == MetricSignedSupportAttestationV1.metric_support_protocol_sha",
      "exact_joins": [
        "certificate.prestructure_authority == certificate.transition_authority.prestructure_authority",
        "certificate.prestructure_authority.prestructure_authority_sha == certificate.transition_authority.measured_transition.prestructure_authority_sha",
        "live transition view prestructure raw body == certificate.prestructure_authority",
        "Parent/materialization/prestructure capability identities agree; fresh factory wrappers may differ but exact factory bodies, bindings, roles and SHAs agree",
        "metric attestation, bridge grid and dynamics grid live views share the same Parent/materialization/branch identities",
        "bridge spec grid equals the live BridgeGridAuthorityV3.bridge_grid body",
        "spectral qualification and diagnostic grids equal the live DynamicsGridAuthorityV3.dynamics_grid body"
      ],
      "failure_contract": {
        "enum_values_and_declaration_order_unchanged": true,
        "wire_only_nonissuable_values": [
          "prestructure_invalid",
          "transition_invalid"
        ],
        "execution_order": [
          "reality_invalid",
          "laurent_resource_exceeded",
          "certified_instability_counterwitness",
          "structure_raw_unresolved",
          "metric_raw_unresolved",
          "spectral_coverage_unresolved",
          "normalized_metric_unresolved",
          "full_state_bridge_failed",
          "power_drift_unresolved"
        ],
        "v6_ambiguity_resolution": "the enum declaration order is a wire/API freeze; upstream join failures raise before outcome construction, and issuable first-failure execution keeps the Jordan check after Laurent preflight and before structure/metric judges",
        "runtime_or_fp64_infrastructure_failure": "raise without issuing a scientific outcome or certificate"
      }
    }
  },
  "typed_failure_routing": [
    {"reason_id": "MATERIALIZATION_INVALID", "required_attack_classes": ["raw/dead/forged/equal-copy materialization", "materialization replay failure"]},
    {"reason_id": "PRESTRUCTURE_INVALID", "required_attack_classes": ["raw/dead/forged/tampered new prestructure", "pair/basis/block-J/self-hash drift"]},
    {"reason_id": "EXECUTOR_FAILED", "required_attack_classes": ["factory executor exception", "executor dtype/shape/non-finite drift"]},
    {"reason_id": "TRANSITION_MEASUREMENT_FAILED", "required_attack_classes": ["kernel or transition self-hash tamper", "raw transition differs from fresh full-state remeasurement"]},
    {"reason_id": "SUPPORT_INVALID", "required_attack_classes": ["support sort/uniqueness/sign/no-wrap drift", "non-positive-zero coefficient outside declared support"]},
    {"reason_id": "BRANCH_JOIN_FAILED", "required_attack_classes": ["factory role/SHA/binding/prestructure/transition mismatch", "actual-matched swap, duplicate or cross-pair splice"]},
    {"reason_id": "CROSS_PARENT_ROOT", "required_attack_classes": ["different live Parent-v3 identity", "parent root splice anywhere in recursive bodies"]}
  ],
  "b6_typed_failure_routing": [
    {
      "failure": "prestructure_invalid",
      "enum_declaration_index": 0,
      "execution_index": null,
      "route_kind": "UPSTREAM_PRECONDITION_TYPED_RAISE_NO_OUTCOME",
      "outcome_issuable": false,
      "typed_exception_reason_id": "PRESTRUCTURE_INVALID",
      "judge_owner": "rulespace_v3.parent_v3_application_prestructure",
      "required_attack_classes": [
        "Parent/materialization/prestructure live identity or recursive root failure",
        "legacy, raw, forged, dead, equal-copy or self-resigned prestructure"
      ],
      "completed_evidence_prefix": []
    },
    {
      "failure": "transition_invalid",
      "enum_declaration_index": 1,
      "execution_index": null,
      "route_kind": "UPSTREAM_PRECONDITION_TYPED_RAISE_NO_OUTCOME",
      "outcome_issuable": false,
      "typed_exception_reason_id": "TRANSITION_INVALID",
      "judge_owner": "rulespace_v3.transition_authority_v3",
      "required_attack_classes": [
        "transition authority identity, branch, factory, support or full-state wire mismatch",
        "fresh real-space impulse remeasurement differs from embedded MeasuredTransition"
      ],
      "completed_evidence_prefix": []
    },
    {
      "failure": "reality_invalid",
      "enum_declaration_index": 2,
      "execution_index": 0,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.structure",
      "required_attack_classes": [
        "factory coefficient or transition-kernel imaginary wire is not bit-exact positive zero",
        "classical reality convention, state or structure binding drift"
      ],
      "completed_evidence_prefix": []
    },
    {
      "failure": "laurent_resource_exceeded",
      "enum_declaration_index": 3,
      "execution_index": 1,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.laurent",
      "required_attack_classes": [
        "canonical-structure convolution support or work cap exceeded",
        "stability-metric convolution support or work cap exceeded"
      ],
      "completed_evidence_prefix": ["reality"]
    },
    {
      "failure": "certified_instability_counterwitness",
      "enum_declaration_index": 10,
      "execution_index": 2,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.instability",
      "required_attack_classes": [
        "exact bit-level Jordan profile with exact origin support",
        "arithmetic witness reconstruction and strict growth proof"
      ],
      "completed_evidence_prefix": ["reality"],
      "evidence": "InstabilityGrowthCounterWitness",
      "status_semantics": "UNSTABLE",
      "exact_profile_only": "exact-zero-offset-jordan-2x2-v1"
    },
    {
      "failure": "structure_raw_unresolved",
      "enum_declaration_index": 4,
      "execution_index": 3,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.laurent",
      "required_attack_classes": [
        "canonical block-J StructureManifest reconstruction failure",
        "canonical-structure Laurent raw supremum exceeds the frozen gate"
      ],
      "completed_evidence_prefix": ["reality"]
    },
    {
      "failure": "metric_raw_unresolved",
      "enum_declaration_index": 5,
      "execution_index": 4,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.metric+rulespace_v3.laurent",
      "required_attack_classes": [
        "B4 metric protocol, I20, origin support, origin binding or witness reconstruction failure",
        "stability-metric Laurent raw residual reconstruction failure"
      ],
      "completed_evidence_prefix": ["reality", "structure_residual"]
    },
    {
      "failure": "spectral_coverage_unresolved",
      "enum_declaration_index": 6,
      "execution_index": 5,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.spectral",
      "required_attack_classes": [
        "B5 dynamics-grid authority or grid/body exact-equality failure",
        "Root64 hard enclosure, resource cap or covered spectral margin failure"
      ],
      "completed_evidence_prefix": ["reality", "structure_residual", "metric_residual"]
    },
    {
      "failure": "normalized_metric_unresolved",
      "enum_declaration_index": 7,
      "execution_index": 6,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.spectral",
      "required_attack_classes": [
        "metric residual, coverage or fp64 protocol SHA join failure",
        "outward normalized metric residual exceeds the frozen 1e-12 gate"
      ],
      "completed_evidence_prefix": ["reality", "structure_residual", "metric_residual", "spectral_margins"]
    },
    {
      "failure": "full_state_bridge_failed",
      "enum_declaration_index": 8,
      "execution_index": 7,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.bridge",
      "required_attack_classes": [
        "B5 bridge-grid authority or bridge spec/grid exact-equality failure",
        "executor versus raw-symbol full-state bridge residual exceeds the frozen gate"
      ],
      "completed_evidence_prefix": ["reality", "structure_residual", "metric_residual", "spectral_margins", "normalized_metric_residual"]
    },
    {
      "failure": "power_drift_unresolved",
      "enum_declaration_index": 9,
      "execution_index": 8,
      "route_kind": "OUTCOME_FIRST_FAILURE",
      "outcome_issuable": true,
      "judge_owner": "rulespace_v3.spectral+rulespace_v3.fp64",
      "required_attack_classes": [
        "normalized raw audit reconstruction or binding failure",
        "fourteen directed squarings or frozen 1e-8 drift gate failure"
      ],
      "completed_evidence_prefix": ["reality", "structure_residual", "metric_residual", "spectral_margins", "normalized_metric_residual", "full_state_bridge_audit"]
    }
  ],
  "attack_matrix": [
    "legacy VerifiedPrestructureAuthority and PrestructureAuthority v1",
    "legacy VerifiedTransition and naked MeasuredTransition",
    "historical Parent-v1/v2 or current raw Parent-v3",
    "raw/forged/dead/equal-copy B2 materialization",
    "raw/forged/dead/tampered ParentV3ApplicationPrestructure",
    "caller factory, pair snapshot, basis, structure form or any SHA",
    "caller kernel, support, state/grid/dt/boundary/macro-step",
    "analytic, FFT, reduced-state or per-k projector measurement",
    "self-resigned recursive body mutation",
    "actual/matched swap, duplicate, half-pair or cross-pair splice",
    "cross-parent identity or root splice",
    "forged/dead/tampered VerifiedTransitionAuthorityV3",
    "public-function global redirect or owner-registry bypass"
  ],
  "b6_attack_matrix": [
    "legacy VerifiedFactory, VerifiedPrestructureAuthority, VerifiedTransition or VerifiedNormalizedMetricResidualAudit",
    "caller raw prestructure, transition, structure, metric, grid, fp64, bridge, Laurent, spectral, normalized, power or runtime body",
    "raw/dead/forged/equal-copy/tampered Parent-v3, materialization, transition, metric or grid capability",
    "cross-parent, cross-materialization, cross-branch, role swap, duplicate branch or half-pair splice",
    "self-resigned nested Parent, prestructure, transition, attestation, grid or evidence body",
    "bridge and dynamics grid swap, caller points, or grid body differing from its live authority",
    "metric protocol, I20 body, origin support, protocol SHA or metric-origin binding drift",
    "legacy transition-registry injection, union registration or replay-callback substitution",
    "analytic, FFT, reduced-state, per-k projector or caller kernel substitute",
    "old normalized opaque injection or duplicated Laurent, spectral, normalized or power algorithm",
    "V3 runtime evaluator id, import roots, transitive source closure, environment or manifest SHA drift",
    "success/failure XOR violation, non-prefix attempt evidence or evidence from an unreached stage",
    "non-Jordan, approximate-Jordan, wrong-support or self-resigned instability witness",
    "public-function global redirect, private-view bypass or owner-registry bypass"
  ],
  "import_dag_delta": {
    "nodes": {
      "rulespace_v3.parent_v3_application_prestructure": [
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.evidence",
        "rulespace_v3.factory"
      ],
      "rulespace_v3.transition_authority_v3": [
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.dynamics",
        "rulespace_v3.evidence",
        "rulespace_v3.parent_v3_application_prestructure"
      ],
      "rulespace_v3.certificate_v3": [
        "rulespace_v3.application_materialization_v3",
        "rulespace_v3.transition_authority_v3",
        "rulespace_v3.parent_v3_application_prestructure",
        "rulespace_v3.metric_support_authority_v1",
        "rulespace_v3.runtime_grids_v3",
        "rulespace_v3.certificate",
        "rulespace_v3.dynamics",
        "rulespace_v3.structure",
        "rulespace_v3.metric",
        "rulespace_v3.bridge",
        "rulespace_v3.instability",
        "rulespace_v3.laurent",
        "rulespace_v3.spectral",
        "rulespace_v3.fp64_protocol",
        "rulespace_v3.runtime"
      ]
    },
    "external_or_preexisting_leaves": [
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.bridge",
      "rulespace_v3.certificate",
      "rulespace_v3.dynamics",
      "rulespace_v3.evidence",
      "rulespace_v3.factory",
      "rulespace_v3.fp64_protocol",
      "rulespace_v3.instability",
      "rulespace_v3.laurent",
      "rulespace_v3.metric",
      "rulespace_v3.metric_support_authority_v1",
      "rulespace_v3.runtime",
      "rulespace_v3.runtime_grids_v3",
      "rulespace_v3.spectral",
      "rulespace_v3.structure"
    ],
    "forbidden_edges": [
      ["rulespace_v3.parent_v3_application_prestructure", "rulespace_v3.prestructure"],
      ["rulespace_v3.transition_authority_v3", "rulespace_v3.prestructure"],
      ["rulespace_v3.transition_authority_v3", "rulespace_v3.parent_authority_v3"],
      ["rulespace_v3.certificate_v3", "rulespace_v3.prestructure"],
      ["rulespace_v3.parent_v3_application_prestructure", "rulespace_v3.transition_authority_v3"]
    ],
    "fresh_process_probe_edges": [
      ["rulespace_v3.runtime._V3_RUNTIME_AUTHORITY", "rulespace_v3.certificate_v3"]
    ],
    "fresh_process_probe_edge_policy": "SUBPROCESS_IMPORT_ROOT_NOT_A_STATIC_PARENT_IMPORT_EDGE",
    "cycle_policy": "STRICT_DIRECT_DAG_NO_TRANSITIVE_BACK_EDGE"
  },
  "legacy_immutability": {
    "prestructure_v1_record_schema": "v3m0.prestructure-authority.v1",
    "prestructure_v1_record_fields": [
      "authority_schema_version",
      "authority_kind",
      "parent_freeze",
      "factory_sha",
      "factory_role",
      "ablation_pair_snapshot",
      "ablation_manifest_sha",
      "ablation_construction_sha",
      "synthetic_registry",
      "synthetic_registry_entry_sha",
      "synthetic_preregistration",
      "synthetic_application_spec",
      "synthetic_application_scenario_spec",
      "synthetic_application_permit_sha",
      "synthetic_scenario_construction_sha",
      "adapter_preregistration",
      "authority_sha"
    ],
    "measured_transition_schema": "v3m0.measured-transition.v1",
    "measured_transition_fields": [
      "transition_schema_version",
      "parent_freeze_sha",
      "prestructure_authority_sha",
      "factory_sha",
      "factory_role",
      "state_schema_id",
      "channel_order",
      "spatial_shape",
      "dt",
      "boundary_manifest_id",
      "state_basis_convention_id",
      "kernel",
      "support_offsets",
      "support_sha",
      "macro_steps",
      "transition_sha"
    ],
    "dynamics_public_signatures": [
      "measure_transition(factory,authority)",
      "verify_measured_transition(transition,factory,authority)",
      "transition_kernel_array(transition)",
      "transition_symbol(transition,momentum)"
    ],
    "prestructure_public_issuers_unchanged": [
      "issue_synthetic_prestructure_authority",
      "verify_synthetic_prestructure_authority",
      "issue_v3m0_application_prestructure_authority"
    ],
    "legacy_wire_mutation_allowed": false,
    "legacy_public_api_mutation_allowed": false,
    "new_private_core_exported_in_dynamics_all": false
  }
}
```
<!-- END V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->

## 9. 实施门

v7 合同先于 B3 production 实现。顺序固定为：

1. v7 机器 registry 通过 strict JSON、duplicate-key、golden 与 DAG 无环测试；
2. 独立评审确认 wire、owner、private view、shared core 与 B6 join；
3. 重写 B3 strict RED，其 full-state fixture 必须是 current C19 exact 20-channel；
4. 先实现 dynamics shared core 并证明 legacy 回归，再实现新 prestructure owner 与
   transition owner；
5. B4/B5 先完成各自 live capability 的私有 reverifier/view，然后才能被 B6 消费；
6. 各 legacy owner 先抽出 owner-neutral 数值核心，并以原记录、SHA、签名和
   `__all__` 回归证明委托不改语义；
7. 建立并验证 V3 runtime 私有 authority，legacy evaluator 与 source closure 必须位级不变；
8. B6 先按冻结 first-failure/attack matrix 进入 strict RED，再实现同一 live
   prestructure 与 B4/B5/runtime 原子总装。

任何实现若需要改动 legacy `PrestructureAuthority` wire，公开 dynamics/prestructure
API，或需要从 SHA 伪造 current prestructure，必须停止并回到设计裁定，不得以 adapter
或放宽测试绕过。
