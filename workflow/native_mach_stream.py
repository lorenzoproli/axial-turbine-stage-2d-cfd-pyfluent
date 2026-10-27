"""Native Mach acquisition throughout a transient, with safe restart indexing."""
from data_schema import csv, json
from common import *
from native_capture_mach_fast import MachCaptureFast
from pipeline import FLUIDS, WALLS
from render_period import verified_motion
from ansys.fluent.core.fields.field_data_interfaces import ScalarFieldDataRequest
import numpy as np
CONFIG_PATH = CONFIG_DIR / 'mach_stream_config.json'

def configuration():
    cfg = json.loads(CONFIG_PATH.read_text())
    assert cfg['fields'] == ['mach-number'] and cfg['CFD_steps_between_frames'] == 10
    assert abs(cfg['timestep_s'] * 400 - T) < 1e-15 and cfg['samples_per_period'] == 40
    assert cfg['start_from_actual_t0'] and cfg['include_nonlooping_final_endpoint']
    folder = cfg.get('output_subdirectory', 'from_t0')
    assert project_path(folder).name == folder and folder not in ['.', '..']
    return cfg

class MachStream:

    def __init__(self, session, directory, segment, completed_step=0, origin_time_s=0.0, origin_step=0, require_t0=True, preserve_future_frames=False):
        self.s = session
        self.directory = project_path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.segment = segment
        self.cfg = configuration()
        self.origin_time_s = origin_time_s
        self.origin_step = origin_step
        if require_t0:
            assert origin_time_s == 0 and origin_step == 0
        self.index_path = self.directory / 'frame_index.json'
        self.index = json.loads(self.index_path.read_text()) if self.index_path.exists() else dict(revision=self.cfg['revision'], origin_time_s=origin_time_s, origin_step=origin_step, frames=[], superseded_after_checkpoint_rollback=[])
        assert self.index['origin_time_s'] == origin_time_s and self.index['origin_step'] == origin_step
        stale = [] if preserve_future_frames else [item for item in self.index['frames'] if item['step'] > completed_step]
        if stale:
            backup = self.directory / ('frame_index_before_rollback_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
            shutil.copy2(self.index_path, backup)
            assert sha(backup) == sha(self.index_path)
            self.index['superseded_after_checkpoint_rollback'].append(dict(utc=now(), checkpoint_step=completed_step, frames=stale))
            self.index['frames'] = [item for item in self.index['frames'] if item['step'] <= completed_step]
            jwrite(self.index_path, self.index)
        self.engine = MachCaptureFast(session, scheme_transport=self.cfg['scheme_transport'], mach_range=self.cfg['fixed_Mach_range'], allow_upper_saturation=self.cfg.get('out_of_range_policy') == 'saturate_with_disclosure')
        self.engine.cfg = dict(self.engine.cfg, samples_per_period=40, selected_fields=['mach'], fps=self.cfg['FPS'])

    def next_step(self, done, total):
        stride = self.cfg['CFD_steps_between_frames']
        return min(total, (done // stride + 1) * stride)

    def records(self):
        records = []
        for item in sorted(self.index['frames'], key=lambda item: item['step']):
            path = self.directory / item['manifest']
            assert sha(path) == item['sha256']
            record = json.loads(path.read_text())
            for image in record['files']:
                p = project_path(image['file'])
                assert p.stat().st_size == image['byte'] and sha(p) == image['sha256']
            records.append(record)
        return records

    def capture(self, step):
        assert step % self.cfg['CFD_steps_between_frames'] == 0
        actual = float(self.s.scheme.eval("(rpgetvar 'flow-time)"))
        native_step = int(self.s.scheme.eval("(rpgetvar 'time-step)"))
        assert native_step == self.origin_step + step
        assert abs(actual - self.origin_time_s - step * self.cfg['timestep_s']) < 1e-12
        existing = next((item for item in self.index['frames'] if item['step'] == step), None)
        if existing:
            path = self.directory / existing['manifest']
            assert sha(path) == existing['sha256']
            record = json.loads(path.read_text())
            assert abs(record['solution_time_s'] - actual) < 1e-12
            for image in record['files']:
                assert sha(project_path(image['file'])) == image['sha256']
            return record
        values = self.s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name='mach-number', node_value=True))
        extrema = {name: dict(min=float(value.min()), max=float(value.max()), finite=bool(np.isfinite(value).all())) for name, value in values.items()}
        assert all((item['finite'] for item in extrema.values()))
        tag = self.segment + f'_step_{step:06d}'
        try:
            record = self.engine.capture(self.directory, tag, dict(solution_time_s=actual, extrema={'mach-number': extrema}), write_manifest=False)
        except Exception:
            jwrite(self.directory / (tag + '_capture_rejected.json'), dict(utc=now(), step=step, native_step=native_step, solution_time_s=actual, nodal_Mach_extrema=extrema, acquisition_configuration=self.cfg))
            raise
        viewport = self.engine.cfg['camera']
        bottom = viewport['centre_m'][1] - viewport['height_m'] / 2
        top = viewport['centre_m'][1] + viewport['height_m'] / 2
        coverage = {}
        for zone, item in record['periodic_instancing'].items():
            low, high = item['original_y_bounds_m']
            shift = item['translation_m'][1] * item['repeats']
            minimum = min(low, low + shift)
            maximum = max(high, high + shift)
            assert minimum <= bottom + 1e-07 and maximum >= top - 1e-07, 'Native periodic instances do not cover the fixed view'
            coverage[zone] = dict(instanced_y_bounds_m=[minimum, maximum], required_y_bounds_m=[bottom, top])
        earlier = [item for item in self.index['frames'] if item['step'] < step]
        if earlier:
            previous_item = max(earlier, key=lambda item: item['step'])
            previous = json.loads((self.directory / previous_item['manifest']).read_text())
            low = previous['periodic_instancing'][FLUIDS[1]]['original_y_bounds_m']
            high = record['periodic_instancing'][FLUIDS[1]]['original_y_bounds_m']
            record['motion_since_previous_frame'] = verified_motion(previous['solution_time_s'], sum(low) / 2, actual, sum(high) / 2)
        record.update(relative_CFD_step=step, native_step=native_step, physical_acquisition_interval_s=self.cfg['timestep_s'] * 10, acquisition_configuration=self.cfg, periodic_view_coverage=coverage, nodal_Mach_extrema=extrema, nodes_above_display_limit={name: int(np.count_nonzero(value > self.cfg['fixed_Mach_range'][1])) for name, value in values.items()}, upper_colour_saturation_disclosed=self.cfg.get('out_of_range_policy') == 'saturate_with_disclosure')
        path = self.directory / (tag + '_manifest.json')
        jwrite(path, record)
        self.index['frames'].append(dict(step=step, solution_time_s=actual, manifest=path.name, sha256=sha(path)))
        self.index['frames'].sort(key=lambda item: item['step'])
        self.index.update(utc=now(), last_native_time_s=actual, last_step=step)
        jwrite(self.index_path, self.index)
        return record

def playback_export(session, directory, run_id, records, require_t0=True):
    """Encode every actual transient frame, including t=0 and final endpoint."""
    directory = project_path(directory)
    cfg = configuration()
    times = [r['solution_time_s'] for r in records]
    assert len(records) >= 2 and all((r['selected_fields'] == ['mach'] for r in records))
    if require_t0:
        assert times[0] == 0 and records[0]['native_step'] == 0
    assert np.allclose(np.diff(times), cfg['timestep_s'] * 10, rtol=0, atol=1e-12)
    assert all((r['configuration'] == records[0]['configuration'] and r['acquisition_configuration'] == cfg for r in records))
    name = run_id.lower() + '-native-mach-transient'
    sequence = directory / (name + '.cxa')
    output = directory / (run_id + '_native_mach_from_t0.mp4')
    assert not sequence.exists() and (not output.exists())
    lines = ['AnimationSequence1.0', f'NAME: {name}', 'WINID: 1', 'STORAGE: 7', 'PLOTANIMATION: 0', f'FRAMES: {len(records)}']
    for i, record in enumerate(records):
        item = record['files'][0]
        path = project_path(item['file'])
        assert sha(path) == item['sha256']
        lines.append(f'Frame {i} 7 {project_path(os.path.relpath(path, directory)).as_posix()} 1')
    text(sequence, '\n'.join(lines) + '\n')
    session.chdir(str(directory))
    pb = session.settings.results.animations.playback
    pb.read_animation_file(animation_file_name=str(sequence))
    pb.current_animation = name
    pb.set_custom_frames.set_state(dict(start_frame=1, end_frame=len(records), increment=1))
    pb.video.set_state(dict(fps=cfg['FPS'], format='mp4', quality='best', name=output.stem, use_original_resolution=False, width=cfg['width_px'], height=cfg['height_px'], advance_quality={'enable_h264': False}))
    jwrite(directory / 'mach_playback_settings.json', pb.get_state())
    pb.write_animation(format_name='video')
    assert output.is_file() and output.stat().st_size > 0
    receipt = dict(utc=now(), state='MACH_TRANSIENT_NATIVE_PLAYBACK_EXPORTED_QA_PENDING', run_id=run_id, encoded_frames=len(records), first_solution_time_s=times[0], last_solution_time_s=times[-1], final_endpoint_included=True, configuration=cfg, file=str(output), byte=output.stat().st_size, sha256=sha(output), sequence=str(sequence), sequence_sha256=sha(sequence), source_manifest_sha256=[sha(directory / item['manifest']) for item in json.loads((directory / 'frame_index.json').read_text())['frames']], interpretation='Startup/transient sequence; no assertion of periodic flow or physical validation')
    jwrite(directory / 'native_mach_playback_manifest.json', receipt)
    return receipt
