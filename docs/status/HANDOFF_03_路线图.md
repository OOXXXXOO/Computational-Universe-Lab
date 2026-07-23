# 路线图:下一步(排优先级)+ 工程注意事项

*配套 `HANDOFF_00_交接总纲.md`。前三份讲"到哪了",这份讲"往哪去"。*

> **2026-07-24 路线覆盖**：当前状态与唯一行动线见
> [`阶段复盘-2026-07-24-M3与主线校准.md`](阶段复盘-2026-07-24-M3与主线校准.md)第七节。
> 下面“建议三步走”保留为历史路线，不再是当前执行清单。

## 当前恢复顺序（R25 pre-M3）

1. 封存 R25 当前符号、UV、静态与动力学符号证书，不继续无仪表微调；
2. 先补 `evaluate_r25_candidate`、统一 state schema 和 R25 dashboard；
3. 再实现同一实空间 step，依次接 moving exact source、约束率、Newton/Eddington、sponge/endurance 与证伪炮；
4. M3 全绿后才开 R25 参数族战役与 M4 去孤岛；固定 3+1D 闭合后才展开动态维度。

旧 GPU/dashboard 基建仍可复用，但其旧五参数 payload 不认识 R25 的 walk shell、Laurent complex、
UV exceptional set 或 auxiliary sector，必须先换 evaluator/schema，不能直接重跑旧 campaign。

---

## 第一优先级:自旋2张量引力从规则涌现(真前沿)

**为什么是它:** 六波 + R7 三次独立确认了标量引力的天花板(EP仅超相对论、相对论物质不束缚、聚不出视界)。真引力需要自旋2张量场 h_μν,而它只在 3+1 维有传播自由度。这是纲领的"β=0 时刻"所在——做成,前面所有工作变成地基。

**验收测试已就位**(路B,`pathB_spin2.py`):任何候选张量构造必须复现——
1. graviton 恰好 2 个物理极化(TT投影 rank=2);
2. 弱场光偏折张量/标量 = 2.000(Eddington 因子)。

**建议的三步走(由易到难):**

1. ✓ **线性化张量场演化器(2026-07-19 完成)。** `rulespace_gpu/spin2_evolver.py`:10分量 h̄_μν 的 leapfrog 演化(□h̄_μν=−16πG T_μν)。三项验收全过(numpy fp64 + MLX):(a) TT 恰 2 自由度以 c 传播(格点 0.991=解析群速,gauge模不传播);(b) 牛顿极限 h_00/φ=2.000、复现 3D 1/r 稀释;(c) 光偏折 1.997→2.000。管线已动力学化、验收层就位。**注:这是已知线性化 GR 的离散实现,不是从规则涌现** —— 下面第 2 步才是真前沿。

2. **张量 QCA 规则。**(2026-07-19 进展)关键跃迁:让 h_μν 从一个**元胞自动机规则**涌现,而非手写波动方程。候选构造:多分量行走者 + 张量coin场,施加离散规范不变性(微分同胚的离散类比)⟹ 应当挑出 Fierz-Pauli 结构。用 C1b 式的裁判漏斗筛规则,J4 换成"复现路B验收测试"。
   - **首个候选已建**(`tensor_qca.py`):做出了**精确离散微分同胚算子** E_μν(对易中心差分,规范证书1.8e-15、纯规范=精确零模)—— 这是"为什么2自由度"在算子层的答案,且三判据全过 + 有证伪对照。但**诚实**:演化仍是谐和规范 leapfrog(同 spin2_evolver 类),2自由度仍由测量时 TT 投影选出,**尚非**多分量 walker+张量 coin。harness 分不清"手搭正确离散"与"涌现"。
   - ✓(a) **涌现判据已建成**(2026-07-19,emergence_judge.py):无投影 Riemann-能量 SVD 自由度计数 + 纯gauge动力学压制;两个手搭候选被判死(N_prop=6、规范反常36%);**最小涌现修复存在**(null-box+无滞后约束阻尼 → N_prop=2、规范反常机器零)。结构定理:演化/约束/规范必须共享同一套对易离散微分演算。过关线与批接口就绪。
   - **(b) 张量 walker 首构完成(诚实FAIL+决定性发现,tensor_walker.py)**:Weyl 对被自旋-动量锁死定理排除(共线无质量½+½最多helicity 1);**逃逸通道已实测**——手性加倍 Dirac 对 + 手性翻转双线性给出 TT 占比 0.987 的光锥波。
   - **下一步(明确三步)**:(0) 在 16 分量 Dirac 对上建全 10 分量观测映射,重跑三判据+涌现判据;(a) 用行走的精确格点守恒流修 de Donder 横向性;(b) 闭环——双线性=T_μν 作源驱动张量 coin 场(engine.py θ-反馈的张量版),补上自由行走**原理上不可能有**的牛顿/约束扇区;(c) 3+1D 旋转协变。全部可插 campaign_runner 长跑搜索(`evaluate_walker_rule` + `judge_emergence` 接口已对齐)。

3. **自洽非线性完成。** 自洽性(联合能量守恒+作用-反作用,复用五波的行走哈密顿能量框架)⟹ 非线性完成为爱因斯坦-Hilbert。检验:近日点进动、正确的强场行为。

**复用的脚手架**(标量扇区全部可搬):自洽源 F=−δE_w/δθ 框架、阴影能量守恒、几何稀释律、裁判漏斗、GPU引擎(engine.py 的行走者/场结构直接推广到多分量)。

**诚实预期:** 数月而非数轮。张量场每格点10分量,3+1维 256³ 只有 GPU 扛得住——引擎就是为此建的。

