"""P0 provenance contracts frozen by the B7 v9.1 machine overlay.

These tests intentionally compare production owners with the signed JSON registry
instead of duplicating field lists in Python.  The future ``ResponseRunSpecV3``
catalog is covered by the root registry test; it must not be imported before the
unique route-selection handoff exists.
"""

from __future__ import annotations

from dataclasses import fields, replace
import importlib.util
import inspect
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPOSITORY / "docsv3/v3-机器合同-B7-v9.1-registry.json"


def _registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _field_names(record_name: str) -> tuple[str, ...]:
    record = _registry()["p0_record_catalog_delta"][record_name]
    return tuple(item["name"] for item in record["field_specs"])


def test_p0_parent_owned_record_fields_exactly_match_v91_overlay() -> None:
    import rulespace_v3.parent_v3_contracts as contracts

    for record_name in (
        "CurrentScenarioResponseContractV3",
        "CurrentCurvatureNormalizerProtocolV1",
        "CurrentReadoutCalibrationSpecV3",
    ):
        record_type = getattr(contracts, record_name)
        assert tuple(item.name for item in fields(record_type)) == _field_names(
            record_name
        )


def test_p0_does_not_preissue_future_response_run_spec_v3_owner() -> None:
    assert importlib.util.find_spec("rulespace_v3.application_response_v3") is None


def test_p0_exported_canonical_owners_accept_no_dependency_injection() -> None:
    import rulespace_v3.parent_v3_contracts as contracts

    assert tuple(
        inspect.signature(
            contracts.current_curvature_normalizer_protocol_v1_payload
        ).parameters
    ) == ("protocol",)
    assert tuple(
        inspect.signature(
            contracts.current_readout_calibration_spec_v3_payload
        ).parameters
    ) == ("spec",)
    assert tuple(
        inspect.signature(
            contracts.current_scenario_response_contract_v3_payload
        ).parameters
    ) == ("contract",)
    assert tuple(
        inspect.signature(
            contracts.verify_current_curvature_normalizer_protocol_v1
        ).parameters
    ) == ("protocol", "response_grid")
    assert tuple(
        inspect.signature(
            contracts.verify_current_readout_calibration_spec_v3
        ).parameters
    ) == ("spec", "geometry", "response_grid")


def test_p0_current_response_payload_order_exactly_matches_v91_overlay() -> None:
    from rulespace_v3.parent_v3_contracts import (
        _geometry_record,
        build_c19_current_application_authority_v3,
        current_scenario_response_contract_v3_payload,
    )

    application = build_c19_current_application_authority_v3()
    response = application.scenario_authorities[0].response_contract
    payload = current_scenario_response_contract_v3_payload(response)

    assert tuple(payload) == _field_names("CurrentScenarioResponseContractV3")[:-1]
    assert tuple(_geometry_record(response.geometry_bundle)) == tuple(
        item.name for item in fields(type(response.geometry_bundle))
    )
    assert response.response_contract_sha != "0" * 64


def _bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def test_p0_current_response_calibration_and_normalizer_bits_are_frozen() -> None:
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.parent_v3_contracts import (
        build_c19_current_application_authority_v3,
        current_curvature_normalizer_protocol_v1_payload,
        current_readout_calibration_spec_v3_payload,
    )

    response = (
        build_c19_current_application_authority_v3()
        .scenario_authorities[0]
        .response_contract
    )
    calibration = response.current_readout_calibration_spec
    normalizer = calibration.curvature_normalizer_protocol

    assert tuple(_bits(value) for value in response.preregistered_phase_bands[0]) == (
        "3ff721fb54442d18",
        "3ffb21fb54442d18",
    )
    assert _bits(response.bridge_tolerance) == "3d719799812dea11"
    assert normalizer.ordered_momentum_fp64_bits == (("3fe921fb54442d18",),)
    assert normalizer.ordered_normalizer_fp64_bits == ("3fe2bec333018867",)
    assert normalizer.response_grid_sha == response.response_grid.response_grid_sha
    assert normalizer.protocol_sha == canonical_sha(
        current_curvature_normalizer_protocol_v1_payload(normalizer)
    )
    assert (
        tuple(current_curvature_normalizer_protocol_v1_payload(normalizer))
        == (_field_names("CurrentCurvatureNormalizerProtocolV1")[:-1])
    )
    assert (
        calibration.geometry_bundle_sha == response.geometry_bundle.geometry_bundle_sha
    )
    assert (
        calibration.source_metric_whitener == response.geometry_bundle.source_whitener
    )
    assert calibration.h_metric_whitener == response.geometry_bundle.h_whitener
    assert (
        calibration.curvature_incidence_operator == response.geometry_bundle.incidence_q
    )
    assert calibration.curvature_incidence_operator.shape == (6, 10)
    assert calibration.curvature_metric_whitener == (
        response.geometry_bundle.curvature_whitener
    )
    assert calibration.spec_sha == canonical_sha(
        current_readout_calibration_spec_v3_payload(calibration)
    )
    assert (
        tuple(current_readout_calibration_spec_v3_payload(calibration))
        == (_field_names("CurrentReadoutCalibrationSpecV3")[:-1])
    )


