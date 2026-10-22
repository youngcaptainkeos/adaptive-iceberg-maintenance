"""Bounded source/entrypoint audit, not a claim of formal absence of all bugs."""
import argparse,ast,hashlib,json
from pathlib import Path
from three_model_maintenance.contracts import require

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(config):
    cfg=json.loads(config.read_text());base=config.parent;out=(base/cfg['output_directory']).resolve();out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','files':[],'weights_loaded':False,'inference_run':False}
    try:
        for spec in cfg['sources']:
            p=(base/spec['path']).resolve();require(sha(p)==spec['sha256'],'Source changed '+str(p));tree=ast.parse(p.read_text(),filename=str(p))
            entry={'path':spec['path'],'sha256':sha(p),'review_class':spec['review_class'],'imports':[]}
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):entry['imports'].extend(a.name for a in node.names)
                if isinstance(node,ast.ImportFrom):entry['imports'].append(node.module or '')
            if spec['review_class']=='new_three_model_path':
                require(not any(x.startswith(('queue_aware_maintenance','joblib')) or 'run_cost_benefit_agent' in x or 'google_trace_mapper' in x for x in entry['imports']), 'New source imports legacy weights/trace adapter or queue code')
                handlers=[n for n in ast.walk(tree) if isinstance(n,ast.ExceptHandler)]
                require(all(any(isinstance(v,ast.Raise) for v in ast.walk(h)) for h in handlers),'Exception path without explicit rethrow needs manual review')
            if spec['review_class']=='retired_live_entrypoint':
                require(any(isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call) and isinstance(n.exc.func,ast.Name) and n.exc.func.id=='SystemExit' for n in tree.body),'Retired entrypoint is no longer unconditionally blocked')
            if spec['review_class']=='retired_policy_decision':
                methods=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='decide'];require(len(methods)==1 and len(methods[0].body)==1 and isinstance(methods[0].body[0],ast.Raise),'Legacy policy decision no longer refuses scheduling')
            report['files'].append(entry)
        metadata=(base/cfg['legacy_metadata_path']).resolve();card=json.loads(metadata.read_text())
        report['legacy_metadata']={'path':str(metadata),'sha256':sha(metadata),'schema_version':card.get('schema_version'),'validation_status':card.get('validation_status'),'feature_names':card.get('features'),'accepted_by_new_pipeline':False}
        require(not(card.get('schema_version')=='three_model_candidate_card_v1'),'Unexpected new card in legacy location; review required')
        report.update(status='passed_registered_source_boundaries_only',limitations=[
            'Manual source classifications are hash-pinned; AST checks cover specified structural boundaries, not semantic proof of no fabrication anywhere.',
            'Historical source/models/tests are preserved and not re-certified; no old weight is loaded or old score reproduced.',
            'Trace normalization and threshold bins remain a legacy verified-trace adapter, not Model C or original database SQL demand.',
            'Standalone empirical baselines may be compared, but missing/OOD learned predictions must remain unsupported; no automatic substitution.'])
    finally:
        report['protocol_sha256']=sha(config);report['audit_source_sha256']=sha(Path(__file__));(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);run(p.parse_args().config.resolve())
