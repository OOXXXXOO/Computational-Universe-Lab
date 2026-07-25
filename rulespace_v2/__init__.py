"""rulespace_v2 -- v2 统一评估器包(M0' 仪器迁移交付物 1)。

结构:
  frozen.py    冻结判据核注册 + sha256 逐位校验 + 只读 import
  candidate.py CandidateV2 schema(任务书 §2)+ GateColumns
  gates.py     G1..G8 门列(v2 极限语言外壳 + v1 冻结核)+ evaluate_v2_candidate
  epsilon.py   G8 epsilon_DOF 主判 + epsilon_E 辅报(D1 口径)
  sigma.py     G2 约束标度(R37 协议外壳,D3 两档)
  controls.py  M0' 控制矩阵 8 行(tol 写死)

用法:
  from rulespace_v2 import CandidateV2, evaluate_v2_candidate
  gc = evaluate_v2_candidate(cand)     # -> GateColumns

红线:证书一律 fp64(numpy/jax);MLX 禁用;不改 v1 任何冻结脚本/JSON。
"""
from .candidate import CandidateV2, GateColumns          # noqa: F401
from .gates import evaluate_v2_candidate                 # noqa: F401
