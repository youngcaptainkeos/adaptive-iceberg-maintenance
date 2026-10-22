"""Fresh persistent evidence workspace and verified terminal archive publication."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from queue_aware_maintenance.core.common import require, sha


def inventory(directory):
    root = Path(directory)
    require(root.is_dir() and not root.is_symlink(), 'Real evidence directory required')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Do not follow evidence symlinks during publication')
        if path.is_file():
            result[str(path.relative_to(root))] = {'bytes':path.stat().st_size,'sha256':sha(path)}
    require(result, 'Empty evidence is not a completed artifact')
    return result


def prepare_workspace(directory, *, device_reference, required_bytes):
    """Reserve a new explicit working directory; budget is supplied by registration."""
    directory, reference = Path(directory), Path(device_reference)
    require(directory.is_absolute() and reference.is_absolute(), 'Explicit absolute storage paths required')
    require(isinstance(required_bytes, int) and not isinstance(required_bytes, bool) and required_bytes > 0, 'Registered positive byte budget required')
    require(not os.path.lexists(directory), 'Never reuse an evidence workspace')
    ancestor = directory.parent
    while not ancestor.exists(): ancestor = ancestor.parent
    require(os.stat(ancestor).st_dev == os.stat(reference).st_dev, 'Wrong workspace device')
    require(shutil.disk_usage(ancestor).free >= required_bytes, 'Insufficient free space for registered budget')
    directory.mkdir(parents=True, exist_ok=False)
    return {'directory':str(directory),'device':os.stat(directory).st_dev,'required_bytes':required_bytes,
            'free_bytes_at_creation':shutil.disk_usage(directory).free}


def publish_terminal_copy(source, destination, *, result_sha256, expected_terminal_status):
    """Copy a terminal artifact via a fresh staging directory, retaining the source.

    The caller must establish producer termination and single ownership first.
    This verifies archival content/durability, never scientific acceptance.
    """
    source, destination = Path(source), Path(destination)
    require(source.is_absolute() and destination.is_absolute(), 'Absolute publication paths required')
    require(source != destination and not destination.is_relative_to(source) and not source.is_relative_to(destination), 'Overlapping publication paths')
    require(sha(source/'result.json') == result_sha256, 'Changed terminal receipt')
    status = json.loads((source/'result.json').read_text())['status']
    require(status == expected_terminal_status and status not in ('running','pending'), 'Expected terminal status required')
    before = inventory(source)
    staging = destination.with_name(destination.name+'.copying')
    require(not os.path.lexists(destination) and not os.path.lexists(staging), 'Never overwrite archive or partial attempt')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, staging)
    require(inventory(staging) == before == inventory(source), 'Copy differs or producer still changing evidence')
    # Persist copied bytes and directory entries before exposing the final archive name.
    for path in staging.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream: os.fsync(stream.fileno())
    directories = [p for p in staging.rglob('*') if p.is_dir()]+[staging]
    for path in sorted(directories, key=lambda p:len(p.parts), reverse=True):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    require(not os.path.lexists(destination), 'Archive appeared during publication; preserve partial copy')
    staging.rename(destination)
    fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    require(inventory(destination) == before == inventory(source), 'Postpublication evidence differs')
    return {'status':'verified_terminal_content_copy_only','source':str(source),'archive':str(destination),
            'file_count':len(before),'bytes':sum(v['bytes'] for v in before.values()),
            'manifest_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
            'files':before,'source_retained':True,'scientific_acceptance_created':False}
