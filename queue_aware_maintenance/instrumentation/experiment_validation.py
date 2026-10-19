"""Fail-closed provenance checks. No generation, training, or table writes."""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def load_json(path):
    path = Path(path).resolve()
    require(path.is_file(), f'Missing JSON document: {path}')
    with path.open() as stream:
        value = json.load(stream)
    require(isinstance(value, dict), f'Expected a JSON object: {path}')
    return value, path.parent


def verified_file(spec, base):
    require(isinstance(spec, dict) and {'path', 'sha256'} <= spec.keys(), 'Artifacts require path and sha256.')
    require(isinstance(spec['path'], str) and isinstance(spec['sha256'], str)
            and re.fullmatch(r'[0-9a-f]{64}', spec['sha256']), 'Invalid artifact path/SHA256.')
    path = (Path(base) / spec['path']).resolve()
    require(path.is_file(), f'Missing artifact: {path}')
    require(sha256(path) == spec['sha256'], f'Artifact checksum mismatch: {path}')
    return path


def finite_number(value, name, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f'{name} must be a finite number.')
    require(not positive or value > 0, f'{name} must be positive.')
    return value


def trace_manifest(path):
    manifest, base = load_json(path)
    require(manifest.get('schema_version') == 'verified_trace_v1', 'Unsupported trace manifest schema.')
    require(manifest.get('origin') == 'observed', 'Only observed source traces are allowed.')
    require(isinstance(manifest.get('source_url'), str) and manifest['source_url'].startswith('https://'),
            'Trace requires its HTTPS source URL.')
    for name in ('transformation_description', 'normalization_rationale', 'regime_rationale'):
        require(isinstance(manifest.get(name), str) and manifest[name].strip(), f'Document {name}.')
    source = verified_file(manifest.get('source'), base)
    derived = verified_file(manifest.get('derived'), base)
    transform = verified_file(manifest.get('transformation_code'), base)
    require(manifest.get('time_mapping') == 'original_elapsed_seconds', 'Preserve original observed timing.')
    lo = finite_number(manifest.get('normalization_min'), 'normalization_min')
    hi = finite_number(manifest.get('normalization_max'), 'normalization_max')
    require(hi > lo, 'Normalization requires a nonzero declared range.')
    bins = manifest.get('regime_boundaries')
    require(isinstance(bins, list) and len(bins) == 3
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in bins)
            and 0 < bins[0] < bins[1] < bins[2] < 1, 'Declare ordered regime boundaries in (0,1).')
    return manifest, derived, {'source': str(source), 'transformation_code': str(transform)}


def validate_model_bundle(directory):
    directory = Path(directory).resolve()
    metadata, _ = load_json(directory / 'model_metadata.json')
    require(metadata.get('schema_version') == 'validated_cost_models_v1'
            and metadata.get('validation_status') == 'accepted', 'Model bundle has no accepted validation record.')
    require(isinstance(metadata.get('features'), list) and metadata['features'], 'Missing feature contract.')
    for name in ('model_a', 'model_b'):
        info = metadata[name]
        require(finite_number(info['q_hat'], f'{name}.q_hat') >= 0, 'Negative conformal offset.')
        require(info.get('acceptance_passed') is True, f'{name} failed acceptance.')
        verified_file(info['artifact'], directory)
    for key in ('training_data', 'compaction_events', 'training_protocol'):
        verified_file(metadata[key], directory)
    evidence = metadata.get('execution_evidence')
    require(isinstance(evidence, list) and evidence, 'Model bundle has no physical execution evidence.')
    for item in evidence:
        verified_file(item, directory)
    return metadata


def experiment_manifest(path, check_live=False, model_dir=None):
    manifest, base = load_json(path)
    require(manifest.get('schema_version') == 'physical_experiment_v1', 'Unsupported experiment manifest.')
    for name in ('experiment_id', 'purpose', 'configuration_rationale'):
        require(isinstance(manifest.get(name), str) and manifest[name].strip(), f'Declare {name}.')
    repo = Path(__file__).resolve().parents[2]
    require(manifest.get('code_revision') == subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(), 'Experiment code revision mismatch.')
    dirty = subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--',
                            'scripts/phase6-live-evaluation/*.py'], cwd=repo, capture_output=True)
    require(dirty.returncode == 0, 'Tracked experiment Python sources differ from recorded HEAD.')
    artifacts = manifest.get('benchmark_sources')
    require(isinstance(artifacts, list) and artifacts, 'Verified benchmark sources are required.')
    for artifact in artifacts:
        verified_file(artifact, base)
    verified_file(manifest.get('generator_provenance'), base)
    trace_path = verified_file(manifest.get('trace_manifest'), base)
    from google_trace_mapper import GoogleTraceMapper
    duration = finite_number(manifest.get('duration_seconds'), 'duration_seconds', positive=True)
    start = finite_number(manifest.get('trace_start_offset_seconds'), 'trace_start_offset_seconds')
    require(start >= 0, 'Negative trace start offset.')
    mapper = GoogleTraceMapper(trace_manifest_path=trace_path, test_duration_hours=duration / 3600,
                               start_offset_seconds=start)
    engine, table = manifest.get('engine', {}), manifest.get('table', {})
    for name in ('host', 'username', 'expected_version'):
        require(isinstance(engine.get(name), str) and engine[name], f'Engine {name} is required.')
    require(re.fullmatch(r'\d+\.\d+\.\d+', engine['expected_version']), 'Declare an exact engine release version.')
    require(isinstance(engine.get('port'), int) and not isinstance(engine['port'], bool)
            and 0 < engine['port'] < 65536, 'Invalid engine port.')
    identifier = table.get('identifier', '')
    require(isinstance(identifier, str) and re.fullmatch(r'[A-Za-z_]\w*\.[A-Za-z_]\w*\.[A-Za-z_]\w*', identifier),
            'Use an explicit catalog.namespace.table identifier.')
    for key in ('snapshot_id', 'record_count', 'file_count'):
        require(isinstance(table.get(key), int) and not isinstance(table[key], bool) and table[key] > 0,
                f'Table {key} must be a positive integer.')
    if model_dir is not None:
        validate_model_bundle(model_dir)
    observation = {'experiment_id': manifest['experiment_id'], 'table': identifier,
                   'trace_bins': mapper.total_bins, 'live_checked': False}
    if check_live:
        from pyhive import hive
        conn = hive.Connection(host=engine['host'], port=engine['port'], username=engine['username'])
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(f'SELECT snapshot_id FROM {identifier}.history ORDER BY made_current_at DESC LIMIT 1')
                rows = cursor.fetchall()
                require(bool(rows) and rows[0][0] == table['snapshot_id'], 'Current table snapshot mismatch.')
                cursor.execute(f'SELECT sum(record_count), count(*) FROM {identifier}.files')
                rows = cursor.fetchall()
                require(bool(rows) and tuple(rows[0]) == (table['record_count'], table['file_count']),
                        'Physical table metadata/cardinality mismatch.')
                cursor.execute('SELECT version()')
                observation['engine_version'] = str(cursor.fetchall()[0][0])
                require(engine['expected_version'] == observation['engine_version'].split()[0], 'Unexpected engine version.')
                observation['live_checked'] = True
            finally:
                cursor.close()
        finally:
            conn.close()
    return manifest, mapper, observation
