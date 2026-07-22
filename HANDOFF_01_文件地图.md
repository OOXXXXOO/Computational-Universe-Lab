# 文件地图:每个文件是什么、怎么跑、产出什么

*配套 `HANDOFF_00_交接总纲.md`。目录:`~/workspace/science/ca-universe-lab/`。*

---

## A. 阅读顺序(文档)

| 想了解 | 读这个 |
|---|---|
| 项目全貌、入口 | `HANDOFF_00_交接总纲.md` |
| 纲领本身(5原理+2猜想+10开放问题) | `纲领-投影规则空间物理.md` |
| 形式化定义 + 8实验学术报告(含LaTeX) | `实验报告-投影规则空间纲领.md` |
| 第一批3实验(涌现/剪枝/投影陷阱) | `报告-计算宇宙三实验.md` |
| 残差学+量子回声(exp4/5) | `报告-中期实验-记忆与回声.md` |
| 泄漏色散+真实LIV界限(exp6) | `报告-实验⑥-泄漏色散与真实界限.md` |
| 3+1维SME匹配 + **新颖性排查** | `报告-实验⑦-3+1维SME匹配与novelty排查.md` |
| 引力战役逐波(C1推导链) | `战役报告-第二/三/四/五/六波-*.md` |
| C1b首轮暴力扫描(裁判漏斗) | `战役报告-C1b-第一轮.md` |
| R7自束缚失败(负结果) | `战役报告-R7-自束缚的诚实失败.md` |
| GPU三条路运行命令 | `RUN_GPU_三条路.md` |

---

## B. 现象学实验(exp*,CPU,numpy/scipy)

按依赖顺序,每个 `python exp*.py` 独立可跑(<45s),产出图到 `figs/`、数据到 `*_results.json`。

| 脚本 | 内容 | 关键产出 |
|---|---|---|
| `exp1_dirac_qca.py` | QCA→狄拉克方程 | 收敛阶 2.014;时空图/色散/收敛图 |
| `exp2_pruning.py` | 剪枝:256经典规则+量子洛伦兹 | 经典256→6平凡;V(δ)幂律 |
| `exp3_projection.py` | 投影陷阱/局部最优 | rule154@88.8%错误定律;acc=1−p/2 |
| `exp4_residual_spectrum.py` | Mori-Zwanzig残差学+反演 | 空间零增益/时间增益;隐藏场反演 |
| `exp5_quantum_projection.py` + `exp5_figs.py` | partial trace + BLP回声 | N(g,n_h)矩阵;小维度回声响 |
| `exp6_kk_dispersion.py` | 泄漏通道字典+真实界限 | σx/σz字典;(ε,g)排除,g<6.6e-52 |
| `exp7_3d_weyl_sme.py` | 3+1维Weyl/Dirac SME匹配 | 手征二分b_z/a_z;零通道<1e-14 |
| `exp8_gauge_emergence.py` | 规范场浮现 | 速度饱和;洛伦兹力 |
| `exp8b_lorentz.py` | 洛伦兹力(严格半经典+量子) | 回旋轨道r+5.6%,ω_c<10% |
| `exp8c_polytime.py` | 谱透明复杂度 | D^2.17 幂律 |
| `anim1-4_*.py` | 4个浮现过程动画 | `figs/anim*.gif` |

---

## C. 引力战役(r*,CPU,C1推导链)

| 脚本 | 波次 | 关键产出 |
|---|---|---|
| `r2a_sign_axiom.py` `r2a_shapiro.py` | 二波 | Shapiro符号字典 +20/−10 |
| `r2b_eotvos*.py` | 二波 | Eötvös选T00作源(η: rho 0.65 vs T00 0.002) |
| `r3_consistency.py` | 三波 | 自洽源F=−δE_w/δθ;吸引κ>0;EP⟺共形 |
| `r4a_dilution.py` | 四波 | 稀释律 r^−(d−2):d=1发散/d=3有限 |
| `r4b_noether.py` | 四波 | 交错能量精确守恒(SymPy);联合漂移 |
| `r4c_selfbind_2d.py` | 四波 | 2+1维边际束缚 + MP4 |
| `r4d_t00_3d.py` | 四波 | 3+1维T00守恒9e-14;EP迁移6.7% |
| `r5a_single_mode.py` | 五波 | 行走哈密顿能量=正确守恒量(25×) |
| `r5b_shadow.py` | 五波 | 阴影守恒 s^2.78;结果B关闭 |
| `r6b_deflection_3d.py` | 六波 | 3+1维吸引偏折 |
| `r6a_capstone.py` | 六波 | **F=tanθ·T00·(1−m²/ω²)** SymPy证明 + 小ε阴影阶 cos²θ/12·k²(已补存,自验ALL PASS) |

