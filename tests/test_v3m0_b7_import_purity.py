"""Import-purity contract for the B7 reviewer-child replay core."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INIT_PATH = REPOSITORY_ROOT / "rulespace_v3" / "__init__.py"
CORE_PATH = REPOSITORY_ROOT / "rulespace_v3" / "b7_replay_core_v1.py"

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
    assert isinstance(docstring.value.value, str)

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


def test_fresh_python_import_executes_only_initializer_and_core() -> None:
    assert CORE_PATH.is_file(), "B7 pure replay core has not been created"
    audit_program = textwrap.dedent(
        """
        import os
        from pathlib import Path
        import sys

        repository_root = Path.cwd().resolve()
        forbidden_events = {
            "os.chdir",
            "os.chmod",
            "os.chown",
            "os.fork",
            "os.forkpty",
            "os.kill",
            "os.killpg",
            "os.mkdir",
            "os.posix_spawn",
            "os.putenv",
            "os.remove",
            "os.rename",
            "os.rmdir",
            "os.spawn",
            "os.system",
            "os.truncate",
            "os.unsetenv",
            "pty.spawn",
            "subprocess.Popen",
        }
        forbidden_prefixes = ("socket.",)

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
                relative = Path(source).resolve().relative_to(repository_root)
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
        sys.stdout.write("IMPORT_PURE\\n")
        """
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    result = subprocess.run(
        [sys.executable, "-s", "-c", audit_program],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "IMPORT_PURE\n"


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
