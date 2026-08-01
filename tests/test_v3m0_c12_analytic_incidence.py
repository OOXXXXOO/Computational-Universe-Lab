"""Extraction guards for the standalone analytic C12 certificate."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
LEGACY_C12_SOURCE_SHA = (
    "c7ea862e12d5c01be08e7316dfe4e0a674a9a415bd67fea385286de234423ffb"
)


class C12AnalyticExtractionTests(unittest.TestCase):
    def test_legacy_source_is_byte_exact(self) -> None:
        source = ROOT / "rulespace_v3" / "c12_incidence_preflight.py"
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            LEGACY_C12_SOURCE_SHA,
        )

    def test_fresh_import_never_captures_finite_response_dependencies(
        self,
    ) -> None:
        script = """
import sys
from unittest.mock import patch

import rulespace_v3.c12_incidence_preflight as legacy


assert "rulespace_v3.c12_analytic_incidence" not in sys.modules
poisoned_calls = []


def poison(label):
    def poisoned(*_, **__):
        poisoned_calls.append(label)
        raise AssertionError(f"analytic graph called {label}")

    return poisoned


with (
    patch.object(
        legacy,
        "_finite_response_at_point",
        poison("finite response"),
    ),
    patch.object(
        legacy,
        "_build_structure_audits",
        poison("structure audit"),
    ),
    patch.object(
        legacy,
        "_build_point_audit",
        poison("point SVD audit"),
    ),
    patch.object(
        legacy,
        "compute_fejer_filtered_response",
        poison("Fejer response"),
    ),
    patch.object(legacy.np.linalg, "svd", poison("SVD")),
):
    import rulespace_v3.c12_analytic_incidence as analytic

    certificate = analytic.build_c12_analytic_incidence_certificate()
    assert (
        analytic.verify_c12_analytic_incidence_certificate(certificate)
        is certificate
    )

assert poisoned_calls == [], poisoned_calls
"""
        completed = subprocess.run(
            (sys.executable, "-c", script),
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stdout + completed.stderr,
        )

    def test_guards_close_both_modules_without_mutating_legacy_class(
        self,
    ) -> None:
        import rulespace_v3.c12_analytic_incidence as analytic
        import rulespace_v3.c12_incidence_preflight as legacy

        self.assertIs(
            analytic._LEGACY_POINT_POST_INIT,
            legacy.C12IncidencePointWire.__post_init__,
        )
        builder = analytic.build_c12_analytic_incidence_certificate
        verifier = analytic.verify_c12_analytic_incidence_certificate
        certificate = builder()
        poisoned_calls = []

        def poison(label):
            def poisoned(*_, **__):
                poisoned_calls.append(label)
                raise AssertionError(f"rebound {label} was called")

            return poisoned

        with (
            patch.object(analytic, "type", poison("analytic type"), create=True),
            patch.object(analytic, "_text", poison("analytic _text")),
            patch.object(
                analytic,
                "getattr",
                poison("analytic getattr"),
                create=True,
            ),
            patch.object(legacy, "type", poison("legacy type"), create=True),
            patch.object(legacy, "_text", poison("legacy _text")),
            patch.object(
                legacy,
                "getattr",
                poison("legacy getattr"),
                create=True,
            ),
            patch.object(
                legacy,
                "_build_incidence_point",
                poison("legacy point builder"),
            ),
            patch.object(
                legacy,
                "_build_incidence_point_body",
                poison("legacy point replay"),
            ),
        ):
            rebuilt = builder()
            self.assertIs(verifier(certificate), certificate)
            self.assertEqual(rebuilt, certificate)
        self.assertEqual(poisoned_calls, [])


if __name__ == "__main__":
    unittest.main()
