from __future__ import annotations

import unittest

from tests import test_v3m0_calibration_authority as calibration_fixtures

from rulespace_v3.calibration_authority import (
    issue_v3m0_response_block_attempt,
)
from rulespace_v3.evidence import EvidenceEnvelope

from experiments.v3m0_controls import (
    CONTROL_IDS,
    EXPECTED_TYPED_TERMINATION_SCENARIO_IDS,
    V3M0CapabilityBundle,
    assemble_v3m0_controls,
)


class V3M0TypedTerminationAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture_type = (
            calibration_fixtures.CalibrationApplicationPermitTests
        )
        fixture_type.setUpClass()
        cls.helper = fixture_type(
            methodName="test_fake_calibration_or_parent_cannot_issue_permit"
        )

    def _evidence(self, calibration) -> EvidenceEnvelope:
        return EvidenceEnvelope(
            evaluator_version="typed-assembly-test-v1",
            grammar_id="v3m0.synthetic-control-grammar.v1",
            target_spec_id="v3m0.synthetic.spin2.v1",
            trace_sha="a" * 64,
            response_manifest_id="typed-response-test-v1",
            parent_v2_sha=self.helper.parent.manifest.parent_v2_sha,
            source_metric_id="source-metric-test-v1",
            physical_h_metric_id="physical-h-metric-test-v1",
            curvature_metric_id="curvature-metric-test-v1",
            physical_quotient_id="physical-quotient-test-v1",
            physical_quotient_metric_id="quotient-metric-test-v1",
            nu_inc_id="nu-inc-test-v1",
            window_manifest_sha=(
                calibration.outcome.manifest.calibration_manifest_sha
            ),
            actual_unary_manifest_id="actual-unary-test-v1",
            ablated_unary_manifest_id="ablated-unary-test-v1",
            toolchain_manifest={"python": "unit-test"},
        )

    def test_live_typed_attempt_is_strictly_replayed_by_task17(self) -> None:
        calibration, spec, permit = self.helper._application_permit(11)
        scenario = spec.scenario_execution_specs[0]
        attempt = issue_v3m0_response_block_attempt(
            permit,
            scenario.scenario_id,
        )

        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(
                window_calibration=calibration,
                parent_freeze=self.helper.parent,
                application_permits=((CONTROL_IDS[10], permit),),
                expected_terminations=((scenario.scenario_id, attempt),),
            ),
            control_results=(),
            invariant_results=(),
            evidence=self._evidence(calibration),
            no_physical_anchor_run=True,
        )

        required = dict(assembly.required_blocks.undefined)
        result = assembly.expected_typed_termination[0]
        self.assertTrue(result.status.defined)
        self.assertTrue(result.passed)
        self.assertEqual(
            result.raw_spectra,
            (("raw_singular_values", (0.0,)),),
        )
        self.assertEqual(
            result.termination_events,
            (("null", "activation", scenario.expected_undefined_reason),),
        )
        self.assertNotIn(
            f"{scenario.scenario_id}.expected_typed_termination",
            required,
        )
        self.assertNotIn(
            f"{scenario.scenario_id}.expected_typed_termination",
            dict(assembly.lane_failures),
        )
        self.assertIn(
            (
                f"{EXPECTED_TYPED_TERMINATION_SCENARIO_IDS[1]}."
                "expected_typed_termination"
            ),
            dict(assembly.lane_failures),
        )

    def test_raw_attempt_body_is_not_a_task17_capability(self) -> None:
        calibration, spec, permit = self.helper._application_permit(11)
        scenario = spec.scenario_execution_specs[0]
        raw = issue_v3m0_response_block_attempt(
            permit,
            scenario.scenario_id,
        ).outcome

        assembly = assemble_v3m0_controls(
            formal_all_pass=True,
            exact_all_pass=True,
            identifiability_all_pass=True,
            capabilities=V3M0CapabilityBundle(
                window_calibration=calibration,
                parent_freeze=self.helper.parent,
                application_permits=((CONTROL_IDS[10], permit),),
                expected_terminations=((scenario.scenario_id, raw),),
            ),
            control_results=(),
            invariant_results=(),
            evidence=None,
            no_physical_anchor_run=True,
        )

        self.assertEqual(
            dict(assembly.lane_failures)[
                f"{scenario.scenario_id}.expected_typed_termination"
            ].value,
            "manifest_mismatch",
        )


if __name__ == "__main__":
    unittest.main()
