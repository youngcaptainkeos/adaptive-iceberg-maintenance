"""Prospective task retention repair using only recorded, complete Spark REST data.

The terminal checkpoint precedes all final metadata/full-table validation SQL.
Incremental event ingestion and a stage-attempt cache avoid per-query event-log
rescans and repeated task-list downloads. Timings describe this observer only.
"""
import hashlib
import json
import math
import time

from engine_archive import ArchivedTaskEvidence, merged_engine_frames
from engine_overlap import task_intervals
from experiment_validation import require
from physical_measurements import stamp

CONTRACT = 'completed_calls_before_final_validation_v1'


def validate_contract(cfg):
    contract = cfg.get('terminal_engine_archive_contract')
    require(contract in (None, CONTRACT), 'Unknown terminal engine archive contract')
    if contract is not None:
        interval = cfg.get('engine_archive_interval_seconds')
        require(isinstance(interval, (int, float)) and not isinstance(interval, bool)
                and math.isfinite(interval) and interval >= 1,
                'Register positive finite engine archive interval seconds')
        require(not cfg.get('engine_archive_offsets_ns'),
                'Periodic terminal contract replaces legacy archive offsets')
    return contract is not None


def digest_frames(rows):
    """Hash exact recorded REST events, including endpoints and response clocks."""
    digest = IncrementalFrameDigest()
    for row in rows:
        digest.append(row)
    return digest.hexdigest()


class IncrementalFrameDigest:
    """Exact canonical JSON-array SHA, without reencoding historical frames.

    iterencode yields JSON tokens rather than one complete payload string.
    A copied hash adds the closing bracket, leaving the live prefix appendable.
    This changes acquisition work, not the v1 digest bytes or acceptance gates.
    Large REST decoding and other collector threads still share the Python GIL.
    """
    def __init__(self):
        self.digest = hashlib.sha256(b'[')
        self.count = 0
        self.encode_wall_ns = 0
        self.encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False)

    def append(self, row):
        started = time.perf_counter_ns()
        if self.count:
            self.digest.update(b',')
        for token in self.encoder.iterencode(row):
            self.digest.update(token.encode())
        self.count += 1
        self.encode_wall_ns += time.perf_counter_ns() - started

    def hexdigest(self):
        digest = self.digest.copy()
        digest.update(b']')
        return digest.hexdigest()


class _CachedTasks:
    def __init__(self, rest):
        self.rest = rest
        self.cache = {}

    def capture_tasks(self, stage, attempt, count):
        key = (stage, attempt)
        if key in self.cache:
            old_count, payload = self.cache[key]
            require(old_count == count, 'Completed stage task count changed')
            return payload
        payload = self.rest.capture_tasks(stage, attempt, count)
        require(len(payload) == count and len({t['taskId'] for t in payload}) == count
                and {t['index'] for t in payload} == set(range(count))
                and all(t.get('attempt') == 0 and t.get('status') == 'SUCCESS'
                        and t.get('duration', 0) > 0 for t in payload), 'Incomplete/unsuccessful archived task attempt')
        self.cache[key] = (count, payload)
        return payload


def strict_intervals(engine_rows, jobs, stages, tasks, **binding):
    """Retain adverse observed history instead of overwriting it with success."""
    marker, table = binding.get('marker'), binding.get('rewrite_table')
    def matches(description):
        description = description or ''
        return marker in description if marker is not None else (
            description.startswith('Rewriting ') and description.endswith(' in ' + table))
    histories = {}
    for event in engine_rows:
        if event['resource'] == 'jobs':
            for job in event['payload']:
                if matches(job.get('description')):
                    histories.setdefault(job['jobId'], []).append(job)
    for job_id, history in histories.items():
        require(all(j['status'] in ('RUNNING', 'SUCCEEDED') and j.get('numFailedTasks', 0) == 0
                    and j.get('numKilledTasks', 0) == 0 and j.get('numFailedStages', 0) == 0 for j in history),
                f'Failed/killed/retried observed archive job {job_id}')
        terminal = [j for j in history if j['status'] == 'SUCCEEDED']
        if terminal:
            identity = lambda j: (j['submissionTime'], j.get('completionTime'), tuple(j['stageIds']),
                                  j.get('numCompletedStages'), j.get('numCompletedTasks'))
            require(all(identity(j) == identity(terminal[0]) for j in terminal)
                    and history[-1]['status'] == 'SUCCEEDED',
                    f'Completed archive job changed/regressed {job_id}')
    stage_ids = {sid for history in histories.values() for j in history for sid in j['stageIds']}
    for event in engine_rows:
        if event['resource'] == 'stages':
            for stage in event['payload']:
                if stage['stageId'] in stage_ids and matches(stage.get('description')):
                    require(stage['attemptId'] == 0 and stage.get('status') != 'FAILED'
                            and stage.get('numFailedTasks', 0) == 0
                            and stage.get('numKilledTasks', 0) == 0,
                            'Observed retried/failed/killed stage attempt')
    return task_intervals(jobs, stages, tasks, **binding)


