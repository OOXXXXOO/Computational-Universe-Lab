# P5c 补检③:R19 staggered-h 放置 vs 立方网格 divdiv 复形最低阶元——等价性判定

*2026-07-23,车道A理论任务(P5 遗留补检③,见 小报告-P5查新-离散线性引力先行文献.md §四)。
判据文献:Hu–Liang–Ma–Zhang, "New conforming finite element divdiv complexes in three
dimensions", arXiv:2204.07895(2022-04-17 v1);期刊版 "A family of conforming finite
element divdiv complexes on cuboid meshes", Numer. Math. 156:1603–1638 (2024),
doi:10.1007/s00211-024-01418-7(主查新给出的线索即此文,arXiv 版与期刊版为同一工作)。
记账脚本:`p5c_divdiv_check.py`(全整数算术,无 fp 依赖,直接运行复现)。*

---

## 一、结论先行:**(ii) 不等价**——三层全不等价,且是范畴性的

R19 staggered-h 放置构造**不是**立方网格 divdiv 复形最低阶元的交错差分等价物,
也不能经平移/对偶变换化为它。三层判定全部为"否":

- **a. DOF 放置几何:否。** 他们的最低阶元(k=3)是**积分矩型协调 Galerkin 元**,
  每胞 48 个全局自由度、无任何顶点自由度;我们是**每分量单点采样**,每胞 6 个空间
  样本(时空 10 个)。48 vs 6、矩 vs 点值,不存在双射的子格重标/平移/格点对偶。
- **b. 算子 symbol:否(最硬判据,范畴性不匹配)。** 他们在单元内做**精确多项式微分**
  + 弱形式连续性,构造中根本没有差商,故 κ_i=2sin(k_i/2) 型半频符号**在其框架中不出现**;
  且其复形末端算子是**标量值二阶 div div**,不是我们的 de Donder **行散度**
  ∂^μ h̄_μν(一阶、4 行)。不同算子 + 不同离散化范畴,symbol 相等无从谈起。
- **c. 范畴:否。** 纯空间 3D、椭圆/静态(双调和方程 + 线性化 Einstein–Bianchi
  混合形式),H(div div;S) Sobolev 协调性;**无时间方向、无 leapfrog 交错、无在壳
  κ·κ=0 结构、无幺正演化、无物质耦合**。

**对新颖性主张 (a) 的直接后果:(a) 无需因 divdiv 立方元收窄,保持"交错实现路径"
表述**(收窄分支不触发)。但本轮检索顺带发现一条对 (a) 措辞更要紧的经典先行线
(velocity–stress 交错网格,见 §四 caveat),建议按 §五 的口径微调。

## 二、判据文献的最低阶元结构(逐字提取,防误读:记账脚本已交叉核对)

Hu–Liang–Ma–Zhang 在立方网格上构造 H(div div,Ω;S) 协调元 Σ_{k,□},**k ≥ 3 才有
定义**(k=3 即最低阶)。形函数空间(其 (3.8)):σ ∈ H¹(K;S),各向异性多项式——

- 对角(法向应力)P_n σ = (σ₁₁,σ₂₂,σ₃₃) ∈ P_{k,k−2,k−2} × P_{k−2,k,k−2} × P_{k−2,k−2,k};
- 非对角(剪应力)P_t σ = (σ₁₂,σ₁₃,σ₂₃) ∈ P_{k−1,k−1,k−2} × P_{k−1,k−2,k−1} × P_{k−2,k−1,k−1}。

自由度(其 Theorem 3.1,(3.10a–d);ī 记模 3 同余):

| DOF 组 | 几何实体 | 内容 |
|---|---|---|
| (3.10a) | **棱** e ∥ x_{ī+1} | 剪分量 σ_{i,ī−1} 的 P_{k−2}(e) 矩 |
| (3.10b) | **面** f ⊥ x_i | 剪分量 σ_{i,ī−1}, σ_{i,ī+1} 对 ∂q(q∈Q_{k−2}(f))的矩 |
| (3.10c) | **面** f ⊥ x_i | **对角** σ_ii 与其法向导数 ∂_i σ_ii 的 Q_{k−2}(f) 矩 |
| (3.10d) | **体内** | 泡函数空间 Σ̊_[k] 的矩 |

