"""V2M0 -- CERT5 非宿主谱系路径测试(宿主侧模拟;M0' 收口执行包件一,2026-07-26)。

AUTHORITY:
  docsv2/v2-复核-车道A-M0整改沙盒双跑-2026-07-26.md §六(退回 lane B 的唯一整改项:
  cert5 MISMATCH 不得 ABORT,记谱系注记并继续主流程落 DONE);
  experiments/v2m0_sigma_calibration_v2.py 头 CERTIFICATES 第 5 条(微补丁后语义)。

WHAT THIS IS(如实标注):
  这是**宿主侧路径测试**,不是真沙盒重跑——在宿主上模拟非宿主谱系:对 legacy 对照
  通道(cert5 唯一消费的 legacy_resid_* 逐模统计,复核 §三判决其为基依赖非观测量)
  注入固定扰动 +1e-10(量级对标跨 BLAS 谱系漂移的放大代表),使 cert5 逐位比对
  必然 MISMATCH(ok5=False),从而走非宿主谱系代码路径。验证三件事:
    (a) 微补丁后脚本不 ABORT,主流程走完,status = DONE;
    (b) lineage = "non-host-lineage(expected-drift,诊断级)",ok_bit_for_bit=False,
        diff 记账 ≈ 注入量;
    (c) 不变量科学字段(judgement_reproduction / cert4 自洽 / 基稳健 /
        direction_fits_invariant(主判+rms 辅报)/ old_vs_new / 分支落点与措辞建议 /
        min_k_raw 与 ray_data 的全部不变量子字段)与正式宿主运行
        data/results/v2m0_sigma_calibration_v2.json **逐位一致**——证明 legacy 通道
        谱系漂移不污染任何判据/科学内容。
  真沙盒完整重跑(Linux/OpenBLAS)留给车道A,随时可做;本测试不替代其证据地位,
  只验证代码路径与科学字段隔离性。

RED LINES:
  * 不覆盖任何正式结果 JSON:被测脚本的 OUT/STATE 全部重定向——
      OUT   -> data/results/v2m0_cert5_pathtest_run.json(测试专用运行产物,留档)
      STATE -> 临时副本(scratchpad 级,不回写 data/runtime/v2m0_state.json)
    正式文件(v2m0_sigma_calibration_v2.json / v2m0_selftest_v2.json /
    v2m0_state.json / r37_results.json)运行前后 sha256 逐位核验未动,入册;
  * 被测脚本源码零修改(monkeypatch 仅在本进程内存中包裹
    rulespace_v2.sigma.collect_direction_invariant,只加扰动到 legacy_resid_* 键,
    不变量键零触碰);
  * fp64 numpy;不碰 git。

Run: RULESPACE_BACKEND=numpy .venv/bin/python experiments/v2m0_cert5_pathtest.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

import numpy as np  # noqa: F401  (fp64 环境自证)

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
for p in (ROOT, DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("RULESPACE_BACKEND", "numpy")

TARGET = os.path.join(DIR, "v2m0_sigma_calibration_v2.py")
OFFICIAL_OUT = os.path.join(ROOT, "data", "results", "v2m0_sigma_calibration_v2.json")
OFFICIAL_SELF2 = os.path.join(ROOT, "data", "results", "v2m0_selftest_v2.json")
OFFICIAL_STATE = os.path.join(ROOT, "data", "runtime", "v2m0_state.json")
R37_JSON = os.path.join(ROOT, "data", "results", "r37_results.json")
TEST_OUT = os.path.join(ROOT, "data", "results", "v2m0_cert5_pathtest_run.json")
VERDICT_OUT = os.path.join(ROOT, "data", "results", "v2m0_cert5_pathtest.json")

PERTURB = 1e-10          # 注入 legacy 通道的固定扰动(写死)
EXPECTED_LINEAGE = "non-host-lineage(expected-drift,诊断级)"

# 不变量科学字段清单(须与正式运行逐位一致;写死)
INVARIANT_FIELDS = [
    "frozen_inputs_sha256", "frozen_hash_match", "faithfulness_certificate",
    "judgement_reproduction", "invariant_1648_consistency_vs_selftest_v2",
    "basis_robustness_fit_set",
    "direction_fits_invariant", "direction_fits_rms_secondary",
    "old_vs_new", "calibration_branch", "axial_O1_invariant_obstruction",
    "face_small_floor_verdict_invariant", "axial_verdict_invariant",
    "wording_update_suggestion", "nature_reminder",
]
LEGACY_KEYS = ("legacy_resid_min", "legacy_resid_max", "legacy_resid_mean")


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def strip_legacy(obj):
    """递归剥除 legacy_resid_* 键(它们按设计随谱系漂移,不参与逐位比对)。"""
    if isinstance(obj, dict):
        return {k: strip_legacy(v) for k, v in obj.items() if k not in LEGACY_KEYS}
    if isinstance(obj, list):
        return [strip_legacy(v) for v in obj]
    return obj


def collect_legacy_values(obj, path="$", acc=None):
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in LEGACY_KEYS and isinstance(v, float):
                acc.append((path + "." + k, v))
            else:
                collect_legacy_values(v, path + "." + str(k), acc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            collect_legacy_values(v, "%s[%d]" % (path, i), acc)
    return acc


def main():
    t0 = time.time()
    pre_hashes = {os.path.relpath(p, ROOT): sha256_file(p)
                  for p in (OFFICIAL_OUT, OFFICIAL_SELF2, OFFICIAL_STATE, R37_JSON)}

    verdict = {
        "register": ("V2M0 cert5 非宿主谱系路径测试(宿主侧模拟;收口执行包件一)"),
        "status": "RUNNING",
        "nature": ("host-side path test simulating non-host lineage; NOT a real "
                   "sandbox rerun(真沙盒重跑留给车道A随时可做);不覆盖正式 JSON"),
        "authority": ["docsv2/v2-复核-车道A-M0整改沙盒双跑-2026-07-26.md §六",
                      "experiments/v2m0_sigma_calibration_v2.py CERTIFICATES 5"],
        "method": ("monkeypatch rulespace_v2.sigma.collect_direction_invariant:"
                   "对每个样点的 legacy_resid_min/max/mean 加固定扰动 +%.0e;"
                   "不变量键零触碰;被测脚本源码零修改,OUT/STATE 重定向" % PERTURB),
        "perturbation": PERTURB,
        "official_files_pre_sha256": pre_hashes,
    }

    # -- 载入被测脚本为模块,重定向输出,包裹 legacy 通道
    spec = importlib.util.spec_from_file_location("v2m0_sigma_calibration_v2_UT",
                                                  TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    tmp_state = os.path.join(tempfile.mkdtemp(prefix="v2m0_pathtest_"),
                             "v2m0_state_copy.json")
    shutil.copy(OFFICIAL_STATE, tmp_state)
    mod.OUT = TEST_OUT
    mod.STATE = tmp_state

    SIG = mod.SIG
    orig_collect = SIG.collect_direction_invariant

    def perturbed_collect(dname, dvec, lattices=None):
        pts = orig_collect(dname, dvec, lattices)
        for s in pts:
            for key in LEGACY_KEYS:
                if key in s and s[key] is not None:
                    s[key] = float(s[key]) + PERTURB
        return pts

    SIG.collect_direction_invariant = perturbed_collect
    try:
        print("=" * 74)
        print("[pathtest] 运行被测脚本(legacy 通道 +%.0e,OUT/STATE 重定向)"
              % PERTURB)
        print("=" * 74)
        mod.main()
    finally:
        SIG.collect_direction_invariant = orig_collect

    # -- 核验官方文件未动
    post_hashes = {os.path.relpath(p, ROOT): sha256_file(p)
                   for p in (OFFICIAL_OUT, OFFICIAL_SELF2, OFFICIAL_STATE, R37_JSON)}
    officials_untouched = post_hashes == pre_hashes
    verdict["official_files_post_sha256"] = post_hashes
    verdict["official_files_untouched"] = bool(officials_untouched)

    # -- 载入两份结果比对
    with open(OFFICIAL_OUT, "r", encoding="utf-8") as fh:
        ref = json.load(fh)
    with open(TEST_OUT, "r", encoding="utf-8") as fh:
        run = json.load(fh)

    # (a) 主流程走完
    ok_status = run.get("status") == "DONE"
    # (b) 谱系路径
    lin = run.get("legacy_rederivation_host_lineage", {})
    ok_lineage = (lin.get("lineage") == EXPECTED_LINEAGE
                  and lin.get("ok_bit_for_bit") is False
                  and bool(lin.get("environment_bound")))
    lin_diffs = lin.get("diff", {})
    ok_diff_scale = bool(lin_diffs) and all(
        0.1 * PERTURB <= d <= 10.0 * PERTURB for d in lin_diffs.values())
    # 对照:正式运行应为宿主逐位
    ref_lin = ref.get("legacy_rederivation_host_lineage", {})
    ref_is_host = (ref_lin.get("lineage") == "host-bit-for-bit"
                   and ref_lin.get("ok_bit_for_bit") is True)

    # (c) 不变量科学字段逐位
    field_cmp, ok_fields = {}, True
    for f in INVARIANT_FIELDS:
        same = canon(run.get(f)) == canon(ref.get(f))
        field_cmp[f] = bool(same)
        ok_fields = ok_fields and same
    # ray_data / min_k_raw:剥 legacy 键后逐位
    for f in ("ray_data", "min_k_raw_readings"):
        same = canon(strip_legacy(run.get(f))) == canon(strip_legacy(ref.get(f)))
        field_cmp[f + "(legacy 键剥除后)"] = bool(same)
        ok_fields = ok_fields and same
    # legacy 键本身:须恰好漂移 ≈ PERTURB(证明扰动确实注入、且只注入了它)
    ref_leg = dict(collect_legacy_values(ref.get("ray_data")))
    run_leg = dict(collect_legacy_values(run.get("ray_data")))
    leg_deltas = [abs(run_leg[k] - ref_leg[k]) for k in ref_leg if k in run_leg]
    ok_leg_shift = (len(leg_deltas) == len(ref_leg) and len(leg_deltas) > 0 and
                    all(abs(d - PERTURB) <= 1e-15 for d in leg_deltas))

    ok_source = run.get("source_sha256") == ref.get("source_sha256")

    verdict["checks"] = {
        "(a)_status_DONE": bool(ok_status),
        "(b)_lineage_non_host_expected_drift": bool(ok_lineage),
        "(b)_lineage_diff_scale~perturbation": bool(ok_diff_scale),
        "(b)_official_run_is_host_bit_for_bit(对照)": bool(ref_is_host),
        "(c)_invariant_science_fields_bit_for_bit": bool(ok_fields),
        "(c)_legacy_keys_shift_exactly_perturbation": bool(ok_leg_shift),
        "same_source_sha256": bool(ok_source),
        "official_files_untouched": bool(officials_untouched),
    }
    verdict["field_comparison"] = field_cmp
    verdict["lineage_record_under_test"] = lin
    verdict["n_legacy_values_compared"] = len(leg_deltas)
    verdict["test_run_status"] = run.get("status")
    verdict["test_run_out"] = os.path.relpath(TEST_OUT, ROOT)
    verdict["state_redirect"] = tmp_state

    all_ok = all(verdict["checks"].values())
    verdict["PASS"] = bool(all_ok)
    verdict["status"] = "DONE" if all_ok else "FAIL"
    verdict["total_seconds"] = time.time() - t0
    verdict["source_sha256"] = sha256_file(__file__)
    verdict["target_script_sha256"] = sha256_file(TARGET)
    with open(VERDICT_OUT, "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, ensure_ascii=False, indent=2)
    with open(VERDICT_OUT, "rb") as fh:
        vsha = hashlib.sha256(fh.read()).hexdigest()

    print("=" * 74)
    print("[pathtest] checks:")
    for k, v in verdict["checks"].items():
        print("    %-52s %s" % (k, "PASS" if v else "FAIL"))
    print("[pathtest] invariant fields bit-for-bit: %d/%d"
          % (sum(field_cmp.values()), len(field_cmp)))
    print("[pathtest] OVERALL: %s" % ("PASS" if all_ok else "FAIL"))
    print("verdict  -> %s (sha256 %s)" % (os.path.relpath(VERDICT_OUT, ROOT), vsha))
    print("test run -> %s" % os.path.relpath(TEST_OUT, ROOT))
    print("total %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
