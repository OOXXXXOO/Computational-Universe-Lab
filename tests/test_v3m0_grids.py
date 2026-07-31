from __future__ import annotations

import dataclasses
import unittest

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.grids import (
    BridgeKGridManifest,
    DynamicsKGridManifest,
    bridge_grid_payload,
    build_bridge_grid_manifest,
    build_dynamics_grid_manifest,
    dynamics_grid_payload,
    verify_bridge_grid_manifest,
    verify_dynamics_grid_manifest,
)


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


if __name__ == "__main__":
    unittest.main()
