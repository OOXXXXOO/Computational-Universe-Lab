# 长跑范式:可观测 · 可控 · 可恢复

一个良性的长跑过程:**晚上启动、早上停、之后接着跑**,全程有一个网页看进度 + 实时 shader 演算绘制。研究负载(现在是规则搜索,以后是张量-QCA)插在同一个 harness 上。

## 三个文件
| 文件 | 作用 |
|---|---|
| `campaign_runner.py` | 计算循环:分批扫规则、累加 stable/lawful/流形。**原子 checkpoint、control 轮询、SIGTERM 优雅退出、确定性可精确恢复** |
| `campaign_server.py` | stdlib 服务(零依赖):`/api/state` 读状态、`/api/control` 写 run/pause/stop |
| `dashboard.html` | 网页控制台:实时指标 + 判据漏斗 + 双流形 + **in-shader θ 场 CA 实时 GPGPU 演算** + 控制按钮 |

运行时状态都在 `run/` 里:`state.json`(公开指标)、`_acc.json`(精确恢复用)、`control.json`(控制)、`best_rule.json`(当前最优 lawful 规则,喂给实时着色器)。

## 用法(正是"启动一晚上→早上停→再恢复")

```bash
source .venv/bin/activate && export RULESPACE_BACKEND=mlx

# 1) 启动(或从断点自动恢复)长跑。不加 --fresh 就是接着上次跑。
nohup python campaign_runner.py run --full > run/runner.log 2>&1 &

# 2) 开控制台
python campaign_server.py            # 然后浏览器打开 http://localhost:8765/
```

- **看进度**:浏览器里实时刷新 —— 已扫规则数、吞吐、稳定率、lawful 率、算子流形(stable vs lawful)、当前最优规则,以及一块**实时着色器画的 θ 场**(用当前最优 lawful 规则的系数在浏览器 GPU 上现算现画,c=cosθ 上色)。
- **早上停**:页面点 ⏹ Stop(或 `python campaign_runner.py stop`)。runner 跑完当前 batch → 写 checkpoint → 退出。
- **之后恢复**:再跑一遍 `nohup python campaign_runner.py run --full &` —— **从断点逐位精确接着跑**(已实测:连续跑 == 分段跑,stable/lawful 完全一致)。

## 控制命令
```bash
python campaign_runner.py pause      # 暂停(runner 保持存活,轮询等待)
python campaign_runner.py resume     # 继续
python campaign_runner.py stop       # 优雅停止并退出
python campaign_runner.py status     # 打印当前状态
python campaign_runner.py reset      # 清空 run/ 重头开始
python campaign_runner.py run --target 5000000 --full   # 定上限;到点自动 done
python campaign_runner.py run --j1                       # 只跑 J1 稳定(快 ~5×,不算等效原理)
```
页面上的 ▶/⏸/⏹ 按钮通过 `/api/control` 控制一个**存活的** runner;启动 runner 本身是上面的 CLI 命令(页面在检测到 runner 不活时会把命令显示出来)。

## 鲁棒性保证(已实测)
- **恢复逐位精确**:每个 batch 用 `seed=batch_index`,总进度是 `batches_done` 的纯函数 → 连续/分段/恢复三种跑法结果完全相同。
- **原子 checkpoint**:临时文件 + `os.replace`,任何时刻断电都不会写坏 state。
- **优雅退出**:SIGINT/SIGTERM 和 stop 命令都会跑完当前 batch、落盘、再退。
- **解耦**:runner 和 server 是两个独立进程,server 只读文件、只写 control;互不阻塞。

## 把张量-QCA 插进来(下一步)
harness 与负载解耦:`campaign_runner.run()` 里调用的是 `rulespace_gpu.campaign.sweep`(标量规则搜索)。等张量-QCA 候选规则构造好、其批量评估函数(复用 `spin2_evolver` 的三项验收当判据)写好后,把 runner 里那一行 `sweep(...)` 换成张量版评估即可 —— 观测/控制/恢复/实时可视化全部照旧复用。
