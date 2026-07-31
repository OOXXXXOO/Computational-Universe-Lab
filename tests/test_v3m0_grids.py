from __future__ import annotations

import dataclasses
import unittest
from unittest import mock

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.grids import (
    BRIDGE_GRID_MAX_POINT_COUNT,
    RESPONSE_GRID_MAX_POINT_COUNT,
    BridgeKGridManifest,
    DirectionManifest,
    DynamicsKGridManifest,
    ResponseKGridManifest,
    build_application_bridge_grid_manifest,
    bridge_grid_payload,
    build_bridge_grid_manifest,
    build_dynamics_grid_manifest,
    build_response_grid_manifest,
    direction_manifest_payload,
    dynamics_grid_payload,
    response_grid_payload,
    verify_application_bridge_grid_manifest,
    verify_bridge_grid_manifest,
    verify_dynamics_grid_manifest,
    verify_response_grid_manifest,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze


GENERAL_EVIDENCE_TEXT_BYTES_MAX = 16_384
GENERAL_EVIDENCE_SPATIAL_NDIM_MAX = 64


class StrictKGridTests(unittest.TestCase):
    def test_zero_support_has_unique_exact_singleton_dynamics_grid(self):
        support = ((0, 0),)
        grid = build_dynamics_grid_manifest(support, support)
        self.assertEqual(grid.qualification_profile, "exact-offset-zero-v1")
        self.assertEqual(grid.spatial_ndim, 2)
        self.assertEqual(grid.torus_denominators, (1, 1))
        self.assertEqual(grid.reciprocal_indices, ((0, 0),))
        self.assertEqual(
            verify_dynamics_grid_manifest(grid, support, support),
            grid,
        )

    def test_nonzero_support_has_complete_lexicographic_full64_grid(self):
        transition_support = ((-1,), (0,), (1,))
        metric_support = ((0,),)
        grid = build_dynamics_grid_manifest(
            transition_support,
            metric_support,
        )
        self.assertEqual(grid.qualification_profile, "cartesian-full-64-v1")
        self.assertEqual(grid.torus_denominators, (64,))
        self.assertEqual(
            grid.reciprocal_indices,
            tuple((index,) for index in range(64)),
        )
        self.assertEqual(
            verify_dynamics_grid_manifest(
                grid,
                transition_support,
                metric_support,
            ),
            grid,
        )

    def test_resigned_dynamics_grid_cannot_change_profile_or_points(self):
        support = ((0,),)
        grid = build_dynamics_grid_manifest(support, support)
        changed = dataclasses.replace(
            grid,
            torus_denominators=(64,),
            dynamics_grid_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            dynamics_grid_sha=canonical_sha(dynamics_grid_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_grid_manifest(changed, support, support)

    def test_bridge_grid_is_mechanically_generated_from_active_axes(self):
        shape = (5, 7)
        support = ((-1, 0), (0, -2), (0, 0), (1, 2))
        grid = build_bridge_grid_manifest(shape, support)
        self.assertEqual(grid.spatial_shape, shape)
        self.assertEqual(grid.torus_denominators, shape)
        self.assertEqual(
            grid.reciprocal_indices,
            tuple(sorted(((0, 0), (1, 0), (4, 0), (0, 1), (0, 6)))),
        )
        self.assertEqual(
            verify_bridge_grid_manifest(grid, shape, support),
            grid,
        )

    def test_zero_support_bridge_grid_is_only_origin(self):
        grid = build_bridge_grid_manifest((2, 9), ((0, 0),))
        self.assertEqual(grid.reciprocal_indices, ((0, 0),))

    def test_active_axis_must_have_non_nyquist_neighbors(self):
        with self.assertRaises((TypeError, ValueError)):
            build_bridge_grid_manifest((2,), ((0,), (1,)))

    def test_grid_types_are_not_interchangeable(self):
        support = ((0,),)
        dynamics = build_dynamics_grid_manifest(support, support)
        bridge = build_bridge_grid_manifest((5,), support)
        self.assertIsInstance(dynamics, DynamicsKGridManifest)
        self.assertIsInstance(bridge, BridgeKGridManifest)
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_grid_manifest(bridge, support, support)
        with self.assertRaises((TypeError, ValueError)):
            verify_bridge_grid_manifest(dynamics, (5,), support)

    def test_resigned_bridge_grid_cannot_add_caller_points(self):
        shape = (5,)
        support = ((-1,), (0,), (1,))
        grid = build_bridge_grid_manifest(shape, support)
        changed = dataclasses.replace(
            grid,
            reciprocal_indices=tuple(
                sorted(grid.reciprocal_indices + ((2,),))
            ),
            bridge_grid_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            bridge_grid_sha=canonical_sha(bridge_grid_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_bridge_grid_manifest(changed, shape, support)

    def test_combined_dynamics_support_cap_precedes_first_hash(self):
        grid = build_dynamics_grid_manifest(((0,),), ((0,),))
        shared_row = ("x" * 1_000,)
        large_support = (shared_row,) * 25_000
        with mock.patch(
            "rulespace_v3.grids.canonical_sha",
            side_effect=AssertionError("hash before combined support cap"),
        ) as hasher:
            with self.assertRaisesRegex(
                ValueError,
                "serialized body.*resource cap",
            ):
                verify_dynamics_grid_manifest(
                    grid,
                    large_support,  # type: ignore[arg-type]
                    large_support,  # type: ignore[arg-type]
                )
        hasher.assert_not_called()


class DirectionalResponseGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.application = (
            cls.parent.manifest.synthetic_control_application_specs[0]
        )

    def test_response_grid_is_exactly_application_derived(self):
        grid = build_response_grid_manifest(self.application)
        source = self.application.grid_protocol

        self.assertIs(type(grid), ResponseKGridManifest)
        self.assertEqual(
            grid.qualification_profile,
            "directional-momentum-shell-path-v1",
        )
        self.assertEqual(grid.spatial_ndim, source.spatial_ndim)
        self.assertEqual(
            grid.torus_denominators,
            source.response_torus_denominators,
        )
        self.assertEqual(
            grid.reciprocal_indices,
            source.response_reciprocal_indices,
        )
        self.assertEqual(
            grid.direction_manifest.direction_ids,
            source.direction_ids,
        )
        self.assertEqual(
            grid.direction_manifest.primitive_directions,
            source.primitive_directions,
        )
        self.assertEqual(
            grid.direction_manifest.path_ids,
            source.path_ids,
        )
        self.assertEqual(
            grid.direction_manifest.ordered_paths,
            source.ordered_paths,
        )
        self.assertEqual(
            grid.direction_manifest.closure_path_pairs,
            source.closure_path_pairs,
        )
        self.assertEqual(
            verify_response_grid_manifest(grid, self.application),
            grid,
        )

    def test_application_bridge_grid_preserves_the_frozen_periodic_points(self):
        grid = build_application_bridge_grid_manifest(self.application)
        source = self.application.grid_protocol
        self.assertEqual(grid.spatial_shape, source.spatial_shape)
        self.assertEqual(
            grid.torus_denominators,
            source.spatial_shape,
        )
        self.assertEqual(
            grid.reciprocal_indices,
            source.bridge_reciprocal_indices,
        )
        self.assertEqual(
            verify_application_bridge_grid_manifest(
                grid,
                self.application,
            ),
            grid,
        )

    def test_resigned_direction_or_grid_body_cannot_change_application_wire(self):
        grid = build_response_grid_manifest(self.application)
        direction = dataclasses.replace(
            grid.direction_manifest,
            direction_ids=("renamed-direction",),
            direction_manifest_sha="0" * 64,
        )
        direction = dataclasses.replace(
            direction,
            direction_manifest_sha=canonical_sha(
                direction_manifest_payload(direction)
            ),
        )
        changed = dataclasses.replace(
            grid,
            direction_manifest=direction,
            response_grid_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            response_grid_sha=canonical_sha(
                response_grid_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_response_grid_manifest(changed, self.application)

    def test_paths_and_closures_are_validated_against_the_grid(self):
        grid = build_response_grid_manifest(self.application)
        direction = dataclasses.replace(
            grid.direction_manifest,
            ordered_paths=(((2,), (1,)),),
            direction_manifest_sha="0" * 64,
        )
        direction = dataclasses.replace(
            direction,
            direction_manifest_sha=canonical_sha(
                direction_manifest_payload(direction)
            ),
        )
        changed = dataclasses.replace(
            grid,
            direction_manifest=direction,
            response_grid_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            response_grid_sha=canonical_sha(
                response_grid_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_response_grid_manifest(changed, self.application)

    def test_response_grid_rejects_other_strict_grid_types(self):
        support = ((0,),)
        dynamics = build_dynamics_grid_manifest(support, support)
        bridge = build_bridge_grid_manifest((5,), support)
        for other in (dynamics, bridge):
            with self.subTest(other=type(other).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    verify_response_grid_manifest(
                        other,
                        self.application,
                    )

    def test_response_point_cap_runs_before_application_replay(self):
        oversized_points = ((0,),) * (RESPONSE_GRID_MAX_POINT_COUNT + 1)
        oversized_protocol = dataclasses.replace(
            self.application.grid_protocol,
            response_reciprocal_indices=oversized_points,
        )
        oversized_application = dataclasses.replace(
            self.application,
            grid_protocol=oversized_protocol,
        )
        with mock.patch(
            "rulespace_v3.grids.verify_synthetic_control_application_spec"
        ) as replay:
            with self.assertRaisesRegex(ValueError, "point cap"):
                build_response_grid_manifest(oversized_application)
        replay.assert_not_called()

    def test_raw_path_cap_runs_before_hash_materialization(self):
        grid = build_response_grid_manifest(self.application)
        oversized_path = ((1,),) * (RESPONSE_GRID_MAX_POINT_COUNT + 1)
        direction = dataclasses.replace(
            grid.direction_manifest,
            ordered_paths=(oversized_path,),
        )
        changed = dataclasses.replace(
            grid,
            direction_manifest=direction,
        )
        with mock.patch("rulespace_v3.grids.canonical_sha") as hasher:
            with self.assertRaisesRegex(ValueError, "paths exceed point cap"):
                verify_response_grid_manifest(changed, self.application)
        hasher.assert_not_called()

    def test_raw_direction_and_response_wires_have_exact_fields(self):
        grid = build_response_grid_manifest(self.application)
        self.assertEqual(
            tuple(DirectionManifest.__dataclass_fields__),
            (
                "direction_schema_version",
                "direction_ids",
                "primitive_directions",
                "path_ids",
                "ordered_paths",
                "closure_path_pairs",
                "direction_manifest_sha",
            ),
        )
        self.assertEqual(
            tuple(ResponseKGridManifest.__dataclass_fields__),
            (
                "grid_schema_version",
                "qualification_profile",
                "spatial_ndim",
                "torus_denominators",
                "reciprocal_indices",
                "direction_manifest",
                "response_grid_sha",
            ),
        )
        self.assertEqual(
            tuple(direction_manifest_payload(grid.direction_manifest)),
            tuple(DirectionManifest.__dataclass_fields__)[:-1],
        )
        self.assertEqual(
            tuple(response_grid_payload(grid)),
            tuple(ResponseKGridManifest.__dataclass_fields__)[:-1],
        )

    def test_raw_grid_verifiers_reject_unknown_instance_fields(self):
        response = build_response_grid_manifest(self.application)
        object.__setattr__(response, "caller_unknown", "forbidden")
        with self.assertRaises((TypeError, ValueError)):
            verify_response_grid_manifest(response, self.application)

        response = build_response_grid_manifest(self.application)
        object.__setattr__(
            response.direction_manifest,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_response_grid_manifest(response, self.application)

        application_bridge = build_application_bridge_grid_manifest(
            self.application
        )
        object.__setattr__(
            application_bridge,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_application_bridge_grid_manifest(
                application_bridge,
                self.application,
            )

        support = ((0,),)
        dynamics = build_dynamics_grid_manifest(support, support)
        object.__setattr__(dynamics, "caller_unknown", "forbidden")
        with self.assertRaises((TypeError, ValueError)):
            verify_dynamics_grid_manifest(dynamics, support, support)

        support_bridge = build_bridge_grid_manifest((5,), support)
        object.__setattr__(
            support_bridge,
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_bridge_grid_manifest(
                support_bridge,
                (5,),
                support,
            )

    def test_all_application_grid_caps_precede_application_replay(self):
        protocol = object.__new__(type(self.application.grid_protocol))
        for field in type(protocol).__dataclass_fields__:
            object.__setattr__(
                protocol,
                field,
                getattr(self.application.grid_protocol, field),
            )
        object.__setattr__(
            protocol,
            "direction_ids",
            ("direction",) * (RESPONSE_GRID_MAX_POINT_COUNT + 1),
        )
        application = object.__new__(type(self.application))
        for field in type(application).__dataclass_fields__:
            object.__setattr__(
                application,
                field,
                getattr(self.application, field),
            )
        object.__setattr__(application, "grid_protocol", protocol)
        with mock.patch(
            "rulespace_v3.grids.verify_synthetic_control_application_spec",
            side_effect=AssertionError("application replay before caps"),
        ) as replay:
            with self.assertRaisesRegex(ValueError, "directions.*point cap"):
                build_response_grid_manifest(application)
        replay.assert_not_called()

    def test_application_bridge_raw_cap_precedes_hash_materialization(self):
        grid = build_application_bridge_grid_manifest(self.application)
        forged = object.__new__(BridgeKGridManifest)
        for field in BridgeKGridManifest.__dataclass_fields__:
            object.__setattr__(forged, field, getattr(grid, field))
        object.__setattr__(
            forged,
            "reciprocal_indices",
            ((0,),) * (BRIDGE_GRID_MAX_POINT_COUNT + 1),
        )
        with mock.patch(
            "rulespace_v3.grids.canonical_sha",
            side_effect=AssertionError("hash before bridge point cap"),
        ) as hasher:
            with self.assertRaisesRegex(ValueError, "bridge grid.*point cap"):
                verify_application_bridge_grid_manifest(
                    forged,
                    self.application,
                )
        hasher.assert_not_called()

    def test_oversized_text_rejects_before_hash_or_application_replay(self):
        grid = build_response_grid_manifest(self.application)
        forged = object.__new__(ResponseKGridManifest)
        for field in ResponseKGridManifest.__dataclass_fields__:
            object.__setattr__(forged, field, getattr(grid, field))
        object.__setattr__(
            forged,
            "grid_schema_version",
            "x" * (GENERAL_EVIDENCE_TEXT_BYTES_MAX + 1),
        )
        with (
            mock.patch(
                "rulespace_v3.grids.canonical_sha",
                side_effect=AssertionError("hash before text cap"),
            ) as hasher,
            mock.patch(
                "rulespace_v3.grids.verify_synthetic_control_application_spec",
                side_effect=AssertionError(
                    "application replay before text cap"
                ),
            ) as replay,
        ):
            with self.assertRaisesRegex(ValueError, "text.*resource cap"):
                verify_response_grid_manifest(
                    forged,
                    self.application,
                )
        hasher.assert_not_called()
        replay.assert_not_called()

    def test_utf8_text_byte_cap_precedes_hash_or_application_replay(self):
        grid = build_response_grid_manifest(self.application)
        forged = object.__new__(ResponseKGridManifest)
        for field in ResponseKGridManifest.__dataclass_fields__:
            object.__setattr__(forged, field, getattr(grid, field))
        object.__setattr__(
            forged,
            "grid_schema_version",
            "😀" * 5_000,
        )
        with (
            mock.patch(
                "rulespace_v3.grids.canonical_sha",
                side_effect=AssertionError("hash before UTF-8 text cap"),
            ) as hasher,
            mock.patch(
                "rulespace_v3.grids.verify_synthetic_control_application_spec",
                side_effect=AssertionError(
                    "application replay before UTF-8 text cap"
                ),
            ) as replay,
        ):
            with self.assertRaisesRegex(ValueError, "text.*resource cap"):
                verify_response_grid_manifest(
                    forged,
                    self.application,
                )
        hasher.assert_not_called()
        replay.assert_not_called()

    def test_response_builder_ignores_expected_grid_global_rebinding(self):
        import rulespace_v3.grids as grids

        baseline = build_response_grid_manifest(self.application)
        forged_direction = dataclasses.replace(
            baseline.direction_manifest,
            direction_ids=("forged-direction",),
            direction_manifest_sha="0" * 64,
        )
        forged_direction = dataclasses.replace(
            forged_direction,
            direction_manifest_sha=canonical_sha(
                direction_manifest_payload(forged_direction)
            ),
        )
        forged = dataclasses.replace(
            baseline,
            direction_manifest=forged_direction,
            response_grid_sha="0" * 64,
        )
        forged = dataclasses.replace(
            forged,
            response_grid_sha=canonical_sha(response_grid_payload(forged)),
        )
        with mock.patch.object(
            grids,
            "_expected_response_grid",
            return_value=forged,
        ):
            observed = build_response_grid_manifest(self.application)
        self.assertEqual(observed, baseline)

    def test_high_dimension_application_rejects_before_replay_or_hash(self):
        protocol = object.__new__(type(self.application.grid_protocol))
        for field in type(protocol).__dataclass_fields__:
            object.__setattr__(
                protocol,
                field,
                getattr(self.application.grid_protocol, field),
            )
        object.__setattr__(
            protocol,
            "spatial_ndim",
            GENERAL_EVIDENCE_SPATIAL_NDIM_MAX + 1,
        )
        object.__setattr__(
            protocol,
            "spatial_shape",
            (8,) * (GENERAL_EVIDENCE_SPATIAL_NDIM_MAX + 1),
        )
        application = object.__new__(type(self.application))
        for field in type(application).__dataclass_fields__:
            object.__setattr__(
                application,
                field,
                getattr(self.application, field),
            )
        object.__setattr__(application, "grid_protocol", protocol)
        with (
            mock.patch(
                "rulespace_v3.grids.verify_synthetic_control_application_spec",
                side_effect=AssertionError(
                    "application replay before dimension cap"
                ),
            ) as replay,
            mock.patch(
                "rulespace_v3.grids.canonical_sha",
                side_effect=AssertionError("hash before dimension cap"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(ValueError, "dimension.*resource cap"):
                build_response_grid_manifest(application)
        replay.assert_not_called()
        hasher.assert_not_called()

    def test_streamed_serialized_upper_bound_rejects_shared_text_body(self):
        shared_text = "x" * GENERAL_EVIDENCE_TEXT_BYTES_MAX
        direction_ids = (shared_text,) * 2_731
        protocol = object.__new__(type(self.application.grid_protocol))
        for field in type(protocol).__dataclass_fields__:
            object.__setattr__(
                protocol,
                field,
                getattr(self.application.grid_protocol, field),
            )
        object.__setattr__(protocol, "direction_ids", direction_ids)
        application = object.__new__(type(self.application))
        for field in type(application).__dataclass_fields__:
            object.__setattr__(
                application,
                field,
                getattr(self.application, field),
            )
        object.__setattr__(application, "grid_protocol", protocol)
        with (
            mock.patch(
                "rulespace_v3.grids.verify_synthetic_control_application_spec",
                side_effect=AssertionError(
                    "application replay before serialized cap"
                ),
            ) as replay,
            mock.patch(
                "rulespace_v3.grids.canonical_sha",
                side_effect=AssertionError("hash before serialized cap"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "serialized body.*resource cap",
            ):
                build_response_grid_manifest(application)
        replay.assert_not_called()
        hasher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
