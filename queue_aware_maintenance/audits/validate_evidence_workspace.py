#!/usr/bin/env python3
"""Round-trip actual terminal diagnostic artifacts through working/archive storage."""
import argparse
import json
from pathlib import Path
import shutil
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.core.common import checked, require, now, sha, write_json
from queue_aware_maintenance.observability.evidence_workspace import inventory, prepare_workspace, publish_terminal_copy


def run(protocol):
    cfg = json.loads(Path(protocol).read_text())
    out = Path(cfg['output_directory'])
    out.mkdir(parents=True,exist_ok=False)
    report = {'status':'running','started_utc':now(),'protocol_sha256':sha(protocol),
              'new_SQL_operations':0,'physical_collector_migrated':False}
    try:
        require(cfg['schema_version'] == 'real_artifact_evidence_workspace_v1', 'Unknown workspace protocol')
        for name,spec in cfg['sources'].items(): checked(spec)
        result = checked(cfg['terminal_source_result'])
        require(json.loads(result.read_text())['status'] == 'passed_real_byte_durable_storage_comparison', 'Actual completed storage diagnostic required')
        original = result.parent
        before = inventory(original)
        size = sum(v['bytes'] for v in before.values())
        workspace = prepare_workspace(cfg['workspace'],device_reference=cfg['device_reference'],required_bytes=size*2)
        local = Path(workspace['directory'])/'terminal_diagnostic_copy'
        shutil.copytree(original,local)
        require(inventory(local) == before, 'Working copy differs from actual evidence')
        publication = publish_terminal_copy(local, out/'published_terminal_diagnostic',
            result_sha256=cfg['terminal_source_result']['sha256'],expected_terminal_status='passed_real_byte_durable_storage_comparison')
        require(inventory(original) == before, 'Original evidence changed')
        report.update(status='passed_real_artifact_workspace_and_archive_roundtrip',workspace=workspace,
            publication=publication, original_source_retained=True,
            limitations=['Real completed storage-probe evidence copied, not new query observations or training labels.',
                         'Validates storage paths/content/fsync publication; no live SQL, freshness or queue performance proof.',
                         'No active collector is moved. Future run must bind producer termination/identity, byte budget, retention and unique paths before use.',
                         'Device power loss/host failure recovery was not injected; source and partial copies are retained.'])
    except Exception as exc:
        report.update(status='failed_preserved',error=str(exc));raise
    finally:
        report['ended_utc']=now();write_json(out/'result.json',report);print(json.dumps(report),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol',required=True)
    run(parser.parse_args().protocol)