def test_p0_normalizer_and_calibration_semantic_mutations_fail_after_resigning() -> (
    None
):
    from rulespace_v3.evidence import canonical_sha
    from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
    import rulespace_v3.parent_v3_contracts as contracts

    response = (
        contracts.build_c19_current_application_authority_v3()
        .scenario_authorities[0]
        .response_contract
    )
    calibration = response.current_readout_calibration_spec
    normalizer = calibration.curvature_normalizer_protocol

    changed_normalizer = replace(
        normalizer,
        ordered_normalizer_values=(normalizer.ordered_normalizer_values[0] + 1.0,),
        ordered_normalizer_fp64_bits=(
            _bits(normalizer.ordered_normalizer_values[0] + 1.0),
        ),
        protocol_sha="0" * 64,
    )
    changed_normalizer = replace(
        changed_normalizer,
        protocol_sha=canonical_sha(
            contracts.current_curvature_normalizer_protocol_v1_payload(
                changed_normalizer
            )
        ),
    )
    try:
        contracts.verify_current_curvature_normalizer_protocol_v1(
            changed_normalizer,
            response.response_grid,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("resigned normalizer mutation was accepted")

    changed_source_whitener = frozen_tensor_array(calibration.source_metric_whitener)
    changed_source_whitener[0, 0] += 1.0
    changed_calibration = replace(
        calibration,
        source_metric_whitener=freeze_complex_tensor(changed_source_whitener),
        spec_sha="0" * 64,
    )
    changed_calibration = replace(
        changed_calibration,
        spec_sha=canonical_sha(
            contracts.current_readout_calibration_spec_v3_payload(changed_calibration)
        ),
    )
    try:
        contracts.verify_current_readout_calibration_spec_v3(
            changed_calibration,
            response.geometry_bundle,
            response.response_grid,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("resigned calibration mutation was accepted")


def test_p0_frozen_literals_do_not_reread_redirected_module_globals(
    monkeypatch,
) -> None:
    import rulespace_v3.parent_v3_contracts as contracts

    expected = contracts.build_c19_current_application_authority_v3()
    expected_response = expected.scenario_authorities[0].response_contract
    original_grid_record = contracts._response_grid_record
    monkeypatch.setattr(contracts, "CURRENT_BRIDGE_TOLERANCE", 0.5)
    monkeypatch.setattr(contracts, "CURRENT_PREREGISTERED_PHASE_BANDS", ((0.0, 1.0),))
    monkeypatch.setattr(
        contracts, "CURRENT_REFERENCE_PHASE_BAND_SOURCE_ID", "redirected"
    )
    monkeypatch.setattr(contracts, "CURRENT_CURVATURE_NORMALIZER_ID", "redirected")
    monkeypatch.setattr(
        contracts, "CURRENT_READOUT_CALIBRATION_DERIVATION_ID", "redirected"
    )
    monkeypatch.setattr(
        contracts,
        "math",
        SimpleNamespace(
            pi=3.0,
            sin=lambda _value: 0.0,
            isfinite=lambda _value: False,
        ),
    )
    monkeypatch.setattr(
        contracts,
        "struct",
        SimpleNamespace(pack=lambda *_args: b"redirected"),
    )
    monkeypatch.setattr(
        contracts,
        "_fp64_bits",
        lambda *_args, **_kwargs: "0000000000000000",
    )
    monkeypatch.setattr(
        contracts,
        "_response_grid_record",
        lambda grid: {
            **original_grid_record(grid),
            "response_grid_sha": "a" * 64,
        },
    )
    monkeypatch.setattr(
        contracts,
        "current_curvature_normalizer_protocol_v1_payload",
        lambda _body: {"redirected": True},
    )
    monkeypatch.setattr(
        contracts,
        "current_readout_calibration_spec_v3_payload",
        lambda _body: {"redirected": True},
    )
    monkeypatch.setattr(
        contracts,
        "c19_observer_geometry_bundle_v1_payload",
        lambda _body: {"redirected": True},
    )
    monkeypatch.setattr(
        contracts,
        "_geometry_record",
        lambda _body: {"redirected": True},
    )

    observed = contracts.build_c19_current_application_authority_v3()
    observed_response = observed.scenario_authorities[0].response_contract

    assert observed_response == expected_response
    assert observed.application_authority_sha == expected.application_authority_sha


def test_p0_exported_verifiers_reject_caller_redirected_grid_and_geometry() -> None:
    import rulespace_v3.parent_v3_contracts as contracts

    response = (
        contracts.build_c19_current_application_authority_v3()
        .scenario_authorities[0]
        .response_contract
    )
    redirected_grid = replace(response.response_grid, response_grid_sha="a" * 64)
    redirected_normalizer = contracts._build_current_curvature_normalizer_protocol_v1(
        redirected_grid
    )
    with pytest.raises(ValueError):
        contracts.verify_current_curvature_normalizer_protocol_v1(
            redirected_normalizer,
            redirected_grid,
        )

    redirected_geometry = replace(
        response.geometry_bundle,
        geometry_bundle_sha="b" * 64,
    )
    redirected_calibration = contracts._build_current_readout_calibration_spec_v3(
        redirected_geometry,
        response.response_grid,
    )
    with pytest.raises(ValueError):
        contracts.verify_current_readout_calibration_spec_v3(
            redirected_calibration,
            redirected_geometry,
            response.response_grid,
        )


def test_b2_private_verified_view_adds_live_permit_without_public_wire_change() -> None:
    import rulespace_v3.application_materialization_v3 as materialization

    private_fields = tuple(
        item.name
        for item in fields(materialization._VerifiedApplicationMaterializationViewV3)
    )
    assert private_fields == (
        "materialization",
        "actual_factory",
        "matched_ablated_factory",
        "permit",
    )
    assert tuple(
        item.name
        for item in fields(materialization.ApplicationScenarioMaterializationV3)
    ) == (
        "materialization_schema_version",
        "permit",
        "current_application_authority",
        "current_scenario_authority",
        "current_scenario_response_contract",
        "basis_contract",
        "construction_trace",
        "ablation_pair_snapshot",
        "actual_factory_binding",
        "matched_ablated_factory_binding",
        "materialization_sha",
    )


def test_parent_construction_and_slice2_replay_closures_cover_v91_additions() -> None:
    import rulespace_v3.parent_candidate_v3 as candidate
    import rulespace_v3.parent_v3_contracts as contracts

    additions = set(_registry()["p0_effective_merge"]["source_closure_additions"])
    observed = set(contracts._CONSTRUCTION_DEPENDENCY_PATHS) | set(
        candidate._SLICE2_CORE_REPLAY_SOURCE_PATHS
    )

    assert additions <= observed


def test_slice2_selector_includes_only_the_two_new_json_authorities() -> None:
    import rulespace_v3.parent_candidate_v3 as candidate

    assert candidate._source_path_is_selected(
        "docsv3/v3-机器合同-B7-v9.1-registry.json"
    )
    assert candidate._source_path_is_selected(
        "tests/fixtures/v3m0_b7_legacy_response_18b0d43.json"
    )
    assert not candidate._source_path_is_selected("docsv3/unfrozen.json")
    assert not candidate._source_path_is_selected("tests/fixtures/unfrozen.json")
