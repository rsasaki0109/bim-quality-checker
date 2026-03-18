"""Tests for bim_quality_checker.report."""

from __future__ import annotations

import json

import pytest

from bim_quality_checker.report import generate_report, _grade


@pytest.fixture()
def sample_results() -> dict:
    return {
        "geometric": {
            "accuracy": 0.92,
            "completeness": 0.88,
            "coverage_ratio": 0.90,
            "chamfer_distance": 0.0023,
            "mean_point_to_surface": 0.032,
            "median_point_to_surface": 0.021,
        },
        "topological": {
            "wall_connectivity": {
                "n_components": 1,
                "largest_component_triangles": 5000,
                "is_single_component": True,
            },
            "room_closure": {
                "is_watertight": True,
                "n_non_manifold_edges": 0,
            },
        },
        "params": {
            "distance_threshold": 0.05,
            "n_mesh_samples": 50000,
            "n_pcd_points": 100000,
        },
    }


class TestGenerateReportJSON:
    def test_json_roundtrip(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="json")
        parsed = json.loads(output)
        assert parsed == sample_results

    def test_json_keys(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="json")
        parsed = json.loads(output)
        assert "geometric" in parsed
        assert "topological" in parsed
        assert "params" in parsed


class TestGenerateReportText:
    def test_contains_header(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="text")
        assert "BIM Quality Report" in output

    def test_contains_metrics(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="text")
        assert "Accuracy" in output
        assert "Completeness" in output
        assert "Coverage ratio" in output
        assert "Chamfer distance" in output

    def test_contains_topological(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="text")
        assert "Wall components" in output
        assert "Watertight" in output

    def test_contains_grade(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="text")
        assert "Grade" in output

    def test_percentage_formatting(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="text")
        assert "92.0%" in output
        assert "88.0%" in output

    def test_default_fmt_is_text(self, sample_results: dict) -> None:
        output = generate_report(sample_results)
        assert "BIM Quality Report" in output


class TestGrading:
    def test_grade_a(self) -> None:
        assert "A" in _grade({"accuracy": 0.97, "completeness": 0.96})

    def test_grade_b(self) -> None:
        assert "B" in _grade({"accuracy": 0.90, "completeness": 0.88})

    def test_grade_c(self) -> None:
        assert "C" in _grade({"accuracy": 0.75, "completeness": 0.72})

    def test_grade_d(self) -> None:
        assert "D" in _grade({"accuracy": 0.50, "completeness": 0.40})

    def test_grade_na(self) -> None:
        assert _grade({}) == "N/A"
