# v3 设计勘误：geometry protocol schema v3

*Computational Universe Lab · 2026-08-01 · 状态：P0 schema implemented，非 Parent/permit/scientific authority*

## 0. 裁定

本切片新增独立的 authority-neutral
`rulespace_v3/geometry_protocol_v3.py`，冻结 C15–C19 的预响应解析上下文、geometry
bundle wire 与共用结构 verifier。它不修改已签发的
`ApplicationScenarioResponseProtocolV2`，不改写 C04 v2 body/hash，不签发 opaque
capability，也不读取 finite response、SVD、threshold verdict 或任何 Task 12 数值产物。

本记录修正旧 geometry bundle verifier 的一条过强公共条件：

```text
physical_quotient_map @ kernel_basis = 0
```

不能作为 C15–C19 的全局合同。`kernel_basis` 表示 geometry 约束 kernel，而
`physical_quotient_map` 只商掉 gauge-null sector；二者不是同一个 kernel。合法的 C15、
C17 必须保留 TT，并只杀 gauge；合法的 C18 使用恒等 physical quotient，因此
`QK≠0`。schema v3 改为逐 kind 验证，不再保留全局 `QK=0`。

## 1. 版本与 authority 边界

新增三个 exact frozen records：

1. `GeometryAnalyticContextV2`：由未来 repository-closed Parent-v2 resolver 机械生成的
   窄解析输入；
2. `ObserverCollapsePrerequisiteSpecV1`：只冻结 observer-collapse 条件定理的前提；
3. `ScenarioResponseGeometryBundleV3`：在任一 response branch 运行前冻结的解析矩阵与
   kind-specific wires。

schema IDs 分别为：

```text
v3m0.geometry-analytic-context.v2
v3m0.observer-collapse-prerequisite-spec.v1
v3m0.scenario-response-geometry-bundle.v3
```

所有 payload 显式列出字段并只排除本层 self-hash；nested tensor/spec 的完整 body 与其 SHA
递归进入外层 payload。verifier 拒绝 subclass、unknown/missing runtime field、nested SHA
漂移和 outer SHA 漂移。

raw body 的完整性不是 authority。全量重签的一份自洽 raw body 仍必须在后续 production
compiler 中与 live Parent-v2、permit、materialization 和 expected analytic rebuild 逐字段
相等，才可能进入 opaque protocol capability。本 P0 不实现该 compiler。

## 2. 公共冻结字段

analytic context 与 bundle 共同冻结：

- closed geometry kind；
- exact `scenario_id/scenario_sha/recipe_sha`；
- Parent reviewed `geometry_derivation_source_id`；
- active scenario 的 `semantic_sector_names`；
- `selected_fejer_order`；
- canonical `analytic_source_recipe_shas`；
- context/bundle self-hash。

context 另冻结 `control_case_id/operation_dag_sha/compiled_contract_sha`、C16 coverage、C17
gauge amplitude 和 C19 expected flag。bundle 递归绑定 `analytic_context_sha`，但不重复
outer protocol 已负责的 Parent/permit/materialization SHAs。

冻结的 T 集合为：

```text
(256, 512, 1024, 2048, 4096, 8192)
```

类型必须是 exact positive `int`，不得接受 `bool/float`。未来总装必须再逐位验证
`bundle T = protocol T = permit T = materialization T`。

analytic source recipe SHA 数量按 kind 冻结：C15 为 canonical 四场景 recipe，C16 为该
四个 C15 reference recipe 加 active C16 recipe，C17–C19 各为 active recipe。active
`recipe_sha` 必须包含在该 tuple，tuple 不得重复。

## 3. kind-specific invariants

### 3.1 C15

四个 scenario 的 semantic slice 固定为：

| scenario | semantic sectors |
|---|---|
| `full-h` | `TT0, TT1, Gauge, Row` |
| `low-rank-tt` | `TT0` |
| `tt` | `TT0, TT1` |
| `tt-plus-row` | `TT0, TT1, Row` |

bundle 冻结 rank-2 TT、rank-1 Gauge 和 `kernel=TT⊕Gauge`。verifier 要求
`Q·Gauge=0`，同时在冻结 physical metric 下 `TT†Q†MQTT=I₂`。不得重新加入
`Q·kernel=0`。

