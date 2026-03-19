"""Tests for bim_quality_checker.deviation_map."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
import pytest

from bim_quality_checker.deviation_map import (
    compute_deviation_map,
    deviation_colors,
    export_colored_pointcloud,
)


class TestComputeDeviationMap:
    def test_on_surface_near_zero(
        self,
        cube_mesh: o3d.geometry.TriangleMesh,
        cube_surface_pcd: o3d.geometry.PointCloud,
    ) -> None:
        devs = compute_deviation_map(cube_mesh, cube_surface_pcd)
        assert devs.shape == (len(np.asarray(cube_surface_pcd.points)),)
        np.testing.assert_allclose(devs, 0.0, atol=1e-3)

    def test_offset_points(
        self, cube_mesh: o3d.geometry.TriangleMesh
    ) -> None:
        pcd = o3d.geometry.PointCloud()
        pts = np.array([[0.6, 0.0, 0.0], [0.0, 0.7, 0.0]], dtype=np.float64)
        pcd.points = o3d.utility.Vector3dVector(pts)
        devs = compute_deviation_map(cube_mesh, pcd)
        np.testing.assert_allclose(devs[0], 0.1, atol=1e-3)
        np.testing.assert_allclose(devs[1], 0.2, atol=1e-3)


class TestDeviationColors:
    def test_shape(self) -> None:
        devs = np.array([0.0, 0.05, 0.1, 0.2])
        colors = deviation_colors(devs)
        assert colors.shape == (4, 3)

    def test_blue_at_zero(self) -> None:
        devs = np.array([0.0])
        colors = deviation_colors(devs, vmin=0.0, vmax=1.0)
        # At t=0 should be blue (0, 0, 1)
        np.testing.assert_allclose(colors[0], [0.0, 0.0, 1.0])

    def test_red_at_max(self) -> None:
        devs = np.array([1.0])
        colors = deviation_colors(devs, vmin=0.0, vmax=1.0)
        # At t=1 should be red (1, 0, 0)
        np.testing.assert_allclose(colors[0], [1.0, 0.0, 0.0])

    def test_green_at_midpoint(self) -> None:
        devs = np.array([0.5])
        colors = deviation_colors(devs, vmin=0.0, vmax=1.0)
        # At t=0.5 should be green (0, 1, 0)
        np.testing.assert_allclose(colors[0], [0.0, 1.0, 0.0])

    def test_values_in_range(self) -> None:
        devs = np.linspace(0, 1, 100)
        colors = deviation_colors(devs, vmin=0.0, vmax=1.0)
        assert colors.min() >= 0.0
        assert colors.max() <= 1.0


class TestExportColoredPointcloud:
    def test_writes_ply(
        self,
        cube_mesh: o3d.geometry.TriangleMesh,
        cube_surface_pcd: o3d.geometry.PointCloud,
        tmp_path: Path,
    ) -> None:
        devs = compute_deviation_map(cube_mesh, cube_surface_pcd)
        out_path = tmp_path / "deviation.ply"
        result_path = export_colored_pointcloud(cube_surface_pcd, devs, out_path)
        assert result_path == out_path
        assert out_path.exists()

        # Reload and verify
        loaded = o3d.io.read_point_cloud(str(out_path))
        assert not loaded.is_empty()
        assert loaded.has_colors()
        assert len(np.asarray(loaded.points)) == len(np.asarray(cube_surface_pcd.points))
