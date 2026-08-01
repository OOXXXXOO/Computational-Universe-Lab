# v3 设计勘误：Parent-v3 downstream production chain

*Computational Universe Lab · Projective Rule-Space Program · 2026-08-01 · 状态：DRAFT / B0 设计冻结 / 未签发*

> 任务：V3-M0 Phase B / B0
> 适用顺序：Parent-v3 P-epoch 签发勘误 → C19 refreeze-v2 与 metric-support authority → V3-M0 任务书 → 本文。

## 0. 裁定边界

本文只冻结 B1–B10 的 future production contract。它不签发 Parent、calibration、permit、
materialization、transition、metric attestation、grid、certificate、response、evidence、
ResponseBlock、run、checkpoint 或科学状态；登记表中的实现状态均为
`EXPECTED-MISSING_AT_B0_FREEZE`，`issued_statuses=[]`。

本文不复制、不修改、也不新增数值阈值。`threshold_values={}`；凡 wire 中出现的 tolerance
或 gate scalar，后续实现只能从既有权威 protocol/body 递归取得并重算。状态 literal 被登记仅为
typed resolver 与 portable ceiling 的闭集，不代表本文件签发该状态。

## 1. exact wire 解释规则

`record_catalog` 是唯一机器合同。每个 record 都有唯一 schema ID、canonical owner、按 wire
顺序排列的 `field_specs` 与 `record_invariants`。每个 field 明确：

- exact wire type；
- 字段是否固定存在但可为 null；
- literal domain；
- tuple 的 exact/nonempty/derived/bounded cardinality；
- nested full body 的 catalog 引用；
- 额外 shape、order、XOR 或 provenance 约束。

`nested_record` 不是 SHA shortcut：它要求序列化完整 nested body，且该名字必须在同一 catalog
中有完整 ordered field body。标为 `canonical-json-object` 的既有叶类型必须在 field constraint
指向唯一 canonical owner payload function，并保存其完整 raw body；不得用 ID、SHA、dict subclass
或旧 opaque wrapper 替代。所有 dataclass
均须 exact frozen type，拒绝未知/缺失字段、bool-as-int、container subclass 与逐层重签。

`apis` 使用结构化 args/return，不再用不可解析的签名字符串。所有 API 的
`raw_hydration_allowed=false`：verifier 读取 raw body 时必须携带表中列出的 live opaque
输入，或在 B10 显式 detached 路径中携带完整 frozen body 与全部原始 bytes；只有重放
executor/source/P-blob/签名/bytes 后才可返回 owner wrapper，自哈希不构成 authority。

## 2. production chain 与原子性

唯一顺序为：

```text
VerifiedParentFreezeV3
→ full WindowCalibrationOutcome/Manifest/Selection
→ PermitV3（full calibration + current application/scenario/response）
→ materialization（full basis/trace/AblationPairSnapshot/two factories）
→ same-branch transition + metric signed support + strict runtime grids
→ same-branch recursive DynamicsCertificationOutcomeV3
→ actual ReferenceOutcome → actual ShellOutcome
→ atomic actual/matched PairedResponseOutcome
→ closed control evidence
→ rulespace_v3.blocks 签 existing VerifiedResponseBlock
→ post-block control-only geometry evaluation
→ Parent-v3 P-blob replayed V3-M0 assembly
→ signed portable checkpoint
```

actual 与 matched_ablated 必须共享 Parent、permit、materialization、protocol、basis、response
grid、ResponseRunSpec、actual-selected reference/shell 与 Fejér order。任何一支失败都保留 typed
attempt，但不得泄漏半对 capability。matched_ablated 不得重寻 reference 或 shell。

## 3. B1–B7 的关键修正

B1 递归保存既有 `WindowCalibrationOutcome`；它继续内嵌完整 manifest 与 optional selection。
calibration 同时保存 Parent-v3 的完整 20 项 tagged current-application registry wire/root，以及按
Parent-v1 原 ordinal 选出的 C01--C03 inherited-V2 full-body replay refs。历史 Parent-v1 只能作为
内部数值 witness，且必须与 live Parent-v3 内嵌 historical body 精确相等；不得构造、伪填或冒充
Parent-v2 registry/window/root。PermitV3 再内嵌完整 calibration、`CurrentApplicationAuthorityV3`、
`CurrentScenarioAuthorityV3` 和 `CurrentScenarioResponseContractV3`。V1/V2 calibration、
permit 或 opaque adapter 均不得进入该链。

C01--C03 replay ref 中的 V2 application/scenario/response 不是泛化 JSON 叶：本冻结逐字段登记
`ScenarioBasisSelectorSpec`、`CurrentScenarioResponseContractV2`、
`CurrentScenarioAuthorityV2`、`CurrentApplicationAuthorityV2`，并分别钉住
`scenario_basis_selector_spec_payload`、`current_scenario_response_contract_v2_payload`、
`current_scenario_authority_v2_payload`、`current_application_authority_v2_payload` 的完整 owner wire。

`rulespace_v3.task11_runner` 必须新增唯一 owner-internal
`_run_task11_window_calibration_from_task8_replay(historical_parent, task8_replay)`。它只接收 exact
historical `VerifiedParentFreeze` 与 exact `CurrentTask8ControlReplay`，在内部重建 authority-neutral
legacy registry/window 并运行六个 frozen order；不得接收 `current_registry`、`current_window` 或
`parent_freeze_v2_sha`。返回的 raw `WindowCalibrationOutcome` 不带 authority。既有 public V2
`run_task11_window_calibration(current_window)` 的签名与行为不变，但两条路线必须委托同一数值 core。

B1 文件边界固定为：CREATE `rulespace_v3/application_authority_v3.py`、CREATE
`tests/test_v3m0_application_authority_v3.py`、MODIFY `rulespace_v3/task11_runner.py`、MODIFY
`tests/test_v3m0_task11_runner.py`；后两项必须验证 shared-core delegation 与旧 V2 public runner 回归。

B2 固定完整 C19 `B_plus/P/I20/I10` bodies、construction trace、
`AblationPairSnapshot` 与两个完整 `LinearRealspaceFactory` branch bindings。C19 literal 计数
为 actual/matched active 50/30、slots 50/50、primitives 50/50、matched neutral identities 20。

B3 复用 canonical `MeasuredTransition` full body；state schema、channel order、spatial shape、
dt、periodic boundary、channel-identity basis、full kernel/support 和 `macro_steps=1` 均在 wire 中。
公开测量只从 live Parent-v3 + materialization + branch role 发出
`VerifiedTransitionAuthorityV3`；不公开 `VerifiedFactory`、`VerifiedPrestructureAuthority`、
`VerifiedTransition`、裸 `MeasuredTransition`、kernel 或 projector 入口。actual/matched 对必须在同一
Parent/materialization 下原子重验。

B4 record/wrapper/issuer 名严格采用 metric-support authority 勘误：
`MetricSignedSupportAttestationV1` /
`VerifiedMetricSignedSupportAttestationV1` /
`issue_c19_metric_signed_support_attestation_v1`。issuer 的第三参数只有 factory role；没有
caller support、grid、metric body 或 SHA。

B5 的 Response/Dynamics/Bridge grid 是三个不兼容 strict record。C19 response 是唯一冻结的
directional node；zero-support dynamics 为 denominator 1 的 origin singleton；zero-support bridge
仍以 realspace shape 8 为 denominator；metric support 是 I20 的 origin singleton。

B6 复用既有 `DynamicsCertificationFailure` 值及顺序，但新签发的
`DynamicsCertificateV3`/`DynamicsCertificationOutcomeV3` 必须同时绑定 live Parent、
materialization、`TransitionAuthorityV3`、metric attestation、bridge grid authority 和 dynamics grid
authority。旧 factory/transition/prestructure opaque 与 caller raw structure/metric/grid/runtime 入口全部禁止。
证书递归保存 transition、prestructure、
structure/reality、metric origin/witness、fp64 protocol/root table、full-state bridge、
两份 Laurent raw enclosure、spectral coverage、normalized audit、power audit 与 runtime。成功/
失败 payload 严格 XOR；只有 exact Jordan counterwitness 可产生 UNSTABLE evidence。

B7 恢复 Reference → Shell → Paired 三层 raw typed outcome/attempt graph及三个 opaque outcome。
`ResponseRunSpec` 保存完整 basis、strict response/bridge grids、frozen source steps/trials 与既有
tolerance。reference/shell 只由 actual certificate 选择；paired body 同时保存两份完整 certificate
与 response body。失败保留上游成功层，没有 flat SHA、string failure 或 half pair。

## 4. B8 evidence、blocks 与 C19 boundary

静态方向固定为：

```text
application_response_v3
  → control_application_evidence_v3
    → rulespace_v3.blocks
      → control_geometry_evaluation_v3
```

closed evidence record 不含 block 或 geometry evaluation。它先递归重验 Parent→paired response
全链；随后 `rulespace_v3.blocks` 作为 `ResponseBlock` 的既有 canonical owner，从 closed
evidence 分支签发 `VerifiedResponseBlock`。geometry evaluator 位于 blocks 之后，消费两支
verified block，因而不会形成 evidence↔blocks 或 blocks↔evaluation 环。

C19 始终为 `OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY`、
`NULL_INTERVENTION_INVARIANCE_CONTROL`、physical/family `INELIGIBLE`。前六项 analytic
prerequisite 加上“actual source/readout 共享同一 endpoint shell 且 paired response finite”共七项，
只能在 response blocks 后逐项形成 control evidence。不得写成 trigger、科学 PASS/FAIL、物理锚或
family 资格。

## 5. B9 Parent-v3 first authorization 与 typed assembly

C01–C18/C20 不能借旧 Parent-v1/v2 opaque authority 重放。通用
`ParentV3ScenarioReplayAuthorityV1` 必须携带 full Parent-v3 raw body、P commit、原 ordinal、
完整 application/scenario bodies 与 P-blob closure；其 opaque wrapper 才是这些 inherited case
在新 epoch 的 first authorization。C19 只走 current `CurrentApplicationAuthorityV3` 路径。

assembly 同时保存：

- BLOCK_SUCCESS 的 closed evidence；
- C11/C13/C14 的 exact typed termination attempts，且 downstream capability 固定为 false；
- C20 clean-zero/true-floor 的 full deterministic-series/Sigma evidence；
- calibration bodies；
- I01–I09 的 ordered representation-invariant outcomes；
- raw `V3M0StateDecisionV3` 与全部 ordered undefined pairs。

四个 JSON leaf 的 path、kind、schema、order 在 registry 中逐项固定；图像不进入 portable root。

## 6. B10 portable handoff

通用 campaign layer自有 reviewer key/registry/receipt/signing-audit primitives，不 import
Parent-specific reviewer 或 signing-audit modules。Stage freeze 递归绑定 previous envelope、
taskbook path/body、manifest path/body/schema、source closure、P/S commits、双 receipts、
reviewer registry 与 strict diff。Run permit 内嵌 verified freeze 的完整 raw body与 exact
state→ceiling table。

`PortableEnvelopeRootV1` 是 generic output 与 V3-M0 checkpoint 的共同 tagged root。两层都
递归携带 stage freeze、run permit 或 verifier 所需 exact bytes/body；V3-M0 specialization 再携带
full Parent-v3 manifest、full run outcome 和四个 ordered artifact refs。unsigned statement 在签名前
单独自哈希，两把 stage reviewer keys 对相同 statement 签名。

所有 B10 public API 的第一参数必须是 exact live
`VerifiedCampaignCheckpointTrustAnchorV1`。该 wrapper 只能由 canonical owner 从进程外
受信 trust store 装载；不存在 public issuer、raw/serialized hydration 或从 envelope 内容轮换
的路径。它递归固定 family/epoch、已信 checkpoint/genesis、previous portable root、campaign
reviewer registry/key source 与 Parent old-S key/literal source。envelope 内嵌的新双钥在与这些 pin
比对之前不是 trust root；caller 即使用自带新双钥重签整条 body，也必须因
`TRUST_ANCHOR_INVALID` 或 `UNTRUSTED_REVIEWER_KEY` 死亡。

portable verifier 明确同时支持 live 与 frozen stage/permit/Parent 输入。detached 路径必须携带
taskbook/manifest bytes、ordered `(source ref, raw bytes)` source bundle、campaign reviewer-key/P/S
source bytes，以及 Parent-v3 old-S signed-source bundle、reviewer-key source bytes 和 signing-literal
source bytes。该路径不得依赖当前 repository、Git HEAD、process registry 或 imported trust literal。

portable verification 对同一 immutable envelope 是幂等的，故不存在序列化
`REPLAYED_ENVELOPE` failure。防止一个 old envelope 被第二次消费，是 next-stage issuer 对其
signed fixed previous-root 的状态约束；不是 portable verifier 的 process-local truth。
HALT state 的 next ceiling 一律 `STOP`；READY literal 只映射 ceiling `V3-M1`，既不等于
科学 PASS，也未被 B0 签发。

## 7. 机器可读合同登记表

