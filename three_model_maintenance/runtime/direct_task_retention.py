"""Versioned direct-SQL task retention, separate from physical certification.

Preserve every observed complete stage referenced by directly owned jobs, even
when its description lacks the query marker. Referenced stages can be reused;
this archive is not a per-query resource or interference attribution proof.
The existing physical collector does not enable this new contract implicitly.
"""
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from three_model_maintenance.research.common import decode, integer, now, number, require, sha, utc, write_new
from three_model_maintenance.research.ownership import exact_bindings
from three_model_maintenance.research.capture_retained_tasks import validate_tasks

CONTRACT = 'direct_SQL_referenced_task_retention_v1'


def retention_plan(bindings, job_frames, stage_frames):
    """Use actual links and explicit counters; missing references stay unresolved."""
    owned = {integer(j, 'owned job') for b in bindings.values() for j in b['success_job_ids']}
    jobs, stages = {}, {}
    for frame in job_frames:
        for job in frame:
            jid = integer(job['jobId'], 'job ID')
            if jid not in owned:
                continue
            require(job['status'] in ('RUNNING', 'SUCCEEDED'), 'Adverse owned job history')
            for field in ('numFailedTasks', 'numKilledTasks', 'numFailedStages'):
                require(integer(job[field], field) == 0, 'Failed or killed owned work')
            require(type(job['stageIds']) is list, 'Explicit stage IDs required')
            ids = [integer(s, 'stage ID') for s in job['stageIds']]
            require(len(ids) == len(set(ids)), 'Repeated job stage reference')
            if jid in jobs and jobs[jid]['status'] == 'SUCCEEDED':
                require(job == jobs[jid], 'Terminal owned job changed')
            jobs[jid] = job
    stage_ids = {sid for j in jobs.values() for sid in j['stageIds']}
    for frame in stage_frames:
        for stage in frame:
            sid = integer(stage['stageId'], 'stage ID')
            if sid not in stage_ids:
                continue
            attempt = integer(stage['attemptId'], 'stage attempt')
            require(attempt == 0 and stage['status'] in ('PENDING', 'ACTIVE', 'COMPLETE', 'SKIPPED'),
                    'Retried or adverse stage')
            for field in ('numFailedTasks', 'numKilledTasks'):
                require(integer(stage[field], field) == 0, 'Failed or killed stage work')
            key = (sid, attempt)
            if key in stages and stages[key]['status'] in ('COMPLETE', 'SKIPPED'):
                old = stages[key]
                require(stage['status'] == old['status'] and stage['numTasks'] == old['numTasks'],
                        'Terminal stage regressed or population changed')
            stages[key] = stage
    tasks, skipped, incomplete = [], [], []
    for (sid, attempt), stage in sorted(stages.items()):
        if stage['status'] == 'COMPLETE':
            tasks.append(dict(stage_id=sid, attempt_id=attempt,
                              num_tasks=integer(stage['numTasks'], 'stage task count', 1)))
        elif stage['status'] == 'SKIPPED':
            skipped.append(sid)
        else:
            incomplete.append(dict(stage_id=sid, attempt_id=attempt, status=stage['status']))
    return dict(contract=CONTRACT, directly_owned_job_ids=sorted(owned),
                missing_owned_job_ids=sorted(owned-jobs.keys()),
                nonterminal_owned_job_ids=sorted(j for j,v in jobs.items() if v['status'] != 'SUCCEEDED'),
                referenced_stage_ids=sorted(stage_ids),
                missing_referenced_stage_ids=sorted(stage_ids-{s for s,_ in stages}),
                observed_skipped_stage_ids=skipped, nonterminal_stage_attempts=incomplete,
                complete_stage_task_requests=tasks, physical_episode_accepted=False,
                per_query_resource_attribution_certified=False)


