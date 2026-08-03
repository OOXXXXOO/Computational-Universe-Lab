"""Task-3 skeleton contract for the import-pure B7 replay core."""

from __future__ import annotations

import ast
import base64
from collections import Counter
import hashlib
import importlib
import json
import math
from pathlib import Path

import numpy as np
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPOSITORY_ROOT / "docsv3" / "v3-机器合同-B7-v9.1-registry.json"
CORE_PATH = REPOSITORY_ROOT / "rulespace_v3" / "b7_replay_core_v1.py"
RESPONSE_PATH = REPOSITORY_ROOT / "rulespace_v3" / "response.py"

PROJECTION_SHA256 = "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"

FORBIDDEN_MODULE_ROOTS = {
    "_posixsubprocess",
    "asyncio",
    "concurrent",
    "ctypes",
    "importlib",
    "multiprocessing",
    "os",
    "posix",
    "pty",
    "runpy",
    "socket",
    "subprocess",
    "threading",
    "time",
}

FORBIDDEN_CALL_NAMES = {
    "__import__",
    "breakpoint",
    "callable",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "hasattr",
    "input",
    "locals",
    "open",
    "print",
    "vars",
}

FUTURE_TASK_SYMBOLS = {
    "validate_response_run_spec_fixture_v1",
    "validate_endpoint_reference_outcome_raw_v1",
    "validate_endpoint_shell_outcome_raw_v1",
    "validate_source_readout_response_raw_v1",
    "validate_synthetic_parent_freeze_v3_body_v1",
    "validate_synthetic_component_body_v1",
    "validate_provenance_fixture_v1",
    "validate_branch_attempt_v1",
    "_select_endpoint_reference_from_raw",
    "_track_endpoint_shell_from_raw",
    "_build_fejer_branch_response_values_from_raw",
    "_audit_source_readout_bridge_from_raw",
    "_assemble_atomic_paired_response_attempt_from_raw",
}

TASK3_PUBLIC_SYMBOLS = {
    "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
    "canonical_json_bytes_v1",
    "canonical_sha_v1",
    "strict_json_loads_v1",
}

TASK3_FUNCTION_SIGNATURES = {
    "canonical_json_bytes_v1": "value",
    "canonical_sha_v1": "value",
    "strict_json_loads_v1": "canonical_json_utf8",
}

TASK3_NESTED_FUNCTION_SIGNATURES = {
    ("canonical_json_bytes_v1", "validate_object_keys"): ("candidate", "path"),
    ("strict_json_loads_v1", "reject_duplicate_object_pairs"): ("pairs",),
    ("strict_json_loads_v1", "reject_nonfinite_constant"): ("constant_text",),
}

TASK3_ALL_FUNCTION_SCOPES = {
    *TASK3_FUNCTION_SIGNATURES,
    *(name for _, name in TASK3_NESTED_FUNCTION_SIGNATURES),
}

TASK3_DIRECT_IMPORTS = ["__future__", "hashlib", "json"]

CORE_DIRECT_IMPORT_BINDINGS = [
    ("from", "__future__", "annotations", None),
    ("import", "hashlib", None, None),
    ("import", "json", None, None),
    ("import", "math", None, None),
    ("from", "fractions", "Fraction", None),
    ("import", "numpy", None, "np"),
    ("import", "scipy.linalg", None, None),
]

TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION = {
    "canonical_json_bytes_v1": {
        "ValueError",
        "json.dumps",
        "set",
        "str.encode",
        "validate_object_keys",
    },
    "validate_object_keys": {
        "TypeError",
        "ValueError",
        "dict.items",
        "enumerate",
        "id",
        "set.add",
        "set.remove",
        "type",
        "validate_object_keys",
    },
    "canonical_sha_v1": {
        "canonical_json_bytes_v1",
        "hashlib.sha256",
        "hashlib.sha256().hexdigest",
    },
    "strict_json_loads_v1": {
        "TypeError",
        "ValueError",
        "bytes.decode",
        "bytes.startswith",
        "canonical_json_bytes_v1",
        "json.loads",
        "type",
    },
    "reject_duplicate_object_pairs": {"ValueError"},
    "reject_nonfinite_constant": {"ValueError"},
}

TASK3_CALL_SHAPES = {
    "ValueError": (1, ()),
    "TypeError": (1, ()),
    "bytes.decode": (2, ()),
    "bytes.startswith": (2, ()),
    "canonical_json_bytes_v1": (1, ()),
    "dict.items": (1, ()),
    "enumerate": (1, ()),
    "hashlib.sha256": (1, ()),
    "hashlib.sha256().hexdigest": (0, ()),
    "id": (1, ()),
    "json.dumps": (
        1,
        ("ensure_ascii", "allow_nan", "sort_keys", "separators"),
    ),
    "json.loads": (1, ("object_pairs_hook", "parse_constant")),
    "set": (0, ()),
    "set.add": (2, ()),
    "set.remove": (2, ()),
    "str.encode": (2, ()),
    "type": (1, ()),
    "validate_object_keys": (2, ()),
}

TASK3_CAPABILITY_CALL_TOKENS = {
    "authority",
    "callback",
    "callable",
    "caller",
    "capability",
    "environment",
    "hydrate",
    "issuer",
    "promote",
    "registry",
    "resign",
    "seal",
    "token",
    "wrapper",
    "worktree",
}

TASK3_RESERVED_CALL_ROOTS = {
    "TypeError",
    "ValueError",
    "bytes",
    "canonical_json_bytes_v1",
    "dict",
    "enumerate",
    "hashlib",
    "id",
    "json",
    "reject_duplicate_object_pairs",
    "reject_nonfinite_constant",
    "set",
    "str",
    "type",
    "validate_object_keys",
}

TASK3_EXACT_LOCAL_CALL_BINDINGS = {
    ("canonical_json_bytes_v1", "text"): "json.dumps",
    ("strict_json_loads_v1", "text"): "bytes.decode",
    ("strict_json_loads_v1", "value"): "json.loads",
}

TASK4_FUNCTION_SIGNATURES = {
    "_split_wire_top_level_v1": ("value", "delimiter"),
    "_literal_wire_value_v1": ("value",),
    "_validate_wire_value_v1": (
        "value",
        "wire_type",
        "nested_record",
        "field",
        "schemas",
    ),
    "_validate_record_raw_v1": ("raw_body", "record_name", "field", "schemas"),
    "_record_schemas_v1": (),
    "_canonical_equal_v1": ("left", "right", "field"),
    "_component_by_id_v1": ("graph_raw", "component_id"),
    "validate_endpoint_reference_outcome_raw_v1": ("raw_body",),
    "validate_endpoint_shell_outcome_raw_v1": ("raw_body",),
    "_validate_parent_review_receipt_structure_v1": ("receipt",),
    "validate_synthetic_parent_freeze_v3_body_v1": ("raw_body",),
    "validate_provenance_fixture_v1": ("raw_body",),
    "_resolve_json_pointer_v1": ("raw_body", "pointer", "field"),
    "validate_synthetic_component_body_v1": (
        "raw_body",
        "ordered_components_raw",
        "parent_raw",
    ),
    "_validate_synthetic_graph_raw_v1": ("graph_raw", "parent_raw"),
    "validate_response_run_spec_fixture_v1": (
        "raw_body",
        "provenance_raw",
        "graph_raw",
    ),
    "validate_source_readout_response_raw_v1": (
        "raw_body",
        "run_spec_raw",
        "provenance_raw",
        "graph_raw",
    ),
    "_require_exact_dict_fields_v1": ("raw_body", "fields", "field"),
    "_require_sha256_v1": ("value", "field"),
    "_require_self_hash_v1": ("raw_body", "hash_field", "field"),
    "_validate_frozen_complex_tensor_raw_v1": ("raw_body", "field"),
    "validate_branch_attempt_v1": ("raw_body",),
}

TASK4_FUNCTION_ANNOTATIONS = {
    "_split_wire_top_level_v1": (("str", "str"), "list[str]"),
    "_literal_wire_value_v1": (("str",), "object"),
    "_validate_wire_value_v1": (
        ("object", "str", "str | None", "str", "dict[str, object]"),
        "None",
    ),
    "_validate_record_raw_v1": (
        ("object", "str", "str", "dict[str, object]"),
        "dict[str, object]",
    ),
    "_record_schemas_v1": ((), "dict[str, object]"),
    "_canonical_equal_v1": (("object", "object", "str"), "None"),
    "_component_by_id_v1": (("object", "str"), "dict[str, object]"),
    "validate_endpoint_reference_outcome_raw_v1": (
        ("object",),
        "dict[str, object]",
    ),
    "validate_endpoint_shell_outcome_raw_v1": (
        ("object",),
        "dict[str, object]",
    ),
    "_validate_parent_review_receipt_structure_v1": (
        ("dict[str, object]",),
        "None",
    ),
    "validate_synthetic_parent_freeze_v3_body_v1": (
        ("object",),
        "dict[str, object]",
    ),
    "validate_provenance_fixture_v1": (("object",), "dict[str, object]"),
    "_resolve_json_pointer_v1": (("object", "str", "str"), "object"),
    "validate_synthetic_component_body_v1": (
        ("object", "object", "object"),
        "dict[str, object]",
    ),
    "_validate_synthetic_graph_raw_v1": (
        ("object", "object"),
        "dict[str, object]",
    ),
    "validate_response_run_spec_fixture_v1": (
        ("object", "object", "object"),
        "dict[str, object]",
    ),
    "validate_source_readout_response_raw_v1": (
        ("object", "object", "object", "object"),
        "dict[str, object]",
    ),
    "_require_exact_dict_fields_v1": (
        ("object", "tuple[str, ...]", "str"),
        "dict[str, object]",
    ),
    "_require_sha256_v1": (("object", "str"), "str"),
    "_require_self_hash_v1": (
        ("dict[str, object]", "str", "str"),
        "None",
    ),
    "_validate_frozen_complex_tensor_raw_v1": (
        ("object", "str"),
        "dict[str, object]",
    ),
    "validate_branch_attempt_v1": (("object",), "dict[str, object]"),
}

TASK4_EXPECTED_FUNCTION_BODY_SHA256 = {
    "_split_wire_top_level_v1": (
        "4d4bcc54cc9df01d07639ce22a0f2ea814799d673913d48e1bca34a432e5e299"
    ),
    "_literal_wire_value_v1": (
        "0ecade7d2b67087982d86227df62c7bfe54f4471fd31265effd0b398e8257ef9"
    ),
    "_validate_wire_value_v1": (
        "5c5366062f0d53b66ae674cf2e30c9bfd8b1401e6d33852e5529432c8e817826"
    ),
    "_validate_record_raw_v1": (
        "cf32ecc644c364265dfb7fe55912e06a38691fa98c1c454299bd4748e58970f7"
    ),
    "_record_schemas_v1": (
        "6cb3161440f1bf932029024aa61ad7964fb868652ad547ab26deef2b69e4f1a0"
    ),
    "_canonical_equal_v1": (
        "6b6a0179c5ed9bb3f44e622ea972f7c894b8cac0f8d6f447d362179e08ed25f4"
    ),
    "_component_by_id_v1": (
        "8ae04de17547777e6eedc3051fb959b6ea7f9904544998daa63555f2b83e305b"
    ),
    "validate_endpoint_reference_outcome_raw_v1": (
        "6e8dbca1265337917e2218d1d0835108f251082385a0d4ffe53617d6700a112f"
    ),
    "validate_endpoint_shell_outcome_raw_v1": (
        "841ead5ec4d5703f6cd20399b3b954c3b3093b3a62e79914589bfb733692dd4d"
    ),
    "_validate_parent_review_receipt_structure_v1": (
        "dadfa06a5571e91e07a917020f0b65c2d2fd7568d26e28b13ae174b01e7ae7af"
    ),
    "validate_synthetic_parent_freeze_v3_body_v1": (
        "2dcad45499fb16b50aa01e2c3a3a15f3683eb12d4e275eaf6ed765b861ae7006"
    ),
    "validate_provenance_fixture_v1": (
        "50a91f489ec455282c6d80d7fb15191871bf603bef07acf94a7cc54694f592e6"
    ),
    "_resolve_json_pointer_v1": (
        "96ba0ff5e097448226a14232f45aa612a94b40e42d287bb1f6d17a99264acab8"
    ),
    "validate_synthetic_component_body_v1": (
        "6982828c023e1a8165e82847e56f8debf333edd3a932a2a5bcdbadf8a909521c"
    ),
    "_validate_synthetic_graph_raw_v1": (
        "adeb8f59dd615ce12e05345d3cc104d6f407ecb87a59f255c13768a998a12cb6"
    ),
    "validate_response_run_spec_fixture_v1": (
        "f40eb82d7d3bd0656bfca1026b925912756f6ec3f47168e546d368edc9a9ca3e"
    ),
    "validate_source_readout_response_raw_v1": (
        "80a68cfdfd9a8d4313fdc57edb515d14af60c8248cf64db74098f6acf388bfbc"
    ),
    "_require_exact_dict_fields_v1": (
        "6d46773205767f216f32a318e2d841d9e25c21f12ac8d76ded27e565d8ef35c9"
    ),
    "_require_sha256_v1": (
        "7a09097db28fcfadeb19113c4c1ee90950eb8277a55751edf022783ffe8be043"
    ),
    "_require_self_hash_v1": (
        "1dda605a7cdaa6defe5f39885d05605e2d406b85d0b3797b6ffc2a0ee065a9d2"
    ),
    "_validate_frozen_complex_tensor_raw_v1": (
        "0aa69734427f7427cfa08f23054c74bb6484a45eb68b869193b13386b6441466"
    ),
    "validate_branch_attempt_v1": (
        "8767ac162d6a5eb980baaa6622fac4fffe82442914c012267898dbbc9ed12653"
    ),
}

TASK4_PUBLIC_VALIDATOR_SYMBOLS = {
    "validate_response_run_spec_fixture_v1",
    "validate_endpoint_reference_outcome_raw_v1",
    "validate_endpoint_shell_outcome_raw_v1",
    "validate_source_readout_response_raw_v1",
    "validate_synthetic_parent_freeze_v3_body_v1",
    "validate_synthetic_component_body_v1",
    "validate_provenance_fixture_v1",
    "validate_branch_attempt_v1",
}

TASK5_FUNCTION_SIGNATURES = {
    "_select_endpoint_reference_from_raw": (
        "reference_spec",
        "transition_matrix",
        "metric_matrix",
        "source_injection_matrix",
        "readout_matrix",
    ),
    "_track_endpoint_shell_from_raw": (
        "reference_outcome",
        "shell_spec",
        "ordered_transition_matrices",
        "ordered_metric_matrices",
        "source_injection_matrix",
        "readout_matrix",
        "actual_factory_sha",
        "actual_transition_sha",
        "actual_dynamics_certificate_sha",
        "dt",
    ),
    "_build_fejer_branch_response_values_from_raw": (
        "branch",
        "response_grid",
        "fejer_order",
        "source_basis",
        "readout_basis",
        "shell_phases",
        "ordered_transition_matrices",
        "ordered_metric_matrices",
    ),
    "_audit_source_readout_bridge_from_raw": (
        "branch",
        "factory_sha",
        "transition_sha",
        "dynamics_certificate_sha",
        "run_spec_sha",
        "bridge_grid",
        "bridge_steps",
        "source_trial_vectors",
        "current_readout_calibration_spec",
        "ordered_raw_differences",
    ),
    "_assemble_atomic_paired_response_attempt_from_raw": (
        "actual_response_values",
        "matched_ablated_response_values",
        "actual_bridge_audit",
        "matched_ablated_bridge_audit",
        "first_failure",
    ),
}

TASK5_DEPENDENCY_BINDINGS = (
    "np",
    "scipy",
    "math",
    "Fraction",
    "canonical_json_bytes_v1",
    "canonical_sha_v1",
    "strict_json_loads_v1",
)

TASK5_HELPER_FUNCTION_SIGNATURES = {
    "_make_task5_dependency_guard_v1": (
        "np_binding",
        "scipy_binding",
        "math_binding",
        "fraction_binding",
        "canonical_json_binding",
        "canonical_sha_binding",
        "strict_json_binding",
    ),
    "_finite_float_v1": ("value", "field"),
    "_strict_complex_matrix_v1": ("value", "field", "square"),
    "_freeze_complex_tensor_raw_v1": ("values",),
    "_frozen_tensor_array_raw_v1": ("raw_body", "field"),
    "_basis_matrix_raw_v1": ("raw_body", "field", "role"),
    "_hermitian_sqrt_pair_raw_v1": ("metric",),
    "_fejer_scalar_raw_v1": ("eigenvalue", "center_phase", "order"),
    "_compute_fejer_filtered_response_raw_v1": (
        "transition",
        "metric",
        "shell_phase",
        "order",
        "source_injection",
        "readout",
    ),
    "_exact_frobenius_upper_raw_v1": ("values",),
    "_principal_phase_raw_v1": ("value",),
    "_phase_distance_raw_v1": ("first", "second"),
    "_phase_bands_raw_v1": ("raw_bands", "field"),
    "_in_phase_bands_raw_v1": ("phase", "bands"),
    "_orthogonal_projector_raw_v1": ("matrix",),
    "_extract_projector_candidates_raw_v1": (
        "transition",
        "metric",
        "raw_phase_bands",
        "order",
        "source_injection",
        "readout",
    ),
    "_phase_grid_collision_raw_v1": ("candidates", "order"),
    "_projector_overlap_raw_v1": ("first", "second", "rank"),
    "_build_branch_attempt_raw_v1": (
        "branch",
        "response_values",
        "bridge_audit",
        "failure",
    ),
}

TASK5_NESTED_FUNCTION_SIGNATURES = {
    ("_make_task5_dependency_guard_v1", "require_task5_dependencies"): (
        "np_candidate",
        "scipy_candidate",
        "math_candidate",
        "fraction_candidate",
        "canonical_json_candidate",
        "canonical_sha_candidate",
        "strict_json_candidate",
    ),
}

TASK5_ALL_FUNCTION_SCOPES = {
    *TASK5_FUNCTION_SIGNATURES,
    *TASK5_HELPER_FUNCTION_SIGNATURES,
    *(name for _, name in TASK5_NESTED_FUNCTION_SIGNATURES),
}

TASK5_TOP_LEVEL_FUNCTION_ORDER = (
    "_make_task5_dependency_guard_v1",
    "_finite_float_v1",
    "_strict_complex_matrix_v1",
    "_freeze_complex_tensor_raw_v1",
    "_frozen_tensor_array_raw_v1",
    "_basis_matrix_raw_v1",
    "_hermitian_sqrt_pair_raw_v1",
    "_fejer_scalar_raw_v1",
    "_compute_fejer_filtered_response_raw_v1",
    "_exact_frobenius_upper_raw_v1",
    "_principal_phase_raw_v1",
    "_phase_distance_raw_v1",
    "_phase_bands_raw_v1",
    "_in_phase_bands_raw_v1",
    "_orthogonal_projector_raw_v1",
    "_extract_projector_candidates_raw_v1",
    "_phase_grid_collision_raw_v1",
    "_projector_overlap_raw_v1",
    "_select_endpoint_reference_from_raw",
    "_track_endpoint_shell_from_raw",
    "_build_fejer_branch_response_values_from_raw",
    "_audit_source_readout_bridge_from_raw",
    "_build_branch_attempt_raw_v1",
    "_assemble_atomic_paired_response_attempt_from_raw",
)

TASK4_LITERAL_ASSIGNMENTS = {
    "_B7_RECORD_SCHEMAS_JSON_V1",
    "_B7_COMPONENT_CONTRACTS_JSON_V1",
}

TASK4_CALL_SHAPES = {
    "TypeError": ((1, ()),),
    "ValueError": ((1, ()),),
    "_canonical_equal_v1": ((3, ()),),
    "_component_by_id_v1": ((2, ()),),
    "_literal_wire_value_v1": ((1, ()),),
    "_record_schemas_v1": ((0, ()),),
    "_require_exact_dict_fields_v1": ((3, ()),),
    "_require_self_hash_v1": ((3, ()),),
    "_require_sha256_v1": ((2, ()),),
    "_resolve_json_pointer_v1": ((3, ()),),
    "_split_wire_top_level_v1": ((2, ()),),
    "_validate_frozen_complex_tensor_raw_v1": ((2, ()),),
    "_validate_parent_review_receipt_structure_v1": ((1, ()),),
    "_validate_record_raw_v1": ((4, ()),),
    "_validate_synthetic_graph_raw_v1": ((2, ()),),
    "_validate_wire_value_v1": ((5, ()),),
    "any": ((1, ()),),
    "armor.split": ((1, ()),),
    "canonical_json_bytes_v1": ((1, ()),),
    "canonical_sha_v1": ((1, ()),),
    "dimensions.split": ((1, ()),),
    "enumerate": ((1, ()),),
    "exact_text.isdigit": ((0, ()),),
    "failure.endswith": ((1, ()),),
    "int": ((1, ()),),
    "item.get": ((1, ()),),
    "json.loads": ((1, ()),),
    "len": ((1, ()),),
    "modifier.startswith": ((1, ()),),
    "pointer.removeprefix": ((1, ()),),
    "pointer.removeprefix().split": ((1, ()),),
    "pointer.startswith": ((1, ()),),
    "raw_body.items": ((0, ()),),
    "raw_token.replace": ((2, ()),),
    "raw_token.replace().replace": ((2, ()),),
    "reviewer_id.strip": ((0, ()),),
    "result.append": ((1, ()),),
    "root_entries.append": ((1, ()),),
    "schemas.get": ((1, ()),),
    "set": ((1, ()),),
    "t_derivation.split": ((2, ()),),
    "t_derivation.startswith": ((1, ()),),
    "token.isdigit": ((0, ()),),
    "tuple": ((1, ()),),
    "type": ((1, ()),),
    "validate_endpoint_reference_outcome_raw_v1": ((1, ()),),
    "validate_provenance_fixture_v1": ((1, ()),),
    "validate_response_run_spec_fixture_v1": ((3, ()),),
    "validate_synthetic_component_body_v1": ((3, ()),),
    "validate_synthetic_parent_freeze_v3_body_v1": ((1, ()),),
    "value.lstrip": ((1, ()),),
    "value.lstrip().isdigit": ((0, ()),),
    "wire_type.removeprefix": ((1, ()),),
    "wire_type.startswith": ((1, ()),),
    "zip": ((2, ()),),
}

TASK3_FUNCTION_ANNOTATIONS = {
    "canonical_json_bytes_v1": (("object",), "bytes"),
    "canonical_sha_v1": (("object",), "str"),
    "strict_json_loads_v1": (("bytes",), "object"),
}

TASK3_NESTED_FUNCTION_ANNOTATIONS = {
    ("canonical_json_bytes_v1", "validate_object_keys"): (
        ("object", "str"),
        "None",
    ),
    ("strict_json_loads_v1", "reject_duplicate_object_pairs"): (
        ("list[tuple[str, object]]",),
        "dict[str, object]",
    ),
    ("strict_json_loads_v1", "reject_nonfinite_constant"): (
        ("str",),
        "object",
    ),
}

