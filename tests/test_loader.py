"""Tests for bim_quality_checker.loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
import pytest

from bim_quality_checker.loader import load_point_cloud


class TestLoadPointCloud:
    def test_load_ply(self, tmp_path: Path) -> None:
        pcd = o3d.geometry.PointCloud()
        pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        pcd.points = o3d.utility.Vector3dVector(pts)
        ply_path = tmp_path / "test.ply"
        o3d.io.write_point_cloud(str(ply_path), pcd)

        loaded = load_point_cloud(ply_path)
        assert not loaded.is_empty()
        loaded_pts = np.asarray(loaded.points)
        np.testing.assert_allclose(loaded_pts, pts, atol=1e-6)

    def test_load_pcd(self, tmp_path: Path) -> None:
        pcd = o3d.geometry.PointCloud()
        pts = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        pcd.points = o3d.utility.Vector3dVector(pts)
        pcd_path = tmp_path / "test.pcd"
        o3d.io.write_point_cloud(str(pcd_path), pcd)

        loaded = load_point_cloud(pcd_path)
        assert not loaded.is_empty()
        assert len(np.asarray(loaded.points)) == 2

    def test_load_xyz(self, tmp_path: Path) -> None:
        xyz_path = tmp_path / "test.xyz"
        xyz_path.write_text("0.0 0.0 0.0\n1.0 1.0 1.0\n2.0 2.0 2.0\n")

        loaded = load_point_cloud(xyz_path)
        assert not loaded.is_empty()
        assert len(np.asarray(loaded.points)) == 3

    def test_unsupported_format(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "test.csv"
        bad_path.write_text("1,2,3\n")
        with pytest.raises(ValueError, match="Unsupported"):
            load_point_cloud(bad_path)

    def test_empty_point_cloud(self, tmp_path: Path) -> None:
        pcd = o3d.geometry.PointCloud()
        ply_path = tmp_path / "empty.ply"
        o3d.io.write_point_cloud(str(ply_path), pcd)
        with pytest.raises(RuntimeError, match="empty"):
            load_point_cloud(ply_path)
