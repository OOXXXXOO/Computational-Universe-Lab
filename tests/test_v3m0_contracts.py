from __future__ import annotations

import copy
import math
import unittest
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from typing import Optional, get_type_hints

import rulespace_v3
from rulespace_v3 import (
    FINAL_RESULT_EVIDENCE_FIELDS,
    BlockStatus,
    EvidenceEnvelope,
    RequiredBlockReport,
    UndefinedReason,
    canonical_sha,
    evaluate_required_blocks,
    validate_evidence_envelope,
    validate_evidence_fields,
)


SHA_FIELDS = ("trace_sha", "parent_v2_sha", "window_manifest_sha")


class PhantomNonEmptyMapping(Mapping[str, object]):
    """Claims one entry while exposing no canonical mapping items."""

    def __getitem__(self, key: str) -> object:
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self) -> int:
        return 1


class ItemsLookupMismatchMapping(Mapping[str, object]):
    """Exposes one items snapshot but returns a different lookup value."""

    def __init__(
        self,
        snapshot: Mapping[str, object],
        lookup_overrides: Mapping[str, object],
    ) -> None:
        self._snapshot = snapshot
        self._lookup_overrides = lookup_overrides

    def __getitem__(self, key: str) -> object:
        if key in self._lookup_overrides:
            return self._lookup_overrides[key]
        return self._snapshot[key]

    def __iter__(self):
        return iter(self._snapshot)

    def __len__(self) -> int:
        return len(self._snapshot)

    def items(self):
        return self._snapshot.items()


class ItemsLookupMismatchBlockMapping(Mapping[str, BlockStatus]):
    """Returns preregistered statuses from items and poisoned direct lookups."""

    def __init__(
        self,
        snapshot: Mapping[str, BlockStatus],
        lookup_overrides: Mapping[str, BlockStatus],
    ) -> None:
        self._snapshot = snapshot
        self._lookup_overrides = lookup_overrides

    def __getitem__(self, key: str) -> BlockStatus:
        if key in self._lookup_overrides:
            return self._lookup_overrides[key]
        return self._snapshot[key]

    def __iter__(self):
        return iter(self._snapshot)

    def __len__(self) -> int:
        return len(self._snapshot)

    def items(self):
        return self._snapshot.items()


class DuplicateItemsBlockMapping(Mapping[str, BlockStatus]):
    """Adversarial Mapping whose items stream repeats a block ID."""

    def __getitem__(self, key: str) -> BlockStatus:
        if key == "response":
            return BlockStatus(True, None)
        raise KeyError(key)

    def __iter__(self):
        return iter(("response",))

    def __len__(self) -> int:
        return 1

    def items(self):
        return iter(
            (
                ("response", BlockStatus(True, None)),
                ("response", BlockStatus(False, UndefinedReason.RESPONSE_NULL)),
            )
        )


def valid_evidence_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        field: f"{field}:fixture" for field in FINAL_RESULT_EVIDENCE_FIELDS[:-1]
    }
    payload.update(
        {
            "trace_sha": "a" * 64,
            "parent_v2_sha": "b" * 64,
            "window_manifest_sha": "c" * 64,
            "toolchain_manifest": {
                "components": (
                    {"name": "lean", "version": "4.32.1"},
                    {"name": "mathlib", "revision": "5" * 40},
                ),
                "python": {"version": "3.9"},
            },
        }
    )
    return payload


class UndefinedReasonTests(unittest.TestCase):
    def test_values_match_the_frozen_contract(self) -> None:
        self.assertEqual(
            {reason.name: reason.value for reason in UndefinedReason},
            {
                "TRACE_UNCLASSIFIED": "trace_unclassified",
                "ABLATION_NOT_REVERSIBLE": "ablation_not_reversible",
                "STATE_SCHEMA_MISMATCH": "state_schema_mismatch",
                "RESPONSE_NULL": "response_null",
                "RESPONSE_GREY": "response_grey",
                "RANK_GAP": "rank_gap",
                "SHELL_TRACKING_AMBIGUOUS": "shell_tracking_ambiguous",
                "UNSTABLE": "unstable",
                "MANIFEST_MISMATCH": "manifest_mismatch",
            },
        )


