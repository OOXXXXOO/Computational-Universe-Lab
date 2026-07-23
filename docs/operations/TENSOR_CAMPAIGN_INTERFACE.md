# 张量战役 — 两车道界面契约

*两条并行车道的收敛点。车道A(工程二,你写):批量快筛核 + J5 引力波速列。车道B(我写):长跑 harness + dashboard + 实时可视化。此文件是唯一的耦合面——改它需两边同意。*

## 架构(和标量战役同构的两级制)

```
prior 采样(N 条张量规则参数)
      │
  ① 批量快筛   screen_tensor_rules(params_batch)      ← 车道A,GPU 批量,便宜
      │        返回每条规则的廉价代理判据 + J5 列
  幸存者(低存活率)
      │
  ② 完整复判   tensor_qca.evaluate_tensor_rule + emergence_judge.judge_emergence  ← 现成,串行
      │        TT 2自由度 / 牛顿 h00φ=2 / 偏折2 / N_prop=2(无投影)/ 规范压制
  lawful_tensor 幸存者 → 存活流形 + best
```

harness(车道B)负责 ①→②→累计→checkpoint/resume/控制/dashboard,**不做物理判据**;物理判据全在 ①(车道A)和 ②(现成)。

## 界面 ①:批量快筛核(车道A 提供)

```python
def screen_tensor_rules(params_batch, quick=True) -> dict[str, np.ndarray]:
    """params_batch: (Bn, P) host float array, columns = PARAM_NAMES。
       返回长度 Bn 的 per-rule 数组(与 campaign.sweep / tensor_qca.evaluate_tensor_rule 同风格)。"""
```

**约定的输出列(harness 依赖这些名字,缺的给 NaN/False):**
| 列 | 类型 | 目标 | 含义 |
|---|---|---|---|
| `passes_screen` | bool | — | 快筛总判(harness 用它挑幸存者送二级) |
| `stable` | bool | — | 稳定/幺正/有界 |
| `tt_dof` | int | 2 | 廉价传播自由度代理 |
| `gw_speed` | float | 1.0 | **J5 引力波速 c_gw/c(第一天就有的列)** |
| `gw_speed_ok` | bool | — | \|gw_speed−1\| < tol(tol 车道A 定,建议 1e-2) |
| `newton_proxy` | float | 2.0 | 廉价 h00/φ 代理(可选) |
| `emergence_proxy` | float | 2 | 廉价 N_prop 代理(可选) |

- `PARAM_NAMES`: 车道A 定义(张量规则参数空间的列名),harness 只按位置/名字透传、不解释。
- `sample_tensor_prior(n, seed) -> (n, P)`:物理形状先验采样器。**建议车道A 提供**(类比 `random_couplings`);若不提供,harness 用均匀/对数均匀兜底(次优)。

## 界面 ②:完整复判(现成,harness 调用)

harness 对快筛幸存者逐条(或小批)调用现成的:
- `tensor_qca.evaluate_tensor_rule(params_batch)` → passes / tt_dof / newton_ratio / deflection / gauge_resid …
- `emergence_judge.judge_emergence(params_batch, step_factory=...)` → n_prop / gauge_decay / passes_emergence …

**需车道A/现成方确认的接线点**:二级复判用哪个 `step_factory`(候选张量规则如何构造成 emergence_judge 能演化的 step)。若快筛核已含"参数→step 工厂",harness 直接复用。

## 界面 ③:harness → dashboard 的 state.json(车道B 内部,已定)

harness 每 checkpoint 原子写 `data/runtime/run_tensor/state.json`,字段镜像标量版 + 张量列:
`status/rules_done/wall/batches, screened, stable, tt2(=tt_dof==2), gw_ok, lawful_tensor(二级全过), *_pct, manifold(存活参数分布), best(参数+各判据数值), history[]`。
dashboard(车道B)读它;live viz 用 best 的参数在浏览器 GPU 实时演化 TT 引力波(h₊/h×)。

## 待确认清单(两边拍一下就收敛)
1. 快筛核**函数名/签名**是否用 `screen_tensor_rules(params_batch, quick=True)`?
2. `PARAM_NAMES`(张量规则参数列)是什么?
3. **J5 列名**定为 `gw_speed`(c_gw/c,目标 1.0)+ `gw_speed_ok`?tol 多少?
4. 二级复判的 `step_factory` 由快筛核提供,还是 harness 现搭?
5. 先验采样器 `sample_tensor_prior` 谁提供?

*车道B 先按本契约 + 桩实现跑通编排;上面 5 条任何调整,改这里 + 换 harness 里一行 import 即可。*

---

## 车道A 回执(2026-07-20,已实现并双后端验证)

**接线:`from rulespace_gpu.tensor_batch import screen_tensor_rules, sample_tensor_prior, PARAM_NAMES, GW_TOL` 换掉 stub import 即可。** 契约自测(numpy↔jax 逐表一致):good(cg2=1 光锥规则)全过;无迹反转判伪器 newton_proxy=4.000 被 S2/S3 双杀;慢引力子(cg2=0.25→gw_speed 0.421)唯 gwOK 杀;CFL 违规爆炸即死。先验漏斗 64→12 pass(18.8%,和你桩假设的 15.7% 同量级)。

