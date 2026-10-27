"""Native Fluent PNG capture and native Playback MP4 export; no external rendering."""
from data_schema import csv, json
from common import *
from pipeline import FLUIDS, WALLS
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, SurfaceDataType
import numpy as np
CONFIG_PATH = CONFIG_DIR / 'native_animation_config.json'

def configuration():
    return json.loads(CONFIG_PATH.read_text())

def configure(s):
    cfg = configuration()
    g = s.settings.results.graphics
    g.picture.set_state(dict(color_mode='color', driver_options={'hardcopy_format': 'png'}, invert_background=True, use_window_resolution=False, x_resolution=cfg['width_px'], y_resolution=cfg['height_px']))
    if cfg.get('legend_layout', {}).get('recreate_native_objects'):
        old = [name for name in ['native-mach', 'native-pressure'] if name in g.contour.get_object_names()]
        if old:
            g.contour.delete(name_list=old)
    for key, field in [('mach', 'mach-number'), ('pressure', 'pressure')]:
        low, high = cfg['fixed_ranges'][key]
        g.contour['native-' + key] = {'field': field, 'filled': True, 'node_values': True, 'boundary_values': True, 'surfaces_list': FLUIDS, 'range_option': {'option': 'auto-range-off', 'auto_range_off': {'minimum': low, 'maximum': high, 'clip_to_range': False}}, 'coloring': {'option': 'smooth', 'smooth': True}, 'color_map': {'format': '%.2f' if key == 'mach' else '%.0f', 'title_elements': 'Variable', 'position': cfg.get('legend_layout', {}).get('contour_colormap_position', 1), 'font_automatic': False, 'font_size': 16, 'length': 0.54, 'width': 6, 'bground_transparent': True}}
    return cfg

def periodic_settings(s, cfg):
    """Fill the fixed crop with native pitch repeats in the required direction."""
    g = s.settings.results.graphics
    geo = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=FLUIDS, data_types=[SurfaceDataType.Vertices]))
    centre_y = cfg['camera']['centre_m'][1]
    height = cfg['camera']['height_m']
    records = {}
    for i, fluid in enumerate(FLUIDS):
        y = geo[fluid].vertices[:, 1].astype(float)
        low = float(y.min())
        high = float(y.max())
        direction = 1 if centre_y > (low + high) / 2 else -1
        distance = max(abs(centre_y - low), abs(centre_y - high)) + height
        count = max(cfg['minimum_repeats'], int(np.ceil(distance / PITCH)) + 4)
        obj = g.periodic_instancing[fluid]
        obj.set_state({'periodic_type': 'translational', 'translation': [0, direction * PITCH, 0], 'repeats': count, 'surfaces': [fluid, WALLS[i]]})
        records[fluid] = dict(original_y_bounds_m=[low, high], direction=direction, repeats=count, translation_m=[0, direction * PITCH, 0])
    return records

def capture_native(s, directory, tag, source_frame):
    cfg = configure(s)
    directory = project_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    g = s.settings.results.graphics
    periodic = periodic_settings(s, cfg)
    actual_time = float(s.scheme.eval("(rpgetvar 'flow-time)"))
    assert abs(actual_time - source_frame['solution_time_s']) < 1e-12
    for key, field in [('mach', 'mach-number'), ('pressure', 'pressure')]:
        values = source_frame['extrema'][field].values()
        low = min((v['min'] for v in values))
        high = max((v['max'] for v in values))
        limits = cfg['fixed_ranges'][key]
        assert low >= limits[0] and high <= limits[1], f'{key}: fixed colour range excludes represented values; review before encoding'
    files = []
    layouts = {}
    for key, window in [('mach', 1), ('pressure', 2)]:
        path = directory / (tag + '_' + key + '.png')
        assert not path.exists()
        g.windows.set_window(window_id=window)
        if cfg.get('legend_layout', {}).get('recreate_capture_windows'):
            g.windows.close_window(window_id=window)
            g.windows.open_window(window_id=window)
        s.scheme.eval(f'(cx-use-window-id {window})')
        g.contour['native-' + key].display()
        camera = g.views.camera
        centre = cfg['camera']['centre_m']
        height = cfg['camera']['height_m']
        camera.projection(type='orthographic')
        camera.position(xyz=[*centre, 1])
        camera.target(xyz=[*centre, 0])
        camera.up_vector(xyz=[0, 1, 0])
        camera.field(width=height * cfg['width_px'] / cfg['height_px'], height=height)
        s.tui.display.clear_annotations()
        text_value = f'Solution time: {actual_time:.12f} s'
        g.windows.text.set_state(dict(visible=True, application=False, date=False))
        s.tui.display.set.titles.left_top(json.dumps(text_value))
        s.tui.display.set.titles.right_top(json.dumps('Absolute Mach number [-]' if key == 'mach' else 'Absolute static pressure [Pa]'))
        g.contour['native-' + key].display()
        camera.projection(type='orthographic')
        camera.position(xyz=[*centre, 1])
        camera.target(xyz=[*centre, 0])
        camera.up_vector(xyz=[0, 1, 0])
        camera.field(width=height * cfg['width_px'] / cfg['height_px'], height=height)
        if cfg.get('legend_layout'):
            layout = cfg['legend_layout']
            g.windows.main.set_state(layout['main'])
            g.windows.scale.set_state(dict(layout['scale'], format='%.2f' if key == 'mach' else '%.0f'))
            g.windows.text.set_state(layout['text'])
        s.tui.display.re_render()
        g.picture.save_picture(file_name=str(path))
        from PIL import Image
        with Image.open(path) as im:
            assert im.size == (cfg['width_px'], cfg['height_px'])
        if cfg.get('legend_layout'):
            from legend_geometry import colour_bar_rectangle
            rectangle = colour_bar_rectangle(path)
            expected = cfg['legend_layout'].get('expected_pixel_rectangles', {}).get(key)
            if expected is not None:
                assert max((abs(a - b) for a, b in zip(rectangle, expected))) <= cfg['legend_layout']['pixel_rectangle_tolerance'], f'{key}: native colour-bar rectangle changed: {rectangle} versus {expected}'
            layouts[key] = dict(pixel_rectangle=rectangle, window_main=g.windows.main.get_state(), window_scale=g.windows.scale.get_state(), window_text=g.windows.text.get_state())
        files.append(dict(field=key, file=str(path), byte=path.stat().st_size, sha256=sha(path), window=window))
    manifest_path = directory / (tag + '_native_manifest.json')
    record = dict(utc=now(), method='Fluent native graphics save-picture', solution_time_s=actual_time, manifest_file=str(manifest_path), rotor_wall_node_centroid=source_frame['rotor_wall_node_centroid'], time_annotation=text_value, configuration=cfg, periodic_instancing=periodic, files=files, source_manifest=source_frame['manifest'], legend_layout_measurements=layouts)
    prior = sorted(directory.glob('step_*_native_manifest.json'))
    if prior:
        from render_period import verified_motion
        previous = json.loads(prior[-1].read_text())
        record['motion_since_previous_frame'] = verified_motion(previous['solution_time_s'], previous['rotor_wall_node_centroid'][1], actual_time, record['rotor_wall_node_centroid'][1])
    jwrite(manifest_path, record)
    return record

