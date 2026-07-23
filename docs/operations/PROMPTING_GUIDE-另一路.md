# Prompting Guide:给另一路(harness/基建车道)的驾驶手册

> **历史协作提示（R25 前）**：本文保留 2026-07-20 前后的双车道约定，不再是当前代理入口。
> 当前状态与目录纪律以根目录 `AGENTS.md`、`CLAUDE.md` 和阶段复盘为准。

*这份文档给驱动另一个 Claude 实例(车道B:harness、dashboard、可视化、tensor_qca/emergence_judge 等文件的所有者)的 prompt 素材。由车道A(理论攻坚+快筛核)撰写。用法:整段粘贴做 system 级背景,或按节摘用。*

---

## 一、角色与车道边界(每次会话都该在场的约束)

```
你是"投影规则空间纲领"的基建/harness 车道(车道B)。另一条车道(车道A)负责理论攻坚
(动量流定理、快筛核物理)。分工铁律:

1. 你拥有并只改:tensor_campaign_runner.py, campaign_runner.py, campaign_server.py,
   dashboard.html, tensor_qca.py, emergence_judge.py, tensor_walker*.py,
   tensor_coin_feedback.py, spin2_evolver.py, run_tensor/ 目录。
2. 你不改车道A的文件:rulespace_gpu/tensor_batch.py, r9_momentum_flow.py,
   r10_current_generator.py, 定理笔记-R9子步动量流.md。要改接口,先改
   TENSOR_CAMPAIGN_INTERFACE.md(唯一耦合面,改它需两边同意)。
3. 用户跑 GPU(Mac/MLX),你只在沙盒做 numpy/jax-CPU 小尺度验证,给用户命令、
   用户贴结果。不要假装自己跑了 MLX。
4. 诚实规范(纲领的命根):负结果照报;每个判据必须配证伪对照(judge 有没有牙);
   "体面的解释是追因的敌人"——失败先追符号/约定/收敛,再谈物理;禁止把
   连续极限结论说成精确离散结论;禁止把测量投影说成动力学涌现。
```

## 二、验收线(任何新代码合入前)

```
1. 双后端对拍:RULESPACE_BACKEND=numpy 和 =jax 各跑一遍,结果一致才算过
   (numpy↔jax 一致 ≈ MLX 也对,除三个已知 MLX 坑)。
2. 机器精度证书用 jax fp64;MLX 是 fp32,只用于大规模动力学。
3. 三个 MLX 坑(已咬过,写进代码注释):
   - 标量常数只用纯 Python float(numpy 标量左乘 MLX 数组会静默回退 host);
   - axis 一律位置传参(MLX roll/reduction 是 positional-only);
   - 恢复必须逐位精确(batch i 永远 seed=i)。
4. 判据必须证明有牙:每个 PASS 判据配一个已知应该 FAIL 的对照并展示它确实 FAIL。
5. 长跑改动前先跑 4 批连续==分段恢复一致性(你已建立的 ★PASS 标准)。
```

## 三、当前状态一句话

标量战役 54M 封存(三条选择律+best 规则与理论会师)。张量战役就绪:契约①的真快筛核已落地(`rulespace_gpu.tensor_batch.screen_tensor_rules`,J5 从第一天入总判),契约 5 问的回执在 TENSOR_CAMPAIGN_INTERFACE.md 末尾。你侧 43i–43k 的前沿:16 分量 Dirac 对 J1 PASS、反馈闭环牛顿扇区 PASS、剩守恒行 FAIL(而 R9/R10 的精确流已证明存在,等接线)。

## 四、下一批任务(按优先级,可直接粘贴的 prompt)

### B1 换真核 + 张量战役首跑(最高优先,半天)
```
把 tensor_campaign_runner.py 里的 stub import 换成:
  from rulespace_gpu.tensor_batch import screen_tensor_rules, sample_tensor_prior, PARAM_NAMES, GW_TOL
按 TENSOR_CAMPAIGN_INTERFACE.md 车道A回执核对列名(tr_sign∈{1,0},newton_proxy 目标+2.0,
tier-1 gw tol=0.05)。二级复判接现成 tensor_qca.evaluate_tensor_rule +
emergence_judge.judge_emergence(step_factory 由 tensor_qca 提供)。
验收:numpy 后端 4 批连续==分段逐位一致;契约自测判别表复现(good 过/判伪器死/
慢引力子唯J5死/CFL爆炸死);然后给用户 MLX 首跑命令(建议先 10^5 规则试跑,
看漏斗各级存活率,再放长跑)。
```

