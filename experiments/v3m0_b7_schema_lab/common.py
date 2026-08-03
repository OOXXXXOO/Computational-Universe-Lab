"""Owner-neutral common contracts for the B7 schema laboratory."""

from __future__ import annotations

import rulespace_v3.b7_replay_core_v1 as _pure_core


LAB_EXACT_RECORD_CATALOGS_V1 = (
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
                "B7LabEnvironmentManifestV1",
                "required",
                "B7LabEnvironmentManifestV1",
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
                "B7LabEnvironmentManifestV1",
                "required",
                "B7LabEnvironmentManifestV1",
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
                "Literal[fresh-python-s-immutable-E-export-canonical-stdout-v1]",
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
        ("v3m0-b7-corpus-replay-v1", "v3m0-b7-metric-replay-v1"),
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


def _core_record_schemas_v1():
    schemas = {}
    for (
        record_name,
        _schema_id,
        hash_field,
        field_specs,
    ) in LAB_EXACT_RECORD_CATALOGS_V1:
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
    for catalog in LAB_EXACT_RECORD_CATALOGS_V1:
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
    return _pure_core.strict_json_loads_v1(
        _pure_core.canonical_json_bytes_v1(validated)
    )


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


def _require_json_pointer_v1(value, field):
    if type(value) is not str:
        raise TypeError(f"{field} must be an exact str")
    if value == "":
        return
    if not value.startswith("/"):
        raise ValueError(f"{field} must be a rooted JSON pointer")
    for token in value.split("/")[1:]:
        index = 0
        while index < len(token):
            if token[index] == "~":
                if index + 1 >= len(token) or token[index + 1] not in ("0", "1"):
                    raise ValueError(f"{field} has an invalid JSON pointer escape")
                index += 1
            index += 1


def validate_nested_body_rule_v1(raw_body):
    """Validate one normalized nested-body traversal rule."""
    rule = _validate_exact_lab_record_v1("B7LabNestedBodyRuleV1", raw_body)
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
    _require_json_pointer_v1(
        mutation["target_json_pointer"],
        "mutation target pointer",
    )
    mutation_id = mutation["mutation_id"]
    expected_prefix = (
        f"M{mutation['mutation_ordinal']:06d}-{mutation['mutation_class']}-"
    )
    suffix = mutation_id.split("-")[-1]
    if (
        not mutation_id.startswith(expected_prefix)
        or len(suffix) != 16
        or any(character not in "0123456789abcdef" for character in suffix)
    ):
        raise ValueError("mutation ID format drifted")
    return mutation


def validate_metric_vector_v1(raw_body):
    """Validate one ten-coordinate metric vector and its self hash."""
    return _validate_exact_lab_record_v1("B7LabMetricVectorV1", raw_body)


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


def validate_provenance_fixture_v1(raw_body):
    """Delegate one provenance fixture validation to the pure core."""
    return _pure_core.validate_provenance_fixture_v1(raw_body)


def validate_branch_attempt_v1(raw_body):
    """Delegate one branch-attempt validation to the pure core."""
    return _pure_core.validate_branch_attempt_v1(raw_body)
