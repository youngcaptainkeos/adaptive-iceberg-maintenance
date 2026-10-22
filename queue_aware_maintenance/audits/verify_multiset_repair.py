#!/usr/bin/env python3
"""Read-only real-table verification of the failed client's row-container check."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import argparse,json
from pathlib import Path
from queue_aware_maintenance.core.common import checked,require,write_json,now,sha
from queue_aware_maintenance.runtime.run_episode import zero_difference_rows

def run(protocol):
 cfg=json.loads(Path(protocol).read_text());out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
 report={'status':'running','started_utc':now(),'read_only':True}
 try:
  rows=[json.loads(x) for x in checked(cfg['failed_events']).open()]
  requests=[r for r in rows if r.get('kind')=='statement_requested' and 'EXCEPT ALL' in r.get('sql','')]
  require(len(requests)==1,'Ambiguous failed equality SQL');request=requests[0]
  prior=[r for r in rows if r.get('kind')=='statement_completed' and r.get('measurement_id')==request['measurement_id']]
  require(len(prior)==1 and prior[0]['rows']==[[0]],'Actual recorded equality was not zero')
  require(not any(r.get('role')=='trace_query' and r.get('kind')=='statement_requested' for r in rows),'Failed arm already replayed queries')
  sql=request['sql'];require(sql.startswith('SELECT count(*) FROM ((') and ';' not in sql,'Unexpected read-only statement')
  from pyhive import hive
  with hive.Connection(**cfg['engine']) as connection:
   cursor=connection.cursor();cursor.execute(sql);actual=cursor.fetchall()
  require(zero_difference_rows(actual),'Actual multiset differs')
  report.update(status='passed_real_readonly_multiset_container_repair',sql=sql,rows=actual,client_container=type(actual).__name__,client_row_container=type(actual[0]).__name__,legacy_predicate_passes=actual==[[0]],corrected_predicate_passes=zero_difference_rows(actual),failed_events=cfg['failed_events'],workload_requests_in_failed_arm=0)
 except Exception as e:report.update(status='failed_preserved',error=str(e));raise
 finally:
  report.update(ended_utc=now(),protocol_sha256=sha(protocol),code_sha256=sha(__file__),runner_sha256=sha(source_file('run_episode.py')));write_json(out/'result.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);run(p.parse_args().protocol)
