"""Verify loaded checkpoint geometry, physical setup and reports before advancement."""
from common import *
from pipeline import FLUIDS
from monitor_paths import monitor_path
from monitor_analysis import read_monitor
from verify_restart_geometry import verify_loaded_geometry
from ansys.fluent.core.fields.field_data_interfaces import ScalarFieldDataRequest
import numpy as np, h5py

def verify(s, target, meta, case, time_s, step):
    assert int(s.scheme.eval("(rpgetvar 'time-step)")) == step
    assert int(s.fields.reduction.count(locations=FLUIDS)) == meta['celle_attive']
    assert not s.scheme.eval("(rpgetvar 'adapt/dynamic?)")
    geometry = verify_loaded_geometry(s, case)
    original = json.loads((target / 'setup_effettivo.json').read_text())
    assert json.dumps(original['setup'], sort_keys=True) == json.dumps(s.settings.setup.get_state(), sort_keys=True), 'Checkpoint physical setup changed'
    assert json.dumps(original['solution']['methods'], sort_keys=True) == json.dumps(s.settings.solution.methods.get_state(), sort_keys=True), 'Numerical methods changed'
    names = ['forza_y_rotore', 'mdot_inlet', 'mdot_outlet', 'pt_outlet', 'massa_dominio']
    computed = {name: float(values[0]) for group in s.settings.solution.report_definitions.compute(report_defs=names) for name, values in group.items()}
    rows = []
    for name in names:
        candidates = []
        for segment in meta['monitor_segments']:
            path = monitor_path(segment['directory'], name)
            series = read_monitor(path)
            selected = series[(abs(series[:, 2] - time_s) < 1e-12) & (series[:, 0] == step)]
            if len(selected):
                candidates.append((path, selected[-1, 1]))
        assert candidates, 'Missing checkpoint-time monitor ' + name
        path, expected = candidates[-1]
        actual = computed[name]
        assert np.isclose(actual, expected, rtol=1e-09, atol=1e-10), 'Loaded checkpoint report differs: ' + name
        rows.append(dict(monitor=name, checkpoint_time_s=time_s, global_step=step, saved_value=float(expected), recomputed_value=actual, absolute_difference=abs(actual - expected), source=str(path)))
    fields = {}
    for field in ['density', 'temperature', 'pressure', 'mach-number']:
        values = s.fields.field_data.get_field_data(ScalarFieldDataRequest(surfaces=FLUIDS, field_name=field, node_value=False))
        assert all((np.isfinite(value).all() for value in values.values()))
        low = min((float(value.min()) for value in values.values()))
        high = max((float(value.max()) for value in values.values()))
        if field != 'mach-number':
            assert low > 0
        fields[field] = dict(min=low, max=high)
    data = case.with_name(case.name.replace('.cas.h5', '.dat.h5'))
    with h5py.File(data, 'r') as f:
        keys = list(f['results/1/phase-1/cells'])
    required = [f'SV_{name}_M{level}' for name in ['DENSITY', 'ENERGY', 'K', 'O', 'P', 'T', 'U', 'V'] for level in [1, 2]]
    assert all((name in keys for name in required)), 'Missing second-order time-history arrays'
    return dict(utc=now(), state='CHECKPOINT_RESTART_VERIFIED_BEFORE_ADVANCE', case=str(case), data=str(data), native_time_s=time_s, native_step=step, geometry=geometry, reports=rows, field_extrema=fields, physical_setup_and_methods_unchanged=True, AMR_active=False, second_order_history_arrays_present=required, initialization_executed=False, time_reset=False)
