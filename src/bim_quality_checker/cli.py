"""CLI interface for BIM quality checking."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from bim_quality_checker.loader import load_ifc_surfaces, load_point_cloud
from bim_quality_checker.metrics import evaluate_all
from bim_quality_checker.report import generate_report


@click.group()
@click.version_option()
def main() -> None:
    """BIM Quality Checker - evaluate BIM models against point cloud data.

    Works with any IFC file from any BIM software (Revit, ArchiCAD, Tekla,
    etc.) against any point cloud scan.
    """


@main.command()
@click.argument("ifc_path", type=click.Path(exists=True, path_type=Path))
@click.argument("pcd_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON path for results. Prints to stdout if omitted.",
)
@click.option(
    "--distance-threshold",
    type=float,
    default=0.05,
    show_default=True,
    help="Distance threshold (metres) for accuracy/completeness evaluation.",
)
@click.option(
    "--threshold",
    type=float,
    default=None,
    help="Pass/fail threshold for average of accuracy and completeness (0-1). "
         "E.g. --threshold 0.85 means the model must score >= 85%%.",
)
def check(
    ifc_path: Path,
    pcd_path: Path,
    output: Path | None,
    distance_threshold: float,
    threshold: float | None,
) -> None:
    """Evaluate a BIM model against a point cloud.

    IFC_PATH is the path to the IFC file (BIM model).
    PCD_PATH is the path to the point cloud file (.ply / .pcd / .xyz).
    """
    click.echo(f"Loading IFC: {ifc_path}")
    bim_mesh = load_ifc_surfaces(ifc_path)

    click.echo(f"Loading point cloud: {pcd_path}")
    pcd = load_point_cloud(pcd_path)

    click.echo("Computing quality metrics ...")
    results = evaluate_all(bim_mesh, pcd, distance_threshold=distance_threshold)

    # Pass/fail determination
    if threshold is not None:
        geo = results.get("geometric", {})
        acc = geo.get("accuracy", 0.0)
        comp = geo.get("completeness", 0.0)
        avg = (acc + comp) / 2.0
        passed = avg >= threshold
        results["pass_fail"] = {
            "threshold": threshold,
            "score": round(avg, 4),
            "passed": passed,
        }

    payload = json.dumps(results, indent=2)
    if output is not None:
        output.write_text(payload)
        click.echo(f"Results written to {output}")
    else:
        click.echo(payload)

    # Exit with non-zero if pass/fail was requested and failed
    if threshold is not None and not results["pass_fail"]["passed"]:
        click.echo(
            f"FAIL: score {results['pass_fail']['score']:.2%} "
            f"< threshold {threshold:.2%}",
            err=True,
        )
        sys.exit(1)


@main.command()
@click.argument("results_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format", "-f",
    "fmt",
    type=click.Choice(["json", "text", "markdown"]),
    default="text",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Prints to stdout if omitted.",
)
def report(results_path: Path, fmt: str, output: Path | None) -> None:
    """Generate a quality report from evaluation results.

    RESULTS_PATH is the JSON file produced by the `check` command.
    """
    results = json.loads(results_path.read_text())
    text = generate_report(results, fmt=fmt)

    if output is not None:
        output.write_text(text)
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)


@main.command()
@click.argument("ifc_path", type=click.Path(exists=True, path_type=Path))
@click.argument("pcd_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON path for per-element results.",
)
@click.option(
    "--distance-threshold",
    type=float,
    default=0.05,
    show_default=True,
    help="Distance threshold (metres) for per-element evaluation.",
)
@click.option(
    "--n-worst",
    type=int,
    default=10,
    show_default=True,
    help="Number of worst elements to highlight.",
)
def elements(
    ifc_path: Path,
    pcd_path: Path,
    output: Path | None,
    distance_threshold: float,
    n_worst: int,
) -> None:
    """Per-element quality breakdown of a BIM model.

    Analyses each IFC building element individually and reports which
    elements have the worst quality scores.
    """
    from bim_quality_checker.element_checker import ElementChecker

    click.echo(f"Loading point cloud: {pcd_path}")
    pcd = load_point_cloud(pcd_path)

    click.echo(f"Analysing elements in: {ifc_path}")
    checker = ElementChecker(
        distance_threshold=distance_threshold,
        n_worst=n_worst,
    )
    report = checker.check_ifc(ifc_path, pcd)

    payload = json.dumps(report.to_dict(), indent=2)
    if output is not None:
        output.write_text(payload)
        click.echo(f"Element results written to {output}")
    else:
        click.echo(payload)


@main.command()
@click.argument("ifc_path", type=click.Path(exists=True, path_type=Path))
@click.argument("pcd_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output PLY path for deviation-coloured point cloud.",
)
@click.option(
    "--vmax",
    type=float,
    default=None,
    help="Max deviation (metres) mapped to red. Defaults to 95th percentile.",
)
def deviation(
    ifc_path: Path,
    pcd_path: Path,
    output: Path,
    vmax: float | None,
) -> None:
    """Export a deviation-coloured point cloud.

    Computes per-point distance from the point cloud to the BIM surface
    and exports a PLY file coloured blue (close) to red (far).
    """
    from bim_quality_checker.deviation_map import (
        compute_deviation_map,
        export_colored_pointcloud,
    )

    click.echo(f"Loading IFC: {ifc_path}")
    bim_mesh = load_ifc_surfaces(ifc_path)

    click.echo(f"Loading point cloud: {pcd_path}")
    pcd = load_point_cloud(pcd_path)

    click.echo("Computing deviation map ...")
    devs = compute_deviation_map(bim_mesh, pcd)

    click.echo(f"Exporting coloured point cloud to {output}")
    export_colored_pointcloud(pcd, devs, output, vmax=vmax)
    click.echo("Done.")


if __name__ == "__main__":
    main()
