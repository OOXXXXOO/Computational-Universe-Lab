from __future__ import annotations

import copy
import hashlib
import math
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path
from unittest import mock

from rulespace_v3.evidence import canonical_sha


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "data/results/v2m3_pilot.json"
PARENT_SHA = "6358edc238095c7662b2a5e91c3a62ba72eac066cca57c8d6e70b5586b8caab0"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resign(cert: dict[str, object]) -> dict[str, object]:
    cert["certificate_sha"] = canonical_sha(
        {key: value for key, value in cert.items() if key != "certificate_sha"}
    )
    return cert


class ItemsSnapshotMapping(Mapping[str, object]):
    def __init__(
        self,
        snapshot: dict[str, object],
        poisoned_lookup: dict[str, object],
    ) -> None:
        self.snapshot = snapshot
        self.poisoned_lookup = poisoned_lookup

    def __getitem__(self, key: str) -> object:
        return self.poisoned_lookup.get(key, self.snapshot[key])

    def __iter__(self) -> Iterator[str]:
        return iter(self.snapshot)

    def __len__(self) -> int:
        return len(self.snapshot)

    def items(self):
        return self.snapshot.items()


class ExactPhase0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from experiments.v3m0_formal_nogo import build_phase0_certificate
        from rulespace_v2 import m3_local_family as local
        from rulespace_v2 import m3_pilot as pilot

        old_factory = local.realspace_step_factory
        old_kernel = pilot.measure_impulse_kernel

        def forbidden(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("production real-space factory/kernel was called")

        local.realspace_step_factory = forbidden  # type: ignore[assignment]
        pilot.measure_impulse_kernel = forbidden  # type: ignore[assignment]
        before = file_sha(PARENT)
        try:
            cls.cert = build_phase0_certificate(PARENT)
        finally:
            local.realspace_step_factory = old_factory
            pilot.measure_impulse_kernel = old_kernel
        if before != PARENT_SHA or file_sha(PARENT) != PARENT_SHA:
            raise AssertionError("parent v2 pilot changed during setUpClass")

    def test_valid_certificate_and_determinism(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate
        from experiments.v3m0_formal_nogo import _json_bytes

        self.assertIsNone(verify_exact_certificate(self.cert))
        self.assertEqual(_json_bytes(self.cert), _json_bytes(copy.deepcopy(self.cert)))
        self.assertEqual(self.cert["status"], "READY-V3M0-CONTROLS")
        self.assertEqual(
            self.cert["evidence_kind"],
            "source_sha_static_symbol_reconstruction",
        )
        for field in (
            "raw_kernel_available",
            "raw_kernel_recomputed",
            "raw_kernel_independent_recomputation",
        ):
            self.assertIs(self.cert[field], False)

    def test_outer_sha_tamper_fails(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        tampered = copy.deepcopy(self.cert)
        tampered["certificate_sha"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "certificate_sha"):
            verify_exact_certificate(tampered)

    def test_semantic_exact_tampering_fails_after_resigning(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        mutations = (
            lambda c: c["exact"]["variable_order"].reverse(),
            lambda c: c["exact"]["directions"][0].update({"rank": 5}),
            lambda c: c["exact"]["directions"][0]["pivot_columns"].reverse(),
            lambda c: c["exact"]["directions"][0]["witness_columns"].reverse(),
            lambda c: c["exact"]["directions"][0].update({"minor": "1"}),
            lambda c: c["exact"]["laurent"]["c_dagger_c_support"].append([9, 9, 9]),
            lambda c: c["exact"]["symplectic"].update({"residual": "1"}),
            lambda c: c["exact"]["directions"][0].update(
                {"whitened_coisometry_required": False}
            ),
            lambda c: c["exact"]["directions"][0].update(
                {"k_domain": "rho>0"}
            ),
            lambda c: c["exact"]["directions"][0].update(
                {"vector": [0, 0, 1]}
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tampered = copy.deepcopy(self.cert)
                mutate(tampered)
                resign(tampered)
                with self.assertRaises((TypeError, ValueError)):
                    verify_exact_certificate(tampered)

    def test_unknown_top_level_and_nested_fields_fail_after_resigning(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        for nested in (False, True):
            tampered = copy.deepcopy(self.cert)
            if nested:
                tampered["exact"]["laurent"]["unknown"] = True
            else:
                tampered["unknown"] = True
            resign(tampered)
            with self.assertRaisesRegex(ValueError, "unknown|schema|exact"):
                verify_exact_certificate(tampered)

    def test_nonfinite_adversarial_payload_is_rejected(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        tampered = copy.deepcopy(self.cert)
        tampered["static_bridge"]["max_saved_spectrum_residual"] = math.nan
        with self.assertRaises(ValueError):
            verify_exact_certificate(tampered)

    def test_parent_saved_scalar_and_static_bridge_scope(self) -> None:
        bridge = self.cert["static_bridge"]
        saved = self.cert["saved_scalar_reduction"]
        self.assertEqual(bridge["reference_count"], 90)
        self.assertLessEqual(bridge["max_coisometry_residual_2"], 1e-12)
        self.assertLessEqual(bridge["max_saved_spectrum_residual"], 2e-15)
        self.assertEqual(saved["record_count"], 90)
        self.assertEqual(saved["unique_N_curv"], [6])
        self.assertEqual(saved["unique_j"], [4])
        self.assertEqual(saved["epsilon_geo"], "1/3")
        self.assertLessEqual(
            saved["max_saved_squared_spectrum_exact_residual"],
            2e-15,
        )
        self.assertFalse(bridge["raw_kernel_content_verified"])

    def test_exact_geometry_claims_are_frozen(self) -> None:
        exact = self.cert["exact"]
        self.assertEqual(exact["variable_order"], ["zx", "zy", "zz"])
        self.assertEqual(len(exact["laurent"]["c_dagger_c_support"]), 13)
        self.assertEqual(
            exact["packing"],
            ["h00", "h01", "h02", "h03", "h11", "h12", "h13", "h22", "h23", "h33"],
        )
        self.assertEqual(
            [row["direction"] for row in exact["directions"]],
            ["axial", "face-diagonal", "body-diagonal"],
        )
        for row in exact["directions"]:
            self.assertEqual(row["rank"], 6)
            self.assertEqual(row["pivot_columns"], row["witness_columns"])
            self.assertEqual(row["physical_quotient_dimension"], 2)
            self.assertEqual(row["gauge_t_phys_orthogonality_residual"], "0")
            self.assertEqual(row["k_sector_rank"], 6)
            self.assertEqual(row["row_complement_dimension"], 4)
            self.assertEqual(row["squared_sine_charpoly"], "x^2*(x-1)^4")
            self.assertEqual(row["witness_rows"], [17, 18, 19, 34, 35, 51])
            self.assertEqual(row["nu_ir_limit"], sum(v * v for v in row["vector"]))
            self.assertEqual(
                row["k_domain"],
                "0<rho<=pi (first-Brillouin punctured ray)",
            )
            self.assertIn("nu_reference_value", row)
            self.assertNotIn("nu_reference_squared", row)
            self.assertEqual(row["nu_order"], 2)
            self.assertIs(row["nu_positive_on_domain"], True)
            self.assertEqual(row["nu_zero_set_on_domain"], "EmptySet")

    def test_exact_profile_cache_cannot_be_polluted(self) -> None:
        from rulespace_v3.exact import exact_profile

        first = exact_profile()
        first["variable_order"].reverse()
        second = exact_profile()
        self.assertEqual(second["variable_order"], ["zx", "zy", "zz"])

    def test_formal_manifest_tamper_fails_after_resigning(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        tampered = copy.deepcopy(self.cert)
        tampered["formal"]["toolchain_sha256"]["formal/v3m0/lean-toolchain"] = "0" * 64
        resign(tampered)
        with self.assertRaisesRegex(ValueError, "independent reconstruction"):
            verify_exact_certificate(tampered)

    def test_frozen_static_lineage_tamper_fails_after_resigning(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        frozen = self.cert["lineage"]["frozen_static_sources"]
        self.assertEqual(
            set(frozen),
            {
                "experiments/r15_walk_dedonder.py",
                "experiments/r32_reachability_probe.py",
                "experiments/r25_auxiliary_wilson_complex.py",
            },
        )
        self.assertTrue(all(row["match"] for row in frozen.values()))
        self.assertIs(self.cert["gates"]["frozen_static_source_sha"], True)
        tampered = copy.deepcopy(self.cert)
        tampered["lineage"]["frozen_static_sources"][
            "experiments/r15_walk_dedonder.py"
        ]["expected_sha256"] = "0" * 64
        resign(tampered)
        with self.assertRaisesRegex(ValueError, "independent reconstruction"):
            verify_exact_certificate(tampered)

    def test_complete_static_execution_closure_is_frozen_and_hashed(self) -> None:
        from experiments.v3m0_formal_nogo import (
            STATIC_CLOSURE_FREEZE,
            _discover_static_execution_closure,
        )

        discovered = _discover_static_execution_closure()
        self.assertEqual(set(discovered), set(STATIC_CLOSURE_FREEZE))
        recorded = self.cert["lineage"]["static_execution_closure"]
        self.assertEqual(set(recorded["files"]), set(STATIC_CLOSURE_FREEZE))
        self.assertEqual(recorded["file_count"], len(STATIC_CLOSURE_FREEZE))
        self.assertTrue(all(row["match"] for row in recorded["files"].values()))
        for required in (
            "experiments/__init__.py",
            "experiments/r10_current_generator.py",
            "experiments/cp1_v4_L2.py",
            "rulespace_gpu/tensor_coin_feedback.py",
            "experiments/r25_dynamic_symbol.py",
            "experiments/r25_realspace_step.py",
            "experiments/r25_walk_dedonder_complex.py",
            "experiments/r25_detour_complex.py",
            "rulespace_v2/m3_local_family.py",
            "rulespace_v2/frozen.py",
            "rulespace_v3/__init__.py",
            "rulespace_v3/contracts.py",
            "rulespace_v3/evidence.py",
        ):
            self.assertIn(required, recorded["files"])
        self.assertIs(self.cert["gates"]["static_execution_closure_sha"], True)

    def test_unknown_closure_authority_is_fail_closed(self) -> None:
        from experiments.v3m0_formal_nogo import (
            STATIC_CLOSURE_FREEZE,
            _authority_sha,
            _load_json,
        )

        parent = _load_json(PARENT)
        with self.assertRaisesRegex(ValueError, "unknown closure authority"):
            _authority_sha(
                "experiments/unknown.py",
                {
                    "sha256": "0" * 64,
                    "authority": "unknown.authority",
                },
                parent,
            )
        for relative in (
            "experiments/cp1_v4_L1.py",
            "experiments/cp1_v4_damping.py",
        ):
            self.assertEqual(
                STATIC_CLOSURE_FREEZE[relative]["authority"],
                "v3m0_task7_signed_execution_closure_freeze",
            )

    def test_fresh_process_loaded_local_modules_are_signed_lineage_subset(
        self,
    ) -> None:
        runtime = self.cert["lineage"]["fresh_process_runtime_closure"]
        loaded = set(runtime["loaded_local_module_files"])
        allowed = set(runtime["allowed_signed_lineage_files"])
        self.assertTrue(runtime["loaded_subset_of_signed_lineage"])
        self.assertEqual(runtime["unexpected_local_module_files"], [])
        self.assertLessEqual(loaded, allowed)
        for required in (
            "experiments/__init__.py",
            "experiments/r10_current_generator.py",
            "rulespace_v3/__init__.py",
            "rulespace_v3/contracts.py",
        ):
            self.assertIn(required, loaded)
            self.assertIn(required, self.cert["lineage"]["static_execution_closure"]["files"])
        self.assertEqual(
            runtime["event_order"],
            [
                "runner_import_complete",
                "closure_preflight_complete",
                "static_reference_complete",
            ],
        )
        boundary = runtime["preflight_boundary"]
        self.assertEqual(
            boundary["verified_before"],
            "first_static_symbol_function_call",
        )
        self.assertEqual(
            boundary["not_verified_before"],
            "python_package_bootstrap_and_runner_top_level_import_execution",
        )
        self.assertIs(boundary["reachable"], True)
        self.assertIs(self.cert["gates"]["fresh_process_runtime_closure"], True)

    def test_each_transitive_static_dependency_tamper_fails_after_resigning(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        files = self.cert["lineage"]["static_execution_closure"]["files"]
        for relative in files:
            with self.subTest(relative=relative):
                tampered = copy.deepcopy(self.cert)
                tampered["lineage"]["static_execution_closure"]["files"][
                    relative
                ]["actual_sha256"] = "0" * 64
                resign(tampered)
                with self.assertRaisesRegex(ValueError, "closure"):
                    verify_exact_certificate(tampered)

    def test_closure_verification_precedes_any_static_symbol_call(self) -> None:
        from experiments import v3m0_formal_nogo as runner

        with mock.patch.object(
            runner,
            "_verify_static_execution_closure",
            side_effect=ValueError("closure preflight blocked"),
        ), mock.patch.object(
            runner.LOCAL,
            "symbol_of_potential",
            side_effect=AssertionError("static symbol ran before closure preflight"),
        ):
            with self.assertRaisesRegex(ValueError, "closure preflight"):
                runner.build_phase0_certificate(PARENT)

    def test_environment_manifest_is_attribution_only_and_strict(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        environment = self.cert["environment"]
        self.assertEqual(
            set(environment),
            {
                "numpy_version",
                "numpy_build",
                "numpy_build_config_sha256",
                "blas",
                "lapack",
                "threadpoolctl",
                "python",
                "platform",
                "machine",
                "system",
                "release",
                "attribution_only",
                "cross_platform_bit_identical_required",
            },
        )
        self.assertIs(environment["attribution_only"], True)
        self.assertIs(environment["cross_platform_bit_identical_required"], False)
        self.assertNotIn("environment", self.cert["gates"])
        tampered = copy.deepcopy(self.cert)
        tampered["environment"]["unknown"] = True
        resign(tampered)
        with self.assertRaisesRegex(ValueError, "environment schema"):
            verify_exact_certificate(tampered)

    def test_adversarial_mapping_is_snapshotted_once_and_cycles_fail(self) -> None:
        from rulespace_v3.exact import verify_exact_certificate

        poisoned = ItemsSnapshotMapping(
            copy.deepcopy(self.cert),
            {"status": "HALT-V3M0-PHASE0", "certificate_sha": "0" * 64},
        )
        self.assertIsNone(verify_exact_certificate(poisoned))
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        with self.assertRaisesRegex(ValueError, "cyclic"):
            verify_exact_certificate(cyclic)

    def test_static_record_ids_order_and_each_coisometry_gate(self) -> None:
        records = self.cert["static_bridge"]["records"]
        ids = self.cert["manifest"]["record_ids"]
        self.assertEqual([row["record_id"] for row in records], ids)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(
            all(
                row["coisometry_pass"]
                and row["coisometry_residual_2"] <= 1e-12
                and row["positive_phase_count"] == 14
                for row in records
            )
        )

    def test_formal_required_modules_are_all_hashed(self) -> None:
        formal = self.cert["formal"]
        hashed = set(formal["source_sha256"])
        required = {
            f"formal/v3m0/{relative}" for relative in formal["required_modules"]
        }
        self.assertEqual(required, hashed)
        self.assertTrue(formal["forbidden_token_pass"])
        self.assertEqual(formal["forbidden_tokens"], {})
        self.assertEqual(formal["lean_version_command"], "lake env lean --version")
        self.assertEqual(formal["lean_version_exit_code"], 0)
        self.assertRegex(
            formal["lean_version_output"],
            r"^Lean \(version 4\.32\.1,",
        )
        self.assertEqual(formal["lean_version_expected"], "4.32.1")
        self.assertIs(formal["lean_version_pass"], True)
        self.assertIs(self.cert["gates"]["lean_version"], True)

    def test_standalone_cli_imports_from_repository_root(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "experiments/v3m0_formal_nogo.py"),
                "--help",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("--generate", completed.stdout)
        self.assertIn("--check", completed.stdout)

    def test_cli_generate_then_check_preserves_parent_and_check_target(self) -> None:
        from experiments.v3m0_formal_nogo import main

        parent_bytes = PARENT.read_bytes()
        parent_stat = PARENT.stat()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "certificate.json"
            with mock.patch(
                "experiments.v3m0_formal_nogo.build_phase0_certificate",
                return_value=copy.deepcopy(self.cert),
            ):
                self.assertEqual(
                    main(
                        [
                            "--generate",
                            "--parent",
                            str(PARENT),
                            "--output",
                            str(output),
                        ]
                    ),
                    0,
                )
            generated = output.read_bytes()
            output_stat = output.stat()
            with mock.patch(
                "experiments.v3m0_formal_nogo.build_phase0_certificate",
                return_value=copy.deepcopy(self.cert),
            ):
                self.assertEqual(
                    main(
                        [
                            "--check",
                            "--parent",
                            str(PARENT),
                            "--output",
                            str(output),
                        ]
                    ),
                    0,
                )
            self.assertEqual(output.read_bytes(), generated)
            self.assertEqual(output.stat().st_mtime_ns, output_stat.st_mtime_ns)
        self.assertEqual(PARENT.read_bytes(), parent_bytes)
        self.assertEqual(PARENT.stat().st_mtime_ns, parent_stat.st_mtime_ns)

    def test_cli_rejects_output_aliasing_parent_without_touching_it(self) -> None:
        from experiments.v3m0_formal_nogo import main

        before = PARENT.read_bytes()
        before_stat = PARENT.stat()
        with self.assertRaisesRegex(ValueError, "protected"):
            main(
                [
                    "--generate",
                    "--parent",
                    str(PARENT),
                    "--output",
                    str(PARENT),
                ]
            )
        self.assertEqual(PARENT.read_bytes(), before)
        self.assertEqual(PARENT.stat().st_mtime_ns, before_stat.st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
