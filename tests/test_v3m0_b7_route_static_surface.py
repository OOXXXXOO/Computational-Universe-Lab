"""Task-7 tests for the frozen B7 route static-surface validator."""

from __future__ import annotations

import copy
import importlib
import inspect

import pytest

from rulespace_v3.b7_replay_core_v1 import canonical_sha_v1


ROUTE_ENTRY = {
    "route_id": "A_FLAT",
    "route_schema_domain": "experimental.v3m0.b7.a-flat",
    "route_module": "experiments.v3m0_b7_schema_lab.a_flat",
    "route_source_path": "experiments/v3m0_b7_schema_lab/a_flat.py",
    "wire_schema_id": "experimental.v3m0.b7.a-flat.wire.v1",
}
ROUTE_COMMIT = "a" * 40
COMMON_COMMIT = "b" * 40
LEGAL_ROUTE_SOURCE = b"""from __future__ import annotations

ROUTE_ID = "A_FLAT"
WIRE_SCHEMA_ID = "experimental.v3m0.b7.a-flat.wire.v1"

def encode_normalized_transcript(canonical_transcript_utf8):
    return canonical_transcript_utf8

def verify_and_decode_route_wire(canonical_route_wire_utf8):
    return canonical_route_wire_utf8
"""


def _route_blob(source: bytes = LEGAL_ROUTE_SOURCE):
    return (
        ROUTE_COMMIT,
        ROUTE_ENTRY["route_source_path"],
        "100644",
        source,
    )


def _production_blobs():
    return (
        (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),
        (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
    )


def _sealed_route_manifest(
    common,
    source: bytes = LEGAL_ROUTE_SOURCE,
    production_blobs=None,
):
    if production_blobs is None:
        production_blobs = _production_blobs()
    route_blob = _route_blob(source)
    computed = common._compute_route_static_fields_v1(
        ROUTE_ENTRY["route_id"],
        COMMON_COMMIT,
        route_blob,
        production_blobs,
    )
    manifest = {
        "route_manifest_schema_version": "experimental.v3m0.b7.route-manifest.v1",
        **ROUTE_ENTRY,
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
        "output_schema_version": ROUTE_ENTRY["wire_schema_id"],
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
    manifest["route_manifest_sha"] = canonical_sha_v1(
        {
            name: value
            for name, value in manifest.items()
            if name != "route_manifest_sha"
        }
    )
    return manifest


def _assert_route_source_rejected(source: bytes) -> None:
    common = _common_module()
    with pytest.raises((TypeError, ValueError, SyntaxError, UnicodeError)):
        manifest = _sealed_route_manifest(common, source)
        common.validate_route_static_surface_v1(
            manifest,
            _route_blob(source),
            _production_blobs(),
        )


def _common_module():
    return importlib.import_module("experiments.v3m0_b7_schema_lab.common")


def test_route_static_validator_exposes_only_caller_supplied_git_blobs() -> None:
    common = _common_module()

    assert tuple(
        inspect.signature(common.validate_route_static_surface_v1).parameters
    ) == ("raw_body", "route_blob", "production_blobs")


def test_route_static_validator_accepts_minimal_frozen_route() -> None:
    common = _common_module()
    manifest = _sealed_route_manifest(common)

    assert (
        common.validate_route_static_surface_v1(
            manifest,
            _route_blob(),
            _production_blobs(),
        )
        == manifest
    )


@pytest.mark.parametrize(
    "source",
    (
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript",
            b"def encode_normalized_transcript_extra",
        ),
        LEGAL_ROUTE_SOURCE
        + b"\ndef accidental_public_surface(value):\n    return value\n",
        LEGAL_ROUTE_SOURCE + b"\ndef __double_private(value):\n    return value\n",
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript(canonical_transcript_utf8):",
            b"def encode_normalized_transcript(wrong_argument):",
        ),
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript(canonical_transcript_utf8):",
            b"def encode_normalized_transcript(canonical_transcript_utf8=b'x'):",
        ),
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript",
            b"async def encode_normalized_transcript",
        ),
        LEGAL_ROUTE_SOURCE.replace(b'ROUTE_ID = "A_FLAT"', b'ROUTE_ID = "C_UNION"'),
        LEGAL_ROUTE_SOURCE + b"\n_private_constant = 1\n",
        LEGAL_ROUTE_SOURCE + b"\nrun_at_import_time()\n",
        LEGAL_ROUTE_SOURCE + b"\nif True:\n    pass\n",
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript(canonical_transcript_utf8):",
            b"@staticmethod\ndef encode_normalized_transcript(canonical_transcript_utf8):",
        ),
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript(canonical_transcript_utf8):",
            b"def encode_normalized_transcript(canonical_transcript_utf8=(bytes())):",
        ),
        LEGAL_ROUTE_SOURCE.replace(
            b"def encode_normalized_transcript(canonical_transcript_utf8):",
            b"def encode_normalized_transcript(canonical_transcript_utf8=[x for x in ()]):",
        ),
    ),
)
def test_route_static_validator_rejects_api_and_import_time_execution_attacks(
    source: bytes,
) -> None:
    _assert_route_source_rejected(source)


@pytest.mark.parametrize(
    "attack",
    (
        b"import os\n",
        b"from os import system\n",
        b"import rulespace_v3\n",
        b"from rulespace_gpu import verify\n",
        b"from json import *\n",
    ),
)
def test_route_static_validator_rejects_every_unlisted_or_star_import(
    attack: bytes,
) -> None:
    source = LEGAL_ROUTE_SOURCE.replace(
        b"from __future__ import annotations\n",
        b"from __future__ import annotations\n" + attack,
    )
    _assert_route_source_rejected(source)


@pytest.mark.parametrize(
    "attack_body",
    (
        b"    return open('secret')",
        b"    print(canonical_transcript_utf8)\n    return canonical_transcript_utf8",
        b"    return eval('canonical_transcript_utf8')",
        b"    return getattr(canonical_transcript_utf8, 'hex')()",
        b"    return __import__('json')",
        b"    return canonical_transcript_utf8.system()",
        b"    return canonical_transcript_utf8.spawnv()",
        b"    return canonical_transcript_utf8.execve()",
    ),
)
def test_route_static_validator_rejects_reachable_dynamic_process_and_io_surfaces(
    attack_body: bytes,
) -> None:
    source = LEGAL_ROUTE_SOURCE.replace(
        b"    return canonical_transcript_utf8",
        attack_body,
        1,
    )
    _assert_route_source_rejected(source)


@pytest.mark.parametrize(
    "identifier",
    (
        "_authority_token",
        "_CAPABILITY_token",
        "_someIssuerToken",
        "_verified_result",
        "_wrapper_surface",
    ),
)
def test_route_static_validator_rejects_authority_and_wrapper_identifier_surfaces(
    identifier: str,
) -> None:
    source = LEGAL_ROUTE_SOURCE + (
        f"\ndef {identifier}(value):\n    return value\n".encode("utf-8")
    )
    _assert_route_source_rejected(source)


def test_route_static_validator_rejects_each_recomputed_manifest_scan_attack() -> None:
    common = _common_module()
    legal = _sealed_route_manifest(common)
    for field, hostile in (
        ("route_source_sha256", "0" * 64),
        ("static_api_scan_sha", "0" * 64),
        ("static_import_scan_sha", "0" * 64),
        ("static_authority_surface_scan_sha", "0" * 64),
        ("production_import_scan_sha", "0" * 64),
        ("production_imported_by_route", True),
        ("route_imported_by_production", True),
        ("authority_surface_count", 1),
        ("wrapper_surface_count", 1),
    ):
        attacked = copy.deepcopy(legal)
        attacked[field] = hostile
        attacked["route_manifest_sha"] = canonical_sha_v1(
            {
                name: value
                for name, value in attacked.items()
                if name != "route_manifest_sha"
            }
        )
        with pytest.raises((TypeError, ValueError)):
            common.validate_route_static_surface_v1(
                attacked,
                _route_blob(),
                _production_blobs(),
            )


