from __future__ import annotations

import builtins
import dataclasses
import hashlib
import inspect
import json
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from rulespace_v3.evidence import canonical_sha
import rulespace_v3.runtime as runtime
from rulespace_v3.runtime import (
    RUNTIME_EVALUATOR_ID,
    RUNTIME_MAX_PROBE_JSON_BYTES,
    RUNTIME_MAX_SOURCE_FILES,
    RUNTIME_SCHEMA_VERSION,
    RuntimeEvidenceManifest,
    issue_runtime_evidence_manifest,
    runtime_evidence_manifest_from_wire,
    runtime_evidence_manifest_payload,
    runtime_evidence_manifest_to_wire,
    verify_runtime_evidence_manifest,
)


class RuntimeEvidenceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = issue_runtime_evidence_manifest()

    def test_issue_and_verify_bind_the_actual_repo_local_import_closure(self):
        manifest = self.manifest
        self.assertEqual(manifest.runtime_schema_version, RUNTIME_SCHEMA_VERSION)
        self.assertEqual(manifest.evaluator_id, RUNTIME_EVALUATOR_ID)
        self.assertEqual(
            manifest.source_closure,
            tuple(sorted(manifest.source_closure)),
        )
        self.assertEqual(
            len(manifest.source_closure),
            len(set(manifest.source_closure)),
        )
        self.assertGreater(len(manifest.source_closure), 10)
        self.assertIn(
            "rulespace_v3/runtime.py",
            {path for path, _ in manifest.source_closure},
        )
        self.assertFalse(
            any(path.startswith("tests/") for path, _ in manifest.source_closure)
        )
        for relative_path, source_sha in manifest.source_closure:
            path = runtime._repository_root() / relative_path
            self.assertTrue(path.is_file(), relative_path)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                source_sha,
            )
        self.assertTrue(manifest.python_version)
        self.assertTrue(manifest.numpy_version)
        self.assertTrue(manifest.scipy_version)
        self.assertRegex(manifest.blas_config_sha, r"^[0-9a-f]{64}$")
        self.assertRegex(manifest.lapack_config_sha, r"^[0-9a-f]{64}$")
        self.assertTrue(manifest.platform_id)
        self.assertEqual(
            verify_runtime_evidence_manifest(manifest),
            manifest,
        )

    def test_public_authority_ignores_synchronized_module_monkeypatches(self):
        authority = runtime._MODULE_RUNTIME_AUTHORITY
        self.assertIsInstance(authority, tuple)
        self.assertIsInstance(authority.caps, tuple)
        self.assertFalse(hasattr(authority, "__dict__"))
        self.assertFalse(hasattr(authority.caps, "__dict__"))
        with self.assertRaises(AttributeError):
            object.__setattr__(
                authority,
                "import_roots",
                ("rulespace_v3.runtime",),
            )

        real_probe = runtime._run_fresh_probe()
        runtime_entry = next(
            entry
            for entry in real_probe.source_closure
            if entry[0] == "rulespace_v3/runtime.py"
        )
        reduced_probe = dataclasses.replace(
            real_probe,
            source_closure=(runtime_entry,),
        )
        with (
            mock.patch.object(
                runtime,
                "RUNTIME_SCHEMA_VERSION",
                "caller.runtime.v999",
            ),
            mock.patch.object(
                runtime,
                "RUNTIME_EVALUATOR_ID",
                "caller-evaluator",
            ),
            mock.patch.object(
                runtime,
                "_FROZEN_IMPORT_ROOT_CANDIDATES",
                ("rulespace_v3.runtime",),
            ),
            mock.patch.object(
                runtime,
                "_OPTIONAL_IMPORT_ROOTS",
                frozenset(),
            ),
            mock.patch.object(
                runtime,
                "_PROBE_SCRIPT",
                "raise SystemExit('caller probe')",
            ),
            mock.patch.object(
                runtime,
                "_probe_module_roots",
                return_value=("rulespace_v3.runtime",),
            ),
            mock.patch.object(
                runtime,
                "_run_fresh_probe",
                return_value=reduced_probe,
            ),
        ):
            issued = issue_runtime_evidence_manifest()
            self.assertEqual(
                issued.runtime_schema_version,
                RUNTIME_SCHEMA_VERSION,
            )
            self.assertEqual(
                issued.evaluator_id,
                RUNTIME_EVALUATOR_ID,
            )
            paths = {path for path, _ in issued.source_closure}
            self.assertIn("rulespace_v3/spectral.py", paths)
            self.assertIn("rulespace_v3/runtime.py", paths)
            self.assertEqual(
                verify_runtime_evidence_manifest(issued),
                issued,
            )

    def test_source_drift_and_resigned_manifest_are_rejected(self):
        changed_closure = tuple(
            (
                path,
                "f" * 64 if index == 0 else source_sha,
            )
            for index, (path, source_sha) in enumerate(
                self.manifest.source_closure
            )
        )
        resigned = dataclasses.replace(
            self.manifest,
            source_closure=changed_closure,
            runtime_manifest_sha="0" * 64,
        )
        resigned = dataclasses.replace(
            resigned,
            runtime_manifest_sha=canonical_sha(
                runtime_evidence_manifest_payload(resigned)
            ),
        )
        with mock.patch(
            "rulespace_v3.runtime._run_fresh_probe",
            side_effect=AssertionError(
                "fresh imports ran before source SHA preflight"
            ),
        ) as fresh_probe:
            with self.assertRaisesRegex(ValueError, "source preflight"):
                verify_runtime_evidence_manifest(resigned)
        fresh_probe.assert_not_called()

    def test_manifest_and_nested_probe_records_have_exact_slots(self):
        expected_manifest_slots = tuple(
            field.name
            for field in dataclasses.fields(RuntimeEvidenceManifest)
        )
        self.assertEqual(
            tuple(RuntimeEvidenceManifest.__slots__),
            expected_manifest_slots,
        )
        self.assertFalse(hasattr(self.manifest, "__dict__"))
        with self.assertRaises(AttributeError):
            object.__setattr__(
                self.manifest,
                "caller_evaluator",
                "forbidden",
            )
        with self.assertRaises(AttributeError):
            object.__setattr__(self.manifest, "__dict__", {})

        probe = runtime._run_fresh_probe()
        expected_probe_slots = tuple(
            field.name for field in dataclasses.fields(type(probe))
        )
        self.assertEqual(
            tuple(type(probe).__slots__),
            expected_probe_slots,
        )
        self.assertFalse(hasattr(probe, "__dict__"))
        self.assertTrue(
            all(
                type(entry) is tuple and len(entry) == 2
                for entry in probe.source_closure
            )
        )

    def test_evaluator_label_is_closed_and_not_a_caller_argument(self):
        self.assertEqual(
            tuple(inspect.signature(issue_runtime_evidence_manifest).parameters),
            (),
        )
        self.assertEqual(
            tuple(inspect.signature(verify_runtime_evidence_manifest).parameters),
            ("manifest",),
        )
        resigned = dataclasses.replace(
            self.manifest,
            evaluator_id="caller-evaluator",
            runtime_manifest_sha="f" * 64,
        )
        with self.assertRaisesRegex(ValueError, "evaluator_id"):
            runtime_evidence_manifest_payload(resigned)
        with self.assertRaisesRegex(ValueError, "evaluator_id"):
            runtime_evidence_manifest_to_wire(resigned)
        with self.assertRaisesRegex(ValueError, "evaluator_id"):
            verify_runtime_evidence_manifest(resigned)

    def test_strict_wire_rejects_unknown_missing_and_nested_unknown_fields(self):
        wire = runtime_evidence_manifest_to_wire(self.manifest)
        self.assertEqual(
            runtime_evidence_manifest_from_wire(wire),
            self.manifest,
        )

        unknown = dict(wire)
        unknown["caller_toolchain"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "unknown"):
            runtime_evidence_manifest_from_wire(unknown)

        missing = dict(wire)
        del missing["platform_id"]
        with self.assertRaisesRegex(ValueError, "missing"):
            runtime_evidence_manifest_from_wire(missing)

        nested = json.loads(json.dumps(wire))
        nested["source_closure"][0]["caller_label"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "source_closure.*unknown"):
            runtime_evidence_manifest_from_wire(nested)

        wrong_nested_type = json.loads(json.dumps(wire))
        wrong_nested_type["source_closure"][0]["relative_path"] = Path(
            wrong_nested_type["source_closure"][0]["relative_path"]
        )
        with self.assertRaisesRegex(TypeError, "relative_path"):
            runtime_evidence_manifest_from_wire(wrong_nested_type)

    def test_fake_objects_and_noncanonical_closure_wires_are_rejected(self):
        fake = types.SimpleNamespace(**dataclasses.asdict(self.manifest))
        with self.assertRaisesRegex(TypeError, "RuntimeEvidenceManifest"):
            verify_runtime_evidence_manifest(fake)

        with self.assertRaisesRegex(TypeError, "source_closure"):
            dataclasses.replace(
                self.manifest,
                source_closure=list(self.manifest.source_closure),
            )

        reversed_closure = tuple(reversed(self.manifest.source_closure))
        with self.assertRaisesRegex(ValueError, "canonical"):
            dataclasses.replace(
                self.manifest,
                source_closure=reversed_closure,
            )

    def test_resource_caps_reject_before_probe_launch_or_json_decode(self):
        too_many_roots = tuple(
            f"rulespace_v3.synthetic_{index}"
            for index in range(runtime.RUNTIME_MAX_IMPORT_ROOTS + 1)
        )
        with self.assertRaisesRegex(ValueError, "import root"):
            runtime._preflight_import_roots(too_many_roots)

        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            package = repository_root / "rulespace_v3"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            runtime_source = package / "runtime.py"
            with runtime_source.open("wb") as handle:
                handle.truncate(runtime.RUNTIME_MAX_SOURCE_FILE_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "before import"):
                runtime._preflight_import_sources(
                    repository_root,
                    ("rulespace_v3.runtime",),
                )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            with path.open("wb") as handle:
                handle.truncate(RUNTIME_MAX_PROBE_JSON_BYTES + 1)
            with mock.patch(
                "rulespace_v3.runtime.json.loads",
                side_effect=AssertionError("decoded before size preflight"),
            ) as loads:
                with self.assertRaisesRegex(ValueError, "probe output"):
                    runtime._load_probe_output(path)
            loads.assert_not_called()

        closure = tuple(
            (f"rulespace_v3/x_{index}.py", "0" * 64)
            for index in range(RUNTIME_MAX_SOURCE_FILES + 1)
        )
        with self.assertRaisesRegex(ValueError, "source_closure"):
            RuntimeEvidenceManifest(
                runtime_schema_version=RUNTIME_SCHEMA_VERSION,
                evaluator_id=RUNTIME_EVALUATOR_ID,
                source_closure=closure,
                python_version="x",
                numpy_version="x",
                scipy_version="x",
                blas_config_sha="0" * 64,
                lapack_config_sha="0" * 64,
                platform_id="x",
                runtime_manifest_sha="0" * 64,
            )

    def test_probe_stdio_uses_bounded_files_and_never_unbounded_pipes(self):
        roots = runtime._probe_module_roots()
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "probe.json"
            with mock.patch(
                "subprocess.run",
                side_effect=AssertionError(
                    "reduced roots reached the child"
                ),
            ) as reduced_runner:
                with self.assertRaisesRegex(
                    ValueError,
                    "module-frozen authority",
                ):
                    runtime._launch_probe_subprocess(
                        ("rulespace_v3.runtime",),
                        output_path,
                        _runner=reduced_runner,
                    )
            reduced_runner.assert_not_called()

            def oversized_stderr_runner(command, **kwargs):
                del command
                self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
                self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
                self.assertIsNot(kwargs["stderr"], subprocess.PIPE)
                kwargs["stderr"].write(
                    b"x"
                    * (
                        runtime.RUNTIME_MAX_SUBPROCESS_STDERR_BYTES
                        + 1
                    )
                )
                kwargs["stderr"].flush()
                return types.SimpleNamespace(returncode=1)

            with self.assertRaisesRegex(
                RuntimeError,
                "stderr.*resource cap",
            ):
                runtime._launch_probe_subprocess(
                    roots,
                    output_path,
                    _runner=oversized_stderr_runner,
                )

    def test_self_hash_is_complete_evidence_not_a_wall_clock(self):
        payload = runtime_evidence_manifest_payload(self.manifest)
        self.assertEqual(
            self.manifest.runtime_manifest_sha,
            canonical_sha(payload),
        )
        self.assertFalse(
            {"timestamp", "issued_at", "sequence"} & set(payload)
        )
        repeated = issue_runtime_evidence_manifest()
        self.assertEqual(repeated, self.manifest)


