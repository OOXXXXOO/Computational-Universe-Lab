# CLAUDE.md

本文件给 Claude Code 提供仓库级工作约束。先读同目录的 `AGENTS.md`；两者冲突时，以
`AGENTS.md` 和用户最新指令为准。

## 视觉系统

一级品牌为 **Computational Universe Lab**，副标题为 **Projective Rule-Space Program**。
后续所有新生成材料共同引用：

- `visualizations/assets/logo.png`
- `visualizations/assets/repo_cover.png`
- `visualizations/dashboards/program_atlas.html`
- `docsv2/v2-设计规范-Computational-Universe-Lab视觉系统与图像生成提示词.md`

基调是克制、编辑式、可审计的科学图册：深黑底 `#0B1013`，青绿 `#45D4C6` 只表示几何、
测量与边界，琥珀 `#E7A24E` 只表示物质/能量，绿色 `#5FD08A` 只表示真实 PASS，封存红
`#E5687A` 只表示已裁定边界。标题用 old-style serif，数字与状态用等宽字；主图形使用
“规则空间格点 + 可测边界 + 三个锚点”。禁止用行星、银河、火箭、原子轨道、AI 大脑、
电路板或六边形 HUD 代替研究母题。视觉 PASS 不等于科学 PASS；冻结的 v1 `docs/` 不追溯
换肤。

## 项目是什么

这是“投影规则空间纲领”的计算物理实验仓库，不是产品工程。研究目标是在严格局域的
quantum-unitary QCA 本体主线中，
用数学自洽、Maxwell/Einstein/Yang–Mills 与真实 3+1D 实验做 QA 剪枝，寻找投影后涌现场论的
规则等价类，同时保留可诊断的高维投影残差。classical-symplectic 只作分栏的结构探针与
构造预飞，不能替代 quantum L4。

以下 **R25 pre-M3** 是 v1 历史状态，不是当前 v2 进度：

- 一般 walk 壳上的 Laurent/de Donder/detour complex 已闭合；
- auxiliary Wilson 与静态 Newton 有候选证书；
- 完整实空间 step、可用约束收缩率、moving source、动态 Newton/Eddington、live conservation、
  sponge/endurance、证伪炮和 M4 参数族尚未完成；
- R25 是 GR-compatible 存在性构造，不得写成“GR 已从宽规则空间涌现”。

v1 历史入口：`docs/status/阶段复盘-2026-07-24-M3与主线校准.md`。

> **状态覆盖（2026-07-30，纲领 v3 生效）**：v1 北极星继续封存，v2 M3′
> `HALT-PILOT-UNRESOLVED` 作为历史事实保留。当前权威入口为 `docsv3/README.md`；
> 依次读取 v3 北极星、v3 裁定、observer-collapse coisometry 勘误、
> application-scenario/typed-termination 勘误、V3-M0 任务书和实施计划。`docs/` 冻结为 v1 历史，
> `docsv2/` 保留 v2 证据链，不追溯改写。

当前活跃战役为 **V3-M0 / 双轴仪器迁移**。仅实施 construction trace、matched ablation、
共同响应链、`ε_causal`、`δ_geom`、`σ`、形式化 no-go 与 synthetic controls；最高状态
`READY-V3-M1-ANCHOR-CERTIFICATION`。R30/R23/R25 物理重测、新 family、Round 0、
30 格 pilot、正式 `10²–10³` 扫描与 GPU 长跑均继续锁定。
Task 12–17 必须区分成功 block、预期 typed termination 与独立 analysis control；
C11/C13/C14/C20 的预期 undefined/series 不得被伪装成成功响应块。

底层候选空间仍是
`target_spec × 复形族 × 物质耦合 × 微观规则参数`；三坐标只是观测坐标。当前 spin 2
曲率仪器切片不得缩窄 spin 0、Maxwell、Einstein 与未来 Yang–Mills 的多目标主线。
任何参数或系数经 target-aware 设计、搜索、筛选或人工择优后必须记为
`target_conditioned`，不得用 numeric literal 洗白。

## 诚实边界

- 这是一个 Git 仓库；工作树可能包含用户尚未提交的实验资产，禁止擅自清理或重置。
- 没有统一的传统单元测试框架。验证分为语法/导入检查、符号证书、物理门和长跑复现。
- `data/results/*_results.json` 的 `PASS` 通常只代表该文件声明的局部门，不代表 M3。
- `visualizations/dashboards/dashboard_tensor.html` 和旧 tensor campaign 使用旧五参数 surrogate
  `(cg2,gamma,G,tr_sign,sigma)`，不能给 R25 背书。
- 固定 3+1D 是当前投影标定面，不是宇宙本体维度假设；动态维度排在固定 3+1D M3/M4 之后。

## 目录

- `rulespace/`：CPU/numpy 参考物理包。为保持导入契约暂留顶层。
- `rulespace_gpu/`：MLX/JAX/numpy 多后端包。为保持 `python -m rulespace_gpu...` 暂留顶层。
- `rulespace_v3/`：V3-M0 双轴仪器包；科学数值路径显式使用 numpy complex128，不走会
  自动选择 MLX fp32 的 backend。
- `experiments/`：历史与当前独立实验脚本；保持平铺以保护脚本间 import 和冻结 SHA。
- `data/results/`：JSON 结果真文件；`data/campaigns/`、`data/sealed/`、`data/runtime/` 分别存战役、
  封存数据和可恢复运行状态。
- `visualizations/`：dashboards、图件和图片资产。
- `docs/`：status、reports、preregistration、operations、engineering。
- `tools/`：campaign runner、server 等运维入口。

`experiments/` 中的 JSON、`figs`、`campaigns`、`rulespace*` 符号链接是迁移兼容层，不是重复数据。
不要把链接展开成副本，也不要在没有迁移证书计划时批量改写冻结科学脚本。

## 常用命令

```bash
bash setup_env.sh
source .venv/bin/activate
export RULESPACE_BACKEND=jax

python -m rulespace_gpu.verify
python -m rulespace_gpu.benchmark
python experiments/exp1_dirac_qca.py
python experiments/r25_laurent_complex.py

python tools/campaign_server.py
python tools/campaign_runner.py status
python tools/tensor_campaign_runner.py status
```

机器精度证书用 jax/numpy fp64；MLX 主要用于大规模动力学，不能用 fp32 结果宣称 `1e-12` 级门。

## 工作规则

1. 先读当前阶段复盘、北极星计划、相关预注册和结果总账，再改科学代码。
2. 新候选只有同时具备符号证书、统一实空间 evaluator、state schema/dashboard，才可进入 M 阶段。
3. 报告区分定理/符号证书、数值实证、代理判据和工程状态；负结果同样入总账。
4. 科学脚本原则上写入 `data/results/`；旧脚本通过 `experiments/` 兼容链接落到该目录。
5. UI、阶段汇报和项目文档使用中文。
6. 改 engine 后至少运行 numpy/jax 验证；长跑前先做小规模 compose 和负控。
7. v3 L4 只归属于从含非目标候选族经 QA 剪出的 target-blind matched-ablated
   representative；带冗余目标编码的 actual 不能凭几何正确冒充强涌现主张。
