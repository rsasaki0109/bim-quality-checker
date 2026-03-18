"""Tests for bim_quality_checker.cli."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from bim_quality_checker.cli import main


class TestCLIGroup:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "BIM Quality Checker" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestReportCommand:
    def test_report_text(self, tmp_path: Path) -> None:
        results = {
            "geometric": {
                "accuracy": 0.95,
                "completeness": 0.90,
                "coverage_ratio": 0.88,
                "chamfer_distance": 0.001,
                "mean_point_to_surface": 0.02,
                "median_point_to_surface": 0.015,
            },
            "topological": {
                "wall_connectivity": {
                    "n_components": 1,
                    "largest_component_triangles": 1000,
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
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(results))

        runner = CliRunner()
        result = runner.invoke(main, ["report", str(json_path)])
        assert result.exit_code == 0
        assert "BIM Quality Report" in result.output

    def test_report_json_format(self, tmp_path: Path) -> None:
        results = {
            "geometric": {"accuracy": 0.95, "completeness": 0.90},
            "topological": {},
            "params": {},
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(results))

        runner = CliRunner()
        result = runner.invoke(main, ["report", str(json_path), "-f", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["geometric"]["accuracy"] == 0.95

    def test_report_output_file(self, tmp_path: Path) -> None:
        results = {
            "geometric": {"accuracy": 0.80, "completeness": 0.75},
            "topological": {},
            "params": {},
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(results))
        out_path = tmp_path / "report.txt"

        runner = CliRunner()
        result = runner.invoke(
            main, ["report", str(json_path), "-o", str(out_path)]
        )
        assert result.exit_code == 0
        assert out_path.exists()
        assert "BIM Quality Report" in out_path.read_text()

    def test_report_missing_file(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["report", "/nonexistent/results.json"])
        assert result.exit_code != 0


class TestCheckCommand:
    def test_check_missing_files(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["check", "/nonexistent/model.ifc", "/nonexistent/scan.ply"]
        )
        assert result.exit_code != 0

    def test_check_has_threshold_option(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["check", "--help"])
        assert result.exit_code == 0
        assert "--threshold" in result.output


class TestElementsCommand:
    def test_elements_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["elements", "--help"])
        assert result.exit_code == 0
        assert "Per-element" in result.output

    def test_elements_missing_files(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["elements", "/nonexistent/model.ifc", "/nonexistent/scan.ply"]
        )
        assert result.exit_code != 0


class TestDeviationCommand:
    def test_deviation_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["deviation", "--help"])
        assert result.exit_code == 0
        assert "deviation" in result.output.lower()

    def test_deviation_missing_files(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["deviation", "/nonexistent/model.ifc", "/nonexistent/scan.ply",
             "-o", "/tmp/out.ply"],
        )
        assert result.exit_code != 0


class TestReportMarkdown:
    def test_report_markdown(self, tmp_path: Path) -> None:
        results = {
            "geometric": {"accuracy": 0.95, "completeness": 0.90},
            "topological": {},
            "params": {},
        }
        json_path = tmp_path / "results.json"
        json_path.write_text(json.dumps(results))

        runner = CliRunner()
        result = runner.invoke(main, ["report", str(json_path), "-f", "markdown"])
        assert result.exit_code == 0
        assert "# BIM Quality Report" in result.output