### 3.2 C16

`coverage_control_id` 必须逐场景等于 operation output 的完整 instance ID，分别以
`.00-coverage-low` 和 `.01-coverage-high` 结尾；fp64 wire 分别精确为 `(0.25,)` 与
`(0.75,)`。low/high ID、wire 交叉拼接必须拒绝。

reviewed Parent-v2 冻结的唯一 derivation ID 是：

```text
c16-analytic-coverage-target-bundle-v1
```

旧 pre-permit builder 使用的
`c16-analytic-coverage-orientation-bundle-v1` 与 reviewed Parent 冲突。production issuer
不得接受别名、静默兼容或在本切片修改 Parent 数据；若理论意图未来改变，必须先走正式
Parent refreeze。本 P0 只按现有 reviewed Parent ID fail closed。

### 3.3 C17

令 `T` 为 undressed TT frame，`G` 为 gauge frame。verifier 要求二者各自正交、互相正交，
`kernel=span(T,G)`，`QG=0` 且 Q 在 physical metric 下保持 T。Parent amplitude 精确为
`8.0`，graph rank 精确为 `2`。

对每个冻结 Fejér order `N`，按固定 fp64 运算顺序重算：

```text
r_N = 1.0 / float(N + 1)
analytic graph sv = (8, 8)
actual raw graph sv = (8, 8)
matched-ablated raw graph sv = (8*r_N, 8*r_N)
```

formula ID 固定为
`c17-fejer-shared-U-actual-a-ablated-a-over-Tplus1-v1`。比较使用 fp64 bit equality，
不得以 tolerance、caller wire 或 measured response 替代。

### 3.4 C18

C18 只承载 independent unary 的解析几何：`kernel` rank 1、targets rank 2，kernel 与第一
target direction 同子空间；`physical_quotient_map=I₄`、metric=`I₄`。因此合法 C18 明确
满足 `QK≠0`。coverage、gauge graph 和 observer-collapse 字段全部禁止。

actual/matched 的 `1/2` active-rank 合同由未来 outer protocol/compiler 与 Parent compiled
contract 交叉绑定；本 P0 不运行 finite response 来判定新方向是否 off-band。

### 3.5 C19

C19 kind 命名为 `C19_OBSERVER_COLLAPSE_CONDITIONS`，避免把 recipe prediction 写成科学
结论。nested spec 只允许：

```text
claim_ceiling   = CONDITIONAL_PREREQUISITES_ONLY
evaluation_state = NOT_EVALUATED_PRE_RESPONSE
```

冻结前提为：完整选择非零 Gram/SVD 支撑；白化 coisometry 或
`range(inc†)` 保持；`rank(inc)=6`；Gauge 位于 incidence kernel 且维数为 4；
`TT₂⊕Gauge₄⊕Row₄` 两两正交完备；`ker C=TT⊕Gauge` 且 projector/metric 兼容。
coisometry residual tolerance 冻结为 `1e-12`。

该 spec 没有 predicted outcome、observed residual、`triggered`、`PASS` 或固定谱
verdict 字段。任何
`TRIGGERED/PASS` 伪状态，即使重新签名，也不属于 closed schema。实际结论仍须由后续
endpoint shell/response evidence 逐项认证，边界服从已签发的
`v3-勘误-observer-collapse-coisometry-2026-07-30.md`。

## 4. 明确非目标

本 P0 不做以下事项：

- 不修改 `scenario_response_protocol.py` 或 `geometry_application_recipes.py`；
- 不连接 Parent/permit/materialization production resolver；
- 不构造 transition、finite response、SVD、geometry measurement 或 verdict；
- 不改 calibration、response、C12 或 Parent data；
- 不签发 V3-M0 control PASS、M1/M2/M3 或 GPU 长跑权限。

## 5. P0 验证合同

定向测试至少覆盖：合法合成 C15/C17/C18；C16 low/high exact mapping；C17 全部冻结 T；
C19 conditional/not-evaluated；unknown/missing field；nested/outer self-hash；cross-kind
field contamination；旧全局 `QK=0` 误拒回归；伪 `TRIGGERED/PASS` 拒绝。

本切片完成后只允许提交独立 schema commit，等待独立复审；不得顺势接入 production
compiler。
