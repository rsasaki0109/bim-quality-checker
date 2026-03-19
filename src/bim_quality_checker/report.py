"""Generate quality reports from evaluation results."""

from __future__ import annotations

import json
from typing import Any


def generate_report(results: dict[str, Any], fmt: str = "text") -> str:
    """Generate a formatted quality report.

    Parameters
    ----------
    results : evaluation dict produced by ``metrics.evaluate_all``
    fmt : ``"json"``, ``"text"``, or ``"markdown"``

    Returns
    -------
    Formatted report string
    """
    if fmt == "json":
        return json.dumps(results, indent=2)
    if fmt == "markdown":
        return _render_markdown(results)
    return _render_text(results)


def _render_text(results: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  BIM Quality Report")
    lines.append("=" * 60)
    lines.append("")

    # --- Geometric ---
    geo = results.get("geometric", {})
    lines.append("Geometric Metrics")
    lines.append("-" * 40)
    lines.append(f"  Accuracy           : {_pct(geo.get('accuracy'))}")
    lines.append(f"  Completeness       : {_pct(geo.get('completeness'))}")
    lines.append(f"  Coverage ratio     : {_pct(geo.get('coverage_ratio'))}")
    lines.append(f"  Chamfer distance   : {_fmt(geo.get('chamfer_distance'))} m^2")
    lines.append(f"  Mean  pt-to-surf   : {_fmt(geo.get('mean_point_to_surface'))} m")
    lines.append(f"  Median pt-to-surf  : {_fmt(geo.get('median_point_to_surface'))} m")
    lines.append("")

    # --- Topological ---
    topo = results.get("topological", {})
    wall = topo.get("wall_connectivity", {})
    room = topo.get("room_closure", {})
    lines.append("Topological Metrics")
    lines.append("-" * 40)
    lines.append(f"  Wall components    : {wall.get('n_components', 'N/A')}")
    lines.append(f"  Single component   : {_yesno(wall.get('is_single_component'))}")
    lines.append(f"  Watertight (closed): {_yesno(room.get('is_watertight'))}")
    lines.append(f"  Non-manifold edges : {room.get('n_non_manifold_edges', 'N/A')}")
    lines.append("")

    # --- Pass/Fail ---
    pf = results.get("pass_fail")
    if pf is not None:
        lines.append("Pass/Fail")
        lines.append("-" * 40)
        status = "PASS" if pf.get("passed") else "FAIL"
        lines.append(f"  Status             : {status}")
        lines.append(f"  Score              : {_pct(pf.get('score'))}")
        lines.append(f"  Threshold          : {_pct(pf.get('threshold'))}")
        lines.append("")

    # --- Per-element breakdown ---
    elem = results.get("element_breakdown")
    if elem is not None:
        lines.append("Per-Element Breakdown")
        lines.append("-" * 40)
        by_type = elem.get("by_type_summary", {})
        for ifc_type, summary in by_type.items():
            lines.append(
                f"  {ifc_type:30s}  count={summary['count']:3d}  "
                f"acc={_pct(summary['mean_accuracy'])}  "
                f"comp={_pct(summary['mean_completeness'])}"
            )
        worst = elem.get("worst_elements", [])
        if worst:
            lines.append("")
            lines.append("  Worst elements:")
            for w in worst:
                lines.append(
                    f"    {w.get('ifc_type', '?'):25s}  "
                    f"id={w.get('global_id', '?')[:12]:12s}  "
                    f"acc={_pct(w.get('accuracy'))}  "
                    f"dev={_fmt(w.get('mean_deviation'))} m"
                )
        lines.append("")

    # --- Overall verdict ---
    lines.append("Overall Verdict")
    lines.append("-" * 40)
    grade = _grade(geo)
    lines.append(f"  Grade: {grade}")
    lines.append("")

    # --- Params ---
    params = results.get("params", {})
    lines.append("Parameters")
    lines.append("-" * 40)
    lines.append(f"  Distance threshold : {params.get('distance_threshold', 'N/A')} m")
    lines.append(f"  Mesh samples       : {params.get('n_mesh_samples', 'N/A')}")
    lines.append(f"  Point cloud points : {params.get('n_pcd_points', 'N/A')}")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def _render_markdown(results: dict[str, Any]) -> str:
    """Render the report as Markdown."""
    lines: list[str] = []
    lines.append("# BIM Quality Report")
    lines.append("")

    # --- Geometric ---
    geo = results.get("geometric", {})
    lines.append("## Geometric Metrics")
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

    # --- Topological ---
    topo = results.get("topological", {})
    wall = topo.get("wall_connectivity", {})
    room = topo.get("room_closure", {})
    lines.append("## Topological Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Wall components | {wall.get('n_components', 'N/A')} |")
    lines.append(f"| Single component | {_yesno(wall.get('is_single_component'))} |")
    lines.append(f"| Watertight (closed) | {_yesno(room.get('is_watertight'))} |")
    lines.append(f"| Non-manifold edges | {room.get('n_non_manifold_edges', 'N/A')} |")
    lines.append("")

    # --- Pass/Fail ---
    pf = results.get("pass_fail")
    if pf is not None:
        status = "**PASS**" if pf.get("passed") else "**FAIL**"
        lines.append("## Pass/Fail")
        lines.append("")
        lines.append(f"- Status: {status}")
        lines.append(f"- Score: {_pct(pf.get('score'))}")
        lines.append(f"- Threshold: {_pct(pf.get('threshold'))}")
        lines.append("")

    # --- Per-element breakdown ---
    elem = results.get("element_breakdown")
    if elem is not None:
        lines.append("## Per-Element Breakdown")
        lines.append("")
        by_type = elem.get("by_type_summary", {})
        if by_type:
            lines.append("| IFC Type | Count | Accuracy | Completeness |")
            lines.append("|---|---|---|---|")
            for ifc_type, summary in by_type.items():
                lines.append(
                    f"| {ifc_type} | {summary['count']} "
                    f"| {_pct(summary['mean_accuracy'])} "
                    f"| {_pct(summary['mean_completeness'])} |"
                )
            lines.append("")

        worst = elem.get("worst_elements", [])
        if worst:
            lines.append("### Worst Elements")
            lines.append("")
            lines.append("| Type | GlobalId | Accuracy | Mean Deviation |")
            lines.append("|---|---|---|---|")
            for w in worst:
                lines.append(
                    f"| {w.get('ifc_type', '?')} "
                    f"| `{w.get('global_id', '?')}` "
                    f"| {_pct(w.get('accuracy'))} "
                    f"| {_fmt(w.get('mean_deviation'))} m |"
                )
            lines.append("")

    # --- Grade ---
    lines.append("## Overall Verdict")
    lines.append("")
    grade = _grade(geo)
    lines.append(f"**Grade: {grade}**")
    lines.append("")

    # --- Params ---
    params = results.get("params", {})
    lines.append("## Parameters")
    lines.append("")
    lines.append(f"- Distance threshold: {params.get('distance_threshold', 'N/A')} m")
    lines.append(f"- Mesh samples: {params.get('n_mesh_samples', 'N/A')}")
    lines.append(f"- Point cloud points: {params.get('n_pcd_points', 'N/A')}")
    lines.append("")

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


def _grade(geo: dict[str, Any]) -> str:
    acc = geo.get("accuracy")
    comp = geo.get("completeness")
    if acc is None or comp is None:
        return "N/A"
    avg = (acc + comp) / 2
    if avg >= 0.95:
        return "A  (Excellent)"
    if avg >= 0.85:
        return "B  (Good)"
    if avg >= 0.70:
        return "C  (Acceptable)"
    return "D  (Needs improvement)"
