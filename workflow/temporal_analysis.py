from common import *
from english_labels import install
install()
from compare_runs import phase_profiles
from registry import update_test
import numpy as np

def analyse_temporal():
    runs = ['T100', 'T200', 'T400']
    base = project_path(ROOT / '05_postprocessing/campagna')
    summaries = {r: json.loads((base / r / 'analisi.json').read_text()) for r in runs}
    assert all((s['periodicita_monitor_entro_criteri_proposti'] for s in summaries.values()))
    assert all((np.allclose(summaries[r]['finestra_s'], summaries['T400']['finestra_s'], rtol=0, atol=1e-13) for r in runs))
    profiles = {r: phase_profiles(r) for r in runs}
    rows = []
    stats = []
    for r in runs:
        stats += summaries[r]['statistiche']
    for left, right in zip(runs, runs[1:]):
        for x, y in zip(summaries[left]['statistiche'], summaries[right]['statistiche']):
            assert x['monitor'] == y['monitor']
            n = x['monitor']
            amp = y['ampiezza_picco_picco_media_cicli']
            rows.append(dict(monitor=n, da_prova=left, a_prova=right, differenza_media_percento=100 * abs(x['media'] - y['media']) / abs(y['media']), differenza_ampiezza_percento=100 * abs(x['ampiezza_picco_picco_media_cicli'] - amp) / amp, rms_fase_percento_ampiezza=100 * float(np.sqrt(np.mean((profiles[left][n] - profiles[right][n]) ** 2))) / amp))
    out = base / 'convergenza_temporale'
    csvwrite(out / 'confronti_temporali.csv', rows)
    csvwrite(out / 'statistiche_comparate.csv', stats)
    iteration = json.loads((base / 'confronto_iterazioni/esito.json').read_text())
    floors = {r['monitor']: r for r in iteration['confronti']}
    flags = [dict(monitor=r['monitor'], confronto=r['da_prova'] + '-' + r['a_prova'], variazione_temporale_media_percento=r['differenza_media_percento'], sensibilita_iterativa_media_percento=floors[r['monitor']]['differenza_media_percento'], variazione_temporale_inferiore_a_sensibilita_iterativa=r['differenza_media_percento'] < floors[r['monitor']]['differenza_media_percento']) for r in rows]
    for flag, r in zip(flags, rows):
        n = r['monitor']
        cyclic = [v for rid in [r['da_prova'], r['a_prova']] for v in summaries[rid]['confronti_cicli'] if v['monitor'] == n]
        flag.update(variazione_ciclica_media_max_percento=max((v['variazione_media_percento'] for v in cyclic)), variazione_ciclica_ampiezza_max_percento=max((v['variazione_ampiezza_percento'] for v in cyclic)), sensibilita_iterativa_ampiezza_percento=floors[n]['differenza_ampiezza_percento'], sensibilita_iterativa_rms_fase_percento_ampiezza=floors[n]['rms_profilo_fase_percento_ampiezza'], variazione_temporale_media_inferiore_a_variabilita_ciclica=r['differenza_media_percento'] < max((v['variazione_media_percento'] for v in cyclic)), variazione_temporale_ampiezza_inferiore_a_sensibilita_iterativa=r['differenza_ampiezza_percento'] < floors[n]['differenza_ampiezza_percento'])
    csvwrite(out / 'controllo_errore_iterativo_vs_temporale.csv', flags)
    result = dict(utc=now(), stato='CONFRONTI_ESEGUITI_INTERPRETAZIONE_E_ACCETTAZIONE_DA_COMPLETARE', finestra_s=summaries['T400']['finestra_s'], confronti=rows, controllo_errore_iterativo=flags, ordine_osservato=None, GCI=None, nota='Tre cicli per run; interpolazione lineare per il confronto in fase. Nessun ordine/GCI attribuito automaticamente. Variazioni fra cicli e sensibilita iterativa da confrontare con le differenze di timestep.')
    jwrite(out / 'esito.json', result)
    fine = [r for r in rows if r['a_prova'] == 'T400']
    accepted = all((r['differenza_media_percento'] <= 0.1 and r['differenza_ampiezza_percento'] <= 2 and (r['rms_fase_percento_ampiezza'] <= 2) for r in fine))
    result['decisione'] = dict(criteri_operativi_proposti=dict(medie_percento=0.1, ampiezze_percento=2, rms_fase_percento_ampiezza=2), T200_T400_entro_criteri=accepted, timestep_spaziale_s=T / (200 if accepted else 400), iterazioni=30, motivazione='T200 se le differenze rispetto a T400 rientrano nei criteri operativi; altrimenti il piu fine T400 resta il candidato da verificare. Non equivale a una stima asintotica dell errore.', limite='Le differenze inferiori alla sensibilita interna o alla variabilita ciclica non consentono un ordine affidabile. La scelta e operativa entro le scale osservate; nessuna dichiarazione di errore nullo.')
    result['stato'] = 'SENSIBILITA_TEMPORALE_MISURATA_SCELTA_OPERATIVA_DOCUMENTATA'
    jwrite(out / 'esito.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir = project_path(ROOT / '06_figure/campagna/convergenza_temporale')
    figdir.mkdir(parents=True, exist_ok=True)
    names = [r['monitor'] for r in summaries['T400']['statistiche']]
    for key, label, filename in [('media', 'Media', 'medie_vs_timestep.png'), ('ampiezza_picco_picco_media_cicli', 'Ampiezza picco-picco', 'ampiezze_vs_timestep.png')]:
        fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
        for ax, name in zip(axs.flat, names):
            selected = [next((v for v in summaries[r]['statistiche'] if v['monitor'] == name)) for r in runs]
            ax.plot([100, 200, 400], [v[key] for v in selected], '-o', color='#155b7d')
            ax.set_xscale('log', base=2)
            ax.set_xticks([100, 200, 400], labels=['T/100', 'T/200', 'T/400'])
            ax.set(ylabel=label + ' [' + selected[0]['unita'] + ']', title=name)
            ax.grid(alpha=0.2)
        fig.suptitle('Mesh adattata fissa: finestre equivalenti di tre periodi dopo assestamento')
        fig.savefig(figdir / filename, dpi=150)
        plt.close(fig)
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for ax, name in zip(axs.flat, names):
        for rid in runs:
            ax.plot(np.linspace(0, 1, len(profiles[rid][name])), profiles[rid][name], label=rid, lw=1)
        ax.set(xlabel='Fase relativa della finestra [-]', title=name)
        ax.grid(alpha=0.2)
        ax.legend()
    fig.savefig(figdir / 'profili_in_fase_temporali.png', dpi=150)
    plt.close(fig)
    from compare_phase_fields import compare_available
    from wall_cycle_analysis import analyse_wall_cycle
    compare_available()
    for rid in runs:
        analyse_wall_cycle(rid)
    append_status(f'Campagna T100/T200/T400 eseguita e confrontata su finestre equivalenti e tre periodi completi. Tabelle di medie/ampiezze/RMS di fase, variabilita fra cicli, sensibilita iterativa, campi alla stessa fase e pressione/y+ nel ciclo disponibili. T200/T400 entro criteri operativi proposti: {accepted}; dt candidato spaziale {result['decisione']['timestep_spaziale_s']:.12g} s. Nessun ordine/GCI o errore nullo attribuito: limiti di risolvibilita documentati.')
    print('TEMPORAL_COMPARISONS_READY', json.dumps(rows), flush=True)
    return result
if __name__ == '__main__':
    analyse_temporal()
