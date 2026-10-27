"""Equivalent complete-period windows and consistent restart segment merging."""
from data_schema import csv, json
from common import *
from english_labels import install
install()
from monitor_paths import monitor_path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
NAMES = ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet']
UNITS = dict(zip(NAMES, ['N (depth 1 m)', 'kg/s', 'kg/s', 'Pa']))

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
    assert np.all(np.diff(a[:, 2]) > 0), f'Non-increasing times: {path}'
    return a

def segment(t, v, a, b):
    tolerance = 64 * np.finfo(float).eps * max(abs(t[0]), abs(t[-1]), abs(a), abs(b), np.finfo(float).tiny)
    assert t[0] <= a + tolerance and t[-1] >= b - tolerance, 'The series does not cover the requested window'
    k = (t > a) & (t < b)
    return (np.r_[a, t[k], b], np.r_[np.interp(a, t, v), v[k], np.interp(b, t, v)])

def merge_series(pieces):
    """Merge duplicate restart samples only when their values agree."""
    x = np.concatenate(pieces)
    x = x[np.argsort(x[:, 2])]
    duplicates = np.where(abs(np.diff(x[:, 2])) < 1e-13)[0]
    for i in duplicates:
        assert np.isclose(x[i, 1], x[i + 1, 1], rtol=1e-10, atol=1e-12), 'Conflicting monitor values at restart'
        assert x[i, 0] == x[i + 1, 0], 'Different global steps at the same physical time'
    if len(duplicates):
        x = np.delete(x, duplicates, axis=0)
    assert np.all(np.diff(x[:, 2]) > 0)
    return x

def accepted_monitor_segments(meta, run_dir):
    """Resolve accepted restart ranges from explicit saved boundaries."""
    run_dir = project_path(run_dir)
    monitor_segments = meta.get('monitor_segments')
    if not monitor_segments:
        current = project_path(meta.get('current_output', run_dir))
        resources = meta.get('resource_segments', [])
        if current != run_dir:
            if not resources or resources[-1].get('initial_time_s') is None:
                raise ValueError('Restarted monitor history requires an explicit accepted segment boundary.')
            boundary = resources[-1]['initial_time_s']
            monitor_segments = [dict(directory=str(run_dir), from_s=None, to_s=boundary),
                                dict(directory=str(current), from_s=boundary, to_s=None)]
        else:
            monitor_segments = [dict(directory=str(run_dir), from_s=None, to_s=None)]
    return monitor_segments

