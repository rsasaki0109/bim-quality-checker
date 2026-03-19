"""Deviation map computation and export.

Computes per-point signed distances between a mesh and a point cloud,
and exports coloured point clouds for deviation visualisation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d


def compute_deviation_map(
    mesh: o3d.geometry.TriangleMesh,
    point_cloud: o3d.geometry.PointCloud,
) -> np.ndarray:
    """Compute per-point unsigned distance from each point to the mesh surface.

    Parameters
    ----------
    mesh : BIM surface mesh
    point_cloud : measured point cloud

    Returns
    -------
    deviations : (N,) array of distances (metres)
    """
    scene = o3d.t.geometry.RaycastingScene()
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    scene.add_triangles(mesh_t)

    pts = np.asarray(point_cloud.points).astype(np.float32)
    query = o3d.core.Tensor(pts, dtype=o3d.core.float32)
    distances = scene.compute_distance(query).numpy()

    return distances


def deviation_colors(
    deviations: np.ndarray,
    vmin: float = 0.0,
    vmax: float | None = None,
) -> np.ndarray:
    """Map deviation values to RGB colours (blue=close, red=far).

    Parameters
    ----------
    deviations : (N,) unsigned distances
    vmin : value mapped to blue
    vmax : value mapped to red; defaults to 95th-percentile of deviations

    Returns
    -------
    colors : (N, 3) array of RGB values in [0, 1]
    """
    if vmax is None:
        vmax = float(np.percentile(deviations, 95))
    if vmax <= vmin:
        vmax = vmin + 1e-6

    t = np.clip((deviations - vmin) / (vmax - vmin), 0.0, 1.0)

    colors = np.zeros((len(t), 3), dtype=np.float64)
    # blue (0,0,1) -> green (0,1,0) -> red (1,0,0)
    # First half: blue -> green
    mask_low = t <= 0.5
    t_low = t[mask_low] * 2.0  # 0..1
    colors[mask_low, 0] = 0.0
    colors[mask_low, 1] = t_low
    colors[mask_low, 2] = 1.0 - t_low

    # Second half: green -> red
    mask_high = t > 0.5
    t_high = (t[mask_high] - 0.5) * 2.0  # 0..1
    colors[mask_high, 0] = t_high
    colors[mask_high, 1] = 1.0 - t_high
    colors[mask_high, 2] = 0.0

    return colors


def export_colored_pointcloud(
    point_cloud: o3d.geometry.PointCloud,
    deviations: np.ndarray,
    output_path: Path,
    vmin: float = 0.0,
    vmax: float | None = None,
) -> Path:
    """Export a point cloud coloured by deviation to a PLY file.

    Parameters
    ----------
    point_cloud : original point cloud
    deviations : (N,) deviation array from ``compute_deviation_map``
    output_path : destination path (``.ply``)
    vmin : deviation value mapped to blue
    vmax : deviation value mapped to red (default: 95th percentile)

    Returns
    -------
    The output path written to
    """
    output_path = Path(output_path)
    colors = deviation_colors(deviations, vmin=vmin, vmax=vmax)

    colored_pcd = o3d.geometry.PointCloud()
    colored_pcd.points = o3d.utility.Vector3dVector(np.asarray(point_cloud.points))
    colored_pcd.colors = o3d.utility.Vector3dVector(colors)

    o3d.io.write_point_cloud(str(output_path), colored_pcd)
    return output_path
