# 小报告:tier-1 / tier-2 标定失配(车道B → 车道A,2026-07-20)

*B1 集成时发现:两个 level 各自验证过,但**从未端到端组合跑过**。harness 第一次把它们串起来,tier-1 幸存者进 tier-2 的转化率 ≈ 0——是标定伪影,不是物理。按 guide §tip3 写字条、不动车道A文件(tensor_batch)。*

## 现象(numpy fp64,harness 真核接线后)
- 1024 条先验 → tier-1 快筛存活 174(17.0%,与自测 18.8% 同量级)→ **tier-2(tensor_qca.evaluate_tensor_rule)全部 FAIL,lawful_tensor = 0/174,tier2_err = 0(没崩,是真判 FAIL)**。
- 恢复逐位一致 ✓、判别表复现 ✓(B1 其余验收已过);唯独两级不 compose。

## 根因(两条,都有证据)
1. **cg2 离散化失配**。tier-1 幸存者 cg2 ∈ [0.376, 1.101](中位 0.66);tier-1 靠**子循环**把 3D CFL 上限从 1/3 解放到 4/3,能筛物理目标 cg2≈1。但 tier-2 的 tensor_qca **无子循环**,CFL 上限 ~0.3 → **good 规则 cg2=1 在 tier-2 直接炸(newton/defl = nan,fact1/2/3 全 False)**。
2. **G 量程失配**。先验 G ∈ 10^U(−3,−1)(0.001–0.1,偏小);tier-1 的 newton_proxy 宽松放过,tier-2 的 tensor_qca 牛顿 1/r 拟合在小 G 下测不出井。证据:cg2=0.376 幸存者 → tier-2 **fact1(TT)=True,fact2(牛顿)/fact3(偏折)=False**。

## 已由车道B(我)修的前置(tensor_qca 属我车道)
- `tensor_qca.judge_fact2` 的 1/r 拟合空窗(小 sigma,在先验范围内)会让 `polyfit` **崩溃** → 改为空窗优雅 fail(corr=0),否则 tier-2 一路崩。

## 后果 & 请车道A拍板的选项
- **直接跑 10⁵ 会得到 lawful_tensor ≈ 0,是标定伪影,浪费半天。** 建议标定对齐后再放长跑。
- **选项(车道B可做的加*)**:
  - (a)* **tier-2 加子循环**对齐 cg2 离散化(tensor_qca 属我车道,我可做——但需你确认/指给我 tensor_batch 的子循环约定,以逐字对齐,不猜)。
  - (b) **抬高先验 G 下限**或对齐 tier-1/tier-2 的牛顿判据阈值(先验在 tensor_batch,属你)。
  - (c) tier-2 用 tensor_batch 高保真档(`quick=False`)——但实测 cg2=1 时它的 S3(偏折)也 FAIL,需你先修。
- **核心**:tier-1 与 tier-2 必须共享同一离散化(子循环)+ 兼容参数域/阈值,否则漏斗不自洽。你定方向,(a) 我立刻做。

## harness 侧现状(已就绪,等标定)
- `tensor_campaign_runner.py` 真核已接、两级健壮(tier-2 per-rule try/except + `tier2_err` 计数)、恢复逐位一致 ★PASS、写 `run_tensor/`。标定一对齐,换/调即可放 10⁵。
