#!/usr/bin/env bash
# setup_env.sh — create the project venv and install the right GPU backend.
#
#   bash setup_env.sh          # auto-detect backend (mlx on Apple Silicon, else cpu)
#   bash setup_env.sh mlx      # force Apple Silicon GPU  (pip install mlx)
#   bash setup_env.sh cuda     # force NVIDIA GPU         (pip install jax[cuda12])
#   bash setup_env.sh cpu      # CPU-only reference
#
# Safe to re-run. Creates ./.venv and prints how to activate it.
set -euo pipefail
cd "$(dirname "$0")"

# ---- pick backend ----
BACKEND="${1:-auto}"
OS="$(uname -s)"; ARCH="$(uname -m)"
if [ "$BACKEND" = "auto" ]; then
  if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then BACKEND="mlx"
  elif command -v nvidia-smi >/dev/null 2>&1; then BACKEND="cuda"
  else BACKEND="cpu"; fi
fi
echo ">> OS=$OS ARCH=$ARCH  ->  backend=$BACKEND"

# ---- python & venv ----
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info>=(3,9), "need Python >=3.9"' \
  || { echo "!! need Python 3.9+ (set PYTHON=/path/to/python3.11)"; exit 1; }
if [ ! -d .venv ]; then
  echo ">> creating .venv"; "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel >/dev/null

# ---- install ----
echo ">> installing core scientific stack"
pip install -r requirements-core.txt

case "$BACKEND" in
  mlx)
    echo ">> installing MLX (Apple Silicon GPU)"
    pip install mlx
    ENVLINE="mlx" ;;
  cuda)
    echo ">> installing JAX + CUDA 12"
    pip install "jax[cuda12]"
    ENVLINE="jax" ;;
  cpu)
    echo ">> CPU reference backend (numpy)"; ENVLINE="numpy" ;;
  *)
    echo "!! unknown backend $BACKEND"; exit 1 ;;
esac

# ---- record backend + smoke test ----
echo "RULESPACE_BACKEND=$ENVLINE" > .env
echo "export RULESPACE_BACKEND=$ENVLINE" > activate_backend.sh
echo ">> wrote .env and activate_backend.sh (RULESPACE_BACKEND=$ENVLINE)"

echo ">> verifying engine on this machine..."
RULESPACE_BACKEND="$ENVLINE" python -m rulespace_gpu.verify || {
  echo "!! verify failed — check the output above"; exit 1; }

cat <<EOF

=========================================================
 done. to use this environment:

     source .venv/bin/activate
     export RULESPACE_BACKEND=$ENVLINE      # or: source activate_backend.sh

 then, e.g.:
     python -m rulespace_gpu.benchmark      # measure your GPU throughput
     python -m rulespace_gpu.campaign       # batched rule search
     python experiments/exp1_dirac_qca.py   # any standalone CPU experiment
=========================================================
EOF
