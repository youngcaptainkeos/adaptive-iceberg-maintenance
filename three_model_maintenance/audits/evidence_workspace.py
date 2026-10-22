"""Validate transport with the actual completed attempt02 package; no new labels."""
import argparse
import json
import shutil
from pathlib import Path
from three_model_maintenance.observability.evidence_workspace import admit_workspace,publish_terminal,inventory,sha
from three_model_maintenance.contracts import require


def run(config):
    cfg=json.loads(config.read_text());source=Path(cfg['source']);parent=Path(cfg['parent_result'])
    require(sha(parent)==cfg['parent_sha256'] and sha(source/'result.json')==cfg['result_sha256'],'Changed actual terminal evidence')
    report=json.loads(parent.read_text());require(report['status']=='completed_one_real_development_measurement_only','Nonterminal prior producer')
    require(next(s for s in report['stages'] if s['label']=='physical')['returncode']==0,'Prior physical producer not successful')
    work=Path(cfg['workspace']);archive=Path(cfg['archive']);out=Path(cfg['output_directory']);out.mkdir(parents=True,exist_ok=False)
    admitted=admit_workspace(work,device_id=cfg['device_id'],required_bytes=cfg['required_bytes'])
    before=inventory(source);shutil.copytree(source,work)
    require(inventory(work)==before==inventory(source),'Workspace copy differs')
    publication=publish_terminal(work,archive,terminal_name='result.json',terminal_sha256=cfg['result_sha256'],
                                 producer_returncode=0,required_bytes=cfg['required_bytes'])
    require(inventory(archive)==before==inventory(source),'Roundtrip differs')
    result={'status':'passed_actual_terminal_package_roundtrip_only','admission':admitted,'publication':publication,
            'original_retained':True,'new_sql_or_training':False,'protocol_sha256':sha(config),'code_sha256':sha(Path(__file__))}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='publication'}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);run(p.parse_args().config.resolve())
