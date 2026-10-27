"""Actual inner iterations and residuals from native transcripts at physical times."""
from data_schema import csv, json
from common import *
from english_labels import install
install()
from monitor_paths import monitor_path
import re, numpy as np
EQ = ['continuity', 'x_velocity', 'y_velocity', 'energy', 'k', 'omega']

def parse(path, expected_iterations=None):
    rows = []
    steps = []
    block = []
    for line in project_path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        parts = line.split()
        if len(parts) >= 9 and parts[0].isdigit() and re.fullmatch('\\d+:\\d+:\\d+', parts[7]):
            try:
                block.append((int(parts[0]), [float(v) for v in parts[1:7]], int(parts[8])))
            except ValueError:
                pass
        m = re.search('Flow time\\s*=\\s*([0-9.eE+-]+)s, time step\\s*=\\s*(\\d+)', line)
        if m and block:
            t = float(m.group(1))
            step = int(m.group(2))
            start = block[0][0]
            last = block[-1][0]
            if expected_iterations and len(block) == expected_iterations and (block[0][2] == expected_iterations - 1) and (block[-1][2] == 0):
                assert all((i + remaining == last for i, _, remaining in block))
                start -= 1
            assert all((b[0] > a[0] for a, b in zip(block, block[1:])))
            for iteration, values, remaining in block:
                rows.append(dict(physical_time_s=t, global_step=step, global_iteration=iteration, inner_iteration=iteration - start, step_initial_state=iteration == start, **dict(zip(EQ, values))))
            steps.append(dict(physical_time_s=t, global_step=step, actual_inner_iterations=last - start, **dict(zip(['final_' + e for e in EQ], block[-1][1]))))
            block = []
    return (rows, steps)

def analyse_residuals(run_id, paths):
    meta = json.loads((case_directory(run_id) / 'progress.json').read_text())
    allrows = []
    allsteps = []
    excluded_steps = 0
    segments = {project_path(seg['directory']).resolve(): seg for seg in meta.get('monitor_segments', [])}
    for p in paths:
        r, st = parse(p, meta['inner_iterations_per_step'])
        segment = segments.get(project_path(p).parent.resolve())
        if segment and (segment.get('from_s') is not None or segment.get('to_s') is not None):
            full_clock = {}
            source = monitor_path(project_path(p).parent, 'forza_y_rotore')
            for line in source.read_text(encoding='utf-8', errors='replace').splitlines():
                values = line.split()
                if len(values) == 3:
                    try:
                        full_clock[int(values[0])] = float(values[2])
                    except ValueError:
                        pass

            def included(row):
                t = full_clock[row['global_step']]
                return (segment.get('from_s') is None or t > segment['from_s'] + 1e-13) and (segment.get('to_s') is None or t <= segment['to_s'] + 1e-13)
            old_count = len(st)
            r = [row for row in r if included(row)]
            st = [row for row in st if included(row)]
            excluded_steps += old_count - len(st)
        allrows += r
        allsteps += st
    assert allsteps
    clock = {}
    directories = [project_path(seg['directory']) for seg in meta.get('monitor_segments', [dict(directory=str(case_directory(run_id)))])]
    directories = list(dict.fromkeys(directories + [project_path(path).parent for path in paths]))
    for directory in directories:
        p = monitor_path(directory, 'forza_y_rotore')
        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
            a = line.split()
            if len(a) == 3:
                try:
                    clock[int(a[0])] = float(a[2])
                except ValueError:
                    pass
    for r in allrows + allsteps:
        assert r['global_step'] in clock, 'Missing full-precision step time'
        r['transcript_printed_time_s'] = r['physical_time_s']
        r['physical_time_s'] = clock[r['global_step']]
    out = project_path(ROOT / '05_postprocessing/campagna' / run_id)
    csvwrite(out / 'residui_iterazioni.csv', allrows)
    csvwrite(out / 'residui_fine_passo.csv', allsteps)
    source_records = []
    for p in paths:
        try:
            source_records.append(dict(file=str(p), sha256=sha(project_path(p)), hash_result='VERIFIED'))
        except OSError:
            source_records.append(dict(file=str(p), sha256=None, hash_result='RINVIATO_HANDLE_TRANSCRIPT_ANCORA_APERTO'))
    result = dict(run_id=run_id, steps=len(allsteps), minimum_inner_iterations=min((r['actual_inner_iterations'] for r in allsteps)), discarded_superseded_steps_after_checkpoint_rollback=excluded_steps, maximum_inner_iterations=max((r['actual_inner_iterations'] for r in allsteps)), sources=source_records, note='Residuals use Fluent printed precision; full-precision time comes from the native monitor at the same global step. Inner row zero is the state before advancement.')
    jwrite(out / 'residui_riepilogo.json', result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12.8, 5), layout='constrained')
    for e in EQ:
        ax.semilogy([r['physical_time_s'] for r in allsteps], [r['final_' + e] for r in allsteps], label=e, lw=0.8)
    ax.set(xlabel='Physical time [s]', ylabel='Scaled residual at step end [-]', title=run_id + ': end-of-step residuals; additional convergence checks required')
    ax.legend(ncol=3)
    ax.grid(alpha=0.2)
    figdir = project_path(ROOT / 'results/figures/generated/campaign' / run_id)
    figdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figdir / 'residui_fine_passo.png', dpi=150)
    plt.close(fig)
    return result
