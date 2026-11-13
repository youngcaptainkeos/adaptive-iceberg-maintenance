"""Small, strict helpers shared by the research programme tools."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name}: explicit integer >= {minimum} required")
    return value


def number(value, name, minimum=None):
    require(type(value) in (int, float) and math.isfinite(value), f"{name}: finite number required")
    require(minimum is None or value >= minimum, f"{name}: below registered minimum")
    return value


def utc(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(t.tzinfo is not None and t.utcoffset() is not None, 'Explicit timezone required')
    return t.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, 'Duplicate JSON key: ' + key)
        out[key] = value
    return out


def decode(text):
    def invalid(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid)


def read(path):
    return decode(Path(path).read_text())


def write_new(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def checked(root, spec):
    path = (Path(root) / spec['path']).resolve()
    require(path.is_relative_to(Path(root).resolve()), 'Evidence path escapes repository')
    require(sha(path) == spec['sha256'], 'Evidence SHA256 differs: ' + str(path))
    return path
