# rulespace_gpu — 大规模计算引擎(投影规则空间纲领)

一套后端无关的科学计算引擎:**同一份物理代码**在 Apple Silicon(MLX)、NVIDIA(CUDA)、或 CPU 上运行。为把纲领从 CPU 玩具规模推到 GPU 大规模而建——尤其是下一个前沿(自旋2张量引力)所必需。

已在 numpy 与 jax 两个后端上验证**逐位一致**(T⁰⁰守恒 4.5×10⁻¹⁴、涌现度规、光锥),证明 MLX/CUDA 路径(同一 NumPy 式 API)可直接工作。

---

## 安装(选一个后端)

**Apple Silicon(M系列,推荐 Mac 用户):**
```bash
pip install mlx numpy scipy
export RULESPACE_BACKEND=mlx
```

**NVIDIA GPU(CUDA):**
```bash
pip install "jax[cuda12]" numpy scipy      # 按你的CUDA版本选 cuda11/cuda12
export RULESPACE_BACKEND=jax
```

**Apple GPU 走 JAX(备选):**
```bash
pip install jax-metal numpy scipy
export RULESPACE_BACKEND=jax
```

**CPU 参考(总能用):**
```bash
pip install numpy scipy
export RULESPACE_BACKEND=numpy      # 或 auto
```

`RULESPACE_BACKEND=auto`(默认)按 mlx → jax → numpy 顺序自动选第一个可用的。

---

## 用法

把 `rulespace_gpu/` 放在工作目录下,然后:

```bash
# 1. 正确性验证(先跑这个,确认引擎在你的设备上物理正确)
RULESPACE_BACKEND=mlx python -m rulespace_gpu.verify

# 2. 吞吐基准(测你的GPU每秒多少格点更新,用来定规模)
RULESPACE_BACKEND=mlx python -m rulespace_gpu.benchmark

# 3. 批量规则搜索(数千条规则并行筛选)
RULESPACE_BACKEND=mlx python -m rulespace_gpu.campaign
```

代码里:
```python
import os; os.environ["RULESPACE_BACKEND"] = "mlx"
from rulespace_gpu import backend as B, engine, states, observables

shape = (128, 128, 128)                      # 3+1维,GPU上可到 256^3+
th = states.uniform_theta(shape, 0.45)
p0, p1 = states.packet(shape, (64,64,64), (0.6,0,0), 5.0, 0.45, dm=0.3)

# 完整耦合动力学(物质↔几何),已jit/编译
params = dict(ndim=3, dm=0.3, source="capstone", cg2=0.2, kappa=0.02,
              th_min=0.08, th_max=1.25)
step = engine.make_stepper(params)
state = (p0, p1, p0, p1, th, th)
for t in range(1000):
    state = step(state)
B.sync(*state)
```

---

## 架构

| 文件 | 内容 |
|---|---|
| `backend.py` | 后端抽象:MLX/JAX/NumPy 统一 API,惰性求值同步、设备传输、jit |
| `engine.py` | 计算核心:1/2/3维 Dirac 行走者 + 动力学θ场 + T⁰⁰ + 源(rho/T00/capstone);纯函数,可jit |
| `states.py` | 网格、波包初始化、主机端 2×2 模算符(小eig在CPU,再传设备) |
| `observables.py` | 设备端测量:圆心质心、⟨k⟩冲量、FFT泊松静态场 |
| `campaign.py` | 批量规则扫描(batch轴并行,GPU一次筛数千规则) |
| `verify.py` | 正确性测试:复现 CPU 时代的验证结果 |
| `benchmark.py` | 吞吐基准 |

## 已验证物理(numpy 与 jax 逐位一致)

- 3+1维真 T⁰⁰ 守恒到 **4.5×10⁻¹⁴**(机器精度)
- 涌现度规:波包局域速度 = cos θ,误差 0.0000
- 因果光锥:速度 ≤ 1
- 批量规则筛选:两后端存活数完全一致

CPU 基准(参考):3+1维 ~1.7×10⁷ 格点更新/秒(numpy),~4×10⁷(jax+jit)。GPU 预期 100–1000×。

---

## 下一个前沿:自旋2张量引力(为什么建这个引擎)

第六波确认:标量 θ 场给出的是标量引力,完整等效原理需要**自旋2张量场** h_μν,而它只在3+1维有传播自由度。移植路线(引擎已为此设计):

1. 把动力学场从标量 `theta` 升级为对称张量 `h[mu,nu]`(每格点10分量,3+1维);
2. 行走者耦合到完整应力-能量 `T[mu,nu]`(引擎的 `T00` 推广为张量);
3. 施加离散规范不变性(微分同胚离散类比)→ 挑出 Fierz–Pauli 结构;
4. 自洽性 → 非线性完成为爱因斯坦–Hilbert。

张量场把每格点的自由度从 1 增到 10,3+1维 256³ 规模只有 GPU 扛得动——这正是本引擎存在的理由。标量扇区的全部机制(自洽源、阴影能量、稀释律、判定漏斗)在张量扇区复用。
