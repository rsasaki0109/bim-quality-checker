"""Tests for bim_quality_checker.ci and the gate CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from bim_quality_checker.ci import (
    QualityGate,
    QualityGateResult,
    format_github_annotation,
    format_markdown_report,
)
from bim_quality_checker.cli import main


# ---------------------------------------------------------------------------
# QualityGateResult dataclass
# ---------------------------------------------------------------------------


class TestQualityGateResult:
    def test_passed_result(self) -> None:
        result = QualityGateResult(
            passed=True,
            grade="A (Excellent)",
            score=0.96,
            threshold=0.85,
            metrics={"geometric": {"accuracy": 0.97, "completeness": 0.95}},
            summary_text="Score: 96.0% -- PASS",
        )
        assert result.passed is True
        assert result.grade == "A (Excellent)"
        assert result.score == 0.96

    def test_failed_result(self) -> None:
        result = QualityGateResult(
            passed=False,
            grade="D (Needs improvement)",
            score=0.50,
            threshold=0.85,
        )
        assert result.passed is False
        assert result.score == 0.50


# ---------------------------------------------------------------------------
# format_markdown_report
# ---------------------------------------------------------------------------


class TestFormatMarkdownReport:
    def _make_result(self, passed: bool = True, score: float = 0.90) -> QualityGateResult:
        return QualityGateResult(
            passed=passed,
            grade="B (Good)" if passed else "D (Needs improvement)",
            score=score,
            threshold=0.85,
            metrics={
                "geometric": {
                    "accuracy": 0.92,
                    "completeness": 0.88,
                    "coverage_ratio": 0.87,
                    "chamfer_distance": 0.002,
                    "mean_point_to_surface": 0.03,
                    "median_point_to_surface": 0.02,
                },
                "topological": {
                    "wall_connectivity": {
                        "n_components": 1,
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
            },
        )

    def test_contains_header(self) -> None:
        md = format_markdown_report(self._make_result())
        assert "## BIM Quality Gate: PASS" in md

    def test_contains_metrics_table(self) -> None:
        md = format_markdown_report(self._make_result())
        assert "| Accuracy |" in md
        assert "| Completeness |" in md

    def test_fail_status(self) -> None:
        md = format_markdown_report(self._make_result(passed=False, score=0.60))
        assert "FAIL" in md

    def test_contains_topological(self) -> None:
        md = format_markdown_report(self._make_result())
        assert "Topological" in md

    def test_contains_parameters(self) -> None:
        md = format_markdown_report(self._make_result())
        assert "Distance threshold" in md


# ---------------------------------------------------------------------------
# format_github_annotation
# ---------------------------------------------------------------------------


class TestFormatGithubAnnotation:
    def test_pass_annotation(self) -> None:
        result = QualityGateResult(
            passed=True,
            grade="A (Excellent)",
            score=0.96,
            threshold=0.85,
            metrics={"geometric": {"accuracy": 0.97, "completeness": 0.95}},
        )
        output = format_github_annotation(result)
        assert "::notice::" in output
        assert "PASSED" in output

    def test_fail_annotation(self) -> None:
        result = QualityGateResult(
            passed=False,
            grade="D (Needs improvement)",
            score=0.50,
            threshold=0.85,
            metrics={"geometric": {"accuracy": 0.40, "completeness": 0.60}},
        )
        output = format_github_annotation(result)
        assert "::error::" in output
        assert "FAILED" in output

    def test_warning_on_low_accuracy(self) -> None:
        result = QualityGateResult(
            passed=False,
            grade="D (Needs improvement)",
            score=0.50,
            threshold=0.85,
            metrics={"geometric": {"accuracy": 0.40, "completeness": 0.60}},
        )
        output = format_github_annotation(result)
        assert "::warning::" in output
        assert "Accuracy" in output

    def test_warning_on_high_deviation(self) -> None:
        result = QualityGateResult(
            passed=True,
            grade="B (Good)",
            score=0.90,
            threshold=0.85,
            metrics={
                "geometric": {
                    "accuracy": 0.92,
                    "completeness": 0.88,
                    "mean_point_to_surface": 0.15,
                },
            },
        )
        output = format_github_annotation(result)
        assert "mean point-to-surface" in output.lower() or "Mean" in output


# ---------------------------------------------------------------------------
# gate CLI command
# ---------------------------------------------------------------------------


class TestGateCLICommand:
    def test_gate_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["gate", "--help"])
        assert result.exit_code == 0
        assert "quality gate" in result.output.lower()
        assert "--threshold" in result.output
        assert "--format" in result.output

    def test_gate_missing_files(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["gate", "/nonexistent/model.ifc", "/nonexistent/scan.ply"],
        )
        assert result.exit_code != 0
