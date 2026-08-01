# Parent-v3 至 GPU checkpoint 实施计划补遗

> **For agentic workers:** REQUIRED SUB-SKILLS: Use
> `superpowers:subagent-driven-development` task-by-task；每个实现切片严格
> RED→GREEN，并依次通过规格复审、代码质量复审与完成前验证。

**目标：** 修复 Parent-v3 签发根，完成 V3-M0 production authority 链；若且仅若逐级科学门
通过，再串行完成 V3-M1 物理正锚、V3-M2 family/Round 0、30 格 pilot、V3-M3 正式扫描
manifest 与 GPU preflight，并停在首个正式扫描 kernel 启动前。

**当前起点：** commit `99dac47`；状态 `HALT-V3M0-WINDOW`；
`READY-V3-M1-ANCHOR-CERTIFICATION` 未签发；当前 `rulespace_gpu.verify` 仅是 backend smoke，
不是 GPU science permit。

**架构：** authority/data flow 唯一为：

```text
P-epoch Parent candidate
  + dual signed review receipts
  + allowlisted S-epoch signing audit
→ VerifiedParentFreezeV3
→ CalibrationV3 → PermitV3 → MaterializationV3
→ actual/matched {TransitionV3, MetricSupportAttestation, BridgeGrid}
→ DynamicsGrid → DynamicsCertificateV3 × 2
→ actual endpoint/shell → atomic paired response
→ closed control evidence → blocks/三坐标/表示不变量
→ V3-M0 READY 或 exact HALT

V3-M0 READY
→ V3-M1 physical anchor PASS 或 exact HALT
→ 同一获批 family 的 V3-M2 Round 0 PASS 或 exact HALT
→ signed 30-grid permit → pilot discernibility PASS 或 exact HALT
→ separately frozen 10²–10³ scan manifest
→ manifest-bound CUDA fp64 preflight PASS
→ GPU checkpoint（停止；不启动正式 kernel）
```

任何 exact HALT 都是合法、诚实的阶段终点；不得改阈值、换 family、扩搜索预算或把工程烟测
改名为 science PASS。

---

## 共同执行规则

1. 工作树固定为 `.worktrees/v3m0-instrument`，分支 `v3m0-instrument`；保留用户改动。
2. Python 固定使用
   `/Users/prismer/workspace/science/ca-universe-lab/.venv/bin/python`。
3. 每个实现任务：先写缺失行为/攻击测试并看到预期 RED，再做最小 GREEN；不得先写 production
   code 后补测试。
4. 每个任务只由一个 implementer 修改；规格 reviewer 与质量 reviewer均只读，发现问题后由原
   implementer修复并重新复审。
5. authority wrapper 只用 module-private token、weak live registry、immutable seal 与 detached
   snapshots；禁止 raw hydration、promotion、resign、subclass 或 V1/V2 capability adapter。
6. raw inherited V2 records 只作为 Parent-v3 内部历史/构造材料；外层 Parent-v3 首次授权。
7. 每次提交前至少运行定向 tests、`ruff check`、`ruff format --check`、`git diff --check`。
8. 阶段完成前运行本计划“总验证矩阵”；昂贵 replay 只在对应 gate 需要时运行。
9. 形成真实 preparation commit `P` 前，所有 V3-M0 downstream code/docs/tests 必须完成；`S` 后
   不再提交代码再假称同一 Parent issuance 有效。
10. 运行产生的 result/runtime/figure 可以在已签发进程中写出；它们不回写 Parent root。

## 阶段状态与停止条件

| 阶段 | 唯一正向出口 | 失败出口 | 后续权限 |
|---|---|---|---|
| A–C Parent/V3-M0 | `READY-V3-M1-ANCHOR-CERTIFICATION` | 现有 V3-M0 typed HALT | 仅可进入 V3-M1 |
| D V3-M1 | `READY-V3-FAMILY-DESIGN` | `HALT-V3M1-NO-PHYSICAL-CAUSAL-ANCHOR` 或任务书冻结的 typed HALT | 仅可设计 family |
| E V3-M2 Round 0 | 任务书冻结的 Round 0 PASS | family-specific typed HALT | 仅可签 30 格 permit |
| F 30 格 pilot | pilot discernibility review PASS | pilot typed HALT | 仅可另行设计正式扫描 |
| G V3-M3 preflight | 任务书冻结的 GPU-ready state | preflight typed HALT | 到 checkpoint 后停止 |

后四阶段的 authoritative state literals 必须在各自任务书中先冻结；本计划不预签一个尚无任务书的
READY 字符串。

