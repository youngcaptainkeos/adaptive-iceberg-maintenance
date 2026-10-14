"""Preserve actual retained Spark REST frames; no reconstructed/invented task outcomes."""
import json
from engine_overlap import task_intervals
from experiment_validation import require


class ArchivedTaskEvidence:
    """Read complete successful raw task frames before requesting retained UI data.

    An empty later REST response is evidence of missing retention, not a reason
    to discard an earlier complete immutable stage-attempt frame.
    """
    def __init__(self, rows, live=None):
        self.rows = rows
        self.live = live

    def capture_tasks(self, stage, attempt, count):
        resource = f'stages/{stage}/{attempt}/taskList?length={count}'
        complete = [r['payload'] for r in self.rows if r['kind'] == 'spark_rest'
                    and r['resource'] == resource and isinstance(r['payload'], list)
                    and len(r['payload']) == count
                    and all(t.get('status') == 'SUCCESS' and t.get('duration', 0) > 0 for t in r['payload'])]
        if complete:
            # Same completed attempt must never silently change task identities.
            identities = [{t['taskId'] for t in frame} for frame in complete]
            require(all(ids == identities[0] for ids in identities), 'Archived task identities changed')
            return complete[-1]
        require(self.live is not None, 'Missing complete raw tasks')
        return self.live.capture_tasks(stage, attempt, count)


def merged_engine_frames(rows):
    jobs={};stages={}
    for event in rows:
        if event['kind']!='spark_rest':continue
        if event['resource']=='jobs':
            for job in event['payload']:jobs[job['jobId']]=job
        elif event['resource']=='stages':
            for stage in event['payload']:stages[(stage['stageId'],stage['attemptId'])]=stage
    require(jobs and stages,'Missing actual archived engine frames')
    return list(jobs.values()),list(stages.values())


def capture_completed_query_tasks(rest,log,event_path):
    jobs=rest.capture('jobs');stages=rest.capture('stages')
    with log.lock:rows=[json.loads(line) for line in event_path.open()]
    requested={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
    completed=[r for r in rows if r['kind']=='statement_completed' and r['role']=='trace_query']
    certified=[];maintenance=[]
    for statement in completed:
        marker=requested[statement['measurement_id']]['marker'];selected=[j for j in jobs if marker in str(j.get('description',''))]
        if not selected or any(j['status']!='SUCCEEDED' for j in selected):continue  # Not certified; final audit still requires complete evidence.
        intervals=task_intervals(jobs,stages,rest,marker=marker)
        certified.append(statement['measurement_id'])
    # Rewrite jobs carry Iceberg's own descriptions, rather than SQL markers.
    # Bind them to the actual completed maintenance call and fresh episode table.
    for statement in rows:
        if statement['kind']!='statement_completed' or statement['role']!='maintenance':continue
        decisions=[r for r in rows if r['kind']=='maintenance_decision_observation'
                   and r['measurement_id']==statement['measurement_id']]
        require(len(decisions)==1,'Missing unique maintenance archive decision')
        task_intervals(jobs,stages,rest,rewrite_table=decisions[0]['table'],request=statement)
        maintenance.append(statement['measurement_id'])
    log.emit('engine_archive_checkpoint',certified_completed_query_ids=certified,
             certified_completed_maintenance_ids=maintenance,
             meaning='Actual REST completed-query and maintenance task snapshots preserved before UI retention; omitted/running calls must certify at final audit')
