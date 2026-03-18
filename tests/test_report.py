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


class TestGenerateReportMarkdown:
    def test_contains_header(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="markdown")
        assert "# BIM Quality Report" in output

    def test_contains_table(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="markdown")
        assert "| Accuracy |" in output
        assert "| Completeness |" in output

    def test_contains_grade(self, sample_results: dict) -> None:
        output = generate_report(sample_results, fmt="markdown")
        assert "Grade:" in output


class TestPassFailReport:
    def test_pass_shown(self, sample_results: dict) -> None:
        sample_results["pass_fail"] = {
            "threshold": 0.85,
            "score": 0.90,
            "passed": True,
        }
        output = generate_report(sample_results, fmt="text")
        assert "PASS" in output

    def test_fail_shown(self, sample_results: dict) -> None:
        sample_results["pass_fail"] = {
            "threshold": 0.95,
            "score": 0.80,
            "passed": False,
        }
        output = generate_report(sample_results, fmt="text")
        assert "FAIL" in output

    def test_markdown_pass_fail(self, sample_results: dict) -> None:
        sample_results["pass_fail"] = {
            "threshold": 0.85,
            "score": 0.90,
            "passed": True,
        }
        output = generate_report(sample_results, fmt="markdown")
        assert "**PASS**" in output


class TestElementBreakdownReport:
    def test_element_breakdown_text(self, sample_results: dict) -> None:
        sample_results["element_breakdown"] = {
            "by_type_summary": {
                "IfcWall": {"count": 5, "mean_accuracy": 0.92, "mean_completeness": 0.88},
            },
            "worst_elements": [
                {
                    "global_id": "abc123",
                    "ifc_type": "IfcWall",
                    "accuracy": 0.60,
                    "mean_deviation": 0.08,
                },
            ],
        }
        output = generate_report(sample_results, fmt="text")
        assert "Per-Element Breakdown" in output
        assert "IfcWall" in output
        assert "abc123" in output

    def test_element_breakdown_markdown(self, sample_results: dict) -> None:
        sample_results["element_breakdown"] = {
            "by_type_summary": {
                "IfcSlab": {"count": 3, "mean_accuracy": 0.85, "mean_completeness": 0.80},
            },
            "worst_elements": [],
        }
        output = generate_report(sample_results, fmt="markdown")
        assert "## Per-Element Breakdown" in output
        assert "IfcSlab" in output


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
