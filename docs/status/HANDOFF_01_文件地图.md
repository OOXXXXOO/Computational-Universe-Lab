# 文件地图：整理后的权威导航

*2026-07-24 工程整理后更新。布局原理见 `../engineering/REPOSITORY_LAYOUT.md`。*

## 阅读顺序

| 目的 | 文件 |
|---|---|
| 当前状态、M3 卡点、主线校准 | `阶段复盘-2026-07-24-M3与主线校准.md` |
| 北极星与升级纪律 | `主线-实施计划-北极星.md` |
| 每条定量结论 | `HANDOFF_02_结果总账.md` |
| 下一步顺序 | `HANDOFF_03_路线图.md` |
| 总纲领与 H/S/E 分层 | `纲领-投影规则空间物理.md` |
| 文档分类总入口 | `../README.md` |

## R25 pre-M3 当前前沿

| 层 | 脚本 | 结果 | 报告/预注册 |
|---|---|---|---|
| Laurent/Floquet | `experiments/r25_laurent_complex.py` | `data/results/r25_laurent_results.json` | `../preregistration/预注册-R25-Laurent模与walk-compatible复形.md` |
| walk de Donder | `experiments/r25_walk_dedonder_complex.py` | `data/results/r25_walk_complex_results.json` | `../reports/小报告-R25-首轮符号结果与UV节点.md` |
| detour complex | `experiments/r25_detour_complex.py` | `data/results/r25_detour_results.json` | 同上 |
| UV exceptional set | `experiments/r25_uv_exceptional_audit.py` | `data/results/r25_uv_exceptional_results.json` | 同上 |
| auxiliary Wilson | `experiments/r25_auxiliary_wilson_complex.py` | `data/results/r25_auxiliary_wilson_results.json` | 阶段复盘 |
| static Newton | `experiments/r25_static_newton.py` | `data/results/r25_static_newton_results.json` | 阶段复盘 |
| dynamic symbol | `experiments/r25_dynamic_symbol.py` | `data/results/r25_dynamic_symbol_results.json` | 阶段复盘 |
| 行业查新 | — | — | `../reports/小报告-R25-deep-research-walk-compatible复形.md` |

这些是局部证书，不是统一 M3。当前不存在 `evaluate_r25_candidate`、`run_r25/state.json` 或
R25 dashboard。

## 代码

- `rulespace/`：CPU/numpy 参考包，含 core、judges、campaign、discover、render。
- `rulespace_gpu/`：多后端包，含 backend、engine、verify、benchmark 和张量判据。
- `experiments/`：exp1–exp8、标量引力 r2–r7、自旋 2 R9–R25、CP1-v4 和动画生成脚本。
- `tools/`：可恢复 campaign runner、tensor runner 与本地 dashboard server。

历史科学脚本保持平铺以保护 import 和 SHA；不要仅为风格继续拆子目录。

## 数据

- `data/results/`：所有根级 JSON 结果真文件。
- `data/campaigns/`：批量搜索记录。
- `data/sealed/`：54M 标量战役等封存资产。
- `data/runtime/run/`：标量 runner 状态。
- `data/runtime/run_tensor/`：旧张量 surrogate runner 状态（106,496 条/1,470 存活）。
- `data/cache/`、`data/logs/`：可再生缓存与日志。

## 可视化

- `visualizations/dashboards/dashboard.html`：标量 campaign console。
- `visualizations/dashboards/dashboard_tensor.html`：旧张量 surrogate console。
- `visualizations/dashboards/dashboard_ladder.html`：CP1-v4 装配阶梯。
- `visualizations/dashboards/lab.html`：早期交互实验室。
- `visualizations/dashboards/program_atlas.html`：纲领图谱。
- `visualizations/figs/`：实验图、GIF 和 MP4。
- `visualizations/assets/`：封面和生成位图。

启动：`python tools/campaign_server.py`，浏览器访问 `http://localhost:8765/`。

## 文档

- `docs/status/`：阶段真相与总账。
- `docs/reports/`：报告、定理笔记与追溯。
- `docs/preregistration/`：冻结门与证伪炮。
- `docs/operations/`：运行与协作说明。
- `docs/engineering/`：目录与迁移约定。

## 环境与最低验证

```bash
bash setup_env.sh
source .venv/bin/activate
export RULESPACE_BACKEND=jax
python -m rulespace_gpu.verify
python -m compileall -q rulespace rulespace_gpu experiments tools
git diff --check
```