## 跨阶段 release-epoch 与可移植 handoff

Parent-v3 的 `S=HEAD` 只服务 V3-M0。V3-M0 运行后再提交任何 M1/M2/pilot/GPU code都会按设计
使 live Parent wrapper失效；本计划不把它伪装成仍然有效，也不重新 hydrate Parent。

跨阶段唯一合法交接为：

```text
clean S0 + live Parent-v3
→ V3-M0 run
→ 双 reviewer key 签名的 portable V3M0CheckpointEnvelope
→ 允许提交 envelope/results 与 V3-M1 code；Parent live authority到此失效

V3-M1 preparation/signing P1/S1
+ verified V3M0 checkpoint envelope
→ V3-M1 run → signed V3M1 checkpoint envelope

V3-M2 Round0 P2/S2 → signed Round0 envelope
pilot P3/S3          → signed pilot envelope
V3-M3 P4/S4          → signed GPU-preflight checkpoint envelope
```

每个 `Pₙ/Sₙ` 都有独立 taskbook/source closure/双 role receipts/strict diff audit，且只接受前一阶段
portable envelope；旧 live opaque wrapper不跨 epoch。portable verifier重验 immutable旧 S commit
blobs、旧 trusted reviewer keys、双 Ed25519 signatures、artifact bytes/root和 typed state。这个显式
export/import是新的 checkpoint authority，不是 Parent或其他 opaque capability 的 raw hydration。

为避免在 S0 后才发明交接协议，Phase B 必须在真实 Parent P 前实现并复审通用
`CampaignStageFreezeV1` 与 `V3M0CheckpointEnvelopeV1` schema/verifier/exporter；后续阶段只能为各自
taskbook增加 typed manifest/body，不得修改已签 handoff语义。

---

## Phase A：P-epoch Parent-v3 raw root

### Task A1：Parent-v2 raw handoff 与 P-blob reader

**Files:**

- Modify: `rulespace_v3/parent_freeze_v2.py`
- Modify: `rulespace_v3/parent_v3_contracts.py`
- Modify: `tests/test_v3m0_parent_freeze_v2.py`
- Modify: `tests/test_v3m0_parent_v3_contracts.py`

**RED：**

- public raw handoff API 缺失；
- C19 P-epoch replay 缺失；
- live doc mutation 会改变 current application root；
- caller bytes/path、symlink/tree mode、wrong Git SHA type未拒绝。

**GREEN：**

- 新增 `build/verify_reviewed_current_application_authorities_v2_raw()`；
- 新增 private P-blob reader 与
  `_replay_c19_current_application_authority_v3_at_preparation_commit(P)`；
- public live raw builder保持兼容，Parent candidate只调用 P-epoch入口；
- fresh replay证明 doc worktree mutation不改变 P-epoch application root。

**Verify:**

```bash
.venv/bin/python -m pytest -q \
  tests/test_v3m0_parent_freeze_v2.py \
  tests/test_v3m0_parent_v3_contracts.py
```

**Commit:** `feat(v3m0): add P-epoch raw authority replay`

### Task A2：ParentFreezeCandidateV3 exact manifest

**Files:**

- Create: `rulespace_v3/parent_candidate_v3.py`
- Create: `tests/test_v3m0_parent_candidate_v3.py`
- Modify: `rulespace_v3/__init__.py` only if an existing package export contract requires it

**RED attacks:**

- raw dict/subclass/unknown field/re-sign；
- C19 old/new 同时 current、旧 C19 未进 historical、new C19 appended而非原位替换；
- old/new success scenario ID 同时存在或 ordinal 漂移；
- V2 opaque Parent adapter；
- source closure 漏路径、乱序、mode/symlink、worktree fallback、untracked dependency；
- DRAFT→SIGNED simulation 导致 candidate/source root漂移。

**GREEN：**

- 实现 `ApplicationSupersessionV3`、`ParentFreezeCandidateV3Manifest` 与 canonical owners；
- current tagged registry 在 historical C19 ordinal原位 supersede；
- 从 P tree 机械形成完整 explicit source closure；
- fresh-interpreter audit hook证明 repository-local imports/reads均被 closure覆盖；
- public builder/verifier只返回 authority-neutral raw dataclass。

**Verify:**

```bash
.venv/bin/python -m pytest -q tests/test_v3m0_parent_candidate_v3.py
```

**Commit:** `feat(v3m0): build Parent-v3 P-epoch candidate`

