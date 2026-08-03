"""Import-pure canonical primitives for B7 reviewer-child replay."""

from __future__ import annotations

import hashlib
import json


B7_V91_PURE_REPLAY_PROJECTION_SHA256 = (
    "bafbaeb75e890715464c1fff6e6e0cbf1d4f56bb53a3817a9b2d12d2a3c27ff9"
)
_B7_RECORD_SCHEMAS_JSON_V1 = (
    '{"AblationManifest":["manifest_sha",[["manifest_schema_version","str",null],["construction_trace_sha","sha256",null],["actual_factory_sha","sha256",null],["ablated_factory_sha","sha256",null],["replacements","tuple[AblationReplacement,...]","AblationReplacement"],["manifest_sha","sha256",null]]],"AblationPairSnapshot":["snapshot_sha",[["snapshot_schema_version","str",null],["construction_status","BlockStatus","BlockStatus"],["actual_factory","LinearRealspaceFactory","LinearRealspaceFactory"],["ablated_factory","LinearRealspaceFactory","LinearRealspaceFactory"],["ablation_manifest","AblationManifest","AblationManifest"],["ablation_construction_sha","sha256",null],["snapshot_sha","sha256",null]]],"AblationReplacement":[null,[["layer_slot_id","str",null],["mechanism_id","str",null],["actual_primitive_sha","sha256",null],["neutral_identity_id","str",null],["ablated_primitive_sha","sha256",null]]],"ApplicationScenarioExecutionSpec":["scenario_sha",[["scenario_schema_version","str",null],["s'
    'cenario_id","str",null],["operation_output_ids","tuple[str,...]",null],["execution_lane","Literal[BLOCK_SUCCESS,EXPECTED_TYPED_TERMINATION,ANALYSIS_CONTROL]",null],["execution_recipe_id","str",null],["recipe_parameter_wires","tuple[tuple[str,TaggedScalarWire],...]","TaggedScalarWire"],["recipe_derivation_source_id","str",null],["expected_terminal_stage","Optional[Literal[activation,trace,stability,endpoint_shell,success]]",null],["expected_undefined_reason","Optional[UndefinedReason]",null],["expected_artifact_type","str",null],["scenario_sha","sha256",null]]],"ApplicationScenarioMaterializationV3":["materialization_sha",[["materialization_schema_version","str",null],["permit","CalibrationApplicationPermitV3","CalibrationApplicationPermitV3"],["current_application_authority","CurrentApplicationAuthorityV3","CurrentApplicationAuthorityV3"],["current_scenario_authority","CurrentScenarioAuthorityV3","CurrentScenarioAuthorityV3"],["current_scenario_response_contract","CurrentScenarioRespon'
    'seContractV3","CurrentScenarioResponseContractV3"],["basis_contract","C19BasisContractV2","C19BasisContractV2"],["construction_trace","ConstructionTrace","ConstructionTrace"],["ablation_pair_snapshot","AblationPairSnapshot","AblationPairSnapshot"],["actual_factory_binding","FactoryBranchBindingV3","FactoryBranchBindingV3"],["matched_ablated_factory_binding","FactoryBranchBindingV3","FactoryBranchBindingV3"],["materialization_sha","sha256",null]]],"BasisManifest":["manifest_id",[["basis_schema_version","str",null],["role","Literal[source,holdout_source,readout]",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["vectors_wire","tuple[tuple[tuple[float,float],...],...]",null],["manifest_id","str",null]]],"BlockStatus":[null,[["defined","bool",null],["reason","Optional[UndefinedReason]",null]]],"BranchSpectrumAudit":["branch_sha",[["branch","Literal[actual,matched_ablated]",null],["declared_rank","int",null],["spectrum_shape","tuple[int,int]",null],["spectrum_or'
    'der_id","Literal[k-major-singular-descending-v1]",null],["raw_spectrum","tuple[float64,...]",null],["active_min","Optional[float64]",null],["inactive_max","Optional[float64]",null],["branch_sha","sha256",null]]],"BridgeAudit":["bridge_sha",[["bridge_schema_version","str",null],["bridge_kind","Literal[full-state]",null],["factory_sha","sha256",null],["transition_sha","sha256",null],["bridge_spec_sha","sha256",null],["cases","tuple[BridgeCaseAudit,...]","BridgeCaseAudit"],["raw_abs_max","float64",null],["normalized_max","float64",null],["bridge_sha","sha256",null]]],"BridgeCaseAudit":[null,[["reciprocal_index","tuple[int,...]",null],["macro_steps","int",null],["trial_index","int",null],["raw_abs_residual","float64",null],["scale","float64",null],["normalized_residual","float64",null]]],"BridgeGridAuthorityV3":["grid_authority_sha",[["grid_authority_schema_version","str",null],["materialization","ApplicationScenarioMaterializationV3","ApplicationScenarioMaterializationV3"],["factory_bindi'
    'ng","FactoryBranchBindingV3","FactoryBranchBindingV3"],["derivation_protocol","BridgeKGridDerivationProtocolV1","BridgeKGridDerivationProtocolV1"],["bridge_grid","BridgeKGridManifest","BridgeKGridManifest"],["grid_authority_sha","sha256",null]]],"BridgeKGridDerivationProtocolV1":["protocol_sha",[["protocol_schema_version","str",null],["branch_roles","tuple[Literal[actual,matched_ablated],...]",null],["spatial_shape","tuple[int,...]",null],["support_source","str",null],["derivation_algorithm","str",null],["bridge_steps","tuple[int,...]",null],["caller_supplied_points_allowed","Literal[false]",null],["fail_closed_condition_ids","tuple[str,...]",null],["protocol_sha","sha256",null]]],"BridgeKGridManifest":["bridge_grid_sha",[["grid_schema_version","str",null],["spatial_shape","tuple[int,...]",null],["torus_denominators","tuple[int,...]",null],["reciprocal_indices","tuple[tuple[int,...],...]",null],["bridge_grid_sha","sha256",null]]],"C19BasisContractV2":["basis_contract_sha",[["basis_cont'
    'ract_schema_version","str",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["common_source_basis","BasisManifest","BasisManifest"],["common_readout_basis","BasisManifest","BasisManifest"],["common_source_tensor","FrozenComplexTensor","FrozenComplexTensor"],["common_readout_tensor","FrozenComplexTensor","FrozenComplexTensor"],["source_selector_b_plus","FrozenComplexTensor","FrozenComplexTensor"],["readout_selector_p","FrozenComplexTensor","FrozenComplexTensor"],["source_injection","FrozenComplexTensor","FrozenComplexTensor"],["readout_coisometry","FrozenComplexTensor","FrozenComplexTensor"],["scenario_source_basis","BasisManifest","BasisManifest"],["scenario_readout_basis","BasisManifest","BasisManifest"],["source_trial_vectors","FrozenComplexTensor","FrozenComplexTensor"],["expected_actual_shell_rank","int",null],["expected_matched_shell_rank","int",null],["basis_contract_sha","sha256",null]]],"C19ObserverGeometryBundleV1":["geometry_bundle_sha",[["geometry'
    '_bundle_schema_version","str",null],["kind","Literal[C19_OBSERVER_COLLAPSE_CONDITIONS]",null],["claim_ceiling","Literal[CONDITIONAL_PREREQUISITES_ONLY]",null],["evaluation_state","Literal[NOT_EVALUATED_PRE_RESPONSE]",null],["conditional_prediction_state","Literal[CONDITIONAL_ANALYTIC_IDENTITY_ONLY]",null],["state_dim","Literal[20]",null],["ambient_h_dim","int",null],["curvature_dim","int",null],["tt_dim","Literal[2]",null],["gauge_dim","Literal[4]",null],["row_dim","Literal[4]",null],["omega_j20","FrozenComplexTensor","FrozenComplexTensor"],["source_b_plus","FrozenComplexTensor","FrozenComplexTensor"],["readout_p","FrozenComplexTensor","FrozenComplexTensor"],["tt_basis","FrozenComplexTensor","FrozenComplexTensor"],["gauge_basis","FrozenComplexTensor","FrozenComplexTensor"],["row_basis","FrozenComplexTensor","FrozenComplexTensor"],["incidence_q","FrozenComplexTensor","FrozenComplexTensor"],["ker_c_projector","FrozenComplexTensor","FrozenComplexTensor"],["curvature_frame","FrozenComplexT'
    'ensor","FrozenComplexTensor"],["conditional_principal_sine_squared","FrozenComplexTensor","FrozenComplexTensor"],["conditional_principal_spectrum","tuple[float64,...]",null],["state_metric","FrozenComplexTensor","FrozenComplexTensor"],["state_whitener","FrozenComplexTensor","FrozenComplexTensor"],["source_metric","FrozenComplexTensor","FrozenComplexTensor"],["source_whitener","FrozenComplexTensor","FrozenComplexTensor"],["h_metric","FrozenComplexTensor","FrozenComplexTensor"],["h_whitener","FrozenComplexTensor","FrozenComplexTensor"],["curvature_metric","FrozenComplexTensor","FrozenComplexTensor"],["curvature_whitener","FrozenComplexTensor","FrozenComplexTensor"],["control_case_id","str",null],["application_instance_id","str",null],["scenario_id","str",null],["operation_dag_sha","sha256",null],["actual_active_step_count","Literal[50]",null],["matched_active_step_count","Literal[30]",null],["actual_layer_slot_count","Literal[50]",null],["matched_layer_slot_count","Literal[50]",null],["a'
    'ctual_slot_program_sha","sha256",null],["matched_slot_program_sha","sha256",null],["actual_active_effect_digest","sha256",null],["matched_active_effect_digest","sha256",null],["common_source_i20_sha","sha256",null],["common_readout_i20_sha","sha256",null],["source_b_plus_sha","sha256",null],["readout_p_sha","sha256",null],["response_grid_sha","sha256",null],["dynamics_derivation_protocol_sha","sha256",null],["bridge_derivation_protocol_sha","sha256",null],["geometry_bundle_sha","sha256",null]]],"C19RuntimeConstructionV2":["construction_sha",[["construction_schema_version","str",null],["state_shape","tuple[int,...]",null],["construction_trace","ConstructionTrace","ConstructionTrace"],["frozen_target","FrozenSyntheticTarget","FrozenSyntheticTarget"],["actual_factory","LinearRealspaceFactory","LinearRealspaceFactory"],["matched_factory","LinearRealspaceFactory","LinearRealspaceFactory"],["ablation_manifest","AblationManifest","AblationManifest"],["actual_active_step_count","Literal[50]",n'
    'ull],["matched_active_step_count","Literal[30]",null],["actual_layer_slot_count","Literal[50]",null],["matched_layer_slot_count","Literal[50]",null],["actual_primitive_count","Literal[50]",null],["matched_primitive_count","Literal[50]",null],["actual_slot_program_sha","sha256",null],["matched_slot_program_sha","sha256",null],["actual_active_effect_digest","sha256",null],["matched_active_effect_digest","sha256",null],["actual_support_offsets","tuple[tuple[int,...],...]",null],["matched_support_offsets","tuple[tuple[int,...],...]",null],["actual_apply_factory_step_kernel","FrozenComplexTensor","FrozenComplexTensor"],["matched_apply_factory_step_kernel","FrozenComplexTensor","FrozenComplexTensor"],["actual_independent_replay_kernel","FrozenComplexTensor","FrozenComplexTensor"],["matched_independent_replay_kernel","FrozenComplexTensor","FrozenComplexTensor"],["construction_sha","sha256",null]]],"CalibrationApplicationPermitV3":["permit_sha",[["permit_schema_version","str",null],["parent_fr'
    'eeze_v3_sha","sha256",null],["calibration","WindowThresholdCalibrationV3","WindowThresholdCalibrationV3"],["current_application_authority","CurrentApplicationAuthorityV3","CurrentApplicationAuthorityV3"],["current_scenario_authority","CurrentScenarioAuthorityV3","CurrentScenarioAuthorityV3"],["current_scenario_response_contract","CurrentScenarioResponseContractV3","CurrentScenarioResponseContractV3"],["selected_fejer_order","int",null],["permit_scope_id","Literal[v3m0-parent-v3-current-application-scenario-v1]",null],["permit_sha","sha256",null]]],"CalibrationObservation":["observation_sha",[["observation_schema_version","str",null],["seed_sha","sha256",null],["runtime_operator_sha","sha256",null],["holdout_source_manifest_id","str",null],["readout_manifest_id","str",null],["response_tensor","FrozenComplexTensor","FrozenComplexTensor"],["observation_sha","sha256",null]]],"CandidateAttemptAudit":["attempt_sha",[["attempt_schema_version","str",null],["control_registry_entry_sha","sha256"'
    ',null],["fejer_order","int",null],["reference_outcome","EndpointReferenceOutcome","EndpointReferenceOutcome"],["shell_outcome","Optional[EndpointShellOutcome]","EndpointShellOutcome"],["paired_response_outcome","Optional[PairedResponseOutcome]","PairedResponseOutcome"],["attempt_sha","sha256",null]]],"ClosedControlRegistry":["registry_sha",[["registry_schema_version","str",null],["entries","tuple[ControlRegistryEntry,...]","ControlRegistryEntry"],["parent_freeze_sha","sha256",null],["registry_sha","sha256",null]]],"CoefficientRecord":[null,[["mechanism_id","str",null],["expression_schema","Literal[v3m0.sympy-exact-ast.v1]",null],["variable_order","tuple[str,...]",null],["expression_ast","tuple[tagged-expression-node,...]",null],["provenance_root_id","str",null],["coefficient_digest","sha256",null]]],"ConstructionTrace":["trace_sha",[["schema_version","str",null],["grammar_id","str",null],["target_spec_id","str",null],["provenance_nodes","tuple[ProvenanceNode,...]","ProvenanceNode"],["c'
    'oefficient_records","tuple[CoefficientRecord,...]","CoefficientRecord"],["primitives","tuple[PrimitiveTrace,...]","PrimitiveTrace"],["trace_sha","sha256",null]]],"ControlCandidateAudit":["audit_sha",[["control_registry_entry","ControlRegistryEntry","ControlRegistryEntry"],["expected_rank_declaration","ExpectedRankDeclaration","ExpectedRankDeclaration"],["candidate_t","ControlCandidateOutcome","ControlCandidateOutcome"],["comparison_2t","ControlCandidateOutcome","ControlCandidateOutcome"],["readout_spectrum_audits","tuple[PerControlReadoutSpectrumAudit,...]","PerControlReadoutSpectrumAudit"],["comparison_2t_readout_spectrum_audits","tuple[PerControlReadoutSpectrumAudit,...]","PerControlReadoutSpectrumAudit"],["phase_separation","Optional[float64]",null],["overlap_margin","Optional[float64]",null],["projector_t2t_distance","Optional[float64]",null],["passed","bool",null],["audit_sha","sha256",null]]],"ControlCandidateOutcome":["outcome_sha",[["status","BlockStatus","BlockStatus"],["failu'
    're","Optional[ControlCandidateFailure]",null],["run_spec","ResponseRunSpec","ResponseRunSpec"],["attempt_audit","CandidateAttemptAudit","CandidateAttemptAudit"],["outcome_sha","sha256",null]]],"ControlReadoutCalibrationSpec":["spec_sha",[["spec_schema_version","str",null],["source_metric_whitener","FrozenComplexTensor","FrozenComplexTensor"],["h_metric_whitener","FrozenComplexTensor","FrozenComplexTensor"],["curvature_incidence_operator","FrozenComplexTensor","FrozenComplexTensor"],["curvature_metric_whitener","FrozenComplexTensor","FrozenComplexTensor"],["curvature_normalizer_id","Literal[synthetic-identity-v1]",null],["spec_sha","sha256",null]]],"ControlRegistryEntry":["entry_sha",[["entry_schema_version","str",null],["control_id","Literal[full,zero,direct_sum]",null],["builder_id","str",null],["factory_sha","sha256",null],["source_basis","BasisManifest","BasisManifest"],["readout_basis","BasisManifest","BasisManifest"],["readout_calibration_spec","ControlReadoutCalibrationSpec","Con'
    'trolReadoutCalibrationSpec"],["mode_count","int",null],["expected_h_actual_rank","int",null],["expected_h_ablated_rank","int",null],["expected_curv_actual_rank","int",null],["expected_curv_ablated_rank","int",null],["parent_freeze_sha","sha256",null],["entry_sha","sha256",null]]],"ControlWindowProtocolEntry":["entry_sha",[["control_id","Literal[full,zero,direct_sum]",null],["control_registry_entry_sha","sha256",null],["response_grid","ResponseKGridManifest","ResponseKGridManifest"],["source_readout_bridge_grid","BridgeKGridManifest","BridgeKGridManifest"],["source_readout_bridge_steps","tuple[int,...]",null],["reference_reciprocal_index","tuple[int,...]",null],["expected_shell_rank","int",null],["expected_shell_rank_source_id","Literal[parent-freeze-control-application-spec-v1]",null],["preregistered_phase_bands","tuple[tuple[float64,float64],...]",null],["source_trial_generation_id","Literal[registry-source-identity-v1]",null],["entry_sha","sha256",null]]],"CurrentApplicationAuthority'
    'V2":["application_authority_sha",[["application_authority_schema_version","str",null],["authority_state","Literal[CURRENT_REVIEWED_APPLICATION]",null],["control_case_id","str",null],["application_instance_id","str",null],["based_on_application_spec_sha","sha256",null],["source_candidate_v1_application_sha","sha256",null],["complete_scenario_execution_specs","tuple[ApplicationScenarioExecutionSpec,...]","ApplicationScenarioExecutionSpec"],["scenario_authorities","tuple[CurrentScenarioAuthorityV2,...]","CurrentScenarioAuthorityV2"],["application_authority_sha","sha256",null]]],"CurrentApplicationAuthorityV3":["application_authority_sha",[["application_authority_schema_version","str",null],["authority_state","Literal[PROVISIONAL_NOT_ISSUED]",null],["claim_ceiling","Literal[OBSERVER_COLLAPSE_TRIGGER_CONTROL_ONLY]",null],["causal_contrast_role","Literal[NULL_INTERVENTION_INVARIANCE_CONTROL]",null],["physical_anchor_eligibility","Literal[INELIGIBLE]",null],["family_eligibility","Literal[INEL'
    'IGIBLE]",null],["control_case_id","str",null],["application_instance_id","str",null],["source_disposition","Literal[C19_REFREEZE_V2_REVIEWED]",null],["source_candidate_sha","sha256",null],["design_source_path","str",null],["design_source_sha","sha256",null],["design_freeze_commit_sha","git-sha1",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["state_shape","tuple[int,...]",null],["spatial_shape","tuple[int,...]",null],["spatial_ndim","Literal[1]",null],["common_source_basis","BasisManifest","BasisManifest"],["common_readout_basis","BasisManifest","BasisManifest"],["common_source_tensor","FrozenComplexTensor","FrozenComplexTensor"],["common_readout_tensor","FrozenComplexTensor","FrozenComplexTensor"],["runtime_construction","C19RuntimeConstructionV2","C19RuntimeConstructionV2"],["runtime_construction_sha","sha256",null],["basis_contract_sha","sha256",null],["grid_protocol_root_sha","sha256",null],["operation_registry","tuple[tuple[Literal[actual,matched_abl'
    'ated],int,str,Primitive],...]","Primitive"],["operation_registry_sha","sha256",null],["construction_dependency_closure_state","Literal[PROVISIONAL_CONSTRUCTION_DEPENDENCIES_NOT_SIGNED]",null],["construction_dependency_closure","tuple[tuple[str,sha256],...]",null],["construction_dependency_closure_sha","sha256",null],["actual_active_step_count","Literal[50]",null],["matched_active_step_count","Literal[30]",null],["actual_layer_slot_count","Literal[50]",null],["matched_layer_slot_count","Literal[50]",null],["actual_primitive_count","Literal[50]",null],["matched_primitive_count","Literal[50]",null],["matched_neutral_identity_count","Literal[20]",null],["operation_dag_sha","sha256",null],["target_spec_sha","sha256",null],["actual_factory_sha","sha256",null],["matched_factory_sha","sha256",null],["ablation_manifest_sha","sha256",null],["actual_slot_program_sha","sha256",null],["matched_slot_program_sha","sha256",null],["actual_active_effect_digest","sha256",null],["matched_active_effect_dig'
    'est","sha256",null],["scenario_authorities","tuple[CurrentScenarioAuthorityV3,...]","CurrentScenarioAuthorityV3"],["application_authority_sha","sha256",null]]],"CurrentCurvatureNormalizerProtocolV1":["protocol_sha",[["protocol_schema_version","Literal[v3m0.current-curvature-normalizer-protocol.v1]",null],["normalizer_id","Literal[spin2-lattice-khat2-nonzero-v1]",null],["formula_id","Literal[nu-inc-4-sum-sin2-half-v1]",null],["derivation_id","Literal[2-exp(+ik)-exp(-ik)-centered-second-difference-v1]",null],["spatial_shape","tuple[int;exact=1,value=8]",null],["response_grid_sha","sha256",null],["ordered_reciprocal_indices","tuple[tuple[int;exact=1],...;exact=response-grid-size]",null],["ordered_momentum_values","tuple[tuple[float64;exact=1],...;exact=response-grid-size]",null],["ordered_momentum_fp64_bits","tuple[tuple[hex64;exact=1],...;exact=response-grid-size]",null],["ordered_normalizer_values","tuple[float64,...;exact=response-grid-size]",null],["ordered_normalizer_fp64_bits","tupl'
    'e[hex64,...;exact=response-grid-size]",null],["zero_mode_policy","Literal[excluded-from-curvature-rank-and-scaling]",null],["protocol_sha","sha256",null]]],"CurrentReadoutCalibrationSpecV3":["spec_sha",[["spec_schema_version","Literal[v3m0.current-readout-calibration-spec.v3]",null],["derivation_id","Literal[c19-geometry-bundle-readout-calibration-v1]",null],["geometry_bundle_sha","sha256",null],["source_metric_whitener","FrozenComplexTensor[10x10]","FrozenComplexTensor"],["h_metric_whitener","FrozenComplexTensor[10x10]","FrozenComplexTensor"],["curvature_incidence_operator","FrozenComplexTensor[6x10]","FrozenComplexTensor"],["curvature_normalizer_protocol","CurrentCurvatureNormalizerProtocolV1","CurrentCurvatureNormalizerProtocolV1"],["curvature_metric_whitener","FrozenComplexTensor[6x6]","FrozenComplexTensor"],["spec_sha","sha256",null]]],"CurrentScenarioAuthorityV2":["scenario_authority_sha",[["scenario_authority_schema_version","str",null],["authority_state","Literal[CURRENT_REVIEW'
    'ED_SCENARIO]",null],["control_case_id","str",null],["application_instance_id","str",null],["based_on_application_spec_sha","sha256",null],["scenario_id","str",null],["scenario_execution_spec","ApplicationScenarioExecutionSpec","ApplicationScenarioExecutionSpec"],["source_disposition","Literal[CANDIDATE_V2_REVIEWED_MODIFIED,CANDIDATE_V1_REVIEWED_UNCHANGED,PARENT_V1_TASK8_SELECTED_CALIBRATION_LANE,PARENT_V1_C04_CLOSED_RECIPE]",null],["source_candidate_v1_scenario_sha","sha256",null],["source_candidate_v2_refreeze_sha","Optional[sha256]",null],["response_contract","CurrentScenarioResponseContractV2","CurrentScenarioResponseContractV2"],["scenario_authority_sha","sha256",null]]],"CurrentScenarioAuthorityV3":["scenario_authority_sha",[["scenario_authority_schema_version","str",null],["authority_state","Literal[PROVISIONAL_NOT_ISSUED]",null],["control_case_id","str",null],["application_instance_id","str",null],["scenario_id","str",null],["source_disposition","Literal[C19_REFREEZE_V2_REVIEWED'
    ']",null],["source_candidate_sha","sha256",null],["source_runtime_construction_sha","sha256",null],["source_basis_contract_sha","sha256",null],["response_contract","CurrentScenarioResponseContractV3","CurrentScenarioResponseContractV3"],["scenario_authority_sha","sha256",null]]],"CurrentScenarioResponseContractV2":["response_contract_sha",[["response_contract_schema_version","str",null],["contract_state","Literal[CURRENT_REVIEWED_RESPONSE_CONTRACT]",null],["scenario_id","str",null],["selector_sha","sha256",null],["selector_spec","ScenarioBasisSelectorSpec","ScenarioBasisSelectorSpec"],["source_trial_vectors","FrozenComplexTensor","FrozenComplexTensor"],["response_torus_denominators","tuple[int,...]",null],["response_reciprocal_indices","tuple[tuple[int,...],...]",null],["source_readout_bridge_reciprocal_indices","tuple[tuple[int,...],...]",null],["source_readout_bridge_steps","tuple[int,...]",null],["reference_reciprocal_index","tuple[int,...]",null],["preregistered_phase_bands","tuple['
    'tuple[float,float],...]",null],["operation_dag_sha","sha256",null],["compiled_contract_sha","sha256",null],["construction_rule_id","str",null],["construction_family_id","str",null],["expected_actual_shell_rank","int",null],["expected_matched_shell_rank","int",null],["actual_step_count","int",null],["matched_ablated_step_count","int",null],["actual_program_sha","sha256",null],["matched_ablated_program_sha","sha256",null],["preflight_derivation_or_recipe_sha","sha256",null],["actual_effect_digest","sha256",null],["matched_ablated_effect_digest","sha256",null],["response_template_sha","sha256",null],["prediction_profile_sha","sha256",null],["uses_global_fft_projection","Literal[false]",null],["uses_per_k_time_step_projector","Literal[false]",null],["response_contract_sha","sha256",null]]],"CurrentScenarioResponseContractV3":["response_contract_sha",[["response_contract_schema_version","Literal[v3m0.current-scenario-response-contract.v3]",null],["contract_state","Literal[PROVISIONAL_NOT_IS'
    'SUED]",null],["control_case_id","Literal[C19_FULL_POSITIVE_OBSERVER_COLLAPSE]",null],["application_instance_id","str",null],["scenario_id","str",null],["basis_contract","C19BasisContractV2","C19BasisContractV2"],["dynamics_grid_derivation","DynamicsKGridDerivationProtocolV1","DynamicsKGridDerivationProtocolV1"],["metric_support_derivation","MetricSupportDerivationProtocolV1","MetricSupportDerivationProtocolV1"],["response_grid","ResponseKGridManifest","ResponseKGridManifest"],["response_reference_reciprocal_index","tuple[int;exact=1]",null],["preregistered_phase_bands","tuple[tuple[float64,float64],...;exact=1]",null],["reference_phase_band_source_id","Literal[analytic-quarter-turn-positive-band-v1]",null],["expected_shell_rank_source_id","Literal[parent-v3-current-scenario-prophecy-v1]",null],["source_trial_generation_id","Literal[c19-positive-frequency-coordinate-identity-v1]",null],["bridge_grid_derivation","BridgeKGridDerivationProtocolV1","BridgeKGridDerivationProtocolV1"],["bridg'
    'e_tolerance","float64",null],["bridge_tolerance_source_id","Literal[v3m0-frozen-thresholds-bridge-tolerance-v1]",null],["geometry_bundle","C19ObserverGeometryBundleV1","C19ObserverGeometryBundleV1"],["current_readout_calibration_spec","CurrentReadoutCalibrationSpecV3","CurrentReadoutCalibrationSpecV3"],["runtime_construction_sha","sha256",null],["actual_factory_sha","sha256",null],["matched_factory_sha","sha256",null],["operation_dag_sha","sha256",null],["expected_actual_shell_rank","Literal[10]",null],["expected_matched_shell_rank","Literal[10]",null],["runtime_artifact_state","Literal[DYNAMICS_AND_BRIDGE_NOT_DERIVED_PRE_RESPONSE]",null],["measurement_state","Literal[NOT_EVALUATED_PRE_RESPONSE]",null],["uses_global_fft_projection","Literal[false]",null],["uses_per_k_time_step_projector","Literal[false]",null],["response_contract_sha","sha256",null]]],"DirectionManifest":["direction_manifest_sha",[["direction_schema_version","str",null],["direction_ids","tuple[str,...]",null],["primiti'
    've_directions","tuple[tuple[int,...],...]",null],["path_ids","tuple[str,...]",null],["ordered_paths","tuple[tuple[tuple[int,...],...],...]",null],["closure_path_pairs","tuple[DirectionPathClosure,...]","DirectionPathClosure"],["direction_manifest_sha","sha256",null]]],"DirectionPathClosure":[null,[["closure_id","str",null],["first_path_id","str",null],["first_path_position","int",null],["second_path_id","str",null],["second_path_position","int",null],["reciprocal_index","tuple[int,...]",null]]],"DynamicsCertificateV3":["certificate_sha",[["certificate_schema_version","str",null],["parent_freeze_v3","ParentFreezeV3Manifest","ParentFreezeV3Manifest"],["materialization","ApplicationScenarioMaterializationV3","ApplicationScenarioMaterializationV3"],["transition_authority","TransitionAuthorityV3","TransitionAuthorityV3"],["metric_attestation","MetricSignedSupportAttestationV1","MetricSignedSupportAttestationV1"],["bridge_grid_authority","BridgeGridAuthorityV3","BridgeGridAuthorityV3"],["dyn'
    'amics_grid_authority","DynamicsGridAuthorityV3","DynamicsGridAuthorityV3"],["prestructure_authority","PrestructureAuthority","PrestructureAuthority"],["structure","StructureManifest","StructureManifest"],["reality","Optional[RealityCertificate]","RealityCertificate"],["stability_metric","StabilityMetricWitness","StabilityMetricWitness"],["fp64_enclosure_protocol","Fp64EnclosureProtocol","Fp64EnclosureProtocol"],["full_state_bridge_spec","FullStateBridgeSpec","FullStateBridgeSpec"],["full_state_bridge_audit","BridgeAudit","BridgeAudit"],["structure_residual","LaurentResidualCertificate","LaurentResidualCertificate"],["metric_residual","LaurentResidualCertificate","LaurentResidualCertificate"],["spectral_margins","SpectralMarginCoverage","SpectralMarginCoverage"],["normalized_metric_residual","NormalizedMetricResidualAudit","NormalizedMetricResidualAudit"],["power_drift","PowerDriftAudit","PowerDriftAudit"],["runtime","RuntimeEvidenceManifest","RuntimeEvidenceManifest"],["certificate_sha'
    '","sha256",null]]],"DynamicsCertificationAttemptAuditV3":["attempt_sha",[["attempt_schema_version","str",null],["parent_freeze_v3_sha","sha256",null],["materialization_sha","sha256",null],["transition_authority_sha","sha256",null],["metric_attestation_sha","sha256",null],["bridge_grid_authority_sha","sha256",null],["dynamics_grid_authority_sha","sha256",null],["first_failure","Optional[DynamicsCertificationFailure]",null],["reality","Optional[RealityCertificate]","RealityCertificate"],["structure_residual","Optional[LaurentResidualCertificate]","LaurentResidualCertificate"],["metric_residual","Optional[LaurentResidualCertificate]","LaurentResidualCertificate"],["spectral_margins","Optional[SpectralMarginCoverage]","SpectralMarginCoverage"],["normalized_metric_residual","Optional[NormalizedMetricResidualAudit]","NormalizedMetricResidualAudit"],["full_state_bridge_audit","Optional[BridgeAudit]","BridgeAudit"],["power_drift","Optional[PowerDriftAudit]","PowerDriftAudit"],["instability_cou'
    'nter_witness","Optional[InstabilityGrowthCounterWitness]","InstabilityGrowthCounterWitness"],["attempt_sha","sha256",null]]],"DynamicsCertificationOutcomeV3":["outcome_sha",[["status","BlockStatus","BlockStatus"],["failure","Optional[DynamicsCertificationFailure]",null],["attempt_audit","DynamicsCertificationAttemptAuditV3","DynamicsCertificationAttemptAuditV3"],["certificate","Optional[DynamicsCertificateV3]","DynamicsCertificateV3"],["outcome_sha","sha256",null]]],"DynamicsGridAuthorityV3":["grid_authority_sha",[["grid_authority_schema_version","str",null],["transition_authority","TransitionAuthorityV3","TransitionAuthorityV3"],["metric_support_attestation","MetricSignedSupportAttestationV1","MetricSignedSupportAttestationV1"],["derivation_protocol","DynamicsKGridDerivationProtocolV1","DynamicsKGridDerivationProtocolV1"],["dynamics_grid","DynamicsKGridManifest","DynamicsKGridManifest"],["grid_authority_sha","sha256",null]]],"DynamicsKGridDerivationProtocolV1":["protocol_sha",[["proto'
    'col_schema_version","str",null],["branch_roles","tuple[Literal[actual,matched_ablated],...]",null],["transition_support_source","str",null],["metric_support_source","str",null],["derivation_algorithm","str",null],["exact_zero_qualification_profile","str",null],["nonzero_fallback_profile","str",null],["caller_supplied_points_allowed","Literal[false]",null],["fail_closed_condition_ids","tuple[str,...]",null],["protocol_sha","sha256",null]]],"DynamicsKGridManifest":["dynamics_grid_sha",[["grid_schema_version","str",null],["qualification_profile","Literal[exact-offset-zero-v1,cartesian-full-64-v1]",null],["spatial_ndim","int",null],["torus_denominators","tuple[int,...]",null],["reciprocal_indices","tuple[tuple[int,...],...]",null],["dynamics_grid_sha","sha256",null]]],"EndpointReferenceAttemptAudit":["attempt_sha",[["attempt_schema_version","str",null],["reference_spec","EndpointReferenceSpec","EndpointReferenceSpec"],["candidate_phases","tuple[float64,...]",null],["candidate_ranks","tuple'
    '[int,...]",null],["expected_shell_rank","int",null],["expected_shell_rank_source_id","Literal[parent-freeze-control-application-spec-v1]",null],["candidate_participations","tuple[float64,...]",null],["runner_up_overlaps","tuple[Optional[float64],...]",null],["hermitian_residuals","tuple[float64,...]",null],["idempotent_residuals","tuple[float64,...]",null],["g_invariance_residuals","tuple[float64,...]",null],["eigenphase_residuals","tuple[float64,...]",null],["observed_competitor_gaps","tuple[Optional[float64],...]",null],["attempt_sha","sha256",null]]],"EndpointReferenceOutcome":["outcome_sha",[["status","BlockStatus","BlockStatus"],["failure","Optional[EndpointReferenceFailure]",null],["reference_spec","EndpointReferenceSpec","EndpointReferenceSpec"],["attempt_audit","EndpointReferenceAttemptAudit","EndpointReferenceAttemptAudit"],["reference","Optional[EndpointReferenceProjector]","EndpointReferenceProjector"],["outcome_sha","sha256",null]]],"EndpointReferenceProjector":["reference_'
    'sha",[["reference_schema_version","str",null],["control_registry_entry_sha","sha256",null],["actual_transition_sha","sha256",null],["actual_dynamics_certificate_sha","sha256",null],["reference_reciprocal_index","tuple[int,...]",null],["reference_phase","float64",null],["projector_coordinate_convention_id","Literal[g-whitened-state-v1]",null],["rank","int",null],["projector","FrozenComplexTensor","FrozenComplexTensor"],["reference_sha","sha256",null]]],"EndpointReferenceSpec":["reference_spec_sha",[["reference_spec_schema_version","str",null],["window_protocol_sha","sha256",null],["control_registry_entry","ControlRegistryEntry","ControlRegistryEntry"],["actual_factory_sha","sha256",null],["actual_transition_sha","sha256",null],["actual_dynamics_certificate_sha","sha256",null],["candidate_fejer_order","int",null],["reference_reciprocal_index","tuple[int,...]",null],["preregistered_phase_bands","tuple[tuple[float64,float64],...]",null],["expected_shell_rank","int",null],["expected_shell_r'
    'ank_source_id","Literal[parent-freeze-control-application-spec-v1]",null],["reference_spec_sha","sha256",null]]],"EndpointShellAttemptAudit":["attempt_sha",[["attempt_schema_version","str",null],["shell_spec","EndpointShellSpec","EndpointShellSpec"],["point_attempts","tuple[ShellCandidatePointAttempt,...]","ShellCandidatePointAttempt"],["projector_residual_max","float64",null],["loop_residual_max_observed","Optional[float64]",null],["attempt_sha","sha256",null]]],"EndpointShellManifest":["shell_manifest_sha",[["shell_schema_version","str",null],["actual_factory_sha","sha256",null],["actual_transition_sha","sha256",null],["actual_dynamics_certificate_sha","sha256",null],["shell_spec","EndpointShellSpec","EndpointShellSpec"],["dt","float64",null],["eigenphase_convention_id","Literal[lambda-exp-plus-i-theta-principal-v1]",null],["shell_phases","tuple[float64,...]",null],["shell_projectors","FrozenComplexTensor","FrozenComplexTensor"],["point_audits","tuple[ShellPointAudit,...]","ShellPoin'
    'tAudit"],["hermitian_residual_max","float64",null],["idempotent_residual_max","float64",null],["g_invariance_residual_max","float64",null],["eigenphase_residual_max","float64",null],["participation_min","float64",null],["nearest_competitor_gap_min","Optional[float64]",null],["reference_overlap_min","float64",null],["runner_up_overlap_max","Optional[float64]",null],["predecessor_overlap_min","Optional[float64]",null],["overlap_margin_min","Optional[float64]",null],["loop_residual_max","Optional[float64]",null],["ambiguous","bool",null],["shell_manifest_sha","sha256",null]]],"EndpointShellOutcome":["outcome_sha",[["status","BlockStatus","BlockStatus"],["failure","Optional[EndpointShellFailure]",null],["reference_outcome","EndpointReferenceOutcome","EndpointReferenceOutcome"],["attempt_audit","EndpointShellAttemptAudit","EndpointShellAttemptAudit"],["shell","Optional[EndpointShellManifest]","EndpointShellManifest"],["outcome_sha","sha256",null]]],"EndpointShellSpec":["shell_spec_sha",[["s'
    'hell_spec_schema_version","str",null],["window_protocol_sha","sha256",null],["control_registry_entry","ControlRegistryEntry","ControlRegistryEntry"],["response_grid","ResponseKGridManifest","ResponseKGridManifest"],["preregistered_phase_bands","tuple[tuple[float64,float64],...]",null],["candidate_fejer_order","int",null],["endpoint_reference_projector","EndpointReferenceProjector","EndpointReferenceProjector"],["extraction_protocol_id","Literal[endpoint-single-node-reference-v1]",null],["shell_spec_sha","sha256",null]]],"ExpectedRankDeclaration":["declaration_sha",[["declaration_schema_version","str",null],["control_registry_sha","sha256",null],["control_registry_entry_sha","sha256",null],["control_id","Literal[full,zero,direct_sum]",null],["expected_h_actual_rank","int",null],["expected_h_ablated_rank","int",null],["expected_curv_actual_rank","int",null],["expected_curv_ablated_rank","int",null],["parent_freeze_sha","sha256",null],["declaration_sha","sha256",null]]],"FactoryBranchBind'
    'ingV3":["binding_sha",[["binding_schema_version","str",null],["parent_freeze_v3_sha","sha256",null],["permit_sha","sha256",null],["materialization_input_sha","sha256",null],["branch","Literal[actual,matched_ablated]",null],["factory","LinearRealspaceFactory","LinearRealspaceFactory"],["construction_trace","ConstructionTrace","ConstructionTrace"],["layer_slot_ids","tuple[str,...]",null],["support_offsets","tuple[tuple[int,...],...]",null],["support_sha","sha256",null],["active_step_count","int",null],["layer_slot_count","Literal[50]",null],["primitive_count","Literal[50]",null],["neutral_identity_count","int",null],["binding_sha","sha256",null]]],"Fp64EnclosureProtocol":["protocol_sha",[["protocol_schema_version","str",null],["unit_roundoff_numerator","Literal[1]",null],["unit_roundoff_denominator","Literal[9007199254740992]",null],["minimum_subnormal_numerator","Literal[1]",null],["minimum_subnormal_power_of_two","Literal[-1074]",null],["gamma_bound_method_id","Literal[integer-ratio-q-'
    'u-over-one-minus-q-u-v1]",null],["complex_add_real_add_count","Literal[2]",null],["complex_multiply_real_multiply_count","Literal[4]",null],["complex_multiply_real_add_count","Literal[2]",null],["matrix_dot_operation_count_id","Literal[complex-dot-real-component-q-equals-4n-minus-1-v1]",null],["scalar_expression_dag_id","Literal[ordered-four-real-products-and-additions-no-fma-v1]",null],["roundoff_bound_id","Literal[gamma-q-times-absolute-product-sum-plus-minsub-v1]",null],["gradual_underflow_additive_id","Literal[real-operation-count-times-minsub-v1]",null],["root_center_error_propagation_id","Literal[coefficient-frobenius-sum-times-root-center-distance-v1]",null],["frobenius_sqrt_containment_id","Literal[exact-integer-ratio-square-containment-v1]",null],["fma_policy","Literal[forbidden]",null],["reassociation_policy","Literal[forbidden]",null],["finite_value_policy","Literal[finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-overflow-v1]",null],["outward_rounding_id","'
    'Literal[nextafter-after-every-scalar-op-v1]",null],["root_interval_table","Fp64RootOfUnityIntervalTable","Fp64RootOfUnityIntervalTable"],["protocol_sha","sha256",null]]],"Fp64RootIntervalEntry":[null,[["root_index","int",null],["dyadic_exponent","Literal[192]",null],["real_lower_numerator","int",null],["real_upper_numerator","int",null],["imag_lower_numerator","int",null],["imag_upper_numerator","int",null],["real_center_f64_bits","int",null],["imag_center_f64_bits","int",null],["center_distance_squared_upper_numerator","int",null],["center_distance_squared_upper_power_of_two","Literal[-384]",null],["center_distance_upper_f64_bits","int",null]]],"Fp64RootOfUnityIntervalTable":["table_sha",[["table_schema_version","str",null],["table_id","Literal[root64-dyadic-machin-taylor-containment-v1]",null],["denominator","Literal[64]",null],["dyadic_exponent","Literal[192]",null],["pi_lower_numerator","int",null],["pi_upper_numerator","int",null],["machin_identity_id","Literal[pi-equals-16atan1ov'
    'er5-minus4atan1over239-v1]",null],["taylor_precision_bits","Literal[192]",null],["remainder_method_id","Literal[bigint-alternating-rational-remainder-v1]",null],["entries","tuple[Fp64RootIntervalEntry,...]","Fp64RootIntervalEntry"],["table_sha","sha256",null]]],"FrozenComplexTensor":["tensor_sha",[["tensor_schema_version","str",null],["shape","tuple[int,...]",null],["values_wire","tuple[tuple[float,float],...]",null],["tensor_sha","sha256",null]]],"FrozenSyntheticTarget":[null,[["target_schema_version","str",null],["target_spec_id","str",null],["target_spec_sha","sha256",null],["calibration_protocol_id","str",null],["seed_sha","sha256",null],["observation","CalibrationObservation","CalibrationObservation"],["target_response","FrozenComplexTensor","FrozenComplexTensor"],["runtime_operator_sha","sha256",null]]],"FullStateBridgeSpec":["bridge_spec_sha",[["bridge_spec_schema_version","str",null],["factory_sha","sha256",null],["parent_freeze_sha","sha256",null],["prestructure_authority_sha"'
    ',"sha256",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["spatial_shape","tuple[int,...]",null],["bridge_grid","BridgeKGridManifest","BridgeKGridManifest"],["macro_steps","tuple[int,...]",null],["state_trial_vectors","FrozenComplexTensor","FrozenComplexTensor"],["trial_generation_id","Literal[canonical-or-sha256-dense-v1]",null],["trial_seed_sha","sha256",null],["trial_domain_separator","Literal[v3m0-full-state-bridge-trials-v1]",null],["trial_gram_frobenius_upper","float64",null],["trial_gram_gate_method_id","Literal[outward-frobenius-dominates-spectral-v1]",null],["bridge_tolerance","float64",null],["bridge_spec_sha","sha256",null]]],"InstabilityGrowthCounterWitness":["witness_sha",[["witness_schema_version","str",null],["witness_profile","Literal[exact-zero-offset-jordan-2x2-v1]",null],["parent_freeze_sha","sha256",null],["prestructure_authority_sha","sha256",null],["transition","MeasuredTransition","MeasuredTransition"],["transition_matrix","FrozenCom'
    'plexTensor","FrozenComplexTensor"],["support_offsets","tuple[tuple[int,...],...]",null],["macro_step","Literal[16384]",null],["initial_vector","FrozenComplexTensor","FrozenComplexTensor"],["exact_power_formula_id","Literal[jordan-one-one-zero-one-power-v1]",null],["initial_norm_squared","Literal[1]",null],["final_norm_squared","Literal[268435457]",null],["required_growth_squared_strict_upper","Literal[100000001]",null],["witness_sha","sha256",null]]],"LaurentResidualCertificate":["residual_sha",[["residual_schema_version","str",null],["residual_kind","Literal[canonical-structure,stability-metric]",null],["operand_shas","tuple[sha256,...]",null],["spatial_ndim","int",null],["n_state","int",null],["fp64_enclosure_protocol_sha","sha256",null],["fourier_convention_id","Literal[signed-displacement-exp-minus-i-k-dot-d-v1]",null],["matrix_norm_id","Literal[spectral-2-v1]",null],["momentum_supremum_method_id","Literal[sum-of-directed-outward-frobenius-upper-v1]",null],["support_offsets","tuple'
    '[tuple[int,...],...]",null],["coefficients","FrozenComplexTensor","FrozenComplexTensor"],["convolution_pair_counts","tuple[int,...]",null],["coefficient_roundoff_frobenius_uppers","tuple[float64,...]",null],["coefficient_frobenius_upper_sum","float64",null],["raw_global_momentum_supremum_bound","float64",null],["residual_sha","sha256",null]]],"LinearRealspaceFactory":["factory_sha",[["factory_schema_version","str",null],["factory_role","Literal[actual,matched_ablated]",null],["factory_id","str",null],["construction_trace_sha","sha256",null],["grammar_id","str",null],["target_spec_id","str",null],["target_spec_sha","sha256",null],["runtime_operator_sha","sha256",null],["interface","PrimitiveInterface","PrimitiveInterface"],["state_schema_id","str",null],["spatial_ndim","int",null],["channel_order","tuple[str,...]",null],["state_shape","tuple[int,...]",null],["dtype","str",null],["backend","str",null],["dt","float64",null],["target_blind_parameters","tuple[tuple[str,float64],...]",null],'
    '["layer_slot_ids","tuple[str,...]",null],["source_manifest_id","str",null],["readout_basis","BasisManifest","BasisManifest"],["boundary_manifest_id","str",null],["run_length","int",null],["primitives","tuple[Primitive,...]","Primitive"],["factory_sha","sha256",null]]],"MeasuredTransition":["transition_sha",[["transition_schema_version","str",null],["parent_freeze_sha","sha256",null],["prestructure_authority_sha","sha256",null],["factory_sha","sha256",null],["factory_role","Literal[actual,matched_ablated]",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["spatial_shape","tuple[int,...]",null],["dt","float64",null],["boundary_manifest_id","Literal[periodic-v1]",null],["state_basis_convention_id","Literal[channel-identity-v1]",null],["kernel","FrozenComplexTensor","FrozenComplexTensor"],["support_offsets","tuple[tuple[int,...],...]",null],["support_sha","sha256",null],["macro_steps","Literal[1]",null],["transition_sha","sha256",null]]],"MetricOriginManifest":['
    '"origin_sha",[["origin_schema_version","str",null],["origin_kind","Literal[synthetic-identity-v1,adapter-preregistered-v1]",null],["parent_freeze_sha","sha256",null],["prestructure_authority_sha","sha256",null],["factory_sha","sha256",null],["structure_manifest_sha","sha256",null],["evidence_lane","Literal[synthetic-classical,classical-adapter,quantum]",null],["derivation_or_preregistration_sha","sha256",null],["metric_kernel_sha","sha256",null],["metric_support_sha","sha256",null],["origin_sha","sha256",null]]],"MetricSignedSupportAttestationV1":["attestation_sha",[["attestation_schema_version","str",null],["parent_freeze_v3_sha","sha256",null],["current_application_authority_v3_sha","sha256",null],["current_scenario_authority_v3_sha","sha256",null],["response_contract_v3_sha","sha256",null],["metric_support_protocol_sha","sha256",null],["application_scenario_materialization_v3_sha","sha256",null],["factory_sha","sha256",null],["factory_role","Literal[actual,matched_ablated]",null],["'
    'state_schema_id","str",null],["channel_order","tuple[str,...]",null],["spatial_shape","tuple[int,...]",null],["metric_kind","Literal[constant-state-v1]",null],["metric_support_offsets","tuple[tuple[int,...],...]",null],["metric_support_sha","sha256",null],["attestation_sha","sha256",null]]],"MetricSupportDerivationProtocolV1":["protocol_sha",[["protocol_schema_version","str",null],["metric_kind","Literal[constant-state-v1]",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["spatial_shape","tuple[int,...]",null],["spatial_ndim","Literal[1]",null],["state_metric","FrozenComplexTensor","FrozenComplexTensor"],["normalization_id","Literal[trace-at-zero-equals-state-dim-v1]",null],["support_derivation_id","Literal[constant-kernel-origin-only-v1]",null],["metric_support_offsets","tuple[tuple[int,...],...]",null],["metric_support_sha","sha256",null],["caller_supplied_support_allowed","Literal[false]",null],["protocol_sha","sha256",null]]],"NormalizedMetricResidualAu'
    'dit":["audit_sha",[["audit_schema_version","str",null],["metric_residual_sha","sha256",null],["spectral_margin_coverage_sha","sha256",null],["raw_metric_residual_upper","float64",null],["covered_g_lambda_min_lower","float64",null],["division_method_id","Literal[fp64-nextafter-outward-division-v1]",null],["normalized_metric_residual_upper","float64",null],["audit_sha","sha256",null]]],"PairedFilteredResponse":["pair_sha",[["pair_schema_version","str",null],["ablation_manifest_sha","sha256",null],["qualification_sha","sha256",null],["actual_dynamics_certificate","DynamicsCertificateV3","DynamicsCertificateV3"],["ablated_dynamics_certificate","DynamicsCertificateV3","DynamicsCertificateV3"],["actual","SourceReadoutResponse","SourceReadoutResponse"],["ablated","SourceReadoutResponse","SourceReadoutResponse"],["run_spec","ResponseRunSpec","ResponseRunSpec"],["shell_manifest","EndpointShellManifest","EndpointShellManifest"],["pair_sha","sha256",null]]],"PairedResponseAttemptAudit":["attempt_'
    'sha",[["attempt_schema_version","str",null],["window_protocol","WindowCalibrationProtocol","WindowCalibrationProtocol"],["qualification_sha","sha256",null],["actual_factory_sha","sha256",null],["ablated_factory_sha","sha256",null],["actual_transition","TransitionAuthorityV3","TransitionAuthorityV3"],["ablated_transition","TransitionAuthorityV3","TransitionAuthorityV3"],["actual_dynamics_certificate","DynamicsCertificateV3","DynamicsCertificateV3"],["ablated_dynamics_certificate","DynamicsCertificateV3","DynamicsCertificateV3"],["run_spec","ResponseRunSpec","ResponseRunSpec"],["shell_outcome","EndpointShellOutcome","EndpointShellOutcome"],["actual_branch_attempt","Optional[SourceReadoutBranchAttemptAudit]","SourceReadoutBranchAttemptAudit"],["ablated_branch_attempt","Optional[SourceReadoutBranchAttemptAudit]","SourceReadoutBranchAttemptAudit"],["first_failure","Optional[PairedResponseFailure]",null],["attempt_sha","sha256",null]]],"PairedResponseOutcome":["outcome_sha",[["status","Block'
    'Status","BlockStatus"],["failure","Optional[PairedResponseFailure]",null],["attempt_audit","PairedResponseAttemptAudit","PairedResponseAttemptAudit"],["paired_response","Optional[PairedFilteredResponse]","PairedFilteredResponse"],["outcome_sha","sha256",null]]],"ParentFreezeCandidateV3Manifest":["candidate_sha",[["candidate_schema_version","str",null],["authority_state","Literal[PROVISIONAL_NOT_ISSUED]",null],["program_id","Literal[projective-rule-space-v3m0-v3]",null],["preparation_commit_sha","git-sha1",null],["historical_parent_v1","canonical-json-object",null],["reviewed_candidate_v1","canonical-json-object",null],["reviewed_candidate_v2","canonical-json-object",null],["inherited_current_application_authorities_v2","tuple[canonical-json-object,...]",null],["superseded_application_authorities_v2","tuple[canonical-json-object,...]",null],["refrozen_current_application_authorities_v3","tuple[CurrentApplicationAuthorityV3,...]","CurrentApplicationAuthorityV3"],["application_supersessio'
    'ns","tuple[canonical-json-object,...]",null],["block_success_scenario_ids","tuple[str,...]",null],["source_closure","canonical-json-object",null],["source_closure_sha","sha256",null],["candidate_sha","sha256",null]]],"ParentFreezeV3Manifest":["parent_freeze_v3_sha",[["parent_freeze_schema_version","str",null],["authority_state","Literal[CURRENT_PARENT_V3_ISSUED]",null],["program_id","Literal[projective-rule-space-v3m0-v3]",null],["preparation_commit_sha","git-sha1",null],["signing_commit_sha","git-sha1",null],["reviewed_candidate_v3","ParentFreezeCandidateV3Manifest","ParentFreezeCandidateV3Manifest"],["signed_source_refs","tuple[SignedSourceRefV2,...]","SignedSourceRefV2"],["review_receipts","tuple[ParentReviewReceiptV1,...]","ParentReviewReceiptV1"],["signing_audit","ParentSigningAuditV1","ParentSigningAuditV1"],["current_application_registry_sha","sha256",null],["parent_freeze_v3_sha","sha256",null]]],"ParentReviewReceiptV1":["receipt_sha",[["receipt_schema_version","str",null],["re'
    'view_role","str",null],["reviewer_id","str",null],["reviewer_key_id","str",null],["signature_algorithm","str",null],["preparation_commit_sha","git-sha1",null],["reviewed_candidate_sha","sha256",null],["reviewed_path_closure","tuple[tuple[str,sha256],...]",null],["reviewed_path_closure_sha","sha256",null],["verdict","Literal[PASS]",null],["signed_statement_sha","sha256",null],["signature_armor","str",null],["receipt_sha","sha256",null]]],"ParentSigningAuditV1":["audit_sha",[["audit_schema_version","str",null],["preparation_commit_sha","git-sha1",null],["signing_commit_sha","git-sha1",null],["review_receipt_shas","tuple[sha256,...]",null],["diff_digest","sha256",null],["diff_allowlist_id","str",null],["signed_source_refs_root_sha","sha256",null],["reviewed_candidate_sha","sha256",null],["reviewed_path_closure_sha","sha256",null],["source_closure_sha","sha256",null],["audit_sha","sha256",null]]],"ParentV3ApplicationPrestructure":["prestructure_authority_sha",[["prestructure_schema_version'
    '","str",null],["parent_freeze_v3_sha","sha256",null],["permit_sha","sha256",null],["materialization_sha","sha256",null],["current_application_authority_v3_sha","sha256",null],["current_scenario_authority_v3_sha","sha256",null],["current_scenario_response_contract_v3_sha","sha256",null],["factory_binding","FactoryBranchBindingV3","FactoryBranchBindingV3"],["factory_sha","sha256",null],["factory_role","Literal[actual,matched_ablated]",null],["ablation_pair_snapshot","AblationPairSnapshot","AblationPairSnapshot"],["basis_contract","C19BasisContractV2","C19BasisContractV2"],["evidence_lane","Literal[synthetic-classical]",null],["target_spec_sha","sha256",null],["state_schema_id","Literal[v3m0.c19-real-canonical-state.v2]",null],["channel_order","tuple[str,...]",null],["canonical_channel_pairs","tuple[tuple[str,str],...]",null],["fourier_adjoint_convention_id","Literal[minus-k-transpose-v1]",null],["structure_form","FrozenComplexTensor","FrozenComplexTensor"],["reality_convention_id","Liter'
    'al[real-kernel-positive-zero-v1]",null],["prestructure_authority_sha","sha256",null]]],"ParentV3CalibrationControlReplayRefV1":["replay_ref_sha",[["replay_ref_schema_version","str",null],["parent_freeze_v3_sha","sha256",null],["current_application_registry_sha","sha256",null],["parent_v1_ordinal","int",null],["authority_tag","Literal[INHERITED_CURRENT_V2]",null],["control_case_id","Literal[C01_BLIND_HOLDOUT_FULL,C02_CONDITIONED_ZERO,C03_EQUAL_RANK_DIRECT_SUM]",null],["control_id","Literal[full,zero,direct_sum]",null],["application_authority_v2","CurrentApplicationAuthorityV2","CurrentApplicationAuthorityV2"],["application_authority_v2_sha","sha256",null],["scenario_authority_v2","CurrentScenarioAuthorityV2","CurrentScenarioAuthorityV2"],["scenario_authority_v2_sha","sha256",null],["response_contract_v2","CurrentScenarioResponseContractV2","CurrentScenarioResponseContractV2"],["response_contract_v2_sha","sha256",null],["replay_ref_sha","sha256",null]]],"PerControlReadoutSpectrumAudit":['
    '"audit_sha",[["readout_kind","Literal[h,curv]",null],["control_registry_entry_sha","sha256",null],["expected_rank_declaration_sha","sha256",null],["fejer_order","int",null],["run_spec_sha","sha256",null],["paired_response_sha","sha256",null],["actual","BranchSpectrumAudit","BranchSpectrumAudit"],["ablated","BranchSpectrumAudit","BranchSpectrumAudit"],["actual_bridge_operator_error_upper","float64",null],["ablated_bridge_operator_error_upper","float64",null],["audit_sha","sha256",null]]],"PowerDriftAudit":["audit_sha",[["audit_schema_version","str",null],["normalized_metric_residual_audit_sha","sha256",null],["macro_step","Literal[16384]",null],["nonzero_delta_squaring_count","Literal[14]",null],["executed_squaring_count","Literal[0,14]",null],["identity_branch","bool",null],["method_id","Literal[t16384-directed-repeated-squaring-v1]",null],["delta_upper","float64",null],["one_minus_delta_lower","float64",null],["one_plus_delta_upper","float64",null],["growth_upper","float64",null],["co'
    'ntraction_upper","float64",null],["drift_upper","float64",null],["audit_sha","sha256",null]]],"PrestructureAuthority":["authority_sha",[["authority_schema_version","str",null],["authority_kind","Literal[synthetic-registry-v1,synthetic-application-v1,adapter-preregistration-v1]",null],["parent_freeze","canonical-json-object",null],["factory_sha","sha256",null],["factory_role","Literal[actual,matched_ablated]",null],["ablation_pair_snapshot","AblationPairSnapshot","AblationPairSnapshot"],["ablation_manifest_sha","sha256",null],["ablation_construction_sha","sha256",null],["synthetic_registry","Optional[ClosedControlRegistry]","ClosedControlRegistry"],["synthetic_registry_entry_sha","Optional[sha256]",null],["synthetic_preregistration","Optional[canonical-json-object]",null],["synthetic_application_spec","Optional[canonical-json-object]",null],["synthetic_application_scenario_spec","Optional[canonical-json-object]",null],["synthetic_application_permit_sha","Optional[sha256]",null],["synthe'
    'tic_scenario_construction_sha","Optional[sha256]",null],["adapter_preregistration","Optional[canonical-json-object]",null],["authority_sha","sha256",null]]],"Primitive":[null,[["primitive_schema_version","str",null],["mechanism_id","str",null],["production_id","str",null],["layer_slot_id","str",null],["operation_id","Literal[local_canonical_shear,neutral_identity]",null],["interface_id","str",null],["source_channel","str",null],["destination_channel","str",null],["offset","tuple[int,...]",null],["support_offsets","tuple[tuple[int,...],...]",null],["coefficient_wire","tuple[float,float]",null],["coefficient_digest","sha256",null],["neutral_identity_id","Optional[str]",null]]],"PrimitiveInterface":[null,[["interface_id","str",null],["state_schema_id","str",null],["spatial_ndim","int",null],["channel_order","tuple[str,...]",null],["dtype","Literal[complex128]",null],["backend","Literal[numpy]",null]]],"PrimitiveTrace":[null,[["grammar_id","str",null],["target_spec_id","str",null],["mechan'
    'ism_id","str",null],["production_id","str",null],["kind","MechanismKind",null],["depends_on","tuple[str,...]",null],["support_offsets","tuple[tuple[int,...],...]",null],["state_channels","tuple[str,...]",null],["coefficient_digest","sha256",null],["symbolic_origin_tags","tuple[str,...]",null],["neutral_ablation","Optional[str]",null],["design_objective_tags","tuple[str,...]",null],["search_run_id","Optional[str]",null],["source_sha","sha256",null],["design_provenance","str",null]]],"ProvenanceNode":[null,[["provenance_id","str",null],["operation","ProvenanceOperation",null],["depends_on","tuple[str,...]",null],["target_refs","tuple[str,...]",null],["objective_tags","tuple[str,...]",null],["search_run_id","Optional[str]",null],["source_sha","sha256",null]]],"ReadoutAggregateCalibrationAudit":["aggregate_sha",[["readout_kind","Literal[h,curv]",null],["per_control","tuple[PerControlReadoutSpectrumAudit,...]","PerControlReadoutSpectrumAudit"],["scale_ref","float64",null],["null_max","Optio'
    'nal[float64]",null],["bridge_operator_error_max","float64",null],["noise_ref","float64",null],["signal_min","float64",null],["tau_sig","float64",null],["signal_noise_ratio","float64",null],["raw_relative_gap","float64",null],["absolute_signal_gate_passed","bool",null],["relative_gap_gate_passed","bool",null],["aggregate_sha","sha256",null]]],"RealityCertificate":["reality_certificate_sha",[["reality_schema_version","str",null],["factory_sha","sha256",null],["transition_sha","sha256",null],["structure_manifest_sha","sha256",null],["factory_coefficient_count","int",null],["transition_entry_count","int",null],["imaginary_bit_pattern_id","Literal[all-positive-zero-f64-v1]",null],["implied_fourier_identity_id","Literal[m-minus-k-equals-conj-m-k-v1]",null],["reality_certificate_sha","sha256",null]]],"ResponseKGridManifest":["response_grid_sha",[["grid_schema_version","str",null],["qualification_profile","Literal[directional-momentum-shell-path-v1]",null],["spatial_ndim","int",null],["torus_d'
    'enominators","tuple[int,...]",null],["reciprocal_indices","tuple[tuple[int,...],...]",null],["direction_manifest","DirectionManifest","DirectionManifest"],["response_grid_sha","sha256",null]]],"ResponseRunSpec":["spec_sha",[["run_spec_schema_version","str",null],["run_spec_id","str",null],["window_protocol_sha","sha256",null],["control_registry_entry_sha","sha256",null],["fejer_order","int",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["source_basis","BasisManifest","BasisManifest"],["readout_basis","BasisManifest","BasisManifest"],["spatial_shape","tuple[int,...]",null],["response_grid","ResponseKGridManifest","ResponseKGridManifest"],["source_readout_bridge_grid","BridgeKGridManifest","BridgeKGridManifest"],["source_readout_bridge_steps","tuple[int,...]",null],["source_trial_vectors","FrozenComplexTensor","FrozenComplexTensor"],["bridge_tolerance","float64",null],["spec_sha","sha256",null]]],"ResponseRunSpecV3":["run_spec_sha",[["run_spec_schema_versio'
    'n","Literal[v3m0.response-run-spec.v3]",null],["parent_freeze_v3_sha","sha256",null],["permit_sha","sha256",null],["materialization_sha","sha256",null],["window_calibration_v3_sha","sha256",null],["window_protocol_sha","sha256",null],["window_selection_sha","sha256",null],["current_scenario_response_contract_v3_sha","sha256",null],["control_case_id","Literal[C19_FULL_POSITIVE_OBSERVER_COLLAPSE]",null],["application_instance_id","str",null],["scenario_id","str",null],["scenario_sha","sha256",null],["selected_fejer_order","int",null],["state_schema_id","Literal[v3m0.c19-real-canonical-state.v2]",null],["channel_order","tuple[str,...;exact=20]",null],["spatial_shape","tuple[int;exact=1,value=8]",null],["source_basis","BasisManifest","BasisManifest"],["readout_basis","BasisManifest","BasisManifest"],["source_injection_isometry","FrozenComplexTensor[20x10]","FrozenComplexTensor"],["readout_coisometry","FrozenComplexTensor[10x20]","FrozenComplexTensor"],["response_grid","ResponseKGridManifes'
    't","ResponseKGridManifest"],["source_readout_bridge_grid","BridgeKGridManifest","BridgeKGridManifest"],["source_readout_bridge_steps","tuple[int,...;nonempty]",null],["reference_reciprocal_index","tuple[int;exact=1]",null],["preregistered_phase_bands","tuple[tuple[float64,float64],...;exact=1]",null],["reference_phase_band_source_id","Literal[analytic-quarter-turn-positive-band-v1]",null],["expected_shell_rank","Literal[10]",null],["expected_shell_rank_source_id","Literal[parent-v3-current-scenario-prophecy-v1]",null],["source_trial_vectors","FrozenComplexTensor[10x10]","FrozenComplexTensor"],["source_trial_generation_id","Literal[c19-positive-frequency-coordinate-identity-v1]",null],["bridge_tolerance","float64",null],["bridge_tolerance_source_id","Literal[v3m0-frozen-thresholds-bridge-tolerance-v1]",null],["current_readout_calibration_spec","CurrentReadoutCalibrationSpecV3","CurrentReadoutCalibrationSpecV3"],["actual_bridge_grid_authority_sha","sha256",null],["matched_ablated_bridge_'
    'grid_authority_sha","sha256",null],["run_spec_sha","sha256",null]]],"RuntimeEvidenceManifest":["runtime_manifest_sha",[["runtime_schema_version","str",null],["evaluator_id","str",null],["source_closure","tuple[tuple[str,sha256],...]",null],["python_version","str",null],["numpy_version","str",null],["scipy_version","str",null],["blas_config_sha","sha256",null],["lapack_config_sha","sha256",null],["platform_id","str",null],["runtime_manifest_sha","sha256",null]]],"ScenarioBasisSelectorSpec":["selector_sha",[["selector_schema_version","str",null],["scenario_id","str",null],["public_source_basis_manifest_id","sha256",null],["public_readout_basis_manifest_id","sha256",null],["source_selector_derivation_id","str",null],["readout_selector_derivation_id","str",null],["source_selector","FrozenComplexTensor","FrozenComplexTensor"],["readout_selector","FrozenComplexTensor","FrozenComplexTensor"],["source_injection","FrozenComplexTensor","FrozenComplexTensor"],["readout_coisometry","FrozenComplexT'
    'ensor","FrozenComplexTensor"],["selector_sha","sha256",null]]],"SelectedControlEvidenceRef":[null,[["control_id","Literal[full,zero,direct_sum]",null],["control_registry_entry_sha","sha256",null],["expected_rank_declaration_sha","sha256",null],["run_spec_sha","sha256",null],["paired_response_sha","sha256",null],["shell_manifest_sha","sha256",null],["comparison_2t_run_spec_sha","sha256",null],["comparison_2t_response_sha","sha256",null],["comparison_2t_shell_manifest_sha","sha256",null]]],"ShellCandidatePointAttempt":[null,[["reciprocal_index","tuple[int,...]",null],["momentum_path_id","str",null],["momentum_path_position","int",null],["candidate_phases","tuple[float64,...]",null],["candidate_ranks","tuple[int,...]",null],["candidate_participations","tuple[float64,...]",null],["candidate_reference_overlaps","tuple[float64,...]",null],["candidate_predecessor_overlaps","tuple[Optional[float64],...]",null]]],"ShellPointAudit":[null,[["reciprocal_index","tuple[int,...]",null],["momentum_pat'
    'h_id","str",null],["momentum_path_position","int",null],["shell_phase","float64",null],["rank","int",null],["hermitian_residual","float64",null],["idempotent_residual","float64",null],["g_invariance_residual","float64",null],["eigenphase_residual","float64",null],["participation","float64",null],["nearest_competitor_gap","Optional[float64]",null],["reference_overlap","float64",null],["runner_up_overlap","Optional[float64]",null],["predecessor_overlap","Optional[float64]",null],["loop_residual","Optional[float64]",null]]],"SignedSourceRefV2":["source_ref_sha",[["source_ref_schema_version","str",null],["source_role","str",null],["source_scope","str",null],["relative_path","str",null],["raw_sha256","sha256",null],["preparation_commit_sha","git-sha1",null],["signing_commit_sha","git-sha1",null],["source_ref_sha","sha256",null]]],"SourceFrameCoverageCertificate":["certificate_sha",[["certificate_schema_version","str",null],["source_basis_sha","sha256",null],["trial_matrix","FrozenComplexTen'
    'sor","FrozenComplexTensor"],["frame_operator_lower","float64",null],["canonical_dual_residual_upper","float64",null],["certificate_sha","sha256",null]]],"SourceReadoutBranchAttemptAudit":["attempt_sha",[["branch","Literal[actual,matched_ablated]",null],["response_values","Optional[FrozenComplexTensor]","FrozenComplexTensor"],["bridge_audit","Optional[SourceReadoutBridgeAudit]","SourceReadoutBridgeAudit"],["failure","Optional[PairedResponseFailure]",null],["attempt_sha","sha256",null]]],"SourceReadoutBridgeAudit":["bridge_sha",[["bridge_schema_version","str",null],["branch","Literal[actual,matched_ablated]",null],["factory_sha","sha256",null],["transition_sha","sha256",null],["dynamics_certificate_sha","sha256",null],["run_spec_sha","sha256",null],["source_metric_whitener_sha","sha256",null],["readout_calibration_spec_sha","sha256",null],["matrix_audits","tuple[SourceReadoutBridgeMatrixAudit,...]","SourceReadoutBridgeMatrixAudit"],["h_operator_error_max","float64",null],["curv_operator_'
    'error_max","float64",null],["bridge_sha","sha256",null]]],"SourceReadoutBridgeMatrixAudit":[null,[["reciprocal_index","tuple[int,...]",null],["macro_steps","int",null],["raw_difference_matrix","FrozenComplexTensor","FrozenComplexTensor"],["frame_coverage","Optional[SourceFrameCoverageCertificate]","SourceFrameCoverageCertificate"],["raw_frobenius_upper","float64",null],["raw_operator_norm_upper","float64",null],["h_whitened_operator_error_upper","float64",null],["curv_whitened_operator_error_upper","float64",null]]],"SourceReadoutResponse":["response_sha",[["response_schema_version","str",null],["branch","Literal[actual,matched_ablated]",null],["factory_sha","sha256",null],["transition_sha","sha256",null],["dynamics_certificate_sha","sha256",null],["source_basis","BasisManifest","BasisManifest"],["readout_basis","BasisManifest","BasisManifest"],["run_spec_sha","sha256",null],["shell_manifest_sha","sha256",null],["bridge_audit","SourceReadoutBridgeAudit","SourceReadoutBridgeAudit"],["va'
    'lues","FrozenComplexTensor","FrozenComplexTensor"],["response_sha","sha256",null]]],"SpectralMarginCoverage":["coverage_sha",[["coverage_schema_version","str",null],["transition_sha","sha256",null],["stability_metric_witness_sha","sha256",null],["fp64_enclosure_protocol","Fp64EnclosureProtocol","Fp64EnclosureProtocol"],["qualification_grid","DynamicsKGridManifest","DynamicsKGridManifest"],["spectral_diagnostic_grid","DynamicsKGridManifest","DynamicsKGridManifest"],["torus_domain_id","Literal[minus-pi-pi-periodic-v1]",null],["distance_convention_id","Literal[principal-linf-torus-v1]",null],["fill_distance","float64",null],["raw_diagnostic_status","Literal[available-lapack-v1,unavailable-v1]",null],["raw_diagnostic_unavailable_reason","Optional[str]",null],["raw_m_sigma_min","Optional[tuple[float64,...]]",null],["raw_m_sigma_max","Optional[tuple[float64,...]]",null],["raw_g_lambda_min","Optional[tuple[float64,...]]",null],["raw_g_lambda_max","Optional[tuple[float64,...]]",null],["point_e'
    'nclosures","SpectralPointEnclosureColumnarSidecar","SpectralPointEnclosureColumnarSidecar"],["grid_m_sigma_min_lower","tuple[float64,...]",null],["grid_m_sigma_max_upper","tuple[float64,...]",null],["grid_g_lambda_min_lower","tuple[float64,...]",null],["grid_g_lambda_max_upper","tuple[float64,...]",null],["m_sigma_min_axis_derivative_bounds","tuple[float64,...]",null],["m_sigma_max_axis_derivative_bounds","tuple[float64,...]",null],["g_lambda_min_axis_derivative_bounds","tuple[float64,...]",null],["g_lambda_max_axis_derivative_bounds","tuple[float64,...]",null],["m_sigma_min_coverage_increment","float64",null],["m_sigma_max_coverage_increment","float64",null],["g_lambda_min_coverage_increment","float64",null],["g_lambda_max_coverage_increment","float64",null],["covered_m_sigma_min_lower","float64",null],["covered_m_sigma_max_upper","float64",null],["covered_g_lambda_min_lower","float64",null],["covered_g_lambda_max_upper","float64",null],["covered_m_condition_number_upper","float64",nu'
    'll],["covered_g_condition_number_upper","float64",null],["spectral_radius_drift_diagnostic","Optional[float64]",null],["coverage_sha","sha256",null]]],"SpectralPointEnclosureColumnarSidecar":["sidecar_sha",[["sidecar_schema_version","str",null],["qualification_grid_sha","sha256",null],["point_count","int",null],["candidate_algorithm_id","Literal[scalar-gauss-jordan-hermitian-cholesky-v1]",null],["encoding_id","Literal[strict-base64-big-endian-f64-columns-v1]",null],["raw_diagnostic_status","Literal[available-lapack-v1,unavailable-v1]",null],["raw_diagnostic_unavailable_reason","Optional[str]",null],["raw_m_sigma_min_b64","Optional[base64-be-f64-column]",null],["raw_m_sigma_max_b64","Optional[base64-be-f64-column]",null],["raw_g_lambda_min_b64","Optional[base64-be-f64-column]",null],["raw_g_lambda_max_b64","Optional[base64-be-f64-column]",null],["transition_symbol_error_upper_b64","base64-be-f64-column",null],["metric_symbol_error_upper_b64","base64-be-f64-column",null],["transition_fro'
    'benius_upper_b64","base64-be-f64-column",null],["inverse_frobenius_upper_b64","base64-be-f64-column",null],["inverse_residual_frobenius_upper_b64","base64-be-f64-column",null],["m_sigma_min_lower_b64","base64-be-f64-column",null],["m_sigma_max_upper_b64","base64-be-f64-column",null],["metric_frobenius_upper_b64","base64-be-f64-column",null],["cholesky_factorization_residual_frobenius_upper_b64","base64-be-f64-column",null],["cholesky_inverse_frobenius_upper_b64","base64-be-f64-column",null],["cholesky_inverse_residual_frobenius_upper_b64","base64-be-f64-column",null],["ell_lower_b64","base64-be-f64-column",null],["g_lambda_min_lower_b64","base64-be-f64-column",null],["g_lambda_max_upper_b64","base64-be-f64-column",null],["raw_byte_count","int",null],["column_data_sha","sha256",null],["roundoff_enclosure_method_id","Literal[fp64-operation-count-nextafter-columnar-v1]",null],["sidecar_sha","sha256",null]]],"StabilityMetricWitness":["witness_sha",[["witness_schema_version","str",null],["s'
    'tructure_manifest_sha","sha256",null],["metric_kind","Literal[constant-state-v1,finite-support-laurent-v1]",null],["metric_kernel","FrozenComplexTensor","FrozenComplexTensor"],["metric_support_offsets","tuple[tuple[int,...],...]",null],["metric_support_sha","sha256",null],["normalization_id","Literal[trace-at-zero-equals-state-dim-v1]",null],["positive_eigenvalue_floor","float64",null],["condition_number_max","float64",null],["metric_origin","MetricOriginManifest","MetricOriginManifest"],["witness_sha","sha256",null]]],"StructureManifest":["structure_manifest_sha",[["structure_schema_version","str",null],["evidence_lane","Literal[synthetic-classical,classical-adapter,quantum]",null],["structure_kind","Literal[unitary,symplectic]",null],["target_spec_sha","sha256",null],["state_schema_id","str",null],["channel_order","tuple[str,...]",null],["canonical_channel_pairs","tuple[tuple[str,str],...]",null],["fourier_adjoint_convention_id","Literal[same-k-dagger-v1,minus-k-transpose-v1]",null],'
    '["structure_form","FrozenComplexTensor","FrozenComplexTensor"],["reality_convention_id","Optional[Literal[real-kernel-positive-zero-v1]]",null],["prestructure_authority_sha","sha256",null],["structure_manifest_sha","sha256",null]]],"TaggedScalarWire":[null,[["value_kind","Literal[integer,fp64-bits,text,complex128-bits]",null],["integer_value","Optional[int]",null],["fp64_bits_value","Optional[int]",null],["text_value","Optional[str]",null],["complex128_bits_value","Optional[tuple[int,int]]",null]]],"TransitionAuthorityV3":["transition_authority_sha",[["transition_authority_schema_version","str",null],["materialization","ApplicationScenarioMaterializationV3","ApplicationScenarioMaterializationV3"],["factory_binding","FactoryBranchBindingV3","FactoryBranchBindingV3"],["prestructure_authority","ParentV3ApplicationPrestructure","ParentV3ApplicationPrestructure"],["measured_transition","MeasuredTransition","MeasuredTransition"],["transition_authority_sha","sha256",null]]],"WindowCalibration'
    'Outcome":["outcome_sha",[["status","BlockStatus","BlockStatus"],["manifest","WindowThresholdCalibrationManifest","WindowThresholdCalibrationManifest"],["selection","Optional[WindowThresholdSelection]","WindowThresholdSelection"],["outcome_sha","sha256",null]]],"WindowCalibrationProtocol":["protocol_sha",[["protocol_schema_version","str",null],["control_registry_sha","sha256",null],["parent_freeze_sha","sha256",null],["t_candidates","tuple[int,...]",null],["control_entries","tuple[ControlWindowProtocolEntry,...]","ControlWindowProtocolEntry"],["phase_grid_protocol_id","Literal[two-pi-over-16T-v1]",null],["phase_separation_protocol_id","Literal[eight-pi-over-T-v1]",null],["participation_min_required","float64",null],["overlap_margin_required","float64",null],["loop_residual_max","float64",null],["projector_residual_max","float64",null],["protocol_sha","sha256",null]]],"WindowCandidateAudit":["audit_sha",[["fejer_order","int",null],["control_audits","tuple[ControlCandidateAudit,...]","Con'
    'trolCandidateAudit"],["readout_aggregate_audits","tuple[ReadoutAggregateCalibrationAudit,...]","ReadoutAggregateCalibrationAudit"],["passed","bool",null],["audit_sha","sha256",null]]],"WindowThresholdCalibrationManifest":["calibration_manifest_sha",[["calibration_schema_version","str",null],["control_registry","ClosedControlRegistry","ClosedControlRegistry"],["window_protocol","WindowCalibrationProtocol","WindowCalibrationProtocol"],["candidate_audits","tuple[WindowCandidateAudit,...]","WindowCandidateAudit"],["calibration_manifest_sha","sha256",null]]],"WindowThresholdCalibrationV3":["calibration_v3_sha",[["calibration_v3_schema_version","str",null],["parent_freeze_v3_sha","sha256",null],["current_application_registry_sha","sha256",null],["current_application_registry_v3","canonical-json-object",null],["calibration_control_replay_refs","tuple[ParentV3CalibrationControlReplayRefV1,...]","ParentV3CalibrationControlReplayRefV1"],["calibration_outcome","WindowCalibrationOutcome","WindowCa'
    'librationOutcome"],["calibration_v3_sha","sha256",null]]],"WindowThresholdSelection":["selection_sha",[["selected_fejer_order","int",null],["h_scale_ref","float64",null],["h_noise_ref","float64",null],["h_signal_min","float64",null],["h_tau_sig","float64",null],["curv_scale_ref","float64",null],["curv_noise_ref","float64",null],["curv_signal_min","float64",null],["curv_tau_sig","float64",null],["selected_evidence_refs","tuple[SelectedControlEvidenceRef,...]","SelectedControlEvidenceRef"],["selection_sha","sha256",null]]]}'
)
_B7_COMPONENT_CONTRACTS_JSON_V1 = (
    '[["calibration_selection","rulespace_v3.calibration_authority.WindowThresholdSelection","WindowThresholdSelection","selection_sha",[],[],[],"/selected_fejer_order"],["permit","rulespace_v3.application_authority_v3.CalibrationApplicationPermitV3","CalibrationApplicationPermitV3","permit_sha",["calibration_selection"],[{"child_json_pointer":"/calibration/calibration_outcome/selection","parent_component_id":"calibration_selection","comparison":"EXACT_COMPLETE_BODY"}],["/selected_fejer_order equals /calibration/calibration_outcome/selection/selected_fejer_order"],"/selected_fejer_order"],["materialization","rulespace_v3.application_materialization_v3.ApplicationScenarioMaterializationV3","ApplicationScenarioMaterializationV3","materialization_sha",["permit"],[{"child_json_pointer":"/permit","parent_component_id":"permit","comparison":"EXACT_COMPLETE_BODY"}],[],"/permit/selected_fejer_order"],["actual_transition_outcome","rulespace_v3.transition_authority_v3.TransitionAuthorityV3","Transiti'
    'onAuthorityV3","transition_authority_sha",["materialization"],[{"child_json_pointer":"/materialization","parent_component_id":"materialization","comparison":"EXACT_COMPLETE_BODY"}],[],"/materialization/permit/selected_fejer_order"],["matched_ablated_transition_outcome","rulespace_v3.transition_authority_v3.TransitionAuthorityV3","TransitionAuthorityV3","transition_authority_sha",["materialization"],[{"child_json_pointer":"/materialization","parent_component_id":"materialization","comparison":"EXACT_COMPLETE_BODY"}],[],"/materialization/permit/selected_fejer_order"],["actual_metric_authority","rulespace_v3.metric_support_authority_v1.MetricSignedSupportAttestationV1","MetricSignedSupportAttestationV1","attestation_sha",["materialization"],[{"child_json_pointer":"/application_scenario_materialization_v3_sha","parent_component_id":"materialization","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"}],[],"lineage:materialization"],["matched_ablated_metric_authority","rulespace_v3.metric_suppor'
    't_authority_v1.MetricSignedSupportAttestationV1","MetricSignedSupportAttestationV1","attestation_sha",["materialization"],[{"child_json_pointer":"/application_scenario_materialization_v3_sha","parent_component_id":"materialization","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"}],[],"lineage:materialization"],["actual_bridge_grid_authority","rulespace_v3.runtime_grids_v3.BridgeGridAuthorityV3","BridgeGridAuthorityV3","grid_authority_sha",["materialization"],[{"child_json_pointer":"/materialization","parent_component_id":"materialization","comparison":"EXACT_COMPLETE_BODY"}],[],"/materialization/permit/selected_fejer_order"],["matched_ablated_bridge_grid_authority","rulespace_v3.runtime_grids_v3.BridgeGridAuthorityV3","BridgeGridAuthorityV3","grid_authority_sha",["materialization"],[{"child_json_pointer":"/materialization","parent_component_id":"materialization","comparison":"EXACT_COMPLETE_BODY"}],[],"/materialization/permit/selected_fejer_order"],["actual_certificate_outcome","rulespa'
    'ce_v3.certificate_v3.DynamicsCertificationOutcomeV3","DynamicsCertificationOutcomeV3","outcome_sha",["materialization","actual_transition_outcome","actual_metric_authority","actual_bridge_grid_authority"],[{"child_json_pointer":"/certificate/materialization","parent_component_id":"materialization","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/transition_authority","parent_component_id":"actual_transition_outcome","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/metric_attestation","parent_component_id":"actual_metric_authority","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/bridge_grid_authority","parent_component_id":"actual_bridge_grid_authority","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/attempt_audit/materialization_sha","parent_component_id":"materialization","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/attempt_audit/transition_authority_sha","parent_component_id":'
    '"actual_transition_outcome","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/attempt_audit/metric_attestation_sha","parent_component_id":"actual_metric_authority","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/attempt_audit/bridge_grid_authority_sha","parent_component_id":"actual_bridge_grid_authority","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/certificate/dynamics_grid_authority/transition_authority","parent_component_id":"actual_transition_outcome","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/dynamics_grid_authority/metric_support_attestation","parent_component_id":"actual_metric_authority","comparison":"EXACT_COMPLETE_BODY"}],["/status/defined is true","/failure is null","/certificate is nonnull"],"/certificate/materialization/permit/selected_fejer_order"],["matched_ablated_certificate_outcome","rulespace_v3.certificate_v3.DynamicsCertificationOutcomeV3","DynamicsCertificationOutc'
    'omeV3","outcome_sha",["materialization","matched_ablated_transition_outcome","matched_ablated_metric_authority","matched_ablated_bridge_grid_authority"],[{"child_json_pointer":"/certificate/materialization","parent_component_id":"materialization","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/transition_authority","parent_component_id":"matched_ablated_transition_outcome","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/metric_attestation","parent_component_id":"matched_ablated_metric_authority","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/bridge_grid_authority","parent_component_id":"matched_ablated_bridge_grid_authority","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/attempt_audit/materialization_sha","parent_component_id":"materialization","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/attempt_audit/transition_authority_sha","parent_component_id":"matched_ablated_transiti'
    'on_outcome","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/attempt_audit/metric_attestation_sha","parent_component_id":"matched_ablated_metric_authority","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/attempt_audit/bridge_grid_authority_sha","parent_component_id":"matched_ablated_bridge_grid_authority","comparison":"SHA_EQUALS_BODY_SELF_HASH_VALUE"},{"child_json_pointer":"/certificate/dynamics_grid_authority/transition_authority","parent_component_id":"matched_ablated_transition_outcome","comparison":"EXACT_COMPLETE_BODY"},{"child_json_pointer":"/certificate/dynamics_grid_authority/metric_support_attestation","parent_component_id":"matched_ablated_metric_authority","comparison":"EXACT_COMPLETE_BODY"}],["/status/defined is true","/failure is null","/certificate is nonnull"],"/certificate/materialization/permit/selected_fejer_order"]]'
)


