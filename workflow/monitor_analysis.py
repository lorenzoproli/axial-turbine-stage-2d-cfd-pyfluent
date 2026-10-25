"""Equivalent complete-period windows and consistent restart segment merging."""
from common import *
from english_labels import install
install()
from monitor_paths import monitor_path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
NAMES = ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet']
UNITS = dict(zip(NAMES, ['N (profondità 1 m)', 'kg/s', 'kg/s', 'Pa']))

def read_monitor(path):
    rows = []
    for line in project_path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        a = line.split()
        if len(a) == 3:
            try:
                rows.append([int(a[0]), float(a[1]), float(a[2])])
            except ValueError:
                continue
    a = np.asarray(rows, dtype=float)
    assert a.ndim == 2 and a.shape[1] == 3, path
    assert np.all(np.diff(a[:, 2]) > 0), f'Tempi non crescenti: {path}'
    return a

def segment(t, v, a, b):
    tolerance = 64 * np.finfo(float).eps * max(abs(t[0]), abs(t[-1]), abs(a), abs(b), np.finfo(float).tiny)
    assert t[0] <= a + tolerance and t[-1] >= b - tolerance, 'La serie non copre la finestra richiesta'
    k = (t > a) & (t < b)
    return (np.r_[a, t[k], b], np.r_[np.interp(a, t, v), v[k], np.interp(b, t, v)])

def merge_series(pieces):
    """Punti comuni di restart ammessi soltanto con valori coerenti."""
    x = np.concatenate(pieces)
    x = x[np.argsort(x[:, 2])]
    duplicates = np.where(abs(np.diff(x[:, 2])) < 1e-13)[0]
    for i in duplicates:
        assert np.isclose(x[i, 1], x[i + 1, 1], rtol=1e-10, atol=1e-12), 'Collisione monitor al restart'
        assert x[i, 0] == x[i + 1, 0], 'Passo globale differente allo stesso tempo fisico'
    if len(duplicates):
        x = np.delete(x, duplicates, axis=0)
    assert np.all(np.diff(x[:, 2]) > 0)
    return x

def accepted_monitor_segments(meta, run_dir):
    """Resolve accepted restart ranges from explicit saved boundaries."""
    run_dir = project_path(run_dir)
    monitor_segments = meta.get('monitor_segments')
    if not monitor_segments:
        current = project_path(meta.get('output_correnti', run_dir))
        resources = meta.get('segmenti_risorse', [])
        if current != run_dir:
            if not resources or resources[-1].get('tempo_iniziale_s') is None:
                raise ValueError('Restarted monitor history requires an explicit accepted segment boundary.')
            boundary = resources[-1]['tempo_iniziale_s']
            monitor_segments = [dict(directory=str(run_dir), from_s=None, to_s=boundary),
                                dict(directory=str(current), from_s=boundary, to_s=None)]
        else:
            monitor_segments = [dict(directory=str(run_dir), from_s=None, to_s=None)]
    return monitor_segments