### Task A3：签发 raw records、reviewer registry 与 literals

**Files:**

- Create: `rulespace_v3/parent_freeze_v3_contracts.py`
- Create: `rulespace_v3/parent_reviewer_keys_v1.py`
- Create: `rulespace_v3/parent_signing_literals_v1.py`
- Create: `tests/test_v3m0_parent_freeze_v3_contracts.py`

**RED attacks:** exact type/field closure、bad role/scope/order、wrong P/S SHA kind、duplicate reviewer
key/identity、non-canonical Ed25519 public-key text/wire blob/fingerprint、bad canonical JSON、oversized
receipt、bad signature/self-hash、tag/root owner drift。

**GREEN：** 实现 `SignedSourceRefV2`、`ParentReviewReceiptV1`、
`ParentSigningAuditV1`、`ParentFreezeV3Manifest` 的 pure contracts/payload/verifiers；keys/literals仍是
P 前占位，不签发 capability。`reviewer_key_id` 严格采用设计冻结的 OpenSSH
SHA-256 fingerprint：解码 canonical `ssh-ed25519 <base64>` wire blob后做 SHA-256、base64
去 padding并加 `SHA256:` 前缀；golden test 必须与 `ssh-keygen -lf` 一致。

**Commit:** `feat(v3m0): freeze Parent-v3 signing records`

### Task A4：strict P..S signing audit

**Files:**

- Create: `rulespace_v3/parent_signing_audit_v1.py`
- Create: `tests/test_v3m0_parent_signing_audit_v1.py`

**RED attacks:** dirty/untracked/conflict/submodule、merge S、wrong `S^`、rename/copy/mode drift、
wrong status transform、receipt exists in P、missing/extra S path、literal AST drift、bad Ed25519 signature、
candidate/live closure混用、HEAD/source ABA visible at snapshots。

**GREEN：** 在 temporary Git fixtures 中重放 immutable P/S blobs、canonical tree diff、五个 literal
RHS transform、四个 full status lines、两份 canonical signed receipts；成功结果只产生 private audit
capability，未签 Parent。

**Commit:** `feat(v3m0): audit Parent-v3 signing commits`

### Task A5：opaque Parent-v3 authority facade skeleton

**Files:**

- Create: `rulespace_v3/parent_freeze_v3.py`
- Create: `rulespace_v3/parent_authority_v3.py`
- Create: `tests/test_v3m0_parent_authority_v3.py`
- Create: `tests/test_v3m0_parent_v3_import_dag.py`

**RED attacks:** public constructor/hydrator/promoter、raw/V1/V2 adapter、object-new、fake token、dead
registry、seal/body mutation、caller P/S/root、lazy import unreviewed code、HEAD/protected path change after
issuance。

**GREEN：** 实现只读 readiness audit、`ParentV3IssuanceBlocked`、opaque wrapper/registry/seal与
唯一零参 issuer的 closed skeleton；真实仓库因尚无 P/S/downstream closure必须 typed blocked。
temporary fixture只验证 raw signing-audit→wrapper primitives，不宣称 full production issuer READY。
final zero-arg issuer、import DAG与完整 source closure在 B10（所有 downstream files存在后）闭合。

**Commit:** `feat(v3m0): close Parent-v3 authority facade`

---

## Phase B：Parent-v3 downstream production chain

### Task B0：冻结 downstream exact schemas 与 module DAG

**Files:**

- Create: `docsv3/v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md`
- Create: `tests/test_v3m0_parent_v3_downstream_contracts.py`

在代码前冻结每个 raw body的 exact fields/schema、唯一 issuer API、opaque wrapper、branch/root join、
canonical owner、typed failure与无环 import DAG。必须覆盖 calibration、permit、materialization、
transition、metric attestation、runtime grids、certificate、response、closed evidence、portable
checkpoint envelope与通用 campaign-stage freeze。独立规格复审 READY 后提交。

**Commit:** `docs(v3): freeze Parent-v3 downstream authority chain`

### Task B1：WindowThresholdCalibrationV3 与 PermitV3

**Files:**

- Create: `rulespace_v3/application_authority_v3.py`
- Create: `tests/test_v3m0_application_authority_v3.py`

**RED：** V2 calibration/permit、cross-Parent roots、copied thresholds、caller observations、missing
C01–C03/Task11 replay、window unresolved仍签 permit。

**GREEN：** 从 live Parent-v3 current registry真实重放 calibration controls，产生
`VerifiedWindowThresholdCalibrationV3`；只有同根且 window resolved才产生
`VerifiedCalibrationApplicationPermitV3`。不改任何冻结 threshold。