class RuntimeWireAuthorityAttackTests(unittest.TestCase):
    def _manifest(self) -> RuntimeEvidenceManifest:
        provisional = RuntimeEvidenceManifest(
            runtime_schema_version=RUNTIME_SCHEMA_VERSION,
            evaluator_id=RUNTIME_EVALUATOR_ID,
            source_closure=(
                ("rulespace_v3/runtime.py", "0" * 64),
            ),
            python_version="fixture-python",
            numpy_version="fixture-numpy",
            scipy_version="fixture-scipy",
            blas_config_sha="1" * 64,
            lapack_config_sha="2" * 64,
            platform_id="fixture-platform",
            runtime_manifest_sha="0" * 64,
        )
        return dataclasses.replace(
            provisional,
            runtime_manifest_sha=canonical_sha(
                runtime_evidence_manifest_payload(provisional)
            ),
        )

    @staticmethod
    def _resign_wire(wire):
        body = dict(wire)
        body.pop("runtime_manifest_sha", None)
        result = dict(wire)
        result["runtime_manifest_sha"] = canonical_sha(body)
        return result

    @staticmethod
    def _unchecked_replace(manifest, **changes):
        result = object.__new__(RuntimeEvidenceManifest)
        for slot in RuntimeEvidenceManifest.__slots__:
            object.__setattr__(
                result,
                slot,
                changes.get(slot, getattr(manifest, slot)),
            )
        return result

    def test_top_and_nested_field_set_rebinding_cannot_expand_wire_schema(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())

        top = json.loads(json.dumps(wire))
        top["caller_toolchain"] = "forbidden"
        with mock.patch.object(
            runtime,
            "_WIRE_FIELDS",
            frozenset((*runtime._WIRE_FIELDS, "caller_toolchain")),
        ):
            with self.assertRaisesRegex(ValueError, "unknown"):
                runtime_evidence_manifest_from_wire(top)

        nested = json.loads(json.dumps(wire))
        nested["source_closure"][0]["caller_label"] = "forbidden"
        with mock.patch.object(
            runtime,
            "_SOURCE_ENTRY_FIELDS",
            frozenset(
                (*runtime._SOURCE_ENTRY_FIELDS, "caller_label")
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "source_closure.*unknown",
            ):
                runtime_evidence_manifest_from_wire(nested)

    def test_schema_evaluator_and_public_serializers_use_frozen_authority(self):
        manifest = self._manifest()
        changed = dataclasses.replace(
            manifest,
            evaluator_id="caller-evaluator",
            runtime_manifest_sha="f" * 64,
        )
        with (
            mock.patch.object(
                runtime,
                "RUNTIME_EVALUATOR_ID",
                "caller-evaluator",
            ),
            mock.patch.object(
                runtime,
                "RUNTIME_SCHEMA_VERSION",
                "caller.runtime.v999",
            ),
        ):
            with self.assertRaisesRegex(ValueError, "evaluator_id"):
                runtime_evidence_manifest_payload(changed)
            with self.assertRaisesRegex(ValueError, "evaluator_id"):
                runtime_evidence_manifest_to_wire(changed)

            wire = runtime_evidence_manifest_to_wire(manifest)
            wire["evaluator_id"] = "caller-evaluator"
            wire = self._resign_wire(wire)
            with self.assertRaisesRegex(ValueError, "evaluator_id"):
                runtime_evidence_manifest_from_wire(wire)

    def test_synchronized_cap_and_validator_rebinding_cannot_expand_body(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())
        wire["source_closure"] = [
            {
                "relative_path": (
                    f"rulespace_v3/x_{index:03d}.py"
                ),
                "sha256": "0" * 64,
            }
            for index in range(RUNTIME_MAX_SOURCE_FILES + 1)
        ]
        wire = self._resign_wire(wire)
        expanded_caps = runtime._RUNTIME_CAPS._replace(
            max_source_files=RUNTIME_MAX_SOURCE_FILES + 1,
        )
        with (
            mock.patch.object(
                runtime,
                "RUNTIME_MAX_SOURCE_FILES",
                RUNTIME_MAX_SOURCE_FILES + 1,
            ),
            mock.patch.object(
                runtime,
                "_RUNTIME_CAPS",
                expanded_caps,
            ),
            mock.patch.object(
                runtime,
                "_source_closure",
                side_effect=lambda value, *args, **kwargs: value,
            ),
            mock.patch.object(
                runtime,
                "_validate_runtime_manifest_fields",
                return_value=None,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                runtime_evidence_manifest_from_wire(wire)

    def test_public_serializers_keep_caps_when_validators_are_rebound(self):
        manifest = self._manifest()
        oversized_closure = tuple(
            (
                f"rulespace_v3/x_{index:03d}.py",
                "0" * 64,
            )
            for index in range(RUNTIME_MAX_SOURCE_FILES + 1)
        )
        expanded_caps = runtime._RUNTIME_CAPS._replace(
            max_source_files=RUNTIME_MAX_SOURCE_FILES + 1,
        )
        with (
            mock.patch.object(
                runtime,
                "RUNTIME_MAX_SOURCE_FILES",
                RUNTIME_MAX_SOURCE_FILES + 1,
            ),
            mock.patch.object(
                runtime,
                "_RUNTIME_CAPS",
                expanded_caps,
            ),
            mock.patch.object(
                runtime,
                "_source_closure",
                side_effect=lambda value, *args, **kwargs: value,
            ),
            mock.patch.object(
                runtime,
                "_validate_runtime_manifest_fields",
                return_value=None,
            ),
        ):
            oversized = self._unchecked_replace(
                manifest,
                source_closure=oversized_closure,
            )
            with self.assertRaisesRegex(ValueError, "resource cap"):
                runtime_evidence_manifest_payload(oversized)
            with self.assertRaisesRegex(ValueError, "resource cap"):
                runtime_evidence_manifest_to_wire(oversized)

    def test_hash_and_public_payload_rebinding_cannot_accept_forgery(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())
        wire["python_version"] = "caller-python"
        wire["runtime_manifest_sha"] = "f" * 64
        with (
            mock.patch.object(
                runtime,
                "canonical_sha",
                return_value="f" * 64,
            ),
            mock.patch.object(
                runtime,
                "runtime_evidence_manifest_payload",
                return_value={},
            ),
            mock.patch.object(
                runtime,
                "_validate_runtime_manifest_fields",
                return_value=None,
            ),
            mock.patch.object(
                runtime,
                "_preflight_canonical_payload",
                return_value=None,
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "runtime_manifest_sha",
            ):
                runtime_evidence_manifest_from_wire(wire)

    def test_record_and_validator_rebinding_cannot_replace_hydrated_type(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())

        def passthrough(value, *args, **kwargs):
            return value

        with (
            mock.patch.object(
                runtime,
                "RuntimeEvidenceManifest",
                types.SimpleNamespace,
            ),
            mock.patch.object(
                runtime,
                "_exact_mapping_fields",
                side_effect=passthrough,
            ),
            mock.patch.object(
                runtime,
                "_text",
                side_effect=passthrough,
            ),
            mock.patch.object(
                runtime,
                "_relative_source_path",
                side_effect=passthrough,
            ),
            mock.patch.object(
                runtime,
                "_sha",
                side_effect=passthrough,
            ),
            mock.patch.object(
                runtime,
                "_source_closure",
                side_effect=passthrough,
            ),
            mock.patch.object(
                runtime,
                "_validate_runtime_manifest_fields",
                return_value=None,
            ),
        ):
            hydrated = runtime_evidence_manifest_from_wire(wire)
            self.assertIs(type(hydrated), RuntimeEvidenceManifest)
            self.assertEqual(
                runtime_evidence_manifest_payload(hydrated),
                {
                    key: value
                    for key, value in wire.items()
                    if key != "runtime_manifest_sha"
                },
            )

    def test_regex_rebinding_cannot_accept_a_non_sha_source_digest(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())
        wire["source_closure"][0]["sha256"] = "not-a-sha"
        wire = self._resign_wire(wire)

        class PermissivePattern:
            @staticmethod
            def fullmatch(value):
                return object()

        with mock.patch.object(
            runtime,
            "_LOWER_SHA",
            PermissivePattern(),
        ):
            with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
                runtime_evidence_manifest_from_wire(wire)

    def test_path_class_rebinding_cannot_accept_repository_escape(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())
        wire["source_closure"][0]["relative_path"] = "../outside.py"
        wire = self._resign_wire(wire)

        class PermissivePurePosixPath:
            def __init__(self, value):
                self.value = value
                self.parts = ("rulespace_v3", "runtime.py")
                self.suffix = ".py"

            def is_absolute(self):
                return False

            def __str__(self):
                return self.value

        with mock.patch.object(
            runtime,
            "PurePosixPath",
            PermissivePurePosixPath,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "relative path|inside the repository",
            ):
                runtime_evidence_manifest_from_wire(wire)

    def test_json_and_hash_primitive_rebinding_cannot_forge_self_hash(self):
        for primitive in ("json", "hash"):
            with self.subTest(primitive=primitive):
                wire = runtime_evidence_manifest_to_wire(
                    self._manifest()
                )
                wire["python_version"] = "caller-python"
                if primitive == "json":
                    forged_bytes = b"caller-controlled-canonical-body"
                    wire["runtime_manifest_sha"] = hashlib.sha256(
                        forged_bytes
                    ).hexdigest()
                    patcher = mock.patch.object(
                        runtime.json,
                        "dumps",
                        return_value=forged_bytes.decode("ascii"),
                    )
                else:
                    wire["runtime_manifest_sha"] = "f" * 64
                    forged_digest = mock.Mock()
                    forged_digest.hexdigest.return_value = "f" * 64
                    patcher = mock.patch.object(
                        runtime.hashlib,
                        "sha256",
                        return_value=forged_digest,
                    )
                with patcher:
                    with self.assertRaisesRegex(
                        ValueError,
                        "runtime_manifest_sha",
                    ):
                        runtime_evidence_manifest_from_wire(wire)

    def test_frozen_json_encoder_matches_contract_on_allowed_domain(self):
        value = {
            "z": [
                "quote\" slash\\ controls\b\f\n\r\t\u0001",
                "雪",
                None,
                True,
                False,
                17,
            ],
            "a": {
                "tuple": ("x", "y"),
            },
        }
        self.assertEqual(
            runtime._RUNTIME_JSON_TEXT(value),
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        self.assertEqual(
            runtime._RUNTIME_CANONICAL_SHA(value),
            canonical_sha(value),
        )

    def test_json_decoder_class_rebinding_cannot_forge_probe_output(self):
        manifest = self._manifest()
        forged_probe = {
            "source_closure": [
                list(manifest.source_closure[0]),
            ],
            "python_version": manifest.python_version,
            "numpy_version": manifest.numpy_version,
            "scipy_version": manifest.scipy_version,
            "blas_config_sha": manifest.blas_config_sha,
            "lapack_config_sha": manifest.lapack_config_sha,
            "platform_id": manifest.platform_id,
        }

        class ForgedDecoder:
            def __init__(self, **kwargs):
                pass

            def decode(self, value):
                return forged_probe

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.json"
            path.write_text("{not-json", encoding="utf-8")
            with mock.patch.object(
                runtime.json,
                "JSONDecoder",
                ForgedDecoder,
            ):
                with self.assertRaisesRegex(ValueError, "JSON"):
                    runtime._load_probe_output(path)

    def test_builtin_type_rebinding_cannot_expand_plain_dict_schema(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())

        class DictSubclass(dict):
            pass

        subclass_wire = DictSubclass(wire)

        def forged_type(value):
            if value is subclass_wire:
                return dict
            return builtins.type(value)

        with mock.patch.object(
            runtime,
            "type",
            side_effect=forged_type,
            create=True,
        ):
            with self.assertRaisesRegex(TypeError, "plain dict"):
                runtime_evidence_manifest_from_wire(subclass_wire)

    def test_builtin_len_rebinding_cannot_bypass_frozen_cap(self):
        wire = runtime_evidence_manifest_to_wire(self._manifest())
        closure_size = RUNTIME_MAX_SOURCE_FILES + 1
        wire["source_closure"] = [
            {
                "relative_path": f"rulespace_v3/x_{index:03d}.py",
                "sha256": "0" * 64,
            }
            for index in range(closure_size)
        ]
        wire = self._resign_wire(wire)

        def forged_len(value):
            actual = builtins.len(value)
            if actual == closure_size and builtins.type(value) in (
                list,
                set,
                tuple,
            ):
                return RUNTIME_MAX_SOURCE_FILES
            return actual

        with mock.patch.object(
            runtime,
            "len",
            side_effect=forged_len,
            create=True,
        ):
            with self.assertRaisesRegex(ValueError, "resource cap"):
                runtime_evidence_manifest_from_wire(wire)

    def test_builtin_sorted_rebinding_cannot_accept_noncanonical_closure(self):
        manifest = self._manifest()
        wire = runtime_evidence_manifest_to_wire(manifest)
        second = {
            "relative_path": "rulespace_v3/zz_runtime.py",
            "sha256": "3" * 64,
        }
        wire["source_closure"] = [
            second,
            wire["source_closure"][0],
        ]
        with mock.patch.object(
            runtime,
            "sorted",
            side_effect=lambda value: list(value),
            create=True,
        ):
            body = dict(wire)
            body.pop("runtime_manifest_sha")
            wire["runtime_manifest_sha"] = runtime._RUNTIME_CANONICAL_SHA(
                body
            )
            with self.assertRaisesRegex(ValueError, "canonical"):
                runtime_evidence_manifest_from_wire(wire)

    def test_subprocess_class_rebinding_cannot_replace_frozen_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "probe.json"
            with mock.patch.object(
                runtime.subprocess,
                "Popen",
                side_effect=AssertionError(
                    "module Popen rebinding reached the probe"
                ),
            ) as rebound:
                runtime._launch_probe_subprocess(
                    runtime._MODULE_RUNTIME_AUTHORITY.import_roots,
                    output_path,
                )
            rebound.assert_not_called()
            self.assertGreater(output_path.stat().st_size, 0)

    def test_probe_schema_set_is_also_frozen_against_rebinding(self):
        manifest = self._manifest()
        probe_payload = {
            "source_closure": [
                list(manifest.source_closure[0]),
            ],
            "python_version": manifest.python_version,
            "numpy_version": manifest.numpy_version,
            "scipy_version": manifest.scipy_version,
            "blas_config_sha": manifest.blas_config_sha,
            "lapack_config_sha": manifest.lapack_config_sha,
            "platform_id": manifest.platform_id,
            "caller_probe_label": "forbidden",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.json"
            path.write_text(
                json.dumps(probe_payload),
                encoding="utf-8",
            )
            with mock.patch.object(
                runtime,
                "_PROBE_FIELDS",
                frozenset(
                    (*runtime._PROBE_FIELDS, "caller_probe_label")
                ),
            ):
                with self.assertRaisesRegex(ValueError, "unknown"):
                    runtime._load_probe_output(path)


if __name__ == "__main__":
    unittest.main()