def analyse(run_dir, monitor_dirs=None):
    run_dir = project_path(run_dir)
    meta = json.loads((run_dir / 'progress.json').read_text())
    run_id = meta['id']
    start, end = meta['finestra_media_s']
    assert meta['passi_completati'] == meta['passi_pianificati'], 'Run incompleto'
    monitor_segments = accepted_monitor_segments(meta, run_dir) if monitor_dirs is None else [
        dict(directory=str(d), from_s=None, to_s=None) for d in monitor_dirs]
    data = {}
    sources = []
    for name in NAMES:
        pieces = []
        for seg in monitor_segments:
            p = monitor_path(seg['directory'], name)
            piece = read_monitor(p)
            if seg.get('from_s') is not None:
                piece = piece[piece[:, 2] >= seg['from_s'] - 1e-13]
            if seg.get('to_s') is not None:
                piece = piece[piece[:, 2] <= seg['to_s'] + 1e-13]
            pieces.append(piece)
            sources.append(dict(file=str(p), sha256=sha(p)))
        x = merge_series(pieces)
        data[name] = x
    tt = data[NAMES[0]][:, 2]
    assert all((np.array_equal(x[:, 2], tt) for x in data.values()))
    ncycles = int(round((end - start) / T))
    assert abs((end - start) / T - ncycles) < 1e-08
    phase = np.linspace(0, 1, 401)
    stats = []
    profiles = {}
    comparisons = []
    overall = []
    for name, x in data.items():
        profiles[name] = []
        for k in range(ncycles):
            a = start + k * T
            b = a + T
            t, v = segment(tt, x[:, 1], a, b)
            profile = np.interp(a + phase * T, tt, x[:, 1])
            profiles[name].append(profile)
            stats.append(dict(prova=run_id, monitor=name, ciclo_finestra=k, inizio_s=a, fine_s=b, media=float(np.trapezoid(v, t) / T), minimo=float(v.min()), massimo=float(v.max()), ampiezza_picco_picco=float(np.ptp(v)), unita=UNITS[name]))
        rows = [r for r in stats if r['monitor'] == name]
        for k in range(1, ncycles):
            a, b = (rows[k - 1], rows[k])
            den = max(abs(b['media']), 1e-20)
            amp = max(b['ampiezza_picco_picco'], 1e-20)
            comparisons.append(dict(prova=run_id, monitor=name, da_ciclo=k - 1, a_ciclo=k, variazione_media_percento=100 * abs(b['media'] - a['media']) / den, variazione_ampiezza_percento=100 * abs(b['ampiezza_picco_picco'] - a['ampiezza_picco_picco']) / amp, rms_fase_percento_ampiezza=100 * float(np.sqrt(np.mean((profiles[name][k] - profiles[name][k - 1]) ** 2))) / amp))
        t, v = segment(tt, x[:, 1], start, end)
        overall.append(dict(prova=run_id, monitor=name, dt_s=meta['dt_s'], iterazioni_per_passo=meta['iterazioni_per_passo'], inizio_s=start, fine_s=end, media=float(np.trapezoid(v, t) / (end - start)), ampiezza_picco_picco_media_cicli=float(np.mean([r['ampiezza_picco_picco'] for r in rows])), unita=UNITS[name]))
    mass = []
    for k in range(ncycles):
        a = start + k * T
        b = a + T
        t, vi = segment(tt, data['mdot_inlet'][:, 1], a, b)
        _, vo = segment(tt, data['mdot_outlet'][:, 1], a, b)
        mi = float(np.trapezoid(vi, t) / T)
        mo = float(np.trapezoid(vo, t) / T)
        mass.append(dict(prova=run_id, ciclo=k, inizio_s=a, fine_s=b, inlet_kg_s=mi, outlet_kg_s=mo, netto_kg_s=mi + mo, sbilanciamento_percento=100 * abs(mi + mo) / abs(mi), massa_netta_integrata_kg=(mi + mo) * T, accumulo_dominio='Non deducibile dai soli monitor; esportazione massa del dominio necessaria'))
    criteria = dict(variazione_media_max_percento=0.5, variazione_ampiezza_max_percento=5, rms_fase_max_percento_ampiezza=10, sbilanciamento_medio_max_percento=0.5)
    checks = dict(medie=all((r['variazione_media_percento'] <= 0.5 for r in comparisons)), ampiezze=all((r['variazione_ampiezza_percento'] <= 5 for r in comparisons)), fase=all((r['rms_fase_percento_ampiezza'] <= 10 for r in comparisons)), portate=all((r['sbilanciamento_percento'] <= 0.5 for r in mass)))
    summary = dict(id=run_id, utc=now(), finestra_s=[start, end], cicli=ncycles, criteri_diagnostici_proposti=criteria, esiti=checks, periodicita_monitor_entro_criteri_proposti=all(checks.values()), validazione_fisica=False, conservazione_con_accumulo_verificata=False, statistiche=overall, confronti_cicli=comparisons, bilancio_portate=mass, sorgenti=sources)
    out = project_path(ROOT / '05_postprocessing' / 'campagna' / run_id)
    figdir = project_path(ROOT / '06_figure' / 'campagna' / run_id)
    masspieces = []
    for seg in monitor_segments:
        p = project_path(seg['directory']) / 'massa_dominio-rfile.out'
        if not p.exists():
            masspieces = []
            break
        x = read_monitor(p)
        sources.append(dict(file=str(p), sha256=sha(p), grandezza='massa_dominio_kg'))
        if seg.get('from_s') is not None:
            x = x[x[:, 2] >= seg['from_s'] - 1e-13]
        if seg.get('to_s') is not None:
            x = x[x[:, 2] <= seg['to_s'] + 1e-13]
        masspieces.append(x)
    if masspieces:
        xm = merge_series(masspieces)
        assert np.array_equal(xm[:, 2], tt), 'Il monitor di massa non e sincronizzato con le portate'
        balance = []
        for k in range(ncycles):
            a = start + k * T
            b = a + T
            t, vi = segment(tt, data['mdot_inlet'][:, 1], a, b)
            _, vo = segment(tt, data['mdot_outlet'][:, 1], a, b)
            integrated = float(np.trapezoid(vi + vo, t))
            stored = float(np.interp(b, tt, xm[:, 1]) - np.interp(a, tt, xm[:, 1]))
            normalization = float(np.trapezoid(abs(vi), t))
            balance.append(dict(prova=run_id, ciclo=k, inizio_s=a, fine_s=b, massa_entrante_netta_integrata_kg=integrated, variazione_massa_dominio_kg=stored, difetto_integrale_kg=integrated - stored, errore_integrale_percento=100 * abs(integrated - stored) / normalization, metodo='Trapezi flussi e massa interpolata agli estremi; errore quadratura distinto dal difetto BDF2'))
        dt = meta['dt_s']
        assert np.allclose(np.diff(tt), dt, rtol=1e-07, atol=1e-12)
        derivative = (3 * xm[2:, 1] - 4 * xm[1:-1, 1] + xm[:-2, 1]) / (2 * dt)
        defect = data['mdot_inlet'][2:, 1] + data['mdot_outlet'][2:, 1] - derivative
        keep = (tt[2:] >= start) & (tt[2:] <= end)
        bdf = [dict(prova=run_id, tempo_s=float(t), dM_dt_BDF2_kg_s=float(d), flusso_netto_entrante_kg_s=float(d + e), difetto_kg_s=float(e), difetto_percento_inlet=100 * float(e) / abs(float(mi))) for t, d, e, mi in zip(tt[2:][keep], derivative[keep], defect[keep], data['mdot_inlet'][2:, 1][keep])]
        csvwrite(out / 'bilancio_massa_con_accumulo_cicli.csv', balance)
        csvwrite(out / 'difetto_massa_BDF2.csv', bdf)
        summary.update(conservazione_con_accumulo_verificata=True, bilancio_con_accumulo=balance, difetto_BDF2_percento_inlet=dict(media_assoluta=float(np.mean([abs(r['difetto_percento_inlet']) for r in bdf])), massimo_assoluto=float(max((abs(r['difetto_percento_inlet']) for r in bdf))), nota='BDF2 costante dopo assestamento; portata entrante positiva, profondita 1 m'))
        for row in mass:
            row['accumulo_dominio'] = 'Verificato separatamente in bilancio_massa_con_accumulo_cicli.csv e difetto_massa_BDF2.csv'
    csvwrite(out / 'statistiche_cicli.csv', stats)
    csvwrite(out / 'confronto_cicli.csv', comparisons)
    csvwrite(out / 'profili_in_fase.csv', [dict(prova=run_id, monitor=name, ciclo=k, fase_relativa=float(ph), tempo_s=float(start + (k + ph) * T), valore=float(v), unita=UNITS[name]) for name, cycles in profiles.items() for k, values in enumerate(cycles) for ph, v in zip(phase, values)])
    csvwrite(out / 'statistiche_finestra.csv', overall)
    csvwrite(out / 'bilancio_portate.csv', mass)
    jwrite(out / 'analisi.json', summary)
    figdir.mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for ax, name in zip(axs.flat, NAMES):
        for k, values in enumerate(profiles[name]):
            ax.plot(phase, values, label=f'Ciclo {k + 1}', lw=1)
        ax.set(xlabel='Fase rispetto all’inizio della finestra [-]', ylabel=UNITS[name], title=name)
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(f'{run_id}: tre periodi completi dopo l’assestamento escluso')
    fig.savefig(figdir / 'confronto_in_fase.png', dpi=150)
    plt.close(fig)
    return summary
if __name__ == '__main__':
    import sys
    r = analyse(case_directory(sys.argv[1]))
    print(json.dumps({k: v for k, v in r.items() if k in ['id', 'esiti', 'periodicita_monitor_entro_criteri_proposti']}, ensure_ascii=False))
