from __future__ import annotations

import ast
from dataclasses import fields, replace
import hashlib
import inspect
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest import mock

import rulespace_v3.adapters.contracts as adapter_contracts
from rulespace_v3.adapters import (
    ADAPTER_IDS,
    R23_ADAPTER_CONTRACT,
    R25_ADAPTER_CONTRACT,
    R30_ADAPTER_CONTRACT,
    all_adapter_contracts,
    get_adapter_contract,
)
from rulespace_v3.adapters.contracts import (
    ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION,
    ADAPTER_CONTRACT_MAX_ANCESTRY_COMMITS,
    ADAPTER_CONTRACT_MAX_BLOB_ENTRIES,
    ADAPTER_CONTRACT_MAX_ROOTS,
    AdapterCommitmentReceipt,
    AdapterContract,
    adapter_commitment_receipt_from_wire,
    adapter_commitment_receipt_payload,
    adapter_commitment_receipt_sha,
    adapter_commitment_receipt_to_wire,
    adapter_contract_from_wire,
    adapter_contract_payload,
    adapter_contract_sha,
    adapter_contract_to_wire,
    adapter_source_path,
    classify_adapter_ancestry,
    validate_adapter_commitment_receipt,
    verify_adapter_contract,
    verify_adapter_source,
)
from rulespace_v3.adapters.r23 import get_r23_adapter_contract
from rulespace_v3.adapters.r25 import get_r25_adapter_contract
from rulespace_v3.adapters.r30 import get_r30_adapter_contract


ROOT = Path(__file__).resolve().parents[1]

ADAPTER_FIELDS = (
    "adapter_id",
    "target_spec_id",
    "frozen_source_sha",
    "state_schema_id",
    "source_manifest_id",
    "readout_manifest_id",
    "target_conditioned_roots",
    "target_blind_roots",
    "one_step_certificate_schema",
    "multistep_certificate_schema",
    "commitment_receipt_schema",
    "certification_state",
)
RECEIPT_FIELDS = (
    "receipt_schema_version",
    "repository_identity",
    "commit_sha",
    "committed_blob_shas",
    "clean_source_tree_sha",
    "required_ancestor_commit_sha",
    "ancestry_path",
    "external_anchor_id",
    "receipt_sha",
)
SOURCE_PATHS = {
    "R23": "experiments/photon_control.py",
    "R30": "experiments/r30_tensor_complex_dynamical.py",
    "R25": "experiments/r25_realspace_step.py",
}
REQUIRED_CONDITIONED_LABELS = {
    "R23": ("curl", "placed-yee", "lorenz", "target-selector"),
    "R30": ("::c", "kerc", "inc", "tt", "placed-coefficients"),
    "R25": ("de-donder", "wilson", "target-repair", "target-selector"),
}


def _sha256_file(relative_path: str) -> str:
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


def _receipt() -> AdapterCommitmentReceipt:
    ancestor = "1" * 40
    commit = "2" * 40
    provisional = AdapterCommitmentReceipt(
        receipt_schema_version=ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION,
        repository_identity="ca-universe-lab.git",
        commit_sha=commit,
        committed_blob_shas=(("experiments/photon_control.py", "3" * 40),),
        clean_source_tree_sha="4" * 64,
        required_ancestor_commit_sha=ancestor,
        ancestry_path=(ancestor, commit),
        external_anchor_id="external-anchor.pending-v3m1.test",
        receipt_sha="0" * 64,
    )
    return replace(
        provisional,
        receipt_sha=adapter_commitment_receipt_sha(provisional),
    )


