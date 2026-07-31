#!/usr/bin/env python3
"""Build/check the conditional V3-M0 formal and exact no-go bridge.

This program deliberately does not call the production real-space factory or
the impulse-kernel measurement.  The v2 pilot did not persist raw kernels, so
the strongest honest bridge is a source-SHA-locked static-symbol
reconstruction plus replay of the scalars that were actually persisted.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import sympy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rulespace_v2 import epsilon as EPS
from rulespace_v2 import frozen as FROZEN
from rulespace_v2 import invariants as INV
from rulespace_v2 import m3_family as FAMILY
from rulespace_v2 import m3_local_family as LOCAL
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.exact import exact_profile, verify_exact_certificate


DEFAULT_PARENT = ROOT / "data/results/v2m3_pilot.json"
DEFAULT_OUTPUT = ROOT / "data/results/v3m0_formal_nogo.json"
FORMAL_ROOT = ROOT / "formal/v3m0"
PARENT_SHA = "6358edc238095c7662b2a5e91c3a62ba72eac066cca57c8d6e70b5586b8caab0"
PARENT_MANIFEST_SHA = "9807e2aad9261d44c35d34816e84e359afd56a705fc313b988326931f159c39e"
LOCAL_CERT_SHA = "a693d0a4a4edfb844b1caf1f2486ec6c0e492f768f9fe2af9f56acbb1d522eb9"
COISOMETRY_TOL = 1e-12
DIRECTIONS = (
    ("axial", (1, 0, 0)),
    ("face-diagonal", (1, 1, 0)),
    ("body-diagonal", (1, 1, 1)),
)
FROZEN_STATIC_DEPENDENCIES = (
    "experiments/r15_walk_dedonder.py",
    "experiments/r32_reachability_probe.py",
    "experiments/r25_auxiliary_wilson_complex.py",
)
STATIC_CLOSURE_ROOT_MODULES = (
    "experiments",
    "rulespace_v2.epsilon",
    "rulespace_v2.frozen",
    "rulespace_v2.invariants",
    "rulespace_v2.m3_family",
    "rulespace_v2.m3_local_family",
    "rulespace_v3",
    "r15_walk_dedonder",
    "r32_reachability_probe",
    "r25_auxiliary_wilson_complex",
)
V3_SOURCE_FILES = (
    "rulespace_v3/evidence.py",
    "rulespace_v3/exact.py",
    "experiments/v3m0_formal_nogo.py",
)
REQUIRED_RUNTIME_BOOTSTRAP_FILES = (
    "experiments/__init__.py",
    "experiments/r10_current_generator.py",
    "rulespace_v3/__init__.py",
    "rulespace_v3/contracts.py",
)
STATIC_CLOSURE_FREEZE = {
    "experiments/__init__.py": {
        "sha256": "1b4bb82a4493cbf123326d43960ab6232ed0eb6aaec75205acb4c2773b1dc4bd",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "experiments/cp1_v4_L1.py": {
        "sha256": "4dad03be4319da896f485d954f0efc97bc0a6f781700f97e3e8120178a5c6035",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "experiments/cp1_v4_L2.py": {
        "sha256": "556e56665766b29c22eedf226645e3530c95c8ddc27e2b99527eb6158a70fb67",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "experiments/cp1_v4_L3.py": {
        "sha256": "dc7cdbea20e47328d0b652a5a9aefd25d8c8c2fae3f9d82b71926c02c150a9a3",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "experiments/cp1_v4_damping.py": {
        "sha256": "0b868b0ffda835ff3cfdf0306952e71fc83599b4d25526756098736c1784c8ab",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "experiments/r10_current_generator.py": {
        "sha256": "da8c8c49ab323ba14d239a89682f00dfd81b0d8ccfd1b7082ac938a4c06623bd",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "experiments/r15_walk_dedonder.py": {
        "sha256": "ce10bc05c5caa487154a72a4169a1095930afe2afd2d84e4f49bba1041bb18cc",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "experiments/r17_placement_operators.py": {
        "sha256": "957bfa91284815c5223f7b41b7cb6cbd22dbaab4d7343ffe781e938a037340cf",
        "authority": "parent.protocol.frozen_verification.record_only",
    },
    "experiments/r18_realspace_damping.py": {
        "sha256": "1aa478ae379cec8935c7e3dbaa44675739eae68d7b20f27e2d083b7a08d6fa23",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "experiments/r25_auxiliary_wilson_complex.py": {
        "sha256": "48eb8653dde48315104e0843d03c88e9947dd13fc2e5642a6264504e9330c1bd",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "experiments/r25_detour_complex.py": {
        "sha256": "ba65bb4ff5d2a3706fdc9714f982f9b5b4836beb31d41b49f5fdd116a9d05112",
        "authority": "data/results/r25_detour_results.json.source_sha256",
    },
    "experiments/r25_dynamic_symbol.py": {
        "sha256": "a2f458f61c61caf125eb59e700f20c5e603def3b98cdb1ca9169db9e1933bfdb",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "experiments/r25_laurent_complex.py": {
        "sha256": "0df01b2ba3b5e6218dba926b6ad72ebd1de3d087e64b75d3f28ac748a9a66bb1",
        "authority": "data/results/r25_laurent_results.json.source_sha256",
    },
    "experiments/r25_realspace_step.py": {
        "sha256": "a66f6082e03c45b55687ad60859257e0993dc04f30185e212ff3e4bd62331445",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "experiments/r25_static_newton.py": {
        "sha256": "79bdefb16219677f9c1d4365cc66f322e7c5b0c9d0b6f0f678efd95b901ca343",
        "authority": "data/results/r25_static_newton_results.json.source_sha256",
    },
    "experiments/r25_walk_dedonder_complex.py": {
        "sha256": "a19c1313bd0422830ab43faf6ef74b819e1ddcdaf656401cad991ab2d4cc01e4",
        "authority": "data/results/r25_walk_complex_results.json.source_sha256",
    },
    "experiments/r32_reachability_probe.py": {
        "sha256": "f1ab9307ea2540a0e733ebf34f975a131790927553ded86a6e1134cd08227442",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "rulespace_gpu/__init__.py": {
        "sha256": "911e8a678bfc9c9ef7fd5b9d775135cf340823fc116f6b02adfabdaab8bcc32a",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_gpu/backend.py": {
        "sha256": "de41d174b2b9a2969a35ab084692c1fb6a6bb5d4e19514330fb240b209b4fae9",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_gpu/emergence_judge.py": {
        "sha256": "0c0188e122f7ee9322b52c5f3901aeae39c1430f77728d878de3480f87312902",
        "authority": "rulespace_v2.frozen.EXPECTED_SHA256",
    },
    "rulespace_gpu/engine.py": {
        "sha256": "3b691ccdc2d690b9b90215761d2f393a29f478730b60f37097d8790ffb2f8ea0",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_gpu/green_one_walk.py": {
        "sha256": "abd379d23e42347c5c861d9bb13ff4430c847cb686fddde8681be3b8d1d646c1",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_gpu/observables.py": {
        "sha256": "739012855938e2faab2381769f44695cd1ea40e02a43ae373ac597ac4fd54913",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_gpu/pathB_spin2.py": {
        "sha256": "a9cb039445caa90ab944449215d1c3459d59b88e06883d3eba0d7ef6e5dc2cd7",
        "authority": "parent.protocol.frozen_verification.record_only",
    },
    "rulespace_gpu/spin2_evolver.py": {
        "sha256": "dc9a1a8a28e87288cf858f4dea0c275983d606e2a15b34fe0e819f98e7150900",
        "authority": "parent.protocol.frozen_verification.record_only",
    },
    "rulespace_gpu/states.py": {
        "sha256": "9d26f3ce4727d634376aebc48a55c49d0824525bb76badc67045f2881da793d8",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_gpu/tensor_coin_feedback.py": {
        "sha256": "c31badcb14b3a005204d92f2149e67ca2a553693c564e9374153a89d993639f7",
        "authority": "parent.protocol.frozen_verification.record_only",
    },
    "rulespace_gpu/tensor_qca.py": {
        "sha256": "172a38d5be927ec7f9632e3bd2ba8caaa5fca006659c9fd8f280ddc37091a507",
        "authority": "parent.protocol.frozen_verification.record_only",
    },
    "rulespace_v2/__init__.py": {
        "sha256": "1a832f91ff0181af8c9d9e448821e53caf42dbfb685c4a7f0d3d437273f8464a",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_v2/candidate.py": {
        "sha256": "1d56818709d9ae3f0f265460c82f3b5f24699645cb35900265596b36d45f1b23",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_v2/epsilon.py": {
        "sha256": "10fbfed89436bf0f1dd1996d7c1b03b10aa5d5e5c4756f1b674e199fc8cd881c",
        "authority": "parent.protocol.code",
    },
    "rulespace_v2/frozen.py": {
        "sha256": "45a31ecd7bd47c769da837a83b1cf6146fa249c10ff20af11e6fc0ca0c024d2f",
        "authority": "parent.protocol.code",
    },
    "rulespace_v2/gates.py": {
        "sha256": "f29f4cb8cd1a2d3e0c3730d4428c4870d151ba50eaa31a47f227135f981fcf68",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_v2/invariants.py": {
        "sha256": "5d51e9733b076a71e66ab29dcb67837ada813b43f15d369617c1dbf8e1b696b3",
        "authority": "parent.protocol.code",
    },
    "rulespace_v2/m3_family.py": {
        "sha256": "7df683dee96ff7db4a56d786c639f8679a921744fc293a6f464fa317b3d01cd7",
        "authority": "parent.protocol.code",
    },
    "rulespace_v2/m3_local_family.py": {
        "sha256": "aedd7f90d7606f6b021e7ce15fd9e0d405600cb915cdfa514a73606afa2827b3",
        "authority": "parent.protocol.code",
    },
    "rulespace_v2/sigma.py": {
        "sha256": "5e68622ecd46fd084993cadb0e904875e3b57d2f45f35ca2fa5832c18e29ee3b",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_v3/__init__.py": {
        "sha256": "d702baf26b02b5a371b6472a648458726739dacc1d03d152016baa9ec40e8b18",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_v3/contracts.py": {
        "sha256": "7f0f77fceeb19d1490b84096cda0679e2b1875fba4e3d4b3753242bd54598d71",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
    "rulespace_v3/evidence.py": {
        "sha256": "46e5ed660d67439eb1e2b696409e9e0cd8d114f20e4257111653491b10f47631",
        "authority": "v3m0_task7_signed_execution_closure_freeze",
    },
}
FORBIDDEN_FORMAL = re.compile(r"\b(?:sorry|admit|axiom|unsafe)\b")


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _module_path(module: str) -> Path | None:
    relative = Path(*module.split("."))
    candidates = (
        ROOT / "experiments" / relative.with_suffix(".py"),
        ROOT / relative.with_suffix(".py"),
        ROOT / relative / "__init__.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _module_name(path: Path) -> str:
    relative = path.resolve().relative_to(ROOT.resolve())
    parts = list(relative.with_suffix("").parts)
    if parts == ["experiments", "__init__"]:
        return "experiments"
    if parts[0] == "experiments":
        parts.pop(0)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_import_paths(module: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    parts = module.split(".")
    for length in range(1, len(parts) + 1):
        candidate = _module_path(".".join(parts[:length]))
        if candidate is not None and candidate not in paths:
            paths.append(candidate)
    return tuple(paths)


def _absolute_import_names(
    node: ast.ImportFrom,
    current_module: str,
    is_package: bool,
) -> tuple[str, ...]:
    if node.level:
        package = current_module if is_package else current_module.rpartition(".")[0]
        components = package.split(".") if package else []
        parents = node.level - 1
        if parents:
            components = components[: len(components) - parents]
        base = ".".join(
            components + ([node.module] if node.module else [])
        )
    else:
        base = node.module or ""
    names = ([base] if base else []) + [
        f"{base}.{alias.name}" if base else alias.name
        for alias in node.names
        if alias.name != "*"
    ]
    return tuple(names)


def _literal_dynamic_import_names(
    node: ast.AST,
    current_module: str,
    is_package: bool,
) -> tuple[str, ...]:
    """Resolve literal ``importlib.import_module`` calls conservatively."""

    if not isinstance(node, ast.Call) or not node.args:
        return ()
    function = node.func
    is_import_module = (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "importlib"
        and function.attr == "import_module"
    )
    if not is_import_module:
        return ()
    literal = node.args[0]
    if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
        return ()
    name = literal.value
    if not name.startswith("."):
        return (name,)

    package = current_module if is_package else current_module.rpartition(".")[0]
    if len(node.args) >= 2:
        package_node = node.args[1]
        if isinstance(package_node, ast.Constant) and isinstance(
            package_node.value, str
        ):
            package = package_node.value
        elif not (
            isinstance(package_node, ast.Name) and package_node.id == "__name__"
        ):
            return ()
    if not package:
        return ()
    level = len(name) - len(name.lstrip("."))
    remainder = name[level:]
    components = package.split(".")
    parents = level - 1
    if parents > len(components):
        return ()
    if parents:
        components = components[: len(components) - parents]
    resolved = ".".join(components + ([remainder] if remainder else []))
    return (resolved,) if resolved else ()


def _discover_static_execution_closure() -> dict[str, dict[str, object]]:
    """Mechanically discover the conservative local Python import closure."""

    pending: list[Path] = []
    for module in STATIC_CLOSURE_ROOT_MODULES:
        pending.extend(_module_import_paths(module))
    discovered: dict[str, dict[str, object]] = {}
    while pending:
        path = pending.pop()
        relative = path.relative_to(ROOT.resolve()).as_posix()
        if relative in discovered:
            continue
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        dependencies: list[Path] = []
        literal_dynamic_imports: set[str] = set()
        for node in ast.walk(tree):
            names: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names = _absolute_import_names(
                    node,
                    module,
                    path.name == "__init__.py",
                )
            dynamic_names = _literal_dynamic_import_names(
                node,
                module,
                path.name == "__init__.py",
            )
            literal_dynamic_imports.update(dynamic_names)
            names += dynamic_names
            for name in names:
                for dependency in _module_import_paths(name):
                    if dependency != path and dependency not in dependencies:
                        dependencies.append(dependency)
                        pending.append(dependency)
        discovered[relative] = {
            "module": module,
            "imports": sorted(
                dependency.relative_to(ROOT.resolve()).as_posix()
                for dependency in dependencies
            ),
            "literal_dynamic_imports": sorted(literal_dynamic_imports),
        }
    return {key: discovered[key] for key in sorted(discovered)}


def _authority_sha(
    relative: str,
    freeze: dict[str, str],
    parent: dict[str, Any],
) -> str:
    authority = freeze["authority"]
    if authority == "rulespace_v2.frozen.EXPECTED_SHA256":
        value = FROZEN.EXPECTED_SHA256.get(relative)
        if not isinstance(value, str):
            raise ValueError(f"closure authority missing frozen SHA: {relative}")
        return value
    if authority == "parent.protocol.code":
        record = parent["protocol"]["code"].get(relative)
        if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
            raise ValueError(f"closure authority missing parent code SHA: {relative}")
        return record["sha256"]
    parent_frozen = parent["protocol"]["frozen_verification"]
    if authority == "parent.protocol.frozen_verification.record_only":
        record = parent_frozen["record_only"].get(relative)
        if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
            raise ValueError(f"closure authority missing parent SHA: {relative}")
        return record["sha256"]
    if authority in {
        "data/results/r25_detour_results.json.source_sha256",
        "data/results/r25_laurent_results.json.source_sha256",
        "data/results/r25_static_newton_results.json.source_sha256",
        "data/results/r25_walk_complex_results.json.source_sha256",
    }:
        result_path_text, field = authority.rsplit(".", 1)
        result = _load_json(ROOT / result_path_text)
        value = result.get(field)
        if not isinstance(value, str):
            raise ValueError(f"closure authority result is incomplete: {relative}")
        return value
    if authority == "v3m0_task7_signed_execution_closure_freeze":
        value = freeze.get("sha256")
        if not isinstance(value, str):
            raise ValueError(f"closure literal freeze is incomplete: {relative}")
        return value
    raise ValueError(f"unknown closure authority for {relative}: {authority!r}")


def _verify_static_execution_closure(
    parent: dict[str, Any],
) -> dict[str, object]:
    """Verify local sources before the first frozen static-symbol evaluation.

    Python package bootstrap and runner top-level imports necessarily precede
    this callable boundary; the fresh-process lineage record states that
    limitation and freezes every observed bootstrap source.
    """

    discovered = _discover_static_execution_closure()
    expected_paths = set(STATIC_CLOSURE_FREEZE)
    actual_paths = set(discovered)
    if actual_paths != expected_paths:
        raise ValueError(
            "static execution closure changed; "
            f"added={sorted(actual_paths - expected_paths)}, "
            f"missing={sorted(expected_paths - actual_paths)}"
        )
    files: dict[str, object] = {}
    for relative in sorted(discovered):
        freeze = STATIC_CLOSURE_FREEZE[relative]
        authority_sha = _authority_sha(relative, freeze, parent)
        expected = freeze["sha256"]
        if authority_sha != expected:
            raise ValueError(f"closure authority SHA mismatch: {relative}")
        actual = _file_sha(ROOT / relative)
        matches = actual == expected
        files[relative] = {
            **discovered[relative],
            "authority": freeze["authority"],
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": matches,
        }
        if not matches:
            raise ValueError(f"static execution closure SHA mismatch: {relative}")
    record: dict[str, object] = {
        "discovery": (
            "python_ast_conservative_local_import_closure_v2_with_"
            "literal_importlib_import_module"
        ),
        "roots": list(STATIC_CLOSURE_ROOT_MODULES),
        "file_count": len(files),
        "files": files,
        "all_match": True,
    }
    record["closure_sha256"] = canonical_sha(record)
    return record


def _static_closure_cache_key(
    closure: dict[str, object],
) -> tuple[str, ...]:
    files = closure["files"]
    if not isinstance(files, dict):
        raise TypeError("closure files must be a mapping")
    return tuple(
        str(files[relative]["actual_sha256"])
        for relative in sorted(files)
    )


@lru_cache(maxsize=2)
def _fresh_process_runtime_closure_cached(
    parent_path_text: str,
    closure_cache_key: tuple[str, ...],
    v3_source_key: tuple[str, ...],
) -> dict[str, object]:
    """Observe the reachable local-module set in a genuinely fresh process."""

    del closure_cache_key, v3_source_key
    marker = "__V3M0_RUNTIME_CLOSURE__"
    probe = r'''
import json
import sys
from pathlib import Path

from experiments import v3m0_formal_nogo as runner

events = ["runner_import_complete"]
parent = runner._load_json(Path(sys.argv[1]))
closure = runner._verify_static_execution_closure(parent)
events.append("closure_preflight_complete")
saved = parent["cells"][0]["epsilon_geo_by_direction"]["axial"]
runner._static_reference(
    0,
    0.0,
    "axial",
    (1, 0, 0),
    saved,
    runner._static_closure_cache_key(closure),
)
events.append("static_reference_complete")
root = runner.ROOT.resolve()
modules_by_file = {}
for module_name, module in sorted(sys.modules.items()):
    source = getattr(module, "__file__", None)
    if not source:
        continue
    try:
        path = Path(source).resolve()
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
    except (OSError, ValueError):
        continue
    modules_by_file.setdefault(relative, []).append(module_name)
payload = {
    "event_order": events,
    "module_names_by_file": {
        relative: sorted(names)
        for relative, names in sorted(modules_by_file.items())
    },
}
print("__V3M0_RUNTIME_CLOSURE__" + json.dumps(payload, sort_keys=True))
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get(
        "PYTHONPATH", ""
    )
    environment["PYTHONWARNINGS"] = "ignore"
    completed = subprocess.run(
        [sys.executable, "-c", probe, parent_path_text],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=60,
    )
    marker_lines = [
        line[len(marker) :]
        for line in completed.stdout.splitlines()
        if line.startswith(marker)
    ]
    if completed.returncode != 0 or len(marker_lines) != 1:
        raise ValueError(
            "fresh-process runtime closure probe failed: "
            f"exit={completed.returncode}; output={completed.stdout[-2000:]!r}"
        )
    payload = json.loads(marker_lines[0])
    if not isinstance(payload, dict):
        raise ValueError("fresh-process runtime closure payload is not a mapping")
    event_order = payload.get("event_order")
    expected_events = [
        "runner_import_complete",
        "closure_preflight_complete",
        "static_reference_complete",
    ]
    if event_order != expected_events:
        raise ValueError("fresh-process runtime closure event order mismatch")
    modules_by_file = payload.get("module_names_by_file")
    if not isinstance(modules_by_file, dict):
        raise ValueError("fresh-process runtime module manifest is incomplete")

    loaded = set(modules_by_file)
    allowed = set(STATIC_CLOSURE_FREEZE) | set(V3_SOURCE_FILES)
    required = set(REQUIRED_RUNTIME_BOOTSTRAP_FILES)
    unexpected = sorted(loaded - allowed)
    missing_required = sorted(required - loaded)
    if unexpected or missing_required:
        raise ValueError(
            "fresh-process local module closure changed; "
            f"unexpected={unexpected}, missing_bootstrap={missing_required}"
        )
    return {
        "probe": (
            "fresh_python_process_runner_import_then_sha_preflight_then_"
            "one_static_reference"
        ),
        "event_order": expected_events,
        "preflight_boundary": {
            "reachable": True,
            "verified_before": "first_static_symbol_function_call",
            "not_verified_before": (
                "python_package_bootstrap_and_runner_top_level_import_execution"
            ),
            "scope": (
                "all observed bootstrap sources are signed in the closure; "
                "the SHA preflight runs after Python import execution but "
                "before LOCAL.symbol_of_potential/FROZEN.mod static evaluation"
            ),
        },
        "loaded_local_module_files": sorted(loaded),
        "module_names_by_file": {
            str(relative): list(names)
            for relative, names in sorted(modules_by_file.items())
        },
        "allowed_signed_lineage_files": sorted(allowed),
        "required_bootstrap_files": sorted(required),
        "unexpected_local_module_files": unexpected,
        "missing_required_bootstrap_files": missing_required,
        "loaded_subset_of_signed_lineage": loaded <= allowed,
    }


def _fresh_process_runtime_closure(
    parent_path: Path,
    static_closure: dict[str, object],
) -> dict[str, object]:
    closure_key = _static_closure_cache_key(static_closure)
    source_key = tuple(_file_sha(ROOT / relative) for relative in V3_SOURCE_FILES)
    cached = _fresh_process_runtime_closure_cached(
        str(parent_path.resolve()),
        closure_key,
        source_key,
    )
    return json.loads(
        json.dumps(cached, allow_nan=False, ensure_ascii=False, sort_keys=True)
    )


def _environment_manifest() -> dict[str, object]:
    config = getattr(np.__config__, "CONFIG", {})
    selected_build = {
        key: config.get(key, {})
        for key in (
            "Compilers",
            "Machine Information",
            "Build Dependencies",
            "SIMD Extensions",
        )
    }
    # NumPy's config is JSON data; round-trip takes one immutable plain snapshot.
    numpy_build = json.loads(
        json.dumps(selected_build, allow_nan=False, sort_keys=True)
    )
    dependencies = numpy_build.get("Build Dependencies", {})
    blas = dependencies.get("blas", {}).get("name", "unknown")
    lapack = dependencies.get("lapack", {}).get("name", "unknown")
    try:
        from threadpoolctl import threadpool_info

        pools = json.loads(
            json.dumps(threadpool_info(), allow_nan=False, sort_keys=True)
        )
    except (ImportError, TypeError, ValueError):
        pools = []
    return {
        "numpy_version": np.__version__,
        "numpy_build": numpy_build,
        "numpy_build_config_sha256": canonical_sha(numpy_build),
        "blas": str(blas),
        "lapack": str(lapack),
        "threadpoolctl": pools,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system": platform.system(),
        "release": platform.release(),
        "attribution_only": True,
        "cross_platform_bit_identical_required": False,
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _independent_verlet(potential: np.ndarray, dt: float) -> np.ndarray:
    """Independent KDK assembly; does not call LOCAL._verlet_symbol."""

    dimension = potential.shape[0]
    identity = np.eye(dimension, dtype=np.complex128)
    zero = np.zeros_like(identity)
    kick = np.block(
        [[identity, zero], [-0.5 * dt * potential, identity]]
    )
    drift = np.block([[identity, dt * identity], [zero, identity]])
    with np.errstate(all="ignore"):
        result = kick @ drift @ kick
    if not np.isfinite(result).all():
        raise FloatingPointError("non-finite independent Verlet symbol")
    return result


def _geometry(k: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r15 = FROZEN.mod("r15_walk_dedonder")
    r32 = FROZEN.mod("r32_reachability_probe")
    placed = r15.kappa_placed(k, LOCAL.C_CONE)
    if placed is None:
        raise ValueError("frozen reference direction left the placed shell")
    q_tt, q_gauge, _ = r32.build_sectors(placed)
    q_ker = INV.orth(np.column_stack((q_tt, q_gauge)))
    incidence = r32.inc_matrix(placed)
    return q_ker, incidence


@lru_cache(maxsize=90)
def _static_reference_cached(
    q: int,
    kappa_c: float,
    direction_name: str,
    direction: tuple[int, int, int],
    saved_sine_values: tuple[float, ...],
    source_key: tuple[str, ...],
) -> dict[str, object]:
    del source_key  # participates in cache identity; algebra uses imported code
    k = (np.pi / 4.0) * np.asarray(direction, dtype=float)
    potential = LOCAL.symbol_of_potential(q, kappa_c, k)
    dt = float(LOCAL.floquet_retune_table()[q]["dt"])
    macro = _independent_verlet(potential, dt)
    with np.errstate(all="ignore"):
        eigenvalues, eigenvectors = np.linalg.eig(macro)
    phases = np.angle(eigenvalues)
    positive = phases > 1e-9
    raw_h = eigenvectors[:10, positive]
    h_basis = INV.orth(raw_h)
    coisometry = float(
        np.linalg.norm(
            h_basis @ h_basis.conj().T - np.eye(10),
            ord=2,
        )
    )
    q_ker, incidence = _geometry(k)
    images = incidence @ h_basis
    _, singular_values, vh = np.linalg.svd(images, full_matrices=False)
    normalized = singular_values / singular_values[0]
    n_curv = int(np.sum(normalized >= INV.SIN_THRESH))
    s_curv = INV.orth(h_basis @ vh.conj().T[:, :n_curv])
    invariants = INV.subspace_invariants(s_curv, q_ker)
    sine = np.asarray(invariants["sin_theta"], dtype=float)
    saved_sine = np.asarray(saved_sine_values, dtype=float)
    if sine.shape != saved_sine.shape:
        saved_residual = float("inf")
    else:
        saved_residual = float(np.max(np.abs(sine - saved_sine)))
    j_value = int(invariants["n_ge_thresh"])
    epsilon = EPS.epsilon_dof(j_value, n_curv)
    return {
        "direction": direction_name,
        "vector": list(direction),
        "ratio": [1, 8],
        "positive_h_rank": int(h_basis.shape[1]),
        "positive_phase_count": int(np.sum(positive)),
        "incidence_rank": int(np.linalg.matrix_rank(incidence)),
        "N_curv": n_curv,
        "j": j_value,
        "epsilon_geo": float(epsilon),
        "sin_theta": [float(value) for value in sine],
        "saved_spectrum_residual": saved_residual,
        "coisometry_residual_2": coisometry,
        "coisometry_pass": bool(coisometry <= COISOMETRY_TOL),
    }


def _static_reference(
    q: int,
    kappa_c: float,
    direction_name: str,
    direction: tuple[int, int, int],
    saved: dict[str, Any],
    closure_cache_key: tuple[str, ...],
) -> dict[str, object]:
    cached = _static_reference_cached(
        q,
        kappa_c,
        direction_name,
        direction,
        tuple(float(value) for value in saved["sin_theta"]),
        (
            _file_sha(ROOT / "rulespace_v2/m3_local_family.py"),
            _file_sha(ROOT / "rulespace_v2/invariants.py"),
            _file_sha(ROOT / "rulespace_v2/epsilon.py"),
            *closure_cache_key,
        ),
    )
    # The caller appends record metadata; never expose the cached dictionary.
    return {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in cached.items()
    }


def _validate_parent_manifest(parent: dict[str, Any]) -> list[dict[str, object]]:
    manifest = parent.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("parent manifest is missing")
    expected = [cell.as_dict() for cell in FAMILY.build_pilot_manifest()]
    if manifest.get("cell_count") != 30 or manifest.get("cells") != expected:
        raise ValueError("parent 30-cell manifest/order mismatch")
    canonical = json.dumps(
        expected,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    recomputed_sha = hashlib.sha256(canonical).hexdigest()
    if (
        recomputed_sha != PARENT_MANIFEST_SHA
        or manifest.get("manifest_sha256") != recomputed_sha
    ):
        raise ValueError("parent manifest SHA mismatch")
    return expected


def _formal_source_paths() -> tuple[Path, ...]:
    sources = tuple(sorted((FORMAL_ROOT / "V3M0").glob("*.lean")))
    return sources + (
        FORMAL_ROOT / "V3M0.lean",
        FORMAL_ROOT / "lean-toolchain",
        FORMAL_ROOT / "lakefile.toml",
        FORMAL_ROOT / "lake-manifest.json",
    )


@lru_cache(maxsize=2)
def _formal_record_cached(
    source_key: tuple[str, ...],
) -> dict[str, object]:
    del source_key
    environment = os.environ.copy()
    elan = "/Users/prismer/.elan/bin"
    environment["PATH"] = elan + os.pathsep + environment.get("PATH", "")
    completed = subprocess.run(
        ["lake", "build"],
        cwd=FORMAL_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    lean_version = subprocess.run(
        ["lake", "env", "lean", "--version"],
        cwd=FORMAL_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    lean_version_output = lean_version.stdout.strip()
    lean_version_expected = "4.32.1"
    lean_version_pass = bool(
        lean_version.returncode == 0
        and re.match(
            rf"^Lean \(version {re.escape(lean_version_expected)},",
            lean_version_output,
        )
    )
    sources = list(sorted((FORMAL_ROOT / "V3M0").glob("*.lean")))
    sources.append(FORMAL_ROOT / "V3M0.lean")
    forbidden: dict[str, list[str]] = {}
    source_sha: dict[str, str] = {}
    for path in sources:
        relative = path.relative_to(ROOT).as_posix()
        source_sha[relative] = _file_sha(path)
        matches = sorted(set(FORBIDDEN_FORMAL.findall(path.read_text("utf-8"))))
        if matches:
            forbidden[relative] = matches
    toolchain_paths = (
        FORMAL_ROOT / "lean-toolchain",
        FORMAL_ROOT / "lakefile.toml",
        FORMAL_ROOT / "lake-manifest.json",
    )
    toolchain_sha = {
        path.relative_to(ROOT).as_posix(): _file_sha(path)
        for path in toolchain_paths
    }
    return {
        "build_command": "lake build",
        "build_exit_code": int(completed.returncode),
        "build_pass": completed.returncode == 0,
        "lean_version_command": "lake env lean --version",
        "lean_version_exit_code": int(lean_version.returncode),
        "lean_version_output": lean_version_output,
        "lean_version_expected": lean_version_expected,
        "lean_version_pass": lean_version_pass,
        "forbidden_tokens": forbidden,
        "forbidden_token_pass": not forbidden,
        "source_sha256": source_sha,
        "required_modules": [
            "V3M0/Common.lean",
            "V3M0/EpsilonComplement.lean",
            "V3M0/ExtensionalNoGo.lean",
            "V3M0/JordanGrowth.lean",
            "V3M0/LocalSymplectic.lean",
            "V3M0/MetricDrift.lean",
            "V3M0/ObserverCollapse.lean",
            "V3M0/SubspaceSurvival.lean",
            "V3M0.lean",
        ],
        "toolchain_sha256": toolchain_sha,
        "lean_toolchain": (FORMAL_ROOT / "lean-toolchain").read_text("utf-8").strip(),
        "sympy_version": sympy.__version__,
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
    }


def _formal_record() -> dict[str, object]:
    source_key = tuple(_file_sha(path) for path in _formal_source_paths())
    cached = _formal_record_cached(source_key)
    return json.loads(
        json.dumps(cached, allow_nan=False, ensure_ascii=False, sort_keys=True)
    )


def _rebuild_phase0_body(parent_v2_path: Path) -> dict[str, object]:
    parent_path = parent_v2_path.resolve()
    if not parent_path.is_file():
        raise FileNotFoundError(parent_path)
    parent_sha_before = _file_sha(parent_path)
    if parent_sha_before != PARENT_SHA:
        raise ValueError("parent v2 pilot SHA mismatch")
    parent = _load_json(parent_path)
    static_closure = _verify_static_execution_closure(parent)
    closure_cache_key = _static_closure_cache_key(static_closure)
    expected_manifest = _validate_parent_manifest(parent)

    local_input = parent["inputs"]["local_certificate"]
    local_path = (ROOT / local_input["path"]).resolve()
    if local_input["sha256"] != LOCAL_CERT_SHA or _file_sha(local_path) != LOCAL_CERT_SHA:
        raise ValueError("local-family certificate SHA mismatch")
    local_cert = _load_json(local_path)
    local_plane = local_cert["plane_wave_bridge"]
    if local_plane.get("pass") is not True:
        raise ValueError("local factory/static plane-wave lineage is not green")
    runtime_closure = _fresh_process_runtime_closure(
        parent_path,
        static_closure,
    )

    protocol = parent["protocol"]
    if protocol.get("directions") != {
        name: list(vector) for name, vector in DIRECTIONS
    }:
        raise ValueError("parent direction manifest/order mismatch")
    if protocol.get("epsilon_reference_ratio") != [1, 8]:
        raise ValueError("parent reference ratio mismatch")

    records: list[dict[str, object]] = []
    saved_n: set[int] = set()
    saved_j: set[int] = set()
    saved_epsilon: list[float] = []
    saved_exact_squared_residuals: list[float] = []
    for index, (cell, expected_cell) in enumerate(
        zip(parent["cells"], expected_manifest)
    ):
        if cell["cell_id"] != expected_cell["cell_id"]:
            raise ValueError(f"parent cell order mismatch at index {index}")
        construction = cell["construction"]
        q = int(construction["q"])
        kappa_c = float(construction["kappa_c"])
        for direction_name, direction in DIRECTIONS:
            saved = cell["epsilon_geo_by_direction"][direction_name]
            if saved.get("ratio") != [1, 8]:
                raise ValueError("parent reference ratio drift")
            saved_sines = np.asarray(saved["sin_theta"], dtype=float)
            reduced_n = int(saved_sines.size)
            reduced_j = int(np.sum(saved_sines >= INV.SIN_THRESH))
            reduced_epsilon = float(EPS.epsilon_dof(reduced_j, reduced_n))
            if (
                int(saved["N_curv"]) != reduced_n
                or int(saved["j_hand_invariant"]) != reduced_j
                or abs(float(saved["epsilon_geo"]) - reduced_epsilon) > 2e-15
            ):
                raise ValueError("parent saved scalar summary disagrees with saved spectrum")
            saved_n.add(reduced_n)
            saved_j.add(reduced_j)
            saved_epsilon.append(reduced_epsilon)
            saved_exact_squared_residuals.append(
                float(
                    np.max(
                        np.abs(
                            np.sort(saved_sines**2)
                            - np.asarray((0, 0, 1, 1, 1, 1), dtype=float)
                        )
                    )
                )
            )
            rebuilt = _static_reference(
                q,
                kappa_c,
                direction_name,
                direction,
                saved,
                closure_cache_key,
            )
            rebuilt["record_id"] = f"{cell['cell_id']}:{direction_name}:1/8"
            rebuilt["cell_id"] = cell["cell_id"]
            rebuilt["q"] = q
            rebuilt["kappa_c"] = kappa_c
            records.append(rebuilt)

    if len(records) != 90 or len({row["record_id"] for row in records}) != 90:
        raise ValueError("static bridge must contain 90 uniquely identified rows")
    coisometry_max = max(float(row["coisometry_residual_2"]) for row in records)
    saved_spectrum_max = max(
        float(row["saved_spectrum_residual"]) for row in records
    )
    static_discrete_pass = all(
        row["positive_h_rank"] == 10
        and row["incidence_rank"] == 6
        and row["N_curv"] == 6
        and row["j"] == 4
        and abs(float(row["epsilon_geo"]) - 1.0 / 3.0) <= 2e-15
        for row in records
    )

    code = protocol["code"]
    lineage_files: dict[str, object] = {}
    for relative in (
        "rulespace_v2/m3_pilot.py",
        "rulespace_v2/m3_local_family.py",
        "rulespace_v2/m3_family.py",
        "rulespace_v2/invariants.py",
        "rulespace_v2/epsilon.py",
        "rulespace_v2/frozen.py",
    ):
        expected = code[relative]["sha256"]
        actual = _file_sha(ROOT / relative)
        if actual != expected:
            raise ValueError(f"lineage source SHA mismatch: {relative}")
        lineage_files[relative] = {"sha256": actual}
    closure_files = static_closure["files"]
    frozen_static_sources = {
        relative: {
            "expected_sha256": closure_files[relative]["expected_sha256"],
            "actual_sha256": closure_files[relative]["actual_sha256"],
            "match": closure_files[relative]["match"],
        }
        for relative in FROZEN_STATIC_DEPENDENCIES
    }
    frozen_static_sources_pass = bool(static_closure["all_match"])

    formal = _formal_record()
    exact = exact_profile()
    environment = _environment_manifest()
    gates = {
        "parent_sha": parent_sha_before == PARENT_SHA,
        "manifest_lineage": True,
        "frozen_static_source_sha": frozen_static_sources_pass,
        "static_execution_closure_sha": bool(static_closure["all_match"]),
        "fresh_process_runtime_closure": bool(
            runtime_closure["loaded_subset_of_signed_lineage"]
            and not runtime_closure["missing_required_bootstrap_files"]
        ),
        "saved_scalar_reduction": (
            saved_n == {6}
            and saved_j == {4}
            and all(abs(value - 1.0 / 3.0) <= 2e-15 for value in saved_epsilon)
        ),
        "static_symbol_reconstruction": (
            static_discrete_pass and saved_spectrum_max <= 2e-15
        ),
        "whitened_coisometry_90": coisometry_max <= COISOMETRY_TOL,
        "exact_reconstruction": True,
        "lean_build": bool(formal["build_pass"]),
        "lean_version": bool(formal["lean_version_pass"]),
        "lean_no_forbidden_tokens": bool(formal["forbidden_token_pass"]),
    }
    all_green = all(gates.values())
    parent_sha_after = _file_sha(parent_path)
    if parent_sha_after != parent_sha_before:
        raise RuntimeError("parent v2 pilot changed during read-only reconstruction")
    return {
        "schema": "v3m0-formal-nogo-v1",
        "artifact_kind": "formal_nogo_intermediate_evidence",
        "evidence_kind": "source_sha_static_symbol_reconstruction",
        "raw_kernel_available": False,
        "raw_kernel_recomputed": False,
        "raw_kernel_independent_recomputation": False,
        "production_symbol_equivalence": "round0_plane_wave_spotcheck",
        "claim_ceiling": "conditional_full_positive_observer_collapse",
        "status": "READY-V3M0-CONTROLS" if all_green else "HALT-V3M0-PHASE0",
        "environment": environment,
        "parent": {
            "path": parent_path.relative_to(ROOT).as_posix(),
            "sha256": parent_sha_before,
            "manifest_sha256": PARENT_MANIFEST_SHA,
            "status": parent["status"],
            "raw_kernel_persisted": False,
        },
        "lineage": {
            "source_files": lineage_files,
            "frozen_static_sources": frozen_static_sources,
            "static_execution_closure": static_closure,
            "fresh_process_runtime_closure": runtime_closure,
            "v3_source_files": {
                relative: {"sha256": _file_sha(ROOT / relative)}
                for relative in V3_SOURCE_FILES
            },
            "local_family_certificate": {
                "path": local_path.relative_to(ROOT).as_posix(),
                "sha256": LOCAL_CERT_SHA,
                "factory_static_plane_wave_max_relative_residual": float(
                    local_plane["max_relative_residual"]
                ),
            },
            "measured_kernel_factory_plane_wave": {
                "source": "parent_persisted_summary",
                "max_relative_residual": float(
                    parent["summary"]["max_plane_bridge_residual"]
                ),
            },
            "historical_runner": {
                "original_sha256": parent["finalization_amendment"]["old_runner_sha256"],
                "finalizer_sha256": parent["finalization_amendment"]["new_runner_sha256"],
            },
        },
        "manifest": {
            "cell_count": 30,
            "q_levels": list(LOCAL.Q_LEVELS),
            "kappa_c_levels": list(LOCAL.KAPPA_C_LEVELS),
            "directions": [
                {"name": name, "vector": list(vector)}
                for name, vector in DIRECTIONS
            ],
            "reference_ratio": [1, 8],
            "reference_record_count": 90,
            "record_ids": [str(row["record_id"]) for row in records],
        },
        "saved_scalar_reduction": {
            "record_count": 90,
            "unique_N_curv": sorted(saved_n),
            "unique_j": sorted(saved_j),
            "epsilon_geo": "1/3",
            "max_saved_squared_spectrum_exact_residual": max(
                saved_exact_squared_residuals
            ),
            "reduction_rule": "N=len(sin_theta);j=count(sin_theta>=0.05);epsilon=1-j/N",
            "conditional_no_go": "j=4,N_curv=6 => epsilon_geo=1/3",
        },
        "static_bridge": {
            "reference_count": 90,
            "records": records,
            "coisometry_tolerance": COISOMETRY_TOL,
            "max_coisometry_residual_2": coisometry_max,
            "max_saved_spectrum_residual": saved_spectrum_max,
            "raw_kernel_content_verified": False,
            "static_discrete_pass": static_discrete_pass,
        },
        "exact": exact,
        "formal": formal,
        "gates": gates,
    }


def build_phase0_certificate(parent_v2_path: Path) -> dict[str, object]:
    """Build, self-verify, and return one deterministic Phase-0 certificate."""

    body = _rebuild_phase0_body(Path(parent_v2_path))
    certificate = dict(body)
    certificate["certificate_sha"] = canonical_sha(body)
    verify_exact_certificate(certificate)
    return certificate


def _json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    if not path.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {path.parent}")
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _validate_output_target(output: Path, parent: Path) -> None:
    """Reject aliases of protected inputs and non-unique repository outputs."""

    output_resolved = output.resolve()
    parent_resolved = parent.resolve()
    parent_payload = _load_json(parent_resolved)
    protected = {parent_resolved}
    inputs = parent_payload.get("inputs")
    if isinstance(inputs, dict):
        for record in inputs.values():
            if isinstance(record, dict) and isinstance(record.get("path"), str):
                protected.add((ROOT / record["path"]).resolve())
    protocol = parent_payload.get("protocol")
    if isinstance(protocol, dict):
        code = protocol.get("code")
        if isinstance(code, dict):
            for record in code.values():
                if isinstance(record, dict) and isinstance(record.get("path"), str):
                    protected.add((ROOT / record["path"]).resolve())
    protected.update((ROOT / relative).resolve() for relative in FROZEN_STATIC_DEPENDENCIES)
    if output_resolved in protected:
        raise ValueError("output target aliases a protected v1/v2 input")
    root_resolved = ROOT.resolve()
    if (
        output_resolved == root_resolved
        or root_resolved in output_resolved.parents
    ) and output_resolved != DEFAULT_OUTPUT.resolve():
        raise ValueError("repository output must be the unique formal no-go target")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)

    _validate_output_target(arguments.output, arguments.parent)
    parent_before = _file_sha(arguments.parent)
    certificate = build_phase0_certificate(arguments.parent)
    encoded = _json_bytes(certificate)
    if arguments.generate:
        if _file_sha(arguments.parent) != parent_before:
            raise RuntimeError("parent v2 pilot changed before atomic write")
        _atomic_write(arguments.output, encoded)
    else:
        if not arguments.output.is_file():
            raise FileNotFoundError(arguments.output)
        existing = arguments.output.read_bytes()
        parsed = json.loads(existing)
        if parsed != certificate or existing != encoded:
            raise ValueError("stored certificate differs from independent reconstruction")
    if _file_sha(arguments.parent) != parent_before:
        raise RuntimeError("parent v2 pilot was modified")
    print(
        f"{certificate['status']} "
        f"sha={certificate['certificate_sha']} "
        f"raw_kernel_independent_recomputation=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
