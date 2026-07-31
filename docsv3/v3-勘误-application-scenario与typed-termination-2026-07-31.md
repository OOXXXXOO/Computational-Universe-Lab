<p align="center">
  <img src="../visualizations/assets/logo.png" alt="Computational Universe Lab" width="58%">
</p>

# v3 勘误：application scenario、typed termination 与参考 shell

*Computational Universe Lab · 2026-07-31 · 状态：签发并生效*

## 0. 勘误边界

本勘误修正 V3-M0 Task 12–17 的一个不可满足接口组合，不改变：

- v3 北极星、三坐标定义或 claim ladder；
- `τ_surv=0.5`、survival grey half-width `0.1`；
- `τ_geom=0.05`、geometry grey half-width `0.01`；
- `τ_cover=0.5`、coverage grey half-width `0.1`；
- V3-M0 → V3-M1 → V3-M2 的串行科学门；
- “V3-M3 前禁止 GPU 长跑”的边界。

它只撤销以下错误隐含前提：

> C04–C20 的每个 application case 都必须由一个
> `V3M0ApplicationConstruction` 产出一对成功的
> `VerifiedResponseBlock`。

该前提会把预期灰带、预期失败和纯分析控制伪装成成功响应，是证据类型错误。

## 1. 触发证据

### 1.1 C11 的 grey 早于 `K_surv`

C11 的三段是 absolute response activation 的
`null / grey / signal`，不是已经定义 `K_surv` 后的 survival threshold 三段。
grey 模式没有合法 `Q_active/Q_curv` 域，因此：

- 不存在可诚实填写的 `s_i`；
- 不得用 `s_i=0.5` 代填；
- 不得为 grey 分支签发 `VerifiedResponseBlock`；
- Task 13 的全 float `SurvivalThresholdInstanceAudit` 只能使用 C04 的
  `s=(0.25,0.75)` 两侧控制。

C11 改由 Task 12 的 typed activation attempt 认证
`0 / undefined / 1` 语义；这里的 `undefined` 是上游激活域不存在，不得与
`|s_i-τ_surv|<0.1` 的 survival-grey 混同。

### 1.2 C14 与 C20 不是 response-block 成功路径

C14 预注册的四个结果分别终止于：

```text
ENDPOINT_SHELL_AMBIGUOUS
RESPONSE_NULL
TRACE_UNCLASSIFIED
UNSTABLE
```

它们通过的含义是“在正确阶段以精确 reason 终止，且没有越权签发下游 capability”，
不是“产出成功 block”。

C20 是 deterministic series / D-M2-6 分析控制。它必须产出独立的已验证 series
evidence，不得把四个样本塞进响应矩阵冒充动力学。

### 1.3 旧 application materializer 没有执行 DAG

首轮实现把 C04–C20 全部降成同一组六个零支撑 shear；operation kind 与参数只进入
provenance，不进入实际算子。实测 C04/C05 的 actual transition 逐位相同，ablated
transition 也逐位相同。该路径只证明“元数据不同”，不证明 control 动力学不同，故不得
签发任何 application control evidence。

### 1.4 旧 prestructure issuer 没有绑定 live permit/construction

旧内部 issuer 只接收 Parent spec、格式合法的 permit SHA、raw matched outcome 与 role。
把真实 C04 outcome 配上任意其他 64 位 SHA 仍可签出 authority。这没有建立

```text
live permit → closed materializer → live construction → role authority
```

的不可替换链，必须关闭。

### 1.5 C04 旧参考 shell 数学不可满足

旧 C04 同时冻结：

```text
real 2×2 symplectic stable transition
principal phase band = [-0.25,0.25]
expected_shell_rank = 1
```

实 `2×2` 辛稳定矩阵的谱为共轭对 `e^{±iθ}`。关于零对称的闭相位带只能同时包含这一对
或同时排除，带内代数重数只能为 `0` 或 `2`；`θ=0` 时重数仍为 `2`。因此 rank 1
不是实现精度问题，而是冻结合同的数学空集。

## 2. 新的 scenario 冻结

每个 application case 必须在 ParentFreeze 中递归内嵌有序
`ApplicationScenarioExecutionSpec`：

```python
@dataclass(frozen=True)
class ApplicationScenarioExecutionSpec:
    scenario_schema_version: str
    scenario_id: str
    operation_output_ids: tuple[str, ...]
    execution_lane: Literal[
        "BLOCK_SUCCESS",
        "EXPECTED_TYPED_TERMINATION",
        "ANALYSIS_CONTROL",
    ]
    execution_recipe_id: str
    expected_terminal_stage: str | None
    expected_undefined_reason: UndefinedReason | None
    expected_artifact_type: str
    scenario_sha: str
```

规则如下：

1. `operation_output_ids` 只能引用同一 application DAG 中已冻结的 node；
2. bundle control 必须展开为有序 scenario，禁止把多个互斥试验硬塞进一个成功 block；
3. `execution_recipe_id` 必须在首次运行前冻结，recipe 从完整 operation body 与参数机械
   生成 factory/source/readout/series；参数只写 provenance 而不改变执行结果视为失败；
