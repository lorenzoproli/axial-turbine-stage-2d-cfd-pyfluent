"""English workflow records with read compatibility for historical metadata."""
from pathlib import Path
import csv as _csv
import json as _json

_ALIAS_PATH = Path(__file__).resolve().parents[1] / "config/legacy_schema.json"
_ALIASES = _json.loads(_ALIAS_PATH.read_text(encoding="utf-8"))["aliases"]


def normalise(value):
    """Map legacy record fields without changing the files that contain them."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            translated = _ALIASES.get(key, key) if isinstance(key, str) else key
            item = normalise(item)
            if translated in result and result[translated] != item:
                raise ValueError("Conflicting metadata aliases for " + str(translated))
            result[translated] = item
        return result
    if isinstance(value, (list, tuple)):
        return [normalise(item) for item in value]
    if isinstance(value, str):
        return _ALIASES.get(value, value)
    return value


class _JSON:
    raw_loads = staticmethod(_json.loads)

    def loads(self, value, *args, **kwargs):
        return normalise(_json.loads(value, *args, **kwargs))

    def load(self, stream, *args, **kwargs):
        return normalise(_json.load(stream, *args, **kwargs))

    def dumps(self, value, *args, **kwargs):
        return _json.dumps(normalise(value), *args, **kwargs)

    def dump(self, value, stream, *args, **kwargs):
        return _json.dump(normalise(value), stream, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(_json, name)


class _DictReader:
    def __init__(self, *args, **kwargs):
        self._reader = _csv.DictReader(*args, **kwargs)

    def __iter__(self):
        return self

    def __next__(self):
        return normalise(next(self._reader))

    @property
    def fieldnames(self):
        return normalise(self._reader.fieldnames)

    def __getattr__(self, name):
        return getattr(self._reader, name)


class _CSV:
    DictReader = _DictReader

    def __getattr__(self, name):
        return getattr(_csv, name)


json = _JSON()
csv = _CSV()
