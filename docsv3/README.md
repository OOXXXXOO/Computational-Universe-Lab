<p align="center">
  <img src="../visualizations/assets/logo.png" alt="Computational Universe Lab" width="72%">
</p>

# docsv3：因果可识别涌现边界文档体系

> 状态：**纲领 v3 已生效；`HALT-V3M0-WINDOW` unchanged**，2026-08-01。
> 本目录记录由 v2 M3′ 30 格无牙追因触发的范式修订。PI 已授权在北极星漂移审计通过后
> 签发并开工；审计结论为 PASS。v2 证据链保持原样，V3-M1、新 family、pilot 与昂贵扫描
> 继续锁定；`READY-V3-M1-ANCHOR-CERTIFICATION` 尚未签发。

## 为什么需要 v3

v2 把“涌现度”压缩为单一 `ε`。M3′ pilot 之后的交叉审计发现，仓库实际运行着三个不同的
估计对象：

1. R30/R23 的 `ε` 来自构造来源：全部手搭或零手搭；
2. 冻结 R25 walk 的 `ε` 来自阈值化主角谱的约束兼容度；legacy greedy repair 是另一条
   基依赖诊断，未证明为严格最小局域修复距离；
3. M3′ pilot 的 `ε_geo` 来自成品传播子空间相对 `ker C` 的几何兼容度。

更严重的是，M0′/M3 与 M2 对同一主角谱使用了互补公式。若
`S_curv ⊂ ker C`，前者给 `ε=1`，M2 给 `ε=0`。这不是阈值、精度或参数范围问题，而是
“构造因果来源”和“成品几何质量”被写进了同一个标量。

v3 因而把单轴拆开：

```text
ε_causal  ：actual 曲率有效 DOF 在 target-conditioned 机制消融后的子空间存活
δ_geom    ：实测传播—曲率响应到目标复形的几何距离
σ=(α,A)   ：约束残差的极限标度
```

这三者必须来自同一个 source-qualified 响应子空间，但不得再互相代填。
其中 `ε_causal` 只测无量纲曲率商空间中的 DOF 存活；任何“目标定律因果涌现”强主张还须
让 matched-ablated 从完整 source domain 独立通过几何、标度、映射、色散及闭环门。

## 权威阅读顺序

1. `v3-纲领-北极星-因果可识别涌现边界制图.md`
2. `v3-裁定-从单epsilon到因果可识别双轴-2026-07-30.md`
3. `v3-勘误-observer-collapse-coisometry-2026-07-30.md`
4. `v3-勘误-application-scenario与typed-termination-2026-07-31.md`
5. `v3-任务书-V3M0-因果响应与几何距离仪器.md`
6. `v3-实施计划-V3M0-双轴仪器迁移-2026-07-30.md`
7. v2 当前状态：`../docsv2/v2-小报告-M3-30格pilot-2026-07-30.md`
8. v2 任务书：`../docsv2/v2-任务书-M3-涌现边界制图.md`

## 版本关系

- v1 的可达性封存不翻案；
- v2 的纲领、任务书、JSON、图和结论不追溯改写；
- v2 M3′ 30 格结果保留为
  `evaluator-v2.0/full-positive` 的条件性 no-go 证据，不是 v3 边界数据点；
- 其中 observer-collapse 的“满张到固定映回子空间”推论须满足
  `v3-勘误-observer-collapse-coisometry-2026-07-30.md` 冻结的白化/coisometry 桥；
- Task 12–17 的 application bundle、预期终止、C20 分析控制和 reference shell 以
  `v3-勘误-application-scenario与typed-termination-2026-07-31.md` 为准；
- v3 新结果使用独立 schema、结果文件和运行态，禁止把不同 evaluator 版本的数据混入
  同一边界拟合；
- `AGENTS.md` / `CLAUDE.md` 已随签发切换到本目录；不启动新 pilot。
- quantum-unitary 与 classical-symplectic 数据分层入图、禁止混合拟合。

底层候选空间继续保留
`target_spec × 复形族 × 物质耦合 × 微观规则参数`；三坐标只是运行后的观测坐标。
spin 0、spin 1 Maxwell、spin 2 Einstein 与未来 Yang–Mills 按 target 分栏，当前 V3-M0
的 spin 2 曲率仪器切片不缩窄整个纲领。

## 当前唯一获批动作

签发后只允许执行 V3-M0：

1. 形式化并数值桥接三个 no-go；
2. 建立机械生成的 construction trace；
3. 对 actual / matched-ablated 两个真实实空间 factory 做成对响应测量；
4. 用 synthetic anchor triangle、相位/幅值 nuisance、干涉、缺模与 D-M2-6 双控制认证；
5. 校准 `ε_causal`、`δ_geom` 和 `σ` 的共同响应子空间、Fejér 窗及判别裕度；
6. 只交付 R30/R23/R25 typed-adapter 合同，不执行其物理重测。

V3-M0 的最高可签发状态是 `READY-V3-M1-ANCHOR-CERTIFICATION`，但当前
仍为 `HALT-V3M0-WINDOW`，该 READY **NOT ISSUED**。旧锚重测与有限物理正锚审计
属于串行的 V3-M1；新 family、30 格 pilot、`10²–10³` 与 GPU 长跑仍全部锁定。

## 非权威设计索引

- [`v3-设计勘误-C19-refreeze-v2-2026-08-01.md`](v3-设计勘误-C19-refreeze-v2-2026-08-01.md)：
  C19 20 实通道 refreeze v2 的 DRAFT 合同。authority-neutral raw candidate、
  两份预响应 grid-derivation protocol、唯一 Response manifest 与 10D conditional
  geometry bundle 已在 commit `4217291` 实现并通过独立复审，但只是
  `OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY / NULL_INTERVENTION_INVARIANCE_CONTROL`，
  明确不具备 physical-anchor 或 family 资格。当前 V2 wire 仍不可承载；新
  `ParentFreezeV3Manifest` / `VerifiedParentFreezeV3` /
  `issue_v3m0_parent_freeze_v3()`、`WindowThresholdCalibrationV3` 及
  calibration/application/response/materialization schema、
  verified metric-support authority、Dynamics/Bridge 运行时 artifact 派生、
  control-evidence issuer 与机械签发闭合均尚待实现。本 DRAFT 不改变 Parent、permit 或
  `HALT-V3M0-WINDOW`，也不签发
  `READY-V3-M1-ANCHOR-CERTIFICATION` 或任何下游解锁状态。
