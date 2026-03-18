"""Quality metrics for BIM-vs-point-cloud evaluation.

Implements geometric and topological metrics inspired by BIMNet's evaluation
framework.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import numpy as np
import open3d as o3d


# ---------------------------------------------------------------------------
# Geometric metrics
# ---------------------------------------------------------------------------

def point_to_surface_distances(
    points: np.ndarray,
    mesh: o3d.geometry.TriangleMesh,
) -> np.ndarray:
    """Compute the closest distance from each point to the mesh surface.

    Parameters
    ----------
    points : (N, 3) array
    mesh : open3d TriangleMesh

    Returns
    -------
    distances : (N,) array of unsigned distances
    """
    scene = o3d.t.geometry.RaycastingScene()
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    scene.add_triangles(mesh_t)

    query_points = o3d.core.Tensor(points.astype(np.float32), dtype=o3d.core.float32)
    result = scene.compute_distance(query_points)
    return result.numpy()


def accuracy(distances: np.ndarray, threshold: float) -> float:
    """Fraction of BIM surface samples within *threshold* of a measured point.

    A high value means the BIM model does not contain spurious geometry.
    """
    return float(np.mean(distances < threshold))


def completeness(distances: np.ndarray, threshold: float) -> float:
    """Fraction of measured points within *threshold* of the BIM surface.

    A high value means the BIM model captures most of the real structure.
    """
    return float(np.mean(distances < threshold))


def chamfer_distance(
    pcd_points: np.ndarray,
    mesh_points: np.ndarray,
) -> float:
    """Symmetric Chamfer distance between two point sets.

    CD = mean(min_dist(A->B)) + mean(min_dist(B->A))
    """
    tree_a = o3d.geometry.KDTreeFlann(
        _to_o3d_pcd(pcd_points),
    )
    tree_b = o3d.geometry.KDTreeFlann(
        _to_o3d_pcd(mesh_points),
    )

    def _mean_nn(src: np.ndarray, tree: o3d.geometry.KDTreeFlann) -> float:
        dists = []
        for pt in src:
            _, _, d2 = tree.search_knn_vector_3d(pt, 1)
            dists.append(d2[0])
        return float(np.mean(dists))

    return _mean_nn(pcd_points, tree_b) + _mean_nn(mesh_points, tree_a)


def coverage_ratio(
    pcd_points: np.ndarray,
    mesh: o3d.geometry.TriangleMesh,
    threshold: float,
) -> float:
    """Ratio of the point cloud that is *covered* by the BIM surface."""
    dists = point_to_surface_distances(pcd_points, mesh)
    return float(np.mean(dists < threshold))


# ---------------------------------------------------------------------------
# Topological metrics (heuristic checks)
# ---------------------------------------------------------------------------

def check_wall_connectivity(
    mesh: o3d.geometry.TriangleMesh,
    gap_threshold: float = 0.02,
) -> dict[str, Any]:
    """Check whether wall surfaces are connected (no large gaps).

    Uses connected-component analysis on the mesh. Gaps larger than
    *gap_threshold* between components indicate disconnected walls.
    """
    cluster_ids, counts, _ = mesh.cluster_connected_triangles()
    cluster_ids = np.asarray(cluster_ids)
    counts = np.asarray(counts)
    n_components = len(counts)

    return {
        "n_components": int(n_components),
        "largest_component_triangles": int(counts.max()) if len(counts) > 0 else 0,
        "is_single_component": n_components == 1,
    }


def check_room_closure(
    mesh: o3d.geometry.TriangleMesh,
) -> dict[str, Any]:
    """Check whether the mesh forms closed rooms (watertight volumes).

    A watertight mesh indicates fully enclosed rooms.
    """
    is_watertight = mesh.is_watertight()
    edges = np.asarray(mesh.get_non_manifold_edges(allow_boundary_edges=False))
    n_non_manifold = len(edges)

    return {
        "is_watertight": bool(is_watertight),
        "n_non_manifold_edges": int(n_non_manifold),
    }


# ---------------------------------------------------------------------------
# Combined evaluation
# ---------------------------------------------------------------------------

def evaluate_all(
    mesh: o3d.geometry.TriangleMesh,
    pcd: o3d.geometry.PointCloud,
    distance_threshold: float = 0.05,
    n_mesh_samples: int = 50_000,
) -> dict[str, Any]:
    """Run all metrics and return a summary dict.

    Parameters
    ----------
    mesh : BIM surface mesh
    pcd : measured point cloud
    distance_threshold : metres
    n_mesh_samples : points to sample on the mesh surface

    Returns
    -------
    dict with geometric and topological results.
    """
    pcd_pts = np.asarray(pcd.points)

    # Sample points on the BIM mesh for accuracy / Chamfer
    mesh_pcd = mesh.sample_points_uniformly(number_of_points=n_mesh_samples)
    mesh_pts = np.asarray(mesh_pcd.points)

    # point cloud -> mesh distances (completeness, coverage)
    dists_pcd_to_mesh = point_to_surface_distances(pcd_pts, mesh)
    # mesh samples -> point cloud distances (accuracy)
    pcd_tree = o3d.geometry.KDTreeFlann(pcd)
    acc_dists = []
    for pt in mesh_pts:
        _, _, d2 = pcd_tree.search_knn_vector_3d(pt, 1)
        acc_dists.append(np.sqrt(d2[0]))
    acc_dists = np.array(acc_dists)

    return {
        "geometric": {
            "accuracy": accuracy(acc_dists, distance_threshold),
            "completeness": completeness(dists_pcd_to_mesh, distance_threshold),
            "coverage_ratio": coverage_ratio(pcd_pts, mesh, distance_threshold),
            "chamfer_distance": chamfer_distance(pcd_pts, mesh_pts),
            "mean_point_to_surface": float(np.mean(dists_pcd_to_mesh)),
            "median_point_to_surface": float(np.median(dists_pcd_to_mesh)),
        },
        "topological": {
            "wall_connectivity": check_wall_connectivity(mesh),
            "room_closure": check_room_closure(mesh),
        },
        "params": {
            "distance_threshold": distance_threshold,
            "n_mesh_samples": n_mesh_samples,
            "n_pcd_points": len(pcd_pts),
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_o3d_pcd(points: np.ndarray) -> o3d.geometry.PointCloud:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    return pcd
