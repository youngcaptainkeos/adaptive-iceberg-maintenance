"""Preserve actual retained Spark REST frames; no reconstructed/invented task outcomes."""
import json
from engine_overlap import task_intervals
from experiment_validation import require


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
    certified=[]
    for statement in completed:
        marker=requested[statement['measurement_id']]['marker'];selected=[j for j in jobs if marker in str(j.get('description',''))]
        if not selected or any(j['status']!='SUCCEEDED' for j in selected):continue  # Not certified; final audit still requires complete evidence.
        intervals=task_intervals(jobs,stages,rest,marker=marker)
        certified.append(statement['measurement_id'])
    log.emit('engine_archive_checkpoint',certified_completed_query_ids=certified,meaning='Actual REST completed-task snapshots preserved before UI retention; omitted/running queries must certify at final audit')
