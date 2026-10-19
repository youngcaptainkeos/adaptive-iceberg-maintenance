#!/usr/bin/env python3
"""Bind a completed registered cohort to its preregistered analysis, without refit."""
import argparse,json
from pathlib import Path
from common import require,sha,write_json,now

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort-result',required=True);p.add_argument('--protocol',required=True);p.add_argument('--output-directory',required=True);a=p.parse_args()
 source=Path(a.cohort_result).resolve();r=json.loads(source.read_text());registration=json.loads((source.parent/'registration.json').read_text())
 planned=sum(len(order) for order in registration['registered_orders'])
 require(r['status']=='completed_full_physical_feasibility_pending_independent_comparison' and r['passed']==planned==8 and r['failed']==r['unattempted']==0,'Whole preregistered cohort must complete before comparison')
 require(not Path(a.output_directory).exists(),'Preserve previous analysis outputs')
 write_json(a.protocol,{'cohort_result':{'path':str(source),'sha256':sha(source)},'output_directory':str(Path(a.output_directory).resolve()),'registered_utc':now(),'analysis_contract':'All preregistered arms, raw reconstruction and past-only decision replay; paired full-cohort response contrasts for all three baselines; no model refit, tuning or calibration claim.','physical_registration_sha256':sha(source.parent/'registration.json')})
 print(a.protocol,flush=True)