class BlockStatusTests(unittest.TestCase):
    def test_defined_status_has_no_reason(self) -> None:
        self.assertEqual(BlockStatus(defined=True, reason=None), BlockStatus(True, None))

    def test_undefined_status_requires_a_reason(self) -> None:
        status = BlockStatus(False, UndefinedReason.RESPONSE_GREY)
        self.assertFalse(status.defined)
        self.assertIs(status.reason, UndefinedReason.RESPONSE_GREY)

    def test_rejects_bool_reason_contradictions(self) -> None:
        for defined, reason in (
            (True, UndefinedReason.RESPONSE_NULL),
            (False, None),
        ):
            with self.subTest(defined=defined, reason=reason):
                with self.assertRaisesRegex(ValueError, "defined.*reason"):
                    BlockStatus(defined, reason)

    def test_rejects_non_boolean_defined_flag(self) -> None:
        with self.assertRaisesRegex(TypeError, "defined.*bool"):
            BlockStatus(1, None)  # type: ignore[arg-type]

    def test_rejects_untyped_reason(self) -> None:
        with self.assertRaisesRegex(TypeError, "UndefinedReason"):
            BlockStatus(False, "response_null")  # type: ignore[arg-type]

    def test_is_immutable(self) -> None:
        status = BlockStatus(True, None)
        with self.assertRaises(FrozenInstanceError):
            status.defined = False  # type: ignore[misc]

    def test_runtime_type_hints_resolve_on_python_39(self) -> None:
        hints = get_type_hints(BlockStatus)
        self.assertEqual(hints["reason"], Optional[UndefinedReason])


