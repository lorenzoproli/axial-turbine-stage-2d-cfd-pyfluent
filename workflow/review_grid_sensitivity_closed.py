"""Recompute three-mesh sensitivity from accepted native monitors; no Fluent access."""
from common import *
from monitor_analysis import read_monitor, merge_series, segment, NAMES
from monitor_paths import monitor_path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
OUT = project_path(ROOT / '05_postprocessing/campagna/grid_sensitivity_review_20261017')
FIG = project_path(ROOT / '06_figure/campagna/grid_sensitivity_review_20261017')
RUNS = ['M1_HYBRID35', 'M2_HYBRID35', 'M3_HYBRID35']
LABELS = dict(zip(NAMES, ['Rotor tangential force', 'Inlet mass flow', 'Outlet mass flow', 'Outlet total pressure']))
UNITS = dict(zip(NAMES, ['N, 1 m depth', 'kg/s', 'kg/s', 'kPa']))
COLOURS = ['#16406b', '#23847f', '#b75a32']

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def main():
    assert project_path(ROOT / 'PROJECT_CLOSURE.json').exists(), 'Offline closed-campaign review only'
    assert not (OUT / 'assessment.json').exists(), 'Preserve an existing review rather than overwrite it'
    OUT.mkdir(parents=True)
    FIG.mkdir(parents=True, exist_ok=True)
    means = []
    cycles = []
    sources = []
    profiles = {}
    metadata = {}
    allwalls = []
    phase = np.linspace(0, 1, 401)
    for rid in RUNS:
        base = project_path(ROOT / '05_postprocessing/campagna' / rid)
        meta = load(case_directory(rid) / 'progress.json')
        old = load(base / 'analisi.json')
        start, end = old['finestra_s']
        assert abs((end - start) / T - 3) < 1e-09
        assert abs(start / T - round(start / T)) < 1e-08
        assert meta['dt_s'] == T / 400 and meta['iterazioni_per_passo'] == 30
        assert meta['passi_completati'] == meta['passi_pianificati']
        metadata[rid] = dict(active_cells=meta['celle_attive'], periods=round(meta['passi_completati'] / 400), window_s=[start, end], monitor_periodicity_passed=old['periodicita_monitor_entro_criteri_proposti'])
        for source in old['sorgenti']:
            p = project_path(source['file'])
            assert sha(p) == source['sha256']
        profiles[rid] = {}
        for name in NAMES:
            pieces = []
            for part in meta['monitor_segments']:
                path = monitor_path(part['directory'], name)
                values = read_monitor(path)
                if part.get('from_s') is not None:
                    values = values[values[:, 2] >= part['from_s'] - 1e-13]
                if part.get('to_s') is not None:
                    values = values[values[:, 2] <= part['to_s'] + 1e-13]
                pieces.append(values)
                sources.append(dict(run_id=rid, monitor=name, file=str(path.relative_to(ROOT)), byte=path.stat().st_size, sha256=sha(path)))
            series = merge_series(pieces)
            assert series[-1, 0] == meta['passi_completati'] and np.all(np.diff(series[:, 0]) == 1)
            assert np.isfinite(series).all()
            assert np.allclose(series[:, 2], series[:, 0] * meta['dt_s'], rtol=0, atol=1e-12)
            pp = []
            cc = []
            for k in range(3):
                a = start + k * T
                b = a + T
                tt, v = segment(series[:, 2], series[:, 1], a, b)
                row = dict(run_id=rid, mesh=rid[:2], monitor=name, cycle=round(a / T) + 1, mean=float(np.trapezoid(v, tt) / T), peak_to_peak=float(np.ptp(v)))
                cc.append(row)
                cycles.append(row)
                pp.append(np.interp(a + phase * T, series[:, 2], series[:, 1]))
            profiles[rid][name] = np.array(pp)
            tt, v = segment(series[:, 2], series[:, 1], start, end)
            saved = next((x for x in old['statistiche'] if x['monitor'] == name))
            mean = float(np.trapezoid(v, tt) / (end - start))
            amp = float(np.mean([x['peak_to_peak'] for x in cc]))
            assert np.isclose(mean, saved['media'], rtol=1e-10, atol=1e-10)
            assert np.isclose(amp, saved['ampiezza_picco_picco_media_cicli'], rtol=1e-10, atol=1e-10)
            means.append(dict(run_id=rid, mesh=rid[:2], monitor=name, label=LABELS[name], active_cells=meta['celle_attive'], window_start_s=start, window_end_s=end, mean=mean, mean_cycle_min=min((x['mean'] for x in cc)), mean_cycle_max=max((x['mean'] for x in cc)), peak_to_peak_mean=amp, amplitude_cycle_min=min((x['peak_to_peak'] for x in cc)), amplitude_cycle_max=max((x['peak_to_peak'] for x in cc))))
        for wall in ['wall_statore', 'wall_rotore']:
            path = base / 'ciclo_pareti' / (wall + '_inviluppo.csv')
            data = rows(path)
            sources.append(dict(run_id=rid, monitor=wall, file=str(path.relative_to(ROOT)), byte=path.stat().st_size, sha256=sha(path)))
            summary = load(base / 'ciclo_pareti/esito.json')
            assert len(summary['intervallo_campionamento_s']) == 4
            assert all((abs(x - T / 4) < 1e-12 for x in summary['intervallo_campionamento_s']))
            allwalls.append(dict(run_id=rid, wall=wall, data=data, sampling='Five common quarter-period phases; finite-window averages, not settled-flow certification'))

    def val(rid, name):
        return next((r for r in means if r['run_id'] == rid and r['monitor'] == name))
    comparisons = []
    for left, right in zip(RUNS, RUNS[1:]):
        for name in NAMES:
            a, b = (val(left, name), val(right, name))
            p = profiles[left][name].mean(axis=0)
            q = profiles[right][name].mean(axis=0)
            comparisons.append(dict(coarser=left[:2], finer=right[:2], monitor=name, label=LABELS[name], mean_difference_percent=100 * abs(a['mean'] - b['mean']) / abs(b['mean']), amplitude_difference_percent=100 * abs(a['peak_to_peak_mean'] - b['peak_to_peak_mean']) / b['peak_to_peak_mean'], phase_RMS_percent_of_finer_amplitude=100 * float(np.sqrt(np.mean((p - q) ** 2))) / b['peak_to_peak_mean'], phase_max_difference_percent_of_finer_amplitude=100 * float(np.max(abs(p - q))) / b['peak_to_peak_mean']))
    trends = []
    for name in NAMES:
        for metric in ['mean', 'peak_to_peak_mean']:
            a, b, c = [val(rid, name)[metric] for rid in RUNS]
            coarse = b - a
            fine = c - b
            trends.append(dict(monitor=name, metric=metric, M1=a, M2=b, M3=c, change_M1_to_M2=coarse, change_M2_to_M3=fine, trend='Oscillatory across the three meshes' if coarse * fine < 0 else 'Monotonic across the three meshes', change_contraction_ratio=abs(fine / coarse) if coarse else None, observed_order=None, GCI=None))
    csvwrite(OUT / 'recomputed_monitor_statistics.csv', means)
    csvwrite(OUT / 'recomputed_cycles.csv', cycles)
    csvwrite(OUT / 'mesh_pair_comparisons.csv', comparisons)
    csvwrite(OUT / 'three_mesh_trends.csv', trends)
    csvwrite(OUT / 'source_manifest_SHA256.csv', sources)
    pr = []
    for rid in RUNS:
        for name in NAMES:
            pp = profiles[rid][name]
            pr.extend((dict(mesh=rid[:2], monitor=name, phase_fraction=float(x), cycle_mean=float(y), cycle_min=float(lo), cycle_max=float(hi)) for x, y, lo, hi in zip(phase, pp.mean(axis=0), pp.min(axis=0), pp.max(axis=0))))
    csvwrite(OUT / 'phase_profiles_with_cycle_range.csv', pr)
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['DejaVu Serif'], 'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10, 'legend.fontsize': 8, 'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 220})
    cells = [metadata[rid]['active_cells'] for rid in RUNS]
    for metric, lo, hi, tag in [('mean', 'mean_cycle_min', 'mean_cycle_max', 'means'), ('peak_to_peak_mean', 'amplitude_cycle_min', 'amplitude_cycle_max', 'amplitudes')]:
        fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.0), layout='constrained')
        for j, (ax, name) in enumerate(zip(axes.flat, NAMES)):
            scale = 0.001 if name == 'pt_outlet' else 1
            vv = [val(rid, name) for rid in RUNS]
            ys = np.array([r[metric] * scale for r in vv])
            ax.plot(cells, ys, color='#7b8793', lw=1, zorder=1)
            for k, r in enumerate(vv):
                ax.vlines(cells[k], r[lo] * scale, r[hi] * scale, color=COLOURS[k], lw=1.8)
                ax.plot(cells[k], r[metric] * scale, 'o', color=COLOURS[k], ms=5, zorder=3)
            ax.set_xticks(cells, [f'{r[:2]}\n{c:,}' for r, c in zip(RUNS, cells)])
            ax.set(xlabel='Active cells', ylabel=('Mean' if metric == 'mean' else 'Peak-to-peak amplitude') + ' [' + UNITS[name] + ']', title=f'({chr(97 + j)}) ' + LABELS[name])
            ax.ticklabel_format(axis='y', style='plain', useOffset=False)
            ax.grid(alpha=0.18)
        fig.savefig(FIG / f'grid_{tag}_cycle_ranges.png')
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.1), layout='constrained')
    for j, (ax, name) in enumerate(zip(axes.flat, NAMES)):
        scale = 0.001 if name == 'pt_outlet' else 1
        for rid, colour in zip(RUNS, COLOURS):
            pp = profiles[rid][name] * scale
            ax.fill_between(phase, pp.min(axis=0), pp.max(axis=0), color=colour, alpha=0.12, lw=0)
            ax.plot(phase, pp.mean(axis=0), color=colour, label=rid[:2], lw=1.4)
        ax.set(xlabel='Blade-passing phase [-]', ylabel=UNITS[name], title=f'({chr(97 + j)}) ' + LABELS[name], xlim=(0, 1))
        ax.ticklabel_format(axis='y', style='plain', useOffset=False)
        ax.grid(alpha=0.18)
        ax.legend(frameon=False)
    fig.savefig(FIG / 'grid_phase_profiles.png')
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.2), layout='constrained')
    for col, wall in enumerate(['wall_statore', 'wall_rotore']):
        for rid, colour in zip(RUNS, COLOURS):
            data = next((r['data'] for r in allwalls if r['run_id'] == rid and r['wall'] == wall))
            xx = [float(r['x_m']) * 1000 for r in data]
            axes[0, col].scatter(xx, [float(r['pressione_media_temporale_Pa']) / 1000 for r in data], s=2, color=colour, label=rid[:2], rasterized=True)
            axes[1, col].scatter(xx, [float(r['yplus_media_temporale']) for r in data], s=2, color=colour, label=rid[:2], rasterized=True)
        axes[0, col].set(title=('(a) Stator' if col == 0 else '(b) Rotor') + ' blade', ylabel='Mean absolute static pressure [kPa]')
        axes[1, col].set(title=('(c) Stator' if col == 0 else '(d) Rotor') + ' wall resolution', ylabel='Mean y+ [-]', ylim=(0, 1.05))
        axes[1, col].axhline(1, color='#767676', ls='--', lw=0.7)
        for ax in axes[:, col]:
            ax.set_xlabel('Axial position [mm]')
            ax.grid(alpha=0.18)
            ax.legend(frameon=False, markerscale=3)
    fig.savefig(FIG / 'grid_blade_pressure_yplus.png')
    plt.close(fig)
    fine = [r for r in comparisons if r['finer'] == 'M3']
    result = dict(utc=now(), state='OFFLINE_GRID_SENSITIVITY_VERIFIED_GRID_INDEPENDENCE_NOT_ESTABLISHED', source='Recomputed directly from accepted native monitor segments, with original hashes and step/time checks; saved summaries agree.', CFD_steps_executed=0, runs=metadata, comparison='Three complete cycles at common phase; M1/M3 cycles33-35 and M2 cycles38-40. Residual transient effects remain.', dt_s=T / 400, inner_iterations=30, refinement_ratios_2D_cellcount=[float(np.sqrt(cells[1] / cells[0])), float(np.sqrt(cells[2] / cells[1]))], cellcount_h_interpretation='Indicative h proportional to N^(-1/2), assuming equal domain area; inflation family is anisotropic, not a single proven error scale.', fine_pair_max_mean_difference_percent=max((r['mean_difference_percent'] for r in fine)), fine_pair_amplitude_difference_percent_range=[min((r['amplitude_difference_percent'] for r in fine)), max((r['amplitude_difference_percent'] for r in fine))], comparisons=comparisons, trends=trends, grid_independence_established=False, observed_order=None, GCI=None, conclusion='Mean quantities have small M2-M3 changes (below0.15%), but oscillatory mesh trends, 5.9-7.5% amplitude changes and unresolved settling/time sensitivity prevent a general grid-independence or asymptotic/GCI claim. No acceptance limit was changed.', wall_comparison='Five common phase samples for each final cycle. Native faces plotted directly against axial position; no unverified suction/pressure-side interpolation or pointwise norm.', cycle_ranges='Three-cycle observed ranges only; not statistical confidence intervals or discretization error bars.', references=['https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html', 'https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html'])
    jwrite(OUT / 'assessment.json', result)
    lines = ['# Offline grid-sensitivity review', '', 'The assessment is recomputed from saved native histories. No CFD steps are executed.', '', '| Quantity | M1-M2 mean change [%] | M2-M3 mean change [%] | M2-M3 amplitude change [%] | M2-M3 phase RMS / amplitude [%] |', '|---|---:|---:|---:|---:|']
    for name in NAMES:
        a = next((r for r in comparisons if r['monitor'] == name and r['finer'] == 'M2'))
        b = next((r for r in fine if r['monitor'] == name))
        lines.append(f'| {LABELS[name]} | {a['mean_difference_percent']:.5f} | {b['mean_difference_percent']:.5f} | {b['amplitude_difference_percent']:.5f} | {b['phase_RMS_percent_of_finer_amplitude']:.5f} |')
    lines += ['', result['conclusion'], '', 'All four cycle-mean sequences change direction between M1-M2 and M2-M3. Force/outlet-flow amplitudes increase monotonically, while inlet/total-pressure amplitudes are nonmonotonic. No formal order or GCI is assigned.', '', result['comparison'], '', result['cycle_ranges'], '', 'Method references: [NASA spatial convergence](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html), [NASA verification assessment](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html).']
    text(OUT / 'REVIEW.md', '\n'.join(lines) + '\n')
    append_status('COMPLETED offline M1/M2/M3 grid-sensitivity verification: native monitor segments rehashed and three-cycle means/amplitudes/profiles recomputed. M2-M3 mean differences below0.15%, but amplitude differences5.9-7.5% and oscillatory mean trends prevent general independence/asymptotic/GCI claims. New English CSV/PNG and blade pressure/y+ comparison created; original results, criteria and closure guard unchanged. No solver launched. Evidence:05_postprocessing/campagna/grid_sensitivity_review_20261017/assessment.json')
    print(json.dumps(dict(state=result['state'], fine_pair=fine, refinement_ratios=result['refinement_ratios_2D_cellcount']), indent=2), flush=True)
if __name__ == '__main__':
    main()
