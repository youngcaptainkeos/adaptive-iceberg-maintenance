#!/usr/bin/env python3
"""Verify preserved real worker3 source bytes; never run archived code."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(archive):
    manifest = json.loads((archive / 'manifest.json').read_text())
    failures = []
    for name, expected in manifest['files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            failures.append({'path': name, 'error': 'unsafe relative path'})
            continue
        path = archive / 'remote_sources' / name
        if not path.is_file() or path.is_symlink():
            failures.append({'path': name, 'error': 'missing regular file'})
            continue
        contents = path.read_bytes()
        if len(contents) != expected['bytes'] or hashlib.sha256(contents).hexdigest() != expected['sha256']:
            failures.append({'path': name, 'error': 'size or hash mismatch'})
    expected_names = set(manifest['files'])
    actual_names = {str(p.relative_to(archive / 'remote_sources'))
                    for p in (archive / 'remote_sources').rglob('*') if p.is_file()}
    for name in sorted(actual_names - expected_names):
        failures.append({'path': name, 'error': 'unlisted archived file'})
    for name in manifest['comparison']['different']:
        path = archive / 'local_conflicts' / name
        expected = manifest.get('local_conflict_sha256', {}).get(name)
        if expected is None or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append({'path': name, 'error': 'local conflict preservation mismatch'})
    return {'archive': str(archive), 'source_files_checked': len(expected_names),
            'local_conflicts_checked': len(manifest['comparison']['different']),
            'status': 'FAIL' if failures else 'PASS', 'failures': failures,
            'scope': 'Byte integrity only. Historical code/data validity is not certified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    args = parser.parse_args()
    report = verify(args.archive.resolve())
    print(json.dumps(report, indent=2))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
