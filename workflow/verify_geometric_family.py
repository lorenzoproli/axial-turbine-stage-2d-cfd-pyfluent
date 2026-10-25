"""Read-only comparison of baseline and systematic blade-wall geometry."""
from common import *
from pipeline import segments
import numpy as np

def distance(points, edges):
    a = edges[:, 0].astype(float)
    delta = edges[:, 1].astype(float) - a
    length2 = np.einsum('ij,ij->i', delta, delta)
    assert np.all(length2 > 0)
    values = []
    for start in range(0, len(points), 256):
        difference = points[start:start + 256, None, :2] - a[None, :, :]
        position = np.clip(np.einsum('pij,ij->pi', difference, delta) / length2, 0, 1)
        offset = difference - position[:, :, None] * delta[None, :, :]
        values.extend(np.sqrt(np.einsum('pij,pij->pi', offset, offset).min(axis=1)))
    return np.asarray(values)

def verify():
    rows = []
    sources = []
    reference = AUDIT / 'baseline_fields_geometry.npz'
    with np.load(reference) as baseline:
        for rid in ['M1', 'M2', 'M3']:
            old_mesh_folder = {'M1': 'M1_grossolana', 'M2': 'M2_media', 'M3': 'M3_fine'}[rid]
            source = project_path('03_simulazioni/convergenza_griglia/' + old_mesh_folder +
                '/mesh_sistematica_20261013/restart_native_v5/prova_breve/campo_interpolato.npz')
            with np.load(source) as target:
                assert float(target['solution_time_s']) == float(baseline['solution_time_s']) == 0.010653
                for zone, blade in [(2, 'Stator'), (3, 'Rotor')]:
                    old_vertices = np.unique(baseline[f'zone{zone}_vertices'][:, :2].astype(float), axis=0)
                    new_vertices = np.unique(target[f'zone{zone}_vertices'][:, :2].astype(float), axis=0)
                    old_edges = segments(baseline[f'zone{zone}_connectivity'], baseline[f'zone{zone}_vertices'])
                    new_edges = segments(target[f'zone{zone}_connectivity'], target[f'zone{zone}_vertices'])
                    old_edges = np.unique(old_edges.reshape(-1, 4), axis=0).reshape(-1, 2, 2)
                    new_edges = np.unique(new_edges.reshape(-1, 4), axis=0).reshape(-1, 2, 2)
                    a = distance(old_vertices, new_edges)
                    b = distance(new_vertices, old_edges)
                    rows.append(dict(mesh=rid, blade=blade, baseline_to_systematic_vertex_segment_max_m=float(a.max()), systematic_to_baseline_vertex_segment_max_m=float(b.max()), symmetric_vertex_segment_max_m=float(max(a.max(), b.max())), baseline_to_systematic_mean_m=float(a.mean()), systematic_to_baseline_mean_m=float(b.mean()), baseline_vertices=len(old_vertices), systematic_vertices=len(new_vertices), physical_time_s=0.010653))
            sources.append(dict(file=str(source), sha256=sha(source)))
    out = project_path(ROOT / '05_postprocessing/english_tables')
    csvwrite(out / 'blade_geometry_comparison.csv', rows)
    jwrite(out / 'blade_geometry_method.json', dict(utc=now(), sources=[dict(file=str(reference), sha256=sha(reference))] + sources, method='Bidirectional vertex-to-segment distances on native blade-wall polylines at the same physical phase; no fitted translation or geometric deformation.', limits='Distances include different curve tessellation. Native coordinates were exported as float32. This is a polyline comparison, not an exact CAD Hausdorff calculation.'))
    print(json.dumps(rows), flush=True)
    return rows
if __name__ == '__main__':
    verify()
