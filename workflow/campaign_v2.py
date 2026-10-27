"""Coherent native checkpoints, isolated monitor segments and strict restarts."""
from data_schema import csv, json
from common import *
from pipeline import snapshot, FLUIDS
from registry import update_test
from transcript_utils import close_transcript
from ansys.fluent.core.fields.field_data_interfaces import ScalarFieldDataRequest
import numpy as np, time, traceback, subprocess
CONFIG = json.loads((CONFIG_DIR / 'workflow_config.json').read_text())

def file_manifest(paths):
    return [dict(file=p.relative_to(ROOT).as_posix(), relative_file=p.relative_to(ROOT).as_posix(), byte=p.stat().st_size, sha256=sha(p)) for p in paths]

def prepare(s, run_cfg):
    from cfd import ensure_campaign_open
    ensure_campaign_open()
    if CONFIG['fluent']['processor_count'] != 24:
        raise ValueError('The documented campaign requires 24 MPI processes.')
    run_id = run_cfg['id']
    target = case_directory(run_id)
    if target.exists():
        raise FileExistsError(f'{run_id} already exists; use a separate verified restart segment.')
    target.mkdir(parents=True)
    checkpoint = project_path(ROOT / run_cfg.get('checkpoint', CONFIG['campaign']['checkpoint']))
    expected_cells = run_cfg.get('expected_cells', 289671)
    s.settings.file.read_case_data(file_name=str(checkpoint))
    close_transcript(s)
    s.transcript.start(file_name=str(target / 'fluent.trn'), write_to_stdout=False)
    t0 = float(s.scheme.eval("(rpgetvar 'flow-time)"))
    assert abs(t0 - run_cfg.get('initial_time_s', 0.010653)) < 1e-12
    for name in s.settings.solution.monitor.report_files.get_object_names():
        s.settings.solution.monitor.report_files[name].file_name = str(target / (name + '.out'))
    s.settings.solution.report_definitions.volume['massa_dominio'] = {'report_type': 'volume-integral', 'field': 'density', 'cell_zones': FLUIDS, 'per_zone': False}
    s.settings.solution.monitor.report_files['massa_dominio-rfile'] = {'file_name': str(target / 'massa_dominio-rfile.out'), 'report_defs': ['massa_dominio', 'flow-time'], 'frequency_of': 'time-step', 'frequency': 1, 'active': True, 'print': False}
    computed = s.settings.solution.report_definitions.compute(report_defs=['massa_dominio'])
    mass = float(computed[0]['massa_dominio'][0])
    assert mass > 0 and np.isfinite(mass)
    s.settings.file.auto_save.data_frequency = 0
    dt = run_cfg['timestep_s']
    iterations = run_cfg['max_iter']
    s.settings.solution.run_calculation.transient_controls.time_step_size = dt
    s.settings.solution.run_calculation.transient_controls.max_iter_per_time_step = iterations
    for name in s.settings.solution.monitor.residual.equations.get_object_names():
        s.settings.solution.monitor.residual.equations[name].check_convergence = False
    assert not s.scheme.eval("(rpgetvar 'adapt/dynamic?)")
    assert int(s.fields.reduction.count(locations=FLUIDS)) == expected_cells
    warm = run_cfg.get('warmup_periods', CONFIG['campaign']['warmup_periods'])
    avg = run_cfg.get('average_periods', CONFIG['campaign']['average_periods'])
    steps = int(np.ceil((warm + avg) * T / dt - 1e-10))
    meta = dict(id=run_id, status='PREPARED_NOT_ADVANCED', start_utc=now(), active_mpi_processes=24, initial_checkpoint=str(checkpoint), initial_checkpoint_sha256=sha(checkpoint), initial_data_sha256=sha(checkpoint.with_name(checkpoint.name.replace('.cas.h5', '.dat.h5'))), initial_time_s=t0, timestep_s=dt, inner_iterations_per_step=iterations, residual_stopping_enabled=False, planned_steps=steps, completed_steps=0, settling_periods=warm, averaging_periods=avg, averaging_window_s=[t0 + warm * T, t0 + (warm + avg) * T], initial_phase_mod_T=t0 / T % 1, mesh=run_cfg.get('mesh', 'baseline_fixed_topology'), active_cells=expected_cells, initial_mass_kg=mass, final_samples_per_period=run_cfg.get('samples_per_period', 100 if run_id in ['T400', 'M3'] else 4), config=CONFIG, current_output=str(target), monitor_segments=[dict(directory=str(target), from_s=t0, to_s=None)])
    meta.update(capture_periods=run_cfg.get('capture_periods', 1), native_animation_enabled=run_cfg.get('native_animation_enabled', True), capture_fields=run_cfg.get('capture_fields', ['mach-number', 'pressure']), max_run_hours=run_cfg.get('max_run_hours', CONFIG['safety']['max_run_hours']), initialization_method=run_cfg.get('initialization_method', 'Native checkpoint restart'))
    if run_cfg.get('native_mach_stream_configuration'):
        path = project_path(ROOT / run_cfg['native_mach_stream_configuration'])
        meta['native_mach_stream_configuration'] = str(path.relative_to(ROOT))
        meta['native_mach_stream_settings'] = json.loads(path.read_text())
    jwrite(target / 'progress.json', meta)
    jwrite(target / 'setup_effettivo.json', s.settings.get_state())
    git_executable = shutil.which('git')
    revision = subprocess.run([git_executable, 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True) if git_executable else None
    meta['git_revision'] = revision.stdout.strip() if revision is not None and revision.returncode == 0 else None
    meta['code_manifest'] = [dict(file=str(p.relative_to(ROOT)), sha256=sha(p)) for p in sorted(Path(__file__).parent.glob('*.py'))]
    meta['initial_checkpoint_relative'] = str(checkpoint.relative_to(ROOT))
    meta['initial_global_step'] = int(s.scheme.eval("(rpgetvar 'time-step)"))
    jwrite(target / 'progress.json', meta)
    print('CAMPAIGN_PREPARED', run_id, steps, 'mass_kg=', mass, flush=True)
    return (target, meta)

def advance(s, target, meta):
    from cfd import ensure_campaign_open
    ensure_campaign_open()
    output = project_path(meta.get('current_output', target))
    start_wall = time.monotonic()
    done = meta['completed_steps']
    total = meta['planned_steps']
    dt = meta['timestep_s']
    iterations = meta['inner_iterations_per_step']
    t0 = meta['initial_time_s']
    reason = 'step_limit_reached'
    meta['status'] = 'RUNNING_24_MPI'
    jwrite(target / 'progress.json', meta)
    update_test(meta['id'], meta['status'], mpi_processes=24, timestep_s=dt, inner_iterations_per_step=iterations, active_cells=meta['active_cells'], mesh=meta['mesh'], evidence=str(target / 'progress.json'), next_activity='Complete the averaging window and assess its statistics')
    append_status(f'{meta['id']} running with 24 MPI processes: dt={dt:.12g} s, {iterations} inner iterations/step, target {total} steps. {meta['settling_periods']} periods excluded; {meta['averaging_periods']} complete periods used for statistics. Restart preserves physical time and the moving mesh.')
    next_checkpoint = int(np.ceil(done * dt / T + 1 - 1e-10))
    from solution_exports import capture
    capture_steps = []
    base_id = mesh_base_id(meta['id'])
    if base_id in ['T100', 'T200', 'T400', 'M1', 'M2', 'M3']:
        per_period = int(round(T / dt))
        assert abs(per_period * dt - T) < 1e-14
        start_cycle = (meta['settling_periods'] + meta['averaging_periods'] - 1) * per_period
        samples = meta.get('final_samples_per_period', 100 if meta['id'] == 'T400' else 4)
        stride = per_period // samples
        assert stride > 0 and per_period % stride == 0
        capture_steps = list(range(start_cycle, start_cycle + per_period + 1, stride))
        for previous in range(1, meta.get('capture_periods', 1)):
            cycle_start = start_cycle - previous * per_period
            assert per_period % 4 == 0 and cycle_start >= 0
            capture_steps.extend(range(cycle_start, cycle_start + per_period + 1, per_period // 4))
        capture_steps = sorted(set(capture_steps))
    meta.setdefault('captures', [])
    native_records = []
    native_directory = None
    mach_stream = None
    stream_settings = meta.get('native_mach_stream_settings')
    if base_id in ['M2', 'M3'] and meta.get('native_animation_enabled', True) and (not stream_settings):
        from native_animation import capture_native, playback_export
        periods = meta['settling_periods'] + meta['averaging_periods']
        native_directory = project_path(ROOT / '07_animazioni/campagna_mesh_sistematiche' / meta['id'] / 'native_fluent' / f'period_{periods:02d}_{output.name}')
        meta['native_animation_directory'] = str(native_directory)
    try:
        if stream_settings:
            from native_mach_stream import MachStream, configuration as stream_configuration
            assert base_id == 'M3' and t0 == 0 and (stream_settings == stream_configuration())
            native_directory = project_path(ROOT / '07_animazioni/campagna_mesh_sistematiche' / meta['id'] / 'native_fluent' / stream_settings.get('output_subdirectory', 'from_t0'))
            meta['native_animation_directory'] = str(native_directory)
            mach_stream = MachStream(s, native_directory, output.name, completed_step=done)
            if done == 0 or done % stream_settings['CFD_steps_between_frames'] == 0:
                mach_stream.capture(done)
                jwrite(target / 'progress.json', meta)
        while done < total:
            if shutil.disk_usage(ROOT).free < CONFIG['safety']['min_free_disk_GiB'] * 1024 ** 3:
                reason = 'insufficient_disk_space'
                break
            if time.monotonic() - start_wall > meta.get('max_run_hours', CONFIG['safety']['max_run_hours']) * 3600:
                reason = 'runtime_limit'
                break
            future_captures = [n for n in capture_steps if n > done]
            batch = min(CONFIG['campaign']['batch_steps'], total - done, min(future_captures) - done if future_captures else total - done)
            if mach_stream is not None:
                batch = min(batch, mach_stream.next_step(done, total) - done)
            s.settings.solution.run_calculation.dual_time_iterate(time_step_count=batch, max_iter_per_step=iterations)
            done += batch
            current = float(s.scheme.eval("(rpgetvar 'flow-time)"))
            assert abs(current - (t0 + done * dt)) < 1e-10
            health = dict(utc=now(), time_s=current, completed_steps=done, mpi_processes=24, active_cells=int(s.fields.reduction.count(locations=FLUIDS)))
            bad = []
            for field in ['density', 'temperature', 'pressure', 'mach-number']:
                vals = s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name=field, node_value=False))
                low = min((float(v.min()) for v in vals.values()))
                high = max((float(v.max()) for v in vals.values()))
                finite = all((np.isfinite(v).all() for v in vals.values()))
                health[field] = dict(min=low, max=high, finite=bool(finite))
                if not finite:
                    bad.append(field + '_non_finite')
                if field in ['density', 'temperature', 'pressure'] and low <= 0:
                    bad.append(field + '_non_positive')
                if field == 'mach-number' and high > CONFIG['safety']['max_mach_diagnostic']:
                    bad.append('Mach_oltre_soglia_diagnostica')
            if health['active_cells'] != meta['active_cells']:
                bad.append('active_cell_count_changed')
            if s.scheme.eval("(rpgetvar 'adapt/dynamic?)"):
                bad.append('automatic_adaptation_enabled')
            with (output / 'health_checks.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(health) + '\n')
            meta.update(completed_steps=done, current_time_s=current, wall_seconds=time.monotonic() - start_wall, updated_utc=now(), latest_health=health)
            if done in capture_steps:
                frame = capture(s, output / 'campi_in_fase', f'step_{done:05d}', fields=meta.get('capture_fields', ['mach-number', 'pressure']))
                if native_directory is not None and mach_stream is None and (done >= start_cycle):
                    native = capture_native(s, native_directory, f'step_{done:05d}', frame)
                    native_records.append(native)
                    frame['native_png_manifest'] = str(native_directory / f'step_{done:05d}_native_manifest.json')
                frame['completed_steps'] = done
                meta['captures'].append(frame)
                print('PHASE_CAPTURE_SAVED', meta['id'], done, f'{current:.12f}', flush=True)
            if mach_stream is not None and done % stream_settings['CFD_steps_between_frames'] == 0:
                record = mach_stream.capture(done)
                meta['native_mach_frames'] = len(mach_stream.index['frames'])
                meta['last_Mach_capture_seconds'] = record['timings']['total_frame_s']
            jwrite(target / 'progress.json', meta)
            print('CAMPAIGN_PROGRESS', meta['id'], done, total, 't=', f'{current:.12f}', 'elapsed_s=', round(meta['wall_seconds'], 1), flush=True)
            if done * dt / T >= next_checkpoint - 1e-08 and done < total:
                cp = output / 'checkpoints' / f'periodo_{next_checkpoint:02d}_step_{done:05d}'
                cp.parent.mkdir(exist_ok=True)
                s.settings.file.write_case_data(file_name=str(cp) + '.cas.h5')
                meta['latest_checkpoint'] = file_manifest(sorted(cp.parent.glob(cp.name + '.*.h5')))
                jwrite(cp.parent / (cp.name + '_manifest.json'), meta['latest_checkpoint'])
                jwrite(target / 'progress.json', meta)
                next_checkpoint += 1
            if bad:
                reason = 'diagnostic_stop:' + ','.join(bad)
                break
            if (WORK / 'STOP_AFTER_BATCH.txt').exists():
                reason = 'controlled_stop_requested'
                break
        if done > 0:
            final = output / 'final.cas.h5'
            assert not final.exists()
            s.settings.file.write_case_data(file_name=str(final))
            meta['final_manifest'] = file_manifest(sorted(output.glob('final.*.h5')))
            if done == total:
                meta['final_fields'] = snapshot(s, output / 'final_fields.npz')
                if mach_stream is not None:
                    from native_mach_stream import playback_export as stream_playback
                    records = mach_stream.records()
                    if records[0]['native_step'] != 0 and stream_settings.get('deferred_startup_reconstruction'):
                        meta['native_playback_pending'] = dict(reason='Early native frames must be reconstructed at the same fixed range before full-transient Playback', missing_steps=list(range(0, records[0]['native_step'], 10)), first_available_step=records[0]['native_step'])
                    else:
                        meta['native_playback'] = stream_playback(s, native_directory, meta.get('native_playback_run_id', meta['id']), records)
                elif native_directory is not None:
                    native_records = [json.loads(project_path(frame['native_png_manifest']).read_text()) for frame in meta['captures'] if frame.get('completed_steps', -1) >= start_cycle and frame.get('native_png_manifest')]
                    meta['native_playback'] = playback_export(s, native_directory, meta['id'], native_records)
        meta.update(status='COMPLETED_ASSESSMENT_PENDING' if done == total else 'STOPPED_WITH_CHECKPOINT', stop_reason=reason, end_utc=now(), wall_seconds=time.monotonic() - start_wall)
        jwrite(target / 'progress.json', meta)
        update_test(meta['id'], meta['status'], completed_steps=done, final_time_s=meta.get('current_time_s'), evidence=str(target / 'progress.json'))
        append_status(f'{meta['id']}: {meta['status']}, {done}/{total} steps. Motivo: {reason}. Final pair indexed by SHA256; statistical assessment follows.')
        print('CAMPAIGN_SAVED', meta['id'], meta['status'], flush=True)
        return meta
    except Exception as e:
        meta.update(status='FAILED', error=repr(e), traceback=traceback.format_exc(), end_utc=now(), stop_reason='technical_error:' + repr(e))
        try:
            if done > 0:
                actual = float(s.scheme.eval("(rpgetvar 'flow-time)"))
                assert abs(actual - (t0 + done * dt)) < 1e-10
                cp = output / 'failure_checkpoints' / f'step_{done:06d}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}'
                cp.parent.mkdir(exist_ok=True)
                s.settings.file.write_case_data(file_name=str(cp) + '.cas.h5')
                checkpoint = file_manifest(sorted(cp.parent.glob(cp.name + '.*.h5')))
                assert len(checkpoint) == 2
                meta['latest_checkpoint'] = checkpoint
                meta['failure_checkpoint_saved'] = True
                jwrite(cp.parent / (cp.name + '_manifest.json'), checkpoint)
        except Exception as checkpoint_error:
            meta['failure_checkpoint_error'] = repr(checkpoint_error)
        jwrite(target / 'progress.json', meta)
        update_test(meta['id'], 'FAILED', evidence=str(target / 'progress.json'))
        raise

def resume(s, run_id):
    from cfd import ensure_campaign_open
    ensure_campaign_open()
    target = case_directory(run_id)
    meta = json.loads((target / 'progress.json').read_text())
    restartable = ['FAILED', 'STOPPED_WITH_CHECKPOINT', 'INTERRUPTED_CHECKPOINT_AVAILABLE', 'RUNNING_24_MPI', 'ready_for_extension', 'READY_FOR_AUTHORISED_EXTENSION']
    if meta['status'] not in restartable:
        raise RuntimeError('The saved run is not in a restartable state.')
    candidates = meta.get('final_manifest') if meta['status'] in ['STOPPED_WITH_CHECKPOINT', 'ready_for_extension', 'READY_FOR_AUTHORISED_EXTENSION'] else meta.get('latest_checkpoint')
    if not candidates:
        raise RuntimeError('No verified checkpoint is available.')
    for f in candidates:
        path = project_path(f['file'])
        if path.stat().st_size != f['byte'] or sha(path) != f['sha256']:
            raise RuntimeError('Restart checkpoint checksum or size differs: ' + str(path))
    cas = next((project_path(f['file']) for f in candidates if f['file'].endswith('.cas.h5')))
    s.settings.file.read_case_data(file_name=str(cas))
    current = float(s.scheme.eval("(rpgetvar 'flow-time)"))
    done = int(round((current - meta['initial_time_s']) / meta['timestep_s']))
    assert abs(current - (meta['initial_time_s'] + done * meta['timestep_s'])) < 1e-10
    verification = None
    if run_id.endswith('_HYBRID35'):
        from verify_campaign_restart import verify
        verification = verify(s, target, meta, cas, current, done)
    segment = target / 'segments' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    segment.mkdir(parents=True)
    segments = meta.setdefault('monitor_segments', [dict(directory=str(target), from_s=meta['initial_time_s'], to_s=None)])
    segments[-1]['to_s'] = current
    segments.append(dict(directory=str(segment), from_s=current, to_s=None, checkpoint=str(cas), sha256=sha(cas)))
    for name in s.settings.solution.monitor.report_files.get_object_names():
        s.settings.solution.monitor.report_files[name].file_name = str(segment / (name + '.out'))
    close_transcript(s)
    s.transcript.start(file_name=str(segment / 'fluent.trn'), write_to_stdout=False)
    if verification is not None:
        jwrite(segment / 'restart_verified_before_advance.json', verification)
        meta.setdefault('verified_restarts', []).append(str(segment / 'restart_verified_before_advance.json'))
    meta.update(completed_steps=done, current_time_s=current, current_output=str(segment), resumed_utc=now(), active_mpi_processes=24)
    if meta.get('error'):
        meta.setdefault('previous_failures', []).append({k: meta.get(k) for k in ['error', 'traceback', 'end_utc', 'stop_reason']})
    for key in ['error', 'traceback', 'end_utc', 'stop_reason', 'latest_health', 'final_manifest']:
        meta.pop(key, None)
    meta['restart_source_manifest'] = candidates
    meta.setdefault('resume_code_manifests', []).append(dict(utc=now(), segment=str(segment), files=[dict(file=str(p.relative_to(ROOT)), sha256=sha(p)) for p in sorted(Path(__file__).parent.glob('*.py'))]))
    jwrite(target / 'progress.json', meta)
    return (target, meta)
