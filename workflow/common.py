"""Portable project paths, stable input reads and atomic workflow records.

Native Fluent zone/report identifiers and the numerical metadata schema are
preserved. Importing this module does not create files or start applications.
"""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager, ExitStack
import csv, hashlib, json, os, re, shutil, time, uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / 'config'
T = 2.97583785e-4
PITCH = 0.04463756775
VY = -150.0
_ALIASES_CACHE = None
_ALIASES_SIGNATURE = None
_COMPONENT_ALIASES = {}
_COMPONENT_TOKENS = {}
_FILENAME_ALIASES = {}
_REVERSE_ALIASES = {}


def _normalise(value):
    return str(value).replace('\\', '/').strip().rstrip('/')


def _path_aliases():
    global _ALIASES_CACHE, _ALIASES_SIGNATURE, _COMPONENT_ALIASES, _COMPONENT_TOKENS, _FILENAME_ALIASES, _REVERSE_ALIASES
    sources = [CONFIG_DIR / 'path_aliases.json', ROOT / 'path_map.json']
    signature = tuple((str(path), path.stat().st_mtime_ns if path.exists() else None) for path in sources)
    if signature == _ALIASES_SIGNATURE:
        return _ALIASES_CACHE
    result = {}
    for source in sources:
        if not source.is_file():
            continue
        value = json.loads(source.read_text(encoding='utf-8-sig'))
        if isinstance(value, dict):
            _COMPONENT_TOKENS.update(value.get('components', {}))
            _FILENAME_ALIASES.update(value.get('filenames', {}))
            value = value.get('mapping', value.get('paths', value))
        if isinstance(value, list):
            value = {item.get('old', item.get('source')): item.get('new', item.get('destination')) for item in value}
        if isinstance(value, dict):
            result.update({_normalise(old): _normalise(new) for old, new in value.items()
                           if isinstance(old, str) and isinstance(new, str)})
    candidates = {}
    for old, new in result.items():
        candidates.setdefault(old.rsplit('/', 1)[-1], set()).add(new.rsplit('/', 1)[-1])
    _COMPONENT_ALIASES = {old: next(iter(values)) for old, values in candidates.items() if len(values) == 1}
    _REVERSE_ALIASES = {}
    for old, new in result.items():
        _REVERSE_ALIASES.setdefault(new, []).append(old)
    _ALIASES_CACHE, _ALIASES_SIGNATURE = result, signature
    return result


def english_name(value):
    """Translate a filename/component without changing native Fluent IDs."""
    value = str(value)
    _path_aliases()
    if value in _FILENAME_ALIASES:
        return _FILENAME_ALIASES[value]
    if value in _COMPONENT_TOKENS:
        return _COMPONENT_TOKENS[value]
    if value in _COMPONENT_ALIASES:
        return _COMPONENT_ALIASES[value]
    return ''.join(_COMPONENT_TOKENS.get(part, part) for part in re.split(r'([^A-Za-z]+)', value))


def project_path(value):
    """Resolve current relative paths and mapped paths from previous checkouts.

    A saved absolute project path is recognised by a mapped technical suffix,
    independently of user name or drive letter. Unrelated absolute paths remain
    absolute; writes must additionally use output_path for containment checks.
    """
    raw = _normalise(value)
    root_string = _normalise(ROOT)
    if raw.lower() == root_string.lower():
        return ROOT
    if raw.lower().startswith(root_string.lower() + '/'):
        raw = raw[len(root_string) + 1:]
    aliases = _path_aliases()
    mapped = False
    for source in sorted(aliases, key=len, reverse=True):
        if raw == source or raw.startswith(source + '/'):
            suffix = raw[len(source):]
            raw = aliases[source] + '/'.join(english_name(part) for part in suffix.split('/'))
            mapped = True
            break
        marker = '/' + source
        start = raw.lower().find(marker.lower())
        if start >= 0 and (len(raw) == start + len(marker) or raw[start + len(marker)] == '/'):
            suffix = raw[start + len(marker):]
            raw = aliases[source] + '/'.join(english_name(part) for part in suffix.split('/'))
            mapped = True
            break
    if not mapped:
        # Already portable paths are not translated a second time. Only child
        # joins and unmapped historical components require filename aliases.
        if not any(raw == target or raw.startswith(target + '/') for target in aliases.values()):
            raw = '/'.join(english_name(part) for part in raw.split('/'))
    path = Path(raw)
    if path.is_absolute():
        return ProjectPath(path)
    if len(raw) > 2 and raw[1:3] == ':/':
        raise FileNotFoundError('Saved Windows project path has no current mapping: ' + raw)
    return ProjectPath(ROOT / path)


class ProjectPath(type(Path())):
    """A project path whose joined child names follow the technical path map."""
    def __truediv__(self, child):
        raw_child = _normalise(child)
        aliases = _path_aliases()
        try:
            current = self.relative_to(ROOT).as_posix()
        except ValueError:
            current = None
        # A branch can move to a different top-level directory (for example
        # the adapted-run checkpoint is an immutable input). Prefer an exact
        # mapped child to a simple translated child of the current directory.
        if current is not None and not Path(raw_child).is_absolute():
            prefix = current
            while prefix:
                for old_prefix in _REVERSE_ALIASES.get(prefix, []):
                    candidate = old_prefix + current[len(prefix):] + '/' + raw_child
                    match = candidate
                    while len(match) > len(old_prefix):
                        if match in aliases:
                            suffix = candidate[len(match):]
                            mapped = aliases[match] + '/'.join(english_name(part) for part in suffix.split('/'))
                            return project_path(ROOT / mapped)
                        match = match.rsplit('/', 1)[0]
                prefix = prefix.rsplit('/', 1)[0] if '/' in prefix else ''
        translated = '/'.join(english_name(part) for part in raw_child.split('/'))
        return project_path(super().__truediv__(translated))


