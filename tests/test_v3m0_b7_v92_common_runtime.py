"""Executable common-layer contracts introduced by the B7 v9.2 overlay."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

from rulespace_v3.b7_replay_core_v1 import canonical_sha_v1


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _overlay() -> dict[str, object]:
    return json.loads(
        (REPOSITORY_ROOT / "docsv3" / "v3-机器合同-B7-v9.2-overlay.json").read_text(
            encoding="utf-8"
        )
    )


def _catalog_entry(record_name: str) -> tuple[object, ...]:
    from experiments.v3m0_b7_schema_lab.common import LAB_EXACT_RECORD_CATALOGS_V2

    matches = [
        entry for entry in LAB_EXACT_RECORD_CATALOGS_V2 if entry[0] == record_name
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize(
    "record_name",
    ("B7LabEnvironmentManifestV2", "B7LabCorpusFixtureV2"),
)
def test_v92_added_record_catalogs_equal_overlay_literals(record_name: str) -> None:
    expected = _overlay()["record_additions"][record_name]
    observed = _catalog_entry(record_name)

    assert observed[1] == expected["schema_id"]
    assert [list(field) for field in observed[3]] == [
        [
            field["name"],
            field["wire_type"],
            field["presence"],
            field["nested_record"],
        ]
        for field in expected["field_specs"]
    ]


def test_v92_effective_d0_d1_catalogs_use_environment_v2() -> None:
    d0 = _catalog_entry("B7LabD0ComparisonV1")
    d1 = _catalog_entry("B7LabD1ComparisonV1")
    assert d0[3][8] == (
        "environment_manifest",
        "B7LabEnvironmentManifestV2",
        "required",
        "B7LabEnvironmentManifestV2",
    )
    assert d1[3][13] == (
        "environment_manifest",
        "B7LabEnvironmentManifestV2",
        "required",
        "B7LabEnvironmentManifestV2",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _live_bundle() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    from experiments.v3m0_b7_schema_lab.compare import (
        precheck_python_invocation_identity_v2,
        run_python_environment_import_probe_v2,
    )

    invocation = Path(sys.executable)
    target = Path(os.path.realpath(invocation))
    prefix = Path(sys.prefix)
    pyvenv_cfg = prefix / "pyvenv.cfg"
    identity = precheck_python_invocation_identity_v2(
        python_invocation_path=str(invocation),
        recorded_realpath=str(target),
        recorded_raw_sha256=_sha256(target),
        recorded_venv_prefix=str(prefix),
        recorded_pyvenv_cfg_path=str(pyvenv_cfg),
        recorded_pyvenv_cfg_raw_sha256=_sha256(pyvenv_cfg),
    )
    assert identity["precheck_passed"] is True
    probe = run_python_environment_import_probe_v2(
        python_invocation_path=str(invocation),
        python_identity_observation=identity,
    )
    assert probe["probe_passed"] is True
    report = probe["report"]
    manifest = {
        "environment_schema_version": "experimental.v3m0.b7.environment-manifest.v2",
        "python_implementation": report["python_implementation"],
        "python_version": report["python_version"],
        "python_invocation_path": str(invocation),
        "python_executable_realpath": str(target),
        "python_executable_raw_sha256": _sha256(target),
        "python_invocation_identity_sha": identity["python_invocation_identity_sha"],
        "python_venv_prefix": str(prefix),
        "python_pyvenv_cfg_path": str(pyvenv_cfg),
        "python_pyvenv_cfg_raw_sha256": _sha256(pyvenv_cfg),
        "numpy_version": report["numpy_version"],
        "scipy_version": report["scipy_version"],
        "platform_system": report["platform_system"],
        "platform_release": report["platform_release"],
        "platform_machine": report["platform_machine"],
        "numpy_float64_dtype_str": report["numpy_float64_dtype_str"],
        "numpy_float64_itemsize": report["numpy_float64_itemsize"],
        "byteorder": report["byteorder"],
        "python_hash_seed": "0",
        "blas_thread_settings": [
            ["OPENBLAS_NUM_THREADS", "1"],
            ["OMP_NUM_THREADS", "1"],
            ["MKL_NUM_THREADS", "1"],
            ["VECLIB_MAXIMUM_THREADS", "1"],
            ["NUMEXPR_NUM_THREADS", "1"],
        ],
        "threadpool_info": report["threadpool_info"],
        "fresh_process_per_capture": True,
        "environment_sha": "",
    }
    manifest["environment_sha"] = canonical_sha_v1(
        {key: value for key, value in manifest.items() if key != "environment_sha"}
    )
    return manifest, identity, probe


def _rehash(manifest: dict[str, object]) -> None:
    manifest["environment_sha"] = canonical_sha_v1(
        {key: value for key, value in manifest.items() if key != "environment_sha"}
    )


def test_v92_environment_validator_recomputes_live_identity_and_probe() -> None:
    from experiments.v3m0_b7_schema_lab.common import (
        validate_environment_manifest_v2,
    )

    manifest, identity, probe = _live_bundle()
    assert (
        validate_environment_manifest_v2(
            manifest,
            python_identity_observation=identity,
            python_probe_result=probe,
        )
        == manifest
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("python_invocation_identity_sha", "0" * 64),
        ("numpy_version", "forged"),
        ("python_hash_seed", "1"),
        ("fresh_process_per_capture", False),
    ),
)
def test_v92_environment_validator_rejects_resigned_runtime_splices(
    field: str,
    value: object,
) -> None:
    from experiments.v3m0_b7_schema_lab.common import (
        validate_environment_manifest_v2,
    )

    manifest, identity, probe = _live_bundle()
    manifest[field] = value
    _rehash(manifest)
    with pytest.raises((TypeError, ValueError)):
        validate_environment_manifest_v2(
            manifest,
            python_identity_observation=identity,
            python_probe_result=probe,
        )