def analyse(run_dir, monitor_dirs=None):
    run_dir = project_path(run_dir)
    meta = json.loads((run_dir / 'progress.json').read_text())
    run_id = meta['id']
    start, end = meta['averaging_window_s']
    assert meta['completed_steps'] == meta['planned_steps'], 'Run is incomplete'
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
            stats.append(dict(run_id=run_id, monitor=name, window_cycle_index=k, start_time_s=a, end_time_s=b, mean=float(np.trapezoid(v, t) / T), minimum=float(v.min()), maximum=float(v.max()), peak_to_peak=float(np.ptp(v)), unit=UNITS[name]))
        rows = [r for r in stats if r['monitor'] == name]
        for k in range(1, ncycles):
            a, b = (rows[k - 1], rows[k])
            den = max(abs(b['mean']), 1e-20)
            amp = max(b['peak_to_peak'], 1e-20)
            comparisons.append(dict(run_id=run_id, monitor=name, from_window_cycle_index=k - 1, to_window_cycle_index=k, mean_change_percent=100 * abs(b['mean'] - a['mean']) / den, amplitude_change_percent=100 * abs(b['peak_to_peak'] - a['peak_to_peak']) / amp, phase_rms_percent_of_amplitude=100 * float(np.sqrt(np.mean((profiles[name][k] - profiles[name][k - 1]) ** 2))) / amp))
        t, v = segment(tt, x[:, 1], start, end)
        overall.append(dict(run_id=run_id, monitor=name, timestep_s=meta['timestep_s'], inner_iterations_per_step=meta['inner_iterations_per_step'], start_time_s=start, end_time_s=end, mean=float(np.trapezoid(v, t) / (end - start)), mean_cycle_peak_to_peak=float(np.mean([r['peak_to_peak'] for r in rows])), unit=UNITS[name]))
    mass = []
    for k in range(ncycles):
        a = start + k * T
        b = a + T
        t, vi = segment(tt, data['mdot_inlet'][:, 1], a, b)
        _, vo = segment(tt, data['mdot_outlet'][:, 1], a, b)
        mi = float(np.trapezoid(vi, t) / T)
        mo = float(np.trapezoid(vo, t) / T)
        mass.append(dict(run_id=run_id, window_cycle_index=k, start_time_s=a, end_time_s=b, inlet_kg_s=mi, outlet_kg_s=mo, net_inward_flow_kg_s=mi + mo, net_flow_percent_of_inlet=100 * abs(mi + mo) / abs(mi), integrated_net_inward_mass_kg=(mi + mo) * T, domain_storage='Domain storage requires the domain-mass export'))
    criteria = dict(maximum_mean_change_percent=0.5, maximum_amplitude_change_percent=5, maximum_phase_rms_percent_of_amplitude=10, maximum_mean_mass_flux_imbalance_percent=0.5)
    checks = dict(means=all((r['mean_change_percent'] <= 0.5 for r in comparisons)), amplitudes=all((r['amplitude_change_percent'] <= 5 for r in comparisons)), phase=all((r['phase_rms_percent_of_amplitude'] <= 10 for r in comparisons)), mass_flows=all((r['net_flow_percent_of_inlet'] <= 0.5 for r in mass)))
    summary = dict(id=run_id, utc=now(), window_s=[start, end], cycles=ncycles, proposed_diagnostic_criteria=criteria, checks=checks, monitor_periodicity_within_proposed_criteria=all(checks.values()), physical_validation=False, mass_conservation_including_storage_checked=False, statistics=overall, cycle_comparisons=comparisons, boundary_mass_balance=mass, sources=sources)
    out = project_path(ROOT / '05_postprocessing' / 'campagna' / run_id)
    figdir = project_path(ROOT / 'results/figures/generated' / 'campaign' / run_id)
    masspieces = []
    for seg in monitor_segments:
        p = project_path(seg['directory']) / 'massa_dominio-rfile.out'
        if not p.exists():
            masspieces = []
            break
        x = read_monitor(p)
        sources.append(dict(file=str(p), sha256=sha(p), quantity='domain_mass_kg'))
        if seg.get('from_s') is not None:
            x = x[x[:, 2] >= seg['from_s'] - 1e-13]
        if seg.get('to_s') is not None:
            x = x[x[:, 2] <= seg['to_s'] + 1e-13]
        masspieces.append(x)
    if masspieces:
        xm = merge_series(masspieces)
        assert np.array_equal(xm[:, 2], tt), 'Domain-mass and boundary-flow monitors are not synchronized'
        balance = []
        for k in range(ncycles):
            a = start + k * T
            b = a + T
            t, vi = segment(tt, data['mdot_inlet'][:, 1], a, b)
            _, vo = segment(tt, data['mdot_outlet'][:, 1], a, b)
            integrated = float(np.trapezoid(vi + vo, t))
            stored = float(np.interp(b, tt, xm[:, 1]) - np.interp(a, tt, xm[:, 1]))
            normalization = float(np.trapezoid(abs(vi), t))
            balance.append(dict(run_id=run_id, window_cycle_index=k, start_time_s=a, end_time_s=b, integrated_net_inward_mass_kg=integrated, domain_mass_change_kg=stored, integral_mass_defect_kg=integrated - stored, integral_mass_defect_percent_of_inlet_mass=100 * abs(integrated - stored) / normalization, method='Trapezoidal flux integration and endpoint-interpolated domain mass; quadrature error is distinct from the BDF2 defect'))
        dt = meta['timestep_s']
        assert np.allclose(np.diff(tt), dt, rtol=1e-07, atol=1e-12)
        derivative = (3 * xm[2:, 1] - 4 * xm[1:-1, 1] + xm[:-2, 1]) / (2 * dt)
        defect = data['mdot_inlet'][2:, 1] + data['mdot_outlet'][2:, 1] - derivative
        keep = (tt[2:] >= start) & (tt[2:] <= end)
        bdf = [dict(run_id=run_id, physical_time_s=float(t), dM_dt_BDF2_kg_s=float(d), net_inward_flow_kg_s=float(d + e), mass_defect_kg_s=float(e), defect_percent_of_inlet=100 * float(e) / abs(float(mi))) for t, d, e, mi in zip(tt[2:][keep], derivative[keep], defect[keep], data['mdot_inlet'][2:, 1][keep])]
        csvwrite(out / 'bilancio_massa_con_accumulo_cicli.csv', balance)
        csvwrite(out / 'difetto_massa_BDF2.csv', bdf)
        summary.update(mass_conservation_including_storage_checked=True, mass_balance_including_storage=balance, BDF2_defect_percent_of_inlet=dict(absolute_mean=float(np.mean([abs(r['defect_percent_of_inlet']) for r in bdf])), absolute_maximum=float(max((abs(r['defect_percent_of_inlet']) for r in bdf))), note='Constant-step BDF2 after settling; inward-positive mass flow; 1 m reference depth'))
        for row in mass:
            row['domain_storage'] = 'Assessed separately in balance_mass_con_storage_cycles.csv and defect_mass_BDF2.csv'
    csvwrite(out / 'statistiche_cicli.csv', stats)
    csvwrite(out / 'confronto_cicli.csv', comparisons)
    csvwrite(out / 'profili_in_fase.csv', [dict(run_id=run_id, monitor=name, window_cycle_index=k, phase_fraction=float(ph), physical_time_s=float(start + (k + ph) * T), value=float(v), unit=UNITS[name]) for name, cycles in profiles.items() for k, values in enumerate(cycles) for ph, v in zip(phase, values)])
    csvwrite(out / 'statistiche_finestra.csv', overall)
    csvwrite(out / 'balance_mass_flows.csv', mass)
    jwrite(out / 'analysis.json', summary)
    figdir.mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for ax, name in zip(axs.flat, NAMES):
        for k, values in enumerate(profiles[name]):
            ax.plot(phase, values, label=f'Cycle {k + 1}', lw=1)
        ax.set(xlabel='Phase from window start [-]', ylabel=UNITS[name], title=name)
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(f'{run_id}: three complete periods after excluded settling')
    fig.savefig(figdir / 'confronto_in_fase.png', dpi=150)
    plt.close(fig)
    return summary
if __name__ == '__main__':
    import sys
    r = analyse(case_directory(sys.argv[1]))
    print(json.dumps({k: v for k, v in r.items() if k in ['id', 'checks', 'monitor_periodicity_within_proposed_criteria']}, ensure_ascii=False))
