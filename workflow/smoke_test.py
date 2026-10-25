from common import *
from pipeline import snapshot, FLUIDS
import numpy as np, time
SMOKE = WORK / 'prova_breve'
SMOKE.mkdir(exist_ok=True)
assert not (SMOKE / 'smoke_final.cas.h5').exists(), 'Prova gia eseguita: non sovrascrivere risultati'
s.settings.file.read_case_data(file_name=str(WORK / 'checkpoint_comune' / 'checkpoint.cas.h5'))
for n in s.settings.solution.monitor.report_files.get_object_names():
    s.settings.solution.monitor.report_files[n].file_name = str(SMOKE / (n + '.out'))
s.settings.file.auto_save.data_frequency = 0
s.settings.solution.run_calculation.transient_controls.time_step_size = 3e-06
s.settings.solution.run_calculation.transient_controls.max_iter_per_time_step = 30
protected = [original_path('stadio_assiale_2D_CFD_final.cas.h5'), original_path('stadio_assiale_2D_CFD_final.dat.h5')] + [original_path(n + '-rfile.out') for n in ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet']]
hashes = {str(p): sha(p) for p in protected}
before = snapshot(s, SMOKE / 'snapshot_000.npz')
assert abs(before['solution_time_s'] - 0.010653) < 1e-14
start = time.monotonic()
frames = [before]
for i in range(1, 4):
    s.settings.solution.run_calculation.dual_time_iterate(time_step_count=2, max_iter_per_step=30)
    frames.append(snapshot(s, SMOKE / f'snapshot_{i:03d}.npz'))
    print('SMOKE_PROGRESS', i * 2, frames[-1]['solution_time_s'], flush=True)
after = frames[-1]
expected_time = before['solution_time_s'] + 6 * 3e-06
assert abs(after['solution_time_s'] - expected_time) < 1e-12
shift = np.array(after['rotor_wall_node_centroid']) - np.array(before['rotor_wall_node_centroid'])
expected = np.array([0, -150 * 6 * 3e-06, 0])
assert np.max(abs(shift - expected)) < 1e-06
assert int(s.fields.reduction.count(locations=FLUIDS)) == 289671
assert not s.scheme.eval("(rpgetvar 'adapt/dynamic?)")
assert all((sha(p) == hashes[str(p)] for p in protected))
assert all((z['finite'] for d in after['extrema'].values() for z in d.values()))
assert min((z['min'] for z in after['extrema']['density'].values())) > 0
assert min((z['min'] for z in after['extrema']['temperature'].values())) > 0
s.settings.file.write_case_data(file_name=str(SMOKE / 'smoke_final.cas.h5'))
manifest = [dict(file=p.name, byte=p.stat().st_size, sha256=sha(p)) for p in sorted(SMOKE.glob('smoke_final.*.h5'))]
computed_before = s.settings.solution.report_definitions.compute(report_defs=['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet'])
s.settings.file.read_case_data(file_name=str(SMOKE / 'smoke_final.cas.h5'))
assert abs(float(s.scheme.eval("(rpgetvar 'flow-time)")) - expected_time) < 1e-12
computed_after = s.settings.solution.report_definitions.compute(report_defs=['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet'])
for a, b in zip(computed_before, computed_after):
    for k in a:
        assert abs(a[k][0] - b[k][0]) < max(1e-08, abs(a[k][0]) * 1e-10)
result = dict(utc=now(), stato='AVANZAMENTO_SALVATAGGIO_RILETTURA_VERIFICATI_RENDER_IN_ATTESA', steps=6, dt_s=3e-06, max_iter_per_step=30, tempo_iniziale_s=before['solution_time_s'], tempo_finale_s=expected_time, spostamento_rotore_xyz_m=shift.tolist(), spostamento_atteso_xyz_m=expected.tolist(), celle_attive=289671, amr_automatico=False, originali_e_monitor_storici_invariati=True, wall_seconds=time.monotonic() - start, frames=frames, manifest=manifest, report_finali=computed_after)
jwrite(SMOKE / 'smoke_verifica.json', result)
append_status('Prova breve PyFluent eseguita: 6 passi da t=0.010653 a 0.010671 s, dt=3e-6 s, massimo 30 iterazioni/passo; mesh attiva invariata e AMR disattivo. Spostamento del rotore verificato contro Vy=-150 m/s. Salvataggio e rilettura coerenti, report coincidenti; baseline e quattro monitor originali invariati. Rendering Mach/pressione in verifica; non è una prova di convergenza.')
print('SMOKE_SAVED_RELOADED_OK', json.dumps({k: result[k] for k in ['tempo_finale_s', 'spostamento_rotore_xyz_m', 'wall_seconds']}), flush=True)
