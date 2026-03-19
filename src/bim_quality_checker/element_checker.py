"""Per-element quality analysis for IFC models.

Categorizes and evaluates individual IFC building elements (IfcWall,
IfcSlab, IfcDoor, IfcWindow, etc.) against a point cloud scan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.geom
import numpy as np
import open3d as o3d
import trimesh

from bim_quality_checker.metrics import point_to_surface_distances


@dataclass
class ElementResult:
    """Quality metrics for a single IFC element."""

    global_id: str
    ifc_type: str
    name: str
    n_vertices: int
    n_faces: int
    accuracy: float
    completeness: float
    mean_deviation: float
    max_deviation: float
    passed: bool


@dataclass
class ElementReport:
    """Aggregated per-element analysis results."""

    elements: list[ElementResult] = field(default_factory=list)
    by_type: dict[str, list[ElementResult]] = field(default_factory=dict)
    worst_elements: list[ElementResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {
            "n_elements": len(self.elements),
            "by_type_summary": {
                ifc_type: {
                    "count": len(elems),
                    "mean_accuracy": float(np.mean([e.accuracy for e in elems])),
                    "mean_completeness": float(np.mean([e.completeness for e in elems])),
                }
                for ifc_type, elems in self.by_type.items()
            },
            "worst_elements": [
                {
                    "global_id": e.global_id,
                    "ifc_type": e.ifc_type,
                    "name": e.name,
                    "accuracy": e.accuracy,
                    "completeness": e.completeness,
                    "mean_deviation": e.mean_deviation,
                    "max_deviation": e.max_deviation,
                    "passed": e.passed,
                }
                for e in self.worst_elements
            ],
            "elements": [
                {
                    "global_id": e.global_id,
                    "ifc_type": e.ifc_type,
                    "name": e.name,
                    "n_vertices": e.n_vertices,
                    "n_faces": e.n_faces,
                    "accuracy": e.accuracy,
                    "completeness": e.completeness,
                    "mean_deviation": e.mean_deviation,
                    "max_deviation": e.max_deviation,
                    "passed": e.passed,
                }
                for e in self.elements
            ],
        }


class ElementChecker:
    """Per-element quality checker for IFC files."""

    # IFC types to analyse individually
    ELEMENT_TYPES: tuple[str, ...] = (
        "IfcWall",
        "IfcWallStandardCase",
        "IfcSlab",
        "IfcDoor",
        "IfcWindow",
        "IfcColumn",
        "IfcBeam",
        "IfcRoof",
        "IfcStair",
        "IfcRailing",
        "IfcCurtainWall",
        "IfcPlate",
        "IfcMember",
        "IfcFooting",
        "IfcPile",
        "IfcBuildingElementProxy",
    )

    def __init__(
        self,
        distance_threshold: float = 0.05,
        n_worst: int = 10,
        n_mesh_samples: int = 2000,
    ) -> None:
        self.distance_threshold = distance_threshold
        self.n_worst = n_worst
        self.n_mesh_samples = n_mesh_samples

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_element(
        self,
        element_mesh: o3d.geometry.TriangleMesh,
        point_cloud: o3d.geometry.PointCloud,
        element_type: str = "Unknown",
        global_id: str = "",
        name: str = "",
    ) -> ElementResult:
        """Evaluate a single element mesh against a point cloud.

        Parameters
        ----------
        element_mesh : triangle mesh for one IFC element
        point_cloud : reference point cloud
        element_type : IFC class name (e.g. ``"IfcWall"``)
        global_id : IFC GlobalId
        name : human-readable element name

        Returns
        -------
        ElementResult with per-element quality metrics
        """
        n_verts = len(np.asarray(element_mesh.vertices))
        n_faces = len(np.asarray(element_mesh.triangles))

        if n_verts == 0 or n_faces == 0:
            return ElementResult(
                global_id=global_id,
                ifc_type=element_type,
                name=name,
                n_vertices=n_verts,
                n_faces=n_faces,
                accuracy=0.0,
                completeness=0.0,
                mean_deviation=float("inf"),
                max_deviation=float("inf"),
                passed=False,
            )

        pcd_pts = np.asarray(point_cloud.points)

        # --- Completeness: pcd -> element mesh ---
        dists_pcd = point_to_surface_distances(pcd_pts, element_mesh)
        nearby_mask = dists_pcd < self.distance_threshold * 10
        if nearby_mask.sum() > 0:
            nearby_dists = dists_pcd[nearby_mask]
            elem_completeness = float(np.mean(nearby_dists < self.distance_threshold))
            mean_dev = float(np.mean(nearby_dists))
            max_dev = float(np.max(nearby_dists))
        else:
            elem_completeness = 0.0
            mean_dev = float("inf")
            max_dev = float("inf")

        # --- Accuracy: mesh samples -> pcd ---
        n_samples = min(self.n_mesh_samples, max(n_faces * 3, 100))
        mesh_pcd = element_mesh.sample_points_uniformly(number_of_points=n_samples)
        mesh_pts = np.asarray(mesh_pcd.points)

        pcd_tree = o3d.geometry.KDTreeFlann(point_cloud)
        acc_dists: list[float] = []
        for pt in mesh_pts:
            _, _, d2 = pcd_tree.search_knn_vector_3d(pt, 1)
            acc_dists.append(np.sqrt(d2[0]))
        acc_arr = np.array(acc_dists)
        elem_accuracy = float(np.mean(acc_arr < self.distance_threshold))

        passed = (
            elem_accuracy >= 0.7
            and elem_completeness >= 0.7
            and mean_dev < self.distance_threshold * 3
        )

        return ElementResult(
            global_id=global_id,
            ifc_type=element_type,
            name=name,
            n_vertices=n_verts,
            n_faces=n_faces,
            accuracy=elem_accuracy,
            completeness=elem_completeness,
            mean_deviation=mean_dev,
            max_deviation=max_dev,
            passed=passed,
        )

    def check_ifc(
        self,
        ifc_path: Path,
        point_cloud: o3d.geometry.PointCloud,
    ) -> ElementReport:
        """Extract elements from an IFC file and evaluate each one.

        Parameters
        ----------
        ifc_path : path to ``.ifc`` file
        point_cloud : reference point cloud

        Returns
        -------
        ElementReport with per-element results grouped by type
        """
        ifc_file = ifcopenshell.open(str(ifc_path))
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        results: list[ElementResult] = []

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

            mesh = o3d.geometry.TriangleMesh()
            mesh.vertices = o3d.utility.Vector3dVector(verts)
            mesh.triangles = o3d.utility.Vector3iVector(faces)
            mesh.compute_vertex_normals()

            ifc_type = product.is_a()
            global_id = getattr(product, "GlobalId", "")
            name = getattr(product, "Name", "") or ""

            result = self.check_element(
                mesh, point_cloud, ifc_type, global_id, name,
            )
            results.append(result)

        # Group by type
        by_type: dict[str, list[ElementResult]] = {}
        for r in results:
            by_type.setdefault(r.ifc_type, []).append(r)

        # Worst elements by mean_deviation (descending)
        sorted_by_dev = sorted(
            results,
            key=lambda e: e.mean_deviation if np.isfinite(e.mean_deviation) else 1e9,
            reverse=True,
        )
        worst = sorted_by_dev[: self.n_worst]

        return ElementReport(elements=results, by_type=by_type, worst_elements=worst)
