"""Common-window phase comparisons without automatic order or GCI claims."""
from common import *
from registry import update_test
import numpy as np
from scipy.spatial import cKDTree

def phase_profiles(run_id):
    p = project_path(ROOT / '05_postprocessing/campagna' / run_id / 'profili_in_fase.csv')
    with p.open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    names = sorted({r['monitor'] for r in rows})
    out = {}
    for name in names:
        cycles = sorted({int(r['ciclo']) for r in rows if r['monitor'] == name})
        out[name] = np.mean([[float(r['valore']) for r in rows if r['monitor'] == name and int(r['ciclo']) == k] for k in cycles], axis=0)
    return out

def compare_iteration():
    base = project_path(ROOT / '05_postprocessing/campagna')
    a = json.loads((base / 'ITER30/analisi.json').read_text())
    b = json.loads((base / 'ITER60/analisi.json').read_text())
    assert np.allclose(a['finestra_s'], b['finestra_s'], rtol=0, atol=1e-13)
    pa, pb = (phase_profiles('ITER30'), phase_profiles('ITER60'))
    rows = []
    for x, y in zip(a['statistiche'], b['statistiche']):
        assert x['monitor'] == y['monitor']
        n = x['monitor']
        amp = y['ampiezza_picco_picco_media_cicli']
        rows.append(dict(monitor=n, media_ITER30=x['media'], media_ITER60=y['media'], unita=x['unita'], differenza_media_percento=100 * abs(x['media'] - y['media']) / abs(y['media']), differenza_ampiezza_percento=100 * abs(x['ampiezza_picco_picco_media_cicli'] - amp) / amp, rms_profilo_fase_percento_ampiezza=100 * float(np.sqrt(np.mean((pa[n] - pb[n]) ** 2))) / amp))
    criteria = dict(media_percento=0.1, ampiezza_percento=2, rms_fase_percento_ampiezza=2)
    passed = all((r['differenza_media_percento'] <= 0.1 and r['differenza_ampiezza_percento'] <= 2 and (r['rms_profilo_fase_percento_ampiezza'] <= 2) for r in rows))
    fields = []
    paths = []
    for rid in ['ITER30', 'ITER60']:
        directory = case_directory(rid)
        meta = json.loads((directory / 'progress.json').read_text())
        paths.append(project_path(meta.get('output_correnti', directory)) / 'final_fields.npz')
    with np.load(paths[0]) as za, np.load(paths[1]) as zb:
        assert abs(float(za['solution_time_s']) - float(zb['solution_time_s'])) < 1e-12
        for iz, zone in enumerate(['statore', 'rotore']):
            xa = za[f'zone{iz}_vertices']
            xb = zb[f'zone{iz}_vertices']
            dist, idx = cKDTree(xb).query(xa)
            assert float(dist.max()) < 1e-07, 'Geometrie non coincidenti: confronto di campi vietato'
            for f in ['mach-number', 'pressure', 'density', 'temperature']:
                va = za[f'zone{iz}_{f}'].astype(float)
                vb = zb[f'zone{iz}_{f}'][idx].astype(float)
                d = va - vb
                fields.append(dict(zona=zone, campo=f, tempo_s=float(za['solution_time_s']), differenza_massima_assoluta=float(abs(d).max()), rms_differenza=float(np.sqrt(np.mean(d * d))), rms_relativo_percento=100 * float(np.sqrt(np.mean(d * d) / np.mean(vb * vb))), errore_massimo_abbinamento_m=float(dist.max()), metodo='Confronto nodale alla stessa fase; nearest coordinate entro 1e-7 m, non pesato in volume'))
    out = base / 'confronto_iterazioni'
    csvwrite(out / 'confronto_ITER30_ITER60.csv', rows)
    csvwrite(out / 'confronto_campi_stessa_fase.csv', fields)
    chosen = 30 if passed else 60
    result = dict(utc=now(), finestre_s=a['finestra_s'], criteri_diagnostici_proposti=criteria, entro_criteri=passed, iterazioni_temporali_scelte=chosen, confronti=rows, campi=fields, nota='Scelta per la campagna temporale; la sensibilita 30/60 non dimostra da sola convergenza temporale o spaziale')
    jwrite(out / 'esito.json', result)
    for rid in ['ITER30', 'ITER60']:
        update_test(rid, 'eseguita_statistiche_e_confronto_iterativo_verificati', cicli_media=3, evidenza=str(out / 'esito.json'), prossima_attivita='Campagna temporale sulla stessa mesh e checkpoint')
        p = WORK / 'campagna' / rid / 'progress.json'
        meta = json.loads(p.read_text())
        meta['stato'] = 'eseguita_analizzata'
        meta['analisi'] = str(base / rid / 'analisi.json')
        jwrite(p, meta)
    append_status(f'Confronto ITER30/ITER60 completato su stessi tre periodi e campi alla stessa fase: {('entro' if passed else 'oltre')} i criteri diagnostici proposti. Per la campagna temporale scelti {chosen} iterazioni effettive/passo. In ITER60 il bilancio con accumulo e stato verificato: massimo difetto integrale circa 0.000114% della massa entrante e massimo difetto BDF2 circa 0.0000275% della portata inlet.')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result
if __name__ == '__main__':
    compare_iteration()
