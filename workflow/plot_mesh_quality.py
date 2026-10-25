"""Cell-count histograms and low-quality locations from native mesh metrics."""
from common import *
from english_labels import install
install()
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mesh_visuals import render_mesh

def plot_quality(mesh_id):
    stored_id = mesh_id + '_HYBRID35_initial_position' if mesh_id in ['M1', 'M2', 'M3'] else mesh_id
    base = project_path(ROOT / '05_postprocessing/qualita_mesh' / stored_id)
    info = json.loads((base / 'esportazione_qualita.json').read_text())
    out = project_path(ROOT / '06_figure/mesh_verificate' / mesh_id)
    out.mkdir(parents=True, exist_ok=True)
    z = np.load(base / 'qualita_celle.npz')
    thresholds = []
    metrics = [('orthogonal_quality', 'Qualità ortogonale [-]', np.linspace(0, 1, 51)), ('aspect_ratio', 'Aspect ratio [-]', np.geomspace(1, 1000, 61)), ('equiangle_skewness', 'Equiangle skewness [-]', np.linspace(0, 1, 51))]
    fig, axs = plt.subplots(1, 3, figsize=(13.33, 4.8), layout='constrained')
    for ax, (metric, label, bins) in zip(axs, metrics):
        for iz, name, color in [(0, 'Statore', '#155b7d'), (1, 'Rotore', '#9c5429')]:
            values = z[f'zone{iz}_{metric}']
            weights = np.full(len(values), 100 / len(values))
            ax.hist(values, bins=bins, weights=weights, histtype='step', lw=1.4, label=name, color=color)
        if metric == 'aspect_ratio':
            ax.set_xscale('log')
        ax.set(xlabel=label, ylabel='Percentuale delle celle nella classe [%]')
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(mesh_id + ': distribuzioni native Fluent, pesatura per numero di celle')
    fig.savefig(out / '05_distribuzioni_qualita.png', dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(13.33, 5.5), layout='constrained')
    for iz, name in [(0, 'statore'), (1, 'rotore')]:
        xy = z[f'zone{iz}_centroids_m']
        q = z[f'zone{iz}_orthogonal_quality']
        ar = z[f'zone{iz}_aspect_ratio']
        for limit in [0.01, 0.05, 0.1, 0.2]:
            thresholds.append(dict(mesh=mesh_id, zona=name, metrica='orthogonal_quality', condizione='<', soglia=limit, celle=int(np.sum(q < limit)), percento=100 * float(np.mean(q < limit))))
        for limit in [20, 50, 100]:
            thresholds.append(dict(mesh=mesh_id, zona=name, metrica='aspect_ratio', condizione='>', soglia=limit, celle=int(np.sum(ar > limit)), percento=100 * float(np.mean(ar > limit))))
        ax.scatter(xy[::max(1, len(xy) // 5000), 0], xy[::max(1, len(xy) // 5000), 1], s=0.2, c='#d4d9dc', rasterized=True)
        k = q < 0.1
        if np.any(k):
            ax.scatter(xy[k, 0], xy[k, 1], s=4, label=name + ' Q<0.1', rasterized=True)
    ax.set(xlabel='X assiale [m]', ylabel='Y tangenziale [m]', title=mesh_id + ': localizzazione delle celle con qualità ortogonale <0.1')
    ax.set_aspect('equal')
    if ax.get_legend_handles_labels()[0]:
        ax.legend()
    else:
        ax.text(0.5, 0.9, 'Nessuna cella con Q<0.1', transform=ax.transAxes, ha='center')
    ax.grid(alpha=0.15)
    fig.savefig(out / '06_localizzazione_qualita_bassa.png', dpi=150)
    plt.close(fig)
    csvwrite(base / 'conteggi_soglie_diagnostiche.csv', thresholds)
    jwrite(out / 'manifest_qualita_png.json', [dict(file=str(p), byte=p.stat().st_size, sha256=sha(p)) for p in sorted(out.glob('0[56]_*.png'))])
    return thresholds
if __name__ == '__main__':
    import sys
    mids = sys.argv[1:] or ['baseline_adattata', 'M1', 'M2', 'M3']
    rows = []
    for mid in mids:
        if mid != 'baseline_adattata':
            src = project_path(ROOT / '03_simulazioni/convergenza_griglia/audit_export_diretto_20261013' / (mid + '_mesh_geometry.npz'))
            render_mesh(src, project_path(ROOT / '06_figure/mesh_verificate' / mid), mid + ': mesh sistematica dalla geometria comune')
        rows += plot_quality(mid)
    csvwrite(project_path(ROOT / '05_postprocessing/qualita_mesh/conteggi_soglie_confronto.csv'), rows)
    print('QUALITY_PNG_READY', mids, flush=True)
