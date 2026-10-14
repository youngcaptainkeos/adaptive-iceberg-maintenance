#!/usr/bin/env python3
"""Read-only byte inventory for actual table fallback; never portable-catalog proof."""
import argparse,json,urllib.request
from pathlib import Path
from urllib.parse import urlparse
from experiment_validation import load_json,verified_file,require,sha256

def run(config):
    cfg,base=load_json(config)
    require(cfg['schema_version']=='physical_table_byte_manifest_v1','Unsupported manifest registration')
    url=cfg['spark_rest_url'].rstrip('/')+'/api/v1/applications/'+cfg['spark_app_id']+'/jobs?status=running'
    def idle():
        with urllib.request.urlopen(url,timeout=cfg['rest_timeout_seconds']) as response:
            require(json.load(response)==[],'Active Spark work; defer byte backup')
    idle();tables=[];seen=set()
    for spec in cfg['successful_results']:
        result=verified_file(spec,base);directory=result.parent
        receipt=json.loads(result.read_text());ecfg=json.loads((directory/'config.json').read_text())
        require(receipt['status']=='audited_real_arrival_queue_diagnostic_only','Failed/raw-unverified table unsupported')
        event_path=directory/'events.jsonl';require(sha256(event_path)==receipt['events_sha256'],'Raw evidence changed')
        rows=[json.loads(s) for s in event_path.open()]
        initial=[r for r in rows if r['kind']=='common_horizon_initial_state'];require(len(initial)==1,'Missing unique initial layout')
        inventory=[r for r in rows if r['kind']=='statement_completed' and r['measurement_id']==initial[0]['file_inventory_measurement_id']]
        require(len(inventory)==1 and inventory[0]['rows'],'Missing actual file paths')
        roots=set()
        for row in inventory[0]['rows']:
            parsed=urlparse(row[0]);require(parsed.scheme in ('','file') and not parsed.netloc,'Local actual table files required')
            path=Path(parsed.path);require(path.is_absolute() and path.parent.name=='data','Unreviewed actual file layout')
            roots.add(path.parent.parent)
        require(len(roots)==1,'Ambiguous table root');root=roots.pop()
        require(root.name==ecfg['destination_table'].split('.')[-1] and root.is_dir() and not root.is_symlink() and root not in seen,'Invalid/reused table root')
        seen.add(root);files=[]
        for path in sorted(root.rglob('*')):
            require(not path.is_symlink(),'Symlink in table byte fallback')
            if path.is_file():files.append({'relative_path':str(path.relative_to(root)),'bytes':path.stat().st_size,'sha256':sha256(path)})
        require(files and any(f['relative_path'].startswith('metadata/') for f in files),'Table metadata missing')
        tables.append({'experiment_id':ecfg['experiment_id'],'table':ecfg['destination_table'],'remote_root':str(root),
                       'result_sha256':sha256(result),'events_sha256':sha256(event_path),'files':files})
    idle();output=(base/cfg['output']).resolve()
    with output.open('x') as handle:
        json.dump({'status':'actual_table_byte_manifest_only','code_sha256':sha256(Path(__file__)),
                   'config_sha256':sha256(config),'tables':tables,'file_count':sum(len(t['files']) for t in tables),
                   'bytes':sum(f['bytes'] for t in tables for f in t['files']),
                   'portable_catalog_verified':False,'limitations':['Catalog/absolute metadata references remain worker3-specific.','Byte hashes require rechecking after transfer; do not delete original files.','Failed tables preserved remotely but excluded from this successful-table fallback inventory.']},handle,indent=2)
        handle.write('\n')
    print(json.dumps({'status':'actual_table_byte_manifest_only','tables':len(tables),'output':str(output)}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);a=p.parse_args();run(a.config.resolve())
