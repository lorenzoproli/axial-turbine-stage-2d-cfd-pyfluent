"""Export native Fluent quality metrics for active two-dimensional cells."""
from data_schema import csv, json
from common import *
from pipeline import FLUIDS
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, ScalarFieldDataRequest, SurfaceDataType
import numpy as np

def export_quality(s, mesh_id, expected_cells=None):
    out = project_path(ROOT / '05_postprocessing' / 'qualita_mesh' / mesh_id)
    out.mkdir(parents=True, exist_ok=True)
    metadata = s.fields.field_data.scalar_fields()
    jwrite(out / 'campi_disponibili.json', metadata)
    names = list(metadata)
    desired = {}
    for metric, patterns in {'orthogonal_quality': ['orthogonal-quality', 'ortho-quality'], 'aspect_ratio': ['aspect-ratio'], 'equiangle_skewness': ['cell-equiangle-skew'], 'equivolume_skewness': ['cell-equivolume-skew'], 'cell_volume_m3': ['cell-volume', 'volume']}.items():
        exact = [n for n in names if n in patterns]
        partial = [n for n in names if any((p in n.lower() for p in patterns))]
        candidates = exact or partial
        if len(candidates) == 1:
            desired[metric] = candidates[0]
    if not desired:
        raise RuntimeError('Quality fields are ambiguous; inspect available_fields.json')
    geo = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=FLUIDS, data_types=[SurfaceDataType.FacesCentroid]))
    fields = {metric: s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name=field, node_value=False, boundary_value=False)) for metric, field in desired.items()}
    summary = []
    npz = {}
    n_total = 0
    target = out / 'qualita_per_cella_attiva.csv'
    assert not target.exists(), 'Export already exists; choose a different identifier'
    with target.open('x', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['zone', 'local_export_index_NOT_CELL_ID', 'x_m', 'y_m', 'z_m'] + list(fields))
        for iz, name in enumerate(FLUIDS):
            xyz = geo[name].face_centroids
            n = len(xyz)
            n_total += n
            arrays = [np.asarray(v[name]).reshape(-1) for v in fields.values()]
            assert all((len(v) == n and np.isfinite(v).all() for v in arrays))
            writer.writerows(((name, k, *map(float, xyz[k]), *(float(v[k]) for v in arrays)) for k in range(n)))
            npz[f'zone{iz}_centroids_m'] = xyz
            for metric, values in zip(fields, arrays):
                npz[f'zone{iz}_{metric}'] = values
                summary.append(dict(mesh=mesh_id, zone=name, metric=metric, native_field=desired[metric], active_cells=n, minimum=float(values.min()), q01=float(np.quantile(values, 0.01)), q05=float(np.quantile(values, 0.05)), median=float(np.median(values)), q95=float(np.quantile(values, 0.95)), q99=float(np.quantile(values, 0.99)), maximum=float(values.max()), unit='m3' if metric == 'cell_volume_m3' else '-'))
    if expected_cells is not None:
        assert n_total == expected_cells
    csvwrite(out / 'statistiche_qualita.csv', summary)
    np.savez_compressed(out / 'qualita_celle.npz', **npz)
    result = dict(mesh=mesh_id, utc=now(), physical_time_s=float(s.scheme.eval("(rpgetvar 'flow-time)")), active_cells=n_total, fields=desired, statistics=summary, index_note='Local exported-array indices; these are not global Fluent IDs', csv=dict(file=str(target), byte=target.stat().st_size, sha256=sha(target)))
    jwrite(out / 'esportazione_qualita.json', result)
    print('QUALITY_EXPORTED', mesh_id, n_total, desired, flush=True)
    return result
