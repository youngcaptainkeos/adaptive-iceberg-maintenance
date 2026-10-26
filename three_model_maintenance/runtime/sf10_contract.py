"""Registered SF10 SQL/results and actual plan capture; no inferred SQL/costs."""
import hashlib,json
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read,sha
from three_model_maintenance.audits.sf10_saved_capability import decode_rows
from three_model_maintenance.experiments.scale_query import canonical
from three_model_maintenance.preparation.query_plan import parse


def pin_query(cfg,table,qid,snapshot):
    specs={q['query_id']:q for q in cfg['query_suite']}
    require(qid in specs,'Unknown SQL identity')
    context={n:r['iceberg_table']+' VERSION AS OF '+str(r['snapshot_id']) for n,r in cfg['sf10_tables'].items()}
    context['lineitem']=table+' VERSION AS OF '+str(snapshot)
    return specs[qid]['sql'].format(**context)


def canonical_result(rows,qid,cfg):
    types=next(q['result_types'] for q in cfg['query_suite'] if q['query_id']==qid)
    logged=[[str(v) if isinstance(v,Decimal) else v for v in row] for row in rows]
    return canonical(decode_rows(logged,types))


def references(cfg):
    spec=cfg['typed_reference'];p=Path(spec['path'])
    require(sha(p)==spec['sha256'],'Changed independent SF10 query reference')
    return {str(r['query_id']):r['canonical_rows'] for r in read(p)}


def plan_recorder(Base,cfg):
    class Recorder(Base):
        def __init__(self,log):super().__init__(log);self.plans={}
        def execute(self,cursor,sql,*,role,query_id=None,measurement_id=None,**kwargs):
            if role=='trace_query':
                digest=hashlib.sha256(sql.encode()).hexdigest()
                if digest not in self.plans:
                    records={}
                    for m in ('FORMATTED','COST'):
                        require(datetime.now(timezone.utc)<datetime.fromisoformat(cfg['no_new_operation_after_utc']),'Plan SQL cutoff reached')
                        records[m]=Base.execute(self,cursor,'EXPLAIN '+m+' '+sql,role='sf10_preexecution_plan',query_id=query_id)
                    texts={m:'\n'.join(str(row[0]) for row in r['rows']) for m,r in records.items()}
                    parsed=parse(texts['FORMATTED'],texts['COST'])
                    event=self.log.emit('sf10_plan_receipt',sql=sql,sql_sha256=digest,query_id=query_id,parsed=parsed,
                        explain_measurement_ids={m:r['measurement_id'] for m,r in records.items()})
                    self.plans[digest]=event
                from physical_measurements import stamp
                self.log.emit('sf10_query_plan_binding',measurement_id=measurement_id,sql_sha256=digest,
                    plan_recorded=self.plans[digest]['recorded'],features=self.plans[digest]['parsed']['features'],available_at=stamp())
            return super().execute(cursor,sql,role=role,query_id=query_id,measurement_id=measurement_id,**kwargs)
    return Recorder
