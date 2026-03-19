# BIM Quality Checker

Evaluate BIM model quality by comparing generated IFC models against point cloud measurements. Implements geometric and topological metrics inspired by BIMNet's evaluation framework.

## Metrics

**Geometric** -- point-to-surface distance, accuracy, completeness, coverage ratio, Chamfer distance.

**Topological** -- wall connectivity (connected-component analysis), room closure (watertight check).

## Installation

```bash
pip install -e .
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

## License

MIT