@pytest.mark.parametrize(
    "source",
    (
        LEGAL_ROUTE_SOURCE + b"\ndef _identity(value):\n    return value\n",
        LEGAL_ROUTE_SOURCE.replace(
            b"    return canonical_transcript_utf8",
            b"    return _identity(canonical_transcript_utf8)",
            1,
        )
        + b"\ndef _identity(value):\n    return value\n",
        LEGAL_ROUTE_SOURCE + b"\ndef _unreachable(value):\n    return open(value)\n",
        LEGAL_ROUTE_SOURCE.replace(
            b"from __future__ import annotations\n",
            b"from __future__ import annotations\nimport json\n",
        ),
        LEGAL_ROUTE_SOURCE.replace(
            b"from __future__ import annotations\n",
            b"from __future__ import annotations\n"
            b"from .common import B7LabMutationRejected\n",
        ),
        LEGAL_ROUTE_SOURCE.replace(
            b"from __future__ import annotations\n",
            b"from __future__ import annotations\nimport dataclasses\n",
        )
        + b"\n@dataclasses.dataclass(frozen=True)\n"
        b"class _FrozenRecord:\n    value: bytes\n",
    ),
)
def test_route_static_validator_accepts_frozen_private_and_import_surfaces(
    source: bytes,
) -> None:
    common = _common_module()
    manifest = _sealed_route_manifest(common, source)

    assert (
        common.validate_route_static_surface_v1(
            manifest,
            _route_blob(source),
            _production_blobs(),
        )
        == manifest
    )


@pytest.mark.parametrize(
    "class_source",
    (
        b"\n@dataclasses.dataclass\nclass _Record:\n    value: bytes\n",
        b"\n@dataclasses.dataclass(frozen=False)\nclass _Record:\n    value: bytes\n",
        b"\n@dataclasses.dataclass(frozen=True, slots=True)\n"
        b"class _Record:\n    value: bytes\n",
        b"\n@dataclasses.dataclass(frozen=True)\nclass _Record:\n    value = bytes()\n",
    ),
)
def test_route_static_validator_rejects_decorator_and_class_body_execution(
    class_source: bytes,
) -> None:
    source = (
        LEGAL_ROUTE_SOURCE.replace(
            b"from __future__ import annotations\n",
            b"from __future__ import annotations\nimport dataclasses\n",
        )
        + class_source
    )
    _assert_route_source_rejected(source)


@pytest.mark.parametrize(
    "production_import",
    (
        b"import experiments.v3m0_b7_schema_lab.a_flat\n",
        b"from experiments.v3m0_b7_schema_lab.a_flat import ROUTE_ID\n",
        b"import experiments.v3m0_b7_schema_lab.a_flat.hidden\n",
    ),
)
def test_route_static_validator_rejects_production_importing_the_route(
    production_import: bytes,
) -> None:
    common = _common_module()
    production_blobs = (
        (
            COMMON_COMMIT,
            "rulespace_v3/__init__.py",
            "100644",
            production_import,
        ),
        (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
    )
    computed = common._compute_route_static_fields_v1(
        "A_FLAT",
        COMMON_COMMIT,
        _route_blob(),
        production_blobs,
    )
    assert computed["route_imported_by_production"] is True
    with pytest.raises((TypeError, ValueError)):
        manifest = _sealed_route_manifest(common, production_blobs=production_blobs)
        common.validate_route_static_surface_v1(
            manifest,
            _route_blob(),
            production_blobs,
        )


@pytest.mark.parametrize(
    "production_blobs",
    (
        [],
        (),
        ((COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),),
        (
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),
        ),
        (
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
        ),
        (
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),
            (COMMON_COMMIT, "untrusted/__init__.py", "100644", b""),
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
        ),
        (
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "160000", b""),
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
        ),
        (
            ("c" * 40, "rulespace_v3/__init__.py", "100644", b""),
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
        ),
        (
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b"\xff"),
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
        ),
        (
            (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b"if:\n"),
            (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
        ),
    ),
)
def test_route_static_validator_rejects_nonexact_production_source_closure(
    production_blobs,
) -> None:
    common = _common_module()
    with pytest.raises((TypeError, ValueError, SyntaxError, UnicodeError)):
        common._compute_route_static_fields_v1(
            "A_FLAT",
            COMMON_COMMIT,
            _route_blob(),
            production_blobs,
        )


@pytest.mark.parametrize(
    "route_blob",
    (
        [
            ROUTE_COMMIT,
            ROUTE_ENTRY["route_source_path"],
            "100644",
            LEGAL_ROUTE_SOURCE,
        ],
        ("A" * 40, ROUTE_ENTRY["route_source_path"], "100644", LEGAL_ROUTE_SOURCE),
        (
            ROUTE_COMMIT,
            "experiments/v3m0_b7_schema_lab/c_union.py",
            "100644",
            LEGAL_ROUTE_SOURCE,
        ),
        (
            ROUTE_COMMIT,
            ROUTE_ENTRY["route_source_path"],
            "100755",
            LEGAL_ROUTE_SOURCE,
        ),
        (ROUTE_COMMIT, ROUTE_ENTRY["route_source_path"], "100644", "not-bytes"),
        (
            ROUTE_COMMIT,
            ROUTE_ENTRY["route_source_path"],
            "100644",
            b"\xef\xbb\xbf" + LEGAL_ROUTE_SOURCE,
        ),
    ),
)
def test_route_static_validator_rejects_nonexact_route_blob_identity(
    route_blob,
) -> None:
    common = _common_module()
    legal = _sealed_route_manifest(common)
    with pytest.raises((TypeError, ValueError, SyntaxError, UnicodeError)):
        common.validate_route_static_surface_v1(
            legal,
            route_blob,
            _production_blobs(),
        )


