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
    operation = mutation["operation"]
    if operation in ("REENCODE", "REPEAT", "RAISE_UPSTREAM"):
        raise ValueError("global probe operation has no materialized transcript")

    mutated = _detach_json_v1(base)
    target_pointer = mutation["target_json_pointer"]
    replacement = _detach_json_v1(mutation["replacement_json"])
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

    effective_snapshot = tuple(base_snapshot) + tuple(
        item for item in success_snapshot if item not in base_snapshot
    )
    _resign_from_snapshots_v1(mutated, target_pointer, effective_snapshot)
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
    """Validate the exact 326-row universe against the frozen generator."""
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
    if (
        universe["mutation_count"] != 326
        or len(observed_mutations) != 326
        or observed_mutations != expected_mutations
    ):
        raise ValueError("mutation universe differs from frozen generation")
    if tuple(mutation["mutation_ordinal"] for mutation in observed_mutations) != tuple(
        range(326)
    ):
        raise ValueError("mutation universe ordinals are not contiguous")
    mutation_ids = tuple(mutation["mutation_id"] for mutation in observed_mutations)
    mutation_shas = tuple(mutation["mutation_sha"] for mutation in observed_mutations)
    if len(set(mutation_ids)) != 326 or len(set(mutation_shas)) != 326:
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


def _apply_presence_attempt_v1(candidate, success, field, parent_bit, *child_bits):
    if parent_bit == "0":
        candidate[field] = None
        return
    attempt = _detach_json_v1(success[field])
    attempt["response_values"] = (
        _detach_json_v1(success[field]["response_values"])
        if child_bits[0] == "1"
        else None
    )
    attempt["bridge_audit"] = (
        _detach_json_v1(success[field]["bridge_audit"])
        if child_bits[1] == "1"
        else None
    )
    attempt["failure"] = None
    _rehash_record_field_v1(attempt, "attempt_sha")
    candidate[field] = attempt


def generate_constructible_invalid_presence_candidates_v1(success_transcript_raw):
    """Generate the exact 1,393 constructible non-case tag/presence states."""

    success = validate_case_contract_v1(success_transcript_raw)
    if success["case_id"] != "success":
        raise ValueError("invalid-presence generation requires the success case")
    legal_pairs = {(row[2], row[4]) for row in _CASE_CONTRACTS_V1}
    candidates = []
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
            transcript["shell_outcome"] = (
                _detach_json_v1(success["shell_outcome"]) if bits[0] == "1" else None
            )
            _apply_presence_attempt_v1(
                transcript,
                success,
                "actual_branch_attempt",
                bits[1],
                bits[2],
                bits[5],
            )
            _apply_presence_attempt_v1(
                transcript,
                success,
                "matched_ablated_branch_attempt",
                bits[3],
                bits[4],
                bits[6],
            )
            transcript["actual_completed_response"] = (
                _detach_json_v1(success["actual_completed_response"])
                if bits[7] == "1"
                else None
            )
            transcript["matched_ablated_completed_response"] = (
                _detach_json_v1(success["matched_ablated_completed_response"])
                if bits[8] == "1"
                else None
            )
            transcript["terminal_tag"] = terminal_tag
            _rehash_record_field_v1(transcript, "experimental_sha")
            candidates.append(
                {
                    "terminal_tag": terminal_tag,
                    "bit_integer": bit_integer,
                    "presence_bits": bits,
                    "half_pair": (bits[5] != bits[6] or bits[7] != bits[8]),
                    "transcript": transcript,
                }
            )
    if len(candidates) != 1393:
        raise AssertionError("invalid-presence domain cardinality drifted")
    return candidates


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


def validate_normalized_transcript_v1(
    raw_body,
    *,
    corpus_spec_sha,
    environment_manifest_sha,
    graph_raw,
):
    """Strictly validate one normalized transcript and all aggregate joins."""

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

    graph = validate_synthetic_graph_manifest_v1(graph_raw)
    provenance = validate_provenance_fixture_v1(transcript["provenance_fixture"])
    run_spec = validate_response_run_spec_fixture_v1(
        transcript["response_run_spec_fixture"],
        provenance,
        graph,
    )
    reference = validate_endpoint_reference_outcome_raw_v1(
        transcript["reference_outcome"]
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
