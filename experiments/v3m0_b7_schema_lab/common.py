"""Owner-neutral common contracts for the B7 schema laboratory."""

from __future__ import annotations

import ast as _ast
import difflib as _difflib

import rulespace_v3.b7_replay_core_v1 as _pure_core


LAB_EXACT_RECORD_CATALOGS_V2 = (
    (
        "B7LabEnvironmentManifestV1",
        "experimental.v3m0.b7.environment-manifest.v1",
        "environment_sha",
        (
            (
                "environment_schema_version",
                "Literal[experimental.v3m0.b7.environment-manifest.v1]",
                "required",
                None,
            ),
            ("python_implementation", "str", "required", None),
            ("python_version", "str", "required", None),
            (
                "python_executable_realpath",
                "absolute-normalized-path",
                "required",
                None,
            ),
            ("python_executable_raw_sha256", "sha256", "required", None),
            ("numpy_version", "str", "required", None),
            ("scipy_version", "str", "required", None),
            ("platform_system", "str", "required", None),
            ("platform_release", "str", "required", None),
            ("platform_machine", "str", "required", None),
            ("numpy_float64_dtype_str", "str", "required", None),
            ("numpy_float64_itemsize", "Literal[8]", "required", None),
            ("byteorder", "Literal[little,big]", "required", None),
            ("python_hash_seed", "str", "required", None),
            (
                "blas_thread_settings",
                "tuple[tuple[str,str],...;exact=5]",
                "required",
                None,
            ),
            ("threadpool_info", "canonical-json-array", "required", None),
            ("fresh_process_per_capture", "Literal[true]", "required", None),
            ("environment_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabEnvironmentManifestV2",
        "experimental.v3m0.b7.environment-manifest.v2",
        "environment_sha",
        (
            (
                "environment_schema_version",
                "Literal[experimental.v3m0.b7.environment-manifest.v2]",
                "required",
                None,
            ),
            ("python_implementation", "str", "required", None),
            ("python_version", "str", "required", None),
            (
                "python_invocation_path",
                "absolute-normalized-path",
                "required",
                None,
            ),
            (
                "python_executable_realpath",
                "absolute-normalized-path",
                "required",
                None,
            ),
            ("python_executable_raw_sha256", "sha256", "required", None),
            ("python_invocation_identity_sha", "sha256", "required", None),
            (
                "python_venv_prefix",
                "absolute-normalized-path",
                "required",
                None,
            ),
            (
                "python_pyvenv_cfg_path",
                "absolute-normalized-path",
                "required",
                None,
            ),
            ("python_pyvenv_cfg_raw_sha256", "sha256", "required", None),
            ("numpy_version", "str", "required", None),
            ("scipy_version", "str", "required", None),
            ("platform_system", "str", "required", None),
            ("platform_release", "str", "required", None),
            ("platform_machine", "str", "required", None),
            ("numpy_float64_dtype_str", "str", "required", None),
            ("numpy_float64_itemsize", "Literal[8]", "required", None),
            ("byteorder", "Literal[little,big]", "required", None),
            ("python_hash_seed", "str", "required", None),
            (
                "blas_thread_settings",
                "tuple[tuple[str,str],...;exact=5]",
                "required",
                None,
            ),
            ("threadpool_info", "canonical-json-array", "required", None),
            ("fresh_process_per_capture", "Literal[true]", "required", None),
            ("environment_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabProvenanceFixtureV1",
        "experimental.v3m0.b7.provenance-fixture.v1",
        "provenance_fixture_sha",
        (
            (
                "provenance_fixture_schema_version",
                "Literal[experimental.v3m0.b7.provenance-fixture.v1]",
                "required",
                None,
            ),
            ("parent_freeze_v3_body", "canonical-json-object", "required", None),
            ("permit_body", "canonical-json-object", "required", None),
            ("materialization_body", "canonical-json-object", "required", None),
            (
                "current_scenario_response_contract_v3_body",
                "canonical-json-object",
                "required",
                None,
            ),
            (
                "actual_bridge_grid_authority_body",
                "canonical-json-object",
                "required",
                None,
            ),
            (
                "matched_ablated_bridge_grid_authority_body",
                "canonical-json-object",
                "required",
                None,
            ),
            ("provenance_fixture_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabBranchAttemptV1",
        "experimental.v3m0.b7.branch-attempt.v1",
        "attempt_sha",
        (
            (
                "branch_attempt_schema_version",
                "Literal[experimental.v3m0.b7.branch-attempt.v1]",
                "required",
                None,
            ),
            ("branch", "Literal[actual,matched_ablated]", "required", None),
            (
                "response_values",
                "Optional[FrozenComplexTensor-raw-body]",
                "required-nullable",
                None,
            ),
            (
                "bridge_audit",
                "Optional[SourceReadoutBridgeAudit-raw-body]",
                "required-nullable",
                None,
            ),
            ("failure", "Optional[branch-failure]", "required-nullable", None),
            ("attempt_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LeafDigestV1",
        "experimental.v3m0.b7.leaf-digest.v1",
        None,
        (
            ("leaf_id", "scheduler-stage-id", "required", None),
            ("call_ordinal", "nonnegative-int", "required", None),
            ("input_body_sha", "sha256", "required", None),
            ("output_body_sha", "sha256", "required", None),
        ),
    ),
    (
        "NormalizedB7ExecutionTranscriptV1",
        "experimental.v3m0.b7.normalized-transcript.v1",
        "experimental_sha",
        (
            (
                "transcript_schema_version",
                "Literal[experimental.v3m0.b7.normalized-transcript.v1]",
                "required",
                None,
            ),
            ("corpus_spec_sha", "sha256", "required", None),
            ("case_id", "case-id", "required", None),
            ("environment_manifest_sha", "sha256", "required", None),
            (
                "provenance_fixture",
                "B7LabProvenanceFixtureV1",
                "required",
                "B7LabProvenanceFixtureV1",
            ),
            ("response_run_spec_fixture", "canonical-json-object", "required", None),
            ("reference_outcome", "canonical-json-object", "required", None),
            (
                "shell_outcome",
                "Optional[canonical-json-object]",
                "required-nullable",
                None,
            ),
            (
                "actual_branch_attempt",
                "Optional[B7LabBranchAttemptV1]",
                "required-nullable",
                "B7LabBranchAttemptV1",
            ),
            (
                "matched_ablated_branch_attempt",
                "Optional[B7LabBranchAttemptV1]",
                "required-nullable",
                "B7LabBranchAttemptV1",
            ),
            (
                "actual_completed_response",
                "Optional[canonical-json-object]",
                "required-nullable",
                None,
            ),
            (
                "matched_ablated_completed_response",
                "Optional[canonical-json-object]",
                "required-nullable",
                None,
            ),
            ("terminal_tag", "terminal-tag", "required", None),
            ("callback_trace", "tuple[scheduler-stage-id,...]", "required", None),
            (
                "ordered_leaf_digests",
                "tuple[B7LeafDigestV1,...]",
                "required",
                "B7LeafDigestV1",
            ),
            ("experimental_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabCorpusCaseV1",
        "experimental.v3m0.b7.corpus-case.v1",
        "case_sha",
        (
            (
                "case_schema_version",
                "Literal[experimental.v3m0.b7.corpus-case.v1]",
                "required",
                None,
            ),
            ("case_ordinal", "nonnegative-int", "required", None),
            ("case_id", "case-id", "required", None),
            ("terminal_tag", "terminal-tag", "required", None),
            (
                "injected_failure_stage",
                "Optional[scheduler-stage-id]",
                "required-nullable",
                None,
            ),
            ("presence_bits", "binary-string-width-9", "required", None),
            (
                "actual_attempt_failure",
                "Optional[branch-failure]",
                "required-nullable",
                None,
            ),
            (
                "matched_ablated_attempt_failure",
                "Optional[branch-failure]",
                "required-nullable",
                None,
            ),
            (
                "expected_callback_trace",
                "tuple[scheduler-stage-id,...]",
                "required",
                None,
            ),
            ("expected_leaf_ids", "tuple[scheduler-stage-id,...]", "required", None),
            ("case_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabNestedBodyRuleV1",
        "experimental.v3m0.b7.nested-body-rule.v1",
        "rule_sha",
        (
            (
                "rule_schema_version",
                "Literal[experimental.v3m0.b7.nested-body-rule.v1]",
                "required",
                None,
            ),
            ("json_pointer", "json-pointer", "required", None),
            ("body_kind", "str", "required", None),
            ("hash_field", "Optional[str]", "required-nullable", None),
            ("nullable", "bool", "required", None),
            ("full_body_required", "Literal[true]", "required", None),
            ("rule_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabCorpusSpecV1",
        "experimental.v3m0.b7.corpus-spec.v1",
        "corpus_spec_sha",
        (
            (
                "corpus_spec_schema_version",
                "Literal[experimental.v3m0.b7.corpus-spec.v1]",
                "required",
                None,
            ),
            (
                "transcript_schema_version",
                "Literal[experimental.v3m0.b7.normalized-transcript.v1]",
                "required",
                None,
            ),
            (
                "canonical_json_profile_id",
                "Literal[canonical-json-sha256-v1]",
                "required",
                None,
            ),
            (
                "scheduler_stage_order",
                "tuple[scheduler-stage-id;exact=6]",
                "required",
                None,
            ),
            ("presence_pointer_order", "tuple[json-pointer;exact=9]", "required", None),
            ("terminal_tag_order", "tuple[terminal-tag;exact=7]", "required", None),
            ("case_contract_sha", "sha256", "required", None),
            (
                "ordered_case_specs",
                "tuple[B7LabCorpusCaseV1;exact=7]",
                "required",
                "B7LabCorpusCaseV1",
            ),
            (
                "nested_body_rules",
                "tuple[B7LabNestedBodyRuleV1,...]",
                "required",
                "B7LabNestedBodyRuleV1",
            ),
            (
                "mutation_algorithm_id",
                "Literal[v3m0-b7-exhaustive-mutation-v1]",
                "required",
                None,
            ),
            ("mutation_class_order", "tuple[mutation-class;exact=9]", "required", None),
            (
                "mutation_operation_order",
                "tuple[mutation-operation;exact=8]",
                "required",
                None,
            ),
            ("mutation_generation_contract_sha", "sha256", "required", None),
            (
                "mutation_generation_rules",
                "tuple[Literal[M01_PRESENCE_TOGGLE,M02_TERMINAL_TAG_OTHER_SIX,M03_BRANCH_FAILURE_SPLICE,M04_DELETE_SUCCESSFUL_PREFIX_BODY,M05_INJECT_POST_FAILURE_BODY,M06_NESTED_SHA_SINGLE_POINT,M07_CROSS_CASE_BODY_SPLICE,M08_CANONICAL_ROUNDTRIP,M09_CANONICAL_REPEAT,M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT];exact=10]",
                "required",
                None,
            ),
            (
                "upstream_invalid_probe_rule",
                "Literal[M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT]",
                "required",
                None,
            ),
            ("metric_spec_sha", "sha256", "required", None),
            ("corpus_spec_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabCorpusFixtureV1",
        "experimental.v3m0.b7.corpus-fixture.v1",
        "fixture_sha",
        (
            (
                "fixture_schema_version",
                "Literal[experimental.v3m0.b7.corpus-fixture.v1]",
                "required",
                None,
            ),
            ("corpus_spec", "B7LabCorpusSpecV1", "required", "B7LabCorpusSpecV1"),
            (
                "mutation_universe",
                "B7LabMutationUniverseV1",
                "required",
                "B7LabMutationUniverseV1",
            ),
            ("metric_spec", "B7LabMetricSpecV1", "required", "B7LabMetricSpecV1"),
            (
                "environment_manifest",
                "B7LabEnvironmentManifestV1",
                "required",
                "B7LabEnvironmentManifestV1",
            ),
            (
                "ordered_d0_transcripts",
                "tuple[NormalizedB7ExecutionTranscriptV1;exact=7]",
                "required",
                "NormalizedB7ExecutionTranscriptV1",
            ),
            ("fixture_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabCorpusFixtureV2",
        "experimental.v3m0.b7.corpus-fixture.v2",
        "fixture_sha",
        (
            (
                "fixture_schema_version",
                "Literal[experimental.v3m0.b7.corpus-fixture.v2]",
                "required",
                None,
            ),
            ("corpus_spec", "B7LabCorpusSpecV1", "required", "B7LabCorpusSpecV1"),
            (
                "mutation_universe",
                "B7LabMutationUniverseV1",
                "required",
                "B7LabMutationUniverseV1",
            ),
            ("metric_spec", "B7LabMetricSpecV1", "required", "B7LabMetricSpecV1"),
            (
                "environment_manifest",
                "B7LabEnvironmentManifestV2",
                "required",
                "B7LabEnvironmentManifestV2",
            ),
            (
                "synthetic_graph_manifest",
                "B7LabSyntheticGraphManifestV1",
                "required",
                "B7LabSyntheticGraphManifestV1",
            ),
            (
                "ordered_d0_transcripts",
                "tuple[NormalizedB7ExecutionTranscriptV1;exact=7]",
                "required",
                "NormalizedB7ExecutionTranscriptV1",
            ),
            ("fixture_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabMutationV1",
        "experimental.v3m0.b7.mutation.v1",
        "mutation_sha",
        (
            (
                "mutation_schema_version",
                "Literal[experimental.v3m0.b7.mutation.v1]",
                "required",
                None,
            ),
            ("mutation_ordinal", "nonnegative-int", "required", None),
            ("mutation_id", "str", "required", None),
            ("base_case_id", "Optional[case-id]", "required-nullable", None),
            ("probe_kind", "probe-kind", "required", None),
            ("mutation_class", "mutation-class", "required", None),
            ("target_json_pointer", "json-pointer", "required", None),
            ("operation", "mutation-operation", "required", None),
            (
                "replacement_json",
                "Optional[canonical-json-value]",
                "required-nullable",
                None,
            ),
            ("expected_boundary", "expected-boundary", "required", None),
            ("mutation_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabMutationUniverseV1",
        "experimental.v3m0.b7.mutation-universe.v1",
        "mutation_universe_sha",
        (
            (
                "mutation_universe_schema_version",
                "Literal[experimental.v3m0.b7.mutation-universe.v1]",
                "required",
                None,
            ),
            ("corpus_spec_sha", "sha256", "required", None),
            ("mutation_generation_contract_sha", "sha256", "required", None),
            ("generator_source_sha256", "sha256", "required", None),
            (
                "ordered_mutations",
                "tuple[B7LabMutationV1,...]",
                "required",
                "B7LabMutationV1",
            ),
            ("mutation_count", "nonnegative-int", "required", None),
            ("mutation_universe_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabRouteManifestV1",
        "experimental.v3m0.b7.route-manifest.v1",
        "route_manifest_sha",
        (
            (
                "route_manifest_schema_version",
                "Literal[experimental.v3m0.b7.route-manifest.v1]",
                "required",
                None,
            ),
            ("route_id", "route-id", "required", None),
            ("route_schema_domain", "route-domain", "required", None),
            ("route_module", "module-name", "required", None),
            ("route_source_path", "repo-relative-posix-path", "required", None),
            ("wire_schema_id", "route-wire-schema-id", "required", None),
            ("route_commit_sha", "git-sha1", "required", None),
            ("route_source_sha256", "sha256", "required", None),
            ("common_commit_sha", "git-sha1", "required", None),
            ("common_source_sha256", "sha256", "required", None),
            ("compare_source_sha256", "sha256", "required", None),
            ("corpus_spec_sha", "sha256", "required", None),
            ("mutation_universe_sha", "sha256", "required", None),
            ("metric_spec_sha", "sha256", "required", None),
            (
                "encoder_symbol",
                "Literal[encode_normalized_transcript]",
                "required",
                None,
            ),
            (
                "verifier_decoder_symbol",
                "Literal[verify_and_decode_route_wire]",
                "required",
                None,
            ),
            (
                "input_schema_version",
                "Literal[experimental.v3m0.b7.normalized-transcript.v1]",
                "required",
                None,
            ),
            ("output_schema_version", "route-wire-schema-id", "required", None),
            ("static_api_scan_sha", "sha256", "required", None),
            ("static_import_scan_sha", "sha256", "required", None),
            ("static_authority_surface_scan_sha", "sha256", "required", None),
            ("production_import_scan_sha", "sha256", "required", None),
            ("production_imported_by_route", "Literal[false]", "required", None),
            ("route_imported_by_production", "Literal[false]", "required", None),
            ("authority_surface_count", "Literal[0]", "required", None),
            ("wrapper_surface_count", "Literal[0]", "required", None),
            ("route_manifest_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabGateObservationV1",
        "experimental.v3m0.b7.gate-observation.v1",
        "observation_sha",
        (
            (
                "gate_observation_schema_version",
                "Literal[experimental.v3m0.b7.gate-observation.v1]",
                "required",
                None,
            ),
            ("gate_id", "gate-id", "required", None),
            ("phase", "Literal[D0,D1]", "required", None),
            ("route_id", "route-id", "required", None),
            ("domain_root_sha", "sha256", "required", None),
            ("predicate_ids", "tuple[str,...]", "required", None),
            (
                "predicate_result_bits",
                "binary-string-variable-width-nonempty",
                "required",
                None,
            ),
            ("failure_reason_codes", "tuple[str,...]", "required", None),
            ("observation_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabGateOutcomeV1",
        "experimental.v3m0.b7.gate-outcome.v1",
        "gate_outcome_sha",
        (
            (
                "gate_outcome_schema_version",
                "Literal[experimental.v3m0.b7.gate-outcome.v1]",
                "required",
                None,
            ),
            ("gate_id", "gate-id", "required", None),
            ("gate_validator_id", "validator-id", "required", None),
            ("phase", "Literal[D0,D1]", "required", None),
            (
                "observation",
                "B7LabGateObservationV1",
                "required",
                "B7LabGateObservationV1",
            ),
            ("passed", "bool", "required", None),
            ("observation_sha", "sha256", "required", None),
            ("reason_codes", "tuple[str,...]", "required", None),
            ("gate_outcome_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabD0RouteResultV1",
        "experimental.v3m0.b7.d0-route-result.v1",
        "route_result_sha",
        (
            (
                "route_result_schema_version",
                "Literal[experimental.v3m0.b7.d0-route-result.v1]",
                "required",
                None,
            ),
            ("route_id", "route-id", "required", None),
            (
                "route_manifest",
                "B7LabRouteManifestV1",
                "required",
                "B7LabRouteManifestV1",
            ),
            ("route_manifest_sha", "sha256", "required", None),
            ("route_commit_sha", "git-sha1", "required", None),
            ("legal_case_count", "nonnegative-int", "required", None),
            ("legal_case_accept_count", "nonnegative-int", "required", None),
            ("mutation_probe_count", "nonnegative-int", "required", None),
            ("mutation_accept_count", "nonnegative-int", "required", None),
            ("upstream_invalid_probe_count", "nonnegative-int", "required", None),
            ("upstream_invalid_transcript_count", "nonnegative-int", "required", None),
            ("evidence_loss_count", "nonnegative-int", "required", None),
            (
                "constructible_invalid_presence_count",
                "nonnegative-int",
                "required",
                None,
            ),
            ("half_pair_state_count", "nonnegative-int", "required", None),
            (
                "gate_outcomes",
                "tuple[B7LabGateOutcomeV1;exact=7]",
                "required",
                "B7LabGateOutcomeV1",
            ),
            ("survives_d0", "bool", "required", None),
            ("route_result_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabD0ComparisonV1",
        "experimental.v3m0.b7.d0-comparison.v1",
        "d0_result_sha",
        (
            (
                "d0_result_schema_version",
                "Literal[experimental.v3m0.b7.d0-comparison.v1]",
                "required",
                None,
            ),
            ("common_commit_sha", "git-sha1", "required", None),
            ("common_source_sha256", "sha256", "required", None),
            ("compare_source_sha256", "sha256", "required", None),
            ("corpus_fixture_raw_sha256", "sha256", "required", None),
            ("corpus_spec_sha", "sha256", "required", None),
            ("mutation_universe_sha", "sha256", "required", None),
            ("metric_spec_sha", "sha256", "required", None),
            (
                "environment_manifest",
                "B7LabEnvironmentManifestV2",
                "required",
                "B7LabEnvironmentManifestV2",
            ),
            (
                "ordered_route_results",
                "tuple[B7LabD0RouteResultV1;exact=3]",
                "required",
                "B7LabD0RouteResultV1",
            ),
            ("surviving_route_ids", "tuple[route-id,...]", "required", None),
            ("decision_payload_sha", "sha256", "required", None),
            ("auxiliary_benchmark", "canonical-json-object", "required", None),
            ("d0_result_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabMetricSpecV1",
        "experimental.v3m0.b7.metric-spec.v1",
        "metric_spec_sha",
        (
            (
                "metric_spec_schema_version",
                "Literal[experimental.v3m0.b7.metric-spec.v1]",
                "required",
                None,
            ),
            (
                "metric_algorithm_id",
                "Literal[v3m0-b7-schema-metrics-v1]",
                "required",
                None,
            ),
            ("metric_contract_sha", "sha256", "required", None),
            ("metric_order", "tuple[metric-id;exact=10]", "required", None),
            (
                "evidence_pointer_order",
                "tuple[json-pointer;exact=15]",
                "required",
                None,
            ),
            ("invalid_presence_bit_width", "Literal[9]", "required", None),
            (
                "reachable_closure_algorithm_id",
                "Literal[python-ast-route-local-reachable-closure-v1]",
                "required",
                None,
            ),
            (
                "branch_count_algorithm_id",
                "Literal[python-ast-branch-contribution-v1]",
                "required",
                None,
            ),
            (
                "b8_diff_algorithm_id",
                "Literal[python-difflib-unified-n0-v1]",
                "required",
                None,
            ),
            ("common_source_sha256", "sha256", "required", None),
            ("compare_source_sha256", "sha256", "required", None),
            ("metric_spec_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabSyntheticComponentBodyV1",
        "experimental.v3m0.b7.synthetic-component-body.v1",
        "component_sha",
        (
            (
                "component_body_schema_version",
                "Literal[experimental.v3m0.b7.synthetic-component-body.v1]",
                "required",
                None,
            ),
            ("component_id", "synthetic-graph-component-id", "required", None),
            ("body_type", "fully-qualified-type-name", "required", None),
            ("complete_body", "canonical-json-object", "required", None),
            ("body_raw_canonical_sha256", "sha256", "required", None),
            ("body_self_hash_field", "str", "required", None),
            ("body_self_hash_value", "sha256", "required", None),
            (
                "lineage_parent_component_ids",
                "tuple[synthetic-graph-component-id,...]",
                "required",
                None,
            ),
            ("fejer_order", "Literal[256]", "required", None),
            ("component_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabTBearerBindingV1",
        "experimental.v3m0.b7.t-bearer-binding.v1",
        "binding_sha",
        (
            (
                "binding_schema_version",
                "Literal[experimental.v3m0.b7.t-bearer-binding.v1]",
                "required",
                None,
            ),
            ("component_id", "synthetic-graph-component-id", "required", None),
            ("body_sha", "sha256", "required", None),
            ("fejer_order", "Literal[256]", "required", None),
            ("binding_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabSyntheticGraphManifestV1",
        "experimental.v3m0.b7.synthetic-graph-manifest.v1",
        "graph_sha",
        (
            (
                "graph_manifest_schema_version",
                "Literal[experimental.v3m0.b7.synthetic-graph-manifest.v1]",
                "required",
                None,
            ),
            (
                "graph_profile_id",
                "Literal[v3m0-b7-d1-nonauthority-synthetic-private-graph-v1]",
                "required",
                None,
            ),
            ("authority_state", "Literal[NON_AUTHORITY_SYNTHETIC]", "required", None),
            ("parent_freeze_v3_body", "canonical-json-object", "required", None),
            ("parent_freeze_v3_sha", "sha256", "required", None),
            ("synthetic_graph_component_root_sha", "sha256", "required", None),
            ("selected_fejer_order", "Literal[256]", "required", None),
            ("calibration_selection_sha", "sha256", "required", None),
            ("permit_sha", "sha256", "required", None),
            ("permit_fejer_order", "Literal[256]", "required", None),
            ("materialization_sha", "sha256", "required", None),
            ("materialization_fejer_order", "Literal[256]", "required", None),
            ("actual_transition_outcome_sha", "sha256", "required", None),
            ("matched_ablated_transition_outcome_sha", "sha256", "required", None),
            ("actual_metric_authority_sha", "sha256", "required", None),
            ("matched_ablated_metric_authority_sha", "sha256", "required", None),
            ("actual_bridge_grid_authority_sha", "sha256", "required", None),
            ("matched_ablated_bridge_grid_authority_sha", "sha256", "required", None),
            ("actual_certificate_outcome_sha", "sha256", "required", None),
            ("matched_ablated_certificate_outcome_sha", "sha256", "required", None),
            (
                "ordered_component_bodies",
                "tuple[B7LabSyntheticComponentBodyV1;exact=11]",
                "required",
                "B7LabSyntheticComponentBodyV1",
            ),
            (
                "ordered_t_bearer_bindings",
                "tuple[B7LabTBearerBindingV1;exact=11]",
                "required",
                "B7LabTBearerBindingV1",
            ),
            ("graph_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabMetricVectorV1",
        "experimental.v3m0.b7.metric-vector.v1",
        "metric_vector_sha",
        (
            ("mutation_accept_count", "nonnegative-int", "required", None),
            ("evidence_loss_count", "nonnegative-int", "required", None),
            (
                "constructible_invalid_presence_count",
                "nonnegative-int",
                "required",
                None,
            ),
            ("half_pair_state_count", "nonnegative-int", "required", None),
            ("b8_consumer_assertion_count", "nonnegative-int", "required", None),
            ("b8_consumer_changed_loc", "nonnegative-int", "required", None),
            ("verifier_branch_count", "nonnegative-int", "required", None),
            ("route_record_count", "nonnegative-int", "required", None),
            ("route_hash_layer_count", "nonnegative-int", "required", None),
            ("canonical_wire_bytes", "nonnegative-int", "required", None),
            ("metric_vector_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabCrossReplayCellV1",
        "experimental.v3m0.b7.cross-replay-cell.v1",
        "cell_sha",
        (
            (
                "cell_schema_version",
                "Literal[experimental.v3m0.b7.cross-replay-cell.v1]",
                "required",
                None,
            ),
            ("capture_ordinal", "Literal[0,1,2]", "required", None),
            ("case_count", "Literal[7]", "required", None),
            ("ordered_case_ids", "tuple[case-id;exact=7]", "required", None),
            ("transcript_set_sha", "sha256", "required", None),
            ("synthetic_graph_manifest_sha", "sha256", "required", None),
            ("route_id", "route-id", "required", None),
            ("route_manifest_sha", "sha256", "required", None),
            ("route_wire_set_sha", "sha256", "required", None),
            ("decoded_transcript_set_sha", "sha256", "required", None),
            ("ordered_leaf_digest_set_sha", "sha256", "required", None),
            ("exact_transcript_match", "bool", "required", None),
            ("cell_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabD1RouteResultV1",
        "experimental.v3m0.b7.d1-route-result.v1",
        "route_result_sha",
        (
            (
                "route_result_schema_version",
                "Literal[experimental.v3m0.b7.d1-route-result.v1]",
                "required",
                None,
            ),
            ("route_id", "route-id", "required", None),
            (
                "route_manifest",
                "B7LabRouteManifestV1",
                "required",
                "B7LabRouteManifestV1",
            ),
            ("route_manifest_sha", "sha256", "required", None),
            ("route_commit_sha", "git-sha1", "required", None),
            (
                "ordered_cross_replay_cells",
                "tuple[B7LabCrossReplayCellV1;exact=3]",
                "required",
                "B7LabCrossReplayCellV1",
            ),
            (
                "gate_outcomes",
                "tuple[B7LabGateOutcomeV1;exact=8]",
                "required",
                "B7LabGateOutcomeV1",
            ),
            ("metric_vector", "B7LabMetricVectorV1", "required", "B7LabMetricVectorV1"),
            ("survives_d1", "bool", "required", None),
            ("route_result_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabD1ComparisonV1",
        "experimental.v3m0.b7.d1-comparison.v1",
        "d1_result_sha",
        (
            (
                "d1_result_schema_version",
                "Literal[experimental.v3m0.b7.d1-comparison.v1]",
                "required",
                None,
            ),
            ("d0_result_raw_sha256", "sha256", "required", None),
            ("d0_result_sha", "sha256", "required", None),
            ("d0_decision_payload_sha", "sha256", "required", None),
            ("common_commit_sha", "git-sha1", "required", None),
            ("common_source_sha256", "sha256", "required", None),
            ("compare_source_sha256", "sha256", "required", None),
            ("leaf_provider_source_sha256", "sha256", "required", None),
            ("corpus_fixture_raw_sha256", "sha256", "required", None),
            ("corpus_spec_sha", "sha256", "required", None),
            ("mutation_universe_sha", "sha256", "required", None),
            ("metric_spec_sha", "sha256", "required", None),
            (
                "synthetic_graph_manifest",
                "B7LabSyntheticGraphManifestV1",
                "required",
                "B7LabSyntheticGraphManifestV1",
            ),
            (
                "environment_manifest",
                "B7LabEnvironmentManifestV2",
                "required",
                "B7LabEnvironmentManifestV2",
            ),
            (
                "ordered_capture_transcript_set_shas",
                "tuple[sha256;exact=3]",
                "required",
                None,
            ),
            (
                "ordered_capture_leaf_digest_set_shas",
                "tuple[sha256;exact=3]",
                "required",
                None,
            ),
            (
                "ordered_route_results",
                "tuple[B7LabD1RouteResultV1,...]",
                "required",
                "B7LabD1RouteResultV1",
            ),
            ("surviving_route_ids", "tuple[route-id,...]", "required", None),
            (
                "minimum_metric_vector",
                "Optional[B7LabMetricVectorV1]",
                "required-nullable",
                "B7LabMetricVectorV1",
            ),
            (
                "provisional_winner_route_id",
                "Optional[route-id]",
                "required-nullable",
                None,
            ),
            ("tie_detected", "bool", "required", None),
            ("decision_payload_sha", "sha256", "required", None),
            ("auxiliary_benchmark", "canonical-json-object", "required", None),
            ("d1_result_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabReplayReportV1",
        "experimental.v3m0.b7.replay-report.v1",
        "replay_report_sha",
        (
            (
                "replay_report_schema_version",
                "Literal[experimental.v3m0.b7.replay-report.v1]",
                "required",
                None,
            ),
            ("reviewer_role", "Literal[CORPUS_REPLAY,METRIC_REPLAY]", "required", None),
            ("review_protocol_id", "review-protocol-id", "required", None),
            ("lab_evidence_commit_sha", "git-sha1", "required", None),
            ("replay_input_root_sha", "sha256", "required", None),
            ("recomputed_d0_decision_payload_sha", "sha256", "required", None),
            ("recomputed_d1_decision_payload_sha", "sha256", "required", None),
            ("observed_surviving_route_ids", "tuple[route-id,...]", "required", None),
            ("observed_provisional_winner_route_id", "route-id", "required", None),
            ("replay_output_root_sha", "sha256", "required", None),
            ("replay_report_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabReviewerReceiptV1",
        "experimental.v3m0.b7.reviewer-receipt.v1",
        "receipt_sha",
        (
            (
                "receipt_schema_version",
                "Literal[experimental.v3m0.b7.reviewer-receipt.v1]",
                "required",
                None,
            ),
            ("reviewer_id", "str", "required", None),
            ("reviewer_role", "Literal[CORPUS_REPLAY,METRIC_REPLAY]", "required", None),
            ("review_protocol_id", "review-protocol-id", "required", None),
            ("reviewed_lab_evidence_commit_sha", "git-sha1", "required", None),
            ("review_environment_manifest_sha", "sha256", "required", None),
            (
                "observed_review_environment_manifest_sha",
                "Optional[sha256]",
                "required-nullable",
                None,
            ),
            ("review_environment_precheck_passed", "bool", "required", None),
            ("reviewed_d0_result_raw_sha256", "sha256", "required", None),
            ("reviewed_d0_result_sha", "sha256", "required", None),
            ("reviewed_d0_decision_payload_sha", "sha256", "required", None),
            ("reviewed_d1_result_raw_sha256", "sha256", "required", None),
            ("reviewed_d1_result_sha", "sha256", "required", None),
            ("reviewed_d1_decision_payload_sha", "sha256", "required", None),
            ("reviewed_common_commit_sha", "git-sha1", "required", None),
            ("reviewed_route_commit_shas", "tuple[git-sha1;exact=3]", "required", None),
            ("reviewed_corpus_spec_sha", "sha256", "required", None),
            ("reviewed_mutation_universe_sha", "sha256", "required", None),
            ("reviewed_metric_spec_sha", "sha256", "required", None),
            ("reviewed_compare_source_sha256", "sha256", "required", None),
            ("reviewed_executable_source_closure_sha", "sha256", "required", None),
            (
                "observed_executable_source_closure_sha",
                "Optional[sha256]",
                "required-nullable",
                None,
            ),
            ("executable_source_origin_precheck_passed", "bool", "required", None),
            (
                "replay_source_path",
                "Literal[experiments/v3m0_b7_schema_lab/compare.py]",
                "required",
                None,
            ),
            ("replay_source_sha256", "sha256", "required", None),
            ("replay_command_argv", "tuple[str,...]", "required", None),
            (
                "fresh_process_protocol_id",
                "Literal[fresh-python-s-immutable-E-venv-invocation-v2]",
                "required",
                None,
            ),
            ("replay_input_root_sha", "sha256", "required", None),
            (
                "observed_report_reviewer_role",
                "Optional[Literal[CORPUS_REPLAY,METRIC_REPLAY]]",
                "required-nullable",
                None,
            ),
            (
                "observed_report_review_protocol_id",
                "Optional[review-protocol-id]",
                "required-nullable",
                None,
            ),
            (
                "observed_report_lab_evidence_commit_sha",
                "Optional[git-sha1]",
                "required-nullable",
                None,
            ),
            (
                "observed_report_replay_input_root_sha",
                "Optional[sha256]",
                "required-nullable",
                None,
            ),
            ("replay_output_root_sha", "Optional[sha256]", "required-nullable", None),
            ("replay_stdout_sha256", "sha256", "required", None),
            ("replay_stderr_sha256", "sha256", "required", None),
            (
                "replay_termination_kind",
                "Literal[EXITED,SIGNALED,PRECHECK_FAILED,SPAWN_FAILED,OUTPUT_LIMIT_EXCEEDED,TIMED_OUT]",
                "required",
                None,
            ),
            (
                "replay_exit_code",
                "Optional[nonnegative-int]",
                "required-nullable",
                None,
            ),
            (
                "replay_signal_number",
                "Optional[positive-int]",
                "required-nullable",
                None,
            ),
            (
                "replayed_d0_decision_payload_sha",
                "Optional[sha256]",
                "required-nullable",
                None,
            ),
            (
                "replayed_d1_decision_payload_sha",
                "Optional[sha256]",
                "required-nullable",
                None,
            ),
            (
                "observed_surviving_route_ids",
                "Optional[tuple[route-id,...]]",
                "required-nullable",
                None,
            ),
            (
                "observed_provisional_winner_route_id",
                "Optional[route-id]",
                "required-nullable",
                None,
            ),
            ("verdict", "Literal[ACCEPT,REJECT]", "required", None),
            ("reason_codes", "tuple[str,...]", "required", None),
            ("receipt_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabReviewHaltV1",
        "experimental.v3m0.b7.review-halt.v1",
        "review_halt_sha",
        (
            (
                "review_halt_schema_version",
                "Literal[experimental.v3m0.b7.review-halt.v1]",
                "required",
                None,
            ),
            ("lab_evidence_commit_sha", "git-sha1", "required", None),
            ("d0_result_raw_sha256", "sha256", "required", None),
            ("d0_result_sha", "sha256", "required", None),
            ("d0_decision_payload_sha", "sha256", "required", None),
            ("d1_result_raw_sha256", "sha256", "required", None),
            ("d1_result_sha", "sha256", "required", None),
            ("d1_decision_payload_sha", "sha256", "required", None),
            ("common_commit_sha", "git-sha1", "required", None),
            ("common_source_sha256", "sha256", "required", None),
            ("compare_source_sha256", "sha256", "required", None),
            ("corpus_fixture_raw_sha256", "sha256", "required", None),
            ("corpus_spec_sha", "sha256", "required", None),
            ("mutation_universe_sha", "sha256", "required", None),
            ("metric_spec_sha", "sha256", "required", None),
            ("environment_manifest_sha", "sha256", "required", None),
            ("ordered_route_commit_shas", "tuple[git-sha1;exact=3]", "required", None),
            ("ordered_route_source_sha256s", "tuple[sha256;exact=3]", "required", None),
            ("provisional_winner_route_id", "route-id", "required", None),
            (
                "reviewer_receipts",
                "tuple[B7LabReviewerReceiptV1;exact=2]",
                "required",
                "B7LabReviewerReceiptV1",
            ),
            (
                "halt_reason",
                "Literal[HALT_REPLAY_MISMATCH,HALT_REVIEW_DIVERGENCE]",
                "required",
                None,
            ),
            ("production_implementation_allowed", "Literal[false]", "required", None),
            ("review_halt_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7LabSelectionReviewV1",
        "experimental.v3m0.b7.selection-review.v1",
        "selection_review_sha",
        (
            (
                "selection_review_schema_version",
                "Literal[experimental.v3m0.b7.selection-review.v1]",
                "required",
                None,
            ),
            ("lab_evidence_commit_sha", "git-sha1", "required", None),
            ("d0_result_raw_sha256", "sha256", "required", None),
            ("d0_result_sha", "sha256", "required", None),
            ("d0_decision_payload_sha", "sha256", "required", None),
            ("d1_result_raw_sha256", "sha256", "required", None),
            ("d1_result_sha", "sha256", "required", None),
            ("d1_decision_payload_sha", "sha256", "required", None),
            ("common_commit_sha", "git-sha1", "required", None),
            ("common_source_sha256", "sha256", "required", None),
            ("compare_source_sha256", "sha256", "required", None),
            ("corpus_fixture_raw_sha256", "sha256", "required", None),
            ("corpus_spec_sha", "sha256", "required", None),
            ("mutation_universe_sha", "sha256", "required", None),
            ("metric_spec_sha", "sha256", "required", None),
            ("environment_manifest_sha", "sha256", "required", None),
            ("ordered_route_commit_shas", "tuple[git-sha1;exact=3]", "required", None),
            ("ordered_route_source_sha256s", "tuple[sha256;exact=3]", "required", None),
            ("provisional_winner_route_id", "route-id", "required", None),
            (
                "reviewer_receipts",
                "tuple[B7LabReviewerReceiptV1;exact=2]",
                "required",
                "B7LabReviewerReceiptV1",
            ),
            ("review_outcome", "Literal[UNIQUE_SCHEMA_SELECTED]", "required", None),
            ("selected_route_id", "route-id", "required", None),
            ("selected_route_schema_domain", "route-domain", "required", None),
            ("selected_route_commit_sha", "git-sha1", "required", None),
            ("selected_route_source_sha256", "sha256", "required", None),
            (
                "engineering_disposition",
                "Literal[B7_UNIQUE_SCHEMA_SELECTED_FOR_IMPLEMENTATION]",
                "required",
                None,
            ),
            ("production_implementation_allowed", "Literal[true]", "required", None),
            ("selection_review_sha", "sha256", "required", None),
        ),
    ),
    (
        "B7ProductionHandoffReviewV1",
        "experimental.v3m0.b7.production-handoff-review.v1",
        "handoff_sha",
        (
            (
                "handoff_schema_version",
                "Literal[experimental.v3m0.b7.production-handoff-review.v1]",
                "required",
                None,
            ),
            (
                "git_object_verifier_protocol_id",
                "Literal[v3m0-b7-schema-selection-git-object-handoff-v1]",
                "required",
                None,
            ),
            ("git_object_format", "Literal[sha1]", "required", None),
            (
                "lab_evidence_tag",
                "Literal[v3m0-b7-schema-selection-v1]",
                "required",
                None,
            ),
            ("lab_evidence_tag_object_sha", "git-sha1", "required", None),
            ("lab_evidence_commit_sha", "git-sha1", "required", None),
            ("lab_selection_commit_sha", "git-sha1", "required", None),
            (
                "d0_result_path",
                "Literal[data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json]",
                "required",
                None,
            ),
            ("d0_result_raw_sha256", "sha256", "required", None),
            ("d0_result_sha", "sha256", "required", None),
            ("d0_decision_payload_sha", "sha256", "required", None),
            (
                "d1_result_path",
                "Literal[data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json]",
                "required",
                None,
            ),
            ("d1_result_raw_sha256", "sha256", "required", None),
            ("d1_result_sha", "sha256", "required", None),
            ("d1_decision_payload_sha", "sha256", "required", None),
            (
                "selection_review_path",
                "Literal[data/results/experimental/v3m0_b7_schema_lab/selection_review.json]",
                "required",
                None,
            ),
            ("selection_review_raw_sha256", "sha256", "required", None),
            ("selection_review_sha", "sha256", "required", None),
            ("selected_route_id", "route-id", "required", None),
            ("selected_route_schema_domain", "route-domain", "required", None),
            ("selected_route_commit_sha", "git-sha1", "required", None),
            ("selected_route_source_sha256", "sha256", "required", None),
            (
                "ordered_reviewer_receipt_shas",
                "tuple[sha256;exact=2]",
                "required",
                None,
            ),
            ("handoff_sha", "sha256", "required", None),
        ),
    ),
)


def _project_v91_catalog_from_v92_v1(catalog):
    record_name, schema_id, self_hash_field, field_specs = catalog
    if record_name in ("B7LabEnvironmentManifestV2", "B7LabCorpusFixtureV2"):
        return None
    if record_name == "B7LabD0ComparisonV1":
        fields = list(field_specs)
        fields[8] = (
            "environment_manifest",
            "B7LabEnvironmentManifestV1",
            "required",
            "B7LabEnvironmentManifestV1",
        )
        field_specs = tuple(fields)
    elif record_name == "B7LabD1ComparisonV1":
        fields = list(field_specs)
        fields[13] = (
            "environment_manifest",
            "B7LabEnvironmentManifestV1",
            "required",
            "B7LabEnvironmentManifestV1",
        )
        field_specs = tuple(fields)
    elif record_name == "B7LabReviewerReceiptV1":
        fields = list(field_specs)
        fields[26] = (
            "fresh_process_protocol_id",
            "Literal[fresh-python-s-immutable-E-export-canonical-stdout-v1]",
            "required",
            None,
        )
        field_specs = tuple(fields)
    return record_name, schema_id, self_hash_field, field_specs


LAB_EXACT_RECORD_CATALOGS_V1 = tuple(
    projected
    for catalog in LAB_EXACT_RECORD_CATALOGS_V2
    if (projected := _project_v91_catalog_from_v92_v1(catalog)) is not None
)


class B7LabMutationRejected(ValueError):
    """Frozen route-level rejection surface for one invalid lab wire."""


_CASE_CONTRACTS_V1 = (
    (
        0,
        "reference_failure",
        "reference_failure",
        "reference",
        "000000000",
        None,
        None,
        ("reference",),
        ("reference",),
    ),
    (
        1,
        "shell_failure",
        "shell_failure",
        "shell",
        "100000000",
        None,
        None,
        ("reference", "shell"),
        ("reference", "shell"),
    ),
    (
        2,
        "actual_response_values_failure",
        "actual_response_values_failure",
        "actual_response_values",
        "110000000",
        "actual_response_failed",
        None,
        ("reference", "shell", "actual_response_values"),
        ("reference", "shell", "actual_response_values"),
    ),
    (
        3,
        "matched_response_values_failure",
        "matched_response_values_failure",
        "matched_ablated_response_values",
        "111100000",
        None,
        "matched_ablated_response_failed",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
        ),
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
        ),
    ),
    (
        4,
        "actual_bridge_failure",
        "actual_bridge_failure",
        "actual_bridge",
        "111110000",
        "actual_bridge_failed",
        None,
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
        ),
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
        ),
    ),
    (
        5,
        "matched_bridge_failure",
        "matched_bridge_failure",
        "matched_ablated_bridge",
        "111111000",
        None,
        "matched_ablated_bridge_failed",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
    ),
    (
        6,
        "success",
        "success",
        None,
        "111111111",
        None,
        None,
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
    ),
)
_BLAS_THREAD_SETTINGS_V1 = (
    ("OPENBLAS_NUM_THREADS", "1"),
    ("OMP_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("VECLIB_MAXIMUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
)
_MUTATION_CLASSES_V1 = (
    "SINGLE_FIELD_PRESENCE",
    "TERMINAL_TAG",
    "OUTER_BRANCH_FAILURE_SPLICE",
    "DELETE_SUCCESSFUL_PREFIX_BODY",
    "INJECT_POST_FAILURE_BODY",
    "NESTED_BODY_SHA_SPLICE",
    "CANONICAL_ROUNDTRIP",
    "CANONICAL_REPEAT",
    "UPSTREAM_INVALID",
)
_MUTATION_OPERATIONS_V1 = (
    "DELETE",
    "SET_NULL",
    "SET_VALUE",
    "INSERT_BODY",
    "REPLACE_BODY_AND_RESIGN",
    "REENCODE",
    "REPEAT",
    "RAISE_UPSTREAM",
)
_MUTATION_PROBE_KINDS_V1 = (
    "MUTATION_MUST_REJECT",
    "ROUNDTRIP_MUST_EQUAL",
    "REPEAT_MUST_EQUAL",
    "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT",
)
_MUTATION_BOUNDARIES_V1 = (
    "TRANSCRIPT_CONSTRUCTION",
    "ROUTE_VERIFICATION",
    "EQUALITY_CHECK",
    "UPSTREAM_JOIN",
)
_SCHEDULER_STAGE_ORDER_V1 = (
    "reference",
    "shell",
    "actual_response_values",
    "matched_ablated_response_values",
    "actual_bridge",
    "matched_ablated_bridge",
)
_METRIC_CONTRACT_SHA_V1 = (
    "8d87a8284f23ccc47a9a04170fb9ef6c2d986907ad334f1fe972b22af67967f9"
)
_CASE_CONTRACT_SHA_V1 = (
    "94eb8e435d4a1c69885b70b205cd6f5d4930e6249b3fd099988c7ebee15ebfbe"
)
_MUTATION_GENERATION_CONTRACT_SHA_V1 = (
    "93e230851b81547c68d8ccc384a3fc2d3313567e5048c8cd61c77d715b5f1894"
)
_METRIC_ORDER_V1 = (
    "mutation_accept_count",
    "evidence_loss_count",
    "constructible_invalid_presence_count",
    "half_pair_state_count",
    "b8_consumer_assertion_count",
    "b8_consumer_changed_loc",
    "verifier_branch_count",
    "route_record_count",
    "route_hash_layer_count",
    "canonical_wire_bytes",
)
_EVIDENCE_POINTER_ORDER_V1 = (
    "/provenance_fixture",
    "/response_run_spec_fixture",
    "/reference_outcome",
    "/shell_outcome",
    "/actual_branch_attempt",
    "/actual_branch_attempt/response_values",
    "/matched_ablated_branch_attempt",
    "/matched_ablated_branch_attempt/response_values",
    "/actual_branch_attempt/bridge_audit",
    "/matched_ablated_branch_attempt/bridge_audit",
    "/actual_completed_response",
    "/matched_ablated_completed_response",
    "/terminal_tag",
    "/callback_trace",
    "/ordered_leaf_digests",
)
_NESTED_BODY_RULE_PROJECTIONS_V1 = (
    (
        "/provenance_fixture",
        "B7LabProvenanceFixtureV1",
        "provenance_fixture_sha",
        False,
    ),
    (
        "/response_run_spec_fixture",
        "ResponseRunSpecV3-plain-fixture",
        "run_spec_sha",
        False,
    ),
    (
        "/reference_outcome",
        "rulespace_v3.response.EndpointReferenceOutcome",
        "outcome_sha",
        False,
    ),
    (
        "/shell_outcome",
        "rulespace_v3.response.EndpointShellOutcome",
        "outcome_sha",
        True,
    ),
    (
        "/actual_branch_attempt",
        "B7LabBranchAttemptV1",
        "attempt_sha",
        True,
    ),
    (
        "/matched_ablated_branch_attempt",
        "B7LabBranchAttemptV1",
        "attempt_sha",
        True,
    ),
    (
        "/actual_completed_response",
        "rulespace_v3.response.SourceReadoutResponse",
        "response_sha",
        True,
    ),
    (
        "/matched_ablated_completed_response",
        "rulespace_v3.response.SourceReadoutResponse",
        "response_sha",
        True,
    ),
)
_MUTATION_GENERATION_RULES_V1 = (
    "M01_PRESENCE_TOGGLE",
    "M02_TERMINAL_TAG_OTHER_SIX",
    "M03_BRANCH_FAILURE_SPLICE",
    "M04_DELETE_SUCCESSFUL_PREFIX_BODY",
    "M05_INJECT_POST_FAILURE_BODY",
    "M06_NESTED_SHA_SINGLE_POINT",
    "M07_CROSS_CASE_BODY_SPLICE",
    "M08_CANONICAL_ROUNDTRIP",
    "M09_CANONICAL_REPEAT",
    "M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT",
)
_LAB_SEMANTIC_STRING_DOMAINS_V1 = (
    (
        "branch-failure",
        (
            "actual_response_failed",
            "matched_ablated_response_failed",
            "actual_bridge_failed",
            "matched_ablated_bridge_failed",
        ),
    ),
    (
        "case-id",
        (
            "reference_failure",
            "shell_failure",
            "actual_response_values_failure",
            "matched_response_values_failure",
            "actual_bridge_failure",
            "matched_bridge_failure",
            "success",
        ),
    ),
    ("expected-boundary", _MUTATION_BOUNDARIES_V1),
    ("gate-id", ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08")),
    (
        "metric-id",
        (
            "mutation_accept_count",
            "evidence_loss_count",
            "constructible_invalid_presence_count",
            "half_pair_state_count",
            "b8_consumer_assertion_count",
            "b8_consumer_changed_loc",
            "verifier_branch_count",
            "route_record_count",
            "route_hash_layer_count",
            "canonical_wire_bytes",
        ),
    ),
    ("mutation-class", _MUTATION_CLASSES_V1),
    ("mutation-operation", _MUTATION_OPERATIONS_V1),
    ("probe-kind", _MUTATION_PROBE_KINDS_V1),
    (
        "review-protocol-id",
        ("v3m0-b7-corpus-replay-v2", "v3m0-b7-metric-replay-v2"),
    ),
    (
        "route-domain",
        (
            "experimental.v3m0.b7.a-flat",
            "experimental.v3m0.b7.b-progress",
            "experimental.v3m0.b7.c-union",
        ),
    ),
    ("route-id", ("A_FLAT", "B_PROGRESS", "C_UNION")),
    (
        "route-wire-schema-id",
        (
            "experimental.v3m0.b7.a-flat.wire.v1",
            "experimental.v3m0.b7.b-progress.wire.v1",
            "experimental.v3m0.b7.c-union.wire.v1",
        ),
    ),
    (
        "scheduler-stage-id",
        (
            "reference",
            "shell",
            "actual_response_values",
            "matched_ablated_response_values",
            "actual_bridge",
            "matched_ablated_bridge",
        ),
    ),
    (
        "synthetic-graph-component-id",
        (
            "calibration_selection",
            "permit",
            "materialization",
            "actual_transition_outcome",
            "matched_ablated_transition_outcome",
            "actual_metric_authority",
            "matched_ablated_metric_authority",
            "actual_bridge_grid_authority",
            "matched_ablated_bridge_grid_authority",
            "actual_certificate_outcome",
            "matched_ablated_certificate_outcome",
        ),
    ),
    (
        "terminal-tag",
        (
            "reference_failure",
            "shell_failure",
            "actual_response_values_failure",
            "matched_response_values_failure",
            "actual_bridge_failure",
            "matched_bridge_failure",
            "success",
        ),
    ),
    (
        "validator-id",
        (
            "validate_branch_attempt_v1",
            "validate_case_contract_v1",
            "validate_corpus_fixture_v1",
            "validate_d0_comparison_v1",
            "validate_d0_decision_payload_projection_v1",
            "validate_d0_route_result_v1",
            "validate_d1_comparison_v1",
            "validate_d1_decision_payload_projection_v1",
            "validate_d1_route_result_v1",
            "validate_endpoint_reference_outcome_raw_v1",
            "validate_endpoint_shell_outcome_raw_v1",
            "validate_gate_e01_v1",
            "validate_gate_e02_v1",
            "validate_gate_e03_v1",
            "validate_gate_e04_v1",
            "validate_gate_e05_v1",
            "validate_gate_e06_v1",
            "validate_gate_e07_v1",
            "validate_gate_e08_v1",
            "validate_production_handoff_v1",
            "validate_provenance_fixture_v1",
            "validate_response_run_spec_fixture_v1",
            "validate_review_halt_v1",
            "validate_reviewer_child_static_surface_v1",
            "validate_reviewer_executable_source_origin_v1",
            "validate_reviewer_receipt_v1",
            "validate_route_static_surface_v1",
            "validate_selection_review_v1",
            "validate_source_readout_response_raw_v1",
            "validate_synthetic_component_body_v1",
            "validate_synthetic_graph_manifest_v1",
            "validate_synthetic_parent_freeze_v3_body_v1",
        ),
    ),
)
_PRESENCE_POINTER_ORDER_V1 = (
    "/shell_outcome",
    "/actual_branch_attempt",
    "/actual_branch_attempt/response_values",
    "/matched_ablated_branch_attempt",
    "/matched_ablated_branch_attempt/response_values",
    "/actual_branch_attempt/bridge_audit",
    "/matched_ablated_branch_attempt/bridge_audit",
    "/actual_completed_response",
    "/matched_ablated_completed_response",
)
_TERMINAL_TAG_ORDER_V1 = (
    "reference_failure",
    "shell_failure",
    "actual_response_values_failure",
    "matched_response_values_failure",
    "actual_bridge_failure",
    "matched_bridge_failure",
    "success",
)
_SUCCESSFUL_BODY_POINTERS_BY_CASE_V1 = (
    ("reference_failure", ()),
    ("shell_failure", ("/reference_outcome",)),
    (
        "actual_response_values_failure",
        ("/reference_outcome", "/shell_outcome"),
    ),
    (
        "matched_response_values_failure",
        (
            "/reference_outcome",
            "/shell_outcome",
            "/actual_branch_attempt/response_values",
        ),
    ),
    (
        "actual_bridge_failure",
        (
            "/reference_outcome",
            "/shell_outcome",
            "/actual_branch_attempt/response_values",
            "/matched_ablated_branch_attempt/response_values",
        ),
    ),
    (
        "matched_bridge_failure",
        (
            "/reference_outcome",
            "/shell_outcome",
            "/actual_branch_attempt/response_values",
            "/matched_ablated_branch_attempt/response_values",
            "/actual_branch_attempt/bridge_audit",
        ),
    ),
    (
        "success",
        (
            "/reference_outcome",
            "/shell_outcome",
            "/actual_branch_attempt/response_values",
            "/matched_ablated_branch_attempt/response_values",
            "/actual_branch_attempt/bridge_audit",
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
)
_POST_FAILURE_POINTERS_BY_CASE_V1 = (
    (
        "reference_failure",
        (
            "/shell_outcome",
            "/actual_branch_attempt",
            "/actual_branch_attempt/response_values",
            "/matched_ablated_branch_attempt",
            "/matched_ablated_branch_attempt/response_values",
            "/actual_branch_attempt/bridge_audit",
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
    (
        "shell_failure",
        (
            "/actual_branch_attempt",
            "/actual_branch_attempt/response_values",
            "/matched_ablated_branch_attempt",
            "/matched_ablated_branch_attempt/response_values",
            "/actual_branch_attempt/bridge_audit",
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
    (
        "actual_response_values_failure",
        (
            "/actual_branch_attempt/response_values",
            "/matched_ablated_branch_attempt",
            "/matched_ablated_branch_attempt/response_values",
            "/actual_branch_attempt/bridge_audit",
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
    (
        "matched_response_values_failure",
        (
            "/matched_ablated_branch_attempt/response_values",
            "/actual_branch_attempt/bridge_audit",
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
    (
        "actual_bridge_failure",
        (
            "/actual_branch_attempt/bridge_audit",
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
    (
        "matched_bridge_failure",
        (
            "/matched_ablated_branch_attempt/bridge_audit",
            "/actual_completed_response",
            "/matched_ablated_completed_response",
        ),
    ),
    ("success", ()),
)
_CROSS_CASE_BODY_POINTER_ORDER_V1 = (
    "/provenance_fixture",
    "/response_run_spec_fixture",
    "/reference_outcome",
    "/shell_outcome",
    "/actual_branch_attempt",
    "/actual_branch_attempt/response_values",
    "/matched_ablated_branch_attempt",
    "/matched_ablated_branch_attempt/response_values",
    "/actual_branch_attempt/bridge_audit",
    "/matched_ablated_branch_attempt/bridge_audit",
    "/actual_completed_response",
    "/matched_ablated_completed_response",
)
_BRANCH_FAILURE_POINTER_ORDER_V1 = (
    "/actual_branch_attempt/failure",
    "/matched_ablated_branch_attempt/failure",
)
_BRANCH_FAILURE_REPLACEMENT_ORDER_V1 = (
    None,
    "actual_response_failed",
    "matched_ablated_response_failed",
    "actual_bridge_failed",
    "matched_ablated_bridge_failed",
)


def _core_record_schemas_v1():
    schemas = {}
    for (
        record_name,
        _schema_id,
        hash_field,
        field_specs,
    ) in LAB_EXACT_RECORD_CATALOGS_V2:
        schemas[record_name] = [
            hash_field,
            [
                [name, wire_type, nested_record]
                for name, wire_type, _presence, nested_record in field_specs
            ],
        ]
    return schemas


def _require_dotted_identifier_v1(value, field, minimum_parts):
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact str")
    parts = value.split(".")
    if len(parts) < minimum_parts or any(not part.isidentifier() for part in parts):
        raise ValueError(f"{field} must be a normalized dotted identifier")


def _require_absolute_normalized_path_v1(value, field):
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact str")
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or "\x00" in value
    ):
        raise ValueError(f"{field} must be an absolute normalized path")
    parts = value.split("/")[1:]
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"{field} must be an absolute normalized path")


def _require_repo_relative_posix_path_v1(value, field):
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact str")
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        raise ValueError(f"{field} must be a normalized repository-relative path")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"{field} must be a normalized repository-relative path")


def _validate_lab_wire_semantics_v1(value, wire_type, nested_record, field):
    if wire_type.startswith("Optional["):
        if value is None:
            return
        _validate_lab_wire_semantics_v1(
            value,
            wire_type[9:-1],
            nested_record,
            field,
        )
        return
    if wire_type.startswith("tuple["):
        item_expression = _pure_core._split_wire_top_level_v1(
            wire_type[6:-1],
            ";",
        )[0]
        item_types = _pure_core._split_wire_top_level_v1(item_expression, ",")
        if item_types[-1] == "...":
            for index, item in enumerate(value):
                _validate_lab_wire_semantics_v1(
                    item,
                    item_types[0],
                    nested_record,
                    f"{field}[{index}]",
                )
        elif len(item_types) == 1:
            for index, item in enumerate(value):
                _validate_lab_wire_semantics_v1(
                    item,
                    item_types[0],
                    nested_record,
                    f"{field}[{index}]",
                )
        else:
            for index, (item, item_type) in enumerate(zip(value, item_types)):
                _validate_lab_wire_semantics_v1(
                    item,
                    item_type,
                    nested_record,
                    f"{field}[{index}]",
                )
        return
    if nested_record is not None:
        _validate_exact_lab_record_v1(nested_record, value)
        return
    for semantic_wire_type, allowed_values in _LAB_SEMANTIC_STRING_DOMAINS_V1:
        if wire_type == semantic_wire_type:
            if type(value) is not str or value not in allowed_values:
                raise ValueError(f"{field} is outside the frozen {wire_type} domain")
            return
    if wire_type == "absolute-normalized-path":
        _require_absolute_normalized_path_v1(value, field)
        return
    if wire_type == "fully-qualified-type-name":
        _require_dotted_identifier_v1(value, field, 2)
        return
    if wire_type == "json-pointer":
        _require_json_pointer_v1(value, field)
        return
    if wire_type == "module-name":
        _require_dotted_identifier_v1(value, field, 1)
        return
    if wire_type == "repo-relative-posix-path":
        _require_repo_relative_posix_path_v1(value, field)
        return
    if wire_type in (
        "canonical-json-value",
        "canonical-json-object",
        "canonical-json-array",
        "bool",
        "int",
        "nonnegative-int",
        "positive-int",
        "uint64",
        "float",
        "float64",
        "sha256",
        "git-sha1",
        "str",
    ) or wire_type.startswith("Literal["):
        return
    if wire_type in (
        "FrozenComplexTensor-raw-body",
        "SourceReadoutBridgeAudit-raw-body",
    ):
        if type(value) is not dict:
            raise TypeError(f"{field} must be an exact JSON object")
        return
    if wire_type == "binary-string-width-9":
        if (
            type(value) is not str
            or len(value) != 9
            or any(character not in "01" for character in value)
        ):
            raise TypeError(f"{field} must be a nine-bit binary string")
        return
    if wire_type == "binary-string-variable-width-nonempty":
        if (
            type(value) is not str
            or not value
            or any(character not in "01" for character in value)
        ):
            raise TypeError(f"{field} must be a non-empty binary string")
        return
    if type(value) is not str or not value:
        raise TypeError(f"{field} must be a non-empty exact semantic string")


def _validate_exact_lab_record_v1(record_name, raw_body):
    if type(record_name) is not str:
        raise TypeError("lab record name must be an exact str")
    selected = None
    for catalog in LAB_EXACT_RECORD_CATALOGS_V2:
        if catalog[0] == record_name:
            selected = catalog
            break
    if selected is None:
        raise ValueError("lab record name is not frozen")
    if type(raw_body) is not dict:
        raise TypeError(f"{record_name} must be an exact dict")
    fields = tuple(field_spec[0] for field_spec in selected[3])
    if len(raw_body) != len(fields) or any(name not in raw_body for name in fields):
        raise ValueError(f"{record_name} fields drifted")
    for name, wire_type, _presence, nested_record in selected[3]:
        _validate_lab_wire_semantics_v1(
            raw_body[name],
            wire_type,
            nested_record,
            f"{record_name}.{name}",
        )
    validated = _pure_core._validate_record_raw_v1(
        raw_body,
        record_name,
        record_name,
        _core_record_schemas_v1(),
    )
    return _detach_json_v1(validated)


def canonical_json_bytes_v1(value):
    """Expose the unique pure-core canonical JSON algorithm to lab consumers."""
    return _pure_core.canonical_json_bytes_v1(value)


def canonical_sha_v1(value):
    """Expose the unique pure-core canonical SHA algorithm to lab consumers."""
    return _pure_core.canonical_sha_v1(value)


def strict_json_loads_v1(canonical_json_utf8):
    """Expose the unique pure-core strict JSON decoder to lab consumers."""
    return _pure_core.strict_json_loads_v1(canonical_json_utf8)


def validate_exact_lab_record_v1(record_name, raw_body):
    """Validate and detach one registry-frozen lab record by exact name."""
    return _validate_exact_lab_record_v1(record_name, raw_body)


def validate_environment_manifest_v1(raw_body):
    """Validate the owner-neutral environment manifest basic contract."""
    manifest = _validate_exact_lab_record_v1(
        "B7LabEnvironmentManifestV1",
        raw_body,
    )
    settings = manifest["blas_thread_settings"]
    if tuple(tuple(item) for item in settings) != _BLAS_THREAD_SETTINGS_V1:
        raise ValueError("environment BLAS thread settings drifted")
    executable = manifest["python_executable_realpath"]
    if type(executable) is not str or not executable.startswith("/"):
        raise ValueError("environment Python executable path is not absolute")
    if manifest["python_hash_seed"] != "0":
        raise ValueError("environment Python hash seed drifted")
    return manifest


def validate_environment_manifest_v2(
    raw_body,
    *,
    python_identity_observation,
    python_probe_result,
):
    """Join one V2 manifest to independently observed path and probe evidence."""

    manifest = _validate_exact_lab_record_v1(
        "B7LabEnvironmentManifestV2",
        raw_body,
    )
    if manifest["python_invocation_path"] == manifest["python_executable_realpath"]:
        raise ValueError("environment invocation and target roles collapsed")
    if tuple(tuple(item) for item in manifest["blas_thread_settings"]) != (
        _BLAS_THREAD_SETTINGS_V1
    ):
        raise ValueError("environment BLAS thread settings drifted")
    if manifest["python_hash_seed"] != "0":
        raise ValueError("environment Python hash seed drifted")
    if manifest["fresh_process_per_capture"] is not True:
        raise ValueError("environment fresh-process policy drifted")
    expected_environment_sha = canonical_sha_v1(
        {
            field: value
            for field, value in manifest.items()
            if field != "environment_sha"
        }
    )
    if manifest["environment_sha"] != expected_environment_sha:
        raise ValueError("environment self root drifted")

    if (
        type(python_identity_observation) is not dict
        or python_identity_observation.get("precheck_passed") is not True
        or python_identity_observation.get("python_invocation_path")
        != manifest["python_invocation_path"]
        or python_identity_observation.get("recorded_realpath")
        != manifest["python_executable_realpath"]
        or python_identity_observation.get("recorded_raw_sha256")
        != manifest["python_executable_raw_sha256"]
        or python_identity_observation.get("recorded_venv_prefix")
        != manifest["python_venv_prefix"]
        or python_identity_observation.get("recorded_pyvenv_cfg_path")
        != manifest["python_pyvenv_cfg_path"]
        or python_identity_observation.get("recorded_pyvenv_cfg_raw_sha256")
        != manifest["python_pyvenv_cfg_raw_sha256"]
        or python_identity_observation.get("python_invocation_identity_sha")
        != manifest["python_invocation_identity_sha"]
    ):
        raise ValueError("environment Python invocation identity drifted")
    if (
        type(python_probe_result) is not dict
        or python_probe_result.get("probe_passed") is not True
        or type(python_probe_result.get("report")) is not dict
    ):
        raise ValueError("environment import probe failed")
    report = python_probe_result["report"]
    probe_manifest_fields = (
        "python_implementation",
        "python_version",
        "python_invocation_path",
        "python_executable_realpath",
        "python_venv_prefix",
        "numpy_version",
        "scipy_version",
        "platform_system",
        "platform_release",
        "platform_machine",
        "numpy_float64_dtype_str",
        "numpy_float64_itemsize",
        "byteorder",
        "threadpool_info",
    )
    for field in probe_manifest_fields:
        if canonical_json_bytes_v1(report[field]) != canonical_json_bytes_v1(
            manifest[field]
        ):
            raise ValueError(f"environment probe {field} drifted")
    return manifest


def validate_corpus_case_v1(raw_body):
    """Validate one exact frozen corpus case and its self hash."""
    case = _validate_exact_lab_record_v1("B7LabCorpusCaseV1", raw_body)
    observed = (
        case["case_ordinal"],
        case["case_id"],
        case["terminal_tag"],
        case["injected_failure_stage"],
        case["presence_bits"],
        case["actual_attempt_failure"],
        case["matched_ablated_attempt_failure"],
        tuple(case["expected_callback_trace"]),
        tuple(case["expected_leaf_ids"]),
    )
    if observed not in _CASE_CONTRACTS_V1:
        raise ValueError("corpus case contract drifted")
    return case


def _escape_json_pointer_token_v1(token):
    if type(token) is not str:
        raise TypeError("JSON pointer token must be an exact str")
    return token.replace("~", "~0").replace("/", "~1")


def _json_pointer_tokens_v1(pointer):
    if type(pointer) is not str:
        raise TypeError("JSON pointer must be an exact str")
    if pointer == "":
        return ()
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must be absolute")
    tokens = []
    for raw_token in pointer[1:].split("/"):
        decoded = []
        index = 0
        while index < len(raw_token):
            character = raw_token[index]
            if character != "~":
                decoded.append(character)
            else:
                if index + 1 >= len(raw_token):
                    raise ValueError("JSON pointer escape is truncated")
                escaped = raw_token[index + 1]
                if escaped == "0":
                    decoded.append("~")
                elif escaped == "1":
                    decoded.append("/")
                else:
                    raise ValueError("JSON pointer escape is not RFC6901")
                index += 1
            index += 1
        tokens.append("".join(decoded))
    return tuple(tokens)


def resolve_json_pointer_v1(raw_body, pointer):
    """Resolve one strict RFC6901 pointer without JSON-Patch extensions."""
    current = raw_body
    for token in _json_pointer_tokens_v1(pointer):
        if type(current) is dict:
            if token not in current:
                raise ValueError("JSON pointer object member does not resolve")
            current = current[token]
        elif type(current) is list:
            if (
                not token
                or any(character not in "0123456789" for character in token)
                or (len(token) > 1 and token.startswith("0"))
            ):
                raise ValueError("JSON pointer array index is not canonical")
            index = int(token)
            if index >= len(current):
                raise ValueError("JSON pointer array index does not resolve")
            current = current[index]
        else:
            raise ValueError("JSON pointer traverses a non-container")
    return current


def _walk_json_pointer_items_into_v1(value, pointer, items):
    items.append((pointer, value))
    if type(value) is dict:
        encoded_keys = sorted((key.encode("utf-8"), key) for key in value)
        for _encoded, key in encoded_keys:
            child_pointer = f"{pointer}/{_escape_json_pointer_token_v1(key)}"
            _walk_json_pointer_items_into_v1(value[key], child_pointer, items)
    elif type(value) is list:
        for index, item in enumerate(value):
            _walk_json_pointer_items_into_v1(item, f"{pointer}/{index}", items)


def walk_json_pointer_items_v1(raw_body):
    """Return the frozen recursive RFC6901 pointer/value walk."""
    _pure_core.canonical_json_bytes_v1(raw_body)
    items = []
    _walk_json_pointer_items_into_v1(raw_body, "", items)
    return tuple(items)


def discover_record_self_hashes_v1(raw_body):
    """Snapshot exact record object paths and their unique self-hash member."""
    discovered = []
    for pointer, candidate in walk_json_pointer_items_v1(raw_body):
        if type(candidate) is not dict:
            continue
        matches = []
        for _encoded, key in sorted((name.encode("utf-8"), name) for name in candidate):
            observed = candidate[key]
            if (
                not key.endswith(("_sha", "_sha256"))
                or type(observed) is not str
                or len(observed) != 64
                or any(character not in "0123456789abcdef" for character in observed)
            ):
                continue
            payload = {name: value for name, value in candidate.items() if name != key}
            if observed == _pure_core.canonical_sha_v1(payload):
                matches.append(key)
        if len(matches) > 1:
            raise ValueError("record has more than one self-hash member")
        if matches:
            discovered.append((pointer, matches[0]))
    return tuple(discovered)


def _clone_json_preserving_order_v1(value):
    if type(value) is dict:
        return {
            name: _clone_json_preserving_order_v1(item) for name, item in value.items()
        }
    if type(value) is list or type(value) is tuple:
        return [_clone_json_preserving_order_v1(item) for item in value]
    return value


def _detach_json_v1(value):
    _pure_core.canonical_json_bytes_v1(value)
    return _clone_json_preserving_order_v1(value)


def _optional_pointer_value_v1(raw_body, pointer):
    try:
        value = resolve_json_pointer_v1(raw_body, pointer)
    except ValueError:
        return False, None
    return value is not None, value


def _resolved_pointer_value_v1(raw_body, pointer):
    try:
        return True, resolve_json_pointer_v1(raw_body, pointer)
    except ValueError:
        return False, None


def _case_pointer_order_v1(catalog, case_id):
    for catalog_case_id, pointers in catalog:
        if catalog_case_id == case_id:
            return pointers
    raise ValueError("mutation pointer catalog case is not frozen")


def _append_mutation_candidate_v1(
    candidates,
    base_ordinal,
    donor_ordinal,
    rule_id,
    base_case_id,
    probe_kind,
    mutation_class,
    target_json_pointer,
    operation,
    replacement_json,
    expected_boundary,
):
    candidates.append(
        (
            base_ordinal,
            donor_ordinal,
            rule_id,
            base_case_id,
            probe_kind,
            mutation_class,
            target_json_pointer,
            operation,
            _detach_json_v1(replacement_json),
            expected_boundary,
        )
    )


def _mutation_candidate_sort_key_v1(candidate):
    return (
        candidate[0],
        _MUTATION_CLASSES_V1.index(candidate[5]),
        candidate[6].encode("utf-8"),
        _MUTATION_OPERATIONS_V1.index(candidate[7]),
        _pure_core.canonical_json_bytes_v1(candidate[8]),
        candidate[1],
        candidate[2].encode("utf-8"),
    )


def _mutation_candidate_projection_v1(candidate):
    return {
        "base_case_id": candidate[3],
        "probe_kind": candidate[4],
        "mutation_class": candidate[5],
        "target_json_pointer": candidate[6],
        "operation": candidate[7],
        "replacement_json": candidate[8],
        "expected_boundary": candidate[9],
    }


def _finalize_mutation_candidates_v1(candidates):
    ordered_indices = sorted(
        (
            _mutation_candidate_sort_key_v1(candidate),
            candidate_index,
        )
        for candidate_index, candidate in enumerate(candidates)
    )
    deduplicated = []
    seen_projections = set()
    for _sort_key, candidate_index in ordered_indices:
        candidate = candidates[candidate_index]
        projection = _mutation_candidate_projection_v1(candidate)
        projection_bytes = _pure_core.canonical_json_bytes_v1(projection)
        if projection_bytes in seen_projections:
            continue
        seen_projections.add(projection_bytes)
        deduplicated.append((candidate, projection))

    ordered_mutations = []
    mutation_ids = set()
    for ordinal, (candidate, projection) in enumerate(deduplicated):
        case_token = "GLOBAL" if candidate[3] is None else candidate[3]
        projection_prefix = _pure_core.canonical_sha_v1(projection)[:16]
        mutation_id = f"M{ordinal:06d}-{candidate[5]}-{case_token}-{projection_prefix}"
        if mutation_id in mutation_ids:
            raise ValueError("mutation ID collision after deduplication")
        mutation_ids.add(mutation_id)
        mutation = {
            "mutation_schema_version": "experimental.v3m0.b7.mutation.v1",
            "mutation_ordinal": ordinal,
            "mutation_id": mutation_id,
            "base_case_id": candidate[3],
            "probe_kind": candidate[4],
            "mutation_class": candidate[5],
            "target_json_pointer": candidate[6],
            "operation": candidate[7],
            "replacement_json": _detach_json_v1(candidate[8]),
            "expected_boundary": candidate[9],
            "mutation_sha": "",
        }
        mutation["mutation_sha"] = _pure_core.canonical_sha_v1(
            {name: value for name, value in mutation.items() if name != "mutation_sha"}
        )
        ordered_mutations.append(validate_mutation_v1(mutation))
    return ordered_mutations


def generate_ordered_mutations_v1(ordered_transcripts_raw):
    """Generate the frozen exhaustive M01--M10 mutation list."""
    if type(ordered_transcripts_raw) is not list or len(ordered_transcripts_raw) != 7:
        raise TypeError("mutation generator requires an exact seven-transcript list")
    transcripts = []
    for case_ordinal, (raw_body, case_contract) in enumerate(
        zip(ordered_transcripts_raw, _CASE_CONTRACTS_V1)
    ):
        transcript = validate_case_contract_v1(raw_body)
        if (
            transcript["case_id"] != case_contract[1]
            or case_ordinal != case_contract[0]
        ):
            raise ValueError("mutation generator transcript order drifted")
        transcripts.append(transcript)
    self_hash_snapshots = tuple(
        discover_record_self_hashes_v1(transcript) for transcript in transcripts
    )
    if len(self_hash_snapshots) != 7:
        raise ValueError("mutation self-hash snapshot cardinality drifted")

    candidates = []
    success = transcripts[6]
    for base_ordinal, transcript in enumerate(transcripts):
        base_case_id = transcript["case_id"]
        for pointer in _PRESENCE_POINTER_ORDER_V1:
            present, _current = _optional_pointer_value_v1(transcript, pointer)
            if present:
                operation = "SET_NULL"
                replacement = None
            else:
                operation = "INSERT_BODY"
                replacement = resolve_json_pointer_v1(success, pointer)
            _append_mutation_candidate_v1(
                candidates,
                base_ordinal,
                7,
                "M01_PRESENCE_TOGGLE",
                base_case_id,
                "MUTATION_MUST_REJECT",
                "SINGLE_FIELD_PRESENCE",
                pointer,
                operation,
                replacement,
                "ROUTE_VERIFICATION",
            )

        for terminal_tag in _TERMINAL_TAG_ORDER_V1:
            if terminal_tag == transcript["terminal_tag"]:
                continue
            _append_mutation_candidate_v1(
                candidates,
                base_ordinal,
                7,
                "M02_TERMINAL_TAG_OTHER_SIX",
                base_case_id,
                "MUTATION_MUST_REJECT",
                "TERMINAL_TAG",
                "/terminal_tag",
                "SET_VALUE",
                terminal_tag,
                "ROUTE_VERIFICATION",
            )

        for pointer in _BRANCH_FAILURE_POINTER_ORDER_V1:
            resolved, current = _resolved_pointer_value_v1(transcript, pointer)
            if not resolved:
                continue
            for replacement in _BRANCH_FAILURE_REPLACEMENT_ORDER_V1:
                if type(replacement) is type(current) and replacement == current:
                    continue
                _append_mutation_candidate_v1(
                    candidates,
                    base_ordinal,
                    7,
                    "M03_BRANCH_FAILURE_SPLICE",
                    base_case_id,
                    "MUTATION_MUST_REJECT",
                    "OUTER_BRANCH_FAILURE_SPLICE",
                    pointer,
                    "SET_VALUE",
                    replacement,
                    "ROUTE_VERIFICATION",
                )

        for pointer in _case_pointer_order_v1(
            _SUCCESSFUL_BODY_POINTERS_BY_CASE_V1,
            base_case_id,
        ):
            _append_mutation_candidate_v1(
                candidates,
                base_ordinal,
                7,
                "M04_DELETE_SUCCESSFUL_PREFIX_BODY",
                base_case_id,
                "MUTATION_MUST_REJECT",
                "DELETE_SUCCESSFUL_PREFIX_BODY",
                pointer,
                "DELETE",
                None,
                "ROUTE_VERIFICATION",
            )

        for pointer in _case_pointer_order_v1(
            _POST_FAILURE_POINTERS_BY_CASE_V1,
            base_case_id,
        ):
            _append_mutation_candidate_v1(
                candidates,
                base_ordinal,
                7,
                "M05_INJECT_POST_FAILURE_BODY",
                base_case_id,
                "MUTATION_MUST_REJECT",
                "INJECT_POST_FAILURE_BODY",
                pointer,
                "INSERT_BODY",
                resolve_json_pointer_v1(success, pointer),
                "ROUTE_VERIFICATION",
            )

        for pointer, value in walk_json_pointer_items_v1(transcript):
            if pointer == "" or pointer == "/experimental_sha":
                continue
            tokens = _json_pointer_tokens_v1(pointer)
            member_name = tokens[-1]
            if (
                not member_name.endswith(("_sha", "_sha256"))
                or type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                continue
            replacement = "f" * 64 if value == "0" * 64 else "0" * 64
            _append_mutation_candidate_v1(
                candidates,
                base_ordinal,
                7,
                "M06_NESTED_SHA_SINGLE_POINT",
                base_case_id,
                "MUTATION_MUST_REJECT",
                "NESTED_BODY_SHA_SPLICE",
                pointer,
                "SET_VALUE",
                replacement,
                "ROUTE_VERIFICATION",
            )

        for pointer in _CROSS_CASE_BODY_POINTER_ORDER_V1:
            base_present, base_body = _optional_pointer_value_v1(transcript, pointer)
            if not base_present:
                continue
            base_bytes = _pure_core.canonical_json_bytes_v1(base_body)
            for donor_ordinal, donor in enumerate(transcripts):
                if donor_ordinal == base_ordinal:
                    continue
                donor_present, donor_body = _optional_pointer_value_v1(donor, pointer)
                if not donor_present:
                    continue
                if _pure_core.canonical_json_bytes_v1(donor_body) == base_bytes:
                    continue
                _append_mutation_candidate_v1(
                    candidates,
                    base_ordinal,
                    donor_ordinal,
                    "M07_CROSS_CASE_BODY_SPLICE",
                    base_case_id,
                    "MUTATION_MUST_REJECT",
                    "NESTED_BODY_SHA_SPLICE",
                    pointer,
                    "REPLACE_BODY_AND_RESIGN",
                    donor_body,
                    "ROUTE_VERIFICATION",
                )

        _append_mutation_candidate_v1(
            candidates,
            base_ordinal,
            7,
            "M08_CANONICAL_ROUNDTRIP",
            base_case_id,
            "ROUNDTRIP_MUST_EQUAL",
            "CANONICAL_ROUNDTRIP",
            "",
            "REENCODE",
            None,
            "EQUALITY_CHECK",
        )
        _append_mutation_candidate_v1(
            candidates,
            base_ordinal,
            7,
            "M09_CANONICAL_REPEAT",
            base_case_id,
            "REPEAT_MUST_EQUAL",
            "CANONICAL_REPEAT",
            "",
            "REPEAT",
            None,
            "EQUALITY_CHECK",
        )

    _append_mutation_candidate_v1(
        candidates,
        7,
        7,
        "M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT",
        None,
        "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT",
        "UPSTREAM_INVALID",
        "",
        "RAISE_UPSTREAM",
        None,
        "UPSTREAM_JOIN",
    )
    return _finalize_mutation_candidates_v1(candidates)


def _pointer_parent_member_v1(raw_body, pointer):
    tokens = _json_pointer_tokens_v1(pointer)
    if not tokens:
        raise ValueError("mutation target may not replace the transcript root")
    parent_pointer = (
        ""
        if len(tokens) == 1
        else "/"
        + "/".join(_escape_json_pointer_token_v1(token) for token in tokens[:-1])
    )
    parent = resolve_json_pointer_v1(raw_body, parent_pointer)
    if type(parent) is not dict:
        raise ValueError("mutation target parent must be an exact object")
    member = tokens[-1]
    if member not in parent:
        raise ValueError("mutation target member does not exist")
    return parent, member


def _materialize_success_ancestor_v1(mutated, success, target_pointer):
    ancestor_pointer = None
    for candidate in (
        "/actual_branch_attempt",
        "/matched_ablated_branch_attempt",
    ):
        if target_pointer.startswith(f"{candidate}/"):
            ancestor_pointer = candidate
            break
    if ancestor_pointer is None:
        raise ValueError("mutation target has no declared materializable ancestor")
    ancestor_parent, ancestor_member = _pointer_parent_member_v1(
        mutated,
        ancestor_pointer,
    )
    if ancestor_parent[ancestor_member] is not None:
        raise ValueError("mutation ancestor is not absent")
    materialized = _detach_json_v1(resolve_json_pointer_v1(success, ancestor_pointer))
    if type(materialized) is not dict:
        raise ValueError("success mutation ancestor is not an exact object")
    materialized["response_values"] = None
    materialized["bridge_audit"] = None
    materialized["failure"] = None
    ancestor_parent[ancestor_member] = materialized


def _record_hash_pointer_v1(record_pointer, hash_field):
    escaped = _escape_json_pointer_token_v1(hash_field)
    return f"{record_pointer}/{escaped}" if record_pointer else f"/{escaped}"


def _resign_from_snapshots_v1(mutated, target_pointer, snapshots):
    containing = []
    seen_record_paths = set()
    for record_pointer, hash_field in snapshots:
        if record_pointer in seen_record_paths:
            continue
        seen_record_paths.add(record_pointer)
        strictly_contains = record_pointer == "" or target_pointer.startswith(
            f"{record_pointer}/"
        )
        if not strictly_contains or record_pointer == target_pointer:
            continue
        if _record_hash_pointer_v1(record_pointer, hash_field) == target_pointer:
            continue
        containing.append(
            (
                -len(_json_pointer_tokens_v1(record_pointer)),
                record_pointer.encode("utf-8"),
                record_pointer,
                hash_field,
            )
        )
    for _negative_depth, _encoded_path, record_pointer, hash_field in sorted(
        containing
    ):
        record = resolve_json_pointer_v1(mutated, record_pointer)
        if type(record) is not dict or hash_field not in record:
            raise ValueError("frozen self-hash snapshot no longer resolves")
        record[hash_field] = _pure_core.canonical_sha_v1(
            {name: value for name, value in record.items() if name != hash_field}
        )


def _apply_validated_transcript_mutation_v1(
    base,
    mutation,
    success,
    effective_self_hash_snapshot,
):
    """Materialize from a strictly validated corpus-local mutation context."""
    if (
        type(base) is not dict
        or type(mutation) is not dict
        or type(success) is not dict
    ):
        raise TypeError("validated mutation context bodies must be exact dicts")
    if success["case_id"] != "success":
        raise ValueError("mutation materializer success donor drifted")
    if mutation["base_case_id"] != base["case_id"]:
        raise ValueError("mutation materializer base case drifted")
    if type(effective_self_hash_snapshot) is not tuple:
        raise TypeError("effective self-hash snapshot must be an exact tuple")
    operation = mutation["operation"]
    if operation in ("REENCODE", "REPEAT", "RAISE_UPSTREAM"):
        raise ValueError("global probe operation has no materialized transcript")

    mutated = _clone_json_preserving_order_v1(base)
    target_pointer = mutation["target_json_pointer"]
    replacement = _clone_json_preserving_order_v1(mutation["replacement_json"])
    if operation == "INSERT_BODY":
        try:
            parent, member = _pointer_parent_member_v1(mutated, target_pointer)
        except ValueError:
            _materialize_success_ancestor_v1(mutated, success, target_pointer)
            parent, member = _pointer_parent_member_v1(mutated, target_pointer)
        if parent[member] is not None:
            raise ValueError("INSERT_BODY target is not null")
        parent[member] = replacement
    else:
        parent, member = _pointer_parent_member_v1(mutated, target_pointer)
        if operation == "DELETE":
            parent.pop(member)
        elif operation == "SET_NULL":
            parent[member] = None
        elif operation in ("SET_VALUE", "REPLACE_BODY_AND_RESIGN"):
            parent[member] = replacement
        else:
            raise ValueError("mutation materializer operation is not frozen")

    _resign_from_snapshots_v1(
        mutated,
        target_pointer,
        effective_self_hash_snapshot,
    )
    return mutated


def apply_transcript_mutation_v1(
    base_transcript_raw,
    mutation_raw,
    success_transcript_raw,
    self_hash_snapshot,
):
    """Materialize one transcript mutation using pre-mutation hash snapshots."""
    base = validate_case_contract_v1(base_transcript_raw)
    success = validate_case_contract_v1(success_transcript_raw)
    mutation = validate_mutation_v1(mutation_raw)
    if success["case_id"] != "success":
        raise ValueError("mutation materializer success donor drifted")
    if mutation["base_case_id"] != base["case_id"]:
        raise ValueError("mutation materializer base case drifted")
    if type(self_hash_snapshot) is not tuple:
        raise TypeError("self-hash snapshot must be an exact tuple")
    base_snapshot = discover_record_self_hashes_v1(base)
    if self_hash_snapshot != base_snapshot:
        raise ValueError("self-hash snapshot differs from the immutable base")
    success_snapshot = discover_record_self_hashes_v1(success)
    effective_snapshot = base_snapshot + tuple(
        item for item in success_snapshot if item not in base_snapshot
    )
    mutated = _apply_validated_transcript_mutation_v1(
        base,
        mutation,
        success,
        effective_snapshot,
    )
    _pure_core.canonical_json_bytes_v1(mutated)
    return mutated


def _require_json_pointer_v1(value, field):
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact str")
    _json_pointer_tokens_v1(value)


def validate_nested_body_rule_v1(raw_body):
    """Validate one normalized nested-body traversal rule."""
    rule = _validate_exact_lab_record_v1("B7LabNestedBodyRuleV1", raw_body)
    if rule["json_pointer"] == "":
        raise ValueError("nested body rule pointer must be rooted and nonempty")
    _require_json_pointer_v1(rule["json_pointer"], "nested body rule pointer")
    return rule


def validate_mutation_v1(raw_body):
    """Validate one mutation-universe row basic contract."""
    mutation = _validate_exact_lab_record_v1("B7LabMutationV1", raw_body)
    if mutation["probe_kind"] not in _MUTATION_PROBE_KINDS_V1:
        raise ValueError("mutation probe kind drifted")
    if mutation["mutation_class"] not in _MUTATION_CLASSES_V1:
        raise ValueError("mutation class drifted")
    if mutation["operation"] not in _MUTATION_OPERATIONS_V1:
        raise ValueError("mutation operation drifted")
    if mutation["expected_boundary"] not in _MUTATION_BOUNDARIES_V1:
        raise ValueError("mutation expected boundary drifted")
    global_operations = ("REENCODE", "REPEAT", "RAISE_UPSTREAM")
    if mutation["operation"] in global_operations:
        if mutation["target_json_pointer"] != "":
            raise ValueError("global mutation operation pointer must be empty")
    else:
        if mutation["target_json_pointer"] == "":
            raise ValueError("local mutation operation pointer must be nonempty")
        _require_json_pointer_v1(
            mutation["target_json_pointer"],
            "mutation target pointer",
        )
    projection = {
        name: mutation[name]
        for name in (
            "base_case_id",
            "probe_kind",
            "mutation_class",
            "target_json_pointer",
            "operation",
            "replacement_json",
            "expected_boundary",
        )
    }
    case_token = (
        "GLOBAL" if mutation["base_case_id"] is None else mutation["base_case_id"]
    )
    expected_id = (
        f"M{mutation['mutation_ordinal']:06d}-{mutation['mutation_class']}-"
        f"{case_token}-{_pure_core.canonical_sha_v1(projection)[:16]}"
    )
    if mutation["mutation_id"] != expected_id:
        raise ValueError("mutation ID projection prefix drifted")
    return mutation


def validate_metric_vector_v1(raw_body):
    """Validate one ten-coordinate metric vector and its self hash."""
    return _validate_exact_lab_record_v1("B7LabMetricVectorV1", raw_body)


def _require_sha256_root_v1(value, field):
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TypeError(f"{field} must be an exact lowercase SHA-256")
    return value


def _raw_source_sha256_v1(source_bytes, field):
    if type(source_bytes) is not bytes:
        raise TypeError(f"{field} source must be exact bytes")
    return _pure_core.hashlib.sha256(source_bytes).hexdigest()


def validate_metric_spec_v1(
    raw_body,
    common_source_bytes,
    compare_source_bytes,
):
    """Validate the metric spec against frozen registry and source bytes."""
    metric = _validate_exact_lab_record_v1("B7LabMetricSpecV1", raw_body)
    expected_fields = (
        ("metric_algorithm_id", "v3m0-b7-schema-metrics-v1"),
        ("metric_contract_sha", _METRIC_CONTRACT_SHA_V1),
        ("metric_order", _METRIC_ORDER_V1),
        ("evidence_pointer_order", _EVIDENCE_POINTER_ORDER_V1),
        ("invalid_presence_bit_width", 9),
        (
            "reachable_closure_algorithm_id",
            "python-ast-route-local-reachable-closure-v1",
        ),
        ("branch_count_algorithm_id", "python-ast-branch-contribution-v1"),
        ("b8_diff_algorithm_id", "python-difflib-unified-n0-v1"),
    )
    for field, expected in expected_fields:
        observed = metric[field]
        if type(expected) is tuple:
            observed = tuple(observed)
        if observed != expected:
            raise ValueError(f"metric spec {field} drifted")
    if metric["common_source_sha256"] != _raw_source_sha256_v1(
        common_source_bytes,
        "common",
    ):
        raise ValueError("metric spec common source SHA drifted")
    if metric["compare_source_sha256"] != _raw_source_sha256_v1(
        compare_source_bytes,
        "compare",
    ):
        raise ValueError("metric spec compare source SHA drifted")
    return metric


def _case_contract_projection_v1(case):
    return (
        case["case_ordinal"],
        case["case_id"],
        case["terminal_tag"],
        case["injected_failure_stage"],
        case["presence_bits"],
        case["actual_attempt_failure"],
        case["matched_ablated_attempt_failure"],
        tuple(case["expected_callback_trace"]),
        tuple(case["expected_leaf_ids"]),
    )


def validate_corpus_spec_v1(raw_body, metric_spec_sha):
    """Validate the corpus spec against every frozen registry join."""
    expected_metric_root = _require_sha256_root_v1(
        metric_spec_sha,
        "metric spec root",
    )
    corpus = _validate_exact_lab_record_v1("B7LabCorpusSpecV1", raw_body)
    expected_fields = (
        (
            "transcript_schema_version",
            "experimental.v3m0.b7.normalized-transcript.v1",
        ),
        ("canonical_json_profile_id", "canonical-json-sha256-v1"),
        ("scheduler_stage_order", _SCHEDULER_STAGE_ORDER_V1),
        ("presence_pointer_order", _PRESENCE_POINTER_ORDER_V1),
        ("terminal_tag_order", _TERMINAL_TAG_ORDER_V1),
        ("case_contract_sha", _CASE_CONTRACT_SHA_V1),
        ("mutation_algorithm_id", "v3m0-b7-exhaustive-mutation-v1"),
        ("mutation_class_order", _MUTATION_CLASSES_V1),
        ("mutation_operation_order", _MUTATION_OPERATIONS_V1),
        (
            "mutation_generation_contract_sha",
            _MUTATION_GENERATION_CONTRACT_SHA_V1,
        ),
        ("mutation_generation_rules", _MUTATION_GENERATION_RULES_V1),
        (
            "upstream_invalid_probe_rule",
            "M10_UPSTREAM_INVALID_ZERO_TRANSCRIPT",
        ),
        ("metric_spec_sha", expected_metric_root),
    )
    for field, expected in expected_fields:
        observed = corpus[field]
        if type(expected) is tuple:
            observed = tuple(observed)
        if observed != expected:
            raise ValueError(f"corpus spec {field} drifted")

    observed_cases = []
    for raw_case in corpus["ordered_case_specs"]:
        case = validate_corpus_case_v1(raw_case)
        observed_cases.append(_case_contract_projection_v1(case))
    if tuple(observed_cases) != _CASE_CONTRACTS_V1:
        raise ValueError("corpus spec ordered case contracts drifted")

    observed_rules = []
    for raw_rule in corpus["nested_body_rules"]:
        rule = validate_nested_body_rule_v1(raw_rule)
        if rule["full_body_required"] is not True:
            raise ValueError("corpus nested body rule is not full-body")
        observed_rules.append(
            (
                rule["json_pointer"],
                rule["body_kind"],
                rule["hash_field"],
                rule["nullable"],
            )
        )
    if tuple(observed_rules) != _NESTED_BODY_RULE_PROJECTIONS_V1:
        raise ValueError("corpus spec nested body registry drifted")
    return corpus


def validate_mutation_universe_v1(
    raw_body,
    ordered_transcripts_raw,
    corpus_spec_sha,
    mutation_generation_contract_sha,
    generator_source_bytes,
):
    """Validate the exact derived universe against the frozen generator."""
    expected_corpus_root = _require_sha256_root_v1(
        corpus_spec_sha,
        "corpus spec root",
    )
    expected_generation_root = _require_sha256_root_v1(
        mutation_generation_contract_sha,
        "mutation generation contract root",
    )
    if expected_generation_root != _MUTATION_GENERATION_CONTRACT_SHA_V1:
        raise ValueError("mutation generation contract root drifted")
    universe = _validate_exact_lab_record_v1(
        "B7LabMutationUniverseV1",
        raw_body,
    )
    if universe["corpus_spec_sha"] != expected_corpus_root:
        raise ValueError("mutation universe corpus root drifted")
    if universe["mutation_generation_contract_sha"] != expected_generation_root:
        raise ValueError("mutation universe generation root drifted")
    if universe["generator_source_sha256"] != _raw_source_sha256_v1(
        generator_source_bytes,
        "mutation generator",
    ):
        raise ValueError("mutation universe generator source SHA drifted")

    observed_mutations = [
        validate_mutation_v1(mutation) for mutation in universe["ordered_mutations"]
    ]
    expected_mutations = generate_ordered_mutations_v1(ordered_transcripts_raw)
    expected_count = len(expected_mutations)
    if (
        universe["mutation_count"] != expected_count
        or len(observed_mutations) != expected_count
        or observed_mutations != expected_mutations
    ):
        raise ValueError("mutation universe differs from frozen generation")
    if tuple(mutation["mutation_ordinal"] for mutation in observed_mutations) != tuple(
        range(expected_count)
    ):
        raise ValueError("mutation universe ordinals are not contiguous")
    mutation_ids = tuple(mutation["mutation_id"] for mutation in observed_mutations)
    mutation_shas = tuple(mutation["mutation_sha"] for mutation in observed_mutations)
    if (
        len(set(mutation_ids)) != expected_count
        or len(set(mutation_shas)) != expected_count
    ):
        raise ValueError("mutation universe IDs or SHAs are not unique")
    return universe


def _presence_bit_v1(value):
    return "1" if value is not None else "0"


def validate_case_contract_v1(raw_body):
    """Validate one transcript against the frozen seven-case state table."""
    transcript = _validate_exact_lab_record_v1(
        "NormalizedB7ExecutionTranscriptV1",
        raw_body,
    )
    selected = None
    for case_contract in _CASE_CONTRACTS_V1:
        if case_contract[1] == transcript["case_id"]:
            selected = case_contract
            break
    if selected is None:
        raise ValueError("transcript case ID is not frozen")
    (
        _case_ordinal,
        _case_id,
        terminal_tag,
        _injected_failure_stage,
        expected_presence_bits,
        actual_failure,
        matched_failure,
        expected_trace,
        expected_leaf_ids,
    ) = selected
    if transcript["terminal_tag"] != terminal_tag:
        raise ValueError("transcript terminal tag differs from its case")

    actual = transcript["actual_branch_attempt"]
    matched = transcript["matched_ablated_branch_attempt"]
    if actual is not None:
        if actual["branch"] != "actual" or actual["failure"] != actual_failure:
            raise ValueError("actual branch attempt differs from its case")
    if matched is not None:
        if (
            matched["branch"] != "matched_ablated"
            or matched["failure"] != matched_failure
        ):
            raise ValueError("matched branch attempt differs from its case")
    observed_presence_bits = "".join(
        (
            _presence_bit_v1(transcript["shell_outcome"]),
            _presence_bit_v1(actual),
            _presence_bit_v1(None if actual is None else actual["response_values"]),
            _presence_bit_v1(matched),
            _presence_bit_v1(None if matched is None else matched["response_values"]),
            _presence_bit_v1(None if actual is None else actual["bridge_audit"]),
            _presence_bit_v1(None if matched is None else matched["bridge_audit"]),
            _presence_bit_v1(transcript["actual_completed_response"]),
            _presence_bit_v1(transcript["matched_ablated_completed_response"]),
        )
    )
    if observed_presence_bits != expected_presence_bits:
        raise ValueError("transcript presence bits differ from its case")

    trace = tuple(transcript["callback_trace"])
    if trace != expected_trace:
        raise ValueError("transcript callback trace is not the frozen prefix")
    leaves = transcript["ordered_leaf_digests"]
    leaf_ids = tuple(leaf["leaf_id"] for leaf in leaves)
    if leaf_ids != expected_leaf_ids or len(leaves) != len(expected_trace):
        raise ValueError("transcript leaf IDs are not the frozen prefix")
    for ordinal, leaf in enumerate(leaves):
        if leaf["call_ordinal"] != ordinal or leaf["leaf_id"] != trace[ordinal]:
            raise ValueError("transcript leaf ordinal or callback join drifted")
    return transcript


def _rehash_record_field_v1(raw_body, hash_field):
    raw_body[hash_field] = canonical_sha_v1(
        {name: value for name, value in raw_body.items() if name != hash_field}
    )


def _copy_presence_pointer_v1(success, pointer, presence_bit):
    if presence_bit == "0":
        return None
    if presence_bit != "1":
        raise ValueError("presence bit must be zero or one")
    return _detach_json_v1(resolve_json_pointer_v1(success, pointer))


def _build_presence_attempt_v1(
    success,
    field,
    parent_bit,
    response_values,
    bridge_audit,
):
    if parent_bit == "0":
        return None
    if parent_bit != "1":
        raise ValueError("presence bit must be zero or one")
    attempt = _detach_json_v1(success[field])
    attempt["response_values"] = response_values
    attempt["bridge_audit"] = bridge_audit
    return attempt


def _attempt_governed_members_changed_v1(candidate_attempt, success_attempt):
    return any(
        candidate_attempt[field] != success_attempt[field]
        for field in ("response_values", "bridge_audit", "failure")
    )


def iter_constructible_invalid_presence_candidates_v1(success_transcript_raw):
    """Yield the exact 1,393 constructible non-case states without retaining them."""

    success = validate_case_contract_v1(success_transcript_raw)
    if success["case_id"] != "success":
        raise ValueError("invalid-presence generation requires the success case")
    legal_pairs = {(row[2], row[4]) for row in _CASE_CONTRACTS_V1}
    candidate_count = 0
    for bit_integer in range(512):
        bits = f"{bit_integer:09b}"
        if not (
            bits[2] <= bits[1]
            and bits[5] <= bits[1]
            and bits[4] <= bits[3]
            and bits[6] <= bits[3]
        ):
            continue
        for terminal_tag in _TERMINAL_TAG_ORDER_V1:
            if (terminal_tag, bits) in legal_pairs:
                continue
            transcript = _detach_json_v1(success)
            actual_response_values = _copy_presence_pointer_v1(
                success,
                "/actual_branch_attempt/response_values",
                bits[2],
            )
            actual_bridge_audit = _copy_presence_pointer_v1(
                success,
                "/actual_branch_attempt/bridge_audit",
                bits[5],
            )
            matched_response_values = _copy_presence_pointer_v1(
                success,
                "/matched_ablated_branch_attempt/response_values",
                bits[4],
            )
            matched_bridge_audit = _copy_presence_pointer_v1(
                success,
                "/matched_ablated_branch_attempt/bridge_audit",
                bits[6],
            )
            transcript["shell_outcome"] = _copy_presence_pointer_v1(
                success,
                "/shell_outcome",
                bits[0],
            )
            transcript["actual_branch_attempt"] = _build_presence_attempt_v1(
                success,
                "actual_branch_attempt",
                bits[1],
                actual_response_values,
                actual_bridge_audit,
            )
            transcript["matched_ablated_branch_attempt"] = _build_presence_attempt_v1(
                success,
                "matched_ablated_branch_attempt",
                bits[3],
                matched_response_values,
                matched_bridge_audit,
            )
            transcript["actual_completed_response"] = _copy_presence_pointer_v1(
                success,
                "/actual_completed_response",
                bits[7],
            )
            transcript["matched_ablated_completed_response"] = (
                _copy_presence_pointer_v1(
                    success,
                    "/matched_ablated_completed_response",
                    bits[8],
                )
            )
            transcript["terminal_tag"] = terminal_tag
            for attempt_field in (
                "actual_branch_attempt",
                "matched_ablated_branch_attempt",
            ):
                attempt = transcript[attempt_field]
                if attempt is not None and _attempt_governed_members_changed_v1(
                    attempt,
                    success[attempt_field],
                ):
                    _rehash_record_field_v1(attempt, "attempt_sha")
            _rehash_record_field_v1(transcript, "experimental_sha")
            candidate_count += 1
            yield {
                "terminal_tag": terminal_tag,
                "bit_integer": bit_integer,
                "presence_bits": bits,
                "half_pair": (bits[5] != bits[6] or bits[7] != bits[8]),
                "transcript": transcript,
            }
    if candidate_count != 1393:
        raise AssertionError("invalid-presence domain cardinality drifted")


def generate_constructible_invalid_presence_candidates_v1(success_transcript_raw):
    """Materialize the compatibility list for callers that require eager JSON."""

    return list(
        iter_constructible_invalid_presence_candidates_v1(success_transcript_raw)
    )


_D0_COMPARISON_FIELDS = (
    "d0_result_schema_version",
    "common_commit_sha",
    "common_source_sha256",
    "compare_source_sha256",
    "corpus_fixture_raw_sha256",
    "corpus_spec_sha",
    "mutation_universe_sha",
    "metric_spec_sha",
    "environment_manifest",
    "ordered_route_results",
    "surviving_route_ids",
    "decision_payload_sha",
    "auxiliary_benchmark",
    "d0_result_sha",
)
_D0_DECISION_FIELDS = _D0_COMPARISON_FIELDS[:11]
_D1_COMPARISON_FIELDS = (
    "d1_result_schema_version",
    "d0_result_raw_sha256",
    "d0_result_sha",
    "d0_decision_payload_sha",
    "common_commit_sha",
    "common_source_sha256",
    "compare_source_sha256",
    "leaf_provider_source_sha256",
    "corpus_fixture_raw_sha256",
    "corpus_spec_sha",
    "mutation_universe_sha",
    "metric_spec_sha",
    "synthetic_graph_manifest",
    "environment_manifest",
    "ordered_capture_transcript_set_shas",
    "ordered_capture_leaf_digest_set_shas",
    "ordered_route_results",
    "surviving_route_ids",
    "minimum_metric_vector",
    "provisional_winner_route_id",
    "tie_detected",
    "decision_payload_sha",
    "auxiliary_benchmark",
    "d1_result_sha",
)
_D1_DECISION_FIELDS = (
    _D1_COMPARISON_FIELDS[0],
    *_D1_COMPARISON_FIELDS[3:21],
)

B8_CONSUMER_SKELETON_UTF8 = (
    b"import json\n"
    b"from __ROUTE_MODULE__ import verify_and_decode_route_wire\n"
    b"from experiments.v3m0_b7_schema_lab.common import "
    b"_b8_require_absent, _b8_require_exact, _b8_require_present\n"
    b"\n"
    b'ROUTE_ID = "__ROUTE_ID__"\n'
    b'WIRE_SCHEMA_ID = "__WIRE_SCHEMA_ID__"\n'
    b"\n"
    b"def consume_b7_paired_response(canonical_route_wire_utf8):\n"
    b"    decoded = verify_and_decode_route_wire(canonical_route_wire_utf8)\n"
    b'    transcript = json.loads(decoded.decode("utf-8"))\n'
    b'    _b8_require_exact(transcript.get("transcript_schema_version"), '
    b'"experimental.v3m0.b7.normalized-transcript.v1", '
    b'"transcript_schema_version")\n'
    b'    _b8_require_exact(transcript.get("terminal_tag"), "success", '
    b'"terminal_tag")\n'
    b'    _b8_require_present(transcript.get("actual_branch_attempt"), '
    b'"actual_branch_attempt")\n'
    b'    _b8_require_present(transcript.get("matched_ablated_branch_attempt"), '
    b'"matched_ablated_branch_attempt")\n'
    b'    _b8_require_absent(transcript["actual_branch_attempt"].get("failure"), '
    b'"actual_failure")\n'
    b"    _b8_require_absent("
    b'transcript["matched_ablated_branch_attempt"].get("failure"), '
    b'"matched_failure")\n'
    b'    _b8_require_present(transcript.get("actual_completed_response"), '
    b'"actual_completed_response")\n'
    b"    _b8_require_present("
    b'transcript.get("matched_ablated_completed_response"), '
    b'"matched_ablated_completed_response")\n'
    b'    return (transcript["actual_completed_response"], '
    b'transcript["matched_ablated_completed_response"])\n'
)

_ROUTE_RENDER_TRIPLES = (
    (
        "A_FLAT",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experimental.v3m0.b7.a-flat.wire.v1",
    ),
    (
        "B_PROGRESS",
        "experiments.v3m0_b7_schema_lab.b_progress",
        "experimental.v3m0.b7.b-progress.wire.v1",
    ),
    (
        "C_UNION",
        "experiments.v3m0_b7_schema_lab.c_union",
        "experimental.v3m0.b7.c-union.wire.v1",
    ),
)


def _b8_require_exact(observed, expected, field):
    if type(field) is not str:
        raise TypeError("B8 exact field label must be an exact str")
    if observed != expected or type(observed) is not type(expected):
        raise ValueError(f"B8 {field} differs")


def _b8_require_present(observed, field):
    if type(field) is not str:
        raise TypeError("B8 present field label must be an exact str")
    if observed is None:
        raise ValueError(f"B8 {field} is absent")


def _b8_require_absent(observed, field):
    if type(field) is not str:
        raise TypeError("B8 absent field label must be an exact str")
    if observed is not None:
        raise ValueError(f"B8 {field} is present")


def render_b8_consumer_adapter_utf8(route_id, route_module, wire_schema_id):
    """Render the frozen test-only B8 adapter for one exact route triple."""
    if (
        type(route_id) is not str
        or type(route_module) is not str
        or type(wire_schema_id) is not str
    ):
        raise TypeError("B8 route renderer inputs must be exact strings")
    if (route_id, route_module, wire_schema_id) not in _ROUTE_RENDER_TRIPLES:
        raise ValueError("B8 route renderer triple is not frozen")
    return (
        B8_CONSUMER_SKELETON_UTF8.replace(
            b"__ROUTE_MODULE__",
            route_module.encode("utf-8"),
        )
        .replace(b"__ROUTE_ID__", route_id.encode("utf-8"))
        .replace(b"__WIRE_SCHEMA_ID__", wire_schema_id.encode("utf-8"))
    )


_ROUTE_METRIC_ROOTS_V1 = (
    "encode_normalized_transcript",
    "verify_and_decode_route_wire",
)
_ROUTE_METRIC_FORBIDDEN_CALLS_V1 = (
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "getattr",
)
_B8_COUNTED_EXACT_CALL_NAMES_V1 = (
    "experiments.v3m0_b7_schema_lab.common._b8_require_exact",
    "experiments.v3m0_b7_schema_lab.common._b8_require_present",
    "experiments.v3m0_b7_schema_lab.common._b8_require_absent",
)


def _absolute_import_from_module_v1(node, route_module):
    if not isinstance(node, _ast.ImportFrom):
        raise TypeError("import-from resolver requires an ImportFrom node")
    if node.level == 0:
        return node.module or ""
    package_parts = route_module.split(".")[:-1]
    parent_count = node.level - 1
    if parent_count >= len(package_parts):
        raise ValueError("relative import escapes the route package")
    base_parts = package_parts[: len(package_parts) - parent_count]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _route_metric_bindings_v1(tree, route_module):
    aliases = {}
    binding_index = {}
    bound_names = set()
    for ordinal, node in enumerate(tree.body):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                resolved = alias.name if alias.asname else alias.name.split(".")[0]
                if bound in bound_names:
                    raise ValueError("route metric closure has a duplicate binding")
                bound_names.add(bound)
                aliases[bound] = resolved
            continue
        if isinstance(node, _ast.ImportFrom):
            module = _absolute_import_from_module_v1(node, route_module)
            if module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    raise ValueError(
                        "route metric closure cannot resolve a star import"
                    )
                bound = alias.asname or alias.name
                if bound in bound_names:
                    raise ValueError("route metric closure has a duplicate binding")
                bound_names.add(bound)
                aliases[bound] = f"{module}.{alias.name}"
            continue
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            name = node.name
        elif isinstance(node, _ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], _ast.Name):
                raise ValueError("route metric closure has a dynamic assignment target")
            name = node.targets[0].id
        elif isinstance(node, _ast.AnnAssign):
            if not isinstance(node.target, _ast.Name):
                raise ValueError("route metric closure has a dynamic annotated target")
            name = node.target.id
        elif (
            ordinal == 0
            and isinstance(node, _ast.Expr)
            and isinstance(node.value, _ast.Constant)
            and type(node.value.value) is str
        ) or isinstance(node, _ast.Pass):
            continue
        else:
            raise ValueError("route metric closure has dynamic top-level resolution")
        if name in bound_names:
            raise ValueError("route metric closure has a duplicate binding")
        bound_names.add(name)
        binding_index[name] = node
    return aliases, binding_index


def _binding_walk_roots_v1(node):
    if isinstance(node, _ast.Assign):
        return (node.value,)
    if isinstance(node, _ast.AnnAssign):
        return tuple(
            value for value in (node.annotation, node.value) if value is not None
        )
    return (node,)


def _resolve_metric_name_v1(node, aliases, binding_index, resolving=()):
    if isinstance(node, _ast.Name):
        if node.id in aliases:
            return aliases[node.id]
        if node.id not in binding_index:
            return node.id
        if node.id in resolving:
            raise ValueError("route metric closure has a cyclic alias")
        binding = binding_index[node.id]
        if isinstance(
            binding, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)
        ):
            return f"<route-binding>.{node.id}"
        value = binding.value
        if value is None:
            return None
        if not isinstance(value, (_ast.Name, _ast.Attribute)):
            return None
        return _resolve_metric_name_v1(
            value,
            aliases,
            binding_index,
            (*resolving, node.id),
        )
    if isinstance(node, _ast.Attribute):
        if isinstance(node.value, _ast.Name):
            owner = binding_index.get(node.value.id)
            if isinstance(owner, _ast.ClassDef):
                members = []
                for statement in owner.body:
                    if (
                        isinstance(
                            statement,
                            (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef),
                        )
                        and statement.name == node.attr
                    ):
                        members.append(statement)
                    elif (
                        isinstance(statement, _ast.Assign)
                        and len(statement.targets) == 1
                        and isinstance(statement.targets[0], _ast.Name)
                        and statement.targets[0].id == node.attr
                    ):
                        members.append(statement)
                    elif (
                        isinstance(statement, _ast.AnnAssign)
                        and isinstance(statement.target, _ast.Name)
                        and statement.target.id == node.attr
                    ):
                        members.append(statement)
                if len(members) != 1:
                    if members:
                        raise ValueError(
                            "route metric closure has a duplicate class binding"
                        )
                    return None
                member = members[0]
                if isinstance(
                    member,
                    (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef),
                ):
                    return f"<route-class-binding>.{node.value.id}.{node.attr}"
                value = member.value
                if value is None or not isinstance(
                    value,
                    (_ast.Name, _ast.Attribute),
                ):
                    return None
                return _resolve_metric_name_v1(
                    value,
                    aliases,
                    binding_index,
                    resolving,
                )
        prefix = _resolve_metric_name_v1(
            node.value,
            aliases,
            binding_index,
            resolving,
        )
        if prefix is None:
            return None
        return f"{prefix}.{node.attr}"
    return None


def _validate_reachable_calls_v1(node, aliases, binding_index):
    for child in _ast.walk(node):
        if not isinstance(child, _ast.Call):
            continue
        resolved = _resolve_metric_name_v1(child.func, aliases, binding_index)
        if resolved is None:
            raise ValueError("route metric closure has dynamic call resolution")
        terminal = resolved.split(".")[-1]
        if resolved in _ROUTE_METRIC_FORBIDDEN_CALLS_V1 or terminal in (
            _ROUTE_METRIC_FORBIDDEN_CALLS_V1
        ):
            raise ValueError("route metric closure calls a forbidden resolver")


def _route_local_reachable_closure_v1(tree, route_module):
    aliases, binding_index = _route_metric_bindings_v1(tree, route_module)
    if any(root not in binding_index for root in _ROUTE_METRIC_ROOTS_V1):
        raise ValueError("route metric closure omits a frozen root")
    queue = list(_ROUTE_METRIC_ROOTS_V1)
    queued = set(queue)
    ordered_bindings = []
    while queue:
        name = queue.pop(0)
        node = binding_index[name]
        ordered_bindings.append((name, node))
        edges = set()
        for walk_root in _binding_walk_roots_v1(node):
            _validate_reachable_calls_v1(walk_root, aliases, binding_index)
            for child in _ast.walk(walk_root):
                if (
                    isinstance(child, _ast.Name)
                    and isinstance(child.ctx, _ast.Load)
                    and child.id in binding_index
                    and child.id not in queued
                ):
                    edges.add(child.id)
        for edge in sorted(edges, key=lambda value: value.encode("utf-8")):
            queued.add(edge)
            queue.append(edge)
    return aliases, binding_index, ordered_bindings


def _iter_route_closure_nodes_v1(ordered_bindings):
    observed = set()
    for _name, binding in ordered_bindings:
        for walk_root in _binding_walk_roots_v1(binding):
            for node in _ast.walk(walk_root):
                if node not in observed:
                    observed.add(node)
                    yield node


def _count_route_branches_v1(closure_nodes):
    count = 0
    for node in closure_nodes:
        if isinstance(
            node,
            (_ast.If, _ast.IfExp, _ast.ExceptHandler, _ast.Assert),
        ) or type(node).__name__ in ("Match", "match_case"):
            count += 1
        elif isinstance(node, _ast.BoolOp):
            count += len(node.values) - 1
        elif isinstance(node, _ast.comprehension):
            count += len(node.ifs)
    return count


def _resolve_record_reference_v1(node, aliases, binding_index):
    target = node.value if isinstance(node, _ast.Subscript) else node
    root = target
    while isinstance(root, _ast.Attribute):
        root = root.value
    if not isinstance(root, _ast.Name):
        raise ValueError("route record test has dynamic resolution")
    static_builtin_roots = (
        "BaseException",
        "Exception",
        "ValueError",
        "bytes",
        "dict",
        "float",
        "frozenset",
        "int",
        "list",
        "object",
        "set",
        "str",
        "tuple",
    )
    if (
        root.id not in aliases
        and root.id not in binding_index
        and root.id not in static_builtin_roots
    ):
        raise ValueError("route record test has dynamic resolution")
    if isinstance(node, _ast.Subscript):
        resolved = _resolve_metric_name_v1(node.value, aliases, binding_index)
        if resolved is None or not resolved.startswith("typing."):
            raise ValueError("route record base uses dynamic subscription")
        return resolved
    resolved = _resolve_metric_name_v1(node, aliases, binding_index)
    if resolved is None:
        raise ValueError("route record test has dynamic resolution")
    return resolved


def _route_record_classes_v1(closure_nodes, aliases, binding_index):
    records = []
    for node in closure_nodes:
        if not isinstance(node, _ast.ClassDef):
            continue
        decorator_names = []
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, _ast.Call) else decorator
            decorator_names.append(
                _resolve_record_reference_v1(target, aliases, binding_index)
            )
        base_names = [
            _resolve_record_reference_v1(base, aliases, binding_index)
            for base in node.bases
        ]
        if "dataclasses.dataclass" in decorator_names or any(
            name in ("enum.Enum", "enum.StrEnum", "enum.IntEnum") for name in base_names
        ):
            records.append(node)
    return records


def _class_has_direct_sha_field_v1(node):
    for statement in node.body:
        field_name = None
        if isinstance(statement, _ast.AnnAssign) and isinstance(
            statement.target,
            _ast.Name,
        ):
            field_name = statement.target.id
        elif (
            isinstance(statement, _ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], _ast.Name)
        ):
            field_name = statement.targets[0].id
        if field_name is not None and field_name.endswith(("_sha", "_sha256")):
            return True
    return False


def _compute_b8_static_metrics_v1(route_id, route_module, wire_schema_id):
    rendered = render_b8_consumer_adapter_utf8(
        route_id,
        route_module,
        wire_schema_id,
    )
    tree = _parse_python_blob_v1(rendered, "<frozen-b8-consumer-adapter>")
    aliases, binding_index = _route_metric_bindings_v1(
        tree,
        "experiments.v3m0_b7_schema_lab._b8_consumer_adapter",
    )
    assertion_count = sum(isinstance(node, _ast.Assert) for node in _ast.walk(tree))
    for node in _ast.walk(tree):
        if (
            isinstance(node, _ast.Call)
            and _resolve_metric_name_v1(
                node.func,
                aliases,
                binding_index,
            )
            in _B8_COUNTED_EXACT_CALL_NAMES_V1
        ):
            assertion_count += 1

    baseline_text = B8_CONSUMER_SKELETON_UTF8.decode("utf-8", errors="strict")
    candidate_text = rendered.decode("utf-8", errors="strict")
    normalized = candidate_text.replace(route_module, "__ROUTE_MODULE__")
    normalized = normalized.replace(route_id, "__ROUTE_ID__")
    normalized = normalized.replace(wire_schema_id, "__WIRE_SCHEMA_ID__")
    diff_lines = _difflib.unified_diff(
        baseline_text.splitlines(keepends=False),
        normalized.splitlines(keepends=False),
        fromfile="skeleton",
        tofile="route",
        n=0,
        lineterm="",
    )
    changed_loc = sum(
        1
        for line in diff_lines
        if (line.startswith("+") or line.startswith("-"))
        and line not in ("--- skeleton", "+++ route")
        and not line.startswith("@@")
    )
    return assertion_count, changed_loc


def compute_route_static_metrics_v1(route_id, route_blob):
    """Compute the five frozen static metrics from one immutable route Git blob."""

    entry = _route_static_registry_entry_v1(route_id)
    _require_git_blob_descriptor_v1(route_blob, "route metric blob")
    _commit_sha, route_path, route_mode, route_source = route_blob
    if route_path != entry[3] or route_mode != "100644":
        raise ValueError("route metric blob path or mode drifted")
    tree = _parse_python_blob_v1(route_source, route_path)
    aliases, binding_index, ordered_bindings = _route_local_reachable_closure_v1(
        tree,
        entry[2],
    )
    closure_nodes = tuple(_iter_route_closure_nodes_v1(ordered_bindings))
    record_classes = _route_record_classes_v1(
        closure_nodes,
        aliases,
        binding_index,
    )
    b8_assertions, b8_changed_loc = _compute_b8_static_metrics_v1(
        entry[0],
        entry[2],
        entry[4],
    )
    return {
        "b8_consumer_assertion_count": b8_assertions,
        "b8_consumer_changed_loc": b8_changed_loc,
        "verifier_branch_count": _count_route_branches_v1(closure_nodes),
        "route_record_count": len(set(record_classes)),
        "route_hash_layer_count": len(
            {node for node in record_classes if _class_has_direct_sha_field_v1(node)}
        ),
    }


def _validate_decision_projection_v1(raw_body, fields, projection_fields):
    if type(raw_body) is not dict:
        raise TypeError("decision payload owner must be an exact dict")
    if len(raw_body) != len(fields) or any(name not in raw_body for name in fields):
        raise ValueError("decision payload owner fields drifted")
    projection = {name: raw_body[name] for name in projection_fields}
    if raw_body["decision_payload_sha"] != _pure_core.canonical_sha_v1(projection):
        raise ValueError("decision payload projection hash mismatch")
    return _pure_core.strict_json_loads_v1(_pure_core.canonical_json_bytes_v1(raw_body))


def validate_d0_decision_payload_projection_v1(raw_body):
    """Validate and detach the frozen D0 decision projection."""
    return _validate_decision_projection_v1(
        raw_body,
        _D0_COMPARISON_FIELDS,
        _D0_DECISION_FIELDS,
    )


def validate_d1_decision_payload_projection_v1(raw_body):
    """Validate and detach the frozen D1 decision projection."""
    return _validate_decision_projection_v1(
        raw_body,
        _D1_COMPARISON_FIELDS,
        _D1_DECISION_FIELDS,
    )


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


def validate_synthetic_graph_manifest_v1(raw_body):
    """Validate one complete graph through the pure core and its embedded Parent."""
    if type(raw_body) is not dict:
        raise TypeError("synthetic graph manifest must be an exact dict")
    parent_raw = raw_body.get("parent_freeze_v3_body")
    if type(parent_raw) is not dict:
        raise ValueError("synthetic graph manifest embedded Parent is absent")
    return _pure_core._validate_synthetic_graph_raw_v1(raw_body, parent_raw)


def validate_provenance_fixture_v1(raw_body):
    """Delegate one provenance fixture validation to the pure core."""
    return _pure_core.validate_provenance_fixture_v1(raw_body)


def validate_branch_attempt_v1(raw_body):
    """Delegate one branch-attempt validation to the pure core."""
    return _pure_core.validate_branch_attempt_v1(raw_body)


def _require_canonical_equal_v1(observed, expected, field):
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError(f"normalized transcript {field} drifted")


def _require_lineage_dict_v1(raw_body, field):
    if type(raw_body) is not dict:
        raise TypeError(f"normalized transcript {field} must be an exact dict")
    return raw_body


def _require_lineage_list_v1(raw_body, field):
    if type(raw_body) is not list:
        raise TypeError(f"normalized transcript {field} must be an exact list")
    return raw_body


def _synthetic_component_complete_body_v1(graph, component_id):
    components = _require_lineage_list_v1(
        graph.get("ordered_component_bodies"),
        "synthetic graph components",
    )
    matches = [
        component
        for component in components
        if type(component) is dict and component.get("component_id") == component_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"normalized transcript synthetic component {component_id} drifted"
        )
    return _require_lineage_dict_v1(
        matches[0].get("complete_body"),
        f"synthetic component {component_id} body",
    )


def _branch_lineage_v1(graph, branch):
    prefix = "actual" if branch == "actual" else "matched_ablated"
    transition = _synthetic_component_complete_body_v1(
        graph,
        f"{prefix}_transition_outcome",
    )
    factory_binding = _require_lineage_dict_v1(
        transition.get("factory_binding"),
        f"{branch} transition factory binding",
    )
    factory = _require_lineage_dict_v1(
        factory_binding.get("factory"),
        f"{branch} transition factory",
    )
    measured_transition = _require_lineage_dict_v1(
        transition.get("measured_transition"),
        f"{branch} measured transition",
    )
    certificate_outcome = _synthetic_component_complete_body_v1(
        graph,
        f"{prefix}_certificate_outcome",
    )
    status = _require_lineage_dict_v1(
        certificate_outcome.get("status"),
        f"{branch} certificate status",
    )
    certificate = certificate_outcome.get("certificate")
    if (
        status.get("defined") is not True
        or certificate_outcome.get("failure") is not None
        or type(certificate) is not dict
    ):
        raise ValueError(
            f"normalized transcript {branch} certificate lineage is not successful"
        )
    return {
        "factory_sha": factory.get("factory_sha"),
        "transition_sha": measured_transition.get("transition_sha"),
        "dynamics_certificate_sha": certificate.get("certificate_sha"),
        "dt": measured_transition.get("dt"),
    }


def _reference_lineage_context_v1(reference, run_spec, provenance, graph):
    permit = _require_lineage_dict_v1(
        provenance.get("permit_body"),
        "provenance permit",
    )
    calibration = _require_lineage_dict_v1(
        permit.get("calibration"),
        "provenance calibration",
    )
    calibration_outcome = _require_lineage_dict_v1(
        calibration.get("calibration_outcome"),
        "provenance calibration outcome",
    )
    calibration_manifest = _require_lineage_dict_v1(
        calibration_outcome.get("manifest"),
        "provenance calibration manifest",
    )
    control_registry = _require_lineage_dict_v1(
        calibration_manifest.get("control_registry"),
        "provenance control registry",
    )
    window_protocol = _require_lineage_dict_v1(
        calibration_manifest.get("window_protocol"),
        "provenance window protocol",
    )
    current_contract = _require_lineage_dict_v1(
        provenance.get("current_scenario_response_contract_v3_body"),
        "provenance current response contract",
    )
    control_entries = _require_lineage_list_v1(
        control_registry.get("entries"),
        "provenance control entries",
    )
    protocol_entries = _require_lineage_list_v1(
        window_protocol.get("control_entries"),
        "provenance window protocol entries",
    )
    reference_spec = _require_lineage_dict_v1(
        reference.get("reference_spec"),
        "endpoint reference spec",
    )
    control_entry = _require_lineage_dict_v1(
        reference_spec.get("control_registry_entry"),
        "endpoint reference control entry",
    )
    if control_entry.get("control_id") != "full":
        raise ValueError("normalized transcript reference control role drifted")
    matching_control_entries = [
        entry
        for entry in control_entries
        if type(entry) is dict
        and canonical_json_bytes_v1(entry) == canonical_json_bytes_v1(control_entry)
    ]
    if len(matching_control_entries) != 1:
        raise ValueError("normalized transcript reference control entry drifted")
    matching_protocol_entries = [
        entry
        for entry in protocol_entries
        if type(entry) is dict
        and entry.get("control_id") == "full"
        and entry.get("control_registry_entry_sha") == control_entry.get("entry_sha")
    ]
    if len(matching_protocol_entries) != 1:
        raise ValueError("normalized transcript reference protocol entry drifted")
    protocol_entry = matching_protocol_entries[0]
    actual_lineage = _branch_lineage_v1(graph, "actual")
    matched_lineage = _branch_lineage_v1(graph, "matched_ablated")

    for observed, expected, field in (
        (
            reference_spec.get("window_protocol_sha"),
            window_protocol.get("protocol_sha"),
            "reference/window protocol",
        ),
        (
            reference_spec.get("window_protocol_sha"),
            run_spec.get("window_protocol_sha"),
            "reference/run-spec protocol",
        ),
        (
            reference_spec.get("actual_factory_sha"),
            control_entry.get("factory_sha"),
            "reference/control factory",
        ),
        (
            reference_spec.get("actual_factory_sha"),
            actual_lineage["factory_sha"],
            "reference/actual factory",
        ),
        (
            actual_lineage["factory_sha"],
            current_contract.get("actual_factory_sha"),
            "actual graph/provenance factory",
        ),
        (
            matched_lineage["factory_sha"],
            current_contract.get("matched_factory_sha"),
            "matched graph/provenance factory",
        ),
        (
            reference_spec.get("actual_transition_sha"),
            actual_lineage["transition_sha"],
            "reference/actual transition",
        ),
        (
            reference_spec.get("actual_dynamics_certificate_sha"),
            actual_lineage["dynamics_certificate_sha"],
            "reference/actual certificate",
        ),
        (
            reference_spec.get("candidate_fejer_order"),
            run_spec.get("selected_fejer_order"),
            "reference/run-spec T",
        ),
        (
            reference_spec.get("candidate_fejer_order"),
            graph.get("selected_fejer_order"),
            "reference/synthetic-graph T",
        ),
        (
            reference_spec.get("reference_reciprocal_index"),
            run_spec.get("reference_reciprocal_index"),
            "reference/run-spec reciprocal index",
        ),
        (
            reference_spec.get("reference_reciprocal_index"),
            protocol_entry.get("reference_reciprocal_index"),
            "reference/protocol reciprocal index",
        ),
        (
            reference_spec.get("preregistered_phase_bands"),
            run_spec.get("preregistered_phase_bands"),
            "reference/run-spec phase bands",
        ),
        (
            reference_spec.get("preregistered_phase_bands"),
            protocol_entry.get("preregistered_phase_bands"),
            "reference/protocol phase bands",
        ),
        (
            reference_spec.get("expected_shell_rank"),
            run_spec.get("expected_shell_rank"),
            "reference/run-spec rank",
        ),
        (
            reference_spec.get("expected_shell_rank"),
            protocol_entry.get("expected_shell_rank"),
            "reference/protocol rank",
        ),
        (
            reference_spec.get("expected_shell_rank_source_id"),
            protocol_entry.get("expected_shell_rank_source_id"),
            "reference/protocol rank source",
        ),
        (
            control_entry.get("source_basis"),
            run_spec.get("source_basis"),
            "reference/run-spec source basis",
        ),
        (
            control_entry.get("readout_basis"),
            run_spec.get("readout_basis"),
            "reference/run-spec readout basis",
        ),
        (
            protocol_entry.get("response_grid"),
            run_spec.get("response_grid"),
            "protocol/run-spec response grid",
        ),
        (
            protocol_entry.get("source_readout_bridge_grid"),
            run_spec.get("source_readout_bridge_grid"),
            "protocol/run-spec bridge grid",
        ),
        (
            protocol_entry.get("source_readout_bridge_steps"),
            run_spec.get("source_readout_bridge_steps"),
            "protocol/run-spec bridge steps",
        ),
    ):
        _require_canonical_equal_v1(observed, expected, field)

    reference_projector = reference.get("reference")
    if reference_projector is not None:
        reference_projector = _require_lineage_dict_v1(
            reference_projector,
            "endpoint reference projector",
        )
        for observed, expected, field in (
            (
                reference_projector.get("control_registry_entry_sha"),
                control_entry.get("entry_sha"),
                "projector/control entry",
            ),
            (
                reference_projector.get("actual_transition_sha"),
                actual_lineage["transition_sha"],
                "projector/actual transition",
            ),
            (
                reference_projector.get("actual_dynamics_certificate_sha"),
                actual_lineage["dynamics_certificate_sha"],
                "projector/actual certificate",
            ),
            (
                reference_projector.get("reference_reciprocal_index"),
                run_spec.get("reference_reciprocal_index"),
                "projector/run-spec reciprocal index",
            ),
            (
                reference_projector.get("rank"),
                run_spec.get("expected_shell_rank"),
                "projector/run-spec rank",
            ),
        ):
            _require_canonical_equal_v1(observed, expected, field)
        projector = _require_lineage_dict_v1(
            reference_projector.get("projector"),
            "endpoint reference projector tensor",
        )
        state_dimension = len(
            _require_lineage_list_v1(
                run_spec.get("channel_order"),
                "run-spec channel order",
            )
        )
        _require_canonical_equal_v1(
            projector.get("shape"),
            [state_dimension, state_dimension],
            "reference projector shape",
        )
    return {
        "actual": actual_lineage,
        "matched_ablated": matched_lineage,
        "control_entry": control_entry,
        "protocol_entry": protocol_entry,
        "reference_projector": reference_projector,
    }


def _validate_shell_lineage_v1(shell_outcome, run_spec, lineage_context):
    shell_attempt = _require_lineage_dict_v1(
        shell_outcome.get("attempt_audit"),
        "endpoint shell attempt",
    )
    shell_spec = _require_lineage_dict_v1(
        shell_attempt.get("shell_spec"),
        "endpoint shell spec",
    )
    control_entry = lineage_context["control_entry"]
    protocol_entry = lineage_context["protocol_entry"]
    reference_projector = lineage_context["reference_projector"]
    for observed, expected, field in (
        (
            shell_spec.get("window_protocol_sha"),
            run_spec.get("window_protocol_sha"),
            "shell/run-spec protocol",
        ),
        (
            shell_spec.get("control_registry_entry"),
            control_entry,
            "shell/reference control entry",
        ),
        (
            shell_spec.get("response_grid"),
            run_spec.get("response_grid"),
            "shell/run-spec response grid",
        ),
        (
            shell_spec.get("response_grid"),
            protocol_entry.get("response_grid"),
            "shell/protocol response grid",
        ),
        (
            shell_spec.get("preregistered_phase_bands"),
            run_spec.get("preregistered_phase_bands"),
            "shell/run-spec phase bands",
        ),
        (
            shell_spec.get("candidate_fejer_order"),
            run_spec.get("selected_fejer_order"),
            "shell/run-spec T",
        ),
        (
            shell_spec.get("endpoint_reference_projector"),
            reference_projector,
            "shell/reference projector",
        ),
    ):
        _require_canonical_equal_v1(observed, expected, field)

    shell = shell_outcome.get("shell")
    if shell is None:
        return
    shell = _require_lineage_dict_v1(shell, "endpoint shell manifest")
    actual_lineage = lineage_context["actual"]
    for observed, expected, field in (
        (
            shell.get("actual_factory_sha"),
            actual_lineage["factory_sha"],
            "shell/actual factory",
        ),
        (
            shell.get("actual_transition_sha"),
            actual_lineage["transition_sha"],
            "shell/actual transition",
        ),
        (
            shell.get("actual_dynamics_certificate_sha"),
            actual_lineage["dynamics_certificate_sha"],
            "shell/actual certificate",
        ),
        (shell.get("dt"), actual_lineage["dt"], "shell/actual dt"),
        (shell.get("shell_spec"), shell_spec, "shell manifest/spec"),
    ):
        _require_canonical_equal_v1(observed, expected, field)
    response_grid = _require_lineage_dict_v1(
        run_spec.get("response_grid"),
        "run-spec response grid",
    )
    reciprocal_indices = _require_lineage_list_v1(
        response_grid.get("reciprocal_indices"),
        "run-spec response reciprocal indices",
    )
    channel_order = _require_lineage_list_v1(
        run_spec.get("channel_order"),
        "run-spec channel order",
    )
    shell_projectors = _require_lineage_dict_v1(
        shell.get("shell_projectors"),
        "shell projector tensor",
    )
    _require_canonical_equal_v1(
        shell_projectors.get("shape"),
        [len(reciprocal_indices), len(channel_order), len(channel_order)],
        "shell projector stack shape",
    )
    point_audits = _require_lineage_list_v1(
        shell.get("point_audits"),
        "shell point audits",
    )
    observed_indices = [
        _require_lineage_dict_v1(point, "shell point audit").get("reciprocal_index")
        for point in point_audits
    ]
    _require_canonical_equal_v1(
        observed_indices,
        reciprocal_indices,
        "shell point/grid order",
    )


def _validate_branch_attempt_lineage_v1(attempt, branch, run_spec, lineage):
    values = attempt.get("response_values")
    source_basis = _require_lineage_dict_v1(
        run_spec.get("source_basis"),
        "run-spec source basis",
    )
    readout_basis = _require_lineage_dict_v1(
        run_spec.get("readout_basis"),
        "run-spec readout basis",
    )
    response_grid = _require_lineage_dict_v1(
        run_spec.get("response_grid"),
        "run-spec response grid",
    )
    source_vectors = _require_lineage_list_v1(
        source_basis.get("vectors_wire"),
        "run-spec source vectors",
    )
    readout_vectors = _require_lineage_list_v1(
        readout_basis.get("vectors_wire"),
        "run-spec readout vectors",
    )
    response_indices = _require_lineage_list_v1(
        response_grid.get("reciprocal_indices"),
        "run-spec response reciprocal indices",
    )
    if values is not None:
        values = _require_lineage_dict_v1(values, f"{branch} attempt values")
        _require_canonical_equal_v1(
            values.get("shape"),
            [len(response_indices), len(readout_vectors), len(source_vectors)],
            f"{branch} attempt values shape",
        )

    bridge = attempt.get("bridge_audit")
    if bridge is None:
        return
    bridge = _require_lineage_dict_v1(bridge, f"{branch} attempt bridge")
    calibration = _require_lineage_dict_v1(
        run_spec.get("current_readout_calibration_spec"),
        "run-spec readout calibration",
    )
    source_whitener = _require_lineage_dict_v1(
        calibration.get("source_metric_whitener"),
        "run-spec source metric whitener",
    )
    for observed, expected, field in (
        (bridge.get("branch"), branch, f"{branch} bridge branch"),
        (
            bridge.get("factory_sha"),
            lineage["factory_sha"],
            f"{branch} bridge factory",
        ),
        (
            bridge.get("transition_sha"),
            lineage["transition_sha"],
            f"{branch} bridge transition",
        ),
        (
            bridge.get("dynamics_certificate_sha"),
            lineage["dynamics_certificate_sha"],
            f"{branch} bridge certificate",
        ),
        (
            bridge.get("run_spec_sha"),
            run_spec.get("run_spec_sha"),
            f"{branch} bridge run spec",
        ),
        (
            bridge.get("source_metric_whitener_sha"),
            source_whitener.get("tensor_sha"),
            f"{branch} bridge source calibration",
        ),
        (
            bridge.get("readout_calibration_spec_sha"),
            calibration.get("spec_sha"),
            f"{branch} bridge readout calibration",
        ),
    ):
        _require_canonical_equal_v1(observed, expected, field)
    bridge_grid = _require_lineage_dict_v1(
        run_spec.get("source_readout_bridge_grid"),
        "run-spec bridge grid",
    )
    bridge_indices = _require_lineage_list_v1(
        bridge_grid.get("reciprocal_indices"),
        "run-spec bridge reciprocal indices",
    )
    bridge_steps = _require_lineage_list_v1(
        run_spec.get("source_readout_bridge_steps"),
        "run-spec bridge steps",
    )
    expected_matrix_keys = [
        (reciprocal_index, macro_steps)
        for reciprocal_index in bridge_indices
        for macro_steps in bridge_steps
    ]
    matrix_audits = _require_lineage_list_v1(
        bridge.get("matrix_audits"),
        f"{branch} bridge matrix audits",
    )
    if len(matrix_audits) != len(expected_matrix_keys):
        raise ValueError(
            f"normalized transcript {branch} bridge matrix coverage drifted"
        )
    for audit_raw, (reciprocal_index, macro_steps) in zip(
        matrix_audits,
        expected_matrix_keys,
    ):
        audit = _require_lineage_dict_v1(
            audit_raw,
            f"{branch} bridge matrix audit",
        )
        _require_canonical_equal_v1(
            audit.get("reciprocal_index"),
            reciprocal_index,
            f"{branch} bridge matrix reciprocal index",
        )
        _require_canonical_equal_v1(
            audit.get("macro_steps"),
            macro_steps,
            f"{branch} bridge matrix macro steps",
        )
        matrix = _require_lineage_dict_v1(
            audit.get("raw_difference_matrix"),
            f"{branch} bridge difference matrix",
        )
        _require_canonical_equal_v1(
            matrix.get("shape"),
            [len(readout_vectors), len(source_vectors)],
            f"{branch} bridge matrix shape",
        )


def _validate_normalized_transcript_against_validated_graph_v1(
    raw_body,
    *,
    corpus_spec_sha,
    environment_manifest_sha,
    validated_graph,
):
    """Validate one transcript against one already validated complete graph."""

    expected_corpus_sha = _require_sha256_root_v1(corpus_spec_sha, "corpus spec")
    expected_environment_sha = _require_sha256_root_v1(
        environment_manifest_sha,
        "environment manifest",
    )
    transcript = validate_case_contract_v1(raw_body)
    if transcript["corpus_spec_sha"] != expected_corpus_sha:
        raise ValueError("normalized transcript corpus root drifted")
    if transcript["environment_manifest_sha"] != expected_environment_sha:
        raise ValueError("normalized transcript environment root drifted")

    if type(validated_graph) is not dict:
        raise TypeError("validated synthetic graph must be an exact dict")
    graph = validated_graph
    provenance = validate_provenance_fixture_v1(transcript["provenance_fixture"])
    run_spec = validate_response_run_spec_fixture_v1(
        transcript["response_run_spec_fixture"],
        provenance,
        graph,
    )
    reference = validate_endpoint_reference_outcome_raw_v1(
        transcript["reference_outcome"]
    )
    lineage_context = _reference_lineage_context_v1(
        reference,
        run_spec,
        provenance,
        graph,
    )
    shell_raw = transcript["shell_outcome"]
    shell = None
    if shell_raw is not None:
        shell = validate_endpoint_shell_outcome_raw_v1(shell_raw)
        _require_canonical_equal_v1(
            shell["reference_outcome"],
            reference,
            "shell/reference body",
        )
        _validate_shell_lineage_v1(shell, run_spec, lineage_context)

    attempts = {}
    for field, branch in (
        ("actual_branch_attempt", "actual"),
        ("matched_ablated_branch_attempt", "matched_ablated"),
    ):
        attempt_raw = transcript[field]
        attempt = None
        if attempt_raw is not None:
            attempt = validate_branch_attempt_v1(attempt_raw)
            if attempt["branch"] != branch:
                raise ValueError("normalized transcript attempt branch drifted")
            _validate_branch_attempt_lineage_v1(
                attempt,
                branch,
                run_spec,
                lineage_context[branch],
            )
        attempts[branch] = attempt

    for field, branch in (
        ("actual_completed_response", "actual"),
        ("matched_ablated_completed_response", "matched_ablated"),
    ):
        response_raw = transcript[field]
        if response_raw is None:
            continue
        response = validate_source_readout_response_raw_v1(
            response_raw,
            run_spec,
            provenance,
            graph,
        )
        if response["branch"] != branch:
            raise ValueError("normalized transcript completed branch drifted")
        attempt = attempts[branch]
        if attempt is None:
            raise ValueError("normalized transcript completed response lacks attempt")
        _require_canonical_equal_v1(
            response["values"],
            attempt["response_values"],
            f"{branch} values/attempt",
        )
        _require_canonical_equal_v1(
            response["bridge_audit"],
            attempt["bridge_audit"],
            f"{branch} bridge/attempt",
        )
        if shell is None or type(shell["shell"]) is not dict:
            raise ValueError("normalized transcript completed response lacks shell")
        if response["shell_manifest_sha"] != shell["shell"]["shell_manifest_sha"]:
            raise ValueError("normalized transcript response/shell root drifted")
    return transcript


def validate_normalized_transcript_v1(
    raw_body,
    *,
    corpus_spec_sha,
    environment_manifest_sha,
    graph_raw,
):
    """Strictly validate one normalized transcript and all aggregate joins."""

    graph = validate_synthetic_graph_manifest_v1(graph_raw)
    return _validate_normalized_transcript_against_validated_graph_v1(
        raw_body,
        corpus_spec_sha=corpus_spec_sha,
        environment_manifest_sha=environment_manifest_sha,
        validated_graph=graph,
    )


_NEUTRAL_CAPTURE_INPUT_FIELDS_V1 = (
    "reference_spec",
    "shell_spec_template",
    "reference_transition_matrix",
    "reference_metric_matrix",
    "ordered_shell_transition_matrices",
    "ordered_shell_metric_matrices",
    "source_injection_matrix",
    "readout_matrix",
    "ordered_actual_transition_matrices",
    "ordered_actual_metric_matrices",
    "ordered_matched_ablated_transition_matrices",
    "ordered_matched_ablated_metric_matrices",
    "ordered_actual_raw_differences",
    "ordered_matched_ablated_raw_differences",
)
_NEUTRAL_CAPTURE_FAILURES_V1 = {
    "actual_response_values": "actual_response_failed",
    "matched_ablated_response_values": "matched_ablated_response_failed",
    "actual_bridge": "actual_bridge_failed",
    "matched_ablated_bridge": "matched_ablated_bridge_failed",
}
_NEUTRAL_CAPTURE_INJECTED_BRANCH_V1 = "__injected_failure__"


def _case_contract_v1(case_id):
    if type(case_id) is not str:
        raise TypeError("capture case ID must be an exact str")
    matches = [row for row in _CASE_CONTRACTS_V1 if row[1] == case_id]
    if len(matches) != 1:
        raise ValueError("capture case ID is not frozen")
    return matches[0]


def _capture_leaf_value_projection_v1(value):
    if isinstance(value, _pure_core.np.ndarray):
        array = _pure_core.np.asarray(value)
        if array.dtype.kind not in ("c", "f", "i", "u"):
            raise TypeError("capture ndarray dtype is not numeric")
        values = []
        for item in array.reshape(-1):
            scalar = complex(item)
            values.append([float(scalar.real), float(scalar.imag)])
        return {
            "python_value_kind": "numpy.ndarray",
            "dtype": str(array.dtype),
            "shape": list(array.shape),
            "values_wire": values,
        }
    if isinstance(value, _pure_core.np.generic):
        return _capture_leaf_value_projection_v1(value.item())
    if type(value) is tuple:
        return {
            "python_value_kind": "tuple",
            "items": [_capture_leaf_value_projection_v1(item) for item in value],
        }
    if type(value) is list:
        return [_capture_leaf_value_projection_v1(item) for item in value]
    if type(value) is dict:
        return {
            name: _capture_leaf_value_projection_v1(item)
            for name, item in value.items()
        }
    if value is None or type(value) in (bool, int, float, str):
        return value
    if type(value) is complex:
        return {
            "python_value_kind": "complex",
            "real": float(value.real),
            "imag": float(value.imag),
        }
    raise TypeError("capture leaf input is not canonically projectable")


def _capture_leaf_digest_v1(leaves, leaf_id, call_args, output):
    leaf = {
        "leaf_id": leaf_id,
        "call_ordinal": len(leaves),
        "input_body_sha": canonical_sha_v1(
            {
                "argument_order": list(range(len(call_args))),
                "arguments": [
                    _capture_leaf_value_projection_v1(item) for item in call_args
                ],
            }
        ),
        "output_body_sha": canonical_sha_v1(_capture_leaf_value_projection_v1(output)),
    }
    leaves.append(leaf)
    return output


def _capture_injected_leaf_failure_v1(leaves, leaf_id, call_args):
    try:
        with _pure_core.np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            if leaf_id in (
                "actual_response_values",
                "matched_ablated_response_values",
            ):
                _pure_core._build_fejer_branch_response_values_from_raw(*call_args)
            elif leaf_id in ("actual_bridge", "matched_ablated_bridge"):
                _pure_core._audit_source_readout_bridge_from_raw(*call_args)
            else:
                raise ValueError("injected leaf ID is not a response stage")
    except (TypeError, ValueError) as error:
        observation = {
            "termination_kind": "INJECTED_FAILURE",
            "exception_type": type(error).__name__,
            "message": str(error),
        }
        _capture_leaf_digest_v1(leaves, leaf_id, call_args, observation)
        return
    raise ValueError(f"injected {leaf_id} leaf unexpectedly returned")


def _capture_rebind_shell_spec_v1(template, reference):
    if type(template) is not dict:
        raise TypeError("capture shell spec template must be an exact dict")
    shell_spec = _detach_json_v1(template)
    if "endpoint_reference_projector" not in shell_spec:
        raise ValueError("capture shell spec template lacks endpoint projector")
    shell_spec["endpoint_reference_projector"] = _detach_json_v1(reference)
    if "shell_spec_sha" not in shell_spec:
        raise ValueError("capture shell spec template lacks self root")
    shell_spec["shell_spec_sha"] = canonical_sha_v1(
        {name: value for name, value in shell_spec.items() if name != "shell_spec_sha"}
    )
    return shell_spec


def _capture_completed_response_v1(
    *,
    branch,
    values,
    bridge_audit,
    shell_manifest_sha,
    run_spec,
    provenance,
    graph,
):
    lineage = _branch_lineage_v1(graph, branch)
    payload = {
        "response_schema_version": "v3m0.source-readout-response.v1",
        "branch": branch,
        "factory_sha": lineage["factory_sha"],
        "transition_sha": lineage["transition_sha"],
        "dynamics_certificate_sha": lineage["dynamics_certificate_sha"],
        "source_basis": _detach_json_v1(run_spec["source_basis"]),
        "readout_basis": _detach_json_v1(run_spec["readout_basis"]),
        "run_spec_sha": run_spec["run_spec_sha"],
        "shell_manifest_sha": shell_manifest_sha,
        "bridge_audit": _detach_json_v1(bridge_audit),
        "values": _detach_json_v1(values),
    }
    response = {**payload, "response_sha": canonical_sha_v1(payload)}
    return validate_source_readout_response_raw_v1(
        response,
        run_spec,
        provenance,
        graph,
    )


def capture_normalized_transcript_from_raw_v1(
    *,
    case_id,
    corpus_spec_sha,
    environment_manifest_sha,
    provenance_fixture,
    response_run_spec_fixture,
    synthetic_graph_manifest,
    leaf_inputs,
):
    """Run one fixed scheduler prefix through the five owner-neutral raw leaves."""

    case_contract = _case_contract_v1(case_id)
    corpus_root = _require_sha256_root_v1(corpus_spec_sha, "capture corpus spec")
    environment_root = _require_sha256_root_v1(
        environment_manifest_sha,
        "capture environment manifest",
    )
    inputs = _require_exact_ordered_dict_v1(
        leaf_inputs,
        _NEUTRAL_CAPTURE_INPUT_FIELDS_V1,
        "neutral capture leaf inputs",
    )
    graph = validate_synthetic_graph_manifest_v1(synthetic_graph_manifest)
    provenance = validate_provenance_fixture_v1(provenance_fixture)
    run_spec = validate_response_run_spec_fixture_v1(
        response_run_spec_fixture,
        provenance,
        graph,
    )
    injected_stage = case_contract[3]
    leaves = []

    reference_args = (
        inputs["reference_spec"],
        inputs["reference_transition_matrix"],
        inputs["reference_metric_matrix"],
        inputs["source_injection_matrix"],
        inputs["readout_matrix"],
    )
    with _pure_core.np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        reference_output = _pure_core._select_endpoint_reference_from_raw(
            *reference_args
        )
    reference = _capture_leaf_digest_v1(
        leaves,
        "reference",
        reference_args,
        reference_output,
    )
    reference_defined = (
        type(reference) is dict
        and type(reference.get("status")) is dict
        and reference["status"].get("defined") is True
        and type(reference.get("reference")) is dict
    )
    if injected_stage == "reference":
        if reference_defined or reference.get("failure") is None:
            raise ValueError("reference-failure capture did not fail at reference")
        shell = None
        actual_attempt = None
        matched_attempt = None
        actual_completed = None
        matched_completed = None
    else:
        if not reference_defined or reference.get("failure") is not None:
            raise ValueError("capture reference leaf did not succeed")
        shell_spec = _capture_rebind_shell_spec_v1(
            inputs["shell_spec_template"],
            reference["reference"],
        )
        actual_lineage = _branch_lineage_v1(graph, "actual")
        shell_args = (
            reference,
            shell_spec,
            inputs["ordered_shell_transition_matrices"],
            inputs["ordered_shell_metric_matrices"],
            inputs["source_injection_matrix"],
            inputs["readout_matrix"],
            actual_lineage["factory_sha"],
            actual_lineage["transition_sha"],
            actual_lineage["dynamics_certificate_sha"],
            actual_lineage["dt"],
        )
        with _pure_core.np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            shell_output = _pure_core._track_endpoint_shell_from_raw(*shell_args)
        shell = _capture_leaf_digest_v1(
            leaves,
            "shell",
            shell_args,
            shell_output,
        )
        shell_defined = (
            type(shell) is dict
            and type(shell.get("status")) is dict
            and shell["status"].get("defined") is True
            and type(shell.get("shell")) is dict
        )
        if injected_stage == "shell":
            if shell_defined or shell.get("failure") is None:
                raise ValueError("shell-failure capture did not fail at shell")
            actual_attempt = None
            matched_attempt = None
            actual_completed = None
            matched_completed = None
        else:
            if not shell_defined or shell.get("failure") is not None:
                raise ValueError("capture shell leaf did not succeed")
            shell_manifest = shell["shell"]
            shell_phases = shell_manifest["shell_phases"]

            value_specs = (
                (
                    "actual_response_values",
                    "actual",
                    "ordered_actual_transition_matrices",
                    "ordered_actual_metric_matrices",
                ),
                (
                    "matched_ablated_response_values",
                    "matched_ablated",
                    "ordered_matched_ablated_transition_matrices",
                    "ordered_matched_ablated_metric_matrices",
                ),
            )
            values_by_branch = {"actual": None, "matched_ablated": None}
            for leaf_id, branch, transition_field, metric_field in value_specs:
                call_branch = (
                    _NEUTRAL_CAPTURE_INJECTED_BRANCH_V1
                    if injected_stage == leaf_id
                    else branch
                )
                call_args = (
                    call_branch,
                    run_spec["response_grid"],
                    run_spec["selected_fejer_order"],
                    run_spec["source_basis"],
                    run_spec["readout_basis"],
                    shell_phases,
                    inputs[transition_field],
                    inputs[metric_field],
                )
                if injected_stage == leaf_id:
                    _capture_injected_leaf_failure_v1(
                        leaves,
                        leaf_id,
                        call_args,
                    )
                    break
                with _pure_core.np.errstate(
                    divide="ignore",
                    over="ignore",
                    invalid="ignore",
                ):
                    values_output = (
                        _pure_core._build_fejer_branch_response_values_from_raw(
                            *call_args
                        )
                    )
                values_by_branch[branch] = _capture_leaf_digest_v1(
                    leaves,
                    leaf_id,
                    call_args,
                    values_output,
                )

            audits_by_branch = {"actual": None, "matched_ablated": None}
            if injected_stage not in (
                "actual_response_values",
                "matched_ablated_response_values",
            ):
                bridge_specs = (
                    ("actual_bridge", "actual", "ordered_actual_raw_differences"),
                    (
                        "matched_ablated_bridge",
                        "matched_ablated",
                        "ordered_matched_ablated_raw_differences",
                    ),
                )
                for leaf_id, branch, differences_field in bridge_specs:
                    lineage = _branch_lineage_v1(graph, branch)
                    call_branch = (
                        _NEUTRAL_CAPTURE_INJECTED_BRANCH_V1
                        if injected_stage == leaf_id
                        else branch
                    )
                    call_args = (
                        call_branch,
                        lineage["factory_sha"],
                        lineage["transition_sha"],
                        lineage["dynamics_certificate_sha"],
                        run_spec["run_spec_sha"],
                        run_spec["source_readout_bridge_grid"],
                        run_spec["source_readout_bridge_steps"],
                        run_spec["source_trial_vectors"],
                        run_spec["current_readout_calibration_spec"],
                        inputs[differences_field],
                    )
                    if injected_stage == leaf_id:
                        _capture_injected_leaf_failure_v1(
                            leaves,
                            leaf_id,
                            call_args,
                        )
                        break
                    with _pure_core.np.errstate(
                        divide="ignore",
                        over="ignore",
                        invalid="ignore",
                    ):
                        bridge_output = (
                            _pure_core._audit_source_readout_bridge_from_raw(*call_args)
                        )
                    audits_by_branch[branch] = _capture_leaf_digest_v1(
                        leaves,
                        leaf_id,
                        call_args,
                        bridge_output,
                    )

            first_failure = _NEUTRAL_CAPTURE_FAILURES_V1.get(injected_stage)
            actual_attempt, matched_attempt, observed_failure = (
                _pure_core._assemble_atomic_paired_response_attempt_from_raw(
                    values_by_branch["actual"],
                    values_by_branch["matched_ablated"],
                    audits_by_branch["actual"],
                    audits_by_branch["matched_ablated"],
                    first_failure,
                )
            )
            if observed_failure != first_failure:
                raise ValueError("capture paired assembly failure drifted")
            actual_completed = None
            matched_completed = None
            if first_failure is None:
                actual_completed = _capture_completed_response_v1(
                    branch="actual",
                    values=values_by_branch["actual"],
                    bridge_audit=audits_by_branch["actual"],
                    shell_manifest_sha=shell_manifest["shell_manifest_sha"],
                    run_spec=run_spec,
                    provenance=provenance,
                    graph=graph,
                )
                matched_completed = _capture_completed_response_v1(
                    branch="matched_ablated",
                    values=values_by_branch["matched_ablated"],
                    bridge_audit=audits_by_branch["matched_ablated"],
                    shell_manifest_sha=shell_manifest["shell_manifest_sha"],
                    run_spec=run_spec,
                    provenance=provenance,
                    graph=graph,
                )

    callback_trace = [leaf["leaf_id"] for leaf in leaves]
    if (
        tuple(callback_trace) != case_contract[7]
        or tuple(callback_trace) != case_contract[8]
    ):
        raise ValueError("capture leaf trace differs from frozen scheduler prefix")
    payload = {
        "transcript_schema_version": ("experimental.v3m0.b7.normalized-transcript.v1"),
        "corpus_spec_sha": corpus_root,
        "case_id": case_id,
        "environment_manifest_sha": environment_root,
        "provenance_fixture": _detach_json_v1(provenance),
        "response_run_spec_fixture": _detach_json_v1(run_spec),
        "reference_outcome": _detach_json_v1(reference),
        "shell_outcome": _detach_json_v1(shell),
        "actual_branch_attempt": _detach_json_v1(actual_attempt),
        "matched_ablated_branch_attempt": _detach_json_v1(matched_attempt),
        "actual_completed_response": _detach_json_v1(actual_completed),
        "matched_ablated_completed_response": _detach_json_v1(matched_completed),
        "terminal_tag": case_contract[2],
        "callback_trace": callback_trace,
        "ordered_leaf_digests": leaves,
    }
    transcript = {**payload, "experimental_sha": canonical_sha_v1(payload)}
    return validate_normalized_transcript_v1(
        transcript,
        corpus_spec_sha=corpus_root,
        environment_manifest_sha=environment_root,
        graph_raw=graph,
    )


def _d1_capture_control_entry_v1(provenance):
    try:
        entries = provenance["permit_body"]["calibration"]["calibration_outcome"][
            "manifest"
        ]["control_registry"]["entries"]
    except (KeyError, TypeError):
        raise ValueError("D1 capture provenance lacks its control registry") from None
    if type(entries) is not list or not entries or type(entries[0]) is not dict:
        raise TypeError("D1 capture control registry must contain a first entry")
    return _detach_json_v1(entries[0])


def _d1_capture_reference_spec_v1(provenance, run_spec, graph):
    actual = _branch_lineage_v1(graph, "actual")
    payload = {
        "reference_spec_schema_version": "v3m0.endpoint-reference-spec.v1",
        "window_protocol_sha": run_spec["window_protocol_sha"],
        "control_registry_entry": _d1_capture_control_entry_v1(provenance),
        "actual_factory_sha": actual["factory_sha"],
        "actual_transition_sha": actual["transition_sha"],
        "actual_dynamics_certificate_sha": actual["dynamics_certificate_sha"],
        "candidate_fejer_order": run_spec["selected_fejer_order"],
        "reference_reciprocal_index": _detach_json_v1(
            run_spec["reference_reciprocal_index"]
        ),
        "preregistered_phase_bands": _detach_json_v1(
            run_spec["preregistered_phase_bands"]
        ),
        "expected_shell_rank": run_spec["expected_shell_rank"],
        "expected_shell_rank_source_id": ("parent-freeze-control-application-spec-v1"),
    }
    return {**payload, "reference_spec_sha": canonical_sha_v1(payload)}


def _d1_capture_shell_spec_template_v1(provenance, run_spec):
    payload = {
        "shell_spec_schema_version": "v3m0.endpoint-shell-spec.v1",
        "window_protocol_sha": run_spec["window_protocol_sha"],
        "control_registry_entry": _d1_capture_control_entry_v1(provenance),
        "response_grid": _detach_json_v1(run_spec["response_grid"]),
        "preregistered_phase_bands": _detach_json_v1(
            run_spec["preregistered_phase_bands"]
        ),
        "candidate_fejer_order": run_spec["selected_fejer_order"],
        "endpoint_reference_projector": None,
        "extraction_protocol_id": "endpoint-single-node-reference-v1",
    }
    return {**payload, "shell_spec_sha": canonical_sha_v1(payload)}


def _d1_capture_leaf_inputs_v1(provenance, run_spec, graph, case_id):
    channel_order = run_spec.get("channel_order")
    shell_rank = run_spec.get("expected_shell_rank")
    if type(channel_order) is not list or not channel_order:
        raise TypeError("D1 capture channel order must be a nonempty list")
    state_count = len(channel_order)
    if type(shell_rank) is not int or not 0 < shell_rank <= state_count:
        raise ValueError("D1 capture shell rank is outside the state space")
    if run_spec.get("selected_fejer_order") != 256:
        raise ValueError("D1 capture raw inputs require T=256")
    bridge_grid = run_spec.get("source_readout_bridge_grid")
    bridge_steps = run_spec.get("source_readout_bridge_steps")
    if (
        type(bridge_grid) is not dict
        or type(bridge_grid.get("reciprocal_indices")) is not list
        or type(bridge_steps) is not list
    ):
        raise TypeError("D1 capture bridge domain is not frozen")

    np = _pure_core.np
    success_transition = np.diag(
        np.asarray(
            [1.0j] * shell_rank + [1.0 + 0.0j] * (state_count - shell_rank),
            dtype=np.complex128,
        )
    )
    failure_transition = np.eye(state_count, dtype=np.complex128)
    metric = np.eye(state_count, dtype=np.complex128)
    source_injection = np.zeros((state_count, shell_rank), dtype=np.complex128)
    source_injection[:shell_rank, :] = np.eye(shell_rank, dtype=np.complex128)
    readout = np.zeros((shell_rank, state_count), dtype=np.complex128)
    readout[:, :shell_rank] = np.eye(shell_rank, dtype=np.complex128)
    bridge_differences = tuple(
        (
            tuple(reciprocal_index),
            macro_steps,
            np.zeros((shell_rank, shell_rank), dtype=np.complex128),
        )
        for reciprocal_index in bridge_grid["reciprocal_indices"]
        for macro_steps in bridge_steps
    )
    return {
        "reference_spec": _d1_capture_reference_spec_v1(
            provenance,
            run_spec,
            graph,
        ),
        "shell_spec_template": _d1_capture_shell_spec_template_v1(
            provenance,
            run_spec,
        ),
        "reference_transition_matrix": (
            failure_transition if case_id == "reference_failure" else success_transition
        ),
        "reference_metric_matrix": metric,
        "ordered_shell_transition_matrices": (
            failure_transition if case_id == "shell_failure" else success_transition,
        ),
        "ordered_shell_metric_matrices": (metric,),
        "source_injection_matrix": source_injection,
        "readout_matrix": readout,
        "ordered_actual_transition_matrices": (success_transition,),
        "ordered_actual_metric_matrices": (metric,),
        "ordered_matched_ablated_transition_matrices": (success_transition,),
        "ordered_matched_ablated_metric_matrices": (metric,),
        "ordered_actual_raw_differences": bridge_differences,
        "ordered_matched_ablated_raw_differences": bridge_differences,
    }


def capture_d1_transcript_set_v1(*, capture_ordinal, validated_corpus_fixture):
    """Freshly recapture the seven T=256 cases through the common-owned harness."""

    if type(capture_ordinal) is not int:
        raise TypeError("D1 capture ordinal must be an exact int")
    if capture_ordinal not in (0, 1, 2):
        raise ValueError("D1 capture ordinal is not frozen")
    fixture, source_sets = _validated_d0_fixture_source_domain_v1(
        validated_corpus_fixture
    )
    if type(source_sets) is not list or len(source_sets) != 1:
        raise ValueError("D1 capture requires exactly one D0 fixture source set")
    d0_sources = source_sets[0]
    graph = validate_synthetic_graph_manifest_v1(fixture["synthetic_graph_manifest"])
    if graph.get("selected_fejer_order") != 256 or canonical_json_bytes_v1(
        graph
    ) != canonical_json_bytes_v1(fixture["synthetic_graph_manifest"]):
        raise ValueError("D1 capture fixture graph is not exact T=256")
    corpus_root = fixture["corpus_spec"]["corpus_spec_sha"]
    environment_root = fixture["environment_manifest"]["environment_sha"]
    validated_sources = []
    for source in d0_sources:
        validated = _validate_normalized_transcript_against_validated_graph_v1(
            source,
            corpus_spec_sha=corpus_root,
            environment_manifest_sha=environment_root,
            validated_graph=graph,
        )
        if canonical_json_bytes_v1(validated) != canonical_json_bytes_v1(source):
            raise ValueError("D1 capture D0 source lineage was substituted")
        validated_sources.append(validated)

    provenance = validated_sources[0].get("provenance_fixture")
    run_spec = validated_sources[0].get("response_run_spec_fixture")
    if type(provenance) is not dict or type(run_spec) is not dict:
        raise TypeError("D1 capture source lacks provenance or run spec")
    for source in validated_sources[1:]:
        if canonical_json_bytes_v1(source.get("provenance_fixture")) != (
            canonical_json_bytes_v1(provenance)
        ) or canonical_json_bytes_v1(source.get("response_run_spec_fixture")) != (
            canonical_json_bytes_v1(run_spec)
        ):
            raise ValueError("D1 capture D0 sources do not share one raw input graph")

    transcripts = []
    for case_contract in _CASE_CONTRACTS_V1:
        case_id = case_contract[1]
        transcript = capture_normalized_transcript_from_raw_v1(
            case_id=case_id,
            corpus_spec_sha=corpus_root,
            environment_manifest_sha=environment_root,
            provenance_fixture=provenance,
            response_run_spec_fixture=run_spec,
            synthetic_graph_manifest=graph,
            leaf_inputs=_d1_capture_leaf_inputs_v1(
                provenance,
                run_spec,
                graph,
                case_id,
            ),
        )
        if type(transcript) is not dict or transcript.get("case_id") != case_id:
            raise ValueError("D1 capture scheduler returned a substituted case")
        transcripts.append(transcript)
    return transcripts


_CORPUS_FIXTURE_V2_FIELDS = (
    "fixture_schema_version",
    "corpus_spec",
    "mutation_universe",
    "metric_spec",
    "environment_manifest",
    "synthetic_graph_manifest",
    "ordered_d0_transcripts",
    "fixture_sha",
)


def _validate_corpus_fixture_v2_top_level_v1(raw_body):
    if type(raw_body) is not dict:
        raise TypeError("B7LabCorpusFixtureV2 must be an exact dict")
    if len(raw_body) != len(_CORPUS_FIXTURE_V2_FIELDS) or any(
        name not in raw_body for name in _CORPUS_FIXTURE_V2_FIELDS
    ):
        raise ValueError("B7LabCorpusFixtureV2 fields drifted")
    fixture = {name: raw_body[name] for name in _CORPUS_FIXTURE_V2_FIELDS}
    if fixture["fixture_schema_version"] != ("experimental.v3m0.b7.corpus-fixture.v2"):
        raise ValueError("B7LabCorpusFixtureV2 schema version drifted")
    for field in (
        "corpus_spec",
        "mutation_universe",
        "metric_spec",
        "environment_manifest",
        "synthetic_graph_manifest",
    ):
        if type(fixture[field]) is not dict:
            raise TypeError(f"B7LabCorpusFixtureV2 {field} must be an exact dict")
    transcripts = fixture["ordered_d0_transcripts"]
    if (
        type(transcripts) is not list
        or len(transcripts) != 7
        or any(type(transcript) is not dict for transcript in transcripts)
    ):
        raise TypeError("B7LabCorpusFixtureV2 requires exactly seven transcripts")
    _require_sha256_root_v1(fixture["fixture_sha"], "corpus fixture")
    canonical_json_bytes_v1(fixture)
    return fixture


def validate_corpus_fixture_v2(
    raw_body,
    common_source_bytes,
    compare_source_bytes,
    *,
    python_identity_observation,
    python_probe_result,
):
    """Validate one graph-bearing V2 corpus against caller-owned observations."""

    fixture = _validate_corpus_fixture_v2_top_level_v1(raw_body)
    corpus = validate_corpus_spec_v1(
        fixture["corpus_spec"],
        fixture["metric_spec"].get("metric_spec_sha"),
    )
    mutation_universe = validate_mutation_universe_v1(
        fixture["mutation_universe"],
        fixture["ordered_d0_transcripts"],
        corpus["corpus_spec_sha"],
        corpus["mutation_generation_contract_sha"],
        common_source_bytes,
    )
    metric = validate_metric_spec_v1(
        fixture["metric_spec"],
        common_source_bytes,
        compare_source_bytes,
    )
    environment = validate_environment_manifest_v2(
        fixture["environment_manifest"],
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
    )
    if corpus["metric_spec_sha"] != metric["metric_spec_sha"]:
        raise ValueError("corpus fixture metric root drifted")
    if mutation_universe["corpus_spec_sha"] != corpus["corpus_spec_sha"]:
        raise ValueError("corpus fixture mutation/corpus root drifted")

    graph = validate_synthetic_graph_manifest_v1(fixture["synthetic_graph_manifest"])
    graph_bytes = canonical_json_bytes_v1(graph)
    if graph_bytes != canonical_json_bytes_v1(fixture["synthetic_graph_manifest"]):
        raise ValueError("corpus fixture validated graph body was substituted")

    expected_case_ids = tuple(row[1] for row in _CASE_CONTRACTS_V1)
    transcripts = fixture["ordered_d0_transcripts"]
    observed_case_ids = tuple(transcript.get("case_id") for transcript in transcripts)
    if observed_case_ids != expected_case_ids:
        raise ValueError("corpus fixture transcript case order drifted")
    for transcript in transcripts:
        if transcript.get("corpus_spec_sha") != corpus["corpus_spec_sha"]:
            raise ValueError("corpus fixture transcript corpus root drifted")
        if transcript.get("environment_manifest_sha") != environment["environment_sha"]:
            raise ValueError("corpus fixture transcript environment root drifted")
        validated_transcript = (
            _validate_normalized_transcript_against_validated_graph_v1(
                transcript,
                corpus_spec_sha=corpus["corpus_spec_sha"],
                environment_manifest_sha=environment["environment_sha"],
                validated_graph=graph,
            )
        )
        if validated_transcript["case_id"] != transcript[
            "case_id"
        ] or canonical_json_bytes_v1(validated_transcript) != canonical_json_bytes_v1(
            transcript
        ):
            raise ValueError("corpus fixture validated transcript was substituted")
        if canonical_json_bytes_v1(graph) != graph_bytes:
            raise ValueError(
                "corpus fixture graph mutated during transcript validation"
            )

    expected_fixture_sha = canonical_sha_v1(
        {
            name: fixture[name]
            for name in _CORPUS_FIXTURE_V2_FIELDS
            if name != "fixture_sha"
        }
    )
    if fixture["fixture_sha"] != expected_fixture_sha:
        raise ValueError("corpus fixture self hash mismatch")
    return _detach_json_v1(fixture)


def _require_exact_seven_bytes_v1(raw_values, field):
    if (
        type(raw_values) is not list
        or len(raw_values) != 7
        or any(type(value) is not bytes for value in raw_values)
    ):
        raise TypeError(f"{field} must be an exact seven-byte-string list")
    return raw_values


def _ordered_bytes_root_v1(case_ids, ordered_bytes):
    return canonical_sha_v1(
        [
            {
                "case_id": case_id,
                "raw_sha256": _pure_core.hashlib.sha256(raw_bytes).hexdigest(),
            }
            for case_id, raw_bytes in zip(case_ids, ordered_bytes)
        ]
    )


def build_cross_replay_cell_v1(
    *,
    capture_ordinal,
    synthetic_graph_manifest_sha,
    route_id,
    route_manifest_sha,
    ordered_source_transcript_bytes,
    ordered_route_wire_bytes,
    ordered_decoded_transcript_bytes,
):
    """Build one D1 cross-replay cell from exact captured byte strings."""

    if type(capture_ordinal) is not int or capture_ordinal not in (0, 1, 2):
        raise ValueError("cross-replay capture ordinal is not frozen")
    _validate_lab_wire_semantics_v1(route_id, "route-id", None, "route_id")
    graph_sha = _require_sha256_root_v1(
        synthetic_graph_manifest_sha,
        "synthetic graph manifest",
    )
    manifest_sha = _require_sha256_root_v1(route_manifest_sha, "route manifest")
    sources = _require_exact_seven_bytes_v1(
        ordered_source_transcript_bytes,
        "source transcripts",
    )
    wires = _require_exact_seven_bytes_v1(
        ordered_route_wire_bytes,
        "route wires",
    )
    decoded = _require_exact_seven_bytes_v1(
        ordered_decoded_transcript_bytes,
        "decoded transcripts",
    )
    transcripts = []
    for raw_bytes in sources:
        parsed = strict_json_loads_v1(raw_bytes)
        if canonical_json_bytes_v1(parsed) != raw_bytes:
            raise ValueError("source transcript bytes are not canonical")
        transcripts.append(validate_case_contract_v1(parsed))
    case_ids = [transcript["case_id"] for transcript in transcripts]
    expected_case_ids = [row[1] for row in _CASE_CONTRACTS_V1]
    if case_ids != expected_case_ids:
        raise ValueError("cross-replay source case order drifted")

    transcript_root = _ordered_bytes_root_v1(case_ids, sources)
    decoded_root = _ordered_bytes_root_v1(case_ids, decoded)
    wire_entries = [
        {
            "case_id": case_id,
            "wire_raw_sha256": _pure_core.hashlib.sha256(raw_bytes).hexdigest(),
        }
        for case_id, raw_bytes in zip(case_ids, wires)
    ]
    route_wire_root = canonical_sha_v1(
        {
            "route_id": route_id,
            "capture_ordinal": capture_ordinal,
            "ordered_entries": wire_entries,
        }
    )
    leaf_entries = [
        {
            "case_id": case_id,
            "ordered_leaf_digests_sha": canonical_sha_v1(
                transcript["ordered_leaf_digests"]
            ),
        }
        for case_id, transcript in zip(case_ids, transcripts)
    ]
    leaf_root = canonical_sha_v1(leaf_entries)
    cell = {
        "cell_schema_version": "experimental.v3m0.b7.cross-replay-cell.v1",
        "capture_ordinal": capture_ordinal,
        "case_count": 7,
        "ordered_case_ids": case_ids,
        "transcript_set_sha": transcript_root,
        "synthetic_graph_manifest_sha": graph_sha,
        "route_id": route_id,
        "route_manifest_sha": manifest_sha,
        "route_wire_set_sha": route_wire_root,
        "decoded_transcript_set_sha": decoded_root,
        "ordered_leaf_digest_set_sha": leaf_root,
        "exact_transcript_match": (
            decoded == sources and decoded_root == transcript_root
        ),
        "cell_sha": "",
    }
    _rehash_record_field_v1(cell, "cell_sha")
    return validate_exact_lab_record_v1("B7LabCrossReplayCellV1", cell)


def compute_evidence_loss_count_v1(
    ordered_source_transcripts_raw,
    ordered_decoded_transcripts_raw,
):
    """Count exact non-null evidence-pointer losses over one seven-case capture."""

    if (
        type(ordered_source_transcripts_raw) is not list
        or type(ordered_decoded_transcripts_raw) is not list
        or len(ordered_source_transcripts_raw) != 7
        or len(ordered_decoded_transcripts_raw) != 7
        or any(type(raw) is not dict for raw in ordered_decoded_transcripts_raw)
    ):
        raise TypeError("evidence metric requires two exact seven-transcript lists")
    sources = [validate_case_contract_v1(raw) for raw in ordered_source_transcripts_raw]
    if [source["case_id"] for source in sources] != [
        row[1] for row in _CASE_CONTRACTS_V1
    ]:
        raise ValueError("evidence metric source case order drifted")
    loss_count = 0
    for source, decoded in zip(sources, ordered_decoded_transcripts_raw):
        for pointer in _EVIDENCE_POINTER_ORDER_V1:
            source_present, source_value = _optional_pointer_value_v1(source, pointer)
            if not source_present:
                continue
            decoded_present, decoded_value = _optional_pointer_value_v1(
                decoded,
                pointer,
            )
            if not decoded_present or canonical_json_bytes_v1(
                decoded_value
            ) != canonical_json_bytes_v1(source_value):
                loss_count += 1
    return loss_count


def compute_canonical_wire_bytes_v1(ordered_wire_bytes):
    """Validate and total one dynamic capture's canonical route-wire bytes."""

    if (
        type(ordered_wire_bytes) is not list
        or not ordered_wire_bytes
        or any(type(raw_bytes) is not bytes for raw_bytes in ordered_wire_bytes)
    ):
        raise TypeError("canonical wire metric requires a nonempty exact bytes list")
    total = 0
    for raw_bytes in ordered_wire_bytes:
        parsed = strict_json_loads_v1(raw_bytes)
        if canonical_json_bytes_v1(parsed) != raw_bytes:
            raise ValueError("route wire is not project-canonical JSON")
        total += len(raw_bytes)
    return total


GATE_CONTRACTS_V1 = (
    (
        "E01",
        ("D0", "D1"),
        "validate_gate_e01_v1",
        (
            "legal-case-count-is-7",
            "every-case-encode-returns-canonical-bytes",
            "every-case-verify-decode-returns-source-bytes",
        ),
        (
            "E01_LEGAL_CASE_COUNT_MISMATCH",
            "E01_LEGAL_ENCODE_FAILURE",
            "E01_LEGAL_DECODE_MISMATCH",
        ),
    ),
    (
        "E02",
        ("D0", "D1"),
        "validate_gate_e02_v1",
        (
            "mutation-probe-count-equals-universe-domain",
            "mutation-accept-count-is-zero",
            "wrong-exception-or-nonbytes-count-is-zero",
        ),
        (
            "E02_MUTATION_DOMAIN_MISMATCH",
            "E02_MUTATION_ACCEPTED",
            "E02_INVALID_REJECTION_SURFACE",
        ),
    ),
    (
        "E03",
        ("D0", "D1"),
        "validate_gate_e03_v1",
        ("evidence-domain-complete", "evidence-loss-count-is-zero"),
        ("E03_EVIDENCE_DOMAIN_MISMATCH", "E03_EVIDENCE_LOSS"),
    ),
    (
        "E04",
        ("D0", "D1"),
        "validate_gate_e04_v1",
        (
            "all-seven-case-contracts-validate",
            "outer-tag-branch-failure-attempt-failure-presence-map-is-one-to-one",
            "no-unlisted-legal-tag-presence-pair",
        ),
        (
            "E04_CASE_CONTRACT_MISMATCH",
            "E04_FAILURE_PRESENCE_NONUNIQUE",
            "E04_UNLISTED_LEGAL_STATE",
        ),
    ),
    (
        "E05",
        ("D1",),
        "validate_gate_e05_v1",
        (
            "capture-ordinals-are-0-1-2",
            "each-cell-has-seven-cases",
            "each-decoded-byte-exactly-equals-broadcast-source-byte",
            "each-decoded-set-root-equals-capture-transcript-set-root",
            "each-leaf-set-root-equals-capture-leaf-set-root",
            "all-survivor-routes-observe-identical-source-and-leaf-roots",
        ),
        (
            "E05_CAPTURE_ORDINAL_MISMATCH",
            "E05_CASE_CARDINALITY_MISMATCH",
            "E05_TRANSCRIPT_BYTE_MISMATCH",
            "E05_TRANSCRIPT_ROOT_MISMATCH",
            "E05_LEAF_ROOT_MISMATCH",
            "E05_CROSS_ROUTE_IDENTITY_MISMATCH",
        ),
    ),
    (
        "E06",
        ("D0", "D1"),
        "validate_gate_e06_v1",
        (
            "all-roundtrip-probes-return-source-bytes",
            "all-repeat-probes-return-identical-bytes",
            "all-tag-failure-delete-inject-sha-and-cross-case-splices-reject",
        ),
        (
            "E06_ROUNDTRIP_NONDETERMINISTIC",
            "E06_REPEAT_NONDETERMINISTIC",
            "E06_SPLICE_ACCEPTED",
        ),
    ),
    (
        "E07",
        ("D0", "D1"),
        "validate_gate_e07_v1",
        (
            "bytes-only-api-exact",
            "no-leaf-provider-or-callback-argument",
            "no-raw-hydrator-wrapper-issuer-registry-capability-or-caller-profile",
            "authority-and-wrapper-surface-counts-are-zero",
        ),
        (
            "E07_API_SURFACE_MISMATCH",
            "E07_CALLBACK_SURFACE_PRESENT",
            "E07_AUTHORITY_SURFACE_PRESENT",
            "E07_NONZERO_SURFACE_COUNT",
        ),
    ),
    (
        "E08",
        ("D0", "D1"),
        "validate_gate_e08_v1",
        (
            "route-does-not-import-production",
            "production-does-not-import-route",
            "route-source-paths-are-absent-from-production-source-closures",
        ),
        (
            "E08_ROUTE_IMPORTS_PRODUCTION",
            "E08_PRODUCTION_IMPORTS_ROUTE",
            "E08_ROUTE_IN_PRODUCTION_SOURCE_CLOSURE",
        ),
    ),
)


_ROUTE_STATIC_REGISTRY_V1 = (
    (
        "A_FLAT",
        "experimental.v3m0.b7.a-flat",
        "experiments.v3m0_b7_schema_lab.a_flat",
        "experiments/v3m0_b7_schema_lab/a_flat.py",
        "experimental.v3m0.b7.a-flat.wire.v1",
    ),
    (
        "B_PROGRESS",
        "experimental.v3m0.b7.b-progress",
        "experiments.v3m0_b7_schema_lab.b_progress",
        "experiments/v3m0_b7_schema_lab/b_progress.py",
        "experimental.v3m0.b7.b-progress.wire.v1",
    ),
    (
        "C_UNION",
        "experimental.v3m0.b7.c-union",
        "experiments.v3m0_b7_schema_lab.c_union",
        "experiments/v3m0_b7_schema_lab/c_union.py",
        "experimental.v3m0.b7.c-union.wire.v1",
    ),
)


def _gate_contract_v1(gate_id):
    matches = [contract for contract in GATE_CONTRACTS_V1 if contract[0] == gate_id]
    if len(matches) != 1:
        raise ValueError("gate ID is not frozen")
    return matches[0]


def build_gate_outcome_v1(
    *,
    gate_id,
    phase,
    route_id,
    domain_root_sha,
    predicate_results,
):
    """Build one mechanical gate observation and its outcome wrapper."""

    _, phase_order, validator_id, predicate_ids, reason_codes = _gate_contract_v1(
        gate_id
    )
    if type(phase) is not str or phase not in phase_order:
        raise ValueError("gate phase is not frozen")
    _validate_lab_wire_semantics_v1(route_id, "route-id", None, "route_id")
    domain_sha = _require_sha256_root_v1(domain_root_sha, "gate domain")
    if (
        type(predicate_results) is not list
        or len(predicate_results) != len(predicate_ids)
        or any(type(result) is not bool for result in predicate_results)
    ):
        raise TypeError("gate predicate results differ from the frozen domain")
    bits = "".join("1" if result else "0" for result in predicate_results)
    failures = [
        reason_code
        for result, reason_code in zip(predicate_results, reason_codes)
        if not result
    ]
    observation = {
        "gate_observation_schema_version": ("experimental.v3m0.b7.gate-observation.v1"),
        "gate_id": gate_id,
        "phase": phase,
        "route_id": route_id,
        "domain_root_sha": domain_sha,
        "predicate_ids": list(predicate_ids),
        "predicate_result_bits": bits,
        "failure_reason_codes": failures,
        "observation_sha": "",
    }
    _rehash_record_field_v1(observation, "observation_sha")
    observation = validate_exact_lab_record_v1(
        "B7LabGateObservationV1",
        observation,
    )
    outcome = {
        "gate_outcome_schema_version": "experimental.v3m0.b7.gate-outcome.v1",
        "gate_id": gate_id,
        "gate_validator_id": validator_id,
        "phase": phase,
        "observation": observation,
        "passed": all(predicate_results) and not failures,
        "observation_sha": observation["observation_sha"],
        "reason_codes": failures,
        "gate_outcome_sha": "",
    }
    _rehash_record_field_v1(outcome, "gate_outcome_sha")
    return validate_exact_lab_record_v1("B7LabGateOutcomeV1", outcome)


def validate_gate_outcome_v1(
    raw_body,
    *,
    expected_domain_root_sha,
    expected_predicate_results,
):
    """Reject any gate self-report that differs from fresh expected predicates."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    expected = build_gate_outcome_v1(
        gate_id=observed["gate_id"],
        phase=observed["phase"],
        route_id=observed["observation"]["route_id"],
        domain_root_sha=expected_domain_root_sha,
        predicate_results=expected_predicate_results,
    )
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError("gate outcome differs from fresh recomputation")
    return observed


_GATE_CAPTURE_ORDINALS_V1 = (("D0", (0,)), ("D1", (0, 1, 2)))
_ROUTE_CALL_OBSERVATION_FIELDS_V1 = ("termination_kind", "raw_bytes")
_ROUTE_CALL_TERMINATION_KINDS_V1 = (
    "RETURNED_BYTES",
    "B7LabMutationRejected",
    "WRONG_EXCEPTION",
    "RETURNED_NONBYTES",
    "NOT_CALLED",
)
_LEGAL_REPLAY_OBSERVATION_FIELDS_V1 = (
    "capture_ordinal",
    "case_id",
    "route_id",
    "source_transcript_bytes",
    "encode_result",
    "decode_result",
)


def _ordered_observation_iterator_v1(raw_body, expected_count, label):
    if type(raw_body) is list:
        if len(raw_body) != expected_count:
            raise TypeError(f"{label} cardinality drifted")
        return iter(raw_body)
    try:
        iterator = iter(raw_body)
    except TypeError:
        raise TypeError(f"{label} must be an exact list or one-shot iterator") from None
    if iterator is not raw_body:
        raise TypeError(f"{label} iterable must be one-shot")
    return iterator


def _next_ordered_observation_v1(iterator, label):
    try:
        return next(iterator)
    except StopIteration:
        raise TypeError(f"{label} cardinality underflow") from None


def _require_ordered_observation_exhausted_v1(iterator, label):
    try:
        next(iterator)
    except StopIteration:
        return
    raise TypeError(f"{label} cardinality overflow")


def _require_exact_ordered_dict_v1(raw_body, fields, label):
    if type(raw_body) is not dict:
        raise TypeError(f"{label} must be an exact dict")
    if tuple(raw_body) != fields:
        raise ValueError(f"{label} fields or field order drifted")
    return raw_body


def _gate_capture_ordinals_v1(phase):
    if type(phase) is not str:
        raise TypeError("gate phase must be an exact str")
    for frozen_phase, capture_ordinals in _GATE_CAPTURE_ORDINALS_V1:
        if phase == frozen_phase:
            return capture_ordinals
    raise ValueError("gate phase is not frozen")


def _case_state_projection_v1(transcript, case_contract):
    actual = transcript.get("actual_branch_attempt")
    matched = transcript.get("matched_ablated_branch_attempt")
    if actual is not None and type(actual) is not dict:
        raise TypeError("actual branch attempt must be an exact dict or None")
    if matched is not None and type(matched) is not dict:
        raise TypeError("matched branch attempt must be an exact dict or None")
    return (
        transcript.get("terminal_tag"),
        case_contract[3],
        None if actual is None else actual.get("branch"),
        None if actual is None else actual.get("failure"),
        None if matched is None else matched.get("branch"),
        None if matched is None else matched.get("failure"),
        _transcript_presence_bits_v1(transcript),
    )


def _expected_case_state_projection_v1(case_contract):
    presence_bits = case_contract[4]
    return (
        case_contract[2],
        case_contract[3],
        "actual" if presence_bits[1] == "1" else None,
        case_contract[5],
        "matched_ablated" if presence_bits[3] == "1" else None,
        case_contract[6],
        presence_bits,
    )


def _validate_source_transcript_sets_v1(
    phase,
    raw_sets,
    *,
    expected_corpus_spec_sha=None,
    expected_environment_sha=None,
):
    capture_ordinals = _gate_capture_ordinals_v1(phase)
    if type(raw_sets) is not list or len(raw_sets) != len(capture_ordinals):
        raise TypeError("source transcript capture domain drifted")
    expected_case_ids = tuple(row[1] for row in _CASE_CONTRACTS_V1)
    validated_sets = []
    for capture_ordinal, raw_set in zip(capture_ordinals, raw_sets):
        if (
            type(raw_set) is not list
            or len(raw_set) != 7
            or any(type(raw) is not dict for raw in raw_set)
        ):
            raise TypeError(
                f"capture {capture_ordinal} source domain must contain seven dicts"
            )
        validated = [_detach_json_v1(raw) for raw in raw_set]
        if tuple(raw.get("case_id") for raw in validated) != expected_case_ids:
            raise ValueError("source transcript case order drifted")
        for checked, case_contract in zip(validated, _CASE_CONTRACTS_V1):
            if (
                expected_corpus_spec_sha is not None
                and checked.get("corpus_spec_sha") != expected_corpus_spec_sha
            ):
                raise ValueError("source transcript corpus root drifted")
            if (
                expected_environment_sha is not None
                and checked.get("environment_manifest_sha") != expected_environment_sha
            ):
                raise ValueError("source transcript environment root drifted")
            if _case_state_projection_v1(
                checked,
                case_contract,
            ) != _expected_case_state_projection_v1(case_contract):
                raise ValueError("source transcript case-contract join drifted")
            canonical_json_bytes_v1(checked)
        validated_sets.append(validated)
    return capture_ordinals, validated_sets


def _validated_d0_fixture_source_domain_v1(validated_corpus_fixture):
    fixture = _validate_corpus_fixture_v2_top_level_v1(validated_corpus_fixture)
    expected_fixture_sha = canonical_sha_v1(
        {
            name: fixture[name]
            for name in _CORPUS_FIXTURE_V2_FIELDS
            if name != "fixture_sha"
        }
    )
    if fixture["fixture_sha"] != expected_fixture_sha:
        raise ValueError("validated corpus fixture self root drifted")
    corpus_root = _require_sha256_root_v1(
        fixture["corpus_spec"].get("corpus_spec_sha"),
        "validated corpus spec",
    )
    environment_root = _require_sha256_root_v1(
        fixture["environment_manifest"].get("environment_sha"),
        "validated corpus environment",
    )
    _capture_ordinals, source_sets = _validate_source_transcript_sets_v1(
        "D0",
        [fixture["ordered_d0_transcripts"]],
        expected_corpus_spec_sha=corpus_root,
        expected_environment_sha=environment_root,
    )
    return fixture, source_sets


def _validated_gate_fixture_source_domain_v1(
    phase,
    validated_corpus_fixture,
    ordered_source_transcript_sets,
):
    if phase == "D0":
        if ordered_source_transcript_sets is not None:
            raise ValueError("D0 gate source domain must come from the fixture")
        return _validated_d0_fixture_source_domain_v1(validated_corpus_fixture)
    if phase != "D1":
        raise ValueError("gate phase is not frozen")
    fixture = _validate_corpus_fixture_v2_top_level_v1(validated_corpus_fixture)
    if fixture["fixture_sha"] != canonical_sha_v1(
        {
            name: fixture[name]
            for name in _CORPUS_FIXTURE_V2_FIELDS
            if name != "fixture_sha"
        }
    ):
        raise ValueError("validated corpus fixture self root drifted")
    corpus_root = _require_sha256_root_v1(
        fixture["corpus_spec"].get("corpus_spec_sha"),
        "validated corpus spec",
    )
    environment_root = _require_sha256_root_v1(
        fixture["environment_manifest"].get("environment_sha"),
        "validated corpus environment",
    )
    _capture_ordinals, source_sets = _validate_source_transcript_sets_v1(
        "D1",
        ordered_source_transcript_sets,
        expected_corpus_spec_sha=corpus_root,
        expected_environment_sha=environment_root,
    )
    return fixture, source_sets


def _validate_route_call_observation_v1(raw_body, label):
    call = _require_exact_ordered_dict_v1(
        raw_body,
        _ROUTE_CALL_OBSERVATION_FIELDS_V1,
        label,
    )
    kind = call["termination_kind"]
    raw_bytes = call["raw_bytes"]
    if type(kind) is not str or kind not in _ROUTE_CALL_TERMINATION_KINDS_V1:
        raise ValueError(f"{label} termination kind is not frozen")
    if kind == "RETURNED_BYTES":
        if type(raw_bytes) is not bytes:
            raise TypeError(f"{label} returned bytes must be exact bytes")
    elif raw_bytes is not None:
        raise ValueError(f"{label} non-return termination must not carry bytes")
    return call


def _raw_bytes_sha_or_none_v1(raw_bytes):
    if raw_bytes is None:
        return None
    if type(raw_bytes) is not bytes:
        raise TypeError("raw byte root input must be exact bytes or None")
    return _pure_core.hashlib.sha256(raw_bytes).hexdigest()


def _canonical_json_bytes_observation_v1(raw_bytes):
    if type(raw_bytes) is not bytes:
        return False
    try:
        decoded = strict_json_loads_v1(raw_bytes)
        return canonical_json_bytes_v1(decoded) == raw_bytes
    except (TypeError, ValueError, UnicodeDecodeError):
        return False


def _normalize_route_call_observation_v1(call):
    raw_bytes = call["raw_bytes"]
    return {
        "termination_kind": call["termination_kind"],
        "raw_sha256": _raw_bytes_sha_or_none_v1(raw_bytes),
        "is_canonical_json_bytes": _canonical_json_bytes_observation_v1(raw_bytes),
    }


def _validate_legal_replay_domain_v1(
    *,
    phase,
    route_id,
    ordered_source_transcript_sets,
    ordered_legal_replays,
):
    _validate_lab_wire_semantics_v1(route_id, "route-id", None, "route_id")
    capture_ordinals, source_sets = _validate_source_transcript_sets_v1(
        phase,
        ordered_source_transcript_sets,
    )
    expected_count = 7 * len(capture_ordinals)
    if (
        type(ordered_legal_replays) is not list
        or len(ordered_legal_replays) != expected_count
    ):
        raise TypeError("legal replay observation cardinality drifted")

    normalized = []
    accepted_count = 0
    cursor = 0
    for capture_ordinal, source_set in zip(capture_ordinals, source_sets):
        for case_ordinal, source in enumerate(source_set):
            row = _require_exact_ordered_dict_v1(
                ordered_legal_replays[cursor],
                _LEGAL_REPLAY_OBSERVATION_FIELDS_V1,
                "legal replay observation",
            )
            cursor += 1
            if (
                type(row["capture_ordinal"]) is not int
                or row["capture_ordinal"] != capture_ordinal
                or type(row["case_id"]) is not str
                or row["case_id"] != source["case_id"]
                or row["route_id"] != route_id
            ):
                raise ValueError("legal replay capture/case/route order drifted")
            source_bytes = row["source_transcript_bytes"]
            if type(
                source_bytes
            ) is not bytes or source_bytes != canonical_json_bytes_v1(source):
                raise ValueError("legal replay source body differs from frozen capture")
            encode = _validate_route_call_observation_v1(
                row["encode_result"],
                "legal encode result",
            )
            decode = _validate_route_call_observation_v1(
                row["decode_result"],
                "legal decode result",
            )
            if (
                encode["termination_kind"] != "RETURNED_BYTES"
                and decode["termination_kind"] != "NOT_CALLED"
            ):
                raise ValueError("legal decoder ran without encoded bytes")
            encoded_canonical = encode[
                "termination_kind"
            ] == "RETURNED_BYTES" and _canonical_json_bytes_observation_v1(
                encode["raw_bytes"]
            )
            decoded_equal = (
                decode["termination_kind"] == "RETURNED_BYTES"
                and decode["raw_bytes"] == source_bytes
            )
            if encoded_canonical and decoded_equal:
                accepted_count += 1
            normalized.append(
                {
                    "capture_ordinal": capture_ordinal,
                    "case_ordinal": case_ordinal,
                    "case_id": source["case_id"],
                    "route_id": route_id,
                    "source_transcript_raw_sha256": _raw_bytes_sha_or_none_v1(
                        source_bytes
                    ),
                    "encode_result": _normalize_route_call_observation_v1(encode),
                    "decode_result": _normalize_route_call_observation_v1(decode),
                    "decoded_equals_source": decoded_equal,
                }
            )
    predicates = (
        len(normalized) == expected_count,
        all(
            row["encode_result"]["termination_kind"] == "RETURNED_BYTES"
            and row["encode_result"]["is_canonical_json_bytes"]
            for row in normalized
        ),
        all(row["decoded_equals_source"] for row in normalized),
    )
    return {
        "domain_root_sha": canonical_sha_v1(normalized),
        "predicate_results": predicates,
        "accepted_count": accepted_count,
        "normalized": normalized,
        "validated_source_sets": source_sets,
    }


def build_gate_e01_v1(
    *,
    phase,
    route_id,
    validated_corpus_fixture,
    ordered_legal_replays,
    ordered_source_transcript_sets=None,
):
    """Build E01 only from the complete ordered legal replay byte domain."""

    _fixture, source_sets = _validated_gate_fixture_source_domain_v1(
        phase,
        validated_corpus_fixture,
        ordered_source_transcript_sets,
    )
    domain = _validate_legal_replay_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=ordered_legal_replays,
    )
    return build_gate_outcome_v1(
        gate_id="E01",
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e01_v1(
    raw_body,
    *,
    validated_corpus_fixture,
    ordered_legal_replays,
    ordered_source_transcript_sets=None,
):
    """Reject an E01 report unless its full byte domain recomputes exactly."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E01":
        raise ValueError("E01 validator received another gate")
    route_id = observed["observation"]["route_id"]
    phase = observed["phase"]
    _fixture, source_sets = _validated_gate_fixture_source_domain_v1(
        phase,
        validated_corpus_fixture,
        ordered_source_transcript_sets,
    )
    domain = _validate_legal_replay_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=ordered_legal_replays,
    )
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


_MUTATION_PROBE_OBSERVATION_FIELDS_V1 = (
    "capture_ordinal",
    "mutation_ordinal",
    "mutation_id",
    "mutation_sha",
    "route_id",
    "materialized_transcript_bytes",
    "upstream_transcript_count",
    "first_encode_result",
    "first_decode_result",
    "second_encode_result",
    "second_decode_result",
)
_E06_SPLICE_CLASSES_V1 = (
    "TERMINAL_TAG",
    "OUTER_BRANCH_FAILURE_SPLICE",
    "DELETE_SUCCESSFUL_PREFIX_BODY",
    "INJECT_POST_FAILURE_BODY",
    "NESTED_BODY_SHA_SPLICE",
)


def _require_two_stage_route_calls_v1(row, prefix, *, required):
    encode = _validate_route_call_observation_v1(
        row[f"{prefix}_encode_result"],
        f"mutation {prefix} encode result",
    )
    decode = _validate_route_call_observation_v1(
        row[f"{prefix}_decode_result"],
        f"mutation {prefix} decode result",
    )
    if required is False:
        if (
            encode["termination_kind"] != "NOT_CALLED"
            or decode["termination_kind"] != "NOT_CALLED"
        ):
            raise ValueError(f"mutation {prefix} route stage was unexpectedly called")
        return encode, decode
    if required is True and encode["termination_kind"] == "NOT_CALLED":
        raise ValueError(f"mutation {prefix} encoder was not called")
    if encode["termination_kind"] == "RETURNED_BYTES":
        if decode["termination_kind"] == "NOT_CALLED":
            raise ValueError(f"mutation {prefix} decoder was not called")
    elif decode["termination_kind"] != "NOT_CALLED":
        raise ValueError(f"mutation {prefix} decoder ran without encoded bytes")
    return encode, decode


def _mutation_final_accept_v1(encode, decode):
    return (
        encode["termination_kind"] == "RETURNED_BYTES"
        and decode["termination_kind"] == "RETURNED_BYTES"
    )


def _mutation_exact_rejection_v1(encode, decode):
    return encode["termination_kind"] == "B7LabMutationRejected" or (
        encode["termination_kind"] == "RETURNED_BYTES"
        and decode["termination_kind"] == "B7LabMutationRejected"
    )


def _validate_mutation_probe_domain_v1(
    *,
    phase,
    route_id,
    validated_corpus_fixture,
    ordered_mutation_probes,
    ordered_source_transcript_sets=None,
):
    """Validate every capture-by-mutation two-stage route observation."""

    _validate_lab_wire_semantics_v1(route_id, "route-id", None, "route_id")
    capture_ordinals = _gate_capture_ordinals_v1(phase)
    d0_fixture, fixture_source_sets = _validated_d0_fixture_source_domain_v1(
        validated_corpus_fixture
    )
    fixture_source_set = fixture_source_sets[0]
    if phase == "D1" and ordered_source_transcript_sets is None:
        # Compatibility for the standalone historical domain probe.  The
        # authoritative D1 route builder always supplies all three captures.
        fixture = d0_fixture
        source_sets = [fixture_source_set for _capture in capture_ordinals]
    else:
        fixture, source_sets = _validated_gate_fixture_source_domain_v1(
            phase,
            validated_corpus_fixture,
            ordered_source_transcript_sets,
        )
    universe = fixture.get("mutation_universe")
    if type(universe) is not dict:
        raise TypeError("validated corpus mutation universe must be an exact dict")
    raw_mutations = universe.get("ordered_mutations")
    mutation_count = universe.get("mutation_count")
    if type(raw_mutations) is not list or type(mutation_count) is not int:
        raise TypeError("validated mutation universe domain is not exact")
    mutations = [validate_mutation_v1(raw) for raw in raw_mutations]
    expected_mutations = generate_ordered_mutations_v1(fixture_source_set)
    if mutation_count != len(mutations) or canonical_json_bytes_v1(
        mutations
    ) != canonical_json_bytes_v1(expected_mutations):
        raise ValueError("validated mutation universe differs from its source domain")
    if [mutation["mutation_ordinal"] for mutation in mutations] != list(
        range(mutation_count)
    ):
        raise ValueError("validated mutation universe order drifted")
    universe_sha = _require_sha256_root_v1(
        universe.get("mutation_universe_sha"),
        "mutation universe",
    )
    expected_count = mutation_count * len(capture_ordinals)
    observation_iterator = _ordered_observation_iterator_v1(
        ordered_mutation_probes,
        expected_count,
        "mutation probe observation",
    )

    normalized = []
    mutation_accept_count = 0
    invalid_rejection_surface_count = 0
    upstream_invalid_probe_count = 0
    mutation_must_reject_count = 0
    upstream_invalid_transcript_count = 0
    all_upstream_route_entry_counts_zero = True
    for capture_ordinal, source_set in zip(capture_ordinals, source_sets):
        sources_by_case = {source["case_id"]: source for source in source_set}
        if len(sources_by_case) != 7 or "success" not in sources_by_case:
            raise ValueError("mutation source case domain drifted")
        success = sources_by_case["success"]
        snapshots = {
            case_id: discover_record_self_hashes_v1(source)
            for case_id, source in sources_by_case.items()
        }
        success_snapshot = snapshots["success"]
        effective_snapshots = {
            case_id: snapshot
            + tuple(item for item in success_snapshot if item not in snapshot)
            for case_id, snapshot in snapshots.items()
        }
        for mutation in mutations:
            row = _require_exact_ordered_dict_v1(
                _next_ordered_observation_v1(
                    observation_iterator,
                    "mutation probe observation",
                ),
                _MUTATION_PROBE_OBSERVATION_FIELDS_V1,
                "mutation probe observation",
            )
            if (
                type(row["capture_ordinal"]) is not int
                or row["capture_ordinal"] != capture_ordinal
                or type(row["mutation_ordinal"]) is not int
                or row["mutation_ordinal"] != mutation["mutation_ordinal"]
                or row["mutation_id"] != mutation["mutation_id"]
                or row["mutation_sha"] != mutation["mutation_sha"]
                or row["route_id"] != route_id
            ):
                raise ValueError("mutation probe capture/mutation/route order drifted")
            if (
                type(row["upstream_transcript_count"]) is not int
                or row["upstream_transcript_count"] < 0
            ):
                raise TypeError("mutation upstream transcript count is not exact")

            probe_kind = mutation["probe_kind"]
            if probe_kind == "MUTATION_MUST_REJECT":
                mutation_must_reject_count += 1
            if probe_kind == "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT":
                expected_body = None
                expected_upstream_count = None
                require_first = None
                require_second = False
            else:
                base_case_id = mutation["base_case_id"]
                if base_case_id not in sources_by_case:
                    raise ValueError("mutation base case is outside the corpus")
                base = sources_by_case[base_case_id]
                if probe_kind in ("ROUNDTRIP_MUST_EQUAL", "REPEAT_MUST_EQUAL"):
                    materialized = base
                else:
                    materialized = _apply_validated_transcript_mutation_v1(
                        base,
                        mutation,
                        success,
                        effective_snapshots[base_case_id],
                    )
                expected_body = canonical_json_bytes_v1(materialized)
                expected_upstream_count = 1
                require_first = True
                require_second = probe_kind == "REPEAT_MUST_EQUAL"
            if (
                row["materialized_transcript_bytes"] != expected_body
                or type(row["materialized_transcript_bytes"]) is not type(expected_body)
                or (
                    expected_upstream_count is not None
                    and row["upstream_transcript_count"] != expected_upstream_count
                )
            ):
                raise ValueError("mutation probe materialization drifted")

            first_encode, first_decode = _require_two_stage_route_calls_v1(
                row,
                "first",
                required=require_first,
            )
            second_encode, second_decode = _require_two_stage_route_calls_v1(
                row,
                "second",
                required=require_second,
            )
            final_accept = _mutation_final_accept_v1(first_encode, first_decode)
            exact_rejection = _mutation_exact_rejection_v1(
                first_encode,
                first_decode,
            )
            wrong_surface_count = sum(
                call["termination_kind"] in ("WRONG_EXCEPTION", "RETURNED_NONBYTES")
                for call in (
                    first_encode,
                    first_decode,
                    second_encode,
                    second_decode,
                )
            )
            if probe_kind == "MUTATION_MUST_REJECT" and final_accept:
                mutation_accept_count += 1
            invalid_rejection_surface_count += wrong_surface_count
            if probe_kind == "UPSTREAM_MUST_PRODUCE_ZERO_TRANSCRIPT":
                upstream_invalid_probe_count += 1
                upstream_invalid_transcript_count += row["upstream_transcript_count"]
                route_not_entered = all(
                    call["termination_kind"] == "NOT_CALLED"
                    for call in (
                        first_encode,
                        first_decode,
                        second_encode,
                        second_decode,
                    )
                )
                all_upstream_route_entry_counts_zero = (
                    all_upstream_route_entry_counts_zero and route_not_entered
                )
            roundtrip_equal = (
                probe_kind == "ROUNDTRIP_MUST_EQUAL"
                and final_accept
                and first_decode["raw_bytes"] == expected_body
            )
            repeat_equal = (
                probe_kind == "REPEAT_MUST_EQUAL"
                and final_accept
                and _mutation_final_accept_v1(second_encode, second_decode)
                and first_encode["raw_bytes"] == second_encode["raw_bytes"]
                and first_decode["raw_bytes"] == expected_body
                and second_decode["raw_bytes"] == expected_body
            )
            normalized.append(
                {
                    "capture_ordinal": capture_ordinal,
                    "mutation_ordinal": mutation["mutation_ordinal"],
                    "mutation_id": mutation["mutation_id"],
                    "mutation_sha": mutation["mutation_sha"],
                    "base_case_id": mutation["base_case_id"],
                    "probe_kind": probe_kind,
                    "mutation_class": mutation["mutation_class"],
                    "operation": mutation["operation"],
                    "route_id": route_id,
                    "materialized_transcript_raw_sha256": (
                        _raw_bytes_sha_or_none_v1(expected_body)
                    ),
                    "upstream_transcript_count": row["upstream_transcript_count"],
                    "first_encode_result": _normalize_route_call_observation_v1(
                        first_encode
                    ),
                    "first_decode_result": _normalize_route_call_observation_v1(
                        first_decode
                    ),
                    "second_encode_result": _normalize_route_call_observation_v1(
                        second_encode
                    ),
                    "second_decode_result": _normalize_route_call_observation_v1(
                        second_decode
                    ),
                    "final_accept": final_accept,
                    "exact_rejection": exact_rejection,
                    "wrong_exception_or_nonbytes_count": wrong_surface_count,
                    "roundtrip_equals_source": roundtrip_equal,
                    "repeat_calls_equal_source": repeat_equal,
                }
            )

    _require_ordered_observation_exhausted_v1(
        observation_iterator,
        "mutation probe observation",
    )

    domain_root = canonical_sha_v1(
        {
            "mutation_universe_sha": universe_sha,
            "ordered_probe_outcomes": normalized,
        }
    )
    return {
        "domain_root_sha": domain_root,
        "predicate_results": (
            len(normalized) == expected_count,
            mutation_accept_count == 0,
            invalid_rejection_surface_count == 0,
        ),
        "total_observation_count": len(normalized),
        "mutation_probe_count": mutation_must_reject_count,
        "mutation_must_reject_count": mutation_must_reject_count,
        "mutation_must_reject_probe_count": mutation_must_reject_count,
        "mutation_accept_count": mutation_accept_count,
        "invalid_rejection_surface_count": invalid_rejection_surface_count,
        "upstream_invalid_probe_count": upstream_invalid_probe_count,
        "upstream_invalid_transcript_count": upstream_invalid_transcript_count,
        "all_upstream_route_entry_counts_zero": (all_upstream_route_entry_counts_zero),
        "normalized": normalized,
    }


def build_gate_e02_v1(
    *,
    phase,
    route_id,
    validated_corpus_fixture,
    ordered_mutation_probes,
):
    """Build E02 from the exact dynamic mutation universe and outcomes."""

    domain = _validate_mutation_probe_domain_v1(
        phase=phase,
        route_id=route_id,
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_mutation_probes=ordered_mutation_probes,
    )
    return build_gate_outcome_v1(
        gate_id="E02",
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e02_v1(
    raw_body,
    *,
    validated_corpus_fixture,
    ordered_mutation_probes,
):
    """Reject E02 unless every dynamic mutation outcome recomputes."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E02":
        raise ValueError("E02 validator received another gate")
    domain = _validate_mutation_probe_domain_v1(
        phase=observed["phase"],
        route_id=observed["observation"]["route_id"],
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_mutation_probes=ordered_mutation_probes,
    )
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


def _validate_e06_domain_v1(mutation_domain):
    if type(mutation_domain) is not dict:
        raise TypeError("E06 mutation domain must be an exact dict")
    selected = [
        row
        for row in mutation_domain["normalized"]
        if row["probe_kind"] in ("ROUNDTRIP_MUST_EQUAL", "REPEAT_MUST_EQUAL")
        or row["mutation_class"] in _E06_SPLICE_CLASSES_V1
    ]
    roundtrips = [
        row for row in selected if row["probe_kind"] == "ROUNDTRIP_MUST_EQUAL"
    ]
    repeats = [row for row in selected if row["probe_kind"] == "REPEAT_MUST_EQUAL"]
    splices = [
        row for row in selected if row["mutation_class"] in _E06_SPLICE_CLASSES_V1
    ]
    # The subset cardinalities derive from the normalized dynamic domain; no
    # historical mutation-count literal participates in E06.
    predicates = (
        bool(roundtrips) and all(row["roundtrip_equals_source"] for row in roundtrips),
        bool(repeats) and all(row["repeat_calls_equal_source"] for row in repeats),
        bool(splices) and all(row["exact_rejection"] for row in splices),
    )
    return {
        "domain_root_sha": canonical_sha_v1(selected),
        "predicate_results": predicates,
        "normalized": selected,
    }


def build_gate_e06_v1(
    *,
    phase,
    route_id,
    validated_corpus_fixture,
    ordered_mutation_probes,
):
    """Build E06 from roundtrip, repeat, and M02--M07 probe subsets."""

    mutation = _validate_mutation_probe_domain_v1(
        phase=phase,
        route_id=route_id,
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_mutation_probes=ordered_mutation_probes,
    )
    domain = _validate_e06_domain_v1(mutation)
    return build_gate_outcome_v1(
        gate_id="E06",
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e06_v1(
    raw_body,
    *,
    validated_corpus_fixture,
    ordered_mutation_probes,
):
    """Reject E06 unless its exact dynamic subsets recompute."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E06":
        raise ValueError("E06 validator received another gate")
    mutation = _validate_mutation_probe_domain_v1(
        phase=observed["phase"],
        route_id=observed["observation"]["route_id"],
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_mutation_probes=ordered_mutation_probes,
    )
    domain = _validate_e06_domain_v1(mutation)
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


def _canonical_value_sha_or_none_v1(value):
    if value is None:
        return None
    return _pure_core.hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()


def _derive_e03_domain_from_legal_v1(*, legal_domain, ordered_legal_replays):
    if type(legal_domain) is not dict or type(ordered_legal_replays) is not list:
        raise TypeError("E03 requires one validated legal domain and replay list")
    evidence_entries = []
    evidence_loss_count = 0
    source_cursor = 0
    for source_set in legal_domain["validated_source_sets"]:
        for source in source_set:
            replay = ordered_legal_replays[source_cursor]
            source_cursor += 1
            decode = replay["decode_result"]
            decoded = {}
            if decode["termination_kind"] == "RETURNED_BYTES":
                try:
                    parsed = strict_json_loads_v1(decode["raw_bytes"])
                    if type(parsed) is dict:
                        decoded = parsed
                except (TypeError, ValueError, UnicodeDecodeError):
                    decoded = {}
            for pointer in _EVIDENCE_POINTER_ORDER_V1:
                source_present, source_value = _optional_pointer_value_v1(
                    source,
                    pointer,
                )
                if not source_present or source_value is None:
                    continue
                decoded_present, decoded_value = _optional_pointer_value_v1(
                    decoded,
                    pointer,
                )
                equal = (
                    decoded_present
                    and decoded_value is not None
                    and canonical_json_bytes_v1(decoded_value)
                    == canonical_json_bytes_v1(source_value)
                )
                if not equal:
                    evidence_loss_count += 1
                evidence_entries.append(
                    {
                        "capture_ordinal": replay["capture_ordinal"],
                        "case_id": replay["case_id"],
                        "json_pointer": pointer,
                        "source_value_sha256": _canonical_value_sha_or_none_v1(
                            source_value
                        ),
                        "decoded_pointer_resolved": decoded_present,
                        "decoded_value_sha256": _canonical_value_sha_or_none_v1(
                            decoded_value if decoded_present else None
                        ),
                        "canonical_values_equal": equal,
                    }
                )
    return {
        "domain_root_sha": canonical_sha_v1(evidence_entries),
        "predicate_results": (True, evidence_loss_count == 0),
        "evidence_loss_count": evidence_loss_count,
        "normalized": evidence_entries,
    }


def _validate_e03_domain_v1(
    *,
    phase,
    route_id,
    ordered_source_transcript_sets,
    ordered_legal_replays,
):
    legal = _validate_legal_replay_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=ordered_source_transcript_sets,
        ordered_legal_replays=ordered_legal_replays,
    )
    return _derive_e03_domain_from_legal_v1(
        legal_domain=legal,
        ordered_legal_replays=ordered_legal_replays,
    )


def build_gate_e03_v1(
    *,
    phase,
    route_id,
    validated_corpus_fixture,
    ordered_legal_replays,
    ordered_source_transcript_sets=None,
):
    """Build E03 from every non-null frozen evidence-pointer pair."""

    _fixture, source_sets = _validated_gate_fixture_source_domain_v1(
        phase,
        validated_corpus_fixture,
        ordered_source_transcript_sets,
    )
    domain = _validate_e03_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=ordered_legal_replays,
    )
    return build_gate_outcome_v1(
        gate_id="E03",
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e03_v1(
    raw_body,
    *,
    validated_corpus_fixture,
    ordered_legal_replays,
    ordered_source_transcript_sets=None,
):
    """Reject E03 unless its complete evidence byte-pair domain recomputes."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E03":
        raise ValueError("E03 validator received another gate")
    route_id = observed["observation"]["route_id"]
    phase = observed["phase"]
    _fixture, source_sets = _validated_gate_fixture_source_domain_v1(
        phase,
        validated_corpus_fixture,
        ordered_source_transcript_sets,
    )
    domain = _validate_e03_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=ordered_legal_replays,
    )
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


_INVALID_PRESENCE_OBSERVATION_FIELDS_V1 = (
    "capture_ordinal",
    "terminal_tag",
    "bit_integer",
    "presence_bits",
    "route_id",
    "candidate_transcript_bytes",
    "encode_result",
)


def _transcript_presence_bits_v1(transcript):
    actual = transcript.get("actual_branch_attempt")
    matched = transcript.get("matched_ablated_branch_attempt")
    return "".join(
        (
            _presence_bit_v1(transcript.get("shell_outcome")),
            _presence_bit_v1(actual),
            _presence_bit_v1(
                None if type(actual) is not dict else actual.get("response_values")
            ),
            _presence_bit_v1(matched),
            _presence_bit_v1(
                None if type(matched) is not dict else matched.get("response_values")
            ),
            _presence_bit_v1(
                None if type(actual) is not dict else actual.get("bridge_audit")
            ),
            _presence_bit_v1(
                None if type(matched) is not dict else matched.get("bridge_audit")
            ),
            _presence_bit_v1(transcript.get("actual_completed_response")),
            _presence_bit_v1(transcript.get("matched_ablated_completed_response")),
        )
    )


def _validate_invalid_presence_domain_v1(
    *,
    phase,
    route_id,
    ordered_source_transcript_sets,
    ordered_invalid_presence_probes,
):
    _validate_lab_wire_semantics_v1(route_id, "route-id", None, "route_id")
    capture_ordinals, source_sets = _validate_source_transcript_sets_v1(
        phase,
        ordered_source_transcript_sets,
    )
    expected_count = 1393 * len(capture_ordinals)
    observation_iterator = _ordered_observation_iterator_v1(
        ordered_invalid_presence_probes,
        expected_count,
        "invalid-presence observation",
    )

    normalized = []
    canonical_accept_count = 0
    half_pair_state_count = 0
    exact_rejections = True
    for capture_ordinal, source_set in zip(capture_ordinals, source_sets):
        candidates = iter_constructible_invalid_presence_candidates_v1(source_set[6])
        for candidate in candidates:
            row = _require_exact_ordered_dict_v1(
                _next_ordered_observation_v1(
                    observation_iterator,
                    "invalid-presence observation",
                ),
                _INVALID_PRESENCE_OBSERVATION_FIELDS_V1,
                "invalid-presence observation",
            )
            expected_bytes = canonical_json_bytes_v1(candidate["transcript"])
            if (
                type(row["capture_ordinal"]) is not int
                or row["capture_ordinal"] != capture_ordinal
                or row["terminal_tag"] != candidate["terminal_tag"]
                or type(row["bit_integer"]) is not int
                or row["bit_integer"] != candidate["bit_integer"]
                or row["presence_bits"] != candidate["presence_bits"]
                or row["route_id"] != route_id
                or type(row["candidate_transcript_bytes"]) is not bytes
                or row["candidate_transcript_bytes"] != expected_bytes
            ):
                raise ValueError(
                    "invalid-presence capture/tag/bit/route/body order drifted"
                )
            encode = _validate_route_call_observation_v1(
                row["encode_result"],
                "invalid-presence encode result",
            )
            if encode["termination_kind"] == "NOT_CALLED":
                raise ValueError("constructible invalid-presence route was not called")
            exact_rejection = encode["termination_kind"] == "B7LabMutationRejected"
            exact_rejections = exact_rejections and exact_rejection
            canonical_accept = encode[
                "termination_kind"
            ] == "RETURNED_BYTES" and _canonical_json_bytes_observation_v1(
                encode["raw_bytes"]
            )
            if canonical_accept:
                canonical_accept_count += 1
            if canonical_accept and candidate["half_pair"]:
                half_pair_state_count += 1
            normalized.append(
                {
                    "capture_ordinal": capture_ordinal,
                    "terminal_tag": candidate["terminal_tag"],
                    "bit_integer": candidate["bit_integer"],
                    "presence_bits": candidate["presence_bits"],
                    "half_pair": candidate["half_pair"],
                    "route_id": route_id,
                    "candidate_transcript_raw_sha256": (
                        _raw_bytes_sha_or_none_v1(expected_bytes)
                    ),
                    "encode_result": _normalize_route_call_observation_v1(encode),
                }
            )
    _require_ordered_observation_exhausted_v1(
        observation_iterator,
        "invalid-presence observation",
    )
    return {
        "normalized": normalized,
        "canonical_accept_count": canonical_accept_count,
        "half_pair_state_count": half_pair_state_count,
        "all_exact_rejections": exact_rejections,
    }


def _derive_e04_domain_from_legal_and_invalid_v1(
    *,
    phase,
    legal_domain,
    ordered_legal_replays,
    invalid_domain,
):
    if (
        type(legal_domain) is not dict
        or type(ordered_legal_replays) is not list
        or type(invalid_domain) is not dict
    ):
        raise TypeError("E04 requires validated legal and invalid-presence domains")
    expected_states = {
        _expected_case_state_projection_v1(row) for row in _CASE_CONTRACTS_V1
    }
    case_observations = []
    observed_states = []
    all_case_contracts_validate = True
    for row, case_contract in zip(
        ordered_legal_replays,
        _CASE_CONTRACTS_V1 * len(_gate_capture_ordinals_v1(phase)),
    ):
        decode = row["decode_result"]
        checked = None
        if decode["termination_kind"] == "RETURNED_BYTES":
            try:
                decoded = strict_json_loads_v1(decode["raw_bytes"])
                checked = validate_case_contract_v1(decoded)
                if checked["case_id"] != row["case_id"]:
                    raise ValueError("decoded case ID drifted")
            except (TypeError, ValueError, UnicodeDecodeError):
                checked = None
        if checked is None:
            all_case_contracts_validate = False
            state = None
        else:
            state = _case_state_projection_v1(checked, case_contract)
            observed_states.append(state)
        case_observations.append(
            {
                "capture_ordinal": row["capture_ordinal"],
                "case_id": row["case_id"],
                "validated_case_contract": checked is not None,
                "terminal_tag": None if state is None else state[0],
                "injected_failure_stage": None if state is None else state[1],
                "actual_branch": None if state is None else state[2],
                "actual_attempt_failure": None if state is None else state[3],
                "matched_ablated_branch": None if state is None else state[4],
                "matched_ablated_attempt_failure": (
                    None if state is None else state[5]
                ),
                "presence_bits": None if state is None else state[6],
                "decoded_transcript_raw_sha256": _raw_bytes_sha_or_none_v1(
                    decode["raw_bytes"]
                ),
            }
        )
    capture_count = len(_gate_capture_ordinals_v1(phase))
    one_to_one = all_case_contracts_validate and all(
        len(set(observed_states[offset : offset + 7])) == 7
        for offset in range(0, 7 * capture_count, 7)
    )
    listed_legal_states = all_case_contracts_validate and all(
        state in expected_states for state in observed_states
    )
    predicates = (
        all_case_contracts_validate,
        one_to_one,
        listed_legal_states and invalid_domain["all_exact_rejections"],
    )
    return {
        "domain_root_sha": canonical_sha_v1(
            {
                "ordered_case_contract_observations": case_observations,
                "ordered_invalid_presence_observations": invalid_domain["normalized"],
            }
        ),
        "predicate_results": predicates,
        "canonical_accept_count": invalid_domain["canonical_accept_count"],
        "half_pair_state_count": invalid_domain["half_pair_state_count"],
    }


def _validate_e04_domain_v1(
    *,
    phase,
    route_id,
    ordered_source_transcript_sets,
    ordered_legal_replays,
    ordered_invalid_presence_probes,
):
    legal = _validate_legal_replay_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=ordered_source_transcript_sets,
        ordered_legal_replays=ordered_legal_replays,
    )
    invalid = _validate_invalid_presence_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=ordered_source_transcript_sets,
        ordered_invalid_presence_probes=ordered_invalid_presence_probes,
    )
    return _derive_e04_domain_from_legal_and_invalid_v1(
        phase=phase,
        legal_domain=legal,
        ordered_legal_replays=ordered_legal_replays,
        invalid_domain=invalid,
    )


def build_gate_e04_v1(
    *,
    phase,
    route_id,
    validated_corpus_fixture,
    ordered_legal_replays,
    ordered_invalid_presence_probes,
    ordered_source_transcript_sets=None,
):
    """Build E04 from every legal state and all 1,393 invalid pairs."""

    _fixture, source_sets = _validated_gate_fixture_source_domain_v1(
        phase,
        validated_corpus_fixture,
        ordered_source_transcript_sets,
    )
    domain = _validate_e04_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=ordered_legal_replays,
        ordered_invalid_presence_probes=ordered_invalid_presence_probes,
    )
    return build_gate_outcome_v1(
        gate_id="E04",
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e04_v1(
    raw_body,
    *,
    validated_corpus_fixture,
    ordered_legal_replays,
    ordered_invalid_presence_probes,
    ordered_source_transcript_sets=None,
):
    """Reject E04 unless both legal and invalid-state domains recompute."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E04":
        raise ValueError("E04 validator received another gate")
    route_id = observed["observation"]["route_id"]
    phase = observed["phase"]
    _fixture, source_sets = _validated_gate_fixture_source_domain_v1(
        phase,
        validated_corpus_fixture,
        ordered_source_transcript_sets,
    )
    domain = _validate_e04_domain_v1(
        phase=phase,
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=ordered_legal_replays,
        ordered_invalid_presence_probes=ordered_invalid_presence_probes,
    )
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


def _route_static_registry_entry_v1(route_id):
    if type(route_id) is not str:
        raise TypeError("route ID must be an exact str")
    for entry in _ROUTE_STATIC_REGISTRY_V1:
        if entry[0] == route_id:
            return entry
    raise ValueError("route ID is not frozen")


def _require_git_blob_descriptor_v1(raw_blob, field):
    if type(raw_blob) is not tuple or len(raw_blob) != 4:
        raise TypeError(f"{field} must be an exact four-item tuple")
    commit_sha, path, mode, source_bytes = raw_blob
    if (
        type(commit_sha) is not str
        or len(commit_sha) != 40
        or any(character not in "0123456789abcdef" for character in commit_sha)
    ):
        raise TypeError(f"{field} commit must be an exact lowercase Git SHA-1")
    _require_repo_relative_posix_path_v1(path, f"{field} path")
    if type(mode) is not str:
        raise TypeError(f"{field} mode must be an exact str")
    if type(source_bytes) is not bytes:
        raise TypeError(f"{field} source must be exact bytes")
    return raw_blob


_ROUTE_PUBLIC_EXPORTS_V1 = (
    "ROUTE_ID",
    "WIRE_SCHEMA_ID",
    "encode_normalized_transcript",
    "verify_and_decode_route_wire",
)
_ROUTE_ALLOWED_IMPORTS_V1 = (
    "__future__",
    "base64",
    "copy",
    "dataclasses",
    "enum",
    "hashlib",
    "json",
    "typing",
    ".common",
    "experiments.v3m0_b7_schema_lab.common",
)
_ROUTE_FORBIDDEN_REACHABLE_NAMES_V1 = (
    "__builtins__",
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "print",
)
_ROUTE_FORBIDDEN_ATTRIBUTE_NAMES_V1 = (
    "ProcessPoolExecutor",
    "exec",
    "fork",
    "forkpty",
    "kill",
    "killpg",
    "popen",
    "posix_spawn",
    "setsid",
    "pthread_kill",
    "raise_signal",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "system",
)
_ROUTE_FORBIDDEN_ATTRIBUTE_PREFIXES_V1 = (
    "exec",
    "fork",
    "kill",
    "popen",
    "posix_spawn",
    "setsid",
    "spawn",
    "system",
)
_ROUTE_FORBIDDEN_IDENTIFIER_TOKENS_V1 = (
    "authority",
    "capability",
    "issuer",
    "verified",
)
_ROUTE_PRODUCTION_ROOTS_V1 = ("rulespace_v3", "rulespace_gpu")


def _parse_python_blob_v1(source_bytes, path):
    if type(source_bytes) is not bytes:
        raise TypeError(f"{path} source must be exact bytes")
    if source_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{path} source must not contain a UTF-8 BOM")
    source_text = source_bytes.decode("utf-8", errors="strict")
    return _ast.parse(
        source_text,
        filename=path,
        mode="exec",
        type_comments=True,
    )


def _source_location_v1(node):
    return [
        type(node).__name__,
        node.lineno,
        node.col_offset,
        node.end_lineno or 0,
        node.end_col_offset or 0,
    ]


def _normalized_import_module_v1(node):
    if isinstance(node, _ast.Import):
        raise TypeError("plain import has one module per alias")
    return "." * node.level + (node.module or "")


def _iter_import_records_v1(tree):
    records = []
    nodes = [
        node
        for node in _ast.walk(tree)
        if isinstance(node, (_ast.Import, _ast.ImportFrom))
    ]
    nodes = sorted(
        nodes,
        key=lambda node: (
            node.lineno,
            node.col_offset,
            node.end_lineno or 0,
            node.end_col_offset or 0,
        ),
    )
    for node in nodes:
        if isinstance(node, _ast.Import):
            for alias_ordinal, alias in enumerate(node.names):
                records.append(
                    {
                        "location": _source_location_v1(node),
                        "kind": "Import",
                        "module": alias.name,
                        "imported_name": None,
                        "bound_name": alias.asname or alias.name.split(".")[0],
                        "alias_ordinal": alias_ordinal,
                    }
                )
        else:
            module = _normalized_import_module_v1(node)
            for alias_ordinal, alias in enumerate(node.names):
                records.append(
                    {
                        "location": _source_location_v1(node),
                        "kind": "ImportFrom",
                        "module": module,
                        "imported_name": alias.name,
                        "bound_name": alias.asname or alias.name,
                        "alias_ordinal": alias_ordinal,
                    }
                )
    return records


def _validate_route_imports_v1(tree):
    records = _iter_import_records_v1(tree)
    for record in records:
        module = record["module"]
        imported_name = record["imported_name"]
        if module not in _ROUTE_ALLOWED_IMPORTS_V1:
            raise ValueError(f"route import {module!r} is not frozen")
        if imported_name == "*":
            raise ValueError("route star import is forbidden")
        if any(
            module == prefix or module.startswith(prefix + ".")
            for prefix in _ROUTE_PRODUCTION_ROOTS_V1
        ):
            raise ValueError("route imports a production package")
    return records


def _top_level_alias_resolution_v1(tree):
    aliases = {}
    for node in tree.body:
        if isinstance(node, _ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                resolved = alias.name if alias.asname else alias.name.split(".")[0]
                if bound in aliases:
                    raise ValueError("route has a duplicate top-level binding")
                aliases[bound] = resolved
        elif isinstance(node, _ast.ImportFrom):
            module = _normalized_import_module_v1(node)
            if module == "__future__":
                continue
            for alias in node.names:
                bound = alias.asname or alias.name
                resolved = f"{module}.{alias.name}"
                if bound in aliases:
                    raise ValueError("route has a duplicate top-level binding")
                aliases[bound] = resolved
    return aliases


def _resolve_attribute_name_v1(node, aliases):
    parts = []
    cursor = node
    while isinstance(cursor, _ast.Attribute):
        parts.append(cursor.attr)
        cursor = cursor.value
    if not isinstance(cursor, _ast.Name):
        return None
    root = aliases.get(cursor.id, cursor.id)
    return ".".join((root, *reversed(parts)))


def _contains_call_or_comprehension_v1(node):
    if node is None:
        return False
    forbidden = (
        _ast.Call,
        _ast.ListComp,
        _ast.SetComp,
        _ast.DictComp,
        _ast.GeneratorExp,
    )
    return any(isinstance(child, forbidden) for child in _ast.walk(node))


def _validate_function_definition_time_v1(node):
    if node.decorator_list:
        raise ValueError("route function decorators are forbidden")
    expressions = [
        *node.args.defaults,
        *(default for default in node.args.kw_defaults if default is not None),
        *(argument.annotation for argument in node.args.posonlyargs),
        *(argument.annotation for argument in node.args.args),
        *(argument.annotation for argument in node.args.kwonlyargs),
        node.args.vararg.annotation if node.args.vararg is not None else None,
        node.args.kwarg.annotation if node.args.kwarg is not None else None,
        node.returns,
    ]
    if any(_contains_call_or_comprehension_v1(item) for item in expressions):
        raise ValueError("route definition-time call or comprehension is forbidden")


def _literal_definition_value_v1(node):
    if isinstance(node, _ast.Constant):
        return True
    if isinstance(node, (_ast.Tuple, _ast.List, _ast.Set)):
        return all(_literal_definition_value_v1(item) for item in node.elts)
    if isinstance(node, _ast.Dict):
        return all(
            key is not None
            and _literal_definition_value_v1(key)
            and _literal_definition_value_v1(value)
            for key, value in zip(node.keys, node.values)
        )
    return False


def _validate_class_definition_time_v1(node, aliases):
    if len(node.decorator_list) > 1:
        raise ValueError("route class has multiple decorators")
    if node.decorator_list:
        decorator = node.decorator_list[0]
        if not isinstance(decorator, _ast.Call):
            raise ValueError("route class decorator must be the exact dataclass call")
        if _resolve_attribute_name_v1(decorator.func, aliases) != (
            "dataclasses.dataclass"
        ):
            raise ValueError("route class decorator is not the frozen dataclass call")
        if decorator.args or len(decorator.keywords) != 1:
            raise ValueError("route dataclass decorator arguments drifted")
        keyword = decorator.keywords[0]
        if (
            keyword.arg != "frozen"
            or not isinstance(keyword.value, _ast.Constant)
            or keyword.value.value is not True
        ):
            raise ValueError("route dataclass decorator must be frozen=True")
    if any(
        _contains_call_or_comprehension_v1(expression)
        for expression in (*node.bases, *(item.value for item in node.keywords))
    ):
        raise ValueError("route class base executes a call or comprehension")
    for statement in node.body:
        if isinstance(statement, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            _validate_function_definition_time_v1(statement)
            continue
        if isinstance(statement, _ast.AnnAssign):
            if not isinstance(statement.target, _ast.Name):
                raise ValueError("route class annotated target is not a name")
            if _contains_call_or_comprehension_v1(statement.annotation):
                raise ValueError("route class annotation executes a call")
            if statement.value is not None and not _literal_definition_value_v1(
                statement.value
            ):
                raise ValueError("route class field default is not literal")
            continue
        if isinstance(statement, _ast.Assign):
            if (
                len(statement.targets) != 1
                or not isinstance(statement.targets[0], _ast.Name)
                or not _literal_definition_value_v1(statement.value)
            ):
                raise ValueError("route class assignment is not a literal name binding")
            continue
        if isinstance(statement, _ast.Pass):
            continue
        raise ValueError("route class body executes a forbidden statement")


def _function_signature_record_v1(node):
    return {
        "name": node.name,
        "positional_only": [argument.arg for argument in node.args.posonlyargs],
        "positional": [argument.arg for argument in node.args.args],
        "keyword_only": [argument.arg for argument in node.args.kwonlyargs],
        "has_vararg": node.args.vararg is not None,
        "has_kwarg": node.args.kwarg is not None,
        "default_count": len(node.args.defaults),
        "keyword_default_count": sum(
            default is not None for default in node.args.kw_defaults
        ),
    }


def _validate_route_top_level_v1(tree, entry, aliases):
    definitions = []
    binding_names = set(aliases)
    binding_index = {}
    for node in tree.body:
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            continue
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            name = node.name
            if name in binding_names:
                raise ValueError("route has a duplicate top-level binding")
            binding_names.add(name)
            binding_index[name] = node
            definitions.append(name)
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                _validate_function_definition_time_v1(node)
            else:
                _validate_class_definition_time_v1(node, aliases)
            continue
        if isinstance(node, _ast.Assign):
            if (
                len(node.targets) != 1
                or not isinstance(node.targets[0], _ast.Name)
                or node.targets[0].id not in ("ROUTE_ID", "WIRE_SCHEMA_ID")
                or not isinstance(node.value, _ast.Constant)
                or type(node.value.value) is not str
            ):
                raise ValueError("route top-level assignment is not a frozen literal")
            name = node.targets[0].id
            if name in binding_names:
                raise ValueError("route has a duplicate top-level binding")
            binding_names.add(name)
            binding_index[name] = node
            definitions.append(name)
            continue
        raise ValueError("route has forbidden top-level execution")
    public = tuple(name for name in definitions if not name.startswith("_"))
    if public != _ROUTE_PUBLIC_EXPORTS_V1:
        raise ValueError("route public exports differ from the frozen API")
    private = tuple(name for name in definitions if name.startswith("_"))
    if any(len(name) < 2 or name.startswith("__") for name in private):
        raise ValueError("route private definitions must use one leading underscore")
    route_literal = binding_index["ROUTE_ID"].value.value
    wire_literal = binding_index["WIRE_SCHEMA_ID"].value.value
    if route_literal != entry[0] or wire_literal != entry[4]:
        raise ValueError("route exported literals differ from the registry")
    expected_signatures = (
        ("encode_normalized_transcript", "canonical_transcript_utf8"),
        ("verify_and_decode_route_wire", "canonical_route_wire_utf8"),
    )
    signatures = []
    for name, argument_name in expected_signatures:
        node = binding_index[name]
        if not isinstance(node, _ast.FunctionDef):
            raise ValueError("route public API must use synchronous functions")
        record = _function_signature_record_v1(node)
        signatures.append(record)
        if record != {
            "name": name,
            "positional_only": [],
            "positional": [argument_name],
            "keyword_only": [],
            "has_vararg": False,
            "has_kwarg": False,
            "default_count": 0,
            "keyword_default_count": 0,
        }:
            raise ValueError(f"route public API signature {name} drifted")
    return definitions, private, binding_index, signatures


def _identifier_surface_records_v1(tree):
    records = []
    for node in _ast.walk(tree):
        identifiers = []
        if isinstance(node, _ast.Name):
            identifiers.append(node.id)
        elif isinstance(node, _ast.arg):
            identifiers.append(node.arg)
        elif isinstance(node, _ast.Attribute):
            identifiers.append(node.attr)
        elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            identifiers.append(node.name)
        elif isinstance(node, _ast.alias):
            identifiers.extend(
                value for value in (node.name, node.asname) if value is not None
            )
        for identifier in identifiers:
            lowered = identifier.lower()
            tokens = [
                token
                for token in _ROUTE_FORBIDDEN_IDENTIFIER_TOKENS_V1
                if token in lowered
            ]
            wrapper = "wrapper" in lowered
            if tokens or wrapper:
                records.append(
                    {
                        "location": _source_location_v1(node),
                        "identifier": identifier,
                        "forbidden_tokens": tokens,
                        "wrapper": wrapper,
                    }
                )
    records = sorted(
        records,
        key=lambda item: (
            item["location"][1],
            item["location"][2],
            item["identifier"].encode("utf-8"),
        ),
    )
    return records


def _reachable_route_records_v1(binding_index):
    queue = ["encode_normalized_transcript", "verify_and_decode_route_wire"]
    visited = []
    queued = set(queue)
    records = []
    while queue:
        name = queue.pop(0)
        node = binding_index[name]
        visited.append(name)
        new_edges = set()
        for child in _ast.walk(node):
            if (
                isinstance(child, _ast.Name)
                and isinstance(child.ctx, _ast.Load)
                and child.id in binding_index
                and child.id not in queued
            ):
                new_edges.add(child.id)
            if (
                isinstance(child, _ast.Name)
                and isinstance(child.ctx, _ast.Load)
                and child.id in _ROUTE_FORBIDDEN_REACHABLE_NAMES_V1
            ):
                raise ValueError("route reachable closure uses a forbidden name")
            if isinstance(child, _ast.Attribute):
                attribute = child.attr
                if attribute in _ROUTE_FORBIDDEN_ATTRIBUTE_NAMES_V1 or any(
                    attribute.startswith(prefix)
                    for prefix in _ROUTE_FORBIDDEN_ATTRIBUTE_PREFIXES_V1
                ):
                    raise ValueError(
                        "route reachable closure uses a forbidden process/I-O attribute"
                    )
        ordered_edges = sorted(new_edges, key=lambda value: value.encode("utf-8"))
        for edge in ordered_edges:
            queued.add(edge)
            queue.append(edge)
        records.append(
            {
                "binding": name,
                "location": _source_location_v1(node),
                "edges": ordered_edges,
            }
        )
    return visited, records


def _production_blob_sort_key_v1(blob):
    path = blob[1]
    root_index = next(
        index
        for index, root in enumerate(_ROUTE_PRODUCTION_ROOTS_V1)
        if path == root or path.startswith(root + "/")
    )
    return root_index, path.encode("utf-8")


def _scan_production_imports_v1(production_blobs, common_commit_sha, route_module):
    if type(production_blobs) is not tuple or not production_blobs:
        raise TypeError("production blobs must be a nonempty exact tuple")
    validated = []
    observed_paths = set()
    observed_roots = set()
    for ordinal, blob in enumerate(production_blobs):
        _require_git_blob_descriptor_v1(blob, f"production blob {ordinal}")
        commit_sha, path, mode, source_bytes = blob
        if commit_sha != common_commit_sha:
            raise ValueError("production blob common commit drifted")
        if mode not in ("100644", "100755"):
            raise ValueError("production source is not a regular Git blob")
        matching_roots = [
            root
            for root in _ROUTE_PRODUCTION_ROOTS_V1
            if path == root or path.startswith(root + "/")
        ]
        if len(matching_roots) != 1:
            raise ValueError("production blob is outside the frozen scan roots")
        if path in observed_paths:
            raise ValueError("production blob path is duplicated")
        observed_paths.add(path)
        observed_roots.add(matching_roots[0])
        validated.append(blob)
    if tuple(validated) != tuple(sorted(validated, key=_production_blob_sort_key_v1)):
        raise ValueError("production blobs are not in frozen root/path order")
    if observed_roots != set(_ROUTE_PRODUCTION_ROOTS_V1):
        raise ValueError("production scan omits a frozen root")
    source_records = []
    imported_by_production = []
    for commit_sha, path, mode, source_bytes in validated:
        imports = []
        if path.endswith(".py"):
            tree = _parse_python_blob_v1(source_bytes, path)
            imports = _iter_import_records_v1(tree)
            for record in imports:
                module = record["module"]
                if module == route_module or module.startswith(route_module + "."):
                    imported_by_production.append({"path": path, "import": record})
        source_records.append(
            {
                "commit_sha": commit_sha,
                "path": path,
                "mode": mode,
                "raw_sha256": _raw_source_sha256_v1(source_bytes, path),
                "imports": imports,
            }
        )
    return source_records, imported_by_production


def _compute_route_static_fields_v1(
    route_id,
    common_commit_sha,
    route_blob,
    production_blobs,
):
    entry = _route_static_registry_entry_v1(route_id)
    _require_git_blob_descriptor_v1(route_blob, "route blob")
    route_commit_sha, route_path, route_mode, route_source = route_blob
    if route_path != entry[3] or route_mode != "100644":
        raise ValueError("route blob path or mode drifted")
    if (
        type(common_commit_sha) is not str
        or len(common_commit_sha) != 40
        or any(character not in "0123456789abcdef" for character in common_commit_sha)
    ):
        raise TypeError("common commit must be an exact Git SHA-1")
    tree = _parse_python_blob_v1(route_source, route_path)
    import_records = _validate_route_imports_v1(tree)
    aliases = _top_level_alias_resolution_v1(tree)
    definitions, private, binding_index, signatures = _validate_route_top_level_v1(
        tree,
        entry,
        aliases,
    )
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            _validate_function_definition_time_v1(node)
        elif isinstance(node, _ast.ClassDef):
            _validate_class_definition_time_v1(node, aliases)
    reachable_names, reachable_records = _reachable_route_records_v1(binding_index)
    surface_records = _identifier_surface_records_v1(tree)
    authority_records = [
        record for record in surface_records if record["forbidden_tokens"]
    ]
    wrapper_records = [record for record in surface_records if record["wrapper"]]
    production_records, imported_by_production = _scan_production_imports_v1(
        production_blobs,
        common_commit_sha,
        entry[2],
    )
    imported_by_route = [
        record
        for record in import_records
        if any(
            record["module"] == root or record["module"].startswith(root + ".")
            for root in _ROUTE_PRODUCTION_ROOTS_V1
        )
    ]
    route_source_sha = _raw_source_sha256_v1(route_source, "route")
    observation_base = {
        "route_id": route_id,
        "route_commit_sha": route_commit_sha,
        "route_source_path": route_path,
        "route_source_sha256": route_source_sha,
    }
    return {
        "route_source_sha256": route_source_sha,
        "static_api_scan_sha": _pure_core.canonical_sha_v1(
            {
                "scan_schema": "v3m0-b7-route-static-api-scan.v1",
                **observation_base,
                "public_exports": list(_ROUTE_PUBLIC_EXPORTS_V1),
                "definitions_in_source_order": definitions,
                "private_definitions_in_source_order": list(private),
                "public_api_signatures": signatures,
                "reachable_bindings_breadth_first": reachable_names,
                "reachable_binding_records": reachable_records,
            }
        ),
        "static_import_scan_sha": _pure_core.canonical_sha_v1(
            {
                "scan_schema": "v3m0-b7-route-static-import-scan.v1",
                **observation_base,
                "allowed_imports_exact": list(_ROUTE_ALLOWED_IMPORTS_V1),
                "imports_in_source_order": import_records,
                "production_import_records": imported_by_route,
            }
        ),
        "static_authority_surface_scan_sha": _pure_core.canonical_sha_v1(
            {
                "scan_schema": "v3m0-b7-route-static-surface-scan.v1",
                **observation_base,
                "forbidden_identifier_tokens": list(
                    _ROUTE_FORBIDDEN_IDENTIFIER_TOKENS_V1
                ),
                "authority_surface_records": authority_records,
                "wrapper_surface_records": wrapper_records,
            }
        ),
        "production_import_scan_sha": _pure_core.canonical_sha_v1(
            {
                "scan_schema": "v3m0-b7-production-import-scan.v1",
                **observation_base,
                "production_roots": list(_ROUTE_PRODUCTION_ROOTS_V1),
                "production_source_records": production_records,
                "route_import_records": imported_by_production,
            }
        ),
        "production_imported_by_route": bool(imported_by_route),
        "route_imported_by_production": bool(imported_by_production),
        "authority_surface_count": len(authority_records),
        "wrapper_surface_count": len(wrapper_records),
    }


def validate_route_static_surface_v1(raw_body, route_blob, production_blobs):
    """Validate one route manifest from caller-supplied immutable Git blobs."""
    manifest = _validate_exact_lab_record_v1("B7LabRouteManifestV1", raw_body)
    entry = _route_static_registry_entry_v1(manifest["route_id"])
    expected_entry_fields = (
        ("route_id", entry[0]),
        ("route_schema_domain", entry[1]),
        ("route_module", entry[2]),
        ("route_source_path", entry[3]),
        ("wire_schema_id", entry[4]),
        ("encoder_symbol", "encode_normalized_transcript"),
        ("verifier_decoder_symbol", "verify_and_decode_route_wire"),
        (
            "input_schema_version",
            "experimental.v3m0.b7.normalized-transcript.v1",
        ),
        ("output_schema_version", entry[4]),
    )
    for field, expected in expected_entry_fields:
        if manifest[field] != expected:
            raise ValueError(f"route manifest {field} drifted")
    computed = _compute_route_static_fields_v1(
        manifest["route_id"],
        manifest["common_commit_sha"],
        route_blob,
        production_blobs,
    )
    if route_blob[0] != manifest["route_commit_sha"]:
        raise ValueError("route blob commit drifted")
    for field, expected in computed.items():
        if manifest[field] != expected or type(manifest[field]) is not type(expected):
            raise ValueError(f"route manifest {field} differs from static scan")
    return manifest


_REVIEWER_ROLE_ROOTS_V1 = (
    (
        "CORPUS_REPLAY",
        "_review_corpus_replay_cli",
    ),
    (
        "METRIC_REPLAY",
        "_review_metric_replay_cli",
    ),
)
_REVIEWER_OUTER_ROOTS_V1 = (
    "precheck_python_invocation_identity_v2",
    "recheck_python_invocation_identity_v2",
    "run_python_environment_import_probe_v2",
    "capture_environment_manifest_v2",
    "run_frozen_reviewer_process_v2",
)
_REVIEWER_OUTER_HELPERS_V1 = (
    "_require_lower_hex_v1",
    "build_sanitized_reviewer_environment_v1",
    "recheck_frozen_python_executable_identity_v1",
    "_require_normalized_absolute_path_v2",
    "_stable_regular_file_observation_v2",
    "_resolve_python_invocation_chain_v2",
    "_nearest_pyvenv_cfg_v2",
    "_python_environment_probe_report_is_well_typed_v2",
    "_empty_process_observation_v1",
    "_process_observation_v1",
    "_validate_bounded_process_configuration_v1",
    "run_bounded_reviewer_process_v1",
    "experiments.v3m0_b7_schema_lab.common.canonical_json_bytes_v1",
    "experiments.v3m0_b7_schema_lab.common.canonical_sha_v1",
    "experiments.v3m0_b7_schema_lab.common.strict_json_loads_v1",
    "experiments.v3m0_b7_schema_lab.common.validate_environment_manifest_v2",
    "experiments.v3m0_b7_schema_lab.common.validate_exact_lab_record_v1",
)
_REVIEWER_CHILD_FORBIDDEN_OUTER_V1 = (
    "precheck_python_invocation_identity_v2",
    "recheck_python_invocation_identity_v2",
    "run_bounded_reviewer_process_v1",
    "run_python_environment_import_probe_v2",
    "capture_environment_manifest_v2",
    "run_frozen_reviewer_process_v2",
)
_REVIEWER_COMMON_IMPORTS_V1 = (
    "__future__",
    "ast",
    "base64",
    "binascii",
    "copy",
    "dataclasses",
    "difflib",
    "enum",
    "hashlib",
    "json",
    "math",
    "numpy",
    "pathlib",
    "re",
    "struct",
    "typing",
    "rulespace_v3.b7_replay_core_v1",
)
_REVIEWER_COMPARE_BOOTSTRAP_IMPORTS_V1 = (
    "__future__",
    "argparse",
    "hashlib",
    "json",
    "pathlib",
    "sys",
    "typing",
    "experiments.v3m0_b7_schema_lab.common",
)
_REVIEWER_COMPARE_OUTER_IMPORTS_V1 = (
    "os",
    "selectors",
    "shutil",
    "signal",
    "stat",
    "subprocess",
    "tarfile",
    "tempfile",
    "time",
)
_REVIEWER_CORE_IMPORTS_V1 = (
    "__future__",
    "base64",
    "binascii",
    "dataclasses",
    "enum",
    "fractions",
    "hashlib",
    "json",
    "math",
    "numpy",
    "re",
    "scipy.linalg",
    "struct",
    "typing",
)
_REVIEWER_FORBIDDEN_EXACT_NAMES_V1 = (
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "print",
    "vars",
)
_REVIEWER_FORBIDDEN_CALL_PREFIXES_V1 = (
    "asyncio.create_subprocess",
    "concurrent.futures.ProcessPoolExecutor",
    "concurrent.futures.process.",
    "ctypes.",
    "multiprocessing.",
    "os.exec",
    "os.fork",
    "os.kill",
    "os.killpg",
    "os.posix_spawn",
    "os.popen",
    "os.setsid",
    "os.spawn",
    "os.system",
    "posix.",
    "pty.",
    "signal.pthread_kill",
    "signal.raise_signal",
    "socket.",
    "subprocess.",
)
_REVIEWER_FORBIDDEN_MODULE_ROOTS_V1 = (
    "_posixsubprocess",
    "asyncio",
    "concurrent",
    "ctypes",
    "importlib",
    "multiprocessing",
    "os",
    "posix",
    "pty",
    "runpy",
    "socket",
    "subprocess",
)
_REVIEWER_ALLOWED_BUILTIN_CALLS_V1 = (
    "Exception",
    "KeyError",
    "RuntimeError",
    "TypeError",
    "ValueError",
    "abs",
    "all",
    "any",
    "bool",
    "bytes",
    "classmethod",
    "dict",
    "enumerate",
    "filter",
    "float",
    "frozenset",
    "int",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "list",
    "map",
    "max",
    "min",
    "next",
    "object",
    "property",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "staticmethod",
    "str",
    "sum",
    "super",
    "tuple",
    "type",
    "zip",
)
_REVIEWER_ALLOWED_EXTERNAL_CALLS_V1 = (
    "argparse.ArgumentParser",
    "argparse.ArgumentParser.add_argument",
    "argparse.ArgumentParser.parse_args",
    "ast.parse",
    "ast.unparse",
    "ast.walk",
    "base64.b64decode",
    "base64.b64encode",
    "binascii.Error",
    "copy.deepcopy",
    "dataclasses.asdict",
    "dataclasses.dataclass",
    "dataclasses.fields",
    "dataclasses.is_dataclass",
    "dataclasses.replace",
    "difflib.unified_diff",
    "enum.Enum",
    "fractions.Fraction",
    "hashlib.sha256",
    "json.dumps",
    "json.loads",
    "math.cos",
    "math.fsum",
    "math.isfinite",
    "math.sin",
    "math.sqrt",
    "numpy.abs",
    "numpy.all",
    "numpy.any",
    "numpy.arange",
    "numpy.array",
    "numpy.asarray",
    "numpy.block",
    "numpy.concatenate",
    "numpy.conj",
    "numpy.diag",
    "numpy.dot",
    "numpy.dtype",
    "numpy.einsum",
    "numpy.eye",
    "numpy.float64",
    "numpy.int64",
    "numpy.isclose",
    "numpy.isfinite",
    "numpy.linalg.cond",
    "numpy.linalg.det",
    "numpy.linalg.eig",
    "numpy.linalg.eigh",
    "numpy.linalg.eigvals",
    "numpy.linalg.eigvalsh",
    "numpy.linalg.inv",
    "numpy.linalg.matrix_rank",
    "numpy.linalg.norm",
    "numpy.linalg.pinv",
    "numpy.linalg.solve",
    "numpy.linalg.svd",
    "numpy.max",
    "numpy.mean",
    "numpy.min",
    "numpy.ones",
    "numpy.real",
    "numpy.reshape",
    "numpy.stack",
    "numpy.sum",
    "numpy.vdot",
    "numpy.where",
    "numpy.zeros",
    "pathlib.Path",
    "pathlib.Path.read_bytes",
    "pathlib.PurePosixPath",
    "re.compile",
    "re.fullmatch",
    "scipy.linalg.schur",
    "struct.pack",
    "struct.unpack",
    "sys.stdout.buffer.write",
)
_REVIEWER_ALLOWED_VALUE_METHODS_V1 = (
    "bytes.decode",
    "bytes.hex",
    "bytes.startswith",
    "dict.copy",
    "dict.get",
    "dict.items",
    "dict.keys",
    "dict.pop",
    "dict.values",
    "hashlib.sha256.digest",
    "hashlib.sha256.hexdigest",
    "complex.conjugate",
    "list.append",
    "list.extend",
    "list.pop",
    "numpy.ndarray.astype",
    "numpy.ndarray.conj",
    "numpy.ndarray.copy",
    "numpy.ndarray.reshape",
    "numpy.ndarray.tobytes",
    "numpy.ndarray.tolist",
    "numpy.ndarray.transpose",
    "set.add",
    "set.difference",
    "set.issubset",
    "str.encode",
    "str.endswith",
    "str.join",
    "str.lower",
    "str.replace",
    "str.split",
    "str.splitlines",
    "str.startswith",
    "str.strip",
    "tuple.index",
)
_REVIEWER_LEGACY_EXPORTS_V1 = (
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
_REVIEWER_LEGACY_EXPORT_MODULES_V1 = (
    "evidence",
    "contracts",
    "evidence",
    "contracts",
    "contracts",
    "evidence",
    "contracts",
    "evidence",
    "evidence",
)


def _require_reviewer_git_sha1_v1(value, field):
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TypeError(f"{field} must be an exact lowercase Git SHA-1")
    return value


def _reviewer_top_level_functions_v1(tree, path):
    functions = [
        node
        for node in tree.body
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
    ]
    names = [node.name for node in functions]
    if len(names) != len(set(names)):
        raise ValueError(f"{path} has duplicate top-level function bindings")
    return functions, {node.name: node for node in functions}


def _reviewer_local_call_closure_v1(root, definitions):
    if root not in definitions:
        raise ValueError(f"reviewer root {root} is absent")
    queue = [root]
    reached = set(queue)
    edges = []
    while queue:
        owner = queue.pop(0)
        callees = []
        for node in _ast.walk(definitions[owner]):
            if (
                isinstance(node, _ast.Call)
                and isinstance(node.func, _ast.Name)
                and node.func.id in definitions
            ):
                callees.append(node.func.id)
        ordered = []
        for name in callees:
            if name not in ordered:
                ordered.append(name)
            if name not in reached:
                reached.add(name)
                queue.append(name)
        edges.append({"owner": owner, "callees": ordered})
    return reached, edges


def _reviewer_imports_owned_by_functions_v1(tree):
    records = []
    for top_level in tree.body:
        if not isinstance(top_level, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        for node in _ast.walk(top_level):
            if not isinstance(node, (_ast.Import, _ast.ImportFrom)):
                continue
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, _ast.Import)
                else [_normalized_import_module_v1(node)]
            )
            for module in modules:
                records.append(
                    {
                        "owner": top_level.name,
                        "module": module,
                        "location": _source_location_v1(node),
                        "star": any(alias.name == "*" for alias in node.names),
                    }
                )
    return records


def _validate_reviewer_initializer_v1(tree, source_bytes):
    if source_bytes != b"" or tree.body:
        raise ValueError("schema-lab initializer must be the exact empty blob")


def _validate_rulespace_initializer_v1(tree):
    if tuple(type(node) for node in tree.body) != (
        _ast.Expr,
        _ast.Assign,
        _ast.FunctionDef,
    ):
        raise ValueError("rulespace initializer node order drifted")
    docstring, export_assignment, lazy = tree.body
    if (
        not isinstance(docstring.value, _ast.Constant)
        or docstring.value.value
        != "V3-M0 immutable contracts and profile-aware evidence primitives."
    ):
        raise ValueError("rulespace initializer docstring drifted")
    if (
        len(export_assignment.targets) != 1
        or not isinstance(export_assignment.targets[0], _ast.Name)
        or export_assignment.targets[0].id != "__all__"
        or not isinstance(export_assignment.value, _ast.Tuple)
        or tuple(
            item.value
            for item in export_assignment.value.elts
            if isinstance(item, _ast.Constant)
        )
        != _REVIEWER_LEGACY_EXPORTS_V1
        or len(export_assignment.value.elts) != len(_REVIEWER_LEGACY_EXPORTS_V1)
    ):
        raise ValueError("rulespace initializer export tuple drifted")
    args = lazy.args
    if (
        lazy.name != "__getattr__"
        or [argument.arg for argument in args.args] != ["name"]
        or args.posonlyargs
        or args.vararg is not None
        or args.kwonlyargs
        or args.kw_defaults
        or args.kwarg is not None
        or args.defaults
        or lazy.decorator_list
        or lazy.returns is not None
        or lazy.type_comment is not None
        or args.args[0].annotation is not None
        or len(lazy.body) != len(_REVIEWER_LEGACY_EXPORTS_V1) + 1
    ):
        raise ValueError("rulespace initializer lazy resolver signature drifted")
    for branch, name, module in zip(
        lazy.body[:-1],
        _REVIEWER_LEGACY_EXPORTS_V1,
        _REVIEWER_LEGACY_EXPORT_MODULES_V1,
    ):
        if (
            not isinstance(branch, _ast.If)
            or branch.orelse
            or not isinstance(branch.test, _ast.Compare)
            or not isinstance(branch.test.left, _ast.Name)
            or branch.test.left.id != "name"
            or len(branch.test.ops) != 1
            or not isinstance(branch.test.ops[0], _ast.Eq)
            or len(branch.test.comparators) != 1
            or not isinstance(branch.test.comparators[0], _ast.Constant)
            or branch.test.comparators[0].value != name
            or len(branch.body) != 2
        ):
            raise ValueError("rulespace initializer lazy branch drifted")
        import_node, return_node = branch.body
        if (
            not isinstance(import_node, _ast.ImportFrom)
            or import_node.level != 1
            or import_node.module != module
            or [(alias.name, alias.asname) for alias in import_node.names]
            != [(name, None)]
            or not isinstance(return_node, _ast.Return)
            or not isinstance(return_node.value, _ast.Name)
            or return_node.value.id != name
        ):
            raise ValueError("rulespace initializer lazy import drifted")
    terminal = lazy.body[-1]
    if (
        not isinstance(terminal, _ast.Raise)
        or terminal.cause is not None
        or not isinstance(terminal.exc, _ast.Call)
        or not isinstance(terminal.exc.func, _ast.Name)
        or terminal.exc.func.id != "AttributeError"
        or len(terminal.exc.args) != 1
        or not isinstance(terminal.exc.args[0], _ast.Name)
        or terminal.exc.args[0].id != "name"
        or terminal.exc.keywords
    ):
        raise ValueError("rulespace initializer terminal raise drifted")


def _reviewer_module_level_imports_v1(tree):
    records = []
    for node in tree.body:
        if isinstance(node, _ast.Import):
            records.extend(alias.name for alias in node.names)
        elif isinstance(node, _ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                raise ValueError("reviewer star import is forbidden")
            records.append(_normalized_import_module_v1(node))
    return records


def _validate_reviewer_import_surface_v1(trees, child_closures):
    common_tree = trees["experiments/v3m0_b7_schema_lab/common.py"]
    for record in _iter_import_records_v1(common_tree):
        if record["module"] not in _REVIEWER_COMMON_IMPORTS_V1:
            raise ValueError("common imports an unlisted module")
        if record["imported_name"] == "*":
            raise ValueError("common star import is forbidden")

    core_tree = trees["rulespace_v3/b7_replay_core_v1.py"]
    for record in _iter_import_records_v1(core_tree):
        if record["module"] not in _REVIEWER_CORE_IMPORTS_V1:
            raise ValueError("pure replay core imports an unlisted module")
        if record["imported_name"] == "*":
            raise ValueError("pure replay core star import is forbidden")

    compare_tree = trees["experiments/v3m0_b7_schema_lab/compare.py"]
    module_imports = _reviewer_module_level_imports_v1(compare_tree)
    if any(
        module not in _REVIEWER_COMPARE_BOOTSTRAP_IMPORTS_V1
        for module in module_imports
    ):
        raise ValueError("compare bootstrap imports an unlisted module")
    owned = _reviewer_imports_owned_by_functions_v1(compare_tree)
    if any(record["star"] for record in owned):
        raise ValueError("reviewer function-local star import is forbidden")
    route_modules = tuple(entry[2] for entry in _ROUTE_STATIC_REGISTRY_V1)
    child_union = set().union(*(closure for closure in child_closures.values()))
    for record in owned:
        module = record["module"]
        if module in route_modules:
            continue
        if module in _REVIEWER_COMPARE_BOOTSTRAP_IMPORTS_V1:
            continue
        if module in _REVIEWER_COMPARE_OUTER_IMPORTS_V1:
            if record["owner"] in child_union:
                raise ValueError("outer process import enters reviewer child closure")
            continue
        raise ValueError("compare function imports an unlisted module")
    for role, closure in child_closures.items():
        ordered_modules = [
            record["module"]
            for record in owned
            if record["owner"] in closure and record["module"] in route_modules
        ]
        if tuple(ordered_modules) != route_modules:
            raise ValueError(f"{role} route import closure/order drifted")
    return module_imports, owned


def _attribute_path_v1(node):
    parts = []
    cursor = node
    while isinstance(cursor, _ast.Attribute):
        parts.append(cursor.attr)
        cursor = cursor.value
    if not isinstance(cursor, _ast.Name):
        return None
    return ".".join((cursor.id, *reversed(parts)))


def _reviewer_module_name_by_path_v1(path):
    if not path.endswith(".py"):
        raise ValueError("reviewer executed module path is not Python")
    if path.endswith("/__init__.py"):
        return path[: -len("/__init__.py")].replace("/", ".")
    return path[:-3].replace("/", ".")


def _reviewer_absolute_import_module_v1(raw_module, owner_module):
    if not raw_module.startswith("."):
        return raw_module
    level = len(raw_module) - len(raw_module.lstrip("."))
    suffix = raw_module[level:]
    package = owner_module.split(".")[:-1]
    if level > len(package):
        raise ValueError("reviewer relative import escapes its package")
    base = package[: len(package) - level + 1]
    return ".".join((*base, *((suffix,) if suffix else ())))


def _reviewer_import_aliases_v1(nodes, owner_module):
    aliases = {}
    for node in nodes:
        if isinstance(node, _ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                resolved = alias.name if alias.asname else alias.name.split(".")[0]
                if bound in aliases:
                    raise ValueError("reviewer import alias is duplicated")
                aliases[bound] = ("MODULE", resolved)
        elif isinstance(node, _ast.ImportFrom):
            module = _reviewer_absolute_import_module_v1(
                _normalized_import_module_v1(node), owner_module
            )
            for alias in node.names:
                if alias.name == "*":
                    raise ValueError("reviewer star import is forbidden")
                bound = alias.asname or alias.name
                if bound in aliases:
                    raise ValueError("reviewer import alias is duplicated")
                aliases[bound] = ("SYMBOL", f"{module}.{alias.name}")
    return aliases


def _reviewer_binding_nodes_v1(node):
    pending = list(reversed(node.body))
    while pending:
        child = pending.pop()
        if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            definition_time = [
                *child.decorator_list,
                *child.args.defaults,
                *(default for default in child.args.kw_defaults if default is not None),
                *(argument.annotation for argument in child.args.posonlyargs),
                *(argument.annotation for argument in child.args.args),
                *(argument.annotation for argument in child.args.kwonlyargs),
                child.args.vararg.annotation if child.args.vararg is not None else None,
                child.args.kwarg.annotation if child.args.kwarg is not None else None,
                child.returns,
            ]
            pending.extend(
                reversed([item for item in definition_time if item is not None])
            )
            continue
        if isinstance(child, _ast.ClassDef):
            definition_time = [
                *child.decorator_list,
                *child.bases,
                *(keyword.value for keyword in child.keywords),
                *child.body,
            ]
            pending.extend(reversed(definition_time))
            continue
        yield child
        children = list(_ast.iter_child_nodes(child))
        pending.extend(reversed(children))


def _reviewer_local_import_nodes_v1(node):
    return [
        child
        for child in _reviewer_binding_nodes_v1(node)
        if isinstance(child, (_ast.Import, _ast.ImportFrom))
    ]


def _reviewer_resolve_qualified_v1(node, aliases):
    parts = []
    cursor = node
    while isinstance(cursor, _ast.Attribute):
        parts.append(cursor.attr)
        cursor = cursor.value
    if not isinstance(cursor, _ast.Name) or cursor.id not in aliases:
        return None
    _kind, root = aliases[cursor.id]
    return ".".join((root, *reversed(parts)))


def _reviewer_local_target_v1(
    resolved,
    module_definitions,
    *,
    require_callable=True,
):
    matches = []
    for module in module_definitions:
        prefix = module + "."
        if resolved.startswith(prefix):
            symbol = resolved[len(prefix) :]
            if "." not in symbol:
                matches.append((module, symbol))
    if len(matches) > 1:
        raise ValueError("reviewer repository-local resolution is ambiguous")
    if not matches:
        return None
    module, symbol = matches[0]
    if symbol not in module_definitions[module] and require_callable:
        raise ValueError("reviewer calls a non-callable repository-local binding")
    if symbol not in module_definitions[module]:
        return None
    return module, symbol


def _validate_reviewer_external_call_v1(resolved, call):
    components = resolved.split(".")
    if any(component.startswith("_") for component in components[1:]):
        raise ValueError("reviewer calls an external private attribute")
    if any(
        resolved.startswith(prefix) for prefix in _REVIEWER_FORBIDDEN_CALL_PREFIXES_V1
    ):
        raise ValueError("reviewer child calls a forbidden capability")
    if components[0] in _REVIEWER_FORBIDDEN_MODULE_ROOTS_V1:
        raise ValueError("reviewer child uses a forbidden module root")
    if resolved not in _REVIEWER_ALLOWED_EXTERNAL_CALLS_V1:
        raise ValueError("reviewer child has an unlisted external call")
    return resolved


def _validate_reviewer_method_call_v1(call):
    if not isinstance(call.func, _ast.Attribute):
        raise ValueError("reviewer child has dynamic call resolution")
    terminal = call.func.attr
    allowed = [
        method
        for method in _REVIEWER_ALLOWED_VALUE_METHODS_V1
        if method.rsplit(".", 1)[-1] == terminal
    ]
    if not allowed:
        raise ValueError("reviewer child calls an unlisted value method")
    return f"<frozen-value>.{terminal}"


def _reviewer_highest_attribute_v1(node, parents):
    cursor = node
    while (
        isinstance(parents.get(cursor), _ast.Attribute)
        and parents[cursor].value is cursor
    ):
        cursor = parents[cursor]
    return cursor


def _validate_reviewer_module_and_callable_flows_v1(
    node,
    aliases,
    parents,
    module_definitions,
):
    external_calls = set(_REVIEWER_ALLOWED_EXTERNAL_CALLS_V1)
    for child in _reviewer_binding_nodes_v1(node):
        if not isinstance(child, _ast.Name) or not isinstance(child.ctx, _ast.Load):
            continue
        binding = aliases.get(child.id)
        if binding is None:
            continue
        kind, resolved = binding
        parent = parents.get(child)
        if kind == "MODULE":
            if not isinstance(parent, _ast.Attribute) or parent.value is not child:
                raise ValueError(
                    "reviewer module object flows through a value/container"
                )
            highest = _reviewer_highest_attribute_v1(child, parents)
            use = parents.get(highest)
            qualified = _reviewer_resolve_qualified_v1(highest, aliases)
            if (
                qualified in external_calls
                or _reviewer_local_target_v1(
                    qualified,
                    module_definitions,
                    require_callable=False,
                )
                is not None
            ) and not (isinstance(use, _ast.Call) and use.func is highest):
                raise ValueError("reviewer callable alias flows without a direct call")
        elif kind == "SYMBOL":
            local = _reviewer_local_target_v1(
                resolved,
                module_definitions,
                require_callable=False,
            )
            if (resolved in external_calls or local is not None) and not (
                isinstance(parent, _ast.Call) and parent.func is child
            ):
                raise ValueError(
                    "reviewer imported callable flows without a direct call"
                )


def _validate_reviewer_terminal_stdout_v1(call, parents, owner):
    statement = parents.get(call)
    if not isinstance(statement, _ast.Return) or statement.value is not call:
        raise ValueError("reviewer stdout write is not the terminal return")
    if statement not in owner.body or owner.body[-1] is not statement:
        raise ValueError("reviewer stdout write is not terminal in its binding")
    if len(call.args) != 1 or call.keywords:
        raise ValueError("reviewer stdout write signature drifted")
    payload = call.args[0]
    if (
        not isinstance(payload, _ast.BinOp)
        or not isinstance(payload.op, _ast.Add)
        or not isinstance(payload.right, _ast.Constant)
        or payload.right.value != b"\n"
    ):
        raise ValueError("reviewer stdout frame is not canonical bytes plus one LF")


def _validate_reviewer_child_calls_v1(trees, definitions, child_union):
    forbidden = set(_REVIEWER_FORBIDDEN_EXACT_NAMES_V1)
    for path, tree in trees.items():
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Name) and node.id in forbidden:
                raise ValueError(f"reviewer source {path} uses forbidden exact name")

    modules_by_path = {path: _reviewer_module_name_by_path_v1(path) for path in trees}
    module_definitions = {}
    module_aliases = {}
    parents_by_module = {}
    for path, tree in trees.items():
        module = modules_by_path[path]
        _functions, by_name = _reviewer_top_level_functions_v1(tree, path)
        classes = {
            node.name: node for node in tree.body if isinstance(node, _ast.ClassDef)
        }
        overlap = set(by_name).intersection(classes)
        if overlap:
            raise ValueError("reviewer top-level callable binding is duplicated")
        module_definitions[module] = {**by_name, **classes}
        module_aliases[module] = _reviewer_import_aliases_v1(
            [
                node
                for node in tree.body
                if isinstance(node, (_ast.Import, _ast.ImportFrom))
            ],
            module,
        )
        parents_by_module[module] = {
            child: parent
            for parent in _ast.walk(tree)
            for child in _ast.iter_child_nodes(parent)
        }

    compare_module = "experiments.v3m0_b7_schema_lab.compare"
    roots = [(compare_module, name) for name in child_union]
    for entry in _ROUTE_STATIC_REGISTRY_V1:
        roots.extend(
            (
                (entry[2], "encode_normalized_transcript"),
                (entry[2], "verify_and_decode_route_wire"),
            )
        )
    queue = list(roots)
    reached = set(queue)
    edge_records = []
    stdout_calls = {}
    while queue:
        module, owner = queue.pop(0)
        if module not in module_definitions or owner not in module_definitions[module]:
            raise ValueError("reviewer fixed-point root is unresolved")
        node = module_definitions[module][owner]
        if isinstance(node, _ast.ClassDef):
            edge_records.append(
                {"owner": f"{module}.{owner}", "calls": [], "edges": []}
            )
            continue
        local_aliases = _reviewer_import_aliases_v1(
            _reviewer_local_import_nodes_v1(node), module
        )
        aliases = {**module_aliases[module], **local_aliases}
        parents = parents_by_module[module]
        _validate_reviewer_module_and_callable_flows_v1(
            node,
            aliases,
            parents,
            module_definitions,
        )
        owner_calls = []
        local_edges = []
        for call in (
            item
            for item in _reviewer_binding_nodes_v1(node)
            if isinstance(item, _ast.Call)
        ):
            target = None
            if isinstance(call.func, _ast.Name):
                name = call.func.id
                if name in module_definitions[module]:
                    target = (module, name)
                    resolved = f"{module}.{name}"
                elif name in aliases:
                    _kind, resolved = aliases[name]
                    target = _reviewer_local_target_v1(resolved, module_definitions)
                    if target is None:
                        _validate_reviewer_external_call_v1(resolved, call)
                elif name in _REVIEWER_ALLOWED_BUILTIN_CALLS_V1:
                    resolved = name
                elif name in forbidden:
                    raise ValueError("reviewer child calls a forbidden resolver")
                else:
                    raise ValueError("reviewer child has an unresolved direct call")
            else:
                resolved = _reviewer_resolve_qualified_v1(call.func, aliases)
                if resolved is None:
                    resolved = _validate_reviewer_method_call_v1(call)
                else:
                    target = _reviewer_local_target_v1(resolved, module_definitions)
                    if target is None:
                        _validate_reviewer_external_call_v1(resolved, call)
            owner_calls.append(resolved)
            if resolved == "sys.stdout.buffer.write":
                _validate_reviewer_terminal_stdout_v1(call, parents, node)
                stdout_calls[(module, call.lineno, call.col_offset)] = (
                    _source_location_v1(call)
                )
            if target is not None:
                local_edges.append(f"{target[0]}.{target[1]}")
                if target not in reached:
                    reached.add(target)
                    queue.append(target)
        edge_records.append(
            {
                "owner": f"{module}.{owner}",
                "calls": owner_calls,
                "edges": local_edges,
            }
        )
    if len(stdout_calls) != 1:
        raise ValueError("reviewer child must have exactly one terminal stdout call")
    return edge_records, next(iter(stdout_calls.values()))


def _validate_reviewer_outer_closure_v1(functions, definitions):
    reached = set()
    common_calls = set()
    for root in _REVIEWER_OUTER_ROOTS_V1:
        closure, _edges = _reviewer_local_call_closure_v1(root, definitions)
        reached.update(closure)
        for owner in closure:
            for call in (
                node
                for node in _ast.walk(definitions[owner])
                if isinstance(node, _ast.Call)
            ):
                path = _attribute_path_v1(call.func)
                if path is not None and path.startswith("_common."):
                    common_calls.add(
                        "experiments.v3m0_b7_schema_lab.common."
                        + path.removeprefix("_common.")
                    )
    local_helpers = [
        node.name
        for node in functions
        if node.name in reached and node.name not in _REVIEWER_OUTER_ROOTS_V1
    ]
    observed = tuple(local_helpers) + tuple(
        sorted(common_calls, key=lambda value: value.encode("utf-8"))
    )
    if observed != _REVIEWER_OUTER_HELPERS_V1:
        raise ValueError("reviewer outer runner helper closure drifted")
    return observed


def _reviewer_module_static_scan_record_v1(path, source_bytes, tree):
    return {
        "path": path,
        "raw_sha256": _raw_source_sha256_v1(source_bytes, path),
        "static_scan_sha": canonical_sha_v1(
            {
                "scan_schema": "v3m0-b7-reviewer-module-ast.v1",
                "path": path,
                "ast_dump": _ast.dump(
                    tree, annotate_fields=True, include_attributes=True
                ),
            }
        ),
    }


def validate_reviewer_child_static_surface_v1(
    *,
    source_commit_sha,
    common_commit_sha,
    route_manifests,
    source_blobs,
    production_blobs,
):
    """Validate the reviewer-child AST closure using caller-supplied Git blobs."""

    _require_reviewer_git_sha1_v1(source_commit_sha, "reviewer source commit")
    _require_reviewer_git_sha1_v1(common_commit_sha, "reviewer common commit")
    if type(route_manifests) is not tuple or len(route_manifests) != 3:
        raise TypeError("reviewer route manifests must be an exact three-item tuple")
    if type(source_blobs) is not tuple or len(source_blobs) != 8:
        raise TypeError("reviewer source blobs must be an exact eight-item tuple")
    source_by_path = {}
    for ordinal, blob in enumerate(source_blobs):
        _require_git_blob_descriptor_v1(blob, f"reviewer source blob {ordinal}")
        commit_sha, path, mode, source_bytes = blob
        if commit_sha != source_commit_sha:
            raise ValueError(
                "reviewer source is not bound to the frozen evidence commit"
            )
        if mode != "100644" or path in source_by_path:
            raise ValueError("reviewer source mode/path set drifted")
        source_by_path[path] = source_bytes
    expected_paths = (
        "experiments/v3m0_b7_schema_lab/__init__.py",
        "experiments/v3m0_b7_schema_lab/common.py",
        "experiments/v3m0_b7_schema_lab/compare.py",
        *(entry[3] for entry in _ROUTE_STATIC_REGISTRY_V1),
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
    )
    if set(source_by_path) != set(expected_paths):
        raise ValueError("reviewer executed local module set drifted")

    route_ids = []
    for entry, manifest in zip(_ROUTE_STATIC_REGISTRY_V1, route_manifests):
        if type(manifest) is not dict or manifest.get("route_id") != entry[0]:
            raise ValueError("reviewer route manifest order drifted")
        if manifest.get("common_commit_sha") != common_commit_sha:
            raise ValueError("reviewer route common commit drifted")
        route_blob = (
            manifest.get("route_commit_sha"),
            entry[3],
            "100644",
            source_by_path[entry[3]],
        )
        validate_route_static_surface_v1(manifest, route_blob, production_blobs)
        route_ids.append(entry[0])

    trees = {
        path: _parse_python_blob_v1(source_by_path[path], path)
        for path in expected_paths
    }
    _validate_reviewer_initializer_v1(
        trees["experiments/v3m0_b7_schema_lab/__init__.py"],
        source_by_path["experiments/v3m0_b7_schema_lab/__init__.py"],
    )
    _validate_rulespace_initializer_v1(trees["rulespace_v3/__init__.py"])
    compare_path = "experiments/v3m0_b7_schema_lab/compare.py"
    functions, definitions = _reviewer_top_level_functions_v1(
        trees[compare_path], compare_path
    )
    child_closures = {}
    child_edges = {}
    for role, root in _REVIEWER_ROLE_ROOTS_V1:
        closure, edges = _reviewer_local_call_closure_v1(root, definitions)
        if closure.intersection(_REVIEWER_CHILD_FORBIDDEN_OUTER_V1):
            raise ValueError("reviewer child reaches an outer process symbol")
        child_closures[role] = closure
        child_edges[role] = edges
    module_imports, function_imports = _validate_reviewer_import_surface_v1(
        trees,
        child_closures,
    )
    outer_helpers = _validate_reviewer_outer_closure_v1(functions, definitions)
    child_union = set().union(*(closure for closure in child_closures.values()))
    child_call_records, stdout_location = _validate_reviewer_child_calls_v1(
        trees,
        definitions,
        child_union,
    )
    execution_paths = (
        "experiments/v3m0_b7_schema_lab/__init__.py",
        compare_path,
        "experiments/v3m0_b7_schema_lab/common.py",
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
        *(entry[3] for entry in _ROUTE_STATIC_REGISTRY_V1),
    )
    module_records = [
        _reviewer_module_static_scan_record_v1(
            path,
            source_by_path[path],
            trees[path],
        )
        for path in execution_paths
    ]
    projection = {
        "static_surface_schema_version": (
            "experimental.v3m0.b7.reviewer-child-static-surface.v1"
        ),
        "source_commit_sha": source_commit_sha,
        "common_commit_sha": common_commit_sha,
        "ordered_role_ids": [role for role, _root in _REVIEWER_ROLE_ROOTS_V1],
        "ordered_route_ids": route_ids,
        "ordered_executed_module_paths": list(execution_paths),
        "module_static_scan_records": module_records,
        "module_level_compare_imports": module_imports,
        "function_local_compare_imports": function_imports,
        "role_local_call_edges": [
            {"role": role, "edges": child_edges[role]}
            for role, _root in _REVIEWER_ROLE_ROOTS_V1
        ],
        "child_call_records": child_call_records,
        "terminal_stdout_call_location": stdout_location,
        "outer_helper_closure": list(outer_helpers),
    }
    return {
        **projection,
        "reviewer_child_static_scan_sha": canonical_sha_v1(projection),
    }


_REVIEWER_COMMON_ORIGIN_EXACT_PATHS_V1 = (
    "docsv3/v3-机器合同-B7-v9.1-registry.json",
    "docsv3/v3-机器合同-B7-v9.2-overlay.json",
    "docsv3/v3-机器合同-B7-v9.2.1-overlay.json",
    "experiments/v3m0_b7_schema_lab/__init__.py",
    "experiments/v3m0_b7_schema_lab/common.py",
    "experiments/v3m0_b7_schema_lab/compare.py",
    "tests/fixtures/v3m0_b7_schema_lab_corpus.json",
)
_REVIEWER_NAMESPACE_OBSERVATION_FIELDS_V1 = (
    "fresh_export_root_count",
    "experiments_init_present",
    "experiments_namespace_portion_count",
    "shadowing_paths",
)
_REVIEWER_SOURCE_MEMBERSHIP_FIELDS_V1 = (
    "role_or_route_id",
    "execution_ordinal",
    "path",
    "candidate_mode",
    "candidate_blob_oid",
    "origin_kind",
    "origin_commit",
    "origin_path",
    "origin_mode",
    "origin_blob_oid",
    "static_scan_sha",
)


def _git_blob_oid_v1(raw_bytes):
    if type(raw_bytes) is not bytes:
        raise TypeError("Git blob body must be exact bytes")
    header = f"blob {len(raw_bytes)}\0".encode("ascii")
    return _pure_core.hashlib.sha1(header + raw_bytes).hexdigest()


def _validate_git_tree_blob_observation_v1(
    raw_blob,
    field,
    *,
    expected_commit=None,
):
    if type(raw_blob) is not tuple or len(raw_blob) != 6:
        raise TypeError(f"{field} must be an exact six-item tuple")
    commit_sha, path, mode, object_type, object_oid, raw_bytes = raw_blob
    _require_reviewer_git_sha1_v1(commit_sha, f"{field} commit")
    if expected_commit is not None and commit_sha != expected_commit:
        raise ValueError(f"{field} origin commit drifted")
    _require_repo_relative_posix_path_v1(path, f"{field} path")
    if mode not in ("100644", "100755") or type(mode) is not str:
        raise ValueError(f"{field} mode is not a regular executable/blob mode")
    if object_type != "blob" or type(object_type) is not str:
        raise ValueError(f"{field} object type is not blob")
    _require_reviewer_git_sha1_v1(object_oid, f"{field} object OID")
    if type(raw_bytes) is not bytes:
        raise TypeError(f"{field} body must be exact bytes")
    if object_oid != _git_blob_oid_v1(raw_bytes):
        raise ValueError(f"{field} object OID/bytes mismatch")
    return raw_blob


def _validate_ordered_git_tree_blobs_v1(
    raw_blobs,
    field,
    *,
    expected_commit=None,
):
    if type(raw_blobs) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    validated = []
    paths = set()
    for ordinal, blob in enumerate(raw_blobs):
        checked = _validate_git_tree_blob_observation_v1(
            blob,
            f"{field} {ordinal}",
            expected_commit=expected_commit,
        )
        if checked[1] in paths:
            raise ValueError(f"{field} has a duplicate path")
        paths.add(checked[1])
        validated.append(checked)
    if tuple(validated) != tuple(
        sorted(validated, key=lambda blob: blob[1].encode("utf-8"))
    ):
        raise ValueError(f"{field} is not in raw path-byte order")
    return tuple(validated)


def _reviewer_origin_blob_maps_v1(
    *,
    common_commit_sha,
    route_manifests,
    common_origin_blobs,
    route_origin_blobs,
):
    common = _validate_ordered_git_tree_blobs_v1(
        common_origin_blobs,
        "reviewer common origin",
        expected_commit=common_commit_sha,
    )
    common_by_path = {blob[1]: blob for blob in common}
    if any(
        path not in common_by_path for path in _REVIEWER_COMMON_ORIGIN_EXACT_PATHS_V1
    ):
        raise ValueError("reviewer common origin omits an exact blob path")
    if any(
        common_by_path[path][2] != "100644"
        for path in _REVIEWER_COMMON_ORIGIN_EXACT_PATHS_V1
    ):
        raise ValueError("reviewer common exact origin mode drifted")
    rulespace_paths = tuple(
        path for path in common_by_path if path.startswith("rulespace_v3/")
    )
    if set(rulespace_paths) != {
        path for path in common_by_path if path.startswith("rulespace_v3/")
    } or not {
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
    }.issubset(rulespace_paths):
        raise ValueError("reviewer common rulespace subtree is incomplete")
    allowed_common_paths = set(_REVIEWER_COMMON_ORIGIN_EXACT_PATHS_V1).union(
        rulespace_paths
    )
    if set(common_by_path) != allowed_common_paths:
        raise ValueError("reviewer common origin has an extra scoped path")

    if type(route_origin_blobs) is not tuple or len(route_origin_blobs) != 3:
        raise TypeError("reviewer route origins must be an exact three-item tuple")
    route_by_path = {}
    for ordinal, (entry, manifest, blob) in enumerate(
        zip(_ROUTE_STATIC_REGISTRY_V1, route_manifests, route_origin_blobs)
    ):
        if type(manifest) is not dict or manifest.get("route_id") != entry[0]:
            raise ValueError("reviewer route manifest order drifted")
        checked = _validate_git_tree_blob_observation_v1(
            blob,
            f"reviewer route origin {ordinal}",
            expected_commit=manifest.get("route_commit_sha"),
        )
        if checked[1] != entry[3] or checked[2] != "100644":
            raise ValueError("reviewer route origin path/mode drifted")
        route_by_path[checked[1]] = checked
    if tuple(route_by_path) != tuple(entry[3] for entry in _ROUTE_STATIC_REGISTRY_V1):
        raise ValueError("reviewer route origin order drifted")
    return common_by_path, route_by_path


def _reviewer_namespace_observation_passes_v1(raw_body):
    if type(raw_body) is not dict or tuple(raw_body) != (
        _REVIEWER_NAMESPACE_OBSERVATION_FIELDS_V1
    ):
        return False
    return (
        type(raw_body["fresh_export_root_count"]) is int
        and raw_body["fresh_export_root_count"] == 1
        and raw_body["experiments_init_present"] is False
        and type(raw_body["experiments_namespace_portion_count"]) is int
        and raw_body["experiments_namespace_portion_count"] == 1
        and type(raw_body["shadowing_paths"]) is list
        and not raw_body["shadowing_paths"]
    )


def _reviewer_static_surface_from_tree_map_v1(
    *,
    evidence_commit_sha,
    common_commit_sha,
    route_manifests,
    tree_by_path,
    production_blobs,
):
    executed_paths = (
        "experiments/v3m0_b7_schema_lab/__init__.py",
        "experiments/v3m0_b7_schema_lab/common.py",
        "experiments/v3m0_b7_schema_lab/compare.py",
        *(entry[3] for entry in _ROUTE_STATIC_REGISTRY_V1),
        "rulespace_v3/__init__.py",
        "rulespace_v3/b7_replay_core_v1.py",
    )
    source_blobs = tuple(
        (
            evidence_commit_sha,
            path,
            tree_by_path[path][2],
            tree_by_path[path][5],
        )
        for path in executed_paths
    )
    return validate_reviewer_child_static_surface_v1(
        source_commit_sha=evidence_commit_sha,
        common_commit_sha=common_commit_sha,
        route_manifests=route_manifests,
        source_blobs=source_blobs,
        production_blobs=production_blobs,
    )


def _reviewer_source_memberships_v1(
    static_surface,
    candidate_by_path,
    common_origin_by_path,
    route_origin_by_path,
):
    scan_by_path = {
        row["path"]: row["static_scan_sha"]
        for row in static_surface["module_static_scan_records"]
    }
    groups = [
        (role, tuple(static_surface["ordered_executed_module_paths"]))
        for role in static_surface["ordered_role_ids"]
    ]
    groups.extend((entry[0], (entry[3],)) for entry in _ROUTE_STATIC_REGISTRY_V1)
    records = []
    for group, paths in groups:
        for ordinal, path in enumerate(paths):
            candidate = candidate_by_path[path]
            if path in route_origin_by_path:
                origin_kind = "ROUTE"
                origin = route_origin_by_path[path]
            else:
                origin_kind = "COMMON"
                origin = common_origin_by_path[path]
            record = {
                "role_or_route_id": group,
                "execution_ordinal": ordinal,
                "path": path,
                "candidate_mode": candidate[2],
                "candidate_blob_oid": candidate[4],
                "origin_kind": origin_kind,
                "origin_commit": origin[0],
                "origin_path": origin[1],
                "origin_mode": origin[2],
                "origin_blob_oid": origin[4],
                "static_scan_sha": scan_by_path[path],
            }
            if tuple(record) != _REVIEWER_SOURCE_MEMBERSHIP_FIELDS_V1:
                raise RuntimeError("reviewer source membership field order drifted")
            records.append(record)
    return records


def validate_reviewer_executable_source_origin_v1(
    *,
    evidence_commit_sha,
    common_commit_sha,
    route_manifests,
    evidence_blobs,
    common_origin_blobs,
    route_origin_blobs,
    production_blobs,
    namespace_observation,
):
    """Totalize E-versus-origin source closure without reading or spawning."""

    _require_reviewer_git_sha1_v1(evidence_commit_sha, "reviewer evidence commit")
    _require_reviewer_git_sha1_v1(common_commit_sha, "reviewer common commit")
    if type(route_manifests) is not tuple or len(route_manifests) != 3:
        raise TypeError("reviewer route manifests must be an exact three-item tuple")
    common_origins, route_origins = _reviewer_origin_blob_maps_v1(
        common_commit_sha=common_commit_sha,
        route_manifests=route_manifests,
        common_origin_blobs=common_origin_blobs,
        route_origin_blobs=route_origin_blobs,
    )
    declared_origins = {**common_origins, **route_origins}
    reviewed_surface = _reviewer_static_surface_from_tree_map_v1(
        evidence_commit_sha=evidence_commit_sha,
        common_commit_sha=common_commit_sha,
        route_manifests=route_manifests,
        tree_by_path=declared_origins,
        production_blobs=production_blobs,
    )
    expected_memberships = _reviewer_source_memberships_v1(
        reviewed_surface,
        declared_origins,
        common_origins,
        route_origins,
    )
    reviewed_root = canonical_sha_v1(expected_memberships)

    observed_memberships = None
    observed_root = None
    all_origin_predicates = False
    try:
        evidence = _validate_ordered_git_tree_blobs_v1(
            evidence_blobs,
            "reviewer evidence tree",
            expected_commit=evidence_commit_sha,
        )
        evidence_by_path = {blob[1]: blob for blob in evidence}
        if set(evidence_by_path) != set(declared_origins):
            raise ValueError("reviewer evidence scoped tree differs from origins")
        lab_paths = tuple(
            path
            for path in evidence_by_path
            if path.startswith("experiments/v3m0_b7_schema_lab/")
        )
        expected_lab_paths = (
            "experiments/v3m0_b7_schema_lab/__init__.py",
            "experiments/v3m0_b7_schema_lab/a_flat.py",
            "experiments/v3m0_b7_schema_lab/b_progress.py",
            "experiments/v3m0_b7_schema_lab/c_union.py",
            "experiments/v3m0_b7_schema_lab/common.py",
            "experiments/v3m0_b7_schema_lab/compare.py",
        )
        if tuple(sorted(lab_paths, key=lambda value: value.encode("utf-8"))) != (
            expected_lab_paths
        ):
            raise ValueError("reviewer lab package does not have exactly six leaves")
        if any(evidence_by_path[path][2] != "100644" for path in expected_lab_paths):
            raise ValueError("reviewer lab package leaf mode drifted")
        if not _reviewer_namespace_observation_passes_v1(namespace_observation):
            raise ValueError("reviewer namespace observation failed")
        observed_surface = _reviewer_static_surface_from_tree_map_v1(
            evidence_commit_sha=evidence_commit_sha,
            common_commit_sha=common_commit_sha,
            route_manifests=route_manifests,
            tree_by_path=evidence_by_path,
            production_blobs=production_blobs,
        )
        observed_memberships = _reviewer_source_memberships_v1(
            observed_surface,
            evidence_by_path,
            common_origins,
            route_origins,
        )
        observed_root = canonical_sha_v1(observed_memberships)
        all_origin_predicates = all(
            evidence_by_path[path][2:] == origin[2:]
            for path, origin in declared_origins.items()
        )
    except (TypeError, ValueError, SyntaxError, UnicodeError):
        observed_memberships = None
        observed_root = None
        all_origin_predicates = False

    passed = (
        observed_root is not None
        and observed_root == reviewed_root
        and all_origin_predicates
    )
    return {
        "reviewed_executable_source_closure_sha": reviewed_root,
        "observed_executable_source_closure_sha": observed_root,
        "executable_source_origin_precheck_passed": passed,
        "ordered_expected_memberships": expected_memberships,
        "ordered_observed_memberships": observed_memberships,
        "all_path_mode_type_oid_byte_namespace_predicates_passed": (
            all_origin_predicates
        ),
    }


_REVIEWER_REASON_ORDER_V1 = (
    "REVIEW_ENVIRONMENT_MISMATCH",
    "REPLAY_SOURCE_MISMATCH",
    "REPLAY_EXECUTABLE_SOURCE_ORIGIN_MISMATCH",
    "REPLAY_INPUT_ROOT_MISMATCH",
    "REPLAY_PROCESS_PRECHECK_FAILED",
    "REPLAY_PROCESS_SPAWN_FAILED",
    "REPLAY_PROCESS_OUTPUT_LIMIT_EXCEEDED",
    "REPLAY_PROCESS_TIMED_OUT",
    "REPLAY_PROCESS_SIGNALED",
    "REPLAY_PROCESS_NONZERO",
    "REPLAY_PROCESS_CLEANUP_DEADLINE_EXCEEDED",
    "REPLAY_EXPORT_CLEANUP_FAILED",
    "REPLAY_STDOUT_NOT_CANONICAL_REPORT",
    "REPLAY_REPORT_IDENTITY_MISMATCH",
    "REPLAY_D0_DECISION_MISMATCH",
    "REPLAY_D1_DECISION_MISMATCH",
    "REPLAY_SURVIVOR_MISMATCH",
    "REPLAY_WINNER_MISMATCH",
)
_REPLAY_INPUT_PROJECTION_FIELDS_V1 = (
    "reviewer_role",
    "review_protocol_id",
    "reviewed_lab_evidence_commit_sha",
    "review_environment_manifest_sha",
    "reviewed_d0_result_raw_sha256",
    "reviewed_d0_result_sha",
    "reviewed_d0_decision_payload_sha",
    "reviewed_d1_result_raw_sha256",
    "reviewed_d1_result_sha",
    "reviewed_d1_decision_payload_sha",
    "reviewed_common_commit_sha",
    "reviewed_route_commit_shas",
    "reviewed_corpus_spec_sha",
    "reviewed_mutation_universe_sha",
    "reviewed_metric_spec_sha",
    "reviewed_compare_source_sha256",
    "reviewed_executable_source_closure_sha",
    "replay_source_sha256",
)
_REVIEW_PROCESS_OBSERVATION_FIELDS_V1 = (
    "termination_kind",
    "exit_code",
    "signal_number",
    "stdout_bytes",
    "stderr_bytes",
    "cleanup_deadline_passed",
    "export_cleanup_passed",
    "required_input_precheck_passed",
)


def _reviewer_protocol_v1(role):
    protocols = {
        "CORPUS_REPLAY": ("v3m0-b7-corpus-replay-v2", "review-corpus"),
        "METRIC_REPLAY": ("v3m0-b7-metric-replay-v2", "review-metric"),
    }
    if type(role) is not str or role not in protocols:
        raise ValueError("reviewer role is not frozen")
    return protocols[role]


def _decode_reviewer_report_v1(stdout_bytes):
    if (
        type(stdout_bytes) is not bytes
        or not stdout_bytes.endswith(b"\n")
        or b"\n" in stdout_bytes[:-1]
    ):
        return None
    payload = stdout_bytes[:-1]
    try:
        parsed = strict_json_loads_v1(payload)
        if canonical_json_bytes_v1(parsed) != payload:
            return None
        report = _validate_exact_lab_record_v1("B7LabReplayReportV1", parsed)
        output_projection = {key: report[key] for key in tuple(report)[:9]}
        if report["replay_output_root_sha"] != canonical_sha_v1(output_projection):
            return None
        expected_report_sha = canonical_sha_v1(
            {key: value for key, value in report.items() if key != "replay_report_sha"}
        )
        if report["replay_report_sha"] != expected_report_sha:
            return None
        return report
    except (TypeError, ValueError, UnicodeError):
        return None


def _validate_reviewer_process_observation_v1(observation):
    if type(observation) is not dict or tuple(observation) != (
        _REVIEW_PROCESS_OBSERVATION_FIELDS_V1
    ):
        raise TypeError("review process observation shape drifted")
    kind = observation["termination_kind"]
    exit_code = observation["exit_code"]
    signal_number = observation["signal_number"]
    stdout = observation["stdout_bytes"]
    stderr = observation["stderr_bytes"]
    if type(stdout) is not bytes or type(stderr) is not bytes:
        raise TypeError("review process streams must be exact bytes")
    for field in (
        "cleanup_deadline_passed",
        "export_cleanup_passed",
        "required_input_precheck_passed",
    ):
        if type(observation[field]) is not bool:
            raise TypeError(f"review process {field} must be an exact bool")
    if kind == "EXITED":
        normalized = type(exit_code) is int and exit_code >= 0 and signal_number is None
    elif kind == "SIGNALED":
        normalized = (
            exit_code is None and type(signal_number) is int and signal_number > 0
        )
    elif kind in ("PRECHECK_FAILED", "SPAWN_FAILED"):
        normalized = (
            exit_code is None
            and signal_number is None
            and stdout == b""
            and stderr == b""
        )
    elif kind in ("OUTPUT_LIMIT_EXCEEDED", "TIMED_OUT"):
        normalized = exit_code is None and signal_number is None
    else:
        normalized = False
    if not normalized:
        raise ValueError("review process outcome normalization drifted")
    return observation


def validate_reviewer_receipt_v1(
    raw_body,
    *,
    evidence_commit_sha,
    validated_d0_result,
    validated_d1_result,
    d0_raw_bytes,
    d1_raw_bytes,
    environment_observation,
    source_origin_observation,
    replay_source_blob,
    process_observation,
):
    """Validate one parent-observed reviewer receipt without spawning a child."""

    receipt = _validate_exact_lab_record_v1("B7LabReviewerReceiptV1", raw_body)
    _require_reviewer_git_sha1_v1(evidence_commit_sha, "reviewed evidence commit")
    if receipt["reviewed_lab_evidence_commit_sha"] != evidence_commit_sha:
        raise ValueError("reviewer receipt evidence commit drifted")
    protocol_id, subcommand = _reviewer_protocol_v1(receipt["reviewer_role"])
    if receipt["review_protocol_id"] != protocol_id:
        raise ValueError("reviewer role/protocol drifted")
    d0 = validated_d0_result
    d1 = validated_d1_result
    if type(d0) is not dict or type(d1) is not dict:
        raise TypeError("reviewer D0/D1 inputs must be validated exact dicts")
    for raw_bytes, expected, label in (
        (d0_raw_bytes, d0, "D0"),
        (d1_raw_bytes, d1, "D1"),
    ):
        parsed = strict_json_loads_v1(raw_bytes)
        if canonical_json_bytes_v1(parsed) != canonical_json_bytes_v1(expected):
            raise ValueError(f"reviewed {label} raw blob body drifted")
    manifests = [row["route_manifest"] for row in d0["ordered_route_results"]]
    expected_joins = (
        ("reviewed_d0_result_raw_sha256", _raw_source_sha256_v1(d0_raw_bytes, "D0")),
        ("reviewed_d0_result_sha", d0["d0_result_sha"]),
        ("reviewed_d0_decision_payload_sha", d0["decision_payload_sha"]),
        ("reviewed_d1_result_raw_sha256", _raw_source_sha256_v1(d1_raw_bytes, "D1")),
        ("reviewed_d1_result_sha", d1["d1_result_sha"]),
        ("reviewed_d1_decision_payload_sha", d1["decision_payload_sha"]),
        ("reviewed_common_commit_sha", d0["common_commit_sha"]),
        ("reviewed_route_commit_shas", [row["route_commit_sha"] for row in manifests]),
        ("reviewed_corpus_spec_sha", d0["corpus_spec_sha"]),
        ("reviewed_mutation_universe_sha", d0["mutation_universe_sha"]),
        ("reviewed_metric_spec_sha", d0["metric_spec_sha"]),
        ("reviewed_compare_source_sha256", d0["compare_source_sha256"]),
    )
    for field, expected in expected_joins:
        if canonical_json_bytes_v1(receipt[field]) != canonical_json_bytes_v1(expected):
            raise ValueError(f"reviewer receipt {field} drifted")
    for field in (
        "common_commit_sha",
        "common_source_sha256",
        "compare_source_sha256",
        "corpus_fixture_raw_sha256",
        "corpus_spec_sha",
        "mutation_universe_sha",
        "metric_spec_sha",
    ):
        if d1[field] != d0[field]:
            raise ValueError(f"reviewed D0/D1 {field} join drifted")
    environment_sha = d1["environment_manifest"]["environment_sha"]
    if d0["environment_manifest"]["environment_sha"] != environment_sha:
        raise ValueError("reviewed D0/D1 environment root drifted")
    if type(environment_observation) is not dict or tuple(environment_observation) != (
        "expected_sha",
        "observed_sha",
        "passed",
    ):
        raise TypeError("review environment observation shape drifted")
    if (
        environment_observation["expected_sha"] != environment_sha
        or receipt["review_environment_manifest_sha"] != environment_sha
        or receipt["observed_review_environment_manifest_sha"]
        != environment_observation["observed_sha"]
        or receipt["review_environment_precheck_passed"]
        is not environment_observation["passed"]
    ):
        raise ValueError("review environment observation join drifted")
    for field in (
        "reviewed_executable_source_closure_sha",
        "observed_executable_source_closure_sha",
        "executable_source_origin_precheck_passed",
    ):
        if receipt[field] != source_origin_observation[field]:
            raise ValueError("reviewer source-origin observation join drifted")
    _require_git_blob_descriptor_v1(replay_source_blob, "reviewer replay source")
    source_commit, source_path, source_mode, source_bytes = replay_source_blob
    source_matches = (
        source_commit == evidence_commit_sha
        and source_path == "experiments/v3m0_b7_schema_lab/compare.py"
        and source_mode == "100644"
        and _raw_source_sha256_v1(source_bytes, "reviewer replay source")
        == receipt["reviewed_compare_source_sha256"]
        == receipt["replay_source_sha256"]
    )
    if receipt["replay_source_path"] != source_path:
        raise ValueError("reviewer replay source path drifted")
    environment = d1["environment_manifest"]
    expected_argv = [
        environment["python_invocation_path"],
        "-s",
        "-m",
        "experiments.v3m0_b7_schema_lab.compare",
        subcommand,
        "--evidence-commit",
        evidence_commit_sha,
        "--reviewed-executable-source-closure-sha",
        receipt["reviewed_executable_source_closure_sha"],
        "--emit-replay-report",
    ]
    if (
        receipt["replay_command_argv"] != expected_argv
        or receipt["fresh_process_protocol_id"]
        != "fresh-python-s-immutable-E-venv-invocation-v2"
    ):
        raise ValueError("reviewer replay command/fresh protocol drifted")
    expected_input_root = canonical_sha_v1(
        {field: receipt[field] for field in _REPLAY_INPUT_PROJECTION_FIELDS_V1}
    )
    if receipt["replay_input_root_sha"] != expected_input_root:
        raise ValueError("reviewer replay input root drifted")
    _validate_reviewer_process_observation_v1(process_observation)
    stdout = process_observation["stdout_bytes"]
    stderr = process_observation["stderr_bytes"]
    for field, expected in (
        ("replay_termination_kind", process_observation["termination_kind"]),
        ("replay_exit_code", process_observation["exit_code"]),
        ("replay_signal_number", process_observation["signal_number"]),
        ("replay_stdout_sha256", _raw_source_sha256_v1(stdout, "stdout")),
        ("replay_stderr_sha256", _raw_source_sha256_v1(stderr, "stderr")),
    ):
        if receipt[field] != expected:
            raise ValueError(f"reviewer process {field} drifted")
    report = _decode_reviewer_report_v1(stdout)
    report_fields = (
        ("observed_report_reviewer_role", "reviewer_role"),
        ("observed_report_review_protocol_id", "review_protocol_id"),
        ("observed_report_lab_evidence_commit_sha", "lab_evidence_commit_sha"),
        ("observed_report_replay_input_root_sha", "replay_input_root_sha"),
        ("replay_output_root_sha", "replay_output_root_sha"),
        ("replayed_d0_decision_payload_sha", "recomputed_d0_decision_payload_sha"),
        ("replayed_d1_decision_payload_sha", "recomputed_d1_decision_payload_sha"),
        ("observed_surviving_route_ids", "observed_surviving_route_ids"),
        (
            "observed_provisional_winner_route_id",
            "observed_provisional_winner_route_id",
        ),
    )
    for receipt_field, report_field in report_fields:
        expected = None if report is None else report[report_field]
        if receipt[receipt_field] != expected:
            raise ValueError("reviewer optional output presence/value drifted")
    predicates = {
        "REVIEW_ENVIRONMENT_MISMATCH": not environment_observation["passed"],
        "REPLAY_SOURCE_MISMATCH": not source_matches,
        "REPLAY_EXECUTABLE_SOURCE_ORIGIN_MISMATCH": not source_origin_observation[
            "executable_source_origin_precheck_passed"
        ],
        "REPLAY_INPUT_ROOT_MISMATCH": (
            not process_observation["required_input_precheck_passed"]
            or (
                report is not None
                and report["replay_input_root_sha"] != expected_input_root
            )
        ),
        "REPLAY_PROCESS_PRECHECK_FAILED": process_observation["termination_kind"]
        == "PRECHECK_FAILED",
        "REPLAY_PROCESS_SPAWN_FAILED": process_observation["termination_kind"]
        == "SPAWN_FAILED",
        "REPLAY_PROCESS_OUTPUT_LIMIT_EXCEEDED": process_observation["termination_kind"]
        == "OUTPUT_LIMIT_EXCEEDED",
        "REPLAY_PROCESS_TIMED_OUT": process_observation["termination_kind"]
        == "TIMED_OUT",
        "REPLAY_PROCESS_SIGNALED": process_observation["termination_kind"]
        == "SIGNALED",
        "REPLAY_PROCESS_NONZERO": process_observation["termination_kind"] == "EXITED"
        and process_observation["exit_code"] != 0,
        "REPLAY_PROCESS_CLEANUP_DEADLINE_EXCEEDED": not process_observation[
            "cleanup_deadline_passed"
        ],
        "REPLAY_EXPORT_CLEANUP_FAILED": not process_observation[
            "export_cleanup_passed"
        ],
        "REPLAY_STDOUT_NOT_CANONICAL_REPORT": report is None,
        "REPLAY_REPORT_IDENTITY_MISMATCH": report is not None
        and (
            report["reviewer_role"] != receipt["reviewer_role"]
            or report["review_protocol_id"] != receipt["review_protocol_id"]
            or report["lab_evidence_commit_sha"] != evidence_commit_sha
        ),
        "REPLAY_D0_DECISION_MISMATCH": report is not None
        and report["recomputed_d0_decision_payload_sha"] != d0["decision_payload_sha"],
        "REPLAY_D1_DECISION_MISMATCH": report is not None
        and report["recomputed_d1_decision_payload_sha"] != d1["decision_payload_sha"],
        "REPLAY_SURVIVOR_MISMATCH": report is not None
        and report["observed_surviving_route_ids"] != d1["surviving_route_ids"],
        "REPLAY_WINNER_MISMATCH": report is not None
        and report["observed_provisional_winner_route_id"]
        != d1["provisional_winner_route_id"],
    }
    expected_reasons = [
        reason for reason in _REVIEWER_REASON_ORDER_V1 if predicates[reason]
    ]
    if receipt["reason_codes"] != expected_reasons:
        raise ValueError("reviewer receipt reason subset/order drifted")
    accept = (
        environment_observation["passed"]
        and source_origin_observation["executable_source_origin_precheck_passed"]
        and not expected_reasons
        and process_observation["termination_kind"] == "EXITED"
        and process_observation["exit_code"] == 0
        and process_observation["signal_number"] is None
        and report is not None
    )
    if receipt["verdict"] != ("ACCEPT" if accept else "REJECT"):
        raise ValueError("reviewer receipt verdict drifted")
    expected_sha = canonical_sha_v1(
        {key: value for key, value in receipt.items() if key != "receipt_sha"}
    )
    if receipt["receipt_sha"] != expected_sha:
        raise ValueError("reviewer receipt self hash drifted")
    return receipt


_REVIEWER_RECEIPT_CONTEXT_FIELDS_V1 = (
    "environment_observation",
    "source_origin_observation",
    "replay_source_blob",
    "process_observation",
)


def _validate_terminal_review_base_v1(
    record,
    *,
    evidence_commit_sha,
    validated_d0_result,
    validated_d1_result,
    d0_raw_bytes,
    d1_raw_bytes,
):
    _require_reviewer_git_sha1_v1(evidence_commit_sha, "review evidence commit")
    if record["lab_evidence_commit_sha"] != evidence_commit_sha:
        raise ValueError("terminal review evidence commit drifted")
    d0 = validated_d0_result
    d1 = validated_d1_result
    if type(d0) is not dict or type(d1) is not dict:
        raise TypeError("terminal review D0/D1 inputs must be validated dicts")
    for raw_bytes, expected, label in (
        (d0_raw_bytes, d0, "D0"),
        (d1_raw_bytes, d1, "D1"),
    ):
        parsed = strict_json_loads_v1(raw_bytes)
        if canonical_json_bytes_v1(parsed) != canonical_json_bytes_v1(expected):
            raise ValueError(f"terminal review {label} blob body drifted")
    d0_raw_sha = _raw_source_sha256_v1(d0_raw_bytes, "terminal D0")
    d1_raw_sha = _raw_source_sha256_v1(d1_raw_bytes, "terminal D1")
    for field, expected in (
        ("d0_result_raw_sha256", d0_raw_sha),
        ("d0_result_sha", d0["d0_result_sha"]),
        ("d0_decision_payload_sha", d0["decision_payload_sha"]),
        ("d1_result_raw_sha256", d1_raw_sha),
        ("d1_result_sha", d1["d1_result_sha"]),
        ("d1_decision_payload_sha", d1["decision_payload_sha"]),
    ):
        if record[field] != expected:
            raise ValueError(f"terminal review {field} drifted")
    for field, expected in (
        ("d0_result_raw_sha256", d0_raw_sha),
        ("d0_result_sha", d0["d0_result_sha"]),
        ("d0_decision_payload_sha", d0["decision_payload_sha"]),
    ):
        if d1[field] != expected:
            raise ValueError(f"terminal review D1 {field} join drifted")
    shared_fields = (
        "common_commit_sha",
        "common_source_sha256",
        "compare_source_sha256",
        "corpus_fixture_raw_sha256",
        "corpus_spec_sha",
        "mutation_universe_sha",
        "metric_spec_sha",
    )
    for field in shared_fields:
        if d1[field] != d0[field] or record[field] != d0[field]:
            raise ValueError(f"terminal review {field} join drifted")
    d0_environment = d0["environment_manifest"]
    d1_environment = d1["environment_manifest"]
    if canonical_json_bytes_v1(d1_environment) != canonical_json_bytes_v1(
        d0_environment
    ):
        raise ValueError("terminal review D0/D1 environment body drifted")
    if record["environment_manifest_sha"] != d0_environment["environment_sha"]:
        raise ValueError("terminal review environment root drifted")
    d0_rows = d0["ordered_route_results"]
    d1_rows = d1["ordered_route_results"]
    if type(d0_rows) is not list or type(d1_rows) is not list:
        raise TypeError("terminal review route results must be exact lists")
    d0_manifests = [row["route_manifest"] for row in d0_rows]
    if len(d0_manifests) != 3:
        raise ValueError("terminal review must bind exactly three D0 routes")
    d0_by_route = {manifest["route_id"]: manifest for manifest in d0_manifests}
    if len(d0_by_route) != len(d0_manifests):
        raise ValueError("terminal review D0 route IDs are not unique")
    d1_route_ids = [row["route_manifest"]["route_id"] for row in d1_rows]
    if d1_route_ids != d0["surviving_route_ids"]:
        raise ValueError("terminal review D1 route order drifted")
    for row in d1_rows:
        manifest = row["route_manifest"]
        if manifest["route_id"] not in d0_by_route or canonical_json_bytes_v1(
            manifest
        ) != canonical_json_bytes_v1(d0_by_route[manifest["route_id"]]):
            raise ValueError("terminal review D1 route manifest drifted")
    route_commits = [manifest["route_commit_sha"] for manifest in d0_manifests]
    route_sources = [manifest["route_source_sha256"] for manifest in d0_manifests]
    if record["ordered_route_commit_shas"] != route_commits:
        raise ValueError("terminal review route commit order drifted")
    if record["ordered_route_source_sha256s"] != route_sources:
        raise ValueError("terminal review route source order drifted")
    winner = d1["provisional_winner_route_id"]
    if (
        d1["tie_detected"] is not False
        or type(winner) is not str
        or winner not in d1["surviving_route_ids"]
        or winner not in d0_by_route
        or record["provisional_winner_route_id"] != winner
    ):
        raise ValueError("terminal review does not have a unique D1 winner")
    return d0, d1, d0_by_route, d0_by_route[winner]


def _validate_terminal_reviewer_receipts_v1(
    receipts,
    contexts,
    *,
    evidence_commit_sha,
    validated_d0_result,
    validated_d1_result,
    d0_raw_bytes,
    d1_raw_bytes,
):
    if type(receipts) is not list or len(receipts) != 2:
        raise TypeError("terminal review receipts must be an exact pair")
    if type(contexts) is not tuple or len(contexts) != 2:
        raise TypeError("terminal reviewer contexts must be an exact tuple pair")
    validated = []
    for receipt, context in zip(receipts, contexts):
        if type(context) is not dict or tuple(context) != (
            _REVIEWER_RECEIPT_CONTEXT_FIELDS_V1
        ):
            raise TypeError("terminal reviewer observation context drifted")
        validated.append(
            validate_reviewer_receipt_v1(
                receipt,
                evidence_commit_sha=evidence_commit_sha,
                validated_d0_result=validated_d0_result,
                validated_d1_result=validated_d1_result,
                d0_raw_bytes=d0_raw_bytes,
                d1_raw_bytes=d1_raw_bytes,
                **context,
            )
        )
    if [receipt["reviewer_role"] for receipt in validated] != [
        "CORPUS_REPLAY",
        "METRIC_REPLAY",
    ]:
        raise ValueError("terminal reviewer role order drifted")
    if len({receipt["reviewer_id"] for receipt in validated}) != 2:
        raise ValueError("terminal reviewer IDs are not independent")
    closure_roots = {
        receipt["reviewed_executable_source_closure_sha"] for receipt in validated
    }
    if len(closure_roots) != 1:
        raise ValueError("terminal reviewer expected source closures diverged")
    return validated


def validate_selection_review_v1(
    raw_body,
    *,
    evidence_commit_sha,
    validated_d0_result,
    validated_d1_result,
    d0_raw_bytes,
    d1_raw_bytes,
    reviewer_receipt_contexts,
):
    """Validate the success-only two-reviewer schema selection record."""

    selection = _validate_exact_lab_record_v1("B7LabSelectionReviewV1", raw_body)
    _d0, d1, _d0_by_route, winner_manifest = _validate_terminal_review_base_v1(
        selection,
        evidence_commit_sha=evidence_commit_sha,
        validated_d0_result=validated_d0_result,
        validated_d1_result=validated_d1_result,
        d0_raw_bytes=d0_raw_bytes,
        d1_raw_bytes=d1_raw_bytes,
    )
    receipts = _validate_terminal_reviewer_receipts_v1(
        selection["reviewer_receipts"],
        reviewer_receipt_contexts,
        evidence_commit_sha=evidence_commit_sha,
        validated_d0_result=validated_d0_result,
        validated_d1_result=validated_d1_result,
        d0_raw_bytes=d0_raw_bytes,
        d1_raw_bytes=d1_raw_bytes,
    )
    if any(receipt["verdict"] != "ACCEPT" for receipt in receipts):
        raise ValueError("selection requires two ACCEPT reviewer receipts")
    for receipt in receipts:
        if (
            receipt["observed_surviving_route_ids"] != d1["surviving_route_ids"]
            or receipt["observed_provisional_winner_route_id"]
            != d1["provisional_winner_route_id"]
        ):
            raise ValueError("selection reviewer observations drifted")
    expected_selected = (
        ("selected_route_id", winner_manifest["route_id"]),
        ("selected_route_schema_domain", winner_manifest["route_schema_domain"]),
        ("selected_route_commit_sha", winner_manifest["route_commit_sha"]),
        (
            "selected_route_source_sha256",
            winner_manifest["route_source_sha256"],
        ),
    )
    for field, expected in expected_selected:
        if selection[field] != expected:
            raise ValueError(f"selection {field} drifted")
    if (
        selection["review_outcome"] != "UNIQUE_SCHEMA_SELECTED"
        or selection["engineering_disposition"]
        != "B7_UNIQUE_SCHEMA_SELECTED_FOR_IMPLEMENTATION"
        or selection["production_implementation_allowed"] is not True
    ):
        raise ValueError("selection terminal disposition drifted")
    expected_sha = canonical_sha_v1(
        {
            key: value
            for key, value in selection.items()
            if key != "selection_review_sha"
        }
    )
    if selection["selection_review_sha"] != expected_sha:
        raise ValueError("selection review self hash drifted")
    return selection


def validate_review_halt_v1(
    raw_body,
    *,
    evidence_commit_sha,
    validated_d0_result,
    validated_d1_result,
    d0_raw_bytes,
    d1_raw_bytes,
    reviewer_receipt_contexts,
):
    """Validate the failure-only two-reviewer terminal halt record."""

    halt = _validate_exact_lab_record_v1("B7LabReviewHaltV1", raw_body)
    _validate_terminal_review_base_v1(
        halt,
        evidence_commit_sha=evidence_commit_sha,
        validated_d0_result=validated_d0_result,
        validated_d1_result=validated_d1_result,
        d0_raw_bytes=d0_raw_bytes,
        d1_raw_bytes=d1_raw_bytes,
    )
    receipts = _validate_terminal_reviewer_receipts_v1(
        halt["reviewer_receipts"],
        reviewer_receipt_contexts,
        evidence_commit_sha=evidence_commit_sha,
        validated_d0_result=validated_d0_result,
        validated_d1_result=validated_d1_result,
        d0_raw_bytes=d0_raw_bytes,
        d1_raw_bytes=d1_raw_bytes,
    )
    compared_fields = (
        "replayed_d0_decision_payload_sha",
        "replayed_d1_decision_payload_sha",
        "observed_surviving_route_ids",
        "observed_provisional_winner_route_id",
    )
    divergence = any(
        receipts[0][field] is not None
        and receipts[1][field] is not None
        and receipts[0][field] != receipts[1][field]
        for field in compared_fields
    )
    if not divergence and all(receipt["verdict"] == "ACCEPT" for receipt in receipts):
        raise ValueError("review halt requires a rejection or replay divergence")
    expected_reason = "HALT_REVIEW_DIVERGENCE" if divergence else "HALT_REPLAY_MISMATCH"
    if halt["halt_reason"] != expected_reason:
        raise ValueError("review halt reason drifted")
    if halt["production_implementation_allowed"] is not False:
        raise ValueError("review halt cannot authorize production")
    expected_sha = canonical_sha_v1(
        {key: value for key, value in halt.items() if key != "review_halt_sha"}
    )
    if halt["review_halt_sha"] != expected_sha:
        raise ValueError("review halt self hash drifted")
    return halt


_PRODUCTION_HANDOFF_REPOSITORY_OBSERVATION_FIELDS_V1 = (
    "trusted_git_protocol_passed",
    "objects_info_alternates_absent",
    "info_grafts_absent",
    "evidence_commit_object",
    "common_commit_object",
    "ordered_route_commit_objects",
    "common_is_ancestor_of_ordered_routes",
    "ordered_routes_are_ancestors_of_evidence",
    "selection_commit_object",
    "selection_tree_delta",
    "selection_tag_ref_object_oid",
    "selection_tag_object",
    "selection_tag_peeled_target",
    "selection_review_absent_at_evidence",
    "review_halt_absent_at_evidence",
    "review_halt_absent_at_selection",
)
_PRODUCTION_HANDOFF_D0_PATH_V1 = (
    "data/results/experimental/v3m0_b7_schema_lab/d0_comparison.json"
)
_PRODUCTION_HANDOFF_D1_PATH_V1 = (
    "data/results/experimental/v3m0_b7_schema_lab/d1_comparison.json"
)
_PRODUCTION_HANDOFF_SELECTION_PATH_V1 = (
    "data/results/experimental/v3m0_b7_schema_lab/selection_review.json"
)


def _git_object_oid_from_body_v1(object_type, raw_bytes):
    if object_type not in ("commit", "tag") or type(object_type) is not str:
        raise ValueError("handoff Git object type is not frozen")
    if type(raw_bytes) is not bytes:
        raise TypeError("handoff Git object body must be exact bytes")
    header = f"{object_type} {len(raw_bytes)}\0".encode("ascii")
    return _pure_core.hashlib.sha1(header + raw_bytes).hexdigest()


def _validate_git_object_observation_v1(
    observation,
    *,
    expected_oid,
    expected_type,
    field,
):
    if type(observation) is not tuple or len(observation) != 3:
        raise TypeError(f"{field} must be an exact three-item tuple")
    object_oid, object_type, raw_bytes = observation
    _require_reviewer_git_sha1_v1(object_oid, f"{field} OID")
    if object_oid != expected_oid or object_type != expected_type:
        raise ValueError(f"{field} identity/type drifted")
    if object_oid != _git_object_oid_from_body_v1(object_type, raw_bytes):
        raise ValueError(f"{field} OID/body drifted")
    return raw_bytes


def _git_object_headers_v1(raw_bytes, field):
    if type(raw_bytes) is not bytes or b"\x00" in raw_bytes:
        raise TypeError(f"{field} body must be exact non-NUL bytes")
    header_block, separator, _message = raw_bytes.partition(b"\n\n")
    if separator != b"\n\n" or not header_block:
        raise ValueError(f"{field} headers are not terminated")
    headers = []
    for line in header_block.split(b"\n"):
        if line.startswith(b" "):
            if not headers:
                raise ValueError(f"{field} starts with a continuation header")
            headers[-1][1].extend(b"\n" + line[1:])
            continue
        if b" " not in line:
            raise ValueError(f"{field} has an unsupported header line")
        name, value = line.split(b" ", 1)
        try:
            decoded_name = name.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{field} header name is not ASCII") from exc
        headers.append([decoded_name, bytearray(value)])
    return [(name, bytes(value)) for name, value in headers]


def _validate_production_handoff_repository_observation_v1(
    observation,
    *,
    evidence_commit_sha,
    selection_commit_sha,
    tag_object_sha,
    common_commit_sha,
    ordered_route_commit_shas,
):
    if type(observation) is not dict or tuple(observation) != (
        _PRODUCTION_HANDOFF_REPOSITORY_OBSERVATION_FIELDS_V1
    ):
        raise TypeError("production handoff repository observation shape drifted")
    if any(
        observation[field] is not True
        for field in (
            "trusted_git_protocol_passed",
            "objects_info_alternates_absent",
            "info_grafts_absent",
            "selection_review_absent_at_evidence",
            "review_halt_absent_at_evidence",
            "review_halt_absent_at_selection",
        )
    ):
        raise ValueError("production handoff repository guard failed")
    if (
        type(common_commit_sha) is not str
        or type(ordered_route_commit_shas) is not list
        or len(ordered_route_commit_shas) != 3
        or len(set(ordered_route_commit_shas)) != 3
    ):
        raise ValueError("production handoff origin commit set drifted")
    _require_reviewer_git_sha1_v1(common_commit_sha, "handoff common commit")
    for ordinal, route_commit in enumerate(ordered_route_commit_shas):
        _require_reviewer_git_sha1_v1(route_commit, f"handoff route commit {ordinal}")
    _validate_git_object_observation_v1(
        observation["evidence_commit_object"],
        expected_oid=evidence_commit_sha,
        expected_type="commit",
        field="handoff evidence commit object",
    )
    _validate_git_object_observation_v1(
        observation["common_commit_object"],
        expected_oid=common_commit_sha,
        expected_type="commit",
        field="handoff common commit object",
    )
    route_objects = observation["ordered_route_commit_objects"]
    if type(route_objects) is not tuple or len(route_objects) != 3:
        raise TypeError("handoff route commit objects must be an exact tuple")
    for ordinal, (route_commit, route_object) in enumerate(
        zip(ordered_route_commit_shas, route_objects)
    ):
        _validate_git_object_observation_v1(
            route_object,
            expected_oid=route_commit,
            expected_type="commit",
            field=f"handoff route commit object {ordinal}",
        )
    if observation["common_is_ancestor_of_ordered_routes"] != [
        True,
        True,
        True,
    ] or observation["ordered_routes_are_ancestors_of_evidence"] != [True, True, True]:
        raise ValueError("production handoff ancestry observation failed")
    selection_commit_body = _validate_git_object_observation_v1(
        observation["selection_commit_object"],
        expected_oid=selection_commit_sha,
        expected_type="commit",
        field="handoff selection commit object",
    )
    selection_headers = _git_object_headers_v1(
        selection_commit_body,
        "handoff selection commit",
    )
    selection_parents = [value for name, value in selection_headers if name == "parent"]
    if selection_parents != [evidence_commit_sha.encode("ascii")]:
        raise ValueError("production handoff selection parent drifted")
    expected_delta = [
        {
            "status": "A",
            "mode": "100644",
            "path": _PRODUCTION_HANDOFF_SELECTION_PATH_V1,
        }
    ]
    if observation["selection_tree_delta"] != expected_delta:
        raise ValueError("production handoff selection tree delta drifted")
    if observation["selection_tag_ref_object_oid"] != tag_object_sha:
        raise ValueError("production handoff tag ref OID drifted")
    tag_body = _validate_git_object_observation_v1(
        observation["selection_tag_object"],
        expected_oid=tag_object_sha,
        expected_type="tag",
        field="handoff selection tag object",
    )
    tag_headers = _git_object_headers_v1(tag_body, "handoff selection tag")
    required_tag_headers = {
        "object": selection_commit_sha.encode("ascii"),
        "type": b"commit",
        "tag": b"v3m0-b7-schema-selection-v1",
    }
    for name, expected in required_tag_headers.items():
        values = [value for header, value in tag_headers if header == name]
        if values != [expected]:
            raise ValueError(f"production handoff tag {name} header drifted")
    if observation["selection_tag_peeled_target"] != selection_commit_sha:
        raise ValueError("production handoff peeled tag target drifted")
    return observation


def _validate_production_handoff_blob_v1(
    observation,
    *,
    expected_commit,
    expected_path,
    field,
):
    checked = _validate_git_tree_blob_observation_v1(
        observation,
        field,
        expected_commit=expected_commit,
    )
    if checked[1] != expected_path or checked[2] != "100644":
        raise ValueError(f"{field} path/mode drifted")
    return checked[5]


def validate_production_handoff_v1(
    raw_body,
    *,
    evidence_commit_sha,
    selection_commit_sha,
    validated_d0_result,
    validated_d1_result,
    d0_blob_observation,
    d1_blob_observation,
    selection_blob_observation,
    repository_observation,
    reviewer_receipt_contexts,
):
    """Validate the Git-bound, authority-free production handoff record."""

    handoff = _validate_exact_lab_record_v1(
        "B7ProductionHandoffReviewV1",
        raw_body,
    )
    _require_reviewer_git_sha1_v1(evidence_commit_sha, "handoff evidence commit")
    _require_reviewer_git_sha1_v1(selection_commit_sha, "handoff selection commit")
    if (
        handoff["lab_evidence_commit_sha"] != evidence_commit_sha
        or handoff["lab_selection_commit_sha"] != selection_commit_sha
    ):
        raise ValueError("production handoff terminal commit join drifted")
    d0_bytes = _validate_production_handoff_blob_v1(
        d0_blob_observation,
        expected_commit=evidence_commit_sha,
        expected_path=_PRODUCTION_HANDOFF_D0_PATH_V1,
        field="production handoff D0 blob",
    )
    d1_bytes = _validate_production_handoff_blob_v1(
        d1_blob_observation,
        expected_commit=evidence_commit_sha,
        expected_path=_PRODUCTION_HANDOFF_D1_PATH_V1,
        field="production handoff D1 blob",
    )
    selection_bytes = _validate_production_handoff_blob_v1(
        selection_blob_observation,
        expected_commit=selection_commit_sha,
        expected_path=_PRODUCTION_HANDOFF_SELECTION_PATH_V1,
        field="production handoff selection blob",
    )
    selection_body = strict_json_loads_v1(selection_bytes)
    selection = validate_selection_review_v1(
        selection_body,
        evidence_commit_sha=evidence_commit_sha,
        validated_d0_result=validated_d0_result,
        validated_d1_result=validated_d1_result,
        d0_raw_bytes=d0_bytes,
        d1_raw_bytes=d1_bytes,
        reviewer_receipt_contexts=reviewer_receipt_contexts,
    )
    d0 = validated_d0_result
    d1 = validated_d1_result
    manifests = [row["route_manifest"] for row in d0["ordered_route_results"]]
    _validate_production_handoff_repository_observation_v1(
        repository_observation,
        evidence_commit_sha=evidence_commit_sha,
        selection_commit_sha=selection_commit_sha,
        tag_object_sha=handoff["lab_evidence_tag_object_sha"],
        common_commit_sha=d0["common_commit_sha"],
        ordered_route_commit_shas=[
            manifest["route_commit_sha"] for manifest in manifests
        ],
    )
    if (
        handoff["git_object_verifier_protocol_id"]
        != "v3m0-b7-schema-selection-git-object-handoff-v1"
        or handoff["git_object_format"] != "sha1"
        or handoff["lab_evidence_tag"] != "v3m0-b7-schema-selection-v1"
    ):
        raise ValueError("production handoff Git protocol drifted")
    expected_joins = (
        ("d0_result_path", _PRODUCTION_HANDOFF_D0_PATH_V1),
        ("d0_result_raw_sha256", _raw_source_sha256_v1(d0_bytes, "handoff D0")),
        ("d0_result_sha", d0["d0_result_sha"]),
        ("d0_decision_payload_sha", d0["decision_payload_sha"]),
        ("d1_result_path", _PRODUCTION_HANDOFF_D1_PATH_V1),
        ("d1_result_raw_sha256", _raw_source_sha256_v1(d1_bytes, "handoff D1")),
        ("d1_result_sha", d1["d1_result_sha"]),
        ("d1_decision_payload_sha", d1["decision_payload_sha"]),
        ("selection_review_path", _PRODUCTION_HANDOFF_SELECTION_PATH_V1),
        (
            "selection_review_raw_sha256",
            _raw_source_sha256_v1(selection_bytes, "handoff selection"),
        ),
        ("selection_review_sha", selection["selection_review_sha"]),
        ("selected_route_id", selection["selected_route_id"]),
        (
            "selected_route_schema_domain",
            selection["selected_route_schema_domain"],
        ),
        ("selected_route_commit_sha", selection["selected_route_commit_sha"]),
        (
            "selected_route_source_sha256",
            selection["selected_route_source_sha256"],
        ),
        (
            "ordered_reviewer_receipt_shas",
            [receipt["receipt_sha"] for receipt in selection["reviewer_receipts"]],
        ),
    )
    for field, expected in expected_joins:
        if canonical_json_bytes_v1(handoff[field]) != canonical_json_bytes_v1(expected):
            raise ValueError(f"production handoff {field} drifted")
    expected_sha = canonical_sha_v1(
        {key: value for key, value in handoff.items() if key != "handoff_sha"}
    )
    if handoff["handoff_sha"] != expected_sha:
        raise ValueError("production handoff self hash drifted")
    return handoff


def _validate_e07_static_domain_v1(route_manifest, route_blob, production_blobs):
    manifest = validate_route_static_surface_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    entry = _route_static_registry_entry_v1(manifest["route_id"])
    exact_api = (
        manifest["encoder_symbol"] == "encode_normalized_transcript"
        and manifest["verifier_decoder_symbol"] == "verify_and_decode_route_wire"
        and manifest["input_schema_version"]
        == "experimental.v3m0.b7.normalized-transcript.v1"
        and manifest["output_schema_version"] == entry[4]
    )
    no_callback_surface = exact_api
    no_authority_surface = (
        manifest["authority_surface_count"] == 0
        and manifest["wrapper_surface_count"] == 0
    )
    zero_surface_counts = (
        type(manifest["authority_surface_count"]) is int
        and type(manifest["wrapper_surface_count"]) is int
        and manifest["authority_surface_count"] == 0
        and manifest["wrapper_surface_count"] == 0
    )
    normalized = {
        "gate_domain_id": "v3m0-b7-e07-route-api-static-surface.v1",
        "route_id": manifest["route_id"],
        "route_manifest_sha": manifest["route_manifest_sha"],
        "route_commit_sha": manifest["route_commit_sha"],
        "route_source_path": manifest["route_source_path"],
        "route_source_sha256": manifest["route_source_sha256"],
        "public_exports_exact": list(_ROUTE_PUBLIC_EXPORTS_V1),
        "encoder_symbol": manifest["encoder_symbol"],
        "verifier_decoder_symbol": manifest["verifier_decoder_symbol"],
        "input_schema_version": manifest["input_schema_version"],
        "output_schema_version": manifest["output_schema_version"],
        "static_api_scan_sha": manifest["static_api_scan_sha"],
        "static_authority_surface_scan_sha": manifest[
            "static_authority_surface_scan_sha"
        ],
        "authority_surface_count": manifest["authority_surface_count"],
        "wrapper_surface_count": manifest["wrapper_surface_count"],
    }
    return {
        "domain_root_sha": canonical_sha_v1(normalized),
        "predicate_results": (
            exact_api,
            no_callback_surface,
            no_authority_surface,
            zero_surface_counts,
        ),
        "normalized": normalized,
        "validated_route_manifest": manifest,
    }


def build_gate_e07_v1(*, phase, route_manifest, route_blob, production_blobs):
    """Build E07 only from the frozen route API/static-surface scan."""

    domain = _validate_e07_static_domain_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    return build_gate_outcome_v1(
        gate_id="E07",
        phase=phase,
        route_id=domain["validated_route_manifest"]["route_id"],
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e07_v1(
    raw_body,
    *,
    route_manifest,
    route_blob,
    production_blobs,
):
    """Reject E07 unless the frozen static scanner reproduces its report."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E07":
        raise ValueError("E07 validator received another gate")
    domain = _validate_e07_static_domain_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    manifest = domain["validated_route_manifest"]
    if (
        observed["observation"]["route_id"] != manifest["route_id"]
        or observed["phase"] not in _gate_contract_v1("E07")[1]
    ):
        raise ValueError("E07 phase or route drifted")
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


def _validate_e08_static_domain_v1(route_manifest, route_blob, production_blobs):
    manifest = validate_route_static_surface_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    route_outside_production_roots = all(
        manifest["route_source_path"] != root
        and not manifest["route_source_path"].startswith(root + "/")
        for root in _ROUTE_PRODUCTION_ROOTS_V1
    )
    normalized = {
        "gate_domain_id": "v3m0-b7-e08-import-source-closure.v1",
        "route_id": manifest["route_id"],
        "route_manifest_sha": manifest["route_manifest_sha"],
        "route_commit_sha": manifest["route_commit_sha"],
        "route_module": manifest["route_module"],
        "route_source_path": manifest["route_source_path"],
        "route_source_sha256": manifest["route_source_sha256"],
        "production_scan_roots": list(_ROUTE_PRODUCTION_ROOTS_V1),
        "static_import_scan_sha": manifest["static_import_scan_sha"],
        "production_import_scan_sha": manifest["production_import_scan_sha"],
        "production_imported_by_route": manifest["production_imported_by_route"],
        "route_imported_by_production": manifest["route_imported_by_production"],
        "route_outside_production_scan_roots": route_outside_production_roots,
    }
    return {
        "domain_root_sha": canonical_sha_v1(normalized),
        "predicate_results": (
            manifest["production_imported_by_route"] is False,
            manifest["route_imported_by_production"] is False,
            route_outside_production_roots,
        ),
        "normalized": normalized,
        "validated_route_manifest": manifest,
    }


def build_gate_e08_v1(*, phase, route_manifest, route_blob, production_blobs):
    """Build E08 only from the frozen import/source-closure scan."""

    domain = _validate_e08_static_domain_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    return build_gate_outcome_v1(
        gate_id="E08",
        phase=phase,
        route_id=domain["validated_route_manifest"]["route_id"],
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e08_v1(
    raw_body,
    *,
    route_manifest,
    route_blob,
    production_blobs,
):
    """Reject E08 unless the frozen import scanner reproduces its report."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E08":
        raise ValueError("E08 validator received another gate")
    domain = _validate_e08_static_domain_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    manifest = domain["validated_route_manifest"]
    if (
        observed["observation"]["route_id"] != manifest["route_id"]
        or observed["phase"] not in _gate_contract_v1("E08")[1]
    ):
        raise ValueError("E08 phase or route drifted")
    return validate_gate_outcome_v1(
        observed,
        expected_domain_root_sha=domain["domain_root_sha"],
        expected_predicate_results=list(domain["predicate_results"]),
    )


_D0_GATE_INPUT_FIELDS_V1 = (
    "ordered_legal_replays",
    "ordered_mutation_probes",
    "ordered_invalid_presence_probes",
)
_D0_GATE_ORDER_V1 = ("E01", "E02", "E03", "E04", "E06", "E07", "E08")


def _validate_d0_gate_inputs_v1(raw_body):
    inputs = _require_exact_ordered_dict_v1(
        raw_body,
        _D0_GATE_INPUT_FIELDS_V1,
        "D0 gate inputs",
    )
    if type(inputs["ordered_legal_replays"]) is not list:
        raise TypeError("D0 legal replay input must be an exact list")
    for field in (
        "ordered_mutation_probes",
        "ordered_invalid_presence_probes",
    ):
        source = inputs[field]
        if type(source) is list:
            continue
        try:
            iterator = iter(source)
        except TypeError:
            raise TypeError(
                f"D0 gate input {field} must be an exact list or one-shot iterator"
            ) from None
        if iterator is not source:
            raise TypeError(f"D0 gate input {field} iterable must be one-shot")
    return inputs


def _build_gate_from_domain_v1(*, gate_id, phase, route_id, domain):
    return build_gate_outcome_v1(
        gate_id=gate_id,
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def build_d0_route_result_v1(
    *,
    route_manifest,
    route_blob,
    production_blobs,
    validated_corpus_fixture,
    gate_inputs,
):
    """Build one D0 route result only from frozen bytes/blob observations."""

    manifest = validate_route_static_surface_v1(
        route_manifest,
        route_blob,
        production_blobs,
    )
    fixture, source_sets = _validated_d0_fixture_source_domain_v1(
        validated_corpus_fixture
    )
    inputs = _validate_d0_gate_inputs_v1(gate_inputs)
    route_id = manifest["route_id"]
    legal = _validate_legal_replay_domain_v1(
        phase="D0",
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=inputs["ordered_legal_replays"],
    )
    mutation = _validate_mutation_probe_domain_v1(
        phase="D0",
        route_id=route_id,
        validated_corpus_fixture=fixture,
        ordered_mutation_probes=inputs["ordered_mutation_probes"],
    )
    evidence = _derive_e03_domain_from_legal_v1(
        legal_domain=legal,
        ordered_legal_replays=inputs["ordered_legal_replays"],
    )
    invalid = _validate_invalid_presence_domain_v1(
        phase="D0",
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_invalid_presence_probes=inputs["ordered_invalid_presence_probes"],
    )
    presence = _derive_e04_domain_from_legal_and_invalid_v1(
        phase="D0",
        legal_domain=legal,
        ordered_legal_replays=inputs["ordered_legal_replays"],
        invalid_domain=invalid,
    )
    deterministic = _validate_e06_domain_v1(mutation)
    static_api = _validate_e07_static_domain_v1(
        manifest,
        route_blob,
        production_blobs,
    )
    static_import = _validate_e08_static_domain_v1(
        manifest,
        route_blob,
        production_blobs,
    )
    domains = (
        ("E01", legal),
        ("E02", mutation),
        ("E03", evidence),
        ("E04", presence),
        ("E06", deterministic),
        ("E07", static_api),
        ("E08", static_import),
    )
    gate_outcomes = [
        _build_gate_from_domain_v1(
            gate_id=gate_id,
            phase="D0",
            route_id=route_id,
            domain=domain,
        )
        for gate_id, domain in domains
    ]
    if tuple(gate["gate_id"] for gate in gate_outcomes) != _D0_GATE_ORDER_V1:
        raise ValueError("D0 gate builder order drifted")

    if mutation["all_upstream_route_entry_counts_zero"] is not True:
        raise ValueError("upstream-invalid probe entered the route")
    survives = (
        all(gate["passed"] for gate in gate_outcomes)
        and legal["accepted_count"] == 7
        and mutation["mutation_accept_count"] == 0
        and mutation["upstream_invalid_transcript_count"] == 0
        and evidence["evidence_loss_count"] == 0
        and presence["half_pair_state_count"] == 0
    )
    result = {
        "route_result_schema_version": "experimental.v3m0.b7.d0-route-result.v1",
        "route_id": route_id,
        "route_manifest": manifest,
        "route_manifest_sha": manifest["route_manifest_sha"],
        "route_commit_sha": manifest["route_commit_sha"],
        "legal_case_count": 7,
        "legal_case_accept_count": legal["accepted_count"],
        "mutation_probe_count": mutation["mutation_probe_count"],
        "mutation_accept_count": mutation["mutation_accept_count"],
        "upstream_invalid_probe_count": mutation["upstream_invalid_probe_count"],
        "upstream_invalid_transcript_count": mutation[
            "upstream_invalid_transcript_count"
        ],
        "evidence_loss_count": evidence["evidence_loss_count"],
        "constructible_invalid_presence_count": presence["canonical_accept_count"],
        "half_pair_state_count": presence["half_pair_state_count"],
        "gate_outcomes": gate_outcomes,
        "survives_d0": survives,
        "route_result_sha": "",
    }
    _rehash_record_field_v1(result, "route_result_sha")
    return validate_exact_lab_record_v1("B7LabD0RouteResultV1", result)


def validate_d0_route_result_v1(
    raw_body,
    *,
    route_blob,
    production_blobs,
    validated_corpus_fixture,
    gate_inputs,
):
    """Recompute every D0 route join, metric, gate, survival bit and root."""

    observed = validate_exact_lab_record_v1("B7LabD0RouteResultV1", raw_body)
    expected = build_d0_route_result_v1(
        route_manifest=observed["route_manifest"],
        route_blob=route_blob,
        production_blobs=production_blobs,
        validated_corpus_fixture=validated_corpus_fixture,
        gate_inputs=gate_inputs,
    )
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError("D0 route result differs from fresh recomputation")
    return observed


_D0_ROUTE_INPUT_FIELDS_V1 = (
    "route_manifest",
    "route_blob",
    "production_blobs",
    "gate_inputs",
)
_D0_AUXILIARY_BENCHMARK_FIELDS_V1 = (
    "warm_up",
    "repeat",
    "reported_statistics",
    "ordered_route_statistics",
)
_D0_AUXILIARY_REPORTED_STATISTICS_V1 = (
    "median",
    "p95",
    "tracemalloc_peak",
)
_D0_AUXILIARY_ROUTE_STATISTIC_FIELDS_V1 = (
    "route_id",
    "median",
    "p95",
    "tracemalloc_peak",
)
_COMMON_SOURCE_PATH_V1 = "experiments/v3m0_b7_schema_lab/common.py"
_COMPARE_SOURCE_PATH_V1 = "experiments/v3m0_b7_schema_lab/compare.py"


def _validate_d0_route_inputs_v1(raw_inputs, common_commit_sha):
    if type(raw_inputs) is not list or len(raw_inputs) != 3:
        raise TypeError("D0 comparison requires exactly three route inputs")
    validated = []
    for route_id, raw_input in zip(
        (entry[0] for entry in _ROUTE_STATIC_REGISTRY_V1),
        raw_inputs,
    ):
        route_input = _require_exact_ordered_dict_v1(
            raw_input,
            _D0_ROUTE_INPUT_FIELDS_V1,
            "D0 route input",
        )
        manifest = validate_exact_lab_record_v1(
            "B7LabRouteManifestV1",
            route_input["route_manifest"],
        )
        if manifest["route_id"] != route_id:
            raise ValueError("D0 route input order drifted")
        route_blob = _require_git_blob_descriptor_v1(
            route_input["route_blob"],
            "D0 route blob",
        )
        if (
            route_blob[0] != manifest["route_commit_sha"]
            or route_blob[1] != manifest["route_source_path"]
            or route_blob[2] != "100644"
        ):
            raise ValueError("D0 route blob descriptor drifted")
        production_blobs = route_input["production_blobs"]
        if type(production_blobs) is not tuple or not production_blobs:
            raise TypeError("D0 production blobs must be a nonempty exact tuple")
        for ordinal, blob in enumerate(production_blobs):
            checked_blob = _require_git_blob_descriptor_v1(
                blob,
                f"D0 production blob {ordinal}",
            )
            if checked_blob[0] != common_commit_sha or checked_blob[2] != "100644":
                raise ValueError("D0 production blob commit or mode drifted")
        _validate_d0_gate_inputs_v1(route_input["gate_inputs"])
        validated.append(route_input)
    return validated


def _validate_common_compare_blobs_v1(common_blob, compare_blob):
    common_checked = _require_git_blob_descriptor_v1(common_blob, "D0 common blob")
    compare_checked = _require_git_blob_descriptor_v1(compare_blob, "D0 compare blob")
    if (
        common_checked[0] != compare_checked[0]
        or common_checked[1] != _COMMON_SOURCE_PATH_V1
        or compare_checked[1] != _COMPARE_SOURCE_PATH_V1
        or common_checked[2] != "100644"
        or compare_checked[2] != "100644"
    ):
        raise ValueError("D0 common/compare blob identity drifted")
    return common_checked, compare_checked


def _validate_d0_auxiliary_benchmark_v1(raw_benchmark):
    benchmark = _require_exact_ordered_dict_v1(
        raw_benchmark,
        _D0_AUXILIARY_BENCHMARK_FIELDS_V1,
        "D0 auxiliary benchmark",
    )
    if type(benchmark["warm_up"]) is not int or benchmark["warm_up"] != 5:
        raise ValueError("D0 auxiliary benchmark warm-up drifted")
    if type(benchmark["repeat"]) is not int or benchmark["repeat"] != 30:
        raise ValueError("D0 auxiliary benchmark repeat count drifted")
    if (
        type(benchmark["reported_statistics"]) is not list
        or tuple(benchmark["reported_statistics"])
        != _D0_AUXILIARY_REPORTED_STATISTICS_V1
    ):
        raise ValueError("D0 auxiliary reported-statistics protocol drifted")
    route_statistics = benchmark["ordered_route_statistics"]
    if type(route_statistics) is not list or len(route_statistics) != 3:
        raise TypeError("D0 auxiliary route statistics must be an exact triple")
    expected_route_ids = tuple(entry[0] for entry in _ROUTE_STATIC_REGISTRY_V1)
    for expected_route_id, raw_statistic in zip(expected_route_ids, route_statistics):
        statistic = _require_exact_ordered_dict_v1(
            raw_statistic,
            _D0_AUXILIARY_ROUTE_STATISTIC_FIELDS_V1,
            "D0 auxiliary route statistic",
        )
        if statistic["route_id"] != expected_route_id:
            raise ValueError("D0 auxiliary route statistic order drifted")
        for field in ("median", "p95"):
            if type(statistic[field]) is not float or statistic[field] < 0.0:
                raise TypeError(
                    f"D0 auxiliary route statistic {field} must be a nonnegative float"
                )
        if statistic["p95"] < statistic["median"]:
            raise ValueError("D0 auxiliary p95 must not be below its median")
        if (
            type(statistic["tracemalloc_peak"]) is not int
            or statistic["tracemalloc_peak"] < 0
        ):
            raise TypeError(
                "D0 auxiliary tracemalloc peak must be a nonnegative exact int"
            )
    canonical_json_bytes_v1(benchmark)
    return _detach_json_v1(benchmark)


def build_d0_comparison_v1(
    *,
    corpus_fixture_raw_bytes,
    common_blob,
    compare_blob,
    python_identity_observation,
    python_probe_result,
    ordered_route_inputs,
    auxiliary_benchmark,
):
    """Build D0 by revalidating one V2 corpus and all immutable blob inputs."""

    if type(corpus_fixture_raw_bytes) is not bytes:
        raise TypeError("D0 corpus fixture input must be exact bytes")
    parsed_fixture = strict_json_loads_v1(corpus_fixture_raw_bytes)
    if type(parsed_fixture) is not dict:
        raise TypeError("D0 corpus fixture bytes must decode to an exact object")
    common_checked, compare_checked = _validate_common_compare_blobs_v1(
        common_blob,
        compare_blob,
    )
    fixture = validate_corpus_fixture_v2(
        parsed_fixture,
        common_checked[3],
        compare_checked[3],
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
    )
    if canonical_json_bytes_v1(fixture) != canonical_json_bytes_v1(parsed_fixture):
        raise ValueError("validated D0 corpus fixture body was substituted")
    route_inputs = _validate_d0_route_inputs_v1(
        ordered_route_inputs,
        common_checked[0],
    )
    route_results = []
    expected_manifest_joins = {
        "common_commit_sha": common_checked[0],
        "common_source_sha256": _raw_source_sha256_v1(
            common_checked[3],
            "common",
        ),
        "compare_source_sha256": _raw_source_sha256_v1(
            compare_checked[3],
            "compare",
        ),
        "corpus_spec_sha": fixture["corpus_spec"]["corpus_spec_sha"],
        "mutation_universe_sha": fixture["mutation_universe"]["mutation_universe_sha"],
        "metric_spec_sha": fixture["metric_spec"]["metric_spec_sha"],
    }
    for route_input in route_inputs:
        result = build_d0_route_result_v1(
            route_manifest=route_input["route_manifest"],
            route_blob=route_input["route_blob"],
            production_blobs=route_input["production_blobs"],
            validated_corpus_fixture=fixture,
            gate_inputs=route_input["gate_inputs"],
        )
        manifest = result["route_manifest"]
        for field, expected in expected_manifest_joins.items():
            if manifest[field] != expected:
                raise ValueError(f"D0 route manifest {field} join drifted")
        route_results.append(result)
    expected_route_ids = tuple(entry[0] for entry in _ROUTE_STATIC_REGISTRY_V1)
    if tuple(result["route_id"] for result in route_results) != expected_route_ids:
        raise ValueError("D0 route result order drifted")
    survivors = [
        result["route_id"] for result in route_results if result["survives_d0"]
    ]
    benchmark = _validate_d0_auxiliary_benchmark_v1(auxiliary_benchmark)
    result = {
        "d0_result_schema_version": "experimental.v3m0.b7.d0-comparison.v1",
        "common_commit_sha": common_checked[0],
        "common_source_sha256": expected_manifest_joins["common_source_sha256"],
        "compare_source_sha256": expected_manifest_joins["compare_source_sha256"],
        "corpus_fixture_raw_sha256": _pure_core.hashlib.sha256(
            corpus_fixture_raw_bytes
        ).hexdigest(),
        "corpus_spec_sha": expected_manifest_joins["corpus_spec_sha"],
        "mutation_universe_sha": expected_manifest_joins["mutation_universe_sha"],
        "metric_spec_sha": expected_manifest_joins["metric_spec_sha"],
        "environment_manifest": fixture["environment_manifest"],
        "ordered_route_results": route_results,
        "surviving_route_ids": survivors,
        "decision_payload_sha": "",
        "auxiliary_benchmark": benchmark,
        "d0_result_sha": "",
    }
    result["decision_payload_sha"] = canonical_sha_v1(
        {name: result[name] for name in _D0_DECISION_FIELDS}
    )
    _rehash_record_field_v1(result, "d0_result_sha")
    validated = validate_exact_lab_record_v1("B7LabD0ComparisonV1", result)
    validate_d0_decision_payload_projection_v1(validated)
    return validated


def validate_d0_comparison_v1(
    raw_body,
    *,
    corpus_fixture_raw_bytes,
    common_blob,
    compare_blob,
    python_identity_observation,
    python_probe_result,
    ordered_route_inputs,
):
    """Reject D0 unless corpus, blobs, routes, survivors and both roots replay."""

    observed = validate_exact_lab_record_v1("B7LabD0ComparisonV1", raw_body)
    validate_d0_decision_payload_projection_v1(observed)
    expected = build_d0_comparison_v1(
        corpus_fixture_raw_bytes=corpus_fixture_raw_bytes,
        common_blob=common_blob,
        compare_blob=compare_blob,
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
        ordered_route_inputs=ordered_route_inputs,
        auxiliary_benchmark=observed["auxiliary_benchmark"],
    )
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError("D0 comparison differs from fresh recomputation")
    return observed


_D1_ROUTE_CAPTURE_INPUT_FIELDS_V1 = (
    "route_id",
    "route_manifest_sha",
    "ordered_legal_replays",
)


def _validate_d1_capture_source_bytes_v1(ordered_capture_source_bytes):
    if (
        type(ordered_capture_source_bytes) is not list
        or len(ordered_capture_source_bytes) != 3
    ):
        raise TypeError("D1 source domain must contain exactly three captures")
    expected_case_ids = [row[1] for row in _CASE_CONTRACTS_V1]
    captures = []
    for capture_ordinal, raw_capture in enumerate(ordered_capture_source_bytes):
        sources = _require_exact_seven_bytes_v1(
            raw_capture,
            f"D1 capture {capture_ordinal} sources",
        )
        transcripts = []
        for raw_bytes in sources:
            parsed = strict_json_loads_v1(raw_bytes)
            if canonical_json_bytes_v1(parsed) != raw_bytes:
                raise ValueError("D1 source transcript bytes are not canonical")
            transcripts.append(validate_case_contract_v1(parsed))
        case_ids = [transcript["case_id"] for transcript in transcripts]
        if case_ids != expected_case_ids:
            raise ValueError("D1 source transcript case order drifted")
        leaf_root = canonical_sha_v1(
            [
                {
                    "case_id": case_id,
                    "ordered_leaf_digests_sha": canonical_sha_v1(
                        transcript["ordered_leaf_digests"]
                    ),
                }
                for case_id, transcript in zip(case_ids, transcripts)
            ]
        )
        captures.append(
            {
                "capture_ordinal": capture_ordinal,
                "case_ids": case_ids,
                "transcripts": transcripts,
                "source_bytes": list(sources),
                "transcript_set_sha": _ordered_bytes_root_v1(case_ids, sources),
                "ordered_leaf_digest_set_sha": leaf_root,
            }
        )
    return captures


def _build_d1_cross_replay_domain_v1(
    *,
    synthetic_graph_manifest_sha,
    ordered_survivor_route_ids,
    ordered_capture_source_bytes,
    ordered_route_capture_inputs,
):
    graph_sha = _require_sha256_root_v1(
        synthetic_graph_manifest_sha,
        "D1 synthetic graph manifest",
    )
    if (
        type(ordered_survivor_route_ids) is not list
        or not ordered_survivor_route_ids
        or len(set(ordered_survivor_route_ids)) != len(ordered_survivor_route_ids)
    ):
        raise TypeError("D1 survivor route order must be a nonempty unique list")
    for route_id in ordered_survivor_route_ids:
        _validate_lab_wire_semantics_v1(route_id, "route-id", None, "route_id")
    if type(ordered_route_capture_inputs) is not list or len(
        ordered_route_capture_inputs
    ) != len(ordered_survivor_route_ids):
        raise TypeError("D1 route capture domain cardinality drifted")

    captures = _validate_d1_capture_source_bytes_v1(ordered_capture_source_bytes)
    route_cells = []
    route_decoded_bytes = []
    for expected_route_id, raw_route_input in zip(
        ordered_survivor_route_ids,
        ordered_route_capture_inputs,
    ):
        route_input = _require_exact_ordered_dict_v1(
            raw_route_input,
            _D1_ROUTE_CAPTURE_INPUT_FIELDS_V1,
            "D1 route capture input",
        )
        if route_input["route_id"] != expected_route_id:
            raise ValueError("D1 route capture order drifted")
        manifest_sha = _require_sha256_root_v1(
            route_input["route_manifest_sha"],
            "D1 route capture manifest",
        )
        replays = route_input["ordered_legal_replays"]
        if type(replays) is not list or len(replays) != 21:
            raise TypeError("D1 route capture must contain exactly 21 replays")
        cells = []
        decoded_by_capture = []
        cursor = 0
        for capture in captures:
            route_sources = []
            route_wires = []
            route_decoded = []
            for case_id in capture["case_ids"]:
                replay = _require_exact_ordered_dict_v1(
                    replays[cursor],
                    _LEGAL_REPLAY_OBSERVATION_FIELDS_V1,
                    "D1 legal replay observation",
                )
                cursor += 1
                if (
                    type(replay["capture_ordinal"]) is not int
                    or replay["capture_ordinal"] != capture["capture_ordinal"]
                    or replay["case_id"] != case_id
                    or replay["route_id"] != expected_route_id
                    or type(replay["source_transcript_bytes"]) is not bytes
                ):
                    raise ValueError("D1 legal replay capture/case/route order drifted")
                encode = _validate_route_call_observation_v1(
                    replay["encode_result"],
                    "D1 legal encode result",
                )
                decode = _validate_route_call_observation_v1(
                    replay["decode_result"],
                    "D1 legal decode result",
                )
                if (
                    encode["termination_kind"] != "RETURNED_BYTES"
                    or decode["termination_kind"] != "RETURNED_BYTES"
                ):
                    raise ValueError("D1 cross replay did not return byte strings")
                route_sources.append(replay["source_transcript_bytes"])
                route_wires.append(encode["raw_bytes"])
                route_decoded.append(decode["raw_bytes"])
            cells.append(
                build_cross_replay_cell_v1(
                    capture_ordinal=capture["capture_ordinal"],
                    synthetic_graph_manifest_sha=graph_sha,
                    route_id=expected_route_id,
                    route_manifest_sha=manifest_sha,
                    ordered_source_transcript_bytes=route_sources,
                    ordered_route_wire_bytes=route_wires,
                    ordered_decoded_transcript_bytes=route_decoded,
                )
            )
            decoded_by_capture.append(route_decoded)
        route_cells.append(cells)
        route_decoded_bytes.append(decoded_by_capture)

    capture_ordinals_match = all(
        [cell["capture_ordinal"] for cell in cells] == [0, 1, 2]
        for cells in route_cells
    )
    case_cardinalities_match = all(
        cell["case_count"] == 7 and cell["ordered_case_ids"] == capture["case_ids"]
        for cells in route_cells
        for cell, capture in zip(cells, captures)
    )
    decoded_bytes_match = all(
        decoded == capture["source_bytes"]
        for decoded_captures in route_decoded_bytes
        for decoded, capture in zip(decoded_captures, captures)
    )
    decoded_roots_match = all(
        cell["decoded_transcript_set_sha"] == capture["transcript_set_sha"]
        for cells in route_cells
        for cell, capture in zip(cells, captures)
    )
    leaf_roots_match = all(
        cell["ordered_leaf_digest_set_sha"] == capture["ordered_leaf_digest_set_sha"]
        for cells in route_cells
        for cell, capture in zip(cells, captures)
    )
    cross_route_identity_matches = all(
        cell["transcript_set_sha"] == capture["transcript_set_sha"]
        and cell["ordered_leaf_digest_set_sha"]
        == capture["ordered_leaf_digest_set_sha"]
        for cells in route_cells
        for cell, capture in zip(cells, captures)
    )
    identity_entries = [
        {
            "capture_ordinal": capture["capture_ordinal"],
            "transcript_set_sha": capture["transcript_set_sha"],
            "ordered_leaf_digest_set_sha": capture["ordered_leaf_digest_set_sha"],
            "ordered_route_ids": list(ordered_survivor_route_ids),
            "ordered_decoded_transcript_set_shas": [
                cells[capture["capture_ordinal"]]["decoded_transcript_set_sha"]
                for cells in route_cells
            ],
        }
        for capture in captures
    ]
    return {
        "graph_sha": graph_sha,
        "captures": captures,
        "route_cells": route_cells,
        "domain_root_sha": canonical_sha_v1(identity_entries),
        "predicate_results": (
            capture_ordinals_match,
            case_cardinalities_match,
            decoded_bytes_match,
            decoded_roots_match,
            leaf_roots_match,
            cross_route_identity_matches,
        ),
    }


def build_gate_e05_v1(
    *,
    phase,
    route_id,
    synthetic_graph_manifest_sha,
    ordered_survivor_route_ids,
    ordered_capture_source_bytes,
    ordered_route_capture_inputs,
):
    """Build D1 E05 only from all survivor routes' exact replay bytes."""

    if phase != "D1":
        raise ValueError("E05 is a D1-only gate")
    if route_id not in ordered_survivor_route_ids:
        raise ValueError("E05 route is not a D0 survivor")
    domain = _build_d1_cross_replay_domain_v1(
        synthetic_graph_manifest_sha=synthetic_graph_manifest_sha,
        ordered_survivor_route_ids=ordered_survivor_route_ids,
        ordered_capture_source_bytes=ordered_capture_source_bytes,
        ordered_route_capture_inputs=ordered_route_capture_inputs,
    )
    return build_gate_outcome_v1(
        gate_id="E05",
        phase=phase,
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def validate_gate_e05_v1(
    raw_body,
    *,
    synthetic_graph_manifest_sha,
    ordered_survivor_route_ids,
    ordered_capture_source_bytes,
    ordered_route_capture_inputs,
):
    """Reject E05 unless every source/wire/decoded/leaf root recomputes."""

    observed = validate_exact_lab_record_v1("B7LabGateOutcomeV1", raw_body)
    if observed["gate_id"] != "E05" or observed["phase"] != "D1":
        raise ValueError("E05 validator received another gate or phase")
    expected = build_gate_e05_v1(
        phase="D1",
        route_id=observed["observation"]["route_id"],
        synthetic_graph_manifest_sha=synthetic_graph_manifest_sha,
        ordered_survivor_route_ids=ordered_survivor_route_ids,
        ordered_capture_source_bytes=ordered_capture_source_bytes,
        ordered_route_capture_inputs=ordered_route_capture_inputs,
    )
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError("E05 outcome differs from fresh recomputation")
    return observed


_D1_GATE_ORDER_V1 = ("E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08")


def _build_d1_gate_from_domain_v1(*, gate_id, route_id, domain):
    """Seal one D1 gate from an already-consumed dynamic-domain summary."""

    if type(domain) is not dict:
        raise TypeError("D1 gate domain summary must be an exact dict")
    return build_gate_outcome_v1(
        gate_id=gate_id,
        phase="D1",
        route_id=route_id,
        domain_root_sha=domain["domain_root_sha"],
        predicate_results=list(domain["predicate_results"]),
    )


def build_d1_route_result_v1(
    *,
    d0_route_result,
    route_blob,
    production_blobs,
    validated_corpus_fixture,
    ordered_capture_source_bytes,
    gate_inputs,
    ordered_survivor_route_ids,
    ordered_route_capture_inputs,
):
    """Build one D1 route result by replaying all captures and all eight gates."""

    d0_result = validate_exact_lab_record_v1(
        "B7LabD0RouteResultV1",
        d0_route_result,
    )
    if d0_result["survives_d0"] is not True:
        raise ValueError("D1 route was not a D0 survivor")
    manifest = validate_route_static_surface_v1(
        d0_result["route_manifest"],
        route_blob,
        production_blobs,
    )
    if canonical_json_bytes_v1(manifest) != canonical_json_bytes_v1(
        d0_result["route_manifest"]
    ):
        raise ValueError("D1 route manifest differs from D0")
    if (
        d0_result["route_id"] != manifest["route_id"]
        or d0_result["route_manifest_sha"] != manifest["route_manifest_sha"]
        or d0_result["route_commit_sha"] != manifest["route_commit_sha"]
    ):
        raise ValueError("D1 route/D0 manifest identity drifted")
    route_id = manifest["route_id"]
    if route_id not in ordered_survivor_route_ids:
        raise ValueError("D1 route order omits its D0 survivor")
    inputs = _validate_d0_gate_inputs_v1(gate_inputs)
    cross = _build_d1_cross_replay_domain_v1(
        synthetic_graph_manifest_sha=validated_corpus_fixture[
            "synthetic_graph_manifest"
        ]["graph_sha"],
        ordered_survivor_route_ids=ordered_survivor_route_ids,
        ordered_capture_source_bytes=ordered_capture_source_bytes,
        ordered_route_capture_inputs=ordered_route_capture_inputs,
    )
    route_ordinal = ordered_survivor_route_ids.index(route_id)
    own_capture_input = ordered_route_capture_inputs[route_ordinal]
    if (
        own_capture_input["route_manifest_sha"] != manifest["route_manifest_sha"]
        or own_capture_input["ordered_legal_replays"] != inputs["ordered_legal_replays"]
    ):
        raise ValueError("D1 route capture input differs from route gate input")
    source_sets = [capture["transcripts"] for capture in cross["captures"]]
    legal = _validate_legal_replay_domain_v1(
        phase="D1",
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_legal_replays=inputs["ordered_legal_replays"],
    )
    mutation = _validate_mutation_probe_domain_v1(
        phase="D1",
        route_id=route_id,
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_source_transcript_sets=source_sets,
        ordered_mutation_probes=inputs["ordered_mutation_probes"],
    )
    evidence = _derive_e03_domain_from_legal_v1(
        legal_domain=legal,
        ordered_legal_replays=inputs["ordered_legal_replays"],
    )
    invalid_presence = _validate_invalid_presence_domain_v1(
        phase="D1",
        route_id=route_id,
        ordered_source_transcript_sets=source_sets,
        ordered_invalid_presence_probes=inputs["ordered_invalid_presence_probes"],
    )
    presence = _derive_e04_domain_from_legal_and_invalid_v1(
        phase="D1",
        legal_domain=legal,
        ordered_legal_replays=inputs["ordered_legal_replays"],
        invalid_domain=invalid_presence,
    )
    e06 = _validate_e06_domain_v1(mutation)
    gates = [
        _build_d1_gate_from_domain_v1(
            gate_id="E01",
            route_id=route_id,
            domain=legal,
        ),
        _build_d1_gate_from_domain_v1(
            gate_id="E02",
            route_id=route_id,
            domain=mutation,
        ),
        _build_d1_gate_from_domain_v1(
            gate_id="E03",
            route_id=route_id,
            domain=evidence,
        ),
        _build_d1_gate_from_domain_v1(
            gate_id="E04",
            route_id=route_id,
            domain=presence,
        ),
        _build_d1_gate_from_domain_v1(
            gate_id="E05",
            route_id=route_id,
            domain=cross,
        ),
        _build_d1_gate_from_domain_v1(
            gate_id="E06",
            route_id=route_id,
            domain=e06,
        ),
        build_gate_e07_v1(
            phase="D1",
            route_manifest=manifest,
            route_blob=route_blob,
            production_blobs=production_blobs,
        ),
        build_gate_e08_v1(
            phase="D1",
            route_manifest=manifest,
            route_blob=route_blob,
            production_blobs=production_blobs,
        ),
    ]
    if tuple(gate["gate_id"] for gate in gates) != _D1_GATE_ORDER_V1:
        raise ValueError("D1 gate builder order drifted")

    if legal["accepted_count"] != 21:
        raise ValueError("D1 legal replay cardinality did not fully accept")
    static_metrics = compute_route_static_metrics_v1(route_id, route_blob)
    canonical_wires = [
        row["encode_result"]["raw_bytes"] for row in inputs["ordered_legal_replays"]
    ]
    metric_values = {
        "mutation_accept_count": mutation["mutation_accept_count"],
        "evidence_loss_count": evidence["evidence_loss_count"],
        "constructible_invalid_presence_count": presence["canonical_accept_count"],
        "half_pair_state_count": presence["half_pair_state_count"],
        **static_metrics,
        "canonical_wire_bytes": compute_canonical_wire_bytes_v1(canonical_wires),
    }
    if tuple(metric_values) != _METRIC_ORDER_V1:
        raise ValueError("D1 metric coordinate order drifted")
    metric_vector = {**metric_values, "metric_vector_sha": ""}
    _rehash_record_field_v1(metric_vector, "metric_vector_sha")
    metric_vector = validate_metric_vector_v1(metric_vector)

    cells = cross["route_cells"][route_ordinal]
    cells_pass = all(
        cell["exact_transcript_match"]
        and cell["transcript_set_sha"]
        == cross["captures"][ordinal]["transcript_set_sha"]
        and cell["ordered_leaf_digest_set_sha"]
        == cross["captures"][ordinal]["ordered_leaf_digest_set_sha"]
        and cell["synthetic_graph_manifest_sha"] == cross["graph_sha"]
        and cell["route_manifest_sha"] == manifest["route_manifest_sha"]
        for ordinal, cell in enumerate(cells)
    )
    result = {
        "route_result_schema_version": "experimental.v3m0.b7.d1-route-result.v1",
        "route_id": route_id,
        "route_manifest": manifest,
        "route_manifest_sha": manifest["route_manifest_sha"],
        "route_commit_sha": manifest["route_commit_sha"],
        "ordered_cross_replay_cells": cells,
        "gate_outcomes": gates,
        "metric_vector": metric_vector,
        "survives_d1": all(gate["passed"] for gate in gates) and cells_pass,
        "route_result_sha": "",
    }
    _rehash_record_field_v1(result, "route_result_sha")
    return validate_exact_lab_record_v1("B7LabD1RouteResultV1", result)


def validate_d1_route_result_v1(
    raw_body,
    *,
    d0_route_result,
    route_blob,
    production_blobs,
    validated_corpus_fixture,
    ordered_capture_source_bytes,
    gate_inputs,
    ordered_survivor_route_ids,
    ordered_route_capture_inputs,
):
    """Reject a D1 route result unless all raw domains replay identically."""

    observed = validate_exact_lab_record_v1("B7LabD1RouteResultV1", raw_body)
    expected = build_d1_route_result_v1(
        d0_route_result=d0_route_result,
        route_blob=route_blob,
        production_blobs=production_blobs,
        validated_corpus_fixture=validated_corpus_fixture,
        ordered_capture_source_bytes=ordered_capture_source_bytes,
        gate_inputs=gate_inputs,
        ordered_survivor_route_ids=ordered_survivor_route_ids,
        ordered_route_capture_inputs=ordered_route_capture_inputs,
    )
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError("D1 route result differs from fresh recomputation")
    return observed


_D1_ROUTE_INPUT_FIELDS_V1 = (
    "route_manifest",
    "route_blob",
    "production_blobs",
    "gate_inputs",
)
_NEUTRAL_LEAF_PROVIDER_SOURCE_PATH_V1 = "rulespace_v3/b7_replay_core_v1.py"


def _validate_d1_route_inputs_v1(raw_inputs, d0_result):
    survivor_ids = d0_result["surviving_route_ids"]
    if (
        type(survivor_ids) is not list
        or not survivor_ids
        or type(raw_inputs) is not list
        or len(raw_inputs) != len(survivor_ids)
    ):
        raise TypeError("D1 route inputs must exactly cover D0 survivors")
    d0_by_id = {
        result["route_id"]: result for result in d0_result["ordered_route_results"]
    }
    validated = []
    for route_id, raw_input in zip(survivor_ids, raw_inputs):
        route_input = _require_exact_ordered_dict_v1(
            raw_input,
            _D1_ROUTE_INPUT_FIELDS_V1,
            "D1 route input",
        )
        manifest = validate_exact_lab_record_v1(
            "B7LabRouteManifestV1",
            route_input["route_manifest"],
        )
        if route_id not in d0_by_id or manifest["route_id"] != route_id:
            raise ValueError("D1 route input order differs from D0 survivors")
        if canonical_json_bytes_v1(manifest) != canonical_json_bytes_v1(
            d0_by_id[route_id]["route_manifest"]
        ):
            raise ValueError("D1 route manifest is not byte-identical to D0")
        route_blob = _require_git_blob_descriptor_v1(
            route_input["route_blob"],
            "D1 route blob",
        )
        if (
            route_blob[0] != manifest["route_commit_sha"]
            or route_blob[1] != manifest["route_source_path"]
            or route_blob[2] != "100644"
        ):
            raise ValueError("D1 route blob descriptor drifted")
        production_blobs = route_input["production_blobs"]
        if type(production_blobs) is not tuple or not production_blobs:
            raise TypeError("D1 production blobs must be a nonempty exact tuple")
        for ordinal, blob in enumerate(production_blobs):
            checked = _require_git_blob_descriptor_v1(
                blob,
                f"D1 production blob {ordinal}",
            )
            if checked[0] != d0_result["common_commit_sha"] or checked[2] != "100644":
                raise ValueError("D1 production blob commit or mode drifted")
        _validate_d0_gate_inputs_v1(route_input["gate_inputs"])
        validated.append(route_input)
    return validated


def _validate_d1_auxiliary_benchmark_v1(raw_benchmark, route_ids):
    benchmark = _require_exact_ordered_dict_v1(
        raw_benchmark,
        _D0_AUXILIARY_BENCHMARK_FIELDS_V1,
        "D1 auxiliary benchmark",
    )
    if type(benchmark["warm_up"]) is not int or benchmark["warm_up"] != 5:
        raise ValueError("D1 auxiliary benchmark warm-up drifted")
    if type(benchmark["repeat"]) is not int or benchmark["repeat"] != 30:
        raise ValueError("D1 auxiliary benchmark repeat count drifted")
    if (
        type(benchmark["reported_statistics"]) is not list
        or tuple(benchmark["reported_statistics"])
        != _D0_AUXILIARY_REPORTED_STATISTICS_V1
    ):
        raise ValueError("D1 auxiliary reported-statistics protocol drifted")
    statistics = benchmark["ordered_route_statistics"]
    if type(statistics) is not list or len(statistics) != len(route_ids):
        raise TypeError("D1 auxiliary route statistics cardinality drifted")
    for route_id, raw_statistic in zip(route_ids, statistics):
        statistic = _require_exact_ordered_dict_v1(
            raw_statistic,
            _D0_AUXILIARY_ROUTE_STATISTIC_FIELDS_V1,
            "D1 auxiliary route statistic",
        )
        if statistic["route_id"] != route_id:
            raise ValueError("D1 auxiliary route statistic order drifted")
        for field in ("median", "p95"):
            if type(statistic[field]) is not float or statistic[field] < 0.0:
                raise TypeError(f"D1 auxiliary {field} must be a nonnegative float")
        if statistic["p95"] < statistic["median"]:
            raise ValueError("D1 auxiliary p95 is below its median")
        if (
            type(statistic["tracemalloc_peak"]) is not int
            or statistic["tracemalloc_peak"] < 0
        ):
            raise TypeError("D1 auxiliary peak must be a nonnegative exact int")
    canonical_json_bytes_v1(benchmark)
    return _detach_json_v1(benchmark)


def build_d1_comparison_v1(
    *,
    d0_result_raw_bytes,
    corpus_fixture_raw_bytes,
    common_blob,
    compare_blob,
    leaf_provider_blob,
    python_identity_observation,
    python_probe_result,
    ordered_capture_source_bytes,
    ordered_route_inputs,
    auxiliary_benchmark,
):
    """Build D1 from canonical D0/corpus bytes and immutable source blobs."""

    if type(d0_result_raw_bytes) is not bytes:
        raise TypeError("D1 D0 input must be exact bytes")
    parsed_d0 = strict_json_loads_v1(d0_result_raw_bytes)
    if type(parsed_d0) is not dict or canonical_json_bytes_v1(parsed_d0) != (
        d0_result_raw_bytes
    ):
        raise ValueError("D1 D0 input is not one canonical object")
    d0_result = validate_exact_lab_record_v1("B7LabD0ComparisonV1", parsed_d0)
    validate_d0_decision_payload_projection_v1(d0_result)
    if not d0_result["surviving_route_ids"]:
        raise ValueError("D1 cannot run after a D0 no-survivor halt")

    common_checked, compare_checked = _validate_common_compare_blobs_v1(
        common_blob,
        compare_blob,
    )
    if (
        common_checked[0] != d0_result["common_commit_sha"]
        or _raw_source_sha256_v1(common_checked[3], "D1 common")
        != d0_result["common_source_sha256"]
        or _raw_source_sha256_v1(compare_checked[3], "D1 compare")
        != d0_result["compare_source_sha256"]
    ):
        raise ValueError("D1 common/compare roots differ from D0")
    leaf_checked = _require_git_blob_descriptor_v1(
        leaf_provider_blob,
        "D1 leaf provider blob",
    )
    if (
        leaf_checked[0] != d0_result["common_commit_sha"]
        or leaf_checked[1] != _NEUTRAL_LEAF_PROVIDER_SOURCE_PATH_V1
        or leaf_checked[2] != "100644"
    ):
        raise ValueError("D1 neutral leaf-provider blob identity drifted")
    leaf_source_sha = _raw_source_sha256_v1(leaf_checked[3], "D1 leaf provider")

    if type(corpus_fixture_raw_bytes) is not bytes:
        raise TypeError("D1 corpus fixture input must be exact bytes")
    parsed_fixture = strict_json_loads_v1(corpus_fixture_raw_bytes)
    if type(parsed_fixture) is not dict or canonical_json_bytes_v1(parsed_fixture) != (
        corpus_fixture_raw_bytes
    ):
        raise ValueError("D1 corpus fixture is not one canonical object")
    fixture = validate_corpus_fixture_v2(
        parsed_fixture,
        common_checked[3],
        compare_checked[3],
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
    )
    if canonical_json_bytes_v1(fixture) != canonical_json_bytes_v1(parsed_fixture):
        raise ValueError("validated D1 corpus fixture body was substituted")
    fixture_raw_sha = _pure_core.hashlib.sha256(corpus_fixture_raw_bytes).hexdigest()
    expected_d0_joins = {
        "corpus_fixture_raw_sha256": fixture_raw_sha,
        "corpus_spec_sha": fixture["corpus_spec"]["corpus_spec_sha"],
        "mutation_universe_sha": fixture["mutation_universe"]["mutation_universe_sha"],
        "metric_spec_sha": fixture["metric_spec"]["metric_spec_sha"],
    }
    for field, expected in expected_d0_joins.items():
        if d0_result[field] != expected:
            raise ValueError(f"D1 fixture/D0 {field} join drifted")
    if canonical_json_bytes_v1(d0_result["environment_manifest"]) != (
        canonical_json_bytes_v1(fixture["environment_manifest"])
    ):
        raise ValueError("D1 environment body differs from D0 or fixture")

    graph = validate_synthetic_graph_manifest_v1(fixture["synthetic_graph_manifest"])
    if graph.get("selected_fejer_order") != 256 or canonical_json_bytes_v1(
        graph
    ) != canonical_json_bytes_v1(fixture["synthetic_graph_manifest"]):
        raise ValueError("D1 graph is not the exact fixture T=256 graph")
    captures = _validate_d1_capture_source_bytes_v1(ordered_capture_source_bytes)
    for capture in captures:
        for transcript in capture["transcripts"]:
            if (
                transcript.get("response_run_spec_fixture", {}).get(
                    "selected_fejer_order"
                )
                != 256
            ):
                raise ValueError("D1 transcript run spec is not T=256")
            validated = _validate_normalized_transcript_against_validated_graph_v1(
                transcript,
                corpus_spec_sha=fixture["corpus_spec"]["corpus_spec_sha"],
                environment_manifest_sha=fixture["environment_manifest"][
                    "environment_sha"
                ],
                validated_graph=graph,
            )
            if canonical_json_bytes_v1(validated) != canonical_json_bytes_v1(
                transcript
            ):
                raise ValueError("D1 validated transcript body was substituted")

    route_inputs = _validate_d1_route_inputs_v1(ordered_route_inputs, d0_result)
    survivor_ids = list(d0_result["surviving_route_ids"])
    route_capture_inputs = [
        {
            "route_id": route_input["route_manifest"]["route_id"],
            "route_manifest_sha": route_input["route_manifest"]["route_manifest_sha"],
            "ordered_legal_replays": route_input["gate_inputs"][
                "ordered_legal_replays"
            ],
        }
        for route_input in route_inputs
    ]
    d0_by_id = {
        result["route_id"]: result for result in d0_result["ordered_route_results"]
    }
    route_results = []
    for route_id, route_input in zip(survivor_ids, route_inputs):
        route_results.append(
            build_d1_route_result_v1(
                d0_route_result=d0_by_id[route_id],
                route_blob=route_input["route_blob"],
                production_blobs=route_input["production_blobs"],
                validated_corpus_fixture=fixture,
                ordered_capture_source_bytes=ordered_capture_source_bytes,
                gate_inputs=route_input["gate_inputs"],
                ordered_survivor_route_ids=survivor_ids,
                ordered_route_capture_inputs=route_capture_inputs,
            )
        )
    if [result["route_id"] for result in route_results] != survivor_ids:
        raise ValueError("D1 route result order drifted")
    surviving_results = [result for result in route_results if result["survives_d1"]]
    surviving_ids = [result["route_id"] for result in surviving_results]
    if not surviving_results:
        minimum_metric = None
        minimum_routes = []
    else:
        minimum_key = min(
            tuple(result["metric_vector"][name] for name in _METRIC_ORDER_V1)
            for result in surviving_results
        )
        minimum_routes = [
            result
            for result in surviving_results
            if tuple(result["metric_vector"][name] for name in _METRIC_ORDER_V1)
            == minimum_key
        ]
        minimum_metric = minimum_routes[0]["metric_vector"]
    tie_detected = len(minimum_routes) >= 2
    winner = minimum_routes[0]["route_id"] if len(minimum_routes) == 1 else None
    benchmark = _validate_d1_auxiliary_benchmark_v1(
        auxiliary_benchmark,
        survivor_ids,
    )
    result = {
        "d1_result_schema_version": "experimental.v3m0.b7.d1-comparison.v1",
        "d0_result_raw_sha256": _pure_core.hashlib.sha256(
            d0_result_raw_bytes
        ).hexdigest(),
        "d0_result_sha": d0_result["d0_result_sha"],
        "d0_decision_payload_sha": d0_result["decision_payload_sha"],
        "common_commit_sha": d0_result["common_commit_sha"],
        "common_source_sha256": d0_result["common_source_sha256"],
        "compare_source_sha256": d0_result["compare_source_sha256"],
        "leaf_provider_source_sha256": leaf_source_sha,
        "corpus_fixture_raw_sha256": fixture_raw_sha,
        "corpus_spec_sha": expected_d0_joins["corpus_spec_sha"],
        "mutation_universe_sha": expected_d0_joins["mutation_universe_sha"],
        "metric_spec_sha": expected_d0_joins["metric_spec_sha"],
        "synthetic_graph_manifest": graph,
        "environment_manifest": fixture["environment_manifest"],
        "ordered_capture_transcript_set_shas": [
            capture["transcript_set_sha"] for capture in captures
        ],
        "ordered_capture_leaf_digest_set_shas": [
            capture["ordered_leaf_digest_set_sha"] for capture in captures
        ],
        "ordered_route_results": route_results,
        "surviving_route_ids": surviving_ids,
        "minimum_metric_vector": minimum_metric,
        "provisional_winner_route_id": winner,
        "tie_detected": tie_detected,
        "decision_payload_sha": "",
        "auxiliary_benchmark": benchmark,
        "d1_result_sha": "",
    }
    result["decision_payload_sha"] = canonical_sha_v1(
        {name: result[name] for name in _D1_DECISION_FIELDS}
    )
    _rehash_record_field_v1(result, "d1_result_sha")
    validated = validate_exact_lab_record_v1("B7LabD1ComparisonV1", result)
    validate_d1_decision_payload_projection_v1(validated)
    return validated


def validate_d1_comparison_v1(
    raw_body,
    *,
    d0_result_raw_bytes,
    corpus_fixture_raw_bytes,
    common_blob,
    compare_blob,
    leaf_provider_blob,
    python_identity_observation,
    python_probe_result,
    ordered_capture_source_bytes,
    ordered_route_inputs,
):
    """Reject D1 unless every D0, graph, capture, route and metric join replays."""

    observed = validate_exact_lab_record_v1("B7LabD1ComparisonV1", raw_body)
    validate_d1_decision_payload_projection_v1(observed)
    expected = build_d1_comparison_v1(
        d0_result_raw_bytes=d0_result_raw_bytes,
        corpus_fixture_raw_bytes=corpus_fixture_raw_bytes,
        common_blob=common_blob,
        compare_blob=compare_blob,
        leaf_provider_blob=leaf_provider_blob,
        python_identity_observation=python_identity_observation,
        python_probe_result=python_probe_result,
        ordered_capture_source_bytes=ordered_capture_source_bytes,
        ordered_route_inputs=ordered_route_inputs,
        auxiliary_benchmark=observed["auxiliary_benchmark"],
    )
    if canonical_json_bytes_v1(observed) != canonical_json_bytes_v1(expected):
        raise ValueError("D1 comparison differs from fresh recomputation")
    return observed
