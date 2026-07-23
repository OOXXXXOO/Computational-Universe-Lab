# 预注册 R25：Laurent 模与 walk-compatible 规范复形

*登记日期：2026-07-24。目标是修复 CP1-v4 L3-v3 已定位的“完整 walk 壳—旧 placed 复形”冲突。北极星原门不变；本轮禁止以非局域投影、收窄波矢集合或放松 J5/DOF 获得通过。*

## 一、唯一研究问题

对现有物质 walk 的精确 Floquet 符号 `U_walk(zx,zy,zz)`，寻找有限支撑的线性复形

```text
R^4 --G_walk--> R^10 --K_curv--> R^m --K2--> ...,
R = Q(i,sqrt(3))[zt^±1,zx^±1,zy^±1,zz^±1],
```

使它在完整 walk 壳上退化为规范秩 4、物理商恰为 2 的线性自旋 2 系统，并在 IR 回到连续 Killing/de Donder/Calabi 结构。`K_curv` 的 compatibility complex 应满足 `ker K_curv=im G`；传播自由度由 gauge–equation detour complex 的 `ker E/im G` 计算。

## 二、冻结项与禁止项

冻结：

- `green_one_walk.geom_walk_all` 所定义的物质宏步与轴序；
- CP1-v4 的精确键流源链、Newton canary 定义及静态双极点要求；
- 正式 J5 门 `<1e-2`，目标仍是使用完整 walk 壳而非近似 ideal 壳；
- 一般正式壳点 `rank G=4`，规范商传播自由度 `N_prop=2`；
- 全 BZ 必须检查额外 rank drop、foldback 与 cohomology。

禁止：

- FFT 或逐动量 projector；
- Green operator、`(K K*)^-1`、`1/P_walk` 等动量依赖除法；
- 无限支撑 perfect action，即便系数指数衰减；
- 只在六个采样点成立的 `K G≈0`；
- 以 auxiliary fields 偷换物理规范秩；
- 在失败后收窄到轴向或放松体对角 DOF/J5。

允许 Laurent 单项式 `zt^a zx^b zy^c zz^d`，因为它们只是整格平移；禁止不可逆多项式分母。

## 三、R25-A：精确 Floquet/Laurent 登记

从实现轴步逐项导出精确 `2x2 U_walk(z)`，而不是从采样频率拟合。登记：

```text
P(zt,z) = det(zt I - U_walk(z)),
a_tr(z) = 2 - tr U_walk(z),
```

以及 L3-v3 的 `a_v3`。必须通过：

- 解析矩阵与现有数值 `geom_walk_all` 在随机 BZ 点误差 `<1e-12`；
- `det U=1` 与 reciprocal/conjugation symmetry 为符号恒等；
- `P` 的 IR 二阶项恢复共享光锥；
- 明列非交换轴序产生的最低阶 odd/cross terms；
- 列出 `a_tr` 的全 BZ 零点/rank-drop 候选，禁止把 UV foldback 隐去。

R25-A 不允许调动力学参数。

## 四、R25-B：规范生成元搜索

不预设 `G_{mu nu}=d_mu xi_nu+d_nu xi_mu` 必须由四个可交换标量差分组成。按 stencil 半径/总次数从小到大搜索一般 Laurent 矩阵

```text
G_walk(z): R^4 -> R^10.
```

约束：

1. IR 主符号等于连续 Killing operator，归一化与列基变换固定后误差从二阶或更高开始；
2. 一般正式壳点 `rank G_walk=4`；
3. 规范子空间在 Floquet 演化下闭合，且不把四个规范方向变成额外物理曲率；
4. 矩阵元无非单项式分母，记录最大时空位移；
5. 实结构/伴随结构足以生成实 `h_mu nu` 演化。

搜索顺序预定为：