def playback_export(s, directory, run_id, records, diagnostic=False):
    """Read native PNG sequence indices into Fluent and use Fluent write-animation."""
    cfg = configuration()
    directory = project_path(directory)
    times = [r['solution_time_s'] for r in records]
    assert len(records) >= 2 and np.all(np.diff(times) >= 0)
    if not diagnostic:
        assert len(records) == 101 and abs(times[-1] - times[0] - T) < 1e-10
        assert np.allclose(np.diff(times), T / 100, rtol=1e-07, atol=1e-12)
        assert all((record['configuration'] == cfg for record in records)), 'Rendering settings changed within a resumed sequence'
    motion_checks = []
    if not diagnostic:
        from render_period import verified_motion
        for earlier, later in zip(records, records[1:]):
            low = earlier['periodic_instancing'][FLUIDS[1]]['original_y_bounds_m']
            high = later['periodic_instancing'][FLUIDS[1]]['original_y_bounds_m']
            motion_checks.append(verified_motion(earlier['solution_time_s'], sum(low) / 2, later['solution_time_s'], sum(high) / 2))
    pb = s.settings.results.animations.playback
    videos = []
    encoded = records if diagnostic else records[:-1]
    for key, window in [('mach', 1), ('pressure', 2)]:
        name = f'{run_id.lower()}-native-{key}'
        sequence = directory / (name + '.cxa')
        assert not sequence.exists()
        lines = ['AnimationSequence1.0', f'NAME: {name}', f'WINID: {window}', 'STORAGE: 7', 'PLOTANIMATION: 0', f'FRAMES: {len(encoded)}']
        for i, record in enumerate(encoded):
            item = next((v for v in record['files'] if v['field'] == key))
            path = project_path(item['file'])
            assert sha(path) == item['sha256']
            lines.append(f'Frame {i} 7 {project_path(os.path.relpath(path, directory)).as_posix()} {window}')
        sequence.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        s.chdir(str(directory))
        pb.read_animation_file(animation_file_name=str(sequence))
        pb.current_animation = name
        pb.set_custom_frames.set_state(dict(start_frame=1, end_frame=len(encoded), increment=1))
        output = directory / f'{run_id}_native_{key}.mp4'
        assert not output.exists()
        pb.video.set_state(dict(fps=cfg['fps'], format='mp4', quality='best', name=output.stem, use_original_resolution=False, width=cfg['width_px'], height=cfg['height_px'], advance_quality={'enable_h264': False}))
        jwrite(directory / (key + '_playback_settings.json'), pb.get_state())
        pb.write_animation(format_name='video')
        assert output.is_file() and output.stat().st_size > 0, 'Fluent Playback did not produce the requested MP4'
        videos.append(dict(file=str(output), byte=output.stat().st_size, sha256=sha(output), sequence=str(sequence), sequence_sha256=sha(sequence), encoded_frames=len(encoded), field=key))
    receipt = dict(utc=now(), method='Fluent native PNG + Fluent Solution Animation Playback', run_id=run_id, state='DIAGNOSTIC_PLAYBACK_EXPORTED' if diagnostic else 'NATIVE_PLAYBACK_EXPORTED_VISUAL_QA_PENDING', diagnostic=diagnostic, configuration=cfg, first_solution_time_s=times[0], last_solution_time_s=times[-1], cross_segment_motion_checks=motion_checks, source_frame_pairs=len(records), frame_manifest_files=[r.get('manifest_file') for r in records if r.get('manifest_file')], videos=videos)
    jwrite(directory / 'native_playback_manifest.json', receipt)
    return receipt
