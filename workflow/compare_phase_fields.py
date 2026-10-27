"""Nodal comparisons at a common mesh and phase, with explicit geometric matching."""
from data_schema import csv, json
from common import *
import numpy as np
from scipy.spatial import cKDTree

def grouped_bounds(values, inverse, count):
    """Retain every exported value at coincident coordinates as an interval."""
    values = np.asarray(values, dtype=float)
    assert np.isfinite(values).all()
    low = np.full(count, np.inf)
    high = np.full(count, -np.inf)
    np.minimum.at(low, inverse, values)
    np.maximum.at(high, inverse, values)
    return (low, high)

def recurrence_bounds(a_low, a_high, b_low, b_high):
    """Bound the norm for every possible duplicate-value selection, without averaging."""
    maximum_difference = np.maximum(abs(a_low - b_high), abs(a_high - b_low))
    minimum_difference = np.maximum(0, np.maximum(a_low - b_high, b_low - a_high))
    min_b = np.where((b_low <= 0) & (b_high >= 0), 0, np.minimum(abs(b_low), abs(b_high)))
    max_b = np.maximum(abs(b_low), abs(b_high))
    denominator_lower = float(np.mean(min_b ** 2))
    denominator_upper = float(np.mean(max_b ** 2))
    assert denominator_lower > 0, 'No positive lower bound for the reference-field RMS'
    return dict(rms_upper=float(np.sqrt(np.mean(maximum_difference ** 2))), rms_lower=float(np.sqrt(np.mean(minimum_difference ** 2))), relative_upper_percent=100 * float(np.sqrt(np.mean(maximum_difference ** 2) / denominator_lower)), relative_lower_percent=100 * float(np.sqrt(np.mean(minimum_difference ** 2) / denominator_upper)), maximum_absolute_upper=float(maximum_difference.max()))

def compare_pair(left, right, label, out, duplicate_policy='strict'):
    assert duplicate_policy in ['strict', 'conservative_bounds']
    rows = []
    with np.load(left) as a, np.load(right) as b:
        ta = float(a['solution_time_s'])
        tb = float(b['solution_time_s'])
        periods = (tb - ta) / T
        assert abs(periods - round(periods)) < 1e-08, 'Physical phases do not match'
        for iz, zone in enumerate(['statore', 'rotore']):
            raw_a = a[f'zone{iz}_vertices'].astype(float)
            raw_b = b[f'zone{iz}_vertices'].astype(float)
            xa, ia, inverse_a = np.unique(raw_a, axis=0, return_index=True, return_inverse=True)
            xb, ib, inverse_b = np.unique(raw_b, axis=0, return_index=True, return_inverse=True)
            assert len(xa) == len(xb), 'Different physical nodes; direct nodal comparison is unavailable'
            wraps = int(round((xb[:, 1].mean() - xa[:, 1].mean()) / PITCH)) if iz else 0
            xb[:, 1] -= wraps * PITCH
            distance, indices = cKDTree(xb).query(xa)
            assert len(np.unique(indices)) == len(xa) and distance.max() < 2e-07, 'Geometric correspondence is not established'
            for field in ['mach-number', 'pressure', 'density', 'temperature']:
                key = f'zone{iz}_{field}'
                if key not in a or key not in b:
                    continue
                raw_va = a[key].astype(float)
                raw_vb = b[key].astype(float)
                if duplicate_policy == 'strict':
                    assert np.array_equal(raw_va, raw_va[ia][inverse_a]) and np.array_equal(raw_vb, raw_vb[ib][inverse_b]), 'MPI duplicate nodes have different values'
                a_low, a_high = grouped_bounds(raw_va, inverse_a, len(xa))
                b_low, b_high = grouped_bounds(raw_vb, inverse_b, len(xb))
                bounds = recurrence_bounds(a_low, a_high, b_low[indices], b_high[indices])
                rows.append(dict(comparison=label, zone=zone, field=field, earlier_time_s=ta, later_time_s=tb, elapsed_periods=float(periods), periodic_mapping_translations=wraps, maximum_mapping_error_m=float(distance.max()), physical_nodes=len(xa), earlier_MPI_duplicates=len(raw_a) - len(xa), later_MPI_duplicates=len(raw_b) - len(xb), maximum_absolute_difference=bounds['maximum_absolute_upper'], absolute_rms_difference=bounds['rms_upper'], relative_rms_percent=bounds['relative_upper_percent'], relative_rms_lower_bound_percent=bounds['relative_lower_percent'], duplicate_policy=duplicate_policy, inconsistent_coordinate_groups_left=int(np.sum(a_high > a_low)), inconsistent_coordinate_groups_right=int(np.sum(b_high > b_low)), maximum_duplicate_spread_left=float((a_high - a_low).max()), maximum_duplicate_spread_right=float((b_high - b_low).max()), method='Geometrically matched unique coordinates; no differing value is averaged or discarded. Reported RMS and maximum are conservative upper bounds over all duplicate-value selections, with a lower bound on reference normalization. Bounds coincide for identical duplicates. RMS is not volume weighted; geometric tolerance 0.2 micrometres for float32 coordinates.'))
    csvwrite(out / (label + '.csv'), rows)
    jwrite(out / (label + '_manifest.json'), dict(utc=now(), sources=[dict(file=str(p), sha256=sha(p)) for p in [left, right]], comparisons=rows))
    return rows

def compare_available():
    out = project_path(ROOT / '05_postprocessing/campagna/confronti_campi_fase')
    results = []
    for rid in ['T100', 'T200', 'T400']:
        p = case_directory(rid) / 'final_fields.npz'
        if p.exists():
            results += compare_pair(AUDIT / 'baseline_fields_geometry.npz', p, 'historical_baseline_' + rid, out)
    for left, right in [('T100', 'T200'), ('T200', 'T400')]:
        a = case_directory(left) / 'final_fields.npz'
        b = case_directory(right) / 'final_fields.npz'
        if a.exists() and b.exists():
            results += compare_pair(a, b, left + '_' + right, out)
    jwrite(out / 'assessment.json', dict(utc=now(), comparisons=results, interpretation='Baseline and reproduction are six periods apart; the difference measures field evolution at matching phase. Timestep comparisons require equal physical times.'))
    return results
if __name__ == '__main__':
    print(json.dumps(compare_available(), ensure_ascii=False))
