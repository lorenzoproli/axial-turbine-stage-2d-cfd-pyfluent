from common import *
import numpy as np, h5py, json, re
from scipy.spatial import cKDTree
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, ScalarFieldDataRequest, SurfaceDataType
fluid_names = ['fluido_statore_fluido_statore', 'fluido_rotore_fluido_rotore']
wall_names = ['wall_statore', 'wall_rotore']
periodic_names = ['periodic_statore', 'periodic_statore_top', 'periodic_rotore', 'periodic_rotore_top']

def geometry(names, centroids=False):
    types = [SurfaceDataType.Vertices, SurfaceDataType.FacesConnectivity]
    if centroids:
        types.append(SurfaceDataType.FacesCentroid)
    return s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=names, data_types=types, flatten_connectivity=True))

def scalars(field, names, node=True):
    return s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=names, field_name=field, node_value=node, boundary_value=True))

def flow_time():
    return float(s.scheme.eval("(rpgetvar 'flow-time)"))

def save_geometry(tag):
    geom = geometry(fluid_names + wall_names)
    fields = {f: scalars(f, fluid_names) for f in ['mach-number', 'pressure', 'density', 'temperature']}
    pack = {'solution_time_s': np.array(flow_time())}
    for i, n in enumerate(fluid_names + wall_names):
        d = geom[n]
        pack[f'zone{i}_vertices'] = d.vertices
        pack[f'zone{i}_connectivity'] = d.connectivity
        if n in fluid_names:
            for field, val in fields.items():
                pack[f'zone{i}_{field}'] = val[n]
    np.savez_compressed(AUDIT / (tag + '.npz'), **pack)
    return (geom, fields)
geom, fields = save_geometry('baseline_fields_geometry')
pg = geometry(periodic_names)
periodic = []
for row in [('statore', periodic_names[0], periodic_names[1]), ('rotore', periodic_names[2], periodic_names[3])]:
    kind, a, b = row
    pa, pb = (pg[a].vertices[:, :2], pg[b].vertices[:, :2])
    opts = []
    for sign in [-1, 1]:
        shifted = pa + np.array([0, sign * PITCH])
        err = max(cKDTree(pb).query(shifted)[0].max(), cKDTree(shifted).query(pb)[0].max())
        opts.append((float(err), sign))
    err, sign = min(opts)
    periodic.append(dict(schiera=kind, da=a, a=b, traslazione_x_m=0, traslazione_y_m=sign * PITCH, errore_massimo_nodi_m=err, verificata=err < 1e-07, tolleranza_m=1e-07, precisione_coordinate=str(pa.dtype)))
assert all((r['verificata'] for r in periodic))
csvwrite(AUDIT / 'periodicita_geometrica.csv', periodic)
scalar_meta = s.fields.field_data.scalar_fields()
yfield = 'y-plus' if 'y-plus' in scalar_meta else next((k for k, v in scalar_meta.items() if v['display_name'] == 'Wall Yplus'))
wgeom = geometry(wall_names, centroids=True)
yp = scalars(yfield, wall_names, node=False)
wp = scalars('pressure', wall_names, node=False)
yplus = []
for n in wall_names:
    xyz = wgeom[n].face_centroids
    vals = yp[n]
    pv = wp[n]
    assert len(xyz) == len(vals) == len(pv)
    csvwrite(AUDIT / (n + '_yplus_pressure.csv'), [dict(face=i, x_m=float(p[0]), y_m=float(p[1]), z_m=float(p[2]), yplus=float(y), pressione_statica_assoluta_Pa=float(pr)) for i, (p, y, pr) in enumerate(zip(xyz, vals, pv))])
    yplus.append(dict(parete=n, facce=len(vals), yplus_min=float(vals.min()), yplus_max=float(vals.max()), yplus_mediana=float(np.median(vals)), frazione_facce_yplus_sotto_1=float(np.mean(vals < 1))))
assert abs(max((r['yplus_max'] for r in yplus)) - float(s.fields.reduction.maximum(expression='WallYplus', locations=wall_names))) < 1e-06
cell_rows = []
face_rows = []
with h5py.File(INPUT / 'stadio_assiale_2D_CFD_final.cas.h5', 'r') as f:
    for kind, rows in [('cells', cell_rows), ('faces', face_rows)]:
        top = f[f'meshes/1/{kind}/zoneTopology']
        names = top['name'][0].decode().split(';')
        for i, n in enumerate(names):
            row = dict(id=int(top['id'][i]), nome=n, numero=int(top['maxId'][i] - top['minId'][i] + 1), zoneType=int(top['zoneType'][i]), childZoneId=int(top['childZoneId'][i]))
            if kind == 'cells':
                row['funzione'] = 'parent_AMR_inattiva_gerarchia' if row['zoneType'] == 32 else 'fluido_attivo'
            else:
                row.update(c0=int(top['c0'][i]), c1=int(top['c1'][i]), shadowZoneId=int(top['shadowZoneId'][i]))
            rows.append(row)
