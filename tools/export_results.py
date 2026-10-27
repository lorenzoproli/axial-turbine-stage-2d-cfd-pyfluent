"""Export English scientific tables from the separately supplied native data.

This offline command verifies accepted monitor hashes, recomputes cycle
statistics, and checks mesh-quality quantiles against the native arrays.
It neither starts Fluent nor changes figures, movies or native input records.
"""
from pathlib import Path
import hashlib
import math
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workflow'))
from data_schema import csv, json
from common import project_path  # portable resolution of native record paths

T = 2.97583785e-4
RUNS = ['ITER30', 'ITER60', 'T100', 'T200', 'T400', 'M1', 'M2', 'M3']
MONITORS = {'forza_y_rotore': ('rotor_tangential_force', 'N'),
            'mdot_inlet': ('inlet_mass_flow', 'kg/s'),
            'mdot_outlet': ('outlet_mass_flow', 'kg/s'),
            'pt_outlet': ('outlet_total_pressure', 'Pa')}
HEADERS = {
    'run_id': 'run_id', 'window_cycle_index': 'window_cycle_index', 'window_cycle_index': 'window_cycle_index',
    'start_time_s': 'start_time_s', 'end_time_s': 'end_time_s', 'timestep_s': 'timestep_s',
    'inner_iterations_per_step': 'inner_iterations', 'mean': 'mean', 'minimum': 'minimum',
    'maximum': 'maximum', 'peak_to_peak': 'peak_to_peak',
    'mean_cycle_peak_to_peak': 'mean_cycle_peak_to_peak', 'unit': 'unit',
    'from_window_cycle_index': 'from_window_cycle_index', 'to_window_cycle_index': 'to_window_cycle_index',
    'mean_change_percent': 'mean_change_percent',
    'amplitude_change_percent': 'amplitude_change_percent',
    'phase_rms_percent_of_amplitude': 'phase_rms_percent_of_amplitude',
    'phase_fraction': 'phase_fraction', 'physical_time_s': 'physical_time_s', 'value': 'value',
    'net_inward_flow_kg_s': 'net_inward_flow_kg_s', 'net_flow_percent_of_inlet': 'net_flow_percent_of_inlet',
    'integrated_net_inward_mass_kg': 'integrated_net_inward_mass_kg',
    'integrated_net_inward_mass_kg': 'integrated_net_inward_mass_kg',
    'domain_mass_change_kg': 'domain_mass_change_kg',
    'integral_mass_defect_kg': 'integral_mass_defect_kg',
    'integral_mass_defect_percent_of_inlet_mass': 'integral_mass_defect_percent_of_inlet_mass',
    'time_samples': 'time_samples', 'sampled_yplus_min': 'sampled_yplus_min',
    'sampled_yplus_max': 'sampled_yplus_max',
    'face_count_fraction_below_one_at_all_samples': 'face_count_fraction_below_one_at_all_samples',
    'reference_face_index': 'reference_face_index', 'reference_y_m': 'reference_y_m',
    'time_mean_static_pressure_Pa': 'time_mean_static_pressure_Pa',
    'sampled_static_pressure_min_Pa': 'sampled_static_pressure_min_Pa',
    'sampled_static_pressure_max_Pa': 'sampled_static_pressure_max_Pa',
    'time_mean_yplus': 'time_mean_yplus', 'zone': 'zone', 'field': 'field',
    'maximum_absolute_difference': 'maximum_absolute_difference',
    'absolute_rms_difference': 'absolute_rms_difference',
    'relative_rms_percent': 'relative_rms_percent',
    'maximum_geometric_mapping_error_m': 'maximum_geometric_mapping_error_m',
    'mean_ITER30': 'mean_ITER30', 'mean_ITER60': 'mean_ITER60',
    'mean_difference_percent': 'mean_difference_percent',
    'amplitude_difference_percent': 'amplitude_difference_percent',
    'phase_rms_percent_of_amplitude': 'phase_rms_percent_of_amplitude',
    'from_run': 'from_run', 'to_run': 'to_run', 'comparison': 'comparison',
    'temporal_mean_difference_percent': 'temporal_mean_difference_percent',
    'inner_iteration_mean_difference_percent': 'inner_iteration_mean_difference_percent',
    'temporal_mean_below_iteration_difference': 'temporal_mean_below_iteration_difference',
    'maximum_cycle_mean_change_percent': 'maximum_cycle_mean_change_percent',
    'maximum_cycle_amplitude_change_percent': 'maximum_cycle_amplitude_change_percent',
    'inner_iteration_amplitude_difference_percent': 'inner_iteration_amplitude_difference_percent',
    'inner_iteration_phase_rms_percent_of_amplitude': 'inner_iteration_phase_rms_percent_of_amplitude',
    'temporal_mean_below_cycle_variability': 'temporal_mean_below_cycle_variability',
    'temporal_amplitude_below_iteration_difference': 'temporal_amplitude_below_iteration_difference',
    'metric': 'metric', 'native_field': 'native_field', 'active_cells': 'active_cells',
    'median': 'median', 'condition': 'condition', 'threshold': 'threshold', 'percent': 'percent',
}
DROP = {'note', 'method', 'domain_storage', 'evidence', 'source', 'file'}
OUTPUTS, SOURCES = [], {}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError('Required separate native input is unavailable: ' + str(path.relative_to(ROOT)))
    SOURCES[path.relative_to(ROOT).as_posix()] = sha(path)
    return path


