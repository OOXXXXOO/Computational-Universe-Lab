"""Mechanical E07/E08 gates over the frozen route static scanner."""

from __future__ import annotations

import copy
import inspect

import pytest


ROUTE_COMMIT = "a" * 40
COMMON_COMMIT = "b" * 40
ROUTE_PATH = "experiments/v3m0_b7_schema_lab/a_flat.py"
ROUTE_MODULE = "experiments.v3m0_b7_schema_lab.a_flat"
WIRE_ID = "experimental.v3m0.b7.a-flat.wire.v1"
LEGAL_ROUTE_SOURCE = b"""from __future__ import annotations

ROUTE_ID = "A_FLAT"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"

def encode_normalized_transcript(canonical_transcript_utf8):
    return canonical_transcript_utf8

def verify_and_decode_route_wire(canonical_route_wire_utf8):
    return canonical_route_wire_utf8
"""


def _common():
    from experiments.v3m0_b7_schema_lab import common

    return common


def _route_blob(source: bytes = LEGAL_ROUTE_SOURCE):
    return (ROUTE_COMMIT, ROUTE_PATH, "100644", source)


def _production_blobs(source: bytes = b""):
    return (
        (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", source),
        (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
    )


def _manifest(source: bytes = LEGAL_ROUTE_SOURCE, production_blobs=None):
    common = _common()
    if production_blobs is None:
        production_blobs = _production_blobs()
    computed = common._compute_route_static_fields_v1(
        "A_FLAT", COMMON_COMMIT, _route_blob(source), production_blobs
    )
    raw = {
        "route_manifest_schema_version": "experimental.v3m0.b7.route-manifest.v1",
        "route_id": "A_FLAT",
        "route_schema_domain": "experimental.v3m0.b7.a-flat",
        "route_module": ROUTE_MODULE,
        "route_source_path": ROUTE_PATH,
        "wire_schema_id": WIRE_ID,
        "route_commit_sha": ROUTE_COMMIT,
        "route_source_sha256": computed["route_source_sha256"],
        "common_commit_sha": COMMON_COMMIT,
        "common_source_sha256": "c" * 64,
        "compare_source_sha256": "d" * 64,
        "corpus_spec_sha": "e" * 64,
        "mutation_universe_sha": "f" * 64,
        "metric_spec_sha": "1" * 64,
        "encoder_symbol": "encode_normalized_transcript",
        "verifier_decoder_symbol": "verify_and_decode_route_wire",
        "input_schema_version": "experimental.v3m0.b7.normalized-transcript.v1",
        "output_schema_version": WIRE_ID,
        "static_api_scan_sha": computed["static_api_scan_sha"],
        "static_import_scan_sha": computed["static_import_scan_sha"],
        "static_authority_surface_scan_sha": computed[
            "static_authority_surface_scan_sha"
        ],
        "production_import_scan_sha": computed["production_import_scan_sha"],
        "production_imported_by_route": False,
        "route_imported_by_production": False,
        "authority_surface_count": 0,
        "wrapper_surface_count": 0,
        "route_manifest_sha": "",
    }
    raw["route_manifest_sha"] = common.canonical_sha_v1(
        {name: value for name, value in raw.items() if name != "route_manifest_sha"}
    )
    return raw


def test_static_gate_signatures_are_exact() -> None:
    common = _common()
    assert tuple(inspect.signature(common.build_gate_e07_v1).parameters) == (
        "phase",
        "route_manifest",
        "route_blob",
        "production_blobs",
    )
    assert tuple(inspect.signature(common.validate_gate_e07_v1).parameters) == (
        "raw_body",
        "route_manifest",
        "route_blob",
        "production_blobs",
    )
    assert tuple(inspect.signature(common.build_gate_e08_v1).parameters) == (
        "phase",
        "route_manifest",
        "route_blob",
        "production_blobs",
    )
    assert tuple(inspect.signature(common.validate_gate_e08_v1).parameters) == (
        "raw_body",
        "route_manifest",
        "route_blob",
        "production_blobs",
    )


@pytest.mark.parametrize("phase", ("D0", "D1"))
def test_e07_e08_recompute_from_the_same_validated_static_surface(phase: str) -> None:
    common = _common()
    manifest = _manifest()
    route_blob = _route_blob()
    production_blobs = _production_blobs()

    e07 = common.build_gate_e07_v1(
        phase=phase,
        route_manifest=manifest,
        route_blob=route_blob,
        production_blobs=production_blobs,
    )
    e08 = common.build_gate_e08_v1(
        phase=phase,
        route_manifest=manifest,
        route_blob=route_blob,
        production_blobs=production_blobs,
    )

    assert e07["passed"] is True
    assert e07["observation"]["predicate_result_bits"] == "1111"
    assert e08["passed"] is True
    assert e08["observation"]["predicate_result_bits"] == "111"
    assert (
        e07["observation"]["domain_root_sha"] != e08["observation"]["domain_root_sha"]
    )
    assert (
        common.validate_gate_e07_v1(
            e07,
            route_manifest=manifest,
            route_blob=route_blob,
            production_blobs=production_blobs,
        )
        == e07
    )
    assert (
        common.validate_gate_e08_v1(
            e08,
            route_manifest=manifest,
            route_blob=route_blob,
            production_blobs=production_blobs,
        )
        == e08
    )


@pytest.mark.parametrize("gate_id", ("e07", "e08"))
def test_static_gate_validator_rejects_self_report_flip(gate_id: str) -> None:
    common = _common()
    manifest = _manifest()
    build = getattr(common, f"build_gate_{gate_id}_v1")
    validate = getattr(common, f"validate_gate_{gate_id}_v1")
    outcome = build(
        phase="D0",
        route_manifest=manifest,
        route_blob=_route_blob(),
        production_blobs=_production_blobs(),
    )
    hostile = copy.deepcopy(outcome)
    hostile["passed"] = False
    hostile["gate_outcome_sha"] = common.canonical_sha_v1(
        {name: value for name, value in hostile.items() if name != "gate_outcome_sha"}
    )

    with pytest.raises((TypeError, ValueError)):
        validate(
            hostile,
            route_manifest=manifest,
            route_blob=_route_blob(),
            production_blobs=_production_blobs(),
        )


@pytest.mark.parametrize(
    "source",
    (
        LEGAL_ROUTE_SOURCE.replace(
            b"canonical_transcript_utf8):", b"canonical_transcript_utf8, callback):"
        ),
        LEGAL_ROUTE_SOURCE + b"\ndef _authority_wrapper(value):\n    return value\n",
        LEGAL_ROUTE_SOURCE.replace(
            b"from __future__ import annotations\n",
            b"from __future__ import annotations\nimport rulespace_v3\n",
        ),
    ),
)
def test_e07_reuses_frozen_static_scanner_for_api_authority_and_import_attacks(
    source: bytes,
) -> None:
    common = _common()
    with pytest.raises((TypeError, ValueError)):
        common.build_gate_e07_v1(
            phase="D0",
            route_manifest=_manifest(),
            route_blob=_route_blob(source),
            production_blobs=_production_blobs(),
        )


def test_e08_reuses_frozen_production_import_scanner() -> None:
    common = _common()
    production_blobs = _production_blobs(
        b"import experiments.v3m0_b7_schema_lab.a_flat\n"
    )
    with pytest.raises((TypeError, ValueError)):
        common.build_gate_e08_v1(
            phase="D0",
            route_manifest=_manifest(),
            route_blob=_route_blob(),
            production_blobs=production_blobs,
        )