**Commit:** `feat(v3m0): issue Parent-v3 calibration permits`

### Task B2：ApplicationScenarioMaterializationV3

**Files:**

- Create: `rulespace_v3/application_materialization_v3.py`
- Create: `tests/test_v3m0_application_materialization_v3.py`

**RED：** historical Parent query、V2 adapter、caller recipe/factory、C19 4-channel、删 slot、30 primitive
matched branch、cross-root/branch、raw hydration。

**GREEN：** 从 Parent→calibration→permit 的 exact C19 current body直接 materialize两支 live
`VerifiedFactory`；slot/primitive `50/50`，active `50/30`，20 个原位 `neutral_identity`，共同
I20/B+/P/I10 wire。

**Commit:** `feat(v3m0): materialize C19 Parent-v3 factories`

### Task B3：same-branch TransitionV3

**Files:**

- Create: `rulespace_v3/transition_authority_v3.py`
- Create: `tests/test_v3m0_transition_authority_v3.py`

从 materialization branch 的真实 executor测量 full-state transition与 signed support；禁止旧
`VerifiedPrestructureAuthority`、旧 `VerifiedTransition`、analytic symbol代测量、FFT/per-k
projector。actual/matched分支必须共享 protocol而不共享结果 capability。

**Commit:** `feat(v3m0): measure Parent-v3 transitions`

### Task B4：metric-support attestation

**Files:**

- Create: `rulespace_v3/metric_support_authority_v1.py`
- Create: `tests/test_v3m0_metric_support_authority_v1.py`

从同一 Parent/materialization/factory branch重建 exact I20、`((0,),)` support 与 attestation；拒绝
raw witness/support/grid、历史 prestructure、cross-branch/root、dead registry与后置 certificate
回流。

**Commit:** `feat(v3m0): attest Parent-v3 metric support`

### Task B5：Bridge/Dynamics runtime grids

**Files:**

- Create: `rulespace_v3/runtime_grids_v3.py`
- Create: `tests/test_v3m0_runtime_grids_v3.py`

Bridge grid只从 live factory support派生；Dynamics grid只从同支 TransitionV3 + metric attestation
+ Parent protocol派生。C19 exact zero-support必须得到 singleton origin；任一非零 support、caller
points、三类 manifest互换均拒绝。

**Commit:** `feat(v3m0): derive Parent-v3 runtime grids`

### Task B6：DynamicsCertificateV3

**Files:**

- Create: `rulespace_v3/certificate_v3.py`
- Create: `tests/test_v3m0_certificate_v3.py`

递归绑定 Parent/materialization/factory/transition/metric/grids/full-state bridge、Laurent residual、
full-64 spectral margin、fp64 symplectic/unitary error。复用纯数值核，不接受任何旧 opaque authority。
冻结门 `≤1e-12` 的项必须从 raw quantities重算。

**Commit:** `feat(v3m0): certify Parent-v3 dynamics`

### Task B7：atomic paired response

**Files:**

- Create: `rulespace_v3/application_response_v3.py`
- Create: `tests/test_v3m0_application_response_v3.py`

只在 actual certificate上选 endpoint reference/shell；matched不得重寻 shell。两支共享 exact
scenario/run/basis/Response grid/Bridge grid/Fejér order；任何一支失败不产生 half-pair capability。

**Commit:** `feat(v3m0): issue Parent-v3 paired responses`

### Task B8：closed control evidence 与 permitted blocks

**Files:**

- Create: `rulespace_v3/control_application_evidence_v3.py`
- Create: `tests/test_v3m0_control_application_evidence_v3.py`
- Modify: `rulespace_v3/blocks.py`
- Modify: `tests/test_v3m0_response_block.py`

issuer内部重验全 live chain后才签 `VerifiedV3M0ControlApplicationEvidence`；C19 geometry七项
prerequisites只有此后才从 `NOT_EVALUATED_PRE_RESPONSE` 进入 observed evaluation。C19 永远
control-only、null-intervention、anchor/family ineligible。

**Commit:** `feat(v3m0): close Parent-v3 control evidence`

### Task B9：V3-M0 总装

**Files:**

- Create: `rulespace_v3/runtime_v3.py`
- Create: `tests/test_v3m0_runtime_v3.py`
- Modify: `experiments/v3m0_preflight.py`
- Modify: `experiments/v3m0_controls.py`
- Modify: `rulespace_v3/state.py`
- Modify: `tests/test_v3m0_state_core.py`