class DirectTaskRetention:
    """Bounded read-only REST adapter with immutable raw response receipts.

    Caller supplies original requests/completions, a fresh evidence directory,
    explicit pagination/read limits and deadline from a registered protocol.
    No retries, SQL execution, subprocess control or implicit legacy activation.
    """
    def __init__(self, directory, *, base_url, app_id, page_length, max_pages,
                 max_requests_per_checkpoint, timeout_seconds, latest_request_utc):
        url = urlsplit(base_url)
        require(url.scheme == 'http' and url.hostname == '127.0.0.1' and url.port is not None
                and url.path in ('', '/') and not url.query and not url.fragment, 'Use loopback Spark REST')
        require(app_id and all(c.isalnum() or c in '-_' for c in app_id), 'Invalid app ID')
        self.root = Path(directory); self.root.mkdir(parents=True, exist_ok=False)
        self.url = base_url.rstrip('/') + '/api/v1/applications/' + app_id
        self.page_length = integer(page_length, 'page length', 1)
        self.max_pages = integer(max_pages, 'max pages', 1)
        self.max_requests = integer(max_requests_per_checkpoint, 'max requests', 1)
        self.timeout = number(timeout_seconds, 'timeout', 0)
        require(self.timeout > 0, 'Positive timeout required')
        self.deadline = utc(latest_request_utc)
        self.jobs, self.stages, self.tasks = [], [], {}
        self.checkpoint = 0
        self.failed = False

    def _get(self, directory, resource, receipts):
        require(len(receipts) < self.max_requests, 'Checkpoint REST request bound exhausted')
        require(utc(now()) < self.deadline, 'Registered REST cutoff reached')
        n = len(receipts)
        raw = directory / f'response_{n:05d}.json'
        record = dict(resource=resource, url=self.url+'/'+resource, request_start_utc=now(),
                      request_start_monotonic_ns=time.monotonic_ns(), raw_path=str(raw.relative_to(self.root)))
        try:
            with urllib.request.urlopen(record['url'], timeout=self.timeout) as response:
                body = response.read(); record['http_status'] = response.status
            with raw.open('xb') as stream:
                stream.write(body)
            record['raw_sha256'] = sha(raw)
            return decode(body)
        except urllib.error.HTTPError as exc:
            with raw.open('xb') as stream:
                stream.write(exc.read())
            record.update(http_status=exc.code, raw_sha256=sha(raw), error=str(exc))
            raise
        except Exception as exc:
            record['error'] = str(exc)
            raise
        finally:
            record.update(response_end_utc=now(), response_end_monotonic_ns=time.monotonic_ns())
            receipts.append(record)
            write_new(directory / f'receipt_{n:05d}.json', record)

    def capture(self, requests, completed_calls, *, terminal=False):
        require(not self.failed, 'Failed archive cannot be resumed or retried')
        self.checkpoint += 1
        directory = self.root / f'checkpoint_{self.checkpoint:05d}'
        directory.mkdir(exist_ok=False)
        receipts = []
        result = dict(contract=CONTRACT, checkpoint=self.checkpoint, terminal=terminal,
                      started_utc=now(), physical_episode_accepted=False)
        try:
            inventory, seen = [], set()
            for page in range(self.max_pages):
                values = self._get(directory, 'sql?details=true&planDescription=true&offset='
                                   +str(page*self.page_length)+'&length='+str(self.page_length), receipts)
                require(type(values) is list and len(values) <= self.page_length, 'Invalid SQL page')
                for row in values:
                    sid = integer(row['id'], 'SQL ID')
                    require(sid not in seen, 'Duplicate SQL ID across mutable pages')
                    seen.add(sid); inventory.append(row)
                if len(values) < self.page_length:
                    break
            else:
                raise ValueError('SQL page bound exhausted; no truncation allowed')
            # Exact requested-call coverage only. An empty final page is not proof
            # of exhaustive engine history while concurrent SQL changes inventory.
            proof = exact_bindings(requests, completed_calls, inventory)
            jobs = self._get(directory, 'jobs', receipts)
            stages = self._get(directory, 'stages', receipts)
            require(type(jobs) is list and type(stages) is list, 'Invalid engine inventory')
            self.jobs.append(jobs); self.stages.append(stages)
            plan = retention_plan(proof['bindings'], self.jobs, self.stages)
            write_new(directory / 'selection.json', dict(bindings=proof, plan=plan))
            retained = []
            for request in plan['complete_stage_task_requests']:
                sid, attempt, count = request['stage_id'], request['attempt_id'], request['num_tasks']
                key = (sid, attempt)
                if key not in self.tasks:
                    payload = self._get(directory, f'stages/{sid}/{attempt}/taskList?length={count}', receipts)
                    validate_tasks(payload, count)
                    self.tasks[key] = dict(request=request, raw_path=receipts[-1]['raw_path'],
                                           raw_sha256=receipts[-1]['raw_sha256'])
                cached = self.tasks[key]
                require(cached['request'] == request and sha(self.root/cached['raw_path']) == cached['raw_sha256'],
                        'Cached task population or raw bytes changed')
                retained.append(cached)
            write_new(directory / 'retained_tasks.json', retained)
            if terminal:
                require(not any(plan[k] for k in ('missing_owned_job_ids','nonterminal_owned_job_ids',
                        'missing_referenced_stage_ids','nonterminal_stage_attempts')),
                        'Terminal direct archive has missing/nonterminal evidence')
            result.update(status='captured_direct_referenced_tasks_only', retained_stage_attempts=len(retained),
                          completed_calls=len(completed_calls),
                          limitation='No completed/skipped per-job execution reconciliation, overlap proof or physical acceptance')
            return result
        except Exception as exc:
            self.failed = True
            result.update(status='failed_preserved', error=str(exc))
            raise
        finally:
            result.update(ended_utc=now(), requests=len(receipts))
            write_new(directory / 'result.json', result)
