"""Verify exact query-to-window/file-inventory/snapshot evidence without RPCs."""
import re
from telemetry_binding import verify_window
from statement_timing import check_completed_statement
from experiment_validation import require


def verify_observations(rows, cfg):
    requests={r['measurement_id']:r for r in rows if r['kind']=='statement_requested'}
    completed={r['measurement_id']:r for r in rows if r['kind']=='statement_completed'}
    observations=[r for r in rows if r['kind']=='query_observation']
    require(observations,'No bound query observations')
    require(len({r['measurement_id'] for r in observations})==len(observations),'Duplicate query observation')
    telemetry=cfg['telemetry'];checks=[]
    for observation in observations:
        identity=observation['measurement_id'];require(identity in requests and identity in completed,'Unfinished observed query')
        request=requests[identity];result=check_completed_statement(completed[identity])
        require(request['query_id']==observation['query_id'] and request['role']==observation['role'],'Observation identity mismatch')
        table=observation['table'];snapshot=observation['snapshot_id']
        require(re.search(r'\bFROM\s+'+re.escape(table)+r'\s+VERSION\s+AS\s+OF\s+'+str(snapshot)+r'\b',request['sql'],re.IGNORECASE),'Actual query SQL does not pin observed snapshot')
        inventory_id=observation['file_inventory_measurement_id'];snapshot_id=observation['snapshot_measurement_id']
        require(inventory_id in completed and snapshot_id in completed,'Missing actual metadata statement')
        require(completed[snapshot_id]['rows'][0][0]==snapshot,'Metadata snapshot differs')
        require(requests[inventory_id]['sql']==f'SELECT file_path, record_count, file_size_in_bytes FROM {table}.files','Unreviewed inventory SQL')
        files=completed[inventory_id]['rows'];require(files and len({r[0] for r in files})==len(files),'Missing/duplicate physical files')
        require(all(len(r)==3 and isinstance(r[1],int) and isinstance(r[2],int) and r[1]>0 and r[2]>0 for r in files),'Invalid measured file metadata')
        state={'file_count':len(files),'record_count':sum(r[1] for r in files),'total_bytes':sum(r[2] for r in files)}
        require(state==observation['file_state'],'Layout values differ from actual inventory')
        # The current inventory was captured while its stated snapshot was current.
        # Later old-snapshot probes intentionally reference this immutable evidence.
        require(completed[snapshot_id]['fetch_end']['monotonic_ns']<=requests[inventory_id]['request_start']['monotonic_ns']
                and completed[inventory_id]['fetch_end']['monotonic_ns']<=observation['recorded']['monotonic_ns']<=request['request_start']['monotonic_ns'],'Metadata/feature chronology differs')
        windows=observation['windows'];require([w['window_seconds'] for w in windows]==telemetry['window_seconds'],'Missing declared history windows')
        for window in windows:
            verify_window(rows,window,max_interval_seconds=telemetry['max_interval_seconds'],max_age_seconds=telemetry['max_age_seconds'],minimum_coverage_fraction=telemetry['minimum_coverage_fraction'])
            require(window['measured_at']['monotonic_ns']<=observation['recorded']['monotonic_ns'],'Feature available after observation')
            require(0<=(result['client_execute_start']['monotonic_ns']-window['last_available_sample_end_monotonic_ns'])/1e9<=telemetry['max_age_seconds'],'Actual submission uses stale/future telemetry')
        checks.append({'measurement_id':identity,'role':observation['role'],'snapshot_id':snapshot,'file_state':state,'windows_verified':len(windows)})
    rests=[r for r in rows if r['kind']=='spark_rest'];require(rests and all(r.get('app_id')==cfg['spark_app_id'] for r in rests),'Missing/mixed recorded Spark application scope')
    return checks
