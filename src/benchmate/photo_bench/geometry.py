"""Board-plane registration, explicitly independent from electrical addresses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np


def _points(value):
    points = np.asarray(value, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError('Expected finite Nx2 points')
    return points


def _normalize(points):
    center = points.mean(axis=0)
    rms = np.sqrt(np.mean(np.sum((points - center) ** 2, axis=1)))
    if rms < 1e-10:
        raise ValueError('Coincident calibration points')
    scale = np.sqrt(2) / rms
    transform = np.array([[scale, 0, -scale * center[0]], [0, scale, -scale * center[1]], [0, 0, 1]])
    return (points - center) * scale, transform


def project(matrix, points):
    points = _points(points)
    homography = np.asarray(matrix, dtype=float)
    if homography.shape != (3, 3) or not np.isfinite(homography).all():
        raise ValueError('Expected finite 3x3 homography')
    homogeneous = np.column_stack([points, np.ones(len(points))]) @ homography.T
    if np.any(np.abs(homogeneous[:, 2]) < 1e-10):
        raise ValueError('Projection crosses the horizon')
    return homogeneous[:, :2] / homogeneous[:, 2:]


def fit_homography(grid, image):
    """Normalized DLT. The caller must keep validation points out of this fit."""
    source, target = _points(grid), _points(image)
    if len(source) != len(target) or len(source) < 4:
        raise ValueError('At least four paired points required')
    if len(np.unique(source, axis=0)) != len(source) or len(np.unique(target, axis=0)) != len(target):
        raise ValueError('Duplicate calibration points')
    source_n, source_t = _normalize(source)
    target_n, target_t = _normalize(target)
    rows = []
    for (x, y), (u, v) in zip(source_n, target_n):
        rows.extend([[-x, -y, -1, 0, 0, 0, u * x, u * y, u],
                     [0, 0, 0, -x, -y, -1, v * x, v * y, v]])
    matrix = np.asarray(rows)
    if np.linalg.matrix_rank(matrix) < 8:
        raise ValueError('Degenerate calibration geometry')
    _, _, right = np.linalg.svd(matrix, full_matrices=True)
    result = np.linalg.inv(target_t) @ right[-1].reshape(3, 3) @ source_t
    result /= np.linalg.norm(result)
    if abs(np.linalg.det(result)) < 1e-14:
        raise ValueError('Singular homography')
    return result


def local_pitch(matrix, points):
    points = _points(points)
    centre = project(matrix, points)
    horizontal = np.linalg.norm(project(matrix, points + [1, 0]) - centre, axis=1)
    vertical = np.linalg.norm(project(matrix, points + [0, 1]) - centre, axis=1)
    pitch = np.minimum(horizontal, vertical)
    if np.any(pitch < 1e-6):
        raise ValueError('Degenerate projected pitch')
    return pitch


def nearest_grid_point(matrix, pixel, columns, rows=5, tolerance_pitch=.25):
    """Return a candidate grid index, never proof of insertion or connectivity."""
    observed = _points([pixel])[0]
    grid = project(np.linalg.inv(np.asarray(matrix)), [observed])[0]
    candidate = np.rint(grid).astype(int)
    if not (0 <= candidate[0] < columns and 0 <= candidate[1] < rows):
        return None
    projected = project(matrix, [candidate])[0]
    error = float(np.linalg.norm(projected - observed) / local_pitch(matrix, [candidate])[0])
    if error > tolerance_pitch:
        return None
    return {'column_from_right': int(candidate[0]), 'row_from_image_top': int(candidate[1]),
            'distance_pitch': error, 'electrical_address': None, 'occupancy': 'unknown'}


def evaluate_design(design: dict, master_sha256: str, image_size: tuple[int, int]) -> dict:
    if design['master_sha256'] != master_sha256:
        raise ValueError('Calibration belongs to a different oriented master')
    result = {'schema': 'benchmate.photo_grid.v1', 'master_sha256': master_sha256,
              'electrical_address_mapping': 'unconfirmed', 'all_occupancy': 'unknown',
              'source': 'one historical development photo; manually reviewed anchors and check labels',
              'strips': {}, 'threshold_p95_pitch': design['threshold_p95_pitch']}
    for name, strip in design['strips'].items():
        fit, check = strip['fit'], strip['check']
        if len(check) < design['minimum_checks_per_strip']:
            raise ValueError('Insufficient withheld checks')
        fit_ids = {tuple(p['grid']) for p in fit}
        check_ids = [tuple(p['grid']) for p in check]
        if fit_ids.intersection(check_ids) or len(set(check_ids)) != len(check_ids):
            raise ValueError('Fit/check leakage or duplicate checks')
        matrix = fit_homography([p['grid'] for p in fit], [p['image_xy'] for p in fit])
        predicted = project(matrix, [p['grid'] for p in check])
        measured = _points([p['image_xy'] for p in check])
        residual = np.linalg.norm(predicted - measured, axis=1)
        normalized = residual / local_pitch(matrix, [p['grid'] for p in check])
        p95 = float(np.percentile(normalized, 95))
        # Only the anchor rectangle is presented as calibrated. No extrapolation
        # from a visible right-hand patch to occluded/off-image contacts.
        bounds = np.array([p['grid'] for p in fit])
        lower, upper = bounds.min(axis=0), bounds.max(axis=0)
        grid = [[column, row] for column in range(strip['columns']) for row in range(strip['rows'])]
        projected = project(matrix, grid)
        holes = []
        for index, point in zip(grid, projected):
            inside = bool(np.all(np.asarray(index) >= lower) and np.all(np.asarray(index) <= upper))
            holes.append({'grid': index, 'image_xy': point.tolist(),
                          'in_image': bool(0 <= point[0] < image_size[0] and 0 <= point[1] < image_size[1]),
                          'within_anchor_domain': inside, 'occupancy': 'unknown', 'electrical_address': None})
        result['strips'][name] = {'homography': matrix.tolist(), 'fit': fit,
            'checks': [{**p, 'predicted_xy': predicted[i].tolist(), 'error_px': float(residual[i]),
                        'error_pitch': float(normalized[i])} for i, p in enumerate(check)],
            'rms_px': float(np.sqrt(np.mean(residual ** 2))), 'p95_error_px': float(np.percentile(residual, 95)),
            'p95_error_pitch': p95, 'max_error_pitch': float(normalized.max()),
            'geometry_gate_passed': p95 <= design['threshold_p95_pitch'], 'holes': holes}
    result['geometry_gate_passed'] = all(s['geometry_gate_passed'] for s in result['strips'].values())
    return result


def evaluate_files(design_path: Path, master_path: Path, output_path: Path):
    from .media import verify_local_master
    if output_path.exists():
        raise FileExistsError('Preserve the first geometry result')
    raw = design_path.read_bytes()
    design = json.loads(raw)
    verified = verify_local_master(master_path)
    result = evaluate_design(design, verified['sha256'], (verified['width'], verified['height']))
    result['design_sha256'] = hashlib.sha256(raw).hexdigest()
    output_path.write_text(json.dumps(result, indent=2) + '\n')
    return result
