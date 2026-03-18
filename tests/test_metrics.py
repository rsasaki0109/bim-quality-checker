"""Tests for bim_quality_checker.metrics."""

from __future__ import annotations

import numpy as np
import open3d as o3d
import pytest

from bim_quality_checker.metrics import (
    accuracy,
    chamfer_distance,
    check_room_closure,
    check_wall_connectivity,
    completeness,
    coverage_ratio,
    point_to_surface_distances,
)


class TestPointToSurfaceDistances:
    """Tests for point_to_surface_distances."""

    def test_points_on_surface_are_zero(
        self, cube_mesh: o3d.geometry.TriangleMesh, cube_surface_points: np.ndarray
    ) -> None:
        dists = point_to_surface_distances(cube_surface_points, cube_mesh)
        assert dists.shape == (len(cube_surface_points),)
        np.testing.assert_allclose(dists, 0.0, atol=1e-4)

    def test_points_offset_from_surface(
        self, cube_mesh: o3d.geometry.TriangleMesh
    ) -> None:
        # Points at distance 0.1 from the +X face (x=0.5)
        pts = np.array([[0.6, 0.0, 0.0], [0.6, 0.2, 0.2]], dtype=np.float64)
        dists = point_to_surface_distances(pts, cube_mesh)
        np.testing.assert_allclose(dists, 0.1, atol=1e-3)


class TestAccuracy:
    def test_all_within_threshold(self) -> None:
        dists = np.array([0.01, 0.02, 0.03, 0.04])
        assert accuracy(dists, threshold=0.05) == 1.0

    def test_none_within_threshold(self) -> None:
        dists = np.array([0.1, 0.2, 0.3])
        assert accuracy(dists, threshold=0.05) == 0.0

    def test_partial(self) -> None:
        dists = np.array([0.01, 0.1])
        assert accuracy(dists, threshold=0.05) == pytest.approx(0.5)


class TestCompleteness:
    def test_all_within_threshold(self) -> None:
        dists = np.array([0.01, 0.02, 0.03])
        assert completeness(dists, threshold=0.05) == 1.0

    def test_partial(self) -> None:
        dists = np.array([0.01, 0.02, 0.1, 0.2])
        assert completeness(dists, threshold=0.05) == pytest.approx(0.5)


class TestChamferDistance:
    def test_identical_sets(self) -> None:
        pts = np.random.default_rng(42).uniform(-1, 1, (100, 3))
        cd = chamfer_distance(pts, pts.copy())
        assert cd == pytest.approx(0.0, abs=1e-8)

    def test_symmetric(self) -> None:
        rng = np.random.default_rng(42)
        a = rng.uniform(-1, 1, (100, 3))
        b = rng.uniform(-1, 1, (100, 3))
        cd_ab = chamfer_distance(a, b)
        cd_ba = chamfer_distance(b, a)
        assert cd_ab == pytest.approx(cd_ba, rel=1e-5)

    def test_distant_sets_larger(self) -> None:
        a = np.zeros((50, 3))
        b_close = np.ones((50, 3)) * 0.1
        b_far = np.ones((50, 3)) * 10.0
        cd_close = chamfer_distance(a, b_close)
        cd_far = chamfer_distance(a, b_far)
        assert cd_far > cd_close


class TestCoverageRatio:
    def test_on_surface_full_coverage(
        self,
        cube_surface_points: np.ndarray,
        cube_mesh: o3d.geometry.TriangleMesh,
    ) -> None:
        ratio = coverage_ratio(cube_surface_points, cube_mesh, threshold=0.01)
        assert ratio > 0.99

    def test_far_points_no_coverage(
        self, cube_mesh: o3d.geometry.TriangleMesh
    ) -> None:
        pts = np.array([[10.0, 10.0, 10.0], [20.0, 20.0, 20.0]])
        ratio = coverage_ratio(pts, cube_mesh, threshold=0.05)
        assert ratio == 0.0


class TestWallConnectivity:
    def test_single_mesh_one_component(
        self, cube_mesh: o3d.geometry.TriangleMesh
    ) -> None:
        result = check_wall_connectivity(cube_mesh)
        assert result["n_components"] == 1
        assert result["is_single_component"] is True

    def test_two_separated_meshes(self) -> None:
        box1 = o3d.geometry.TriangleMesh.create_box(1, 1, 1)
        box2 = o3d.geometry.TriangleMesh.create_box(1, 1, 1)
        box2.translate([10, 10, 10])
        combined = box1 + box2
        result = check_wall_connectivity(combined)
        assert result["n_components"] == 2
        assert result["is_single_component"] is False


class TestRoomClosure:
    def test_watertight_box(self, cube_mesh: o3d.geometry.TriangleMesh) -> None:
        result = check_room_closure(cube_mesh)
        assert result["is_watertight"] is True
        assert result["n_non_manifold_edges"] == 0
