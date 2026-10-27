"""Restore the actual original rotor geometry before a fresh t=0 Hybrid start."""
from data_schema import csv, json
from common import *
from pipeline import FLUIDS, WALLS, snapshot, segments
from cfd import node_processes
from campaign_v2 import file_manifest
from verify_restart_geometry import verify_loaded_geometry
from verify_geometric_family import distance
from transcript_utils import close_transcript
from render_period import verified_motion
from quality_export import export_quality
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, SurfaceDataType
from scipy.spatial import cKDTree
import numpy as np

def clock(s):
    return dict(time_s=float(s.scheme.eval("(rpgetvar 'flow-time)")), step=int(s.scheme.eval("(rpgetvar 'time-step)")))

def geometry(s):
    surfaces = s.fields.field_data.surfaces()
    missing = [name for name in FLUIDS if name not in surfaces]
    if missing:
        s.settings.results.surfaces.create_multiple_zone_surfaces(zone_names=missing)
    values = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=FLUIDS + WALLS, data_types=[SurfaceDataType.Vertices, SurfaceDataType.FacesConnectivity], flatten_connectivity=True))
    result = {}
    for index, name in enumerate(FLUIDS + WALLS):
        result[f'zone{index}_vertices'] = values[name].vertices
        result[f'zone{index}_connectivity'] = values[name].connectivity
    return result

def bounds(g, index):
    values = g[f'zone{index}_vertices'].astype(float)
    return np.array([values.min(axis=0), values.max(axis=0)])

def nearest_error(a, b):
    a = np.unique(a[:, :2].astype(float), axis=0)
    b = np.unique(b[:, :2].astype(float), axis=0)
    assert len(a) == len(b), 'Physical wall node count changed'
    return float(max(cKDTree(a).query(b)[0].max(), cKDTree(b).query(a)[0].max()))

def periodic_check(s, tolerance):
    names = ['periodic_statore', 'periodic_statore_top', 'periodic_rotore', 'periodic_rotore_top']
    values = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=names, data_types=[SurfaceDataType.Vertices]))
    result = []
    for a, b in [(names[0], names[1]), (names[2], names[3])]:
        low = values[a].vertices[:, :2].astype(float) + [0, PITCH]
        high = values[b].vertices[:, :2].astype(float)
        error = float(max(cKDTree(low).query(high)[0].max(), cKDTree(high).query(low)[0].max()))
        assert error < tolerance, 'Translational periodic pair no longer matches'
        result.append(dict(from_zone=a, to_zone=b, pitch_m=PITCH, error_m=error))
    return result

def finite_positive(record):
    for field, zones in record['extrema'].items():
        assert all((value['finite'] for value in zones.values())), field + ' is nonfinite'
        if field in ['pressure', 'temperature', 'density']:
            assert min((value['min'] for value in zones.values())) > 0, field + ' is nonpositive'

def overlay(reference, restored, run_id):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    out = project_path(ROOT / 'results/figures/generated/campaign' / run_id / 'initial_rotor_position.png')
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6), layout='constrained')
    for g, color, width, label in [(reference, '#b35413', 1.3, 'Original t=0 blade profiles'), (restored, '#126486', 0.7, 'Restored systematic mesh profiles')]:
        for zone in [2, 3]:
            edges = segments(g[f'zone{zone}_connectivity'], g[f'zone{zone}_vertices'])
            for repeat in [-1, 0, 1]:
                shifted = edges.copy()
                shifted[:, :, 1] += repeat * PITCH
                ax.add_collection(LineCollection(shifted, colors=color, linewidths=width, label=label if zone == 2 and repeat == 0 else None))
    ax.set(xlim=(0.13, 0.265), ylim=(-0.09, 0.045), xlabel='Axial coordinate X [m]', ylabel='Tangential coordinate Y [m]', title=run_id + ' - rotor position restored before Hybrid Initialization')
    ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(alpha=0.2)
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return dict(file=str(out.relative_to(ROOT)), byte=out.stat().st_size, sha256=sha(out))