def output_path(value):
    """Resolve an output and prevent traversal outside the checkout."""
    path = project_path(value).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Project output must remain inside the checkout: ' + str(path))
    return path


def original_path(relative):
    candidate = project_path('03_simulazioni/baseline/originali_20261013/' + str(relative))
    return candidate if candidate.exists() else project_path(relative)


ORIGINALS = project_path('03_simulazioni/baseline/originali_20261013')
WORK = project_path('03_simulazioni/riproduzione_mesh_adattata/sessione_20261013')
AUDIT = project_path('03_simulazioni/riproduzione_mesh_adattata/sessione_20261013/audit')
INPUT = ROOT / 'inputs' / 'historical_baseline_working_copy'
ANALYSIS = project_path('05_postprocessing/monitor_storici_20261013')
FIG = project_path('06_figure/monitor_storici_20261013')


def mesh_base_id(run_id):
    for suffix in ['_HYBRID35', '_HYBRID']:
        if run_id.endswith(suffix):
            return run_id[:-len(suffix)]
    return run_id


def case_directory(run_id):
    names = {'M1': 'M1_grossolana', 'M2': 'M2_media', 'M3': 'M3_fine'}
    base_id = mesh_base_id(run_id)
    if run_id.endswith('_HYBRID35') and base_id in names:
        return project_path('03_simulazioni/convergenza_griglia/' + names[base_id] + '/soluzione_hybrid35_20261014')
    if run_id.endswith('_HYBRID') and base_id in names:
        return project_path('03_simulazioni/convergenza_griglia/' + names[base_id] + '/soluzione_hybrid_20261014')
    if run_id in names:
        return project_path('03_simulazioni/convergenza_griglia/' + names[run_id] + '/soluzione_pyfluent_20261013')
    return project_path('03_simulazioni/riproduzione_mesh_adattata/sessione_20261013/campagna/' + run_id)


def now():
    return datetime.now(timezone.utc).isoformat()


def portable_record(value):
    """Store paths inside the checkout relative to its root."""
    if isinstance(value, dict):
        return {key: portable_record(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable_record(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str) and (Path(value).is_absolute() or re.match(r'^[A-Za-z]:[\\/]', value)):
        candidate = project_path(value)
        if candidate.is_relative_to(ROOT):
            return candidate.relative_to(ROOT).as_posix()
    return value


def jwrite(path, value, replace_timeout_s=10):
    path = output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}-{uuid.uuid4().hex}.tmp')
    temporary.write_text(json.dumps(portable_record(value), ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    deadline = time.monotonic() + replace_timeout_s
    attempts = 0
    while True:
        try:
            temporary.replace(path)
            return
        except PermissionError as error:
            if getattr(error, 'winerror', None) not in [None, 5, 32, 33] or time.monotonic() >= deadline:
                raise
            attempts += 1
            time.sleep(min(.05 * 2 ** min(attempts - 1, 4), .5, max(0, deadline - time.monotonic())))


def text(path, value):
    path = output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def csvwrite(path, rows):
    path = output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(portable_record(rows))


@contextmanager
def safe_read(path):
    """On Windows, deny writer sharing while an input or checkpoint is read."""
    path = project_path(path)
    if os.name != 'nt':
        with path.open('rb') as stream:
            yield stream
        return
    import ctypes, msvcrt
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, 'rb') as stream:
        yield stream


def digest(stream):
    stream.seek(0)
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
        value.update(block)
    return value.hexdigest()


def sha(path):
    with safe_read(path) as stream:
        return digest(stream)


def prepare_input():
    names = ['stadio_assiale_2D_CFD_final.cas.h5', 'stadio_assiale_2D_CFD_final.dat.h5']
    manifest = json.loads(project_path('03_simulazioni/baseline/baseline_SHA256.json').read_text(encoding='utf-8'))
    expected = {name: item['sha256'] for name, item in manifest.items()}
    INPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with ExitStack() as stack:
        opened = [stack.enter_context(safe_read(original_path(name))) for name in names]
        for name, stream in zip(names, opened):
            actual = digest(stream)
            if actual != expected[name]:
                raise RuntimeError('Historical baseline checksum changed: ' + name)
            destination = INPUT / original_path(name).name
            if not destination.exists():
                stream.seek(0)
                with destination.open('xb') as target:
                    shutil.copyfileobj(stream, target, 4 * 1024 * 1024)
            if sha(destination) != actual:
                raise RuntimeError('Working baseline copy checksum differs: ' + str(destination))
            rows.append(dict(source=str(original_path(name).relative_to(ROOT)), copy=str(destination.relative_to(ROOT)),
                             bytes=destination.stat().st_size, sha256=actual, status='VERIFIED'))
    jwrite(AUDIT / 'baseline_input_manifest.json', rows)
    return rows, {'status': 'ORIGINAL_TRANSCRIPT_PRESERVED_WITH_BASELINE'}


def append_status(message):
    """Append a technical event without rewriting project documentation."""
    path = ROOT / 'runs' / 'workflow_events.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(utc=now(), message=message), ensure_ascii=False) + '\n')
