"""One registered SF10 resource repair; retain failed data and existing services.

Wait for shared physical resources, rehash the successful original source, start
an additional isolated Thrift service, verify its actual scratch configuration,
then run the unchanged full-row ingestion/query/rewrite gates on fresh tables.
There is no retry loop for a physical stage and no service stop on any exit.
"""
import argparse
import ast
import fcntl
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from three_model_maintenance.contracts import require
from three_model_maintenance.training.data import read, save, sha
from three_model_maintenance.experiments import scale_query as pilot

REPO = Path(__file__).resolve().parents[2]
ALERT = REPO / 'scripts/phase6-live-evaluation/run_with_failure_alert.py'
LOCKS = ('.three_model_collection.lock', '.queue_aware_study.lock',
         '.common_horizon_cohort.lock', '.physical_correctness.lock')


def now():
    return datetime.now(timezone.utc).isoformat()


def frozen(cfg):
    for spec in cfg['sources']:
        path = REPO / spec['path']
        require(sha(path) == spec['sha256'], 'Changed source ' + str(path))
        if path.suffix == '.py':
            ast.parse(path.read_text(), filename=str(path))
    for spec in cfg['binaries']:
        require(sha(Path(spec['path'])) == spec['sha256'], 'Changed backend binary')
    original = REPO / cfg['original_protocol']['path']
    require(sha(original) == cfg['original_protocol']['sha256'], 'Changed original protocol')
    pilot.checked(read(original))


def acquire(cfg, update):
    """No data scans, SQL or service launch while another owner holds locks."""
    while datetime.now(timezone.utc) < datetime.fromisoformat(cfg['latest_start_utc']):
        predecessor = Path(cfg['resource_predecessor']['result'])
        if not predecessor.exists():
            update()
            time.sleep(cfg['poll_seconds'])
            continue
        previous = read(predecessor)
        require(previous['protocol_sha256'] == cfg['resource_predecessor']['protocol_sha256'] and
                previous['status'] in cfg['resource_predecessor']['terminal_statuses'] and previous.get('ended_utc'),
                'Resource predecessor identity/terminal state differs')
        held = []
        try:
            for name in LOCKS:
                stream = (REPO / 'results' / name).open('a')
                held.append(stream)
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return held
        except BlockingIOError:
            for stream in held:
                stream.close()
            update()
            time.sleep(cfg['poll_seconds'])
    raise RuntimeError('Resource-wait deadline reached; no physical recovery launched')


def capacity(cfg, root):
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemTotal:', 'MemAvailable:'))}
    data_free = shutil.disk_usage(root).free
    root_free = shutil.disk_usage('/tmp').free
    require(memory['MemAvailable'] >= cfg['minimum_available_memory_bytes'], 'Additional backend RAM budget unavailable')
    require(data_free >= cfg['required_free_bytes'], 'Data/scratch disk budget unavailable')
    require(root_free >= cfg['minimum_system_free_bytes'], 'System disk safety floor unavailable')
    return dict(memory=memory, data_free_bytes=data_free, system_free_bytes=root_free, observed_utc=now())


