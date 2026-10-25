from common import *
from english_labels import install
install()
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot_walls(run_ids):
    selected = []
    stats = []
    for rid in run_ids:
        directory = case_directory(rid)
        meta = json.loads((directory / 'progress.json').read_text())
        if rid in ['ITER30', 'ITER60']:
            d = directory / 'postprocessing_finale'
            tag = 'fine_run'
        else:
            d = project_path(meta.get('output_correnti', directory)) / 'campi_in_fase'
            tag = f'step_{meta['passi_pianificati']:05d}'
        manifest = json.loads((d / (tag + '_manifest.json')).read_text())
        t = manifest['solution_time_s']
        selected.append((rid, d, tag, t))
        for wall in manifest['pareti']:
            stats.append(dict(prova=rid, tempo_s=t, fase_mod_T=t / T % 1, **wall))
    for value in selected:
        offset = (value[3] - selected[0][3]) / T
        assert abs(offset - round(offset)) < 1e-07, 'Rotor phases differ: comparison refused'
    out = project_path(ROOT / '05_postprocessing/campagna' / ('pareti_' + '_'.join(run_ids)))
    csvwrite(out / 'riepilogo_yplus.csv', stats)
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for col, wall in enumerate(['wall_statore', 'wall_rotore']):
        for rid, d, tag, t in selected:
            with (d / (tag + '_' + wall + '.csv')).open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            x = np.array([float(r['x_m']) for r in rows])
            pressure = np.array([float(r['pressione_statica_assoluta_Pa']) for r in rows])
            yp = np.array([float(r['yplus']) for r in rows])
            axs[0, col].scatter(x, pressure, s=1.2, label=rid, alpha=0.7)
            axs[1, col].scatter(x, yp, s=1.2, label=rid, alpha=0.7)
        axs[0, col].set(title=wall, ylabel='Pressione statica assoluta [Pa]', xlabel='X assiale [m]')
        axs[1, col].set(ylabel='y+ [-]', xlabel='X assiale [m]')
        axs[1, col].axhline(1, color='#333333', ls='--', lw=0.7)
        for ax in axs[:, col]:
            ax.grid(alpha=0.2)
            ax.legend(markerscale=4)
    same_time = max((v[3] for v in selected)) - min((v[3] for v in selected)) < 1e-10
    fig.suptitle(f'Blade surfaces at a common phase: Solution time {selected[0][3]:.12f} s' if same_time else f'Blade surfaces at a common rotor phase: t/T mod 1 = {selected[0][3] / T % 1:.8f}')
    dest = project_path(ROOT / '06_figure/campagna' / out.name)
    dest.mkdir(parents=True, exist_ok=True)
    p = dest / 'pressione_yplus_pareti.png'
    fig.savefig(p, dpi=150)
    plt.close(fig)
    jwrite(out / 'manifest_figura.json', dict(file=str(p), sha256=sha(p), tempo_s=selected[0][3], physical_times_s={r: t for r, d, tag, t in selected}, equal_absolute_time=same_time, metodo='Scatter dei valori nativi alle facce; entrambe le facce della paletta rappresentate senza congiungere punti di rami diversi'))
    return stats
if __name__ == '__main__':
    import sys
    print(plot_walls(sys.argv[1:] or ['ITER30', 'ITER60']))
