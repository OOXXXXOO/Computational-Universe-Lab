"""Tests for the M3′ 30-cell real-space pilot evaluator."""

from __future__ import annotations

from importlib.util import find_spec
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


class PilotInterfaceTests(unittest.TestCase):
    def test_module_exists(self) -> None:
        self.assertIsNotNone(find_spec("rulespace_v2.m3_pilot"))

    def test_public_interfaces_exist(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        for name in (
            "measure_impulse_kernel",
            "kernel_matrix_at_k",
            "evaluate_measured_kernel",
            "measure_cell",
            "assess_resolvability",
        ):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(pilot, name, None)))


class ImpulseKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v2 import m3_pilot as pilot

        cls.measured = pilot.measure_impulse_kernel(q=0, kappa_c=0.0, L=17)

    def test_realspace_impulse_kernel_has_the_frozen_shape_and_support(self) -> None:
        self.assertEqual(self.measured["kernel"].shape, (28, 28, 17, 17, 17))
        self.assertEqual(self.measured["realspace_runs"], 28)
        self.assertEqual(self.measured["support_radius"], 4)
        self.assertEqual(len(self.measured["kernel_sha256"]), 64)

    def test_measured_kernel_reconstructs_a_direct_plane_wave_step(self) -> None:
        from rulespace_v2 import m3_local_family as local
        from rulespace_v2 import m3_pilot as pilot

        L = 17
        k_units = np.array([1, 2, 3], dtype=float)
        k = 2.0 * math.pi * k_units / L
        rng = np.random.default_rng(260730)
        amplitude = rng.normal(size=28) + 1j * rng.normal(size=28)
        coordinates = np.indices((L, L, L), dtype=float)
        phase = np.exp(1j * np.einsum("i,ixyz->xyz", k, coordinates))

        def field(values: np.ndarray) -> np.ndarray:
            return values[:, None, None, None] * phase[None, ...]

        state = local.LocalFamilyState(
            h=field(amplitude[:10]),
            zeta=field(amplitude[10:14]),
            p_h=field(amplitude[14:24]),
            p_zeta=field(amplitude[24:]),
        )
        stepped = local.realspace_step_factory(0, 0.0)(state)
        direct = np.concatenate(
            (
                stepped.h[:, 0, 0, 0],
                stepped.zeta[:, 0, 0, 0],
                stepped.p_h[:, 0, 0, 0],
                stepped.p_zeta[:, 0, 0, 0],
            )
        )
        matrix = pilot.kernel_matrix_at_k(self.measured["kernel"], k)
        with np.errstate(all="ignore"):
            expected = matrix @ amplitude
        residual = np.linalg.norm(direct - expected) / np.linalg.norm(direct)
        self.assertLess(residual, 1e-12)


class MeasuredCoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v2 import m3_pilot as pilot

        cls.measured = pilot.measure_impulse_kernel(q=0, kappa_c=0.0, L=17)

    def test_coordinate_measurement_does_not_read_the_offline_symbol(self) -> None:
        from rulespace_v2 import m3_local_family as local
        from rulespace_v2 import m3_pilot as pilot

        k = np.array([math.pi / 4.0, 0.0, 0.0])
        with patch.object(
            local,
            "symbol_of_potential",
            side_effect=AssertionError("offline symbol is not runtime output"),
        ):
            row = pilot.evaluate_measured_kernel(self.measured["kernel"], k)
        self.assertTrue(row["valid"])
        self.assertLessEqual(row["floquet"]["max_modulus_error"], 1e-10)

    def test_epsilon_is_measured_from_the_curvature_subspace(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        rows = {}
        for name, direction in pilot.DIRECTIONS.items():
            k = (math.pi / 4.0) * np.asarray(direction, dtype=float)
            rows[name] = pilot.evaluate_measured_kernel(
                self.measured["kernel"], k
            )
        for row in rows.values():
            with self.subTest(k=row["k"]):
                self.assertEqual(row["N_curv"], 6)
                self.assertEqual(row["j_hand_invariant"], 4)
                self.assertAlmostEqual(row["epsilon_geo"], 1.0 / 3.0)
                self.assertEqual(len(row["invariants"]["sin_theta"]), 6)
                self.assertLessEqual(
                    row["basis_robustness"]["max_drift"], 1e-12
                )
                self.assertTrue(row["basis_robustness"]["j_stable"])

    def test_basis_robustness_rotates_raw_phase_clusters(self) -> None:
        from rulespace_v2 import invariants
        from rulespace_v2 import m3_pilot as pilot

        k = np.array([math.pi / 4.0, 0.0, 0.0])
        with patch.object(
            invariants,
            "rotate_within_clusters",
            wraps=invariants.rotate_within_clusters,
        ) as rotate:
            row = pilot.evaluate_measured_kernel(self.measured["kernel"], k)
        self.assertTrue(row["valid"])
        self.assertEqual(rotate.call_count, len(invariants.ROT_SEEDS))


class SigmaMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v2 import m3_pilot as pilot

        measured = pilot.measure_impulse_kernel(q=0, kappa_c=0.0, L=17)
        cls.points = pilot.collect_direction_from_kernel(
            measured["kernel"],
            "axial",
            pilot.DIRECTIONS["axial"],
        )

    def test_sampling_inherits_the_frozen_r37_shell(self) -> None:
        self.assertEqual(len(self.points), 16)
        self.assertEqual(sum(point["in_fit"] for point in self.points), 6)
        self.assertEqual(
            sum(point["in_fit_window"] for point in self.points), 8
        )
        ratio_to_provenance = {
            tuple(point["ratio"]): point["provenance"] for point in self.points
        }
        self.assertEqual(
            ratio_to_provenance[(1, 8)],
            [[16, 2], [24, 3], [32, 4], [48, 6]],
        )

    def test_sigma_fit_reports_full_primary_and_robustness_fields(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        judge = pilot.judge_direction_full("axial", self.points)
        self.assertEqual(judge["n_fit_points"], 6)
        self.assertIn(judge["verdict"], ("PASS", "FAIL", "ambiguous"))
        for key in (
            "A",
            "sigma_A",
            "alpha",
            "sigma_alpha",
            "dAIC_const_minus_power",
        ):
            self.assertIn(key, judge["sigma"])
            self.assertTrue(math.isfinite(judge["sigma"][key]))
        self.assertEqual(len(judge["loo"]["rows"]), 6)
        self.assertEqual(judge["widened_window_diagnostic"]["n_points"], 8)

    def test_synthetic_power_and_constant_controls_have_teeth(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        x = np.linspace(0.2, 0.8, 8)

        def points(y: np.ndarray) -> list[dict[str, object]]:
            return [
                {
                    "kabs": float(xv),
                    "max_sin_theta": float(yv),
                    "rms_sin": float(yv),
                    "in_fit": True,
                    "in_fit_window": True,
                    "off_band": False,
                }
                for xv, yv in zip(x, y)
            ]

        power = pilot.judge_direction_full(
            "synthetic-power", points(0.4 * x**2)
        )
        constant = pilot.judge_direction_full(
            "synthetic-constant", points(np.full_like(x, 0.2))
        )
        self.assertEqual(power["verdict"], "PASS")
        self.assertEqual(constant["verdict"], "FAIL")


class CellMeasurementTests(unittest.TestCase):
    def test_one_cell_runs_and_measures_all_coordinates(self) -> None:
        from rulespace_v2 import m3_local_family as local
        from rulespace_v2 import m3_pilot as pilot

        with patch.object(
            local,
            "symbol_of_potential",
            side_effect=AssertionError("offline symbol is forbidden"),
        ), patch.object(
            np.fft,
            "fftn",
            side_effect=AssertionError("FFT is forbidden in the pilot"),
        ):
            cell = pilot.measure_cell(q=0, kappa_c=0.0)
        self.assertTrue(cell["valid"])
        self.assertEqual(cell["construction"], {"q": 0, "kappa_c": 0.0})
        self.assertEqual(cell["runtime"]["delta_realspace_runs"], 28)
        self.assertEqual(cell["runtime"]["validation_realspace_runs"], 1)
        self.assertLessEqual(cell["runtime"]["plane_bridge_residual"], 1e-12)
        self.assertEqual(set(cell["epsilon_geo_by_direction"]), set(pilot.DIRECTIONS))
        self.assertEqual(set(cell["sigma_by_direction"]), set(pilot.DIRECTIONS))
        self.assertEqual(len(cell["epsilon_signature"]), 3)
        self.assertNotIn("q", cell["coordinates"])
        self.assertNotIn("kappa_c", cell["coordinates"])


class PilotResolvabilityTests(unittest.TestCase):
    @staticmethod
    def _cells(
        *,
        epsilon_teeth: bool,
        sigma_teeth: bool,
        bracket: bool,
    ) -> list[dict[str, object]]:
        from rulespace_v2 import m3_pilot as pilot

        cells = []
        for index in range(30):
            upper = index >= 15
            j_hand = 3 if epsilon_teeth and upper else 4
            amplitude = 0.20 if sigma_teeth and upper else 0.0
            verdict = "FAIL" if upper or not bracket else "PASS"
            if bracket and not upper:
                verdict = "PASS"
            sigma_by_direction = {}
            sigma_judges = {}
            for direction in pilot.DIRECTIONS:
                sigma_by_direction[direction] = {
                    "A": amplitude,
                    "sigma_A": 0.001,
                    "alpha": 2.0,
                    "sigma_alpha": 0.01,
                    "verdict": verdict,
                }
                sigma_judges[direction] = {
                    "loo": {
                        "rows": [
                            {"A": amplitude - 0.0002},
                            {"A": amplitude + 0.0002},
                        ]
                    }
                }
            cells.append(
                {
                    "cell_id": f"cell-{index}",
                    "valid": True,
                    "epsilon_signature": [
                        {
                            "direction": direction,
                            "N_curv": 6,
                            "j_hand_invariant": j_hand,
                        }
                        for direction in pilot.DIRECTIONS
                    ],
                    "sigma_by_direction": sigma_by_direction,
                    "sigma_judges": sigma_judges,
                }
            )
        return cells

    def test_missing_or_invalid_cell_halts_as_invalid(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        result = pilot.assess_resolvability(
            self._cells(epsilon_teeth=True, sigma_teeth=True, bracket=True)[:-1],
            {"pass": True, "margin_factor": 2.0},
        )
        self.assertEqual(result["status"], "HALT-PILOT-INVALID")
        self.assertFalse(result["formal_scan_unlocked"])

    def test_a_flat_epsilon_signature_is_unresolved(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        result = pilot.assess_resolvability(
            self._cells(epsilon_teeth=False, sigma_teeth=True, bracket=True),
            {"pass": True, "margin_factor": 2.0},
        )
        self.assertEqual(result["status"], "HALT-PILOT-UNRESOLVED")
        self.assertFalse(result["criteria"]["epsilon_counting_teeth"]["pass"])

    def test_overlapping_sigma_intervals_are_unresolved(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        result = pilot.assess_resolvability(
            self._cells(epsilon_teeth=True, sigma_teeth=False, bracket=True),
            {"pass": True, "margin_factor": 2.0},
        )
        self.assertEqual(result["status"], "HALT-PILOT-UNRESOLVED")
        self.assertFalse(result["criteria"]["sigma_continuous_teeth"]["pass"])

    def test_ulp_scale_sigma_difference_is_not_a_tooth(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        cells = self._cells(
            epsilon_teeth=True,
            sigma_teeth=True,
            bracket=True,
        )
        for index, cell in enumerate(cells):
            amplitude = 2e-10 if index >= 15 else 0.0
            for direction in pilot.DIRECTIONS:
                cell["sigma_by_direction"][direction]["A"] = amplitude
                cell["sigma_by_direction"][direction]["sigma_A"] = 1e-12
                for row in cell["sigma_judges"][direction]["loo"]["rows"]:
                    row["A"] = amplitude
        result = pilot.assess_resolvability(
            cells,
            {"pass": True, "margin_factor": 2.0},
        )
        self.assertEqual(result["status"], "HALT-PILOT-UNRESOLVED")
        self.assertFalse(result["criteria"]["sigma_continuous_teeth"]["pass"])

    def test_all_teeth_only_unlock_formal_preregistration(self) -> None:
        from rulespace_v2 import m3_pilot as pilot

        result = pilot.assess_resolvability(
            self._cells(epsilon_teeth=True, sigma_teeth=True, bracket=True),
            {"pass": True, "margin_factor": 2.0},
        )
        self.assertEqual(result["status"], "READY-FORMAL-PREREGISTRATION")
        self.assertTrue(result["formal_preregistration_unlocked"])
        self.assertFalse(result["formal_scan_unlocked"])
        self.assertTrue(all(row["pass"] for row in result["criteria"].values()))


class PilotRunnerTests(unittest.TestCase):
    def test_runner_module_and_public_preflight_exist(self) -> None:
        self.assertIsNotNone(find_spec("experiments.v2m3_pilot"))
        from experiments import v2m3_pilot as runner

        self.assertTrue(callable(runner.audit_inputs))
        self.assertTrue(callable(runner.evaluate_input_payloads))

    def test_current_round_zero_evidence_unlocks_exactly_thirty_cells(self) -> None:
        from experiments import v2m3_pilot as runner

        audit = runner.audit_inputs()
        self.assertTrue(audit["pass"])
        self.assertEqual(len(audit["manifest_cells"]), 30)
        self.assertEqual(audit["preflight"]["status"], "READY-PILOT")

    def test_tampered_round_zero_status_keeps_runner_locked(self) -> None:
        from experiments import v2m3_pilot as runner

        current = runner.audit_inputs()
        preflight = copy.deepcopy(current["preflight"])
        preflight["status"] = "HALT-FAMILY-ADMISSION"
        audit = runner.evaluate_input_payloads(
            preflight,
            current["state"],
            current["local_certificate"],
            current["file_records"],
        )
        self.assertFalse(audit["pass"])
        self.assertFalse(audit["checks"]["preflight_ready"])

    def test_persisted_resource_halt_is_terminal_on_resume(self) -> None:
        from experiments import v2m3_pilot as runner

        audit = runner.audit_inputs()
        payload = {
            "status": "HALT-PILOT-RESOURCE",
            "main_pilot_executed": False,
            "inputs": audit["file_records"],
            "protocol": runner._protocol_record(),
            "resource_preflight": {"pass": False},
            "cells": [{"cell_id": "m3-q0-kc0p000"}],
        }
        decision = runner.validate_existing_payload(
            payload,
            audit["file_records"],
            runner._protocol_record(),
        )
        self.assertTrue(decision["pass"])
        self.assertEqual(decision["action"], "halt-resource")

    def test_resume_rejects_a_different_evaluator_sha(self) -> None:
        from experiments import v2m3_pilot as runner

        audit = runner.audit_inputs()
        stale_protocol = copy.deepcopy(runner._protocol_record())
        stale_protocol["code"]["rulespace_v2/m3_pilot.py"]["sha256"] = "0" * 64
        payload = {
            "status": "RUNNING-PILOT",
            "main_pilot_executed": False,
            "inputs": audit["file_records"],
            "protocol": stale_protocol,
            "cells": [{"cell_id": "m3-q0-kc0p000"}],
        }
        decision = runner.validate_existing_payload(
            payload,
            audit["file_records"],
            runner._protocol_record(),
        )
        self.assertFalse(decision["pass"])
        self.assertIn("protocol_changed", decision["failures"])

    def test_json_roundtrip_restores_nonfinite_diagnostics(self) -> None:
        from experiments import v2m3_pilot as runner

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nonfinite.json"
            runner._write_json_atomic(
                path,
                {"positive": float("inf"), "negative": float("-inf")},
            )
            restored = runner._read_json(path)
        self.assertTrue(math.isinf(restored["positive"]))
        self.assertGreater(restored["positive"], 0.0)
        self.assertTrue(math.isinf(restored["negative"]))
        self.assertLess(restored["negative"], 0.0)

    def test_thirty_cells_allow_runner_only_finalization_amendment(self) -> None:
        from experiments import v2m3_pilot as runner

        old_protocol = {
            "code": {
                "experiments/v2m3_pilot.py": {
                    "path": "experiments/v2m3_pilot.py",
                    "sha256": "1" * 64,
                },
                "rulespace_v2/m3_pilot.py": {"sha256": "2" * 64},
            },
            "frozen_verification": {"pass": True},
        }
        new_protocol = copy.deepcopy(old_protocol)
        new_protocol["code"]["experiments/v2m3_pilot.py"]["sha256"] = "3" * 64
        payload = {
            "status": "RUNNING-PILOT",
            "main_pilot_executed": False,
            "inputs": {"preflight": {"sha256": "4" * 64}},
            "protocol": old_protocol,
            "cells": [{"cell_id": f"cell-{index}"} for index in range(30)],
        }
        decision = runner.validate_existing_payload(
            payload,
            payload["inputs"],
            new_protocol,
        )
        self.assertTrue(decision["pass"])
        self.assertEqual(decision["action"], "finalize-runner-amendment")

    def test_runner_amendment_rejects_missing_or_changed_runner_record(self) -> None:
        from experiments import v2m3_pilot as runner

        old_protocol = {
            "code": {
                "experiments/v2m3_pilot.py": {
                    "path": "experiments/v2m3_pilot.py",
                    "sha256": "1" * 64,
                },
                "rulespace_v2/m3_pilot.py": {"sha256": "2" * 64},
            },
            "frozen_verification": {"pass": True},
        }
        payload = {
            "status": "RUNNING-PILOT",
            "main_pilot_executed": False,
            "inputs": {"preflight": {"sha256": "4" * 64}},
            "protocol": old_protocol,
            "cells": [{"cell_id": f"cell-{index}"} for index in range(30)],
        }
        for changed in ("missing", "path"):
            current = copy.deepcopy(old_protocol)
            if changed == "missing":
                del current["code"]["experiments/v2m3_pilot.py"]
            else:
                current["code"]["experiments/v2m3_pilot.py"]["path"] = (
                    "experiments/other.py"
                )
                current["code"]["experiments/v2m3_pilot.py"]["sha256"] = "3" * 64
            decision = runner.validate_existing_payload(
                payload,
                payload["inputs"],
                current,
            )
            with self.subTest(changed=changed):
                self.assertFalse(decision["pass"])
                self.assertIn("protocol_changed", decision["failures"])

    def test_protocol_pins_environment_and_all_execution_dependencies(self) -> None:
        from experiments import v2m3_pilot as runner

        protocol = runner._protocol_record()
        self.assertTrue(protocol["frozen_verification"]["pass"])
        self.assertIn("numpy_version", protocol["environment_fingerprint"])
        pinned = protocol["code"]
        for relative_path in (
            "rulespace_v2/m3_pilot.py",
            "rulespace_v2/m3_local_family.py",
            "rulespace_v2/m3_family.py",
            "rulespace_v2/invariants.py",
            "rulespace_v2/epsilon.py",
            "rulespace_v2/frozen.py",
            "experiments/v2m3_pilot.py",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertEqual(len(pinned[relative_path]["sha256"]), 64)

    def test_pilot_state_without_result_is_a_broken_checkpoint_pair(self) -> None:
        from experiments import v2m3_pilot as runner

        state = {"generator": "experiments/v2m3_pilot.py"}
        decision = runner.validate_checkpoint_pair(
            state,
            result_exists=False,
        )
        self.assertFalse(decision["pass"])
        self.assertIn("state_result_pair_mismatch", decision["failures"])

    def test_checkpoint_sha_and_manifest_prefix_are_verified(self) -> None:
        from experiments import v2m3_pilot as runner

        audit = runner.audit_inputs()
        manifest = audit["manifest_cells"]
        payload = {
            "status": "RUNNING-PILOT",
            "main_pilot_executed": False,
            "cells": [
                {
                    "cell_id": manifest[0]["cell_id"],
                    "construction": {
                        "q": manifest[0]["q"],
                        "kappa_c": manifest[0]["kappa_c"],
                    },
                }
            ],
        }
        state = {
            "generator": "experiments/v2m3_pilot.py",
            "status": "RUNNING-PILOT",
            "main_pilot_executed": False,
            "completed_cells": 1,
            "result": {"sha256": "a" * 64},
        }
        bad_sha = runner.validate_checkpoint(
            payload,
            state,
            manifest,
            "b" * 64,
        )
        self.assertFalse(bad_sha["pass"])
        self.assertIn("checkpoint_result_sha_mismatch", bad_sha["failures"])

        tampered = copy.deepcopy(payload)
        tampered["cells"][0]["construction"]["q"] = 4
        bad_prefix = runner.validate_checkpoint(
            tampered,
            state,
            manifest,
            "a" * 64,
        )
        self.assertFalse(bad_prefix["pass"])
        self.assertIn("cells_not_manifest_prefix", bad_prefix["failures"])

    def test_measurement_exception_becomes_an_invalid_cell_record(self) -> None:
        from experiments import v2m3_pilot as runner

        manifest_cell = build_cell = {
            "cell_id": "m3-q0-kc0p000",
            "q": 0,
            "kappa_c": 0.0,
        }
        with patch.object(
            runner.PILOT,
            "measure_cell",
            side_effect=ValueError("empty curvature"),
        ):
            cell = runner.measure_manifest_cell(build_cell)
        self.assertEqual(cell["cell_id"], manifest_cell["cell_id"])
        self.assertFalse(cell["valid"])
        self.assertIn("measurement_exception", cell["failures"])
        self.assertEqual(cell["error"]["type"], "ValueError")
        self.assertGreater(cell["runtime"]["process_peak_rss_bytes"], 0)

    def test_run_rejects_tampered_checkpoint_before_measurement(self) -> None:
        from experiments import v2m3_pilot as runner

        baseline = runner.audit_inputs()
        manifest = baseline["manifest_cells"]
        protocol = runner._protocol_record()
        inputs = baseline["file_records"]
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            state_path = Path(directory) / "state.json"
            payload = {
                "status": "RUNNING-PILOT",
                "main_pilot_executed": False,
                "inputs": inputs,
                "protocol": protocol,
                "cells": [
                    {
                        "cell_id": manifest[0]["cell_id"],
                        "construction": {"q": 4, "kappa_c": 0.0},
                    }
                ],
            }
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            state = {
                "generator": "experiments/v2m3_pilot.py",
                "status": "RUNNING-PILOT",
                "main_pilot_executed": False,
                "completed_cells": 1,
                "result": {"sha256": runner.sha256_file(result_path)},
            }
            audit = {
                **baseline,
                "pass": True,
                "state": state,
                "manifest_cells": manifest,
                "file_records": inputs,
            }
            with patch.object(runner, "RESULT_PATH", result_path), patch.object(
                runner, "STATE_PATH", state_path
            ), patch.object(runner, "audit_inputs", return_value=audit), patch.object(
                runner, "_protocol_record", return_value=protocol
            ), patch.object(runner.PILOT, "measure_cell") as measure:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "checkpoint is inconsistent",
                ):
                    runner.run()
            measure.assert_not_called()

    def test_run_fails_closed_on_frozen_sha_mismatch(self) -> None:
        from experiments import v2m3_pilot as runner

        baseline = runner.audit_inputs()
        protocol = {"frozen_verification": {"pass": False}}
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            with patch.object(runner, "RESULT_PATH", result_path), patch.object(
                runner, "audit_inputs", return_value=baseline
            ), patch.object(
                runner, "_protocol_record", return_value=protocol
            ), patch.object(runner.PILOT, "measure_cell") as measure:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "frozen evaluator/source SHA",
                ):
                    runner.run()
            measure.assert_not_called()

    def test_run_persists_measurement_exceptions_as_invalid_pilot(self) -> None:
        from experiments import v2m3_pilot as runner

        baseline = runner.audit_inputs()
        manifest = baseline["manifest_cells"]
        inputs = baseline["file_records"]
        protocol = {"frozen_verification": {"pass": True}}
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            state_path = Path(directory) / "state.json"
            figure_path = Path(directory) / "figure.png"
            audit = {
                **baseline,
                "pass": True,
                "state": {"generator": "experiments/v2m3_preflight.py"},
                "manifest_cells": manifest,
                "file_records": inputs,
                "preflight": {
                    "pilot_manifest": {"manifest_sha256": "test-manifest"}
                },
            }
            with patch.object(runner, "RESULT_PATH", result_path), patch.object(
                runner, "STATE_PATH", state_path
            ), patch.object(runner, "FIGURE_PATH", figure_path), patch.object(
                runner, "ROOT", Path(directory)
            ), patch.object(
                runner, "audit_inputs", return_value=audit
            ), patch.object(
                runner, "_protocol_record", return_value=protocol
            ), patch.object(
                runner.PILOT,
                "measure_cell",
                side_effect=ValueError("empty curvature"),
            ), patch.object(runner, "make_figure"):
                payload = runner.run()
            self.assertEqual(payload["status"], "HALT-PILOT-INVALID")
            self.assertEqual(len(payload["cells"]), 30)
            self.assertTrue(
                all(not cell["valid"] for cell in payload["cells"])
            )
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "HALT-PILOT-INVALID")
            self.assertTrue(state["main_pilot_executed"])
            self.assertFalse(state["formal_scan_unlocked"])


if __name__ == "__main__":
    unittest.main()
