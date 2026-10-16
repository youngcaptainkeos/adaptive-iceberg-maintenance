#!/usr/bin/env python3
"""Real accepted/failed raw regressions; never generate timestamps, queries or data."""
import argparse,json,traceback
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256,ValidationError
from run_trace_queue_diagnostic import audit

def run(protocol):
    cfg,base=load_json(protocol);require(cfg['schema_version']=='real_rpc_boundary_regression_v1','Unsupported regression protocol')
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','cases':[],'new_rpc_abort_branch_live_verified':False,'failed_historical_evidence_upgraded':False}
    try:
        for case in cfg['cases']:
            event_path=verified_file(case['events'],base);directory=event_path.parent
            try:
                result=audit(directory)
                report['cases'].append({'directory':str(directory),'status':'accepted_raw_regression_passed','events_sha256':sha256(event_path),'offered':result['offered'],'dispatched':result['dispatched']})
            except ValidationError as exc:
                if case['expected']!='reject':raise
                require(case['expected_error'] in str(exc),'Historical failure rejected for a different reason')
                report['cases'].append({'directory':str(directory),'status':'historical_failure_correctly_rejected','error':str(exc),'events_sha256':sha256(event_path)})
            else:
                require(case['expected']=='pass','Previously failed raw evidence unexpectedly accepted')
        report['status']='real_raw_regressions_passed_new_live_branch_pending'
    except Exception as exc:
        report.update(status='failed_preserved',error=str(exc),traceback=traceback.format_exc());raise
    finally:
        report['protocol_sha256']=sha256(protocol);report['audit_code_sha256']=sha256(Path(__file__))
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,required=True);a=p.parse_args();run(a.protocol)
