#!/usr/bin/env python3
"""Observe actual worker telemetry to check declared time windows; no generated workload."""
import argparse
import json
from pathlib import Path
import shutil
import time

from experiment_validation import load_json,require,sha256
from physical_measurements import EventLog,TelemetrySampler
from telemetry_binding import verify_ledger


def validate(config_path):
    config,base=load_json(config_path)
    require(config.get('schema_version')=='physical_telemetry_window_check_v1','Unsupported configuration')
    require(bool(config.get('rationale')),'Explain observer parameters and physical conditions')
    windows=config['window_seconds']
    require(isinstance(windows,list) and windows and all(isinstance(w,(int,float)) and w>0 for w in windows),'Declare positive windows')
    require(config['warmup_seconds']>max(windows),'Warmup must exceed longest window')
    require(0<config['minimum_coverage_fraction']<=1,'Declare measured coverage gate')
    output=(base/config['output_directory']).resolve();output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(config_path,output/'config.json')
    for name in ('validate_telemetry_windows.py','physical_measurements.py','experiment_validation.py','telemetry_binding.py'):
        shutil.copy2(Path(__file__).parent/name,output/name)
    log=EventLog(output/'events.jsonl',config['experiment_id'])
    log.emit('protocol',configuration=config,code_sha256={p.name:sha256(p) for p in output.glob('*.py')})
    sampler=TelemetrySampler(log,config['interval_seconds'])
    try:
        sampler.start();time.sleep(config['warmup_seconds']);results=[]
        for seconds in windows:
            window=sampler.window(seconds=seconds,max_interval_seconds=config['max_interval_seconds'],max_age_seconds=config['max_age_seconds'])
            require(window['covered_seconds']/seconds>=config['minimum_coverage_fraction'],'Insufficient measured coverage')
            log.emit('validated_window',**window);results.append(window)
        # Finish this bounded observer before reading its complete immutable ledger.
        sampler.stop()
        checks=verify_ledger(output/'events.jsonl',config)
        result={'raw_counter_reconstruction':checks,'status':'accepted_physical_window_check','windows':results,'scope':'Observer integrity under recorded host conditions; no model or workload performance claim'}
        log.emit('accepted',**result);(output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    except Exception as exc:
        log.emit('failed',error_type=type(exc).__name__,error=str(exc));raise
    finally:
        try: sampler.stop()
        finally: log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True)
    args=parser.parse_args();validate(args.config)
