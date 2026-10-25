"""Saved-cycle wall statistics with verified geometric face matching."""
from common import *
from english_labels import install
install()
import numpy as np
from scipy.spatial import cKDTree

def analyse_wall_cycle(run_id):
    d = case_directory(run_id)
    meta = json.loads((d / 'progress.json').read_text())
    assert meta['passi_completati'] == meta['passi_pianificati']
    directory = project_path(meta.get('output_correnti', d)) / 'campi_in_fase'
    if meta.get('captures'):
        first_step = meta['passi_pianificati'] - int(round(T / meta['dt_s']))
        manifests = [m for m in meta['captures'] if m.get('passi_completati', -1) >= first_step]
    else:
        manifests = [json.loads(p.read_text()) for p in sorted(directory.glob('step_*_manifest.json'))]
    times = np.array([m['solution_time_s'] for m in manifests])
    assert len(times) >= 5
    assert abs(times[-1] - times[0] - T) < 1e-10 and np.all(np.diff(times) > 0)
    out = project_path(ROOT / '05_postprocessing/campagna' / run_id / 'ciclo_pareti')
    stats = []
    envelopes = {}
    evidence = []
    for wall in ['wall_statore', 'wall_rotore']:
        pressures = []
        ys = []
        reference = None
        for m in manifests:
            expected_filename = english_name(m['tag'] + '_' + wall + '.csv')
            declared = next((v for v in m['manifest'] if project_path(v['file']).name == expected_filename))
            p = project_path(declared['file'])
            assert sha(p) == declared['sha256'] and p.stat().st_size == declared['byte']
            with p.open(encoding='utf-8-sig') as f:
                r = list(csv.DictReader(f))
            xy = np.array([[float(v['x_m']), float(v['y_m'])] for v in r])
            pressure = np.array([float(v['pressione_statica_assoluta_Pa']) for v in r])
            yp = np.array([float(v['yplus']) for v in r])
            assert np.isfinite(pressure).all() and np.isfinite(yp).all() and (yp >= 0).all()
            assert np.allclose([float(v['tempo_s']) for v in r], m['solution_time_s'], atol=1e-12, rtol=0)
            if reference is None:
                reference = xy.copy()
            assert len(xy) == len(reference), 'Topologia parete modificata'
            shift = xy.mean(axis=0) - reference.mean(axis=0)
            distance, indices = cKDTree(xy - shift).query(reference)
            assert len(np.unique(indices)) == len(reference) and distance.max() < 1e-07, 'Corrispondenza facce non verificata'
            assert abs(shift[0]) < 1e-07 and (wall == 'wall_rotore' or abs(shift[1]) < 1e-07)
            evidence.append(dict(wall=wall, tempo_s=m['solution_time_s'], traslazione_native_y_m=float(shift[1]), errore_mapping_m=float(distance.max()), file=str(p), sha256=declared['sha256']))
            pressures.append(pressure[indices])
            ys.append(yp[indices])
        pressures = np.array(pressures)
        ys = np.array(ys)
        mean_p = np.trapezoid(pressures, times, axis=0) / T
        mean_y = np.trapezoid(ys, times, axis=0) / T
        rows = [dict(indice_riferimento=i, x_m=float(x), y_riferimento_m=float(y), pressione_media_temporale_Pa=float(mean_p[i]), pressione_min_campionata_Pa=float(pressures[:, i].min()), pressione_max_campionata_Pa=float(pressures[:, i].max()), yplus_media_temporale=float(mean_y[i]), yplus_min_campionato=float(ys[:, i].min()), yplus_max_campionato=float(ys[:, i].max())) for i, (x, y) in enumerate(reference)]
        csvwrite(out / (wall + '_inviluppo.csv'), rows)
        envelopes[wall] = rows
        stats.append(dict(prova=run_id, wall=wall, faces=len(reference), campioni_temporali=len(times), inizio_s=float(times[0]), fine_s=float(times[-1]), yplus_min_campionato=float(ys.min()), yplus_max_campionato=float(ys.max()), frazione_facce_con_yplus_sempre_lt1=float(np.mean(ys.max(axis=0) < 1)), nota='Estremi sui campioni disponibili; nessuna garanzia sugli istanti non campionati. Frazione per numero facce, senza pesatura per area. Media temporale trapezoidale.'))
    csvwrite(out / 'riepilogo_ciclo.csv', stats)
    csvwrite(out / 'mapping_e_sha256.csv', evidence)
    result = dict(utc=now(), prova=run_id, stato='CICLO_CAMPIONATO_ANALIZZATO', statistiche=stats, intervallo_campionamento_s=np.diff(times).tolist(), nota=f'Actual saved final-cycle sampling: {len(times) - 1} intervals. Sampled extrema do not bound unsaved phases; datasets with different phase resolution do not have equivalent peak resolution.')
    jwrite(out / 'esito.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for col, (wall, rows) in enumerate(envelopes.items()):
        x = np.array([r['x_m'] for r in rows])
        for ax, mean, low, high, label in [(axs[0, col], 'pressione_media_temporale_Pa', 'pressione_min_campionata_Pa', 'pressione_max_campionata_Pa', 'Pressione statica assoluta [Pa]'), (axs[1, col], 'yplus_media_temporale', 'yplus_min_campionato', 'yplus_max_campionato', 'y+ [-]')]:
            ax.vlines(x, [r[low] for r in rows], [r[high] for r in rows], color='#8db4c6', lw=0.5, alpha=0.5, label='Inviluppo campionato')
            ax.scatter(x, [r[mean] for r in rows], s=1.2, color='#145775', label='Media temporale')
            ax.set(xlabel='X assiale [m]', ylabel=label, title=wall)
            ax.grid(alpha=0.2)
            ax.legend()
        axs[1, col].axhline(1, color='#333333', ls='--', lw=0.7)
    fig.suptitle(f'{run_id}: ciclo [{times[0]:.12f}, {times[-1]:.12f}] s; {len(times)} campioni')
    figdir = project_path(ROOT / '06_figure/campagna' / run_id)
    figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / 'pressione_yplus_inviluppo_ciclo.png', dpi=150)
    plt.close(fig)
    return result
if __name__ == '__main__':
    import sys
    print(json.dumps(analyse_wall_cycle(sys.argv[1] if len(sys.argv) > 1 else 'T100'), ensure_ascii=False))
