"""Short isolated t=0/moving/restart/Playback preflight for native Mach stream."""
from data_schema import csv, json
from common import *
from native_mach_stream import MachStream, playback_export, configuration
from native_animation import configure, periodic_settings
from pipeline import FLUIDS
from cfd import launch, node_processes
from transcript_utils import close_transcript
from ansys.fluent.core.fields.field_data_interfaces import ScalarFieldDataRequest
from PIL import Image
import numpy as np, h5py, imageio_ffmpeg, subprocess, time, traceback

def values(session):
    return session.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name='mach-number', node_value=True))

def reports(session):
    names = ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet', 'massa_dominio']
    return {name: float(value[0]) for group in session.settings.solution.report_definitions.compute(report_defs=names) for name, value in group.items()}

def isolated_monitors(session, directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name in session.settings.solution.monitor.report_files.get_object_names():
        session.settings.solution.monitor.report_files[name].file_name = str(directory / (name + '.out'))
    session.settings.file.auto_save.data_frequency = 0

def reference_Mach(session, path, mach_range):
    """Rebuild exactly the verified native scene, rendering only Mach."""
    assert not path.exists()
    cfg = configure(session)
    g = session.settings.results.graphics
    low, high = mach_range
    g.contour['native-mach'].range_option.set_state({'option': 'auto-range-off', 'auto_range_off': {'minimum': low, 'maximum': high, 'clip_to_range': False}})
    periodic_settings(session, cfg)
    g.windows.set_window(window_id=1)
    g.windows.close_window(window_id=1)
    g.windows.open_window(window_id=1)
    session.scheme.eval('(cx-use-window-id 1)')
    g.contour['native-mach'].display()

    def camera():
        camera = g.views.camera
        centre = cfg['camera']['centre_m']
        height = cfg['camera']['height_m']
        camera.projection(type='orthographic')
        camera.position(xyz=[*centre, 1])
        camera.target(xyz=[*centre, 0])
        camera.up_vector(xyz=[0, 1, 0])
        camera.field(width=height * cfg['width_px'] / cfg['height_px'], height=height)
    camera()

    def menu(command):
        session.scheme.eval('(ti-menu-load-string ' + json.dumps(command) + ')')
    menu('/display/clear-annotations')
    g.windows.text.set_state(dict(visible=True, application=False, date=False))
    actual = float(session.scheme.eval("(rpgetvar 'flow-time)"))
    menu('/display/set/titles/left-top ' + json.dumps(f'Solution time: {actual:.12f} s'))
    menu('/display/set/titles/right-top ' + json.dumps('Absolute Mach number [-]'))
    g.contour['native-mach'].display()
    camera()
    layout = cfg['legend_layout']
    g.windows.main.set_state(layout['main'])
    g.windows.scale.set_state(dict(layout['scale'], format='%.2f'))
    g.windows.text.set_state(layout['text'])
    menu('/display/re-render')
    g.picture.save_picture(file_name=str(path))

def preflight(session, checkpoint, run_id, directory, source_manifest):
    directory = project_path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    assert len(node_processes()) == 24
    for item in source_manifest:
        assert project_path(item['file']).stat().st_size == item['byte'] and sha(project_path(item['file'])) == item['sha256']
    close_transcript(session)
    session.transcript.start(file_name=str(directory / 'fluent.trn'), write_to_stdout=False)
    session.settings.file.read_case_data(file_name=str(checkpoint))
    assert int(session.scheme.eval("(rpgetvar 'time-step)")) == 0 and float(session.scheme.eval("(rpgetvar 'flow-time)")) == 0
    setup = session.settings.setup.get_state()
    methods = session.settings.solution.methods.get_state()
    isolated_monitors(session, directory / 'initial_monitor_segment')
    session.settings.solution.report_definitions.volume['massa_dominio'] = {'report_type': 'volume-integral', 'field': 'density', 'cell_zones': FLUIDS, 'per_zone': False}
    session.settings.solution.monitor.report_files['massa_dominio-rfile'] = {'file_name': str(directory / 'initial_monitor_segment/massa_dominio-rfile.out'), 'report_defs': ['massa_dominio', 'flow-time'], 'frequency_of': 'time-step', 'frequency': 1, 'active': True, 'print': False}
    cells = int(session.fields.reduction.count(locations=FLUIDS))
    field_health = []
    cfg = configuration()
    session.settings.solution.run_calculation.transient_controls.time_step_size = cfg['timestep_s']
    session.settings.solution.run_calculation.transient_controls.max_iter_per_time_step = 30
    for name in session.settings.solution.monitor.residual.equations.get_object_names():
        session.settings.solution.monitor.residual.equations[name].check_convergence = False
    stream = MachStream(session, directory / 'frames', 'initial', completed_step=0)
    zero = stream.capture(0)
    initial_values = {name: value.copy() for name, value in values(session).items()}
    checkpoint10 = directory / 'checkpoint_step_000010.cas.h5'
    for step in [10, 20]:
        tick = time.perf_counter()
        session.settings.solution.run_calculation.dual_time_iterate(time_step_count=10, max_iter_per_step=30)
        compute = time.perf_counter() - tick
        assert not session.scheme.eval("(rpgetvar 'adapt/dynamic?)")
        assert int(session.fields.reduction.count(locations=FLUIDS)) == cells
        extrema = {}
        for field in ['density', 'temperature', 'pressure']:
            data = session.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name=field, node_value=False))
            assert all((np.isfinite(value).all() for value in data.values()))
            low = min((float(value.min()) for value in data.values()))
            assert low > 0
            extrema[field] = dict(min=low, max=max((float(value.max()) for value in data.values())))
        field_health.append(dict(step=step, extrema=extrema))
        frame = stream.capture(step)
        print('MACH_STREAM_PREFLIGHT', run_id, step, 'solve_s', round(compute, 2), 'PNG_s', round(frame['timings']['total_frame_s'], 3), flush=True)
        if step == 10:
            reports10 = reports(session)
            session.settings.file.write_case_data(file_name=str(checkpoint10))
    reports20 = reports(session)
    final_values = values(session)
    changed = {name: float(np.max(np.abs(final_values[name] - initial_values[name]))) for name in FLUIDS}
    assert any((value > 1e-05 for value in changed.values())), 'The short test did not produce a distinguishable changing Mach field'
    reference = directory / 'rebuilt_reference_step_000020_mach.png'
    reference_Mach(session, reference, cfg['fixed_Mach_range'])
    with Image.open(reference) as a, Image.open(frame['files'][0]['file']) as b:
        assert np.array_equal(np.asarray(a), np.asarray(b)), 'Warm moving-field PNG differs from rebuilt native scene'
    checkpoint_manifest = [dict(file=str(path), byte=path.stat().st_size, sha256=sha(path)) for path in sorted(directory.glob('checkpoint_step_000010.*.h5'))]
    assert len(checkpoint_manifest) == 2
    with h5py.File(checkpoint10.with_name(checkpoint10.name.replace('.cas.h5', '.dat.h5')), 'r') as f:
        keys = list(f['results/1/phase-1/cells'])
    history = [f'SV_{name}_M{level}' for name in ['DENSITY', 'ENERGY', 'K', 'O', 'P', 'T', 'U', 'V'] for level in [1, 2]]
    assert all((name in keys for name in history))
    session.settings.file.read_case_data(file_name=str(checkpoint10))
    assert int(session.scheme.eval("(rpgetvar 'time-step)")) == 10
    assert json.dumps(session.settings.setup.get_state(), sort_keys=True) == json.dumps(setup, sort_keys=True)
    assert json.dumps(session.settings.solution.methods.get_state(), sort_keys=True) == json.dumps(methods, sort_keys=True)
    actual10 = reports(session)
    assert all((np.isclose(actual10[name], value, rtol=1e-09, atol=1e-10) for name, value in reports10.items()))
    isolated_monitors(session, directory / 'restart_monitor_segment')
    restarted = MachStream(session, directory / 'frames', 'restart', completed_step=10)
    reused = restarted.capture(10)
    assert reused['files'][0]['sha256'] == stream.records()[1]['files'][0]['sha256']
    assert len(restarted.index['frames']) == 2 and len(restarted.index['superseded_after_checkpoint_rollback']) == 1
    session.settings.solution.run_calculation.dual_time_iterate(time_step_count=10, max_iter_per_step=30)
    last = restarted.capture(20)
    after = reports(session)
    assert all((np.isclose(after[name], value, rtol=1e-09, atol=1e-10) for name, value in reports20.items()))
    assert len(restarted.index['frames']) == 3 and len({item['step'] for item in restarted.index['frames']}) == 3
    video = playback_export(session, directory / 'frames', run_id + '_PREFLIGHT', restarted.records())
    count, seconds = imageio_ffmpeg.count_frames_and_secs(video['file'])
    assert count == 3 and abs(seconds - 0.12) < 0.01
    generator = imageio_ffmpeg.read_frames(video['file'])
    metadata = next(generator)
    generator.close()
    assert metadata['size'] == (1920, 1080) and metadata['fps'] == 25
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-i', video['file'], '-vsync', '0', str(directory / 'decoded_%02d.png')], check=True)
    close_transcript(session)
    from residual_analysis import parse
    _, steps = parse(directory / 'fluent.trn', expected_iterations=30)
    assert len(steps) == 30 and all((item['actual_inner_iterations'] == 30 for item in steps))
    for item in source_manifest:
        assert sha(project_path(item['file'])) == item['sha256']
    result = dict(utc=now(), state='MACH_STREAM_T0_MOVING_RESTART_AND_PLAYBACK_VERIFIED', run_id=run_id, initial_native_time_s=0, initial_native_step=0, active_frame_steps=[0, 10, 20], physical_interval_s=10 * cfg['timestep_s'], diagnostic_CFD_steps_advanced_including_repeated_branch=30, physical_setup_unchanged=True, automatic_mesh_adaptation_active=False, source_manifest=source_manifest, checkpoint10_manifest=checkpoint_manifest, unchanged_unset_reference_values=[name for name, value in setup.get('reference_values', {}).items() if isinstance(value, float) and np.isnan(value)], active_cells=cells, positive_finite_field_health=field_health, current_time_s=float(session.scheme.eval("(rpgetvar 'flow-time)")), source_originals_unchanged=True, nodal_Mach_change_max=changed, warm_moving_frame_pixel_identical_to_rebuilt_scene=True, restart_reports_match_at_step10_and20=True, BDF_history_preserved=history, rollback_preserves_superseded_PNGs=True, duplicate_active_frames=False, video=video, frame_manifest_index=str(restarted.index_path), visual_review_pending=True, renderer_hashes={name: sha(CONFIG_DIR / name if name.endswith('.json') else Path(__file__).with_name(name)) for name in ['native_mach_stream.py', 'native_capture_mach_fast.py', 'verify_mach_stream.py', 'mach_stream_config.json']}, limitations='Short native acquisition/restart preflight on this mesh only; not flow convergence, full-transient range/coverage proof or a long-run performance guarantee. Main run must reload the untouched t=0 initialized checkpoint.')
    jwrite(directory / 'proof.json', result)
    print('MACH_STREAM_PREFLIGHT_VERIFIED', run_id, directory, flush=True)
    return result

