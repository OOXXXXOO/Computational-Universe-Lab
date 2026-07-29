# AGENTS.md

## 当前任务边界

> **状态覆盖(2026-07-26,纲领 v2 生效)**:v1 北极星已封存,纲领升级为 v2
> "涌现边界制图"。**权威阅读顺序移至:1. `docsv2/README.md` 2. `docsv2/v2-纲领-北极星-涌现边界制图.md`
> 3. `docsv2/v2-裁定-D1D5-2026-07-26.md` 4. 当前任务对应的 v2 任务书/预注册
> 5. v1 背景:`docs/status/阶段封存-2026-07-26-可达性战役收束-自旋2M3结构性不可达.md`。**
> M0′ 完成前,v1 证书不得直接当 v2 门的 PASS 依据;v1 术语(M3/M4/四承诺)只在 v1
> 语境内使用。下文保留为 v1 历史约束,其仓库纪律与验证最低线条款继续有效。

当前活跃战役为 **M3′ / `HALT-PILOT-UNRESOLVED`**（2026-07-30）。权威任务书：
`docsv2/v2-任务书-M3-涌现边界制图.md`；当前判读：
`docsv2/v2-小报告-M3-30格pilot-2026-07-30.md`。legacy RC3-(ii) R2 仍被拒绝；独立的新
严格局域实空间 `q` 族已通过 Round 0，30 格 pilot 也已完整运行，但 30 格在实测
`(ε_geo,σ)` 中塌缩为同一点，没有边界牙齿。正式预注册和正式扫描仍锁定，M3′ 未 PASS、
未物理 FAIL。不得把方向级 σ FAIL、`HALT-PILOT-UNRESOLVED` 或局域族 H0 证书写成
M3′ PASS/FAIL。下一步只允许回 M0′ evaluator / 构造族追因。
当前稳定性准入以 `64³` 全布里渊区为准；8 个 `K_CERT` 只作辛性/Hermitian 探针，不得
再引用为全域稳定性证明。

## 视觉系统（当前与后续材料）

一级品牌为 **Computational Universe Lab**，研究计划副标题为
**Projective Rule-Space Program**。所有新生成的报告封面、README 入口、活跃仪表、演示图与
宣传材料必须先引用以下权威资产和规范，不得另起一套视觉语言：

- Logo：`visualizations/assets/logo.png`
- Repo cover：`visualizations/assets/repo_cover.png`
- 视觉蓝本：`visualizations/dashboards/program_atlas.html`
- 完整规范与图像生成提示词：
  `docsv2/v2-设计规范-Computational-Universe-Lab视觉系统与图像生成提示词.md`

视觉基调为“可复核的科学图册”：`#0B1013` ground、`#111B22` panel、`#1E2C35` line、
`#DDE6EC` ink、`#AEBAC4` dim、`#7F909D` muted、`#45D4C6` geometry/metric、
`#E7A24E` matter、`#5FD08A` PASS、`#E5687A` sealed。标题用编辑式 old-style serif，
数字、坐标和状态用等宽字体。图形母题固定为“稀疏规则空间格点 + 可测边界 + 三个锚点”；
禁用行星、银河、火箭、原子轨道、AI 大脑、芯片纹和泛科技六边形。

颜色必须服从科学语义：视觉 PASS 不是科学 PASS，状态色不得越权表达实验裁定。冻结的 v1
`docs/` 证据链不追溯换肤；只更新当前入口和 v2 活跃材料。

以下 **R25 pre-M3** 状态与阅读顺序是 v1 历史约束，不是当前 v2 进度。仍不得把局部符号
PASS 宣告为 v1 M3，也不得把单个 GR-compatible 构造描述为宽规则空间中的 GR 涌现。

权威阅读顺序：

1. `docs/status/阶段复盘-2026-07-24-M3与主线校准.md`
2. `docs/status/主线-实施计划-北极星.md`
3. `docs/status/HANDOFF_02_结果总账.md`
4. 当前任务对应的 `docs/preregistration/` 与 `docs/reports/`

## 仓库纪律

- 保留用户未提交改动；禁止 `git reset --hard`、批量删除或覆盖实验资产。
- `experiments/` 中 CP1/R25 等脚本包含 SHA 证书链。仅为美化路径不得改写其内容。
- `experiments/*.json`、`experiments/figs`、`experiments/campaigns` 是兼容链接；真数据在 `data/`
  和 `visualizations/`。不要复制成双份。
- 新结果写入 `data/results/`，新图写入 `visualizations/figs/`；v2 新报告写入 `docsv2/`，
  冻结的 v1 `docs/` 只保留历史证据链。
- `data/runtime/` 是可恢复运行态；reset 操作具有删除语义，除非用户明确要求，不得执行。
- 核心包暂留 `rulespace/`、`rulespace_gpu/` 顶层以保护导入和模块运行契约，不要擅自搬入 `src/`。

## 科学判定纪律

- M3 必须是同一实空间构造、同一次运行通过全部预注册门和证伪炮。
- M4 必须在包含非 GR 候选的参数族中证明存活者非空、非孤点，才能恢复“规则空间涌现”强主张。
- Maxwell/Einstein/Yang–Mills 主要是投影后的 IR judge；不能把全部连续方程逐项硬编码后仍称涌现。
- 约束分 H（硬门）、S（结构先验）、E（探索残差）；弦论/高维数学默认属于 S，不自动属于 H。
- 任何数字必须能指向脚本与 JSON；任何失败不得用修改阈值掩盖。

## 验证最低线

按改动风险选择：

```bash
python -m compileall -q rulespace rulespace_gpu rulespace_v2 experiments tools
python -m rulespace_gpu.verify
git diff --check
```

涉及某条证书链时，只运行对应的小规模证书或 `--help/status` 探针；不要为了“整理”擅自重跑昂贵长跑。
所有面向用户的阶段汇报和 UI 文案使用中文。
