"""CI/CD quality gate for automated BIM validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class QualityGateResult:
    """Result of a quality gate check."""

    passed: bool
    grade: str
    score: float
    threshold: float
    metrics: dict[str, Any] = field(default_factory=dict)
    summary_text: str = ""


class QualityGate:
    """Automated BIM quality gate for CI/CD pipelines.

    Runs a full quality evaluation and determines pass/fail
    against a configurable threshold.
    """

    def check(
        self,
        ifc_path: str | Path,
        pcd_path: str | Path,
        threshold: float = 0.85,
        distance_threshold: float = 0.05,
    ) -> QualityGateResult:
        """Run quality gate check.

        Parameters
        ----------
        ifc_path : path to IFC file
        pcd_path : path to point cloud file
        threshold : pass/fail threshold for mean(accuracy, completeness)
        distance_threshold : distance threshold in metres

        Returns
        -------
        QualityGateResult with pass/fail, grade, metrics, and summary text
        """
        from bim_quality_checker.loader import load_ifc_surfaces, load_point_cloud
        from bim_quality_checker.metrics import evaluate_all

        ifc_path = Path(ifc_path)
        pcd_path = Path(pcd_path)

        bim_mesh = load_ifc_surfaces(ifc_path)
        pcd = load_point_cloud(pcd_path)
        metrics = evaluate_all(bim_mesh, pcd, distance_threshold=distance_threshold)

        geo = metrics.get("geometric", {})
        acc = geo.get("accuracy", 0.0)
        comp = geo.get("completeness", 0.0)
        score = (acc + comp) / 2.0

        passed = score >= threshold
        grade = _compute_grade(score)

        summary = (
            f"Score: {score:.1%} (threshold: {threshold:.1%}) -- "
            f"{'PASS' if passed else 'FAIL'} | "
            f"Grade: {grade}"
        )

        return QualityGateResult(
            passed=passed,
            grade=grade,
            score=score,
            threshold=threshold,
            metrics=metrics,
            summary_text=summary,
        )


def format_markdown_report(result: QualityGateResult) -> str:
    """Format a quality gate result as a Markdown report for PR comments.

    Parameters
    ----------
    result : QualityGateResult from QualityGate.check()

    Returns
    -------
    Markdown string suitable for posting as a PR comment
    """
    status_icon = "PASS" if result.passed else "FAIL"
    lines: list[str] = []

    lines.append(f"## BIM Quality Gate: {status_icon}")
    lines.append("")
    lines.append(f"**Grade: {result.grade}** | "
                 f"Score: {result.score:.1%} | "
                 f"Threshold: {result.threshold:.1%}")
    lines.append("")

    geo = result.metrics.get("geometric", {})
    lines.append("### Geometric Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Accuracy | {_pct(geo.get('accuracy'))} |")
    lines.append(f"| Completeness | {_pct(geo.get('completeness'))} |")
    lines.append(f"| Coverage ratio | {_pct(geo.get('coverage_ratio'))} |")
    lines.append(f"| Chamfer distance | {_fmt(geo.get('chamfer_distance'))} m^2 |")
    lines.append(f"| Mean pt-to-surf | {_fmt(geo.get('mean_point_to_surface'))} m |")
    lines.append(f"| Median pt-to-surf | {_fmt(geo.get('median_point_to_surface'))} m |")
    lines.append("")

    topo = result.metrics.get("topological", {})
    wall = topo.get("wall_connectivity", {})
    room = topo.get("room_closure", {})
    lines.append("### Topological Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Wall components | {wall.get('n_components', 'N/A')} |")
    lines.append(f"| Single component | {_yesno(wall.get('is_single_component'))} |")
    lines.append(f"| Watertight | {_yesno(room.get('is_watertight'))} |")
    lines.append(f"| Non-manifold edges | {room.get('n_non_manifold_edges', 'N/A')} |")
    lines.append("")

    params = result.metrics.get("params", {})
    lines.append("<details>")
    lines.append("<summary>Parameters</summary>")
    lines.append("")
    lines.append(f"- Distance threshold: {params.get('distance_threshold', 'N/A')} m")
    lines.append(f"- Mesh samples: {params.get('n_mesh_samples', 'N/A')}")
    lines.append(f"- Point cloud points: {params.get('n_pcd_points', 'N/A')}")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    return "\n".join(lines)


def format_github_annotation(result: QualityGateResult) -> str:
    """Format a quality gate result as GitHub Actions annotations.

    Parameters
    ----------
    result : QualityGateResult from QualityGate.check()

    Returns
    -------
    String of GitHub Actions annotation commands (::error / ::warning)
    """
    lines: list[str] = []

    if result.passed:
        lines.append(
            f"::notice::BIM Quality Gate PASSED - "
            f"Grade {result.grade}, Score {result.score:.1%}"
        )
    else:
        lines.append(
            f"::error::BIM Quality Gate FAILED - "
            f"Score {result.score:.1%} < threshold {result.threshold:.1%}"
        )

    geo = result.metrics.get("geometric", {})
    acc = geo.get("accuracy", 0.0)
    comp = geo.get("completeness", 0.0)

    if acc < result.threshold:
        lines.append(
            f"::warning::Accuracy is {acc:.1%}, below threshold {result.threshold:.1%}"
        )
    if comp < result.threshold:
        lines.append(
            f"::warning::Completeness is {comp:.1%}, below threshold {result.threshold:.1%}"
        )

    mean_dev = geo.get("mean_point_to_surface")
    if mean_dev is not None and mean_dev > 0.1:
        lines.append(
            f"::warning::Mean point-to-surface deviation is {mean_dev:.4f} m"
        )

    return "\n".join(lines)


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def _fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def _yesno(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "Yes" if value else "No"


def _compute_grade(score: float) -> str:
    if score >= 0.95:
        return "A (Excellent)"
    if score >= 0.85:
        return "B (Good)"
    if score >= 0.70:
        return "C (Acceptable)"
    return "D (Needs improvement)"
