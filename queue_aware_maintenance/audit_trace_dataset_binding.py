#!/usr/bin/env python3
"""Read-only source-window, physical SQL and scheduled-clock reconstruction."""
import argparse, csv, json, re
from collections import Counter
from pathlib import Path
from common import checked, sha, require, utc, now, write_json
from run_correctness_pilot import query_templates


def audit(protocol, output):
    cfg = json.loads(Path(protocol).read_text())
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_utc': now(), 'code_sha256': sha(__file__),
              'protocol_sha256': sha(protocol), 'new_sql_operations': 0}
    try:
        template = cfg['episode_template']
        source_csv = checked(template['arrivals'])
        cohort_path = source_csv.parent / 'cohort_record.json'
        cohort = json.loads(cohort_path.read_text())
        require(cohort['status'] == 'extracted_arrival_cohort_only', 'Unaccepted extraction')
        require(cohort['observed_arrivals_sha256'] == sha(source_csv), 'Extraction CSV changed')
        validation = source_csv.parent / 'source_validation_record.json'
        require(sha(validation) == cohort['source_validation_sha256'], 'Upstream receipt changed')
        require(sha(source_csv.parent / 'cohort_code.py') == cohort['tool_sha256'], 'Extraction producer changed')
        start, end = utc(template['source_start_utc']), utc(template['source_end_utc'])
        require((end-start).total_seconds() == template['horizon_seconds'], 'Wrong source horizon')
        expected, total, previous, identities = [], 0, None, set()
        with source_csv.open() as stream:
            for r in csv.DictReader(stream):
                timestamp = utc(r['arrival_utc'])
                order = (timestamp, int(r['queryId']))
                require(previous is None or previous <= order, 'Unsorted source export')
                previous = order
                require(r['queryId'] not in identities, 'Duplicate exported source ID')
                identities.add(r['queryId'])
                require(int(r['warehouseId']) == cohort['selected_warehouse_id'], 'Mixed warehouse')
                total += 1
                if start <= timestamp < end:
                    delta = timestamp-start
                    offset = (delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000
                    expected.append(dict(source_query_id=r['queryId'], warehouse_id=r['warehouseId'],
                                         source_arrival_utc=r['arrival_utc'], offset_ns=str(offset),
                                         query_id=str(template['query_ids'][len(expected)%len(template['query_ids'])])))
        require(total == cohort['selected_total_arrivals'], 'Incomplete source export')
        mapping = checked(template['mapping'])
        with mapping.open() as stream:
            mapped = list(csv.DictReader(stream))
        require(mapped == expected and len(mapped) == template['arrival_count'], 'Source IDs/order/timestamps/template mapping differ')
        source = json.loads(checked(template['preparation_result']).read_text())
        require(source['status'] == 'accepted_correctness_source', 'Unaccepted physical dataset')
        root = Path(cfg['output_directory'])
        progress = json.loads((root/'progress.json').read_text())
        require(progress['passed'] == 8 and progress['failed'] == progress['unattempted'] == 0, 'Incomplete physical scope')
        rows = []
        for attempt in progress['attempts']:
            episode = root/'episodes'/attempt['experiment_id']
            ecfg = json.loads((episode/'config.json').read_text())
            require(sha(episode/'mapped_arrivals.csv') == sha(mapping), 'Episode mapping changed')
            require(sha(episode/'preparation_result.json') == template['preparation_result']['sha256'], 'Episode dataset receipt changed')
            result = json.loads((episode/'result.json').read_text())
            require(sha(episode/'result.json') == attempt['result_sha256'], 'Saved result changed')
            require(result['completed'] == len(mapped) and result['failed'] == result['unfinished'] == 0, 'Incomplete requests')
            clock = None
            offered, dispatched, completed, sqls, observations, differences = {}, [], [], {}, {}, []
            for line in (episode/'events.jsonl').open():
                r = json.loads(line)
                kind = r['kind']
                if kind == 'cohort_clock':
                    clock = r['start_monotonic_ns']
                    require(r['arrival_end_monotonic_ns']-clock == int(template['horizon_seconds']*1e9), 'Retimed horizon')
                elif kind == 'cohort_queue_transition':
                    require(clock is not None, 'Missing start clock')
                    identity = r['source']['source_query_id']
                    if r['state'] == 'offered':
                        require(identity not in offered, 'Duplicate offered identity')
                        require(r['scheduled_monotonic_ns'] == clock+int(r['source']['offset_ns']), 'Retimed physical arrival')
                        offered[identity] = r
                    elif r['state'] == 'dispatched': dispatched.append(identity)
                    elif r['state'] == 'completed': completed.append(identity)
                elif kind == 'query_observation': observations[r['measurement_id']] = r
                elif kind == 'statement_requested':
                    if r['role'] == 'trace_query':
                        require(r['measurement_id'] not in sqls, 'Repeated SQL intent')
                        sqls[r['measurement_id']] = r
                    if 'EXCEPT ALL' in r['sql']: differences.append(r['measurement_id'])
            require([r['source'] for r in offered.values()] == mapped, 'Physical offered sequence differs')
            require(dispatched == completed == [r['source_query_id'] for r in mapped], 'FIFO drain differs')
            lateness = []
            for row in mapped:
                offer = offered[row['source_query_id']]
                mid = offer['measurement_id']
                observation, statement = observations[mid], sqls[mid]
                qid = int(row['query_id'])
                expected_sql = query_templates(ecfg['destination_table'])[qid].replace(
                    'FROM '+ecfg['destination_table'], 'FROM '+ecfg['destination_table']+' VERSION AS OF '+str(observation['snapshot_id']))
                require(statement['query_id'] == qid and statement['sql'] == expected_sql, 'Wrong physical SQL/template/snapshot')
                late = offer['actual_transition']['monotonic_ns']-offer['scheduled_monotonic_ns']
                require(late >= 0, 'Offered before schedule')
                lateness.append(late)
            require(len(sqls) == len(mapped) and len(differences) == 2, 'SQL population/multiset validation scope differs')
            require(result['initial_file_state']['record_count'] == source['record_count'], 'Physical row count differs')
            lateness.sort()
            rows.append({'experiment_id': attempt['experiment_id'], 'requests_verified': len(mapped),
                         'events_sha256': sha(episode/'events.jsonl'),
                         'generator_lateness_ms': {'median': lateness[len(lateness)//2]/1e6,
                                                   'p99': lateness[min(len(lateness)-1, int(len(lateness)*.99))]/1e6,
                                                   'maximum': max(lateness)/1e6}})
        report.update(status='passed_export_to_mapping_to_actual_SQL_and_clocks',
                      source_export_rows=total, selected_arrivals=len(mapped), selected_warehouse=cohort['selected_warehouse_id'],
                      source_interval=[start.isoformat(), end.isoformat()], template_counts=dict(Counter(r['query_id'] for r in mapped)),
                      mapping_sha256=sha(mapping), source_csv_sha256=sha(source_csv),
                      upstream_validation_receipt_sha256=sha(validation), physical_dataset_receipt=source,
                      episodes=rows, limitations=[
                          'Fresh audit starts at the hash-bound exported trace CSV; raw Parquet/archive validation is historical, not rerun here.',
                          'TPC-H data are generated benchmark data; four custom lineitem templates are not the complete official TPC-H query suite.',
                          'Round-robin SQL assignment preserves arrival timing/identity, not original trace SQL, costs or template correlations.',
                          'Physical data/result correctness relies on completed full raw audits and symmetric EXCEPT ALL; no fresh SQL or generator rebuild.',
                          'Arrival targets are exact offsets; actual thread release has measured lateness. Serial client and instrumentation affect performance.',
                          'No production representativeness, causal scheduling benefit or novelty established.'])
    except Exception as exc:
        report.update(status='failed_preserved', error=str(exc))
        raise
    finally:
        report['ended_utc'] = now()
        write_json(out/'result.json', report)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    audit(args.protocol, args.output)