协调性由 σn_f 与 n_f^T div σ 的跨面连续实现(其 Remark 3.2),即
Σ_{k,□} ⊆ H(div div;S) ∩ H(div;S)——一个**加强正则性的椭圆型 Sobolev 条件**。

记账核对(`p5c_divdiv_check.py` 输出):dim Σ_[k](K;S) = 6k³−6k²−3k+3,k=3 时
**102/胞(孤立胞)**、周期网格共享摊派后 **48 矩/胞**;k=3 时无 (3.10d) 对角体内项
但仍有剪切体内矩 6 个。对照:R19 空间块 **6 点值/胞**、全时空 **10 样本/时空胞**。

## 三、三层对比表(判定依据)

| 层面 | HLMZ 立方 divdiv 最低阶元 (k=3) | R19 staggered-h | 判定 |
|---|---|---|---|
| DOF 类型 | 棱/面/体上**积分矩**,48/胞(周期摊派),**无顶点 DOF** | 每分量**单点采样**,6(空间)/10(时空)每胞 | **不等价** |
| 对角分量 | 挂 ⊥x_i 的**面**(σ_ii 与 ∂_iσ_ii 的面矩)+ 体内 | 挂**整点(顶点)** | 不一致,亦非对偶像 |
| 空间非对角 | ∥x_l 的**棱**上 P_{k−2} 矩 + ⊥x_i,⊥x_j 面上梯度矩 + 体内 | ⊥x_l 的**面心** x+½(e_i+e_j) | 仅"指标互补轴"关联同型(棱∥x_l 与面⊥x_l 在立方格上互为对偶实体)——结构回声,非等价 |
| 0μ 分量 | 无(无时间方向) | h_0i 在 x+½e_i、**半时间格**;h_00 整点整时 | 他方不存在此对象 |
| 算子 | 标量值二阶 div div,Galerkin 弱形式;单元内**精确多项式微分,无差商** | de Donder 行散度 ∂^μ h̄_μν,一阶 4 行,整数 roll 差分 | **不同算子 + 不同范畴** |
| symbol | e^{ik} 的有理函数(48 维 Galerkin 块 + 质量矩阵),**无 2sin(k/2) 半频结构** | κ_placed = (2sin(ω/2)/c, 2sin(k_i/2)),纯实,R17/R19 证书级 | **不等价** |
| 时间/在壳 | 静态椭圆(双调和、Einstein–Bianchi 混合形式);如做演化是方法线 | leapfrog 切片配对、在壳 κ·κ=0 匹配 QCA 半角壳、TT∈ker 恒等式 | 他方无此层 |
| 精确核结构 | ker(div div)∩Σ_h = sym curl U_h(复形正合性,离散上同调) | ker K_placed/gauge = TT(dim 2, rank 4) | 同一物理动机("精确离散核"),不同数学对象 |

**关于逐 k 矩阵对拍(任务预留的跳过分支,理由声明):** 未做,因不可行且不必要——
HLMZ 的离散算子**不是平移不变的单场差分模板**(每胞 48 DOF 的混合 Galerkin 块,
symbol 是含质量矩阵逆的有理矩阵函数),文献未给出、也不存在从 48 维矩空间到我们
10 维点值空间的规范约化映射;而三层不等价已在结构层面各自独立成立(点值 vs 矩、
一阶行散度 vs 二阶标量 divdiv、有时间 vs 无时间),矩阵对拍不能翻转任何一层。
`p5c_divdiv_check.py` 做的是可复现的确定性记账(维数公式 vs DOF 计数交叉核对
k=3,4,5 全对、周期摊派 48 vs 6、实体挂载表),不是 symbol 对拍。

## 四、诚实 caveat(两条,第 2 条对 (a) 措辞比 divdiv 本身更要紧)

1. **结构回声要在成文时主动承认:** 两个构造都把剪切对 (i,j) 关联到互补轴 l
   (他们:棱 ∥x_l;我们:面心 ⊥x_l——立方格上互为对偶实体)。这是"对称张量
   分量按指标挂几何实体"这一共同几何语法的表现,建议成文引用 HLMZ 时明说
   "同一几何语法、不同实现范畴",与 P5 主查新对 Hanot–Hu 的"互补表述,不贬低"
   口径一致。
