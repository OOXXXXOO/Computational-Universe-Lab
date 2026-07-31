from __future__ import annotations

import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from rulespace_v3.factory import (
    PRIMITIVE_SCHEMA_VERSION,
    Primitive,
    PrimitiveInterface,
    _apply_primitive,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _api():
    try:
        return importlib.import_module("rulespace_gpu.v3_local_shear")
    except ModuleNotFoundError as exc:
        raise AssertionError("V3 local-shear adapter is missing") from exc


def _verify_api():
    try:
        return importlib.import_module("rulespace_gpu.v3_verify")
    except ModuleNotFoundError as exc:
        raise AssertionError("V3 local-shear preflight is missing") from exc


def _reference_fixture():
    api = _api()
    interface = PrimitiveInterface(
        interface_id="v3-gpu-local-shear-test-interface",
        state_schema_id="v3-gpu-local-shear-test-state",
        spatial_ndim=2,
        channel_order=("a", "b", "c"),
        dtype="complex128",
        backend="numpy",
    )
    specifications = (
        ("a", "b", (1, -1), 0.5 + 0.25j),
        ("b", "c", (-2, 1), -0.75 + 0.5j),
        ("c", "a", (0, -1), 0.125 - 0.375j),
    )
    primitives = tuple(
        Primitive(
            primitive_schema_version=PRIMITIVE_SCHEMA_VERSION,
            mechanism_id=f"mechanism-{index}",
            production_id="local_canonical_shear",
            layer_slot_id=f"layer-{index}",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=source,
            destination_channel=destination,
            offset=offset,
            support_offsets=tuple(sorted({(0, 0), offset})),
            coefficient_wire=(coefficient.real, coefficient.imag),
            coefficient_digest=f"{index + 1:064x}",
            neutral_identity_id=None,
        )
        for index, (source, destination, offset, coefficient) in enumerate(
            specifications
        )
    )
    steps = tuple(
        api.LocalShearStep(
            operation_id="local_canonical_shear",
            source_index=interface.channel_order.index(source),
            destination_index=interface.channel_order.index(destination),
            offset=offset,
            coefficient=coefficient,
        )
        for source, destination, offset, coefficient in specifications
    )
    program = api.LocalShearProgram(
        channel_count=len(interface.channel_order),
        spatial_ndim=interface.spatial_ndim,
        steps=steps,
    )
    rng = np.random.default_rng(20260801)
    state = (
        rng.normal(size=(5, 3, 6, 7))
        + 1j * rng.normal(size=(5, 3, 6, 7))
    ).astype(np.complex128)
    expected = np.stack(
        [
            _apply_reference_sequence(interface, primitives, sample)
            for sample in state
        ],
        axis=0,
    )
    return api, interface, primitives, program, state, expected


def _apply_reference_sequence(interface, primitives, state):
    result = state.copy()
    for primitive in primitives:
        result = _apply_primitive(primitive, interface, result)
    return result


def test_public_api_is_inert_and_backend_is_mandatory() -> None:
    api = _api()

    assert api.__all__ == [
        "BackendPreflight",
        "BackendUnavailableError",
        "CudaUnavailableError",
        "LocalShearProgram",
        "LocalShearStep",
        "make_batched_local_shear_step",
        "preflight_backend",
    ]
    signature = inspect.signature(api.make_batched_local_shear_step)
    assert signature.parameters["backend"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["backend"].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="backend"):
        api.make_batched_local_shear_step(  # type: ignore[call-arg]
            api.LocalShearProgram(
                channel_count=1,
                spatial_ndim=1,
                steps=(
                    api.LocalShearStep(
                        operation_id="neutral_identity",
                        source_index=0,
                        destination_index=0,
                        offset=(0,),
                        coefficient=0.0j,
                    ),
                ),
            )
        )

    source = inspect.getsource(api).lower()
    for forbidden in ("rulespace_v3", "verified", "fft", "projector"):
        assert forbidden not in source


def test_importing_v3_adapter_does_not_load_legacy_backend() -> None:
    command = (
        "import importlib, sys; "
        "importlib.import_module('rulespace_gpu.v3_local_shear'); "
        "assert 'rulespace_gpu.backend' not in sys.modules; "
        "assert 'jax' not in sys.modules; "
        "assert 'mlx' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_legacy_package_exports_remain_lazy_and_compatible() -> None:
    command = (
        "import rulespace_gpu, sys; "
        "assert 'rulespace_gpu.backend' not in sys.modules; "
        "from rulespace_gpu import backend, engine, states, observables; "
        "assert backend.NAME == 'numpy'; "
        "assert engine.__name__ == 'rulespace_gpu.engine'; "
        "assert states.__name__ == 'rulespace_gpu.states'; "
        "assert observables.__name__ == 'rulespace_gpu.observables'"
    )
    environment = dict(os.environ)
    environment["RULESPACE_BACKEND"] = "numpy"
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_numpy_matches_authoritative_ordered_primitive_executor_exactly() -> None:
    api, _, _, program, state, expected = _reference_fixture()
    original = state.copy()

    actual = api.make_batched_local_shear_step(
        program,
        backend="numpy",
    )(state)

    assert type(actual) is np.ndarray
    assert actual.dtype == np.dtype(np.complex128)
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(state, original)


def test_primitive_order_is_sequential_and_observable() -> None:
    api, _, _, program, state, expected = _reference_fixture()
    reversed_program = api.LocalShearProgram(
        channel_count=program.channel_count,
        spatial_ndim=program.spatial_ndim,
        steps=tuple(reversed(program.steps)),
    )

    reversed_result = api.make_batched_local_shear_step(
        reversed_program,
        backend="numpy",
    )(state)

    assert not np.allclose(reversed_result, expected, rtol=0.0, atol=0.0)


@pytest.mark.parametrize("backend", ["numpy", "jax"])
def test_batch_and_chunk_execution_are_equivalent(backend: str) -> None:
    api, _, _, program, state, _ = _reference_fixture()
    if backend == "jax":
        pytest.importorskip("jax")
    runner = api.make_batched_local_shear_step(program, backend=backend)

    whole = np.asarray(runner(state))
    chunked = np.concatenate(
        [
            np.asarray(runner(state[:1])),
            np.asarray(runner(state[1:3])),
            np.asarray(runner(state[3:])),
        ],
        axis=0,
    )

    if backend == "numpy":
        np.testing.assert_array_equal(chunked, whole)
    else:
        np.testing.assert_allclose(chunked, whole, rtol=0.0, atol=2e-15)


def test_jax_x64_matches_numpy_reference() -> None:
    jax = pytest.importorskip("jax")
    api, _, _, program, state, expected = _reference_fixture()

    report = api.preflight_backend("jax")
    actual = api.make_batched_local_shear_step(program, backend="jax")(state)
    jax.block_until_ready(actual)

    assert report.backend == "jax"
    assert report.x64_enabled is True
    assert report.complex_dtype == "complex128"
    assert actual.dtype == np.dtype(np.complex128)
    np.testing.assert_allclose(
        np.asarray(actual),
        expected,
        rtol=0.0,
        atol=2e-15,
    )


def test_backend_selection_rejects_auto_mlx_and_unknown_values() -> None:
    api = _api()

    for backend in ("auto", "mlx", "JAX", "cuda", ""):
        with pytest.raises(ValueError, match="backend"):
            api.preflight_backend(backend)


def test_explicit_jax_request_reports_optional_dependency_absence(
    monkeypatch,
) -> None:
    api = _api()
    original_import = api.importlib.import_module

    def import_without_jax(name):
        if name == "jax":
            raise ModuleNotFoundError("simulated missing optional dependency")
        return original_import(name)

    monkeypatch.setattr(api.importlib, "import_module", import_without_jax)

    with pytest.raises(api.BackendUnavailableError, match="not installed"):
        api.preflight_backend("jax")


def test_jax_cuda_is_fail_closed_without_proven_nvidia_cuda() -> None:
    jax = pytest.importorskip("jax")
    api = _api()
    cuda_devices = tuple(
        device
        for device in jax.devices()
        if device.platform.lower() in {"cuda", "gpu"}
        and (
            "nvidia" in str(getattr(device, "device_kind", "")).lower()
            or "cuda"
            in str(getattr(device.client, "platform_version", "")).lower()
        )
    )

    if cuda_devices:
        report = api.preflight_backend("jax-cuda")
        assert report.backend == "jax-cuda"
        assert report.cuda_devices
    else:
        with pytest.raises(api.CudaUnavailableError, match="CUDA"):
            api.preflight_backend("jax-cuda")


def test_imported_preflight_main_reports_missing_cuda_as_json(capsys) -> None:
    jax = pytest.importorskip("jax")
    api = _api()
    verify = _verify_api()
    cuda_devices = tuple(
        device
        for device in jax.devices()
        if device.platform.lower() in {"cuda", "gpu"}
        and (
            "nvidia" in str(getattr(device, "device_kind", "")).lower()
            or "cuda"
            in str(getattr(device.client, "platform_version", "")).lower()
        )
    )
    if cuda_devices:
        pytest.skip("this assertion covers the no-CUDA fail-closed path")

    assert verify.main(["--backend", "jax-cuda"]) == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["backend"] == "jax-cuda"
    assert payload["passed"] is False
    assert "CUDA" in payload["error"]
    with pytest.raises(api.CudaUnavailableError):
        api.preflight_backend("jax-cuda")


def test_program_and_state_validation_fail_closed() -> None:
    api, _, _, program, state, _ = _reference_fixture()

    with pytest.raises(ValueError, match="operation_id"):
        api.LocalShearStep(
            operation_id="dense_matrix",
            source_index=0,
            destination_index=1,
            offset=(0, 0),
            coefficient=1.0j,
        )
    with pytest.raises(ValueError, match="offset"):
        api.LocalShearProgram(
            channel_count=3,
            spatial_ndim=2,
            steps=(
                api.LocalShearStep(
                    operation_id="local_canonical_shear",
                    source_index=0,
                    destination_index=1,
                    offset=(1,),
                    coefficient=1.0j,
                ),
            ),
        )
    with pytest.raises(ValueError, match="channels must differ"):
        api.LocalShearProgram(
            channel_count=3,
            spatial_ndim=2,
            steps=(
                api.LocalShearStep(
                    operation_id="local_canonical_shear",
                    source_index=0,
                    destination_index=0,
                    offset=(1, 0),
                    coefficient=1.0j,
                ),
            ),
        )
    with pytest.raises(ValueError, match="finite"):
        api.LocalShearStep(
            operation_id="local_canonical_shear",
            source_index=0,
            destination_index=1,
            offset=(0, 0),
            coefficient=complex(np.nan, 0.0),
        )
    with pytest.raises(ValueError, match="non-zero"):
        api.LocalShearStep(
            operation_id="local_canonical_shear",
            source_index=0,
            destination_index=1,
            offset=(0, 0),
            coefficient=0.0j,
        )

    runner = api.make_batched_local_shear_step(program, backend="numpy")
    with pytest.raises(TypeError, match="complex128"):
        runner(state.astype(np.complex64))
    with pytest.raises(ValueError, match="rank"):
        runner(state[:, :, :, 0])
    with pytest.raises(ValueError, match="channel"):
        runner(state[:, :2])
    with pytest.raises(ValueError, match="positive"):
        runner(state[:0])


@pytest.mark.parametrize(
    "coefficient",
    [
        np.complex64(0.5 + 0.25j),
        np.float32(0.5),
        0.5,
        1,
        True,
    ],
    ids=("complex64", "float32", "float", "int", "bool"),
)
def test_coefficient_requires_exact_builtin_complex(coefficient) -> None:
    api = _api()

    with pytest.raises(TypeError, match="built-in complex"):
        api.LocalShearStep(
            operation_id="local_canonical_shear",
            source_index=0,
            destination_index=1,
            offset=(0, 0),
            coefficient=coefficient,
        )


def test_neutral_identity_is_a_copy_and_does_not_change_state() -> None:
    api = _api()
    program = api.LocalShearProgram(
        channel_count=2,
        spatial_ndim=1,
        steps=(
            api.LocalShearStep(
                operation_id="neutral_identity",
                source_index=0,
                destination_index=0,
                offset=(0,),
                coefficient=0.0j,
            ),
        ),
    )
    state = np.arange(24).reshape(3, 2, 4).astype(np.complex128)

    result = api.make_batched_local_shear_step(
        program,
        backend="numpy",
    )(state)

    np.testing.assert_array_equal(result, state)
    assert result is not state
    assert not np.shares_memory(result, state)


def test_v3_preflight_is_inert_machine_readable_and_small() -> None:
    verify = _verify_api()

    report = verify.run_preflight("numpy")

    assert report.backend == "numpy"
    assert report.passed is True
    assert report.dtype == "complex128"
    assert report.batch_size <= 4
    assert report.max_abs_error == 0.0
    assert report.chunk_parity is True
    payload = report.as_dict()
    assert payload["backend"] == "numpy"
    assert payload["passed"] is True

    completed = subprocess.run(
        [sys.executable, "-m", "rulespace_gpu.v3_verify", "--backend", "numpy"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == payload
