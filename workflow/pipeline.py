from common import *
import numpy as np
from ansys.fluent.core.fields.field_data_interfaces import SurfaceFieldDataRequest, ScalarFieldDataRequest, SurfaceDataType
FLUIDS = ['fluido_statore_fluido_statore', 'fluido_rotore_fluido_rotore']
WALLS = ['wall_statore', 'wall_rotore']

def snapshot(s, p, fields=None):
    geo = s.fields.field_data.get_field_data(SurfaceFieldDataRequest(surfaces=FLUIDS + WALLS, data_types=[SurfaceDataType.Vertices, SurfaceDataType.FacesConnectivity], flatten_connectivity=True))
    data = {'solution_time_s': np.array(float(s.scheme.eval("(rpgetvar 'flow-time)")))}
    for i, n in enumerate(FLUIDS + WALLS):
        data[f'zone{i}_vertices'] = geo[n].vertices
        data[f'zone{i}_connectivity'] = geo[n].connectivity
    extrema = {}
    for field in fields or ['mach-number', 'pressure', 'density', 'temperature']:
        out = s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name=field, node_value=True))
        extrema[field] = {}
        for i, n in enumerate(FLUIDS):
            data[f'zone{i}_{field}'] = out[n]
            a = out[n]
            extrema[field][n] = {'min': float(a.min()), 'max': float(a.max()), 'finite': bool(np.isfinite(a).all())}
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **data)
    return {'solution_time_s': float(data['solution_time_s']), 'rotor_wall_node_centroid': data['zone3_vertices'].mean(axis=0).astype(float).tolist(), 'extrema': extrema}

def triangulate(flat):
    triangles = []
    i = 0
    while i < len(flat):
        n = int(flat[i])
        ids = flat[i + 1:i + 1 + n]
        if n >= 3:
            triangles.extend(((int(ids[0]), int(ids[j]), int(ids[j + 1])) for j in range(1, n - 1)))
        i += n + 1
    return np.asarray(triangles, dtype=np.int32)

def segments(flat, xyz):
    out = []
    i = 0
    while i < len(flat):
        n = int(flat[i])
        ids = flat[i + 1:i + n + 1]
        if n == 2:
            out.append(xyz[ids, :2])
        i += n + 1
    return np.asarray(out)

def render_snapshot(p, outdir, tag):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    from matplotlib.collections import LineCollection
    outdir.mkdir(parents=True, exist_ok=True)
    with np.load(p) as z:
        t = float(z['solution_time_s'])
        prepared = []
        for i in [0, 1]:
            prepared.append((z[f'zone{i}_vertices'].astype(float), triangulate(z[f'zone{i}_connectivity']), {f: z[f'zone{i}_{f}'] for f in ['mach-number', 'pressure']}))
        walls = [segments(z[f'zone{i}_connectivity'], z[f'zone{i}_vertices']) for i in [2, 3]]
    limits = {'mach-number': (0, 1.2, 'Absolute Mach number [-]'), 'pressure': (80000, 180000, 'Absolute static pressure [Pa]')}
    files = []
    saturation = {}
    for field, (vmin, vmax, label) in limits.items():
        fig, ax = plt.subplots(figsize=(12.8, 6.4), dpi=120, layout='constrained')
        for xyz, tri, vals in prepared:
            values = vals[field]
            for k in [-3, -2, -1, 0, 1, 2, 3]:
                xy = xyz[:, :2].copy()
                xy[:, 1] += k * PITCH
                corners = xy[tri]
                keep = (corners[:, :, 1].min(axis=1) <= 0.095) & (corners[:, :, 1].max(axis=1) >= -0.095)
                if not np.any(keep):
                    continue
                topology = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles=tri[keep])
                artist = ax.tripcolor(topology, values, shading='gouraud', cmap='viridis' if field == 'mach-number' else 'plasma', vmin=vmin, vmax=vmax, rasterized=True)
        for seg in walls:
            for k in [-3, -2, -1, 0, 1, 2, 3]:
                line = seg.copy()
                line[:, :, 1] += k * PITCH
                ax.add_collection(LineCollection(line, colors='#202020', linewidths=0.35))
        ax.set(xlim=(0.005, 0.402), ylim=(-0.095, 0.095), xlabel='Axial X [m]', ylabel='Tangential Y [m]')
        ax.set_aspect('equal')
        ax.set_title(label + ' — mesh adattata mantenuta fissa', loc='left', fontsize=12)
        ax.text(0.99, 1.035, f'Solution time: {t:.9f} s', transform=ax.transAxes, ha='right', va='bottom', fontsize=11, fontfamily='monospace')
        ax.text(0.015, 0.02, 'Stationary stator  |  Rotor Vy = -150 m/s  |  Periodic pitch: 0.04463756775 m', transform=ax.transAxes, fontsize=8, color='black', bbox={'facecolor': 'white', 'alpha': 0.85, 'edgecolor': 'none'})
        fig.colorbar(artist, ax=ax, shrink=0.85, label=label)
        target = outdir / (tag + '_' + ('mach' if field == 'mach-number' else 'pressure') + '.png')
        fig.savefig(target)
        plt.close(fig)
        files.append(str(target))
        saturation[field] = sum((int(np.sum((vals[field] < vmin) | (vals[field] > vmax))) for xyz, tri, vals in prepared))
    jwrite(outdir / (tag + '_render.json'), dict(solution_time_s=t, camera=dict(xlim_m=[0.005, 0.402], ylim_m=[-0.095, 0.095], projection='XY_orthographic'), legende_fisse=limits, copie_periodiche=[-3, -2, -1, 0, 1, 2, 3], verifica_periodiche=str(AUDIT / 'periodicita_geometrica.csv'), nodal_interpolation=True, punti_fuori_legenda=saturation, files=files))
    return files
if __name__ == '__main__':
    import sys
    print(render_snapshot(project_path(sys.argv[1]), project_path(sys.argv[2]), sys.argv[3]))