TASK3_EXPECTED_SCOPE_BINDINGS = Counter(
    {
        ((), "annotations", "import-alias"): 1,
        ((), "hashlib", "import-alias"): 1,
        ((), "json", "import-alias"): 1,
        ((), "B7_V91_PURE_REPLAY_PROJECTION_SHA256", "assign-target"): 1,
        ((), "canonical_json_bytes_v1", "function-def"): 1,
        ((), "canonical_sha_v1", "function-def"): 1,
        ((), "strict_json_loads_v1", "function-def"): 1,
        (("canonical_json_bytes_v1",), "value", "parameter"): 1,
        (("canonical_json_bytes_v1",), "active_containers", "assign-target"): 1,
        (("canonical_json_bytes_v1",), "validate_object_keys", "function-def"): 1,
        (("canonical_json_bytes_v1",), "text", "assign-target"): 1,
        (("canonical_json_bytes_v1",), "exc", "except-handler"): 1,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "candidate",
            "parameter",
        ): 1,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "path",
            "parameter",
        ): 1,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "candidate_type",
            "assign-target",
        ): 1,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "container_id",
            "assign-target",
        ): 2,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "key",
            "for-target",
        ): 1,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "item",
            "for-target",
        ): 2,
        (
            ("canonical_json_bytes_v1", "validate_object_keys"),
            "index",
            "for-target",
        ): 1,
        (("canonical_sha_v1",), "value", "parameter"): 1,
        (("strict_json_loads_v1",), "canonical_json_utf8", "parameter"): 1,
        (
            ("strict_json_loads_v1",),
            "reject_duplicate_object_pairs",
            "function-def",
        ): 1,
        (
            ("strict_json_loads_v1",),
            "reject_nonfinite_constant",
            "function-def",
        ): 1,
        (("strict_json_loads_v1",), "text", "assign-target"): 1,
        (("strict_json_loads_v1",), "exc", "except-handler"): 1,
        (("strict_json_loads_v1",), "value", "assign-target"): 1,
        (
            ("strict_json_loads_v1", "reject_duplicate_object_pairs"),
            "pairs",
            "parameter",
        ): 1,
        (
            ("strict_json_loads_v1", "reject_duplicate_object_pairs"),
            "result",
            "assign-target",
        ): 1,
        (
            ("strict_json_loads_v1", "reject_duplicate_object_pairs"),
            "key",
            "for-target",
        ): 1,
        (
            ("strict_json_loads_v1", "reject_duplicate_object_pairs"),
            "value",
            "for-target",
        ): 1,
        (
            ("strict_json_loads_v1", "reject_nonfinite_constant"),
            "constant_text",
            "parameter",
        ): 1,
    }
)

TASK3_EXPECTED_CALL_TARGETS = Counter(
    {
        ("canonical_json_bytes_v1", "set"): 1,
        ("canonical_json_bytes_v1", "validate_object_keys"): 1,
        ("canonical_json_bytes_v1", "json.dumps"): 1,
        ("canonical_json_bytes_v1", "str.encode"): 1,
        ("canonical_json_bytes_v1", "ValueError"): 1,
        ("validate_object_keys", "type"): 2,
        ("validate_object_keys", "id"): 2,
        ("validate_object_keys", "ValueError"): 2,
        ("validate_object_keys", "set.add"): 2,
        ("validate_object_keys", "dict.items"): 1,
        ("validate_object_keys", "TypeError"): 2,
        ("validate_object_keys", "validate_object_keys"): 2,
        ("validate_object_keys", "set.remove"): 2,
        ("validate_object_keys", "enumerate"): 1,
        ("canonical_sha_v1", "hashlib.sha256().hexdigest"): 1,
        ("canonical_sha_v1", "hashlib.sha256"): 1,
        ("canonical_sha_v1", "canonical_json_bytes_v1"): 1,
        ("strict_json_loads_v1", "type"): 1,
        ("strict_json_loads_v1", "TypeError"): 1,
        ("strict_json_loads_v1", "bytes.startswith"): 1,
        ("strict_json_loads_v1", "ValueError"): 2,
        ("strict_json_loads_v1", "bytes.decode"): 1,
        ("strict_json_loads_v1", "json.loads"): 1,
        ("strict_json_loads_v1", "canonical_json_bytes_v1"): 1,
        ("reject_duplicate_object_pairs", "ValueError"): 1,
        ("reject_nonfinite_constant", "ValueError"): 1,
    }
)

TASK3_EXPECTED_CALL_EXPRESSIONS = {
    "canonical_json_bytes_v1": (
        "set()",
        'validate_object_keys(value, "$")',
        "json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, "
        'separators=(",", ":"))',
        'str.encode(text, "utf-8")',
        'ValueError("canonical JSON text must be valid UTF-8")',
    ),
    "validate_object_keys": (
        "type(candidate)",
        "id(candidate)",
        'ValueError("JSON value contains a cyclic container")',
        "set.add(active_containers, container_id)",
        "dict.items(candidate)",
        "type(key)",
        'TypeError("JSON object key must be a str")',
        "validate_object_keys(item, path)",
        "set.remove(active_containers, container_id)",
        "id(candidate)",
        'ValueError("JSON value contains a cyclic container")',
        "set.add(active_containers, container_id)",
        "enumerate(candidate)",
        "validate_object_keys(item, path)",
        "set.remove(active_containers, container_id)",
        'TypeError("JSON value must contain only exact built-in JSON values")',
    ),
    "canonical_sha_v1": (
        "hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()",
        "hashlib.sha256(canonical_json_bytes_v1(value))",
        "canonical_json_bytes_v1(value)",
    ),
    "strict_json_loads_v1": (
        "type(canonical_json_utf8)",
        'TypeError("canonical_json_utf8 must be exact bytes")',
        'bytes.startswith(canonical_json_utf8, b"\\xef\\xbb\\xbf")',
        'ValueError("JSON UTF-8 BOM is forbidden")',
        'bytes.decode(canonical_json_utf8, "utf-8")',
        'ValueError("JSON input must be strict UTF-8")',
        "json.loads(text, object_pairs_hook=reject_duplicate_object_pairs, "
        "parse_constant=reject_nonfinite_constant)",
        "canonical_json_bytes_v1(value)",
    ),
    "reject_duplicate_object_pairs": ('ValueError("duplicate JSON object key")',),
    "reject_nonfinite_constant": ('ValueError("JSON number must be finite")',),
}

TASK3_EXPECTED_IF_TESTS = {
    "validate_object_keys": (
        "candidate is None or candidate_type is str or candidate_type is bool "
        "or candidate_type is int or candidate_type is float",
        "candidate_type is dict",
        "container_id in active_containers",
        "type(key) is not str",
        "candidate_type is list or candidate_type is tuple",
        "container_id in active_containers",
    ),
    "reject_duplicate_object_pairs": ("key in result",),
    "strict_json_loads_v1": (
        "type(canonical_json_utf8) is not bytes",
        'bytes.startswith(canonical_json_utf8, b"\\xef\\xbb\\xbf")',
    ),
}

TASK3_EXPECTED_FOR_SHAPES = Counter(
    {
        (
            "validate_object_keys",
            ("key", "item"),
            "dict.items",
            ("candidate",),
        ): 1,
        (
            "validate_object_keys",
            ("index", "item"),
            "enumerate",
            ("candidate",),
        ): 1,
        (
            "reject_duplicate_object_pairs",
            ("key", "value"),
            None,
            ("pairs",),
        ): 1,
    }
)

TASK3_EXPECTED_EXCEPTION_HANDLERS = Counter(
    {
        (
            "canonical_json_bytes_v1",
            "UnicodeEncodeError",
            "exc",
            "canonical JSON text must be valid UTF-8",
        ): 1,
        (
            "strict_json_loads_v1",
            "UnicodeDecodeError",
            "exc",
            "JSON input must be strict UTF-8",
        ): 1,
    }
)

TASK3_EXPECTED_RETURN_SPECS = (
    (
        ("canonical_json_bytes_v1",),
        "Try.body",
        0,
        'str.encode(text, "utf-8")',
    ),
    (
        ("canonical_json_bytes_v1", "validate_object_keys"),
        "If.body",
        0,
        None,
    ),
    (
        ("canonical_json_bytes_v1", "validate_object_keys"),
        "If.body",
        4,
        None,
    ),
    (
        ("canonical_json_bytes_v1", "validate_object_keys"),
        "If.body",
        4,
        None,
    ),
    (
        ("canonical_sha_v1",),
        "FunctionDef.body",
        1,
        "hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()",
    ),
    (
        ("strict_json_loads_v1", "reject_duplicate_object_pairs"),
        "FunctionDef.body",
        2,
        "result",
    ),
    (
        ("strict_json_loads_v1",),
        "FunctionDef.body",
        8,
        "value",
    ),
)

TASK3_EXPECTED_FUNCTION_BODY_SHA256 = {
    (
        "canonical_json_bytes_v1",
    ): "cdb10942de36a1b5becf7b802b18f4949796cee984316296882812e3e1d501df",
    (
        "canonical_json_bytes_v1",
        "validate_object_keys",
    ): "3be9204927ccc1eb5ee4c054a0ba0e06a6a2b95f15bcef79620047e37d4c9d81",
    (
        "canonical_sha_v1",
    ): "df9ce1ca2fad7ff08f79dd33288e19b2189faabf73ae990a1f4d6bc9f1e82b1b",
    (
        "strict_json_loads_v1",
    ): "fd46d22d7a799ef4a5f467b6e62e0146a057737414491b67930039c7f22431f0",
    (
        "strict_json_loads_v1",
        "reject_duplicate_object_pairs",
    ): "e6684affcbbf87132c616d78742db7709c85e9c1848b190d043bbf62c6ced7d7",
    (
        "strict_json_loads_v1",
        "reject_nonfinite_constant",
    ): "d2fc09e7a475ed42ac9fa527cc761c29a7e7db2f5cf1aba69372499ac663c964",
}


def _registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _core_module():
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    return importlib.import_module("rulespace_v3.b7_replay_core_v1")


def _resolved_attribute_root(node: ast.Attribute) -> str | None:
    value: ast.AST = node
    while isinstance(value, ast.Attribute):
        value = value.value
    return value.id if isinstance(value, ast.Name) else None


def _task3_call_target(node: ast.Call) -> str | None:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if not isinstance(function, ast.Attribute):
        return None
    if isinstance(function.value, ast.Name):
        return f"{function.value.id}.{function.attr}"
    if isinstance(function.value, ast.Call):
        receiver = _task3_call_target(function.value)
        if receiver is not None:
            return f"{receiver}().{function.attr}"
    return None


def _enclosing_function_name(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> str | None:
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.FunctionDef):
            return parent.name
        parent = parents.get(parent)
    return None