**5 问逐条:**
1. **签名**:`screen_tensor_rules(params_batch, quick=True, c_matter_rel=1.0, jit=True)`——前两参完全按契约;`c_matter_rel` 是可选校准旋钮(物质速/格点光速,walker 扇区实测 v/c≈0.993 时传它,默认 1.0),harness 透传或忽略均可。
2. **`PARAM_NAMES = ["cg2","gamma","G","tr_sign","sigma"]`**(=tensor_qca 的)。语义注意:**tr_sign ∈ {1, 0}**(1=正确迹反转,0=破坏=证伪对照),对齐 tensor_qca 的 tr_sign=0 判伪约定——**不是 ±1**,你桩里已经是对的。
3. **J5 列名确认 `gw_speed`(目标 1.0)+ `gw_speed_ok`;tier-1 tol = `GW_TOL` = 0.05**(不是 1e-2:tier-1 波包速度测量的系统误差地板就在几个百分点;定义为 与 cg2=1 参考规则同协议实测速度之比,色散系统误差一阶抵消)。**tier-2 收紧到 1e-2**:用 null-box 实测群速(你们已有 0.991)对 walker 物质速(0.993)之比,那里测量精度够。两级 tol 分工写死在此。
4. **step_factory:现成方(tensor_qca)提供,harness 直接接**;快筛核不提供(职责分离:tier-1 是代理判据,不是规则本体)。总账 43f 已注明 `judge_emergence` 批接口支持外部 step_factory、43c 注明 `evaluate_tensor_rule` 可插 runner。
5. **`sample_tensor_prior(n, seed)` 车道A 已提供**(tensor_batch 内):cg2∈10^U(−1,0.1)(**含物理目标 cg2=1**;快筛核内部 dt 子循环把 3D CFL 上限从 1/3 解放到 4/3,光锥规则可筛),gamma∈10^U(−2.5,−0.8),G∈10^U(−3,−1),tr_sign P(1)=0.85,sigma∈U(1.5,3.5)。

**输出列**:契约 7 列全给(`newton_proxy` 目标 +2.0,内部判 cg2·h00/φ=−2 后取负号报出);另透传原始诊断列 `tt_speed/tt_retention/gauge_growth/newton_conv/deflection_ratio/S1_tt/S2_newton/S3_eddington/J5_gw`,dashboard 可直接画漏斗。

**成本参考**:64 规则 CPU ~4s(quick);MLX 上预期 ≥10×。`passes_screen = S1∧S2∧S3∧J5`(J5 第一天入总判,这是纲领论点本身)。

---

## 车道A 标定拍板(2026-07-20,回应 小报告-tier1-tier2标定失配)

**决定:(a) 为主,(b)(c) 我侧已同步修完。** 原则:两级必须共享同一离散化——tier-2 加子循环,不是 tier-1 退回 CFL<1/3(那会把物理目标 cg2=1 永久锁在搜索域外,本末倒置)。

### (a) tensor_qca 子循环约定(逐字对齐 tensor_batch,勿改常数)

```
SUB  = 0.5          # dt' = SUB * dt
SUB2 = 0.25         # = SUB^2

每个 leapfrog 步的系数替换:
  cg2_sim   = SUB2 * cg2        # 波刚度
  gamma_sim = SUB  * gamma      # 一阶阻尼/约束项
  src_sim   = SUB2 * src        # 源项(含 16πG T_μν 整体)

回折规则:
  速度:   v_phys = v_sim / SUB          (或等价地 T_sim = T_phys/SUB 步覆盖同一物理时长)
  弛豫:   收敛所需步数 ×(1/SUB2) = 4     (牛顿扇区步数预算相应抬)
  振幅:   静态不动点为物理振幅(SUB2 在 src 与 cg2 间约去)
          ⟹ 一切 cg2·h/φ 型判据公式照旧用【物理 cg2】,阈值全部不变
  稳定域: 物理 cg2 < (1/3)/SUB2 = 4/3
```

坑提示:只把 cg2 换成 cg2_sim 而忘了 src 同乘 SUB2,井振幅会虚高 4×,fact2 的 1/r 相关不受影响但幅度判据会错;两处必须一起换。

### (b) 已修(tensor_batch,我侧)

先验 G 下限抬高 1e-3 → **1e-2**(G∈10^U(−2,−0.7)):tier-2 的 1/r 相关判据是 SNR 受限的,G<1e-2 的井它原理上测不出;tier-1 的比值判据无标度、放过了它们——这是口径差不是物理。你们 fact2 空窗优雅 fail 的前置修法我认可。

### (c) 已修(tensor_batch,我侧)

quick=False 的 S3 失败复现并追因:不是 cg2=1 特有,是我的偏折比含 /n 有限振幅修正,随 L 漂移(good 规则 1.78@L20→1.63@L32)——pathB 当年同一课重犯。已改为线性化 Born 比:**good 两档均精确 2.000,判伪器精确 4.000**,numpy↔jax 一致。tier-2 仍用 tensor_qca 正判,不用 quick=False 替代。

### compose 验收线(两级串联,放 10⁵ 前必须过)

1. 金标准探针 `[1.0, 0.05, 0.02, 1, 2.5]` 必须端到端 lawful_tensor=True;
2. 判伪探针 `[1.0, 0.05, 0.02, 0, 2.5]` 必须端到端 False(tier-1 已杀;若人为直送 tier-2 也须 FAIL——两级都有牙的证明);
3. 1024 条先验:tier-1→tier-2 转化率 > 0 且 lawful_tensor > 0(健康带预期 O(10%–40%) 转化;若 >80% 说明 tier-2 判据松了,同样要报);
4. resume 逐位一致重跑一遍(子循环改动后)。

过线即放 10⁵。
