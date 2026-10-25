"""Read-only CFD audit of a completed assessment; never launches or alters a solver."""
from common import *
from monitor_analysis import read_monitor, merge_series, segment
import numpy as np
import matplotlib.pyplot as plt

def diagnose(run_id='M1'):
    source = project_path(ROOT / '05_postprocessing/campagna' / run_id)
    analysis_path = source / 'analisi.json'
    analysis = json.loads(analysis_path.read_text())
    progress = json.loads((case_directory(run_id) / 'progress.json').read_text())
    start, end = analysis['finestra_s']
    periods = int(round((end - progress['tempo_iniziale_s']) / T))
    out = source / f'periodicity_diagnostic_{periods:02d}_periods'
    out.mkdir(parents=True, exist_ok=True)
    phase_path = source / 'profili_in_fase.csv'
    stats_path = source / 'statistiche_cicli.csv'
    checksums = {p.name: sha(p) for p in [analysis_path, phase_path, stats_path]}
    with phase_path.open(encoding='utf-8-sig') as stream:
        profiles = list(csv.DictReader(stream))
    mass_sources = [r for r in analysis['sorgenti'] if r.get('grandezza') == 'massa_dominio_kg']
    pieces = []
    for row in mass_sources:
        path = project_path(row['file'])
        assert sha(path) == row['sha256']
        pieces.append(read_monitor(path))
    mass = merge_series(pieces)
    time, values = segment(mass[:, 2], mass[:, 1], start, end)
    mean_mass = float(np.trapezoid(values, time) / (end - start))
    flow = next((r['media'] for r in analysis['statistiche'] if r['monitor'] == 'mdot_inlet'))
    turnover = mean_mass / flow
    tests = [dict(metric='Cycle mean change', limit_percent=0.5, observed_percent=max((r['variazione_media_percento'] for r in analysis['confronti_cicli']))), dict(metric='Peak-to-peak amplitude change', limit_percent=5, observed_percent=max((r['variazione_ampiezza_percento'] for r in analysis['confronti_cicli']))), dict(metric='Phase-aligned RMS / peak-to-peak amplitude', limit_percent=10, observed_percent=max((r['rms_fase_percento_ampiezza'] for r in analysis['confronti_cicli']))), dict(metric='Cycle mean mass-flux imbalance', limit_percent=0.5, observed_percent=max((r['sbilanciamento_percento'] for r in analysis['bilancio_portate'])))]
    csvwrite(out / 'acceptance_checks.csv', tests)
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 7.4), layout='constrained')
    labels = [('forza_y_rotore', 'Rotor tangential force [N; 1 m depth]', 1), ('mdot_inlet', 'Inlet mass flow [kg/s]', 1), ('mdot_outlet', 'Outlet mass-flow magnitude [kg/s]', -1), ('pt_outlet', 'Outlet mass-weighted total pressure [Pa]', 1)]
    colours = ['#0072B2', '#D55E00', '#009E73']
    for ax, (name, label, sign) in zip(axes.flat, labels):
        for k in range(3):
            rows = [r for r in profiles if r['monitor'] == name and int(r['ciclo']) == k]
            x = np.array([float(r['fase_relativa']) for r in rows])
            y = sign * np.array([float(r['valore']) for r in rows])
            ax.plot(x, y, color=colours[k], lw=1.4, label=f'Cycle {periods - 2 + k}')
        ax.set(xlabel='Phase within one blade-passing period [-]', ylabel=label, xlim=(0, 1))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=9)
    passed = analysis['periodicita_monitor_entro_criteri_proposti']
    initialisation = 'fresh Hybrid start' if 'hybrid' in progress.get('initialization_method', '').lower() else 'initial field transfer'
    outcome = 'PASSED' if passed else 'NOT passed'
    fig.suptitle(f'{run_id}: cycles {periods - 2}-{periods} after {initialisation}; monitor criteria {outcome}', fontsize=13)
    figure = project_path(ROOT / '06_figure/campagna' / run_id / f'periodicity_diagnostic_{periods:02d}_periods.png')
    fig.savefig(figure, dpi=150)
    plt.close(fig)
    assert all((sha(source / name) == checksum for name, checksum in checksums.items())), 'Assessment changed during this audit'
    evidence = dict(utc=now(), run_id=run_id, completed_assessment_periods=periods, physical_window_s=[start, end], checks=tests, mean_domain_mass_kg=mean_mass, mean_inlet_mass_flow_kg_s=flow, inventory_turnover_s=turnover, inventory_turnover_in_pitch_periods=turnover / T, elapsed_since_initial_field_s=end - progress['tempo_iniziale_s'], initial_field_method=initialisation, monitor_criteria_passed=passed, max_integrated_mass_conservation_defect_percent=max((r['errore_integrale_percento'] for r in analysis['bilancio_con_accumulo'])), assessment_sources_sha256=checksums, figure=dict(file=str(figure), sha256=sha(figure)), interpretation='Three complete monitored cycles satisfy the configured operational recurrence criteria; consult the separate phase-field assessment.' if passed else 'The monitored cycles do not yet satisfy the configured recurrence criteria after ' + initialisation + '. The unique cause is not established.', limits='Inventory/flow is an indicative mass-turnover scale, not a convergence criterion or an exact residence-time distribution. Monitor recurrence does not prove full-field recurrence. The 30/60 iteration test on the adapted mesh does not establish iteration independence on M1.')
    jwrite(out / 'diagnostic.json', evidence)
    text(out / 'README.md', f'# {run_id} periodicity diagnostic after {periods} periods\n\nCompleted: independent audit of the last completed three-cycle assessment, native closed mass histories, acceptance metrics and phase-aligned figure. This operation does not launch or change Fluent. The running extension is a separate state.\n\nThe mass inventory is {mean_mass:.8g} kg and mean inlet flow {flow:.8g} kg/s, giving an indicative inventory/flow scale of {turnover * 1000:.5g} ms ({turnover / T:.4g} pitch periods). Elapsed physical time after {initialisation} is {(end - progress['tempo_iniziale_s']) * 1000:.5g} ms. This estimate is not an acceptance criterion.\n\nObserved: monitor recurrence criteria {outcome}. The actual means, amplitudes, phase RMS and mean mass-flux imbalance are recorded in acceptance_checks.csv. Integrated conservation including changing domain mass is assessed separately; a changing mass inventory is distinct from a numerical mass-conservation defect.\n\nNo strict mathematical periodicity, experimental validation or numerical independence is inferred. If these operational checks fail, further settling or other numerical investigations require review; no automatic transient extension follows from this diagnostic. Mesh-specific inner-iteration sensitivity remains distinct from the completed adapted-mesh 30/60 test.\n\nThe same-phase full-field recurrence results, when available, are in ../asymptotic_assessment/assessment.json and phase_field_recurrence.csv; the monitor plot alone does not establish field recurrence. Source hashes and monitor metrics are in diagnostic.json and acceptance_checks.csv.\n')
    append_status(f'{run_id} completed-assessment periodicity audit at {periods} periods after {initialisation}: monitor criteria {outcome}; worst cycle mean change {tests[0]['observed_percent']:.4g}%, amplitude change {tests[1]['observed_percent']:.4g}%, phase RMS {tests[2]['observed_percent']:.4g}% of peak-to-peak amplitude, cycle mean mass-flux imbalance {tests[3]['observed_percent']:.4g}%. Indicative inventory/flow scale {turnover * 1000:.5g} ms ({turnover / T:.4g} pitch periods), not a convergence criterion. Full-field recurrence is reported in the separate asymptotic assessment when available; mesh-specific iteration independence remains separate. No solver setting changed. Evidence: ' + str(out.relative_to(ROOT)) + '/diagnostic.json.')
    print(json.dumps(evidence, ensure_ascii=False), flush=True)
    return evidence
if __name__ == '__main__':
    diagnose()
