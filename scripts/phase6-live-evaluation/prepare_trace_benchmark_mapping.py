#!/usr/bin/env python3
"""Export every arrival in the first nonempty TRAIN bin; explicit benchmark mapping, no replay."""
import argparse,csv,json,shutil
from datetime import datetime,timedelta
from pathlib import Path
from experiment_validation import load_json,verified_file,require,sha256
from run_correctness_pilot import query_templates


def instant(value):
    value=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(value.utcoffset() is not None and value.utcoffset().total_seconds()==0,'UTC required')
    return value


def ns_between(a,b):
    delta=a-b
    return (delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000


def prepare(config):
    cfg,base=load_json(config)
    require(cfg['schema_version']=='trace_benchmark_mapping_v1' and cfg['selection'] in ('first_nonempty_complete_training_bin','first_nonempty_complete_window_in_registered_training_day') and cfg['sql_mapping']=='arrival_order_round_robin_registered_templates','Unregistered mapping')
    paths={k:verified_file(cfg[k],base) for k in ('cohort_record','arrivals','bins','sql_template_code')}
    receipt=json.loads(paths['cohort_record'].read_text())
    require(receipt['status']=='extracted_arrival_cohort_only' and receipt['observed_arrivals_sha256']==cfg['arrivals']['sha256'] and receipt['observed_bin_counts_sha256']==cfg['bins']['sha256'],'Unbound cohort sources')
    bin_width=receipt['configuration']['bin_seconds'];window_bins=cfg.get('window_bin_count',1);day=cfg.get('training_day_index',0)
    require(isinstance(window_bins,int) and not isinstance(window_bins,bool) and window_bins>0 and isinstance(day,int) and not isinstance(day,bool) and day>=0,'Register window/day sizes')
    width=bin_width*window_bins;origin=instant(receipt['observation_origin_utc']);end_train=instant(receipt['training_end_utc'])
    lower=origin+timedelta(days=day) if cfg['selection']=='first_nonempty_complete_window_in_registered_training_day' else origin
    upper=min(end_train,lower+timedelta(days=1)) if cfg['selection']=='first_nonempty_complete_window_in_registered_training_day' else end_train
    require(lower<end_train,'Window selected outside training')
    with paths['bins'].open() as f:
        all_bins=list(csv.DictReader(f))
        eligible=[r for r in all_bins if int(r['observed_arrivals'])>0 and lower<=origin+timedelta(seconds=int(r['elapsed_seconds'])) and origin+timedelta(seconds=int(r['elapsed_seconds'])+width)<=upper]
    require(eligible,'No nonempty complete training bin')
    chosen=eligible[0];start=origin+timedelta(seconds=int(chosen['elapsed_seconds']));end=start+timedelta(seconds=width)
    selected=[];count=0;previous=None;identities=set()
    with paths['arrivals'].open() as f:
        for r in csv.DictReader(f):
            timestamp=instant(r['arrival_utc']);identity=r['queryId'];count+=1
            require(identity not in identities and int(r['warehouseId'])==receipt['selected_warehouse_id'],'Duplicate/mixed cohort identity');identities.add(identity)
            require(previous is None or timestamp>=previous,'Arrival order differs');previous=timestamp
            if start<=timestamp<end:selected.append(r)
    chosen_bins=[r for r in all_bins if int(chosen['elapsed_seconds'])<=int(r['elapsed_seconds'])<int(chosen['elapsed_seconds'])+width]
    require(len(chosen_bins)==window_bins and count==receipt['selected_total_arrivals'] and len(selected)==sum(int(r['observed_arrivals']) for r in chosen_bins),'Incomplete source/window coverage')
    selected.sort(key=lambda r:(instant(r['arrival_utc']),int(r['queryId'])))
    require(cfg['query_ids']==list(range(len(query_templates('local.experiment.placeholder')))),'Explicit existing template vocabulary required')
    out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(config,out/'config.json');shutil.copy2(Path(__file__),out/'mapping_code.py');shutil.copy2(paths['sql_template_code'],out/'sql_template_code.py')
    fields=['source_query_id','warehouse_id','source_arrival_utc','offset_ns','query_id']
    with (out/'mapped_arrivals.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for i,r in enumerate(selected):writer.writerow(dict(source_query_id=r['queryId'],warehouse_id=r['warehouseId'],source_arrival_utc=r['arrival_utc'],offset_ns=ns_between(instant(r['arrival_utc']),start),query_id=cfg['query_ids'][i%len(cfg['query_ids'])]))
    report={'schema_version':cfg['schema_version'],'status':'mapped_real_arrivals_no_physical_replay','source_interval_start_utc':start.isoformat(),'source_interval_end_utc':end.isoformat(),'horizon_ns':ns_between(end,start),'source_bin_id':int(chosen['bin_id']),'window_bin_count':window_bins,'training_day_index':day,'arrival_count':len(selected),'mapped_arrivals_sha256':sha256(out/'mapped_arrivals.csv'),'configuration_sha256':sha256(out/'config.json'),'mapping_code_sha256':sha256(out/'mapping_code.py'),'source_sha256':{k:sha256(p) for k,p in paths.items()},'sql_mapping':cfg['sql_mapping'],'limitations':cfg['limitations']}
    (out/'mapping_record.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);prepare(p.parse_args().config)
