"""Identify unique native monitors from their headers after filename changes."""
from common import project_path

def monitor_path(directory, name):
    directory = project_path(directory)
    candidates = list(directory.glob('*.out'))
    matches = []
    for path in candidates:
        with path.open(encoding='utf-8', errors='replace') as stream:
            header = [next(stream, '').strip() for _ in range(3)]
        if header[0] == '"' + name + '-rfile"' and '"flow-time"' in header[2]:
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f'{directory}: expected one native monitor {name}; found {matches}')
    return matches[0]
