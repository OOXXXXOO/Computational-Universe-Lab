# R25 首轮符号结果：walk-compatible detour 已闭合，UV 节点另立病灶

*2026-07-24。证书：`r25_laurent_results.json`、`r25_walk_complex_results.json`、`r25_detour_results.json`、`r25_uv_exceptional_results.json`。本报告不改变北极星门。*

## 结论

严格局域的 walk-compatible de Donder/gauge complex 在**一般完整 walk 壳点**已经构造出来，不再是猜想。关键不是给 R15 的 `2sin(k_i/2)` 调系数，而是将完整 Floquet 矩阵

```text
F(z) = z_t I_2 - U_walk(z)
```

按 Pauli 基分解成四个标量 Laurent 分量：

```text
F = kappa_0 I + kappa_i sigma_i,
kappa.eta.kappa = -det(F) = -P_walk.
```

把这个 `kappa` 代入普通 Killing、de Donder、线性 Einstein 与 Bianchi 代数，得到有限 stencil 的 detour complex

```text
R^4 --G--> R^10 --E--> R^10 --B--> R^4,
E G = 0,  B E = 0,
```

且在两支各 1028 个一般壳点上：

```text
rank(G,C,E) = (4,4,4),
dim ker(E)/im(G) = 2,
最坏恒等残差 = 6.75e-15.
```

这同时保住完整 walk 特征壳、严格局域、规范秩 4 和两个传播自由度。IR Jacobian 为 `diag(-i,i/2,i/2,i/2)`，精确回到速度 `c=1/2` 的连续 Killing covector。

## 一、B0 为什么失败，B2 为什么成功

旧 R15 ansatz 强制时间与三个空间差分彼此分离。其 null polynomial 与完整 walk polynomial 的差在轴向为零，但在一般斜向从三/四阶 Trotter 项出现。精确 Laurent 比较得到 27 点非零残差，因此 B0 只对 ideal half-angle 壳成立。

完整 `F=z_tI-U` 的 `kappa_0` 同时含时间位移和空间 Laurent 项；这正是 separated de Donder 禁止、而非交换轴序要求的混合 stencil。由 `det F=P_walk`，`C G=P_walk Q` 和 detour 恒等不再依赖采样拟合。

另有两个辅助恒等：

```text
det(I-U)=2-tr U=a_tr,
(I-U)^*(I-U)=a_tr I_2.
```

它们说明完整 walk stiffness 天然有严格局域的矩阵值平方根。

## 二、全 BZ 新病灶：冻结 walk 有精确第二个 +I 点

exceptional audit 在 `z_y=1,z_z=z_x` 切片对 `U-I` 四个矩阵元取公因子，得到

```text
(z_x-1) [z_x + 1/7 + (4sqrt(3)/7)i].
```

第二根

```text
z_x=z_z=(-1-4sqrt(3)i)/7,
k_x=k_z=-1.714143896...,
```

严格位于单位圆，代回得到 `U_walk=I`。这正是 L3-v3 数值 UV near-foldback 的极限，不是网格偶然。

在该点 `F=0`，canonical detour 的 `G=E=0`，同调从一般点的 2 跳到 10。原点也有同样的 cone-vertex 增强，但原点承担 Newton 零模；非零点则是额外 UV Floquet/Dirac 节点。

## 三、对主线的含义

需要分清两个命题：

1. “一般 walk 壳点是否存在严格局域的 rank-4/2-DOF 复形？”——已回答 **YES**。
2. “冻结两带 walk 是否同时只有一个零频节点、全 BZ 无额外同调？”——已回答 **NO**；传播壳本身已有第二节点，约束复形不能凭空删掉它。

这不修改原北极星的正式低动量 J5/DOF 门，但阻止我们把纯 `a_tr` 用作全 BZ 静态 stiffness：它会在第二节点产生额外静态极点。L3-v3 的 Wilson return 因而仍是必需的，只是现在必须与 detour complex 共同变形。

## 四、下一步登记

继续的主线不是退回 old `K_placed`，而是 auxiliary Wilson–detour：

- 保留 B2 的物理 gauge rank 4 与 IR Killing 极限；
- 用有限局域 auxiliary/matrix factorization 提升 Wilson 修正，不用 Green projector；
- 在非零 `U=I` 点使物理 equation complex 不再出现额外同调；
- 正式低动量 J5 仍 `<1e-2`，目标沿用 L3-v3 已达到的 `4.65e-4`；
- 完成后才进入实空间 Z4c/源链与 Newton canary。

若证明任何这样的 finite auxiliary resolution 都要求改变 matter walk 或增加物理 gauge rank，才升级为架构决策；目前尚未到该 no-go。
