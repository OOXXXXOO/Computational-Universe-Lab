"""Import-purity contract for the B7 reviewer-child replay core."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INIT_PATH = REPOSITORY_ROOT / "rulespace_v3" / "__init__.py"
CORE_PATH = REPOSITORY_ROOT / "rulespace_v3" / "b7_replay_core_v1.py"
PACKAGE_DOCSTRING = "V3-M0 immutable contracts and profile-aware evidence primitives."
EXTERNAL_DEPENDENCY_MODULES = (
    "__future__",
    "fractions",
    "hashlib",
    "json",
    "math",
    "numpy",
    "scipy",
    "scipy.linalg",
)
LOCAL_SOURCE_RELATIVE_PATHS = (
    "rulespace_v3/__init__.py",
    "rulespace_v3/b7_replay_core_v1.py",
)
TRUSTED_LOCAL_SOURCE_SHA256 = {
    "rulespace_v3/__init__.py": (
        "00f79cabe2ca6c5696e6056f13c6225a3594a905888488333ca3eed3a616a7a0"
    ),
    "rulespace_v3/b7_replay_core_v1.py": (
        "67ce973d82994aeb8160ca1ddbc5e604401ee8674f0cdd21ec70d1c1501c6bee"
    ),
}
_STAGING_MANIFEST_CACHE: dict[str, object] | None = None

LEGACY_EXPORTS = (
    "FINAL_RESULT_EVIDENCE_FIELDS",
    "BlockStatus",
    "EvidenceEnvelope",
    "RequiredBlockReport",
    "UndefinedReason",
    "canonical_sha",
    "evaluate_required_blocks",
    "validate_evidence_envelope",
    "validate_evidence_fields",
)

LEGACY_EXPORT_MODULES = {
    "FINAL_RESULT_EVIDENCE_FIELDS": "evidence",
    "BlockStatus": "contracts",
    "EvidenceEnvelope": "evidence",
    "RequiredBlockReport": "contracts",
    "UndefinedReason": "contracts",
    "canonical_sha": "evidence",
    "evaluate_required_blocks": "contracts",
    "validate_evidence_envelope": "evidence",
    "validate_evidence_fields": "evidence",
}


def _assert_name(node: ast.AST, expected: str) -> None:
    assert isinstance(node, ast.Name)
    assert node.id == expected


def test_rulespace_initializer_has_exact_lazy_legacy_surface() -> None:
    tree = ast.parse(PACKAGE_INIT_PATH.read_text(encoding="utf-8"))

    assert tuple(type(node) for node in tree.body) == (
        ast.Expr,
        ast.Assign,
        ast.FunctionDef,
    )

    docstring, all_assignment, lazy_getattr = tree.body
    assert isinstance(docstring.value, ast.Constant)
    assert docstring.value.value == PACKAGE_DOCSTRING

    assert len(all_assignment.targets) == 1
    _assert_name(all_assignment.targets[0], "__all__")
    assert ast.literal_eval(all_assignment.value) == LEGACY_EXPORTS

    assert lazy_getattr.name == "__getattr__"
    assert [argument.arg for argument in lazy_getattr.args.args] == ["name"]
    assert lazy_getattr.args.posonlyargs == []
    assert lazy_getattr.args.vararg is None
    assert lazy_getattr.args.kwonlyargs == []
    assert lazy_getattr.args.kw_defaults == []
    assert lazy_getattr.args.kwarg is None
    assert lazy_getattr.args.defaults == []
    assert lazy_getattr.decorator_list == []
    assert lazy_getattr.returns is None
    assert lazy_getattr.type_comment is None
    assert lazy_getattr.args.args[0].annotation is None

    assert len(lazy_getattr.body) == len(LEGACY_EXPORTS) + 1
    for branch, export_name in zip(lazy_getattr.body[:-1], LEGACY_EXPORTS):
        assert isinstance(branch, ast.If)
        assert branch.orelse == []
        assert isinstance(branch.test, ast.Compare)
        _assert_name(branch.test.left, "name")
        assert len(branch.test.ops) == 1
        assert isinstance(branch.test.ops[0], ast.Eq)
        assert len(branch.test.comparators) == 1
        comparator = branch.test.comparators[0]
        assert isinstance(comparator, ast.Constant)
        assert comparator.value == export_name
        assert len(branch.body) == 2

        import_node, return_node = branch.body
        assert isinstance(import_node, ast.ImportFrom)
        assert import_node.level == 1
        assert import_node.module == LEGACY_EXPORT_MODULES[export_name]
        assert [(alias.name, alias.asname) for alias in import_node.names] == [
            (export_name, None)
        ]
        assert isinstance(return_node, ast.Return)
        _assert_name(return_node.value, export_name)

    terminal = lazy_getattr.body[-1]
    assert isinstance(terminal, ast.Raise)
    assert terminal.cause is None
    assert isinstance(terminal.exc, ast.Call)
    _assert_name(terminal.exc.func, "AttributeError")
    assert len(terminal.exc.args) == 1
    _assert_name(terminal.exc.args[0], "name")
    assert terminal.exc.keywords == []


def _materialize_minimal_export(export_root: Path) -> None:
    package_root = export_root / "rulespace_v3"
    package_root.mkdir(parents=True)
    shutil.copy2(PACKAGE_INIT_PATH, package_root / "__init__.py")
    shutil.copy2(CORE_PATH, package_root / "b7_replay_core_v1.py")


def _expected_external_origins() -> dict[str, str]:
    origins: dict[str, str] = {}
    for module_name in EXTERNAL_DEPENDENCY_MODULES:
        specification = importlib.util.find_spec(module_name)
        assert specification is not None
        assert specification.origin is not None
        origins[module_name] = str(Path(specification.origin).resolve())
    return origins


def _local_source_sha256(source_root: Path) -> dict[str, str]:
    return {
        relative_path: hashlib.sha256(
            (source_root / relative_path).read_bytes()
        ).hexdigest()
        for relative_path in LOCAL_SOURCE_RELATIVE_PATHS
    }


def _expected_staging_manifest() -> dict[str, object]:
    global _STAGING_MANIFEST_CACHE
    if _STAGING_MANIFEST_CACHE is not None:
        return _STAGING_MANIFEST_CACHE

    probe_program = textwrap.dedent(
        """
        import dis
        import importlib.util
        import os
        from pathlib import Path
        import sys

        active = False
        open_events = set()
        directory_events = set()
        dynamic_library_events = set()
        import_events = set()
        forbidden_events = {
            "os.chdir", "os.chmod", "os.chown", "os.fork", "os.forkpty",
            "os.kill", "os.killpg", "os.link", "os.mkdir", "os.posix_spawn",
            "os.putenv", "os.remove", "os.rename", "os.rmdir", "os.spawn",
            "os.system", "os.symlink", "os.truncate", "os.unsetenv", "pty.spawn",
            "signal.pthread_kill", "signal.raise_signal", "subprocess.Popen",
        }

        def normalize_path(raw):
            if isinstance(raw, bytes):
                raw = os.fsdecode(raw)
            if isinstance(raw, os.PathLike):
                raw = os.fspath(raw)
            if not isinstance(raw, str) or raw in {"built-in", "frozen"}:
                return raw
            return os.path.abspath(raw)

        def audit(event, arguments):
            if not active:
                return
            if event in forbidden_events or event.startswith("socket."):
                raise OSError(f"staging probe rejected capability event: {event}")
            if event == "open":
                mode = arguments[1]
                flags = arguments[2]
                write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
                if isinstance(mode, str) and any(token in mode for token in "wax+"):
                    raise OSError("staging probe rejected filesystem write")
                if isinstance(flags, int) and flags & write_flags:
                    raise OSError("staging probe rejected filesystem write")
                if not isinstance(arguments[0], (str, bytes, os.PathLike)):
                    raise OSError("staging probe rejected non-path file access")
                open_events.add(normalize_path(arguments[0]))
            elif event in {"os.listdir", "os.scandir"}:
                if not isinstance(arguments[0], (str, bytes, os.PathLike)):
                    raise OSError("staging probe rejected non-path directory access")
                directory_events.add((event, normalize_path(arguments[0])))
            elif event.startswith("ctypes.dl"):
                value = normalize_path(arguments[0]) if arguments else None
                dynamic_library_events.add((event, value))
            elif event == "import":
                import_events.add(
                    (
                        arguments[0],
                        (
                            normalize_path(arguments[1])
                            if arguments[1] is not None
                            else None
                        ),
                    )
                )

        export_root = Path.cwd().resolve()
        sys.path[:] = [
            entry
            for entry in sys.path
            if Path(entry or os.curdir).resolve() != export_root
        ]
        sys.addaudithook(audit)
        modules_before_staging = set(sys.modules)
        active = True
        for external_name in (
            "__future__", "fractions", "hashlib", "json", "math", "numpy", "scipy"
        ):
            __import__(external_name)
        __import__("scipy.linalg")
        active = False

        loaded_module_origins = []
        for name in sorted(set(sys.modules).difference(modules_before_staging)):
            module = sys.modules[name]
            source = getattr(module, "__file__", None)
            specification = getattr(module, "__spec__", None)
            origin = source if source is not None else getattr(specification, "origin", None)
            loaded_module_origins.append((name, normalize_path(origin)))

        manifest = {
            "open_events": tuple(sorted(open_events)),
            "directory_events": tuple(sorted(directory_events)),
            "dynamic_library_events": tuple(
                sorted(dynamic_library_events, key=repr)
            ),
            "import_events": tuple(sorted(import_events, key=repr)),
            "loaded_module_origins": tuple(loaded_module_origins),
        }
        print(repr(manifest))
        """
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["OPENBLAS_MAIN_FREE"] = "1"
    environment["GOTOBLAS_MAIN_FREE"] = "1"
    result = subprocess.run(
        [sys.executable, "-s", "-B", "-c", probe_program],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    parsed = ast.literal_eval(result.stdout)
    assert isinstance(parsed, dict)
    assert set(parsed) == {
        "open_events",
        "directory_events",
        "dynamic_library_events",
        "import_events",
        "loaded_module_origins",
    }
    _STAGING_MANIFEST_CACHE = parsed
    return parsed


def _run_fresh_import_audit(
    export_root: Path,
    *,
    expected_local_source_sha256: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    expected_external_origins = _expected_external_origins()
    staging_manifest = _expected_staging_manifest()
    assert _local_source_sha256(REPOSITORY_ROOT) == TRUSTED_LOCAL_SOURCE_SHA256
    trusted_local_sha256 = (
        TRUSTED_LOCAL_SOURCE_SHA256
        if expected_local_source_sha256 is None
        else expected_local_source_sha256
    )
    assert set(trusted_local_sha256) == set(LOCAL_SOURCE_RELATIVE_PATHS)
    assert all(
        len(value) == 64 and set(value) <= set("0123456789abcdef")
        for value in trusted_local_sha256.values()
    )

    audit_program = textwrap.dedent(
        """
        import dis
        import importlib.util
        import os
        from pathlib import Path
        import sys

        export_root = Path.cwd().resolve()
        package_root = export_root / "rulespace_v3"
        approved_external_origins = {
            name: Path(origin).resolve()
            for name, origin in __EXPECTED_EXTERNAL_ORIGINS__.items()
        }
        trusted_local_sha256 = __TRUSTED_LOCAL_SHA256__
        staging_manifest = __STAGING_MANIFEST__
        trusted_staging_open_events = set(staging_manifest["open_events"])
        trusted_staging_directory_events = set(staging_manifest["directory_events"])
        trusted_staging_dynamic_library_events = set(
            staging_manifest["dynamic_library_events"]
        )
        trusted_staging_import_events = set(staging_manifest["import_events"])
        trusted_staging_module_origins = dict(
            staging_manifest["loaded_module_origins"]
        )
        approved_local_sources = {
            export_root / relative_path for relative_path in trusted_local_sha256
        }
        approved_local_source_strings = {
            os.path.abspath(os.fspath(path)) for path in approved_local_sources
        }
        approved_local_loader_reads = set(approved_local_source_strings)
        approved_local_loader_reads.update(
            os.path.abspath(importlib.util.cache_from_source(os.fspath(path)))
            for path in approved_local_sources
        )
        forbidden_events = {
            "os.chdir", "os.chmod", "os.chown", "os.fork", "os.forkpty",
            "os.kill", "os.killpg", "os.link", "os.mkdir", "os.posix_spawn",
            "os.putenv", "os.remove", "os.rename", "os.rmdir", "os.spawn",
            "os.system", "os.symlink", "os.truncate", "os.unsetenv", "pty.spawn",
            "signal.pthread_kill", "signal.raise_signal", "subprocess.Popen",
        }
        external_roots = (
            "__future__", "fractions", "hashlib", "json", "math", "numpy", "scipy"
        )

        def normalize_event_path(raw):
            if isinstance(raw, bytes):
                raw = os.fsdecode(raw)
            if isinstance(raw, os.PathLike):
                raw = os.fspath(raw)
            if not isinstance(raw, str) or raw in {"built-in", "frozen"}:
                return raw
            return os.path.abspath(raw)

        def local_body_is_executing():
            frame = sys._getframe(1)
            while frame is not None:
                filename = normalize_event_path(frame.f_code.co_filename)
                if filename in approved_local_source_strings:
                    return True
                frame = frame.f_back
            return False

        audit_phase = "staging"

        def reject_capability(event):
            raise OSError(f"forbidden audit capability event during {audit_phase}: {event}")

        def validate_read_only_open(arguments):
            mode = arguments[1]
            flags = arguments[2]
            write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            if isinstance(mode, str) and any(token in mode for token in "wax+"):
                reject_capability("filesystem-write")
            if isinstance(flags, int) and flags & write_flags:
                reject_capability("filesystem-write")
            if not isinstance(arguments[0], (str, bytes, os.PathLike)):
                reject_capability("non-path-file-access")
            return normalize_event_path(arguments[0])

        def audit(event, arguments):
            if event in forbidden_events or event.startswith("socket."):
                reject_capability(event)
            if event == "open":
                path = validate_read_only_open(arguments)
                if audit_phase == "staging":
                    if path not in trusted_staging_open_events:
                        reject_capability(f"untrusted-staging-open:{path}")
                    return
                if audit_phase == "identity":
                    if path not in approved_local_source_strings:
                        reject_capability(f"untrusted-identity-open:{path}")
                    return
                if audit_phase == "core":
                    if local_body_is_executing():
                        reject_capability("local-module-body-open")
                    if path not in approved_local_loader_reads:
                        reject_capability(f"untrusted-local-loader-open:{path}")
                    return
                reject_capability(f"post-import-open:{path}")
            if event in {"os.listdir", "os.scandir"}:
                if not isinstance(arguments[0], (str, bytes, os.PathLike)):
                    reject_capability("non-path-directory-access")
                signature = (event, normalize_event_path(arguments[0]))
                if audit_phase == "staging":
                    if signature not in trusted_staging_directory_events:
                        reject_capability(f"untrusted-staging-directory:{signature!r}")
                    return
                if audit_phase == "core" and not local_body_is_executing():
                    if signature[1] == os.path.abspath(os.fspath(package_root)):
                        return
                reject_capability(f"local-module-body-directory:{signature!r}")
            if event.startswith("ctypes.dl"):
                signature = (
                    event,
                    normalize_event_path(arguments[0]) if arguments else None,
                )
                if (
                    audit_phase == "staging"
                    and signature in trusted_staging_dynamic_library_events
                ):
                    return
                reject_capability(f"dynamic-library:{signature!r}")
            if event == "import":
                signature = (
                    arguments[0],
                    normalize_event_path(arguments[1]) if arguments[1] is not None else None,
                )
                if audit_phase == "staging":
                    if signature not in trusted_staging_import_events:
                        reject_capability(f"untrusted-staging-import:{signature!r}")
                    return
                if audit_phase == "core" and not local_body_is_executing():
                    if signature[0] in {
                        "rulespace_v3",
                        "rulespace_v3.b7_replay_core_v1",
                    } and (
                        signature[1] is None
                        or signature[1] in approved_local_loader_reads
                    ):
                        return
                reject_capability(f"local-module-body-import:{signature!r}")

        for external_name in external_roots:
            if external_name in sys.modules:
                raise RuntimeError(f"external module was unexpectedly preloaded: {external_name}")
            specification = importlib.util.find_spec(external_name)
            if specification is None or specification.origin is None:
                raise RuntimeError(f"external module has no static origin: {external_name}")
            origin = Path(specification.origin).resolve()
            if origin != approved_external_origins[external_name]:
                raise RuntimeError(
                    f"unapproved external import origin for {external_name}: {origin}"
                )

        original_search_path = list(sys.path)
        sys.path[:] = [
            entry
            for entry in original_search_path
            if Path(entry or os.curdir).resolve() != export_root
        ]
        sys.addaudithook(audit)
        modules_before_staging = set(sys.modules)
        try:
            for external_name in external_roots:
                __import__(external_name)
            specification = importlib.util.find_spec("scipy.linalg")
            if specification is None or specification.origin is None:
                raise RuntimeError("external module has no static origin: scipy.linalg")
            origin = Path(specification.origin).resolve()
            if origin != approved_external_origins["scipy.linalg"]:
                raise RuntimeError(
                    f"unapproved external import origin for scipy.linalg: {origin}"
                )
            __import__("scipy.linalg")
        finally:
            sys.path[:] = original_search_path
        audit_phase = "post-staging"

        staged_module_names = set(sys.modules).difference(modules_before_staging)
        observed_staged_origins = {}
        for name in sorted(staged_module_names):
            module = sys.modules[name]
            source = getattr(module, "__file__", None)
            specification = getattr(module, "__spec__", None)
            origin = source if source is not None else getattr(specification, "origin", None)
            observed_staged_origins[name] = normalize_event_path(origin)
        if observed_staged_origins != trusted_staging_module_origins:
            raise RuntimeError("frozen external staging module closure drifted")

        for external_name, expected_origin in approved_external_origins.items():
            module = sys.modules.get(external_name)
            if module is None:
                raise RuntimeError(f"approved external module was not staged: {external_name}")
            source = getattr(module, "__file__", None)
            if source is None or Path(source).resolve() != expected_origin:
                raise RuntimeError(
                    f"unapproved loaded-module origin: {external_name} from {source}"
                )

        staged_module_identities = {
            name: sys.modules[name] for name in staged_module_names
        }
        protected_namespace_names = (
            "fractions", "hashlib", "json", "math", "numpy", "numpy.linalg",
            "scipy", "scipy.linalg",
        )

        def namespace_fingerprint(module_name):
            module = sys.modules[module_name]
            return tuple(sorted((name, id(value)) for name, value in vars(module).items()))

        protected_namespace_fingerprints = {
            name: namespace_fingerprint(name) for name in protected_namespace_names
        }

        def resolve_binding(module_name, *attribute_path):
            value = sys.modules[module_name]
            for attribute_name in attribute_path:
                value = vars(value)[attribute_name]
            return value

        critical_binding_specs = (
            ("numpy.ndarray", "numpy", "ndarray"),
            ("numpy.asarray", "numpy", "asarray"),
            ("numpy.linalg.inv", "numpy.linalg", "inv"),
            ("scipy.linalg.schur", "scipy.linalg", "schur"),
            ("math.cos", "math", "cos"),
            ("math.hypot", "math", "hypot"),
            ("fractions.Fraction", "fractions", "Fraction"),
            ("hashlib.sha256", "hashlib", "sha256"),
            ("json.dumps", "json", "dumps"),
            ("json.loads", "json", "loads"),
        )
        critical_binding_identities = {
            label: resolve_binding(module_name, *attribute_path)
            for label, module_name, *attribute_path in critical_binding_specs
        }

        audit_phase = "identity"
        hashlib_module = sys.modules["hashlib"]
        for relative_path, expected_sha256 in trusted_local_sha256.items():
            source_path = export_root / relative_path
            observed_sha256 = hashlib_module.sha256(source_path.read_bytes()).hexdigest()
            if observed_sha256 != expected_sha256:
                raise RuntimeError(f"untrusted local source identity: {relative_path}")

        allowed_core_imports = {
            ("__future__", ("annotations",), 0),
            ("hashlib", (), 0),
            ("json", (), 0),
            ("math", (), 0),
            ("fractions", ("Fraction",), 0),
            ("numpy", (), 0),
            ("scipy.linalg", (), 0),
        }
        import_name_opcode = dis.opmap["IMPORT_NAME"]
        builtins_module = sys.modules["builtins"]
        original_import = builtins_module.__import__
        core_source_path = os.path.abspath(
            os.fspath(export_root / "rulespace_v3" / "b7_replay_core_v1.py")
        )

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            caller = sys._getframe(1)
            caller_path = normalize_event_path(caller.f_code.co_filename)
            if caller_path in approved_local_source_strings:
                if caller.f_code.co_code[caller.f_lasti] != import_name_opcode:
                    raise RuntimeError("dynamic import from local module body is forbidden")
                signature = (name, tuple(fromlist or ()), level)
                if caller_path != core_source_path or signature not in allowed_core_imports:
                    raise RuntimeError(f"forbidden local static import: {signature!r}")
            return original_import(name, globals, locals, fromlist, level)

        modules_before_core = set(sys.modules)
        builtins_module.__import__ = guarded_import
        audit_phase = "core"
        try:
            original_import("rulespace_v3.b7_replay_core_v1")
        finally:
            audit_phase = "post-import"
            builtins_module.__import__ = original_import

        for name, expected_module in staged_module_identities.items():
            if sys.modules.get(name) is not expected_module:
                raise RuntimeError(f"preloaded external module identity changed: {name}")
        for name, expected_fingerprint in protected_namespace_fingerprints.items():
            if namespace_fingerprint(name) != expected_fingerprint:
                raise RuntimeError(f"preloaded external namespace changed: {name}")
        for label, module_name, *attribute_path in critical_binding_specs:
            if (
                resolve_binding(module_name, *attribute_path)
                is not critical_binding_identities[label]
            ):
                raise RuntimeError(f"preloaded critical binding changed: {label}")

        forbidden_modules = {
            "rulespace_v3.contracts", "rulespace_v3.evidence",
            "rulespace_v3.response", "rulespace_v3.runtime",
        }
        loaded_forbidden = forbidden_modules.intersection(sys.modules)
        if loaded_forbidden:
            raise RuntimeError(f"forbidden rulespace modules loaded: {sorted(loaded_forbidden)}")

        expected_local_modules = {
            "rulespace_v3": "rulespace_v3/__init__.py",
            "rulespace_v3.b7_replay_core_v1": "rulespace_v3/b7_replay_core_v1.py",
        }
        loaded_after_core = set(sys.modules).difference(modules_before_core)
        if loaded_after_core != set(expected_local_modules):
            raise RuntimeError(
                "unexpected imported module set: "
                f"missing={sorted(set(expected_local_modules) - loaded_after_core)!r}, "
                f"extra={sorted(loaded_after_core - set(expected_local_modules))!r}"
            )
        observed_local_modules = {}
        for name in loaded_after_core:
            module = sys.modules[name]
            source = getattr(module, "__file__", None)
            if source is None:
                raise RuntimeError(f"imported local module has no origin: {name}")
            relative = Path(source).resolve().relative_to(export_root).as_posix()
            observed_local_modules[name] = relative
        if observed_local_modules != expected_local_modules:
            raise RuntimeError(f"unexpected local import closure: {observed_local_modules!r}")
        sys.stdout.write("IMPORT_PURE\\n")
        """
    )
    audit_program = audit_program.replace(
        "__EXPECTED_EXTERNAL_ORIGINS__", repr(expected_external_origins)
    )
    audit_program = audit_program.replace(
        "__TRUSTED_LOCAL_SHA256__", repr(trusted_local_sha256)
    )
    audit_program = audit_program.replace(
        "__STAGING_MANIFEST__", repr(staging_manifest)
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["OPENBLAS_MAIN_FREE"] = "1"
    environment["GOTOBLAS_MAIN_FREE"] = "1"
    result = subprocess.run(
        [sys.executable, "-s", "-B", "-c", audit_program],
        cwd=export_root,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    return result


def test_fresh_python_import_executes_only_initializer_and_core(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    _materialize_minimal_export(export_root)
    result = _run_fresh_import_audit(export_root)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "IMPORT_PURE\n"


@pytest.mark.parametrize(
    "relative_path",
    [
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
    ],
)
def test_fresh_import_rejects_untrusted_local_source_identity(
    tmp_path: Path,
    relative_path: str,
) -> None:
    export_root = tmp_path / "source-identity-export"
    _materialize_minimal_export(export_root)
    source_path = export_root / relative_path
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + "\npass\n",
        encoding="utf-8",
    )

    result = _run_fresh_import_audit(export_root)

    assert result.returncode != 0
    assert "untrusted local source identity" in result.stderr


@pytest.mark.parametrize(
    "shadow_name",
    [
        "fractions.py",
        "hashlib.py",
        "json.py",
        "math.py",
        "numpy.py",
        "scipy.py",
    ],
)
def test_fresh_import_rejects_repository_root_external_shadow(
    tmp_path: Path,
    shadow_name: str,
) -> None:
    export_root = tmp_path / "shadow-export"
    _materialize_minimal_export(export_root)
    (export_root / shadow_name).write_text(
        "raise RuntimeError('shadow module executed')\n",
        encoding="utf-8",
    )

    result = _run_fresh_import_audit(export_root)

    assert result.returncode != 0
    assert "unapproved external import origin" in result.stderr
    assert "shadow module executed" not in result.stderr


@pytest.mark.parametrize(
    ("attack_source", "forbidden_path"),
    [
        ("import os\nos.system('/usr/bin/touch process-escaped')\n", "process-escaped"),
        ("import socket\nsocket.socket()\n", None),
        ("open('write-escaped', 'w')\n", "write-escaped"),
        ("import os\nos.putenv('B7_ESCAPE', '1')\n", None),
        pytest.param("__import__('os')\n", None, id="dynamic-import-preloaded-os"),
        pytest.param("import os\n", None, id="static-import-preloaded-os"),
        pytest.param(
            "open(__file__, 'r').read()\n",
            None,
            id="core-body-local-source-read",
        ),
        pytest.param(
            "import os\nos.listdir('.')\n",
            None,
            id="core-body-directory-read",
        ),
        pytest.param(
            "import os\nos.environ.get('PATH')\n",
            None,
            id="core-body-environment-read",
        ),
        pytest.param(
            "import time\ntime.time()\n",
            None,
            id="core-body-clock-read",
        ),
    ],
)
def test_fresh_import_audit_blocks_side_effects_before_execution(
    tmp_path: Path,
    attack_source: str,
    forbidden_path: str | None,
) -> None:
    export_root = tmp_path / "attack-export"
    _materialize_minimal_export(export_root)
    core_path = export_root / "rulespace_v3" / "b7_replay_core_v1.py"
    core_path.write_text(
        core_path.read_text(encoding="utf-8") + "\n" + attack_source,
        encoding="utf-8",
    )

    result = _run_fresh_import_audit(
        export_root,
        expected_local_source_sha256=_local_source_sha256(export_root),
    )

    assert result.returncode != 0
    assert "untrusted local source identity" not in result.stderr
    if forbidden_path is not None:
        assert not (export_root / forbidden_path).exists()


def test_fresh_import_rejects_initializer_preloaded_dependency_poison(
    tmp_path: Path,
) -> None:
    export_root = tmp_path / "dependency-poison-export"
    _materialize_minimal_export(export_root)
    package_init_path = export_root / "rulespace_v3" / "__init__.py"
    package_init_path.write_text(
        package_init_path.read_text(encoding="utf-8")
        + "\nimport sys\n"
        + "sys.modules['numpy'].asarray = sys.modules['os'].system\n",
        encoding="utf-8",
    )

    result = _run_fresh_import_audit(
        export_root,
        expected_local_source_sha256=_local_source_sha256(export_root),
    )

    assert result.returncode != 0
    assert "untrusted local source identity" not in result.stderr


def test_lazy_package_exports_preserve_legacy_object_identity() -> None:
    identity_program = textwrap.dedent(
        """
        import rulespace_v3
        from rulespace_v3 import contracts, evidence

        expected = {
            "FINAL_RESULT_EVIDENCE_FIELDS": evidence.FINAL_RESULT_EVIDENCE_FIELDS,
            "BlockStatus": contracts.BlockStatus,
            "EvidenceEnvelope": evidence.EvidenceEnvelope,
            "RequiredBlockReport": contracts.RequiredBlockReport,
            "UndefinedReason": contracts.UndefinedReason,
            "canonical_sha": evidence.canonical_sha,
            "evaluate_required_blocks": contracts.evaluate_required_blocks,
            "validate_evidence_envelope": evidence.validate_evidence_envelope,
            "validate_evidence_fields": evidence.validate_evidence_fields,
        }
        if tuple(rulespace_v3.__all__) != tuple(expected):
            raise RuntimeError("legacy __all__ drifted")
        for name, value in expected.items():
            if getattr(rulespace_v3, name) is not value:
                raise RuntimeError(f"legacy export identity drifted: {name}")
        """
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-s", "-c", identity_program],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