def _nearest_binding_scope(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    *,
    skip_comprehensions: bool = False,
) -> ast.AST:
    scope_types = (
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.Lambda,
        ast.ClassDef,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    comprehension_types = (
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, scope_types) and not (
            skip_comprehensions and isinstance(parent, comprehension_types)
        ):
            return parent
        parent = parents.get(parent)
    raise AssertionError("binding has no lexical scope")


def _binding_target_kind(
    node: ast.Name,
    parents: dict[ast.AST, ast.AST],
) -> str:
    target: ast.AST = node
    parent = parents.get(target)
    while isinstance(parent, (ast.List, ast.Tuple, ast.Starred)):
        target = parent
        parent = parents.get(target)
    if isinstance(parent, (ast.For, ast.AsyncFor)) and parent.target is target:
        return "for-target"
    if isinstance(parent, ast.comprehension) and parent.target is target:
        return "comprehension-target"
    if isinstance(parent, ast.withitem) and parent.optional_vars is target:
        return "with-target"
    if isinstance(parent, ast.NamedExpr) and parent.target is target:
        return "named-expression"
    if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return "assign-target"
    return "name-store"


def _scope_binding_events(
    tree: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> list[tuple[ast.AST, str, str, ast.AST]]:
    events: list[tuple[ast.AST, str, str, ast.AST]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            kind = _binding_target_kind(node, parents)
            events.append(
                (
                    _nearest_binding_scope(
                        node,
                        parents,
                        skip_comprehensions=kind == "named-expression",
                    ),
                    node.id,
                    kind,
                    node,
                )
            )
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            events.append(
                (
                    _nearest_binding_scope(node, parents),
                    node.name,
                    "except-handler",
                    node,
                )
            )
        elif isinstance(node, ast.alias):
            parent = parents[node]
            if isinstance(parent, ast.Import):
                bound_name = node.asname or node.name.split(".", 1)[0]
            else:
                assert isinstance(parent, ast.ImportFrom)
                bound_name = node.asname or node.name
            events.append(
                (
                    _nearest_binding_scope(node, parents),
                    bound_name,
                    "import-alias",
                    node,
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            events.append(
                (
                    _nearest_binding_scope(node, parents),
                    node.name,
                    "function-def",
                    node,
                )
            )
        elif isinstance(node, ast.ClassDef):
            events.append(
                (
                    _nearest_binding_scope(node, parents),
                    node.name,
                    "class-def",
                    node,
                )
            )
        elif isinstance(node, ast.arg):
            events.append(
                (
                    _nearest_binding_scope(node, parents),
                    node.arg,
                    "parameter",
                    node,
                )
            )

        node_type = type(node).__name__
        if node_type in {"MatchAs", "MatchStar"}:
            bound_name = getattr(node, "name", None)
            if bound_name is not None:
                events.append(
                    (
                        _nearest_binding_scope(node, parents),
                        bound_name,
                        "match-capture",
                        node,
                    )
                )
        elif node_type == "MatchMapping":
            bound_name = getattr(node, "rest", None)
            if bound_name is not None:
                events.append(
                    (
                        _nearest_binding_scope(node, parents),
                        bound_name,
                        "match-capture",
                        node,
                    )
                )
    return events


def _scope_path(
    scope: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> tuple[str, ...]:
    names: list[str] = []
    current: ast.AST | None = scope
    while current is not None and not isinstance(current, ast.Module):
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(current.name)
        elif isinstance(current, ast.Lambda):
            names.append("<lambda>")
        else:
            names.append(f"<{type(current).__name__}>")
        current = parents.get(current)
        while current is not None and not isinstance(
            current,
            (
                ast.Module,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Lambda,
                ast.ClassDef,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
            ),
        ):
            current = parents.get(current)
    return tuple(reversed(names))


def _expression_shape(source: str) -> str:
    return ast.dump(ast.parse(source, mode="eval").body, include_attributes=False)


def _normalized_function_body_sha256(node: ast.FunctionDef) -> str:
    normalized_body = ast.dump(
        ast.Module(body=node.body, type_ignores=[]),
        annotate_fields=True,
        include_attributes=False,
    )
    return hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()


def _statement_parent_position(
    node: ast.stmt,
    parents: dict[ast.AST, ast.AST],
) -> tuple[str, int]:
    parent = parents[node]
    for field in ("body", "orelse", "finalbody"):
        statements = getattr(parent, field, None)
        if isinstance(statements, list) and node in statements:
            return f"{type(parent).__name__}.{field}", statements.index(node)
    raise AssertionError("statement is outside a frozen statement list")


def _target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    assert isinstance(node, (ast.Tuple, ast.List))
    names: list[str] = []
    for element in node.elts:
        names.extend(_target_names(element))
    return tuple(names)


def _is_annotation_node(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    child = node
    parent = parents.get(child)
    while parent is not None:
        if isinstance(parent, ast.arg) and parent.annotation is child:
            return True
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return parent.returns is child
        if isinstance(parent, ast.AnnAssign):
            return parent.annotation is child
        if isinstance(parent, ast.stmt):
            return False
        child = parent
        parent = parents.get(child)
    return False


def _assert_exact_function_shape(
    node: ast.FunctionDef,
    expected_arguments: tuple[str, ...],
    expected_annotations: tuple[str, ...],
    expected_return: str,
) -> None:
    assert node.decorator_list == []
    assert node.type_comment is None
    assert node.args.defaults == []
    assert all(default is None for default in node.args.kw_defaults)
    assert node.args.posonlyargs == []
    assert node.args.vararg is None
    assert node.args.kwonlyargs == []
    assert node.args.kwarg is None
    assert tuple(argument.arg for argument in node.args.args) == expected_arguments
    assert (
        tuple(ast.unparse(argument.annotation) for argument in node.args.args)
        == expected_annotations
    )
    assert node.returns is not None
    assert ast.unparse(node.returns) == expected_return


def _assert_exact_unannotated_function_shape(
    node: ast.FunctionDef,
    expected_arguments: tuple[str, ...],
) -> None:
    assert node.decorator_list == []
    assert node.type_comment is None
    assert node.args.defaults == []
    assert all(default is None for default in node.args.kw_defaults)
    assert node.args.posonlyargs == []
    assert node.args.vararg is None
    assert node.args.kwonlyargs == []
    assert node.args.kwarg is None
    assert tuple(argument.arg for argument in node.args.args) == expected_arguments
    assert all(argument.annotation is None for argument in node.args.args)
    assert node.returns is None


def test_scope_binding_extractor_covers_every_python_binding_site() -> None:
    tree = ast.parse(
        """
import hashlib as imported_name
from json import dumps as imported_from_name

assigned_name = 1

def function_name(parameter_name):
    try:
        pass
    except Exception as exception_name:
        pass
    with context as with_name:
        pass
    for for_name in sequence:
        pass
    comprehended = [item for comprehension_name in sequence]
    (walrus_name := source)

    class class_name:
        pass

async def asynchronous(async_parameter_name):
    async with context as async_with_name:
        pass
    async for async_for_name in sequence:
        pass
"""
    )
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    observed = {
        (name, kind) for _, name, kind, _ in _scope_binding_events(tree, parents)
    }

    assert {
        ("imported_name", "import-alias"),
        ("imported_from_name", "import-alias"),
        ("assigned_name", "assign-target"),
        ("function_name", "function-def"),
        ("parameter_name", "parameter"),
        ("exception_name", "except-handler"),
        ("with_name", "with-target"),
        ("for_name", "for-target"),
        ("comprehension_name", "comprehension-target"),
        ("walrus_name", "named-expression"),
        ("class_name", "class-def"),
        ("asynchronous", "function-def"),
        ("async_parameter_name", "parameter"),
        ("async_with_name", "with-target"),
        ("async_for_name", "for-target"),
    }.issubset(observed)


def test_scope_binding_extractor_covers_match_capture_forms() -> None:
    match_as_type = type("MatchAs", (ast.AST,), {"_fields": ("pattern", "name")})
    match_star_type = type("MatchStar", (ast.AST,), {"_fields": ("name",)})
    match_mapping_type = type(
        "MatchMapping",
        (ast.AST,),
        {"_fields": ("keys", "patterns", "rest")},
    )
    match_as = match_as_type()
    match_as.pattern = None
    match_as.name = "match_as_name"
    match_star = match_star_type()
    match_star.name = "match_star_name"
    match_mapping = match_mapping_type()
    match_mapping.keys = []
    match_mapping.patterns = []
    match_mapping.rest = "match_mapping_rest"
    tree = ast.Module(body=[match_as, match_star, match_mapping], type_ignores=[])
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    observed = {
        (name, kind) for _, name, kind, _ in _scope_binding_events(tree, parents)
    }

    assert {
        ("match_as_name", "match-capture"),
        ("match_star_name", "match-capture"),
        ("match_mapping_rest", "match-capture"),
    }.issubset(observed)


def _assert_core_source_contract(source: str) -> None:
    tree = ast.parse(source)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    contract = _registry()["lab_contract"]["pure_replay_core_contract"]
    allowed_imports = set(contract["allowed_external_import_modules_exact"])

    imported_modules: list[str] = []
    imported_bindings: list[tuple[str, str, str | None, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
                imported_bindings.append(("import", alias.name, None, alias.asname))
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "repository-local imports are forbidden"
            assert node.module is not None
            assert all(alias.name != "*" for alias in node.names)
            assert all(alias.asname is None for alias in node.names)
            if node.module == "__future__":
                assert [(alias.name, alias.asname) for alias in node.names] == [
                    ("annotations", None)
                ]
            imported_modules.append(node.module)
            imported_bindings.extend(
                ("from", node.module, alias.name, alias.asname) for alias in node.names
            )
    assert imported_bindings == CORE_DIRECT_IMPORT_BINDINGS
    assert set(imported_modules).issubset(allowed_imports)
    assert not (
        {name.split(".", 1)[0] for name in imported_modules} & FORBIDDEN_MODULE_ROOTS
    )

    top_level_assignments: set[str] = set()
    top_level_functions: list[str] = []
    for node in tree.body:
        assert isinstance(
            node,
            (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef),
        )
        if isinstance(node, ast.Expr):
            assert isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            )
        elif isinstance(node, ast.Assign):
            assert all(isinstance(target, ast.Name) for target in node.targets)
            top_level_assignments.update(target.id for target in node.targets)
            target_names = tuple(target.id for target in node.targets)
            if target_names == ("_require_task5_dependencies_v1",):
                assert isinstance(node.value, ast.Call)
                assert _task3_call_target(node.value) == (
                    "_make_task5_dependency_guard_v1"
                )
                assert node.value.keywords == []
                assert (
                    tuple(
                        argument.id
                        for argument in node.value.args
                        if isinstance(argument, ast.Name)
                    )
                    == TASK5_DEPENDENCY_BINDINGS
                )
            else:
                ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef):
            top_level_functions.append(node.name)
            if node.name in TASK3_FUNCTION_SIGNATURES:
                expected_arguments = (TASK3_FUNCTION_SIGNATURES[node.name],)
                expected_annotations, expected_return = TASK3_FUNCTION_ANNOTATIONS[
                    node.name
                ]
                _assert_exact_function_shape(
                    node,
                    expected_arguments,
                    expected_annotations,
                    expected_return,
                )
            elif node.name in TASK4_FUNCTION_SIGNATURES:
                expected_arguments = TASK4_FUNCTION_SIGNATURES[node.name]
                expected_annotations, expected_return = TASK4_FUNCTION_ANNOTATIONS[
                    node.name
                ]
                observed_body_sha256 = _normalized_function_body_sha256(node)
                assert (
                    observed_body_sha256
                    == TASK4_EXPECTED_FUNCTION_BODY_SHA256[node.name]
                )
                _assert_exact_function_shape(
                    node,
                    expected_arguments,
                    expected_annotations,
                    expected_return,
                )
            else:
                expected_arguments = {
                    **TASK5_HELPER_FUNCTION_SIGNATURES,
                    **TASK5_FUNCTION_SIGNATURES,
                }[node.name]
                _assert_exact_unannotated_function_shape(
                    node,
                    expected_arguments,
                )

    assert top_level_assignments == {
        "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
        *TASK4_LITERAL_ASSIGNMENTS,
        "_require_task5_dependencies_v1",
    }
    assert top_level_functions == [
        *TASK3_FUNCTION_SIGNATURES,
        *TASK4_FUNCTION_SIGNATURES,
        *TASK5_TOP_LEVEL_FUNCTION_ORDER,
    ]
    assert TASK4_PUBLIC_VALIDATOR_SYMBOLS <= set(top_level_functions)
    assert set(TASK4_EXPECTED_FUNCTION_BODY_SHA256) == set(TASK4_FUNCTION_SIGNATURES)

    expected_return_shapes = Counter(
        (
            scope_path,
            parent_field,
            position,
            None if expression is None else _expression_shape(expression),
        )
        for scope_path, parent_field, position, expression in (
            TASK3_EXPECTED_RETURN_SPECS
        )
    )
    observed_return_shapes: Counter[tuple[tuple[str, ...], str, int, str | None]] = (
        Counter()
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        return_scope = _nearest_binding_scope(node, parents)
        assert isinstance(return_scope, ast.FunctionDef)
        scope_path = _scope_path(return_scope, parents)
        if not scope_path or scope_path[0] not in TASK3_FUNCTION_SIGNATURES:
            continue
        parent_field, position = _statement_parent_position(node, parents)
        observed_return_shapes[
            (
                scope_path,
                parent_field,
                position,
                (
                    None
                    if node.value is None
                    else ast.dump(node.value, include_attributes=False)
                ),
            )
        ] += 1
    assert observed_return_shapes == expected_return_shapes

    observed_function_body_sha256: dict[tuple[str, ...], str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        function_path = _scope_path(node, parents)
        if not function_path or function_path[0] not in TASK3_FUNCTION_SIGNATURES:
            continue
        assert function_path not in observed_function_body_sha256
        observed_function_body_sha256[function_path] = _normalized_function_body_sha256(
            node
        )
    assert observed_function_body_sha256 == TASK3_EXPECTED_FUNCTION_BODY_SHA256

    binding_events = _scope_binding_events(tree, parents)
    task3_module_bindings = {
        "annotations",
        "hashlib",
        "json",
        "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
        *TASK3_FUNCTION_SIGNATURES,
    }
    observed_scope_bindings = Counter(
        (scope_path, name, kind)
        for scope, name, kind, _ in binding_events
        if (
            (scope_path := _scope_path(scope, parents))
            and scope_path[0] in TASK3_FUNCTION_SIGNATURES
        )
        or (not scope_path and name in task3_module_bindings)
    )
    assert observed_scope_bindings == TASK3_EXPECTED_SCOPE_BINDINGS

    expected_if_tests = Counter(
        (scope, _expression_shape(expression))
        for scope, expressions in TASK3_EXPECTED_IF_TESTS.items()
        for expression in expressions
    )
    observed_if_tests: Counter[tuple[str, str]] = Counter()
    approved_condition_nodes: set[ast.AST] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        scope = _enclosing_function_name(node, parents)
        assert scope is not None
        if scope not in TASK3_ALL_FUNCTION_SCOPES:
            continue
        observed_if_tests[(scope, ast.dump(node.test, include_attributes=False))] += 1
        approved_condition_nodes.update(ast.walk(node.test))
    assert observed_if_tests == expected_if_tests

    observed_for_shapes: Counter[
        tuple[str, tuple[str, ...], str | None, tuple[str, ...]]
    ] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        scope = _enclosing_function_name(node, parents)
        assert scope is not None
        if scope not in TASK3_ALL_FUNCTION_SCOPES:
            continue
        assert node.orelse == []
        assert node.type_comment is None
        target_names = _target_names(node.target)
        if isinstance(node.iter, ast.Call):
            iterator_target = _task3_call_target(node.iter)
            assert iterator_target is not None
            assert node.iter.keywords == []
            assert all(isinstance(argument, ast.Name) for argument in node.iter.args)
            iterator_arguments = tuple(argument.id for argument in node.iter.args)
        else:
            assert isinstance(node.iter, ast.Name)
            iterator_target = None
            iterator_arguments = (node.iter.id,)
        observed_for_shapes[
            (scope, target_names, iterator_target, iterator_arguments)
        ] += 1
        if iterator_target in {"dict.items", "enumerate"}:
            expected_guard = _expression_shape(
                "candidate_type is dict"
                if iterator_target == "dict.items"
                else "candidate_type is list or candidate_type is tuple"
            )
            guarded_child: ast.AST = node
            guard_ancestor = parents.get(guarded_child)
            while guard_ancestor is not None:
                if (
                    isinstance(guard_ancestor, ast.If)
                    and ast.dump(
                        guard_ancestor.test,
                        include_attributes=False,
                    )
                    == expected_guard
                ):
                    assert guarded_child in guard_ancestor.body
                    break
                guarded_child = guard_ancestor
                guard_ancestor = parents.get(guarded_child)
            else:
                raise AssertionError("for-loop exact-type guard is not dominant")
    assert observed_for_shapes == TASK3_EXPECTED_FOR_SHAPES

    observed_handlers: Counter[tuple[str, str, str, str]] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        scope = _enclosing_function_name(node, parents)
        assert scope is not None
        if scope not in TASK3_ALL_FUNCTION_SCOPES:
            continue
        assert isinstance(node.type, ast.Name)
        assert node.name is not None
        assert len(node.body) == 1 and isinstance(node.body[0], ast.Raise)
        raise_node = node.body[0]
        assert isinstance(raise_node.exc, ast.Call)
        assert _task3_call_target(raise_node.exc) == "ValueError"
        assert len(raise_node.exc.args) == 1
        assert isinstance(raise_node.exc.args[0], ast.Constant)
        assert isinstance(raise_node.exc.args[0].value, str)
        assert isinstance(raise_node.cause, ast.Name)
        assert raise_node.cause.id == node.name
        observed_handlers[
            (
                scope,
                node.type.id,
                node.name,
                raise_node.exc.args[0].value,
            )
        ] += 1
    assert observed_handlers == TASK3_EXPECTED_EXCEPTION_HANDLERS

    observed_try_shapes: Counter[tuple[str, str]] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        scope = _enclosing_function_name(node, parents)
        assert scope is not None
        if scope not in TASK3_ALL_FUNCTION_SCOPES:
            continue
        assert node.orelse == []
        if scope == "validate_object_keys":
            assert node.handlers == []
            assert len(node.body) == 1 and isinstance(node.body[0], ast.For)
            assert len(node.finalbody) == 1
            final_statement = node.finalbody[0]
            assert isinstance(final_statement, ast.Expr)
            assert isinstance(final_statement.value, ast.Call)
            assert _task3_call_target(final_statement.value) == "set.remove"
            assert len(final_statement.value.args) == 2
            assert all(
                isinstance(argument, ast.Name)
                for argument in final_statement.value.args
            )
            assert tuple(argument.id for argument in final_statement.value.args) == (
                "active_containers",
                "container_id",
            )
            observed_try_shapes[(scope, "finally")] += 1
        elif scope == "canonical_json_bytes_v1":
            assert node.finalbody == []
            assert len(node.handlers) == 1
            assert len(node.body) == 1 and isinstance(node.body[0], ast.Return)
            return_value = node.body[0].value
            assert isinstance(return_value, ast.Call)
            assert _task3_call_target(return_value) == "str.encode"
            observed_try_shapes[(scope, "except")] += 1
        elif scope == "strict_json_loads_v1":
            assert node.finalbody == []
            assert len(node.handlers) == 1
            assert len(node.body) == 1 and isinstance(node.body[0], ast.Assign)
            assert isinstance(node.body[0].value, ast.Call)
            assert _task3_call_target(node.body[0].value) == "bytes.decode"
            observed_try_shapes[(scope, "except")] += 1
        else:
            raise AssertionError("unexpected try statement")
    assert observed_try_shapes == Counter(
        {
            ("validate_object_keys", "finally"): 2,
            ("canonical_json_bytes_v1", "except"): 1,
            ("strict_json_loads_v1", "except"): 1,
        }
    )

    observed_nested_functions: set[tuple[str, str]] = set()
    observed_task5_nested_functions: set[tuple[str, str]] = set()
    observed_exact_local_bindings: set[tuple[str, str]] = set()
    observed_call_targets: Counter[tuple[str, str]] = Counter()
    expected_call_expressions = Counter(
        (scope, _expression_shape(expression))
        for scope, expressions in TASK3_EXPECTED_CALL_EXPRESSIONS.items()
        for expression in expressions
    )
    observed_call_expressions: Counter[tuple[str, str]] = Counter()
    forbidden_implicit_nodes = (
        ast.AsyncFunctionDef,
        ast.AsyncFor,
        ast.AsyncWith,
        ast.Assert,
        ast.AugAssign,
        ast.Await,
        ast.BinOp,
        ast.Break,
        ast.ClassDef,
        ast.Continue,
        ast.Delete,
        ast.DictComp,
        ast.FormattedValue,
        ast.GeneratorExp,
        ast.Global,
        ast.IfExp,
        ast.JoinedStr,
        ast.Lambda,
        ast.ListComp,
        ast.NamedExpr,
        ast.Nonlocal,
        ast.Pass,
        ast.Set,
        ast.SetComp,
        ast.Starred,
        ast.UnaryOp,
        ast.While,
        ast.With,
        ast.Yield,
        ast.YieldFrom,
    )
    for node in ast.walk(tree):
        node_scope = _enclosing_function_name(node, parents)
        if node_scope is None or node_scope in TASK3_ALL_FUNCTION_SCOPES:
            assert not isinstance(node, forbidden_implicit_nodes)
            assert not type(node).__name__.startswith("Match")
            assert type(node).__name__ != "TryStar"
        if isinstance(node, ast.FunctionDef) and node not in tree.body:
            parent_name = _enclosing_function_name(node, parents)
            assert parent_name is not None
            key = (parent_name, node.name)
            if key in TASK3_NESTED_FUNCTION_SIGNATURES:
                assert key not in observed_nested_functions
                observed_nested_functions.add(key)
                expected_annotations, expected_return = (
                    TASK3_NESTED_FUNCTION_ANNOTATIONS[key]
                )
                _assert_exact_function_shape(
                    node,
                    TASK3_NESTED_FUNCTION_SIGNATURES[key],
                    expected_annotations,
                    expected_return,
                )
            else:
                assert key in TASK5_NESTED_FUNCTION_SIGNATURES
                assert key not in observed_task5_nested_functions
                observed_task5_nested_functions.add(key)
                _assert_exact_unannotated_function_shape(
                    node,
                    TASK5_NESTED_FUNCTION_SIGNATURES[key],
                )
        if isinstance(node, ast.Assign):
            assert node.type_comment is None
            assert len(node.targets) == 1
            target_node = node.targets[0]
            scope = _enclosing_function_name(node, parents)
            if scope not in TASK3_ALL_FUNCTION_SCOPES and scope is not None:
                continue
            if isinstance(target_node, ast.Subscript):
                assert _enclosing_function_name(node, parents) == (
                    "reject_duplicate_object_pairs"
                )
                assert isinstance(target_node.value, ast.Name)
                assert target_node.value.id == "result"
                assert isinstance(target_node.slice, ast.Name)
                assert target_node.slice.id == "key"
                assert isinstance(node.value, ast.Name)
                assert node.value.id == "value"
            else:
                assert isinstance(target_node, ast.Name)
                binding_key = (scope, target_node.id)
                if binding_key == (None, "B7_V91_PURE_REPLAY_PROJECTION_SHA256"):
                    assert ast.literal_eval(node.value) == PROJECTION_SHA256
                elif scope is None and target_node.id in TASK4_LITERAL_ASSIGNMENTS:
                    ast.literal_eval(node.value)
                elif binding_key == (None, "_require_task5_dependencies_v1"):
                    assert isinstance(node.value, ast.Call)
                    assert _task3_call_target(node.value) == (
                        "_make_task5_dependency_guard_v1"
                    )
                else:
                    expected_assignment_calls = {
                        ("validate_object_keys", "candidate_type"): "type",
                        ("validate_object_keys", "container_id"): "id",
                        ("canonical_json_bytes_v1", "text"): "json.dumps",
                        ("strict_json_loads_v1", "text"): "bytes.decode",
                        ("strict_json_loads_v1", "value"): "json.loads",
                    }
                    assert isinstance(node.value, ast.Call)
                    assert (
                        _task3_call_target(node.value)
                        == expected_assignment_calls[binding_key]
                    )
        if isinstance(node, ast.AnnAssign):
            scope = _enclosing_function_name(node, parents)
            if scope not in TASK3_ALL_FUNCTION_SCOPES:
                continue
            assert isinstance(node.target, ast.Name)
            assert node.simple == 1
            annotation_shape = ast.unparse(node.annotation)
            if (scope, node.target.id) == (
                "canonical_json_bytes_v1",
                "active_containers",
            ):
                assert annotation_shape == "set[int]"
                assert isinstance(node.value, ast.Call)
                assert _task3_call_target(node.value) == "set"
                assert node.value.args == [] and node.value.keywords == []
            else:
                assert (scope, node.target.id) == (
                    "reject_duplicate_object_pairs",
                    "result",
                )
                assert annotation_shape == "dict[str, object]"
                assert isinstance(node.value, ast.Dict)
                assert node.value.keys == [] and node.value.values == []
        if (
            isinstance(node, ast.Subscript)
            and not _is_annotation_node(node, parents)
            and _enclosing_function_name(node, parents) in TASK3_ALL_FUNCTION_SCOPES
        ):
            assert isinstance(node.ctx, ast.Store)
            assert _enclosing_function_name(node, parents) == (
                "reject_duplicate_object_pairs"
            )
            assert isinstance(node.value, ast.Name) and node.value.id == "result"
            assert isinstance(node.slice, ast.Name) and node.slice.id == "key"
            assignment = parents[node]
            assert isinstance(assignment, ast.Assign)
            assert assignment.targets == [node]
            assert isinstance(assignment.value, ast.Name)
            assert assignment.value.id == "value"
            loop = parents[assignment]
            assert isinstance(loop, ast.For)
            assert assignment in loop.body
            assert _target_names(loop.target) == ("key", "value")
            assert isinstance(loop.iter, ast.Name) and loop.iter.id == "pairs"
        if (
            isinstance(node, ast.Dict)
            and _enclosing_function_name(node, parents) in TASK3_ALL_FUNCTION_SCOPES
        ):
            assert node.keys == [] and node.values == []
            assignment = parents[node]
            assert isinstance(assignment, ast.AnnAssign)
            assert isinstance(assignment.target, ast.Name)
            assert assignment.target.id == "result"
            assert _enclosing_function_name(assignment, parents) == (
                "reject_duplicate_object_pairs"
            )
        if (
            isinstance(node, (ast.BoolOp, ast.Compare))
            and _enclosing_function_name(node, parents) in TASK3_ALL_FUNCTION_SCOPES
        ):
            assert node in approved_condition_nodes
        if isinstance(node, ast.Raise):
            assert isinstance(node.exc, ast.Call)
            scope = _enclosing_function_name(node, parents)
            allowed_exceptions = (
                {"TypeError", "ValueError", "AssertionError", "RuntimeError"}
                if scope in TASK5_ALL_FUNCTION_SCOPES
                else {"TypeError", "ValueError"}
            )
            assert _task3_call_target(node.exc) in allowed_exceptions
            if node.cause is not None:
                handler = parents[node]
                assert isinstance(handler, ast.ExceptHandler)
                assert isinstance(node.cause, ast.Name)
                assert node.cause.id == handler.name
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            scope = _enclosing_function_name(node, parents)
            if scope is None:
                assert node.id in {
                    "B7_V91_PURE_REPLAY_PROJECTION_SHA256",
                    *TASK4_LITERAL_ASSIGNMENTS,
                    "_require_task5_dependencies_v1",
                }
            elif scope in TASK3_FUNCTION_SIGNATURES or scope in {
                item[1] for item in TASK3_NESTED_FUNCTION_SIGNATURES
            }:
                assert node.id not in TASK3_RESERVED_CALL_ROOTS
                binding_key = (scope, node.id)
                if binding_key in TASK3_EXACT_LOCAL_CALL_BINDINGS:
                    assert binding_key not in observed_exact_local_bindings
                    assignment = parents[node]
                    assert isinstance(assignment, ast.Assign)
                    assert assignment.targets == [node]
                    assert isinstance(assignment.value, ast.Call)
                    assert (
                        _task3_call_target(assignment.value)
                        == TASK3_EXACT_LOCAL_CALL_BINDINGS[binding_key]
                    )
                    observed_exact_local_bindings.add(binding_key)
            else:
                assert scope in (
                    TASK4_FUNCTION_SIGNATURES.keys() | TASK5_ALL_FUNCTION_SCOPES
                )
                assert node.id not in FORBIDDEN_CALL_NAMES
                assert node.id not in FORBIDDEN_MODULE_ROOTS
        if isinstance(node, ast.Attribute) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            raise AssertionError("attribute mutation is forbidden in the Task-3 core")
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            scope = _enclosing_function_name(node, parents)
            if scope in TASK3_FUNCTION_SIGNATURES or scope in {
                item[1] for item in TASK3_NESTED_FUNCTION_SIGNATURES
            }:
                attribute_parent = parents[node]
                assert isinstance(attribute_parent, ast.Call)
                assert attribute_parent.func is node
        if isinstance(node, ast.Call):
            scope = _enclosing_function_name(node, parents)
            if scope in TASK5_ALL_FUNCTION_SCOPES:
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in FORBIDDEN_CALL_NAMES
                if isinstance(node.func, ast.Attribute):
                    assert (
                        _resolved_attribute_root(node.func)
                        not in FORBIDDEN_MODULE_ROOTS
                    )
                continue
            target = _task3_call_target(node)
            assert target is not None, "dynamic call target is forbidden"
            if isinstance(node.func, ast.Name):
                assert node.func.id not in FORBIDDEN_CALL_NAMES
            if isinstance(node.func, ast.Attribute):
                assert _resolved_attribute_root(node.func) not in FORBIDDEN_MODULE_ROOTS
            if scope is None:
                assert target == "_make_task5_dependency_guard_v1"
                assert node.keywords == []
                assert (
                    tuple(
                        argument.id
                        for argument in node.args
                        if isinstance(argument, ast.Name)
                    )
                    == TASK5_DEPENDENCY_BINDINGS
                )
                continue
            if scope in TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION:
                lowered_target = target.casefold()
                assert not any(
                    token in lowered_target for token in TASK3_CAPABILITY_CALL_TOKENS
                )
                assert target in TASK3_ALLOWED_CALL_TARGETS_BY_FUNCTION[scope]
                observed_call_targets[(scope, target)] += 1
                observed_call_expressions[
                    (scope, ast.dump(node, include_attributes=False))
                ] += 1
                positional_count, keyword_names = TASK3_CALL_SHAPES[target]
                shapes = ((positional_count, keyword_names),)
            elif scope in TASK4_FUNCTION_SIGNATURES:
                assert scope in TASK4_FUNCTION_SIGNATURES
                shapes = TASK4_CALL_SHAPES[target]
            else:
                assert scope in TASK5_ALL_FUNCTION_SCOPES
                shapes = (
                    (
                        len(node.args),
                        tuple(keyword.arg for keyword in node.keywords),
                    ),
                )
            observed_shape = (
                len(node.args),
                tuple(keyword.arg for keyword in node.keywords),
            )
            assert observed_shape in shapes
            assert not any(isinstance(argument, ast.Starred) for argument in node.args)
            assert all(keyword.arg is not None for keyword in node.keywords)
            if target == "json.dumps":
                assert {
                    keyword.arg: ast.literal_eval(keyword.value)
                    for keyword in node.keywords
                } == {
                    "ensure_ascii": False,
                    "allow_nan": False,
                    "sort_keys": True,
                    "separators": (",", ":"),
                }
            elif target == "json.loads" and scope == "strict_json_loads_v1":
                observed_hooks = {
                    keyword.arg: keyword.value.id
                    for keyword in node.keywords
                    if isinstance(keyword.value, ast.Name)
                }
                assert observed_hooks == {
                    "object_pairs_hook": "reject_duplicate_object_pairs",
                    "parse_constant": "reject_nonfinite_constant",
                }
        if isinstance(node, ast.arg):
            lowered = node.arg.casefold()
            assert "authority" not in lowered
            assert "callback" not in lowered
            assert "callable" not in lowered

    assert observed_nested_functions == set(TASK3_NESTED_FUNCTION_SIGNATURES)
    assert observed_task5_nested_functions == set(TASK5_NESTED_FUNCTION_SIGNATURES)
    assert observed_exact_local_bindings == set(TASK3_EXACT_LOCAL_CALL_BINDINGS)
    assert observed_call_targets == TASK3_EXPECTED_CALL_TARGETS
    assert observed_call_expressions == expected_call_expressions

    canonical_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _enclosing_function_name(node, parents) == "canonical_json_bytes_v1"
    ]
    guards = [
        node
        for node in canonical_calls
        if _task3_call_target(node) == "validate_object_keys"
    ]
    dumps_calls = [
        node for node in canonical_calls if _task3_call_target(node) == "json.dumps"
    ]
    assert len(guards) == 1 and len(dumps_calls) == 1
    guard = guards[0]
    dumps_call = dumps_calls[0]
    assert len(guard.args) == 2
    assert isinstance(guard.args[0], ast.Name) and guard.args[0].id == "value"
    assert isinstance(guard.args[1], ast.Constant) and guard.args[1].value == "$"
    assert len(dumps_call.args) == 1
    assert isinstance(dumps_call.args[0], ast.Name)
    assert dumps_call.args[0].id == "value"
    guard_statement = parents[guard]
    dumps_statement = parents[dumps_call]
    assert isinstance(guard_statement, ast.Expr)
    assert isinstance(dumps_statement, ast.Assign)
    canonical_function = parents[guard_statement]
    assert isinstance(canonical_function, ast.FunctionDef)
    assert canonical_function.name == "canonical_json_bytes_v1"
    assert parents[dumps_statement] is canonical_function
    assert canonical_function.body.index(
        guard_statement
    ) < canonical_function.body.index(dumps_statement)


def test_core_source_has_exact_task3_task4_symbols_imports_and_signatures() -> None:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    _assert_core_source_contract(CORE_PATH.read_text(encoding="utf-8"))


def test_core_runtime_namespace_has_exact_task3_task4_symbols() -> None:
    core = _core_module()
    import_symbols = {
        "annotations",
        "Fraction",
        "hashlib",
        "json",
        "math",
        "np",
        "scipy",
    }
    observed_public = {
        name
        for name in vars(core)
        if not name.startswith("__")
        and name not in import_symbols
        and not name.startswith("_")
    }
    expected_public = TASK3_PUBLIC_SYMBOLS | TASK4_PUBLIC_VALIDATOR_SYMBOLS
    assert observed_public == expected_public

    observed_private = {
        name
        for name in vars(core)
        if name.startswith("_") and not name.startswith("__")
    }
    expected_private = (
        TASK4_LITERAL_ASSIGNMENTS
        | {name for name in TASK4_FUNCTION_SIGNATURES if name.startswith("_")}
        | set(TASK5_TOP_LEVEL_FUNCTION_ORDER)
        | {"_require_task5_dependencies_v1"}
    )
    assert observed_private == expected_private


def test_task5_owner_neutral_leaf_signatures_are_exact() -> None:
    tree = ast.parse(CORE_PATH.read_text(encoding="utf-8"))
    observed = {
        node.name: tuple(argument.arg for argument in node.args.args)
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in TASK5_FUNCTION_SIGNATURES
    }

    assert observed == TASK5_FUNCTION_SIGNATURES


def test_task5_dependency_guard_is_definition_time_and_dominates_every_leaf() -> None:
    tree = ast.parse(CORE_PATH.read_text(encoding="utf-8"))
    factories = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_make_task5_dependency_guard_v1"
    ]
    assert len(factories) == 1
    factory = factories[0]
    assert len(factory.body) == 2
    nested = factory.body[0]
    factory_return = factory.body[1]
    assert isinstance(nested, ast.FunctionDef)
    assert nested.name == "require_task5_dependencies"
    assert isinstance(factory_return, ast.Return)
    assert isinstance(factory_return.value, ast.Name)
    assert factory_return.value.id == nested.name
    assert len(nested.body) == 1
    dependency_if = nested.body[0]
    assert isinstance(dependency_if, ast.If)
    assert ast.dump(dependency_if.test, include_attributes=False) == (
        _expression_shape(
            "np_candidate is not np_binding "
            "or scipy_candidate is not scipy_binding "
            "or math_candidate is not math_binding "
            "or fraction_candidate is not fraction_binding "
            "or canonical_json_candidate is not canonical_json_binding "
            "or canonical_sha_candidate is not canonical_sha_binding "
            "or strict_json_candidate is not strict_json_binding"
        )
    )
    assert dependency_if.orelse == []
    assert len(dependency_if.body) == 1
    failure = dependency_if.body[0]
    assert isinstance(failure, ast.Raise)
    assert isinstance(failure.exc, ast.Call)
    assert _task3_call_target(failure.exc) == "RuntimeError"
    assert len(failure.exc.args) == 1
    assert isinstance(failure.exc.args[0], ast.Constant)
    assert failure.exc.args[0].value == "B7 Task-5 dependency binding changed"

    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "_require_task5_dependencies_v1"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    assignment_call = assignments[0].value
    assert isinstance(assignment_call, ast.Call)
    assert _task3_call_target(assignment_call) == ("_make_task5_dependency_guard_v1")
    assert len(assignment_call.args) == len(TASK5_DEPENDENCY_BINDINGS)
    assert (
        tuple(
            argument.id
            for argument in assignment_call.args
            if isinstance(argument, ast.Name)
        )
        == TASK5_DEPENDENCY_BINDINGS
    )

    leaves = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in TASK5_FUNCTION_SIGNATURES
    }
    assert set(leaves) == set(TASK5_FUNCTION_SIGNATURES)
    for leaf in leaves.values():
        first_statement = leaf.body[0]
        assert isinstance(first_statement, ast.Expr)
        guard_call = first_statement.value
        assert isinstance(guard_call, ast.Call)
        assert _task3_call_target(guard_call) == "_require_task5_dependencies_v1"
        assert guard_call.keywords == []
        assert len(guard_call.args) == len(TASK5_DEPENDENCY_BINDINGS)
        assert (
            tuple(
                argument.id
                for argument in guard_call.args
                if isinstance(argument, ast.Name)
            )
            == TASK5_DEPENDENCY_BINDINGS
        )


def test_task5_response_wrappers_are_one_guarded_static_delegation() -> None:
    tree = ast.parse(RESPONSE_PATH.read_text(encoding="utf-8"))
    matches = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in TASK5_FUNCTION_SIGNATURES
    }
    assert set(matches) == set(TASK5_FUNCTION_SIGNATURES)
    for function_name, function in matches.items():
        assert (
            tuple(argument.arg for argument in function.args.args)
            == (TASK5_FUNCTION_SIGNATURES[function_name])
        )
        assert len(function.body) == 1
        statement = function.body[0]
        assert isinstance(statement, ast.Return)
        call = statement.value
        assert isinstance(call, ast.Call)
        assert isinstance(call.func, ast.Attribute)
        guard_call = call.func.value
        assert isinstance(guard_call, ast.Call)
        assert isinstance(guard_call.func, ast.Name)
        assert guard_call.func.id == "_require_b7_replay_core_v1"
        assert guard_call.keywords == []
        assert len(guard_call.args) == 1
        assert isinstance(guard_call.args[0], ast.Name)
        assert guard_call.args[0].id == "_b7_replay_core_v1"
        assert call.func.attr == function_name
        assert not call.keywords
        assert len(call.args) == len(TASK5_FUNCTION_SIGNATURES[function_name])
        assert (
            tuple(
                argument.id for argument in call.args if isinstance(argument, ast.Name)
            )
            == TASK5_FUNCTION_SIGNATURES[function_name]
        )


def test_task5_response_core_guard_captures_exact_imported_module() -> None:
    tree = ast.parse(RESPONSE_PATH.read_text(encoding="utf-8"))
    factories = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_make_b7_replay_core_guard_v1"
    ]
    assert len(factories) == 1
    factory = factories[0]
    assert tuple(argument.arg for argument in factory.args.args) == ("core_binding",)
    assert len(factory.body) == 2
    nested = factory.body[0]
    factory_return = factory.body[1]
    assert isinstance(nested, ast.FunctionDef)
    assert tuple(argument.arg for argument in nested.args.args) == ("candidate",)
    assert len(nested.body) == 2
    guard = nested.body[0]
    assert isinstance(guard, ast.If)
    assert ast.dump(guard.test, include_attributes=False) == _expression_shape(
        "candidate is not core_binding"
    )
    failure = guard.body[0]
    assert isinstance(failure, ast.Raise)
    assert isinstance(failure.exc, ast.Call)
    assert _task3_call_target(failure.exc) == "RuntimeError"
    assert isinstance(failure.exc.args[0], ast.Constant)
    assert failure.exc.args[0].value == "B7 replay core module binding changed"
    nested_return = nested.body[1]
    assert isinstance(nested_return, ast.Return)
    assert isinstance(nested_return.value, ast.Name)
    assert nested_return.value.id == "core_binding"
    assert isinstance(factory_return, ast.Return)
    assert isinstance(factory_return.value, ast.Name)
    assert factory_return.value.id == nested.name

    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_require_b7_replay_core_v1"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    assignment_call = assignments[0].value
    assert isinstance(assignment_call, ast.Call)
    assert _task3_call_target(assignment_call) == ("_make_b7_replay_core_guard_v1")
    assert len(assignment_call.args) == 1
    assert isinstance(assignment_call.args[0], ast.Name)
    assert assignment_call.args[0].id == "_b7_replay_core_v1"


@pytest.mark.parametrize("binding_name", TASK5_DEPENDENCY_BINDINGS)
def test_task5_core_dependency_redirect_fails_closed_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    binding_name: str,
) -> None:
    core = _core_module()
    callback_trace: list[str] = []

    class HostileDependency:
        def __call__(self, *args, **kwargs):
            del args, kwargs
            callback_trace.append("call")
            raise AssertionError("caller dependency executed")

        def __getattr__(self, name: str):
            callback_trace.append(name)
            raise AssertionError("caller dependency attribute executed")

    monkeypatch.setattr(core, binding_name, HostileDependency())
    with pytest.raises(RuntimeError, match="B7 Task-5 dependency binding changed"):
        core._assemble_atomic_paired_response_attempt_from_raw(
            None,
            None,
            None,
            None,
            None,
        )
    assert callback_trace == []


def test_task5_response_core_module_redirect_fails_closed_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = importlib.import_module("rulespace_v3.response")
    callback_trace: list[str] = []

    class HostileCore:
        def __getattr__(self, name: str):
            callback_trace.append(name)
            raise AssertionError("caller core module executed")

    monkeypatch.setattr(response, "_b7_replay_core_v1", HostileCore())
    with pytest.raises(RuntimeError, match="B7 replay core module binding changed"):
        response._assemble_atomic_paired_response_attempt_from_raw(
            None,
            None,
            None,
            None,
            None,
        )
    assert callback_trace == []


def _task5_basis(role: str) -> dict[str, object]:
    basis = _task4_minimal_record("BasisManifest")
    basis["role"] = role
    basis["state_schema_id"] = "task5-state-v1"
    basis["channel_order"] = ["q0", "q1"]
    basis["vectors_wire"] = [
        [[1.0, 0.0], [0.0, 0.0]],
        [[0.0, 0.0], [1.0, 0.0]],
    ]
    _task4_resign_tree("BasisManifest", basis)
    return basis


def _task5_response_grid() -> dict[str, object]:
    grid = _task4_minimal_record("ResponseKGridManifest")
    grid["spatial_ndim"] = 1
    grid["torus_denominators"] = [8]
    grid["reciprocal_indices"] = [[0]]
    _task4_resign_tree("ResponseKGridManifest", grid)
    return grid


def _task5_tensor_from_array(values: np.ndarray) -> dict[str, object]:
    array = np.asarray(values, dtype=np.complex128)
    tensor = {
        "tensor_schema_version": "v3m0.frozen-complex-tensor.v1",
        "shape": [int(length) for length in array.shape],
        "values_wire": [
            [float(value.real), float(value.imag)]
            for value in array.reshape(-1, order="C")
        ],
        "tensor_sha": "0" * 64,
    }
    return _task4_seal(tensor, "tensor_sha")


def _task5_bridge_grid() -> dict[str, object]:
    grid = _task4_minimal_record("BridgeKGridManifest")
    grid["spatial_shape"] = [8]
    grid["torus_denominators"] = [8]
    grid["reciprocal_indices"] = [[0]]
    _task4_resign_tree("BridgeKGridManifest", grid)
    return grid


def _task5_current_readout_spec() -> dict[str, object]:
    spec = _task4_minimal_record("CurrentReadoutCalibrationSpecV3")
    spec["source_metric_whitener"] = _task5_tensor_from_array(
        np.eye(10, dtype=np.complex128)
    )
    spec["h_metric_whitener"] = _task5_tensor_from_array(
        np.eye(10, dtype=np.complex128)
    )
    spec["curvature_incidence_operator"] = _task5_tensor_from_array(
        np.eye(10, dtype=np.complex128)[:6]
    )
    spec["curvature_metric_whitener"] = _task5_tensor_from_array(
        np.eye(6, dtype=np.complex128)
    )
    _task4_resign_tree("CurrentReadoutCalibrationSpecV3", spec)
    return spec


def _task5_reference_spec(
    phase_bands: list[list[float]],
) -> dict[str, object]:
    spec = _task4_minimal_record("EndpointReferenceSpec")
    spec["reference_spec_schema_version"] = "v3m0.endpoint-reference-spec.v1"
    spec["window_protocol_sha"] = "a" * 64
    spec["actual_factory_sha"] = "b" * 64
    spec["actual_transition_sha"] = "c" * 64
    spec["actual_dynamics_certificate_sha"] = "d" * 64
    spec["candidate_fejer_order"] = 256
    spec["reference_reciprocal_index"] = [0]
    spec["preregistered_phase_bands"] = phase_bands
    spec["expected_shell_rank"] = 1
    spec["expected_shell_rank_source_id"] = "parent-freeze-control-application-spec-v1"
    _task4_resign_tree("EndpointReferenceSpec", spec)
    return spec


def _task5_reference_success_raw(
    spec: dict[str, object],
) -> dict[str, object]:
    projector = _task5_tensor_from_array(np.ones((1, 1), dtype=np.complex128))
    reference = _task4_seal(
        {
            "reference_schema_version": "v3m0.endpoint-reference-projector.v1",
            "control_registry_entry_sha": spec["control_registry_entry"]["entry_sha"],
            "actual_transition_sha": spec["actual_transition_sha"],
            "actual_dynamics_certificate_sha": spec["actual_dynamics_certificate_sha"],
            "reference_reciprocal_index": spec["reference_reciprocal_index"],
            "reference_phase": math.pi / 2.0,
            "projector_coordinate_convention_id": "g-whitened-state-v1",
            "rank": 1,
            "projector": projector,
            "reference_sha": "0" * 64,
        },
        "reference_sha",
    )
    attempt = _task4_seal(
        {
            "attempt_schema_version": "v3m0.endpoint-reference-attempt.v1",
            "reference_spec": spec,
            "candidate_phases": [math.pi / 2.0],
            "candidate_ranks": [1],
            "expected_shell_rank": 1,
            "expected_shell_rank_source_id": (
                "parent-freeze-control-application-spec-v1"
            ),
            "candidate_participations": [1.0],
            "runner_up_overlaps": [None],
            "hermitian_residuals": [0.0],
            "idempotent_residuals": [0.0],
            "g_invariance_residuals": [0.0],
            "eigenphase_residuals": [math.cos(math.pi / 2.0)],
            "observed_competitor_gaps": [None],
            "attempt_sha": "0" * 64,
        },
        "attempt_sha",
    )
    return _task4_seal(
        {
            "status": {"defined": True, "reason": None},
            "failure": None,
            "reference_spec": spec,
            "attempt_audit": attempt,
            "reference": reference,
            "outcome_sha": "0" * 64,
        },
        "outcome_sha",
    )


def _task5_shell_spec(
    reference_outcome: dict[str, object],
) -> dict[str, object]:
    assert isinstance(reference_outcome["reference"], dict)
    spec = _task4_minimal_record("EndpointShellSpec")
    spec["shell_spec_schema_version"] = "v3m0.endpoint-shell-spec.v1"
    spec["window_protocol_sha"] = "a" * 64
    spec["control_registry_entry"] = reference_outcome["reference_spec"][
        "control_registry_entry"
    ]
    grid = _task5_response_grid()
    direction = grid["direction_manifest"]
    direction["direction_ids"] = ["d0"]
    direction["primitive_directions"] = [[1]]
    direction["path_ids"] = ["p0"]
    direction["ordered_paths"] = [[[0]]]
    direction["closure_path_pairs"] = []
    _task4_resign_tree("ResponseKGridManifest", grid)
    spec["response_grid"] = grid
    spec["preregistered_phase_bands"] = [[1.0, 2.0]]
    spec["candidate_fejer_order"] = 256
    spec["endpoint_reference_projector"] = reference_outcome["reference"]
    spec["extraction_protocol_id"] = "endpoint-single-node-reference-v1"
    _task4_resign_tree("EndpointShellSpec", spec)
    return spec


def test_task5_fejer_leaf_builds_canonical_ordered_fp64_tensor() -> None:
    core = _core_module()
    transition = np.asarray(
        [[1.0 + 0.0j, 0.0 + 0.0j], [0.0 + 0.0j, -1.0 + 0.0j]],
        dtype=np.complex128,
    )
    metric = np.eye(2, dtype=np.complex128)

    observed = core._build_fejer_branch_response_values_from_raw(
        "actual",
        _task5_response_grid(),
        256,
        _task5_basis("source"),
        _task5_basis("readout"),
        [0.0],
        (transition,),
        (metric,),
    )

    expected = _task4_tensor([1, 2, 2])
    expected["values_wire"] = [
        [1.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [1.0 / 257.0, 0.0],
    ]
    expected = _task4_seal(expected, "tensor_sha")
    assert observed == expected


@pytest.mark.parametrize(
    ("branch", "shell_phases", "matrices"),
    (
        ("caller", [0.0], "valid"),
        ("actual", [], "valid"),
        ("actual", [0.0], "float64"),
    ),
)
def test_task5_fejer_leaf_rejects_owner_and_numeric_shape_drift(
    branch: str,
    shell_phases: list[float],
    matrices: str,
) -> None:
    core = _core_module()
    dtype = np.float64 if matrices == "float64" else np.complex128
    transition = np.eye(2, dtype=dtype)

    with pytest.raises((TypeError, ValueError)):
        core._build_fejer_branch_response_values_from_raw(
            branch,
            _task5_response_grid(),
            256,
            _task5_basis("source"),
            _task5_basis("readout"),
            shell_phases,
            (transition,),
            (np.eye(2, dtype=np.complex128),),
        )


def test_task5_reference_leaf_selects_and_hashes_one_invariant_projector() -> None:
    core = _core_module()
    spec = _task5_reference_spec([[1.0, 2.0]])
    transition = np.asarray([[0.0 + 1.0j]], dtype=np.complex128)
    identity = np.ones((1, 1), dtype=np.complex128)

    observed = core._select_endpoint_reference_from_raw(
        spec,
        transition,
        identity,
        identity,
        identity,
    )

    assert observed == _task5_reference_success_raw(spec)


def test_task5_reference_leaf_freezes_empty_band_failure_prefix() -> None:
    core = _core_module()
    spec = _task5_reference_spec([[-2.0, -1.0]])
    transition = np.asarray([[0.0 + 1.0j]], dtype=np.complex128)
    identity = np.ones((1, 1), dtype=np.complex128)

    observed = core._select_endpoint_reference_from_raw(
        spec,
        transition,
        identity,
        identity,
        identity,
    )

    assert observed["status"] == {
        "defined": False,
        "reason": "endpoint_shell_ambiguous",
    }
    assert observed["failure"] == "phase_band_empty"
    assert observed["reference"] is None
    assert observed["attempt_audit"]["candidate_phases"] == []
    assert observed["outcome_sha"] == _task4_canonical_sha(
        {key: value for key, value in observed.items() if key != "outcome_sha"}
    )


def test_task5_shell_leaf_tracks_one_path_and_freezes_complete_manifest() -> None:
    core = _core_module()
    reference_spec = _task5_reference_spec([[1.0, 2.0]])
    reference_outcome = _task5_reference_success_raw(reference_spec)
    shell_spec = _task5_shell_spec(reference_outcome)
    transition = np.asarray([[0.0 + 1.0j]], dtype=np.complex128)
    identity = np.ones((1, 1), dtype=np.complex128)

    observed = core._track_endpoint_shell_from_raw(
        reference_outcome,
        shell_spec,
        (transition,),
        (identity,),
        identity,
        identity,
        "1" * 64,
        "2" * 64,
        "3" * 64,
        1.0,
    )

    assert observed["status"] == {"defined": True, "reason": None}
    assert observed["failure"] is None
    shell = observed["shell"]
    assert shell["shell_phases"] == [math.pi / 2.0]
    assert shell["point_audits"][0]["rank"] == 1
    assert shell["point_audits"][0]["momentum_path_id"] == "p0"
    assert shell["shell_projectors"] == _task5_tensor_from_array(
        np.ones((1, 1, 1), dtype=np.complex128)
    )
    assert shell["shell_manifest_sha"] == _task4_canonical_sha(
        {key: value for key, value in shell.items() if key != "shell_manifest_sha"}
    )
    assert observed["outcome_sha"] == _task4_canonical_sha(
        {key: value for key, value in observed.items() if key != "outcome_sha"}
    )


def test_task5_bridge_leaf_supports_rectangular_current_curvature_readout() -> None:
    core = _core_module()
    raw_difference = np.diag(np.arange(1.0, 11.0, dtype=np.float64)).astype(
        np.complex128
    )
    spec = _task5_current_readout_spec()

    observed = core._audit_source_readout_bridge_from_raw(
        "actual",
        "1" * 64,
        "2" * 64,
        "3" * 64,
        "4" * 64,
        _task5_bridge_grid(),
        [2],
        _task5_tensor_from_array(np.eye(10, dtype=np.complex128)),
        spec,
        (((0,), 2, raw_difference),),
    )

    assert observed["branch"] == "actual"
    assert (
        observed["source_metric_whitener_sha"]
        == (spec["source_metric_whitener"]["tensor_sha"])
    )
    assert observed["readout_calibration_spec_sha"] == spec["spec_sha"]
    assert len(observed["matrix_audits"]) == 1
    matrix = observed["matrix_audits"][0]
    assert matrix["raw_difference_matrix"] == _task5_tensor_from_array(raw_difference)
    assert matrix["frame_coverage"] is None
    assert matrix["h_whitened_operator_error_upper"] >= float(
        np.linalg.norm(raw_difference, "fro")
    )
    assert matrix["curv_whitened_operator_error_upper"] >= float(
        np.linalg.norm(raw_difference[:6], "fro")
    )
    assert observed["bridge_sha"] == _task4_canonical_sha(
        {key: value for key, value in observed.items() if key != "bridge_sha"}
    )


def test_task5_bridge_leaf_rejects_nonidentity_trial_frame() -> None:
    core = _core_module()
    trials = np.eye(10, dtype=np.complex128)
    trials[0, 0] = 2.0 + 0.0j

    with pytest.raises(ValueError, match="identity frame"):
        core._audit_source_readout_bridge_from_raw(
            "actual",
            "1" * 64,
            "2" * 64,
            "3" * 64,
            "4" * 64,
            _task5_bridge_grid(),
            [2],
            _task5_tensor_from_array(trials),
            _task5_current_readout_spec(),
            (((0,), 2, np.eye(10, dtype=np.complex128)),),
        )


def _task5_branch_attempt(
    branch: str,
    response_values: object,
    bridge_audit: object,
    failure: str | None,
) -> dict[str, object]:
    return _task4_seal(
        {
            "branch_attempt_schema_version": ("experimental.v3m0.b7.branch-attempt.v1"),
            "branch": branch,
            "response_values": response_values,
            "bridge_audit": bridge_audit,
            "failure": failure,
            "attempt_sha": "0" * 64,
        },
        "attempt_sha",
    )


def test_task5_atomic_assembly_preserves_actual_response_failure_prefix() -> None:
    core = _core_module()

    observed = core._assemble_atomic_paired_response_attempt_from_raw(
        None,
        None,
        None,
        None,
        "actual_response_failed",
    )
    assert observed == (
        _task5_branch_attempt(
            "actual",
            None,
            None,
            "actual_response_failed",
        ),
        None,
        "actual_response_failed",
    )


@pytest.mark.parametrize(
    ("first_failure", "expected_actual", "expected_matched"),
    (
        (
            "matched_ablated_response_failed",
            ("present", None),
            ("absent", "matched_ablated_response_failed"),
        ),
        (
            "actual_bridge_failed",
            ("present", "actual_bridge_failed"),
            ("present", None),
        ),
    ),
)
def test_task5_atomic_assembly_preserves_values_prefix_before_bridge(
    first_failure: str,
    expected_actual: tuple[str, str | None],
    expected_matched: tuple[str, str | None],
) -> None:
    core = _core_module()
    actual_values = _task4_tensor([1, 1])
    matched_values = (
        None
        if first_failure == "matched_ablated_response_failed"
        else _task4_tensor([1, 1])
    )

    actual, matched, observed_failure = (
        core._assemble_atomic_paired_response_attempt_from_raw(
            actual_values,
            matched_values,
            None,
            None,
            first_failure,
        )
    )

    assert observed_failure == first_failure
    assert actual == _task5_branch_attempt(
        "actual",
        actual_values,
        None,
        expected_actual[1],
    )
    assert matched == _task5_branch_attempt(
        "matched_ablated",
        None if expected_matched[0] == "absent" else matched_values,
        None,
        expected_matched[1],
    )


@pytest.mark.parametrize(
    "first_failure",
    ("matched_ablated_bridge_failed", None),
)
def test_task5_atomic_assembly_preserves_bridge_prefix_and_success(
    first_failure: str | None,
) -> None:
    core = _core_module()
    actual_values = _task4_tensor([1, 1])
    matched_values = _task4_tensor([1, 1])
    actual_bridge = _task4_minimal_record("SourceReadoutBridgeAudit")
    matched_bridge = json.loads(json.dumps(actual_bridge))
    matched_bridge["branch"] = "matched_ablated"
    _task4_resign_tree("SourceReadoutBridgeAudit", matched_bridge)
    supplied_matched_bridge = None if first_failure is not None else matched_bridge

    observed = core._assemble_atomic_paired_response_attempt_from_raw(
        actual_values,
        matched_values,
        actual_bridge,
        supplied_matched_bridge,
        first_failure,
    )

    assert observed == (
        _task5_branch_attempt(
            "actual",
            actual_values,
            actual_bridge,
            None,
        ),
        _task5_branch_attempt(
            "matched_ablated",
            matched_values,
            supplied_matched_bridge,
            first_failure,
        ),
        first_failure,
    )


def test_task5_atomic_assembly_rejects_post_failure_evidence() -> None:
    core = _core_module()

    with pytest.raises(ValueError, match="invalid raw prefix"):
        core._assemble_atomic_paired_response_attempt_from_raw(
            _task4_tensor([1, 1]),
            None,
            None,
            None,
            "actual_response_failed",
        )


def test_static_contract_rejects_extra_helper_callback_and_capability_imports() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    attacks = (
        source + "\ndef _extra_callback_helper(value):\n    return value\n",
        source.replace(
            "def canonical_json_bytes_v1(value: object)",
            "def canonical_json_bytes_v1(value: object, callback=None)",
            1,
        ),
        source.replace(
            "def validate_response_run_spec_fixture_v1(\n    raw_body: object,",
            "def validate_response_run_spec_fixture_v1(\n    raw_body: object,\n    callback: object,",
            1,
        ),
        source.replace("import json", "import json\nimport time", 1),
        source.replace("import json", "import json\nimport random", 1),
        source.replace("import json", "import json\nimport os", 1),
        source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if callable(value):\n        return value()\n",
            1,
        ),
        source.replace(
            '    """Validate one B7 ResponseRunSpec-v3 raw fixture and supplied joins."""\n',
            '    """Validate one B7 ResponseRunSpec-v3 raw fixture and supplied joins."""\n'
            + "    if callable(raw_body):\n"
            + "        return raw_body()\n",
            1,
        ),
        source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if hasattr(value, 'issue_authority'):\n"
            + "        return value.issue_authority()\n",
            1,
        ),
    )

    for attacked_source in attacks:
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_task4_static_contract_rejects_allowlisted_call_target_substitution() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    attacked_source = source.replace(
        "canonical_json_bytes_v1(left)",
        "canonical_sha_v1(left)",
        1,
    )

    assert attacked_source != source
    with pytest.raises((AssertionError, KeyError)):
        _assert_core_source_contract(attacked_source)


def test_static_contract_rejects_definition_use_capability_escapes() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    strict_load_anchor = "    value = json.loads(\n"
    canonical_try_anchor = '    try:\n        return str.encode(text, "utf-8")\n'

    receiver_rebinding = source.replace(
        canonical_try_anchor,
        '    if value == "__escape__":\n        text = value\n' + canonical_try_anchor,
        1,
    )
    attacks = {
        "callee_alias": source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    hidden_hook = value\n"
            + "    if False:\n"
            + "        return hidden_hook()\n",
            1,
        ),
        "parameter_attribute_call": source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if False:\n"
            + "        return value.issue_authority()\n",
            1,
        ),
        "parameter_attribute_load": source.replace(
            canonical_body_anchor,
            canonical_body_anchor
            + "\n    if False:\n"
            + "        value.issue_authority\n",
            1,
        ),
        "kwargs_hook_replacement": source.replace(
            "object_pairs_hook=reject_duplicate_object_pairs,",
            "object_pairs_hook=json.loads,",
            1,
        ),
        "nested_hook_rebinding": source.replace(
            strict_load_anchor,
            '    if canonical_json_utf8 == b"__escape__":\n'
            "        reject_duplicate_object_pairs = canonical_json_utf8.__class__\n"
            + strict_load_anchor,
            1,
        ),
        "allowlisted_receiver_rebinding": receiver_rebinding,
    }

    for attack_id, attacked_source in attacks.items():
        assert attacked_source != source, (
            f"attack fixture did not mutate source: {attack_id}"
        )
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_except_handler_cannot_shadow_json_receiver_before_sentinel_dispatch() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    attacked_source = source.replace(
        canonical_body_anchor,
        canonical_body_anchor
        + "\n    try:\n"
        + "        raise value\n"
        + "    except BaseException as json:\n"
        + "        return json.dumps(\n"
        + "            value,\n"
        + "            ensure_ascii=False,\n"
        + "            allow_nan=False,\n"
        + "            sort_keys=True,\n"
        + '            separators=(",", ":"),\n'
        + "        )\n",
        1,
    )
    callback_trace: list[object] = []

    class ReceiverSentinel(BaseException):
        def dumps(self, *args, **kwargs):
            callback_trace.append(self)
            return b"CALLER_RECEIVER"

    namespace: dict[str, object] = {}
    exec(compile(attacked_source, "<except-receiver-attack>", "exec"), namespace)
    sentinel = ReceiverSentinel()

    assert namespace["canonical_json_bytes_v1"](sentinel) == b"CALLER_RECEIVER"
    assert callback_trace == [sentinel]
    with pytest.raises((AssertionError, KeyError)):
        _assert_core_source_contract(attacked_source)