4. 同一 recipe 可复用，但不得按运行结果选择 recipe；
5. 每个 scenario 分别生成 construction/evidence SHA；case-level PASS 是这些 scenario
   按冻结顺序全部通过后的聚合结果。

至少按以下分栏：

| control | scenario/lane |
|---|---|
| C04 | canonical-angle，`BLOCK_SUCCESS` |
| C05 | phase、gain 两个 `BLOCK_SUCCESS` |
| C06–C10 | 各自冻结的 `BLOCK_SUCCESS` scenario |
| C11 | null=`EXPECTED_TYPED_TERMINATION/RESPONSE_NULL`；grey=`EXPECTED_TYPED_TERMINATION/RESPONSE_GREY`；signal=`BLOCK_SUCCESS` |
| C12 | IR/window normalization，`BLOCK_SUCCESS` |
| C13 | both-zero，`EXPECTED_TYPED_TERMINATION/RESPONSE_NULL` |
| C14 | 四个精确 failure scenario，`EXPECTED_TYPED_TERMINATION` |
| C15 | full-h、low-rank-TT、TT、TT⊕row 四个 `BLOCK_SUCCESS` |
| C16 | coverage-low/high 两个 `BLOCK_SUCCESS` |
| C17–C19 | 各自冻结的 `BLOCK_SUCCESS` scenario |
| C20 | clean-zero、true-floor 两个 `ANALYSIS_CONTROL` |

若某个高层 `direct-sum-v1` 真正表示同一次线性代数直和而不是 scenario bundle，
execution spec 必须显式把它标为同一 recipe 的内部 node；不得由字符串名称猜测。

## 3. 三类合法输出

### 3.1 `BLOCK_SUCCESS`

成功路径必须提供：

```text
VerifiedCalibrationApplicationPermit
→ VerifiedV3M0ScenarioConstruction
→ actual/ablated role authorities
→ transitions + dynamics certificates
→ qualification + endpoint shell + paired response
→ VerifiedV3M0ControlApplicationEvidence
→ branch-specific VerifiedResponseBlock
```

任一缺失、raw substitute、错 scenario、错 role、错 permit 或错 body 都是 unexpected
undefined，阻止 READY。

### 3.2 `EXPECTED_TYPED_TERMINATION`

必须提供 opaque `VerifiedResponseBlockAttemptOutcome` 或同阶段专用的 verified attempt：

```python
@dataclass(frozen=True)
class ResponseBlockAttemptOutcome:
    attempt_schema_version: str
    application_spec: V3M0SyntheticControlApplicationSpec
    scenario_spec: ApplicationScenarioExecutionSpec
    permit: CalibrationApplicationPermit
    terminal_stage: str
    status: BlockStatus
    raw_singular_values: tuple[float, ...]
    activation_labels: tuple[Literal["null", "grey", "signal"], ...]
    precursor_evidence_sha: str
    downstream_capability_issued: Literal[False]
    outcome_sha: str
```

要求：

- reason 必须逐位等于 ParentFreeze 的预言；
- 保存到达终止阶段前的完整可重放证据；
- `downstream_capability_issued` 必须为 `False`；
- 预期终止的 control-level result 是 defined/PASS，但其内部物理坐标仍为 `undefined`；
- 不得用 raw `BlockStatus`、异常文本或 caller reason 代替 verified attempt。

terminal stage 字符串只允许
`activation / trace / stability / endpoint_shell / success`。当前冻结映射为：

```text
C11 null   → activation / RESPONSE_NULL
C11 grey   → activation / RESPONSE_GREY
C11 signal → success / None
C13        → activation / RESPONSE_NULL

C14 endpoint-ambiguous  → endpoint_shell / ENDPOINT_SHELL_AMBIGUOUS
C14 response-null       → activation     / RESPONSE_NULL
C14 trace-unclassified  → trace          / TRACE_UNCLASSIFIED
C14 unstable            → stability      / UNSTABLE
```

### 3.3 `ANALYSIS_CONTROL`

C20 必须提供 opaque `VerifiedDeterministicSeriesControlOutcome`，递归保存：

```text
scenario spec
raw samples
series class
D-M2-6 双测结果
fit/decision evidence
self hash 与 live seal
```

它可以引用基础动力学 lineage 作为旁证，但不得伪装成 `ResponseBlock`。

## 4. Permit、construction 与 role authority

case-level permit 必须绑定完整 scenario tuple。scenario construction issuer 的最小输入为：

```text
live VerifiedCalibrationApplicationPermit
+ exact scenario_id
+ closed materializer 产生的 live construction attestation
```

禁止再导出或内部接受：

```text
raw parent + raw application spec + caller permit SHA + arbitrary matched outcome
```

`VerifiedV3M0ScenarioConstruction` 私有 seal 至少递归绑定：

- parent、window calibration、permit 与 scenario full body；
- operation DAG 的逐 node 求值记录；
- recipe ID、源码 closure 与参数读取记录；
- actual/ablated 完整 `AblationPairSnapshot`；
- factory/interface/source/readout/grid/run-spec 的全部 SHA；
- 每个 operation 对执行 artifact 的 effect digest。

