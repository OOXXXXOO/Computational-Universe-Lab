# 投影规则空间纲领 · 计算宇宙实验室

这是一个以实验剪枝为核心的 QCA/计算物理研究仓库。当前北极星是在固定 3+1D 投影中，让
Einstein/自旋 2 通道通过完整动力学 QA；Maxwell 是正控，Yang–Mills 是后续非阿贝尔推广。

## 当前状态

> **状态覆盖（2026-07-26，可达性战役收束——正式封存）：** 三半验证（R36/R37）+ 车道A
> 复核后，PI 正式裁定：**纲领四承诺（精确约束传播 + 涌现物质 + 严格局域 + 酉）全要时，
> 自旋 2 的 M3 结构性不可达**——不可达死于极化计数与稳定性死锁（TT₂ 轴向 76.2° 对称
> 锁出，耦合家族无关；死锁标度性无调参走廊），不是残差本身（δ=12–18% 为 16³ 判据点
> 读数，48³ 已 2–4%）。R30 存在性定理、R26 清除机制（已在涌现走行上重认证）等正资产
> 不受影响；三放松候选定价保留；卡点④ 正式按住；后续主线待 PI 另裁。权威入口：
> [`阶段封存-2026-07-26-可达性战役收束`](docs/status/阶段封存-2026-07-26-可达性战役收束-自旋2M3结构性不可达.md)。
> 下文为 2026-07-24 状态，保留作历史。

**R25 pre-M3，M3 未过；前沿已移位到「可达性」（2026-07-24，R30）。** 决定性正面结果：
**局域酉的离散线性化-Bianchi 张量复形存在**（R30，已独立复核）——张量版 `div curl=0`
与 Maxwell 同为 κ 的多项式恒等式（机器零，形式无关），Yee 型演化严格酉、局域，
无投影 **N_prop=2 断崖**证得。Nielsen–Ninomiya 没有杀死自旋2复形。

**但这是存在性构造，不是涌现，不是 M3。** 该复形的 `U` 是**手搭的**局域剪切之积，
**不是从 QCA 规则涌现的 Dirac 走行**——「手搭正确离散 vs 涌现」的老区分在张量层重演。
**「复形存在」不可读作「引力涌现了」。** 前沿因此是**移位**而非关闭：

> 之前的开放阻塞（R25 走行动力学 N_prop=4–5≠2）隐含两个未知——复形是否存在 + 涌现走行
> 能否达到它。R30 把第一个答成 **YES**，R28 的 [4,4,4,4] 被精确重定位为「涌现走行不在
> 这个已证存在的复形内」。**新前沿 = 把涌现物质走行形变到这个已知存在、有验收判据的复形
> 上（= M3）**：风险从「存在性」降到「可达性」，但 M3 未解。

下一战役（形变涌现走行到 R30 复形）由 PI 单独起、单独定范围；卡点④ 单次联验在走行落到
复形、N_prop=2 之前无意义，按住。

先读：

1. [R30 独立复核：张量复形存在性证得](docs/reports/小报告-R30独立复核-张量复形存在性证得.md)（最新权威结论 + 边界）
2. [阶段封存：DOF 开放阻塞 + 正结果封存](docs/status/阶段封存-2026-07-24-DOF开放阻塞.md)（R30 之前的封存，前沿已移位）
3. [阶段复盘：M3 与主线校准](docs/status/阶段复盘-2026-07-24-M3与主线校准.md)
4. [北极星实施计划](docs/status/主线-实施计划-北极星.md)
5. [结果总账](docs/status/HANDOFF_02_结果总账.md)
6. [工程布局说明](docs/engineering/REPOSITORY_LAYOUT.md)

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
