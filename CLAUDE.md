# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A computational-physics research lab — the **Projective Rule-Space Program** (投影规则空间纲领). The
question: which inhomogeneous quantum cellular automaton (QCA) rules produce *law-like* emergent
physics (an emergent metric, causality, gravity-like matter coupling, the equivalence principle)?
The workflow is a scientific campaign, not a product: each experiment is a self-contained script
that runs a simulation, writes a `*_results.json`, drops figures into `figs/`, and feeds a
written report (the Chinese-language `报告-*.md` / `战役报告-*.md` files at the repo root — these
are the lab notebook and the record of what has and hasn't worked).

Not a git repo, no test framework, no build step. "Correctness testing" means running the physics
verification suite (see below); "running tests" means reproducing validated physics results.

## Environment & commands

```bash
bash setup_env.sh            # create ./.venv, install core stack + GPU backend (auto-detected)
bash setup_env.sh mlx        # force Apple Silicon GPU  | cuda = NVIDIA | cpu = numpy reference
source .venv/bin/activate
export RULESPACE_BACKEND=mlx  # or: source activate_backend.sh   (mlx | jax | numpy | auto)
```

`RULESPACE_BACKEND` selects the compute device for the `rulespace_gpu` package. `auto` picks the
first available of mlx → jax → numpy. `.env` / `activate_backend.sh` record the last setup choice.

```bash
python -m rulespace_gpu.verify       # correctness suite — RUN THIS FIRST after any engine change
python -m rulespace_gpu.benchmark    # measure GPU throughput (grid-updates/s)
python -m rulespace_gpu.campaign     # batched rule search (thousands of rules in parallel)
python exp1_dirac_qca.py             # standalone CPU experiments run directly, no args
python -m rulespace_gpu.pathA_sn_soliton --L 96 --T 4000 --scan   # GPU experiments take CLI args
```

`rulespace_gpu.verify` is the acceptance gate: it checks 3+1D T⁰⁰ conservation (~1e-14), the
emergent metric (packet speed = cos θ), and the causal light cone. Any change to the engine must
keep all three PASS on both `numpy` and `mlx`/`jax` backends (they are validated bit-for-bit
identical). See `RUN_GPU_三条路.md` for the current active experiment set (paths A/B/C) and the
exact commands + expected numbers.

## Architecture

**The physical model** (defined in `rulespace/core.py`, mirrored in `rulespace_gpu/engine.py`):
a 2-spinor split-step Dirac/Weyl walker with a *local* coin angle `theta(x,t)`. The emergent
light speed is `c(x) = cos theta(x)` — so θ *is* the metric. θ is itself a dynamical field updated
by a second-order (leapfrog) rule driven by a library of local operators (Laplacian stiffness,
gradient², matter density `rho`, momentum `J`, restoring, damping) weighted by a **coupling vector
`a`**. A "rule" = a choice of `a`. Matter (the walker) sources geometry (θ); geometry steers matter
— a closed feedback loop. `dm` is a mass-gap knob taking the walker off the Weyl line.

**`rulespace/` — CPU reference package** (numpy, the physics is authored here first):
- `core.py` — the walker + dynamical coin field + coupled run loop (`run_coupled`). Start here.
- `judges.py` — the **law-likeness funnel** J1–J5, the heart of the program: J1 stability,
  J2 causality (perturbation front ≤ light cone), J3 matter-response, J4 **universality /
  equivalence principle** (the observer's reduced law must have state-independent coefficients —
  "THE law detector"), J5 gravity sign (matter slows light). An experiment "passes" by surviving
  the funnel.
- `campaign.py` — samples rules from a physics-shaped sparse prior, runs the funnel, appends
  results to `campaigns/*.jsonl`.
- `discover.py` — SINDy-style sparse regression (STLSQ): recover the sparsest θ_tt = Σ cᵢ Oᵢ that
  explains a trajectory (a control/inverse-problem layer).
- `render.py` — figure helpers.

**`rulespace_gpu/` — device-agnostic scaled engine** (the same physics, big grids/batches):
- `backend.py` — one NumPy-like API over mlx / jax / numpy, chosen by `RULESPACE_BACKEND`. Smooths
  over conj/angle naming, lazy-eval `sync`, host transfer, and `jit`. **All physics code is written
  against this shim (`B.xp`, `B.roll`, `B.jit`, …), never against a backend directly** — that is
  what keeps one source running on four devices. MLX is fp32-native; jax/numpy use fp64.
- `engine.py` — the compute core: 1/2/3-D walker, dynamical θ, T⁰⁰, sources (`rho`/`T00`/`capstone`
  = tan(θ)·T⁰⁰). Every function is **pure (no in-place mutation)** so it JIT-compiles. `make_stepper`
  returns a jitted one-macro-step closure.
- `states.py` — grid/packet init, 2×2 mode operator (small eig on host, then transferred).
- `observables.py` — device-side measurements (center-of-mass, ⟨k⟩, FFT-Poisson static field).
- `campaign.py` — batched (batch-axis-parallel) 1+1D rule screening — the GPU version of the CPU
  judge funnel.
- `pathA_sn_soliton.py`, `pathB_spin2.py`, `pathC_scale.py`, `r7_selfbind_3d.py` — current GPU
  experiments (self-gravity solitons, linearized spin-2 graviton, 10⁵-rule survival-manifold scan).

**Standalone scripts at repo root** — the experiment history, each writes `<name>_results.json` +
figures to `figs/`:
- `exp1`–`exp8*` — the foundational sequence (Dirac QCA, pruning, projection, residual spectrum,
  quantum projection, KK dispersion, 3D Weyl+SME, gauge/Lorentz emergence).
- `r2`–`r7`, `c1*`, `pathA/B/C`, `anim*` — later "campaign waves"; naming maps to the wave reports.
Convention: import numpy, `matplotlib.use("Agg")`, write JSON + PNG under `figs/`. When adding an
experiment, follow this pattern and pair it with a report entry.

## Working conventions

- **Author physics in `rulespace/` (CPU/numpy) first, then port to `rulespace_gpu/`** for scale.
  The two must stay physically consistent; `rulespace_gpu.verify` is the cross-check.
- **Keep engine functions pure** — no in-place array writes, or JIT breaks under jax/mlx.
- Build static host arrays (fftfreq, small eigenvectors) once on the host and transfer; don't
  recompute them inside the device step.
- Reports are the source of truth for *why* a rule was kept or killed and what the next wave tests.
  Read the relevant `报告-*.md` / `战役报告-*.md` before extending an experiment line.
- The current frontier (per `rulespace_gpu/README.md`): upgrading the scalar θ field to a symmetric
  tensor `h_μν` (spin-2 tensor gravity), which is why the GPU engine exists.


所有UI和汇报文档都用中文