def backend(cfg, root):
    """New persistent process only. Never mutate or restart the original backend."""
    save(root / 'capacity.json', capacity(cfg, root))
    for port in (cfg['thrift_port'], cfg['ui_port']):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))  # Occupied identity fails before startup.
    directory = Path(cfg['backend_directory'])
    directory.mkdir(parents=True, exist_ok=False)
    for name in ('scratch', 'tmp', 'conf', 'pids', 'logs'):
        (directory / name).mkdir()
    home = cfg['spark_home']
    warehouse = cfg['warehouse']
    command = [str(Path(home) / 'sbin/start-thriftserver.sh'), '--master', cfg['expected_spark_master'],
               '--driver-memory', cfg['driver_memory'], '--jars', cfg['iceberg_jar'],
               '--conf', 'spark.ui.port=' + str(cfg['ui_port']),
               '--conf', 'spark.ui.bindAddress=127.0.0.1',
               '--conf', 'spark.local.dir=' + str(directory / 'scratch'),
               '--conf', 'spark.driver.extraJavaOptions=-Djava.io.tmpdir=' + str(directory / 'tmp'),
               '--conf', 'spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
               '--conf', 'spark.sql.catalog.local=org.apache.iceberg.spark.SparkCatalog',
               '--conf', 'spark.sql.catalog.local.type=hadoop',
               '--conf', 'spark.sql.catalog.local.warehouse=' + warehouse,
               '--hiveconf', 'hive.server2.thrift.port=' + str(cfg['thrift_port']),
               '--hiveconf', 'hive.server2.thrift.bind.host=127.0.0.1',
               '--hiveconf', 'javax.jdo.option.ConnectionURL=jdbc:derby:;databaseName=' + str(directory / 'metastore_db') + ';create=true']
    env = dict(os.environ, SPARK_HOME=home, SPARK_CONF_DIR=str(directory / 'conf'),
               SPARK_LOCAL_DIRS=str(directory / 'scratch'), SPARK_NO_DAEMONIZE='1',
               SPARK_PID_DIR=str(directory / 'pids'), SPARK_LOG_DIR=str(directory / 'logs'),
               SPARK_IDENT_STRING=cfg['experiment_id'])
    require(not env.get('SPARK_MASTER'), 'Unexpected launcher rsync configuration')
    with (directory / 'service.log').open('x') as log, open(os.devnull) as stdin:
        process = subprocess.Popen([sys.executable, '-B', str(ALERT), '--label', cfg['experiment_id'] + '_persistent_backend',
            '--receipt', str(directory / 'failure_alert.json'), '--', *command], cwd=directory, env=env,
            stdin=stdin, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    save(root / 'backend_launch.json', dict(command=command, wrapper_pid=process.pid, log=str(directory / 'service.log'),
        service_retained_on_completion_or_failure=True, started_utc=now()))
    base = 'http://127.0.0.1:' + str(cfg['ui_port'])
    deadline = time.monotonic() + cfg['backend_startup_timeout_seconds']
    last_error = None
    while time.monotonic() < deadline:
        require(process.poll() is None, 'Isolated Spark service exited; inspect preserved service log')
        try:
            with urllib.request.urlopen(base + '/api/v1/applications', timeout=cfg['rest_timeout_seconds']) as response:
                apps = json.load(response)
            require(len(apps) == 1, 'Unexpected new backend application inventory')
            app_id = apps[0]['id']
            with urllib.request.urlopen(base + '/api/v1/applications/' + app_id + '/environment', timeout=cfg['rest_timeout_seconds']) as response:
                environment = json.load(response)
            properties = dict(environment['sparkProperties'])
            require(properties['spark.local.dir'] == str(directory / 'scratch') and
                    properties['spark.master'] == cfg['expected_spark_master'] and
                    properties['spark.driver.memory'] == cfg['driver_memory'] and
                    properties['spark.ui.port'] == str(cfg['ui_port']), 'Actual Spark resource profile differs')
            require(dict(environment['systemProperties'])['java.io.tmpdir'] == str(directory / 'tmp'), 'Actual Java scratch differs')
            require((directory / 'scratch').stat().st_dev == REPO.stat().st_dev, 'Scratch not on registered data filesystem')
            with socket.create_connection(('127.0.0.1', cfg['thrift_port']), timeout=cfg['rest_timeout_seconds']):
                pass
            save(root / 'backend_environment.json', environment)
            return base, app_id
        except (OSError, ValueError, KeyError) as exc:
            last_error = str(exc)
            time.sleep(cfg['poll_seconds'])
    raise RuntimeError('New backend readiness timeout; no SQL launched: ' + str(last_error))


def run(protocol):
    cfg = read(protocol)
    require(cfg['schema_version'] == 'sf10_scratch_recovery_v1', 'Unknown recovery registration')
    frozen(cfg)
    require(subprocess.check_output(['git', 'show', 'HEAD:' + str(protocol.relative_to(REPO))], cwd=REPO) == protocol.read_bytes(),
            'Recovery protocol must be committed unchanged')
    root = Path(cfg['output_directory']); root.mkdir(parents=True, exist_ok=False)
    save(root / 'registration.json', cfg)
    state = dict(status='waiting_for_shared_resources', pid=os.getpid(), started_utc=now(),
                 protocol_sha256=sha(protocol), stages=[], reused_source_only=True,
                 cost_training_accepted=False, matched_pending_state_corpus=False, sf100_ready=False)
    held = []
    def progress():
        state['last_updated_utc'] = now()
        temp = root / 'progress.next.json'; temp.write_text(json.dumps(state, indent=2) + '\n'); temp.replace(root / 'progress.json')
    try:
        progress(); held = acquire(cfg, progress); frozen(cfg)
        state['resource_predecessor_result_sha256'] = sha(Path(cfg['resource_predecessor']['result']))
        # The old terminal failure is an input, not upgraded or hidden.
        original = Path(cfg['original_output_directory'])
        for name, digest in cfg['reused_receipts'].items():
            require(sha(original / name) == digest, 'Changed original evidence ' + name)
        require(read(original / 'result.json')['status'] == 'failed_preserved_no_retry', 'Original failure identity differs')
        source = read(original / 'source_reference/result.json')
        require(source['status'] == 'verified_typed_relational_source_and_reference_queries', 'Source not verified')
        require(sha(original / 'source_reference/query_references.json') == source['reference_sha256'], 'Changed independent query references')
        state['status'] = 'rehashing_successful_source_before_reuse'; progress()
        for item in source['tables']:
            path = Path(item['path'])
            require(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'Changed source data')
        for name in ('generate/result.json', 'source_reference/result.json', 'source_reference/query_references.json'):
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream: stream.write((original / name).read_bytes())
        save(root / 'reuse_manifest.json', dict(status='reused_original_successful_source_not_rerun',
            original_output_directory=str(original), receipts=cfg['reused_receipts'], source_tables=source['tables'],
            original_failed_ingestion_reused=False, rehash_completed_utc=now()))
        pilot.guard(cfg); state['status'] = 'starting_isolated_data_disk_backend'; progress()
        base, app_id = backend(cfg, root)
        execution = read(REPO / cfg['original_protocol']['path'])
        execution.update({key: cfg[key] for key in ('experiment_id', 'output_directory', 'table_prefix', 'no_new_operation_after_utc')})
        execution.update(rest_url=base, spark_app_id=app_id)
        execution['engine'] = dict(execution['engine'], port=cfg['thrift_port'])
        execution['resource_repair_protocol_sha256'] = sha(protocol)
        target = root / 'execution_registration.json'; save(target, execution)
        state.update(status='running_fresh_physical_gates', backend_app_id=app_id, execution_registration_sha256=sha(target)); progress()
        for stage in ('admission', 'prepare', 'plan_query', 'audit'):
            pilot.guard(cfg); frozen(cfg)
            record = dict(stage=stage, started_utc=now()); state['stages'].append(record); progress()
            with (root / (stage + '.log')).open('x') as log:
                result = subprocess.run([sys.executable, '-B', str(ALERT), '--label', cfg['experiment_id'] + '_' + stage,
                    '--receipt', str(root / (stage + '_failure_alert.json')), '--', sys.executable, '-B', '-m',
                    'three_model_maintenance.experiments.scale_query', '--protocol', str(target), '--stage', stage],
                    cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            record.update(returncode=result.returncode, ended_utc=now()); progress()
            require(result.returncode == 0, 'Failed ' + stage + '; no automatic retry')
            record['result_sha256'] = sha(root / stage / 'result.json')
        state['status'] = 'completed_recovered_sf10_capability_only'
    except Exception as exc:
        state.update(status='failed_or_blocked_preserved_no_retry', error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        state['ended_utc'] = now(); progress(); save(root / 'result.json', state)
        for stream in held: stream.close()
    notice = dict(delivered=False)
    try:
        request = urllib.request.Request(cfg['notification_topic'], data=(cfg['experiment_id'] +
            ': SF10 source/ingestion/plans/queries/rewrite capability passed; no model or scheduler acceptance. New backend retained.').encode(),
            headers={'Title': 'Capstone SF10 recovery completed'}, method='POST')
        with urllib.request.urlopen(request, timeout=10) as response: notice.update(delivered=True, http_status=response.status)
    except Exception as exc: notice['error'] = str(exc)
    save(root / 'completion_notification.json', notice)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--protocol', type=Path, required=True)
    run(parser.parse_args().protocol.resolve())
