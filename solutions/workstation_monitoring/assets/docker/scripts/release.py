#!/usr/bin/env python3
"""Durable, project-scoped Docker release preparation and recovery."""
import argparse
import fcntl
import functools
import grp
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'release-state'
PERSISTENT = ROOT / 'persistent'
JOURNAL = STATE / 'release.json'
PROJECT = os.environ.get('COMPOSE_PROJECT_NAME', 'jetson_worktime')
IMAGE = 'chenduola6/jetson-worktime:0.1.0-rc1-jp62-r36.4.3'


def command(*args, **kwargs):
    return subprocess.check_output(args, text=True, cwd=ROOT, **kwargs).strip()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(json.dumps(value, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def journal():
    return json.loads(JOURNAL.read_text()) if JOURNAL.exists() else {}


def serialized(action):
    @functools.wraps(action)
    def wrapped(*args, **kwargs):
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (STATE / 'transaction.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return action(*args, **kwargs)
    return wrapped


def environment(path=None):
    result = {}
    path = path or ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            key, separator, value = line.partition('=')
            if separator:
                result[key] = json.loads(value).replace('$$', '$')
    return result


def compose(*arguments, file=None, env_file=None):
    env_file = env_file or ROOT / '.env'
    process_env = {key: value for key, value in os.environ.items() if not key.startswith('WORKTIME_')}
    process_env.update(environment(env_file))
    return command('docker', 'compose', '--project-directory', str(ROOT), '--env-file', str(env_file),
                   '-f', str(file or ROOT / 'docker-compose.yml'),
                   '-p', PROJECT, *arguments, env=process_env)


def configure():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'deployment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = journal()
        if previous.get('phase') not in (None, 'committed', 'rolled_back'):
            rollback(previous['deployment_id'])
        for name in ('configs', 'data', 'outputs', 'logs'):
            (PERSISTENT / name).mkdir(parents=True, exist_ok=True, mode=0o700)
        port = int(os.environ.get('WORKTIME_PORT', '8088'))
        offset = int(os.environ.get('WORKTIME_MEDIA_PORT_OFFSET', '0'))
        ports = [port] + [p + offset for p in (8189, 8554, 8889, 9997)]
        if any(not 1024 <= p <= 65535 for p in ports) or len(set(ports)) != len(ports):
            raise RuntimeError('Invalid or overlapping HTTP/media ports')
        encoder = os.environ.get('WORKTIME_ENCODER', 'auto')
        if encoder not in ('auto', 'nvidia', 'x264'):
            raise RuntimeError('Unsupported encoder selection')
        def group(name):
            try:
                return grp.getgrnam(name).gr_gid
            except KeyError:
                return os.getgid()
        values = {'WORKTIME_IMAGE': os.environ.get('WORKTIME_IMAGE', IMAGE),
                  'WORKTIME_UID': str(os.getuid()), 'WORKTIME_GID': str(os.getgid()),
                  'WORKTIME_VIDEO_GID': str(group('video')),
                  'WORKTIME_RENDER_GID': str(group('render')),
                  'WORKTIME_PORT': str(port), 'WORKTIME_MEDIA_PORT_OFFSET': str(offset),
                  'WORKTIME_ENCODER': encoder, 'TZ': os.environ.get('TZ', 'Asia/Shanghai')}
        if not re.fullmatch(r'[a-z][a-z0-9_-]{2,50}', PROJECT):
            raise RuntimeError('Invalid Compose project name')
        if not re.fullmatch(r'[a-zA-Z0-9./_:@-]+', values['WORKTIME_IMAGE']):
            raise RuntimeError('Invalid image reference')
        path = ROOT / '.env'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(''.join(k + '=' + json.dumps(v.replace('$', '$$')) + '\n' for k, v in values.items()))
        temporary.chmod(0o600)
        os.replace(temporary, path)
        if not JOURNAL.exists():
            save(JOURNAL, {'phase': 'rolled_back', 'deployment_id': None})
        print('Device configuration prepared')


def check_host():
    release = Path('/etc/nv_tegra_release').read_text()
    model = Path('/proc/device-tree/model').read_text().strip('\0')
    os_release = Path('/etc/os-release').read_text()
    if not re.search(r'# R36 .*REVISION: 4\.3,', release):
        raise RuntimeError('Requires L4T 36.4.3')
    if 'VERSION_ID="22.04"' not in os_release or command('uname', '-m') != 'aarch64':
        raise RuntimeError('Requires Ubuntu 22.04 ARM64')
    if command('uname', '-r') != '5.15.148-tegra':
        raise RuntimeError('Kernel differs from verified 5.15.148-tegra')
    if not any(name in model.lower() for name in ('orin nx', 'orin nano')):
        raise RuntimeError('Requires a supported Orin NX or Orin Nano')
    total = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))
    if total < 7 * 1024**3:
        raise RuntimeError('Requires an 8GB or 16GB module')
    info = json.loads(command('docker', 'info', '--format', '{{json .}}'))
    if 'nvidia' not in info['Runtimes']:
        raise RuntimeError('NVIDIA Runtime missing; configure the JetPack NVIDIA Container Toolkit')
    command('docker', 'compose', 'version')


def check_training():
    database = PERSISTENT / 'data/worktime.sqlite'
    if database.exists():
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
            for value, in connection.execute("SELECT value FROM objects WHERE kind='job'"):
                if json.loads(value).get('state') in ('queued', 'preparing', 'running', 'validating', 'saving', 'stopping'):
                    raise RuntimeError('Pause or finish the active training job before upgrading')


def prepare(ident):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(STATE / 'deployment.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check_host()
        check_training()
        env = environment()
        image = json.loads(command('docker', 'image', 'inspect', env['WORKTIME_IMAGE']))[0]
        if image['Architecture'] != 'arm64' or image['Os'] != 'linux':
            raise RuntimeError('Image platform is not Linux ARM64')
        manifest_path = ROOT / 'release-manifest.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            expected = manifest.get('rootfs_diff_ids')
            if not expected or image['RootFS']['Layers'] != expected:
                raise RuntimeError('Image does not match the published release manifest')
        else:
            raise RuntimeError('Release manifest missing')
        if shutil.disk_usage(ROOT).free < 2 * 1024**3:
            raise RuntimeError('Less than 2GB free disk after image preparation')
        command('docker', 'run', '--rm', '--runtime=nvidia', '--network=none',
                env['WORKTIME_IMAGE'], 'gpu-check')
        active = STATE / 'active.json'
        previous = json.loads(active.read_text()) if active.exists() else None
        if previous is None:
            offset = int(env['WORKTIME_MEDIA_PORT_OFFSET'])
            for protocol, port in [(socket.SOCK_STREAM, int(env['WORKTIME_PORT']))] + [
                (socket.SOCK_STREAM, p + offset) for p in (8189, 8554, 8889, 9997)] + [(socket.SOCK_DGRAM, 8189 + offset)]:
                with socket.socket(socket.AF_INET, protocol) as probe:
                    probe.bind(('0.0.0.0', port))
        backup = ROOT / 'releases' / ident
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        value = {'deployment_id': ident, 'phase': 'preparing', 'previous': previous,
                 'backup': str(backup), 'backup_complete': False, 'started': time.time()}
        save(JOURNAL, value)
        with open(os.devnull, 'wb') as output:
            subprocess.Popen([sys.executable, __file__, 'watch', ident, '--lease-fd', str(descriptor)],
                             pass_fds=(descriptor,), start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=output, stderr=output)
        # Requests that passed the maintenance gate before publication must finish
        # before taking the checkpoint. Recheck training after that short drain.
        time.sleep(2)
        check_training()
        if previous:
            compose('stop', '-t', '60', file=STATE / 'active-compose.yml', env_file=STATE / 'active.env')
        shutil.copytree(PERSISTENT / 'configs', backup / 'configs', dirs_exist_ok=True)
        database = PERSISTENT / 'data/worktime.sqlite'
        if database.exists():
            with sqlite3.connect(database) as source, sqlite3.connect(backup / 'worktime.sqlite') as destination:
                source.backup(destination)
        latest = PERSISTENT / 'outputs/behavior/latest.json'
        if latest.exists():
            shutil.copy2(latest, backup / 'latest.json')
        if previous:
            shutil.copy2(STATE / 'active-compose.yml', backup / 'previous-compose.yml')
            shutil.copy2(STATE / 'active.env', backup / 'previous.env')
        value.update(phase='switching', backup_complete=True)
        save(JOURNAL, value)
        print('Release prepared with rollback checkpoint')
    finally:
        os.close(descriptor)


def ready():
    port = environment()['WORKTIME_PORT']
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
            'http://127.0.0.1:' + port + '/health/ready', timeout=5) as response:
        value = json.load(response)
    if not value.get('ready'):
        raise RuntimeError('Application is not ready')


@serialized
def commit(ident):
    value = journal()
    if value.get('deployment_id') != ident or value.get('phase') != 'switching':
        raise RuntimeError('Release ownership mismatch')
    ready()
    env = environment()
    image = json.loads(command('docker', 'image', 'inspect', env['WORKTIME_IMAGE']))[0]
    shutil.copy2(ROOT / 'docker-compose.yml', STATE / 'active-compose.yml')
    shutil.copy2(ROOT / '.env', STATE / 'active.env')
    # Rollback must survive a mutable registry tag being replaced later.
    pinned = environment(STATE / 'active.env')
    pinned['WORKTIME_IMAGE'] = image['Id']
    (STATE / 'active.env').write_text(''.join(k + '=' + json.dumps(v.replace('$', '$$')) + '\n' for k, v in pinned.items()))
    (STATE / 'active.env').chmod(0o600)
    save(STATE / 'active.json', {'image': env['WORKTIME_IMAGE'], 'image_id': image['Id'],
                               'deployment_id': ident, 'committed_at': time.time()})
    value['phase'] = 'committed'
    save(JOURNAL, value)
    checkpoints = sorted((ROOT / 'releases').iterdir(), key=lambda path: path.stat().st_mtime, reverse=True)
    for checkpoint in checkpoints[2:]:
        if checkpoint.is_dir():
            shutil.rmtree(checkpoint)
    print('Release committed; open the Jetson web address on port ' + env['WORKTIME_PORT'])


@serialized
def rollback(ident):
    value = journal()
    if value.get('deployment_id') != ident or value.get('phase') in ('committed', 'rolled_back'):
        return
    previous = value.get('previous')
    if value.get('phase') != 'preparing':
        compose('stop', '-t', '60')
    backup = Path(value['backup'])
    if value.get('backup_complete'):
        shutil.rmtree(PERSISTENT / 'configs')
        shutil.copytree(backup / 'configs', PERSISTENT / 'configs')
        if (backup / 'worktime.sqlite').exists():
            database = PERSISTENT / 'data/worktime.sqlite'
            for suffix in ('-wal', '-shm'):
                Path(str(database) + suffix).unlink(missing_ok=True)
            shutil.copy2(backup / 'worktime.sqlite', database)
        if (backup / 'latest.json').exists():
            shutil.copy2(backup / 'latest.json', PERSISTENT / 'outputs/behavior/latest.json')
    if previous:
        old_compose = backup / 'previous-compose.yml'
        old_env = backup / 'previous.env'
        if old_compose.exists():
            shutil.copy2(old_compose, STATE / 'active-compose.yml')
            shutil.copy2(old_env, STATE / 'active.env')
        shutil.copy2(STATE / 'active-compose.yml', ROOT / 'docker-compose.yml')
        shutil.copy2(STATE / 'active.env', ROOT / '.env')
        compose('up', '-d', '--wait', '--wait-timeout', '180',
                file=STATE / 'active-compose.yml', env_file=STATE / 'active.env')
        save(STATE / 'active.json', previous)
    value['phase'] = 'rolled_back'
    save(JOURNAL, value)
    print('Previous release restored' if previous else 'Initial deployment stopped; persistent data retained')


def watch(ident, lease_fd):
    try:
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            value = journal()
            if value.get('deployment_id') != ident or value.get('phase') in ('committed', 'rolled_back'):
                return
            time.sleep(2)
        rollback(ident)
    finally:
        os.close(lease_fd)


def diagnose():
    value = journal()
    print(json.dumps({key: value.get(key) for key in
                      ('deployment_id', 'phase', 'started', 'backup_complete')}, indent=2))
    print(compose('ps', '-a'))
    try:
        ready()
        print('Application readiness: PASS')
    except Exception:
        print('Application readiness: unavailable; inspect local container logs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['configure', 'prepare', 'commit', 'rollback', 'watch', 'check', 'diagnose'])
    parser.add_argument('deployment_id', nargs='?', default=os.environ.get('DEPLOYMENT_ID'))
    parser.add_argument('--lease-fd', type=int)
    arguments = parser.parse_args()
    try:
        if arguments.action == 'configure':
            configure()
        elif arguments.action == 'check':
            check_host()
        elif arguments.action == 'diagnose':
            diagnose()
        elif arguments.action == 'watch':
            watch(arguments.deployment_id, arguments.lease_fd)
        else:
            if not arguments.deployment_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', arguments.deployment_id):
                raise RuntimeError('A deployment ID is required')
            {'prepare': prepare, 'commit': commit, 'rollback': rollback}[arguments.action](arguments.deployment_id)
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        sys.exit(1)