class CanonicalShaTests(unittest.TestCase):
    def test_mapping_order_does_not_change_sha(self) -> None:
        first = {
            "outer": {"b": 2, "a": [True, None, 1.25]},
            "label": "control",
        }
        second = {
            "label": "control",
            "outer": {"a": [True, None, 1.25], "b": 2},
        }
        self.assertEqual(canonical_sha(first), canonical_sha(second))

    def test_frozen_utf8_canonical_sha_vector(self) -> None:
        self.assertEqual(
            canonical_sha(
                {
                    "label": "μ",
                    "outer": {"a": [True, None, 1.25], "b": -0.0},
                }
            ),
            "2f0bf9a094ad2c3eed47c42435f3ad6044c7e26faa33d2db314a92c5cf5ba6c5",
        )

    def test_docstring_freezes_the_hash_encoding_contract(self) -> None:
        documentation = canonical_sha.__doc__ or ""
        for required_text in (
            "SHA-256",
            "UTF-8",
            "sort_keys=True",
            "separators=(',', ':')",
            "ensure_ascii=False",
            "allow_nan=False",
            "complete payload",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, documentation)

    def test_array_order_changes_sha(self) -> None:
        self.assertNotEqual(
            canonical_sha({"samples": [1, 2, 3]}),
            canonical_sha({"samples": [3, 2, 1]}),
        )

    def test_list_and_tuple_have_the_same_json_array_encoding(self) -> None:
        self.assertEqual(
            canonical_sha({"samples": [1, 2, 3]}),
            canonical_sha({"samples": (1, 2, 3)}),
        )

    def test_hashes_the_complete_payload(self) -> None:
        base = {"artifact": "trace", "payload": {"rank": 10}}
        extended = {**base, "extra": "must-not-be-dropped"}
        self.assertNotEqual(canonical_sha(base), canonical_sha(extended))

    def test_distinguishes_negative_and_positive_zero(self) -> None:
        self.assertNotEqual(
            canonical_sha({"value": -0.0}),
            canonical_sha({"value": 0.0}),
        )

    def test_does_not_mutate_payload(self) -> None:
        payload = {"blocks": ({"id": "b", "values": [1.0, 2.0]},)}
        before = copy.deepcopy(payload)
        digest = canonical_sha(payload)
        self.assertEqual(len(digest), 64)
        self.assertEqual(payload, before)
        self.assertIsInstance(payload["blocks"], tuple)

    def test_rejects_non_finite_numbers_recursively(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    canonical_sha({"nested": [{"value": value}]})

    def test_rejects_non_string_mapping_keys_recursively(self) -> None:
        with self.assertRaisesRegex(TypeError, "mapping key.*str"):
            canonical_sha({"nested": {1: "not-json"}})  # type: ignore[dict-item]

    def test_rejects_non_json_values_and_non_array_sequences(self) -> None:
        for value in ({1, 2}, b"bytes", memoryview(b"bytes"), range(3), object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(TypeError, "JSON"):
                    canonical_sha({"value": value})

    def test_rejects_cyclic_containers(self) -> None:
        cyclic_list: list[object] = []
        cyclic_list.append(cyclic_list)
        cyclic_mapping: dict[str, object] = {}
        cyclic_mapping["self"] = cyclic_mapping
        for value in (cyclic_list, cyclic_mapping):
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(ValueError, "cyclic"):
                    canonical_sha({"value": value})


class EvidenceProfileTests(unittest.TestCase):
    def test_final_result_field_names_match_taskbook_section_eight(self) -> None:
        self.assertEqual(
            FINAL_RESULT_EVIDENCE_FIELDS,
            (
                "evaluator_version",
                "grammar_id",
                "target_spec_id",
                "trace_sha",
                "response_manifest_id",
                "parent_v2_sha",
                "source_metric_id",
                "physical_h_metric_id",
                "curvature_metric_id",
                "physical_quotient_id",
                "physical_quotient_metric_id",
                "nu_inc_id",
                "window_manifest_sha",
                "actual_unary_manifest_id",
                "ablated_unary_manifest_id",
                "toolchain_manifest",
            ),
        )

    def test_intermediate_profile_does_not_require_final_result_fields(self) -> None:
        payload = {
            "artifact_kind": "formal_no_go",
            "trace_sha": "d" * 64,
            "certificate": {"rank": 10},
        }
        self.assertIsNone(
            validate_evidence_fields(
                payload,
                required_fields=("artifact_kind", "trace_sha", "certificate"),
            )
        )

    def test_profile_rejects_missing_required_field(self) -> None:
        with self.assertRaisesRegex(ValueError, "certificate"):
            validate_evidence_fields(
                {"artifact_kind": "formal_no_go"},
                required_fields=("artifact_kind", "certificate"),
            )

    def test_final_validator_rejects_each_missing_required_field(self) -> None:
        for field in FINAL_RESULT_EVIDENCE_FIELDS:
            with self.subTest(field=field):
                payload = valid_evidence_payload()
                del payload[field]
                with self.assertRaisesRegex(ValueError, field):
                    validate_evidence_envelope(payload)

    def test_first_fifteen_final_fields_are_non_empty_strings(self) -> None:
        for field in FINAL_RESULT_EVIDENCE_FIELDS[:-1]:
            for value in ("", " \t", None, 7):
                with self.subTest(field=field, value=value):
                    payload = valid_evidence_payload()
                    payload[field] = value
                    with self.assertRaisesRegex((ValueError, TypeError), field):
                        validate_evidence_envelope(payload)

    def test_sha_fields_require_lowercase_64_digit_hex(self) -> None:
        invalid_values = ("a" * 63, "a" * 65, "A" * 64, "g" * 64)
        for field in SHA_FIELDS:
            for value in invalid_values:
                with self.subTest(field=field, value=value[:4]):
                    payload = valid_evidence_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(ValueError, field):
                        validate_evidence_envelope(payload)

    def test_toolchain_manifest_must_be_a_non_empty_mapping(self) -> None:
        for value in ("toolchain:v1", {}, [], None):
            with self.subTest(value=type(value).__name__):
                payload = valid_evidence_payload()
                payload["toolchain_manifest"] = value
                with self.assertRaisesRegex(
                    (ValueError, TypeError), "toolchain_manifest"
                ):
                    validate_evidence_envelope(payload)

    def test_toolchain_nonempty_check_uses_the_canonical_snapshot(self) -> None:
        payload = valid_evidence_payload()
        payload["toolchain_manifest"] = PhantomNonEmptyMapping()
        with self.assertRaisesRegex(ValueError, "toolchain_manifest"):
            validate_evidence_envelope(payload)

    def test_envelope_never_relooks_up_values_after_snapshot(self) -> None:
        snapshot = valid_evidence_payload()
        adversarial = ItemsLookupMismatchMapping(
            snapshot,
            {"toolchain_manifest": "poisoned-second-read"},
        )
        envelope = validate_evidence_envelope(adversarial)
        self.assertIsInstance(envelope.toolchain_manifest, Mapping)
        self.assertIn("components", envelope.toolchain_manifest)

    def test_envelope_deep_freezes_toolchain_manifest(self) -> None:
        payload = valid_evidence_payload()
        source_manifest = payload["toolchain_manifest"]
        envelope = validate_evidence_envelope(payload)

        self.assertIsInstance(envelope, EvidenceEnvelope)
        self.assertIsInstance(envelope.toolchain_manifest, Mapping)
        components = envelope.toolchain_manifest["components"]
        self.assertIsInstance(components, tuple)
        first_component = components[0]  # type: ignore[index]
        self.assertIsInstance(first_component, Mapping)

        with self.assertRaises(TypeError):
            envelope.toolchain_manifest["new"] = "forbidden"  # type: ignore[index]
        with self.assertRaises(TypeError):
            first_component["version"] = "changed"  # type: ignore[index]
        with self.assertRaises(TypeError):
            components[0] = {"name": "changed"}  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            envelope.trace_sha = "f" * 64  # type: ignore[misc]

        source_manifest["python"]["version"] = "mutated"  # type: ignore[index]
        frozen_python = envelope.toolchain_manifest["python"]
        self.assertEqual(frozen_python["version"], "3.9")  # type: ignore[index]


class RequiredBlockEvaluationTests(unittest.TestCase):
    def test_all_required_blocks_defined_returns_an_empty_report(self) -> None:
        report = evaluate_required_blocks(
            {
                "geometry": BlockStatus(True, None),
                "response": BlockStatus(True, None),
            },
            ("response", "geometry"),
        )
        self.assertEqual(
            report,
            RequiredBlockReport(BlockStatus(True, None), ()),
        )

    def test_preserves_all_undefined_reasons_in_preregistered_order(self) -> None:
        report = evaluate_required_blocks(
            {
                "alpha": BlockStatus(False, UndefinedReason.RESPONSE_GREY),
                "middle": BlockStatus(True, None),
                "zeta": BlockStatus(False, UndefinedReason.UNSTABLE),
            },
            ("zeta", "middle", "alpha"),
        )
        self.assertEqual(
            report.undefined,
            (
                ("zeta", UndefinedReason.UNSTABLE),
                ("alpha", UndefinedReason.RESPONSE_GREY),
            ),
        )
        self.assertEqual(
            report.status,
            BlockStatus(False, UndefinedReason.UNSTABLE),
        )

    def test_optional_undefined_block_does_not_propagate(self) -> None:
        report = evaluate_required_blocks(
            {
                "required": BlockStatus(True, None),
                "optional": BlockStatus(False, UndefinedReason.RESPONSE_NULL),
            },
            ("required",),
        )
        self.assertEqual(report.status, BlockStatus(True, None))
        self.assertEqual(report.undefined, ())

    def test_missing_required_block_is_a_schema_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing.*geometry"):
            evaluate_required_blocks(
                {"response": BlockStatus(True, None)},
                ("response", "geometry"),
            )

    def test_block_evaluation_uses_one_items_snapshot(self) -> None:
        blocks = ItemsLookupMismatchBlockMapping(
            {
                "response": BlockStatus(
                    False,
                    UndefinedReason.RESPONSE_GREY,
                ),
                "geometry": BlockStatus(True, None),
            },
            {"response": BlockStatus(True, None)},
        )
        report = evaluate_required_blocks(
            blocks,
            ("response", "geometry"),
        )
        self.assertEqual(
            report.undefined,
            (("response", UndefinedReason.RESPONSE_GREY),),
        )

    def test_duplicate_block_items_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate.*response"):
            evaluate_required_blocks(
                DuplicateItemsBlockMapping(),
                ("response",),
            )

    def test_required_ids_must_be_nonempty_unique_nonempty_strings(self) -> None:
        blocks = {"response": BlockStatus(True, None)}
        for required_ids in ((), ("response", "response"), ("",), (7,)):
            with self.subTest(required_ids=required_ids):
                with self.assertRaises((ValueError, TypeError)):
                    evaluate_required_blocks(
                        blocks,
                        required_ids,  # type: ignore[arg-type]
                    )

    def test_report_is_immutable_and_old_lossy_api_is_not_exported(self) -> None:
        report = evaluate_required_blocks(
            {"response": BlockStatus(False, UndefinedReason.RESPONSE_NULL)},
            ("response",),
        )
        with self.assertRaises(FrozenInstanceError):
            report.undefined = ()  # type: ignore[misc]
        self.assertFalse(hasattr(rulespace_v3, "aggregate_required_blocks"))


if __name__ == "__main__":
    unittest.main()
