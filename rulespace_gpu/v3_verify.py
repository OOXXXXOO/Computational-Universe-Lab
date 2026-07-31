"""Small machine-readable preflight for the V3 local-shear array adapter."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import sys
from typing import Dict, Optional, Sequence

import numpy as np

from .v3_local_shear import (
    BackendUnavailableError,
    LocalShearProgram,
    LocalShearStep,
    make_batched_local_shear_step,
    preflight_backend,
)


@dataclass(frozen=True)
class LocalShearPreflightResult:
    backend: str
    engine: str
    dtype: str
    batch_size: int
    max_abs_error: float
    chunk_parity: bool
    passed: bool

    def as_dict(self) -> Dict[str, object]:
        return {
            "backend": self.backend,
            "engine": self.engine,
            "dtype": self.dtype,
            "batch_size": self.batch_size,
            "max_abs_error": self.max_abs_error,
            "chunk_parity": self.chunk_parity,
            "passed": self.passed,
        }


def _program() -> LocalShearProgram:
    return LocalShearProgram(
        channel_count=3,
        spatial_ndim=2,
        steps=(
            LocalShearStep(
                operation_id="local_canonical_shear",
                source_index=0,
                destination_index=1,
                offset=(1, -1),
                coefficient=0.5 + 0.25j,
            ),
            LocalShearStep(
                operation_id="local_canonical_shear",
                source_index=1,
                destination_index=2,
                offset=(-1, 1),
                coefficient=-0.75 + 0.5j,
            ),
        ),
    )


def _reference(program: LocalShearProgram, state: np.ndarray) -> np.ndarray:
    result = state.copy()
    for step in program.steps:
        if step.operation_id == "neutral_identity":
            continue
        shifted = result[:, step.source_index, ...]
        for axis, coordinate in enumerate(step.offset):
            shifted = np.roll(shifted, shift=-coordinate, axis=axis + 1)
        output = result.copy()
        output[:, step.destination_index, ...] += step.coefficient * shifted
        result = output
    return result


def run_preflight(backend: str) -> LocalShearPreflightResult:
    facts = preflight_backend(backend)
    program = _program()
    values = np.arange(3 * 3 * 4 * 5, dtype=np.float64).reshape(3, 3, 4, 5)
    state = (values + 1j * values[::-1]).astype(np.complex128)
    expected = _reference(program, state)
    runner = make_batched_local_shear_step(program, backend=backend)
    actual = np.asarray(runner(state))
    chunked = np.concatenate(
        (np.asarray(runner(state[:1])), np.asarray(runner(state[1:]))),
        axis=0,
    )
    error = float(np.max(np.abs(actual - expected)))
    chunk_parity = bool(np.allclose(chunked, actual, rtol=0.0, atol=2e-15))
    dtype = actual.dtype.name
    passed = bool(
        dtype == "complex128" and error <= 2e-15 and chunk_parity
    )
    return LocalShearPreflightResult(
        backend=backend,
        engine=facts.engine,
        dtype=dtype,
        batch_size=state.shape[0],
        max_abs_error=error,
        chunk_parity=chunk_parity,
        passed=passed,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated V3 local-shear array preflight."
    )
    parser.add_argument(
        "--backend",
        required=True,
        choices=("numpy", "jax", "jax-cuda"),
    )
    arguments = parser.parse_args(argv)
    try:
        report = run_preflight(arguments.backend)
    except BackendUnavailableError as exc:
        print(
            json.dumps(
                {
                    "backend": arguments.backend,
                    "passed": False,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report.as_dict(), sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["LocalShearPreflightResult", "main", "run_preflight"]