class AdapterContractTests(unittest.TestCase):
    def test_frozen_interface_and_three_pending_contracts(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(AdapterContract)),
            ADAPTER_FIELDS,
        )
        self.assertEqual(ADAPTER_IDS, ("R23", "R30", "R25"))
        contracts = all_adapter_contracts()
        self.assertEqual(
            tuple(contract.adapter_id for contract in contracts),
            ADAPTER_IDS,
        )
        self.assertEqual(
            contracts,
            (
                R23_ADAPTER_CONTRACT,
                R30_ADAPTER_CONTRACT,
                R25_ADAPTER_CONTRACT,
            ),
        )
        self.assertEqual(get_r23_adapter_contract(), R23_ADAPTER_CONTRACT)
        self.assertEqual(get_r30_adapter_contract(), R30_ADAPTER_CONTRACT)
        self.assertEqual(get_r25_adapter_contract(), R25_ADAPTER_CONTRACT)
        for adapter_id in ADAPTER_IDS:
            contract = get_adapter_contract(adapter_id)
            self.assertIs(verify_adapter_contract(contract), contract)
            self.assertEqual(contract.certification_state, "PENDING_V3M1")
            self.assertEqual(
                contract.commitment_receipt_schema,
                ADAPTER_COMMITMENT_RECEIPT_SCHEMA_VERSION,
            )
            self.assertIn("one-step", contract.one_step_certificate_schema)
            self.assertIn(
                "multistep-response",
                contract.multistep_certificate_schema,
            )

    def test_source_sha_and_typed_manifest_ids_are_bound(self) -> None:
        for contract in all_adapter_contracts():
            with self.subTest(adapter_id=contract.adapter_id):
                relative_path = SOURCE_PATHS[contract.adapter_id]
                self.assertEqual(adapter_source_path(contract), relative_path)
                self.assertEqual(
                    contract.frozen_source_sha,
                    _sha256_file(relative_path),
                )
                self.assertIs(verify_adapter_source(contract), contract)
                self.assertIn(contract.adapter_id.lower(), contract.state_schema_id)
                self.assertIn(contract.adapter_id.lower(), contract.source_manifest_id)
                self.assertIn(contract.adapter_id.lower(), contract.readout_manifest_id)

    def test_required_target_conditioned_sources_are_explicit(self) -> None:
        for contract in all_adapter_contracts():
            roots_text = "\n".join(contract.target_conditioned_roots).lower()
            for label in REQUIRED_CONDITIONED_LABELS[contract.adapter_id]:
                with self.subTest(
                    adapter_id=contract.adapter_id,
                    label=label,
                ):
                    self.assertIn(label, roots_text)
            self.assertEqual(
                contract.target_conditioned_roots,
                tuple(sorted(contract.target_conditioned_roots)),
            )
            self.assertEqual(
                contract.target_blind_roots,
                tuple(sorted(contract.target_blind_roots)),
            )
            self.assertTrue(contract.target_blind_roots)
            self.assertTrue(
                set(contract.target_conditioned_roots).isdisjoint(
                    contract.target_blind_roots
                )
            )

    def test_numeric_literal_cache_copy_and_rename_cannot_remove_taint(self) -> None:
        contract = R23_ADAPTER_CONTRACT
        conditioned = contract.target_conditioned_roots[0]
        blind = contract.target_blind_roots[0]
        for ancestry in (
            (conditioned, 0),
            (conditioned, 0.5),
            (conditioned, "literal:0.0"),
            (conditioned, "cache", "copy", "rename", 1),
            (blind, conditioned, "literal:1"),
        ):
            with self.subTest(ancestry=ancestry):
                self.assertEqual(
                    classify_adapter_ancestry(contract, ancestry),
                    "target_conditioned",
                )
        self.assertEqual(
            classify_adapter_ancestry(contract, (blind, "literal:2")),
            "unclassified",
        )
        self.assertEqual(
            classify_adapter_ancestry(contract, (3, "literal:3")),
            "unclassified",
        )
        with self.assertRaisesRegex(ValueError, "unclassified"):
            classify_adapter_ancestry(contract, ("caller-claims-blind",))

    def test_ancestry_classifier_freezes_cap_validator_and_finiteness(self) -> None:
        contract = R23_ADAPTER_CONTRACT
        blind = contract.target_blind_roots[0]
        oversized = (blind,) * (
            adapter_contracts.ADAPTER_CONTRACT_MAX_PROVENANCE_ANCESTRY + 1
        )
        tampered = replace(
            contract,
            target_spec_id="spin2.linearized.v1",
        )
        with (
            mock.patch.object(
                adapter_contracts,
                "ADAPTER_CONTRACT_MAX_PROVENANCE_ANCESTRY",
                10_000,
            ),
            mock.patch.object(
                adapter_contracts,
                "verify_adapter_contract",
                return_value=contract,
            ),
            mock.patch.object(
                adapter_contracts,
                "_text",
                side_effect=lambda value, field: str(value),
            ),
            mock.patch.object(
                adapter_contracts.math,
                "isfinite",
                return_value=True,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                classify_adapter_ancestry(contract, oversized)
            with self.assertRaisesRegex(ValueError, "finite"):
                classify_adapter_ancestry(contract, (float("nan"),))
            with self.assertRaisesRegex(
                ValueError,
                "frozen|canonical|contract",
            ):
                classify_adapter_ancestry(tampered, (blind,))
        self.assertEqual(
            tuple(inspect.signature(classify_adapter_ancestry).parameters),
            ("contract", "ancestry"),
        )

    def test_exact_contract_wire_self_hash_and_resign_attack(self) -> None:
        for contract in all_adapter_contracts():
            wire = adapter_contract_to_wire(contract)
            self.assertEqual(
                tuple(wire),
                (*ADAPTER_FIELDS, "adapter_contract_sha"),
            )
            self.assertEqual(
                wire["adapter_contract_sha"],
                adapter_contract_sha(contract),
            )
            self.assertEqual(adapter_contract_from_wire(wire), contract)
            self.assertEqual(
                tuple(adapter_contract_payload(contract)),
                ADAPTER_FIELDS,
            )

        wire = adapter_contract_to_wire(R23_ADAPTER_CONTRACT)
        wire["target_spec_id"] = "spin2.linearized.v1"
        provisional = dict(wire)
        provisional.pop("adapter_contract_sha")
        wire["adapter_contract_sha"] = adapter_contract_sha(
            replace(
                R23_ADAPTER_CONTRACT,
                target_spec_id="spin2.linearized.v1",
            )
        )
        with self.assertRaisesRegex(ValueError, "frozen|canonical|contract"):
            adapter_contract_from_wire(wire)

    def test_contract_wire_unknown_missing_and_wrong_container_types_fail(self) -> None:
        base = adapter_contract_to_wire(R30_ADAPTER_CONTRACT)
        attacks = (
            {**base, "caller_unknown": "forbidden"},
            {key: value for key, value in base.items() if key != "state_schema_id"},
            {
                **base,
                "target_conditioned_roots": tuple(base["target_conditioned_roots"]),
            },
            {**base, "target_blind_roots": "not-a-list"},
        )
        for attack in attacks:
            with self.subTest(keys=tuple(attack)):
                with self.assertRaises((TypeError, ValueError)):
                    adapter_contract_from_wire(attack)

    def test_fake_subclass_partial_instance_and_public_monkeypatch_fail_closed(
        self,
    ) -> None:
        class ForgedAdapterContract(AdapterContract):
            pass

        fake = ForgedAdapterContract(
            **{field: getattr(R23_ADAPTER_CONTRACT, field) for field in ADAPTER_FIELDS}
        )
        with self.assertRaisesRegex(TypeError, "AdapterContract"):
            verify_adapter_contract(fake)

        partial = object.__new__(AdapterContract)
        object.__setattr__(partial, "adapter_id", "R23")
        with self.assertRaises((TypeError, ValueError)):
            verify_adapter_contract(partial)

        tampered = replace(
            R23_ADAPTER_CONTRACT,
            target_spec_id="spin2.linearized.v1",
        )
        with mock.patch(
            "rulespace_v3.adapters.contracts.canonical_sha",
            return_value="a" * 64,
        ):
            with self.assertRaisesRegex(ValueError, "frozen|canonical|contract"):
                verify_adapter_contract(tampered)
            self.assertIs(
                verify_adapter_contract(R23_ADAPTER_CONTRACT),
                R23_ADAPTER_CONTRACT,
            )

    def test_contract_resource_caps_precede_hashing(self) -> None:
        wire = adapter_contract_to_wire(R25_ADAPTER_CONTRACT)
        wire["target_conditioned_roots"] = ["literal:0"] * (
            ADAPTER_CONTRACT_MAX_ROOTS + 1
        )
        with mock.patch(
            "rulespace_v3.adapters.contracts.canonical_sha",
            side_effect=AssertionError("hashing ran before cap"),
        ) as hasher:
            with self.assertRaisesRegex(ValueError, "root|cap|maximum"):
                adapter_contract_from_wire(wire)
            hasher.assert_not_called()

    def test_synchronized_module_rebinding_cannot_forge_or_replace_contract(
        self,
    ) -> None:
        wire = adapter_contract_to_wire(R23_ADAPTER_CONTRACT)
        wire["target_spec_id"] = "spin2.linearized.v1"
        payload = dict(wire)
        payload.pop("adapter_contract_sha")
        wire["adapter_contract_sha"] = adapter_contracts.canonical_sha(payload)
        with (
            mock.patch.object(
                adapter_contracts,
                "AdapterContract",
                types.SimpleNamespace,
            ),
            mock.patch.object(
                adapter_contracts,
                "_require_exact_instance_fields",
                return_value=None,
            ),
            mock.patch.object(
                adapter_contracts,
                "_validate_adapter_contract_fields",
                return_value=None,
            ),
            mock.patch.object(
                adapter_contracts,
                "adapter_contract_payload",
                return_value=payload,
            ),
            mock.patch.object(
                adapter_contracts,
                "adapter_source_path",
                return_value=SOURCE_PATHS["R23"],
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "frozen|canonical|contract",
            ):
                adapter_contract_from_wire(wire)

    def test_rebinding_wire_field_set_cannot_admit_unknown_field(self) -> None:
        wire = adapter_contract_to_wire(R30_ADAPTER_CONTRACT)
        wire["caller_unknown"] = "forbidden"
        expanded = (
            *adapter_contracts._ADAPTER_CONTRACT_WIRE_FIELDS,
            "caller_unknown",
        )
        with mock.patch.object(
            adapter_contracts,
            "_ADAPTER_CONTRACT_WIRE_FIELDS",
            expanded,
        ):
            with self.assertRaisesRegex(ValueError, "unknown"):
                adapter_contract_from_wire(wire)


class AdapterCommitmentReceiptTests(unittest.TestCase):
    def test_raw_receipt_has_exact_wire_and_self_hash_but_no_authority(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(AdapterCommitmentReceipt)),
            RECEIPT_FIELDS,
        )
        receipt = _receipt()
        self.assertIs(validate_adapter_commitment_receipt(receipt), receipt)
        self.assertEqual(
            receipt.receipt_sha,
            adapter_commitment_receipt_sha(receipt),
        )
        self.assertEqual(
            tuple(adapter_commitment_receipt_payload(receipt)),
            RECEIPT_FIELDS[:-1],
        )
        wire = adapter_commitment_receipt_to_wire(receipt)
        self.assertEqual(tuple(wire), RECEIPT_FIELDS)
        self.assertEqual(adapter_commitment_receipt_from_wire(wire), receipt)

        import rulespace_v3.adapters as adapters

        public = set(adapters.__all__)
        self.assertFalse(
            {
                "VerifiedPrestructureAuthority",
                "CalibrationApplicationPermit",
                "VerifiedV3M1ParentFreeze",
                "issue_adapter_authority",
            }
            & public
        )
        self.assertNotIn(
            "parent", inspect.signature(verify_adapter_contract).parameters
        )

    def test_receipt_unknown_fields_resigning_and_ancestry_mismatch_fail(self) -> None:
        receipt = _receipt()
        wire = adapter_commitment_receipt_to_wire(receipt)
        with self.assertRaises((TypeError, ValueError)):
            adapter_commitment_receipt_from_wire({**wire, "caller_unknown": True})

        tampered = dict(wire)
        tampered["external_anchor_id"] = "self-hash-is-not-an-anchor"
        payload = dict(tampered)
        payload.pop("receipt_sha")
        provisional = AdapterCommitmentReceipt(
            receipt_schema_version=payload["receipt_schema_version"],
            repository_identity=payload["repository_identity"],
            commit_sha=payload["commit_sha"],
            committed_blob_shas=tuple(
                tuple(entry) for entry in payload["committed_blob_shas"]
            ),
            clean_source_tree_sha=payload["clean_source_tree_sha"],
            required_ancestor_commit_sha=payload["required_ancestor_commit_sha"],
            ancestry_path=tuple(payload["ancestry_path"]),
            external_anchor_id=payload["external_anchor_id"],
            receipt_sha="0" * 64,
        )
        tampered["receipt_sha"] = adapter_commitment_receipt_sha(provisional)
        # A raw receipt can self-hash, but remains raw and grants no capability.
        rebuilt = adapter_commitment_receipt_from_wire(tampered)
        self.assertEqual(
            rebuilt.external_anchor_id,
            "self-hash-is-not-an-anchor",
        )

        with self.assertRaisesRegex(ValueError, "ancestry|commit"):
            replace(
                receipt,
                ancestry_path=("1" * 40, "5" * 40),
            )

    def test_receipt_resource_caps_fail_before_hash(self) -> None:
        wire = adapter_commitment_receipt_to_wire(_receipt())
        for field, over_cap, message in (
            (
                "committed_blob_shas",
                [
                    [f"experiments/{index}.py", "3" * 40]
                    for index in range(ADAPTER_CONTRACT_MAX_BLOB_ENTRIES + 1)
                ],
                "blob",
            ),
            (
                "ancestry_path",
                ["1" * 40] * (ADAPTER_CONTRACT_MAX_ANCESTRY_COMMITS + 1),
                "ancestry",
            ),
        ):
            attack = {**wire, field: over_cap}
            with self.subTest(field=field):
                with mock.patch(
                    "rulespace_v3.adapters.contracts.canonical_sha",
                    side_effect=AssertionError("hashing ran before cap"),
                ) as hasher:
                    with self.assertRaisesRegex(ValueError, message):
                        adapter_commitment_receipt_from_wire(attack)
                    hasher.assert_not_called()

    def test_synchronized_module_rebinding_cannot_forge_receipt_schema(
        self,
    ) -> None:
        wire = adapter_commitment_receipt_to_wire(_receipt())
        wire["receipt_schema_version"] = "caller.receipt.v999"
        payload = dict(wire)
        payload.pop("receipt_sha")
        wire["receipt_sha"] = adapter_contracts.canonical_sha(payload)
        with (
            mock.patch.object(
                adapter_contracts,
                "AdapterCommitmentReceipt",
                types.SimpleNamespace,
            ),
            mock.patch.object(
                adapter_contracts,
                "_validate_receipt_fields",
                return_value=None,
            ),
            mock.patch.object(
                adapter_contracts,
                "_require_exact_instance_fields",
                return_value=None,
            ),
            mock.patch.object(
                adapter_contracts,
                "adapter_commitment_receipt_payload",
                return_value=payload,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "schema"):
                adapter_commitment_receipt_from_wire(wire)


class AdapterStaticBoundaryTests(unittest.TestCase):
    def test_imports_do_not_load_or_execute_historical_physics(self) -> None:
        script = r"""
import builtins
import importlib
import pathlib
import sys

forbidden = {
    "photon_control",
    "r23_maxwell_control",
    "r30_tensor_complex_dynamical",
    "r25_realspace_step",
    "r25_dynamic_symbol",
    "r25_auxiliary_wilson_complex",
}
original_import = builtins.__import__
original_open = builtins.open

def guarded_import(name, *args, **kwargs):
    if name.split(".")[-1] in forbidden:
        raise AssertionError("historical physics import attempted: " + name)
    return original_import(name, *args, **kwargs)

def guarded_open(file, mode="r", *args, **kwargs):
    if any(flag in mode for flag in ("w", "a", "x", "+")):
        raise AssertionError("adapter import attempted a write")
    return original_open(file, mode, *args, **kwargs)

builtins.__import__ = guarded_import
builtins.open = guarded_open
importlib.import_module("rulespace_v3.adapters")
importlib.import_module("rulespace_v3.adapters.r23")
importlib.import_module("rulespace_v3.adapters.r30")
importlib.import_module("rulespace_v3.adapters.r25")
assert forbidden.isdisjoint({name.split(".")[-1] for name in sys.modules})
"""
        completed = subprocess.run(
            (sys.executable, "-c", script),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stdout + completed.stderr,
        )

    def test_no_family_specific_epsilon_branch_or_legacy_execution_call(self) -> None:
        adapter_files = tuple((ROOT / "rulespace_v3" / "adapters").glob("*.py"))
        self.assertEqual(len(adapter_files), 5)
        forbidden_calls = {
            "step_yee",
            "leap_M",
            "evolve_components",
            "step",
            "batched_step",
            "judge",
            "main",
        }
        for path in adapter_files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    condition = ast.unparse(node.test).lower()
                    self.assertFalse(
                        "epsilon" in condition
                        and any(
                            adapter.lower() in condition for adapter in ADAPTER_IDS
                        ),
                        msg=f"family-specific epsilon branch in {path}",
                    )
                if isinstance(node, ast.Call):
                    function_name = (
                        node.func.id
                        if isinstance(node.func, ast.Name)
                        else (
                            node.func.attr
                            if isinstance(node.func, ast.Attribute)
                            else ""
                        )
                    )
                    self.assertNotIn(
                        function_name,
                        forbidden_calls,
                        msg=f"historical execution call in {path}",
                    )


if __name__ == "__main__":
    unittest.main()
