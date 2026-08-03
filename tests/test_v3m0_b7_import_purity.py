"""Import-purity contract for the B7 reviewer-child replay core."""

from __future__ import annotations

import ast
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


def _run_fresh_import_audit(export_root: Path) -> subprocess.CompletedProcess[str]:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    expected_external_origins = _expected_external_origins()
    audit_program = textwrap.dedent(
        """
        import importlib.util
        import os
        from pathlib import Path
        import sys

        export_root = Path.cwd().resolve()
        stdlib_root = Path(os.__file__).resolve().parent
        approved_external_origins = {
            name: Path(origin).resolve()
            for name, origin in __EXPECTED_EXTERNAL_ORIGINS__.items()
        }
        approved_local_sources = {
            export_root / "rulespace_v3" / "__init__.py",
            export_root / "rulespace_v3" / "b7_replay_core_v1.py",
        }
        approved_local_reads = set(approved_local_sources)
        approved_local_reads.update(
            Path(importlib.util.cache_from_source(str(path))).resolve()
            for path in approved_local_sources
        )
        for extension_name in ("_blake2", "_hashlib", "_json", "_sha3"):
            specification = importlib.util.find_spec(extension_name)
            if specification is None or specification.origin is None:
                raise RuntimeError(f"frozen extension is unavailable: {extension_name}")
            origin = Path(specification.origin).resolve()
            try:
                origin.relative_to(stdlib_root)
            except ValueError as exc:
                raise RuntimeError(
                    f"frozen extension escaped stdlib: {extension_name} from {origin}"
                ) from exc
        forbidden_events = {
            "os.chdir",
            "os.chmod",
            "os.chown",
            "os.fork",
            "os.forkpty",
            "os.kill",
            "os.killpg",
            "os.link",
            "os.mkdir",
            "os.posix_spawn",
            "os.putenv",
            "os.remove",
            "os.rename",
            "os.rmdir",
            "os.spawn",
            "os.system",
            "os.symlink",
            "os.truncate",
            "os.unsetenv",
            "pty.spawn",
            "signal.pthread_kill",
            "signal.raise_signal",
            "subprocess.Popen",
        }
        forbidden_prefixes = ("socket.",)

        def is_within(path, root):
            try:
                path.relative_to(root)
            except ValueError:
                return False
            return True

        def audit(event, arguments):
            if event in forbidden_events or event.startswith(forbidden_prefixes):
                raise RuntimeError(f"forbidden audit event during core import: {event}")
            if event == "open":
                mode = arguments[1]
                flags = arguments[2]
                if isinstance(mode, str) and any(token in mode for token in "wax+"):
                    raise RuntimeError("filesystem write during core import")
                write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
                if isinstance(flags, int) and flags & write_flags:
                    raise RuntimeError("filesystem write during core import")
                if not isinstance(arguments[0], (str, bytes, os.PathLike)):
                    raise RuntimeError("non-path filesystem read during core import")
                path = Path(arguments[0]).resolve()
                if path not in approved_local_reads:
                    raise RuntimeError(f"unapproved file-read origin during core import: {path}")

        external_roots = (
            "__future__",
            "fractions",
            "hashlib",
            "json",
            "math",
            "numpy",
            "scipy",
        )
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

        for external_name, expected_origin in approved_external_origins.items():
            module = sys.modules.get(external_name)
            if module is None:
                raise RuntimeError(f"approved external module was not staged: {external_name}")
            source = getattr(module, "__file__", None)
            if source is None:
                raise RuntimeError(f"approved external module has no file origin: {external_name}")
            origin = Path(source).resolve()
            if origin != expected_origin:
                raise RuntimeError(
                    f"unapproved loaded-module origin: {external_name} from {origin}"
                )

        modules_before_core = set(sys.modules)
        sys.addaudithook(audit)
        __import__("rulespace_v3.b7_replay_core_v1")

        forbidden_modules = {
            "rulespace_v3.contracts",
            "rulespace_v3.evidence",
            "rulespace_v3.response",
            "rulespace_v3.runtime",
        }
        loaded_forbidden = forbidden_modules.intersection(sys.modules)
        if loaded_forbidden:
            raise RuntimeError(f"forbidden rulespace modules loaded: {sorted(loaded_forbidden)}")

        local_modules = {}
        for name, module in tuple(sys.modules.items()):
            source = getattr(module, "__file__", None)
            if source is None:
                continue
            try:
                relative = Path(source).resolve().relative_to(export_root)
            except ValueError:
                continue
            if relative.parts and relative.parts[0] == "rulespace_v3":
                local_modules[name] = relative.as_posix()

        expected = {
            "rulespace_v3": "rulespace_v3/__init__.py",
            "rulespace_v3.b7_replay_core_v1": "rulespace_v3/b7_replay_core_v1.py",
        }
        if local_modules != expected:
            raise RuntimeError(f"unexpected local import closure: {local_modules!r}")

        loaded_after_core = set(sys.modules).difference(modules_before_core)
        expected_loaded = set(expected)
        if loaded_after_core != expected_loaded:
            raise RuntimeError(
                "unexpected imported module set: "
                f"missing={sorted(expected_loaded - loaded_after_core)!r}, "
                f"extra={sorted(loaded_after_core - expected_loaded)!r}"
            )
        for name in loaded_after_core:
            module = sys.modules[name]
            source = getattr(module, "__file__", None)
            if source is None:
                raise RuntimeError(f"imported module has no file origin: {name}")
            origin = Path(source).resolve()
            if origin in approved_local_sources:
                continue
            raise RuntimeError(f"unapproved loaded-module origin: {name} from {origin}")
        sys.stdout.write("IMPORT_PURE\\n")
        """
    ).replace("__EXPECTED_EXTERNAL_ORIGINS__", repr(expected_external_origins))
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    result = subprocess.run(
        [sys.executable, "-s", "-c", audit_program],
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

    result = _run_fresh_import_audit(export_root)

    assert result.returncode != 0
    if forbidden_path is not None:
        assert not (export_root / forbidden_path).exists()


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
