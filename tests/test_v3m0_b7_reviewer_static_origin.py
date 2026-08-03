"""Attack tests for the frozen B7 reviewer source precheck validators."""

from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path

import pytest

from experiments.v3m0_b7_schema_lab import common


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_COMMIT = "e" * 40
COMMON_COMMIT = "c" * 40
ROUTE_COMMITS = ("a" * 40, "b" * 40, "d" * 40)
ROUTE_ROWS = (
    (
        "A_FLAT",
        "experimental.v3m0.b7.a-flat",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experiments/v3m0_b7_schema_lab/a_flat.py",
        "experimental.v3m0.b7.a-flat.wire.v1",
    ),
    (
        "B_PROGRESS",
        "experimental.v3m0.b7.b-progress",
        "experiments.v3m0_b7_schema_lab.b_progress",
        "experiments/v3m0_b7_schema_lab/b_progress.py",
        "experimental.v3m0.b7.b-progress.wire.v1",
    ),
    (
        "C_UNION",
        "experimental.v3m0.b7.c-union",
        "experiments.v3m0_b7_schema_lab.c_union",
        "experiments/v3m0_b7_schema_lab/c_union.py",
        "experimental.v3m0.b7.c-union.wire.v1",
    ),
)


def _route_source(row: tuple[str, str, str, str, str]) -> bytes:
    route_id, _domain, _module, _path, wire_schema = row
    return f'''from __future__ import annotations

ROUTE_ID = "{route_id}"
WIRE_SCHEMA_ID = "{wire_schema}"

def encode_normalized_transcript(canonical_transcript_utf8):
    return canonical_transcript_utf8

def verify_and_decode_route_wire(canonical_route_wire_utf8):
    return canonical_route_wire_utf8
'''.encode()


def _production_blobs():
    return (
        (COMMON_COMMIT, "rulespace_v3/__init__.py", "100644", b""),
        (COMMON_COMMIT, "rulespace_gpu/__init__.py", "100644", b""),
    )


