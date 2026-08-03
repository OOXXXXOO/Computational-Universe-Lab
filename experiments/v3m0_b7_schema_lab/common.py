"""Owner-neutral common contracts for the B7 schema laboratory."""

from __future__ import annotations

import rulespace_v3.b7_replay_core_v1 as _pure_core


class B7LabMutationRejected(ValueError):
    """Frozen route-level rejection surface for one invalid lab wire."""


def validate_response_run_spec_fixture_v1(
    raw_body,
    provenance_raw,
    graph_raw,
):
    """Delegate one response-run-spec raw validation to the pure core."""
    return _pure_core.validate_response_run_spec_fixture_v1(
        raw_body,
        provenance_raw,
        graph_raw,
    )


def validate_endpoint_reference_outcome_raw_v1(raw_body):
    """Delegate one endpoint-reference raw validation to the pure core."""
    return _pure_core.validate_endpoint_reference_outcome_raw_v1(raw_body)


def validate_endpoint_shell_outcome_raw_v1(raw_body):
    """Delegate one endpoint-shell raw validation to the pure core."""
    return _pure_core.validate_endpoint_shell_outcome_raw_v1(raw_body)


def validate_source_readout_response_raw_v1(
    raw_body,
    run_spec_raw,
    provenance_raw,
    graph_raw,
):
    """Delegate one source/readout raw validation to the pure core."""
    return _pure_core.validate_source_readout_response_raw_v1(
        raw_body,
        run_spec_raw,
        provenance_raw,
        graph_raw,
    )


def validate_synthetic_parent_freeze_v3_body_v1(raw_body):
    """Delegate one synthetic Parent raw validation to the pure core."""
    return _pure_core.validate_synthetic_parent_freeze_v3_body_v1(raw_body)


def validate_synthetic_component_body_v1(
    raw_body,
    ordered_components_raw,
    parent_raw,
):
    """Delegate one synthetic component raw validation to the pure core."""
    return _pure_core.validate_synthetic_component_body_v1(
        raw_body,
        ordered_components_raw,
        parent_raw,
    )


def validate_provenance_fixture_v1(raw_body):
    """Delegate one provenance fixture validation to the pure core."""
    return _pure_core.validate_provenance_fixture_v1(raw_body)


def validate_branch_attempt_v1(raw_body):
    """Delegate one branch-attempt validation to the pure core."""
    return _pure_core.validate_branch_attempt_v1(raw_body)
