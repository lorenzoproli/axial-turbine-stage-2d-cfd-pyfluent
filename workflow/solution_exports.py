from data_schema import csv, json
from common import *
from pipeline import snapshot, FLUIDS, WALLS
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, ScalarFieldDataRequest, SurfaceDataType
import numpy as np

def capture(s, directory, tag, fields=None):
    directory = project_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (tag + '.npz')
    assert not output.exists(), 'Frame already exists; preserve the existing output'
    result = snapshot(s, output, fields=fields)
    geo = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=WALLS, data_types=[SurfaceDataType.FacesCentroid]))
    scalar = {f: s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=WALLS, field_name=f, node_value=False, boundary_value=True)) for f in ['pressure', 'y-plus']}
    wallstats = []
    paths = [output]
    for wall in WALLS:
        xyz = geo[wall].face_centroids
        p = scalar['pressure'][wall]
        yp = scalar['y-plus'][wall]
        assert len(xyz) == len(p) == len(yp) and np.isfinite(p).all() and np.isfinite(yp).all()
        csvpath = directory / (tag + '_' + wall + '.csv')
        assert not csvpath.exists()
        csvwrite(csvpath, [dict(physical_time_s=result['solution_time_s'], local_index=i, x_m=float(v[0]), y_m=float(v[1]), pressione_statica_assoluta_Pa=float(pr), yplus=float(y)) for i, (v, pr, y) in enumerate(zip(xyz, p, yp))])
        wallstats.append(dict(wall=wall, faces=len(yp), yplus_min=float(yp.min()), yplus_max=float(yp.max()), yplus_median=float(np.median(yp)), fraction_yplus_lt1=float(np.mean(yp < 1))))
        paths.append(csvpath)
    result.update(tag=tag, phase_mod_T=result['solution_time_s'] / T % 1, walls=wallstats, manifest=[dict(file=str(p), byte=p.stat().st_size, sha256=sha(p)) for p in paths])
    jwrite(directory / (tag + '_manifest.json'), result)
    return result