def initialise(s, run_cfg, cfg):
    run_id = run_cfg['id']
    target = case_directory(run_id)
    directory = project_path(ROOT / 'runs/initialization' / mesh_base_id(run_id))
    if directory.exists():
        raise FileExistsError('Initialisation output already exists; do not overwrite it.')
    directory.mkdir(parents=True)
    close_transcript(s)
    s.transcript.start(file_name=str(directory / 'initialization.trn'), write_to_stdout=False)
    reference_case = project_path(ROOT / cfg['initial_geometry_reference'])
    source = project_path(ROOT / run_cfg['source_case'])
    assert sha(reference_case) == cfg['initial_geometry_reference_sha256']
    assert sha(source) == run_cfg['source_case_sha256']
    s.settings.file.read_case(file_name=str(reference_case))
    original_clock = clock(s)
    assert original_clock == dict(time_s=0.0, step=0)
    reference = geometry(s)
    np.savez_compressed(directory / 'original_t0_geometry.npz', **reference)
    s.settings.file.read_case(file_name=str(source))
    setup = s.settings.setup.get_state()
    methods = s.settings.solution.methods.get_state()
    controls = s.settings.solution.controls.get_state()
    reports = s.settings.solution.report_definitions.get_state()
    source_clock = clock(s)
    verify_loaded_geometry(s, source)
    checkpoint_geometry = geometry(s)
    expected = int(run_cfg['expected_cells'])
    assert len(node_processes()) == 24 and int(s.fields.reduction.count(locations=FLUIDS)) == expected
    assert not s.scheme.eval("(rpgetvar 'adapt/dynamic?)")
    mesh = project_path(ROOT / run_cfg['source_mesh'])
    settings = project_path(ROOT / run_cfg['settings_file'])
    assert sha(mesh) == run_cfg['source_mesh_sha256'] and sha(settings) == run_cfg['settings_sha256']
    s.settings.file.read_mesh(file_name=str(mesh))
    s.settings.results.surfaces.create_multiple_zone_surfaces(zone_names=FLUIDS)
    s.settings.setup.mesh_interfaces.delete_all()
    s.settings.setup.mesh_interfaces.one_to_one_pairing(one_to_one_interface=False, proceed=True, delete_empty=True)
    for row in ['statore', 'rotore']:
        s.settings.mesh.modify_zones.make_periodic(zone_name='periodic_' + row + '_bottom', shadow_zone_name='periodic_' + row + '_top', rotate_periodic=False, create=True, auto_translation=False, direction=[0, PITCH, 0])
        s.settings.mesh.modify_zones.zone_name(zone_name='periodic_' + row + '_bottom', new_name='periodic_' + row)
    s.settings.mesh.modify_zones.zone_type(zone_names=['inlet'], new_type='pressure-inlet')
    before = geometry(s)
    raw_delta = bounds(reference, 1) - bounds(before, 1)
    assert np.max(abs(raw_delta[:, [0, 2]])) < cfg['geometry_tolerance_m']
    assert abs(raw_delta[0, 1] - raw_delta[1, 1]) < cfg['geometry_tolerance_m']
    offset = float(raw_delta[:, 1].mean())
    print('RESTORING_ORIGINAL_ROTOR_POSITION', run_id, 'offset_y_m=', offset, flush=True)
    s.settings.mesh.modify_zones.translate_zone(zone_names=[FLUIDS[1]], offset=[0, offset, 0])
    s.settings.file.read_settings(file_name=str(settings))
    setup_case = directory / 'restored_mesh_setup.cas.h5'
    s.settings.file.cff_files = True
    s.settings.file.write_case(file_name=str(setup_case))
    s.settings.file.read_case(file_name=str(setup_case))
    s.settings.file.read_settings(file_name=str(settings))
    restored = geometry(s)
    errors = []
    for index, wall in [(2, WALLS[0]), (3, WALLS[1])]:
        predicted = before[f'zone{index}_vertices'].astype(float).copy()
        if index == 3:
            predicted[:, 1] += offset
        exact_error = nearest_error(predicted, restored[f'zone{index}_vertices'])
        assert exact_error < cfg['geometry_tolerance_m'], 'Restoration was not the expected rigid translation'
        old = reference[f'zone{index}_vertices']
        new = restored[f'zone{index}_vertices']
        old_edges = segments(reference[f'zone{index}_connectivity'], old)
        new_edges = segments(restored[f'zone{index}_connectivity'], new)
        polyline_error = float(max(distance(old, new_edges).max(), distance(new, old_edges).max()))
        assert polyline_error < cfg['blade_polyline_tolerance_m'], 'Original and restored blade profiles do not agree'
        errors.append(dict(wall=wall, rigid_translation_error_m=exact_error, original_t0_bidirectional_vertex_segment_error_m=polyline_error, restored_min_xy_m=new[:, :2].min(axis=0).astype(float).tolist(), restored_max_xy_m=new[:, :2].max(axis=0).astype(float).tolist()))
    assert np.max(abs(bounds(reference, 1) - bounds(restored, 1))) < cfg['geometry_tolerance_m']
    assert json.dumps(setup, sort_keys=True) == json.dumps(s.settings.setup.get_state(), sort_keys=True), 'Translation altered physical setup'
    periodic = periodic_check(s, cfg['geometry_tolerance_m'])
    s.settings.mesh.check()
    s.settings.mesh.quality()
    s.scheme.eval("(rpsetvar 'flow-time 0.0)")
    s.scheme.eval("(rpsetvar 'time-step 0)")
    pre_hybrid = clock(s)
    assert pre_hybrid == dict(time_s=0.0, step=0)
    init_settings = s.settings.solution.initialization.get_state()
    assert init_settings['reference_frame'] == cfg['reference_frame']
    print('HYBRID_AT_ORIGINAL_POSITION_START', run_id, pre_hybrid, flush=True)
    s.settings.solution.initialization.hybrid_initialize()
    assert clock(s) == dict(time_s=0.0, step=0)
    after = geometry(s)
    for index in [2, 3]:
        assert nearest_error(restored[f'zone{index}_vertices'], after[f'zone{index}_vertices']) < cfg['geometry_tolerance_m']
    for label, old, current in [('setup', setup, s.settings.setup.get_state()), ('methods', methods, s.settings.solution.methods.get_state()), ('controls', controls, s.settings.solution.controls.get_state()), ('report definitions', reports, s.settings.solution.report_definitions.get_state())]:
        assert json.dumps(old, sort_keys=True) == json.dumps(current, sort_keys=True), label + ' changed during Hybrid'
    for name in s.settings.solution.monitor.report_files.get_object_names():
        s.settings.solution.monitor.report_files[name].file_name = str(directory / (name + '.out'))
    s.settings.file.auto_save.data_frequency = 0
    s.settings.solution.run_calculation.transient_controls.time_step_size = cfg['timestep_s']
    s.settings.solution.run_calculation.transient_controls.max_iter_per_time_step = cfg['inner_iterations_per_step']
    for equation in s.settings.solution.monitor.residual.equations.get_object_names():
        s.settings.solution.monitor.residual.equations[equation].check_convergence = False
    initial = snapshot(s, directory / 'hybrid_initial_fields.npz')
    finite_positive(initial)
    quality = export_quality(s, run_id + '_initial_position', expected)
    checkpoint = directory / 'hybrid_initial.cas.h5'
    s.settings.file.write_case_data(file_name=str(checkpoint))
    manifest = file_manifest(sorted(directory.glob('hybrid_initial.*.h5')))
    verify_loaded_geometry(s, checkpoint)
    image = overlay(reference, after, run_id)
    steps = cfg['smoke_steps']
    s.settings.solution.run_calculation.dual_time_iterate(time_step_count=steps, max_iter_per_step=cfg['inner_iterations_per_step'])
    smoke = snapshot(s, directory / 'smoke_fields.npz')
    finite_positive(smoke)
    assert abs(smoke['solution_time_s'] - steps * cfg['timestep_s']) < 1e-12
    motion = verified_motion(initial['solution_time_s'], initial['rotor_wall_node_centroid'][1], smoke['solution_time_s'], smoke['rotor_wall_node_centroid'][1])
    assert int(s.fields.reduction.count(locations=FLUIDS)) == expected and (not s.scheme.eval("(rpgetvar 'adapt/dynamic?)"))
    s.settings.file.write_case_data(file_name=str(directory / 'smoke_final.cas.h5'))
    close_transcript(s)
    record = dict(utc=now(), state='ORIGINAL_POSITION_T0_HYBRID_AND_SIX_STEP_SMOKE_VERIFIED', run_id=run_id, reference_case=str(reference_case), reference_sha256=sha(reference_case), reference_clock=original_clock, source_case=str(source), source_sha256=sha(source), source_clock=source_clock, native_mesh=str(mesh), native_mesh_sha256=sha(mesh), settings_file=str(settings), settings_sha256=sha(settings), geometry_restoration_method='Verified native raw mesh and native settings transfer; rotor aligned to the original t=0 case before Hybrid. No DAT/IP read.', checkpoint_to_original_offset_y_m=float((bounds(reference, 1) - bounds(checkpoint_geometry, 1))[:, 1].mean()), rotor_restoration_offset_y_m=offset, restoration_before_hybrid=True, pre_hybrid_clock=pre_hybrid, initial_clock=dict(time_s=0.0, step=0), initialization_settings=init_settings, geometry_checks=errors, periodic_pairs=periodic, physical_setup_unchanged=True, data_or_IP_loaded=False, old_BDF_history_loaded=False, automatic_mesh_adaptation_active=False, initial_fields=initial, smoke_fields=smoke, smoke_motion=motion, initial_checkpoint=str(checkpoint), manifest_initial_checkpoint=manifest, quality_evidence=str(project_path(ROOT / '05_postprocessing/qualita_mesh' / (run_id + '_initial_position') / 'esportazione_qualita.json')), position_overlay=image, smoke_excluded_from_main_run=True)
    jwrite(directory / 'hybrid_initialization_verified.json', record)
    text(directory / 'README.md', '# Original-position Hybrid start\n\nThe original historical t=0 case supplies the rotor geometry. The verified systematic case supplies mesh and physical setup. Only the rotor fluid zone is translated; periodic pairs, blade polylines and unchanged setup are checked. Physical time and step are set to zero before Hybrid. No historical data or IP file is read. The six-step smoke test is separate; the main run reloads the untouched fresh initialized checkpoint at t=0.\n')
    append_status(run_id + ': original rotor position restored before Hybrid at t=0/step=0; physical setup and periodicity preserved, quality exported, six-step motion/finite-field smoke test verified. Main run will reload the fresh initialized checkpoint; smoke steps are excluded. Evidence: ' + str((directory / 'hybrid_initialization_verified.json').relative_to(ROOT)))
    print('INITIAL_POSITION_HYBRID_VERIFIED', run_id, flush=True)
    return (checkpoint, record)
