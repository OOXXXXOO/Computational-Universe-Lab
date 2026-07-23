# 投影规则空间纲领 · 计算宇宙实验室

这是一个以实验剪枝为核心的 QCA/计算物理研究仓库。当前北极星是在固定 3+1D 投影中，让
Einstein/自旋 2 通道通过完整动力学 QA；Maxwell 是正控，Yang–Mills 是后续非阿贝尔推广。

## 当前状态

**R25 pre-M3，不是 M3 已完成。** 一般 walk 壳上的局域规范复形、auxiliary Wilson 和静态
Newton 已有候选证书；完整实空间闭环、moving source、动态 Newton/Eddington、约束率、
sponge/endurance、证伪炮与 M4 参数族仍未完成。

先读：

1. [阶段复盘](docs/status/阶段复盘-2026-07-24-M3与主线校准.md)
2. [北极星实施计划](docs/status/主线-实施计划-北极星.md)
3. [结果总账](docs/status/HANDOFF_02_结果总账.md)
4. [工程布局说明](docs/engineering/REPOSITORY_LAYOUT.md)

## 目录

| 位置 | 内容 |
|---|---|
| `rulespace/` | CPU/numpy 参考物理包 |
| `rulespace_gpu/` | MLX/JAX/numpy 多后端物理包 |
| `experiments/` | 独立实验与证书脚本，原字节迁移以保护 SHA |
| `data/results/` | 所有 JSON 结果真文件 |
| `data/campaigns/`、`data/sealed/` | campaign 与封存数据 |
| `data/runtime/` | runner 可恢复状态 |
| `visualizations/dashboards/` | 交互实验室和 dashboard |
| `visualizations/figs/` | PNG/GIF/MP4 图件 |
| `docs/` | 状态、报告、预注册、操作和工程文档 |
| `tools/` | runner 与本地观测服务 |

## 快速验证

```bash
bash setup_env.sh
source .venv/bin/activate
export RULESPACE_BACKEND=jax

python -m rulespace_gpu.verify
python experiments/exp1_dirac_qca.py
python experiments/r25_laurent_complex.py
```

运行仪表：

```bash
python tools/campaign_server.py
# 浏览器打开 http://localhost:8765/
```

张量旧 campaign 与 R25 不是同一 payload。旧 dashboard 中的 1,470 个 `lawful_tensor` 只属于
`(cg2,gamma,G,tr_sign,sigma)` surrogate，不能作为 R25 通过证据。

## 研究纪律

- 已验证物理分为硬门 H、结构先验 S、探索残差 E；实验定律约束投影后的 universality class，
  不逐格指定唯一 UV rule。
- `*_results.json` 的 PASS 只代表该文件声明的门；M3 必须由统一实空间运行一次性通过。
- 负结果、修正和无效运行与正结果同等记录。
- 固定 3+1D 是当前可检验投影，不是本体维度宣言；动态维度排在固定 3+1D M3/M4 之后。
