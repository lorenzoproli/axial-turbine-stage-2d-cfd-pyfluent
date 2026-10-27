"""Compare loaded blade geometry with coordinates in the saved native HDF5 case."""
from data_schema import csv, json
from common import *
from pipeline import WALLS
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, SurfaceDataType
import numpy as np, h5py
from scipy.spatial import cKDTree

def saved_wall_coordinates(case, wall):
    with h5py.File(case, 'r') as f:
        mesh = f['meshes/1']
        top = mesh['faces/zoneTopology']
        names = top['name'][0].decode().split(';')
        i = names.index(wall)
        first, last = (int(top['minId'][i]), int(top['maxId'][i]))
        ids = []
        for section in mesh['faces/nodes'].values():
            start = int(section.attrs['minId'][0])
            end = int(section.attrs['maxId'][0])
            a, b = (max(first, start), min(last, end))
            if a > b:
                continue
            offsets = np.r_[0, np.cumsum(section['nnodes'][()].astype(np.int64))]
            ids.extend(section['nodes'][int(offsets[a - start]):int(offsets[b - start + 1])].tolist())
        ids = np.unique(np.array(ids, dtype=np.int64))
        assert len(ids) > 0
        points = []
        for section in mesh['nodes/coords'].values():
            start = int(section.attrs['minId'][0])
            end = int(section.attrs['maxId'][0])
            keep = ids[(ids >= start) & (ids <= end)]
            if len(keep):
                points.append(section[()][keep - start, :2])
        return np.unique(np.concatenate(points), axis=0)

def verify_loaded_geometry(s, case):
    data = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=WALLS, data_types=[SurfaceDataType.Vertices]))
    rows = []
    for wall in WALLS:
        source = saved_wall_coordinates(case, wall)
        loaded = np.unique(data[wall].vertices[:, :2].astype(float), axis=0)
        error = max(cKDTree(source).query(loaded)[0].max(), cKDTree(loaded).query(source)[0].max())
        assert len(source) == len(loaded) and error < 1e-07, 'Restart geometry differs from the saved case'
        rows.append(dict(wall=wall, physical_nodes=len(source), maximum_error_m=float(error), saved_min_xy_m=source.min(axis=0).tolist(), saved_max_xy_m=source.max(axis=0).tolist()))
    return rows
