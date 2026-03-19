# BIM Quality Checker

[![CI](https://github.com/rsasaki0109/bim-quality-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/rsasaki0109/bim-quality-checker/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Evaluate BIM model quality by comparing generated IFC models against point cloud measurements. Implements geometric and topological metrics inspired by BIMNet's evaluation framework.

## Metrics

### Geometric Metrics

| Metric | Description |
|---|---|
| **Accuracy** | Fraction of BIM surface samples within a distance threshold of a measured point. A high value means the BIM model does not contain spurious geometry. |
| **Completeness** | Fraction of measured points within a distance threshold of the BIM surface. A high value means the BIM model captures most of the real structure. |
| **Chamfer Distance** | Symmetric Chamfer distance (`CD = mean(min_dist(A->B)) + mean(min_dist(B->A))`). Lower values indicate better geometric agreement between the BIM model and the point cloud. |
| **Coverage Ratio** | Ratio of point cloud points that lie within the distance threshold of the BIM surface. |
| **Mean / Median Point-to-Surface** | Statistical summaries of the unsigned distance from each point cloud point to the nearest BIM surface. |

### Topological Metrics

| Metric | Description |
|---|---|
| **Wall Connectivity** | Connected-component analysis on the mesh. A single component indicates all walls are properly connected. Multiple components suggest gaps or disconnections. |
| **Room Closure** | Watertight check on the mesh. A watertight mesh indicates fully enclosed rooms. Non-manifold edges are also reported. |

### Grading System

An overall grade is computed from the average of accuracy and completeness:

| Grade | Average (Accuracy + Completeness) / 2 |
|---|---|
| **A** (Excellent) | >= 95% |
| **B** (Good) | >= 85% |
| **C** (Acceptable) | >= 70% |
| **D** (Needs improvement) | < 70% |

## Installation

```bash
pip install -e .
```

For development (includes pytest and ruff):

```bash
pip install -e ".[dev]"
```

## Usage

### Evaluate a BIM model

```bash
bim-quality-checker check model.ifc scan.ply -o results.json --distance-threshold 0.05
```

### Generate a human-readable report

```bash
bim-quality-checker report results.json
bim-quality-checker report results.json -f json -o report.json
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT
