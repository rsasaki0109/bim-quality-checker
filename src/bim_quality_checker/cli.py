"""CLI interface for BIM quality checking."""

from __future__ import annotations

import json
from pathlib import Path

import click

from bim_quality_checker.loader import load_ifc_surfaces, load_point_cloud
from bim_quality_checker.metrics import evaluate_all
from bim_quality_checker.report import generate_report


@click.group()
@click.version_option()
def main() -> None:
    """BIM Quality Checker - evaluate BIM models against point cloud data."""


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
def check(
    ifc_path: Path,
    pcd_path: Path,
    output: Path | None,
    distance_threshold: float,
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

    payload = json.dumps(results, indent=2)
    if output is not None:
        output.write_text(payload)
        click.echo(f"Results written to {output}")
    else:
        click.echo(payload)


@main.command()
@click.argument("results_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format", "-f",
    "fmt",
    type=click.Choice(["json", "text"]),
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


if __name__ == "__main__":
    main()