class TerminalArchive:
    def __init__(self, rest, log, event_path, table):
        self.rest, self.log, self.event_path, self.table = rest, log, event_path, table
        self.offset = 0
        self.engine_rows = []
        self.frame_digest = IncrementalFrameDigest()
        self.event_decode_wall_ns = 0
        self.max_event_decode_wall_ns = 0
        self.requests, self.completed, self.certified = {}, {}, set()
        self.tasks = _CachedTasks(rest)
        self.number = 0

    def _ingest(self):
        with self.log.lock:
            with self.event_path.open() as stream:
                stream.seek(self.offset)
                lines = stream.readlines()
                self.offset = stream.tell()
        for line in lines:
            started = time.perf_counter_ns()
            event = json.loads(line)
            elapsed = time.perf_counter_ns() - started
            self.event_decode_wall_ns += elapsed
            self.max_event_decode_wall_ns = max(self.max_event_decode_wall_ns, elapsed)
            if event['kind'] == 'spark_rest':
                self.engine_rows.append(event)
                self.frame_digest.append(event)
            elif event['kind'] == 'statement_requested':
                require(event['measurement_id'] not in self.requests, 'Duplicate statement request')
                self.requests[event['measurement_id']] = event
            elif event['kind'] == 'statement_completed':
                require(event['measurement_id'] not in self.completed, 'Duplicate statement completion')
                self.completed[event['measurement_id']] = event

    def capture(self, *, terminal=False):
        if terminal:
            self.log.emit('terminal_engine_archive_barrier', contract=CONTRACT,
                          meaning='Workload threads joined; no final SQL before terminal task capture')
        started, wall, cpu = stamp(), time.perf_counter_ns(), time.process_time_ns()
        self.rest.capture('jobs')
        self.rest.capture('stages')
        self._ingest()
        jobs, stages = merged_engine_frames(self.engine_rows)
        expected = {mid: row for mid, row in self.completed.items()
                    if row['role'] in ('trace_query', 'maintenance')}
        for mid, row in expected.items():
            if mid in self.certified and not terminal:
                continue
            request = self.requests[mid]
            if row['role'] == 'trace_query':
                selected = [j for j in jobs if request['marker'] in str(j.get('description', ''))]
            else:
                selected = [j for j in jobs
                            if str(j.get('description', '')).startswith('Rewriting ')
                            and str(j.get('description', '')).endswith(' in ' + self.table)]
            # REST can briefly lag the client fetch. Never certify a running or
            # absent call; the mandatory terminal checkpoint cannot omit it.
            if not selected or any(j.get('status') == 'RUNNING' for j in selected):
                require(not terminal,
                        f'Terminal archive missing terminal Spark jobs for {row["role"]} {mid}')
                continue
            try:
                if row['role'] == 'trace_query':
                    strict_intervals(self.engine_rows, jobs, stages, self.tasks, marker=request['marker'])
                else:
                    strict_intervals(self.engine_rows, jobs, stages, self.tasks, rewrite_table=self.table, request=row)
            except Exception as exc:
                raise RuntimeError(f'Cannot archive complete tasks for {row["role"]} {mid}: {exc}') from exc
            self.certified.add(mid)
        self._ingest()  # Include newly downloaded raw task lists in the digest.
        query_ids = sorted(mid for mid in self.certified if expected[mid]['role'] == 'trace_query')
        action_ids = sorted(mid for mid in self.certified if expected[mid]['role'] == 'maintenance')
        require(not terminal or self.certified == set(expected), 'Terminal archive has omitted completed calls')
        self.number += 1
        require(self.frame_digest.count == len(self.engine_rows), 'Archive hash frame count differs')
        source_digest=self.frame_digest.hexdigest()
        observed_jobs=sorted({j['jobId'] for e in self.engine_rows if e['resource']=='jobs' for j in e['payload']})
        self.log.emit('terminal_engine_archive_checkpoint', contract=CONTRACT,
                      checkpoint_number=self.number, terminal=terminal, capture_started=started,
                      capture_ended=stamp(), observer_wall_ns=time.perf_counter_ns()-wall,
                      observer_process_cpu_ns=time.process_time_ns()-cpu,
                      certified_completed_query_ids=query_ids,
                      certified_completed_maintenance_ids=action_ids,
                      observer_timing_scope='checkpoint body before own event serialization/fsync; process CPU includes concurrent collector threads',
                      observed_job_ids=observed_jobs,
                      source_rest_event_count=len(self.engine_rows),
                      source_digest_encoding_wall_ns_cumulative=self.frame_digest.encode_wall_ns,
                      source_digest_encoding_contract='incremental_canonical_json_array_v1',
                      event_decode_wall_ns_cumulative=self.event_decode_wall_ns,
                      max_event_decode_wall_ns=self.max_event_decode_wall_ns,
                      source_rest_events_sha256=source_digest,
                      meaning='Actual completed job/stage/task REST evidence; observer timings are not query or maintenance resource totals')


