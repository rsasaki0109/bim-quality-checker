"""Load IFC (BIM) files and point cloud data."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np
import open3d as o3d
import trimesh


def load_point_cloud(path: Path) -> o3d.geometry.PointCloud:
    """Load a point cloud from .ply / .pcd / .xyz / .las file.

    Parameters
    ----------
    path : path to point cloud file

    Returns
    -------
    open3d PointCloud
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".ply", ".pcd", ".xyz", ".xyzn", ".pts"):
        pcd = o3d.io.read_point_cloud(str(path))
    else:
        raise ValueError(f"Unsupported point cloud format: {suffix}")

    if pcd.is_empty():
        raise RuntimeError(f"Point cloud is empty: {path}")

    return pcd


def load_ifc_surfaces(path: Path) -> o3d.geometry.TriangleMesh:
    """Extract a triangle-mesh surface from an IFC file.

    Uses ifcopenshell geometry processing to tessellate all
    building-element shapes, then merges them into a single
    open3d TriangleMesh.

    Parameters
    ----------
    path : path to .ifc file

    Returns
    -------
    open3d TriangleMesh (merged from all IFC building elements)
    """
    path = Path(path)
    ifc_file = ifcopenshell.open(str(path))

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    combined = trimesh.Trimesh()

    products = ifc_file.by_type("IfcProduct")
    for product in products:
        if not product.Representation:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception:
            continue

        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = np.array(shape.geometry.faces, dtype=np.int32).reshape(-1, 3)

        if len(verts) == 0:
            continue

        part = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        combined = trimesh.util.concatenate([combined, part])

    if len(combined.vertices) == 0:
        raise RuntimeError(f"No geometry extracted from IFC file: {path}")

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(np.array(combined.vertices))
    mesh.triangles = o3d.utility.Vector3iVector(np.array(combined.faces))
    mesh.compute_vertex_normals()

    return mesh