def test_route_static_scan_roots_are_raw_byte_deterministic() -> None:
    common = _common_module()
    first = common._compute_route_static_fields_v1(
        "A_FLAT",
        COMMON_COMMIT,
        _route_blob(),
        _production_blobs(),
    )
    repeated = common._compute_route_static_fields_v1(
        "A_FLAT",
        COMMON_COMMIT,
        _route_blob(),
        _production_blobs(),
    )
    changed_source = LEGAL_ROUTE_SOURCE + b"\n"
    changed = common._compute_route_static_fields_v1(
        "A_FLAT",
        COMMON_COMMIT,
        _route_blob(changed_source),
        _production_blobs(),
    )

    assert first == repeated
    for field in (
        "route_source_sha256",
        "static_api_scan_sha",
        "static_import_scan_sha",
        "static_authority_surface_scan_sha",
        "production_import_scan_sha",
    ):
        assert changed[field] != first[field]


@pytest.mark.parametrize(
    ("field", "hostile"),
    (
        ("route_id", "C_UNION"),
        ("route_schema_domain", "experimental.v3m0.b7.c-union"),
        ("route_module", "experiments.v3m0_b7_schema_lab.c_union"),
        ("route_source_path", "experiments/v3m0_b7_schema_lab/c_union.py"),
        ("wire_schema_id", "experimental.v3m0.b7.c-union.wire.v1"),
        ("route_commit_sha", "c" * 40),
        ("common_commit_sha", "c" * 40),
        ("encoder_symbol", "wrong_encoder"),
        ("verifier_decoder_symbol", "wrong_decoder"),
        ("input_schema_version", "experimental.v3m0.b7.wrong.v1"),
        ("output_schema_version", "experimental.v3m0.b7.c-union.wire.v1"),
    ),
)
def test_route_static_validator_rejects_every_registry_and_blob_join_attack(
    field: str,
    hostile: str,
) -> None:
    common = _common_module()
    attacked = copy.deepcopy(_sealed_route_manifest(common))
    attacked[field] = hostile
    attacked["route_manifest_sha"] = canonical_sha_v1(
        {
            name: value
            for name, value in attacked.items()
            if name != "route_manifest_sha"
        }
    )

    with pytest.raises((TypeError, ValueError)):
        common.validate_route_static_surface_v1(
            attacked,
            _route_blob(),
            _production_blobs(),
        )


def test_route_static_validator_is_detached_and_idempotent() -> None:
    common = _common_module()
    manifest = _sealed_route_manifest(common)

    first = common.validate_route_static_surface_v1(
        manifest,
        _route_blob(),
        _production_blobs(),
    )
    second = common.validate_route_static_surface_v1(
        first,
        _route_blob(),
        _production_blobs(),
    )

    assert first == manifest
    assert second == first
    assert first is not manifest
    assert second is not first


def test_route_static_production_scan_binds_non_python_blob_bytes() -> None:
    common = _common_module()
    base = _production_blobs()
    with_readme = (
        (COMMON_COMMIT, "rulespace_v3/README.md", "100644", b"frozen\n"),
        base[0],
        base[1],
    )
    changed_readme = (
        (COMMON_COMMIT, "rulespace_v3/README.md", "100644", b"changed\n"),
        base[0],
        base[1],
    )

    first = common._compute_route_static_fields_v1(
        "A_FLAT", COMMON_COMMIT, _route_blob(), with_readme
    )
    changed = common._compute_route_static_fields_v1(
        "A_FLAT", COMMON_COMMIT, _route_blob(), changed_readme
    )

    assert first["production_import_scan_sha"] != changed["production_import_scan_sha"]
    assert first["static_api_scan_sha"] == changed["static_api_scan_sha"]
