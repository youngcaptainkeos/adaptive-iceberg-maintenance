#!/usr/bin/env python3
"""Hash immutable completed real evidence; no table or service operations."""
import argparse,json,hashlib
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(protocol):
 cfg=json.loads(protocol.read_text());repo=Path(cfg['repository']);out=repo/cfg['output'];assert not out.exists(),'Manifest already exists'
 terminal=json.loads((repo/'results/consistent_collection_20261016/result.json').read_text());assert terminal['passed_episodes']==18 and terminal['failed_episodes']==0 and terminal['status']=='completed_candidate_collection_no_models'
 manifest={'status':'completed_evidence_byte_manifest','protocol_sha256':sha(protocol),'code_sha256':sha(Path(__file__)),'files':[],'roots':cfg['roots'],'physical_table_bytes_included':False}
 for root in cfg['roots']:
  d=repo/root;assert d.is_dir(),str(d)
  for p in sorted(d.rglob('*')):
   if p.is_file():
    assert not p.is_symlink(),'No linked evidence accepted'
    before=p.stat();h=sha(p);after=p.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Evidence mutated while hashing'
    manifest['files'].append({'path':str(p.relative_to(repo)),'bytes':after.st_size,'sha256':h})
 assert len({r['path'] for r in manifest['files']})==len(manifest['files']),'Duplicate roots/files'
 manifest.update(file_count=len(manifest['files']),total_bytes=sum(x['bytes'] for x in manifest['files']));out.write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k!='files'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);run(p.parse_args().protocol)
