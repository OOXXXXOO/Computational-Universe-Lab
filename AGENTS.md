# AGENTS.md

## 当前任务边界

本仓库当前处于 **R25 pre-M3**。默认先维护研究仪器和证据链，不得把局部符号 PASS 宣告为 M3，
也不得把单个 GR-compatible 构造描述为宽规则空间中的 GR 涌现。

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
- 新结果写入 `data/results/`，新图写入 `visualizations/figs/`，新报告按类型写入 `docs/`。
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
python -m compileall -q rulespace rulespace_gpu experiments tools
python -m rulespace_gpu.verify
git diff --check
```

涉及某条证书链时，只运行对应的小规模证书或 `--help/status` 探针；不要为了“整理”擅自重跑昂贵长跑。
所有面向用户的阶段汇报和 UI 文案使用中文。
