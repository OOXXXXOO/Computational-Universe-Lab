# 仓库布局与 2026-07-24 整理记录

## 目标

把过去堆在根目录的科学代码、文档、数据和可视化资产分离，同时不破坏冻结实验脚本的 SHA、
脚本间平铺 import、结果引用和可恢复 campaign 状态。

## 迁移规则

| 原资产 | 新位置 |
|---|---|
| 根目录独立实验 `*.py` | `experiments/` |
| 根目录 `*_results.json` 等 | `data/results/` |
| `campaigns/`、`sealed/` | `data/campaigns/`、`data/sealed/` |
| `run/`、`run_tensor/` | `data/runtime/` |
| `figs/`、HTML、根目录 PNG | `visualizations/` |
| handoff/主线/纲领/复盘 | `docs/status/` |
| 报告/定理笔记/追溯 | `docs/reports/` |
| 预注册 | `docs/preregistration/` |
| runner/server | `tools/` |

## 为什么 `rulespace/` 和 `rulespace_gpu/` 没搬

它们是可导入包，现有复现命令依赖 `python -m rulespace_gpu...`。在没有 `pyproject.toml`、安装包迁移
和全后端对拍之前搬入 `src/` 会扩大风险，因此刻意保留顶层。这是导入边界，不是整理遗漏。

## 兼容链接

`experiments/` 保持科学脚本原字节，并提供指向 `data/results/`、`visualizations/figs/`、
`data/campaigns/` 和核心包的符号链接。原因是 CP1/R25 证书链包含源码 SHA，直接改写脚本的路径常量
会使历史证书失配。

真文件只有一份；链接不得复制展开。新实验不应继续依赖这种历史兼容层，应直接使用规范目录。

## 根目录允许项

根目录只保留 README、代理约束、环境/依赖入口、两个核心包，以及分类后的顶层目录。新的实验、
JSON、报告和图片不得重新落回根目录。
