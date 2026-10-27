"""Persistent native Mach scene with per-frame geometry and time checks.

Reset after every case/data reload. A saved view reduces repeated camera calls;
every frame refreshes the actual contour and validates the colour-bar geometry.
The production stream performs separate moving-field and restart preflight.
"""
from common import *
from native_animation import configure, periodic_settings
from legend_geometry import colour_bar_rectangle
from PIL import Image
import time, uuid

class MachCaptureFast:

    def __init__(self, session, scheme_transport=False, mach_range=None, allow_upper_saturation=False):
        self.s = session
        self.scheme_transport = scheme_transport
        self.mach_range = mach_range
        self.allow_upper_saturation = allow_upper_saturation
        self.reset()

    def menu_string(self, command):
        return self.s.scheme.eval('(ti-menu-load-string ' + json.dumps(command) + ')')

    def reset(self):
        started = time.perf_counter()
        self.cfg = configure(self.s)
        self.warmed = False
        if self.mach_range is not None:
            low, high = map(float, self.mach_range)
            assert 0 <= low < high
            self.cfg['fixed_ranges']['mach'] = [low, high]
            self.s.settings.results.graphics.contour['native-mach'].range_option.set_state({'option': 'auto-range-off', 'auto_range_off': {'minimum': low, 'maximum': high, 'clip_to_range': False}})
        self.view = 'mach-fixed-' + uuid.uuid4().hex[:12]
        self.setup_seconds = time.perf_counter() - started

    def capture(self, directory, tag, source, write_manifest=True):
        started = time.perf_counter()
        s = self.s
        g = s.settings.results.graphics
        cfg = self.cfg
        directory = project_path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (tag + '_mach.png')
        manifest = directory / (tag + '_manifest.json')
        assert not path.exists() and (not manifest.exists())
        actual = float(s.scheme.eval("(rpgetvar 'flow-time)"))
        assert abs(actual - source['solution_time_s']) < 1e-12
        values = source['extrema']['mach-number'].values()
        assert min((v['min'] for v in values)) >= cfg['fixed_ranges']['mach'][0]
        maximum = max((v['max'] for v in values))
        if not self.allow_upper_saturation:
            assert maximum <= cfg['fixed_ranges']['mach'][1], f'Mach maximum {maximum:.8g} exceeds fixed limit {cfg['fixed_ranges']['mach'][1]}; no frame autoscaling'
        timings = {}
        stage = time.perf_counter()
        periodic = periodic_settings(s, cfg)
        timings['periodic_settings_s'] = time.perf_counter() - stage
        cold = not self.warmed
        if cold:
            g.windows.set_window(window_id=1)
            g.windows.close_window(window_id=1)
            g.windows.open_window(window_id=1)
            s.scheme.eval('(cx-use-window-id 1)')
            g.contour['native-mach'].display()
            if self.scheme_transport:
                self.menu_string('/display/clear-annotations')
            else:
                s.tui.display.clear_annotations()
            g.windows.text.set_state(dict(visible=True, application=False, date=False))
            title = 'Absolute Mach number [-]'
            if self.allow_upper_saturation:
                title += f' (display capped at {cfg['fixed_ranges']['mach'][1]:.2f})'
            if self.scheme_transport:
                self.menu_string('/display/set/titles/right-top ' + json.dumps(title))
            else:
                s.tui.display.set.titles.right_top(json.dumps(title))
        annotation = f'Solution time: {actual:.12f} s'
        stage = time.perf_counter()
        if self.scheme_transport:
            self.menu_string('/display/set/titles/left-top ' + json.dumps(annotation))
        else:
            s.tui.display.set.titles.left_top(json.dumps(annotation))
        timings['time_annotation_s'] = time.perf_counter() - stage
        stage = time.perf_counter()
        g.contour['native-mach'].display()
        timings['field_refresh_s'] = time.perf_counter() - stage
        stage = time.perf_counter()
        if cold:
            camera = g.views.camera
            centre = cfg['camera']['centre_m']
            height = cfg['camera']['height_m']
            camera.projection(type='orthographic')
            camera.position(xyz=[*centre, 1])
            camera.target(xyz=[*centre, 0])
            camera.up_vector(xyz=[0, 1, 0])
            camera.field(width=height * cfg['width_px'] / cfg['height_px'], height=height)
            layout = cfg['legend_layout']
            g.windows.main.set_state(layout['main'])
            g.windows.scale.set_state(dict(layout['scale'], format='%.2f'))
            g.windows.text.set_state(layout['text'])
            g.views.save_view(view_name=self.view)
        else:
            g.views.restore_view(view_name=self.view)
        timings['fixed_camera_and_layout_s'] = time.perf_counter() - stage
        stage = time.perf_counter()
        if self.scheme_transport:
            self.menu_string('/display/re-render')
        else:
            s.tui.display.re_render()
        timings['rerender_s'] = time.perf_counter() - stage
        stage = time.perf_counter()
        g.picture.save_picture(file_name=str(path))
        timings['PNG_write_s'] = time.perf_counter() - stage
        rectangle = colour_bar_rectangle(path)
        layout = cfg['legend_layout']
        assert max((abs(a - b) for a, b in zip(rectangle, layout['expected_pixel_rectangles']['mach']))) <= layout['pixel_rectangle_tolerance']
        with Image.open(path) as im:
            assert im.size == (cfg['width_px'], cfg['height_px'])
        self.warmed = True
        timings['total_frame_s'] = time.perf_counter() - started
        record = dict(utc=now(), state='CANDIDATE_MACH_CAPTURE', cold_scene=cold, solution_time_s=actual, time_annotation=annotation, configuration=cfg, selected_fields=['mach'], periodic_instancing=periodic, camera_restore_method='Named native Fluent view; reset after every case/data reload', command_transport='Scheme ti-menu-load-string' if self.scheme_transport else 'Python TUI wrapper', pixel_rectangle=rectangle, timings=timings, display_upper_saturation_allowed=self.allow_upper_saturation, actual_Mach_maximum=maximum, upper_display_limit=cfg['fixed_ranges']['mach'][1], files=[dict(field='mach', file=str(path), byte=path.stat().st_size, sha256=sha(path))])
        if write_manifest:
            jwrite(manifest, record)
        return record
