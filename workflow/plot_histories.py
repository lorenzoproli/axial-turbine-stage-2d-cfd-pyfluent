"""English physical-time histories and storage-inclusive mass-balance plots."""
from data_schema import csv, json
from common import *
from monitor_paths import monitor_path
from monitor_analysis import read_monitor, merge_series, accepted_monitor_segments, NAMES
from english_labels import install, translate
install()
import numpy as np

def plot(run_id):
    import matplotlib.pyplot as plt
    d = case_directory(run_id)
    meta = json.loads((d / 'progress.json').read_text())
    assert meta['completed_steps'] == meta['planned_steps'], 'Use a completed, closed data window'
    directories = accepted_monitor_segments(meta, d)
    values = {}
    sources = []
    for name in NAMES:
        pieces = []
        for segment in directories:
            p = monitor_path(segment['directory'], name)
            x = read_monitor(p)
            if segment.get('from_s') is not None:
                x = x[x[:, 2] >= segment['from_s'] - 1e-13]
            if segment.get('to_s') is not None:
                x = x[x[:, 2] <= segment['to_s'] + 1e-13]
            pieces.append(x)
            sources.append(dict(file=str(p), sha256=sha(p)))
        values[name] = merge_series(pieces)
    units = ['N (1 m depth)', 'kg/s', 'kg/s', 'Pa']
    fig, axs = plt.subplots(2, 2, figsize=(12.8, 7.2), layout='constrained')
    for ax, name, unit in zip(axs.flat, NAMES, units):
        x = values[name]
        ax.plot(x[:, 2], x[:, 1], lw=0.8, color='#155b7d')
        ax.axvspan(*meta['averaging_window_s'], color='#76aa97', alpha=0.22, label='Assessed three-period window')
        ax.set(xlabel='Physical time [s]', ylabel=unit, title=translate(name))
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle(run_id + ': full recorded history; settling excluded from statistics')
    out = project_path(ROOT / 'results/figures/generated/campaign' / run_id)
    out.mkdir(parents=True, exist_ok=True)
    p = out / 'physical_time_histories.png'
    fig.savefig(p, dpi=180)
    plt.close(fig)
    source = project_path(ROOT / '05_postprocessing/campagna' / run_id / 'difetto_massa_BDF2.csv')
    if source.exists():
        with source.open(encoding='utf-8-sig') as stream:
            rows = list(csv.DictReader(stream))
        t = np.array([float(r['physical_time_s']) for r in rows])
        fig, axs = plt.subplots(2, 1, figsize=(12.8, 6.5), layout='constrained', sharex=True)
        for key, label, color in [('net_inward_flow_kg_s', 'Net inward boundary flow', '#155b7d'), ('dM_dt_BDF2_kg_s', 'Domain mass storage (BDF2)', '#aa622e')]:
            axs[0].plot(t, [float(r[key]) for r in rows], label=label, color=color, lw=1)
        axs[0].set(ylabel='Mass rate [kg/s]', title=run_id + ': boundary flux and domain storage')
        axs[0].legend()
        axs[0].grid(alpha=0.2)
        axs[1].plot(t, [float(r['defect_percent_of_inlet']) for r in rows], color='#155b7d', lw=0.8)
        axs[1].set(xlabel='Physical time [s]', ylabel='Defect / inlet flow [%]')
        axs[1].grid(alpha=0.2)
        fig.savefig(out / 'mass_conservation_storage.png', dpi=180)
        plt.close(fig)
        sources.append(dict(file=str(source), sha256=sha(source)))
    jwrite(out / 'history_plot_provenance.json', dict(utc=now(), sources=sources, images=[dict(file=str(p), sha256=sha(p)) for p in [out / 'physical_time_histories.png', out / 'mass_conservation_storage.png'] if p.exists()]))
    print('PHYSICAL_HISTORIES_READY', run_id, flush=True)
if __name__ == '__main__':
    import sys
    for run in sys.argv[1:] or ['ITER60', 'T400']:
        plot(run)
