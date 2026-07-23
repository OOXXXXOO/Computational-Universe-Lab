# R25 deep research：严格局域的 walk-compatible de Donder / gauge complex

*2026-07-24。承接 CP1-v4 L3-v3 的“演化壳—约束复形冲突”。本文只调查保持北极星原主张的路线：完整 walk 壳、严格有限支撑、线性规范秩 4、规范商传播自由度恰为 2；不以动量投影、Green 算子或放松 J5/DOF 代替构造。*

## 结论先行

截至本轮查新，没有发现业界已经完成如下组合：给定 3+1D 离散时间 QCA/Floquet 符号 `U_walk(k)`，构造一个严格局域、有限 stencil、与完整 walk 壳精确同源的线性自旋 2 de Donder/Calabi complex，并使一般壳点的规范商恰有两个传播自由度。

但最近工作给出了三块足够强的组件，令主线不再只能“猜修正差分”：

1. exact discrete de Rham / BGG complex 已能在一般多面体或立方网格上精确保留一部分 Einstein/Bianchi 约束；
2. curved-background compatibility complex 已被证明可以算法化构造，并具有“所有局域有限阶规范不变量都经第一 compatibility operator 因子化”的完备性意义；
3. 平移不变局域算子可转写为 Laurent 多项式矩阵，规范闭合与后续 compatibility operators 就是 syzygy 与 free resolution 问题。

因此下一步应当是：**不再给旧 `K_placed` 换一个标量波矢，而是同时求 `G_walk` 及其完整 syzygy complex。** 若所需生成元不可避免地含 Laurent 环以外的分母或无限支撑，这本身就是一个可核验的严格局域 no-go 证书。

## 一、最接近的直接进展

### 1. Oliynyk–Qian 2025：围绕 exact complex 构造 Einstein 演化

Oliynyk 与 Qian 将 3+1 Einstein 方程写成 exterior-calculus 系统，再以 ECDDR 离散 de Rham complex 在一般多面体网格离散。`d_h²=0` 使若干辅助约束得到精确的强/弱传播。论文也明确区分这种结构保持与 Z4/CCZ4/Z4c 的约束阻尼。

这项工作的直接意义是确认我们的架构判断：约束复形不能是演化器装好后的附加检测器，演化必须围绕 exact complex 共同构造。它仍不是现成答案：其空间是多面体有限元空间，时间推进并非给定的 QCA/Floquet walk，而且论文没有证明主 Hamiltonian/Einstein 约束 `(4.25a)` 的完全精确保留。

