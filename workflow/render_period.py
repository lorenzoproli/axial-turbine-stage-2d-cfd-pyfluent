"""Verified periodic copies with a fixed camera and fixed legend over a complete period."""
from data_schema import csv, json
from common import *
from english_labels import install
install()
from pipeline import triangulate, segments
import numpy as np, subprocess

def verified_motion(previous_time, previous_y, time, y):
    """Accept physical motion or native periodic wraps by integer pitches only."""
    expected = VY * (time - previous_time)
    raw = y - previous_y
    wraps = int(round((raw - expected) / PITCH))
    error = raw - expected - wraps * PITCH
    assert abs(error) < 1e-07, f'Inconsistent rotor displacement: error {error} m'
    return dict(t_s=time, native_y_displacement_m=raw, expected_y_displacement_m=expected, native_periodic_wraps=wraps, pitch_modulo_error_m=error)

def render_period(run_id='T400', diagnostic_preview=False, output_name=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.labelsize': 11, 'axes.titlesize': 13, 'xtick.labelsize': 10, 'ytick.labelsize': 10})
    import matplotlib.tri as mtri
    from matplotlib.collections import LineCollection
    import imageio_ffmpeg
    source = case_directory(run_id)
    meta = json.loads((source / 'progress.json').read_text())
    assert meta['completed_steps'] == meta['planned_steps']
    analysis = json.loads(project_path(ROOT / '05_postprocessing/campagna' / run_id / 'analysis.json').read_text())
    assert analysis['monitor_periodicity_within_proposed_criteria'], 'Window periodicity is unconfirmed'
    files = sorted((project_path(meta.get('current_output', source)) / 'campi_in_fase').glob('step_*.npz'))
    if diagnostic_preview and len(files) == 101:
        files = files[::25]
    assert len(files) == (5 if diagnostic_preview else 101), 'Unexpected native field count'
    samples = len(files) - 1
    cfg = json.loads((CONFIG_DIR / 'workflow_config.json').read_text())['render']
    if diagnostic_preview:
        cfg = dict(cfg, fps=1)
    visible = cfg['visible_passages']
    copies = cfg.get('periodic_copies_per_row', 9)
    assert copies % 2 == 1 and copies >= visible + 4
    with (AUDIT / 'periodicita_geometrica.csv').open(encoding='utf-8-sig') as f:
        periodic = list(csv.DictReader(f))
    assert len(periodic) == 2 and all((r['verified'].lower() == 'true' for r in periodic))
    if run_id in ['M1', 'M2', 'M3']:
        receipt = json.loads((project_path(meta['initial_checkpoint']).parent / 'verifica_restart.json').read_text())
        assert len(receipt['periodic_boundaries_verified']) == 2 and all((v['error_m'] < 1e-07 for v in receipt['periodic_boundaries_verified']))
    with np.load(AUDIT / 'baseline_fields_geometry.npz') as z:
        ref = float(np.unique(z['zone3_vertices'].astype(float), axis=0)[:, 1].mean())
        reference_walls = np.concatenate([z['zone2_vertices'][:, :2], z['zone3_vertices'][:, :2]])
        camera_y = float(np.unique(z['zone2_vertices'].astype(float), axis=0)[:, 1].mean())
    with np.load(files[0]) as z:
        initial = float(np.unique(z['zone3_vertices'].astype(float), axis=0)[:, 1].mean())
    offset = np.arange(-(copies // 2), copies // 2 + 1)
    indices = {0: offset.tolist(), 1: (offset + int(round((ref - initial) / PITCH))).tolist()}
    extrema = {f: [np.inf, -np.inf] for f in ['mach-number', 'pressure']}
    times = []
    bounds = []
    motion = []
    previous = None
    cumulative_wraps = 0
    frame_indices = []
    for p in files:
        with np.load(p) as z:
            t = float(z['solution_time_s'])
            times.append(t)
            center = np.unique(z['zone3_vertices'].astype(float), axis=0).mean(axis=0)
            if previous is not None:
                record = verified_motion(previous[0], previous[1][1], t, float(center[1]))
                cumulative_wraps += record['native_periodic_wraps']
                motion.append(record)
            previous = (t, center)
            current_indices = {0: indices[0], 1: [k - cumulative_wraps for k in indices[1]]}
            frame_indices.append(current_indices)
            for iz in [0, 1]:
                xy = z[f'zone{iz}_vertices'][:, :2].astype(float)
                for k in current_indices[iz]:
                    lo = xy.min(axis=0)
                    hi = xy.max(axis=0)
                    lo[1] += k * PITCH
                    hi[1] += k * PITCH
                    bounds.append([lo, hi])
                for field in extrema:
                    v = z[f'zone{iz}_{field}']
                    assert np.isfinite(v).all()
                    extrema[field] = [min(extrema[field][0], float(v.min())), max(extrema[field][1], float(v.max()))]
    assert np.allclose(np.diff(times), T / samples, rtol=1e-07, atol=1e-12) and abs(times[-1] - times[0] - T) < 1e-10
    lo = np.array([float(reference_walls[:, 0].min()) - 0.065, camera_y - visible * PITCH / 2])
    hi = np.array([float(reference_walls[:, 0].max()) + 0.075, camera_y + visible * PITCH / 2])
    ranges = {'mach-number': [0, float(np.ceil(extrema['mach-number'][1] * 20) / 20)], 'pressure': [float(np.floor(extrema['pressure'][0] / 5000) * 5000), float(np.ceil(extrema['pressure'][1] / 5000) * 5000)]}
    category = 'campagna_mesh_sistematiche' if run_id in ['M1', 'M2', 'M3'] else 'riproduzione_mesh_adattata'
    directory = project_path(ROOT / '07_animazioni' / category / run_id / (output_name or ('preview_three_passages_en' if diagnostic_preview else 'periodo_finale')))
    assert not directory.exists(), 'Choose a new identifier; existing results are preserved'
    frames = directory / 'frames'
    frames.mkdir(parents=True)
    scene = dict(utc=now(), run_id=run_id, status='RENDERING_IN_PROGRESS', width_px=cfg['width_px'], height_px=cfg['height_px'], fps=cfg['fps'], solution_time_start_s=times[0], solution_time_end_s=times[-1], physical_sample_interval_s=T / samples, diagnostic_preview=diagnostic_preview, samples_per_period=samples, rotor_motion_reference='Centroid of unique physical wall nodes; MPI duplicates excluded', passages_per_row=copies, visible_passages=visible, initial_copy_indices=indices, copy_indices_per_frame=frame_indices, periodic_translation_m=[0, PITCH, 0], camera=dict(xlim_m=[float(lo[0]), float(hi[0])], ylim_m=[float(lo[1]), float(hi[1])], projection='XY_orthographic', axes_box_normalized=[0.065, 0.095, 0.8, 0.85], colorbar_box_normalized=[0.9, 0.12, 0.022, 0.77]), legend_ranges=ranges, raw_extrema=extrema, pressure_reference='absolute; operating pressure 0 Pa', mach_reference='absolute', note='Nine verified periodic copies per row; fixed camera cropped to three pitches. Partial blades enter and leave the fixed view as the rotor moves. Native integer-pitch wrapping is compensated only through verified periodic translations.', renderer=dict(file=str(Path(__file__).relative_to(ROOT)), sha256=sha(Path(__file__))), workflow_config_sha256=sha(CONFIG_DIR / 'workflow_config.json'), source_files=[dict(file=str(p), sha256=sha(p)) for p in files])
    jwrite(directory / 'render_config.json', scene)
    text(directory / 'renderer_source.py', Path(__file__).read_text())
    assert sha(directory / 'renderer_source.py') == scene['renderer']['sha256']
    csvwrite(directory / 'verifica_moto_rotore.csv', motion)
    receipts = []
    verified_axes = None
    for n, p in enumerate(files):
        with np.load(p) as z:
            t = float(z['solution_time_s'])
            data = [(z[f'zone{i}_vertices'].astype(float), triangulate(z[f'zone{i}_connectivity']), {f: z[f'zone{i}_{f}'] for f in extrema}) for i in [0, 1]]
            walls = [segments(z[f'zone{i}_connectivity'], z[f'zone{i}_vertices']) for i in [2, 3]]
        for field, short, label, cmap in [('mach-number', 'mach', 'Absolute Mach number [-]', 'viridis'), ('pressure', 'pressure', 'Absolute static pressure [Pa]', 'plasma')]:
            fig = plt.figure(figsize=(cfg['width_px'] / 120, cfg['height_px'] / 120), dpi=120)
            ax = fig.add_axes(scene['camera']['axes_box_normalized'])
            cax = fig.add_axes(scene['camera']['colorbar_box_normalized'])
            for iz, (xyz, tri, values) in enumerate(data):
                for k in frame_indices[n][iz]:
                    xy = xyz[:, :2].copy()
                    xy[:, 1] += k * PITCH
                    if xy[:, 1].max() < lo[1] or xy[:, 1].min() > hi[1]:
                        continue
                    coordinates = xy[tri]
                    keep = (coordinates[:, :, 0].max(axis=1) >= lo[0]) & (coordinates[:, :, 0].min(axis=1) <= hi[0]) & (coordinates[:, :, 1].max(axis=1) >= lo[1]) & (coordinates[:, :, 1].min(axis=1) <= hi[1])
                    topology = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles=tri[keep])
                    artist = ax.tripcolor(topology, values[field], shading='gouraud', cmap=cmap, vmin=ranges[field][0], vmax=ranges[field][1], rasterized=True)
            for iz, lines in enumerate(walls):
                for k in frame_indices[n][iz]:
                    line = lines.copy()
                    line[:, :, 1] += k * PITCH
                    ax.add_collection(LineCollection(line, colors='#161616', linewidths=0.6))
            ax.set(xlim=scene['camera']['xlim_m'], ylim=scene['camera']['ylim_m'], xlabel='Axial X [m]', ylabel='Tangential Y [m]')
            ax.set_aspect('equal')
            ax.set_title(label + f' | {visible} visible passages', loc='left', fontsize=13)
            ax.text(0.99, 0.985, f'Solution time: {t:.12f} s', ha='right', va='top', transform=ax.transAxes, fontsize=12, fontfamily='monospace', bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'))
            ax.text(0.01, 0.02, f'Fixed stator | Rotor Vy=-150 m/s | t/T={t / T:.5f} | phase mod T={t / T % 1:.5f}', transform=ax.transAxes, fontsize=9, bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'))
            fig.colorbar(artist, cax=cax, label=label)
            out = frames / f'frame_{n:04d}_{short}.png'
            fig.savefig(out)
            actual_axes = list(ax.get_position().bounds)
            if verified_axes is None:
                verified_axes = actual_axes
            assert np.allclose(actual_axes, verified_axes, rtol=0, atol=1e-12), 'Inquadratura pixel differente fra frame o fields'
            plt.close(fig)
            receipts.append(dict(frame=n, field=short, solution_time_s=t, file=str(out), byte=out.stat().st_size, sha256=sha(out), axes_box_normalized=actual_axes))
        if n % 10 == 0:
            print('PERIOD_RENDER_PROGRESS', run_id, n, len(files), flush=True)
    csvwrite(directory / 'manifest_frames_sha256.csv', receipts)
    videos = []
    for short in ['mach', 'pressure']:
        out = directory / (run_id + '_' + short + '_periodo_finale.mp4')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-framerate', str(cfg['fps']), '-i', str(frames / ('frame_%04d_' + short + '.png')), '-frames:v', str(samples), '-c:v', 'libx264', '-threads', '2', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)], check=True)
        reader = imageio_ffmpeg.read_frames(str(out))
        video_meta = next(reader)
        reader.close()
        assert tuple(video_meta['size']) == (cfg['width_px'], cfg['height_px'])
        videos.append(dict(file=str(out), byte=out.stat().st_size, sha256=sha(out), metadata=video_meta, frame_count=samples))
    scene.update(status='MP4_ENCODED_VISUAL_REVIEW_REQUIRED', videos=videos, endpoint_frame_saved_not_encoded=True, axes_box_verified_identical_all_fields_frames=verified_axes)
    jwrite(directory / 'render_config.json', scene)
    append_status(f'Animations {run_id} generated from a complete period: {samples} encoded frames, {len(files)} source frames per field, 1920x1080, fixed camera/legends and physical Fluent time. Coarse diagnostic sampling: {diagnostic_preview}. Visual inspection of initial, intermediate and final frames is required.')
    return scene
if __name__ == '__main__':
    import sys
    render_period(sys.argv[1] if len(sys.argv) > 1 else 'T400', diagnostic_preview='--preview' in sys.argv)