def test_static_contract_rejects_implicit_protocol_surfaces() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    candidate_type_anchor = "        candidate_type = type(candidate)\n"
    attacks = {
        "with": canonical_body_anchor + "\n    with value as hidden:\n        pass\n",
        "for": canonical_body_anchor + "\n    for hidden in value:\n        break\n",
        "comprehension": canonical_body_anchor + "\n    [hidden for hidden in value]\n",
        "named_expression": candidate_type_anchor
        + "        (candidate_type := list)\n",
        "subscript_load": canonical_body_anchor + "\n    value[0]\n",
        "subscript_store": canonical_body_anchor + "\n    value[0] = 1\n",
        "subscript_delete": canonical_body_anchor + "\n    del value[0]\n",
        "augmented_assignment": canonical_body_anchor + "\n    value += ()\n",
        "truthiness_if": canonical_body_anchor + "\n    if value:\n        pass\n",
        "truthiness_assert": canonical_body_anchor + "\n    assert value\n",
        "formatted_string": canonical_body_anchor + '\n    f"{value}"\n',
        "binary_operation": canonical_body_anchor + "\n    value + 1\n",
        "membership": canonical_body_anchor + "\n    0 in value\n",
        "star_list": canonical_body_anchor + "\n    [*value]\n",
        "star_dict": canonical_body_anchor + "\n    {**value}\n",
        "set_literal": canonical_body_anchor + "\n    {value}\n",
        "dict_key": canonical_body_anchor + "\n    {value: 1}\n",
        "unpack_assignment": canonical_body_anchor + "\n    hidden, = value\n",
        "yield": canonical_body_anchor + "\n    yield value\n",
        "yield_from": canonical_body_anchor + "\n    yield from value\n",
    }

    for attack_id, injected_source in attacks.items():
        if attack_id == "named_expression":
            attacked_source = source.replace(
                candidate_type_anchor,
                injected_source,
                1,
            )
        else:
            attacked_source = source.replace(
                canonical_body_anchor,
                injected_source,
                1,
            )
        assert attacked_source != source, (
            f"attack fixture did not mutate source: {attack_id}"
        )
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_dynamic_container_literals_dispatch_only_without_static_gate() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'

    for expression in ("{value}", "{value: 1}"):
        attacked_source = source.replace(
            canonical_body_anchor,
            canonical_body_anchor + f"\n    {expression}\n",
            1,
        )
        callback_trace: list[str] = []

        class HashSentinel:
            def __hash__(self):
                callback_trace.append("__hash__")
                return 0

        namespace: dict[str, object] = {}
        exec(compile(attacked_source, "<literal-attack>", "exec"), namespace)
        with pytest.raises(TypeError, match="exact built-in JSON"):
            namespace["canonical_json_bytes_v1"](HashSentinel())
        assert callback_trace != []