def canonical_json_bytes_v1(value: object) -> bytes:
    """Encode one JSON value using the frozen B7 canonical byte algorithm."""

    active_containers: set[int] = set()

    def validate_object_keys(candidate: object, path: str) -> None:
        candidate_type = type(candidate)
        if (
            candidate is None
            or candidate_type is str
            or candidate_type is bool
            or candidate_type is int
            or candidate_type is float
        ):
            return
        if candidate_type is dict:
            container_id = id(candidate)
            if container_id in active_containers:
                raise ValueError("JSON value contains a cyclic container")
            set.add(active_containers, container_id)
            try:
                for key, item in dict.items(candidate):
                    if type(key) is not str:
                        raise TypeError("JSON object key must be a str")
                    validate_object_keys(item, path)
            finally:
                set.remove(active_containers, container_id)
            return
        if candidate_type is list or candidate_type is tuple:
            container_id = id(candidate)
            if container_id in active_containers:
                raise ValueError("JSON value contains a cyclic container")
            set.add(active_containers, container_id)
            try:
                for index, item in enumerate(candidate):
                    validate_object_keys(item, path)
            finally:
                set.remove(active_containers, container_id)
            return
        raise TypeError("JSON value must contain only exact built-in JSON values")

    validate_object_keys(value, "$")
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    try:
        return str.encode(text, "utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("canonical JSON text must be valid UTF-8") from exc


def canonical_sha_v1(value: object) -> str:
    """Hash the frozen canonical JSON bytes for one B7 raw value."""

    return hashlib.sha256(canonical_json_bytes_v1(value)).hexdigest()


def strict_json_loads_v1(canonical_json_utf8: bytes) -> object:
    """Decode strict UTF-8 JSON while rejecting BOMs, duplicates and NaN."""

    def reject_duplicate_object_pairs(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def reject_nonfinite_constant(constant_text: str) -> object:
        raise ValueError("JSON number must be finite")

    if type(canonical_json_utf8) is not bytes:
        raise TypeError("canonical_json_utf8 must be exact bytes")
    if bytes.startswith(canonical_json_utf8, b"\xef\xbb\xbf"):
        raise ValueError("JSON UTF-8 BOM is forbidden")
    try:
        text = bytes.decode(canonical_json_utf8, "utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("JSON input must be strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=reject_duplicate_object_pairs,
        parse_constant=reject_nonfinite_constant,
    )
    canonical_json_bytes_v1(value)
    return value


def _split_wire_top_level_v1(value: str, delimiter: str) -> list[str]:
    result: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
        elif character == delimiter and depth == 0:
            result.append(value[start:index])
            start = index + 1
    result.append(value[start:])
    return result


def _literal_wire_value_v1(value: str) -> object:
    if value == "true":
        return True
    if value == "false":
        return False
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def _validate_wire_value_v1(
    value: object,
    wire_type: str,
    nested_record: str | None,
    field: str,
    schemas: dict[str, object],
) -> None:
    if wire_type.startswith("Optional["):
        if value is None:
            return
        _validate_wire_value_v1(
            value,
            wire_type[9:-1],
            nested_record,
            field,
            schemas,
        )
        return
    if wire_type.startswith("tuple["):
        if type(value) is not list:
            raise TypeError(f"{field} must be an exact JSON array")
        body = wire_type[6:-1]
        sections = _split_wire_top_level_v1(body, ";")
        item_expression = sections[0]
        modifiers = sections[1:]
        exact_count: int | None = None
        nonempty = False
        repeated_value: object | None = None
        for modifier in modifiers:
            if modifier == "nonempty":
                nonempty = True
            elif modifier.startswith("exact="):
                exact_text = modifier[6:]
                if exact_text.isdigit():
                    exact_count = int(exact_text)
            elif modifier.startswith("value="):
                repeated_value = _literal_wire_value_v1(modifier[6:])
        if exact_count is not None and len(value) != exact_count:
            raise ValueError(f"{field} length is not frozen")
        if nonempty and not value:
            raise ValueError(f"{field} must be non-empty")
        if repeated_value is not None:
            for item in value:
                if type(item) is not type(repeated_value) or item != repeated_value:
                    raise ValueError(f"{field} fixed tuple value drifted")
        item_types = _split_wire_top_level_v1(item_expression, ",")
        if item_types[-1] == "...":
            item_type = item_types[0]
            for index, item in enumerate(value):
                _validate_wire_value_v1(
                    item,
                    item_type,
                    nested_record,
                    f"{field}[{index}]",
                    schemas,
                )
        elif len(item_types) == 1:
            for index, item in enumerate(value):
                _validate_wire_value_v1(
                    item,
                    item_types[0],
                    nested_record,
                    f"{field}[{index}]",
                    schemas,
                )
        else:
            if len(value) != len(item_types):
                raise ValueError(f"{field} fixed tuple length drifted")
            for index, (item, item_type) in enumerate(zip(value, item_types)):
                _validate_wire_value_v1(
                    item,
                    item_type,
                    nested_record,
                    f"{field}[{index}]",
                    schemas,
                )
        return
    if nested_record is not None and (
        wire_type == nested_record or wire_type.startswith(f"{nested_record}[")
    ):
        nested = _validate_record_raw_v1(value, nested_record, field, schemas)
        if wire_type.startswith("FrozenComplexTensor["):
            dimensions = wire_type.removeprefix("FrozenComplexTensor[")[:-1]
            expected_shape = [int(item) for item in dimensions.split("x")]
            if nested["shape"] != expected_shape:
                raise ValueError(f"{field} frozen tensor shape drifted")
        return
    if wire_type.startswith("Literal["):
        allowed = tuple(
            _literal_wire_value_v1(item)
            for item in _split_wire_top_level_v1(wire_type[8:-1], ",")
        )
        if not any(type(value) is type(item) and value == item for item in allowed):
            raise ValueError(f"{field} literal is not frozen")
        return
    if wire_type == "sha256":
        _require_sha256_v1(value, field)
        return
    if wire_type == "hex64":
        if (
            type(value) is not str
            or len(value) != 16
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise TypeError(f"{field} must be exact lowercase 64-bit hex")
        return
    if wire_type == "git-sha1":
        if (
            type(value) is not str
            or len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise TypeError(f"{field} must be a lowercase Git SHA-1")
        return
    if wire_type in ("str", "base64-be-f64-column"):
        if type(value) is not str or not value:
            raise TypeError(f"{field} must be a non-empty exact str")
        return
    if wire_type == "UndefinedReason":
        allowed_reasons = (
            "trace_unclassified",
            "ablation_not_reversible",
            "state_schema_mismatch",
            "response_null",
            "response_grey",
            "rank_gap",
            "shell_tracking_ambiguous",
            "unstable",
            "manifest_mismatch",
            "prestructure_invalid",
            "reality_violation",
            "laurent_resource_exceeded",
            "structure_unresolved",
            "dynamics_bridge_failed",
            "stability_unresolved",
            "window_unresolved",
            "endpoint_shell_ambiguous",
            "paired_response_failed",
            "response_bridge_failed",
        )
        if type(value) is not str or value not in allowed_reasons:
            raise ValueError(f"{field} undefined reason is not frozen")
        return
    if wire_type in (
        "DynamicsCertificationFailure",
        "EndpointReferenceFailure",
        "EndpointShellFailure",
        "PairedResponseFailure",
        "ControlCandidateFailure",
    ):
        if wire_type == "DynamicsCertificationFailure":
            allowed_failures = (
                "prestructure_invalid",
                "transition_invalid",
                "reality_invalid",
                "laurent_resource_exceeded",
                "structure_raw_unresolved",
                "metric_raw_unresolved",
                "spectral_coverage_unresolved",
                "normalized_metric_unresolved",
                "full_state_bridge_failed",
                "power_drift_unresolved",
                "certified_instability_counterwitness",
            )
        elif wire_type == "EndpointReferenceFailure":
            allowed_failures = (
                "phase_band_empty",
                "phase_band_nonunique",
                "rank_mismatch",
                "participation_failed",
                "runner_up_margin_failed",
                "projector_invalid",
            )
        elif wire_type == "EndpointShellFailure":
            allowed_failures = (
                "phase_band_empty",
                "phase_separation_failed",
                "gap_failed",
                "participation_failed",
                "reference_ambiguous",
                "runner_up_margin",
                "loop_inconsistent",
                "projector_invalid",
            )
        elif wire_type == "PairedResponseFailure":
            allowed_failures = (
                "qualification_invalid",
                "input_binding_invalid",
                "actual_response_failed",
                "ablated_response_failed",
                "actual_bridge_failed",
                "ablated_bridge_failed",
            )
        else:
            allowed_failures = (
                "reference_failed",
                "shell_failed",
                "response_failed",
                "bridge_failed",
            )
        if type(value) is not str or value not in allowed_failures:
            raise ValueError(f"{field} named failure is not frozen")
        return
    if wire_type == "MechanismKind":
        if value not in ("target_blind", "target_conditioned", "unclassified") or (
            type(value) is not str
        ):
            raise ValueError(f"{field} mechanism kind is not frozen")
        return
    if wire_type == "ProvenanceOperation":
        if (
            value
            not in (
                "grammar_primitive",
                "grammar_constant",
                "target_spec_read",
                "target_equation_read",
                "target_projector_read",
                "target_aware_objective",
                "derive",
                "cache",
                "copy",
                "rename",
                "search",
                "selection",
                "manual_selection",
                "opaque_literal",
                "unclassified",
            )
            or type(value) is not str
        ):
            raise ValueError(f"{field} provenance operation is not frozen")
        return
    if wire_type == "bool":
        if type(value) is not bool:
            raise TypeError(f"{field} must be an exact bool")
        return
    if wire_type in ("int", "nonnegative-int", "positive-int", "uint64"):
        if type(value) is not int:
            raise TypeError(f"{field} must be an exact int")
        if wire_type == "nonnegative-int" and value < 0:
            raise ValueError(f"{field} must be nonnegative")
        if wire_type == "positive-int" and value <= 0:
            raise ValueError(f"{field} must be positive")
        return
    if wire_type in ("float", "float64"):
        if type(value) is not float or value != value or value - value != 0.0:
            raise TypeError(f"{field} must be one finite exact float")
        return
    if wire_type == "canonical-json-object":
        if type(value) is not dict:
            raise TypeError(f"{field} must be an exact JSON object")
        canonical_json_bytes_v1(value)
        return
    if wire_type == "canonical-json-array":
        if type(value) is not list:
            raise TypeError(f"{field} must be an exact JSON array")
        canonical_json_bytes_v1(value)
        return
    if nested_record is not None:
        _validate_record_raw_v1(value, nested_record, field, schemas)
        return
    if type(value) not in (str, int, float, bool, list, dict) and value is not None:
        raise TypeError(f"{field} is not a plain JSON value")
    canonical_json_bytes_v1(value)


def _validate_record_raw_v1(
    raw_body: object,
    record_name: str,
    field: str,
    schemas: dict[str, object],
) -> dict[str, object]:
    schema = schemas.get(record_name)
    if type(schema) is not list or len(schema) != 2:
        raise ValueError(f"{field} has no frozen pure-core schema")
    hash_field, field_specs = schema
    if type(field_specs) is not list:
        raise ValueError(f"{field} frozen schema is malformed")
    fields = tuple(item[0] for item in field_specs)
    record = _require_exact_dict_fields_v1(raw_body, fields, field)
    for name, wire_type, nested_record in field_specs:
        _validate_wire_value_v1(
            record[name],
            wire_type,
            nested_record,
            f"{field}.{name}",
            schemas,
        )
    if record_name == "BlockStatus":
        defined = record["defined"]
        reason = record["reason"]
        if (defined and reason is not None) or (not defined and reason is None):
            raise ValueError(f"{field} defined/reason presence mismatch")
    elif record_name == "FrozenComplexTensor":
        if record["tensor_schema_version"] != "v3m0.frozen-complex-tensor.v1":
            raise ValueError(f"{field} tensor schema drifted")
        shape = record["shape"]
        values = record["values_wire"]
        if not shape or any(type(item) is not int or item <= 0 for item in shape):
            raise ValueError(f"{field} tensor shape must be positive")
        entries = 1
        for item in shape:
            entries *= item
        if len(values) != entries:
            raise ValueError(f"{field} tensor wire length mismatch")
    elif record_name == "BasisManifest":
        channels = record["channel_order"]
        vectors = record["vectors_wire"]
        if not channels or not vectors:
            raise ValueError(f"{field} basis dimensions must be non-empty")
        if any(len(row) != len(channels) for row in vectors):
            raise ValueError(f"{field} basis vectors/channel shape mismatch")
    elif record_name == "CurrentCurvatureNormalizerProtocolV1":
        column_names = (
            "ordered_reciprocal_indices",
            "ordered_momentum_values",
            "ordered_momentum_fp64_bits",
            "ordered_normalizer_values",
            "ordered_normalizer_fp64_bits",
        )
        cardinality = len(record[column_names[0]])
        if cardinality == 0 or any(
            len(record[name]) != cardinality for name in column_names
        ):
            raise ValueError(f"{field} response-grid columns are not aligned")
    if hash_field is not None:
        _require_self_hash_v1(record, hash_field, field)
    return record


def _record_schemas_v1() -> dict[str, object]:
    schemas = json.loads(_B7_RECORD_SCHEMAS_JSON_V1)
    if type(schemas) is not dict:
        raise ValueError("B7 pure-core record schema literal is malformed")
    return schemas


def _canonical_equal_v1(left: object, right: object, field: str) -> None:
    if canonical_json_bytes_v1(left) != canonical_json_bytes_v1(right):
        raise ValueError(f"{field} complete raw bodies differ")


def _component_by_id_v1(
    graph_raw: object,
    component_id: str,
) -> dict[str, object]:
    graph = _require_exact_dict_fields_v1(
        graph_raw,
        (
            "graph_manifest_schema_version",
            "graph_profile_id",
            "authority_state",
            "parent_freeze_v3_body",
            "parent_freeze_v3_sha",
            "synthetic_graph_component_root_sha",
            "selected_fejer_order",
            "calibration_selection_sha",
            "permit_sha",
            "permit_fejer_order",
            "materialization_sha",
            "materialization_fejer_order",
            "actual_transition_outcome_sha",
            "matched_ablated_transition_outcome_sha",
            "actual_metric_authority_sha",
            "matched_ablated_metric_authority_sha",
            "actual_bridge_grid_authority_sha",
            "matched_ablated_bridge_grid_authority_sha",
            "actual_certificate_outcome_sha",
            "matched_ablated_certificate_outcome_sha",
            "ordered_component_bodies",
            "ordered_t_bearer_bindings",
            "graph_sha",
        ),
        "synthetic_graph_manifest",
    )
    components = graph["ordered_component_bodies"]
    if type(components) is not list:
        raise TypeError("synthetic_graph_manifest components must be an exact list")
    matches = [
        item
        for item in components
        if type(item) is dict and item.get("component_id") == component_id
    ]
    if len(matches) != 1:
        raise ValueError(f"synthetic graph component {component_id} is not unique")
    return matches[0]


def validate_endpoint_reference_outcome_raw_v1(
    raw_body: object,
) -> dict[str, object]:
    """Validate one complete authority-free endpoint-reference raw outcome."""

    schemas = _record_schemas_v1()
    outcome = _validate_record_raw_v1(
        raw_body,
        "EndpointReferenceOutcome",
        "endpoint_reference_outcome",
        schemas,
    )
    failure = outcome["failure"]
    if failure not in (
        None,
        "phase_band_empty",
        "phase_band_nonunique",
        "rank_mismatch",
        "participation_failed",
        "runner_up_margin_failed",
        "projector_invalid",
    ) or (failure is not None and type(failure) is not str):
        raise ValueError("endpoint reference failure is not frozen")
    status = outcome["status"]
    reference = outcome["reference"]
    success = failure is None
    if status["defined"] is not success or (reference is not None) is not success:
        raise ValueError("endpoint reference status/failure/payload presence mismatch")
    spec = outcome["reference_spec"]
    attempt = outcome["attempt_audit"]
    _canonical_equal_v1(
        spec,
        attempt["reference_spec"],
        "endpoint reference attempt/reference spec",
    )
    if (
        attempt["expected_shell_rank"] != spec["expected_shell_rank"]
        or attempt["expected_shell_rank_source_id"]
        != spec["expected_shell_rank_source_id"]
    ):
        raise ValueError("endpoint reference expected-rank binding drifted")
    candidate_count = len(attempt["candidate_phases"])
    for name in (
        "candidate_ranks",
        "candidate_participations",
        "runner_up_overlaps",
        "hermitian_residuals",
        "idempotent_residuals",
        "g_invariance_residuals",
        "eigenphase_residuals",
        "observed_competitor_gaps",
    ):
        if len(attempt[name]) != candidate_count:
            raise ValueError("endpoint reference attempt columns are not aligned")
    if reference is not None:
        if (
            reference["control_registry_entry_sha"]
            != spec["control_registry_entry"]["entry_sha"]
            or reference["actual_transition_sha"] != spec["actual_transition_sha"]
            or reference["actual_dynamics_certificate_sha"]
            != spec["actual_dynamics_certificate_sha"]
            or reference["reference_reciprocal_index"]
            != spec["reference_reciprocal_index"]
            or reference["rank"] != spec["expected_shell_rank"]
        ):
            raise ValueError("endpoint reference projector/spec binding drifted")
        projector_shape = reference["projector"]["shape"]
        if (
            len(projector_shape) != 2
            or projector_shape[0] != projector_shape[1]
            or reference["rank"] > projector_shape[0]
        ):
            raise ValueError("endpoint reference projector rank/shape drifted")
    return outcome


def validate_endpoint_shell_outcome_raw_v1(
    raw_body: object,
) -> dict[str, object]:
    """Validate one complete authority-free endpoint-shell raw outcome."""

    schemas = _record_schemas_v1()
    outcome = _validate_record_raw_v1(
        raw_body,
        "EndpointShellOutcome",
        "endpoint_shell_outcome",
        schemas,
    )
    validate_endpoint_reference_outcome_raw_v1(outcome["reference_outcome"])
    failure = outcome["failure"]
    if failure not in (
        None,
        "phase_band_empty",
        "phase_separation_failed",
        "gap_failed",
        "participation_failed",
        "reference_ambiguous",
        "runner_up_margin",
        "loop_inconsistent",
        "projector_invalid",
    ) or (failure is not None and type(failure) is not str):
        raise ValueError("endpoint shell failure is not frozen")
    status = outcome["status"]
    shell = outcome["shell"]
    success = failure is None
    if status["defined"] is not success or (shell is not None) is not success:
        raise ValueError("endpoint shell status/failure/payload presence mismatch")
    attempt = outcome["attempt_audit"]
    shell_spec = attempt["shell_spec"]
    reference = outcome["reference_outcome"]["reference"]
    if reference is not None:
        _canonical_equal_v1(
            shell_spec["endpoint_reference_projector"],
            reference,
            "endpoint shell/reference projector",
        )
    if shell is not None:
        _canonical_equal_v1(
            shell["shell_spec"],
            shell_spec,
            "endpoint shell attempt/manifest spec",
        )
        if len(shell["shell_phases"]) != len(shell["point_audits"]):
            raise ValueError("endpoint shell phase/audit columns are not aligned")
        projector_shape = shell["shell_projectors"]["shape"]
        if (
            len(projector_shape) != 3
            or projector_shape[0] != len(shell["point_audits"])
            or projector_shape[1] != projector_shape[2]
        ):
            raise ValueError("endpoint shell projector stack shape drifted")
    return outcome


def _validate_parent_review_receipt_structure_v1(
    receipt: dict[str, object],
) -> None:
    reviewer_id = receipt["reviewer_id"]
    if reviewer_id == "" or reviewer_id != reviewer_id.strip():
        raise ValueError("Parent-v3 reviewer identity is not canonical")
    fingerprint = receipt["reviewer_key_id"]
    base64_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    if (
        type(fingerprint) is not str
        or len(fingerprint) != 50
        or fingerprint[:7] != "SHA256:"
        or any(character not in base64_alphabet for character in fingerprint[7:])
        or fingerprint[-1] not in "AEIMQUYcgkosw048"
    ):
        raise ValueError("Parent-v3 reviewer fingerprint is not canonical")
    armor = receipt["signature_armor"]
    if type(armor) is not str or "\r" in armor or armor[-1:] != "\n":
        raise ValueError("Parent-v3 signature armor framing drifted")
    lines = armor.split("\n")
    if (
        len(lines) < 4
        or lines[0] != "-----BEGIN SSH SIGNATURE-----"
        or lines[-2] != "-----END SSH SIGNATURE-----"
        or lines[-1] != ""
    ):
        raise ValueError("Parent-v3 signature armor headers drifted")
    encoded_lines = lines[1:-2]
    if (
        not encoded_lines
        or any(not line or len(line) > 70 for line in encoded_lines)
        or any(len(line) != 70 for line in encoded_lines[:-1])
    ):
        raise ValueError("Parent-v3 signature armor wrapping drifted")
    encoded = ""
    for line in encoded_lines:
        encoded += line
    if len(encoded) % 4 != 0 or encoded[:8] != "U1NIU0lH" or len(encoded) < 96:
        raise ValueError("Parent-v3 signature armor payload drifted")
    padding = 2 if encoded[-2:] == "==" else 1 if encoded[-1:] == "=" else 0
    data = encoded if padding == 0 else encoded[:-padding]
    if (
        not data
        or "=" in data
        or any(character not in base64_alphabet for character in data)
        or (padding == 2 and data[-1] not in "AQgw")
        or (padding == 1 and data[-1] not in "AEIMQUYcgkosw048")
    ):
        raise ValueError("Parent-v3 signature armor base64 is not canonical")


def validate_synthetic_parent_freeze_v3_body_v1(
    raw_body: object,
) -> dict[str, object]:
    """Validate one complete non-authority synthetic Parent-v3 raw body."""

    parent = _validate_record_raw_v1(
        raw_body,
        "ParentFreezeV3Manifest",
        "parent_freeze_v3_body",
        _record_schemas_v1(),
    )
    candidate = parent["reviewed_candidate_v3"]
    audit = parent["signing_audit"]
    if parent["preparation_commit_sha"] == parent["signing_commit_sha"]:
        raise ValueError("Parent-v3 preparation and signing commits must differ")
    if (
        candidate["preparation_commit_sha"] != parent["preparation_commit_sha"]
        or audit["preparation_commit_sha"] != parent["preparation_commit_sha"]
        or audit["signing_commit_sha"] != parent["signing_commit_sha"]
        or audit["reviewed_candidate_sha"] != candidate["candidate_sha"]
        or audit["source_closure_sha"] != candidate["source_closure_sha"]
    ):
        raise ValueError("Parent-v3 candidate/signing lineage drifted")
    if (
        parent["parent_freeze_schema_version"] != "v3m0.parent-freeze.v3"
        or candidate["candidate_schema_version"] != "v3m0.parent-freeze-candidate.v3"
        or audit["audit_schema_version"] != "v3m0.parent-signing-audit.v1"
        or audit["diff_allowlist_id"] != "parent-v3-signing-diff-v1"
    ):
        raise ValueError("Parent-v3 schema or signing protocol drifted")
    source_specs = (
        (
            "docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md",
            "SIGNED_INCREMENTAL_ERRATUM",
            "C05_C18_SCENARIO_RESPONSE_GEOMETRY",
        ),
        (
            "docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md",
            "SIGNED_CONSTRUCTION_ERRATUM",
            "C19_REAL20_REFREEZE_V2",
        ),
        (
            "docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md",
            "SIGNED_ISSUANCE_PROTOCOL",
            "PARENT_V3_P_EPOCH_SIGNING",
        ),
        (
            "docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md",
            "SIGNED_RUNTIME_AUTHORITY_PROTOCOL",
            "C19_METRIC_SUPPORT_AUTHORITY_V1",
        ),
    )
    references = parent["signed_source_refs"]
    if type(references) is not list or len(references) != len(source_specs):
        raise ValueError("Parent-v3 signed-source closure is incomplete")
    for reference, (path, role, scope) in zip(references, source_specs):
        if (
            reference["source_ref_schema_version"] != "v3m0.signed-source-ref.v2"
            or reference["relative_path"] != path
            or reference["source_role"] != role
            or reference["source_scope"] != scope
            or reference["preparation_commit_sha"] != parent["preparation_commit_sha"]
            or reference["signing_commit_sha"] != parent["signing_commit_sha"]
        ):
            raise ValueError("Parent-v3 signed-source identity/commit drifted")
    expected_source_root = canonical_sha_v1(
        {
            "signed_source_refs_schema_version": ("v3m0.signed-source-ref-tuple.v1"),
            "entries": references,
        }
    )
    if audit["signed_source_refs_root_sha"] != expected_source_root:
        raise ValueError("Parent-v3 signed-source root drifted")
    review_roles = (
        "MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW",
        "AUTHORITY_AND_BOUNDARY_REVIEW",
    )
    receipts = parent["review_receipts"]
    if type(receipts) is not list or len(receipts) != len(review_roles):
        raise ValueError("Parent-v3 review receipt closure is incomplete")
    reviewed_path_root: str | None = None
    for receipt, review_role in zip(receipts, review_roles):
        _validate_parent_review_receipt_structure_v1(receipt)
        if (
            receipt["receipt_schema_version"] != "v3m0.parent-review-receipt.v1"
            or receipt["review_role"] != review_role
            or receipt["signature_algorithm"] != "openssh-ed25519-v1"
            or receipt["preparation_commit_sha"] != parent["preparation_commit_sha"]
            or receipt["reviewed_candidate_sha"] != candidate["candidate_sha"]
            or receipt["verdict"] != "PASS"
        ):
            raise ValueError("Parent-v3 review receipt identity drifted")
        closure_entries = receipt["reviewed_path_closure"]
        closure_payload = {
            "reviewed_path_closure_schema_version": (
                "v3m0.parent-reviewed-path-closure.v1"
            ),
            "entries": [
                {"relative_path": item[0], "raw_sha256": item[1]}
                for item in closure_entries
            ],
        }
        observed_path_root = canonical_sha_v1(closure_payload)
        if receipt["reviewed_path_closure_sha"] != observed_path_root:
            raise ValueError("Parent-v3 reviewed-path root drifted")
        if reviewed_path_root is None:
            reviewed_path_root = observed_path_root
        elif reviewed_path_root != observed_path_root:
            raise ValueError("Parent-v3 reviewers did not sign one path closure")
        statement = {
            name: receipt[name]
            for name in (
                "receipt_schema_version",
                "review_role",
                "reviewer_id",
                "reviewer_key_id",
                "signature_algorithm",
                "preparation_commit_sha",
                "reviewed_candidate_sha",
                "reviewed_path_closure",
                "reviewed_path_closure_sha",
                "verdict",
            )
        }
        if receipt["signed_statement_sha"] != canonical_sha_v1(statement):
            raise ValueError("Parent-v3 review signed-statement root drifted")
    if (
        len(set(item["reviewer_id"] for item in receipts)) != len(receipts)
        or len(set(item["reviewer_key_id"] for item in receipts)) != len(receipts)
        or len(set(item["receipt_sha"] for item in receipts)) != len(receipts)
    ):
        raise ValueError("Parent-v3 review receipt identities are not distinct")
    receipt_shas = [item["receipt_sha"] for item in parent["review_receipts"]]
    if (
        audit["review_receipt_shas"] != receipt_shas
        or audit["reviewed_path_closure_sha"] != reviewed_path_root
    ):
        raise ValueError("Parent-v3 review receipt root order drifted")
    return parent


def validate_provenance_fixture_v1(raw_body: object) -> dict[str, object]:
    """Validate one complete B7 non-authority provenance fixture raw tree."""

    fixture = _require_exact_dict_fields_v1(
        raw_body,
        (
            "provenance_fixture_schema_version",
            "parent_freeze_v3_body",
            "permit_body",
            "materialization_body",
            "current_scenario_response_contract_v3_body",
            "actual_bridge_grid_authority_body",
            "matched_ablated_bridge_grid_authority_body",
            "provenance_fixture_sha",
        ),
        "provenance_fixture",
    )
    if (
        fixture["provenance_fixture_schema_version"]
        != "experimental.v3m0.b7.provenance-fixture.v1"
    ):
        raise ValueError("provenance fixture schema drifted")
    schemas = _record_schemas_v1()
    parent = validate_synthetic_parent_freeze_v3_body_v1(
        fixture["parent_freeze_v3_body"]
    )
    permit = _validate_record_raw_v1(
        fixture["permit_body"],
        "CalibrationApplicationPermitV3",
        "provenance_fixture.permit_body",
        schemas,
    )
    materialization = _validate_record_raw_v1(
        fixture["materialization_body"],
        "ApplicationScenarioMaterializationV3",
        "provenance_fixture.materialization_body",
        schemas,
    )
    contract = _validate_record_raw_v1(
        fixture["current_scenario_response_contract_v3_body"],
        "CurrentScenarioResponseContractV3",
        "provenance_fixture.current_scenario_response_contract_v3_body",
        schemas,
    )
    actual_bridge = _validate_record_raw_v1(
        fixture["actual_bridge_grid_authority_body"],
        "BridgeGridAuthorityV3",
        "provenance_fixture.actual_bridge_grid_authority_body",
        schemas,
    )
    matched_bridge = _validate_record_raw_v1(
        fixture["matched_ablated_bridge_grid_authority_body"],
        "BridgeGridAuthorityV3",
        "provenance_fixture.matched_ablated_bridge_grid_authority_body",
        schemas,
    )
    if permit["parent_freeze_v3_sha"] != parent["parent_freeze_v3_sha"]:
        raise ValueError("provenance permit/Parent-v3 binding drifted")
    _canonical_equal_v1(
        materialization["permit"],
        permit,
        "provenance materialization/permit",
    )
    for name in (
        "current_application_authority",
        "current_scenario_authority",
        "current_scenario_response_contract",
    ):
        _canonical_equal_v1(
            materialization[name],
            permit[name],
            f"provenance materialization/permit {name}",
        )
    _canonical_equal_v1(
        contract,
        permit["current_scenario_response_contract"],
        "provenance current response contract",
    )
    response_grid = contract["response_grid"]
    calibration_spec = contract["current_readout_calibration_spec"]
    geometry = contract["geometry_bundle"]
    normalizer = calibration_spec["curvature_normalizer_protocol"]
    if (
        normalizer["response_grid_sha"] != response_grid["response_grid_sha"]
        or normalizer["ordered_reciprocal_indices"]
        != response_grid["reciprocal_indices"]
        or len(normalizer["ordered_reciprocal_indices"])
        != len(response_grid["reciprocal_indices"])
        or normalizer["spatial_shape"] != response_grid["torus_denominators"]
        or calibration_spec["geometry_bundle_sha"] != geometry["geometry_bundle_sha"]
    ):
        raise ValueError("provenance current response calibration lineage drifted")
    for calibration_field, geometry_field in (
        ("source_metric_whitener", "source_whitener"),
        ("h_metric_whitener", "h_whitener"),
        ("curvature_incidence_operator", "incidence_q"),
        ("curvature_metric_whitener", "curvature_whitener"),
    ):
        _canonical_equal_v1(
            calibration_spec[calibration_field],
            geometry[geometry_field],
            f"provenance current calibration {calibration_field}",
        )
    _canonical_equal_v1(
        actual_bridge["materialization"],
        materialization,
        "provenance actual bridge/materialization",
    )
    _canonical_equal_v1(
        matched_bridge["materialization"],
        materialization,
        "provenance matched bridge/materialization",
    )
    if actual_bridge["grid_authority_sha"] == matched_bridge["grid_authority_sha"]:
        raise ValueError("provenance branch bridge identities must be distinct")
    if (
        actual_bridge["factory_binding"]["branch"] != "actual"
        or matched_bridge["factory_binding"]["branch"] != "matched_ablated"
    ):
        raise ValueError("provenance B5 bridge branch roles drifted")
    _canonical_equal_v1(
        actual_bridge["bridge_grid"],
        matched_bridge["bridge_grid"],
        "provenance branch bridge grids",
    )
    _require_self_hash_v1(fixture, "provenance_fixture_sha", "provenance_fixture")
    return fixture


def _resolve_json_pointer_v1(raw_body: object, pointer: str, field: str) -> object:
    if type(pointer) is not str or not pointer.startswith("/"):
        raise ValueError(f"{field} is not a frozen absolute JSON pointer")
    current = raw_body
    for raw_token in pointer.removeprefix("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            if token not in current:
                raise ValueError(f"{field} does not resolve")
            current = current[token]
        elif type(current) is list and token.isdigit():
            index = int(token)
            if index >= len(current):
                raise ValueError(f"{field} array index does not resolve")
            current = current[index]
        else:
            raise ValueError(f"{field} traverses a non-container")
    return current


def validate_synthetic_component_body_v1(
    raw_body: object,
    ordered_components_raw: object,
    parent_raw: object,
) -> dict[str, object]:
    """Validate one B7 synthetic component raw body and its supplied lineage."""

    component = _require_exact_dict_fields_v1(
        raw_body,
        (
            "component_body_schema_version",
            "component_id",
            "body_type",
            "complete_body",
            "body_raw_canonical_sha256",
            "body_self_hash_field",
            "body_self_hash_value",
            "lineage_parent_component_ids",
            "fejer_order",
            "component_sha",
        ),
        "synthetic_component_body",
    )
    if (
        component["component_body_schema_version"]
        != "experimental.v3m0.b7.synthetic-component-body.v1"
    ):
        raise ValueError("synthetic component schema drifted")
    if type(ordered_components_raw) is not list:
        raise TypeError("ordered_components_raw must be an exact list")
    ordered_matches = [
        item
        for item in ordered_components_raw
        if type(item) is dict
        and item.get("component_id") == component["component_id"]
        and canonical_json_bytes_v1(item) == canonical_json_bytes_v1(component)
    ]
    if len(ordered_matches) != 1:
        raise ValueError("synthetic component is absent or duplicated in its order")
    contracts = json.loads(_B7_COMPONENT_CONTRACTS_JSON_V1)
    matches = [item for item in contracts if item[0] == component["component_id"]]
    if len(matches) != 1:
        raise ValueError("synthetic component ID is not frozen")
    (
        component_id,
        body_type,
        record_name,
        self_hash_field,
        lineage_ids,
        lineage_bindings,
        predicates,
        t_derivation,
    ) = matches[0]
    if (
        component["component_id"] != component_id
        or component["body_type"] != body_type
        or component["body_self_hash_field"] != self_hash_field
        or component["lineage_parent_component_ids"] != lineage_ids
    ):
        raise ValueError("synthetic component registry metadata drifted")
    complete_body = _validate_record_raw_v1(
        component["complete_body"],
        record_name,
        f"synthetic_component_body.{component_id}.complete_body",
        _record_schemas_v1(),
    )
    if component["body_raw_canonical_sha256"] != canonical_sha_v1(complete_body):
        raise ValueError("synthetic component complete-body raw SHA drifted")
    if component["body_self_hash_value"] != complete_body[self_hash_field]:
        raise ValueError("synthetic component body self-hash metadata drifted")
    parent = validate_synthetic_parent_freeze_v3_body_v1(parent_raw)
    parents: dict[str, dict[str, object]] = {}
    for lineage_id in lineage_ids:
        lineage_matches = [
            item
            for item in ordered_components_raw
            if type(item) is dict and item.get("component_id") == lineage_id
        ]
        if len(lineage_matches) != 1:
            raise ValueError("synthetic component lineage parent is not unique")
        parents[lineage_id] = validate_synthetic_component_body_v1(
            lineage_matches[0],
            ordered_components_raw,
            parent_raw,
        )
    for binding in lineage_bindings:
        lineage_id = binding["parent_component_id"]
        parent_component = parents[lineage_id]
        observed = _resolve_json_pointer_v1(
            complete_body,
            binding["child_json_pointer"],
            "synthetic component lineage binding",
        )
        if binding["comparison"] == "EXACT_COMPLETE_BODY":
            _canonical_equal_v1(
                observed,
                parent_component["complete_body"],
                "synthetic component exact lineage body",
            )
        elif binding["comparison"] == "SHA_EQUALS_BODY_SELF_HASH_VALUE":
            if observed != parent_component["body_self_hash_value"]:
                raise ValueError("synthetic component lineage SHA drifted")
        else:
            raise ValueError("synthetic component lineage comparison is unknown")
    if t_derivation.startswith("/"):
        derived_t = _resolve_json_pointer_v1(
            complete_body,
            t_derivation,
            "synthetic component T derivation",
        )
    elif t_derivation.startswith("lineage:"):
        lineage_id = t_derivation.split(":", 1)[1]
        if lineage_id not in parents:
            raise ValueError("synthetic component T lineage is absent")
        derived_t = parents[lineage_id]["fejer_order"]
    else:
        raise ValueError("synthetic component T derivation is unknown")
    if derived_t != 256 or component["fejer_order"] != 256:
        raise ValueError("synthetic component Fejer order drifted")
    for predicate in predicates:
        if predicate == (
            "/selected_fejer_order equals "
            "/calibration/calibration_outcome/selection/selected_fejer_order"
        ):
            left = _resolve_json_pointer_v1(
                complete_body,
                "/selected_fejer_order",
                "synthetic component permit T",
            )
            right = _resolve_json_pointer_v1(
                complete_body,
                "/calibration/calibration_outcome/selection/selected_fejer_order",
                "synthetic component selection T",
            )
            if left != right:
                raise ValueError("synthetic component permit/selection T drifted")
        elif predicate == "/status/defined is true":
            if (
                _resolve_json_pointer_v1(
                    complete_body,
                    "/status/defined",
                    "synthetic component certificate status",
                )
                is not True
            ):
                raise ValueError("synthetic component certificate is not defined")
        elif predicate == "/failure is null":
            if (
                _resolve_json_pointer_v1(
                    complete_body,
                    "/failure",
                    "synthetic component certificate failure",
                )
                is not None
            ):
                raise ValueError("synthetic component certificate has a failure")
        elif predicate == "/certificate is nonnull":
            if (
                _resolve_json_pointer_v1(
                    complete_body,
                    "/certificate",
                    "synthetic component certificate payload",
                )
                is None
            ):
                raise ValueError("synthetic component certificate is absent")
        else:
            raise ValueError("synthetic component predicate is unknown")
    if component_id in (
        "permit",
        "actual_metric_authority",
        "matched_ablated_metric_authority",
    ):
        if complete_body["parent_freeze_v3_sha"] != parent["parent_freeze_v3_sha"]:
            raise ValueError("synthetic component Parent-v3 SHA binding drifted")
    elif component_id in (
        "actual_certificate_outcome",
        "matched_ablated_certificate_outcome",
    ):
        _canonical_equal_v1(
            complete_body["certificate"]["parent_freeze_v3"],
            parent,
            "synthetic component certificate/Parent-v3",
        )
    _require_self_hash_v1(component, "component_sha", "synthetic_component_body")
    return component


def _validate_synthetic_graph_raw_v1(
    graph_raw: object,
    parent_raw: object,
) -> dict[str, object]:
    graph = _component_by_id_v1(graph_raw, "calibration_selection")
    del graph
    manifest = graph_raw
    if (
        manifest["graph_manifest_schema_version"]
        != "experimental.v3m0.b7.synthetic-graph-manifest.v1"
        or manifest["graph_profile_id"]
        != "v3m0-b7-d1-nonauthority-synthetic-private-graph-v1"
        or manifest["authority_state"] != "NON_AUTHORITY_SYNTHETIC"
        or manifest["selected_fejer_order"] != 256
        or manifest["permit_fejer_order"] != 256
        or manifest["materialization_fejer_order"] != 256
    ):
        raise ValueError("synthetic graph frozen identity or T drifted")
    parent = validate_synthetic_parent_freeze_v3_body_v1(parent_raw)
    _canonical_equal_v1(
        manifest["parent_freeze_v3_body"],
        parent,
        "synthetic graph Parent-v3 body",
    )
    if manifest["parent_freeze_v3_sha"] != parent["parent_freeze_v3_sha"]:
        raise ValueError("synthetic graph Parent-v3 SHA drifted")
    contracts = json.loads(_B7_COMPONENT_CONTRACTS_JSON_V1)
    component_order = [item[0] for item in contracts]
    components = manifest["ordered_component_bodies"]
    if (
        type(components) is not list
        or [
            item.get("component_id") if type(item) is dict else None
            for item in components
        ]
        != component_order
    ):
        raise ValueError("synthetic graph component order drifted")
    schemas = _record_schemas_v1()
    by_id: dict[str, dict[str, object]] = {}
    for component, contract in zip(components, contracts):
        component_id, body_type, record_name, self_hash_field = contract[:4]
        wrapper = _require_exact_dict_fields_v1(
            component,
            (
                "component_body_schema_version",
                "component_id",
                "body_type",
                "complete_body",
                "body_raw_canonical_sha256",
                "body_self_hash_field",
                "body_self_hash_value",
                "lineage_parent_component_ids",
                "fejer_order",
                "component_sha",
            ),
            f"synthetic_graph.component.{component_id}",
        )
        if (
            wrapper["component_body_schema_version"]
            != "experimental.v3m0.b7.synthetic-component-body.v1"
            or wrapper["component_id"] != component_id
            or wrapper["body_type"] != body_type
            or wrapper["body_self_hash_field"] != self_hash_field
            or wrapper["lineage_parent_component_ids"] != contract[4]
            or wrapper["fejer_order"] != 256
        ):
            raise ValueError("synthetic graph component metadata drifted")
        complete = _validate_record_raw_v1(
            wrapper["complete_body"],
            record_name,
            f"synthetic_graph.component.{component_id}.complete_body",
            schemas,
        )
        if (
            wrapper["body_raw_canonical_sha256"] != canonical_sha_v1(complete)
            or wrapper["body_self_hash_value"] != complete[self_hash_field]
        ):
            raise ValueError("synthetic graph component body digest drifted")
        _require_self_hash_v1(
            wrapper,
            "component_sha",
            f"synthetic_graph.component.{component_id}",
        )
        by_id[component_id] = wrapper
    field_by_component = {
        "calibration_selection": "calibration_selection_sha",
        "permit": "permit_sha",
        "materialization": "materialization_sha",
        "actual_transition_outcome": "actual_transition_outcome_sha",
        "matched_ablated_transition_outcome": (
            "matched_ablated_transition_outcome_sha"
        ),
        "actual_metric_authority": "actual_metric_authority_sha",
        "matched_ablated_metric_authority": ("matched_ablated_metric_authority_sha"),
        "actual_bridge_grid_authority": "actual_bridge_grid_authority_sha",
        "matched_ablated_bridge_grid_authority": (
            "matched_ablated_bridge_grid_authority_sha"
        ),
        "actual_certificate_outcome": "actual_certificate_outcome_sha",
        "matched_ablated_certificate_outcome": (
            "matched_ablated_certificate_outcome_sha"
        ),
    }
    root_entries: list[dict[str, object]] = []
    for component_id in component_order:
        wrapper = by_id[component_id]
        if (
            manifest[field_by_component[component_id]]
            != wrapper["body_self_hash_value"]
        ):
            raise ValueError("synthetic graph component root field drifted")
        root_entries.append(
            {
                "component_id": component_id,
                "body_self_hash_value": wrapper["body_self_hash_value"],
            }
        )
    if manifest["synthetic_graph_component_root_sha"] != canonical_sha_v1(root_entries):
        raise ValueError("synthetic graph component root SHA drifted")
    bindings = manifest["ordered_t_bearer_bindings"]
    if type(bindings) is not list or len(bindings) != len(component_order):
        raise ValueError("synthetic graph T bindings are incomplete")
    for binding, component_id in zip(bindings, component_order):
        checked = _require_exact_dict_fields_v1(
            binding,
            (
                "binding_schema_version",
                "component_id",
                "body_sha",
                "fejer_order",
                "binding_sha",
            ),
            f"synthetic_graph.binding.{component_id}",
        )
        if (
            checked["binding_schema_version"]
            != "experimental.v3m0.b7.t-bearer-binding.v1"
            or checked["component_id"] != component_id
            or checked["body_sha"] != by_id[component_id]["body_self_hash_value"]
            or checked["fejer_order"] != 256
        ):
            raise ValueError("synthetic graph T binding drifted")
        _require_self_hash_v1(
            checked,
            "binding_sha",
            f"synthetic_graph.binding.{component_id}",
        )
    for component in components:
        validate_synthetic_component_body_v1(component, components, parent)
    _require_self_hash_v1(manifest, "graph_sha", "synthetic_graph_manifest")
    return manifest


def validate_response_run_spec_fixture_v1(
    raw_body: object,
    provenance_raw: object,
    graph_raw: object,
) -> dict[str, object]:
    """Validate one B7 ResponseRunSpec-v3 raw fixture and supplied joins."""

    provenance = validate_provenance_fixture_v1(provenance_raw)
    parent = provenance["parent_freeze_v3_body"]
    graph = _validate_synthetic_graph_raw_v1(graph_raw, parent)
    spec = _validate_record_raw_v1(
        raw_body,
        "ResponseRunSpecV3",
        "response_run_spec_fixture",
        _record_schemas_v1(),
    )
    permit = provenance["permit_body"]
    materialization = provenance["materialization_body"]
    contract = provenance["current_scenario_response_contract_v3_body"]
    actual_bridge = provenance["actual_bridge_grid_authority_body"]
    matched_bridge = provenance["matched_ablated_bridge_grid_authority_body"]
    if (
        spec["parent_freeze_v3_sha"] != parent["parent_freeze_v3_sha"]
        or spec["permit_sha"] != permit["permit_sha"]
        or spec["materialization_sha"] != materialization["materialization_sha"]
        or spec["current_scenario_response_contract_v3_sha"]
        != contract["response_contract_sha"]
    ):
        raise ValueError(
            "response run-spec Parent/permit/materialization lineage drifted"
        )
    calibration = permit["calibration"]
    calibration_outcome = calibration["calibration_outcome"]
    selection = calibration_outcome["selection"]
    if selection is None or calibration_outcome["status"]["defined"] is not True:
        raise ValueError("response run-spec calibration selection is absent")
    window_protocol = calibration_outcome["manifest"]["window_protocol"]
    if (
        spec["window_calibration_v3_sha"] != calibration["calibration_v3_sha"]
        or spec["window_protocol_sha"] != window_protocol["protocol_sha"]
        or spec["window_selection_sha"] != selection["selection_sha"]
        or spec["selected_fejer_order"] != permit["selected_fejer_order"]
        or spec["selected_fejer_order"] != selection["selected_fejer_order"]
        or spec["selected_fejer_order"] != graph["selected_fejer_order"]
        or spec["selected_fejer_order"] != 256
    ):
        raise ValueError("response run-spec calibration/T binding drifted")
    if (
        spec["control_case_id"] != contract["control_case_id"]
        or spec["application_instance_id"] != contract["application_instance_id"]
        or spec["scenario_id"] != contract["scenario_id"]
        or spec["scenario_sha"]
        != permit["current_scenario_authority"]["scenario_authority_sha"]
    ):
        raise ValueError("response run-spec scenario identity drifted")
    basis_contract = materialization["basis_contract"]
    if (
        spec["state_schema_id"] != basis_contract["state_schema_id"]
        or spec["channel_order"] != basis_contract["channel_order"]
        or len(spec["channel_order"]) != 20
        or len(set(spec["channel_order"])) != 20
        or spec["spatial_shape"] != [8]
    ):
        raise ValueError("response run-spec state/channel/spatial contract drifted")
    for name in ("source_basis", "readout_basis"):
        expected_name = (
            "scenario_source_basis"
            if name == "source_basis"
            else "scenario_readout_basis"
        )
        _canonical_equal_v1(
            spec[name],
            basis_contract[expected_name],
            f"response run-spec {name}",
        )
        if (
            spec[name]["state_schema_id"] != spec["state_schema_id"]
            or spec[name]["channel_order"] != spec["channel_order"]
            or len(spec[name]["vectors_wire"]) != 10
        ):
            raise ValueError("response run-spec basis dimension drifted")
    if (
        spec["source_basis"]["role"] != "source"
        or spec["readout_basis"]["role"] != "readout"
    ):
        raise ValueError("response run-spec basis roles drifted")
    tensor_shapes = (
        ("source_injection_isometry", [20, 10], "source_injection"),
        ("readout_coisometry", [10, 20], "readout_coisometry"),
        ("source_trial_vectors", [10, 10], "source_trial_vectors"),
    )
    for name, shape, basis_name in tensor_shapes:
        if spec[name]["shape"] != shape:
            raise ValueError("response run-spec tensor shape drifted")
        _canonical_equal_v1(
            spec[name],
            basis_contract[basis_name],
            f"response run-spec {name}",
        )
    _canonical_equal_v1(
        spec["response_grid"],
        contract["response_grid"],
        "response run-spec response grid",
    )
    _canonical_equal_v1(
        spec["source_readout_bridge_grid"],
        actual_bridge["bridge_grid"],
        "response run-spec actual bridge grid",
    )
    _canonical_equal_v1(
        spec["source_readout_bridge_grid"],
        matched_bridge["bridge_grid"],
        "response run-spec matched bridge grid",
    )
    if not spec["source_readout_bridge_steps"] or any(
        type(item) is not int or item <= 0
        for item in spec["source_readout_bridge_steps"]
    ):
        raise ValueError("response run-spec bridge steps drifted")
    if (
        spec["reference_reciprocal_index"]
        != contract["response_reference_reciprocal_index"]
        or spec["preregistered_phase_bands"] != contract["preregistered_phase_bands"]
        or spec["reference_phase_band_source_id"]
        != contract["reference_phase_band_source_id"]
        or spec["expected_shell_rank"] != contract["expected_actual_shell_rank"]
        or spec["expected_shell_rank"] != contract["expected_matched_shell_rank"]
        or spec["expected_shell_rank"] != 10
        or spec["source_trial_generation_id"] != contract["source_trial_generation_id"]
    ):
        raise ValueError("response run-spec endpoint/rank/trial contract drifted")
    if (
        canonical_json_bytes_v1(spec["bridge_tolerance"])
        != canonical_json_bytes_v1(contract["bridge_tolerance"])
        or spec["bridge_tolerance_source_id"] != contract["bridge_tolerance_source_id"]
    ):
        raise ValueError("response run-spec bridge tolerance drifted")
    _canonical_equal_v1(
        spec["current_readout_calibration_spec"],
        contract["current_readout_calibration_spec"],
        "response run-spec readout calibration",
    )
    for component_id in (
        "actual_certificate_outcome",
        "matched_ablated_certificate_outcome",
    ):
        certificate_outcome = _component_by_id_v1(graph, component_id)["complete_body"]
        certificate = certificate_outcome["certificate"]
        if (
            certificate_outcome["status"]["defined"] is not True
            or certificate_outcome["failure"] is not None
            or type(certificate) is not dict
        ):
            raise ValueError(
                "response run-spec B6 certificate outcome is not successful"
            )
        bridge_spec = certificate["full_state_bridge_spec"]
        if canonical_json_bytes_v1(
            bridge_spec["bridge_tolerance"]
        ) != canonical_json_bytes_v1(spec["bridge_tolerance"]):
            raise ValueError("response run-spec B6 bridge tolerance drifted")
        _canonical_equal_v1(
            bridge_spec["bridge_grid"],
            spec["source_readout_bridge_grid"],
            "response run-spec B6 bridge grid",
        )
        if bridge_spec["macro_steps"] != spec["source_readout_bridge_steps"]:
            raise ValueError("response run-spec B6 bridge steps drifted")
    if (
        spec["actual_bridge_grid_authority_sha"] != actual_bridge["grid_authority_sha"]
        or spec["actual_bridge_grid_authority_sha"]
        != graph["actual_bridge_grid_authority_sha"]
        or spec["matched_ablated_bridge_grid_authority_sha"]
        != matched_bridge["grid_authority_sha"]
        or spec["matched_ablated_bridge_grid_authority_sha"]
        != graph["matched_ablated_bridge_grid_authority_sha"]
    ):
        raise ValueError("response run-spec B5 authority lineage drifted")
    return spec


def validate_source_readout_response_raw_v1(
    raw_body: object,
    run_spec_raw: object,
    provenance_raw: object,
    graph_raw: object,
) -> dict[str, object]:
    """Validate one source/readout raw response against supplied frozen joins."""

    run_spec = validate_response_run_spec_fixture_v1(
        run_spec_raw,
        provenance_raw,
        graph_raw,
    )
    response = _validate_record_raw_v1(
        raw_body,
        "SourceReadoutResponse",
        "source_readout_response",
        _record_schemas_v1(),
    )
    # ``shell_manifest_sha`` is syntax-checked above, but this four-raw validator
    # has no shell body to join.  The v9.1 M06 contract assigns that comparison
    # to Task-7 aggregate/case ROUTE_VERIFICATION; do not claim it here.
    branch = response["branch"]
    if branch not in ("actual", "matched_ablated") or type(branch) is not str:
        raise ValueError("source/readout response branch drifted")
    prefix = "actual" if branch == "actual" else "matched_ablated"
    transition_component = _component_by_id_v1(
        graph_raw,
        f"{prefix}_transition_outcome",
    )
    certificate_component = _component_by_id_v1(
        graph_raw,
        f"{prefix}_certificate_outcome",
    )
    transition = transition_component["complete_body"]
    certificate_outcome = certificate_component["complete_body"]
    certificate = certificate_outcome["certificate"]
    if (
        certificate_outcome["status"]["defined"] is not True
        or certificate_outcome["failure"] is not None
        or type(certificate) is not dict
    ):
        raise ValueError(
            "source/readout response certificate lineage is not successful"
        )
    expected_factory_sha = transition["factory_binding"]["factory"]["factory_sha"]
    expected_transition_sha = transition["measured_transition"]["transition_sha"]
    expected_certificate_sha = certificate["certificate_sha"]
    if (
        response["factory_sha"] != expected_factory_sha
        or response["transition_sha"] != expected_transition_sha
        or response["dynamics_certificate_sha"] != expected_certificate_sha
    ):
        raise ValueError(
            "source/readout response factory/transition/certificate drifted"
        )
    _canonical_equal_v1(
        response["source_basis"],
        run_spec["source_basis"],
        "source/readout response source basis",
    )
    _canonical_equal_v1(
        response["readout_basis"],
        run_spec["readout_basis"],
        "source/readout response readout basis",
    )
    if response["run_spec_sha"] != run_spec["run_spec_sha"]:
        raise ValueError("source/readout response run-spec SHA drifted")
    bridge = response["bridge_audit"]
    if (
        bridge["branch"] != branch
        or bridge["factory_sha"] != response["factory_sha"]
        or bridge["transition_sha"] != response["transition_sha"]
        or bridge["dynamics_certificate_sha"] != response["dynamics_certificate_sha"]
        or bridge["run_spec_sha"] != response["run_spec_sha"]
    ):
        raise ValueError("source/readout response bridge lineage drifted")
    calibration = run_spec["current_readout_calibration_spec"]
    if (
        bridge["source_metric_whitener_sha"]
        != calibration["source_metric_whitener"]["tensor_sha"]
        or bridge["readout_calibration_spec_sha"] != calibration["spec_sha"]
    ):
        raise ValueError("source/readout response bridge calibration drifted")
    source_count = len(run_spec["source_basis"]["vectors_wire"])
    readout_count = len(run_spec["readout_basis"]["vectors_wire"])
    expected_matrix_keys = [
        (reciprocal_index, macro_steps)
        for reciprocal_index in run_spec["source_readout_bridge_grid"][
            "reciprocal_indices"
        ]
        for macro_steps in run_spec["source_readout_bridge_steps"]
    ]
    matrix_audits = bridge["matrix_audits"]
    if len(matrix_audits) != len(expected_matrix_keys):
        raise ValueError("source/readout bridge matrix coverage drifted")
    for audit, expected_key in zip(matrix_audits, expected_matrix_keys):
        if (audit["reciprocal_index"], audit["macro_steps"]) != expected_key:
            raise ValueError("source/readout bridge matrix order drifted")
        if audit["raw_difference_matrix"]["shape"] != [
            readout_count,
            source_count,
        ]:
            raise ValueError("source/readout bridge matrix shape drifted")
    expected_values_shape = [
        len(run_spec["response_grid"]["reciprocal_indices"]),
        readout_count,
        source_count,
    ]
    if response["values"]["shape"] != expected_values_shape:
        raise ValueError("source/readout response values shape drifted")
    return response


def _require_exact_dict_fields_v1(
    raw_body: object,
    fields: tuple[str, ...],
    field: str,
) -> dict[str, object]:
    if type(raw_body) is not dict:
        raise TypeError(f"{field} must be an exact dict")
    if len(raw_body) != len(fields) or any(name not in raw_body for name in fields):
        raise ValueError(f"{field} fields drifted")
    return {name: raw_body[name] for name in fields}


def _require_sha256_v1(value: object, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TypeError(f"{field} must be a lowercase SHA-256")
    return value


def _require_self_hash_v1(
    raw_body: dict[str, object],
    hash_field: str,
    field: str,
) -> None:
    observed = _require_sha256_v1(raw_body[hash_field], f"{field}.{hash_field}")
    payload = {key: value for key, value in raw_body.items() if key != hash_field}
    if observed != canonical_sha_v1(payload):
        raise ValueError(f"{field}.{hash_field} mismatch")


def _validate_frozen_complex_tensor_raw_v1(
    raw_body: object,
    field: str,
) -> dict[str, object]:
    tensor = _require_exact_dict_fields_v1(
        raw_body,
        ("tensor_schema_version", "shape", "values_wire", "tensor_sha"),
        field,
    )
    if tensor["tensor_schema_version"] != "v3m0.frozen-complex-tensor.v1":
        raise ValueError(f"{field} schema drifted")
    shape = tensor["shape"]
    if (
        type(shape) is not list
        or not shape
        or any(type(item) is not int or item <= 0 for item in shape)
    ):
        raise TypeError(f"{field}.shape must contain positive exact ints")
    entry_count = 1
    for item in shape:
        entry_count *= item
    values = tensor["values_wire"]
    if type(values) is not list or len(values) != entry_count:
        raise ValueError(f"{field}.values_wire shape mismatch")
    for index, wire in enumerate(values):
        if (
            type(wire) is not list
            or len(wire) != 2
            or any(type(component) is not float for component in wire)
        ):
            raise TypeError(f"{field}.values_wire[{index}] is not a float pair")
    _require_self_hash_v1(tensor, "tensor_sha", field)
    return tensor


def validate_branch_attempt_v1(raw_body: object) -> dict[str, object]:
    """Validate one authority-free B7 branch-attempt raw tree."""

    attempt = _require_exact_dict_fields_v1(
        raw_body,
        (
            "branch_attempt_schema_version",
            "branch",
            "response_values",
            "bridge_audit",
            "failure",
            "attempt_sha",
        ),
        "branch_attempt",
    )
    if (
        attempt["branch_attempt_schema_version"]
        != "experimental.v3m0.b7.branch-attempt.v1"
    ):
        raise ValueError("branch_attempt schema drifted")
    branch = attempt["branch"]
    if branch not in ("actual", "matched_ablated") or type(branch) is not str:
        raise ValueError("branch_attempt branch is not frozen")
    values = attempt["response_values"]
    if values is not None:
        _validate_frozen_complex_tensor_raw_v1(values, "branch_attempt.response_values")
    bridge_audit = attempt["bridge_audit"]
    if bridge_audit is not None:
        checked_bridge = _validate_record_raw_v1(
            bridge_audit,
            "SourceReadoutBridgeAudit",
            "branch_attempt.bridge_audit",
            _record_schemas_v1(),
        )
        if checked_bridge["branch"] != branch:
            raise ValueError("branch attempt/bridge branch binding drifted")
    failure = attempt["failure"]
    allowed_failures = (
        (None, "actual_response_failed", "actual_bridge_failed")
        if branch == "actual"
        else (
            None,
            "matched_ablated_response_failed",
            "matched_ablated_bridge_failed",
        )
    )
    if failure not in allowed_failures or (
        failure is not None and type(failure) is not str
    ):
        raise ValueError("branch_attempt failure is not valid for its branch")
    if failure is not None and failure.endswith("_response_failed"):
        if values is not None or bridge_audit is not None:
            raise ValueError("response failure must precede values and bridge audit")
    elif failure is not None and failure.endswith("_bridge_failed"):
        if values is None or bridge_audit is not None:
            raise ValueError("bridge failure requires values and a null bridge audit")
    elif values is None:
        raise ValueError("null failure requires present response values")
    _require_self_hash_v1(attempt, "attempt_sha", "branch_attempt")
    return attempt