**注(2026-07-18 已解决):** r6a 的符号封顶原先只在 bash 内联跑、没存成 .py。**现已补存为 `r6a_capstone.py`**(SymPy 三条恒等 ==0 + 小ε级数给出阴影阶 cos²θ/12·k² + 数值复现报告 #32 到 ~1e-4;`python r6a_capstone.py` → ALL PASS,写 `r6a_results.json`)。

---

## D. CPU 规则空间包(`rulespace/`)

首个标准化演算基建(第七/八轮建的,CPU)。

| 模块 | 内容 |
|---|---|
| `core.py` | 非均匀split-step行走者 + 动力学coin场 + 6算子库 |
| `judges.py` | 四级裁判漏斗:J1稳定/J2因果/J3响应/**J4等效原理** |
| `campaign.py` | 采样+漏斗+JSONL存储 |
| `discover.py` | 稀疏回归(STLSQ,贡献尺度阈值) |
| `render.py` | 统一可视化标准(几何/物质/时空/判定四带→MP4) |

跑法:`python -c "from rulespace.campaign import sweep; ..."`(见 `战役报告-C1b-第一轮.md`)。

---

## E. GPU 引擎(`rulespace_gpu/`)—— 当前主力

多后端(MLX/JAX/CUDA/numpy),同一份物理代码。**先读 `rulespace_gpu/README.md`。**

| 模块 | 内容 |
|---|---|
| `backend.py` | 后端抽象:统一NumPy式API、惰性同步、jit、设备传输 |
| `engine.py` | 核心:1/2/3维Dirac行走者+动力学θ场+T00+源(纯函数可jit) |
| `states.py` | 网格/波包初始化/主机端2×2模算符(小eig在CPU) |
| `observables.py` | 圆心质心/⟨k⟩冲量/FFT泊松静态场 |
| `campaign.py` | **批量**规则扫描(batch轴并行,GPU一次筛数千) |
| `verify.py` | 正确性测试(复现CPU结果) |
| `benchmark.py` | 吞吐基准 |
| `pathA_sn_soliton.py` | 路A:非相对论S-N自引力孤子 |
| `pathB_spin2.py` | 路B:线性化自旋2验收(2极化+光偏折因子2) |
| `pathC_scale.py` | 路C:10⁵规则大规模搜索 |
| `r7_selfbind_3d.py` | R7:相对论自束缚(负结果) |

**运行(Mac):**
```bash
source .venv/bin/activate && export RULESPACE_BACKEND=mlx
python -m rulespace_gpu.verify        # 先验证
python -m rulespace_gpu.benchmark     # 测吞吐
python -m rulespace_gpu.pathA_sn_soliton --L 96 --T 4000 --scan
python -m rulespace_gpu.pathB_spin2
python -m rulespace_gpu.pathC_scale --n 100000 --batch 8192
```

---

## F. 可视化与交付物

| 文件 | 内容 |
|---|---|
| `lab.html` | 交互实验室(三模块:QCA波包/剪枝/投影陷阱),浏览器直接开 |
| `3d_gravity_well.html` | Three.js 3+1维自引力井体渲染(可交互旋转) |
| `figs/anim1-4_*.gif` | 浮现过程动画(判定内置画面) |
| `figs/mov_r2a/r2c/r4c_*.mp4` | Shapiro/湍流对照/2D造星影片 |
| `figs/*.png` | 39张结果图 |
| `*_results.json` | 23个数据文件(各实验数值) |

---

## G. 长跑范式(可观测·可控·可恢复)—— 详见 `HARNESS_使用说明.md`

| 文件 | 内容 |
|---|---|
| `campaign_runner.py` | 可恢复长跑循环:原子 checkpoint、control 轮询、SIGTERM 优雅退出、**逐位精确恢复**(已实测连续==分段) |
| `campaign_server.py` | stdlib 零依赖服务:`/api/state` 读、`/api/control` 写 run/pause/stop |
| `dashboard.html` | 网页控制台(本地开 http://localhost:8765/,非 artifact):实时指标+判据漏斗+双流形+**in-shader θ场 CA 实时 GPGPU 演算**+控制按钮 |
| `run/` | 运行时状态:`state.json`/`_acc.json`(恢复)/`control.json`/`best_rule.json` |

工作流:`nohup python campaign_runner.py run --full &` + `python campaign_server.py` → 浏览器看+控制;早上 Stop 自动 checkpoint,之后 `run` 从断点接着跑。张量-QCA 以后换掉 runner 里的 sweep 负载即可复用整套观测/控制/恢复。

## H. 环境

| 文件 | 内容 |
|---|---|
| `setup_env.sh` | 一键建venv+装后端(Mac自动MLX/NVIDIA自动CUDA)+跑verify |
| `requirements-core.txt` | numpy/scipy/matplotlib/sympy/scikit-learn |
| `.venv/` | (用户本机生成,勿同步) |
| `CLAUDE.md` | (自动记忆索引,非项目内容) |
