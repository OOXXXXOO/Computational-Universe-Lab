<p align="center">
  <img src="../visualizations/assets/logo.png" alt="Computational Universe Lab" width="72%">
</p>

# docsv3：因果可识别涌现边界文档体系

> 状态：**设计审阅期**，2026-07-30。
> 本目录记录由 v2 M3′ 30 格无牙追因触发的范式修订。PI 已授权在确有范式级病灶时建立
> `docsv3/`；在本目录的纲领与首个 M0 设计完成复核前，v2 证据链保持原样，昂贵扫描继续锁定。

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

## 权威阅读顺序（设计审阅期）

1. `v3-裁定草案-从单epsilon到因果可识别双轴-2026-07-30.md`
2. `v3-纲领草案-北极星-因果可识别涌现边界制图.md`
3. `v3-设计-V3M0-因果响应与几何距离仪器-2026-07-30.md`
4. v2 当前状态：`../docsv2/v2-小报告-M3-30格pilot-2026-07-30.md`
5. v2 任务书：`../docsv2/v2-任务书-M3-涌现边界制图.md`

## 版本关系

- v1 的可达性封存不翻案；
- v2 的纲领、任务书、JSON、图和结论不追溯改写；
- v2 M3′ 30 格结果保留为
  `evaluator-v2.0/full-positive` 的条件性 no-go 证据，不是 v3 边界数据点；
- v3 新结果使用独立 schema、结果文件和运行态，禁止把不同 evaluator 版本的数据混入
  同一边界拟合；
- 在 V3-M0 控制矩阵通过前，不更新 `AGENTS.md` / `CLAUDE.md` 的权威入口，不启动新 pilot。
- quantum-unitary 与 classical-symplectic 数据分层入图、禁止混合拟合。

## 签发前与签发后的唯一动作

本目录仍是设计稿。PI 复核签发前，只允许设计修订、只读审计和工具链烟测，不允许创建
`rulespace_v3/` 实现或运行物理锚。签发后只允许执行 V3-M0：

1. 形式化并数值桥接三个 no-go；
2. 建立机械生成的 construction trace；
3. 对 actual / matched-ablated 两个真实实空间 factory 做成对响应测量；
4. 用 synthetic anchor triangle、相位/幅值 nuisance、干涉、缺模与 D-M2-6 双控制认证；
5. 校准 `ε_causal`、`δ_geom` 和 `σ` 的共同响应子空间、Fejér 窗及判别裕度；
6. 只交付 R30/R23/R25 typed-adapter 合同，不执行其物理重测。

V3-M0 的最高状态是 `READY-V3-M1-ANCHOR-CERTIFICATION`。旧锚重测与有限物理正锚审计
属于串行的 V3-M1；新 family、30 格 pilot、`10²–10³` 与 GPU 长跑仍全部锁定。