def audit_terminal_archive(rows, cfg):
    """Reconstruct coverage from raw events; do not accept a certificate boolean."""
    if not validate_contract(cfg):
        return None
    checkpoints = [r for r in rows if r['kind'] == 'terminal_engine_archive_checkpoint']
    require(checkpoints and [r['checkpoint_number'] for r in checkpoints] == list(range(1, len(checkpoints)+1)),
            'Missing/nonsequential engine archive checkpoints')
    terminal = [r for r in checkpoints if r['terminal']]
    require(len(terminal) == 1 and terminal[0] is checkpoints[-1], 'Missing unique last terminal archive')
    end = terminal[0]
    index = rows.index(end)
    prefix = rows[:index]
    completed = {r['measurement_id']: r for r in rows
                 if r['kind'] == 'statement_completed' and r['role'] in ('trace_query', 'maintenance')}
    requests = {r['measurement_id']: r for r in rows if r['kind'] == 'statement_requested'}
    require(completed and all(r in prefix for r in completed.values()), 'Terminal archive before call completion')
    barriers = [r for r in prefix if r['kind'] == 'terminal_engine_archive_barrier']
    require(len(barriers) == 1 and barriers[0]['contract'] == CONTRACT, 'Missing unique terminal barrier')
    barrier_index = rows.index(barriers[0])
    require(all(rows.index(r) < barrier_index for r in completed.values())
            and not any(r['kind'] == 'statement_requested' for r in rows[barrier_index+1:index])
            and not any(r['kind'] in ('common_horizon_multiset_validation', 'common_horizon_final_state') for r in prefix),
            'Workload incomplete or final validation SQL preceded terminal archive')
    for event in checkpoints:
        require(event['contract'] == CONTRACT and isinstance(event['terminal'], bool), 'Archive contract differs')
        position = rows.index(event)
        before = rows[:position]
        engine_rows = [r for r in before if r['kind'] == 'spark_rest']
        require(event['source_rest_event_count'] == len(engine_rows)
                and event['source_rest_events_sha256'] == digest_frames(engine_rows), 'Archive source REST hash differs')
        require(event['capture_started']['monotonic_ns'] <= event['capture_ended']['monotonic_ns']
                <= event['recorded']['monotonic_ns'] and event['observer_wall_ns'] >= 0
                and event['observer_process_cpu_ns'] >= 0, 'Invalid archive observer clocks')
        query_ids, action_ids = event['certified_completed_query_ids'], event['certified_completed_maintenance_ids']
        require(query_ids == sorted(set(query_ids)) and action_ids == sorted(set(action_ids))
                and not set(query_ids) & set(action_ids), 'Duplicate/archive role identity')
        jobs, stages = merged_engine_frames(engine_rows)
        tasks = _CachedTasks(ArchivedTaskEvidence(engine_rows))
        require(event['observed_job_ids'] == sorted({j['jobId'] for e in engine_rows if e['resource']=='jobs' for j in e['payload']}), 'Observed job inventory differs')
        for mid, role in [(mid, 'trace_query') for mid in query_ids] + [(mid, 'maintenance') for mid in action_ids]:
            require(mid in completed and completed[mid] in before and completed[mid]['role'] == role,
                    'Archive certifies unknown/incomplete/wrong-role call')
            if role == 'trace_query':
                strict_intervals(engine_rows, jobs, stages, tasks, marker=requests[mid]['marker'])
            else:
                strict_intervals(engine_rows, jobs, stages, tasks, rewrite_table=cfg['destination_table'], request=completed[mid])
    require(end['certified_completed_query_ids'] == sorted(mid for mid, r in completed.items() if r['role'] == 'trace_query')
            and end['certified_completed_maintenance_ids'] == sorted(mid for mid, r in completed.items() if r['role'] == 'maintenance'),
            'Terminal raw task coverage omits completed calls')
    return {'contract': CONTRACT, 'checkpoint_count': len(checkpoints),
            'query_count': len(end['certified_completed_query_ids']),
            'maintenance_count': len(end['certified_completed_maintenance_ids']),
            'terminal_source_rest_events_sha256': end['source_rest_events_sha256'],
            'meaning': 'Independent raw coverage before final SQL; no model/resource-benefit claim'}