def main():
    source = project_path('inputs/initial_conditions/M2')
    receipt = json.loads((source / 'hybrid_initialization_verified.json').read_text())
    assert receipt['restoration_before_hybrid'] and receipt['physical_setup_unchanged']
    directory = project_path(ROOT / '03_simulazioni/diagnostica_prestazioni' / ('MACH_STREAM_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')))
    s = None
    try:
        s = launch(directory.parent / ('mach_stream_launcher_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')), graphics=True)
        proof = preflight(s, project_path(receipt['initial_checkpoint']), 'M2_HYBRID35', directory, receipt['manifest_initial_checkpoint'])
        append_status('Isolated Mach stream preflight on the preserved original-position M2 Hybrid t=0 checkpoint: true initial frame, moving-field captures every 10 steps, rebuilt-scene pixel comparison, native BDF2 checkpoint/restart, preservation of orphaned future frames, unique active timestamps and variable-length native Playback passed. Thirty diagnostic steps including a repeated ten-step branch remain separate from the accepted campaign. Main M2/M3 results unchanged; fine-mesh preflight still required before a fine-mesh production run. Evidence: ' + str((directory / 'proof.json').relative_to(ROOT)))
    except Exception as error:
        jwrite(directory / 'error.json', dict(utc=now(), error=repr(error), traceback=traceback.format_exc()))
        raise
    finally:
        if s is not None:
            close_transcript(s)
            s.exit()
if __name__ == '__main__':
    main()
