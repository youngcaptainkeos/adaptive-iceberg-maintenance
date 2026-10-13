"""Evidence-only Spark task attribution and overlap; never synthesize task intervals."""
from datetime import datetime
from experiment_validation import require


def engine_time(value):
    require(isinstance(value,str) and value.endswith('GMT'), 'Expected Spark UTC timestamp')
    return datetime.fromisoformat(value[:-3]+'+00:00').timestamp()


def task_intervals(jobs, stages, rest, *, marker=None, rewrite_table=None, request=None):
    require((marker is None) != (rewrite_table is None), 'Choose marker or exclusive rewrite table')
    def matches(description):
        if marker is not None:
            return marker in (description or '')
        return (description or '').startswith('Rewriting ') and (description or '').endswith(' in '+rewrite_table)
    selected=[j for j in jobs if matches(j.get('description'))]
    if rewrite_table:
        start=datetime.fromisoformat(request.get('client_execute_start',request['request_start'])['utc']).timestamp()
        end=datetime.fromisoformat(request['fetch_end']['utc']).timestamp()
        selected=[j for j in selected if start <= engine_time(j['submissionTime'])
                  and engine_time(j['completionTime']) <= end
                  and str(j.get('jobGroup','')).startswith('REWRITE-DATA-FILES')]
    require(bool(selected), 'No attributable Spark jobs')
    require(all(j['status']=='SUCCEEDED' and j.get('numFailedTasks',0)==0
                and j.get('numKilledTasks',0)==0 for j in selected), 'Failed/retried Spark work cannot certify overlap')
    stage_ids={s for job in selected for s in job['stageIds']}
    selected_stages=[s for s in stages if s['stageId'] in stage_ids and matches(s.get('description'))]
    require(bool(selected_stages), 'No attributable executed stages')
    for job in selected:
        matched = {s['stageId'] for s in selected_stages if s['stageId'] in job['stageIds']}
        require(isinstance(job.get('numCompletedStages'), int)
                and len(matched) == job['numCompletedStages'],
                'Incomplete attributable completed-stage coverage')
    intervals=[]
    for stage in selected_stages:
        require(stage['status']=='COMPLETE' and stage['numFailedTasks']==0 and stage['numKilledTasks']==0,
                'Incomplete or retried stage')
        tasks=rest.capture_tasks(stage['stageId'],stage['attemptId'],stage['numTasks'])
        for task in tasks:
            require(task['status']=='SUCCESS' and task['duration']>0, 'Invalid completed task evidence')
            launched=engine_time(task['launchTime'])
            intervals.append(dict(stage_id=stage['stageId'],attempt_id=stage['attemptId'],
                                  task_id=task['taskId'],start_epoch_seconds=launched,
                                  end_epoch_seconds=launched+task['duration']/1000))
    require(bool(intervals),'No physical task intervals')
    return intervals


def overlap_evidence(query_tasks,rewrite_tasks):
    pairs=[]
    for query in query_tasks:
        for rewrite in rewrite_tasks:
            start=max(query['start_epoch_seconds'],rewrite['start_epoch_seconds'])
            end=min(query['end_epoch_seconds'],rewrite['end_epoch_seconds'])
            if end>start:
                pairs.append(dict(query_task_id=query['task_id'],rewrite_task_id=rewrite['task_id'],
                                  start_epoch_seconds=start,end_epoch_seconds=end))
    # Duration is union of overlap intervals, not inflated by task-pair count.
    union=[]
    for start,end in sorted((p['start_epoch_seconds'],p['end_epoch_seconds']) for p in pairs):
        if union and start<=union[-1][1]: union[-1][1]=max(union[-1][1],end)
        else: union.append([start,end])
    return dict(verified_task_lifetime_overlap=bool(pairs),overlap_seconds=sum(b-a for a,b in union),
                task_pairs=pairs,meaning='Overlapping Spark task lifetimes; not proof of simultaneous CPU execution')