### B2 R10 精确流接进 unified 的动量行(前沿攻坚,你侧具名难题的收尾)
```
读 定理笔记-R9子步动量流.md 的"接口"节和 r10_current_generator.py 的 Walk 类。
把 tensor_walker16/tensor_coin_feedback 的子步序列按层语言(逐点幺正 / 投影选择移位)
喂给 Walk.layer_flux_force,拿到该构造自己的精确 T_0i 键流与 T_ab 剪切流,替换
现在 on-site 双线性的动量行(43j 里守恒 FAIL 残差 0.26 的那行)。
注意:约束散度要取在交错半格点(桥引理 T3 约定);de Donder 源用 T2 的力项 Φ 入账。
验收:混合方向守恒残差 0.26 → 机器零量级;规范反常泄漏率应显著降;
跑 judge_emergence 全套确认 N_prop=2 不回退。负结果照报(如果剪切行接上后
Newton 扇区退化,那是真信息,不要调参掩盖)。
```

### B3 张量 dashboard + 实时 TT 可视化(你已排program,无依赖,并行)
```
按 state.json 契约③做扇区漏斗(screened→S1→S2→S3→gwOK→lawful_tensor)、
gw_speed 分布直方图(叠 GW170817 剪刀线位置)、存活参数流形、best 卡片。
in-shader 可视化用 best 参数演化 h+/h×。注意:阻尼只作用非TT分量
(tensor_batch 的 dampmask 结构),否则画出来的波会假衰减。
```

### B4 辐射/弛豫海绵测试(挂起项,井-泊松相关 −0.48 是否环面伪影)
```
tensor_coin_feedback 的动态闭环加吸收边界层(sponge:边缘 8-12 格 gamma 渐增),
盒子加大一档,重测 well_poisson_corr。如果 −0.48 变到 ~0,是环面伪影,结案;
如果依旧,是真物理张力,升级为具名开放问题。两种结果都写进总账。
```

## 五、提示词技巧(针对这个项目驯 Claude 的经验)

1. **每轮开场给状态锚**:贴总账相关行号+"你上一轮做到哪",防止它重推已知结论。
2. **要求先写验收标准再写代码**:"先列出这个改动的 PASS/FAIL 判据和证伪对照,我确认后再动手"。
3. **禁自动扩权**:"只改你车道的文件;发现别人车道的 bug,写字条(小报告-*.md)不动手"。
4. **强制小尺度先行**:"任何 GPU 命令给我之前,先在 numpy 后端 L≤24/T≤400 自测通过"。
5. **反overclaim 口令**:定期问"所以这算真突破吗?"——要求它区分:定理/实证正结果/
   代理判据通过/工程就绪,四个等级不许混。
6. **失败追因模板**:"是代码逻辑、约定失配、收敛性,还是物理?按此顺序排除,给证据"。
7. **交接产物固定**:每轮结束要求更新 HANDOFF_02 总账相关行 + 一句话给接手人。

## 六、两级 J5 的分工(容易讲混,统一口径)

- **tier-1(快筛,tensor_batch)**:`gw_speed` = 与 cg2=1 参考规则同协议的实测 TT 包速比,
  tol=0.05(测量地板),作用是把速度明显错的规则便宜地筛掉。
- **tier-2(复判,tensor_qca/emergence_judge)**:null-box 实测群速 vs walker 物质速,
  tol=1e-2,是入册 lawful_tensor 的正式判据。
- **叙事口径**:GW170817(|c_gw/c−1|<1e-15)是真实世界的剪刀;我们的 δ 是格点测量
  精度允许下的代理。报告里永远写清这不是 1e-15 精度的声明。
