# v3 勘误：observer-collapse 的 coisometry 桥接条件

*Computational Universe Lab · 2026-07-30 · 状态：签发并生效*

## 0. 裁定

本勘误修正
`v3-裁定-从单epsilon到因果可识别双轴-2026-07-30.md` §1.2 中一条遗漏前提的
range 推论。它不改变 v3 北极星、claim ladder、V3-M0 权限边界或任何冻结阈值，也不
追溯改写 v1/v2 证据链。

北极星漂移审计结论仍为 **无漂移**。被修正的是“正频 `h` 投影满张”与“映回 `h`
空间后的曲率 observer 固定”之间缺失的白化 metric/coisometry 桥。

## 1. 原推论为何过强

在有限维复内积空间中，令

```text
B_h : H_mode → H_h
inc : H_h → H_curv
A = inc ∘ B_h .
```

`B_h` 满射只推出输出侧的

```text
range(A) = range(inc).
```

它不单独推出把 `A` 的非零右奇异子空间经 `B_h` 映回后等于
`range(inc†)`。二维反例为

```text
inc = [1 0],
B_h = [[1, 1],
       [0, 1]].
```

这里 `B_h` 可逆，故满射；但 `A=[1 1]` 的非零右奇异子空间为
`span(1,1)`，经 `B_h` 映回得到 `span(2,1)`，而
`range(inc†)=span(1,0)`。因此“满张 ⇒ 固定 observer 子空间”在任意坐标 metric 下
不成立。

## 2. 修正后的定理分层

在有限维 Hilbert 空间中：

1. 若 `B_h` 满射，则
   `range(inc∘B_h)=range(inc)`；
2. 令 `A=inc∘B_h`。`A†A` 的非零谱支撑精确为
   `range(A†A)=range(A†)`；
3. 将该支撑经 `B_h` 映回 `H_h`，得到
   `range(B_h B_h† inc†)`，而不是无条件的 `range(inc†)`；
4. 若冻结白化 metric 下 `B_h` 是 coisometry，
   `B_h B_h†=I_h`，则才有
   `range(B_h B_h† inc†)=range(inc†)`。更弱地，只要
   `B_h B_h†` 保持 `range(inc†)`（在该有限维子空间上的限制因正定而可逆），同一
   range 结论也成立。

形式化实现必须保留这四层，不得再由满射跳过 metric bridge。

## 3. 当前 v2 evaluator 为何仍满足桥接

历史 evaluator 在 `rulespace_v2/m3_pilot.py` 中先执行

```text
raw_h   = eigenvectors[:10, positive]
h_basis = orth(raw_h)
```

再把 `h_basis` 送入曲率测量。30 格记录中的正频 `h` rank 为 10；因此
`h_basis` 是 `10×10` 的正交归一方阵，在该冻结 Euclidean/Hermitian metric 下满足

```text
h_basis h_basis† = I_10.
```

所以旧 evaluator 的实测常数谱仍可由 coisometry 桥接解释。保留的事实是：

- 30 个 kernel SHA 不同；
- 30 格均实测 `N_curv=6`、`j=4`、`max sin θ=1`；
- 在该 evaluator 的白化、非零谱选择和分解前提下，这一常数谱是条件性结构事实。

撤回的只有“任意满射 `B_h` 都必然给出相同映回子空间”这一无条件表述。

## 4. 固定平方谱的完整条件链

要推出

```text
sin²θ multiset = {0, 0, 1, 1, 1, 1},
```

至少须显式认证：

1. evaluator 完整选择 `A=inc∘B_h` 的非零右奇异/Gram 支撑；
2. 冻结白化 metric 下 `B_h B_h†=I_h`，或认证上述更弱的
   `range(inc†)` 保持条件；
3. `rank(inc)=6`；
4. `Gauge≤ker(inc)`、`dim Gauge=4`，从而 `Gauge=ker(inc)`；
5. `TT₂⊕Gauge₄⊕Row₄` 是 ambient `H_h` 的两两正交分解；
6. `ker C=TT⊕Gauge`，并使用与该分解一致的冻结 projector。

这些条件共同推出

```text
S_curv = range(inc†) = TT ⊕ Row,
ker C  = TT ⊕ Gauge,
sin²θ  = (0, 0, 1, 1, 1, 1).
```

首批 Lean 证书只声明平方谱，不以 `sqrt` 或 `arccos` 扩张结论。

## 5. 影响与权限

- v3 北极星、双轴 observer 和 V3-M0 研究范式不变；
- v2 30 格数据仍是 `evaluator-v2.0/full-positive` 的条件性 observer-collapse
  证据，不升级为 v3 边界点；
- 不改阈值、不重跑历史 pilot、不解锁新 family、Round 0、30 格 pilot、
  `10²–10³` 正式扫描或 GPU 长跑；
- 对应 Lean 证书位于
  `formal/v3m0/V3M0/ObserverCollapse.lean`，并须同时证明输出 range、Gram 支撑、
  coisometry 桥、固定平方谱和 gauge quotient，不能把任一数值前提藏入定义。
