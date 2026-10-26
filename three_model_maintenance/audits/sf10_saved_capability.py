"""Typed, exact audit of immutable SF10 evidence; no SQL or physical rerun.

EventLog uses JSON default=str for Decimal. Projection types must come from an
explicit SQL-bound registration, never guessed from reference values or strings.
The historical v1 auditor and its failed terminal receipt remain unchanged.
"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
import traceback
from decimal import Decimal
from pathlib import Path

from three_model_maintenance.contracts import require
from three_model_maintenance.experiments.scale_query import canonical
from three_model_maintenance.preparation.query_plan import parse
from three_model_maintenance.training.data import read, save, sha

REPO = Path(__file__).resolve().parents[2]


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def decode_rows(rows, types):
    decoded = []
    for row in rows:
        require(len(row) == len(types), 'Registered result width differs')
        values = []
        for value, kind in zip(row, types):
            if kind == 'integer':
                require(type(value) is int, 'JSON integer required; no string/float coercion')
            elif kind == 'decimal':
                require(type(value) is str and re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]+)?', value),
                        'Exact logged decimal string required; no float, null or guessed value')
                value = Decimal(value)
                require(value.is_finite() and len(value.as_tuple().digits) <= 28, 'Unsupported decimal precision')
            elif kind == 'text':
                require(type(value) is str, 'Literal text required')
            else:
                raise ValueError('Unregistered result type ' + str(kind))
            values.append(value)
        decoded.append(values)
    return decoded


def events(path):
    rows = [json.loads(line) for line in path.open()]
    require(not any(r['kind'] in ('statement_failed', 'statement_not_submitted') for r in rows), 'Failed/unsubmitted SQL in accepted stage')
    result = {}
    for kind in ('statement_requested', 'statement_completed'):
        selected = [r for r in rows if r['kind'] == kind]
        index = {r['measurement_id']: r for r in selected}
        require(len(index) == len(selected), 'Duplicate statement identity')
        result[kind] = index
    require(set(result['statement_requested']) == set(result['statement_completed']), 'Missing requested/completed SQL')
    return result['statement_requested'], result['statement_completed']


def run(protocol):
    cfg = read(protocol)
    require(cfg['schema_version'] == 'sf10_saved_typed_audit_v2', 'Unknown typed audit contract')
    require(subprocess.check_output(['git', 'show', 'HEAD:' + str(protocol.relative_to(REPO))], cwd=REPO) == protocol.read_bytes(), 'Uncommitted audit registration')
    for spec in cfg['sources']:
        p = REPO / spec['path']; require(sha(p) == spec['sha256'], 'Changed audit source')
        if p.suffix == '.py': ast.parse(p.read_text(), filename=str(p))
    root = Path(cfg['input_directory']); out = Path(cfg['output_directory'])
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'registration.json', cfg)
    try:
        require(inventory(root) == cfg['input_files'], 'Immutable source package changed')
        execution = read(root / 'execution_registration.json')
        parent = read(root / 'result.json')
        require(parent['status'] == 'failed_or_blocked_preserved_no_retry' and parent['error'] == 'Failed audit; no automatic retry', 'Historical failure identity differs')
        stage_map = {r['stage']: r for r in parent['stages']}
        for stage in ('prepare', 'plan_query'):
            require(stage_map[stage]['returncode'] == 0 and sha(root / stage / 'result.json') == stage_map[stage]['result_sha256'], 'Physical producer stage did not pass')
        require(stage_map['audit']['returncode'] == 1 and read(root / 'audit/failure.json')['error'] == 'Actual query result/timing differs', 'Different audit failure')
        prepared = read(root / 'prepare/result.json')
        require(prepared['status'] == 'verified_sf10_eight_table_ingestion_only' and sha(root / 'prepare/events.jsonl') == prepared['events_sha256'], 'Preparation binding differs')
        pre_requests, pre_calls = events(root / 'prepare/events.jsonl')
        def exact_call(requests, calls, sql):
            ids = [mid for mid, r in requests.items() if r['sql'] == sql]
            require(len(ids) == 1, 'Expected unique actual SQL: ' + sql)
            return calls[ids[0]]
        tables = {r['table']: r for r in prepared['tables']}
        require(set(tables) == set(execution['table_order']), 'Missing source table')
        source = read(root / 'source_reference/result.json')
        require(source['status'] == 'verified_typed_relational_source_and_reference_queries' and
                sha(root / 'source_reference/query_references.json') == source['reference_sha256'], 'Independent references changed')
        source_rows = {r['table']: r['rows'] for r in source['tables']}
        for name, table in tables.items():
            require(table['rows'] == source_rows[name], 'Source/table count differs')
            sql = 'SELECT count(*) FROM ' + table['iceberg_table']
            require(exact_call(pre_requests, pre_calls, sql)['rows'] == [[table['rows']]], 'Raw loaded count differs')
            cols = ', '.join(f['name'] for f in execution['schemas'][name]); view = 'sf10_source_' + name
            diff = 'SELECT count(*) FROM ((SELECT ' + cols + ' FROM ' + table['iceberg_table'] + ' EXCEPT ALL SELECT ' + cols + ' FROM ' + view + ') UNION ALL (SELECT ' + cols + ' FROM ' + view + ' EXCEPT ALL SELECT ' + cols + ' FROM ' + table['iceberg_table'] + ')) d'
            require(exact_call(pre_requests, pre_calls, diff)['rows'] == [[0]], 'Raw full-row multiset gate differs')
        requested, completed = events(root / 'plan_query/events.jsonl')
        refs = {r['query_id']: r for r in read(root / 'source_reference/query_references.json')}
        registered = {q['query_id']: q for q in cfg['queries']}
        require(cfg['queries'] and len(registered) == len(cfg['queries']) and
                [{k:q[k] for k in ('query_id', 'sql')} for q in cfg['queries']] ==
                [{k:q[k] for k in ('query_id', 'sql')} for q in execution['queries']], 'Typed projection/actual SQL registration differs')
        observed = read(root / 'plan_query/observations.json'); checked = []
        maintenance = read(root / 'plan_query/maintenance.json')
        require(len({r['measurement_id'] for r in observed}) == len(observed) and
                {(r['phase'], r['query_id']) for r in observed} == {(p, q) for p in ('fragmented', 'compacted') for q in registered} and
                len(observed) == 2 * len(registered), 'Missing/duplicate query-phase observations')
        require({mid for mid, r in requested.items() if r['role'] == 'sf10_capability_query'} == {r['measurement_id'] for r in observed}, 'Unaccounted physical queries')
        for record in observed:
            folder = root / 'plan_query'; receipt = read(folder / record['receipt'])
            require(sha(folder / record['receipt']) == record['receipt_sha256'], 'Changed plan receipt')
            prefix = record['phase'] + '_' + str(record['query_id'])
            snapshots = {n: t['snapshot_id'] for n, t in tables.items()}
            if record['phase'] == 'compacted': snapshots['lineitem'] = maintenance['after_snapshot']
            require(receipt['snapshots'] == snapshots, 'Plan snapshot/state binding differs')
            extracted = parse((folder / (prefix + '_FORMATTED.txt')).read_text(), (folder / (prefix + '_COST.txt')).read_text())
            require(extracted == receipt['plan'] and extracted['features'] == record['features'], 'Plan reconstruction differs')
            for mode, mid in receipt['plan_call_ids'].items():
                require(requested[mid]['sql'] == 'EXPLAIN ' + mode + ' ' + receipt['sql'] and
                        '\n'.join(str(r[0]) for r in completed[mid]['rows']) == (folder / (prefix + '_' + mode + '.txt')).read_text() and
                        completed[mid]['fetch_end']['monotonic_ns'] <= record['plan_available_observed_at']['monotonic_ns'], 'Raw plan/persistence binding differs')
            qid = record['query_id']; call = completed[record['measurement_id']]
            values = decode_rows(call['rows'], registered[qid]['result_types'])
            require(canonical(values) == refs[qid]['canonical_rows'], 'Exact typed result differs from independent reference')
            require(record['service_ms'] == (call['fetch_end']['monotonic_ns'] - call['client_execute_start']['monotonic_ns']) / 1e6 and
                    record['client_execute_start'] == call['client_execute_start'] and record['fetch_end'] == call['fetch_end'], 'Exact timing reconstruction differs')
            expected_sql = registered[qid]['sql'].format(**{n: t['iceberg_table'] + ' VERSION AS OF ' + str(receipt['snapshots'][n]) for n, t in tables.items()})
            require(requested[record['measurement_id']]['sql'] == receipt['sql'] == expected_sql and
                    hashlib.sha256(expected_sql.encode()).hexdigest() == receipt['sql_sha256'] and
                    record['plan_available_observed_at']['monotonic_ns'] <= call['client_execute_start']['monotonic_ns'], 'Feature/SQL availability binding differs')
            checked.append(dict(phase=record['phase'], query_id=qid, typed_result_equal=True, exact_timing_equal=True, features=extracted['features']))
        line = tables['lineitem']; table = line['iceberg_table']
        require(maintenance['before_snapshot'] == line['snapshot_id'] and maintenance['after_snapshot'] != line['snapshot_id'] and
                maintenance['before_files'] == line['file_count'] and 0 < maintenance['after_files'] < line['file_count'], 'Useful rewrite/layout transition missing')
        mid = maintenance['statement']['measurement_id']
        require(all(completed[mid][k] == v for k, v in maintenance['statement'].items()) and
                requested[mid]['role'] == 'sf10_maintenance', 'Actual rewrite statement differs')
        diff = 'SELECT count(*) FROM ((SELECT * FROM ' + table + ' VERSION AS OF ' + str(line['snapshot_id']) + ' EXCEPT ALL SELECT * FROM ' + table + ') UNION ALL (SELECT * FROM ' + table + ' EXCEPT ALL SELECT * FROM ' + table + ' VERSION AS OF ' + str(line['snapshot_id']) + ')) d'
        require(exact_call(requested, completed, diff)['rows'] == [[0]], 'Rewrite full-row multiset gate differs')
        require(any(r['features']['plan_join_count'] > 0 for r in checked) and any(r['features']['plan_sort_count'] > 0 for r in checked), 'Missing query structure variety')
        require(inventory(root) == cfg['input_files'], 'Source evidence changed during audit')
        save(out / 'result.json', dict(status='passed_saved_sf10_typed_capability_audit_only', observations=checked,
             tables_verified=len(tables), before_files=maintenance['before_files'], after_files=maintenance['after_files'],
             original_terminal_sha256=sha(root / 'result.json'), protocol_sha256=sha(protocol),
             original_failure_preserved=True, SQL_executed=False, physical_rerun=False,
             cost_training_accepted=False, matched_pending_state_corpus=False, sf100_ready=False,
             limitations=['Saved SF10 capability audit, not a trace replay, A/B training corpus, calibrated model or scheduler benefit.',
                          'Result projection types explicitly registered after serialization failure; no numeric tolerance or inferred string types.',
                          'Original source/reference and physical receipts retained; original parent remains failed, superseded only by this separate typed audit.']))
    except Exception as exc:
        save(out / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--protocol', type=Path, required=True)
    run(parser.parse_args().protocol.resolve())
