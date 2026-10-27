"""Common-window phase comparisons without automatic order or GCI claims."""
from data_schema import csv, json
from common import *
from registry import update_test
import numpy as np
from scipy.spatial import cKDTree

def phase_profiles(run_id):
    p = project_path(ROOT / '05_postprocessing/campagna' / run_id / 'profili_in_fase.csv')
    with p.open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    names = sorted({r['monitor'] for r in rows})
    out = {}
    for name in names:
        cycles = sorted({int(r['window_cycle_index']) for r in rows if r['monitor'] == name})
        out[name] = np.mean([[float(r['value']) for r in rows if r['monitor'] == name and int(r['window_cycle_index']) == k] for k in cycles], axis=0)
    return out

def compare_iteration():
    base = project_path(ROOT / '05_postprocessing/campagna')
    a = json.loads((base / 'ITER30/analysis.json').read_text())
    b = json.loads((base / 'ITER60/analysis.json').read_text())
    assert np.allclose(a['window_s'], b['window_s'], rtol=0, atol=1e-13)
    pa, pb = (phase_profiles('ITER30'), phase_profiles('ITER60'))
    rows = []
    for x, y in zip(a['statistics'], b['statistics']):
        assert x['monitor'] == y['monitor']
        n = x['monitor']
        amp = y['mean_cycle_peak_to_peak']
        rows.append(dict(monitor=n, mean_ITER30=x['mean'], mean_ITER60=y['mean'], unit=x['unit'], mean_difference_percent=100 * abs(x['mean'] - y['mean']) / abs(y['mean']), amplitude_difference_percent=100 * abs(x['mean_cycle_peak_to_peak'] - amp) / amp, phase_rms_percent_of_amplitude=100 * float(np.sqrt(np.mean((pa[n] - pb[n]) ** 2))) / amp))
    criteria = dict(mean_percent=0.1, amplitude_percent=2, phase_rms_percent_of_amplitude=2)
    passed = all((r['mean_difference_percent'] <= 0.1 and r['amplitude_difference_percent'] <= 2 and (r['phase_rms_percent_of_amplitude'] <= 2) for r in rows))
    fields = []
    paths = []
    for rid in ['ITER30', 'ITER60']:
        directory = case_directory(rid)
        meta = json.loads((directory / 'progress.json').read_text())
        paths.append(project_path(meta.get('current_output', directory)) / 'final_fields.npz')
    with np.load(paths[0]) as za, np.load(paths[1]) as zb:
        assert abs(float(za['solution_time_s']) - float(zb['solution_time_s'])) < 1e-12
        for iz, zone in enumerate(['statore', 'rotore']):
            xa = za[f'zone{iz}_vertices']
            xb = zb[f'zone{iz}_vertices']
            dist, idx = cKDTree(xb).query(xa)
            assert float(dist.max()) < 1e-07, 'Field comparison requires matching geometry'
            for f in ['mach-number', 'pressure', 'density', 'temperature']:
                va = za[f'zone{iz}_{f}'].astype(float)
                vb = zb[f'zone{iz}_{f}'][idx].astype(float)
                d = va - vb
                fields.append(dict(zone=zone, field=f, physical_time_s=float(za['solution_time_s']), maximum_absolute_difference=float(abs(d).max()), absolute_rms_difference=float(np.sqrt(np.mean(d * d))), relative_rms_percent=100 * float(np.sqrt(np.mean(d * d) / np.mean(vb * vb))), maximum_geometric_mapping_error_m=float(dist.max()), method='Nodal comparison at matching phase; nearest coordinates within 1e-7 m; no volume weighting'))
    out = project_path(ROOT / 'runs/analysis/sensitivity/inner_iterations')
    csvwrite(out / 'confronto_ITER30_ITER60.csv', rows)
    csvwrite(out / 'confronto_campi_stessa_fase.csv', fields)
    chosen = 30 if passed else 60
    result = dict(utc=now(), windows_s=a['window_s'], proposed_diagnostic_criteria=criteria, within_criteria=passed, selected_temporal_iterations=chosen, comparisons=rows, fields=fields, note='Operational setting for the timestep study; the 30/60 comparison alone does not establish temporal or spatial independence')
    jwrite(out / 'assessment.json', result)
    for rid in ['ITER30', 'ITER60']:
        update_test(rid, 'COMPLETED_STATISTICS_AND_ITERATION_COMPARISON_CHECKED', averaging_cycles=3, evidence=str(out / 'assessment.json'), next_activity='Timestep study on the same mesh and common checkpoint')
        p = WORK / 'campagna' / rid / 'progress.json'
        meta = json.loads(p.read_text())
        meta['status'] = 'COMPLETED_AND_ANALYSED'
        meta['analysis'] = str(base / rid / 'analysis.json')
        jwrite(p, meta)
    append_status(f'ITER30/ITER60 compared over the same three periods and phase-matched fields: {('within' if passed else 'outside')} the proposed diagnostic criteria. Selected for the timestep study: {chosen} actual iterations per step. ITER60 includes domain storage: maximum integral defect about 0.000114% of inlet mass and maximum BDF2 defect about 0.0000275% of inlet flow.')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result
if __name__ == '__main__':
    compare_iteration()
