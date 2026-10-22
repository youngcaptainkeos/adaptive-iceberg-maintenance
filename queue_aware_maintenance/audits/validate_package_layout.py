#!/usr/bin/env python3
"""Validate imports, real entry points and recorded trace bindings after relocation."""
import argparse
import ast
import importlib
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
from queue_aware_maintenance.core.common import now, sha, write_json, require


def run(output, protocol):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': now(), 'code_sha256': sha(__file__),
              'new_SQL_operations': 0, 'imported': [], 'entrypoints': []}
    try:
        manifest = json.loads((PACKAGE_ROOT/'layout_manifest.json').read_text())
        for source in PACKAGE_ROOT.rglob('*.py'):
            ast.parse(source.read_text())
        for old, relative in manifest['source_moves'].items():
            require(source_file(old) == PACKAGE_ROOT/relative, 'Wrong relocated source lookup')
            name = 'queue_aware_maintenance.'+relative[:-3].replace('/', '.')
            importlib.import_module(name)
            report['imported'].append(name)
            text = (PACKAGE_ROOT/relative).read_text()
            if "__name__" in text and "__main__" in text:
                for command in ([sys.executable, '-B', str(PACKAGE_ROOT/relative), '--help'],
                                [sys.executable, '-B', '-m', name, '--help']):
                    result = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, text=True)
                    require(result.returncode == 0, 'Entry point failed '+str(command)+': '+result.stderr)
                report['entrypoints'].append(relative)
        # This executes a real recorded-evidence audit, never a fabricated physical scenario.
        from queue_aware_maintenance.audits.audit_trace_dataset_binding import audit
        audit(protocol, out/'trace_binding')
        report['recorded_trace_audit_sha256'] = sha(out/'trace_binding/result.json')
        report['status'] = 'passed_grouped_imports_entrypoints_and_real_trace_binding'
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc))
        raise
    finally:
        report['ended_utc'] = now()
        write_json(out/'result.json', report)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--protocol', required=True)
    args = parser.parse_args()
    run(args.output, args.protocol)