将 C01–C20、I01–I09、typed expected terminations、causal/geometry/sigma、representation invariants
和 block success artifacts总装到一次 run。最终 state只能由 opaque capabilities与原始量重算；
缺 required block按 manifest顺序聚合全部 reason。

**Commit:** `feat(v3m0): assemble Parent-v3 instrument runtime`

### Task B10：portable checkpoint、通用 stage freeze 与 final Parent issuer

**Files:**

- Create: `rulespace_v3/campaign_stage_authority_v1.py`
- Create: `rulespace_v3/checkpoint_envelope_v1.py`
- Create: `tests/test_v3m0_campaign_stage_authority_v1.py`
- Create: `tests/test_v3m0_checkpoint_envelope_v1.py`
- Modify: `rulespace_v3/parent_freeze_v3.py`
- Modify: `rulespace_v3/parent_authority_v3.py`
- Modify: `tests/test_v3m0_parent_authority_v3.py`
- Modify: `tests/test_v3m0_parent_v3_import_dag.py`

先冻结并 TDD：

- `V3M0CheckpointEnvelopeV1` exact artifact list/root、Parent/S0/source closure、typed state、next-stage
  ceiling、双 reviewer-key signatures与portable verifier；
- `CampaignStageFreezeV1` 的 previous-envelope root、taskbook/manifest/source closure、Pₙ/Sₙ、双
  receipts、strict diff、opaque run permit与portable output envelope共同字段；
- wrong old S/key/signature/artifact/state、cross-stage/cross-family、replayed envelope、raw old
  capability、missing artifact、post-sign source drift攻击。

随后把 B0–B10全部 downstream modules纳入 Parent source/import closure，完成 final zero-arg
`issue_v3m0_parent_freeze_v3()` 与 fresh-interpreter import-DAG tests。此后才允许进入 C1。

**Commit:** `feat(v3m0): close portable stage handoff and Parent issuer`

---

## Phase C：真实 P/S 与 V3-M0 gate

### Task C1：preparation readiness 与 semantic-state closure

**Files:**

- Modify: 四份 mandatory signed-source docs
- Modify: `docsv3/README.md`
- Modify: `rulespace_v3/parent_reviewer_keys_v1.py`
- Modify: `rulespace_v3/parent_signing_literals_v1.py` only to restore exact P placeholders if needed
- Create/Modify: focused source-closure/readiness tests

运行全部 V3-M0 suites；修正文档正文为
`IMPLEMENTED / REVIEW PENDING / NOT ISSUED`。在 P 前先指定两名不同 role reviewer；每名 reviewer
各自在自己的 custody boundary 内生成并保管一把 Ed25519 private key，只把 public key与
fingerprint交给 C1 implementer写入 P registry。P/S assembler不得生成、接收或读取两把 private
keys。所有实现/测试/doc body稳定后形成 clean preparation commit `P`。

**Commit:** `chore(v3m0): prepare Parent-v3 signing root`

### Task C2：双独立复审与 signing commit S

1. 两个已预注册 key 的 reviewer分别审 mathematics/evidence 与 authority/boundary；二者读取同一
   P candidate/path closure，输出 PASS 或阻断；
2. 任一 reviewer要求 body change：回到 C1，产生新 P，旧 reviews/keys签名全部废弃；
3. 两个 PASS各自用预注册 private key签 canonical receipt statement；
4. 构造两份 receipt JSON，计算 doc/receipt literals；
5. 只做四个 exact status transforms、两 receipt新增、五个 literal RHS注入；
6. 形成 single-parent signing commit `S`；
7. 在 clean S运行 zero-arg issuer与 strict internal audit。

**Commit:** `chore(v3m0): sign Parent-v3 authority`

### Task C3：执行 V3-M0

在同一个已签发 process中运行 full orchestrator并原子写：

```text
data/results/v3m0_parent_v3.json
data/results/v3m0_controls_v3.json
data/results/v3m0_response_v3.json
data/runtime/v3m0_state.json
visualizations/figs/v3m0_*.png
```

然后从 raw JSON独立复核 state：

- 无论 READY/HALT，都从 immutable S0 root与 exact artifacts构造 checkpoint statement，由两名
  registered reviewers独立重算后各自签名，输出 portable `V3M0CheckpointEnvelopeV1`；
