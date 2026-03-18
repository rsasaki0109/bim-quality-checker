"""Shared fixtures for BIM Quality Checker tests."""

from __future__ import annotations

import numpy as np
import open3d as o3d
import pytest


@pytest.fixture()
def cube_mesh() -> o3d.geometry.TriangleMesh:
    """Unit cube mesh centered at origin."""
    mesh = o3d.geometry.TriangleMesh.create_box(1.0, 1.0, 1.0)
    mesh.translate([-0.5, -0.5, -0.5])
    mesh.compute_vertex_normals()
    return mesh


@pytest.fixture()
def cube_surface_pcd(cube_mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.PointCloud:
    """Point cloud sampled on the cube surface."""
    pcd = cube_mesh.sample_points_uniformly(number_of_points=5000)
    return pcd


@pytest.fixture()
def cube_surface_points(cube_surface_pcd: o3d.geometry.PointCloud) -> np.ndarray:
    """Numpy array of points on the cube surface."""
    return np.asarray(cube_surface_pcd.points)
