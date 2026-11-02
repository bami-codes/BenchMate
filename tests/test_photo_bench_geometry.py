import copy
import numpy as np
import pytest
from benchmate.photo_bench.geometry import fit_homography, project, local_pitch, nearest_grid_point, evaluate_design


H = np.array([[42, 4, 200], [-2, 40, 300], [.0003, -.0002, 1.]])


def design():
    fit = [[0, 0], [29, 0], [0, 4], [29, 4]]
    checks = [[c, r] for c in [2, 8, 17, 25] for r in range(5)]
    return {'master_sha256': 'image-one', 'minimum_checks_per_strip': 20, 'threshold_p95_pitch': .25,
            'strips': {'upper': {'columns': 63, 'rows': 5,
                'fit': [{'grid': p, 'image_xy': q.tolist()} for p, q in zip(fit, project(H, fit))],
                'check': [{'grid': p, 'image_xy': q.tolist()} for p, q in zip(checks, project(H, checks))]}}}


def test_project_and_inverse_round_trip():
    points = [[0, 0], [25.5, 3.3], [60, 4]]
    assert project(np.linalg.inv(H), project(H, points)) == pytest.approx(np.array(points))
    calibrated = fit_homography([[0, 0], [29, 0], [0, 4], [29, 4]], project(H, [[0, 0], [29, 0], [0, 4], [29, 4]]))
    assert project(calibrated, points) == pytest.approx(project(H, points))


def test_degenerate_and_duplicate_anchor_rejection():
    with pytest.raises(ValueError, match='Degenerate'):
        fit_homography([[0, 0], [1, 0], [2, 0], [3, 0]], [[0, 1], [1, 1], [2, 1], [3, 1]])
    with pytest.raises(ValueError, match='Duplicate'):
        fit_homography([[0, 0], [0, 0], [1, 1], [2, 2]], [[0, 1], [1, 2], [2, 3], [3, 4]])


def test_withheld_points_cannot_leak_into_fit():
    value = design()
    value['strips']['upper']['check'][0] = value['strips']['upper']['fit'][0]
    with pytest.raises(ValueError, match='leakage'):
        evaluate_design(value, 'image-one', (3000, 4000))


def test_wrong_photo_and_insufficient_checks_rejected():
    with pytest.raises(ValueError, match='different'):
        evaluate_design(design(), 'image-two', (3000, 4000))
    value = design()
    value['strips']['upper']['check'].pop()
    with pytest.raises(ValueError, match='Insufficient'):
        evaluate_design(value, 'image-one', (3000, 4000))


def test_failed_validation_does_not_refit_or_disappear():
    value = design()
    baseline = evaluate_design(value, 'image-one', (3000, 4000))
    for point in value['strips']['upper']['check']:
        point['image_xy'][0] += 18
    result = evaluate_design(value, 'image-one', (3000, 4000))
    assert not result['geometry_gate_passed']
    assert result['strips']['upper']['homography'] == baseline['strips']['upper']['homography']
    assert len(result['strips']['upper']['checks']) == 20


def test_projected_holes_do_not_claim_wiring_or_safe_addresses():
    result = evaluate_design(design(), 'image-one', (3000, 4000))
    assert result['geometry_gate_passed']
    points = result['strips']['upper']['holes']
    assert len(points) == 315
    assert all(p['occupancy'] == 'unknown' and p['electrical_address'] is None for p in points)
    assert any(not p['within_anchor_domain'] for p in points)


def test_nearest_candidate_rejects_between_holes_and_outside_board():
    candidate = nearest_grid_point(H, project(H, [[5, 2]])[0], 63)
    assert candidate['column_from_right'] == 5 and candidate['electrical_address'] is None
    assert nearest_grid_point(H, project(H, [[5.5, 2]])[0], 63) is None
    assert nearest_grid_point(H, project(H, [[70, 2]])[0], 63) is None