def test_early_return_dead_code_attack_runs_only_without_static_gate() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    attacked_source = source.replace(
        canonical_body_anchor,
        canonical_body_anchor + '\n    return b"ATTACK"\n',
        1,
    )
    namespace: dict[str, object] = {}
    exec(compile(attacked_source, "<early-return-attack>", "exec"), namespace)

    assert namespace["canonical_json_bytes_v1"]({"safe": 1}) == b"ATTACK"
    with pytest.raises((AssertionError, KeyError)):
        _assert_core_source_contract(attacked_source)


def test_static_contract_rejects_early_return_in_every_function_scope() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    attacks = {
        "canonical_json_bytes_v1": (
            '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n',
            '\n    return b"ATTACK"\n',
        ),
        "validate_object_keys": (
            "    def validate_object_keys(candidate: object, path: str) -> None:\n",
            "        return\n",
        ),
        "canonical_sha_v1": (
            '    """Hash the frozen canonical JSON bytes for one B7 raw value."""\n',
            '\n    return "ATTACK"\n',
        ),
        "strict_json_loads_v1": (
            '    """Decode strict UTF-8 JSON while rejecting BOMs, duplicates and NaN."""\n',
            "\n    return canonical_json_utf8\n",
        ),
        "reject_duplicate_object_pairs": (
            "    def reject_duplicate_object_pairs(\n"
            "        pairs: list[tuple[str, object]],\n"
            "    ) -> dict[str, object]:\n",
            "        return pairs\n",
        ),
        "reject_nonfinite_constant": (
            "    def reject_nonfinite_constant(constant_text: str) -> object:\n",
            "        return constant_text\n",
        ),
    }

    for attack_id, (anchor, injection) in attacks.items():
        attacked_source = source.replace(anchor, anchor + injection, 1)
        assert attacked_source != source, (
            f"attack fixture did not mutate source: {attack_id}"
        )
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_statement_reorder_attack_runs_only_without_static_gate() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'
    encode_try = (
        '    try:\n        return str.encode(text, "utf-8")\n'
        "    except UnicodeEncodeError as exc:\n"
        '        raise ValueError("canonical JSON text must be valid UTF-8") from exc\n'
    )
    attacked_source = source.replace(encode_try, "", 1).replace(
        canonical_body_anchor,
        canonical_body_anchor + "\n" + encode_try,
        1,
    )
    namespace: dict[str, object] = {}
    exec(compile(attacked_source, "<statement-reorder-attack>", "exec"), namespace)

    with pytest.raises(UnboundLocalError):
        namespace["canonical_json_bytes_v1"]({"safe": 1})
    with pytest.raises((AssertionError, KeyError)):
        _assert_core_source_contract(attacked_source)


