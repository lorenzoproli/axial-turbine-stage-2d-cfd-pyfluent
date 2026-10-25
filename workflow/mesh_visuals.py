"""Scientific mesh views from native cell edges, without artificial diagonals."""
from common import *
from english_labels import install
install()
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def edges(flat, xyz):
    pairs = []
    i = 0
    cells = 0
    while i < len(flat):
        n = int(flat[i])
        ids = flat[i + 1:i + n + 1].astype(np.int32)
        if n >= 3:
            pairs.extend(zip(ids, np.roll(ids, -1)))
            cells += 1
        elif n == 2:
            pairs.append(tuple(ids))
        i += n + 1
    pairs = np.sort(np.asarray(pairs, dtype=np.int32), axis=1)
    pairs = np.unique(pairs, axis=0)
    return (xyz[pairs, :2], cells)

def render_mesh(source, outdir, title, native_summary=None):
    outdir = project_path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with np.load(source) as z:
        time_s = float(z['solution_time_s']) if 'solution_time_s' in z else None
        fluid = [edges(z[f'zone{i}_connectivity'], z[f'zone{i}_vertices']) for i in [0, 1]]
        wall = [edges(z[f'zone{i}_connectivity'], z[f'zone{i}_vertices'])[0] for i in [2, 3]]
        allxy = np.concatenate([z[f'zone{i}_vertices'][:, :2] for i in [0, 1]])
        wallxy = [z[f'zone{i}_vertices'][:, :2] for i in [2, 3]]
    views = [('01_dominio', None, None, 'Dominio completo: un passaggio per schiera')]
    for i, n in enumerate(['statore', 'rotore']):
        p = wallxy[i][np.argmin(wallxy[i][:, 0])]
        views.append((f'0{i + 2}_parete_{n}', [float(p[0] - 0.003), float(p[0] + 0.006)], [float(p[1] - 0.0045), float(p[1] + 0.0045)], f'Bordo di attacco e strati vicino alla parete: {n}'))
    x_interface = float(wallxy[0][:, 0].max() + 0.00797)
    views.append(('04_interfaccia', [x_interface - 0.005, x_interface + 0.005], [-0.043, -0.023], 'Interfaccia sliding: lati statore e rotore'))
    result = []
    for name, xlim, ylim, label in views:
        fig, ax = plt.subplots(figsize=(10, 3.7) if name == '01_dominio' else (10, 6.3), dpi=180, layout='constrained')
        if xlim is None:
            lo = allxy.min(axis=0)
            hi = allxy.max(axis=0)
            pad = (hi - lo) * 0.025
            xlim = [float(lo[0] - pad[0]), float(hi[0] + pad[0])]
            ylim = [float(lo[1] - pad[1]), float(hi[1] + pad[1])]
        for (seg, count), color in zip(fluid, ['#155b7d', '#9c5429']):
            keep = (seg[:, :, 0].max(axis=1) >= xlim[0]) & (seg[:, :, 0].min(axis=1) <= xlim[1]) & (seg[:, :, 1].max(axis=1) >= ylim[0]) & (seg[:, :, 1].min(axis=1) <= ylim[1])
            ax.add_collection(LineCollection(seg[keep], colors=color, linewidths=0.13 if name == '01_dominio' else 0.28))
        for seg in wall:
            ax.add_collection(LineCollection(seg, colors='#111111', linewidths=0.9))
        ax.set(xlim=xlim, ylim=ylim, xlabel='X assiale [m]', ylabel='Y tangenziale [m]')
        ax.set_aspect('equal')
        fig.suptitle(title, fontsize=14)
        time_label = f'Solution time: {time_s:.9f} s' if time_s is not None else 'Geometria di riferimento; nessuna soluzione CFD'
        ax.set_title(label + '\n' + time_label, loc='left', fontsize=11)
        ax.text(0.01, 0.02, 'Lati reali delle celle; nessuna triangolazione aggiunta', transform=ax.transAxes, fontsize=8, bbox=dict(facecolor='white', alpha=0.9, edgecolor='none'))
        p = outdir / (name + '.png')
        fig.savefig(p)
        plt.close(fig)
        result.append(dict(file=str(p), byte=p.stat().st_size, sha256=sha(p), xlim_m=xlim, ylim_m=ylim))
    meta = dict(sorgente=str(source), sorgente_sha256=sha(project_path(source)), tempo_s=time_s, celle_poligonali_per_zona=[v[1] for v in fluid], render='lati poligonali esportati da Fluent; Matplotlib', qualita_nativa=native_summary, immagini=result)
    jwrite(outdir / 'manifest_mesh_png.json', meta)
    return meta
if __name__ == '__main__':
    a = json.loads((AUDIT / 'audit_baseline.json').read_text())
    out = project_path(ROOT / '06_figure' / 'mesh_verificate' / 'baseline_adattata')
    meta = render_mesh(AUDIT / 'baseline_fields_geometry.npz', out, 'Baseline storica: mesh adattata mantenuta fissa', a['qualita'])
    rows = [dict(mesh='baseline_adattata', grandezza=k, valore=v, unita='-' if k != 'profondita_2D_m' else 'm', fonte='audit Fluent della coppia final, t=0.010653 s') for k, v in {'celle_attive': a['active_cells'], 'celle_parent_AMR': a['parent_cells'], 'celle_memorizzate': a['stored_cells'], 'orthogonal_quality_min': a['qualita']['orthogonal_quality_min'], 'aspect_ratio_max': a['qualita']['aspect_ratio_max'], 'profondita_2D_m': a['profondita_2D_m']}.items()]
    dest = project_path(ROOT / '05_postprocessing' / 'qualita_mesh')
    csvwrite(dest / 'baseline_riepilogo_native.csv', rows)
    csvwrite(dest / 'baseline_yplus_pareti.csv', a['yplus'])
    assert sum(meta['celle_poligonali_per_zona']) == a['active_cells']
    append_status('Esportate quattro immagini PNG della mesh adattata verificata: dominio, pareti statore/rotore, interfaccia sliding; lati reali delle celle senza diagonali di rendering. Tabelle CSV delle misure native e y+ alla baseline disponibili in 05_postprocessing/qualita_mesh. Distribuzioni della qualità per cella e controlli delle mesh sistematiche ancora da esportare in Fluent.')
    print(json.dumps(meta, ensure_ascii=False), flush=True)
