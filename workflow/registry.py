"""A compact operational run register; scientific results remain immutable."""
from common import *

REG = ROOT / 'runs/run_register.csv'
FIELD_NAMES = {'processi': 'mpi_processes', 'iterazioni_per_passo': 'inner_iterations_per_step',
    'celle_attive': 'active_cells', 'evidenza': 'evidence', 'prossima_attivita': 'next_activity',
    'passi_completati': 'completed_steps', 'tempo_finale_s': 'physical_time_s', 'mesh': 'mesh'}


def update_test(run_id, status, **values):
    rows = []
    if REG.exists():
        with REG.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
    item = next((row for row in rows if row['run_id'] == run_id), None)
    if item is None:
        item = {'run_id': run_id}
        rows.append(item)
    item.update(status=status, updated_utc=now(), **{FIELD_NAMES.get(key, key): value for key, value in values.items()})
    fields = list(dict.fromkeys(key for row in rows for key in row))
    for row in rows:
        for key in fields:
            row.setdefault(key, '')
    csvwrite(REG, rows)
