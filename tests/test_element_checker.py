"""Tests for bim_quality_checker.element_checker."""

from __future__ import annotations

import numpy as np
import open3d as o3d
import pytest

from bim_quality_checker.element_checker import ElementChecker, ElementResult, ElementReport


@pytest.fixture()
def wall_mesh() -> o3d.geometry.TriangleMesh:
    """A thin box representing a wall."""
    mesh = o3d.geometry.TriangleMesh.create_box(3.0, 0.2, 2.5)
    mesh.compute_vertex_normals()
    return mesh


@pytest.fixture()
def wall_pcd(wall_mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.PointCloud:
    """Point cloud sampled on the wall surface."""
    return wall_mesh.sample_points_uniformly(number_of_points=3000)


class TestCheckElement:
    def test_perfect_match(
        self,
        wall_mesh: o3d.geometry.TriangleMesh,
        wall_pcd: o3d.geometry.PointCloud,
    ) -> None:
        checker = ElementChecker(distance_threshold=0.05)
        result = checker.check_element(
            wall_mesh, wall_pcd, element_type="IfcWall", global_id="abc123",
        )
        assert isinstance(result, ElementResult)
        assert result.ifc_type == "IfcWall"
        assert result.global_id == "abc123"
        assert result.accuracy > 0.7
        assert result.completeness > 0.5
        assert result.n_vertices > 0
        assert result.n_faces > 0

    def test_empty_mesh(self) -> None:
        checker = ElementChecker()
        empty_mesh = o3d.geometry.TriangleMesh()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.array([[0.0, 0.0, 0.0]]))
        result = checker.check_element(empty_mesh, pcd)
        assert result.accuracy == 0.0
        assert result.completeness == 0.0
        assert result.passed is False

    def test_far_points_low_quality(
        self,
        wall_mesh: o3d.geometry.TriangleMesh,
    ) -> None:
        """Points far from the mesh should give low accuracy."""
        far_pcd = o3d.geometry.PointCloud()
        far_pts = np.array([[100.0, 100.0, 100.0]] * 100)
        far_pcd.points = o3d.utility.Vector3dVector(far_pts)
        checker = ElementChecker(distance_threshold=0.05)
        result = checker.check_element(wall_mesh, far_pcd, element_type="IfcWall")
        assert result.accuracy == 0.0


class TestElementReport:
    def test_to_dict(self) -> None:
        elem = ElementResult(
            global_id="id1",
            ifc_type="IfcWall",
            name="Wall 1",
            n_vertices=8,
            n_faces=12,
            accuracy=0.95,
            completeness=0.88,
            mean_deviation=0.02,
            max_deviation=0.1,
            passed=True,
        )
        report = ElementReport(
            elements=[elem],
            by_type={"IfcWall": [elem]},
            worst_elements=[elem],
        )
        d = report.to_dict()
        assert d["n_elements"] == 1
        assert "IfcWall" in d["by_type_summary"]
        assert d["by_type_summary"]["IfcWall"]["count"] == 1
        assert len(d["worst_elements"]) == 1
        assert d["worst_elements"][0]["global_id"] == "id1"
        assert len(d["elements"]) == 1

    def test_empty_report(self) -> None:
        report = ElementReport()
        d = report.to_dict()
        assert d["n_elements"] == 0
        assert d["by_type_summary"] == {}
        assert d["worst_elements"] == []