- 若为 typed HALT：停止，不进入 V3-M1；输出 first undefined、证据 root 与最短修复边界；
- 只有 portable envelope 验证为
  `READY-V3-M1-ANCHOR-CERTIFICATION` 才允许提交后续 D 阶段文件；该提交明确终止 live Parent
  capability，D 阶段只消费 envelope。

---

## Phase D：V3-M1 旧锚与物理正锚

### Task D1：先冻结任务书与预注册

仅在 C3 READY 后创建并独立复审：

- `docsv3/v3-任务书-V3M1-旧锚认证与物理正锚.md`
- `docsv3/v3-预注册-V3M1-锚认证-2026-08-01.md`
- `docsv3/v3-实施计划-V3M1-锚认证-2026-08-01.md`

任务书必须冻结 target-blind旧资产 SHA/顺序、R30/R23/R25 typed adapters、有限正锚清单、运行
预算、全部正锚谓词与 exact HALT。禁止看结果后新增候选。

### Task D2：实现 adapter authority 与 anchor certificate

**Planned files（D1 taskbook只能收窄或版本化，不能静默改名）：**

- `rulespace_v3/v3m1_anchor_authority.py`
- `rulespace_v3/v3m1_anchor_materialization.py`
- `rulespace_v3/v3m1_anchor_certificate.py`
- `tests/test_v3m1_anchor_authority.py`
- `tests/test_v3m1_anchor_materialization.py`
- `tests/test_v3m1_anchor_certificate.py`

先 RED 覆盖 raw result/V2 wrapper/cross-envelope/old-S/stage-root splice/selector drift/单支运行/
缺闭环门；再实现同一 paired interface下的 actual/ablated full-source运行与 physical-anchor
certificate。

必须先实现不可绕过的 **pre-run committed authority**：

```text
VerifiedV3M0CheckpointEnvelopeV1
+ VerifiedCampaignStageFreezeV1 over frozen V3-M1 asset registry/taskbook root
→ VerifiedV3M1AnchorRunPermit
→ VerifiedV3M1AnchorMaterialization
→ exact paired run spec capability
→ 才能调用 actual/ablated executor
```

permit必须绑定有限 target-blind资产顺序、adapter/source/selector/shell/grid/threshold roots、预算、
两支 factory与output schema；materialization内部重验并关闭 caller factory/run-spec输入。攻击测试
必须证明无 permit、raw permit、cross-Parent、run后补签、改 grid/shell/selector或只运行一支均在
kernel入口前拒绝。

### Task D3：有限重测与裁定

D1/D2 code/docs/tests稳定后形成 V3-M1 `P1`，双复审后以 strict `S1` 签发
`VerifiedCampaignStageFreezeV1` 与 `VerifiedV3M1AnchorRunPermit`；只有 clean S1 process可执行。
按冻结顺序运行旧锚与正锚；CPU replay可并行，数值 kernel在 frozen parity通过后可用 GPU，
但 GPU加速不改变 evidence authority。若没有至少一个
`PHYSICAL-CAUSAL-ANCHOR-PASS`，签 exact HALT并停止；否则签
`READY-V3-FAMILY-DESIGN`。两种结果都生成双签 portable V3-M1 checkpoint envelope；只有 READY
envelope可被 E 阶段 `P2/S2` 消费。

---

## Phase E：V3-M2 family 与 Round 0

### Task E1：路线比较与 family 任务书

仅在 D3 READY 后，由数学/计算物理/authority 三路独立评审至少比较：

1. 受控 defect classical-symplectic 插值；
2. exact syzygy仅作目标端点的秩受限 Hamiltonian；
3. 第一阶 unitary QCA。

随后冻结：

- `docsv3/v3-任务书-V3M2-可识别局域族与Round0.md`
- `docsv3/v3-预注册-V3M2-Round0-2026-08-01.md`
- `docsv3/v3-实施计划-V3M2-Round0-2026-08-01.md`

获批 family 必须满足用户已冻结的最低合同：q=0…4 同一状态空间；真实
`realspace_step_factory`；明确局域 shear且 support radius与 L 无关；fp64酉性/辛性误差
`≤1e-12`；无逐-k/全局 FFT projector time step；由 actual Floquet shell冻结重调参；运行后测量
`ε_geo` 与 `σ=(α,A)`，不得把目标方程逐项硬编码成整族 exact identity。

### Task E2：实现 family 与 Round 0 audit

**Planned files：**

- `rulespace_v3/v3m2_family_contracts.py`
- `rulespace_v3/v3m2_family_authority.py`
- `rulespace_v3/v3m2_round0.py`
- `rulespace_gpu/v3m2_family_worker.py`
- `tests/test_v3m2_family_authority.py`
- `tests/test_v3m2_round0.py`
- `tests/test_v3_gpu_v3m2_family.py`

