"""rulespace_v2.frozen -- I 类冻结判据核的注册、sha256 逐位校验与只读导入。

v2 任务书(docsv2/v2-任务书-M0-仪器迁移.md)红线 1/3:
  * 不改 v1 任何冻结脚本/JSON;所有引用冻结件运行时 sha256 逐位校验并入册;
  * 判据核从 I 类清单继承,禁止重写算法内核 -- 本模块只做"找到冻结文件、验哈希、import"。

EXPECTED_SHA256 的每个值都注明出处(某冻结结果 JSON 内记录的 hash),运行时与磁盘文件
逐位比对;RECORD_ONLY 列出的文件在任何冻结 JSON 里没有先行 hash 记录,只能"入册"
(记录当前 sha256),不能"比对"——这一区别如实写进校验结果。

本模块不含任何物理判据。
"""
from __future__ import annotations

import hashlib
import importlib
import os
import sys

# fp64 numpy 后端(红线 2:证书一律 fp64;MLX 禁用)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

_THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_THIS)
EXPERIMENTS = os.path.join(ROOT, "experiments")
RESULTS = os.path.join(ROOT, "data", "results")

for _p in (ROOT, EXPERIMENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --------------------------------------------------------------------------
# 冻结源文件 -> 先行记录的 sha256(出处注明;逐位比对)
# --------------------------------------------------------------------------
EXPECTED_SHA256 = {
    # -- rc3ii_results.json frozen_inputs_sha256 (== r36/r37 复核记录) --------
    "experiments/rc1a_tensor_index_scan.py":
        "ca57a32534c865542d5057eba0e578e7c3aee6e8ca36f779ab103fac6f2ab84f",
    "experiments/r32_reachability_probe.py":
        "f1ab9307ea2540a0e733ebf34f975a131790927553ded86a6e1134cd08227442",
    "experiments/r15_walk_dedonder.py":
        "ce10bc05c5caa487154a72a4169a1095930afe2afd2d84e4f49bba1041bb18cc",
    # -- r36_results.json certificates.frozen_hashes --------------------------
    "experiments/r25_dynamic_symbol.py":
        "a2f458f61c61caf125eb59e700f20c5e603def3b98cdb1ca9169db9e1933bfdb",
    "experiments/r25_realspace_step.py":
        "a66f6082e03c45b55687ad60859257e0993dc04f30185e212ff3e4bd62331445",
    "experiments/cp1_v4_L2.py":
        "556e56665766b29c22eedf226645e3530c95c8ddc27e2b99527eb6158a70fb67",
    # -- r32_results.json frozen_inputs_sha256 --------------------------------
    "experiments/r25_auxiliary_wilson_complex.py":
        "48eb8653dde48315104e0843d03c88e9947dd13fc2e5642a6264504e9330c1bd",
    # -- r30_results.json frozen_inputs_sha256 --------------------------------
    "experiments/r16_cp1_invitro.py":
        "5696d921903043ba91f3c287cba3eba8d2f2f68e1c69a04c482999bcaec26478",
    "rulespace_gpu/emergence_judge.py":
        "0c0188e122f7ee9322b52c5f3901aeae39c1430f77728d878de3480f87312902",
    "experiments/r28_placed_judge_reverdict.py":
        "3c10cd669b3f9e49daf91eab362bc249df23d9b25f38d478f66628ac07afabc7",
    # -- 各冻结结果 JSON 自记录的 source_sha256 -------------------------------
    "experiments/r30_tensor_complex_dynamical.py":           # r30_results.json
        "eae6034d8403a93977988d0a56e80c8899b9ffe80fcacc4084fc0244b2d519a4",
    "experiments/rc3ii_relaxation_framework.py":             # rc3ii_results.json
        "23cfc187db9454f5a89bb1b7467db6887efd465b8cbe964ec74633ce54a994a6",
    "experiments/r36_r3_verification.py":                    # r36_results.json
        "2169f7acbaef06c0954750d9e63441e880389fb48613e2d38092095a22ff1abe",
    "experiments/r37_residual_scaling_audit.py":             # r37_results.json
        "b847808c96ef8c64c72973d0e415db202497beb0236575d351a91c1fa9508df0",
    "experiments/r25_emergence_timeseries.py":               # 卡点⑦ 结果 JSON
        "ccb3de344eaba5593526fc06e13a709c52967e61bbbd3d16127f0e70ae3b9594",
}

# 无先行 hash 记录的引用冻结件:只入册当前 sha256,诚实标注"record-only"。
RECORD_ONLY = [
    "experiments/r23_maxwell_control.py",
    "experiments/r17_placement_operators.py",
    "rulespace_gpu/tensor_qca.py",
    "rulespace_gpu/pathB_spin2.py",
    "rulespace_gpu/spin2_evolver.py",
    "rulespace_gpu/tensor_coin_feedback.py",
]

# 冻结结果 JSON(已知答案来源;当前文件 sha256 入册。注意其内部 results_sha256
# 字段是"写入该字段前一刻"的哈希,与最终文件哈希不同,不能用来比对文件本身)。
FROZEN_RESULT_JSONS = [
    "data/results/r30_results.json",
    "data/results/r23_results.json",
    "data/results/r25_emergence_timeseries_results.json",
    "data/results/r28_results.json",
    "data/results/r32_results.json",
    "data/results/rc3ii_results.json",
    "data/results/r36_results.json",
    "data/results/r37_results.json",
    "data/results/tensor_qca_results.json",
]


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def verify_frozen() -> dict:
    """逐位校验全部有先行记录的冻结源文件;入册 record-only 文件与结果 JSON。
    返回 {"pass": bool, "checked": {...}, "record_only": {...}, "result_jsons": {...}}。
    任一有记录文件不匹配 => pass=False(红线 1:停手条件)。"""
    checked, ok = {}, True
    for rel, exp in EXPECTED_SHA256.items():
        p = os.path.join(ROOT, rel)
        got = sha256_file(p)
        m = (got == exp)
        ok = ok and m
        checked[rel] = {"sha256": got, "expected": exp, "match": m}
    rec = {rel: {"sha256": sha256_file(os.path.join(ROOT, rel)),
                 "note": "record-only (无先行 hash 记录可比对)"}
           for rel in RECORD_ONLY}
    rjs = {rel: sha256_file(os.path.join(ROOT, rel)) for rel in FROZEN_RESULT_JSONS}
    return {"pass": bool(ok), "checked": checked, "record_only": rec,
            "result_jsons_sha256": rjs}


_MODCACHE: dict = {}


def mod(name: str):
    """只读 import 一个冻结模块(experiments/ 平铺脚本或 rulespace_gpu 子模块)。"""
    if name not in _MODCACHE:
        _MODCACHE[name] = importlib.import_module(name)
    return _MODCACHE[name]
