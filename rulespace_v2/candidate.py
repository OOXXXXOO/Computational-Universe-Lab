"""rulespace_v2.candidate -- v2 候选 schema(任务书 §2,字段写死)与门列容器。

CandidateV2 必含字段(v2-任务书-M0-仪器迁移.md §2):
  sector     : "spin0" | "spin1" | "spin2"
  geometry   : {"family": "R30"|"yee_maxwell"|"frozen_walk"|..., "params": {...}}
  coupling   : {"variant", "kappa", "eta_back", ...} | None
  hand_built : {"dof_indices": ...} | None      # epsilon_DOF 的分子来源(见 epsilon.py)
  lattice    : {"L": [...], "judge_k_set": [...], "ray_directions": [...]}
  backend    : "numpy" | "jax"                  # 证书一律 fp64
  frozen_refs: {file: sha256, ...}              # 引用冻结件 hash,运行时逐位校验

geometry.family 在 M0' 已实现的取值(gates.py 分派):
  "R30"          -- R30 手搭局域酉张量复形(Yee leapfrog;epsilon=0 锚)
  "yee_maxwell"  -- R23 自旋 1 Yee/Maxwell 符号层(epsilon=1 锚)
  "frozen_walk"  -- 冻结涌现走行族(RC1a 重组机器物理点 theta=pi/3, dm=0, c=0.5)
  "null_damped"  -- 卡点⑦/R28 正控规则(涌现判据机器自带的 2-DOF 正控)
  "teeth_spin2"  -- 裸 10 分量波负控(N_prop=6,判据有牙)
  "tensor_qca"   -- v1 裁判组 Newton/Eddington 载体(G4/G5 与 tr_sign 炮)

hand_built 约定(D1 裁定,epsilon.py 实现):
  {"dof_indices": "all"}     -> j_hand = N_curv  -> epsilon_DOF = 0(R30 锚,定义写死)
  {"dof_indices": None}      -> j_hand = 0       -> epsilon_DOF = 1(R23 锚,定义写死)
  {"dof_indices": "measure_rc3ii_R2"} -> j_hand 由 RC3-(ii) R2 冻结手搭计数机逐 k 实测

GateColumns:evaluate_v2_candidate 的输出容器。每门一个条目:
  {"raw": 原始读数, "per_L": 逐 L 读数表|None, "limit_fit": {A, alpha, dAIC}|None,
   "verdict": "PASS"|"FAIL"|"ambiguous"|"CONTROL"|"NA", "diagnostics": {...}}
纲领 §四:任何 verdict 不得由单一固定尺度读数产生;做不到逐尺度的门(实空间时序类
控制行)一律记 verdict="CONTROL"(仪器对答案行,非物理判定),并在 diagnostics 注明。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

SECTORS = ("spin0", "spin1", "spin2")
FAMILIES = ("R30", "yee_maxwell", "frozen_walk", "null_damped",
            "teeth_spin2", "tensor_qca")
GATE_NAMES = ("G1_dof_nprop", "G2_sigma_scaling", "G3_j5_cocone",
              "G4_newton", "G5_eddington", "G6_conservation",
              "G7_stability", "G8_epsilon")
VERDICTS = ("PASS", "FAIL", "ambiguous", "CONTROL", "NA")


@dataclass
class CandidateV2:
    sector: str
    geometry: dict
    coupling: Optional[dict] = None
    hand_built: Optional[dict] = None
    lattice: dict = field(default_factory=lambda: {
        "L": [16, 24, 32, 48],
        "judge_k_set": [[2, 0, 0], [0, 3, 0], [2, 2, 0], [2, 2, 2]],
        "ray_directions": [[1, 0, 0], [1, 1, 0], [1, 1, 1]],
    })
    backend: str = "numpy"
    frozen_refs: dict = field(default_factory=dict)
    cand_id: str = ""

    def __post_init__(self):
        assert self.sector in SECTORS, f"sector {self.sector!r} not in {SECTORS}"
        assert isinstance(self.geometry, dict) and "family" in self.geometry
        assert self.geometry["family"] in FAMILIES, self.geometry["family"]
        assert self.backend in ("numpy", "jax")
        for key in ("L", "judge_k_set", "ray_directions"):
            assert key in self.lattice, f"lattice missing {key}"

    @property
    def family(self) -> str:
        return self.geometry["family"]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "CandidateV2":
        return cls(**json.loads(s))


@dataclass
class GateColumns:
    cand_id: str
    family: str
    sector: str
    gates: dict = field(default_factory=dict)   # gate_name -> entry dict
    certificates: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    def set_gate(self, name: str, raw: Any, verdict: str,
                 per_L: Any = None, limit_fit: Any = None,
                 diagnostics: Any = None) -> None:
        assert name in GATE_NAMES, name
        assert verdict in VERDICTS, verdict
        self.gates[name] = {"raw": raw, "per_L": per_L, "limit_fit": limit_fit,
                            "verdict": verdict, "diagnostics": diagnostics or {}}

    def as_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)