<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->
```json
{
  "registry_schema_version": "v3m0.parent-v3-downstream-contract-registry.v6",
  "document_authority": "DESIGN_ONLY_NO_AUTHORITY",
  "production_status": "EXPECTED-MISSING_AT_B0_FREEZE",
  "issued_statuses": [],
  "threshold_values": {},
  "threshold_policy": "REFERENCE_EXISTING_FROZEN_VALUES_ONLY",
  "branch_literals": [
    "actual",
    "matched_ablated"
  ],
  "wire_type_grammar": {
    "containers": [
      "Optional[T]",
      "tuple[T,...]",
      "tuple[T1,...,Tn]",
      "canonical-json-object"
    ],
    "integer_policy": "exact int; bool is rejected",
    "float_policy": "finite IEEE-754 binary64; signed-zero rules come from the canonical owner",
    "hash_policy": "sha256 is 64 lowercase hex; git-sha1 is 40 lowercase hex",
    "body_policy": "every nested_record resolves to a complete record_catalog body; raw body is never a capability"
  },
  "enum_catalog": {
    "DynamicsCertificationFailure": [
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
    "EndpointReferenceFailure": [
      "phase_band_empty",
      "phase_band_nonunique",
      "rank_mismatch",
      "participation_failed",
      "runner_up_margin_failed",
      "projector_invalid"
    ],
    "EndpointShellFailure": [
      "phase_band_empty",
      "phase_separation_failed",
      "gap_failed",
      "participation_failed",
      "reference_ambiguous",
      "runner_up_margin",
      "loop_inconsistent",
      "projector_invalid"
    ],
    "PairedResponseFailure": [
      "qualification_invalid",
      "input_binding_invalid",
      "actual_response_failed",
      "ablated_response_failed",
      "actual_bridge_failed",
      "ablated_bridge_failed"
    ],
    "ClosedEvidenceFailureV3": [
      "upstream_invalid",
      "cross_parent_root",
      "cross_branch",
      "chain_replay_failed",
      "paired_response_not_success",
      "claim_ceiling_violation"
    ],
    "V3M0State": [
      "HALT-V3M0-FORMAL",
      "HALT-V3M0-CONTROL",
      "HALT-V3M0-IDENTIFIABILITY",
      "HALT-V3M0-WINDOW",
      "READY-V3-M1-ANCHOR-CERTIFICATION"
    ]
  },
  "record_catalog": {
    "BlockStatus": {
      "schema_id": "v3m0.block-status.wire.v1",
      "canonical_owner": "rulespace_v3.contracts",
      "field_specs": [
        {
          "name": "defined",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reason",
          "wire_type": "Optional[UndefinedReason]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "null iff defined is true"
          ]
        }
      ],
      "record_invariants": [
        "defined is true iff reason is null"
      ]
    },
    "FrozenComplexTensor": {
      "schema_id": "v3m0.frozen-complex-tensor.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "tensor_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.frozen-complex-tensor.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "rank >= 1"
          },
          "nested_record": null,
          "constraints": [
            "positive dimensions"
          ]
        },
        {
          "name": "values_wire",
          "wire_type": "tuple[tuple[float,float],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "product(shape)"
          },
          "nested_record": null,
          "constraints": [
            "C-order complex wire"
          ]
        },
        {
          "name": "tensor_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "tensor_sha covers schema, shape, and complete values_wire"
      ]
    },
    "BasisManifest": {
      "schema_id": "v3m0.basis-manifest.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "basis_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.basis-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "role",
          "wire_type": "Literal[source,holdout_source,readout]",
          "presence": "required",
          "literal_domain": [
            "source",
            "holdout_source",
            "readout"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state channel count"
          },
          "nested_record": null,
          "constraints": [
            "unique ordered channel IDs"
          ]
        },
        {
          "name": "vectors_wire",
          "wire_type": "tuple[tuple[tuple[float,float],...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "basis vector count"
          },
          "nested_record": null,
          "constraints": [
            "rectangular complex wire"
          ]
        },
        {
          "name": "manifest_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "vectors_wire width equals len(channel_order)"
      ]
    },
    "DirectionPathClosure": {
      "schema_id": "v3m0.direction-path-closure.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "closure_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "first_path_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "first_path_position",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "second_path_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "second_path_position",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "both path IDs exist in the containing DirectionManifest"
      ]
    },
    "DirectionManifest": {
      "schema_id": "v3m0.direction-manifest.v1",
      "canonical_owner": "rulespace_v3.grids",
      "field_specs": [
        {
          "name": "direction_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.direction-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "direction_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "direction count"
          },
          "nested_record": null,
          "constraints": [
            "unique"
          ]
        },
        {
          "name": "primitive_directions",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(direction_ids)"
          },
          "nested_record": null,
          "constraints": [
            "primitive integer directions"
          ]
        },
        {
          "name": "path_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "path count"
          },
          "nested_record": null,
          "constraints": [
            "unique"
          ]
        },
        {
          "name": "ordered_paths",
          "wire_type": "tuple[tuple[tuple[int,...],...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(path_ids)"
          },
          "nested_record": null,
          "constraints": [
            "each path nonempty"
          ]
        },
        {
          "name": "closure_path_pairs",
          "wire_type": "tuple[DirectionPathClosure,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "0..declared closure count"
          },
          "nested_record": "DirectionPathClosure",
          "constraints": []
        },
        {
          "name": "direction_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "direction_ids and primitive_directions align",
        "path_ids and ordered_paths align"
      ]
    },
    "ResponseKGridManifest": {
      "schema_id": "v3m0.response-k-grid.v1",
      "canonical_owner": "rulespace_v3.grids",
      "field_specs": [
        {
          "name": "grid_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-k-grid.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "qualification_profile",
          "wire_type": "Literal[directional-momentum-shell-path-v1]",
          "presence": "required",
          "literal_domain": [
            "directional-momentum-shell-path-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_ndim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "positive"
          ]
        },
        {
          "name": "torus_denominators",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": [
            "positive"
          ]
        },
        {
          "name": "reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "response point count"
          },
          "nested_record": null,
          "constraints": [
            "each index has spatial_ndim coordinates"
          ]
        },
        {
          "name": "direction_manifest",
          "wire_type": "DirectionManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DirectionManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_grid_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "direction manifest points and reciprocal indices are recursively consistent"
      ]
    },
    "DynamicsKGridDerivationProtocolV1": {
      "schema_id": "v3m0.dynamics-k-grid-derivation-protocol.v1",
      "canonical_owner": "rulespace_v3.c19_refreeze_v2",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.dynamics-k-grid-derivation-protocol.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "branch_roles",
          "wire_type": "tuple[Literal[actual,matched_ablated],...]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "transition_support_source",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "metric_support_source",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "derivation_algorithm",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "exact_zero_qualification_profile",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "nonzero_fallback_profile",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "caller_supplied_points_allowed",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fail_closed_condition_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "frozen condition count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "branch_roles equals (actual, matched_ablated) in that order"
      ]
    },
    "BridgeKGridDerivationProtocolV1": {
      "schema_id": "v3m0.bridge-k-grid-derivation-protocol.v1",
      "canonical_owner": "rulespace_v3.c19_refreeze_v2",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.bridge-k-grid-derivation-protocol.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "branch_roles",
          "wire_type": "tuple[Literal[actual,matched_ablated],...]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "C19 exact (8,)"
          ]
        },
        {
          "name": "support_source",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "derivation_algorithm",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_steps",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "frozen step count"
          },
          "nested_record": null,
          "constraints": [
            "contains a value > 1"
          ]
        },
        {
          "name": "caller_supplied_points_allowed",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fail_closed_condition_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "frozen condition count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "branch_roles equals (actual, matched_ablated) in that order"
      ]
    },
    "MetricSupportDerivationProtocolV1": {
      "schema_id": "v3m0.metric-support-derivation-protocol.v1",
      "canonical_owner": "rulespace_v3.parent_v3_contracts",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.metric-support-derivation-protocol.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "metric_kind",
          "wire_type": "Literal[constant-state-v1]",
          "presence": "required",
          "literal_domain": [
            "constant-state-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-real-canonical-state.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "20"
          },
          "nested_record": null,
          "constraints": [
            "exact C19 q0,p0,...,q9,p9 order"
          ]
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "exact (8,)"
          ]
        },
        {
          "name": "spatial_ndim",
          "wire_type": "Literal[1]",
          "presence": "required",
          "literal_domain": [
            1
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_metric",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact I20"
          ]
        },
        {
          "name": "normalization_id",
          "wire_type": "Literal[trace-at-zero-equals-state-dim-v1]",
          "presence": "required",
          "literal_domain": [
            "trace-at-zero-equals-state-dim-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "support_derivation_id",
          "wire_type": "Literal[constant-kernel-origin-only-v1]",
          "presence": "required",
          "literal_domain": [
            "constant-kernel-origin-only-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "metric_support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "exact ((0,),)"
          ]
        },
        {
          "name": "metric_support_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "caller_supplied_support_allowed",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "state_metric is bit-exact I20",
        "support is exactly the one-dimensional origin"
      ]
    },
    "C19BasisContractV2": {
      "schema_id": "v3m0.c19-basis-contract.v2",
      "canonical_owner": "rulespace_v3.c19_refreeze_v2",
      "field_specs": [
        {
          "name": "basis_contract_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-basis-contract.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-real-canonical-state.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "20"
          },
          "nested_record": null,
          "constraints": [
            "q0,p0,...,q9,p9"
          ]
        },
        {
          "name": "common_source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "common_readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "common_source_tensor",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "common_readout_tensor",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_selector_b_plus",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact B_plus"
          ]
        },
        {
          "name": "readout_selector_p",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact P"
          ]
        },
        {
          "name": "source_injection",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact I20.T @ B_plus"
          ]
        },
        {
          "name": "readout_coisometry",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact P @ conj(I20)"
          ]
        },
        {
          "name": "scenario_source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "scenario_readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_trial_vectors",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact I10"
          ]
        },
        {
          "name": "expected_actual_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_matched_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "basis_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "common source/readout are exact I20",
        "selectors and trials are B_plus/P/I20/I10, never SHA-only"
      ]
    },
    "ConstructionTrace": {
      "schema_id": "v3m0.construction-trace.v1",
      "canonical_owner": "rulespace_v3.trace",
      "field_specs": [
        {
          "name": "schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.construction-trace.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "grammar_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_spec_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "provenance_nodes",
          "wire_type": "tuple[ProvenanceNode,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "trace provenance count"
          },
          "nested_record": "ProvenanceNode",
          "constraints": [
            "full recursive raw bodies"
          ]
        },
        {
          "name": "coefficient_records",
          "wire_type": "tuple[CoefficientRecord,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "coefficient record count"
          },
          "nested_record": "CoefficientRecord",
          "constraints": [
            "full recursive raw bodies"
          ]
        },
        {
          "name": "primitives",
          "wire_type": "tuple[PrimitiveTrace,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "primitive trace count"
          },
          "nested_record": "PrimitiveTrace",
          "constraints": [
            "full recursive raw bodies"
          ]
        },
        {
          "name": "trace_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all three nested trace tables are complete bodies, not roots"
      ]
    },
    "PrimitiveInterface": {
      "schema_id": "v3m0.primitive-interface.wire.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "interface_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_ndim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state channel count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dtype",
          "wire_type": "Literal[complex128]",
          "presence": "required",
          "literal_domain": [
            "complex128"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "backend",
          "wire_type": "Literal[numpy]",
          "presence": "required",
          "literal_domain": [
            "numpy"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "channel_order is unique"
      ]
    },
    "Primitive": {
      "schema_id": "v3m0.local-linear-primitive.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "primitive_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.local-linear-primitive.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "mechanism_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "production_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "layer_slot_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operation_id",
          "wire_type": "Literal[local_canonical_shear,neutral_identity]",
          "presence": "required",
          "literal_domain": [
            "local_canonical_shear",
            "neutral_identity"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "interface_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_channel",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "destination_channel",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "offset",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficient_wire",
          "wire_type": "tuple[float,float]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficient_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "neutral_identity_id",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "non-null iff operation_id is neutral_identity"
          ]
        }
      ],
      "record_invariants": [
        "neutral_identity_id presence is an XOR with active shear"
      ]
    },
    "LinearRealspaceFactory": {
      "schema_id": "v3m0.linear-realspace-factory.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "factory_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.linear-realspace-factory.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "factory_role",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "factory_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "construction_trace_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "grammar_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_spec_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "runtime_operator_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "interface",
          "wire_type": "PrimitiveInterface",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PrimitiveInterface",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_ndim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state channel count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state rank"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dtype",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "complex128"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "backend",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "numpy"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dt",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_blind_parameters",
          "wire_type": "tuple[tuple[str,float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "frozen parameter count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "layer_slot_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "slot count"
          },
          "nested_record": null,
          "constraints": [
            "unique ordered slots"
          ]
        },
        {
          "name": "source_manifest_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "boundary_manifest_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "periodic-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "run_length",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "primitives",
          "wire_type": "tuple[Primitive,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "primitive count"
          },
          "nested_record": "Primitive",
          "constraints": []
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "len(layer_slot_ids) equals len(primitives)",
        "C19 each branch has 50 slots and 50 primitives"
      ]
    },
    "AblationReplacement": {
      "schema_id": "v3m0.ablation-replacement.wire.v1",
      "canonical_owner": "rulespace_v3.ablation",
      "field_specs": [
        {
          "name": "layer_slot_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "mechanism_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_primitive_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "neutral_identity_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "ablated_primitive_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "replacement is in-place at one existing layer slot"
      ]
    },
    "AblationManifest": {
      "schema_id": "v3m0.ablation-manifest.v1",
      "canonical_owner": "rulespace_v3.ablation",
      "field_specs": [
        {
          "name": "manifest_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.ablation-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "construction_trace_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "ablated_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "replacements",
          "wire_type": "tuple[AblationReplacement,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "replacement count"
          },
          "nested_record": "AblationReplacement",
          "constraints": []
        },
        {
          "name": "manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "C19 has exactly 20 neutral-identity replacements"
      ]
    },
    "AblationPairSnapshot": {
      "schema_id": "v3m0.ablation-pair-snapshot.v1",
      "canonical_owner": "rulespace_v3.pair_snapshot",
      "field_specs": [
        {
          "name": "snapshot_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.ablation-pair-snapshot.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "construction_status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_factory",
          "wire_type": "LinearRealspaceFactory",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LinearRealspaceFactory",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablated_factory",
          "wire_type": "LinearRealspaceFactory",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LinearRealspaceFactory",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablation_manifest",
          "wire_type": "AblationManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "AblationManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablation_construction_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "snapshot_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "actual and ablated factory bodies are both complete",
        "construction status must be defined"
      ]
    },
    "C19RuntimeConstructionV2": {
      "schema_id": "v3m0.c19-runtime-construction.v2",
      "canonical_owner": "rulespace_v3.c19_refreeze_v2",
      "field_specs": [
        {
          "name": "construction_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-runtime-construction.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "state_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state rank"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "construction_trace",
          "wire_type": "ConstructionTrace",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ConstructionTrace",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "frozen_target",
          "wire_type": "FrozenSyntheticTarget",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenSyntheticTarget",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_factory",
          "wire_type": "LinearRealspaceFactory",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LinearRealspaceFactory",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_factory",
          "wire_type": "LinearRealspaceFactory",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LinearRealspaceFactory",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablation_manifest",
          "wire_type": "AblationManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "AblationManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_active_step_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_active_step_count",
          "wire_type": "Literal[30]",
          "presence": "required",
          "literal_domain": [
            30
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_primitive_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_primitive_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_slot_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_slot_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_active_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_active_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_apply_factory_step_kernel",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_apply_factory_step_kernel",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_independent_replay_kernel",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_independent_replay_kernel",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "construction_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "actual/matched kernels are independently replayed and byte-equal to executor kernels",
        "matched branch has exactly 20 neutral identities through its ablation manifest"
      ]
    },
    "C19ObserverGeometryBundleV1": {
      "schema_id": "v3m0.c19-observer-geometry-bundle.v1",
      "canonical_owner": "rulespace_v3.c19_refreeze_v2",
      "field_specs": [
        {
          "name": "geometry_bundle_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-observer-geometry-bundle.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "kind",
          "wire_type": "Literal[C19_OBSERVER_COLLAPSE_CONDITIONS]",
          "presence": "required",
          "literal_domain": [
            "C19_OBSERVER_COLLAPSE_CONDITIONS"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "claim_ceiling",
          "wire_type": "Literal[CONDITIONAL_PREREQUISITES_ONLY]",
          "presence": "required",
          "literal_domain": [
            "CONDITIONAL_PREREQUISITES_ONLY"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "evaluation_state",
          "wire_type": "Literal[NOT_EVALUATED_PRE_RESPONSE]",
          "presence": "required",
          "literal_domain": [
            "NOT_EVALUATED_PRE_RESPONSE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "conditional_prediction_state",
          "wire_type": "Literal[CONDITIONAL_ANALYTIC_IDENTITY_ONLY]",
          "presence": "required",
          "literal_domain": [
            "CONDITIONAL_ANALYTIC_IDENTITY_ONLY"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_dim",
          "wire_type": "Literal[20]",
          "presence": "required",
          "literal_domain": [
            20
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "ambient_h_dim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curvature_dim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "tt_dim",
          "wire_type": "Literal[2]",
          "presence": "required",
          "literal_domain": [
            2
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "gauge_dim",
          "wire_type": "Literal[4]",
          "presence": "required",
          "literal_domain": [
            4
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "row_dim",
          "wire_type": "Literal[4]",
          "presence": "required",
          "literal_domain": [
            4
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "omega_j20",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_b_plus",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_p",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "tt_basis",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "gauge_basis",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "row_basis",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "incidence_q",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ker_c_projector",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_frame",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "conditional_principal_sine_squared",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "conditional_principal_spectrum",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "conditional spectrum count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_metric",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "exact I20"
          ]
        },
        {
          "name": "state_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_metric",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "h_metric",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "h_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_metric",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operation_dag_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_active_step_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_active_step_count",
          "wire_type": "Literal[30]",
          "presence": "required",
          "literal_domain": [
            30
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_slot_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_slot_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_active_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_active_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "common_source_i20_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "common_readout_i20_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_b_plus_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "readout_p_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "response_grid_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "dynamics_derivation_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "bridge_derivation_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "geometry_bundle_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "this body contains no measured residual, triggered flag, PASS, or live dynamics/bridge artifact",
        "pre-response evaluation state is immutable"
      ]
    },
    "CurrentScenarioResponseContractV3": {
      "schema_id": "v3m0.current-scenario-response-contract.v3",
      "canonical_owner": "rulespace_v3.parent_v3_contracts",
      "field_specs": [
        {
          "name": "response_contract_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.current-scenario-response-contract.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "contract_state",
          "wire_type": "Literal[PROVISIONAL_NOT_ISSUED]",
          "presence": "required",
          "literal_domain": [
            "PROVISIONAL_NOT_ISSUED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "basis_contract",
          "wire_type": "C19BasisContractV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "C19BasisContractV2",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "dynamics_grid_derivation",
          "wire_type": "DynamicsKGridDerivationProtocolV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsKGridDerivationProtocolV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "metric_support_derivation",
          "wire_type": "MetricSupportDerivationProtocolV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MetricSupportDerivationProtocolV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_grid",
          "wire_type": "ResponseKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_reference_reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_grid_derivation",
          "wire_type": "BridgeKGridDerivationProtocolV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeKGridDerivationProtocolV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "geometry_bundle",
          "wire_type": "C19ObserverGeometryBundleV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "C19ObserverGeometryBundleV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "runtime_construction_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "operation_dag_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "expected_actual_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_matched_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "runtime_artifact_state",
          "wire_type": "Literal[DYNAMICS_AND_BRIDGE_NOT_DERIVED_PRE_RESPONSE]",
          "presence": "required",
          "literal_domain": [
            "DYNAMICS_AND_BRIDGE_NOT_DERIVED_PRE_RESPONSE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "measurement_state",
          "wire_type": "Literal[NOT_EVALUATED_PRE_RESPONSE]",
          "presence": "required",
          "literal_domain": [
            "NOT_EVALUATED_PRE_RESPONSE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "uses_global_fft_projection",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "uses_per_k_time_step_projector",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "contains no live DynamicsKGridManifest or BridgeKGridManifest",
        "basis/grid/geometry bodies are complete and recursive"
      ]
    },
    "CurrentScenarioAuthorityV3": {
      "schema_id": "v3m0.current-scenario-authority.v3",
      "canonical_owner": "rulespace_v3.parent_v3_contracts",
      "field_specs": [
        {
          "name": "scenario_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.current-scenario-authority.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_state",
          "wire_type": "Literal[PROVISIONAL_NOT_ISSUED]",
          "presence": "required",
          "literal_domain": [
            "PROVISIONAL_NOT_ISSUED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_disposition",
          "wire_type": "Literal[C19_REFREEZE_V2_REVIEWED]",
          "presence": "required",
          "literal_domain": [
            "C19_REFREEZE_V2_REVIEWED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_candidate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_runtime_construction_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_basis_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "response_contract",
          "wire_type": "CurrentScenarioResponseContractV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioResponseContractV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "scenario_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all IDs equal the nested response contract IDs"
      ]
    },
    "CurrentApplicationAuthorityV3": {
      "schema_id": "v3m0.current-application-authority.v3",
      "canonical_owner": "rulespace_v3.parent_v3_contracts",
      "field_specs": [
        {
          "name": "application_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.current-application-authority.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_state",
          "wire_type": "Literal[PROVISIONAL_NOT_ISSUED]",
          "presence": "required",
          "literal_domain": [
            "PROVISIONAL_NOT_ISSUED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "claim_ceiling",
          "wire_type": "Literal[OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY]",
          "presence": "required",
          "literal_domain": [
            "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "causal_contrast_role",
          "wire_type": "Literal[NULL_INTERVENTION_INVARIANCE_CONTROL]",
          "presence": "required",
          "literal_domain": [
            "NULL_INTERVENTION_INVARIANCE_CONTROL"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "physical_anchor_eligibility",
          "wire_type": "Literal[INELIGIBLE]",
          "presence": "required",
          "literal_domain": [
            "INELIGIBLE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "family_eligibility",
          "wire_type": "Literal[INELIGIBLE]",
          "presence": "required",
          "literal_domain": [
            "INELIGIBLE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "C19_FULL_POSITIVE_OBSERVER_COLLAPSE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_disposition",
          "wire_type": "Literal[C19_REFREEZE_V2_REVIEWED]",
          "presence": "required",
          "literal_domain": [
            "C19_REFREEZE_V2_REVIEWED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_candidate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "design_source_path",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "design_source_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "design_freeze_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-real-canonical-state.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "20"
          },
          "nested_record": null,
          "constraints": [
            "q0,p0,...,q9,p9"
          ]
        },
        {
          "name": "state_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state rank"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "exact (8,)"
          ]
        },
        {
          "name": "spatial_ndim",
          "wire_type": "Literal[1]",
          "presence": "required",
          "literal_domain": [
            1
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "common_source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "common_readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "common_source_tensor",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "common_readout_tensor",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "runtime_construction",
          "wire_type": "C19RuntimeConstructionV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "C19RuntimeConstructionV2",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "runtime_construction_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "basis_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "grid_protocol_root_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "operation_registry",
          "wire_type": "tuple[tuple[Literal[actual,matched_ablated],int,str,Primitive],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "100"
          },
          "nested_record": "Primitive",
          "constraints": [
            "50 rows per branch in canonical branch/ordinal order"
          ]
        },
        {
          "name": "operation_registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "construction_dependency_closure_state",
          "wire_type": "Literal[PROVISIONAL_CONSTRUCTION_DEPENDENCIES_NOT_SIGNED]",
          "presence": "required",
          "literal_domain": [
            "PROVISIONAL_CONSTRUCTION_DEPENDENCIES_NOT_SIGNED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "construction_dependency_closure",
          "wire_type": "tuple[tuple[str,sha256],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "complete P-blob construction closure"
          },
          "nested_record": null,
          "constraints": [
            "UTF-8 path order"
          ]
        },
        {
          "name": "construction_dependency_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_active_step_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_active_step_count",
          "wire_type": "Literal[30]",
          "presence": "required",
          "literal_domain": [
            30
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_primitive_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_primitive_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_neutral_identity_count",
          "wire_type": "Literal[20]",
          "presence": "required",
          "literal_domain": [
            20
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operation_dag_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "target_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "ablation_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_slot_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_slot_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_active_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_active_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "scenario_authorities",
          "wire_type": "tuple[CurrentScenarioAuthorityV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": "CurrentScenarioAuthorityV3",
          "constraints": []
        },
        {
          "name": "application_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "C19 is control-only/null-intervention and ineligible for physical/family claims",
        "all 50/30/50/50/50/50/20 counts are literal wire invariants"
      ]
    },
    "ControlRegistryEntry": {
      "schema_id": "v3m0.control-registry-entry.v1",
      "canonical_owner": "rulespace_v3.registry",
      "field_specs": [
        {
          "name": "entry_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.control-registry-entry.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_id",
          "wire_type": "Literal[full,zero,direct_sum]",
          "presence": "required",
          "literal_domain": [
            "full",
            "zero",
            "direct_sum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "builder_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_calibration_spec",
          "wire_type": "ControlReadoutCalibrationSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ControlReadoutCalibrationSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "mode_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_h_actual_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_h_ablated_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_curv_actual_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_curv_ablated_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "control_id uniquely identifies one closed registry entry"
      ]
    },
    "ClosedControlRegistry": {
      "schema_id": "v3m0.closed-control-registry.v1",
      "canonical_owner": "rulespace_v3.registry",
      "field_specs": [
        {
          "name": "registry_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.closed-control-registry.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "entries",
          "wire_type": "tuple[ControlRegistryEntry,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": "ControlRegistryEntry",
          "constraints": [
            "order full, zero, direct_sum"
          ]
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "contains exactly the C01/C02/C03 calibration controls"
      ]
    },
    "WindowCalibrationProtocol": {
      "schema_id": "v3m0.window-calibration-protocol.v1",
      "canonical_owner": "rulespace_v3.window",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.window-calibration-protocol.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "t_candidates",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "frozen Fejer candidate count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_entries",
          "wire_type": "tuple[ControlWindowProtocolEntry,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": "ControlWindowProtocolEntry",
          "constraints": [
            "full recursive raw bodies in control registry order"
          ]
        },
        {
          "name": "phase_grid_protocol_id",
          "wire_type": "Literal[two-pi-over-16T-v1]",
          "presence": "required",
          "literal_domain": [
            "two-pi-over-16T-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "phase_separation_protocol_id",
          "wire_type": "Literal[eight-pi-over-T-v1]",
          "presence": "required",
          "literal_domain": [
            "eight-pi-over-T-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "participation_min_required",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact upstream frozen value"
          ]
        },
        {
          "name": "overlap_margin_required",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact upstream frozen value"
          ]
        },
        {
          "name": "loop_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact upstream frozen value"
          ]
        },
        {
          "name": "projector_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact upstream frozen value"
          ]
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "B0 introduces no threshold value"
      ]
    },
    "SelectedControlEvidenceRef": {
      "schema_id": "v3m0.selected-control-evidence-ref.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "control_id",
          "wire_type": "Literal[full,zero,direct_sum]",
          "presence": "required",
          "literal_domain": [
            "full",
            "zero",
            "direct_sum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "expected_rank_declaration_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "run_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "paired_response_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "shell_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "comparison_2t_run_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "comparison_2t_response_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "comparison_2t_shell_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "T and 2T evidence are both present"
      ]
    },
    "WindowCandidateAudit": {
      "schema_id": "v3m0.window-candidate-audit.wire.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_audits",
          "wire_type": "tuple[ControlCandidateAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": "ControlCandidateAudit",
          "constraints": [
            "full recursive bodies in registry order"
          ]
        },
        {
          "name": "readout_aggregate_audits",
          "wire_type": "tuple[ReadoutAggregateCalibrationAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "readout aggregate count"
          },
          "nested_record": "ReadoutAggregateCalibrationAudit",
          "constraints": [
            "full recursive h/curv bodies"
          ]
        },
        {
          "name": "passed",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "passed is recomputed from all three control audits"
      ]
    },
    "WindowThresholdSelection": {
      "schema_id": "v3m0.window-threshold-selection.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "selected_fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "h_scale_ref",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "h_noise_ref",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "h_signal_min",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "h_tau_sig",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curv_scale_ref",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curv_noise_ref",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curv_signal_min",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curv_tau_sig",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "selected_evidence_refs",
          "wire_type": "tuple[SelectedControlEvidenceRef,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": "SelectedControlEvidenceRef",
          "constraints": []
        },
        {
          "name": "selection_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all scalar thresholds are replayed observations/derivations, never caller input"
      ]
    },
    "WindowThresholdCalibrationManifest": {
      "schema_id": "v3m0.window-threshold-calibration-manifest.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "calibration_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.window-threshold-calibration-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_registry",
          "wire_type": "ClosedControlRegistry",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ClosedControlRegistry",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "window_protocol",
          "wire_type": "WindowCalibrationProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "WindowCalibrationProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "candidate_audits",
          "wire_type": "tuple[WindowCandidateAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "len(window_protocol.t_candidates)"
          },
          "nested_record": "WindowCandidateAudit",
          "constraints": []
        },
        {
          "name": "calibration_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "candidate audit order equals window_protocol.t_candidates"
      ]
    },
    "WindowCalibrationOutcome": {
      "schema_id": "v3m0.window-calibration-outcome.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "manifest",
          "wire_type": "WindowThresholdCalibrationManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "WindowThresholdCalibrationManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "selection",
          "wire_type": "Optional[WindowThresholdSelection]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "WindowThresholdSelection",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff status.defined and selection is non-null",
        "failure iff not status.defined and selection is null"
      ]
    },
    "ScenarioBasisSelectorSpec": {
      "schema_id": "v3m0.scenario-basis-selector.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "selector_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.scenario-basis-selector.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "public_source_basis_manifest_id",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "public_readout_basis_manifest_id",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_selector_derivation_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "readout_selector_derivation_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_selector",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_selector",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_injection",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_coisometry",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "selector_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "exact wire is rulespace_v3.parent_freeze.scenario_basis_selector_spec_payload plus selector_sha",
        "selector_sha equals canonical_sha of the exact owner payload without the self hash",
        "all four tensor fields are exact FrozenComplexTensor bodies"
      ]
    },
    "CurrentScenarioResponseContractV2": {
      "schema_id": "v3m0.current-scenario-response-contract.v2",
      "canonical_owner": "rulespace_v3.parent_v2_contracts",
      "field_specs": [
        {
          "name": "response_contract_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.current-scenario-response-contract.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "contract_state",
          "wire_type": "Literal[CURRENT_REVIEWED_RESPONSE_CONTRACT]",
          "presence": "required",
          "literal_domain": [
            "CURRENT_REVIEWED_RESPONSE_CONTRACT"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "selector_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256",
            "equals selector_spec.selector_sha"
          ]
        },
        {
          "name": "selector_spec",
          "wire_type": "ScenarioBasisSelectorSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ScenarioBasisSelectorSpec",
          "constraints": [
            "full recursive exact owner body"
          ]
        },
        {
          "name": "source_trial_vectors",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "shape equals selected source-column square"
          ]
        },
        {
          "name": "response_torus_denominators",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "response spatial dimension"
          },
          "nested_record": null,
          "constraints": [
            "positive exact ints"
          ]
        },
        {
          "name": "response_reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "response grid point count"
          },
          "nested_record": null,
          "constraints": [
            "nonempty exact integer tuples"
          ]
        },
        {
          "name": "source_readout_bridge_reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "bridge grid point count"
          },
          "nested_record": null,
          "constraints": [
            "nonempty exact integer tuples"
          ]
        },
        {
          "name": "source_readout_bridge_steps",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "bridge step count"
          },
          "nested_record": null,
          "constraints": [
            "positive exact ints"
          ]
        },
        {
          "name": "reference_reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "response spatial dimension"
          },
          "nested_record": null,
          "constraints": [
            "exact integer tuple"
          ]
        },
        {
          "name": "preregistered_phase_bands",
          "wire_type": "tuple[tuple[float,float],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "phase-band count"
          },
          "nested_record": null,
          "constraints": [
            "finite ordered fp64 pairs"
          ]
        },
        {
          "name": "operation_dag_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "compiled_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "construction_rule_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "construction_family_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_actual_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "positive exact int"
          ]
        },
        {
          "name": "expected_matched_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "nonnegative exact int"
          ]
        },
        {
          "name": "actual_step_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "positive exact int"
          ]
        },
        {
          "name": "matched_ablated_step_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "nonnegative exact int"
          ]
        },
        {
          "name": "actual_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_ablated_program_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "preflight_derivation_or_recipe_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_ablated_effect_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "response_template_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "prediction_profile_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "uses_global_fft_projection",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "uses_per_k_time_step_projector",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "exact wire is rulespace_v3.parent_v2_contracts.current_scenario_response_contract_v2_payload plus response_contract_sha",
        "response_contract_sha equals canonical_sha of the exact owner payload without the self hash",
        "selector SHA/body and all tensor/grid/rank/step constraints are replayed by the canonical owner"
      ]
    },
    "CurrentScenarioAuthorityV2": {
      "schema_id": "v3m0.current-scenario-authority.v2",
      "canonical_owner": "rulespace_v3.parent_v2_contracts",
      "field_specs": [
        {
          "name": "scenario_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.current-scenario-authority.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_state",
          "wire_type": "Literal[CURRENT_REVIEWED_SCENARIO]",
          "presence": "required",
          "literal_domain": [
            "CURRENT_REVIEWED_SCENARIO"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "based_on_application_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_execution_spec",
          "wire_type": "ApplicationScenarioExecutionSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": [
            "exact BLOCK_SUCCESS scenario body"
          ]
        },
        {
          "name": "source_disposition",
          "wire_type": "Literal[CANDIDATE_V2_REVIEWED_MODIFIED,CANDIDATE_V1_REVIEWED_UNCHANGED,PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE,PARENT_V1_C04_CLOSED_RECIPE]",
          "presence": "required",
          "literal_domain": [
            "CANDIDATE_V2_REVIEWED_MODIFIED",
            "CANDIDATE_V1_REVIEWED_UNCHANGED",
            "PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE",
            "PARENT_V1_C04_CLOSED_RECIPE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_candidate_v1_scenario_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_candidate_v2_refreeze_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "non-null iff source_disposition is CANDIDATE_V2_REVIEWED_MODIFIED"
          ]
        },
        {
          "name": "response_contract",
          "wire_type": "CurrentScenarioResponseContractV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioResponseContractV2",
          "constraints": [
            "full recursive exact owner body"
          ]
        },
        {
          "name": "scenario_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "exact wire is rulespace_v3.parent_v2_contracts.current_scenario_authority_v2_payload plus scenario_authority_sha",
        "scenario_authority_sha equals canonical_sha of the exact owner payload without the self hash",
        "scenario execution spec and response contract share the exact scenario and application roots"
      ]
    },
    "CurrentApplicationAuthorityV2": {
      "schema_id": "v3m0.current-application-authority.v2",
      "canonical_owner": "rulespace_v3.parent_v2_contracts",
      "field_specs": [
        {
          "name": "application_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.current-application-authority.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_state",
          "wire_type": "Literal[CURRENT_REVIEWED_APPLICATION]",
          "presence": "required",
          "literal_domain": [
            "CURRENT_REVIEWED_APPLICATION"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "based_on_application_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_candidate_v1_application_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "complete_scenario_execution_specs",
          "wire_type": "tuple[ApplicationScenarioExecutionSpec,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "complete application scenario count"
          },
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": [
            "unique ordered scenario IDs"
          ]
        },
        {
          "name": "scenario_authorities",
          "wire_type": "tuple[CurrentScenarioAuthorityV2,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "ordered BLOCK_SUCCESS subset"
          },
          "nested_record": "CurrentScenarioAuthorityV2",
          "constraints": [
            "exact ordered BLOCK_SUCCESS subset of complete_scenario_execution_specs"
          ]
        },
        {
          "name": "application_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "exact wire is rulespace_v3.parent_v2_contracts.current_application_authority_v2_payload plus application_authority_sha",
        "application_authority_sha equals canonical_sha of the exact owner payload without the self hash",
        "all scenario bodies are exact, ordered, unique, and bound to the same control/application/spec roots"
      ]
    },
    "ParentV3CalibrationControlReplayRefV1": {
      "schema_id": "v3m0.parent-v3-calibration-control-replay-ref.v1",
      "canonical_owner": "rulespace_v3.application_authority_v3",
      "field_specs": [
        {
          "name": "replay_ref_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.parent-v3-calibration-control-replay-ref.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "current_application_registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "parent_v1_ordinal",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact nonnegative int"
          ]
        },
        {
          "name": "authority_tag",
          "wire_type": "Literal[INHERITED_CURRENT_V2]",
          "presence": "required",
          "literal_domain": [
            "INHERITED_CURRENT_V2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "Literal[C01_BLIND_HOLDOUT_FULL,C02_CONDITIONED_ZERO,C03_EQUAL_RANK_DIRECT_SUM]",
          "presence": "required",
          "literal_domain": [
            "C01_BLIND_HOLDOUT_FULL",
            "C02_CONDITIONED_ZERO",
            "C03_EQUAL_RANK_DIRECT_SUM"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_id",
          "wire_type": "Literal[full,zero,direct_sum]",
          "presence": "required",
          "literal_domain": [
            "full",
            "zero",
            "direct_sum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_authority_v2",
          "wire_type": "CurrentApplicationAuthorityV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentApplicationAuthorityV2",
          "constraints": [
            "full exact CurrentApplicationAuthorityV2 body selected from the live Parent-v3 P-frozen inherited entry",
            "wire equals rulespace_v3.parent_v2_contracts.current_application_authority_v2_payload plus application_authority_sha"
          ]
        },
        {
          "name": "application_authority_v2_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "scenario_authority_v2",
          "wire_type": "CurrentScenarioAuthorityV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioAuthorityV2",
          "constraints": [
            "full exact CurrentScenarioAuthorityV2 body nested in application_authority_v2",
            "wire equals rulespace_v3.parent_v2_contracts.current_scenario_authority_v2_payload plus scenario_authority_sha"
          ]
        },
        {
          "name": "scenario_authority_v2_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "response_contract_v2",
          "wire_type": "CurrentScenarioResponseContractV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioResponseContractV2",
          "constraints": [
            "full exact CurrentScenarioResponseContractV2 body nested in scenario_authority_v2",
            "wire equals rulespace_v3.parent_v2_contracts.current_scenario_response_contract_v2_payload plus response_contract_sha"
          ]
        },
        {
          "name": "response_contract_v2_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "replay_ref_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "replay refs are exactly ordered as (0,C01_BLIND_HOLDOUT_FULL,full), (1,C02_CONDITIONED_ZERO,zero), (2,C03_EQUAL_RANK_DIRECT_SUM,direct_sum)",
        "every application body is the exact INHERITED_CURRENT_V2 tagged body at its Parent-v1 ordinal in the full Parent-v3 current registry",
        "each selected application exposes exactly one scenario authority and the ref repeats that exact body and its nested response contract",
        "scenario and response bodies are exact nested members of the selected application and retain all self hashes",
        "no parent_freeze_v2_sha, Parent-v2 registry/window body, or V2 opaque capability is accepted or serialized"
      ]
    },
    "WindowThresholdCalibrationV3": {
      "schema_id": "v3m0.window-threshold-calibration.v3",
      "canonical_owner": "rulespace_v3.application_authority_v3",
      "field_specs": [
        {
          "name": "calibration_v3_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.window-threshold-calibration.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "current_application_registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256",
            "equals live ParentFreezeV3Manifest.current_application_registry_sha"
          ]
        },
        {
          "name": "current_application_registry_v3",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact full current_application_registry_v3_payload from the live Parent-v3 reviewed candidate",
            "exactly 20 entries with parent_v1_ordinal, authority_tag, and full V2-or-V3 application_authority body"
          ]
        },
        {
          "name": "calibration_control_replay_refs",
          "wire_type": "tuple[ParentV3CalibrationControlReplayRefV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": "ParentV3CalibrationControlReplayRefV1",
          "constraints": [
            "exact ordered C01-C03 replay references"
          ]
        },
        {
          "name": "calibration_outcome",
          "wire_type": "WindowCalibrationOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "WindowCalibrationOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "calibration_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "calibration outcome recursively includes full manifest and optional selection",
        "current registry retains exactly 19 inherited V2 entries and one refrozen V3 C19 entry in Parent-v1 ordinal order",
        "old and replacement C19 cannot both be current; delete, reorder, duplicate, or tag/body splice invalidates calibration",
        "all controls are replayed from the same Parent-v3 P blobs",
        "historical Parent-v1 is an internal numerical witness only and must equal the live Parent-v3 nested historical_parent_v1; no Parent-v2 root or opaque wrapper is constructed"
      ]
    },
    "CalibrationApplicationPermitV3": {
      "schema_id": "v3m0.calibration-application-permit.v3",
      "canonical_owner": "rulespace_v3.application_authority_v3",
      "field_specs": [
        {
          "name": "permit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.calibration-application-permit.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "calibration",
          "wire_type": "WindowThresholdCalibrationV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "WindowThresholdCalibrationV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_application_authority",
          "wire_type": "CurrentApplicationAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentApplicationAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_scenario_authority",
          "wire_type": "CurrentScenarioAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_scenario_response_contract",
          "wire_type": "CurrentScenarioResponseContractV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioResponseContractV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "selected_fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "permit_scope_id",
          "wire_type": "Literal[v3m0-parent-v3-current-application-scenario-v1]",
          "presence": "required",
          "literal_domain": [
            "v3m0-parent-v3-current-application-scenario-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "permit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "permit exists only when calibration outcome selection is non-null",
        "all four recursive bodies share one Parent-v3 root and exact application/scenario/response IDs"
      ]
    },
    "FactoryBranchBindingV3": {
      "schema_id": "v3m0.factory-branch-binding.v3",
      "canonical_owner": "rulespace_v3.application_materialization_v3",
      "field_specs": [
        {
          "name": "binding_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.factory-branch-binding.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "permit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "materialization_input_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "branch",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "factory",
          "wire_type": "LinearRealspaceFactory",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LinearRealspaceFactory",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "construction_trace",
          "wire_type": "ConstructionTrace",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ConstructionTrace",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "layer_slot_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "50"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "support_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "active_step_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "layer_slot_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "primitive_count",
          "wire_type": "Literal[50]",
          "presence": "required",
          "literal_domain": [
            50
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "neutral_identity_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "binding_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "actual has 50 active steps and zero neutral identities",
        "matched_ablated has 30 active steps and 20 neutral identities"
      ]
    },
    "ApplicationScenarioMaterializationV3": {
      "schema_id": "v3m0.application-scenario-materialization.v3",
      "canonical_owner": "rulespace_v3.application_materialization_v3",
      "field_specs": [
        {
          "name": "materialization_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.application-scenario-materialization.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "permit",
          "wire_type": "CalibrationApplicationPermitV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CalibrationApplicationPermitV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_application_authority",
          "wire_type": "CurrentApplicationAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentApplicationAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_scenario_authority",
          "wire_type": "CurrentScenarioAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_scenario_response_contract",
          "wire_type": "CurrentScenarioResponseContractV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CurrentScenarioResponseContractV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "basis_contract",
          "wire_type": "C19BasisContractV2",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "C19BasisContractV2",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "construction_trace",
          "wire_type": "ConstructionTrace",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ConstructionTrace",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablation_pair_snapshot",
          "wire_type": "AblationPairSnapshot",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "AblationPairSnapshot",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_factory_binding",
          "wire_type": "FactoryBranchBindingV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FactoryBranchBindingV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_factory_binding",
          "wire_type": "FactoryBranchBindingV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FactoryBranchBindingV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "materialization_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "permit, current bodies, basis, trace, pair snapshot, and both full factory bodies share one root",
        "actual and matched branch bodies are atomic and cannot be materialized separately"
      ]
    },
    "MeasuredTransition": {
      "schema_id": "v3m0.measured-transition.v1",
      "canonical_owner": "rulespace_v3.dynamics",
      "field_specs": [
        {
          "name": "transition_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.measured-transition.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "prestructure_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_role",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state channel count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dt",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "boundary_manifest_id",
          "wire_type": "Literal[periodic-v1]",
          "presence": "required",
          "literal_domain": [
            "periodic-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_basis_convention_id",
          "wire_type": "Literal[channel-identity-v1]",
          "presence": "required",
          "literal_domain": [
            "channel-identity-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "kernel",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "canonical signed support count"
          },
          "nested_record": null,
          "constraints": [
            "lexicographically sorted unique signed displacements"
          ]
        },
        {
          "name": "support_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "macro_steps",
          "wire_type": "Literal[1]",
          "presence": "required",
          "literal_domain": [
            1
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "kernel shape is (n_state,n_state,*spatial_shape)",
        "each full-state channel impulse is rerun; no caller projector"
      ]
    },
    "TransitionAuthorityV3": {
      "schema_id": "v3m0.transition-authority.v3",
      "canonical_owner": "rulespace_v3.transition_authority_v3",
      "field_specs": [
        {
          "name": "transition_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.transition-authority.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "materialization",
          "wire_type": "ApplicationScenarioMaterializationV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioMaterializationV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "factory_binding",
          "wire_type": "FactoryBranchBindingV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FactoryBranchBindingV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "measured_transition",
          "wire_type": "MeasuredTransition",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MeasuredTransition",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "transition_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "factory binding branch/factory/root equals measured transition branch/factory/root"
      ]
    },
    "MetricSignedSupportAttestationV1": {
      "schema_id": "v3m0.metric-signed-support-attestation.v1",
      "canonical_owner": "rulespace_v3.metric_support_authority_v1",
      "field_specs": [
        {
          "name": "attestation_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.metric-signed-support-attestation.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "current_application_authority_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "current_scenario_authority_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "response_contract_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "metric_support_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "application_scenario_materialization_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_role",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "20"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "exact (8,)"
          ]
        },
        {
          "name": "metric_kind",
          "wire_type": "Literal[constant-state-v1]",
          "presence": "required",
          "literal_domain": [
            "constant-state-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "metric_support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "exact ((0,),)"
          ]
        },
        {
          "name": "metric_support_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "attestation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "issuer accepts no support, grid, metric body, or caller SHA",
        "all lineage roots are replayed from Parent-v3 and the materialization"
      ]
    },
    "DynamicsKGridManifest": {
      "schema_id": "v3m0.dynamics-k-grid.v1",
      "canonical_owner": "rulespace_v3.grids",
      "field_specs": [
        {
          "name": "grid_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.dynamics-k-grid.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "qualification_profile",
          "wire_type": "Literal[exact-offset-zero-v1,cartesian-full-64-v1]",
          "presence": "required",
          "literal_domain": [
            "exact-offset-zero-v1",
            "cartesian-full-64-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_ndim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "torus_denominators",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "1 or 64^spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dynamics_grid_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "zero support iff denominators are all 1 and origin is the sole point",
        "nonzero support iff full lexicographic 64^d grid"
      ]
    },
    "BridgeKGridManifest": {
      "schema_id": "v3m0.bridge-k-grid.v1",
      "canonical_owner": "rulespace_v3.grids",
      "field_specs": [
        {
          "name": "grid_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.bridge-k-grid.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "torus_denominators",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_shape"
          },
          "nested_record": null,
          "constraints": [
            "componentwise equal to spatial_shape"
          ]
        },
        {
          "name": "reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "derived bridge point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_grid_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "zero support yields origin only but retains realspace denominators"
      ]
    },
    "BridgeGridAuthorityV3": {
      "schema_id": "v3m0.bridge-grid-authority.v3",
      "canonical_owner": "rulespace_v3.runtime_grids_v3",
      "field_specs": [
        {
          "name": "grid_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.bridge-grid-authority.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "materialization",
          "wire_type": "ApplicationScenarioMaterializationV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioMaterializationV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "factory_binding",
          "wire_type": "FactoryBranchBindingV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FactoryBranchBindingV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "derivation_protocol",
          "wire_type": "BridgeKGridDerivationProtocolV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeKGridDerivationProtocolV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "bridge_grid",
          "wire_type": "BridgeKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "grid_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "grid is mechanically derived from the full live factory support; caller points forbidden"
      ]
    },
    "DynamicsGridAuthorityV3": {
      "schema_id": "v3m0.dynamics-grid-authority.v3",
      "canonical_owner": "rulespace_v3.runtime_grids_v3",
      "field_specs": [
        {
          "name": "grid_authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.dynamics-grid-authority.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "transition_authority",
          "wire_type": "TransitionAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "TransitionAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "metric_support_attestation",
          "wire_type": "MetricSignedSupportAttestationV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MetricSignedSupportAttestationV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "derivation_protocol",
          "wire_type": "DynamicsKGridDerivationProtocolV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsKGridDerivationProtocolV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "dynamics_grid",
          "wire_type": "DynamicsKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "grid_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "transition and metric supports share root/branch/state and uniquely select singleton or full-64"
      ]
    },
    "PrestructureAuthority": {
      "schema_id": "v3m0.prestructure-authority.v1",
      "canonical_owner": "rulespace_v3.prestructure",
      "field_specs": [
        {
          "name": "authority_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.prestructure-authority.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_kind",
          "wire_type": "Literal[synthetic-registry-v1,synthetic-application-v1,adapter-preregistration-v1]",
          "presence": "required",
          "literal_domain": [
            "synthetic-registry-v1",
            "synthetic-application-v1",
            "adapter-preregistration-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "parent_freeze",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full canonical ParentFreezeManifest body; V3 outer binding separately enforces Parent-v3"
          ]
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_role",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "ablation_pair_snapshot",
          "wire_type": "AblationPairSnapshot",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "AblationPairSnapshot",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablation_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "ablation_construction_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "synthetic_registry",
          "wire_type": "Optional[ClosedControlRegistry]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ClosedControlRegistry",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "synthetic_registry_entry_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "synthetic_preregistration",
          "wire_type": "Optional[canonical-json-object]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full SyntheticStructurePreregistration body"
          ]
        },
        {
          "name": "synthetic_application_spec",
          "wire_type": "Optional[canonical-json-object]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full V3M0SyntheticControlApplicationSpec body"
          ]
        },
        {
          "name": "synthetic_application_scenario_spec",
          "wire_type": "Optional[canonical-json-object]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full ApplicationScenarioExecutionSpec body"
          ]
        },
        {
          "name": "synthetic_application_permit_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "synthetic_scenario_construction_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "adapter_preregistration",
          "wire_type": "Optional[canonical-json-object]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full AdapterStructurePreregistration body"
          ]
        },
        {
          "name": "authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "synthetic-registry, synthetic-application, and adapter body groups are mutually exclusive"
      ]
    },
    "StructureManifest": {
      "schema_id": "v3m0.structure-manifest.v1",
      "canonical_owner": "rulespace_v3.structure",
      "field_specs": [
        {
          "name": "structure_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.structure-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "evidence_lane",
          "wire_type": "Literal[synthetic-classical,classical-adapter,quantum]",
          "presence": "required",
          "literal_domain": [
            "synthetic-classical",
            "classical-adapter",
            "quantum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "structure_kind",
          "wire_type": "Literal[unitary,symplectic]",
          "presence": "required",
          "literal_domain": [
            "unitary",
            "symplectic"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state channel count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "canonical_channel_pairs",
          "wire_type": "tuple[tuple[str,str],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "0..n_state/2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fourier_adjoint_convention_id",
          "wire_type": "Literal[same-k-dagger-v1,minus-k-transpose-v1]",
          "presence": "required",
          "literal_domain": [
            "same-k-dagger-v1",
            "minus-k-transpose-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "structure_form",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "reality_convention_id",
          "wire_type": "Optional[Literal[real-kernel-positive-zero-v1]]",
          "presence": "required-nullable",
          "literal_domain": [
            "real-kernel-positive-zero-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "prestructure_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "structure_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "classical lanes use symplectic/minus-k-transpose/reality body",
        "quantum lane uses unitary/same-k-dagger/no reality body"
      ]
    },
    "RealityCertificate": {
      "schema_id": "v3m0.reality-certificate.v1",
      "canonical_owner": "rulespace_v3.structure",
      "field_specs": [
        {
          "name": "reality_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.reality-certificate.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "structure_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_coefficient_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "transition_entry_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "imaginary_bit_pattern_id",
          "wire_type": "Literal[all-positive-zero-f64-v1]",
          "presence": "required",
          "literal_domain": [
            "all-positive-zero-f64-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "implied_fourier_identity_id",
          "wire_type": "Literal[m-minus-k-equals-conj-m-k-v1]",
          "presence": "required",
          "literal_domain": [
            "m-minus-k-equals-conj-m-k-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reality_certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "every factory coefficient and transition imaginary bit is +0.0"
      ]
    },
    "MetricOriginManifest": {
      "schema_id": "v3m0.metric-origin-manifest.v1",
      "canonical_owner": "rulespace_v3.metric",
      "field_specs": [
        {
          "name": "origin_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.metric-origin-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "origin_kind",
          "wire_type": "Literal[synthetic-identity-v1,adapter-preregistered-v1]",
          "presence": "required",
          "literal_domain": [
            "synthetic-identity-v1",
            "adapter-preregistered-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "prestructure_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "structure_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "evidence_lane",
          "wire_type": "Literal[synthetic-classical,classical-adapter,quantum]",
          "presence": "required",
          "literal_domain": [
            "synthetic-classical",
            "classical-adapter",
            "quantum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "derivation_or_preregistration_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "metric_kernel_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "metric_support_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "origin_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "origin body is embedded in StabilityMetricWitness, not replaced by origin_sha"
      ]
    },
    "StabilityMetricWitness": {
      "schema_id": "v3m0.stability-metric-witness.v1",
      "canonical_owner": "rulespace_v3.metric",
      "field_specs": [
        {
          "name": "witness_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.stability-metric-witness.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "structure_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "metric_kind",
          "wire_type": "Literal[constant-state-v1,finite-support-laurent-v1]",
          "presence": "required",
          "literal_domain": [
            "constant-state-v1",
            "finite-support-laurent-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "metric_kernel",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "metric_support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "canonical symmetric support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "metric_support_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "normalization_id",
          "wire_type": "Literal[trace-at-zero-equals-state-dim-v1]",
          "presence": "required",
          "literal_domain": [
            "trace-at-zero-equals-state-dim-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "positive_eigenvalue_floor",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact existing frozen value"
          ]
        },
        {
          "name": "condition_number_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact existing frozen value"
          ]
        },
        {
          "name": "metric_origin",
          "wire_type": "MetricOriginManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MetricOriginManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "witness_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "metric origin body is recursive",
        "B0 adds no threshold"
      ]
    },
    "Fp64RootIntervalEntry": {
      "schema_id": "v3m0.fp64-root-interval-entry.wire.v1",
      "canonical_owner": "rulespace_v3.root64",
      "field_specs": [
        {
          "name": "root_index",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dyadic_exponent",
          "wire_type": "Literal[192]",
          "presence": "required",
          "literal_domain": [
            192
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "real_lower_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "real_upper_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "imag_lower_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "imag_upper_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "real_center_f64_bits",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "imag_center_f64_bits",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "center_distance_squared_upper_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "center_distance_squared_upper_power_of_two",
          "wire_type": "Literal[-384]",
          "presence": "required",
          "literal_domain": [
            -384
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "center_distance_upper_f64_bits",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "interval contains the exact root and outward center-distance upper"
      ]
    },
    "Fp64RootOfUnityIntervalTable": {
      "schema_id": "v3m0.fp64-root-of-unity-interval-table.v1",
      "canonical_owner": "rulespace_v3.root64",
      "field_specs": [
        {
          "name": "table_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.fp64-root-of-unity-interval-table.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "table_id",
          "wire_type": "Literal[root64-dyadic-machin-taylor-containment-v1]",
          "presence": "required",
          "literal_domain": [
            "root64-dyadic-machin-taylor-containment-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "denominator",
          "wire_type": "Literal[64]",
          "presence": "required",
          "literal_domain": [
            64
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dyadic_exponent",
          "wire_type": "Literal[192]",
          "presence": "required",
          "literal_domain": [
            192
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "pi_lower_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "pi_upper_numerator",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "machin_identity_id",
          "wire_type": "Literal[pi-equals-16atan1over5-minus4atan1over239-v1]",
          "presence": "required",
          "literal_domain": [
            "pi-equals-16atan1over5-minus4atan1over239-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "taylor_precision_bits",
          "wire_type": "Literal[192]",
          "presence": "required",
          "literal_domain": [
            192
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "remainder_method_id",
          "wire_type": "Literal[bigint-alternating-rational-remainder-v1]",
          "presence": "required",
          "literal_domain": [
            "bigint-alternating-rational-remainder-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "entries",
          "wire_type": "tuple[Fp64RootIntervalEntry,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "64"
          },
          "nested_record": "Fp64RootIntervalEntry",
          "constraints": []
        },
        {
          "name": "table_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "contains all 64 roots in root_index order"
      ]
    },
    "Fp64EnclosureProtocol": {
      "schema_id": "v3m0.fp64-enclosure-protocol.v1",
      "canonical_owner": "rulespace_v3.fp64_protocol",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.fp64-enclosure-protocol.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "unit_roundoff_numerator",
          "wire_type": "Literal[1]",
          "presence": "required",
          "literal_domain": [
            1
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "unit_roundoff_denominator",
          "wire_type": "Literal[9007199254740992]",
          "presence": "required",
          "literal_domain": [
            9007199254740992
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "minimum_subnormal_numerator",
          "wire_type": "Literal[1]",
          "presence": "required",
          "literal_domain": [
            1
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "minimum_subnormal_power_of_two",
          "wire_type": "Literal[-1074]",
          "presence": "required",
          "literal_domain": [
            -1074
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "gamma_bound_method_id",
          "wire_type": "Literal[integer-ratio-q-u-over-one-minus-q-u-v1]",
          "presence": "required",
          "literal_domain": [
            "integer-ratio-q-u-over-one-minus-q-u-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "complex_add_real_add_count",
          "wire_type": "Literal[2]",
          "presence": "required",
          "literal_domain": [
            2
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "complex_multiply_real_multiply_count",
          "wire_type": "Literal[4]",
          "presence": "required",
          "literal_domain": [
            4
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "complex_multiply_real_add_count",
          "wire_type": "Literal[2]",
          "presence": "required",
          "literal_domain": [
            2
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matrix_dot_operation_count_id",
          "wire_type": "Literal[complex-dot-real-component-q-equals-4n-minus-1-v1]",
          "presence": "required",
          "literal_domain": [
            "complex-dot-real-component-q-equals-4n-minus-1-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scalar_expression_dag_id",
          "wire_type": "Literal[ordered-four-real-products-and-additions-no-fma-v1]",
          "presence": "required",
          "literal_domain": [
            "ordered-four-real-products-and-additions-no-fma-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "roundoff_bound_id",
          "wire_type": "Literal[gamma-q-times-absolute-product-sum-plus-minsub-v1]",
          "presence": "required",
          "literal_domain": [
            "gamma-q-times-absolute-product-sum-plus-minsub-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "gradual_underflow_additive_id",
          "wire_type": "Literal[real-operation-count-times-minsub-v1]",
          "presence": "required",
          "literal_domain": [
            "real-operation-count-times-minsub-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "root_center_error_propagation_id",
          "wire_type": "Literal[coefficient-frobenius-sum-times-root-center-distance-v1]",
          "presence": "required",
          "literal_domain": [
            "coefficient-frobenius-sum-times-root-center-distance-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "frobenius_sqrt_containment_id",
          "wire_type": "Literal[exact-integer-ratio-square-containment-v1]",
          "presence": "required",
          "literal_domain": [
            "exact-integer-ratio-square-containment-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fma_policy",
          "wire_type": "Literal[forbidden]",
          "presence": "required",
          "literal_domain": [
            "forbidden"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reassociation_policy",
          "wire_type": "Literal[forbidden]",
          "presence": "required",
          "literal_domain": [
            "forbidden"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "finite_value_policy",
          "wire_type": "Literal[finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-overflow-v1]",
          "presence": "required",
          "literal_domain": [
            "finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-overflow-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "outward_rounding_id",
          "wire_type": "Literal[nextafter-after-every-scalar-op-v1]",
          "presence": "required",
          "literal_domain": [
            "nextafter-after-every-scalar-op-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "root_interval_table",
          "wire_type": "Fp64RootOfUnityIntervalTable",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "Fp64RootOfUnityIntervalTable",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all hard arithmetic in one certificate references this exact complete protocol"
      ]
    },
    "FullStateBridgeSpec": {
      "schema_id": "v3m0.full-state-bridge-spec.v1",
      "canonical_owner": "rulespace_v3.bridge",
      "field_specs": [
        {
          "name": "bridge_spec_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.full-state-bridge-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "prestructure_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "n_state"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_grid",
          "wire_type": "BridgeKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "macro_steps",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": null,
          "constraints": [
            "exact (1,2,4)"
          ]
        },
        {
          "name": "state_trial_vectors",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "trial_generation_id",
          "wire_type": "Literal[canonical-or-sha256-dense-v1]",
          "presence": "required",
          "literal_domain": [
            "canonical-or-sha256-dense-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "trial_seed_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "trial_domain_separator",
          "wire_type": "Literal[v3m0-full-state-bridge-trials-v1]",
          "presence": "required",
          "literal_domain": [
            "v3m0-full-state-bridge-trials-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "trial_gram_frobenius_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "trial_gram_gate_method_id",
          "wire_type": "Literal[outward-frobenius-dominates-spectral-v1]",
          "presence": "required",
          "literal_domain": [
            "outward-frobenius-dominates-spectral-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_tolerance",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact existing frozen bridge tolerance"
          ]
        },
        {
          "name": "bridge_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "trial count is min(n_state,32) and caller cannot select trials/grid/steps"
      ]
    },
    "BridgeCaseAudit": {
      "schema_id": "v3m0.bridge-case-audit.wire.v1",
      "canonical_owner": "rulespace_v3.bridge",
      "field_specs": [
        {
          "name": "reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "macro_steps",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "trial_index",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_abs_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scale",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "normalized_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "one row for every grid x steps x trials case"
      ]
    },
    "BridgeAudit": {
      "schema_id": "v3m0.full-state-bridge-audit.v1",
      "canonical_owner": "rulespace_v3.bridge",
      "field_specs": [
        {
          "name": "bridge_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.full-state-bridge-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "bridge_kind",
          "wire_type": "Literal[full-state]",
          "presence": "required",
          "literal_domain": [
            "full-state"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "bridge_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "cases",
          "wire_type": "tuple[BridgeCaseAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "complete Cartesian case count"
          },
          "nested_record": "BridgeCaseAudit",
          "constraints": []
        },
        {
          "name": "raw_abs_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "normalized_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "cases are complete grid x steps x trials Cartesian product"
      ]
    },
    "LaurentResidualCertificate": {
      "schema_id": "v3m0.laurent-residual-certificate.v1",
      "canonical_owner": "rulespace_v3.laurent",
      "field_specs": [
        {
          "name": "residual_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.laurent-residual-certificate.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "residual_kind",
          "wire_type": "Literal[canonical-structure,stability-metric]",
          "presence": "required",
          "literal_domain": [
            "canonical-structure",
            "stability-metric"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operand_shas",
          "wire_type": "tuple[sha256,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_ndim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "n_state",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fp64_enclosure_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "fourier_convention_id",
          "wire_type": "Literal[signed-displacement-exp-minus-i-k-dot-d-v1]",
          "presence": "required",
          "literal_domain": [
            "signed-displacement-exp-minus-i-k-dot-d-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matrix_norm_id",
          "wire_type": "Literal[spectral-2-v1]",
          "presence": "required",
          "literal_domain": [
            "spectral-2-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "momentum_supremum_method_id",
          "wire_type": "Literal[sum-of-directed-outward-frobenius-upper-v1]",
          "presence": "required",
          "literal_domain": [
            "sum-of-directed-outward-frobenius-upper-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "residual support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficients",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "convolution_pair_counts",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "convolution stage count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficient_roundoff_frobenius_uppers",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(support_offsets)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficient_frobenius_upper_sum",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_global_momentum_supremum_bound",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "residual_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "contains raw enclosure only; no coverage-dependent normalization or verdict"
      ]
    },
    "SpectralPointEnclosureColumnarSidecar": {
      "schema_id": "v3m0.spectral-point-sidecar.v1",
      "canonical_owner": "rulespace_v3.spectral",
      "field_specs": [
        {
          "name": "sidecar_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.spectral-point-sidecar.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "qualification_grid_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "point_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_algorithm_id",
          "wire_type": "Literal[scalar-gauss-jordan-hermitian-cholesky-v1]",
          "presence": "required",
          "literal_domain": [
            "scalar-gauss-jordan-hermitian-cholesky-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "encoding_id",
          "wire_type": "Literal[strict-base64-big-endian-f64-columns-v1]",
          "presence": "required",
          "literal_domain": [
            "strict-base64-big-endian-f64-columns-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_diagnostic_status",
          "wire_type": "Literal[available-lapack-v1,unavailable-v1]",
          "presence": "required",
          "literal_domain": [
            "available-lapack-v1",
            "unavailable-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_diagnostic_unavailable_reason",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_m_sigma_min_b64",
          "wire_type": "Optional[base64-be-f64-column]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_m_sigma_max_b64",
          "wire_type": "Optional[base64-be-f64-column]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_g_lambda_min_b64",
          "wire_type": "Optional[base64-be-f64-column]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_g_lambda_max_b64",
          "wire_type": "Optional[base64-be-f64-column]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "transition_symbol_error_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "metric_symbol_error_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "transition_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "inverse_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "inverse_residual_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "m_sigma_min_lower_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "m_sigma_max_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "metric_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "cholesky_factorization_residual_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "cholesky_inverse_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "cholesky_inverse_residual_frobenius_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "ell_lower_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "g_lambda_min_lower_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "g_lambda_max_upper_b64",
          "wire_type": "base64-be-f64-column",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "decoded length equals point_count"
          ]
        },
        {
          "name": "raw_byte_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "column_data_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "roundoff_enclosure_method_id",
          "wire_type": "Literal[fp64-operation-count-nextafter-columnar-v1]",
          "presence": "required",
          "literal_domain": [
            "fp64-operation-count-nextafter-columnar-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "sidecar_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "available has 18 aligned columns; unavailable has 14 hard columns and four null raw columns"
      ]
    },
    "SpectralMarginCoverage": {
      "schema_id": "v3m0.spectral-margin-coverage.v1",
      "canonical_owner": "rulespace_v3.spectral",
      "field_specs": [
        {
          "name": "coverage_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.spectral-margin-coverage.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "stability_metric_witness_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "fp64_enclosure_protocol",
          "wire_type": "Fp64EnclosureProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "Fp64EnclosureProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "qualification_grid",
          "wire_type": "DynamicsKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "spectral_diagnostic_grid",
          "wire_type": "DynamicsKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "torus_domain_id",
          "wire_type": "Literal[minus-pi-pi-periodic-v1]",
          "presence": "required",
          "literal_domain": [
            "minus-pi-pi-periodic-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "distance_convention_id",
          "wire_type": "Literal[principal-linf-torus-v1]",
          "presence": "required",
          "literal_domain": [
            "principal-linf-torus-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fill_distance",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_diagnostic_status",
          "wire_type": "Literal[available-lapack-v1,unavailable-v1]",
          "presence": "required",
          "literal_domain": [
            "available-lapack-v1",
            "unavailable-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_diagnostic_unavailable_reason",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_m_sigma_min",
          "wire_type": "Optional[tuple[float64,...]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_m_sigma_max",
          "wire_type": "Optional[tuple[float64,...]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_g_lambda_min",
          "wire_type": "Optional[tuple[float64,...]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_g_lambda_max",
          "wire_type": "Optional[tuple[float64,...]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "point_enclosures",
          "wire_type": "SpectralPointEnclosureColumnarSidecar",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SpectralPointEnclosureColumnarSidecar",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "grid_m_sigma_min_lower",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "grid_m_sigma_max_upper",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "grid_g_lambda_min_lower",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "grid_g_lambda_max_upper",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "qualification point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "m_sigma_min_axis_derivative_bounds",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "m_sigma_max_axis_derivative_bounds",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_lambda_min_axis_derivative_bounds",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_lambda_max_axis_derivative_bounds",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "m_sigma_min_coverage_increment",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "m_sigma_max_coverage_increment",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_lambda_min_coverage_increment",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_lambda_max_coverage_increment",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_m_sigma_min_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_m_sigma_max_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_g_lambda_min_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_g_lambda_max_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_m_condition_number_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_g_condition_number_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spectral_radius_drift_diagnostic",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coverage_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "coverage proves only four spectral extrema/conditions, never the residual gate"
      ]
    },
    "NormalizedMetricResidualAudit": {
      "schema_id": "v3m0.normalized-metric-residual-audit.v1",
      "canonical_owner": "rulespace_v3.spectral",
      "field_specs": [
        {
          "name": "audit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.normalized-metric-residual-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "metric_residual_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "spectral_margin_coverage_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "raw_metric_residual_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "covered_g_lambda_min_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "division_method_id",
          "wire_type": "Literal[fp64-nextafter-outward-division-v1]",
          "presence": "required",
          "literal_domain": [
            "fp64-nextafter-outward-division-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "normalized_metric_residual_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "normalization is computed only after positive covered metric lower bound"
      ]
    },
    "PowerDriftAudit": {
      "schema_id": "v3m0.power-drift-audit.v1",
      "canonical_owner": "rulespace_v3.spectral",
      "field_specs": [
        {
          "name": "audit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.power-drift-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "normalized_metric_residual_audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "macro_step",
          "wire_type": "Literal[16384]",
          "presence": "required",
          "literal_domain": [
            16384
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "nonzero_delta_squaring_count",
          "wire_type": "Literal[14]",
          "presence": "required",
          "literal_domain": [
            14
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "executed_squaring_count",
          "wire_type": "Literal[0,14]",
          "presence": "required",
          "literal_domain": [
            0,
            14
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "identity_branch",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "method_id",
          "wire_type": "Literal[t16384-directed-repeated-squaring-v1]",
          "presence": "required",
          "literal_domain": [
            "t16384-directed-repeated-squaring-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "delta_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "one_minus_delta_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "one_plus_delta_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "growth_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "contraction_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "drift_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "identity branch uses zero squarings; nonzero branch uses exactly fourteen"
      ]
    },
    "RuntimeEvidenceManifest": {
      "schema_id": "v3m0.runtime-evidence-manifest.v1",
      "canonical_owner": "rulespace_v3.runtime",
      "field_specs": [
        {
          "name": "runtime_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.runtime-evidence-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "evaluator_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_closure",
          "wire_type": "tuple[tuple[str,sha256],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "runtime source count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "python_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "numpy_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scipy_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "blas_config_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "lapack_config_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "platform_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "runtime_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "runtime source closure is ordered and complete"
      ]
    },
    "InstabilityGrowthCounterWitness": {
      "schema_id": "v3m0.instability-growth-counter-witness.v1",
      "canonical_owner": "rulespace_v3.instability",
      "field_specs": [
        {
          "name": "witness_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.instability-growth-counter-witness.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "witness_profile",
          "wire_type": "Literal[exact-zero-offset-jordan-2x2-v1]",
          "presence": "required",
          "literal_domain": [
            "exact-zero-offset-jordan-2x2-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "prestructure_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "transition",
          "wire_type": "MeasuredTransition",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MeasuredTransition",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "transition_matrix",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "exact ((0,),)"
          ]
        },
        {
          "name": "macro_step",
          "wire_type": "Literal[16384]",
          "presence": "required",
          "literal_domain": [
            16384
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "initial_vector",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "exact_power_formula_id",
          "wire_type": "Literal[jordan-one-one-zero-one-power-v1]",
          "presence": "required",
          "literal_domain": [
            "jordan-one-one-zero-one-power-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "initial_norm_squared",
          "wire_type": "Literal[1]",
          "presence": "required",
          "literal_domain": [
            1
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "final_norm_squared",
          "wire_type": "Literal[268435457]",
          "presence": "required",
          "literal_domain": [
            268435457
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "required_growth_squared_strict_upper",
          "wire_type": "Literal[100000001]",
          "presence": "required",
          "literal_domain": [
            100000001
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "witness_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "only exact J=[[1,1],[0,1]] profile may carry this witness"
      ]
    },
    "DynamicsCertificateV3": {
      "schema_id": "v3m0.dynamics-certificate.v3",
      "canonical_owner": "rulespace_v3.certificate_v3",
      "field_specs": [
        {
          "name": "certificate_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.dynamics-certificate.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3",
          "wire_type": "ParentFreezeV3Manifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ParentFreezeV3Manifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "materialization",
          "wire_type": "ApplicationScenarioMaterializationV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioMaterializationV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "transition_authority",
          "wire_type": "TransitionAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "TransitionAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "metric_attestation",
          "wire_type": "MetricSignedSupportAttestationV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MetricSignedSupportAttestationV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "bridge_grid_authority",
          "wire_type": "BridgeGridAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeGridAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "dynamics_grid_authority",
          "wire_type": "DynamicsGridAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsGridAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "prestructure_authority",
          "wire_type": "PrestructureAuthority",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PrestructureAuthority",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "structure",
          "wire_type": "StructureManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "StructureManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "reality",
          "wire_type": "Optional[RealityCertificate]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "RealityCertificate",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "stability_metric",
          "wire_type": "StabilityMetricWitness",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "StabilityMetricWitness",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "fp64_enclosure_protocol",
          "wire_type": "Fp64EnclosureProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "Fp64EnclosureProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "full_state_bridge_spec",
          "wire_type": "FullStateBridgeSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FullStateBridgeSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "full_state_bridge_audit",
          "wire_type": "BridgeAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "structure_residual",
          "wire_type": "LaurentResidualCertificate",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LaurentResidualCertificate",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "metric_residual",
          "wire_type": "LaurentResidualCertificate",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LaurentResidualCertificate",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "spectral_margins",
          "wire_type": "SpectralMarginCoverage",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SpectralMarginCoverage",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "normalized_metric_residual",
          "wire_type": "NormalizedMetricResidualAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "NormalizedMetricResidualAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "power_drift",
          "wire_type": "PowerDriftAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PowerDriftAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "runtime",
          "wire_type": "RuntimeEvidenceManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "RuntimeEvidenceManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all bodies are recursively embedded; no SHA-only replacement",
        "Parent, materialization, TransitionAuthorityV3, metric attestation and both grid authorities have one exact branch/root join",
        "classical/quantum reality presence follows StructureManifest lane"
      ]
    },
    "DynamicsCertificationAttemptAuditV3": {
      "schema_id": "v3m0.dynamics-certification-attempt.v3",
      "canonical_owner": "rulespace_v3.certificate_v3",
      "field_specs": [
        {
          "name": "attempt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.dynamics-certification-attempt.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "materialization_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "transition_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "metric_attestation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "bridge_grid_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "dynamics_grid_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "first_failure",
          "wire_type": "Optional[DynamicsCertificationFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reality",
          "wire_type": "Optional[RealityCertificate]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "RealityCertificate",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "structure_residual",
          "wire_type": "Optional[LaurentResidualCertificate]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LaurentResidualCertificate",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "metric_residual",
          "wire_type": "Optional[LaurentResidualCertificate]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "LaurentResidualCertificate",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "spectral_margins",
          "wire_type": "Optional[SpectralMarginCoverage]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SpectralMarginCoverage",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "normalized_metric_residual",
          "wire_type": "Optional[NormalizedMetricResidualAudit]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "NormalizedMetricResidualAudit",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "full_state_bridge_audit",
          "wire_type": "Optional[BridgeAudit]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeAudit",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "power_drift",
          "wire_type": "Optional[PowerDriftAudit]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PowerDriftAudit",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "instability_counter_witness",
          "wire_type": "Optional[InstabilityGrowthCounterWitness]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "InstabilityGrowthCounterWitness",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "attempt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "optional evidence is a prefix of the fixed first-failure pipeline",
        "six required upstream roots are copied only from their live verified authorities",
        "instability witness non-null iff first_failure is certified_instability_counterwitness"
      ]
    },
    "DynamicsCertificationOutcomeV3": {
      "schema_id": "v3m0.dynamics-certification-outcome.v3",
      "canonical_owner": "rulespace_v3.certificate_v3",
      "field_specs": [
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[DynamicsCertificationFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "attempt_audit",
          "wire_type": "DynamicsCertificationAttemptAuditV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificationAttemptAuditV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "certificate",
          "wire_type": "Optional[DynamicsCertificateV3]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificateV3",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff failure is null and certificate is non-null",
        "failure iff failure is non-null and certificate is null",
        "no unstable reason without the exact counterwitness"
      ]
    },
    "ResponseRunSpec": {
      "schema_id": "v3m0.response-run-spec.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "run_spec_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-run-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "run_spec_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "window_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "channel_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "state channel count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_grid",
          "wire_type": "ResponseKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_readout_bridge_grid",
          "wire_type": "BridgeKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_readout_bridge_steps",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "frozen source bridge step count"
          },
          "nested_record": null,
          "constraints": [
            "exact frozen WindowCalibrationProtocol value",
            "contains a value > 1"
          ]
        },
        {
          "name": "source_trial_vectors",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "full I_nsource columns; C19 exact I10; no sampling or rank reduction"
          ]
        },
        {
          "name": "bridge_tolerance",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact frozen WindowCalibrationProtocol value"
          ]
        },
        {
          "name": "spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "response and bridge grids retain distinct strict types",
        "contains source/readout trials only, never full-state bridge trials"
      ]
    },
    "EndpointReferenceSpec": {
      "schema_id": "v3m0.endpoint-reference-spec.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "reference_spec_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.endpoint-reference-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "window_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "control_registry_entry",
          "wire_type": "ControlRegistryEntry",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ControlRegistryEntry",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_dynamics_certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "candidate_fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preregistered_phase_bands",
          "wire_type": "tuple[tuple[float64,float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "phase band count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank_source_id",
          "wire_type": "Literal[parent-freeze-control-application-spec-v1]",
          "presence": "required",
          "literal_domain": [
            "parent-freeze-control-application-spec-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "reference is actual-only and expected rank comes from Parent, never observation"
      ]
    },
    "EndpointReferenceProjector": {
      "schema_id": "v3m0.endpoint-reference-projector.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "reference_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.endpoint-reference-projector.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_dynamics_certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "reference_reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_phase",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "projector_coordinate_convention_id",
          "wire_type": "Literal[g-whitened-state-v1]",
          "presence": "required",
          "literal_domain": [
            "g-whitened-state-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "projector",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "reference_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "projector is square, Hermitian/idempotent, and rank matches the Parent declaration"
      ]
    },
    "EndpointReferenceAttemptAudit": {
      "schema_id": "v3m0.endpoint-reference-attempt.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "attempt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.endpoint-reference-attempt.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "reference_spec",
          "wire_type": "EndpointReferenceSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "candidate_phases",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "candidate count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_ranks",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank_source_id",
          "wire_type": "Literal[parent-freeze-control-application-spec-v1]",
          "presence": "required",
          "literal_domain": [
            "parent-freeze-control-application-spec-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_participations",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "runner_up_overlaps",
          "wire_type": "tuple[Optional[float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "hermitian_residuals",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "idempotent_residuals",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_invariance_residuals",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "eigenphase_residuals",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "observed_competitor_gaps",
          "wire_type": "tuple[Optional[float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "attempt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all candidate columns align exactly",
        "competitor values are null iff no competitor exists"
      ]
    },
    "EndpointReferenceOutcome": {
      "schema_id": "v3m0.endpoint-reference-outcome.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[EndpointReferenceFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_spec",
          "wire_type": "EndpointReferenceSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "attempt_audit",
          "wire_type": "EndpointReferenceAttemptAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceAttemptAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "reference",
          "wire_type": "Optional[EndpointReferenceProjector]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceProjector",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff failure is null and reference is non-null",
        "failure iff failure is non-null and reference is null"
      ]
    },
    "EndpointShellSpec": {
      "schema_id": "v3m0.endpoint-shell-spec.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "shell_spec_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.endpoint-shell-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "window_protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "control_registry_entry",
          "wire_type": "ControlRegistryEntry",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ControlRegistryEntry",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_grid",
          "wire_type": "ResponseKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "preregistered_phase_bands",
          "wire_type": "tuple[tuple[float64,float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "phase band count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "endpoint_reference_projector",
          "wire_type": "EndpointReferenceProjector",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceProjector",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "extraction_protocol_id",
          "wire_type": "Literal[endpoint-single-node-reference-v1]",
          "presence": "required",
          "literal_domain": [
            "endpoint-single-node-reference-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "shell_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "shell uses the actual-only endpoint reference body"
      ]
    },
    "ShellPointAudit": {
      "schema_id": "v3m0.shell-point-audit.wire.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "momentum_path_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "momentum_path_position",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "shell_phase",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "hermitian_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "idempotent_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_invariance_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "eigenphase_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "participation",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "nearest_competitor_gap",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_overlap",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "runner_up_overlap",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "predecessor_overlap",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "loop_residual",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "runner-up, predecessor, and loop fields are null unless their declared relation exists"
      ]
    },
    "EndpointShellManifest": {
      "schema_id": "v3m0.endpoint-shell-manifest.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "shell_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.endpoint-shell-manifest.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "actual_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_dynamics_certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "shell_spec",
          "wire_type": "EndpointShellSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "dt",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "eigenphase_convention_id",
          "wire_type": "Literal[lambda-exp-plus-i-theta-principal-v1]",
          "presence": "required",
          "literal_domain": [
            "lambda-exp-plus-i-theta-principal-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "shell_phases",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "shell point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "shell_projectors",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "point_audits",
          "wire_type": "tuple[ShellPointAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(shell_phases)"
          },
          "nested_record": "ShellPointAudit",
          "constraints": []
        },
        {
          "name": "hermitian_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "idempotent_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "g_invariance_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "eigenphase_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "participation_min",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "nearest_competitor_gap_min",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_overlap_min",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "runner_up_overlap_max",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "predecessor_overlap_min",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "overlap_margin_min",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "loop_residual_max",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "ambiguous",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "shell_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all extrema are recomputed from point_audits",
        "matched_ablated cannot own or reselect this shell"
      ]
    },
    "ShellCandidatePointAttempt": {
      "schema_id": "v3m0.shell-candidate-point-attempt.wire.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "momentum_path_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "momentum_path_position",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_phases",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "candidate count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_ranks",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_participations",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_reference_overlaps",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "candidate_predecessor_overlaps",
          "wire_type": "tuple[Optional[float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(candidate_phases)"
          },
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "candidate columns align at one exact path point"
      ]
    },
    "EndpointShellAttemptAudit": {
      "schema_id": "v3m0.endpoint-shell-attempt.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "attempt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.endpoint-shell-attempt.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "shell_spec",
          "wire_type": "EndpointShellSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "point_attempts",
          "wire_type": "tuple[ShellCandidatePointAttempt,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "response grid point count"
          },
          "nested_record": "ShellCandidatePointAttempt",
          "constraints": []
        },
        {
          "name": "projector_residual_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "loop_residual_max_observed",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "attempt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "each response-grid path point retains its own typed candidate attempt"
      ]
    },
    "EndpointShellOutcome": {
      "schema_id": "v3m0.endpoint-shell-outcome.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[EndpointShellFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_outcome",
          "wire_type": "EndpointReferenceOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "attempt_audit",
          "wire_type": "EndpointShellAttemptAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellAttemptAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "shell",
          "wire_type": "Optional[EndpointShellManifest]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellManifest",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff failure is null and shell is non-null",
        "failure iff failure is non-null and shell is null",
        "reference outcome is retained on every shell branch"
      ]
    },
    "SourceFrameCoverageCertificate": {
      "schema_id": "v3m0.source-frame-coverage.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "certificate_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.source-frame-coverage.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "source_basis_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "trial_matrix",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "frame_operator_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "canonical_dual_residual_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "trials cover the full source frame"
      ]
    },
    "SourceReadoutBridgeMatrixAudit": {
      "schema_id": "v3m0.source-readout-bridge-matrix-audit.wire.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "macro_steps",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_difference_matrix",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "frame_coverage",
          "wire_type": "Optional[SourceFrameCoverageCertificate]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceFrameCoverageCertificate",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "raw_frobenius_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_operator_norm_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "h_whitened_operator_error_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curv_whitened_operator_error_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "one audit row per bridge-grid point and source bridge step"
      ]
    },
    "SourceReadoutBridgeAudit": {
      "schema_id": "v3m0.source-readout-bridge.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "bridge_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.source-readout-bridge.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "branch",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "dynamics_certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "run_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_metric_whitener_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "readout_calibration_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matrix_audits",
          "wire_type": "tuple[SourceReadoutBridgeMatrixAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "grid x steps count"
          },
          "nested_record": "SourceReadoutBridgeMatrixAudit",
          "constraints": []
        },
        {
          "name": "h_operator_error_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curv_operator_error_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "both branches bind the exact same ResponseRunSpec SHA"
      ]
    },
    "SourceReadoutResponse": {
      "schema_id": "v3m0.source-readout-response.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "response_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.source-readout-response.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "branch",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "transition_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "dynamics_certificate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "run_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "shell_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "bridge_audit",
          "wire_type": "SourceReadoutBridgeAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutBridgeAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "values",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "actual and matched responses use the actual-selected shell manifest"
      ]
    },
    "PairedFilteredResponse": {
      "schema_id": "v3m0.paired-filtered-response.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "pair_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.paired-filtered-response.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "ablation_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "qualification_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_dynamics_certificate",
          "wire_type": "DynamicsCertificateV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificateV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablated_dynamics_certificate",
          "wire_type": "DynamicsCertificateV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificateV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual",
          "wire_type": "SourceReadoutResponse",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutResponse",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablated",
          "wire_type": "SourceReadoutResponse",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutResponse",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "run_spec",
          "wire_type": "ResponseRunSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseRunSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "shell_manifest",
          "wire_type": "EndpointShellManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "pair_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "both certificate and response bodies are complete",
        "one shared run spec and actual-selected shell",
        "no half pair"
      ]
    },
    "SourceReadoutBranchAttemptAudit": {
      "schema_id": "v3m0.source-readout-branch-attempt.wire.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "branch",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_values",
          "wire_type": "Optional[FrozenComplexTensor]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "bridge_audit",
          "wire_type": "Optional[SourceReadoutBridgeAudit]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutBridgeAudit",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[PairedResponseFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "attempt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success branch has response and bridge bodies; failed branch preserves every completed body"
      ]
    },
    "PairedResponseAttemptAudit": {
      "schema_id": "v3m0.paired-response-attempt.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "attempt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.paired-response-attempt.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "window_protocol",
          "wire_type": "WindowCalibrationProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "WindowCalibrationProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "qualification_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "ablated_factory_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_transition",
          "wire_type": "TransitionAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "TransitionAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablated_transition",
          "wire_type": "TransitionAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "TransitionAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_dynamics_certificate",
          "wire_type": "DynamicsCertificateV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificateV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablated_dynamics_certificate",
          "wire_type": "DynamicsCertificateV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificateV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "run_spec",
          "wire_type": "ResponseRunSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseRunSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "shell_outcome",
          "wire_type": "EndpointShellOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_branch_attempt",
          "wire_type": "Optional[SourceReadoutBranchAttemptAudit]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutBranchAttemptAudit",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "ablated_branch_attempt",
          "wire_type": "Optional[SourceReadoutBranchAttemptAudit]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutBranchAttemptAudit",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "first_failure",
          "wire_type": "Optional[PairedResponseFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "attempt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "shell outcome is always retained",
        "branch attempts are both absent before branching or present according to the fixed attempt order"
      ]
    },
    "PairedResponseOutcome": {
      "schema_id": "v3m0.paired-response-outcome.v1",
      "canonical_owner": "rulespace_v3.response",
      "field_specs": [
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[PairedResponseFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "attempt_audit",
          "wire_type": "PairedResponseAttemptAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PairedResponseAttemptAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "paired_response",
          "wire_type": "Optional[PairedFilteredResponse]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PairedFilteredResponse",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff failure is null and paired_response is non-null",
        "failure iff failure is non-null and paired_response is null",
        "no half-pair capability exists"
      ]
    },
    "ClosedControlApplicationEvidenceV3": {
      "schema_id": "v3m0.closed-control-application-evidence.v3",
      "canonical_owner": "rulespace_v3.control_application_evidence_v3",
      "field_specs": [
        {
          "name": "evidence_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.closed-control-application-evidence.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "permit",
          "wire_type": "CalibrationApplicationPermitV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CalibrationApplicationPermitV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "materialization",
          "wire_type": "ApplicationScenarioMaterializationV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioMaterializationV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_transition_authority",
          "wire_type": "TransitionAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "TransitionAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_transition_authority",
          "wire_type": "TransitionAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "TransitionAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_metric_support_attestation",
          "wire_type": "MetricSignedSupportAttestationV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MetricSignedSupportAttestationV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_metric_support_attestation",
          "wire_type": "MetricSignedSupportAttestationV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "MetricSignedSupportAttestationV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_bridge_grid_authority",
          "wire_type": "BridgeGridAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeGridAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_bridge_grid_authority",
          "wire_type": "BridgeGridAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeGridAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_dynamics_grid_authority",
          "wire_type": "DynamicsGridAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsGridAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_dynamics_grid_authority",
          "wire_type": "DynamicsGridAuthorityV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsGridAuthorityV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_certification_outcome",
          "wire_type": "DynamicsCertificationOutcomeV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificationOutcomeV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_certification_outcome",
          "wire_type": "DynamicsCertificationOutcomeV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DynamicsCertificationOutcomeV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "paired_response_outcome",
          "wire_type": "PairedResponseOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PairedResponseOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "claim_ceiling",
          "wire_type": "Literal[OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY]",
          "presence": "required",
          "literal_domain": [
            "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "causal_contrast_role",
          "wire_type": "Literal[NULL_INTERVENTION_INVARIANCE_CONTROL]",
          "presence": "required",
          "literal_domain": [
            "NULL_INTERVENTION_INVARIANCE_CONTROL"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "physical_anchor_eligibility",
          "wire_type": "Literal[INELIGIBLE]",
          "presence": "required",
          "literal_domain": [
            "INELIGIBLE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "family_eligibility",
          "wire_type": "Literal[INELIGIBLE]",
          "presence": "required",
          "literal_domain": [
            "INELIGIBLE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "chain_replay_audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "evidence_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "contains no ResponseBlock or geometry evaluation body",
        "both certification outcomes and paired outcome are success bodies from one root/run spec/shell"
      ]
    },
    "ClosedControlApplicationEvidenceOutcomeV3": {
      "schema_id": "v3m0.closed-control-application-evidence-outcome.v3",
      "canonical_owner": "rulespace_v3.control_application_evidence_v3",
      "field_specs": [
        {
          "name": "outcome_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.closed-control-application-evidence-outcome.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[ClosedEvidenceFailureV3]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "paired_response_outcome",
          "wire_type": "PairedResponseOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PairedResponseOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "replay_stage_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "fixed full-chain stage count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "evidence",
          "wire_type": "Optional[ClosedControlApplicationEvidenceV3]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ClosedControlApplicationEvidenceV3",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff failure is null and evidence is non-null",
        "failure iff failure is non-null and evidence is null",
        "paired typed evidence is retained on failure"
      ]
    },
    "ResponseBlockOperatorSpec": {
      "schema_id": "v3m0.response-block-operator-spec.v1",
      "canonical_owner": "rulespace_v3.blocks",
      "field_specs": [
        {
          "name": "spec_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-block-operator-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "source_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "h_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_incidence_operator",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_normalizer_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "derivation_id",
          "wire_type": "Literal[control-readout-calibration-spec-recursive-v1]",
          "presence": "required",
          "literal_domain": [
            "control-readout-calibration-spec-recursive-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "operator spec is recursively derived from closed evidence"
      ]
    },
    "ResponseBlockAudit": {
      "schema_id": "v3m0.response-block-audit.v1",
      "canonical_owner": "rulespace_v3.blocks",
      "field_specs": [
        {
          "name": "audit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-block-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "q_all_orth_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "q_active_orth_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curvature_hermitian_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "q_curv_orth_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "s_curv_hermitian_residual",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_metric_min_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "h_metric_min_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curvature_metric_min_lower",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "active_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "curvature_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all values are recomputed from the response block operator body"
      ]
    },
    "ResponseBlock": {
      "schema_id": "v3m0.response-block.v1",
      "canonical_owner": "rulespace_v3.blocks",
      "field_specs": [
        {
          "name": "block_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-block.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "branch",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_readout_response",
          "wire_type": "SourceReadoutResponse",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SourceReadoutResponse",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "pair_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "operator_spec",
          "wire_type": "ResponseBlockOperatorSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseBlockOperatorSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "q_all",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "q_active",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "v_curv",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "q_curv",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "s_curv",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "audit",
          "wire_type": "ResponseBlockAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseBlockAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "paired_response_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "calibration_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "selected_fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_authority_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "block_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "canonical owner remains rulespace_v3.blocks",
        "VerifiedResponseBlock is signed only after closed evidence is reverified"
      ]
    },
    "GeometryPrerequisiteEvaluationV3": {
      "schema_id": "v3m0.geometry-prerequisite-evaluation.v3",
      "canonical_owner": "rulespace_v3.control_geometry_evaluation_v3",
      "field_specs": [
        {
          "name": "evaluation_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.geometry-prerequisite-evaluation.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "prerequisite_id",
          "wire_type": "Literal[C19 seven frozen predicate IDs]",
          "presence": "required",
          "literal_domain": [
            "complete-nonzero-gram-support-selection",
            "whitened-coisometry-or-incidence-range-preservation",
            "incidence-rank-six",
            "gauge-contained-in-incidence-kernel-dimension-four",
            "tt2-gauge4-row4-pairwise-orthogonal-complete-decomposition",
            "constraint-kernel-tt-plus-gauge-compatible-projector-and-metric",
            "actual-source-readout-share-endpoint-shell-and-finite-paired-response"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "closed_evidence_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual_response_block_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "matched_ablated_response_block_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "raw_observation",
          "wire_type": "GeometryPrerequisiteObservationV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "GeometryPrerequisiteObservationV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "reason_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "predicate reason count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "evaluation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "status is a control prerequisite evaluation only, never scientific PASS/FAIL"
      ]
    },
    "C19ControlGeometryEvaluationV3": {
      "schema_id": "v3m0.c19-control-geometry-evaluation.v3",
      "canonical_owner": "rulespace_v3.control_geometry_evaluation_v3",
      "field_specs": [
        {
          "name": "control_geometry_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.c19-control-geometry-evaluation.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "closed_evidence",
          "wire_type": "ClosedControlApplicationEvidenceV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ClosedControlApplicationEvidenceV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_response_block",
          "wire_type": "ResponseBlock",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseBlock",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "matched_ablated_response_block",
          "wire_type": "ResponseBlock",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseBlock",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "prerequisite_evaluations",
          "wire_type": "tuple[GeometryPrerequisiteEvaluationV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "7"
          },
          "nested_record": "GeometryPrerequisiteEvaluationV3",
          "constraints": []
        },
        {
          "name": "claim_ceiling",
          "wire_type": "Literal[OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY]",
          "presence": "required",
          "literal_domain": [
            "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "causal_contrast_role",
          "wire_type": "Literal[NULL_INTERVENTION_INVARIANCE_CONTROL]",
          "presence": "required",
          "literal_domain": [
            "NULL_INTERVENTION_INVARIANCE_CONTROL"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "physical_anchor_eligibility",
          "wire_type": "Literal[INELIGIBLE]",
          "presence": "required",
          "literal_domain": [
            "INELIGIBLE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "family_eligibility",
          "wire_type": "Literal[INELIGIBLE]",
          "presence": "required",
          "literal_domain": [
            "INELIGIBLE"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "evaluation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "evaluation order equals the seven frozen prerequisite IDs",
        "does not contain triggered, PASS, physical anchor, or family-eligibility upgrade"
      ]
    },
    "V3M0SyntheticControlApplicationSpec": {
      "schema_id": "v3m0.synthetic-control-application-spec.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "application_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-control-application-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "builder_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "basis_protocol",
          "wire_type": "SyntheticApplicationBasisProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SyntheticApplicationBasisProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "grid_protocol",
          "wire_type": "SyntheticApplicationGridProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SyntheticApplicationGridProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_protocol",
          "wire_type": "SyntheticApplicationReadoutProtocol",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SyntheticApplicationReadoutProtocol",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "protocol_constant_payload",
          "wire_type": "SyntheticApplicationProtocolConstants",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SyntheticApplicationProtocolConstants",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "operations",
          "wire_type": "tuple[SyntheticApplicationOperation,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "operation count"
          },
          "nested_record": "SyntheticApplicationOperation",
          "constraints": [
            "full recursive raw bodies"
          ]
        },
        {
          "name": "output_operation_instance_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "output count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_execution_specs",
          "wire_type": "tuple[ApplicationScenarioExecutionSpec,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "scenario count"
          },
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": []
        },
        {
          "name": "required_pipeline_stages",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "stage count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_prediction_profile_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_prediction_profile",
          "wire_type": "SyntheticApplicationPredictionProfile",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SyntheticApplicationPredictionProfile",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "expected_control_evidence_schema",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "body is replayed from immutable Parent-v3 preparation-commit blobs"
      ]
    },
    "ApplicationScenarioExecutionSpec": {
      "schema_id": "v3m0.application-scenario-execution-spec.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "scenario_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.application-scenario-execution-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "scenario_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operation_output_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "scenario output count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "execution_lane",
          "wire_type": "Literal[BLOCK_SUCCESS,EXPECTED_TYPED_TERMINATION,ANALYSIS_CONTROL]",
          "presence": "required",
          "literal_domain": [
            "BLOCK_SUCCESS",
            "EXPECTED_TYPED_TERMINATION",
            "ANALYSIS_CONTROL"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "execution_recipe_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "recipe_parameter_wires",
          "wire_type": "tuple[tuple[str,TaggedScalarWire],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "recipe parameter count"
          },
          "nested_record": "TaggedScalarWire",
          "constraints": [
            "full recursive tagged scalar bodies"
          ]
        },
        {
          "name": "recipe_derivation_source_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_terminal_stage",
          "wire_type": "Optional[Literal[activation,trace,stability,endpoint_shell,success]]",
          "presence": "required-nullable",
          "literal_domain": [
            "activation",
            "trace",
            "stability",
            "endpoint_shell",
            "success"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_undefined_reason",
          "wire_type": "Optional[UndefinedReason]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_artifact_type",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "scenario_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "BLOCK_SUCCESS has null expected terminal/reason; typed termination has both; analysis lane is distinct"
      ]
    },
    "ParentV3ScenarioReplayAuthorityV1": {
      "schema_id": "v3m0.parent-v3-scenario-replay-authority.v1",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "replay_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.parent-v3-scenario-replay-authority.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3",
          "wire_type": "ParentFreezeV3Manifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ParentFreezeV3Manifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "preparation_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "source_parent_v1_ordinal",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "application_spec",
          "wire_type": "V3M0SyntheticControlApplicationSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0SyntheticControlApplicationSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "scenario_specs",
          "wire_type": "tuple[ApplicationScenarioExecutionSpec,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "application scenario count"
          },
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": []
        },
        {
          "name": "p_blob_source_closure",
          "wire_type": "tuple[tuple[str,sha256],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "complete replay source count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "p_blob_source_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "replay_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "C01-C18/C20 retain exact inherited ordinal and are first authorized by live Parent-v3",
        "no Parent-v1/v2 opaque wrapper or adapter appears"
      ]
    },
    "ResponseBlockAttemptOutcome": {
      "schema_id": "v3m0.response-block-attempt-outcome.v3",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "attempt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-block-attempt-outcome.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "application_spec",
          "wire_type": "V3M0SyntheticControlApplicationSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0SyntheticControlApplicationSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "scenario_spec",
          "wire_type": "ApplicationScenarioExecutionSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "permit",
          "wire_type": "CalibrationApplicationPermitV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CalibrationApplicationPermitV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "terminal_stage",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "raw_singular_values",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "stage-specific raw singular value count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "activation_labels",
          "wire_type": "tuple[Literal[null,grey,signal],...]",
          "presence": "required",
          "literal_domain": [
            "null",
            "grey",
            "signal"
          ],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(raw_singular_values)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "precursor_evidence_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "downstream_capability_issued",
          "wire_type": "Literal[false]",
          "presence": "required",
          "literal_domain": [
            false
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "typed termination never mints a downstream capability",
        "terminal stage/reason must match the frozen C11/C13/C14 route"
      ]
    },
    "SigmaResult": {
      "schema_id": "v3m0.sigma-result.wire.v1",
      "canonical_owner": "rulespace_v3.sigma",
      "field_specs": [
        {
          "name": "geometry_manifest_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "deterministic",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "model_winner",
          "wire_type": "Literal[constant,power]",
          "presence": "required",
          "literal_domain": [
            "constant",
            "power"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "constant_fit",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full ConstantFit body"
          ]
        },
        {
          "name": "power_fit",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full PowerFit body"
          ]
        },
        {
          "name": "high_order_fit",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full HighOrderFit body"
          ]
        },
        {
          "name": "A",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "alpha",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "sigma_A",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "sigma_alpha",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "delta_aic",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "loo",
          "wire_type": "tuple[canonical-json-object,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "leave-one-out count"
          },
          "nested_record": null,
          "constraints": [
            "full LeaveOneOutPowerFit bodies"
          ]
        },
        {
          "name": "fit_window",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "fit window count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expanded_window",
          "wire_type": "Optional[tuple[float64,...]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "optional expanded window count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "direction",
          "wire_type": "Literal[geometry-manifest-defined]",
          "presence": "required",
          "literal_domain": [
            "geometry-manifest-defined"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "alpha_identifiable",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "zero_consistent",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "zero_test",
          "wire_type": "Literal[dm26-double-test,two-sigma]",
          "presence": "required",
          "literal_domain": [
            "dm26-double-test",
            "two-sigma"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "dm26_decision",
          "wire_type": "Optional[canonical-json-object]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full DM26Decision body when present"
          ]
        },
        {
          "name": "dm26_controls",
          "wire_type": "tuple[canonical-json-object,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "DM26 control count"
          },
          "nested_record": null,
          "constraints": [
            "full DM26ControlAudit bodies"
          ]
        }
      ],
      "record_invariants": [
        "all fits and controls remain raw recursive evidence"
      ]
    },
    "DeterministicSeriesControlOutcome": {
      "schema_id": "v3m0.deterministic-series-control-outcome.v1",
      "canonical_owner": "rulespace_v3.series_control",
      "field_specs": [
        {
          "name": "outcome_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.deterministic-series-control-outcome.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "application_spec",
          "wire_type": "V3M0SyntheticControlApplicationSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0SyntheticControlApplicationSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "scenario_spec",
          "wire_type": "ApplicationScenarioExecutionSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "k_values",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "series sample count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_samples",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(k_values)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "series_class",
          "wire_type": "Literal[clean-zero,true-floor]",
          "presence": "required",
          "literal_domain": [
            "clean-zero",
            "true-floor"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "decision_rule",
          "wire_type": "Literal[D-M2-6]",
          "presence": "required",
          "literal_domain": [
            "D-M2-6"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "sigma_result",
          "wire_type": "SigmaResult",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "SigmaResult",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "fit_decision_evidence_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "C20 is analysis-only and never enters ResponseBlock issuance"
      ]
    },
    "RepresentationInvariantOutcomeV3": {
      "schema_id": "v3m0.representation-invariant-outcome.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "invariant_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.representation-invariant-outcome.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "invariant_id",
          "wire_type": "Literal[I01,I02,I03,I04,I05,I06,I07,I08,I09]",
          "presence": "required",
          "literal_domain": [
            "I01",
            "I02",
            "I03",
            "I04",
            "I05",
            "I06",
            "I07",
            "I08",
            "I09"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "raw_observation",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_evidence_shas",
          "wire_type": "tuple[sha256,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "invariant source count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "one exact record per I01-I09 in canonical order"
      ]
    },
    "V3M0ScenarioEvidenceItemV3": {
      "schema_id": "v3m0.scenario-evidence-item.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "item_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.scenario-evidence-item.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_v3_replay",
          "wire_type": "ParentV3ScenarioReplayAuthorityV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ParentV3ScenarioReplayAuthorityV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "scenario_spec",
          "wire_type": "ApplicationScenarioExecutionSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ApplicationScenarioExecutionSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "item_tag",
          "wire_type": "Literal[BLOCK_SUCCESS,EXPECTED_TYPED_TERMINATION,ANALYSIS_CONTROL]",
          "presence": "required",
          "literal_domain": [
            "BLOCK_SUCCESS",
            "EXPECTED_TYPED_TERMINATION",
            "ANALYSIS_CONTROL"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "closed_control_evidence",
          "wire_type": "Optional[ClosedControlApplicationEvidenceV3]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ClosedControlApplicationEvidenceV3",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "response_block_attempt_outcome",
          "wire_type": "Optional[ResponseBlockAttemptOutcome]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseBlockAttemptOutcome",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "deterministic_series_outcome",
          "wire_type": "Optional[DeterministicSeriesControlOutcome]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "DeterministicSeriesControlOutcome",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "item_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "exactly one of closed_control_evidence, response_block_attempt_outcome, deterministic_series_outcome is non-null according to item_tag"
      ]
    },
    "V3M0ControlsResultV3": {
      "schema_id": "v3m0.controls-result.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "controls_result_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.controls-result.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "scenario_items",
          "wire_type": "tuple[V3M0ScenarioEvidenceItemV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "manifest scenario count"
          },
          "nested_record": "V3M0ScenarioEvidenceItemV3",
          "constraints": []
        },
        {
          "name": "calibrations",
          "wire_type": "tuple[WindowThresholdCalibrationV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "required calibration count"
          },
          "nested_record": "WindowThresholdCalibrationV3",
          "constraints": []
        },
        {
          "name": "representation_invariants",
          "wire_type": "tuple[RepresentationInvariantOutcomeV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "9"
          },
          "nested_record": "RepresentationInvariantOutcomeV3",
          "constraints": []
        },
        {
          "name": "controls_result_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "scenario and invariant order exactly follows V3M0RunManifestV3"
      ]
    },
    "V3M0ResponseResultV3": {
      "schema_id": "v3m0.response-result.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "response_result_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.response-result.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "closed_evidence",
          "wire_type": "tuple[ClosedControlApplicationEvidenceV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "BLOCK_SUCCESS scenario count"
          },
          "nested_record": "ClosedControlApplicationEvidenceV3",
          "constraints": []
        },
        {
          "name": "verified_response_block_shas",
          "wire_type": "tuple[sha256,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "two per successful scenario"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "geometry_evaluations",
          "wire_type": "tuple[C19ControlGeometryEvaluationV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "C19 control evaluation count"
          },
          "nested_record": "C19ControlGeometryEvaluationV3",
          "constraints": []
        },
        {
          "name": "response_result_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "block SHA order is scenario order then actual/matched branch order"
      ]
    },
    "V3M0StateDecisionV3": {
      "schema_id": "v3m0.state-decision.v3",
      "canonical_owner": "rulespace_v3.state",
      "field_specs": [
        {
          "name": "state_decision_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.state-decision.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "state",
          "wire_type": "V3M0State",
          "presence": "required",
          "literal_domain": [
            "HALT-V3M0-FORMAL",
            "HALT-V3M0-CONTROL",
            "HALT-V3M0-IDENTIFIABILITY",
            "HALT-V3M0-WINDOW",
            "READY-V3-M1-ANCHOR-CERTIFICATION"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "undefined",
          "wire_type": "tuple[tuple[str,UndefinedReason],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "required-block count"
          },
          "nested_record": null,
          "constraints": [
            "manifest block order"
          ]
        },
        {
          "name": "decision_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "READY is only a V3-M1 ceiling decision, not scientific PASS"
      ]
    },
    "PortableArtifactRefV1": {
      "schema_id": "v3m0.portable-artifact-ref.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "artifact_ref_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.portable-artifact-ref.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "artifact_kind",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "relative_path",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_sha256",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "byte_length",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_ref_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "path/kind/schema/order equals the stage manifest entry",
        "raw SHA covers exact immutable bytes"
      ]
    },
    "V3M0RunManifestV3": {
      "schema_id": "v3m0.run-manifest.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "run_manifest_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.run-manifest.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "signing_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "parent_v3_replay_case_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "19"
          },
          "nested_record": null,
          "constraints": [
            "C01..C18,C20 in that order"
          ]
        },
        {
          "name": "scenario_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "all frozen scenarios"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "representation_invariant_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "9"
          },
          "nested_record": null,
          "constraints": [
            "I01..I09"
          ]
        },
        {
          "name": "artifact_contracts",
          "wire_type": "tuple[V3M0ArtifactContractV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "4"
          },
          "nested_record": "V3M0ArtifactContractV3",
          "constraints": [
            "four path-kind-schema-order contracts; no output hashes"
          ]
        },
        {
          "name": "no_physical_anchor_run",
          "wire_type": "Literal[true]",
          "presence": "required",
          "literal_domain": [
            true
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "run_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "C19 routes only through CurrentApplicationAuthorityV3 and is not in inherited replay cases",
        "run manifest contains artifact contracts, never PortableArtifactRef output hashes"
      ]
    },
    "V3M0InstrumentResultV3": {
      "schema_id": "v3m0.instrument-result.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "result_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.instrument-result.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "run_manifest",
          "wire_type": "V3M0RunManifestV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0RunManifestV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "controls_result",
          "wire_type": "V3M0ControlsResultV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0ControlsResultV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "response_result",
          "wire_type": "V3M0ResponseResultV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0ResponseResultV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "representation_invariants",
          "wire_type": "tuple[RepresentationInvariantOutcomeV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "9"
          },
          "nested_record": "RepresentationInvariantOutcomeV3",
          "constraints": []
        },
        {
          "name": "state_decision",
          "wire_type": "V3M0StateDecisionV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0StateDecisionV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "formal_all_pass",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "exact_all_pass",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "identifiability_all_pass",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "all_required_controls_pass",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "all_expected_terminations_verified",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "all_analysis_controls_verified",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "representation_invariants_pass",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "no_unexpected_downstream_capability",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "no_physical_anchor_run",
          "wire_type": "Literal[true]",
          "presence": "required",
          "literal_domain": [
            true
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "result_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "booleans are recomputed from complete raw evidence and cannot override state decision"
      ]
    },
    "V3M0RunOutcomeV3": {
      "schema_id": "v3m0.run-outcome.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "outcome_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.run-outcome.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "run_manifest",
          "wire_type": "V3M0RunManifestV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0RunManifestV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "result",
          "wire_type": "V3M0InstrumentResultV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0InstrumentResultV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "first_undefined",
          "wire_type": "Optional[tuple[str,UndefinedReason]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "all_required_undefined",
          "wire_type": "tuple[tuple[str,UndefinedReason],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "required block count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "first_undefined is first element of all_required_undefined or null when empty"
      ]
    },
    "ParentFreezeCandidateV3Manifest": {
      "schema_id": "v3m0.parent-freeze-candidate.v3",
      "canonical_owner": "rulespace_v3.parent_candidate_v3",
      "field_specs": [
        {
          "name": "candidate_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.parent-freeze-candidate.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_state",
          "wire_type": "Literal[PROVISIONAL_NOT_ISSUED]",
          "presence": "required",
          "literal_domain": [
            "PROVISIONAL_NOT_ISSUED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "program_id",
          "wire_type": "Literal[projective-rule-space-v3m0-v3]",
          "presence": "required",
          "literal_domain": [
            "projective-rule-space-v3m0-v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preparation_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "historical_parent_v1",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full ParentFreezeManifest body from P blob"
          ]
        },
        {
          "name": "reviewed_candidate_v1",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full ParentFreezeCandidateManifest body from P blob"
          ]
        },
        {
          "name": "reviewed_candidate_v2",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full ParentFreezeCandidateV2Manifest body from P blob"
          ]
        },
        {
          "name": "inherited_current_application_authorities_v2",
          "wire_type": "tuple[canonical-json-object,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "19"
          },
          "nested_record": null,
          "constraints": [
            "full CurrentApplicationAuthorityV2 bodies for C01-C18,C20"
          ]
        },
        {
          "name": "superseded_application_authorities_v2",
          "wire_type": "tuple[canonical-json-object,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "full historical C19 CurrentApplicationAuthorityV2 body"
          ]
        },
        {
          "name": "refrozen_current_application_authorities_v3",
          "wire_type": "tuple[CurrentApplicationAuthorityV3,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": "CurrentApplicationAuthorityV3",
          "constraints": []
        },
        {
          "name": "application_supersessions",
          "wire_type": "tuple[canonical-json-object,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "1"
          },
          "nested_record": null,
          "constraints": [
            "full ApplicationSupersessionV3 body"
          ]
        },
        {
          "name": "block_success_scenario_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "canonical current scenario count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_closure",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "full SourceClosureV1 body from preparation commit"
          ]
        },
        {
          "name": "source_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "candidate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "C19 is replaced in place; C01-C18/C20 retain exact Parent-v1 ordinals",
        "all candidate bytes are read from preparation commit P"
      ]
    },
    "SignedSourceRefV2": {
      "schema_id": "v3m0.signed-source-ref.v2",
      "canonical_owner": "rulespace_v3.parent_freeze_v3_contracts",
      "field_specs": [
        {
          "name": "source_ref_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.signed-source-ref.v2"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "source_role",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_scope",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "relative_path",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_sha256",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "preparation_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "signing_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "source_ref_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "raw_sha256 covers the immutable S-epoch document blob"
      ]
    },
    "ParentReviewReceiptV1": {
      "schema_id": "v3m0.parent-review-receipt.v1",
      "canonical_owner": "rulespace_v3.parent_freeze_v3_contracts",
      "field_specs": [
        {
          "name": "receipt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.parent-review-receipt.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "review_role",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_key_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signature_algorithm",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "openssh-ed25519-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preparation_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "reviewed_candidate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "reviewed_path_closure",
          "wire_type": "tuple[tuple[str,sha256],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "complete candidate source closure"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewed_path_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "verdict",
          "wire_type": "Literal[PASS]",
          "presence": "required",
          "literal_domain": [
            "PASS"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signed_statement_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "signature_armor",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "receipt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "two Parent receipts have distinct fixed roles/keys and identical P/candidate/path closure"
      ]
    },
    "ParentSigningAuditV1": {
      "schema_id": "v3m0.parent-signing-audit.v1",
      "canonical_owner": "rulespace_v3.parent_freeze_v3_contracts",
      "field_specs": [
        {
          "name": "audit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.parent-signing-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "preparation_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "signing_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "review_receipt_shas",
          "wire_type": "tuple[sha256,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "diff_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "diff_allowlist_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signed_source_refs_root_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "reviewed_candidate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "reviewed_path_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "S has one parent P and only the frozen signed-source/receipt/literal transforms"
      ]
    },
    "ParentFreezeV3Manifest": {
      "schema_id": "v3m0.parent-freeze.v3",
      "canonical_owner": "rulespace_v3.parent_freeze_v3_contracts",
      "field_specs": [
        {
          "name": "parent_freeze_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.parent-freeze.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "authority_state",
          "wire_type": "Literal[CURRENT_PARENT_V3_ISSUED]",
          "presence": "required",
          "literal_domain": [
            "CURRENT_PARENT_V3_ISSUED"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "program_id",
          "wire_type": "Literal[projective-rule-space-v3m0-v3]",
          "presence": "required",
          "literal_domain": [
            "projective-rule-space-v3m0-v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preparation_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "signing_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "reviewed_candidate_v3",
          "wire_type": "ParentFreezeCandidateV3Manifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ParentFreezeCandidateV3Manifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "signed_source_refs",
          "wire_type": "tuple[SignedSourceRefV2,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "4"
          },
          "nested_record": "SignedSourceRefV2",
          "constraints": []
        },
        {
          "name": "review_receipts",
          "wire_type": "tuple[ParentReviewReceiptV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": "ParentReviewReceiptV1",
          "constraints": []
        },
        {
          "name": "signing_audit",
          "wire_type": "ParentSigningAuditV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ParentSigningAuditV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "current_application_registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "parent_freeze_v3_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "full Parent body is recursively present in V3M0 checkpoint",
        "live opaque Parent remains epoch-scoped; this raw body alone is not a capability"
      ]
    },
    "PortableSourceRefV1": {
      "schema_id": "v3m0.portable-source-ref.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "source_ref_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.portable-source-ref.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "relative_path",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "git_mode",
          "wire_type": "Literal[100644,100755]",
          "presence": "required",
          "literal_domain": [
            "100644",
            "100755"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_sha256",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "byte_length",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_ref_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "source bytes come from the immutable preparation/signing tree selected by the stage protocol"
      ]
    },
    "CampaignReviewerKeyV1": {
      "schema_id": "v3m0.campaign-reviewer-key.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "key_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-reviewer-key.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "review_role",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_key_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "public_key_algorithm",
          "wire_type": "Literal[ssh-ed25519]",
          "presence": "required",
          "literal_domain": [
            "ssh-ed25519"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "canonical_public_key_text",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "public_key_wire_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "key_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "reviewer_key_id is the canonical OpenSSH SHA256 fingerprint of the decoded key blob"
      ]
    },
    "CampaignReviewerRegistryV1": {
      "schema_id": "v3m0.campaign-reviewer-registry.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "registry_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-reviewer-registry.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_family_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_keys",
          "wire_type": "tuple[CampaignReviewerKeyV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": "CampaignReviewerKeyV1",
          "constraints": []
        },
        {
          "name": "registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "generic campaign registry owns its reviewer primitives; it imports no Parent-specific registry"
      ]
    },
    "CampaignStageReviewReceiptV1": {
      "schema_id": "v3m0.campaign-stage-review-receipt.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "receipt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-stage-review-receipt.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "review_role",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_key",
          "wire_type": "CampaignReviewerKeyV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignReviewerKeyV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "preparation_epoch_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "reviewed_taskbook_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "reviewed_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "reviewed_source_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "previous_envelope_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "verdict",
          "wire_type": "Literal[PASS]",
          "presence": "required",
          "literal_domain": [
            "PASS"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signed_statement_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "signature_algorithm",
          "wire_type": "Literal[openssh-ed25519-v1]",
          "presence": "required",
          "literal_domain": [
            "openssh-ed25519-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signature_armor",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "receipt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "exactly two distinct fixed roles sign the same taskbook/manifest/source/previous-root statement"
      ]
    },
    "CampaignStageSigningAuditV1": {
      "schema_id": "v3m0.campaign-stage-signing-audit.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "audit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-stage-signing-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preparation_epoch_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "signing_epoch_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "previous_envelope_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "taskbook_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "stage_manifest_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "source_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "review_receipt_shas",
          "wire_type": "tuple[sha256,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "strict_diff_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "strict_diff_allowlist_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "signing epoch is the unique one-parent successor of preparation epoch",
        "strict diff contains only stage-frozen signing transforms"
      ]
    },
    "CampaignStageFreezeV1": {
      "schema_id": "v3m0.campaign-stage-freeze.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "freeze_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-stage-freeze.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "stage_sequence",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "previous_envelope",
          "wire_type": "Optional[CampaignStageOutputEnvelopeV1]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignStageOutputEnvelopeV1",
          "constraints": [
            "full recursive previous portable body when non-null",
            "null only for the first campaign stage"
          ]
        },
        {
          "name": "previous_envelope_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "null only for the first campaign stage",
            "otherwise equals the verified previous envelope root"
          ]
        },
        {
          "name": "taskbook_ref",
          "wire_type": "PortableSourceRefV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PortableSourceRefV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "taskbook_body_utf8",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "stage_manifest_ref",
          "wire_type": "PortableArtifactRefV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PortableArtifactRefV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "stage_manifest_body",
          "wire_type": "canonical-json-object",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "stage_manifest_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_closure",
          "wire_type": "tuple[PortableSourceRefV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "complete stage source count"
          },
          "nested_record": "PortableSourceRefV1",
          "constraints": []
        },
        {
          "name": "source_closure_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "preparation_epoch_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "signing_epoch_commit_sha",
          "wire_type": "git-sha1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "40 lowercase hexadecimal Git commit SHA-1"
          ]
        },
        {
          "name": "reviewer_registry",
          "wire_type": "CampaignReviewerRegistryV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignReviewerRegistryV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "review_receipts",
          "wire_type": "tuple[CampaignStageReviewReceiptV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": "CampaignStageReviewReceiptV1",
          "constraints": []
        },
        {
          "name": "strict_diff_audit",
          "wire_type": "CampaignStageSigningAuditV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignStageSigningAuditV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "taskbook path/body/hash and stage manifest path/body/schema/hash are all recursively fixed",
        "previous_envelope and previous_envelope_sha are both null only for the first stage; otherwise full body SHA equals the derived field and verifier revalidates the prior opaque envelope"
      ]
    },
    "CampaignStageRunPermitV1": {
      "schema_id": "v3m0.campaign-stage-run-permit.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "permit_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-stage-run-permit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_freeze",
          "wire_type": "CampaignStageFreezeV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignStageFreezeV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "allowed_typed_state_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "taskbook allowed states"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_to_next_stage_ceiling",
          "wire_type": "tuple[tuple[str,str],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(allowed_typed_state_ids)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "permit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "issued only from a recursively verified stage freeze",
        "state/ceiling table equals the signed stage manifest"
      ]
    },
    "UnsignedPortableEnvelopeStatementV1": {
      "schema_id": "v3m0.unsigned-portable-envelope-statement.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "statement_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.unsigned-portable-envelope-statement.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "stage_sequence",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "stage_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "run_permit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "previous_portable_envelope_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "typed_state_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "next_stage_ceiling_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_root_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "statement_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "statement excludes signatures and portable_envelope_sha"
      ]
    },
    "PortableEnvelopeSignatureV1": {
      "schema_id": "v3m0.portable-envelope-signature.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "signature_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.portable-envelope-signature.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "review_role",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reviewer_key",
          "wire_type": "CampaignReviewerKeyV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignReviewerKeyV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "unsigned_statement_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "signature_algorithm",
          "wire_type": "Literal[openssh-ed25519-v1]",
          "presence": "required",
          "literal_domain": [
            "openssh-ed25519-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signature_armor",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signature_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "two distinct trusted reviewer keys sign the identical unsigned statement"
      ]
    },
    "PortableEnvelopeRootV1": {
      "schema_id": "v3m0.portable-envelope-root.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "portable_root_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.portable-envelope-root.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "stage_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "stage_sequence",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "previous_portable_envelope_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "typed_state_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "next_stage_ceiling_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_root_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "unsigned_statement_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "portable_envelope_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "portable_envelope_sha covers the complete unsigned statement, ordered signatures, and ordered artifact references"
      ]
    },
    "CampaignStageOutputEnvelopeV1": {
      "schema_id": "v3m0.campaign-stage-output-envelope.v1",
      "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
      "field_specs": [
        {
          "name": "output_envelope_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.campaign-stage-output-envelope.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "portable_root",
          "wire_type": "PortableEnvelopeRootV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PortableEnvelopeRootV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "stage_freeze",
          "wire_type": "CampaignStageFreezeV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignStageFreezeV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "run_permit",
          "wire_type": "CampaignStageRunPermitV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignStageRunPermitV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "artifact_refs",
          "wire_type": "tuple[PortableArtifactRefV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "stage manifest artifact count"
          },
          "nested_record": "PortableArtifactRefV1",
          "constraints": []
        },
        {
          "name": "unsigned_statement",
          "wire_type": "UnsignedPortableEnvelopeStatementV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "UnsignedPortableEnvelopeStatementV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "review_signatures",
          "wire_type": "tuple[PortableEnvelopeSignatureV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": "PortableEnvelopeSignatureV1",
          "constraints": []
        },
        {
          "name": "output_envelope_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "portable_root.portable_envelope_sha equals output_envelope_sha",
        "artifact root is recomputed from exact path-kind-schema-order leaves"
      ]
    },
    "V3M0CheckpointEnvelopeV1": {
      "schema_id": "v3m0.v3m0-checkpoint-envelope.v1",
      "canonical_owner": "rulespace_v3.checkpoint_envelope_v1",
      "field_specs": [
        {
          "name": "checkpoint_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.v3m0-checkpoint-envelope.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "portable_root",
          "wire_type": "PortableEnvelopeRootV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PortableEnvelopeRootV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "stage_output_envelope",
          "wire_type": "CampaignStageOutputEnvelopeV1",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CampaignStageOutputEnvelopeV1",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "parent_freeze_v3",
          "wire_type": "ParentFreezeV3Manifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ParentFreezeV3Manifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "run_outcome",
          "wire_type": "V3M0RunOutcomeV3",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "V3M0RunOutcomeV3",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "artifact_refs",
          "wire_type": "tuple[PortableArtifactRefV1,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "4"
          },
          "nested_record": "PortableArtifactRefV1",
          "constraints": []
        },
        {
          "name": "checkpoint_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "stage is V3-M0 and artifact tuple has the four exact registered leaves",
        "Parent root/run root/artifact bodies and portable root all agree",
        "checkpoint state is not scientific PASS and does not itself issue next-stage authority"
      ]
    },
    "V3M0ArtifactContractV3": {
      "schema_id": "v3m0.artifact-contract.v3",
      "canonical_owner": "rulespace_v3.runtime_v3",
      "field_specs": [
        {
          "name": "artifact_contract_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.artifact-contract.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "artifact_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "relative_path",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_kind",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_schema_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "artifact_contract_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "contains no raw SHA or byte length, avoiding a run-manifest/output self-hash cycle",
        "the four bodies equal artifact_contracts metadata in order"
      ]
    },
    "ControlReadoutCalibrationSpec": {
      "schema_id": "v3m0.control-readout-calibration-spec.v1",
      "canonical_owner": "rulespace_v3.registry",
      "field_specs": [
        {
          "name": "spec_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.control-readout-calibration-spec.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "source_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "h_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_incidence_operator",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_normalizer_id",
          "wire_type": "Literal[synthetic-identity-v1]",
          "presence": "required",
          "literal_domain": [
            "synthetic-identity-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all matrices are full frozen bodies"
      ]
    },
    "ControlWindowProtocolEntry": {
      "schema_id": "v3m0.control-window-protocol-entry.wire.v1",
      "canonical_owner": "rulespace_v3.window",
      "field_specs": [
        {
          "name": "control_id",
          "wire_type": "Literal[full,zero,direct_sum]",
          "presence": "required",
          "literal_domain": [
            "full",
            "zero",
            "direct_sum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "response_grid",
          "wire_type": "ResponseKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_readout_bridge_grid",
          "wire_type": "BridgeKGridManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BridgeKGridManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "source_readout_bridge_steps",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "frozen step count"
          },
          "nested_record": null,
          "constraints": [
            "contains a value > 1"
          ]
        },
        {
          "name": "reference_reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank_source_id",
          "wire_type": "Literal[parent-freeze-control-application-spec-v1]",
          "presence": "required",
          "literal_domain": [
            "parent-freeze-control-application-spec-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preregistered_phase_bands",
          "wire_type": "tuple[tuple[float64,float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "band count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_trial_generation_id",
          "wire_type": "Literal[registry-source-identity-v1]",
          "presence": "required",
          "literal_domain": [
            "registry-source-identity-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "response grid, bridge grid, steps, reference and bands are complete per-control bodies"
      ]
    },
    "ExpectedRankDeclaration": {
      "schema_id": "v3m0.expected-rank-declaration.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "declaration_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.expected-rank-declaration.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_registry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "control_id",
          "wire_type": "Literal[full,zero,direct_sum]",
          "presence": "required",
          "literal_domain": [
            "full",
            "zero",
            "direct_sum"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_h_actual_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_h_ablated_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_curv_actual_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_curv_ablated_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "parent_freeze_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "declaration_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "ranks come from Parent/registry, never observed candidates"
      ]
    },
    "CandidateAttemptAudit": {
      "schema_id": "v3m0.candidate-attempt-audit.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "attempt_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.candidate-attempt-audit.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_outcome",
          "wire_type": "EndpointReferenceOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointReferenceOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "shell_outcome",
          "wire_type": "Optional[EndpointShellOutcome]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "EndpointShellOutcome",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "paired_response_outcome",
          "wire_type": "Optional[PairedResponseOutcome]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "PairedResponseOutcome",
          "constraints": [
            "full recursive raw body when non-null"
          ]
        },
        {
          "name": "attempt_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "reference always present; shell iff reference success; paired iff shell success"
      ]
    },
    "ControlCandidateOutcome": {
      "schema_id": "v3m0.control-candidate-outcome.wire.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "status",
          "wire_type": "BlockStatus",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BlockStatus",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "failure",
          "wire_type": "Optional[ControlCandidateFailure]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "run_spec",
          "wire_type": "ResponseRunSpec",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ResponseRunSpec",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "attempt_audit",
          "wire_type": "CandidateAttemptAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CandidateAttemptAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "outcome_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "success iff failure is null and status is defined",
        "failure mapping follows reference -> shell -> paired -> bridge first error"
      ]
    },
    "BranchSpectrumAudit": {
      "schema_id": "v3m0.branch-spectrum-audit.wire.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "branch",
          "wire_type": "Literal[actual,matched_ablated]",
          "presence": "required",
          "literal_domain": [
            "actual",
            "matched_ablated"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "declared_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spectrum_shape",
          "wire_type": "tuple[int,int]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spectrum_order_id",
          "wire_type": "Literal[k-major-singular-descending-v1]",
          "presence": "required",
          "literal_domain": [
            "k-major-singular-descending-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_spectrum",
          "wire_type": "tuple[float64,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "product(spectrum_shape)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "active_min",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "inactive_max",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "branch_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "active/inactive extrema are recomputed from declared rank and raw spectrum"
      ]
    },
    "PerControlReadoutSpectrumAudit": {
      "schema_id": "v3m0.per-control-readout-spectrum-audit.wire.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "readout_kind",
          "wire_type": "Literal[h,curv]",
          "presence": "required",
          "literal_domain": [
            "h",
            "curv"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_registry_entry_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "expected_rank_declaration_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "fejer_order",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "run_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "paired_response_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "actual",
          "wire_type": "BranchSpectrumAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BranchSpectrumAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "ablated",
          "wire_type": "BranchSpectrumAudit",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BranchSpectrumAudit",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "actual_bridge_operator_error_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "ablated_bridge_operator_error_upper",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "both branches and bridge errors are retained"
      ]
    },
    "ControlCandidateAudit": {
      "schema_id": "v3m0.control-candidate-audit.wire.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "control_registry_entry",
          "wire_type": "ControlRegistryEntry",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ControlRegistryEntry",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "expected_rank_declaration",
          "wire_type": "ExpectedRankDeclaration",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ExpectedRankDeclaration",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "candidate_t",
          "wire_type": "ControlCandidateOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ControlCandidateOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "comparison_2t",
          "wire_type": "ControlCandidateOutcome",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "ControlCandidateOutcome",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_spectrum_audits",
          "wire_type": "tuple[PerControlReadoutSpectrumAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": "PerControlReadoutSpectrumAudit",
          "constraints": []
        },
        {
          "name": "comparison_2t_readout_spectrum_audits",
          "wire_type": "tuple[PerControlReadoutSpectrumAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": "PerControlReadoutSpectrumAudit",
          "constraints": []
        },
        {
          "name": "phase_separation",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "overlap_margin",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "projector_t2t_distance",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "passed",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "audit_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "T and 2T typed outcome graphs are both complete"
      ]
    },
    "ReadoutAggregateCalibrationAudit": {
      "schema_id": "v3m0.readout-aggregate-calibration-audit.wire.v1",
      "canonical_owner": "rulespace_v3.calibration_authority",
      "field_specs": [
        {
          "name": "readout_kind",
          "wire_type": "Literal[h,curv]",
          "presence": "required",
          "literal_domain": [
            "h",
            "curv"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "per_control",
          "wire_type": "tuple[PerControlReadoutSpectrumAudit,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "3"
          },
          "nested_record": "PerControlReadoutSpectrumAudit",
          "constraints": []
        },
        {
          "name": "scale_ref",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "null_max",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_operator_error_max",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "noise_ref",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signal_min",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "tau_sig",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "signal_noise_ratio",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "raw_relative_gap",
          "wire_type": "float64",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "absolute_signal_gate_passed",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "relative_gap_gate_passed",
          "wire_type": "bool",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "aggregate_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all values derive from the three full per-control bodies"
      ]
    },
    "ProvenanceNode": {
      "schema_id": "v3m0.provenance-node.wire.v1",
      "canonical_owner": "rulespace_v3.trace",
      "field_specs": [
        {
          "name": "provenance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operation",
          "wire_type": "ProvenanceOperation",
          "presence": "required",
          "literal_domain": [
            "grammar_primitive",
            "grammar_constant",
            "target_spec_read",
            "target_equation_read",
            "target_projector_read",
            "target_aware_objective",
            "derive",
            "cache",
            "copy",
            "rename",
            "search",
            "selection",
            "manual_selection",
            "opaque_literal",
            "unclassified"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "depends_on",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "dependency count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_refs",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "target ref count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "objective_tags",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "objective count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "search_run_id",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "operation literal determines target-aware classification"
      ]
    },
    "CoefficientRecord": {
      "schema_id": "v3m0.coefficient-record.wire.v1",
      "canonical_owner": "rulespace_v3.trace",
      "field_specs": [
        {
          "name": "mechanism_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expression_schema",
          "wire_type": "Literal[v3m0.sympy-exact-ast.v1]",
          "presence": "required",
          "literal_domain": [
            "v3m0.sympy-exact-ast.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "variable_order",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "symbol count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expression_ast",
          "wire_type": "tuple[tagged-expression-node,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "AST node count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "provenance_root_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficient_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "expression AST is the exact tagged tuple grammar owned by rulespace_v3.trace"
      ]
    },
    "PrimitiveTrace": {
      "schema_id": "v3m0.primitive-trace.wire.v1",
      "canonical_owner": "rulespace_v3.trace",
      "field_specs": [
        {
          "name": "grammar_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_spec_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "mechanism_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "production_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "kind",
          "wire_type": "MechanismKind",
          "presence": "required",
          "literal_domain": [
            "target_blind",
            "target_conditioned",
            "unclassified"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "depends_on",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "dependency count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "support_offsets",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "support count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "state_channels",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "channel count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coefficient_digest",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "symbolic_origin_tags",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "origin tag count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "neutral_ablation",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "design_objective_tags",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "objective count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "search_run_id",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "source_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "design_provenance",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "all primitive lineage fields are carried, not a trace SHA alone"
      ]
    },
    "CalibrationObservation": {
      "schema_id": "v3m0.calibration-observation.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "observation_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.calibration-observation.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "seed_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "runtime_operator_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "holdout_source_manifest_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "readout_manifest_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_tensor",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "observation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "response tensor is complete"
      ]
    },
    "FrozenSyntheticTarget": {
      "schema_id": "v3m0.synthetic-target.v1",
      "canonical_owner": "rulespace_v3.factory",
      "field_specs": [
        {
          "name": "target_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-target.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "target_spec_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "target_spec_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "calibration_protocol_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "seed_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        },
        {
          "name": "observation",
          "wire_type": "CalibrationObservation",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "CalibrationObservation",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "target_response",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "runtime_operator_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "target and observation bodies are recursively bound"
      ]
    },
    "GeometryPrerequisiteObservationV3": {
      "schema_id": "v3m0.geometry-prerequisite-observation.v3",
      "canonical_owner": "rulespace_v3.control_geometry_evaluation_v3",
      "field_specs": [
        {
          "name": "observation_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.geometry-prerequisite-observation.v3"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "prerequisite_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "nonzero_gram_singular_values",
          "wire_type": "Optional[tuple[float64,...]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "selected support rank"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "coisometry_or_range_residual",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "incidence_rank",
          "wire_type": "Optional[int]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "gauge_kernel_residual",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "gauge_dimension",
          "wire_type": "Optional[int]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "subspace_gram",
          "wire_type": "Optional[FrozenComplexTensor]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body",
            "nullable; only decomposition predicate"
          ]
        },
        {
          "name": "constraint_kernel_residual",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "projector_metric_compatibility_residual",
          "wire_type": "Optional[float64]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "common_endpoint_shell_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "actual_response_finite",
          "wire_type": "Optional[bool]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "matched_response_finite",
          "wire_type": "Optional[bool]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "paired_response_sha",
          "wire_type": "Optional[sha256]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "observation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "presence pattern is uniquely determined by prerequisite_id",
        "seventh predicate requires common shell, both finite flags true, and paired response root"
      ]
    },
    "TaggedScalarWire": {
      "schema_id": "v3m0.tagged-scalar-wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "value_kind",
          "wire_type": "Literal[integer,fp64-bits,text,complex128-bits]",
          "presence": "required",
          "literal_domain": [
            "integer",
            "fp64-bits",
            "text",
            "complex128-bits"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "integer_value",
          "wire_type": "Optional[int]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "fp64_bits_value",
          "wire_type": "Optional[int]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "text_value",
          "wire_type": "Optional[str]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "complex128_bits_value",
          "wire_type": "Optional[tuple[int,int]]",
          "presence": "required-nullable",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "exact",
            "value": "2"
          },
          "nested_record": null,
          "constraints": []
        }
      ],
      "record_invariants": [
        "exactly one value is non-null and matches value_kind"
      ]
    },
    "SyntheticApplicationBasisProtocol": {
      "schema_id": "v3m0.synthetic-application-basis-protocol.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-application-basis-protocol.wire.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "source_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "readout_basis",
          "wire_type": "BasisManifest",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "BasisManifest",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "both bases are complete"
      ]
    },
    "SyntheticApplicationGridProtocol": {
      "schema_id": "v3m0.synthetic-application-grid-protocol.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-application-grid-protocol.wire.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "spatial_ndim",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "spatial_shape",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_torus_denominators",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "response_reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "response point count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "direction_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "direction count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "primitive_directions",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(direction_ids)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "path_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "path count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "ordered_paths",
          "wire_type": "tuple[tuple[tuple[int,...],...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "len(path_ids)"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "closure_path_pairs",
          "wire_type": "tuple[DirectionPathClosure,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "closure count"
          },
          "nested_record": "DirectionPathClosure",
          "constraints": []
        },
        {
          "name": "bridge_reciprocal_indices",
          "wire_type": "tuple[tuple[int,...],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "bridge count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "bridge_steps",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "step count"
          },
          "nested_record": null,
          "constraints": [
            "contains >1"
          ]
        },
        {
          "name": "reference_reciprocal_index",
          "wire_type": "tuple[int,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "derived",
            "value": "spatial_ndim"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "preregistered_phase_bands",
          "wire_type": "tuple[tuple[float64,float64],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "nonempty",
            "value": "band count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "reference_phase_band_source_id",
          "wire_type": "Literal[analytic-quarter-turn-positive-band-v1]",
          "presence": "required",
          "literal_domain": [
            "analytic-quarter-turn-positive-band-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_shell_rank_source_id",
          "wire_type": "Literal[parent-freeze-control-application-spec-v1]",
          "presence": "required",
          "literal_domain": [
            "parent-freeze-control-application-spec-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "full path/closure/bridge/reference bodies are embedded"
      ]
    },
    "SyntheticApplicationReadoutProtocol": {
      "schema_id": "v3m0.synthetic-application-readout-protocol.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "protocol_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-application-readout-protocol.wire.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "source_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "h_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_incidence_operator",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_metric_whitener",
          "wire_type": "FrozenComplexTensor",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": "FrozenComplexTensor",
          "constraints": [
            "full recursive raw body"
          ]
        },
        {
          "name": "curvature_normalizer_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "protocol_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all selector/metric operators are complete"
      ]
    },
    "SyntheticApplicationProtocolConstants": {
      "schema_id": "v3m0.synthetic-application-protocol-constants.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "constants_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-application-protocol-constants.wire.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "tagged_constants",
          "wire_type": "tuple[tuple[str,TaggedScalarWire],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "constant count"
          },
          "nested_record": "TaggedScalarWire",
          "constraints": []
        },
        {
          "name": "max_operation_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "max_dependency_edge_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "max_parameter_count",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "max_serialized_bytes",
          "wire_type": "int",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "constants_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "all constants use exact tagged scalar wires"
      ]
    },
    "SyntheticApplicationOperation": {
      "schema_id": "v3m0.synthetic-application-operation.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "operation_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-application-operation.wire.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "operation_instance_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "operation_kind",
          "wire_type": "ApplicationOperationKind",
          "presence": "required",
          "literal_domain": [
            "identity-v1",
            "canonical-shear-v1",
            "phase-rotation-v1",
            "amplitude-rescale-v1",
            "source-linear-mix-v1",
            "direct-sum-v1",
            "geometry-subspace-v1",
            "coverage-subspace-v1",
            "deterministic-series-v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "input_operation_instance_ids",
          "wire_type": "tuple[str,...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "dependency count"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "parameters",
          "wire_type": "tuple[tuple[str,TaggedScalarWire],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "parameter count"
          },
          "nested_record": "TaggedScalarWire",
          "constraints": []
        },
        {
          "name": "operation_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "operation IDs form the frozen DAG"
      ]
    },
    "SyntheticApplicationPredictionProfile": {
      "schema_id": "v3m0.synthetic-application-prediction-profile.wire.v1",
      "canonical_owner": "rulespace_v3.parent_freeze",
      "field_specs": [
        {
          "name": "prediction_schema_version",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [
            "v3m0.synthetic-application-prediction-profile.wire.v1"
          ],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "exact schema literal"
          ]
        },
        {
          "name": "prediction_profile_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "control_case_id",
          "wire_type": "str",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "expected_exact_values",
          "wire_type": "tuple[tuple[str,tuple[TaggedScalarWire,...]],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "exact prediction rows"
          },
          "nested_record": "TaggedScalarWire",
          "constraints": []
        },
        {
          "name": "expected_qualitative_labels",
          "wire_type": "tuple[tuple[str,tuple[str,...]],...]",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": {
            "kind": "bounded",
            "value": "qualitative rows"
          },
          "nested_record": null,
          "constraints": []
        },
        {
          "name": "prediction_profile_sha",
          "wire_type": "sha256",
          "presence": "required",
          "literal_domain": [],
          "tuple_cardinality": null,
          "nested_record": null,
          "constraints": [
            "64 lowercase hexadecimal SHA-256"
          ]
        }
      ],
      "record_invariants": [
        "predictions are Parent-frozen, never derived from observed response"
      ]
    }
  },
  "tasks": {
    "B1": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.application_authority_v3",
        "rulespace_v3.task11_runner"
      ],
      "implementation_files": [
        {
          "action": "CREATE",
          "path": "rulespace_v3/application_authority_v3.py"
        },
        {
          "action": "CREATE",
          "path": "tests/test_v3m0_application_authority_v3.py"
        },
        {
          "action": "MODIFY",
          "path": "rulespace_v3/task11_runner.py"
        },
        {
          "action": "MODIFY",
          "path": "tests/test_v3m0_task11_runner.py"
        }
      ],
      "owned_records": [
        "BlockStatus",
        "DynamicsKGridDerivationProtocolV1",
        "BridgeKGridDerivationProtocolV1",
        "MetricSupportDerivationProtocolV1",
        "C19BasisContractV2",
        "C19RuntimeConstructionV2",
        "C19ObserverGeometryBundleV1",
        "CurrentScenarioResponseContractV3",
        "CurrentScenarioAuthorityV3",
        "CurrentApplicationAuthorityV3",
        "ControlRegistryEntry",
        "ClosedControlRegistry",
        "WindowCalibrationProtocol",
        "SelectedControlEvidenceRef",
        "WindowCandidateAudit",
        "WindowThresholdSelection",
        "WindowThresholdCalibrationManifest",
        "WindowCalibrationOutcome",
        "ScenarioBasisSelectorSpec",
        "CurrentScenarioResponseContractV2",
        "CurrentScenarioAuthorityV2",
        "CurrentApplicationAuthorityV2",
        "ParentV3CalibrationControlReplayRefV1",
        "WindowThresholdCalibrationV3",
        "CalibrationApplicationPermitV3",
        "ControlReadoutCalibrationSpec",
        "ControlWindowProtocolEntry",
        "ExpectedRankDeclaration",
        "CandidateAttemptAudit",
        "ControlCandidateOutcome",
        "BranchSpectrumAudit",
        "PerControlReadoutSpectrumAudit",
        "ControlCandidateAudit",
        "ReadoutAggregateCalibrationAudit"
      ],
      "apis": [
        {
          "name": "_run_task11_window_calibration_from_task8_replay",
          "visibility": "owner-internal",
          "args": [
            {
              "name": "historical_parent",
              "wire_type": "VerifiedParentFreeze"
            },
            {
              "name": "task8_replay",
              "wire_type": "CurrentTask8ControlReplay"
            }
          ],
          "returns": "WindowCalibrationOutcome",
          "raw_hydration_allowed": false,
          "semantics": "accept only the exact historical Parent-v1 and exact CurrentTask8ControlReplay; internally rebuild the authority-neutral legacy registry/window, share the same six-order numerical core with the unchanged public V2 runner, and return a raw WindowCalibrationOutcome carrying no authority; no current_registry, current_window, or parent_freeze_v2_sha argument exists"
        },
        {
          "name": "calibrate_v3m0_window_thresholds_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            }
          ],
          "returns": "VerifiedWindowThresholdCalibrationV3",
          "raw_hydration_allowed": false,
          "semantics": "under the live Parent-v3 root, bind the full tagged 20-entry current registry, select exact inherited-V2 C01-C03 P bodies by original ordinal, rebuild the authority-neutral numerical registry/window from the exact historical Parent-v1 witness, and run Task 11 without constructing a Parent-v2 root or opaque adapter; return a typed full outcome"
        },
        {
          "name": "verify_window_threshold_calibration_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "calibration",
              "wire_type": "VerifiedWindowThresholdCalibrationV3"
            }
          ],
          "returns": "VerifiedWindowThresholdCalibrationV3",
          "raw_hydration_allowed": false,
          "semantics": "recursively replay Parent/current registry/calibration; never promote a raw body"
        },
        {
          "name": "issue_calibration_application_permit_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "calibration",
              "wire_type": "VerifiedWindowThresholdCalibrationV3"
            },
            {
              "name": "control_case_id",
              "wire_type": "str"
            },
            {
              "name": "application_instance_id",
              "wire_type": "str"
            },
            {
              "name": "scenario_id",
              "wire_type": "str"
            }
          ],
          "returns": "VerifiedCalibrationApplicationPermitV3",
          "raw_hydration_allowed": false,
          "semantics": "select exact full current application/scenario/response bodies from Parent; selection must be resolved"
        },
        {
          "name": "verify_calibration_application_permit_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "permit",
              "wire_type": "VerifiedCalibrationApplicationPermitV3"
            }
          ],
          "returns": "VerifiedCalibrationApplicationPermitV3",
          "raw_hydration_allowed": false,
          "semantics": "replay all recursive permit joins"
        }
      ],
      "opaque_wrappers": [
        "VerifiedWindowThresholdCalibrationV3",
        "VerifiedCalibrationApplicationPermitV3"
      ],
      "typed_failures": [
        "PARENT_V3_UNAVAILABLE",
        "CALIBRATION_REPLAY_FAILED",
        "WINDOW_UNRESOLVED",
        "CURRENT_APPLICATION_MISSING",
        "SCENARIO_MISSING",
        "CROSS_PARENT_ROOT"
      ],
      "invariants": [
        "V1/V2 calibration or permit wrappers are rejected",
        "permit has no caller observation or copied threshold",
        "calibration stores the exact full mixed V2/V3 current registry and exact C01-C03 replay refs",
        "no invented parent_freeze_v2_sha or raw/opaque V2 registry-window input exists",
        "owner-internal Task11 replay accepts only historical Parent-v1 plus Task8 replay, returns authority-neutral raw outcome, and shares the unchanged public V2 runner numerical core"
      ]
    },
    "B2": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.application_materialization_v3"
      ],
      "owned_records": [
        "FrozenComplexTensor",
        "BasisManifest",
        "ConstructionTrace",
        "PrimitiveInterface",
        "Primitive",
        "LinearRealspaceFactory",
        "AblationReplacement",
        "AblationManifest",
        "AblationPairSnapshot",
        "FactoryBranchBindingV3",
        "ApplicationScenarioMaterializationV3",
        "ProvenanceNode",
        "CoefficientRecord",
        "PrimitiveTrace",
        "CalibrationObservation",
        "FrozenSyntheticTarget"
      ],
      "apis": [
        {
          "name": "materialize_v3m0_application_scenario_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "permit",
              "wire_type": "VerifiedCalibrationApplicationPermitV3"
            }
          ],
          "returns": "VerifiedV3M0ApplicationScenarioMaterializationV3",
          "raw_hydration_allowed": false,
          "semantics": "replay the full construction trace, AblationPairSnapshot, and both 50-slot factories"
        },
        {
          "name": "verify_v3m0_application_scenario_materialization_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "permit",
              "wire_type": "VerifiedCalibrationApplicationPermitV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            }
          ],
          "returns": "VerifiedV3M0ApplicationScenarioMaterializationV3",
          "raw_hydration_allowed": false,
          "semantics": "recursively rerun the same construction and both branch bindings"
        }
      ],
      "opaque_wrappers": [
        "VerifiedV3M0ApplicationScenarioMaterializationV3"
      ],
      "typed_failures": [
        "PARENT_V3_UNAVAILABLE",
        "PERMIT_INVALID",
        "FACTORY_REPLAY_FAILED",
        "FACTORY_WIRE_DRIFT",
        "BRANCH_JOIN_FAILED",
        "CROSS_PARENT_ROOT"
      ],
      "invariants": [
        "actual/matched pair is atomic",
        "C19 uses only the current 20-channel Parent-v3 body"
      ]
    },
    "B3": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.transition_authority_v3"
      ],
      "owned_records": [
        "MeasuredTransition",
        "TransitionAuthorityV3"
      ],
      "apis": [
        {
          "name": "issue_transition_authority_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "factory_role",
              "wire_type": "Literal[actual,matched_ablated]"
            }
          ],
          "returns": "VerifiedTransitionAuthorityV3",
          "raw_hydration_allowed": false,
          "semantics": "select one live Parent-v3 materialization branch, derive its prestructure internally, run every canonical full-state unit impulse, and issue only the bound TransitionAuthorityV3"
        },
        {
          "name": "verify_transition_authority_v3",
          "visibility": "public",
          "args": [
            {
              "name": "transition",
              "wire_type": "TransitionAuthorityV3"
            },
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            }
          ],
          "returns": "VerifiedTransitionAuthorityV3",
          "raw_hydration_allowed": false,
          "semantics": "recursively join the full Parent-v3 branch live view and remeasure exact kernel/support/root; raw self-hash is insufficient"
        },
        {
          "name": "verify_transition_pair_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "actual_transition",
              "wire_type": "VerifiedTransitionAuthorityV3"
            },
            {
              "name": "matched_ablated_transition",
              "wire_type": "VerifiedTransitionAuthorityV3"
            }
          ],
          "returns": "tuple[VerifiedTransitionAuthorityV3,VerifiedTransitionAuthorityV3]",
          "raw_hydration_allowed": false,
          "semantics": "require the actual and matched_ablated TransitionAuthorityV3 live views to be an atomic same-Parent/materialization branch pair"
        }
      ],
      "opaque_wrappers": [
        "VerifiedTransitionAuthorityV3"
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
        "no naked kernel API",
        "no VerifiedFactory, VerifiedPrestructureAuthority, VerifiedTransition, MeasuredTransition, or raw prestructure entry is public",
        "state/channel/spatial/dt/boundary/basis/macro-step fields are exact"
      ]
    },
    "B4": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.metric_support_authority_v1"
      ],
      "owned_records": [
        "MetricSignedSupportAttestationV1"
      ],
      "apis": [
        {
          "name": "issue_c19_metric_signed_support_attestation_v1",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "factory_role",
              "wire_type": "Literal[actual,matched_ablated]"
            }
          ],
          "returns": "VerifiedMetricSignedSupportAttestationV1",
          "raw_hydration_allowed": false,
          "semantics": "derive exact I20 constant metric support from Parent/materialization; accepts no support/grid/SHA"
        },
        {
          "name": "verify_c19_metric_signed_support_attestation_v1",
          "visibility": "public",
          "args": [
            {
              "name": "attestation",
              "wire_type": "MetricSignedSupportAttestationV1"
            },
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            }
          ],
          "returns": "VerifiedMetricSignedSupportAttestationV1",
          "raw_hydration_allowed": false,
          "semantics": "recursively replay protocol, branch factory and support"
        }
      ],
      "opaque_wrappers": [
        "VerifiedMetricSignedSupportAttestationV1"
      ],
      "typed_failures": [
        "MATERIALIZATION_INVALID",
        "FACTORY_DEAD",
        "METRIC_PROTOCOL_DRIFT",
        "METRIC_REPLAY_FAILED",
        "SUPPORT_INVALID",
        "BRANCH_JOIN_FAILED",
        "CROSS_PARENT_ROOT"
      ],
      "invariants": [
        "record and wrapper names are exactly the metric-support authority erratum names"
      ]
    },
    "B5": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.runtime_grids_v3"
      ],
      "owned_records": [
        "DirectionPathClosure",
        "DirectionManifest",
        "ResponseKGridManifest",
        "DynamicsKGridManifest",
        "BridgeKGridManifest",
        "BridgeGridAuthorityV3",
        "DynamicsGridAuthorityV3"
      ],
      "apis": [
        {
          "name": "derive_bridge_grid_authority_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "factory_role",
              "wire_type": "Literal[actual,matched_ablated]"
            }
          ],
          "returns": "VerifiedBridgeGridAuthorityV3",
          "raw_hydration_allowed": false,
          "semantics": "derive bridge points solely from the live factory support"
        },
        {
          "name": "derive_dynamics_grid_authority_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "transition",
              "wire_type": "VerifiedTransitionAuthorityV3"
            },
            {
              "name": "metric",
              "wire_type": "VerifiedMetricSignedSupportAttestationV1"
            }
          ],
          "returns": "VerifiedDynamicsGridAuthorityV3",
          "raw_hydration_allowed": false,
          "semantics": "derive singleton or full-64 solely from transition/metric supports"
        },
        {
          "name": "verify_runtime_grid_authorities_v3",
          "visibility": "public",
          "args": [
            {
              "name": "bridge_grid",
              "wire_type": "VerifiedBridgeGridAuthorityV3"
            },
            {
              "name": "dynamics_grid",
              "wire_type": "VerifiedDynamicsGridAuthorityV3"
            }
          ],
          "returns": "tuple[VerifiedBridgeGridAuthorityV3,VerifiedDynamicsGridAuthorityV3]",
          "raw_hydration_allowed": false,
          "semantics": "replay strict grid types and branch/root joins"
        }
      ],
      "opaque_wrappers": [
        "VerifiedBridgeGridAuthorityV3",
        "VerifiedDynamicsGridAuthorityV3"
      ],
      "typed_failures": [
        "FACTORY_SUPPORT_INVALID",
        "TRANSITION_INVALID",
        "METRIC_ATTESTATION_INVALID",
        "BRANCH_JOIN_FAILED",
        "GRID_DERIVATION_FAILED",
        "CROSS_PARENT_ROOT"
      ],
      "invariants": [
        "response/dynamics/bridge grid classes are never interchangeable",
        "caller points are forbidden"
      ]
    },
    "B6": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.certificate_v3"
      ],
      "owned_records": [
        "PrestructureAuthority",
        "StructureManifest",
        "RealityCertificate",
        "MetricOriginManifest",
        "StabilityMetricWitness",
        "Fp64RootIntervalEntry",
        "Fp64RootOfUnityIntervalTable",
        "Fp64EnclosureProtocol",
        "FullStateBridgeSpec",
        "BridgeCaseAudit",
        "BridgeAudit",
        "LaurentResidualCertificate",
        "SpectralPointEnclosureColumnarSidecar",
        "SpectralMarginCoverage",
        "NormalizedMetricResidualAudit",
        "PowerDriftAudit",
        "RuntimeEvidenceManifest",
        "InstabilityGrowthCounterWitness",
        "DynamicsCertificateV3",
        "DynamicsCertificationAttemptAuditV3",
        "DynamicsCertificationOutcomeV3"
      ],
      "apis": [
        {
          "name": "certify_transition_dynamics_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "transition",
              "wire_type": "VerifiedTransitionAuthorityV3"
            },
            {
              "name": "metric_attestation",
              "wire_type": "VerifiedMetricSignedSupportAttestationV1"
            },
            {
              "name": "bridge_grid",
              "wire_type": "VerifiedBridgeGridAuthorityV3"
            },
            {
              "name": "dynamics_grid",
              "wire_type": "VerifiedDynamicsGridAuthorityV3"
            }
          ],
          "returns": "VerifiedDynamicsCertificationOutcomeV3",
          "raw_hydration_allowed": false,
          "semantics": "consume exactly one live Parent/materialization/TransitionAuthorityV3/metric-attestation/bridge-grid/dynamics-grid join, derive all legacy judge inputs owner-internally, run the fixed first-failure pipeline, and preserve completed raw bodies"
        },
        {
          "name": "verify_dynamics_certificate_v3",
          "visibility": "public",
          "args": [
            {
              "name": "certificate",
              "wire_type": "DynamicsCertificateV3"
            },
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "transition",
              "wire_type": "VerifiedTransitionAuthorityV3"
            },
            {
              "name": "metric_attestation",
              "wire_type": "VerifiedMetricSignedSupportAttestationV1"
            },
            {
              "name": "bridge_grid",
              "wire_type": "VerifiedBridgeGridAuthorityV3"
            },
            {
              "name": "dynamics_grid",
              "wire_type": "VerifiedDynamicsGridAuthorityV3"
            }
          ],
          "returns": "VerifiedDynamicsCertificateV3",
          "raw_hydration_allowed": false,
          "semantics": "recursively rejoin all six live upstream authorities before replaying executor, structure, metric, fp64, Laurent, coverage, bridge and power evidence"
        },
        {
          "name": "verify_dynamics_certification_outcome_v3",
          "visibility": "public",
          "args": [
            {
              "name": "outcome",
              "wire_type": "DynamicsCertificationOutcomeV3"
            },
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "transition",
              "wire_type": "VerifiedTransitionAuthorityV3"
            },
            {
              "name": "metric_attestation",
              "wire_type": "VerifiedMetricSignedSupportAttestationV1"
            },
            {
              "name": "bridge_grid",
              "wire_type": "VerifiedBridgeGridAuthorityV3"
            },
            {
              "name": "dynamics_grid",
              "wire_type": "VerifiedDynamicsGridAuthorityV3"
            }
          ],
          "returns": "VerifiedDynamicsCertificationOutcomeV3",
          "raw_hydration_allowed": false,
          "semantics": "rejoin all six live upstream authorities and replay success/failure XOR plus exact first-failure order"
        }
      ],
      "opaque_wrappers": [
        "VerifiedDynamicsCertificationOutcomeV3",
        "VerifiedDynamicsCertificateV3"
      ],
      "typed_failures": [
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
      "invariants": [
        "failure order is exactly DynamicsCertificationFailure enum order",
        "no old VerifiedFactory/VerifiedTransition/VerifiedPrestructureAuthority or caller raw structure/metric/grid/runtime entry exists",
        "only exact Jordan counterwitness can issue UNSTABLE"
      ]
    },
    "B7": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.application_response_v3"
      ],
      "owned_records": [
        "ResponseRunSpec",
        "EndpointReferenceSpec",
        "EndpointReferenceProjector",
        "EndpointReferenceAttemptAudit",
        "EndpointReferenceOutcome",
        "EndpointShellSpec",
        "ShellPointAudit",
        "EndpointShellManifest",
        "ShellCandidatePointAttempt",
        "EndpointShellAttemptAudit",
        "EndpointShellOutcome",
        "SourceFrameCoverageCertificate",
        "SourceReadoutBridgeMatrixAudit",
        "SourceReadoutBridgeAudit",
        "SourceReadoutResponse",
        "PairedFilteredResponse",
        "SourceReadoutBranchAttemptAudit",
        "PairedResponseAttemptAudit",
        "PairedResponseOutcome"
      ],
      "apis": [
        {
          "name": "build_endpoint_reference_outcome_v3",
          "visibility": "owner-internal",
          "args": [
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "actual_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            },
            {
              "name": "run_spec",
              "wire_type": "ResponseRunSpec"
            }
          ],
          "returns": "VerifiedEndpointReferenceOutcome",
          "raw_hydration_allowed": false,
          "semantics": "actual-only reference selection with complete typed attempt"
        },
        {
          "name": "build_endpoint_shell_outcome_v3",
          "visibility": "owner-internal",
          "args": [
            {
              "name": "reference",
              "wire_type": "VerifiedEndpointReferenceOutcome"
            },
            {
              "name": "actual_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            },
            {
              "name": "run_spec",
              "wire_type": "ResponseRunSpec"
            }
          ],
          "returns": "VerifiedEndpointShellOutcome",
          "raw_hydration_allowed": false,
          "semantics": "actual-only shell tracking with per-point attempts"
        },
        {
          "name": "issue_v3m0_application_paired_response_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "actual_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            },
            {
              "name": "matched_ablated_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            }
          ],
          "returns": "VerifiedPairedResponseOutcome",
          "raw_hydration_allowed": false,
          "semantics": "internally construct Reference -> Shell -> atomic Paired outcomes; never return half pair"
        },
        {
          "name": "verify_endpoint_reference_outcome_v3",
          "visibility": "owner-internal",
          "args": [
            {
              "name": "outcome",
              "wire_type": "EndpointReferenceOutcome"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "actual_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            },
            {
              "name": "run_spec",
              "wire_type": "ResponseRunSpec"
            }
          ],
          "returns": "VerifiedEndpointReferenceOutcome",
          "raw_hydration_allowed": false,
          "semantics": "replay exact reference attempt and payload XOR"
        },
        {
          "name": "verify_endpoint_shell_outcome_v3",
          "visibility": "owner-internal",
          "args": [
            {
              "name": "outcome",
              "wire_type": "EndpointShellOutcome"
            },
            {
              "name": "reference",
              "wire_type": "VerifiedEndpointReferenceOutcome"
            },
            {
              "name": "actual_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            },
            {
              "name": "run_spec",
              "wire_type": "ResponseRunSpec"
            }
          ],
          "returns": "VerifiedEndpointShellOutcome",
          "raw_hydration_allowed": false,
          "semantics": "replay exact shell attempt and payload XOR"
        },
        {
          "name": "verify_paired_response_outcome_v3",
          "visibility": "public",
          "args": [
            {
              "name": "outcome",
              "wire_type": "PairedResponseOutcome"
            },
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "materialization",
              "wire_type": "VerifiedV3M0ApplicationScenarioMaterializationV3"
            },
            {
              "name": "actual_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            },
            {
              "name": "matched_ablated_certificate",
              "wire_type": "VerifiedDynamicsCertificateV3"
            }
          ],
          "returns": "VerifiedPairedResponseOutcome",
          "raw_hydration_allowed": false,
          "semantics": "replay all three outcome layers and both branches atomically"
        }
      ],
      "opaque_wrappers": [
        "VerifiedEndpointReferenceOutcome",
        "VerifiedEndpointShellOutcome",
        "VerifiedPairedResponseOutcome"
      ],
      "typed_failures": [
        "REFERENCE_FAILED",
        "SHELL_FAILED",
        "PAIRED_RESPONSE_FAILED",
        "RESPONSE_BRIDGE_FAILED",
        "CROSS_PARENT_ROOT",
        "CROSS_BRANCH",
        "HALF_PAIR_FORBIDDEN"
      ],
      "invariants": [
        "reference, shell and paired raw outcomes are all retained",
        "matched branch never reselects reference or shell"
      ]
    },
    "B8": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.control_application_evidence_v3",
        "rulespace_v3.blocks",
        "rulespace_v3.control_geometry_evaluation_v3"
      ],
      "owned_records": [
        "ClosedControlApplicationEvidenceV3",
        "ClosedControlApplicationEvidenceOutcomeV3",
        "ResponseBlockOperatorSpec",
        "ResponseBlockAudit",
        "ResponseBlock",
        "GeometryPrerequisiteEvaluationV3",
        "C19ControlGeometryEvaluationV3",
        "GeometryPrerequisiteObservationV3"
      ],
      "apis": [
        {
          "name": "issue_closed_control_application_evidence_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "paired_response",
              "wire_type": "VerifiedPairedResponseOutcome"
            }
          ],
          "returns": "VerifiedClosedControlApplicationEvidenceOutcomeV3",
          "raw_hydration_allowed": false,
          "semantics": "replay the entire live chain and close evidence before any block construction"
        },
        {
          "name": "require_closed_control_application_evidence_v3",
          "visibility": "public",
          "args": [
            {
              "name": "outcome",
              "wire_type": "VerifiedClosedControlApplicationEvidenceOutcomeV3"
            }
          ],
          "returns": "VerifiedClosedControlApplicationEvidenceV3",
          "raw_hydration_allowed": false,
          "semantics": "return the private sealed evidence capability only from a recursively reverified success outcome"
        },
        {
          "name": "issue_verified_response_block_from_closed_evidence",
          "visibility": "public",
          "args": [
            {
              "name": "evidence",
              "wire_type": "VerifiedClosedControlApplicationEvidenceV3"
            },
            {
              "name": "branch",
              "wire_type": "Literal[actual,matched_ablated]"
            }
          ],
          "returns": "VerifiedResponseBlock",
          "raw_hydration_allowed": false,
          "semantics": "rulespace_v3.blocks signs its existing ResponseBlock only from closed evidence"
        },
        {
          "name": "evaluate_c19_control_geometry_v3",
          "visibility": "public",
          "args": [
            {
              "name": "evidence",
              "wire_type": "VerifiedClosedControlApplicationEvidenceV3"
            },
            {
              "name": "actual_block",
              "wire_type": "VerifiedResponseBlock"
            },
            {
              "name": "matched_ablated_block",
              "wire_type": "VerifiedResponseBlock"
            }
          ],
          "returns": "VerifiedC19ControlGeometryEvaluationV3",
          "raw_hydration_allowed": false,
          "semantics": "evaluate seven control-only prerequisites only after both verified blocks"
        }
      ],
      "opaque_wrappers": [
        "VerifiedClosedControlApplicationEvidenceOutcomeV3",
        "VerifiedClosedControlApplicationEvidenceV3",
        "VerifiedResponseBlock",
        "VerifiedC19ControlGeometryEvaluationV3"
      ],
      "typed_failures": [
        "UPSTREAM_INVALID",
        "CROSS_PARENT_ROOT",
        "CROSS_BRANCH",
        "CHAIN_REPLAY_FAILED",
        "RESPONSE_BLOCK_FAILED",
        "PAIR_BINDING_FAILED",
        "GEOMETRY_PREREQUISITE_FAILED",
        "CLAIM_CEILING_VIOLATION"
      ],
      "invariants": [
        "module order is paired response -> closed evidence -> blocks -> geometry evaluation",
        "C19 remains null-intervention and ineligible"
      ]
    },
    "B9": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.runtime_v3",
        "rulespace_v3.state"
      ],
      "owned_records": [
        "V3M0SyntheticControlApplicationSpec",
        "ApplicationScenarioExecutionSpec",
        "ParentV3ScenarioReplayAuthorityV1",
        "ResponseBlockAttemptOutcome",
        "SigmaResult",
        "DeterministicSeriesControlOutcome",
        "RepresentationInvariantOutcomeV3",
        "V3M0ScenarioEvidenceItemV3",
        "V3M0ControlsResultV3",
        "V3M0ResponseResultV3",
        "V3M0StateDecisionV3",
        "V3M0RunManifestV3",
        "V3M0InstrumentResultV3",
        "V3M0RunOutcomeV3",
        "V3M0ArtifactContractV3",
        "TaggedScalarWire",
        "SyntheticApplicationBasisProtocol",
        "SyntheticApplicationGridProtocol",
        "SyntheticApplicationReadoutProtocol",
        "SyntheticApplicationProtocolConstants",
        "SyntheticApplicationOperation",
        "SyntheticApplicationPredictionProfile"
      ],
      "apis": [
        {
          "name": "replay_parent_v3_scenario_authority_v1",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "control_case_id",
              "wire_type": "Literal[C01..C18,C20]"
            }
          ],
          "returns": "VerifiedParentV3ScenarioReplayAuthorityV1",
          "raw_hydration_allowed": false,
          "semantics": "first-authorize the full inherited application/scenario bodies from Parent-v3 P blobs"
        },
        {
          "name": "verify_parent_v3_scenario_replay_authority_v1",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "replay",
              "wire_type": "VerifiedParentV3ScenarioReplayAuthorityV1"
            }
          ],
          "returns": "VerifiedParentV3ScenarioReplayAuthorityV1",
          "raw_hydration_allowed": false,
          "semantics": "replay exact ordinal, P-blob closure, application and scenarios"
        },
        {
          "name": "run_v3m0_instrument_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            }
          ],
          "returns": "VerifiedV3M0RunOutcomeV3",
          "raw_hydration_allowed": false,
          "semantics": "assemble block successes, typed terminations, C20 series, calibration and I01-I09 into raw results/state"
        },
        {
          "name": "verify_v3m0_run_outcome_v3",
          "visibility": "public",
          "args": [
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "outcome",
              "wire_type": "VerifiedV3M0RunOutcomeV3"
            }
          ],
          "returns": "VerifiedV3M0RunOutcomeV3",
          "raw_hydration_allowed": false,
          "semantics": "replay every scenario lane, four artifact bodies and state decision"
        }
      ],
      "opaque_wrappers": [
        "VerifiedParentV3ScenarioReplayAuthorityV1",
        "VerifiedResponseBlockAttemptOutcomeV3",
        "VerifiedDeterministicSeriesControlOutcome",
        "VerifiedRepresentationInvariantOutcomeV3",
        "VerifiedV3M0RunOutcomeV3"
      ],
      "typed_failures": [
        "HALT-V3M0-FORMAL",
        "HALT-V3M0-CONTROL",
        "HALT-V3M0-IDENTIFIABILITY",
        "HALT-V3M0-WINDOW"
      ],
      "invariants": [
        "C01-C18/C20 have no Parent-v1/v2 opaque adapter",
        "READY literal is referenced but not issued by B0",
        "raw state preserves every (block_id, UndefinedReason) in manifest order"
      ]
    },
    "B10": {
      "implementation_status": "EXPECTED-MISSING_AT_B0_FREEZE",
      "modules": [
        "rulespace_v3.campaign_stage_authority_v1",
        "rulespace_v3.checkpoint_envelope_v1"
      ],
      "owned_records": [
        "PortableArtifactRefV1",
        "ParentFreezeCandidateV3Manifest",
        "SignedSourceRefV2",
        "ParentReviewReceiptV1",
        "ParentSigningAuditV1",
        "ParentFreezeV3Manifest",
        "PortableSourceRefV1",
        "CampaignReviewerKeyV1",
        "CampaignReviewerRegistryV1",
        "CampaignStageReviewReceiptV1",
        "CampaignStageSigningAuditV1",
        "CampaignStageFreezeV1",
        "CampaignStageRunPermitV1",
        "UnsignedPortableEnvelopeStatementV1",
        "PortableEnvelopeSignatureV1",
        "PortableEnvelopeRootV1",
        "CampaignStageOutputEnvelopeV1",
        "V3M0CheckpointEnvelopeV1"
      ],
      "apis": [
        {
          "name": "verify_campaign_stage_freeze_v1",
          "visibility": "public",
          "args": [
            {
              "name": "trust_anchor",
              "wire_type": "VerifiedCampaignCheckpointTrustAnchorV1"
            },
            {
              "name": "freeze",
              "wire_type": "CampaignStageFreezeV1"
            },
            {
              "name": "previous_envelope_input",
              "wire_type": "Optional[Union[VerifiedCampaignStageOutputEnvelopeV1,CampaignStageOutputEnvelopeV1]]"
            },
            {
              "name": "taskbook_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "stage_manifest_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "source_bundle",
              "wire_type": "tuple[tuple[PortableSourceRefV1,bytes],...]"
            },
            {
              "name": "reviewer_key_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "preparation_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "signing_source_bytes",
              "wire_type": "bytes"
            }
          ],
          "returns": "VerifiedCampaignStageFreezeV1",
          "raw_hydration_allowed": false,
          "semantics": "first require the exact out-of-band live trust-anchor and join its family/epoch/checkpoint/root/key-registry pins; only then verify exact taskbook/manifest bytes, ordered (source ref,raw bytes) closure, reviewer-key source, P/S source bytes, two receipts, strict diff and the frozen-or-live previous body"
        },
        {
          "name": "issue_campaign_stage_run_permit_v1",
          "visibility": "public",
          "args": [
            {
              "name": "trust_anchor",
              "wire_type": "VerifiedCampaignCheckpointTrustAnchorV1"
            },
            {
              "name": "stage_freeze",
              "wire_type": "VerifiedCampaignStageFreezeV1"
            }
          ],
          "returns": "VerifiedCampaignStageRunPermitV1",
          "raw_hydration_allowed": false,
          "semantics": "require the same out-of-band live trust-anchor sealed into the verified stage freeze, then issue only the signed manifest state/ceiling table"
        },
        {
          "name": "verify_campaign_stage_output_envelope_v1",
          "visibility": "public",
          "args": [
            {
              "name": "trust_anchor",
              "wire_type": "VerifiedCampaignCheckpointTrustAnchorV1"
            },
            {
              "name": "envelope",
              "wire_type": "CampaignStageOutputEnvelopeV1"
            },
            {
              "name": "stage_freeze_input",
              "wire_type": "Union[VerifiedCampaignStageFreezeV1,CampaignStageFreezeV1]"
            },
            {
              "name": "run_permit_input",
              "wire_type": "Union[VerifiedCampaignStageRunPermitV1,CampaignStageRunPermitV1]"
            },
            {
              "name": "previous_envelope_input",
              "wire_type": "Optional[Union[VerifiedCampaignStageOutputEnvelopeV1,CampaignStageOutputEnvelopeV1]]"
            },
            {
              "name": "taskbook_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "stage_manifest_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "source_bundle",
              "wire_type": "tuple[tuple[PortableSourceRefV1,bytes],...]"
            },
            {
              "name": "reviewer_key_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "preparation_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "signing_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "artifact_bundle",
              "wire_type": "tuple[bytes,...]"
            }
          ],
          "returns": "VerifiedCampaignStageOutputEnvelopeV1",
          "raw_hydration_allowed": false,
          "semantics": "first join the exact out-of-band live trust-anchor to the pinned checkpoint/root and campaign registry/key bytes; recursively verify live-or-frozen stage/permit/previous inputs, then verify root/statement/two signatures and artifact bytes; caller re-key self-bootstrap is forbidden"
        },
        {
          "name": "issue_v3m0_checkpoint_envelope_v1",
          "visibility": "public",
          "args": [
            {
              "name": "trust_anchor",
              "wire_type": "VerifiedCampaignCheckpointTrustAnchorV1"
            },
            {
              "name": "parent",
              "wire_type": "VerifiedParentFreezeV3"
            },
            {
              "name": "run_outcome",
              "wire_type": "VerifiedV3M0RunOutcomeV3"
            },
            {
              "name": "stage_freeze",
              "wire_type": "VerifiedCampaignStageFreezeV1"
            },
            {
              "name": "run_permit",
              "wire_type": "VerifiedCampaignStageRunPermitV1"
            },
            {
              "name": "artifact_bundle",
              "wire_type": "tuple[bytes,bytes,bytes,bytes]"
            },
            {
              "name": "review_signatures",
              "wire_type": "tuple[PortableEnvelopeSignatureV1,PortableEnvelopeSignatureV1]"
            }
          ],
          "returns": "VerifiedV3M0CheckpointEnvelopeV1",
          "raw_hydration_allowed": false,
          "semantics": "require the same out-of-band live trust-anchor sealed into stage/permit, reject review signatures outside its pinned campaign registry, then specialize the generic envelope with full Parent/run bodies and four exact leaves"
        },
        {
          "name": "verify_v3m0_checkpoint_envelope_v1",
          "visibility": "public",
          "args": [
            {
              "name": "trust_anchor",
              "wire_type": "VerifiedCampaignCheckpointTrustAnchorV1"
            },
            {
              "name": "checkpoint",
              "wire_type": "V3M0CheckpointEnvelopeV1"
            },
            {
              "name": "stage_freeze_input",
              "wire_type": "Union[VerifiedCampaignStageFreezeV1,CampaignStageFreezeV1]"
            },
            {
              "name": "run_permit_input",
              "wire_type": "Union[VerifiedCampaignStageRunPermitV1,CampaignStageRunPermitV1]"
            },
            {
              "name": "parent_input",
              "wire_type": "Union[VerifiedParentFreezeV3,ParentFreezeV3Manifest]"
            },
            {
              "name": "previous_envelope_input",
              "wire_type": "Optional[Union[VerifiedCampaignStageOutputEnvelopeV1,CampaignStageOutputEnvelopeV1]]"
            },
            {
              "name": "taskbook_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "stage_manifest_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "source_bundle",
              "wire_type": "tuple[tuple[PortableSourceRefV1,bytes],...]"
            },
            {
              "name": "reviewer_key_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "preparation_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "signing_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "old_s_source_bundle",
              "wire_type": "tuple[tuple[SignedSourceRefV2,bytes],...]"
            },
            {
              "name": "old_s_reviewer_key_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "old_s_signing_literal_source_bytes",
              "wire_type": "bytes"
            },
            {
              "name": "artifact_bundle",
              "wire_type": "tuple[bytes,bytes,bytes,bytes]"
            }
          ],
          "returns": "VerifiedV3M0CheckpointEnvelopeV1",
          "raw_hydration_allowed": false,
          "semantics": "first require the exact out-of-band live trust-anchor and join its checkpoint/root plus campaign/Parent key-source pins; detached cross-machine verification then recursively checks frozen-or-live stage/permit/Parent inputs, exact campaign and old-S source/key/literal bytes, portable root, full generic envelope, run joins, artifacts and state ceiling without repository, Git, imported trust literals or caller re-key bootstrap"
        }
      ],
      "opaque_wrappers": [
        "VerifiedCampaignCheckpointTrustAnchorV1",
        "VerifiedCampaignStageFreezeV1",
        "VerifiedCampaignStageRunPermitV1",
        "VerifiedCampaignStageOutputEnvelopeV1",
        "VerifiedV3M0CheckpointEnvelopeV1"
      ],
      "typed_failures": [
        "TRUST_ANCHOR_INVALID",
        "PREVIOUS_ENVELOPE_INVALID",
        "TASKBOOK_DRIFT",
        "MANIFEST_DRIFT",
        "SOURCE_CLOSURE_DRIFT",
        "PREPARATION_EPOCH_INVALID",
        "SIGNING_EPOCH_INVALID",
        "REVIEW_RECEIPT_INVALID",
        "SIGNING_DIFF_INVALID",
        "CROSS_STAGE",
        "CROSS_FAMILY",
        "ARTIFACT_MISSING",
        "ARTIFACT_SHA_MISMATCH",
        "STATE_NOT_TASKBOOK_ALLOWED",
        "NEXT_STAGE_CEILING_EXCEEDED",
        "UNTRUSTED_REVIEWER_KEY",
        "SIGNATURE_INVALID"
      ],
      "invariants": [
        "generic reviewer primitives are self-contained",
        "every B10 public API requires the exact out-of-band live trust-anchor as its first argument",
        "no public issuer, raw hydration, serialized anchor, caller key registry or envelope content can mint or rotate the trust-anchor",
        "portable verification accepts live authority wrappers or recursively verified frozen bodies for stage, permit and Parent",
        "detached checkpoint verification carries old-S signed source bytes, reviewer-key source bytes and signing-literal source bytes explicitly",
        "portable verifier is idempotent; duplicate consumption belongs to next-stage issuer"
      ],
      "reviewer_primitives_owner": "rulespace_v3.campaign_stage_authority_v1"
    }
  },
  "import_dag": {
    "rulespace_v3.parent_v3_contracts": [
      "rulespace_v3.ablation",
      "rulespace_v3.c19_refreeze_v2",
      "rulespace_v3.evidence",
      "rulespace_v3.factory",
      "rulespace_v3.grids",
      "rulespace_v3.metric"
    ],
    "rulespace_v3.parent_candidate_v3": [
      "rulespace_v3.evidence",
      "rulespace_v3.parent_candidate_v2",
      "rulespace_v3.parent_freeze",
      "rulespace_v3.parent_freeze_v2",
      "rulespace_v3.parent_v2_contracts",
      "rulespace_v3.parent_v3_contracts"
    ],
    "rulespace_v3.parent_freeze_v3_contracts": [
      "rulespace_v3.evidence",
      "rulespace_v3.parent_candidate_v3"
    ],
    "rulespace_v3.parent_signing_audit_v1": [
      "rulespace_v3.evidence",
      "rulespace_v3.parent_candidate_v3",
      "rulespace_v3.parent_freeze_v3_contracts",
      "rulespace_v3.parent_v3_contracts"
    ],
    "rulespace_v3.parent_freeze_v3": [
      "rulespace_v3.evidence",
      "rulespace_v3.parent_candidate_v3",
      "rulespace_v3.parent_freeze_v3_contracts",
      "rulespace_v3.parent_signing_audit_v1"
    ],
    "rulespace_v3.parent_authority_v3": [
      "rulespace_v3.evidence",
      "rulespace_v3.parent_candidate_v3",
      "rulespace_v3.parent_freeze_v3",
      "rulespace_v3.parent_freeze_v3_contracts",
      "rulespace_v3.parent_reviewer_keys_v1",
      "rulespace_v3.parent_signing_audit_v1",
      "rulespace_v3.parent_signing_literals_v1"
    ],
    "rulespace_v3.task11_runner": [
      "rulespace_v3.ablation",
      "rulespace_v3.bridge",
      "rulespace_v3.calibration_authority",
      "rulespace_v3.certificate",
      "rulespace_v3.contracts",
      "rulespace_v3.current_window_replay",
      "rulespace_v3.dynamics",
      "rulespace_v3.evidence",
      "rulespace_v3.factory",
      "rulespace_v3.frozen_call_graph",
      "rulespace_v3.grids",
      "rulespace_v3.metric",
      "rulespace_v3.parent_freeze",
      "rulespace_v3.prestructure",
      "rulespace_v3.qualification",
      "rulespace_v3.registry",
      "rulespace_v3.replay_scope",
      "rulespace_v3.response",
      "rulespace_v3.runtime",
      "rulespace_v3.structure",
      "rulespace_v3.task8_control_replay",
      "rulespace_v3.thresholds",
      "rulespace_v3.window"
    ],
    "rulespace_v3.application_authority_v3": [
      "rulespace_v3.parent_authority_v3",
      "rulespace_v3.parent_candidate_v3",
      "rulespace_v3.parent_v3_contracts",
      "rulespace_v3.calibration_authority",
      "rulespace_v3.parent_freeze",
      "rulespace_v3.task8_control_replay",
      "rulespace_v3.task11_runner"
    ],
    "rulespace_v3.application_materialization_v3": [
      "rulespace_v3.application_authority_v3",
      "rulespace_v3.parent_authority_v3",
      "rulespace_v3.factory",
      "rulespace_v3.ablation",
      "rulespace_v3.pair_snapshot",
      "rulespace_v3.trace"
    ],
    "rulespace_v3.transition_authority_v3": [
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.dynamics",
      "rulespace_v3.prestructure"
    ],
    "rulespace_v3.metric_support_authority_v1": [
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.parent_v3_contracts",
      "rulespace_v3.metric"
    ],
    "rulespace_v3.runtime_grids_v3": [
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.transition_authority_v3",
      "rulespace_v3.metric_support_authority_v1",
      "rulespace_v3.grids"
    ],
    "rulespace_v3.certificate_v3": [
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.transition_authority_v3",
      "rulespace_v3.metric_support_authority_v1",
      "rulespace_v3.runtime_grids_v3",
      "rulespace_v3.certificate",
      "rulespace_v3.structure",
      "rulespace_v3.metric",
      "rulespace_v3.bridge",
      "rulespace_v3.laurent",
      "rulespace_v3.spectral",
      "rulespace_v3.fp64_protocol"
    ],
    "rulespace_v3.application_response_v3": [
      "rulespace_v3.application_authority_v3",
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.runtime_grids_v3",
      "rulespace_v3.certificate_v3",
      "rulespace_v3.response"
    ],
    "rulespace_v3.control_application_evidence_v3": [
      "rulespace_v3.application_authority_v3",
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.transition_authority_v3",
      "rulespace_v3.metric_support_authority_v1",
      "rulespace_v3.runtime_grids_v3",
      "rulespace_v3.certificate_v3",
      "rulespace_v3.application_response_v3"
    ],
    "rulespace_v3.blocks": [
      "rulespace_v3.control_application_evidence_v3",
      "rulespace_v3.calibration_authority",
      "rulespace_v3.response"
    ],
    "rulespace_v3.control_geometry_evaluation_v3": [
      "rulespace_v3.control_application_evidence_v3",
      "rulespace_v3.blocks",
      "rulespace_v3.parent_v3_contracts",
      "rulespace_v3.geometry_protocol_v3"
    ],
    "rulespace_v3.state": [
      "rulespace_v3.contracts"
    ],
    "rulespace_v3.runtime_v3": [
      "rulespace_v3.parent_authority_v3",
      "rulespace_v3.application_authority_v3",
      "rulespace_v3.application_materialization_v3",
      "rulespace_v3.transition_authority_v3",
      "rulespace_v3.metric_support_authority_v1",
      "rulespace_v3.runtime_grids_v3",
      "rulespace_v3.certificate_v3",
      "rulespace_v3.application_response_v3",
      "rulespace_v3.control_application_evidence_v3",
      "rulespace_v3.blocks",
      "rulespace_v3.control_geometry_evaluation_v3",
      "rulespace_v3.state",
      "rulespace_v3.causal",
      "rulespace_v3.geometry",
      "rulespace_v3.sigma",
      "rulespace_v3.series_control"
    ],
    "rulespace_v3.campaign_stage_authority_v1": [
      "rulespace_v3.evidence"
    ],
    "rulespace_v3.checkpoint_envelope_v1": [
      "rulespace_v3.campaign_stage_authority_v1",
      "rulespace_v3.parent_authority_v3",
      "rulespace_v3.parent_freeze_v3_contracts",
      "rulespace_v3.runtime_v3"
    ],
    "experiments.v3m0_preflight": [
      "rulespace_v3.parent_authority_v3",
      "rulespace_v3.runtime_v3",
      "rulespace_v3.checkpoint_envelope_v1"
    ],
    "experiments.v3m0_controls": [
      "rulespace_v3.runtime_v3",
      "rulespace_v3.checkpoint_envelope_v1"
    ]
  },
  "import_dag_external_leaves": [
    "rulespace_v3.ablation",
    "rulespace_v3.bridge",
    "rulespace_v3.c19_refreeze_v2",
    "rulespace_v3.calibration_authority",
    "rulespace_v3.causal",
    "rulespace_v3.certificate",
    "rulespace_v3.contracts",
    "rulespace_v3.current_window_replay",
    "rulespace_v3.dynamics",
    "rulespace_v3.evidence",
    "rulespace_v3.factory",
    "rulespace_v3.fp64_protocol",
    "rulespace_v3.frozen_call_graph",
    "rulespace_v3.geometry",
    "rulespace_v3.geometry_protocol_v3",
    "rulespace_v3.grids",
    "rulespace_v3.laurent",
    "rulespace_v3.metric",
    "rulespace_v3.pair_snapshot",
    "rulespace_v3.parent_candidate_v2",
    "rulespace_v3.parent_freeze",
    "rulespace_v3.parent_freeze_v2",
    "rulespace_v3.parent_reviewer_keys_v1",
    "rulespace_v3.parent_signing_literals_v1",
    "rulespace_v3.parent_v2_contracts",
    "rulespace_v3.prestructure",
    "rulespace_v3.qualification",
    "rulespace_v3.registry",
    "rulespace_v3.replay_scope",
    "rulespace_v3.response",
    "rulespace_v3.runtime",
    "rulespace_v3.series_control",
    "rulespace_v3.sigma",
    "rulespace_v3.spectral",
    "rulespace_v3.structure",
    "rulespace_v3.task8_control_replay",
    "rulespace_v3.thresholds",
    "rulespace_v3.trace",
    "rulespace_v3.window"
  ],
  "import_dag_ast_pinned_nodes": [
    "rulespace_v3.parent_signing_audit_v1",
    "rulespace_v3.parent_freeze_v3",
    "rulespace_v3.parent_authority_v3",
    "rulespace_v3.task11_runner"
  ],
  "c19_freeze": {
    "control_case_id": "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
    "claim_ceiling": "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY",
    "causal_contrast_role": "NULL_INTERVENTION_INVARIANCE_CONTROL",
    "physical_anchor_eligibility": "INELIGIBLE",
    "family_eligibility": "INELIGIBLE",
    "state_schema_id": "v3m0.c19-real-canonical-state.v2",
    "channel_count": 20,
    "spatial_shape": [
      8
    ],
    "actual_active_step_count": 50,
    "matched_active_step_count": 30,
    "actual_layer_slot_count": 50,
    "matched_layer_slot_count": 50,
    "actual_primitive_count": 50,
    "matched_primitive_count": 50,
    "matched_neutral_identity_count": 20,
    "source_selector": "B_plus",
    "readout_selector": "P",
    "state_metric": "I20",
    "source_trial_vectors": "I10"
  },
  "grid_freeze": {
    "response": "directional-momentum-shell-path-v1; exact one C19 directional node",
    "dynamics_zero": "denominators=(1,); indices=((0,),); support=((0,),)",
    "bridge_zero": "denominators=(8,); indices=((0,),); support=((0,),)",
    "metric_support": "constant-state-v1; I20; offsets=((0,),)",
    "grids_are_not_interchangeable": true,
    "caller_supplied_points_allowed": false
  },
  "response_chain": {
    "raw_layers": {
      "reference": [
        "EndpointReferenceSpec",
        "EndpointReferenceProjector",
        "EndpointReferenceAttemptAudit",
        "EndpointReferenceOutcome"
      ],
      "shell": [
        "EndpointShellSpec",
        "ShellPointAudit",
        "EndpointShellManifest",
        "ShellCandidatePointAttempt",
        "EndpointShellAttemptAudit",
        "EndpointShellOutcome"
      ],
      "paired": [
        "SourceReadoutBridgeMatrixAudit",
        "SourceReadoutBridgeAudit",
        "SourceReadoutResponse",
        "PairedFilteredResponse",
        "SourceReadoutBranchAttemptAudit",
        "PairedResponseAttemptAudit",
        "PairedResponseOutcome"
      ]
    },
    "opaque_outcomes": [
      "VerifiedEndpointReferenceOutcome",
      "VerifiedEndpointShellOutcome",
      "VerifiedPairedResponseOutcome"
    ],
    "selection_branch": "actual",
    "matched_reselection_allowed": false,
    "success_failure_xor": true,
    "half_pair_capability_allowed": false
  },
  "c19_geometry_boundary": {
    "claim_ceiling": "OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY",
    "causal_contrast_role": "NULL_INTERVENTION_INVARIANCE_CONTROL",
    "physical_anchor_eligibility": "INELIGIBLE",
    "family_eligibility": "INELIGIBLE",
    "pre_response_state": "NOT_EVALUATED_PRE_RESPONSE",
    "required_predicate_ids": [
      "complete-nonzero-gram-support-selection",
      "whitened-coisometry-or-incidence-range-preservation",
      "incidence-rank-six",
      "gauge-contained-in-incidence-kernel-dimension-four",
      "tt2-gauge4-row4-pairwise-orthogonal-complete-decomposition",
      "constraint-kernel-tt-plus-gauge-compatible-projector-and-metric",
      "actual-source-readout-share-endpoint-shell-and-finite-paired-response"
    ],
    "evaluation_requires_verified_response_blocks": true,
    "eligible_for_physical_or_family_claim": false
  },
  "v3m0_execution_freeze": {
    "parent_v3_replay_case_ids": [
      "C01",
      "C02",
      "C03",
      "C04",
      "C05",
      "C06",
      "C07",
      "C08",
      "C09",
      "C10",
      "C11",
      "C12",
      "C13",
      "C14",
      "C15",
      "C16",
      "C17",
      "C18",
      "C20"
    ],
    "c19_route": "CurrentApplicationAuthorityV3 only",
    "v2_opaque_authority_allowed": false,
    "representation_invariant_ids": [
      "I01",
      "I02",
      "I03",
      "I04",
      "I05",
      "I06",
      "I07",
      "I08",
      "I09"
    ],
    "typed_termination_routes": [
      [
        "C11:null",
        "activation",
        "RESPONSE_NULL"
      ],
      [
        "C11:grey",
        "activation",
        "RESPONSE_GREY"
      ],
      [
        "C11:signal",
        "success",
        null
      ],
      [
        "C13:both-zero",
        "activation",
        "RESPONSE_NULL"
      ],
      [
        "C14:endpoint-ambiguous",
        "endpoint_shell",
        "ENDPOINT_SHELL_AMBIGUOUS"
      ],
      [
        "C14:response-null",
        "activation",
        "RESPONSE_NULL"
      ],
      [
        "C14:trace-unclassified",
        "trace",
        "TRACE_UNCLASSIFIED"
      ],
      [
        "C14:unstable",
        "stability",
        "UNSTABLE"
      ]
    ],
    "scenario_item_tags": [
      "BLOCK_SUCCESS",
      "EXPECTED_TYPED_TERMINATION",
      "ANALYSIS_CONTROL"
    ],
    "denied_opaque_types": [
      "VerifiedParentFreeze",
      "VerifiedParentFreezeV2",
      "VerifiedWindowThresholdCalibration",
      "VerifiedCalibrationApplicationPermit",
      "VerifiedWindowThresholdCalibrationV2",
      "VerifiedCalibrationApplicationPermitV2",
      "VerifiedV3M0ApplicationScenarioMaterializationV2",
      "VerifiedApplicationScenarioResponseProtocolV2",
      "VerifiedApplicationPairedResponseOutcomeV2"
    ]
  },
  "artifact_contracts": [
    {
      "order": 0,
      "relative_path": "data/results/v3m0_parent_v3.json",
      "artifact_kind": "PARENT_V3_FREEZE",
      "artifact_schema_id": "v3m0.parent-freeze.v3"
    },
    {
      "order": 1,
      "relative_path": "data/results/v3m0_controls_v3.json",
      "artifact_kind": "V3M0_CONTROLS_RESULT",
      "artifact_schema_id": "v3m0.controls-result.v3"
    },
    {
      "order": 2,
      "relative_path": "data/results/v3m0_response_v3.json",
      "artifact_kind": "V3M0_RESPONSE_RESULT",
      "artifact_schema_id": "v3m0.response-result.v3"
    },
    {
      "order": 3,
      "relative_path": "data/runtime/v3m0_state.json",
      "artifact_kind": "V3M0_STATE_DECISION",
      "artifact_schema_id": "v3m0.state-decision.v3"
    }
  ],
  "state_ceiling_map": {
    "HALT-V3M0-FORMAL": "STOP",
    "HALT-V3M0-CONTROL": "STOP",
    "HALT-V3M0-IDENTIFIABILITY": "STOP",
    "HALT-V3M0-WINDOW": "STOP",
    "READY-V3-M1-ANCHOR-CERTIFICATION": "V3-M1"
  },
  "portable_trust_anchor_freeze": {
    "wrapper_type": "VerifiedCampaignCheckpointTrustAnchorV1",
    "canonical_owner": "rulespace_v3.campaign_stage_authority_v1",
    "provisioning": "OUT_OF_BAND_TRUST_STORE_ONLY",
    "public_issuer_exists": false,
    "raw_or_serialized_anchor_allowed": false,
    "caller_supplied_registry_or_key_bootstrap_allowed": false,
    "ordered_pins": [
      "anchor_profile_id",
      "stage_family_id",
      "trust_epoch_id",
      "trusted_checkpoint_or_genesis_sha",
      "trusted_previous_portable_envelope_sha",
      "campaign_reviewer_registry_sha",
      "campaign_reviewer_key_source_sha",
      "parent_reviewer_key_source_sha",
      "parent_signing_literal_source_sha"
    ],
    "verification_order": [
      "require exact live trust-anchor wrapper identity",
      "join stage family, trust epoch and pinned checkpoint/root",
      "join embedded campaign registry and key-source bytes to anchor pins",
      "join Parent old-S key/literal source bytes to anchor pins",
      "only then verify source closures, receipts and envelope signatures"
    ],
    "anchor_rotation": "out-of-band only after separately authenticated checkpoint approval; never from envelope contents",
    "wrong_anchor_failure": "TRUST_ANCHOR_INVALID",
    "rekeyed_self_bootstrap_failure": "UNTRUSTED_REVIEWER_KEY"
  },
  "portable_verifier_freeze": {
    "detached_cross_machine_supported": true,
    "repository_or_git_state_required": false,
    "out_of_band_live_trust_anchor_required": true,
    "stage_freeze_input_types": [
      "VerifiedCampaignStageFreezeV1",
      "CampaignStageFreezeV1"
    ],
    "run_permit_input_types": [
      "VerifiedCampaignStageRunPermitV1",
      "CampaignStageRunPermitV1"
    ],
    "parent_input_types": [
      "VerifiedParentFreezeV3",
      "ParentFreezeV3Manifest"
    ],
    "source_bundle_entry": "(signed ref, exact raw bytes) in manifest order",
    "old_s_inputs": [
      "old_s_source_bundle",
      "old_s_reviewer_key_source_bytes",
      "old_s_signing_literal_source_bytes"
    ],
    "detached_positive_route": "exact out-of-band live trust-anchor plus frozen stage/permit/Parent bodies and exact source, key, manifest, taskbook and artifact bytes verify without importing repository literals",
    "detached_death_cases": [
      "missing_trust_anchor",
      "wrong_trust_anchor",
      "caller_rekeyed_self_bootstrap",
      "missing_stage_freeze_body",
      "missing_run_permit_body",
      "missing_parent_body",
      "missing_source_bundle",
      "missing_reviewer_key_source_bytes",
      "missing_old_s_source_bundle",
      "missing_old_s_reviewer_key_source_bytes",
      "missing_old_s_signing_literal_source_bytes",
      "mutated_source_bytes",
      "mutated_key_bytes"
    ]
  },
  "portable_replay_semantics": "portable verification is idempotent; duplicate consumption is rejected only by the next-stage issuer against its fixed previous envelope root",
  "global_invariants": [
    "raw bodies are exact frozen data and are never capabilities",
    "every nested_record resolves to a complete ordered field_specs body",
    "opaque wrappers are minted only by their canonical owner after recursive live replay",
    "public APIs accept exact typed arguments and no caller roots branches grids thresholds observations or raw promotion",
    "one actual/matched construction and response pair is atomic; no half capability",
    "C19 is control-only/null-intervention/physical-ineligible/family-ineligible",
    "B0 issues no status, threshold, Parent, permit, certificate, response, evidence, block, run, or checkpoint"
  ]
}
```
<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->

## 8. 后续切片验收

B1–B10 各自落地时必须先用攻击测试得到 RED，再实现 canonical owner、唯一 closed issuer、
recursive verifier 与 opaque wrapper。实现不得通过修改本 B0 表来迁就代码 drift；任何 schema、
field order、literal、tuple cardinality、XOR、join、failure order 或 import edge 变化都须独立勘误
与复审。B10 完成、P/S 签发并有完整攻击回归之前，本文件不构成 production readiness 证据。