TDD实现 family manifest、parameter graph、local factory、endpoint fidelity、support/locality、
symplectic/unitary、Floquet shell、CPU↔GPU fp64 parity与三坐标 adapters。Round 0只运行任务书冻结
的小预算 audit；同一运行通过全部门与证伪炮才 PASS。

E1/E2稳定后形成 `P2/S2` campaign-stage authority；clean S2只接受 V3-M1 READY envelope，签发
exact Round 0 run permit后才启动 kernel。结果由双 reviewer重算并形成 portable Round 0 envelope。

Round 0 FAIL立即停止；换 family必须回到 E1并重置全部下游证据。

---

## Phase F：30 格 pilot

### Task F1：签发同一 family 的 pilot permit

**Planned files：**

- `rulespace_v3/v3m2_pilot_authority.py`
- `rulespace_v3/v3m2_pilot_runtime.py`
- `tests/test_v3m2_pilot_authority.py`
- `tests/test_v3m2_pilot_runtime.py`

Round 0 PASS 后另建 `docsv3/v3-任务书-V3M2-30格pilot.md`，冻结 exact 30 cells、三方向、L、
seeds、shell、negative controls、discernibility estimand、资源预算、artifact schema、family root 与
Round 0 evidence root。实现 exact `PilotManifestV1`、opaque permit issuer/verifier与攻击 tests；
permit禁止 caller grid与跨-family root。本任务只完成 taskbook/manifest/permit body，不提前形成
P3/S3。

### Task F2：冻结 review/exporter、形成 P3/S3 并执行 pilot

**Additional planned files：**

- `rulespace_v3/v3m2_pilot_review.py`
- `tests/test_v3m2_pilot_review.py`

在任何签发/运行前，先实现并测试 F3 所需的 exact `PilotReviewV1`、双签 portable pilot
envelope、typed state、独立 verifier及全部攻击 tests；因此
`rulespace_v3/v3m2_pilot_review.py` 和 `tests/test_v3m2_pilot_review.py` 必须与 F1/F2 runtime一起进入
preparation commit `P3`。完整 code/docs/tests稳定并经双复审后才形成 strict `S3`，只从 verified
Round 0 portable envelope签发 live pilot permit。

CPU replay与CUDA kernel可按独立 cells/shards并行；每 shard使用可恢复原子输出，保存 raw quantities
与 toolchain/device manifest。不得在运行中调阈值、换 shell或补 cell。

### Task F3：可分辨性独立复核

从 raw 30-grid结果重算牙度、margin、negative-control separation、representation invariants与三坐标。
调用 S3 前已冻结的 exact `PilotReviewV1` 与独立 verifier；攻击合同已覆盖伪 PASS、缺 cell、跨
family、改阈值/shell、单 reviewer与 artifact splice。S3 后只允许复核和写 artifact，不再修改
review code/tests。review FAIL则停止；只有 signed PASS envelope才能进入正式扫描设计。

---

## Phase G：V3-M3 正式扫描 manifest 与 GPU preflight

### Task G1：冻结正式扫描任务书、manifest schema 与 worker合同

先创建并独立复审：

- `docsv3/v3-任务书-V3M3-GPU正式扫描.md`
- `docsv3/v3-预注册-V3M3-正式扫描-2026-08-01.md`
- exact machine-readable scan manifest schema（此时不填 cells/root、不签发）

任务书必须要求最终 manifest 绑定 family root、Round 0/pilot evidence、100–1000 exact cells、三方向、L序列、
negative controls、convergence order、source/code closure、precision、seed、sharding、resume、output
schema与资源上限。不得把 pilot grid默认为正式 grid；schema/taskbook本身不产生 scan permit。

### Task G2：实现并冻结 CUDA worker 与 preflight verifier

**Planned files：**

- `rulespace_gpu/v3m3_scan_worker.py`
- `rulespace_gpu/v3m3_preflight.py`
- `tests/test_v3_gpu_v3m3_scan_worker.py`
- `tests/test_v3_gpu_v3m3_preflight.py`

先以 unsigned test manifests做 RED→GREEN，实现纯 worker adapter与preflight verifier；production
worker只接受已签 manifest，不能选择 family/grid/threshold/shell。攻击 tests、CPU↔GPU fixture、
resume与atomic output全部完成并提交，形成待绑定的 exact worker/source closure。任何后续 worker或
verifier修改都使未来 manifest重新冻结。preflight至少验证：

