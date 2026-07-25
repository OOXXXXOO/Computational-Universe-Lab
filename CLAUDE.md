# CLAUDE.md

本文件给 Claude Code 提供仓库级工作约束。先读同目录的 `AGENTS.md`；两者冲突时，以
`AGENTS.md` 和用户最新指令为准。

## 项目是什么

这是“投影规则空间纲领”的计算物理实验仓库，不是产品工程。研究目标是在局域 QCA 规则空间中，
用数学自洽、Maxwell/Einstein/Yang–Mills 与真实 3+1D 实验做 QA 剪枝，寻找投影后涌现场论的
规则等价类，同时保留可诊断的高维投影残差。

当前状态是 **R25 pre-M3**，不是 M3 完成：

- 一般 walk 壳上的 Laurent/de Donder/detour complex 已闭合；
- auxiliary Wilson 与静态 Newton 有候选证书；
- 完整实空间 step、可用约束收缩率、moving source、动态 Newton/Eddington、live conservation、
  sponge/endurance、证伪炮和 M4 参数族尚未完成；
- R25 是 GR-compatible 存在性构造，不得写成“GR 已从宽规则空间涌现”。

当前权威入口：`docs/status/阶段复盘-2026-07-24-M3与主线校准.md`。

> **状态覆盖(2026-07-26,纲领 v2 生效)**:v1 北极星(自旋 2 涌现 M3)已正式封存
> (`docs/status/阶段封存-2026-07-26-可达性战役收束-自旋2M3结构性不可达.md`);
> 纲领升级为 v2"涌现边界制图",**当前权威入口移至 `docsv2/README.md`**
> (主张阶梯、M0′–M4′ 门、D1–D5 裁定、M0′ 任务书)。`docs/` 冻结为 v1 历史与证据链,
> 只加状态行不改史;上文"当前状态"段保留为 v1 历史描述。

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
