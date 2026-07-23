"""p5c_divdiv_check -- P5 遗留补检③: R19 staggered-h 放置 vs 立方网格 divdiv
复形最低阶元 (Hu-Liang-Ma-Zhang, arXiv:2204.07895 = Numer. Math. 156:1603, 2024)
的形式等价性判定的可复现记账。

为什么没有逐 k 的矩阵 symbol 对拍(任务预留的跳过分支,理由记录在此):
  该文的 Sigma_{k,□} 是 k>=3 的协调 Galerkin 元 -- 每分量是各向异性多项式
  (sigma_ii in P_{k,k-2,k-2} 等),自由度是棱/面/体上的**积分矩**(Thm 3.1),
  离散 divdiv 算子 = 单元内精确多项式微分 + 弱形式(质量矩阵),不是平移不变的
  单场差分模板。周期均匀网格上它的 "symbol" 是每胞 48 个全局 DOF (k=3) 的
  Galerkin 块的有理函数,与 4x10 的 kappa_placed 之间不存在文献给出的规范
  约化映射;不存在可比较的 2sin(k/2) 型半频符号(FEM 内部没有差商)。
  故 symbol 层的不等价是范畴性的,矩阵对拍无从谈起、也不改变结论。

本脚本做三件确定性的记账(全部整数算术,fp 无关):
  1. 用 (3.8) 的各向异性多项式空间维数复算 dim Sigma_[k](K;S),与 Thm 3.1
     证明里的 DOF 计数公式 6k^3-6k^2-3k+3 交叉核对 (k=3,4,5) -- 确认我们
     对该元结构的读取无误;
  2. 周期网格上每胞全局 DOF 数(棱/面共享摊派)vs R19 每胞样本数;
  3. 分量-几何实体挂载表的并排打印(他们 vs 我们),标出唯一的结构回声
     (指标互补轴关联,对偶实体味道)与所有不匹配项。

Run: .venv/bin/python p5c_divdiv_check.py
"""


def dim_sigma_shape(k):
    """dim Sigma_[k](K;S) from (3.8): sigma_ii in P_{k,k-2,k-2} (3 comps),
    sigma_ij in P_{k-1,k-1,k-2} (3 comps)."""
    diag = (k + 1) * (k - 1) ** 2
    shear = k * k * (k - 1)
    return 3 * diag + 3 * shear


def dof_count_paper(k):
    """Thm 3.1 proof: 12(k-1) + 12(k-2)(k-1) + 12(k-1)^2 + 3(k-1)^2(k-3)
    + 3(k-2)^2(k-1)  =  6k^3 - 6k^2 - 3k + 3."""
    return (12 * (k - 1) + 12 * (k - 2) * (k - 1) + 12 * (k - 1) ** 2
            + 3 * (k - 1) ** 2 * (k - 3) + 3 * (k - 2) ** 2 * (k - 1))


def dofs_per_cell_periodic(k):
    """global DOFs per cell on a periodic cuboid mesh (entity sharing:
    edge / 4 cells -> 3 unique edges per cell; face / 2 -> 3 unique faces)."""
    per_edge = k - 1                      # (3.10a): P_{k-2}(e) moments of one shear comp
    per_face_shear = 2 * (k - 2) * (k - 1)  # (3.10b): 2 shear comps x grad-moments Q_{k-2}
    per_face_diag = 2 * (k - 1) ** 2      # (3.10c): sigma_ii and d_i sigma_ii, Q_{k-2}(f)
    interior = 3 * (k - 1) ** 2 * (k - 3) + 3 * (k - 2) ** 2 * (k - 1)  # (3.10d)
    return 3 * per_edge + 3 * (per_face_shear + per_face_diag) + interior


R19_SPATIAL_PER_CELL = 6    # 6 space-space components, 1 point sample per cell each
R19_SPACETIME_PER_CELL = 10  # all h_munu, 1 sample per spacetime cell each

ENTITY_TABLE = [
    # (component, HLMZ cuboid divdiv element (k=3 lowest), R19 staggered-h)
    ("sigma_ii / h_ii", "faces PERP x_i: moments (s_ii,q)_f,(d_i s_ii,q)_f, "
     "q in Q_{k-2}; + interior", "VERTEX (integer points), 1 point sample"),
    ("sigma_ij / h_ij", "edges PARA x_l: P_{k-2} moments; faces perp x_i,x_j: "
     "grad-moments; + interior", "FACE CENTER perp x_l: x+(e_i+e_j)/2, 1 sample"),
    ("h_0i", "-- (no time direction in the FEM complex)",
     "x+e_i/2 at HALF TIME steps (leapfrog slices)"),
    ("h_00", "--", "integer points, integer time"),
]

if __name__ == "__main__":
    print("P5c: R19 staggered-h vs Hu-Liang-Ma-Zhang cuboid divdiv element")
    print("=" * 72)
    print("\n[1] reading check: shape-space dim == DOF count (unisolvence)")
    ok = True
    for k in (3, 4, 5):
        ds, dd = dim_sigma_shape(k), dof_count_paper(k)
        ok &= (ds == dd == 6 * k ** 3 - 6 * k ** 2 - 3 * k + 3)
        print(f"    k={k}:  dim Sigma_[k] = {ds}   #DOF(Thm 3.1) = {dd}   "
              f"{'OK' if ds == dd else 'MISMATCH'}")
    print(f"    lowest order is k=3 (element undefined below k=3)  -> "
          f"{'PASS' if ok else 'FAIL'}")

    print("\n[2] DOFs per cell, periodic uniform mesh (their global element vs ours)")
    for k in (3, 4):
        print(f"    HLMZ Sigma_{{{k},cuboid}}: {dofs_per_cell_periodic(k)} moments/cell")
    print(f"    R19 spatial block   : {R19_SPATIAL_PER_CELL} point samples/cell")
    print(f"    R19 full spacetime  : {R19_SPACETIME_PER_CELL} samples/spacetime cell")
    print("    -> 48 (k=3) vs 6: no bijective sublattice relabeling / translation /")
    print("       lattice duality can identify the two DOF sets.")

    print("\n[3] component -> geometric entity")
    for comp, theirs, ours in ENTITY_TABLE:
        print(f"    {comp:18s} | HLMZ: {theirs}")
        print(f"    {'':18s} | R19 : {ours}")
    print("    structural echo (NOT an equivalence): both attach the shear pair")
    print("    (i,j) to the complementary axis l -- their edges PARA x_l vs our")
    print("    face centers PERP x_l are dual entities on the cubic lattice; but")
    print("    integral moments != point samples, 48 != 6, and their diagonal")
    print("    lives on faces while ours lives on vertices (not dual images).")

    print("\n[symbol] categorical mismatch, recorded (no computation possible):")
    print("    - their end map is scalar div div (2nd order, Galerkin-weak),")
    print("      exact polynomial differentiation inside cells: NO difference")
    print("      quotient, hence no 2 sin(k/2) half-frequency symbol anywhere;")
    print("    - our K_placed is the de Donder ROW divergence (1st order, 4 rows)")
    print("      with certified symbol kappa = (2sin(w/2)/c, 2sin(k_i/2)) (R17/R19).")
    print("    Different operator, different discretization category.")

    print("\nVERDICT: NOT EQUIVALENT (level a: placement geometry -- no; level b:")
    print("operator symbol -- no, categorically; level c: no time direction /")
    print("leapfrog / on-shell structure in the FEM complex).")