def test_static_contract_rejects_zero_binding_zero_call_statements() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    canonical_body_anchor = '    """Encode one JSON value using the frozen B7 canonical byte algorithm."""\n'

    for statement in ("pass", 'b"ATTACK"'):
        attacked_source = source.replace(
            canonical_body_anchor,
            canonical_body_anchor + f"\n    {statement}\n",
            1,
        )
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_projection_literal_recomputes_from_the_pinned_registry() -> None:
    registry = _registry()
    projection_contract = registry["lab_contract"]["pure_replay_core_contract"][
        "registry_literal_projection"
    ]
    projection: dict[str, object] = {}
    for field, pointer in zip(
        projection_contract["field_order"],
        projection_contract["source_pointers_in_field_order"],
    ):
        value: object = registry
        for token in pointer.removeprefix("/").split("/"):
            assert isinstance(value, dict)
            value = value[token]
        projection[field] = value

    canonical = json.dumps(
        projection,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    observed = hashlib.sha256(canonical).hexdigest()
    assert observed == PROJECTION_SHA256
    assert observed == projection_contract["canonical_sha256"]

    core = _core_module()
    assert core.B7_V91_PURE_REPLAY_PROJECTION_SHA256 == observed


def test_canonical_json_bytes_and_sha_match_the_registry_algorithm() -> None:
    core = _core_module()
    payload = {"β": "雪", "a": [1, -0.0, True, None]}
    expected = '{"a":[1,-0.0,true,null],"β":"雪"}'.encode("utf-8")

    assert core.canonical_json_bytes_v1(payload) == expected
    assert core.canonical_sha_v1(payload) == hashlib.sha256(expected).hexdigest()
    with pytest.raises(ValueError):
        core.canonical_json_bytes_v1({"bad": math.nan})
    with pytest.raises(TypeError, match="key"):
        core.canonical_json_bytes_v1({1: "not-a-JSON-object-key"})
    with pytest.raises(ValueError, match="UTF-8"):
        core.canonical_json_bytes_v1({"bad": "\ud800"})
    cyclic_list: list[object] = []
    cyclic_list.append(cyclic_list)
    with pytest.raises(ValueError, match="cyclic"):
        core.canonical_json_bytes_v1(cyclic_list)
    cyclic_dict: dict[str, object] = {}
    cyclic_dict["self"] = cyclic_dict
    with pytest.raises(ValueError, match="cyclic"):
        core.canonical_json_bytes_v1(cyclic_dict)


def test_canonical_json_rejects_subclasses_before_caller_dispatch() -> None:
    core = _core_module()
    callback_trace: list[str] = []

    class CallerDict(dict):
        def items(self):
            callback_trace.append("dict.items")
            return super().items()

    class CallerList(list):
        def __iter__(self):
            callback_trace.append("list.__iter__")
            return super().__iter__()

    class CallerTuple(tuple):
        def __iter__(self):
            callback_trace.append("tuple.__iter__")
            return super().__iter__()

    class CallerString(str):
        def encode(self, encoding="utf-8", errors="strict"):
            callback_trace.append("str.encode")
            return super().encode(encoding, errors)

    subclass_values = (
        CallerDict(a=1),
        CallerList((1, 2)),
        CallerTuple((1, 2)),
        CallerString("caller-owned"),
        {"nested": CallerDict(a=1)},
        {"nested": CallerList((1, 2))},
        {"nested": CallerTuple((1, 2))},
        {"nested": CallerString("caller-owned")},
    )

    for value in subclass_values:
        callback_trace.clear()
        with pytest.raises(TypeError, match="exact built-in JSON"):
            core.canonical_json_bytes_v1(value)
        assert callback_trace == []


def test_canonical_json_rejects_custom_metaclass_without_equality_dispatch() -> None:
    core = _core_module()
    callback_trace: list[object] = []

    class CallerMetaclass(type):
        def __eq__(cls, other):
            callback_trace.append(other)
            return False

    class CallerValue(metaclass=CallerMetaclass):
        pass

    with pytest.raises(TypeError, match="exact built-in JSON"):
        core.canonical_json_bytes_v1(CallerValue())
    assert callback_trace == []


def test_static_contract_freezes_future_annotations_guard_order_and_handlers() -> None:
    source = CORE_PATH.read_text(encoding="utf-8")
    guard = '    validate_object_keys(value, "$")\n'
    canonical_try = '    try:\n        return str.encode(text, "utf-8")\n'
    delayed_guard = source.replace(guard, "", 1).replace(
        canonical_try,
        guard + canonical_try,
        1,
    )
    attacks = {
        "future_feature": source.replace(
            "from __future__ import annotations",
            "from __future__ import generator_stop",
            1,
        ),
        "argument_annotation": source.replace(
            "from __future__ import annotations",
            "from __future__ import generator_stop",
            1,
        ).replace(
            "def canonical_json_bytes_v1(value: object)",
            "def canonical_json_bytes_v1(value: probe[0])",
            1,
        ),
        "return_annotation": source.replace(
            "from __future__ import annotations",
            "from __future__ import generator_stop",
            1,
        ).replace(
            "def canonical_json_bytes_v1(value: object) -> bytes",
            "def canonical_json_bytes_v1(value: object) -> probe[0]",
            1,
        ),
        "delayed_guard": delayed_guard,
        "handler_type": source.replace(
            "except UnicodeEncodeError as exc:",
            "except BaseException as exc:",
            1,
        ),
        "handler_name": source.replace(
            "except UnicodeEncodeError as exc:",
            "except UnicodeEncodeError as hidden:",
            1,
        ).replace(
            "from exc\n\n\ndef canonical_sha_v1",
            "from hidden\n\n\ndef canonical_sha_v1",
            1,
        ),
        "handler_cause": source.replace(
            "from exc\n\n\ndef canonical_sha_v1",
            "from value\n\n\ndef canonical_sha_v1",
            1,
        ),
    }

    for attack_id, attacked_source in attacks.items():
        assert attacked_source != source, (
            f"attack fixture did not mutate source: {attack_id}"
        )
        with pytest.raises((AssertionError, KeyError)):
            _assert_core_source_contract(attacked_source)


def test_annotation_and_delayed_guard_attacks_dispatch_only_without_static_gate() -> (
    None
):
    source = CORE_PATH.read_text(encoding="utf-8")
    annotation_attack = (
        source.replace(
            "from __future__ import annotations",
            "from __future__ import generator_stop",
            1,
        )
        .replace(
            "def canonical_json_bytes_v1(value: object)",
            "def canonical_json_bytes_v1(value: probe[0])",
            1,
        )
        .replace(
            "str | None",
            "object",
        )
    )
    annotation_trace: list[object] = []

    class AnnotationProbe:
        def __getitem__(self, key):
            annotation_trace.append(key)
            return object

    exec(
        compile(
            annotation_attack,
            "<annotation-attack>",
            "exec",
            dont_inherit=True,
        ),
        {"probe": AnnotationProbe()},
    )
    assert annotation_trace == [0]

    guard = '    validate_object_keys(value, "$")\n'
    canonical_try = '    try:\n        return str.encode(text, "utf-8")\n'
    delayed_guard = source.replace(guard, "", 1).replace(
        canonical_try,
        guard + canonical_try,
        1,
    )
    item_trace: list[str] = []

    class CallerDict(dict):
        def items(self):
            item_trace.append("items")
            return super().items()

    namespace: dict[str, object] = {}
    exec(compile(delayed_guard, "<delayed-guard-attack>", "exec"), namespace)
    with pytest.raises(TypeError):
        namespace["canonical_json_bytes_v1"](CallerDict(a=1))
    assert item_trace != []


def test_strict_json_loader_rejects_ambiguous_or_nonfinite_input() -> None:
    core = _core_module()

    assert core.strict_json_loads_v1(b'{"a":[1,true,null],"z":"\xe9\x9b\xaa"}') == {
        "a": [1, True, None],
        "z": "雪",
    }
    with pytest.raises(TypeError):
        core.strict_json_loads_v1('{"a":1}')
    with pytest.raises(ValueError, match="BOM"):
        core.strict_json_loads_v1(b"\xef\xbb\xbf{}")
    with pytest.raises(ValueError, match="duplicate"):
        core.strict_json_loads_v1(b'{"a":1,"a":2}')
    with pytest.raises(ValueError, match="UTF-8"):
        core.strict_json_loads_v1(b'"\\ud800"')
    for token in (b"NaN", b"Infinity", b"-Infinity"):
        with pytest.raises(ValueError, match="finite"):
            core.strict_json_loads_v1(token)


# Task 4 fixtures are deliberately independent of the not-yet-created Task 7
# D1 corpus.  They freeze legal raw production-body shapes without claiming D1
# corpus coverage.
def _task4_canonical_sha(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _task4_seal(raw_body: dict[str, object], hash_field: str) -> dict[str, object]:
    payload = {key: value for key, value in raw_body.items() if key != hash_field}
    sealed = dict(payload)
    sealed[hash_field] = _task4_canonical_sha(payload)
    return sealed


def _task4_tensor(shape: list[int]) -> dict[str, object]:
    entry_count = math.prod(shape)
    return _task4_seal(
        {
            "tensor_schema_version": "v3m0.frozen-complex-tensor.v1",
            "shape": shape,
            "values_wire": [[0.0, 0.0] for _ in range(entry_count)],
            "tensor_sha": "0" * 64,
        },
        "tensor_sha",
    )


def _task4_branch_attempt(
    branch: str = "actual",
) -> dict[str, object]:
    return _task4_seal(
        {
            "branch_attempt_schema_version": ("experimental.v3m0.b7.branch-attempt.v1"),
            "branch": branch,
            "response_values": _task4_tensor([1, 1]),
            "bridge_audit": None,
            "failure": None,
            "attempt_sha": "0" * 64,
        },
        "attempt_sha",
    )


def test_task4_branch_attempt_accepts_fixture_independent_legal_raw_body() -> None:
    core = _core_module()
    raw_body = _task4_branch_attempt()

    assert core.validate_branch_attempt_v1(raw_body) == raw_body
    assert raw_body["attempt_sha"] == _task4_canonical_sha(
        {key: value for key, value in raw_body.items() if key != "attempt_sha"}
    )


def test_task4_canonical_roundtrip_projects_catalog_field_order() -> None:
    core = _core_module()
    raw_body = _task4_branch_attempt()
    roundtripped = core.strict_json_loads_v1(core.canonical_json_bytes_v1(raw_body))
    assert type(roundtripped) is dict
    assert tuple(roundtripped) != tuple(raw_body)

    projected = core.validate_branch_attempt_v1(roundtripped)

    assert projected == raw_body
    assert tuple(projected) == tuple(raw_body)


def test_task4_hex64_accepts_exact_fp64_bits_and_rejects_sha256_width() -> None:
    core = _core_module()
    normalizer = _task4_minimal_record("CurrentCurvatureNormalizerProtocolV1")
    normalizer["ordered_reciprocal_indices"] = [[1]]
    normalizer["ordered_momentum_values"] = [[math.pi / 4.0]]
    normalizer["ordered_momentum_fp64_bits"] = [["3fe921fb54442d18"]]
    normalizer["ordered_normalizer_values"] = [0.5857864376269049]
    normalizer["ordered_normalizer_fp64_bits"] = ["3fe2bec333018867"]
    _task4_resign_tree("CurrentCurvatureNormalizerProtocolV1", normalizer)

    assert (
        core._validate_record_raw_v1(
            normalizer,
            "CurrentCurvatureNormalizerProtocolV1",
            "normalizer",
            core._record_schemas_v1(),
        )
        == normalizer
    )
    for hostile_bits in (True, "A" * 16, "a" * 15, "a" * 17, "a" * 64):
        hostile = _task4_clone(normalizer)
        hostile["ordered_normalizer_fp64_bits"] = [hostile_bits]
        _task4_resign_tree("CurrentCurvatureNormalizerProtocolV1", hostile)
        with pytest.raises((TypeError, ValueError)):
            core._validate_record_raw_v1(
                hostile,
                "CurrentCurvatureNormalizerProtocolV1",
                "normalizer",
                core._record_schemas_v1(),
            )


@pytest.mark.parametrize(
    ("record_name", "legal_failure"),
    (
        ("DynamicsCertificationOutcomeV3", "transition_invalid"),
        ("EndpointReferenceOutcome", "phase_band_empty"),
        ("EndpointShellOutcome", "gap_failed"),
        ("PairedResponseOutcome", "actual_response_failed"),
        ("ControlCandidateOutcome", "reference_failed"),
    ),
)
def test_task4_named_failure_enums_reject_bool_and_unknown(
    record_name: str,
    legal_failure: str,
) -> None:
    core = _core_module()
    legal = _task4_minimal_record(record_name)
    legal["failure"] = legal_failure
    _task4_resign_tree(record_name, legal)
    assert (
        core._validate_record_raw_v1(
            legal,
            record_name,
            "named_failure",
            core._record_schemas_v1(),
        )
        == legal
    )
    for hostile_value in (True, "caller-defined-failure"):
        hostile = _task4_clone(legal)
        hostile["failure"] = hostile_value
        _task4_resign_tree(record_name, hostile)
        with pytest.raises((TypeError, ValueError)):
            core._validate_record_raw_v1(
                hostile,
                record_name,
                "named_failure",
                core._record_schemas_v1(),
            )


def test_task4_named_failure_enums_accept_exact_frozen_catalogs_only() -> None:
    core = _core_module()
    expected_catalogs = {
        "DynamicsCertificationFailure": (
            "prestructure_invalid",
            "transition_invalid",
            "reality_invalid",
            "laurent_resource_exceeded",
            "structure_raw_unresolved",
            "metric_raw_unresolved",
            "spectral_coverage_unresolved",
            "normalized_metric_unresolved",
            "full_state_bridge_failed",
            "power_drift_unresolved",
            "certified_instability_counterwitness",
        ),
        "EndpointReferenceFailure": (
            "phase_band_empty",
            "phase_band_nonunique",
            "rank_mismatch",
            "participation_failed",
            "runner_up_margin_failed",
            "projector_invalid",
        ),
        "EndpointShellFailure": (
            "phase_band_empty",
            "phase_separation_failed",
            "gap_failed",
            "participation_failed",
            "reference_ambiguous",
            "runner_up_margin",
            "loop_inconsistent",
            "projector_invalid",
        ),
        "PairedResponseFailure": (
            "qualification_invalid",
            "input_binding_invalid",
            "actual_response_failed",
            "ablated_response_failed",
            "actual_bridge_failed",
            "ablated_bridge_failed",
        ),
        "ControlCandidateFailure": (
            "reference_failed",
            "shell_failed",
            "response_failed",
            "bridge_failed",
        ),
    }
    schemas = core._record_schemas_v1()
    for wire_type, expected_values in expected_catalogs.items():
        for value in expected_values:
            core._validate_wire_value_v1(
                value,
                wire_type,
                None,
                f"failure.{wire_type}",
                schemas,
            )
        for hostile_value in (False, "caller-defined-failure"):
            with pytest.raises((TypeError, ValueError)):
                core._validate_wire_value_v1(
                    hostile_value,
                    wire_type,
                    None,
                    f"failure.{wire_type}",
                    schemas,
                )


def test_task4_normalizer_symbolic_grid_columns_are_nonempty_and_aligned() -> None:
    core = _core_module()
    normalizer = _task4_provenance_fixture()[
        "current_scenario_response_contract_v3_body"
    ]["current_readout_calibration_spec"]["curvature_normalizer_protocol"]
    assert (
        core._validate_record_raw_v1(
            normalizer,
            "CurrentCurvatureNormalizerProtocolV1",
            "normalizer",
            core._record_schemas_v1(),
        )
        == normalizer
    )
    for field in (
        "ordered_reciprocal_indices",
        "ordered_momentum_values",
        "ordered_momentum_fp64_bits",
        "ordered_normalizer_values",
        "ordered_normalizer_fp64_bits",
    ):
        hostile = _task4_clone(normalizer)
        hostile[field] = []
        _task4_resign_tree("CurrentCurvatureNormalizerProtocolV1", hostile)
        with pytest.raises((TypeError, ValueError)):
            core._validate_record_raw_v1(
                hostile,
                "CurrentCurvatureNormalizerProtocolV1",
                "normalizer",
                core._record_schemas_v1(),
            )


@pytest.mark.parametrize(
    "attack",
    (
        "unknown",
        "missing",
        "field_order",
        "type",
        "nullability",
        "enum",
        "self_hash",
        "nested_self_hash",
        "cross_branch_failure",
        "response_failure_presence",
        "bridge_failure_presence",
    ),
)
def test_task4_branch_attempt_rejects_schema_hash_and_branch_attacks(
    attack: str,
) -> None:
    core = _core_module()
    raw_body = _task4_branch_attempt()
    if attack == "unknown":
        raw_body["caller_unknown"] = False
    elif attack == "missing":
        del raw_body["failure"]
    elif attack == "field_order":
        raw_body = {key: raw_body[key] for key in reversed(tuple(raw_body))}
    elif attack == "type":
        raw_body["branch"] = 1
    elif attack == "nullability":
        raw_body["response_values"] = None
    elif attack == "enum":
        raw_body["branch"] = "caller_branch"
    elif attack == "self_hash":
        raw_body["attempt_sha"] = "f" * 64
    elif attack == "nested_self_hash":
        assert isinstance(raw_body["response_values"], dict)
        raw_body["response_values"]["tensor_sha"] = "f" * 64
        raw_body = _task4_seal(raw_body, "attempt_sha")
    elif attack == "cross_branch_failure":
        raw_body["failure"] = "matched_ablated_response_failed"
        raw_body["response_values"] = None
        raw_body = _task4_seal(raw_body, "attempt_sha")
    elif attack == "response_failure_presence":
        raw_body["failure"] = "actual_response_failed"
        raw_body = _task4_seal(raw_body, "attempt_sha")
    elif attack == "bridge_failure_presence":
        raw_body["failure"] = "actual_bridge_failed"
        raw_body["response_values"] = None
        raw_body = _task4_seal(raw_body, "attempt_sha")

    if attack == "field_order":
        assert core.validate_branch_attempt_v1(raw_body) == _task4_branch_attempt()
        return
    with pytest.raises((TypeError, ValueError)):
        core.validate_branch_attempt_v1(raw_body)


_TASK4_V6_PATH = (
    REPOSITORY_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-downstream-production-chain-2026-08-01.md"
)
_TASK4_V7_PATH = (
    REPOSITORY_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-prestructure-production-chain-v7-2026-08-02.md"
)
_TASK4_V8_PATH = (
    REPOSITORY_ROOT
    / "docsv3"
    / "v3-设计勘误-Parent-v3-B7至B10-production-chain-v8-2026-08-02.md"
)
_TASK4_EMBEDDED_MARKERS = (
    (
        _TASK4_V6_PATH,
        "<!-- BEGIN V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->",
        "<!-- END V3M0_DOWNSTREAM_CONTRACT_REGISTRY -->",
        "record_catalog",
    ),
    (
        _TASK4_V7_PATH,
        "<!-- BEGIN V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->",
        "<!-- END V3M0_PARENT_V3_PRESTRUCTURE_V7_REGISTRY -->",
        "record_catalog_delta",
    ),
    (
        _TASK4_V8_PATH,
        "<!-- BEGIN V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->",
        "<!-- END V3M0_PARENT_V3_B7_B10_V8_REGISTRY -->",
        "record_catalog_delta",
    ),
)
_TASK4_NON_SELF_HASHED_RECORDS = {
    "AblationReplacement",
    "CoefficientRecord",
    "DirectionPathClosure",
    "Fp64RootIntervalEntry",
    "FrozenSyntheticTarget",
    "Primitive",
    "PrimitiveInterface",
    "PrimitiveTrace",
    "ProvenanceNode",
    "SelectedControlEvidenceRef",
    "ShellCandidatePointAttempt",
    "ShellPointAudit",
    "SourceReadoutBridgeMatrixAudit",
    "TaggedScalarWire",
}
_TASK4_CATALOG_CACHE: dict[str, dict[str, object]] | None = None


def _task4_embedded_registry(
    path: Path,
    begin: str,
    end: str,
) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    payload = text.split(begin, 1)[1].split(end, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("\n```")
    value = json.loads(payload.removeprefix("```json\n").removesuffix("\n```"))
    assert type(value) is dict
    return value


def _task4_effective_catalog() -> dict[str, dict[str, object]]:
    global _TASK4_CATALOG_CACHE
    if _TASK4_CATALOG_CACHE is not None:
        return _TASK4_CATALOG_CACHE
    catalog: dict[str, dict[str, object]] = {}
    for path, begin, end, key in _TASK4_EMBEDDED_MARKERS:
        registry = _task4_embedded_registry(path, begin, end)
        delta = registry[key]
        assert type(delta) is dict
        catalog.update(delta)
    p0_delta = _registry()["p0_record_catalog_delta"]
    assert type(p0_delta) is dict
    catalog.update(p0_delta)
    _TASK4_CATALOG_CACHE = catalog
    return catalog


def _task4_split_top_level(value: str, delimiter: str) -> list[str]:
    result: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
        elif character == delimiter and depth == 0:
            result.append(value[start:index])
            start = index + 1
    result.append(value[start:])
    return result


def _task4_literal(token: str) -> object:
    if token == "true":
        return True
    if token == "false":
        return False
    if token.lstrip("-").isdigit():
        return int(token)
    return token


def _task4_minimal_wire(
    wire_type: str,
    nested_record: str | None,
    active: tuple[str, ...],
) -> object:
    if wire_type.startswith("Optional["):
        return None
    if nested_record is not None and wire_type.startswith("tuple["):
        body = wire_type[6:-1]
        parts = _task4_split_top_level(body, ";")
        modifiers = parts[1:]
        count = 0
        for modifier in modifiers:
            if modifier.startswith("exact=") and modifier[6:].isdigit():
                count = int(modifier[6:])
            elif modifier == "nonempty":
                count = max(count, 1)
        return [_task4_minimal_record(nested_record, active) for _ in range(count)]
    if nested_record is not None:
        nested = _task4_minimal_record(nested_record, active)
        if nested_record == "FrozenComplexTensor":
            shape = [1]
            if wire_type.startswith("FrozenComplexTensor["):
                dimensions = wire_type.removeprefix("FrozenComplexTensor[")[:-1]
                shape = [int(item) for item in dimensions.split("x")]
            nested["shape"] = shape
            nested["values_wire"] = [[0.0, 0.0] for _ in range(math.prod(shape))]
            nested = _task4_resign_record("FrozenComplexTensor", nested)
        return nested
    if wire_type.startswith("Literal["):
        return _task4_literal(_task4_split_top_level(wire_type[8:-1], ",")[0])
    if wire_type == "sha256":
        return "a" * 64
    if wire_type == "hex64":
        return "0" * 16
    if wire_type == "git-sha1":
        return "a" * 40
    if wire_type in {"str", "base64-be-f64-column"}:
        return "fixture-value"
    if wire_type == "UndefinedReason":
        return "response_null"
    if wire_type == "MechanismKind":
        return "target_blind"
    if wire_type == "ProvenanceOperation":
        return "derive"
    if wire_type == "bool":
        return False
    if wire_type == "int":
        return 1
    if wire_type in {"float", "float64"}:
        return 1.0
    if wire_type == "canonical-json-object":
        return {}
    if wire_type.startswith("tuple["):
        body = wire_type[6:-1]
        parts = _task4_split_top_level(body, ";")
        item_expression = parts[0]
        modifiers = parts[1:]
        count: int | None = None
        for modifier in modifiers:
            if modifier.startswith("exact=") and modifier[6:].isdigit():
                count = int(modifier[6:])
            elif modifier == "exact=response-grid-size":
                count = 1
            elif modifier == "nonempty":
                count = max(count or 0, 1)
        items = _task4_split_top_level(item_expression, ",")
        if items[-1] == "...":
            count = 0 if count is None else count
            item_types = [items[0]] * count
        elif len(items) == 1:
            count = 1 if count is None else count
            item_types = [items[0]] * count
        else:
            item_types = items
        result = [
            _task4_minimal_wire(item_type, None, active) for item_type in item_types
        ]
        for modifier in modifiers:
            if modifier.startswith("value="):
                expected = _task4_literal(modifier[6:])
                result = [expected for _ in result]
        return result
    return "fixture-enum"


def _task4_self_hash_field(record_name: str) -> str | None:
    if record_name in _TASK4_NON_SELF_HASHED_RECORDS:
        return None
    if record_name == "BasisManifest":
        return "manifest_id"
    record = _task4_effective_catalog()[record_name]
    fields = record["field_specs"]
    assert type(fields) is list and fields
    final = fields[-1]
    if final["wire_type"] == "sha256":
        return final["name"]
    return None


def _task4_resign_record(
    record_name: str,
    raw_body: dict[str, object],
) -> dict[str, object]:
    hash_field = _task4_self_hash_field(record_name)
    if hash_field is None:
        return raw_body
    return _task4_seal(raw_body, hash_field)


def _task4_minimal_record(
    record_name: str,
    active: tuple[str, ...] = (),
) -> dict[str, object]:
    assert record_name not in active, f"unbroken required cycle at {record_name}"
    if record_name == "BlockStatus":
        return {"defined": False, "reason": "response_null"}
    record = _task4_effective_catalog()[record_name]
    fields = record["field_specs"]
    assert type(fields) is list
    raw_body = {
        field["name"]: _task4_minimal_wire(
            field["wire_type"],
            field.get("nested_record"),
            (*active, record_name),
        )
        for field in fields
    }
    if record_name == "FrozenComplexTensor":
        raw_body["tensor_schema_version"] = "v3m0.frozen-complex-tensor.v1"
    elif record_name == "BasisManifest":
        raw_body["channel_order"] = ["q0"]
        raw_body["vectors_wire"] = [[[0.0, 0.0]]]
    return _task4_resign_record(record_name, raw_body)


def _task4_clone(value: object) -> object:
    return json.loads(
        json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    )


def _task4_resign_tree(record_name: str, raw_body: dict[str, object]) -> None:
    catalog = _task4_effective_catalog()
    for field in catalog[record_name]["field_specs"]:
        nested = field.get("nested_record")
        value = raw_body[field["name"]]
        if nested is None or value is None:
            continue
        if type(value) is list:
            for item in value:
                assert type(item) is dict
                _task4_resign_tree(nested, item)
        else:
            assert type(value) is dict
            _task4_resign_tree(nested, value)
    hash_field = _task4_self_hash_field(record_name)
    if hash_field is not None:
        raw_body[hash_field] = _task4_canonical_sha(
            {key: value for key, value in raw_body.items() if key != hash_field}
        )


def _task4_status(defined: bool) -> dict[str, object]:
    return {"defined": defined, "reason": None if defined else "response_null"}


def _task4_endpoint_reference_outcome() -> dict[str, object]:
    outcome = _task4_minimal_record("EndpointReferenceOutcome")
    spec = outcome["reference_spec"]
    attempt = outcome["attempt_audit"]
    assert type(spec) is dict and type(attempt) is dict
    reference = _task4_minimal_record("EndpointReferenceProjector")
    spec["reference_reciprocal_index"] = [0]
    spec["preregistered_phase_bands"] = [[0.1, 0.2]]
    spec["expected_shell_rank"] = 1
    _task4_resign_tree("EndpointReferenceSpec", spec)
    attempt["reference_spec"] = _task4_clone(spec)
    attempt["candidate_phases"] = [0.15]
    attempt["candidate_ranks"] = [1]
    attempt["expected_shell_rank"] = 1
    attempt["candidate_participations"] = [1.0]
    attempt["runner_up_overlaps"] = [None]
    attempt["hermitian_residuals"] = [0.0]
    attempt["idempotent_residuals"] = [0.0]
    attempt["g_invariance_residuals"] = [0.0]
    attempt["eigenphase_residuals"] = [0.0]
    attempt["observed_competitor_gaps"] = [None]
    _task4_resign_tree("EndpointReferenceAttemptAudit", attempt)
    reference["control_registry_entry_sha"] = spec["control_registry_entry"][
        "entry_sha"
    ]
    reference["actual_transition_sha"] = spec["actual_transition_sha"]
    reference["actual_dynamics_certificate_sha"] = spec[
        "actual_dynamics_certificate_sha"
    ]
    reference["reference_reciprocal_index"] = [0]
    reference["reference_phase"] = 0.15
    reference["rank"] = 1
    reference["projector"] = _task4_tensor([1, 1])
    _task4_resign_tree("EndpointReferenceProjector", reference)
    outcome["status"] = _task4_status(True)
    outcome["failure"] = None
    outcome["reference"] = reference
    _task4_resign_tree("EndpointReferenceOutcome", outcome)
    return outcome


def _task4_endpoint_shell_outcome() -> dict[str, object]:
    outcome = _task4_minimal_record("EndpointShellOutcome")
    reference_outcome = _task4_endpoint_reference_outcome()
    reference = reference_outcome["reference"]
    assert type(reference) is dict
    attempt = outcome["attempt_audit"]
    assert type(attempt) is dict
    shell_spec = attempt["shell_spec"]
    assert type(shell_spec) is dict
    shell_spec["endpoint_reference_projector"] = _task4_clone(reference)
    shell_spec["preregistered_phase_bands"] = [[0.1, 0.2]]
    shell_spec["candidate_fejer_order"] = 256
    _task4_resign_tree("EndpointShellSpec", shell_spec)
    attempt["point_attempts"] = []
    _task4_resign_tree("EndpointShellAttemptAudit", attempt)
    shell = _task4_minimal_record("EndpointShellManifest")
    shell["shell_spec"] = _task4_clone(shell_spec)
    shell["shell_phases"] = [0.15]
    shell["shell_projectors"] = _task4_tensor([1, 1, 1])
    shell["point_audits"] = [_task4_minimal_record("ShellPointAudit")]
    _task4_resign_tree("EndpointShellManifest", shell)
    outcome["status"] = _task4_status(True)
    outcome["failure"] = None
    outcome["reference_outcome"] = reference_outcome
    outcome["shell"] = shell
    _task4_resign_tree("EndpointShellOutcome", outcome)
    return outcome


def _task4_parent_body() -> dict[str, object]:
    parent = _task4_minimal_record("ParentFreezeV3Manifest")
    candidate = parent["reviewed_candidate_v3"]
    audit = parent["signing_audit"]
    assert type(candidate) is dict and type(audit) is dict
    parent["parent_freeze_schema_version"] = "v3m0.parent-freeze.v3"
    parent["preparation_commit_sha"] = "1" * 40
    parent["signing_commit_sha"] = "2" * 40
    candidate["candidate_schema_version"] = "v3m0.parent-freeze-candidate.v3"
    candidate["preparation_commit_sha"] = parent["preparation_commit_sha"]
    _task4_resign_tree("ParentFreezeCandidateV3Manifest", candidate)
    source_specs = (
        (
            "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md",
            "SIGNED_INCREMENTAL_ERRATUM",
            "C05_C18_SCENARIO_RESPONSE_GEOMETRY",
        ),
        (
            "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
            "SIGNED_CONSTRUCTION_ERRATUM",
            "C19_REAL20_REFREEZE_V2",
        ),
        (
            "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md",
            "SIGNED_ISSUANCE_PROTOCOL",
            "PARENT_V3_P_EPOCH_SIGNING",
        ),
        (
            "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
            "SIGNED_RUNTIME_AUTHORITY_PROTOCOL",
            "C19_METRIC_SUPPORT_AUTHORITY_V1",
        ),
    )
    references: list[dict[str, object]] = []
    for index, (path, role, scope) in enumerate(source_specs):
        reference = _task4_minimal_record("SignedSourceRefV2")
        reference.update(
            {
                "source_ref_schema_version": "v3m0.signed-source-ref.v2",
                "source_role": role,
                "source_scope": scope,
                "relative_path": path,
                "raw_sha256": f"{index + 1:x}" * 64,
                "preparation_commit_sha": parent["preparation_commit_sha"],
                "signing_commit_sha": parent["signing_commit_sha"],
            }
        )
        _task4_resign_tree("SignedSourceRefV2", reference)
        references.append(reference)
    parent["signed_source_refs"] = references

    closure = [["docsv3/fixture-reviewed.md", "9" * 64]]
    closure_root = _task4_canonical_sha(
        {
            "reviewed_path_closure_schema_version": (
                "v3m0.parent-reviewed-path-closure.v1"
            ),
            "entries": [
                {"relative_path": path, "raw_sha256": raw_sha}
                for path, raw_sha in closure
            ],
        }
    )
    receipts: list[dict[str, object]] = []
    signature_wire = b"SSHSIG" + bytes(range(64))
    signature_text = base64.b64encode(signature_wire).decode("ascii")
    signature_armor = (
        "-----BEGIN SSH SIGNATURE-----\n"
        + "\n".join(
            signature_text[index : index + 70]
            for index in range(0, len(signature_text), 70)
        )
        + "\n-----END SSH SIGNATURE-----\n"
    )
    for index, role in enumerate(
        (
            "MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW",
            "AUTHORITY_AND_BOUNDARY_REVIEW",
        )
    ):
        receipt = _task4_minimal_record("ParentReviewReceiptV1")
        receipt.update(
            {
                "receipt_schema_version": "v3m0.parent-review-receipt.v1",
                "review_role": role,
                "reviewer_id": f"fixture-reviewer-{index}",
                "reviewer_key_id": "SHA256:"
                + base64.b64encode(bytes([index]) * 32).decode("ascii").rstrip("="),
                "signature_algorithm": "openssh-ed25519-v1",
                "preparation_commit_sha": parent["preparation_commit_sha"],
                "reviewed_candidate_sha": candidate["candidate_sha"],
                "reviewed_path_closure": _task4_clone(closure),
                "reviewed_path_closure_sha": closure_root,
                "verdict": "PASS",
                "signature_armor": signature_armor,
            }
        )
        statement = {
            key: receipt[key]
            for key in (
                "receipt_schema_version",
                "review_role",
                "reviewer_id",
                "reviewer_key_id",
                "signature_algorithm",
                "preparation_commit_sha",
                "reviewed_candidate_sha",
                "reviewed_path_closure",
                "reviewed_path_closure_sha",
                "verdict",
            )
        }
        receipt["signed_statement_sha"] = _task4_canonical_sha(statement)
        _task4_resign_tree("ParentReviewReceiptV1", receipt)
        receipts.append(receipt)
    parent["review_receipts"] = receipts
    audit["audit_schema_version"] = "v3m0.parent-signing-audit.v1"
    audit["preparation_commit_sha"] = parent["preparation_commit_sha"]
    audit["signing_commit_sha"] = parent["signing_commit_sha"]
    audit["diff_allowlist_id"] = "parent-v3-signing-diff-v1"
    audit["review_receipt_shas"] = [item["receipt_sha"] for item in receipts]
    audit["signed_source_refs_root_sha"] = _task4_canonical_sha(
        {
            "signed_source_refs_schema_version": ("v3m0.signed-source-ref-tuple.v1"),
            "entries": references,
        }
    )
    audit["reviewed_candidate_sha"] = candidate["candidate_sha"]
    audit["reviewed_path_closure_sha"] = closure_root
    audit["source_closure_sha"] = candidate["source_closure_sha"]
    _task4_resign_tree("ParentSigningAuditV1", audit)
    _task4_resign_tree("ParentFreezeV3Manifest", parent)
    return parent


def _task4_resign_parent_receipts(parent: dict[str, object]) -> dict[str, object]:
    statement_fields = (
        "receipt_schema_version",
        "review_role",
        "reviewer_id",
        "reviewer_key_id",
        "signature_algorithm",
        "preparation_commit_sha",
        "reviewed_candidate_sha",
        "reviewed_path_closure",
        "reviewed_path_closure_sha",
        "verdict",
    )
    for receipt in parent["review_receipts"]:
        receipt["signed_statement_sha"] = _task4_canonical_sha(
            {field: receipt[field] for field in statement_fields}
        )
        _task4_resign_tree("ParentReviewReceiptV1", receipt)
    audit = parent["signing_audit"]
    audit["review_receipt_shas"] = [
        receipt["receipt_sha"] for receipt in parent["review_receipts"]
    ]
    _task4_resign_tree("ParentSigningAuditV1", audit)
    _task4_resign_tree("ParentFreezeV3Manifest", parent)
    return parent


def _task4_provenance_fixture() -> dict[str, object]:
    parent = _task4_parent_body()
    permit = _task4_minimal_record("CalibrationApplicationPermitV3")
    calibration = permit["calibration"]
    assert type(calibration) is dict
    calibration_outcome = calibration["calibration_outcome"]
    assert type(calibration_outcome) is dict
    selection = _task4_minimal_record("WindowThresholdSelection")
    selection["selected_fejer_order"] = 256
    _task4_resign_tree("WindowThresholdSelection", selection)
    calibration_outcome["status"] = _task4_status(True)
    calibration_outcome["selection"] = selection
    _task4_resign_tree("WindowCalibrationOutcome", calibration_outcome)
    permit["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
    permit["selected_fejer_order"] = 256
    contract = permit["current_scenario_response_contract"]
    assert type(contract) is dict
    response_grid = contract["response_grid"]
    assert type(response_grid) is dict
    response_grid["spatial_ndim"] = 1
    response_grid["torus_denominators"] = [8]
    response_grid["reciprocal_indices"] = [[1]]
    _task4_resign_tree("ResponseKGridManifest", response_grid)
    contract["response_reference_reciprocal_index"] = [1]
    contract["preregistered_phase_bands"] = [[1.4457963267948966, 1.6957963267948966]]
    contract["bridge_tolerance"] = 1e-12
    calibration_spec = contract["current_readout_calibration_spec"]
    assert type(calibration_spec) is dict
    calibration_spec["source_metric_whitener"] = _task4_tensor([10, 10])
    calibration_spec["h_metric_whitener"] = _task4_tensor([10, 10])
    calibration_spec["curvature_incidence_operator"] = _task4_tensor([6, 10])
    calibration_spec["curvature_metric_whitener"] = _task4_tensor([6, 6])
    normalizer = calibration_spec["curvature_normalizer_protocol"]
    assert type(normalizer) is dict
    normalizer["spatial_shape"] = [8]
    normalizer["response_grid_sha"] = response_grid["response_grid_sha"]
    normalizer["ordered_reciprocal_indices"] = [[1]]
    normalizer["ordered_momentum_values"] = [[math.pi / 4.0]]
    normalizer["ordered_momentum_fp64_bits"] = [["3fe921fb54442d18"]]
    normalizer["ordered_normalizer_values"] = [0.5857864376269049]
    normalizer["ordered_normalizer_fp64_bits"] = ["3fe2bec333018867"]
    _task4_resign_tree("CurrentCurvatureNormalizerProtocolV1", normalizer)
    geometry = contract["geometry_bundle"]
    assert type(geometry) is dict
    geometry["source_whitener"] = _task4_clone(
        calibration_spec["source_metric_whitener"]
    )
    geometry["h_whitener"] = _task4_clone(calibration_spec["h_metric_whitener"])
    geometry["incidence_q"] = _task4_clone(
        calibration_spec["curvature_incidence_operator"]
    )
    geometry["curvature_whitener"] = _task4_clone(
        calibration_spec["curvature_metric_whitener"]
    )
    _task4_resign_tree("C19ObserverGeometryBundleV1", geometry)
    calibration_spec["geometry_bundle_sha"] = geometry["geometry_bundle_sha"]
    _task4_resign_tree("CurrentReadoutCalibrationSpecV3", calibration_spec)
    _task4_resign_tree("CurrentScenarioResponseContractV3", contract)
    _task4_resign_tree("CalibrationApplicationPermitV3", permit)

    materialization = _task4_minimal_record("ApplicationScenarioMaterializationV3")
    materialization["permit"] = _task4_clone(permit)
    materialization["current_application_authority"] = _task4_clone(
        permit["current_application_authority"]
    )
    materialization["current_scenario_authority"] = _task4_clone(
        permit["current_scenario_authority"]
    )
    materialization["current_scenario_response_contract"] = _task4_clone(
        permit["current_scenario_response_contract"]
    )
    basis = materialization["basis_contract"]
    assert type(basis) is dict
    channels = [f"q{index}" for index in range(20)]
    basis["state_schema_id"] = "v3m0.c19-real-canonical-state.v2"
    basis["channel_order"] = channels
    for role, field in (
        ("source", "scenario_source_basis"),
        ("readout", "scenario_readout_basis"),
    ):
        basis_body = basis[field]
        assert type(basis_body) is dict
        basis_body["role"] = role
        basis_body["state_schema_id"] = basis["state_schema_id"]
        basis_body["channel_order"] = channels
        basis_body["vectors_wire"] = [[[0.0, 0.0] for _ in channels] for _ in range(10)]
        _task4_resign_tree("BasisManifest", basis_body)
    basis["source_injection"] = _task4_tensor([20, 10])
    basis["readout_coisometry"] = _task4_tensor([10, 20])
    basis["source_trial_vectors"] = _task4_tensor([10, 10])
    basis["expected_actual_shell_rank"] = 10
    basis["expected_matched_shell_rank"] = 10
    _task4_resign_tree("C19BasisContractV2", basis)
    _task4_resign_tree("ApplicationScenarioMaterializationV3", materialization)

    actual_bridge = _task4_minimal_record("BridgeGridAuthorityV3")
    actual_bridge["materialization"] = _task4_clone(materialization)
    actual_binding = actual_bridge["factory_binding"]
    assert type(actual_binding) is dict
    actual_binding["branch"] = "actual"
    _task4_resign_tree("FactoryBranchBindingV3", actual_binding)
    bridge_grid = actual_bridge["bridge_grid"]
    assert type(bridge_grid) is dict
    bridge_grid["spatial_shape"] = [8]
    bridge_grid["torus_denominators"] = [8]
    bridge_grid["reciprocal_indices"] = [[0]]
    _task4_resign_tree("BridgeKGridManifest", bridge_grid)
    _task4_resign_tree("BridgeGridAuthorityV3", actual_bridge)

    matched_bridge = _task4_clone(actual_bridge)
    assert type(matched_bridge) is dict
    matched_binding = matched_bridge["factory_binding"]
    assert type(matched_binding) is dict
    matched_binding["branch"] = "matched_ablated"
    _task4_resign_tree("FactoryBranchBindingV3", matched_binding)
    _task4_resign_tree("BridgeGridAuthorityV3", matched_bridge)

    fixture = {
        "provenance_fixture_schema_version": (
            "experimental.v3m0.b7.provenance-fixture.v1"
        ),
        "parent_freeze_v3_body": parent,
        "permit_body": permit,
        "materialization_body": materialization,
        "current_scenario_response_contract_v3_body": _task4_clone(
            permit["current_scenario_response_contract"]
        ),
        "actual_bridge_grid_authority_body": actual_bridge,
        "matched_ablated_bridge_grid_authority_body": matched_bridge,
        "provenance_fixture_sha": "0" * 64,
    }
    return _task4_seal(fixture, "provenance_fixture_sha")


def _task4_rebind_provenance_contract(
    fixture: dict[str, object],
    contract: dict[str, object],
) -> dict[str, object]:
    permit = fixture["permit_body"]
    permit["current_scenario_response_contract"] = _task4_clone(contract)
    permit["current_scenario_authority"]["response_contract"] = _task4_clone(contract)
    _task4_resign_tree(
        "CurrentScenarioAuthorityV3",
        permit["current_scenario_authority"],
    )
    _task4_resign_tree("CalibrationApplicationPermitV3", permit)
    materialization = fixture["materialization_body"]
    materialization["permit"] = _task4_clone(permit)
    materialization["current_application_authority"] = _task4_clone(
        permit["current_application_authority"]
    )
    materialization["current_scenario_authority"] = _task4_clone(
        permit["current_scenario_authority"]
    )
    materialization["current_scenario_response_contract"] = _task4_clone(contract)
    _task4_resign_tree("ApplicationScenarioMaterializationV3", materialization)
    fixture["current_scenario_response_contract_v3_body"] = _task4_clone(contract)
    for field in (
        "actual_bridge_grid_authority_body",
        "matched_ablated_bridge_grid_authority_body",
    ):
        fixture[field]["materialization"] = _task4_clone(materialization)
        _task4_resign_tree("BridgeGridAuthorityV3", fixture[field])
    return _task4_seal(fixture, "provenance_fixture_sha")


def _task4_component_wrapper(
    component_id: str,
    complete_body: dict[str, object],
) -> dict[str, object]:
    entry = next(
        item
        for item in _registry()["lab_contract"]["synthetic_component_registry"]
        if item["component_id"] == component_id
    )
    hash_field = entry["self_hash_field"]
    body = {
        "component_body_schema_version": (
            "experimental.v3m0.b7.synthetic-component-body.v1"
        ),
        "component_id": component_id,
        "body_type": entry["body_type"],
        "complete_body": complete_body,
        "body_raw_canonical_sha256": _task4_canonical_sha(complete_body),
        "body_self_hash_field": hash_field,
        "body_self_hash_value": complete_body[hash_field],
        "lineage_parent_component_ids": entry["lineage_parent_component_ids"],
        "fejer_order": 256,
        "component_sha": "0" * 64,
    }
    return _task4_seal(body, "component_sha")


def _task4_graph_manifest(
    provenance: dict[str, object],
) -> dict[str, object]:
    parent = provenance["parent_freeze_v3_body"]
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    matched_bridge = provenance["matched_ablated_bridge_grid_authority_body"]
    assert all(
        type(item) is dict
        for item in (parent, permit, materialization, actual_bridge, matched_bridge)
    )
    selection = permit["calibration"]["calibration_outcome"]["selection"]
    assert type(selection) is dict

    actual_transition = _task4_minimal_record("TransitionAuthorityV3")
    actual_transition["materialization"] = _task4_clone(materialization)
    actual_transition["factory_binding"]["branch"] = "actual"
    _task4_resign_tree("TransitionAuthorityV3", actual_transition)
    matched_transition = _task4_clone(actual_transition)
    assert type(matched_transition) is dict
    matched_transition["factory_binding"]["branch"] = "matched_ablated"
    _task4_resign_tree("TransitionAuthorityV3", matched_transition)

    actual_metric = _task4_minimal_record("MetricSignedSupportAttestationV1")
    actual_metric["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
    actual_metric["application_scenario_materialization_v3_sha"] = materialization[
        "materialization_sha"
    ]
    actual_metric["factory_role"] = "actual"
    _task4_resign_tree("MetricSignedSupportAttestationV1", actual_metric)
    matched_metric = _task4_clone(actual_metric)
    assert type(matched_metric) is dict
    matched_metric["factory_role"] = "matched_ablated"
    _task4_resign_tree("MetricSignedSupportAttestationV1", matched_metric)

    def certification(
        transition: dict[str, object],
        metric: dict[str, object],
        bridge: dict[str, object],
    ) -> dict[str, object]:
        certificate = _task4_minimal_record("DynamicsCertificateV3")
        certificate["parent_freeze_v3"] = _task4_clone(parent)
        certificate["materialization"] = _task4_clone(materialization)
        certificate["transition_authority"] = _task4_clone(transition)
        certificate["metric_attestation"] = _task4_clone(metric)
        certificate["bridge_grid_authority"] = _task4_clone(bridge)
        dynamics_grid = certificate["dynamics_grid_authority"]
        assert type(dynamics_grid) is dict
        dynamics_grid["transition_authority"] = _task4_clone(transition)
        dynamics_grid["metric_support_attestation"] = _task4_clone(metric)
        _task4_resign_tree("DynamicsGridAuthorityV3", dynamics_grid)
        bridge_spec = certificate["full_state_bridge_spec"]
        assert type(bridge_spec) is dict
        bridge_spec["bridge_grid"] = _task4_clone(bridge["bridge_grid"])
        bridge_spec["macro_steps"] = [1]
        bridge_spec["bridge_tolerance"] = permit["current_scenario_response_contract"][
            "bridge_tolerance"
        ]
        _task4_resign_tree("FullStateBridgeSpec", bridge_spec)
        _task4_resign_tree("DynamicsCertificateV3", certificate)
        outcome = _task4_minimal_record("DynamicsCertificationOutcomeV3")
        attempt = outcome["attempt_audit"]
        assert type(attempt) is dict
        attempt["parent_freeze_v3_sha"] = parent["parent_freeze_v3_sha"]
        attempt["materialization_sha"] = materialization["materialization_sha"]
        attempt["transition_authority_sha"] = transition["transition_authority_sha"]
        attempt["metric_attestation_sha"] = metric["attestation_sha"]
        attempt["bridge_grid_authority_sha"] = bridge["grid_authority_sha"]
        attempt["first_failure"] = None
        _task4_resign_tree("DynamicsCertificationAttemptAuditV3", attempt)
        outcome["status"] = _task4_status(True)
        outcome["failure"] = None
        outcome["certificate"] = certificate
        _task4_resign_tree("DynamicsCertificationOutcomeV3", outcome)
        return outcome

    actual_certificate = certification(actual_transition, actual_metric, actual_bridge)
    matched_certificate = certification(
        matched_transition,
        matched_metric,
        matched_bridge,
    )
    complete_bodies = {
        "calibration_selection": selection,
        "permit": permit,
        "materialization": materialization,
        "actual_transition_outcome": actual_transition,
        "matched_ablated_transition_outcome": matched_transition,
        "actual_metric_authority": actual_metric,
        "matched_ablated_metric_authority": matched_metric,
        "actual_bridge_grid_authority": actual_bridge,
        "matched_ablated_bridge_grid_authority": matched_bridge,
        "actual_certificate_outcome": actual_certificate,
        "matched_ablated_certificate_outcome": matched_certificate,
    }
    component_order = _registry()["lab_contract"]["synthetic_graph_contract"][
        "component_order"
    ]
    components = [
        _task4_component_wrapper(component_id, complete_bodies[component_id])
        for component_id in component_order
    ]
    root_entries = [
        {
            "component_id": component["component_id"],
            "body_self_hash_value": component["body_self_hash_value"],
        }
        for component in components
    ]
    bindings = [
        _task4_seal(
            {
                "binding_schema_version": ("experimental.v3m0.b7.t-bearer-binding.v1"),
                "component_id": component["component_id"],
                "body_sha": component["body_self_hash_value"],
                "fejer_order": 256,
                "binding_sha": "0" * 64,
            },
            "binding_sha",
        )
        for component in components
    ]
    by_id = {component["component_id"]: component for component in components}
    graph = {
        "graph_manifest_schema_version": (
            "experimental.v3m0.b7.synthetic-graph-manifest.v1"
        ),
        "graph_profile_id": ("v3m0-b7-d1-nonauthority-synthetic-private-graph-v1"),
        "authority_state": "NON_AUTHORITY_SYNTHETIC",
        "parent_freeze_v3_body": _task4_clone(parent),
        "parent_freeze_v3_sha": parent["parent_freeze_v3_sha"],
        "synthetic_graph_component_root_sha": _task4_canonical_sha(root_entries),
        "selected_fejer_order": 256,
        "calibration_selection_sha": by_id["calibration_selection"][
            "body_self_hash_value"
        ],
        "permit_sha": by_id["permit"]["body_self_hash_value"],
        "permit_fejer_order": 256,
        "materialization_sha": by_id["materialization"]["body_self_hash_value"],
        "materialization_fejer_order": 256,
        "actual_transition_outcome_sha": by_id["actual_transition_outcome"][
            "body_self_hash_value"
        ],
        "matched_ablated_transition_outcome_sha": by_id[
            "matched_ablated_transition_outcome"
        ]["body_self_hash_value"],
        "actual_metric_authority_sha": by_id["actual_metric_authority"][
            "body_self_hash_value"
        ],
        "matched_ablated_metric_authority_sha": by_id[
            "matched_ablated_metric_authority"
        ]["body_self_hash_value"],
        "actual_bridge_grid_authority_sha": by_id["actual_bridge_grid_authority"][
            "body_self_hash_value"
        ],
        "matched_ablated_bridge_grid_authority_sha": by_id[
            "matched_ablated_bridge_grid_authority"
        ]["body_self_hash_value"],
        "actual_certificate_outcome_sha": by_id["actual_certificate_outcome"][
            "body_self_hash_value"
        ],
        "matched_ablated_certificate_outcome_sha": by_id[
            "matched_ablated_certificate_outcome"
        ]["body_self_hash_value"],
        "ordered_component_bodies": components,
        "ordered_t_bearer_bindings": bindings,
        "graph_sha": "0" * 64,
    }
    return _task4_seal(graph, "graph_sha")


def _task4_response_run_spec(
    provenance: dict[str, object],
    graph: dict[str, object],
) -> dict[str, object]:
    spec = _task4_minimal_record("ResponseRunSpecV3")
    parent = provenance["parent_freeze_v3_body"]
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    contract = provenance["current_scenario_response_contract_v3_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    assert all(
        type(item) is dict
        for item in (parent, permit, materialization, contract, actual_bridge)
    )
    calibration = permit["calibration"]
    outcome = calibration["calibration_outcome"]
    selection = outcome["selection"]
    window_protocol = outcome["manifest"]["window_protocol"]
    basis = materialization["basis_contract"]
    assert all(
        type(item) is dict
        for item in (calibration, outcome, selection, window_protocol, basis)
    )
    spec.update(
        {
            "parent_freeze_v3_sha": parent["parent_freeze_v3_sha"],
            "permit_sha": permit["permit_sha"],
            "materialization_sha": materialization["materialization_sha"],
            "window_calibration_v3_sha": calibration["calibration_v3_sha"],
            "window_protocol_sha": window_protocol["protocol_sha"],
            "window_selection_sha": selection["selection_sha"],
            "current_scenario_response_contract_v3_sha": contract[
                "response_contract_sha"
            ],
            "application_instance_id": contract["application_instance_id"],
            "scenario_id": contract["scenario_id"],
            "scenario_sha": permit["current_scenario_authority"][
                "scenario_authority_sha"
            ],
            "selected_fejer_order": 256,
            "channel_order": list(basis["channel_order"]),
            "spatial_shape": [8],
            "source_basis": _task4_clone(basis["scenario_source_basis"]),
            "readout_basis": _task4_clone(basis["scenario_readout_basis"]),
            "source_injection_isometry": _task4_clone(basis["source_injection"]),
            "readout_coisometry": _task4_clone(basis["readout_coisometry"]),
            "response_grid": _task4_clone(contract["response_grid"]),
            "source_readout_bridge_grid": _task4_clone(actual_bridge["bridge_grid"]),
            "source_readout_bridge_steps": [1],
            "reference_reciprocal_index": list(
                contract["response_reference_reciprocal_index"]
            ),
            "preregistered_phase_bands": _task4_clone(
                contract["preregistered_phase_bands"]
            ),
            "expected_shell_rank": 10,
            "source_trial_vectors": _task4_clone(basis["source_trial_vectors"]),
            "bridge_tolerance": contract["bridge_tolerance"],
            "current_readout_calibration_spec": _task4_clone(
                contract["current_readout_calibration_spec"]
            ),
            "actual_bridge_grid_authority_sha": graph[
                "actual_bridge_grid_authority_sha"
            ],
            "matched_ablated_bridge_grid_authority_sha": graph[
                "matched_ablated_bridge_grid_authority_sha"
            ],
        }
    )
    channels = [f"q{index}" for index in range(20)]
    spec["channel_order"] = channels
    for role, field in (("source", "source_basis"), ("readout", "readout_basis")):
        basis_body = spec[field]
        assert type(basis_body) is dict
        basis_body["role"] = role
        basis_body["state_schema_id"] = spec["state_schema_id"]
        basis_body["channel_order"] = channels
        basis_body["vectors_wire"] = [[[0.0, 0.0] for _ in channels] for _ in range(10)]
        _task4_resign_tree("BasisManifest", basis_body)
    spec["source_injection_isometry"] = _task4_tensor([20, 10])
    spec["readout_coisometry"] = _task4_tensor([10, 20])
    spec["source_trial_vectors"] = _task4_tensor([10, 10])
    _task4_resign_tree("ResponseRunSpecV3", spec)
    return spec


def _task4_component_by_id(
    graph: dict[str, object],
    component_id: str,
) -> dict[str, object]:
    return next(
        component
        for component in graph["ordered_component_bodies"]
        if component["component_id"] == component_id
    )


def _task4_source_response(
    branch: str,
    run_spec: dict[str, object],
    graph: dict[str, object],
) -> dict[str, object]:
    response = _task4_minimal_record("SourceReadoutResponse")
    prefix = "actual" if branch == "actual" else "matched_ablated"
    transition = _task4_component_by_id(
        graph,
        f"{prefix}_transition_outcome",
    )["complete_body"]
    certificate_outcome = _task4_component_by_id(
        graph,
        f"{prefix}_certificate_outcome",
    )["complete_body"]
    assert type(transition) is dict and type(certificate_outcome) is dict
    certificate = certificate_outcome["certificate"]
    assert type(certificate) is dict
    factory_sha = transition["factory_binding"]["factory"]["factory_sha"]
    transition_sha = transition["measured_transition"]["transition_sha"]
    certificate_sha = certificate["certificate_sha"]
    response.update(
        {
            "branch": branch,
            "factory_sha": factory_sha,
            "transition_sha": transition_sha,
            "dynamics_certificate_sha": certificate_sha,
            "source_basis": _task4_clone(run_spec["source_basis"]),
            "readout_basis": _task4_clone(run_spec["readout_basis"]),
            "run_spec_sha": run_spec["run_spec_sha"],
        }
    )
    bridge = response["bridge_audit"]
    assert type(bridge) is dict
    bridge.update(
        {
            "branch": branch,
            "factory_sha": factory_sha,
            "transition_sha": transition_sha,
            "dynamics_certificate_sha": certificate_sha,
            "run_spec_sha": run_spec["run_spec_sha"],
            "source_metric_whitener_sha": run_spec["current_readout_calibration_spec"][
                "source_metric_whitener"
            ]["tensor_sha"],
            "readout_calibration_spec_sha": run_spec[
                "current_readout_calibration_spec"
            ]["spec_sha"],
        }
    )
    matrix = _task4_minimal_record("SourceReadoutBridgeMatrixAudit")
    matrix["reciprocal_index"] = [0]
    matrix["macro_steps"] = 1
    matrix["raw_difference_matrix"] = _task4_tensor([10, 10])
    bridge["matrix_audits"] = [matrix]
    _task4_resign_tree("SourceReadoutBridgeAudit", bridge)
    response["values"] = _task4_tensor([1, 10, 10])
    _task4_resign_tree("SourceReadoutResponse", response)
    return response


def test_task4_embedded_schema_literals_recompute_from_pinned_registries() -> None:
    core = _core_module()
    catalog = _task4_effective_catalog()
    roots = [
        "ParentFreezeV3Manifest",
        "WindowThresholdSelection",
        "CalibrationApplicationPermitV3",
        "ApplicationScenarioMaterializationV3",
        "TransitionAuthorityV3",
        "MetricSignedSupportAttestationV1",
        "BridgeGridAuthorityV3",
        "DynamicsCertificationOutcomeV3",
        "ResponseRunSpecV3",
        "EndpointReferenceOutcome",
        "EndpointShellOutcome",
        "SourceReadoutResponse",
        "CurrentScenarioResponseContractV3",
    ]
    closure: set[str] = set()
    pending = list(roots)
    while pending:
        record_name = pending.pop()
        if record_name in closure:
            continue
        closure.add(record_name)
        for field in catalog[record_name]["field_specs"]:
            nested = field.get("nested_record")
            if nested is not None:
                pending.append(nested)
    expected_schemas: dict[str, object] = {}
    for record_name in sorted(closure):
        fields = catalog[record_name]["field_specs"]
        hash_field = _task4_self_hash_field(record_name)
        expected_schemas[record_name] = [
            hash_field,
            [
                [field["name"], field["wire_type"], field.get("nested_record")]
                for field in fields
            ],
        ]
    assert json.loads(core._B7_RECORD_SCHEMAS_JSON_V1) == expected_schemas

    expected_components = [
        [
            entry["component_id"],
            entry["body_type"],
            entry["body_type"].rsplit(".", 1)[1],
            entry["self_hash_field"],
            entry["lineage_parent_component_ids"],
            entry["lineage_bindings"],
            entry["required_body_predicates"],
            entry["t_derivation"],
        ]
        for entry in _registry()["lab_contract"]["synthetic_component_registry"]
    ]
    assert json.loads(core._B7_COMPONENT_CONTRACTS_JSON_V1) == expected_components


def test_task4_branch_attempt_strictly_validates_present_bridge_raw_tree() -> None:
    core = _core_module()
    raw = _task4_branch_attempt()
    bridge = _task4_minimal_record("SourceReadoutBridgeAudit")
    bridge["branch"] = "actual"
    matrix = _task4_minimal_record("SourceReadoutBridgeMatrixAudit")
    matrix["reciprocal_index"] = [0]
    matrix["macro_steps"] = 1
    matrix["raw_difference_matrix"] = _task4_tensor([1, 1])
    bridge["matrix_audits"] = [matrix]
    _task4_resign_tree("SourceReadoutBridgeAudit", bridge)
    raw["bridge_audit"] = bridge
    raw = _task4_seal(raw, "attempt_sha")
    assert core.validate_branch_attempt_v1(raw) == raw

    hostile = _task4_clone(raw)
    assert type(hostile) is dict
    hostile["bridge_audit"]["bridge_sha"] = "f" * 64
    hostile = _task4_seal(hostile, "attempt_sha")
    with pytest.raises((TypeError, ValueError)):
        core.validate_branch_attempt_v1(hostile)


def test_task4_endpoint_reference_validator_covers_legal_and_hostile_raw_trees() -> (
    None
):
    core = _core_module()
    legal = _task4_endpoint_reference_outcome()
    assert core.validate_endpoint_reference_outcome_raw_v1(legal) == legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "status_presence",
        "attempt_spec_splice",
        "reference_binding_splice",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["failure"] = 1
        elif attack == "self_hash":
            raw["outcome_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["reference_spec"]["reference_spec_sha"] = "f" * 64
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "status_presence":
            raw["status"] = _task4_status(False)
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "attempt_spec_splice":
            raw["attempt_audit"]["reference_spec"]["actual_factory_sha"] = "f" * 64
            _task4_resign_tree(
                "EndpointReferenceAttemptAudit",
                raw["attempt_audit"],
            )
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "reference_binding_splice":
            raw["reference"]["actual_transition_sha"] = "f" * 64
            _task4_resign_tree("EndpointReferenceProjector", raw["reference"])
            raw = _task4_seal(raw, "outcome_sha")
        if attack == "field_order":
            assert core.validate_endpoint_reference_outcome_raw_v1(raw) == legal
            continue
        with pytest.raises((TypeError, ValueError)):
            core.validate_endpoint_reference_outcome_raw_v1(raw)


def test_task4_endpoint_shell_validator_covers_legal_and_hostile_raw_trees() -> None:
    core = _core_module()
    legal = _task4_endpoint_shell_outcome()
    assert core.validate_endpoint_shell_outcome_raw_v1(legal) == legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "status_presence",
        "attempt_shell_spec_splice",
        "shell_reference_splice",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["failure"] = 1
        elif attack == "self_hash":
            raw["outcome_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["attempt_audit"]["attempt_sha"] = "f" * 64
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "status_presence":
            raw["status"] = _task4_status(False)
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "attempt_shell_spec_splice":
            raw["attempt_audit"]["shell_spec"]["candidate_fejer_order"] = 128
            _task4_resign_tree("EndpointShellAttemptAudit", raw["attempt_audit"])
            raw = _task4_seal(raw, "outcome_sha")
        elif attack == "shell_reference_splice":
            raw["shell"]["shell_spec"]["endpoint_reference_projector"][
                "actual_transition_sha"
            ] = "f" * 64
            _task4_resign_tree("EndpointShellManifest", raw["shell"])
            raw = _task4_seal(raw, "outcome_sha")
        if attack == "field_order":
            assert core.validate_endpoint_shell_outcome_raw_v1(raw) == legal
            continue
        with pytest.raises((TypeError, ValueError)):
            core.validate_endpoint_shell_outcome_raw_v1(raw)


def test_task4_synthetic_parent_validator_covers_recursive_and_join_attacks() -> None:
    core = _core_module()
    legal = _task4_parent_body()
    assert core.validate_synthetic_parent_freeze_v3_body_v1(legal) == legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "candidate_preparation_join",
        "audit_signing_join",
        "audit_candidate_join",
        "source_ref_commit_join",
        "signed_source_root",
        "receipt_statement_root",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["authority_state"] = 1
        elif attack == "self_hash":
            raw["parent_freeze_v3_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["reviewed_candidate_v3"]["candidate_sha"] = "f" * 64
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "candidate_preparation_join":
            raw["reviewed_candidate_v3"]["preparation_commit_sha"] = "3" * 40
            _task4_resign_tree(
                "ParentFreezeCandidateV3Manifest",
                raw["reviewed_candidate_v3"],
            )
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "audit_signing_join":
            raw["signing_audit"]["signing_commit_sha"] = "3" * 40
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "audit_candidate_join":
            raw["signing_audit"]["reviewed_candidate_sha"] = "f" * 64
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "source_ref_commit_join":
            raw["signed_source_refs"][0]["signing_commit_sha"] = "3" * 40
            _task4_resign_tree("SignedSourceRefV2", raw["signed_source_refs"][0])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "signed_source_root":
            raw["signing_audit"]["signed_source_refs_root_sha"] = "f" * 64
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        elif attack == "receipt_statement_root":
            receipt = raw["review_receipts"][0]
            receipt["signed_statement_sha"] = "f" * 64
            _task4_resign_tree("ParentReviewReceiptV1", receipt)
            raw["signing_audit"]["review_receipt_shas"][0] = receipt["receipt_sha"]
            _task4_resign_tree("ParentSigningAuditV1", raw["signing_audit"])
            raw = _task4_seal(raw, "parent_freeze_v3_sha")
        if attack == "field_order":
            assert core.validate_synthetic_parent_freeze_v3_body_v1(raw) == legal
            continue
        with pytest.raises((TypeError, ValueError)):
            core.validate_synthetic_parent_freeze_v3_body_v1(raw)


@pytest.mark.parametrize(
    "attack",
    (
        "fingerprint",
        "signature_armor",
        "short_signature",
        "empty_reviewer",
        "duplicate_reviewer",
        "duplicate_key",
    ),
)
def test_task4_parent_receipts_match_production_structural_contract(
    attack: str,
) -> None:
    core = _core_module()
    hostile = _task4_parent_body()
    receipts = hostile["review_receipts"]
    if attack == "fingerprint":
        receipts[0]["reviewer_key_id"] = "SHA256:" + "!" * 43
    elif attack == "signature_armor":
        receipts[0]["signature_armor"] = (
            "-----BEGIN SSH SIGNATURE-----\nfixture\n-----END SSH SIGNATURE-----"
        )
    elif attack == "short_signature":
        receipts[0]["signature_armor"] = (
            "-----BEGIN SSH SIGNATURE-----\nU1NIU0lH\n-----END SSH SIGNATURE-----\n"
        )
    elif attack == "empty_reviewer":
        receipts[0]["reviewer_id"] = ""
    elif attack == "duplicate_reviewer":
        receipts[1]["reviewer_id"] = receipts[0]["reviewer_id"]
    elif attack == "duplicate_key":
        receipts[1]["reviewer_key_id"] = receipts[0]["reviewer_key_id"]
    hostile = _task4_resign_parent_receipts(hostile)

    with pytest.raises((TypeError, ValueError)):
        core.validate_synthetic_parent_freeze_v3_body_v1(hostile)


def test_task4_provenance_validator_covers_recursive_and_lineage_attacks() -> None:
    core = _core_module()
    legal = _task4_provenance_fixture()
    assert core.validate_provenance_fixture_v1(legal) == legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "permit_parent_join",
        "materialization_permit_join",
        "current_contract_join",
        "bridge_identity",
        "bridge_grid_join",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["permit_body"] = []
        elif attack == "self_hash":
            raw["provenance_fixture_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["permit_body"]["permit_sha"] = "f" * 64
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "permit_parent_join":
            raw["permit_body"]["parent_freeze_v3_sha"] = "f" * 64
            _task4_resign_tree("CalibrationApplicationPermitV3", raw["permit_body"])
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "materialization_permit_join":
            raw["materialization_body"]["permit"]["permit_scope_id"] = "splice"
            _task4_resign_tree(
                "ApplicationScenarioMaterializationV3",
                raw["materialization_body"],
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "current_contract_join":
            raw["current_scenario_response_contract_v3_body"][
                "application_instance_id"
            ] = "splice"
            _task4_resign_tree(
                "CurrentScenarioResponseContractV3",
                raw["current_scenario_response_contract_v3_body"],
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "bridge_identity":
            raw["matched_ablated_bridge_grid_authority_body"] = _task4_clone(
                raw["actual_bridge_grid_authority_body"]
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        elif attack == "bridge_grid_join":
            raw["matched_ablated_bridge_grid_authority_body"]["bridge_grid"][
                "reciprocal_indices"
            ] = [[1]]
            _task4_resign_tree(
                "BridgeGridAuthorityV3",
                raw["matched_ablated_bridge_grid_authority_body"],
            )
            raw = _task4_seal(raw, "provenance_fixture_sha")
        if attack == "field_order":
            assert core.validate_provenance_fixture_v1(raw) == legal
            continue
        with pytest.raises((TypeError, ValueError)):
            core.validate_provenance_fixture_v1(raw)


def test_task4_provenance_rejects_resigned_b5_branch_role_swap() -> None:
    core = _core_module()
    hostile = _task4_provenance_fixture()
    actual = hostile["actual_bridge_grid_authority_body"]
    matched = hostile["matched_ablated_bridge_grid_authority_body"]
    actual["factory_binding"]["branch"] = "matched_ablated"
    matched["factory_binding"]["branch"] = "actual"
    _task4_resign_tree("BridgeGridAuthorityV3", actual)
    _task4_resign_tree("BridgeGridAuthorityV3", matched)
    hostile = _task4_seal(hostile, "provenance_fixture_sha")

    with pytest.raises((TypeError, ValueError)):
        core.validate_provenance_fixture_v1(hostile)


def test_task4_provenance_positive_matches_frozen_p0_oracle() -> None:
    core = _core_module()
    fixture = _task4_provenance_fixture()

    assert core.validate_provenance_fixture_v1(fixture) == fixture
    contract = fixture["current_scenario_response_contract_v3_body"]
    response_grid = contract["response_grid"]
    normalizer = contract["current_readout_calibration_spec"][
        "curvature_normalizer_protocol"
    ]
    geometry = contract["geometry_bundle"]
    geometry_fields = tuple(
        field["name"]
        for field in _task4_effective_catalog()["C19ObserverGeometryBundleV1"][
            "field_specs"
        ]
    )

    assert response_grid["torus_denominators"] == [8]
    assert response_grid["reciprocal_indices"] == [[1]]
    assert contract["response_reference_reciprocal_index"] == [1]
    assert contract["preregistered_phase_bands"] == [
        [1.4457963267948966, 1.6957963267948966]
    ]
    assert contract["bridge_tolerance"] == 1e-12
    assert normalizer["ordered_momentum_fp64_bits"] == [["3fe921fb54442d18"]]
    assert normalizer["ordered_normalizer_fp64_bits"] == ["3fe2bec333018867"]
    assert len(geometry_fields) == 50
    assert tuple(geometry) == geometry_fields


def test_task4_provenance_binds_normalizer_cardinality_to_response_grid() -> None:
    core = _core_module()
    hostile = _task4_provenance_fixture()
    contract = hostile["current_scenario_response_contract_v3_body"]
    response_grid = contract["response_grid"]
    response_grid["reciprocal_indices"] = [[1], [2]]
    _task4_resign_tree("ResponseKGridManifest", response_grid)
    _task4_resign_tree("CurrentScenarioResponseContractV3", contract)
    hostile = _task4_rebind_provenance_contract(hostile, contract)

    with pytest.raises((TypeError, ValueError)):
        core.validate_provenance_fixture_v1(hostile)


def test_task4_synthetic_component_validator_covers_metadata_body_and_t() -> None:
    core = _core_module()
    parent = _task4_parent_body()
    selection = _task4_minimal_record("WindowThresholdSelection")
    selection["selected_fejer_order"] = 256
    _task4_resign_tree("WindowThresholdSelection", selection)
    legal = _task4_component_wrapper("calibration_selection", selection)
    ordered = [legal]
    assert core.validate_synthetic_component_body_v1(legal, ordered, parent) == legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "body_type",
        "raw_sha",
        "self_hash_field",
        "lineage",
        "fejer_order",
        "duplicate_order",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["component_id"] = 1
        elif attack == "self_hash":
            raw["component_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["complete_body"]["selection_sha"] = "f" * 64
            raw["body_raw_canonical_sha256"] = _task4_canonical_sha(
                raw["complete_body"]
            )
            raw["body_self_hash_value"] = "f" * 64
            raw = _task4_seal(raw, "component_sha")
        elif attack == "body_type":
            raw["body_type"] = "caller.Type"
            raw = _task4_seal(raw, "component_sha")
        elif attack == "raw_sha":
            raw["body_raw_canonical_sha256"] = "f" * 64
            raw = _task4_seal(raw, "component_sha")
        elif attack == "self_hash_field":
            raw["body_self_hash_field"] = "caller_sha"
            raw = _task4_seal(raw, "component_sha")
        elif attack == "lineage":
            raw["lineage_parent_component_ids"] = ["permit"]
            raw = _task4_seal(raw, "component_sha")
        elif attack == "fejer_order":
            raw["fejer_order"] = 128
            raw = _task4_seal(raw, "component_sha")
        elif attack == "duplicate_order":
            pass
        ordered_attack = (
            [raw, _task4_clone(raw)] if attack == "duplicate_order" else [raw]
        )
        if attack == "field_order":
            assert (
                core.validate_synthetic_component_body_v1(
                    raw,
                    ordered_attack,
                    parent,
                )
                == legal
            )
            continue
        with pytest.raises((TypeError, ValueError)):
            core.validate_synthetic_component_body_v1(raw, ordered_attack, parent)


def test_task4_all_eleven_synthetic_components_validate_in_frozen_order() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    ordered = graph["ordered_component_bodies"]
    parent = provenance["parent_freeze_v3_body"]
    expected_order = _registry()["lab_contract"]["synthetic_graph_contract"][
        "component_order"
    ]
    assert [item["component_id"] for item in ordered] == expected_order
    for component in ordered:
        assert (
            core.validate_synthetic_component_body_v1(component, ordered, parent)
            == component
        )


def test_task4_standalone_component_recursively_validates_lineage_wrappers() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    hostile_order = _task4_clone(graph["ordered_component_bodies"])
    child = next(
        item for item in hostile_order if item["component_id"] == "materialization"
    )
    permit = next(item for item in hostile_order if item["component_id"] == "permit")
    permit["component_sha"] = "f" * 64

    with pytest.raises((TypeError, ValueError)):
        core.validate_synthetic_component_body_v1(
            child,
            hostile_order,
            provenance["parent_freeze_v3_body"],
        )


def test_task4_response_run_spec_validator_covers_external_join_attacks() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    legal = _task4_response_run_spec(provenance, graph)
    assert core.validate_response_run_spec_fixture_v1(legal, provenance, graph) == legal

    for attack in (
        "unknown",
        "field_order",
        "type",
        "self_hash",
        "nested_self_hash",
        "parent_join",
        "permit_join",
        "materialization_join",
        "contract_join",
        "t_join",
        "basis_rank",
        "bridge_grid_join",
        "bridge_authority_join",
    ):
        raw = _task4_clone(legal)
        assert type(raw) is dict
        if attack == "unknown":
            raw["caller_unknown"] = False
        elif attack == "field_order":
            raw = {key: raw[key] for key in reversed(tuple(raw))}
        elif attack == "type":
            raw["selected_fejer_order"] = 256.0
        elif attack == "self_hash":
            raw["run_spec_sha"] = "f" * 64
        elif attack == "nested_self_hash":
            raw["source_basis"]["manifest_id"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "parent_join":
            raw["parent_freeze_v3_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "permit_join":
            raw["permit_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "materialization_join":
            raw["materialization_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "contract_join":
            raw["current_scenario_response_contract_v3_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "t_join":
            raw["selected_fejer_order"] = 128
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "basis_rank":
            raw["source_basis"]["vectors_wire"] = raw["source_basis"]["vectors_wire"][
                :-1
            ]
            _task4_resign_tree("BasisManifest", raw["source_basis"])
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "bridge_grid_join":
            raw["source_readout_bridge_grid"]["reciprocal_indices"] = [[1]]
            _task4_resign_tree(
                "BridgeKGridManifest",
                raw["source_readout_bridge_grid"],
            )
            raw = _task4_seal(raw, "run_spec_sha")
        elif attack == "bridge_authority_join":
            raw["actual_bridge_grid_authority_sha"] = "f" * 64
            raw = _task4_seal(raw, "run_spec_sha")
        if attack == "field_order":
            assert (
                core.validate_response_run_spec_fixture_v1(raw, provenance, graph)
                == legal
            )
            continue
        with pytest.raises((TypeError, ValueError)):
            core.validate_response_run_spec_fixture_v1(raw, provenance, graph)

    hostile_graph = _task4_clone(graph)
    assert type(hostile_graph) is dict
    hostile_components = hostile_graph["ordered_component_bodies"]
    assert type(hostile_components) is list
    hostile_transition = next(
        item
        for item in hostile_components
        if item["component_id"] == "actual_transition_outcome"
    )
    hostile_transition_body = hostile_transition["complete_body"]
    hostile_transition_body["materialization"]["current_application_authority"][
        "application_instance_id"
    ] = "hostile-lineage"
    _task4_resign_tree("TransitionAuthorityV3", hostile_transition_body)
    hostile_transition["body_raw_canonical_sha256"] = _task4_canonical_sha(
        hostile_transition_body
    )
    hostile_transition["body_self_hash_value"] = hostile_transition_body[
        "transition_authority_sha"
    ]
    hostile_transition = _task4_seal(hostile_transition, "component_sha")
    hostile_index = next(
        index
        for index, item in enumerate(hostile_components)
        if item["component_id"] == "actual_transition_outcome"
    )
    hostile_components[hostile_index] = hostile_transition
    hostile_graph["actual_transition_outcome_sha"] = hostile_transition[
        "body_self_hash_value"
    ]
    hostile_binding = hostile_graph["ordered_t_bearer_bindings"][hostile_index]
    hostile_binding["body_sha"] = hostile_transition["body_self_hash_value"]
    hostile_graph["ordered_t_bearer_bindings"][hostile_index] = _task4_seal(
        hostile_binding,
        "binding_sha",
    )
    hostile_graph["synthetic_graph_component_root_sha"] = _task4_canonical_sha(
        [
            {
                "component_id": item["component_id"],
                "body_self_hash_value": item["body_self_hash_value"],
            }
            for item in hostile_components
        ]
    )
    hostile_graph = _task4_seal(hostile_graph, "graph_sha")
    with pytest.raises((TypeError, ValueError)):
        core.validate_response_run_spec_fixture_v1(legal, provenance, hostile_graph)


def test_task4_source_response_validator_covers_branch_shape_and_lineage_attacks() -> (
    None
):
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    run_spec = _task4_response_run_spec(provenance, graph)
    for branch in ("actual", "matched_ablated"):
        legal = _task4_source_response(branch, run_spec, graph)
        assert (
            core.validate_source_readout_response_raw_v1(
                legal,
                run_spec,
                provenance,
                graph,
            )
            == legal
        )
        for attack in (
            "unknown",
            "field_order",
            "type",
            "self_hash",
            "nested_self_hash",
            "branch_bridge_join",
            "factory_join",
            "transition_join",
            "certificate_join",
            "run_spec_join",
            "basis_join",
            "calibration_join",
            "values_shape",
        ):
            raw = _task4_clone(legal)
            assert type(raw) is dict
            if attack == "unknown":
                raw["caller_unknown"] = False
            elif attack == "field_order":
                raw = {key: raw[key] for key in reversed(tuple(raw))}
            elif attack == "type":
                raw["branch"] = 1
            elif attack == "self_hash":
                raw["response_sha"] = "f" * 64
            elif attack == "nested_self_hash":
                raw["values"]["tensor_sha"] = "f" * 64
                raw = _task4_seal(raw, "response_sha")
            elif attack == "branch_bridge_join":
                raw["bridge_audit"]["branch"] = (
                    "matched_ablated" if branch == "actual" else "actual"
                )
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "factory_join":
                raw["factory_sha"] = "f" * 64
                raw["bridge_audit"]["factory_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "transition_join":
                raw["transition_sha"] = "f" * 64
                raw["bridge_audit"]["transition_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "certificate_join":
                raw["dynamics_certificate_sha"] = "f" * 64
                raw["bridge_audit"]["dynamics_certificate_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "run_spec_join":
                raw["run_spec_sha"] = "f" * 64
                raw["bridge_audit"]["run_spec_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "basis_join":
                raw["source_basis"]["role"] = "holdout_source"
                _task4_resign_tree("BasisManifest", raw["source_basis"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "calibration_join":
                raw["bridge_audit"]["readout_calibration_spec_sha"] = "f" * 64
                _task4_resign_tree("SourceReadoutBridgeAudit", raw["bridge_audit"])
                raw = _task4_seal(raw, "response_sha")
            elif attack == "values_shape":
                raw["values"] = _task4_tensor([2, 10, 10])
                raw = _task4_seal(raw, "response_sha")
            if attack == "field_order":
                assert (
                    core.validate_source_readout_response_raw_v1(
                        raw,
                        run_spec,
                        provenance,
                        graph,
                    )
                    == legal
                )
                continue
            with pytest.raises((TypeError, ValueError)):
                core.validate_source_readout_response_raw_v1(
                    raw,
                    run_spec,
                    provenance,
                    graph,
                )


def test_task4_source_response_defers_shell_join_to_task7_route_verification() -> None:
    core = _core_module()
    provenance = _task4_provenance_fixture()
    graph = _task4_graph_manifest(provenance)
    run_spec = _task4_response_run_spec(provenance, graph)
    raw = _task4_source_response("actual", run_spec, graph)
    raw["shell_manifest_sha"] = "f" * 64
    raw = _task4_seal(raw, "response_sha")

    assert (
        core.validate_source_readout_response_raw_v1(
            raw,
            run_spec,
            provenance,
            graph,
        )
        == raw
    )


def test_task4_all_seven_legacy_endpoint_payloads_match_production_golden() -> None:
    fixture_path = (
        REPOSITORY_ROOT / "tests" / "fixtures" / "v3m0_b7_legacy_response_18b0d43.json"
    )
    if not fixture_path.is_file():
        pytest.skip(
            "Task-2 legacy golden is integrated after this isolated Task-4 branch"
        )
    core = _core_module()
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    assert [item["case_id"] for item in fixture["cases"]] == [
        "qualification_invalid",
        "input_binding_invalid",
        "actual_response_failed",
        "ablated_response_failed",
        "actual_bridge_failed",
        "ablated_bridge_failed",
        "success",
    ]
    for case in fixture["cases"]:
        shell = case["complete_input_wire"]["shell_outcome"]
        reference = shell["reference_outcome"]
        before_shell = core.canonical_json_bytes_v1(shell)
        before_reference = core.canonical_json_bytes_v1(reference)
        assert core.validate_endpoint_reference_outcome_raw_v1(reference) == reference
        assert core.validate_endpoint_shell_outcome_raw_v1(shell) == shell
        assert core.canonical_json_bytes_v1(reference) == before_reference
        assert core.canonical_json_bytes_v1(shell) == before_shell
        assert reference["outcome_sha"] == core.canonical_sha_v1(
            {key: value for key, value in reference.items() if key != "outcome_sha"}
        )
        assert shell["outcome_sha"] == core.canonical_sha_v1(
            {key: value for key, value in shell.items() if key != "outcome_sha"}
        )