- CUDA/device/driver/toolchain manifest；
- fp64/complex128强制，无 silent fp32；
- representative cells CPU↔GPU raw parity；
- batch/chunk/shard invariance；
- locality/support与无 FFT/projector source scan；
- memory/time/disk upper bound；
- interruption/resume、atomic shard、duplicate/missing-cell detection；
- manifest/result root与跨机器 source closure一致。

preflight kernel使用 taskbook冻结、与正式 cells不重合的 `PREFLIGHT_ONLY` cell IDs、独立 nonce、
独立 artifact namespace与资源上限；其输出不得进入 formal shard completion bitmap、正式 result root
或任何科学拟合。worker 的 `FORMAL_SCAN` mode在 GPU checkpoint certificate尚未签发时必须在
kernel launch前机械拒绝。

### Task G3：签正式 manifest、执行 preflight并签发 checkpoint

**Planned files：**

- `rulespace_v3/v3m3_scan_authority.py`
- `rulespace_v3/v3m3_gpu_checkpoint.py`
- `tests/test_v3m3_scan_authority.py`
- `tests/test_v3m3_gpu_checkpoint.py`

只有 G2 worker/tests/source closure冻结后，才实现并完成 G3 所列
`GPUPreflightOutcomeV1`、`GPUCheckpointCertificateV1`、opaque issuer、portable envelope、独立
verifier与全部攻击 tests，并构造 exact 10²–10³ machine-readable scan manifest bytes。上述代码、
tests、taskbook、worker closure与 manifest bytes全部进入 V3-M3 preparation commit `P4`；双复审后
`S4` 只允许 stage-freeze协议预注册的 status/receipt/literal transforms，不能新增或修改 root-bearing
code/manifest body。

clean S4 campaign-stage authority验证 portable pilot PASS envelope并签发 P4 中已冻结的 manifest；
随后把 **同一 signed manifest** 传给 CUDA preflight。任何 worker/verifier/source closure/manifest
body改动都必须废弃 P4/S4，回到 G2/G3产生新 epoch。独立 verifier从 raw preflight重算 verdict；
仅当 taskbook冻结的 GPU-ready state PASS，输出可复制到
其他 CUDA 机器的：

```text
signed scan manifest
source/commit closure
CUDA environment requirements
shard table
resume/verification commands
expected artifact schemas
preflight certificate
```

到此即为本请求的 GPU checkpoint。**不得启动首个正式扫描 kernel。**

---

## 总验证矩阵

每个阶段按风险取子集；形成 P 前执行完整矩阵：

```bash
(cd formal/v3m0 && PATH=/Users/prismer/.elan/bin:$PATH lake build)
.venv/bin/python -m pytest -q tests/test_v3m0_*.py
.venv/bin/python -m pytest -q tests/test_v3_gpu_*.py
.venv/bin/python -m compileall -q \
  rulespace rulespace_gpu rulespace_v2 rulespace_v3 experiments tools
v3_changed_python=(${(f)"$(git diff --name-only --diff-filter=ACMR 99dac47..HEAD -- '*.py')"})
(( ${#v3_changed_python[@]} == 0 )) || /opt/homebrew/bin/ruff check "${v3_changed_python[@]}"
(( ${#v3_changed_python[@]} == 0 )) || /opt/homebrew/bin/ruff format --check "${v3_changed_python[@]}"
RULESPACE_BACKEND=numpy .venv/bin/python -m rulespace_gpu.verify
git diff --check
```

Ruff 只约束本战役自基线 `99dac47` 起修改的 Python files；仓库既有 legacy lint debt 不属于本
战役，也不得用 bulk auto-fix污染历史实验/证书源码。

具有 CUDA 的机器在 G2 另跑 taskbook冻结的 explicit CUDA preflight；本机 MLX/JAX/numpy smoke
不得替代 CUDA PASS。

## 阶段汇报合同

每次 checkpoint 汇报必须列：

1. 当前 commit/branch/clean 状态；
2. 当前 authoritative state 与是否可进入下一阶段；
3. 新通过的 exact gates及 JSON/root路径；
4. 仍阻断的第一项与所有 required undefined reasons；
5. 已跑验证的命令/通过数/耗时；
6. GPU science permit 是 `LOCKED`、`PREFLIGHT_READY` 还是 taskbook冻结的正式 READY；
7. 若 HALT，明确这是科学裁定、工程缺口还是环境缺口。
