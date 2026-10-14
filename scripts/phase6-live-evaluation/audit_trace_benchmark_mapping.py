#!/usr/bin/env python3
"""Read-only reconstruction of real source-window coverage and declared SQL mapping."""
import argparse,csv,json
from datetime import timedelta
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256
from prepare_trace_benchmark_mapping import instant,ns_between


def audit(config,directory,output):
    cfg,base=load_json(config);directory=Path(directory)
    record=json.loads((directory/'mapping_record.json').read_text())
    require(record['status']=='mapped_real_arrivals_no_physical_replay' and json.loads((directory/'config.json').read_text())==cfg,'Registration changed')
    require(sha256(directory/'config.json')==record['configuration_sha256'] and sha256(directory/'mapping_code.py')==record['mapping_code_sha256'],'Frozen mapping files changed')
    paths={k:verified_file(cfg[k],base) for k in ('cohort_record','arrivals','bins','sql_template_code')}
    require(record['source_sha256']=={k:sha256(p) for k,p in paths.items()} and sha256(directory/'sql_template_code.py')==cfg['sql_template_code']['sha256'],'Source bindings differ')
    receipt=json.loads(paths['cohort_record'].read_text());origin=instant(receipt['observation_origin_utc']);bin_width=receipt['configuration']['bin_seconds'];window_bins=cfg.get('window_bin_count',1);width=bin_width*window_bins
    lower=origin+timedelta(days=cfg['training_day_index']) if cfg['selection']=='first_nonempty_complete_window_in_registered_training_day' else origin
    upper=min(instant(receipt['training_end_utc']),lower+timedelta(days=1)) if cfg['selection']=='first_nonempty_complete_window_in_registered_training_day' else instant(receipt['training_end_utc'])
    with paths['bins'].open() as f:
        all_bins=list(csv.DictReader(f))
        choices=[r for r in all_bins if int(r['observed_arrivals'])>0 and lower<=origin+timedelta(seconds=int(r['elapsed_seconds'])) and origin+timedelta(seconds=int(r['elapsed_seconds'])+width)<=upper]
    chosen=choices[0];start=origin+timedelta(seconds=int(chosen['elapsed_seconds']));end=start+timedelta(seconds=width)
    require(record['source_interval_start_utc']==start.isoformat() and record['source_interval_end_utc']==end.isoformat() and record['horizon_ns']==ns_between(end,start) and record['source_bin_id']==int(chosen['bin_id']),'Window selection changed')
    expected=[]
    with paths['arrivals'].open() as f:
        for r in csv.DictReader(f):
            if start<=instant(r['arrival_utc'])<end:expected.append(r)
    expected.sort(key=lambda r:(instant(r['arrival_utc']),int(r['queryId'])))
    mapped=list(csv.DictReader((directory/'mapped_arrivals.csv').open()))
    included=[r for r in all_bins if int(chosen['elapsed_seconds'])<=int(r['elapsed_seconds'])<int(chosen['elapsed_seconds'])+width]
    require(len(included)==window_bins and len(mapped)==len(expected)==record['arrival_count']==sum(int(r['observed_arrivals']) for r in included),'Arrival coverage differs')
    require(sha256(directory/'mapped_arrivals.csv')==record['mapped_arrivals_sha256'],'Mapped schedule changed')
    for i,(r,src) in enumerate(zip(mapped,expected)):
        require(r=={'source_query_id':src['queryId'],'warehouse_id':src['warehouseId'],'source_arrival_utc':src['arrival_utc'],'offset_ns':str(ns_between(instant(src['arrival_utc']),start)),'query_id':str(cfg['query_ids'][i%len(cfg['query_ids'])])},'Retimed/dropped/invented source or SQL mapping')
    report={'status':'audited_complete_real_arrival_benchmark_mapping_only','arrival_count':len(mapped),'source_interval_start_utc':start.isoformat(),'source_interval_end_utc':end.isoformat(),'mapping_record_sha256':sha256(directory/'mapping_record.json'),'audit_code_sha256':sha256(Path(__file__)),'physical_replay_performed':False,'limitations':cfg['limitations']}
    with Path(output).open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--mapping-directory',required=True);p.add_argument('--output',required=True);a=p.parse_args();audit(a.config,a.mapping_directory,a.output)
