from __future__ import annotations

import copy
import dataclasses
import inspect
import math
import unittest
from unittest import mock

import numpy as np

import rulespace_v3.series_control as series_control
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.series_control import (
    DETERMINISTIC_SERIES_CONTROL_OUTCOME_SCHEMA_VERSION,
    DeterministicSeriesControlOutcome,
    VerifiedDeterministicSeriesControlOutcome,
    deterministic_series_control_outcome_payload,
    issue_v3m0_deterministic_series_control_outcomes,
    verify_verified_deterministic_series_control_outcome,
)


class V3M0DeterministicSeriesControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = issue_v3m0_parent_freeze()
        self.outcomes = issue_v3m0_deterministic_series_control_outcomes(
            self.parent
        )

    def test_c20_two_scenarios_are_materialized_from_parent_wires(self) -> None:
        self.assertEqual(len(self.outcomes), 2)
        expected_classes = ("clean-zero", "true-floor")
        expected_slugs = ("clean-zero", "true-floor")
        k_values = np.asarray(
            [2.0 * math.pi / size for size in (16, 24, 32, 48)],
            dtype=np.float64,
        )
        clean = (
            0.236 * k_values**2
            - 0.05 * k_values**4
            + 0.01 * k_values**6
        ).astype(np.float64)

        for capability, series_class, slug in zip(
            self.outcomes,
            expected_classes,
            expected_slugs,
        ):
            self.assertIsInstance(
                capability,
                VerifiedDeterministicSeriesControlOutcome,
            )
            outcome = verify_verified_deterministic_series_control_outcome(
                capability
            )
            self.assertEqual(
                outcome.outcome_schema_version,
                DETERMINISTIC_SERIES_CONTROL_OUTCOME_SCHEMA_VERSION,
            )
            self.assertEqual(
                outcome.application_spec.control_case_id,
                "C20_DM26_CLEAN_ZERO_TRUE_FLOOR",
            )
            self.assertEqual(
                outcome.scenario_spec.scenario_id,
                (
                    "v3m0.synthetic-control.c20.v1."
                    f"scenario.{slug}.v1"
                ),
            )
            self.assertEqual(
                outcome.scenario_spec.execution_lane,
                "ANALYSIS_CONTROL",
            )
            self.assertEqual(outcome.series_class, series_class)
            self.assertEqual(outcome.decision_rule, "D-M2-6")
            np.testing.assert_array_equal(outcome.k_values, tuple(k_values))

        clean_outcome = self.outcomes[0].outcome
        floor_outcome = self.outcomes[1].outcome
        np.testing.assert_array_equal(clean_outcome.raw_samples, tuple(clean))
        np.testing.assert_array_equal(
            floor_outcome.raw_samples,
            tuple(clean + np.float64(1.2e-4)),
        )
        self.assertTrue(clean_outcome.sigma_result.zero_consistent)
        self.assertFalse(floor_outcome.sigma_result.zero_consistent)
        self.assertTrue(clean_outcome.sigma_result.dm26_decision.both_pollution)
        self.assertFalse(floor_outcome.sigma_result.dm26_decision.both_pollution)

    def test_recursive_payload_binds_parent_scenario_samples_and_fit(self) -> None:
        for capability in self.outcomes:
            outcome = capability.outcome
            payload = deterministic_series_control_outcome_payload(outcome)
            self.assertEqual(
                outcome.fit_decision_evidence_sha,
                canonical_sha(payload["fit_decision_evidence"]),
            )
            self.assertEqual(outcome.outcome_sha, canonical_sha(payload))
            self.assertEqual(
                payload["application_spec"]["application_spec_sha"],
                outcome.application_spec.application_spec_sha,
            )
            self.assertEqual(
                payload["scenario_spec"]["scenario_sha"],
                outcome.scenario_spec.scenario_sha,
            )
            self.assertEqual(
                payload["raw_samples"],
                list(outcome.raw_samples),
            )
            self.assertEqual(
                payload["fit_decision_evidence"]["zero_test"],
                "dm26-double-test",
            )
            self.assertEqual(
                len(payload["fit_decision_evidence"]["dm26_controls"]),
                8,
            )

    def test_raw_wrapper_forgery_and_resigned_outcome_are_rejected(self) -> None:
        outcome = self.outcomes[0].outcome
        with self.assertRaises(TypeError):
            VerifiedDeterministicSeriesControlOutcome(
                object(),
                self.parent,
                outcome.scenario_spec.scenario_id,
                "0" * 64,
            )

        changed = dataclasses.replace(
            outcome,
            raw_samples=(
                outcome.raw_samples[0] + 1.0e-6,
                *outcome.raw_samples[1:],
            ),
        )
        changed = dataclasses.replace(
            changed,
            outcome_sha=canonical_sha(
                deterministic_series_control_outcome_payload(changed)
            ),
        )
        self.assertIsInstance(changed, DeterministicSeriesControlOutcome)
        self.assertNotEqual(changed.outcome_sha, outcome.outcome_sha)
        with self.assertRaises((TypeError, ValueError)):
            verify_verified_deterministic_series_control_outcome(changed)

    def test_returned_body_mutation_cannot_change_live_replay(self) -> None:
        capability = self.outcomes[0]
        original = capability.outcome
        hostile = copy.deepcopy(original)
        object.__setattr__(
            hostile,
            "raw_samples",
            (1.0, *hostile.raw_samples[1:]),
        )
        replayed = capability.outcome
        self.assertEqual(replayed, original)
        self.assertNotEqual(replayed.raw_samples, hostile.raw_samples)

    def test_public_issuers_expose_no_dependency_injection_bypass(self) -> None:
        self.assertEqual(
            tuple(
                inspect.signature(
                    issue_v3m0_deterministic_series_control_outcomes
                ).parameters
            ),
            ("parent",),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    verify_verified_deterministic_series_control_outcome
                ).parameters
            ),
            ("value",),
        )
        with self.assertRaises(TypeError):
            issue_v3m0_deterministic_series_control_outcomes(
                self.parent,
                _issuer=lambda *_: object(),
            )

    def test_materializer_rebinding_and_slot_copy_fail_closed(self) -> None:
        with mock.patch.object(
            series_control,
            "_materialize_outcome",
            side_effect=AssertionError("mutable module binding was consulted"),
        ):
            fresh = issue_v3m0_deterministic_series_control_outcomes(
                self.parent
            )
            self.assertEqual(fresh[0].outcome.series_class, "clean-zero")

        with self.assertRaises(AttributeError):
            copy.copy(self.outcomes[0])

        object.__setattr__(
            self.outcomes[0],
            "_VerifiedDeterministicSeriesControlOutcome__scenario_id",
            self.outcomes[1].outcome.scenario_spec.scenario_id,
        )
        with self.assertRaises(ValueError):
            verify_verified_deterministic_series_control_outcome(
                self.outcomes[0]
            )


if __name__ == "__main__":
    unittest.main()
