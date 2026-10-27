"""Assess each completed duration target before allowing the next mesh."""
from data_schema import csv, json
from common import *
from monitor_analysis import analyse
from residual_analysis import analyse_residuals
from wall_cycle_analysis import analyse_wall_cycle
from compare_phase_fields import compare_pair
from registry import update_test
from transcript_utils import close_transcript
from monitor_paths import monitor_path
import numpy as np, time

def wait_for_closed_outputs(meta, timeout_s=120):
    """Keep writer-denying reads; wait for native shutdown to release every output."""
    previous = None
    deadline = time.monotonic() + timeout_s
    last_error = None
    while time.monotonic() < deadline:
        try:
            paths = []
            for segment in meta['monitor_segments']:
                directory = project_path(segment['directory'])
                paths.extend((monitor_path(directory, name) for name in ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet', 'massa_dominio']))
                paths.append(directory / 'fluent.trn')
            signature = []
            for path in paths:
                with safe_read(path):
                    pass
                stat = path.stat()
                signature.append((str(path), stat.st_size, stat.st_mtime_ns))
            if signature == previous:
                print('CLOSED_OUTPUTS_VERIFIED', meta['id'], len(paths), flush=True)
                return
            previous = signature
        except OSError as error:
            if getattr(error, 'winerror', None) not in [32, 33]:
                raise
            last_error = error
            previous = None
        time.sleep(1)
    raise RuntimeError('Native output handles did not become stably readable after solver exit: ' + str(last_error))

def assess(run_id, cfg):
    directory = case_directory(run_id)
    meta = json.loads((directory / 'progress.json').read_text())
    periods = int(round(meta['planned_steps'] * meta['timestep_s'] / T))
    expected = periods * cfg['steps_per_period']
    assert 4 <= periods <= 100 and meta['completed_steps'] == meta['planned_steps'] == expected
    assert periods == cfg.get('period_targets_by_run', {}).get(run_id, cfg['total_periods_each_mesh'])
    assert abs(meta['current_time_s'] - meta['initial_time_s'] - periods * T) < 1e-12
    wait_for_closed_outputs(meta)
    for item in meta['final_manifest']:
        path = project_path(item['file'])
        assert path.stat().st_size == item['byte'] and sha(path) == item['sha256']
    monitors = analyse(directory)
    transcripts = [project_path(segment['directory']) / 'fluent.trn' for segment in meta['monitor_segments']]
    residuals = analyse_residuals(run_id, transcripts)
    inner_ok = residuals['steps'] == expected and residuals['minimum_inner_iterations'] == residuals['maximum_inner_iterations'] == cfg['inner_iterations_per_step']
    walls = analyse_wall_cycle(run_id)
    wall_ok = all((row['sampled_yplus_max'] < 1 for row in walls['statistics']))
    out = project_path(ROOT / '05_postprocessing/campagna' / run_id / 'asymptotic_assessment')
    out.mkdir(parents=True, exist_ok=True)
    captures = {item['completed_steps']: item for item in meta['captures']}
    per = cfg['steps_per_period']
    first = (periods - 3) * per
    first_cycle = periods - 2
    fields = []
    for cycle in range(2):
        for phase in range(4):
            left_step = first + cycle * per + phase * per // 4
            right_step = left_step + per

            def path(step):
                frame = captures[step]
                item = next((item for item in frame['manifest'] if item['file'].endswith('.npz')))
                result = project_path(item['file'])
                assert result.stat().st_size == item['byte'] and sha(result) == item['sha256']
                return result
            label = f'cycle_{cycle + first_cycle}_to_{cycle + first_cycle + 1}_phase_{phase:02d}_of_04'
            comparison = compare_pair(path(left_step), path(right_step), label, out / 'native_comparisons', duplicate_policy='conservative_bounds')
            for row in comparison:
                fields.append(dict(from_cycle=cycle + first_cycle, to_cycle=cycle + first_cycle + 1, phase_fraction=phase / 4, zone='Stator' if row['zone'] == 'statore' else 'Rotor', field=row['field'], earlier_time_s=row['earlier_time_s'], later_time_s=row['later_time_s'], RMS_relative_percent=row['relative_rms_percent'], RMS_absolute=row['absolute_rms_difference'], RMS_relative_lower_bound_percent=row['relative_rms_lower_bound_percent'], metric_interpretation='Conservative upper bound over all coincident-coordinate value selections', inconsistent_groups_earlier=row['inconsistent_coordinate_groups_left'], inconsistent_groups_later=row['inconsistent_coordinate_groups_right'], maximum_absolute_difference=row['maximum_absolute_difference'], geometric_mapping_max_error_m=row['maximum_mapping_error_m'], unique_nodes=row['physical_nodes'], limit_RMS_percent=cfg['field_recurrence_relative_RMS_limit_percent']))
    csvwrite(out / 'phase_field_recurrence.csv', fields)
    field_ok = all((row['RMS_relative_percent'] <= cfg['field_recurrence_relative_RMS_limit_percent'] for row in fields))
    defects = [abs(row['integral_mass_defect_percent_of_inlet_mass']) for row in monitors.get('mass_balance_including_storage', [])]
    mass_ok = len(defects) == 3 and max(defects) <= cfg['integral_mass_defect_limit_percent_inlet_mass']
    checks = dict(three_cycle_monitor_periodicity=monitors['monitor_periodicity_within_proposed_criteria'], phase_field_recurrence=field_ok, integrated_mass_conservation_including_storage=mass_ok, actual_inner_iterations=inner_ok, sampled_yplus_below_one=wall_ok)
    passed = all(checks.values())
    record = dict(utc=now(), run_id=run_id, periods=periods, checks=checks, passed_for_next_mesh=passed, state='OPERATIONAL_ASYMPTOTIC_CHECKS_PASSED' if passed else 'REVIEW_REQUIRED_BEFORE_NEXT_MESH', statistics_window_s=meta['averaging_window_s'], monitor_evidence=str(project_path(ROOT / '05_postprocessing/campagna' / run_id / 'analysis.json')), field_recurrence_csv=str(out / 'phase_field_recurrence.csv'), field_RMS_relative_limit_percent=cfg['field_recurrence_relative_RMS_limit_percent'], field_RMS_interpretation='Conservative upper bound including every value at coincident exported coordinates; no averaging or exclusion. Identical duplicate values give the exact unique-coordinate RMS. Lower bounds and duplicate spreads are retained in the comparison CSVs.', field_RMS_relative_max_percent=max((row['RMS_relative_percent'] for row in fields)), integral_mass_defect_max_percent=max(defects) if defects else None, integral_mass_defect_limit_percent=cfg['integral_mass_defect_limit_percent_inlet_mass'], sampled_yplus_max={row['wall']: row['sampled_yplus_max'] for row in walls['statistics']}, physical_validation=False, timestep_independence_established=False, spatial_independence_established=False, limitations='Operational settling diagnostics on three complete phase-aligned cycles. Nodal field RMS is not volume weighted. No experimental validation, grid-asymptotic order or GCI follows from these checks. Native video visual review remains separate. No automatic transient extension is performed.')
    jwrite(out / 'assessment.json', record)
    meta.update(status='COMPLETED_MONITOR_PERIODICITY_CHECKS_PASSED' if passed else 'COMPLETED_PERIODICITY_UNCONFIRMED', asymptotic_assessment=str(out / 'assessment.json'), next_mesh_allowed_by_checks=passed, sampled_yplus_below_one=wall_ok, analysis=record['monitor_evidence'])
    jwrite(directory / 'progress.json', meta)
    if meta.get('native_playback'):
        streaming = bool(meta.get('native_mach_stream_settings'))
        path = project_path(meta['native_animation_directory']) / ('native_mach_playback_manifest.json' if streaming else 'native_playback_manifest.json')
        native = json.loads(path.read_text())
        native.update(monitor_periodicity_passed=checks['three_cycle_monitor_periodicity'], asymptotic_assessment=record['state'], window_interpretation='Full startup transient; only the separately assessed final three cycles may be called periodically settled; visual review pending' if streaming else 'Final-period candidate; visual review pending' if passed else 'Unsettled diagnostic; review required')
        jwrite(path, native)
    next_activity = 'Review the completed mesh assessment before configuring another run.'
    update_test(run_id, meta['status'], evidence=str(out / 'assessment.json'), next_activity=next_activity)
    from periodicity_diagnostic import diagnose
    diagnose(run_id)
    from plot_histories import plot
    plot(run_id)
    append_status(run_id + f': {periods} periods completed and the solver exited before assessment. Checks: ' + json.dumps(checks) + '. ' + (next_activity + '.' if passed else 'Campaign stopped for review; no following mesh and no automatic transient extension.'))
    print('ASYMPTOTIC_ASSESSMENT', run_id, passed, checks, flush=True)
    return record