- B0：classical symmetric-gradient 形式，允许四个 Laurent `d_mu`；用于快速 no-go/基线；
- B1：优先使用 `D_walk=I-U_walk` 与 `F_walk=z_t I-U_walk` 的严格局域 `2×2` matrix factorization，尝试以 auxiliary resolution 提升到张量规范生成元；同时测试与轴序相符的最低阶交叉项；
- B2：一般 rank-4 Laurent 矩阵，按半径 `r=1,2,...` 递增并施加 IR 线性约束。

不得因 B0 失败就宣称总 no-go。

## 五、R25-C：完整 syzygy / compatibility complex

对每个通过 B 门的 `G_walk`，以 Gröbner/syzygy 算法求左模 `Syz(G_walk)`，选取完整第一曲率 compatibility operator `K_curv`，再求后续 syzygies。另在壳商环 `S=R/(P_walk)` 上构造 de Donder/equation detour complex；允许 `C G=P_walk Q`，但不允许非 Laurent 分母。

硬门：

- `K_curv G_walk ≡ 0` 是约化后的 Laurent 多项式恒等；de Donder 行另证 `C G=P_walk Q`；
- 登记生成元数、次数、stencil 半径与是否需要饱和；
- 曲率 compatibility complex 在一般点 exact；一般正式壳点的 detour/equation 同调 `dim ker(E)/im(G)` 恰为 2；
- `k=0` 的静态扇区保留 Newton 双极点，不被 gauge-fixing 质量化；
- 全 BZ minors/Fitting-ideal 或等价穷检不得出现额外物理 cohomology/UV 零点；
- 由 `K_curv` 定义的曲率读出对 `im G_walk` 为机器精度零，并在 IR 回到线性 Riemann/Calabi 读出。

数值 SVD 只作为代数恒等之后的诊断，不能代替 exactness 证明。

## 六、R25-D：共同变形的局域演化

仅当 A–C 通过后，才构造与复形同源的 Hodge-like 演化，例如局域组合 `K* W K + G V G*` 或一阶 auxiliary realization。具体形式不得预注册为唯一答案，但必须满足：

- 无逆算子，有限 stencil；
- 物理极点严格落在完整 `P(zt,z)=0` 壳上；
- 规范/约束扇区可阻尼，两个物理模不受损；
- 重放 L3-v3 的 J5、`N_prop`、纯 gauge、静态井、精确源链和全 BZ 稳定门。

最终完整门沿用北极星：J5 `<1e-2`、全部正式 k 的 `N_prop=2`、纯 gauge 曲率 `<1e-12`、Newton `h00/phi=2.00±0.02` 且 `1/r` 相关 `>0.99`、守恒 `<1e-12`，以及规定证伪炮必须击穿至少一门。

## 七、预登记的失败解释

- 若 B0 无解：只说明“四个标量差分的 classical symmetric gradient”与完整 walk 不相容，继续 B1/B2。
- 若某半径内 B2 无解：登记为次数/半径有界 no-go，不外推到所有有限半径。
- 若 syzygy 只能在局部化后生成且分母不是 Laurent 单项式：登记为该 ansatz 的严格局域 no-go。
- 若必须增加内部通道：允许作为 auxiliary resolution 继续，但物理 gauge rank 仍必须为 4，并单列 auxiliary modes 的消除证书。
- 若全 BZ 出现额外同调：演化壳与 complex 必须共同 Wilson 化；禁止只改传播壳重演 L3-v3。
- 只有当两个不同半径/ansatz 家族都给出同一结构障碍，且继续需要选择“扩大场内容、修改物质 walk、或改变北极星主张”时，才升级为用户决策点。

## 八、首轮交付物

1. 精确 Laurent 符号导出器与 JSON 证书；
2. `P`、`a_tr`、IR 展开、非交换项和 UV 零点登记；
3. B0 的可解性/no-go 结果；
4. 至少一个 B1 候选或明确的线性代数秩障碍；
5. 对任何候选分别给出 exact `K_curv G=0` 与 detour complex 的一般壳点同调表。
