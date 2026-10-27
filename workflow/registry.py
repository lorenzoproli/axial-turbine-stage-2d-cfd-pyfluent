"""A compact operational run register; scientific results remain immutable."""
from data_schema import csv, json
from common import *

REG = ROOT / 'runs/run_register.csv'
FIELD_NAMES = {'mpi_processes': 'mpi_processes', 'inner_iterations_per_step': 'inner_iterations_per_step',
    'active_cells': 'active_cells', 'evidence': 'evidence', 'next_activity': 'next_activity',
    'completed_steps': 'completed_steps', 'final_time_s': 'physical_time_s', 'mesh': 'mesh'}


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