def load(path):
    return json.loads(source(path).read_text(encoding='utf-8-sig'))


def read_csv(path):
    with source(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(relative, rows):
    if not rows:
        return
    path = ROOT / 'results' / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    OUTPUTS.append({'file': path.relative_to(ROOT / 'results').as_posix(),
                    'rows': len(rows), 'sha256': sha(path)})


def write_json(relative, value):
    path = ROOT / 'results' / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    OUTPUTS.append({'file': path.relative_to(ROOT / 'results').as_posix(), 'sha256': sha(path)})


def label(value):
    if value in MONITORS:
        return MONITORS[value][0]
    if value == 'wall_statore':
        return 'stator_blade'
    if value == 'wall_rotore':
        return 'rotor_blade'
    if 'statore' in value:
        return 'stator'
    if 'rotore' in value:
        return 'rotor'
    if value == 'baseline_adattata':
        return 'historical_baseline'
    if value.endswith('_HYBRID35_initial_position'):
        return value.split('_')[0]
    return value


def export_table(src, destination):
    rows = read_csv(src)
    result = []
    for row in rows:
        monitor = row.get('monitor')
        translated = {}
        for key, value in row.items():
            if key in DROP:
                continue
            new_key = HEADERS.get(key, key)
            if key == 'unit' and monitor in MONITORS:
                value = MONITORS[monitor][1]
            elif key in {'monitor', 'wall', 'zone', 'zone', 'mesh'}:
                value = label(value)
            translated[new_key] = value
        result.append(translated)
    write_csv(destination, result)
    return result


def native_rows(path):
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        parts = line.split()
        if len(parts) == 3:
            try:
                rows.append([int(parts[0]), float(parts[1]), float(parts[2])])
            except ValueError:
                pass
    array = np.asarray(rows, dtype=float)
    assert array.ndim == 2 and array.shape[1] == 3, path
    assert np.isfinite(array).all() and np.all(np.diff(array[:, 2]) > 0), path
    return array


def interval(t, values, start, end):
    assert t[0] <= start + 1e-13 and t[-1] >= end - 1e-13
    keep = (t > start) & (t < end)
    return np.r_[start, t[keep], end], np.r_[np.interp(start, t, values), values[keep], np.interp(end, t, values)]


def check_native_statistics(analysis, progress):
    checked = 0
    for native_name in MONITORS:
        pieces = []
        for record in analysis['sources']:
            path = project_path(record['file'])
            with path.open(encoding='utf-8', errors='replace') as stream:
                if next(stream, '').strip() != '"' + native_name + '-rfile"':
                    continue
            assert sha(source(path)) == record['sha256'], path
            values = native_rows(path)
            for segment in progress.get('monitor_segments', []):
                if project_path(segment['directory']).resolve() != path.parent.resolve():
                    continue
                if segment.get('from_s') is not None:
                    values = values[values[:, 2] >= segment['from_s'] - 1e-13]
                if segment.get('to_s') is not None:
                    values = values[values[:, 2] <= segment['to_s'] + 1e-13]
            pieces.append(values)
        assert pieces, native_name
        values = np.concatenate(pieces)
        values = values[np.argsort(values[:, 2])]
        duplicates = np.where(np.abs(np.diff(values[:, 2])) < 1e-13)[0]
        for index in duplicates:
            assert values[index, 0] == values[index + 1, 0]
            assert np.isclose(values[index, 1], values[index + 1, 1], rtol=1e-10, atol=1e-12)
        values = np.delete(values, duplicates, axis=0)
        start, end = analysis['window_s']
        tt, vv = interval(values[:, 2], values[:, 1], start, end)
        mean = float(np.trapezoid(vv, tt) / (end - start))
        amplitudes = []
        for cycle in range(analysis['cycles']):
            _, vv = interval(values[:, 2], values[:, 1], start + cycle*T, start + (cycle+1)*T)
            amplitudes.append(float(np.ptp(vv)))
        saved = next(row for row in analysis['statistics'] if row['monitor'] == native_name)
        assert math.isclose(mean, saved['mean'], rel_tol=1e-11, abs_tol=1e-10)
        assert math.isclose(float(np.mean(amplitudes)), saved['mean_cycle_peak_to_peak'], rel_tol=1e-10, abs_tol=1e-10)
        checked += 1
    return checked


def export_runs():
    summaries = []
    for run in RUNS:
        systematic = run.startswith('M')
        group = 'systematic_mesh' if systematic else 'adapted_mesh'
        directory = ROOT / 'runs' / 'analysis' / group / run
        progress = load(ROOT / 'runs' / group / run / 'progress.json')
        analysis = load(directory / 'analysis.json')
        assert check_native_statistics(analysis, progress) == 4
        duration = progress['current_time_s'] - progress['initial_time_s']
        steps = progress['completed_steps']
        assert math.isclose(duration, steps * progress['timestep_s'], abs_tol=1e-12)
        periods = int(round(progress['current_time_s'] / T)) if systematic else None
        if systematic:
            assert periods == {'M1': 35, 'M2': 40, 'M3': 35}[run]
        resources = progress.get('resource_segments', [])
        configured = progress.get('config', {}).get('fluent', {}).get('processor_count')
        initial_mpi = resources[0]['mpi_processes'] if resources else configured
        final_mpi = resources[-1]['mpi_processes'] if resources else configured
        if not initial_mpi or not final_mpi:
            raise ValueError('Missing recorded MPI count for ' + run)
        change_step = resources[1]['initial_steps'] if len(resources) > 1 else None
        row = dict(run_id=analysis['id'], dataset=group,
                   active_cells=progress['active_cells'], timestep_s=progress['timestep_s'],
                   inner_iterations=progress['inner_iterations_per_step'],
                   mpi_processes_initial_segment=initial_mpi,
                   mpi_processes_final_segment=final_mpi,
                   mpi_change_after_accepted_step=change_step,
                   accepted_steps=steps, final_time_s=progress['current_time_s'],
                   integration_duration_s=duration, periods_from_hybrid=periods,
                   statistics_start_s=analysis['window_s'][0], statistics_end_s=analysis['window_s'][1],
                   statistics_periods=analysis['cycles'],
                   operational_monitor_checks_passed=analysis['monitor_periodicity_within_proposed_criteria'])
        summaries.append(row)
        prefix = group + '/' + run + '/'
        tables = {'statistics_window.csv': 'window_statistics.csv', 'statistics_cycles.csv': 'cycle_statistics.csv',
                  'comparison_cycles.csv': 'cycle_recurrence.csv', 'profiles_in_phase.csv': 'phase_profiles.csv',
                  'balance_mass_flows.csv': 'cycle_mass_flux.csv',
                  'balance_mass_con_storage_cycles.csv': 'cycle_mass_conservation.csv'}
        for name, target in tables.items():
            if (directory / name).is_file():
                export_table(directory / name, prefix + target)
        record = dict(schema_version=1, **row,
                      checks=dict(cycle_means=analysis['checks']['means'],
                                  cycle_amplitudes=analysis['checks']['amplitudes'],
                                  phase_waveforms=analysis['checks']['phase'],
                                  boundary_mass_flux=analysis['checks']['mass_flows']),
                      diagnostic_limits=dict(mean_change_percent=0.5, amplitude_change_percent=5,
                                             phase_rms_percent_of_amplitude=10, boundary_mass_flux_percent=0.5),
                      reference_depth_m=1, physical_validation=False,
                      grid_independence_established=False, timestep_independence_established=False,
                      native_monitor_statistics_recomputed=True)
        residuals = load(directory / 'residuals_summary.json')
        record['residual_history'] = dict(steps_available=residuals['steps'],
                                         minimum_inner_iterations=residuals['minimum_inner_iterations'],
                                         maximum_inner_iterations=residuals['maximum_inner_iterations'])
        assessment = directory / 'asymptotic_assessment' / 'assessment.json'
        if assessment.is_file():
            saved = load(assessment)
            record['additional_checks'] = saved['checks']
            record['maximum_field_relative_rms_percent'] = saved['field_RMS_relative_max_percent']
            record['maximum_integral_mass_defect_percent'] = saved['integral_mass_defect_max_percent']
            record['field_relative_rms_limit_percent'] = saved['field_RMS_relative_limit_percent']
            record['integral_mass_defect_limit_percent'] = saved['integral_mass_defect_limit_percent']
            export_table(directory / 'asymptotic_assessment' / 'phase_field_recurrence.csv', prefix + 'phase_field_recurrence.csv')
        walls = directory / 'cycle_walls'
        if (walls / 'summary_cycle.csv').is_file():
            export_table(walls / 'summary_cycle.csv', prefix + 'sampled_wall_resolution.csv')
            for blade in ['stator', 'rotor']:
                export_table(walls / ('wall_' + blade + '_envelope.csv'), prefix + blade + '_wall_envelope.csv')
        write_json(prefix + 'assessment.json', record)
    write_csv('run_summary.csv', summaries)


def export_quality():
    extrema = []
    thresholds = []
    for mesh in ['baseline', 'M1', 'M2', 'M3']:
        directory = ROOT / 'runs' / 'mesh_quality' / mesh
        saved = read_csv(directory / 'statistics_quality.csv')
        archive = np.load(source(directory / 'quality_cells.npz'))
        for row in saved:
            zone_index = 0 if 'statore' in row['zone'] else 1
            array = archive[f'zone{zone_index}_{row["metric"]}']
            assert len(array) == int(row['active_cells']) and np.isfinite(array).all()
            checks = dict(minimum=np.min(array), maximum=np.max(array), median=np.median(array),
                          q01=np.quantile(array, .01), q05=np.quantile(array, .05),
                          q95=np.quantile(array, .95), q99=np.quantile(array, .99))
            assert all(math.isclose(float(value), float(row[key]), rel_tol=1e-12, abs_tol=1e-20)
                       for key, value in checks.items()), (mesh, row['metric'])
            if row['metric'] == 'cell_volume_m3':
                assert np.all(array > 0)
            conditions = {'orthogonal_quality': [('<', .01), ('<', .05), ('<', .1)],
                          'aspect_ratio': [('>', 100)], 'equiangle_skewness': [('>', .9)]}
            for condition, threshold in conditions.get(row['metric'], []):
                count = int(np.count_nonzero(array < threshold if condition == '<' else array > threshold))
                thresholds.append(dict(mesh='historical_baseline' if mesh == 'baseline' else mesh,
                                       zone='stator' if zone_index == 0 else 'rotor', metric=row['metric'],
                                       condition=condition, threshold=threshold, active_cells=count,
                                       percent_of_zone_cells=100*count/len(array)))
        export_table(directory / 'statistics_quality.csv', 'mesh_quality/' + mesh + '_zone_quantiles.csv')
        def metric(name, key):
            values = [float(row[key]) for row in saved if row['metric'] == name]
            return min(values) if key == 'minimum' else max(values)
        cells = sum(int(row['active_cells']) for row in saved if row['metric'] == 'orthogonal_quality')
        assert cells == {'baseline': 289671, 'M1': 54287, 'M2': 104831, 'M3': 196569}[mesh]
        extrema.append(dict(mesh='historical_baseline' if mesh == 'baseline' else mesh,
                            active_cells=cells, minimum_orthogonal_quality=metric('orthogonal_quality', 'minimum'),
                            maximum_aspect_ratio=metric('aspect_ratio', 'maximum'),
                            maximum_equiangle_skewness=metric('equiangle_skewness', 'maximum'),
                            minimum_cell_volume_m3=metric('cell_volume_m3', 'minimum'),
                            all_cell_volumes_positive=True))
    write_csv('mesh_quality/summary.csv', extrema)
    write_csv('mesh_quality/diagnostic_threshold_counts.csv', thresholds)


def export_sensitivity():
    base = ROOT / 'runs' / 'analysis' / 'sensitivity'
    iteration = load(base / 'inner_iterations' / 'assessment.json')
    export_table(base / 'inner_iterations' / 'comparison_ITER30_ITER60.csv', 'sensitivity/inner_iteration_comparison.csv')
    field_tables = [p for p in (base / 'inner_iterations').glob('*.csv')
                    if read_csv(p) and 'relative_rms_percent' in read_csv(p)[0]]
    assert len(field_tables) == 1
    export_table(field_tables[0], 'sensitivity/inner_iteration_phase_fields.csv')
    time = load(base / 'timestep' / 'assessment.json')
    time_csv = next((base / 'timestep').glob('*temporali.csv'), None)
    if time_csv is None:
        time_csv = base / 'timestep' / 'comparisons_temporal.csv'
    if not time_csv.is_file():
        candidates = [p for p in (base / 'timestep').glob('*.csv') if read_csv(p) and 'from_run' in read_csv(p)[0]]
        time_csv = max(candidates, key=lambda p: len(read_csv(p)))
    export_table(time_csv, 'sensitivity/timestep_comparison.csv')
    error_tables = [p for p in (base / 'timestep').glob('*.csv')
                    if read_csv(p) and 'inner_iteration_mean_difference_percent' in read_csv(p)[0]]
    assert len(error_tables) == 1
    export_table(error_tables[0], 'sensitivity/timestep_iteration_error_comparison.csv')
    grid = load(base / 'grid' / 'assessment.json')
    for filename in ['mesh_pair_comparisons.csv', 'recomputed_monitor_statistics.csv',
                     'phase_profiles_with_cycle_range.csv', 'three_mesh_trends.csv']:
        export_table(base / 'grid' / filename, 'sensitivity/grid_' + filename)
    decision = time['decision']
    write_json('sensitivity/assessment.json', dict(
        schema_version=1,
        inner_iterations=dict(within_recorded_diagnostic_limits=iteration['within_criteria'],
                              adopted_iterations=iteration['selected_temporal_iterations'],
                              mean_difference_limit_percent=0.1, amplitude_difference_limit_percent=2,
                              phase_rms_limit_percent_of_amplitude=2,
                              applicable_mesh='historical_baseline_mesh'),
        timestep=dict(T200_T400_within_recorded_limits=decision['T200_T400_within_criteria'],
                      adopted_systematic_campaign_timestep_s=decision['spatial_study_timestep_s'],
                      mean_difference_limit_percent=0.1, amplitude_difference_limit_percent=2,
                      phase_rms_limit_percent_of_amplitude=2, independence_established=False),
        grid=dict(fine_pair_maximum_mean_difference_percent=grid['fine_pair_max_mean_difference_percent'],
                  fine_pair_amplitude_difference_percent_range=grid['fine_pair_amplitude_difference_percent_range'],
                  indicative_2d_cellcount_refinement_ratios=grid['refinement_ratios_2D_cellcount'],
                  independence_established=False, observed_order=None, GCI=None),
        physical_validation=False))


def main():
    export_runs()
    export_quality()
    export_sensitivity()
    write_json('data_manifest.json', dict(schema_version=1, accepted_runs=8,
               native_monitor_statistics_checked=32, native_mesh_quality_collections_checked=4,
               units=dict(time='s', force='N at 1 m reference depth', mass_flow='kg/s', pressure='Pa',
                          phase='fraction of one blade-passing period', yplus='dimensionless'),
               inputs=[dict(file=name, sha256=digest) for name, digest in sorted(SOURCES.items())],
               outputs=OUTPUTS.copy()))
    print(json.dumps(dict(accepted_runs=8, checked_monitor_statistics=32,
                         checked_mesh_quality_collections=4, output_files=len(OUTPUTS)), indent=2))


if __name__ == '__main__':
    main()