- Todd A. Oliynyk, Jia Jia Qian, “A polytopal discrete de Rham scheme for the exterior calculus Einstein’s equations”, *Physical Review D* (2025). [DOI](https://doi.org/10.1103/6t8n-rlld), [arXiv:2505.00286](https://arxiv.org/abs/2505.00286)

### 2. Bonizzoni–Hu–Kanschat–Sap 2024：立方网格 tensor-product BGG

该工作从一维 complexes 的张量积系统构造 cubical Hessian、elasticity 与 divdiv BGG sequences，并给出 bounded commuting interpolators 与 exactness。它为本工程 R19 的正则立方/交错布局提供了成熟母体。

但构造的硬条件是微分与连接映射满足交换关系

```text
D_{j+1} S_j = - S_{j+1} D_tilde_j.
```

我们的完整 `xyz` walk 壳来自非交换 SU(2) 轴步乘积；斜向的 Trotter 交叉项正是 L3-v3 中 ideal 半角壳与 `U_walk` 壳分离的来源。因此普通 tensor-product BGG 可以作为 IR 初值和对照，却不能原封不动吸收完整 walk。

- F. Bonizzoni, K. Hu, G. Kanschat, D. Sap, “Discrete tensor product BGG sequences: Splines and finite elements”, *Mathematics of Computation* (2024). [DOI](https://doi.org/10.1090/mcom/3969), [arXiv:2302.02434](https://arxiv.org/abs/2302.02434)

### 3. Christiansen–Hu 2022：vector-bundle curvature 与离散 Bianchi

该文在 vector bundles 上发展 finite element systems，并证明离散 Bianchi 型恒等式；平坦情形恢复离散 de Rham/cohomology。它说明“twisted/curved complex”有数学先行线，但并未处理 Floquet 符号或非交换轴序产生的特定 Laurent 结构。

- S. H. Christiansen, K. Hu, “Finite Element Systems for Vector Bundles: Elasticity and Curvature”, *Foundations of Computational Mathematics* (2022). [DOI](https://doi.org/10.1007/s10208-022-09555-x)

## 二、最关键的方法突破：compatibility complex 而非猜 de Donder 行

Aksteiner 等对黑洞背景的 Killing operator 构造了完整 compatibility complex，满足 `K_{i+1}K_i=0`。其核心完备性陈述是：任意局域有限阶 gauge invariant 都通过第一 compatibility operator 因子化。构造依赖 formal PDE、prolongation 与计算代数；一般曲背景不能靠一个通用的低阶修正自动得到 complex，而要针对背景重新求解。

对本工程的对应非常直接：

```text
规范参数 --G_walk--> 10 分量 h --K_curv--> 曲率/相容性数据 --> 后续 syzygies
```

L3-v3 的失败说明 classical `G(d)`/`K_placed(d)` 只与 ideal null polynomial 相容。完整 walk 壳改变后，正确问题是求一个在 Laurent 环上完整的 `G_walk` 与 `Syz(G_walk)`，不是挑四个“更像 walk”的 de Donder 行。

- S. Aksteiner et al., “Compatibility Complex for Black Hole Spacetimes”, *Communications in Mathematical Physics* (2021). [DOI](https://doi.org/10.1007/s00220-021-04078-y)
- I. Khavkine, “Compatibility complexes of overdetermined PDEs of finite type, with applications to the Killing equation” (2019). [arXiv:1805.03751](https://arxiv.org/abs/1805.03751)

## 三、严格局域性的边界：一般“可修”并不够

Kupferman–Leder 证明 elliptic pre-complex 可经零阶修正成为 complex，并建立 Hodge-like decomposition；但论文明确指出该修正一般是 pseudodifferential、依赖 Green operators，因而非局域。Garg–Dodin 的一般背景线性引力 gauge-invariant projector 同样依赖 Green operator。perfect-action/coarse-graining 路线可以恢复离散 gauge symmetry，但完美算子一般也获得长程耦合。

这排除了三种表面捷径：

- 不能用 FFT/动量逐点投影把 10 分量投到两维物理子空间；
- 不能用 `1/P_walk(z)` 或 `1/(K K*)` 修补约束；
- 不能把指数衰减但无限支撑的 perfect operator 称为“严格局域”。

平坦、常系数、平移不变是我们仍可能逃过一般非局域边界的特殊结构；必须在 Laurent 多项式层给出有限生成元。

- R. Kupferman, J. Leder, “Elliptic Pre-Complexes, Hodge-like Decompositions and Overdetermined Boundary-Value Problems”, *Forum of Mathematics, Sigma* (2025). [DOI](https://doi.org/10.1017/fms.2025.10)
- I. Y. Dodin, S. Garg, “Gauge invariants of linearized gravity with a general background metric”, *Classical and Quantum Gravity* (2022). [DOI](https://doi.org/10.1088/1361-6382/aca067)
- B. Bahr, B. Dittrich, F. Hellmann, W. Kaminski, “Coarse-graining free theories with gauge symmetries: the linearized case”, *New Journal of Physics* 13 (2011). [DOI](https://doi.org/10.1088/1367-2630/13/4/045009)

## 四、可计算的新表述：Laurent 模与 syzygy

令

```text
R = C[z_t^±1, z_x^±1, z_y^±1, z_z^±1].
```

任意有限时空 stencil 都是 `R` 上的矩阵。给定规范生成元 `G_walk(z): R^4 -> R^10`，第一 compatibility operator 的行就是左 syzygies：

```text
K_curv(z) G_walk(z) = 0.
```

后续 syzygies 给出 complex/free resolution。这样可以把四项此前混在数值 SVD 中的要求拆开验证：

1. 多项式恒等：`K_curv G_walk ≡ 0`；
2. 局域性：所有矩阵元都是 Laurent 多项式，记录实际 stencil 半径；
3. 一般壳点秩：曲率 compatibility complex 检查 exactness；gauge–equation detour complex 的同调才给出两个物理自由度；
4. 全 Brillouin 区异常：由 minors/Fitting ideals 检测额外 rank drop 与 UV cohomology。

Haah 对平移不变 stabilizer Hamiltonians 的 Laurent-module 方法并非引力先例，但其“局域算子 = free modules 之间的多项式映射、激发/约束 = kernel/cokernel”的计算语言高度同型，适合作为工具母体。

- J. Haah, “Commuting Pauli Hamiltonians as Maps between Free Modules”, *Communications in Mathematical Physics* (2013). [DOI](https://doi.org/10.1007/s00220-013-1810-2), [arXiv:1204.1063](https://arxiv.org/abs/1204.1063)

另一个可能的辅助问题是将非负 walk trigonometric polynomial 写成有限平方和 `a_walk=Σ d_a* d_a`。多变量 Fejer–Riesz 理论在二维和严格正条件下有新进展，但三空间变量、且 `k=0` 必须有零点的情形没有可直接套用的有限因子保证。因此它只能作为项目内的 Gram/SOS 搜索，不能作为存在性定理引用。

- M. A. Dritschel, “Factoring non-negative operator valued trigonometric polynomials in two variables” (2024). [DOI](https://doi.org/10.1007/s00208-024-02895-9)

## 五、对北极星主张的裁定

本轮查新不支持放松原主张，反而把下一步压缩为一个更清楚、可证伪的问题：

> 在 `U_walk` 所定义的 Laurent/Floquet 代数上，是否存在一个有限支撑的 rank-4 Killing-like generator、一个 exact curvature compatibility complex，以及一个在一般正式壳点同调恰为两个自旋 2 模的 gauge–equation detour complex，并且静态 Newton 双极点与精确源链同时保留？

成功将给出业界组合空白中的新构造；失败也必须以代数证书表述：指定半径/次数内不可解，或饱和后的 syzygy 必须引入非单项式分母/额外 BZ 同调。单纯的数值调参失败不再足够。

这里必须区分两种结构。曲率 compatibility complex 在平坦情形应当 exact，即 `ker K_curv=im G`；两个传播自由度不是它的同调。物理的 `2` 属于 gauge–equation detour complex，或等价地属于 walk 特征壳商环上的 on-shell complex：

```text
S^4 --G--> S^10 --E--> S^10 --B--> S^4,
S = R/(P_walk),
dim ker(E)/im(G) = 2  （一般壳点）.
```

de Donder 行可以满足 `C G=P_walk Q`，即在 `S` 上组成 complex；不应错误要求每个 off-shell de Donder 行本身都是 `G` 的严格 syzygy。

R25-A 已给出首个精确结构结果。对冻结 walk：

```text
det(I-U_walk) = 2-tr(U_walk) = a_tr,
(I-U_walk)^* (I-U_walk) = a_tr I_2,
adj(z_t I-U_walk)(z_t I-U_walk) = P_walk I_2.
```

因此完整 walk 壳自带严格局域的 `2×2` matrix factorization。它还不是最终自旋 2 复形，但说明非交换轴步要求的自然“差分”是矩阵值的；R15 的四个可交换标量差分只是其 IR 退化。B1 应优先把这两个内部通道提升为 auxiliary resolution，而不是继续拟合三个标量平方根。

下一阶段据此登记为 R25：先精确导出 Floquet Laurent 符号与特征多项式，再搜索 `G_walk`，随后分别求 curvature syzygy 与 on-shell detour complex；只有 compatibility 层过门后才构造 Hodge-like evolution。