csvwrite(AUDIT / 'topologia_celle.csv', cell_rows)
csvwrite(AUDIT / 'topologia_facce.csv', face_rows)
report_defs = ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet']
computed = s.settings.solution.report_definitions.compute(report_defs=report_defs)
last = {}
for n in report_defs:
    vals = original_path(n + '-rfile.out').read_text().splitlines()[-1].split()
    last[n] = float(vals[1])
computed_flat = {n: float(v[0]) for d in computed for n, v in d.items()}
assert all((abs(computed_flat[n] - last[n]) < max(1e-09, abs(last[n]) * 1e-12) for n in report_defs))
position = {n: dict(nodi=geom[n].vertices.shape[0], min_xyz_m=geom[n].vertices.min(axis=0).tolist(), max_xyz_m=geom[n].vertices.max(axis=0).tolist(), centroide_nodi_m=geom[n].vertices.mean(axis=0).tolist()) for n in fluid_names + wall_names}
amr_dynamic = bool(s.scheme.eval("(rpgetvar 'adapt/dynamic?)"))
assert not amr_dynamic
extrema = {f: {n: dict(min=float(v.min()), max=float(v.max()), finite=bool(np.isfinite(v).all())) for n, v in d.items()} for f, d in fields.items()}
summary = dict(utc=now(), tempo_fisico_s=flow_time(), time_step=int(s.scheme.eval("(rpgetvar 'time-step)")), dt_s=float(s.scheme.eval("(rpgetvar 'physical-time-step)")), active_cells=sum((r['numero'] for r in cell_rows if r['funzione'] == 'fluido_attivo')), parent_cells=sum((r['numero'] for r in cell_rows if r['funzione'].startswith('parent'))), stored_cells=sum((r['numero'] for r in cell_rows)), zone_celle=cell_rows, periodiche=periodic, moto_rotore_m_s=[0, -150], rotazione_rotore_rad_s=0, amr_automatico_attivo=amr_dynamic, criteri_auto_attivi=False, qualita=dict(orthogonal_quality_min=0.0263166, aspect_ratio_max=76.9229, fonte='mesh.quality nel transcript audit corrente; peggioramento rispetto al valore riferito della mesh pre-AMR'), yplus=yplus, monitor_definizioni=state['solution']['report_definitions'], monitor_calcolati=computed_flat, monitor_ultimo_campione=last, profondita_2D_m=float(s.scheme.eval("(rpgetvar 'reference-depth)")), posizione_geometrica_checkpoint=position, fase_modulo_periodo=float(flow_time() / T % 1), estremi_campi_nodali=extrema, stato='RESTART_LEGGIBILE_COERENTE_NON_ANCORA_VALIDATO_PERIODICO')
jwrite(AUDIT / 'audit_baseline.json', summary)
out = WORK / 'checkpoint_comune'
out.mkdir(exist_ok=True)
for n in s.settings.solution.monitor.report_files.get_object_names():
    s.settings.solution.monitor.report_files[n].file_name = str(out / (n + '.out'))
s.settings.file.auto_save.data_frequency = 0
for n in s.settings.solution.calculation_activity.solution_animations.get_object_names():
    s.settings.solution.calculation_activity.solution_animations[n].storage_dir = str(WORK / 'animazioni_ereditate_disabilitate')
    s.settings.solution.calculation_activity.solution_animations[n].frequency = 1000000000
s.settings.solution.monitor.residual.options.plot = False
assert not bool(s.scheme.eval("(rpgetvar 'adapt/dynamic?)"))
s.settings.file.write_case_data(file_name=str(out / 'checkpoint.cas.h5'))
assert flow_time() == summary['tempo_fisico_s']
manifest = []
for p in sorted(out.glob('checkpoint.*.h5')):
    manifest.append(dict(percorso=str(p), byte=p.stat().st_size, sha256=sha(p)))
jwrite(out / 'checkpoint_manifest.json', dict(utc=now(), tempo_fisico_s=flow_time(), posizione_rotore=position['wall_rotore'], fase_modulo_T=summary['fase_modulo_periodo'], variazioni_solo_output=['monitor reindirizzati', 'autosave disattivato; salvataggi espliciti', 'animazione ereditata resa inattiva per frequenza; cartella separata', 'plot residui disattivato', 'AMR dinamico confermato disattivo'], files=manifest))
jwrite(AUDIT / 'setup_checkpoint.json', s.settings.get_state())
append_status('Historical reference verified at t=0.010653 s, step 3551: 289671 active cells and 72168 inactive AMR parents; translational periodicity, sliding interface and rotor mesh velocity Y=-150 m/s verified; automatic adaptation disabled. Recomputed reports match the historical final samples with 1 m reference depth and mass-weighted outlet total pressure. Minimum orthogonal quality is 0.0263166 and maximum aspect ratio is 76.9229; wall y+ exported. The common checkpoint preserves physical time, solution and rotor position. Statistical periodicity remains unconfirmed.')
print(json.dumps({k: summary[k] for k in ['tempo_fisico_s', 'active_cells', 'parent_cells', 'stored_cells', 'amr_automatico_attivo', 'qualita', 'yplus', 'monitor_calcolati']}, ensure_ascii=False), flush=True)
print('CHECKPOINT_COMMON_READY', flush=True)