def _route_manifest(row, route_commit, source):
    route_id, domain, module, path, wire_schema = row
    route_blob = (route_commit, path, "100644", source)
    computed = common._compute_route_static_fields_v1(
        route_id,
        COMMON_COMMIT,
        route_blob,
        _production_blobs(),
    )
    body = {
        "route_manifest_schema_version": "experimental.v3m0.b7.route-manifest.v1",
        "route_id": route_id,
        "route_schema_domain": domain,
        "route_module": module,
        "route_source_path": path,
        "wire_schema_id": wire_schema,
        "route_commit_sha": route_commit,
        "route_source_sha256": computed["route_source_sha256"],
        "common_commit_sha": COMMON_COMMIT,
        "common_source_sha256": "1" * 64,
        "compare_source_sha256": "2" * 64,
        "corpus_spec_sha": "3" * 64,
        "mutation_universe_sha": "4" * 64,
        "metric_spec_sha": "5" * 64,
        "encoder_symbol": "encode_normalized_transcript",
        "verifier_decoder_symbol": "verify_and_decode_route_wire",
        "input_schema_version": "experimental.v3m0.b7.normalized-transcript.v1",
        "output_schema_version": wire_schema,
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
    body["route_manifest_sha"] = common.canonical_sha_v1(
        {key: value for key, value in body.items() if key != "route_manifest_sha"}
    )
    return body


_OUTER_HELPERS = (
    "_require_lower_hex_v1",
    "build_sanitized_reviewer_environment_v1",
    "recheck_frozen_python_executable_identity_v1",
    "_require_normalized_absolute_path_v2",
    "_stable_regular_file_observation_v2",
    "_resolve_python_invocation_chain_v2",
    "_nearest_pyvenv_cfg_v2",
    "_python_environment_probe_report_is_well_typed_v2",
    "_empty_process_observation_v1",
    "_process_observation_v1",
    "_validate_bounded_process_configuration_v1",
    "run_bounded_reviewer_process_v1",
)
_OUTER_ROOTS = (
    "precheck_python_invocation_identity_v2",
    "recheck_python_invocation_identity_v2",
    "run_python_environment_import_probe_v2",
    "capture_environment_manifest_v2",
    "run_frozen_reviewer_process_v2",
)


def _compare_source() -> bytes:
    lines = [
        "from __future__ import annotations",
        "",
        "import hashlib",
        "import sys",
        "",
        "import experiments.v3m0_b7_schema_lab.common as _common",
        "",
    ]
    for helper in _OUTER_HELPERS:
        lines.extend((f"def {helper}(*args, **kwargs):", "    return None", ""))
    common_calls = (
        "canonical_json_bytes_v1({})",
        "canonical_sha_v1({})",
        "strict_json_loads_v1(b'{}')",
        (
            "validate_environment_manifest_v2({}, "
            "python_identity_observation={}, python_probe_result={})"
        ),
        "validate_exact_lab_record_v1('B7LabReplayReportV1', {})",
    )
    root_body = [f"    {name}()" for name in _OUTER_HELPERS]
    root_body.extend(f"    _common.{call}" for call in common_calls)
    root_body.append("    return None")
    for root in _OUTER_ROOTS:
        lines.extend((f"def {root}():", *root_body, ""))
    lines.extend(
        (
            "def _load_all_routes():",
            (
                "    from experiments.v3m0_b7_schema_lab.a_flat "
                "import ROUTE_ID as a_route_id, "
                "encode_normalized_transcript as encode_a"
            ),
            (
                "    from experiments.v3m0_b7_schema_lab.b_progress "
                "import ROUTE_ID as b_route_id"
            ),
            (
                "    from experiments.v3m0_b7_schema_lab.c_union "
                "import ROUTE_ID as c_route_id"
            ),
            "    return (a_route_id, b_route_id, c_route_id, encode_a(b'{}'))",
            "",
            "def _emit_report(payload):",
            "    return sys.stdout.buffer.write(payload + b'\\n')",
            "",
            "def _review_corpus_replay_cli():",
            "    _common._child_common_identity(b'{}')",
            "    _load_all_routes()",
            "    return _emit_report(b'{}')",
            "",
            "def _review_metric_replay_cli():",
            "    _common._child_common_identity(b'{}')",
            "    _load_all_routes()",
            "    return _emit_report(b'{}')",
            "",
        )
    )
    return "\n".join(lines).encode()


def _static_inputs(compare_source: bytes | None = None):
    if compare_source is None:
        compare_source = _compare_source()
    route_sources = tuple(_route_source(row) for row in ROUTE_ROWS)
    manifests = tuple(
        _route_manifest(row, commit, source)
        for row, commit, source in zip(ROUTE_ROWS, ROUTE_COMMITS, route_sources)
    )
    common_source = (
        REPO_ROOT / "experiments/v3m0_b7_schema_lab/common.py"
    ).read_bytes() + (
        b"\n\ndef _child_common_identity(value):\n"
        b"    return _pure_core._child_core_identity(value)\n"
    )
    core_source = (REPO_ROOT / "rulespace_v3/b7_replay_core_v1.py").read_bytes() + (
        b"\n\ndef _child_core_identity(value):\n    return value\n"
    )
    source_rows = [
        (
            EVIDENCE_COMMIT,
            "experiments/v3m0_b7_schema_lab/__init__.py",
            "100644",
            b"",
        ),
        (
            EVIDENCE_COMMIT,
            "experiments/v3m0_b7_schema_lab/common.py",
            "100644",
            common_source,
        ),
        (
            EVIDENCE_COMMIT,
            "experiments/v3m0_b7_schema_lab/compare.py",
            "100644",
            compare_source,
        ),
        *(
            (EVIDENCE_COMMIT, row[3], "100644", source)
            for row, source in zip(ROUTE_ROWS, route_sources)
        ),
        (
            EVIDENCE_COMMIT,
            "rulespace_v3/__init__.py",
            "100644",
            (REPO_ROOT / "rulespace_v3/__init__.py").read_bytes(),
        ),
        (
            EVIDENCE_COMMIT,
            "rulespace_v3/b7_replay_core_v1.py",
            "100644",
            core_source,
        ),
    ]
    return {
        "source_commit_sha": EVIDENCE_COMMIT,
        "common_commit_sha": COMMON_COMMIT,
        "route_manifests": manifests,
        "source_blobs": tuple(source_rows),
        "production_blobs": _production_blobs(),
    }


def test_reviewer_static_surface_has_caller_supplied_pure_signature() -> None:
    assert tuple(
        inspect.signature(common.validate_reviewer_child_static_surface_v1).parameters
    ) == (
        "source_commit_sha",
        "common_commit_sha",
        "route_manifests",
        "source_blobs",
        "production_blobs",
    )


def test_reviewer_static_surface_accepts_both_roles_and_all_routes() -> None:
    result = common.validate_reviewer_child_static_surface_v1(**_static_inputs())

    assert result["static_surface_schema_version"] == (
        "experimental.v3m0.b7.reviewer-child-static-surface.v1"
    )
    assert result["ordered_role_ids"] == ["CORPUS_REPLAY", "METRIC_REPLAY"]
    assert result["ordered_route_ids"] == [row[0] for row in ROUTE_ROWS]
    assert result["ordered_executed_module_paths"] == [
        "experiments/v3m0_b7_schema_lab/__init__.py",
        "experiments/v3m0_b7_schema_lab/compare.py",
        "experiments/v3m0_b7_schema_lab/common.py",
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
        *(row[3] for row in ROUTE_ROWS),
    ]
    assert len(result["reviewer_child_static_scan_sha"]) == 64


@pytest.mark.parametrize(
    "attack_id",
    (
        "current-worktree",
        "extra-module",
        "dynamic-import",
        "omit-route-import",
        "outer-runner-edge",
        "unlisted-import",
        "process-call",
    ),
)
def test_reviewer_static_surface_rejects_closure_and_import_attacks(
    attack_id: str,
) -> None:
    inputs = _static_inputs()
    blobs = list(inputs["source_blobs"])
    compare_index = next(
        index for index, blob in enumerate(blobs) if blob[1].endswith("compare.py")
    )
    compare = blobs[compare_index][3]
    if attack_id == "current-worktree":
        blobs[0] = ("f" * 40, *blobs[0][1:])
    elif attack_id == "extra-module":
        blobs.append(
            (
                EVIDENCE_COMMIT,
                "experiments/v3m0_b7_schema_lab/extra.py",
                "100644",
                b"",
            )
        )
    elif attack_id == "dynamic-import":
        compare = compare.replace(
            b"    _load_all_routes()\n",
            b"    __import__('experiments.v3m0_b7_schema_lab.a_flat')\n",
            1,
        )
    elif attack_id == "omit-route-import":
        compare = compare.replace(
            b"    from experiments.v3m0_b7_schema_lab.c_union import ROUTE_ID as c_route_id\n",
            b"    c_route_id = 'C_UNION'\n",
        )
    elif attack_id == "outer-runner-edge":
        compare = compare.replace(
            b"    _load_all_routes()\n",
            b"    run_python_environment_import_probe_v2()\n",
            1,
        )
    elif attack_id == "unlisted-import":
        compare = compare.replace(b"import hashlib\n", b"import hashlib\nimport antigravity\n")
    else:
        compare = compare.replace(
            b"import hashlib\n",
            b"import hashlib\nimport subprocess\n",
        ).replace(
            b"    _load_all_routes()\n",
            b"    subprocess.Popen(('false',))\n",
            1,
        )
    if attack_id not in ("current-worktree", "extra-module"):
        blobs[compare_index] = (*blobs[compare_index][:3], compare)
    inputs["source_blobs"] = tuple(blobs)

    with pytest.raises((TypeError, ValueError, SyntaxError, UnicodeError)):
        common.validate_reviewer_child_static_surface_v1(**inputs)


def test_reviewer_static_surface_revalidates_each_route_manifest() -> None:
    inputs = _static_inputs()
    manifests = list(copy.deepcopy(inputs["route_manifests"]))
    manifests[1]["static_api_scan_sha"] = "0" * 64
    manifests[1]["route_manifest_sha"] = common.canonical_sha_v1(
        {
            key: value
            for key, value in manifests[1].items()
            if key != "route_manifest_sha"
        }
    )
    inputs["route_manifests"] = tuple(manifests)

    with pytest.raises(ValueError, match="static scan"):
        common.validate_reviewer_child_static_surface_v1(**inputs)


@pytest.mark.parametrize(
    "attack_id",
    (
        "reachable-common-write",
        "numpy-ctypeslib",
        "external-private-attribute",
        "module-object-container-flow",
        "route-alias-unresolved",
        "stdout-not-terminal",
        "nested-default-capability",
    ),
)
def test_reviewer_static_surface_rejects_cross_module_and_flow_attacks(
    attack_id: str,
) -> None:
    inputs = _static_inputs()
    blobs = list(inputs["source_blobs"])
    common_index = next(
        index for index, blob in enumerate(blobs) if blob[1].endswith("common.py")
    )
    compare_index = next(
        index for index, blob in enumerate(blobs) if blob[1].endswith("compare.py")
    )
    common_source = blobs[common_index][3]
    compare_source = blobs[compare_index][3]
    if attack_id == "reachable-common-write":
        common_source += (
            b"\nimport pathlib as _review_pathlib\n"
            b"def _hostile_child(value):\n"
            b"    return _review_pathlib.Path(value).write_text('x')\n"
        )
        compare_source = compare_source.replace(
            b"    _common._child_common_identity(b'{}')\n",
            b"    _common._hostile_child('escape')\n",
            1,
        )
    elif attack_id == "numpy-ctypeslib":
        common_source += (
            b"\nimport numpy as _review_numpy\n"
            b"def _hostile_child(value):\n"
            b"    return _review_numpy.ctypeslib.load_library(value, '.')\n"
        )
        compare_source = compare_source.replace(
            b"    _common._child_common_identity(b'{}')\n",
            b"    _common._hostile_child('x')\n",
            1,
        )
    elif attack_id == "external-private-attribute":
        compare_source = compare_source.replace(
            b"    _load_all_routes()\n",
            b"    hashlib._private_constructor()\n",
            1,
        )
    elif attack_id == "module-object-container-flow":
        compare_source = compare_source.replace(
            b"    _load_all_routes()\n",
            b"    hidden_modules = [hashlib]\n    _load_all_routes()\n",
            1,
        )
    elif attack_id == "route-alias-unresolved":
        compare_source = compare_source.replace(
            b"    return (a_route_id, b_route_id, c_route_id, encode_a(b'{}'))\n",
            b"    return a_route_id()\n",
        )
    elif attack_id == "stdout-not-terminal":
        compare_source = compare_source.replace(
            b"    return sys.stdout.buffer.write(payload + b'\\n')\n",
            (
                b"    sys.stdout.buffer.write(payload + b'\\n')\n"
                b"    return hashlib.sha256(payload).digest()\n"
            ),
        )
    else:
        common_source += (
            b"\nimport pathlib as _review_pathlib\n"
            b"def _hostile_child(value):\n"
            b"    def _hidden(payload=_review_pathlib.Path(value).write_text('x')):\n"
            b"        return payload\n"
            b"    return value\n"
        )
        compare_source = compare_source.replace(
            b"    _common._child_common_identity(b'{}')\n",
            b"    _common._hostile_child('escape')\n",
            1,
        )
    blobs[common_index] = (*blobs[common_index][:3], common_source)
    blobs[compare_index] = (*blobs[compare_index][:3], compare_source)
    inputs["source_blobs"] = tuple(blobs)

    with pytest.raises((TypeError, ValueError, SyntaxError, UnicodeError)):
        common.validate_reviewer_child_static_surface_v1(**inputs)


def _git_blob_oid(raw_bytes: bytes) -> str:
    header = f"blob {len(raw_bytes)}\0".encode()
    return hashlib.sha1(header + raw_bytes).hexdigest()


def _tree_blob(commit: str, path: str, raw_bytes: bytes, mode: str = "100644"):
    return (commit, path, mode, "blob", _git_blob_oid(raw_bytes), raw_bytes)


def _origin_inputs():
    static = _static_inputs()
    executed = {blob[1]: blob[3] for blob in static["source_blobs"]}
    exact_common = {
        "docsv3/v3-机器合同-B7-v9.1-registry.json": (
            REPO_ROOT / "docsv3/v3-机器合同-B7-v9.1-registry.json"
        ).read_bytes(),
        "docsv3/v3-机器合同-B7-v9.2-overlay.json": (
            REPO_ROOT / "docsv3/v3-机器合同-B7-v9.2-overlay.json"
        ).read_bytes(),
        "docsv3/v3-机器合同-B7-v9.2.1-overlay.json": (
            REPO_ROOT / "docsv3/v3-机器合同-B7-v9.2.1-overlay.json"
        ).read_bytes(),
        "experiments/v3m0_b7_schema_lab/__init__.py": executed[
            "experiments/v3m0_b7_schema_lab/__init__.py"
        ],
        "experiments/v3m0_b7_schema_lab/common.py": executed[
            "experiments/v3m0_b7_schema_lab/common.py"
        ],
        "experiments/v3m0_b7_schema_lab/compare.py": executed[
            "experiments/v3m0_b7_schema_lab/compare.py"
        ],
        "tests/fixtures/v3m0_b7_schema_lab_corpus.json": b"{}\n",
    }
    rulespace = {}
    for path in sorted((REPO_ROOT / "rulespace_v3").glob("**/*")):
        if path.is_file():
            relative = str(path.relative_to(REPO_ROOT))
            rulespace[relative] = executed.get(relative, path.read_bytes())
    common_bodies = {**exact_common, **rulespace}
    common_origins = tuple(
        _tree_blob(COMMON_COMMIT, path, common_bodies[path])
        for path in sorted(common_bodies, key=lambda value: value.encode())
    )
    route_origins = tuple(
        _tree_blob(commit, row[3], executed[row[3]])
        for row, commit in zip(ROUTE_ROWS, ROUTE_COMMITS)
    )
    evidence_bodies = {
        **common_bodies,
        **{entry[1]: entry[5] for entry in route_origins},
    }
    evidence_blobs = tuple(
        _tree_blob(EVIDENCE_COMMIT, path, evidence_bodies[path])
        for path in sorted(evidence_bodies, key=lambda value: value.encode())
    )
    return {
        "evidence_commit_sha": EVIDENCE_COMMIT,
        "common_commit_sha": COMMON_COMMIT,
        "route_manifests": static["route_manifests"],
        "evidence_blobs": evidence_blobs,
        "common_origin_blobs": common_origins,
        "route_origin_blobs": route_origins,
        "production_blobs": static["production_blobs"],
        "namespace_observation": {
            "fresh_export_root_count": 1,
            "experiments_init_present": False,
            "experiments_namespace_portion_count": 1,
            "shadowing_paths": [],
        },
    }


def test_source_origin_validator_has_total_pure_observation_signature() -> None:
    assert tuple(
        inspect.signature(
            common.validate_reviewer_executable_source_origin_v1
        ).parameters
    ) == (
        "evidence_commit_sha",
        "common_commit_sha",
        "route_manifests",
        "evidence_blobs",
        "common_origin_blobs",
        "route_origin_blobs",
        "production_blobs",
        "namespace_observation",
    )


def test_source_origin_accepts_identical_e_and_declared_origins() -> None:
    result = common.validate_reviewer_executable_source_origin_v1(**_origin_inputs())

    assert result["executable_source_origin_precheck_passed"] is True
    assert result["observed_executable_source_closure_sha"] == result[
        "reviewed_executable_source_closure_sha"
    ]
    assert len(result["reviewed_executable_source_closure_sha"]) == 64


@pytest.mark.parametrize(
    "attack_id",
    (
        "current-worktree",
        "extra-module",
        "dynamic-import",
        "namespace-shadow",
        "wrong-mode",
        "wrong-oid",
        "wrong-bytes",
    ),
)
def test_source_origin_totalizes_candidate_attacks(attack_id: str) -> None:
    inputs = _origin_inputs()
    evidence = list(inputs["evidence_blobs"])
    compare_index = next(
        index for index, blob in enumerate(evidence) if blob[1].endswith("compare.py")
    )
    common_index = next(
        index for index, blob in enumerate(evidence) if blob[1].endswith("common.py")
    )
    if attack_id == "current-worktree":
        evidence[0] = ("f" * 40, *evidence[0][1:])
    elif attack_id == "extra-module":
        evidence.append(
            _tree_blob(
                EVIDENCE_COMMIT,
                "experiments/v3m0_b7_schema_lab/extra.py",
                b"",
            )
        )
        evidence.sort(key=lambda blob: blob[1].encode())
    elif attack_id == "dynamic-import":
        raw = evidence[compare_index][5].replace(
            b"    _load_all_routes()\n",
            b"    __import__('experiments.v3m0_b7_schema_lab.a_flat')\n",
            1,
        )
        evidence[compare_index] = _tree_blob(
            EVIDENCE_COMMIT, evidence[compare_index][1], raw
        )
    elif attack_id == "namespace-shadow":
        inputs["namespace_observation"]["shadowing_paths"] = [
            "/tmp/hostile/experiments"
        ]
    elif attack_id == "wrong-mode":
        blob = evidence[common_index]
        evidence[common_index] = (blob[0], blob[1], "100755", *blob[3:])
    elif attack_id == "wrong-oid":
        blob = evidence[common_index]
        evidence[common_index] = (*blob[:4], "0" * 40, blob[5])
    else:
        blob = evidence[common_index]
        raw = blob[5] + b"\n# candidate-only-byte-drift\n"
        evidence[common_index] = _tree_blob(EVIDENCE_COMMIT, blob[1], raw)
    inputs["evidence_blobs"] = tuple(evidence)

    result = common.validate_reviewer_executable_source_origin_v1(**inputs)

    assert result["executable_source_origin_precheck_passed"] is False
    if attack_id == "wrong-bytes":
        assert result["observed_executable_source_closure_sha"] is not None
        assert result["observed_executable_source_closure_sha"] != result[
            "reviewed_executable_source_closure_sha"
        ]
    else:
        assert result["observed_executable_source_closure_sha"] is None


@pytest.mark.parametrize("attack_id", ("wrong-origin-commit", "wrong-origin-oid"))
def test_source_origin_rejects_malformed_declared_origins(attack_id: str) -> None:
    inputs = _origin_inputs()
    routes = list(inputs["route_origin_blobs"])
    blob = routes[1]
    if attack_id == "wrong-origin-commit":
        routes[1] = ("f" * 40, *blob[1:])
    else:
        routes[1] = (*blob[:4], "0" * 40, blob[5])
    inputs["route_origin_blobs"] = tuple(routes)

    with pytest.raises((TypeError, ValueError), match="origin"):
        common.validate_reviewer_executable_source_origin_v1(**inputs)
