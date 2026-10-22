"""Terminal-content publication, adapted from the project's verified storage helper.

No queue-package import. Main physical receipts have no top-level status, so caller
must establish producer termination and bind the actual result/failure filename.
"""
import hashlib
import os
import json
import shutil
from pathlib import Path
from three_model_maintenance.contracts import require


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), 'Real evidence directory required')
    result={}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Evidence symlinks forbidden')
        if path.is_file():result[str(path.relative_to(root))]={'bytes':path.stat().st_size,'sha256':sha(path)}
    require(result, 'Empty evidence cannot be published')
    return result


def admit_workspace(path, *, device_id, required_bytes):
    require(path.is_absolute() and not os.path.lexists(path), 'Fresh explicit workspace required')
    require(type(required_bytes) is int and required_bytes>0, 'Registered evidence byte budget required')
    path.parent.mkdir(parents=True, exist_ok=True)
    require(path.parent.stat().st_dev==device_id, 'Workspace on wrong registered device')
    free=shutil.disk_usage(path.parent).free
    require(free>=required_bytes, 'Insufficient workspace space')
    return {'path':str(path),'device_id':device_id,'required_bytes':required_bytes,'free_bytes':free}


def publish_terminal(source, destination, *, terminal_name, terminal_sha256, producer_returncode, required_bytes):
    require(type(producer_returncode) is int, 'Producer must have exited before copying')
    require(terminal_name==('result.json' if producer_returncode==0 else 'failure.json'), 'Terminal outcome/receipt differs')
    require(sha(source/terminal_name)==terminal_sha256, 'Changed terminal receipt')
    require(source.is_absolute() and destination.is_absolute() and source!=destination and
            not source.is_relative_to(destination) and not destination.is_relative_to(source), 'Overlapping archive paths')
    before=inventory(source);size=sum(x['bytes'] for x in before.values())
    require(size<=required_bytes, 'Actual evidence exceeds registered byte budget; preserve working copy')
    staging=destination.with_name(destination.name+'.copying')
    require(not os.path.lexists(destination) and not os.path.lexists(staging), 'Never overwrite archive/partial copy')
    destination.parent.mkdir(parents=True,exist_ok=True)
    require(shutil.disk_usage(destination.parent).free>=size, 'Insufficient canonical archive space')
    shutil.copytree(source,staging)
    require(inventory(staging)==before==inventory(source), 'Changed producer or copied evidence')
    for path in staging.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:os.fsync(stream.fileno())
    for path in sorted([p for p in staging.rglob('*') if p.is_dir()]+[staging],key=lambda p:len(p.parts),reverse=True):
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    require(not os.path.lexists(destination), 'Archive appeared; preserve partial copy')
    staging.rename(destination)
    fd=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    require(inventory(destination)==before==inventory(source), 'Published/source evidence differs')
    return {'status':'verified_terminal_copy_not_scientific_acceptance','source':str(source),'archive':str(destination),
            'producer_returncode':producer_returncode,'source_retained':True,'file_count':len(before),'bytes':size,
            'manifest_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),'files':before}
