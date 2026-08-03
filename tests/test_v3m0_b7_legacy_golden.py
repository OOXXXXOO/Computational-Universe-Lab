from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


SOURCE_COMMIT_SHA = "18b0d4302658c376fcc237a56fc1dc28bf6dd95e"
RESPONSE_SOURCE_PATH = "rulespace_v3/response.py"
RESPONSE_SOURCE_RAW_SHA256 = (
    "d8670ba98a153eef660e22fcdca45fd56e68140445e1b17ef6f273d0ab7f9b89"
)
FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "v3m0_b7_legacy_response_18b0d43.json"
)


def _trusted_git_object(path: str) -> bytes:
    completed = subprocess.run(
        [
            "/usr/bin/git",
            "--no-pager",
            "--no-replace-objects",
            "show",
            f"{SOURCE_COMMIT_SHA}:{path}",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def test_legacy_response_golden_replays_exactly() -> None:
    source_bytes = _trusted_git_object(RESPONSE_SOURCE_PATH)
    assert hashlib.sha256(source_bytes).hexdigest() == RESPONSE_SOURCE_RAW_SHA256

    fixture_bytes = FIXTURE_PATH.read_bytes()
    fixture = json.loads(fixture_bytes)
    assert fixture