---

## 第二优先级:把三条路各自收成正式结果

**路A(冷物质自引力)——最接近发表:**
- 低 g 细扫(g∈{1,2,5,10,20})定出**弥散→束缚的临界耦合**(现在阈值只知道<20)。建议给 `pathA_sn_soliton.py` 加 `--glist` 参数。
- 存宽度**时间轨迹**(现在只存终点,而终点被孤子振荡相位污染,非单调);画"自由弥散 vs 孤子束缚"对比图。
- 孤子的**质量-半径关系**(S-N孤子的标度律),与已知 Schrödinger-Newton 文献对标。
- **维度对照**:同一 S-N 求解器在 1D/2D 跑,看束缚行为随维度变化——把稀释律的动力学版讲完整。

**路B:** 见第一优先级(它就是前沿的验收层)。

**路C(规则搜索):**
- 推到 10⁶(GPU 上 4616 规则/秒 → 10⁶ 约 3.6 分钟)。**注:** 目前 sweep 时间循环仍未 jit;10⁶ 或带完整漏斗时先把 per-step body 用 `B.jit`(mlx `compile`/jax `jit`)包住再跑。
- ✓ **GPU批量版 J3/J4 已实现**(2026-07-18):`rulespace_gpu/campaign.py` 现有 `sweep(..., full=True)`,批量 J1+J3+J4(reduced-law 2×2 Gram 闭式解,无 python 循环),`pathC_scale.py --full` 可surface。对拍 CPU 漏斗与 numpy↔mlx 一致(见结果总账)。缺的只是大N RUN。
- 存活流形边界的精细结构 / 稀有存活方向(10⁶ RUN 后分析)。

---

## 第三优先级:符号封顶 + 收尾

- ✓ **小ε解析证明**(2026-07-18 完成):`r6a_capstone.py` 用 SymPy 级数证明 R(k)=F/(tanθT00)=1+(cos²θ/12)k²+O(k⁴),阴影阶封闭。C1 连续极限定理符号封死。
- ✓ **补存 `r6a_capstone.py`**(2026-07-18 完成):自验 ALL PASS,写 `r6a_results.json`。
- Lean4 形式化定理陈述(可选豪华配置)。
- 若要成文:C1 标量引力已是完整故事(连续极限定理 + 诚实天花板),可先出一篇;新颖性定位见 `报告-实验⑦`。

---

## 工程注意事项(institutional knowledge,别踩重复的坑)

**1. MLX 的 numpy 标量强制回退(重要,已咬过一次)。**
> `inv = 1/np.sqrt(2)` 产生 `numpy.float64`;`numpy_scalar * mlx_array` 时 numpy 的 `__mul__` 赢过 MLX 的 `__rmul__`,**整个表达式静默回退成 host numpy ndarray**,后续 MLX 操作报类型错。
>
> **规则:任何常数标量用纯 Python float(如 `2.0 ** -0.5`),别用 numpy 标量。** engine.py/core.py 用 `INV2 = 1.0/math.sqrt(2.0)` 是对的;campaign.py 曾用 `1/np.sqrt(2)` 是唯一犯规处,已修。**新写批量 kernel 时最容易复发——检查每个左乘 MLX 数组的标量。**

**2. MLX 的 positional-only 参数。**
> MLX 的 `roll`(以及部分 reduction)签名里有 `/`,axis 必须**位置参数**,不能 `axis=`。numpy/jax 容忍 keyword,所以沙盒测不出来;jit 路径也容忍(编译时追踪),eager 路径才崩。`backend.roll` 已改成位置传参;`campaign.py` 的 mean/var/sum 也改成位置 axis。**新代码统一位置传 axis。**

**3. MLX 是 fp32 原生。**
> `backend.py` 给 MLX 设了 complex64/float32。做**机器精度**的守恒验证(如 T00 到 1e-14)必须用 `RULESPACE_BACKEND=jax`(CPU fp64)。大规模动力学/规则搜索用 MLX(快)没问题,精度 ~1e-6 够用。

**4. 后端逐位一致是验收线。**
> 任何新 kernel 写完,先 `RULESPACE_BACKEND=numpy` 和 `=jax` 各跑一遍 verify/对拍,确认结果一致,再上 MLX。numpy↔jax 一致 ≈ 保证 MLX(同 NumPy 式 API)也对(除上面三个 MLX 特有坑)。

**5. jit 加速规则搜索。**
> `rulespace_gpu/campaign.py` 的 sweep 时间循环没 jit(batch 轴已向量化)。10⁵ 够快(21.7s),但推 10⁶ 或加 J4 时,把时间循环也 jit(jax 用 `lax.fori_loop`,mlx 用 `mx.compile`)能再快几倍。

**6. 沙盒 vs 用户机器分工。**
> 开发方(如AI助手)在 Linux 沙盒只有 numpy/jax-CPU,**跑不了 MLX/CUDA**。分工:助手写代码 + 小尺度 jax 验证 + 给命令;用户在 Mac GPU 跑 + 贴结果。venv 必须在用户机器本地建(`setup_env.sh`),Linux 沙盒的 venv 同步过去是坏的。

---

## 一句话给接手人

标量引力这条线**已经完整且诚实地关闭**(是定理,也知道自己为什么不是GR)。所有精力应转向**自旋2张量场从规则涌现**——验收测试、脚手架、GPU引擎都已就位,缺的是那个能通过路B验收的张量QCA规则构造。那是纲领成败的唯一未决问题,而它良定义、有明确的第一步(线性化张量演化器)。