2. **检索顺带发现(转入补检②管辖,但先记录):** R19 的**空间**放置模式——对角
   σ_ii 共点、剪切 σ_ij 在 x+½(e_i+e_j)、"速度型"分量在 x+½e_i 且**半时间步**——
   与地震学/弹性动力学的经典 **velocity–stress 交错网格 FD**(Virieux 1986 2D;
   Levander/Graves 3D;各向异性版 Lebedev 格,Lisitsa–Vishnevskiy, Geophys.
   Prospect. 58:619, 2010, doi:10.1111/j.1365-2478.2009.00862.x)**同型**,且该线
   同样用 leapfrog 时间交错、其动量方程 ∂_t v_i = ∂_j σ_ij 的空间差分同样是半频
   symbol。此线**没有** h_00、没有把 10 分量统一为单一 4-张量协变规则
   x+½(e_μ+e_ν)、没有 de Donder 约束算子、没有 TT-核恒等式、没有与量子行走壳的
   匹配——但"对称张量 + 行散度 + 时空交错 + 2sin(k/2) 符号"作为**离散化技术**
   在弹性动力学是教科书级存在。(a) 的新颖性重心必须避开"交错放置对称张量"本身。

## 五、判定与 (a) 的最终表述建议

**判定:(ii) 不等价。** (a) 不触发"收窄为该元的交错差分实现"分支,保持"实现路径"
表述;但依 §四.2 把重心从"交错"挪到"协变统一 + 壳匹配":

> **(a) 建议口径:** "我们给出线性化引力 h̄_μν 全部 10 分量在时空立方格上的**单一
> 协变放置规则** x+½(e_μ+e_ν)(其空间-空间块与弹性动力学 velocity–stress 交错网格
> 同型,此处按其精神推广到含 h_00、h_0i 的 4-张量并配 leapfrog 切片语义),使
> de Donder 约束成为纯整数 roll 算子、其半频符号 κ=(2sin(ω/2)/c, 2sin(k_i/2)) 与
> 量子行走的半角在壳结构**精确匹配**(κ·κ=0 在壳、TT∈ker 为代数恒等式)。'精确
> 离散约束核'本身 FEEC/Regge/Hanot–Hu 已用他法实现(据我们查新所及),且与立方
> 网格 divdiv 复形元(Hu–Liang–Ma–Zhang 2024)**不同构**(点值 vs 矩、一阶行散度
> vs 二阶 divdiv、时空 vs 纯空间);我们主张的新颖性在于该协变放置与幺正 QCA
> 演化核的在壳匹配及其服务的涌现判据,而非交错放置或精确核任一单项。"

后续动作建议:补检②("Yee grid for gravity")执行时把 Virieux/Graves/Lebedev 线
并入定向检索词("staggered grid linearized gravity"、"velocity-stress scheme
gravitational waves"),确认有无人已把 SSG 推广到 4-张量;若有,(a) 需再议。

## 引用清单

- Hu, Liang, Ma, Zhang, *New conforming finite element divdiv complexes in three
  dimensions*, arXiv:2204.07895;期刊版 *A family of conforming finite element
  divdiv complexes on cuboid meshes*, Numer. Math. 156:1603–1638 (2024),
  doi:10.1007/s00211-024-01418-7。【判据文献,本报告 §二 全部结构事实出处:
  其 (1.2)(3.8)(3.10a–d), Thm 3.1, Remark 3.2, Lemma 3.2】
- Chen, Huang, arXiv:2007.12399(四面体 divdiv 元,最低阶 dim 162,P5 主查新已录)。
- Hu, Liang, Ma, arXiv:2103.00088, SINUM 60:1307 (2022)(四面体 divdiv 复形 +
  Einstein–Bianchi,P5 主查新已录)。
- Hu, Liang, Ma, Zhang, *Finite element grad grad complexes and elasticity
  complexes on cuboid meshes*, arXiv:2302.03783, J. Sci. Comput. (2024),
  doi:10.1007/s10915-024-02512-6(同组对偶复形,同为矩型协调元,佐证范畴判定)。
- Lisitsa, Vishnevskiy, *Lebedev scheme for … 3D anisotropic elasticity*,
  Geophys. Prospect. 58:619 (2010), doi:10.1111/j.1365-2478.2009.00862.x;
  Virieux, Geophysics 51:889 (1986)【§四.2 caveat,转补检②】。
