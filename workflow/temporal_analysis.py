from data_schema import csv, json
from common import *
from english_labels import install
install()
from compare_runs import phase_profiles
from registry import update_test
import numpy as np

def analyse_temporal():
    runs = ['T100', 'T200', 'T400']
    base = project_path(ROOT / '05_postprocessing/campagna')
    summaries = {r: json.loads((base / r / 'analysis.json').read_text()) for r in runs}
    assert all((s['monitor_periodicity_within_proposed_criteria'] for s in summaries.values()))
    assert all((np.allclose(summaries[r]['window_s'], summaries['T400']['window_s'], rtol=0, atol=1e-13) for r in runs))
    profiles = {r: phase_profiles(r) for r in runs}
    rows = []
    stats = []
    for r in runs:
        stats += summaries[r]['statistics']
    for left, right in zip(runs, runs[1:]):
        for x, y in zip(summaries[left]['statistics'], summaries[right]['statistics']):
            assert x['monitor'] == y['monitor']
            n = x['monitor']
            amp = y['mean_cycle_peak_to_peak']
            rows.append(dict(monitor=n, from_run=left, to_run=right, mean_difference_percent=100 * abs(x['mean'] - y['mean']) / abs(y['mean']), amplitude_difference_percent=100 * abs(x['mean_cycle_peak_to_peak'] - amp) / amp, phase_rms_percent_of_amplitude=100 * float(np.sqrt(np.mean((profiles[left][n] - profiles[right][n]) ** 2))) / amp))
    out = base / 'convergenza_temporale'
    csvwrite(out / 'confronti_temporali.csv', rows)
    csvwrite(out / 'statistiche_comparate.csv', stats)
    iteration = json.loads(project_path(ROOT / 'runs/analysis/sensitivity/inner_iterations/assessment.json').read_text())
    floors = {r['monitor']: r for r in iteration['comparisons']}
    flags = [dict(monitor=r['monitor'], comparison=r['from_run'] + '-' + r['to_run'], temporal_mean_difference_percent=r['mean_difference_percent'], inner_iteration_mean_difference_percent=floors[r['monitor']]['mean_difference_percent'], temporal_mean_below_iteration_difference=r['mean_difference_percent'] < floors[r['monitor']]['mean_difference_percent']) for r in rows]
    for flag, r in zip(flags, rows):
        n = r['monitor']
        cyclic = [v for rid in [r['from_run'], r['to_run']] for v in summaries[rid]['cycle_comparisons'] if v['monitor'] == n]
        flag.update(maximum_cycle_mean_change_percent=max((v['mean_change_percent'] for v in cyclic)), maximum_cycle_amplitude_change_percent=max((v['amplitude_change_percent'] for v in cyclic)), inner_iteration_amplitude_difference_percent=floors[n]['amplitude_difference_percent'], inner_iteration_phase_rms_percent_of_amplitude=floors[n]['phase_rms_percent_of_amplitude'], temporal_mean_below_cycle_variability=r['mean_difference_percent'] < max((v['mean_change_percent'] for v in cyclic)), temporal_amplitude_below_iteration_difference=r['amplitude_difference_percent'] < floors[n]['amplitude_difference_percent'])
    csvwrite(out / 'controllo_errore_iterativo_vs_temporale.csv', flags)
    result = dict(utc=now(), status='COMPARISONS_COMPLETE_INTERPRETATION_PENDING', window_s=summaries['T400']['window_s'], comparisons=rows, inner_iteration_error_control=flags, observed_order=None, GCI=None, note='Three cycles per run with linear interpolation for phase comparison. Compare cycle variability and inner-iteration sensitivity with timestep differences; no automatic order or GCI is assigned.')
    jwrite(out / 'assessment.json', result)
    fine = [r for r in rows if r['to_run'] == 'T400']
    accepted = all((r['mean_difference_percent'] <= 0.1 and r['amplitude_difference_percent'] <= 2 and (r['phase_rms_percent_of_amplitude'] <= 2) for r in fine))
    result['decision'] = dict(proposed_operational_criteria=dict(means_percent=0.1, amplitudes_percent=2, phase_rms_percent_of_amplitude=2), T200_T400_within_criteria=accepted, spatial_study_timestep_s=T / (200 if accepted else 400), iterations=30, reason='Use T200 only if comparison with T400 meets the operational criteria; otherwise retain T400 as the finest tested setting. This is not an asymptotic error estimate.', limit='Differences below inner-iteration sensitivity or cycle variability do not support a reliable order. The operational choice applies to the observed scales.')
    result['status'] = 'TEMPORAL_SENSITIVITY_RECORDED_OPERATIONAL_CHOICE_DOCUMENTED'
    jwrite(out / 'assessment.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir = project_path(ROOT / 'results/figures/generated/campaign/timestep')
    figdir.mkdir(parents=True, exist_ok=True)
    names = [r['monitor'] for r in summaries['T400']['statistics']]
    for key, label, filename in [('mean', 'Mean', 'medie_vs_timestep.png'), ('mean_cycle_peak_to_peak', 'Peak-to-peak amplitude', 'ampiezze_vs_timestep.png')]:
        fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
        for ax, name in zip(axs.flat, names):
            selected = [next((v for v in summaries[r]['statistics'] if v['monitor'] == name)) for r in runs]
            ax.plot([100, 200, 400], [v[key] for v in selected], '-o', color='#155b7d')
            ax.set_xscale('log', base=2)
            ax.set_xticks([100, 200, 400], labels=['T/100', 'T/200', 'T/400'])
            ax.set(ylabel=label + ' [' + selected[0]['unit'] + ']', title=name)
            ax.grid(alpha=0.2)
        fig.suptitle('Baseline mesh: equivalent three-period windows after settling')
        fig.savefig(figdir / filename, dpi=150)
        plt.close(fig)
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for ax, name in zip(axs.flat, names):
        for rid in runs:
            ax.plot(np.linspace(0, 1, len(profiles[rid][name])), profiles[rid][name], label=rid, lw=1)
        ax.set(xlabel='Phase from window start [-]', title=name)
        ax.grid(alpha=0.2)
        ax.legend()
    fig.savefig(figdir / 'profili_in_fase_temporali.png', dpi=150)
    plt.close(fig)
    from compare_phase_fields import compare_available
    from wall_cycle_analysis import analyse_wall_cycle
    compare_available()
    for rid in runs:
        analyse_wall_cycle(rid)
    append_status(f'T100/T200/T400 compared over equivalent three-period windows. Means, amplitudes, phase RMS, cycle variability, iterative sensitivity and wall data are available. T200/T400 within the proposed criteria: {accepted}; spatial-study timestep {result['decision']['spatial_study_timestep_s']:.12g} s. No observed order, GCI or zero-error claim is assigned.')
    print('TEMPORAL_COMPARISONS_READY', json.dumps(rows), flush=True)
    return result
if __name__ == '__main__':
    analyse_temporal()