role prestructure authority 只能消费该 live construction capability，并在每次 reverify 时
从 permit 重放 materializer。任意 SHA 替换、跨 scenario pair、相同 provenance 但不同
执行 body、或 operation 参数对 effect digest 无影响，都必须拒绝。

## 5. 参考 shell 修正

V3-M0 synthetic application 的 reference carrier 改为解析 quarter-turn：

```text
U_ref = [[0,-1],[1,0]]
eigenphases = {-π/2,+π/2}
```

reference phase band 冻结为：

```text
[π/2-1/8, π/2+1/8]
expected_shell_rank = 1
```

端点离两侧边界均为 `1/8`，且与负频同伴相隔至少 `π-1/4`。这些数由解析谱先验推出，
不是从 control 运行结果调参。ParentFreeze 必须保存相应 fp64 bits 与解析来源 ID，并由
exact/数值测试共同重算。

若某个 scenario 需要更大的状态空间，它必须把 `U_ref` 作为显式 direct-sum reference
sector，并为其他 sector 冻结不与该带相交的相位；不得继续宣称旧两通道 carrier 能承载
任意 bundle。

### 5.1 C04 的首个可满足局域 recipe

C04 冻结为两个 canonical pairs，即 real channel order
`(q0,p0,q1,p1)`，source/readout 与 h/curvature operators 使用 identity-4。用 complex
two-mode 记号定义

```text
F    = diag(i,-1)
C    = diag(1,-1)
R(t) = [[cos t,-sin t],[sin t,cos t]]
D(k) = [[0,-exp(-ik)],[exp(ik),0]]
S(k) = R(α) D(k) R(β)

M_ablated(k) = S(k) F S(k)†
M_actual(k)  = C M_ablated(k) C†
```

`R` 由 on-site 三 shear 分解，`D` 由两个 canonical pair 之间的 reciprocal signed
swap 分解，`C` 是 target-conditioned on-site mode sign；actual 消融 `C/C†` 后精确得到
matched-ablated。每个分解都须由真实 factory executor 与 static symbol 对拍，不能把上式
矩阵直接塞进 response。

角度不从数值搜索结果选择，而由以下解析方程冻结：

```text
cos(2α) cos(2β) = -1/2
sin(2α) sin(2β) = -(sqrt(3)-1)/2
2(α-β) = -5π/6
2(α+β) = arccos(sqrt(3)/2-1)
```

取相应 principal solution，约为
`α=-0.22820472, β=1.08079222`；ParentFreeze 保存实际 fp64 bits 与方程来源。
若 `w(k)` 是 `S(k)` 第一列、`p(k)=|w_0(k)|²`，则在冻结
`k₁=π/4,k₂=π/2`：

```text
p(k₁)=3/4
p(k₂)=(2+sqrt(3))/4
|w† C w|²=(2p-1)² ∈ {1/4,3/4}
```

因此两个 k-block 的 `+π/2` projector 叠成 rank-2 响应后，actual/ablated 主角平方多重集
精确为 `{0.25,0.75}`。两支的完整相位谱保持
`{+π/2,-π/2,π,π}`，identity metric 下 unitary/symplectic residual 必须
`≤1e-12`，real-space 支撑半径必须与 `L` 无关。

## 6. Task 13 与 Task 17 的修正

Task 13 的 survival threshold calibration 只用 C04 两个合法 survival 值
`0.25/0.75`。C11 不进入 `SurvivalThresholdInstanceAudit`。

Task 17 的 READY 条件改为：

```python
ready = (
    formal_all_pass
    and exact_all_pass
    and all_block_success_artifacts_verified
    and no_unexpected_undefined_in_block_success
    and all_expected_terminal_outcomes_verified
    and no_unexpected_downstream_capability
    and all_analysis_controls_verified
    and all_required_controls_pass
    and representation_invariants_pass
    and no_physical_anchor_run
)
```

`no_required_block_undefined` 只量化 `BLOCK_SUCCESS` 路径。预期 typed termination 的内部
`undefined` 不得污染顶层 control PASS，也不得被抹成成功物理坐标。

## 7. 迁移与重新冻结

本勘误生效后：

1. 当前未签发的 Task 12 application evidence 全部作废；
2. ParentFreeze schema、manifest SHA、formal/static closure 与所有下游 source manifest
   必须重新冻结；
3. 先加入以下 RED 测试，再实现：
   - C04/C05 operation/参数改变时执行 artifact 不同；
   - 任意 permit SHA 不能签 role authority；
   - C11 grey 不产生 `VerifiedResponseBlock`；
   - C14 精确阶段终止且无下游 capability；
   - C20 不经过 response-block API；
   - reference quarter-turn 的带内 rank 精确为 1；
4. 旧 C04–C20 同动力学 carrier 不得作为回归基线；
5. V3-M0 未重新全过前，V3-M1、family、pilot 与 GPU 仍全部锁定。

这是一项 V3-M0 前置合同修复，不是阈值修改，也不提高任何物理主张。
