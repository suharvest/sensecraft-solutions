#!/usr/bin/env python3
"""Maintainer build/publish and verified offline deployment (Python stdlib only)."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'chenduola6/jetson-worktime:0.1.0-rc1-jp62-r36.4.3'


def run(*args, capture=False, cwd=ROOT, env=None):
    if capture:
        return subprocess.check_output(args, text=True, cwd=cwd, env=env).strip()
    subprocess.run(args, cwd=cwd, env=env, check=True)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inspected(image):
    return json.loads(run('docker', 'image', 'inspect', image, capture=True))[0]


def resolve_build_dir(build_dir=None):
    candidate = Path(build_dir).expanduser().resolve() if build_dir else (ROOT.parent / 'image')
    if not candidate.is_dir() or not (candidate / 'resources.lock.json').is_file():
        raise RuntimeError(
            f'Build directory not found or missing resources.lock.json: {candidate}. '
            'Pass --build-dir pointing to the image/ directory in the application source repository.'
        )
    return candidate


def manifest(image, build_dir=None):
    resolved_build_dir = resolve_build_dir(build_dir)
    value = inspected(image)
    app = resolved_build_dir / 'app'
    source = hashlib.sha256()
    for path in sorted(app.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and not path.name.startswith('._'):
            source.update(str(path.relative_to(app)).encode() + b'\0' + bytes.fromhex(sha(path)))
    result = {'schema_version': 1, 'image': image, 'image_id': value['Id'],
              'platform': 'linux/arm64', 'rootfs_diff_ids': value['RootFS']['Layers'],
              'source_sha256': source.hexdigest(), 'created_at': value['Created'],
              'compatibility': {'ubuntu': '22.04', 'l4t': '36.4.3', 'kernel': '5.15.148-tegra',
                                'modules': ['Orin NX 8GB', 'Orin NX 16GB', 'Orin Nano 8GB']},
              'runtime': {'cuda': '12.6.68', 'cudnn': '9.3.0.75', 'tensorrt': '10.3.0.30',
                          'torch': '2.7.0', 'torchvision': '0.22.0'},
              'resources': json.loads((resolved_build_dir / 'resources.lock.json').read_text())}
    (ROOT / 'release-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def verify(image):
    expected = json.loads((ROOT / 'release-manifest.json').read_text())
    if inspected(image)['RootFS']['Layers'] != expected['rootfs_diff_ids']:
        raise RuntimeError('Image does not match the release manifest')
    return expected


def build(resources, image, build_dir=None):
    if platform.machine() != 'aarch64':
        raise RuntimeError('Build on the ARM64 Jetson release builder')
    resolved_build_dir = resolve_build_dir(build_dir)
    resources = Path(resources).resolve()
    lock = json.loads((resolved_build_dir / 'resources.lock.json').read_text())
    for relative, expected in lock.items():
        path = resources / relative
        if not path.is_file() or sha(path) != expected['sha256']:
            raise RuntimeError('Resource checksum mismatch: ' + relative)
    # COPY must use files inside the context; never include a live project tree.
    with tempfile.TemporaryDirectory(prefix='worktime-build-') as temporary:
        context = Path(temporary)
        shutil.copytree(resolved_build_dir, context, dirs_exist_ok=True)
        shutil.copytree(resources, context / 'resources')
        run('docker', 'build', '--platform=linux/arm64', '--network=host',
            '-t', 'jetson-worktime-cuda:12.6-r36.4.3', str(resolved_build_dir / 'cuda-runtime'))
        run('docker', 'build', '--platform=linux/arm64', '--network=host', '-t', image, str(context))
    run('docker', 'run', '--rm', '--runtime=nvidia', '--network=none', image, 'gpu-check')
    manifest(image, build_dir=resolved_build_dir)
    print('Build and GPU verification complete: ' + image)


def publish(image):
    verify(image)
    run('docker', 'run', '--rm', '--runtime=nvidia', '--network=none', image, 'gpu-check')
    run('docker', 'push', image)
    value = json.loads((ROOT / 'release-manifest.json').read_text())
    digests = inspected(image).get('RepoDigests', [])
    digests = [d for d in digests if d.split('@')[0].endswith('chenduola6/jetson-worktime')]
    if not digests:
        raise RuntimeError('Push finished but the registry digest was not recorded')
    value['registry_digest'] = digests[0]
    (ROOT / 'release-manifest.json').write_text(json.dumps(value, indent=2) + '\n')
    print('Published: ' + digests[0])


def export(output, image):
    value = verify(image)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    required = inspected(image)['Size'] * 2 + 2*1024**3
    if shutil.disk_usage(output).free < required:
        raise RuntimeError('Insufficient disk for image export and compression')
    target = output / ('jetson-worktime-' + image.rsplit(':', 1)[-1] + '-arm64.tar.gz')
    with tempfile.TemporaryDirectory(prefix='.worktime-export-', dir=output) as temporary:
        staging = Path(temporary)
        for file in ('docker-compose.yml', 'release-manifest.json'):
            shutil.copy2(ROOT / file, staging / file)
        shutil.copytree(ROOT / 'scripts', staging / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        run('docker', 'save', '-o', str(staging / 'image.tar'), image)
        image_sha = sha(staging / 'image.tar')
        (staging / 'offline.json').write_text(json.dumps({'image': image, 'image_sha256': image_sha,
                                                        'rootfs_diff_ids': value['rootfs_diff_ids']}, indent=2))
        temporary_target = target.with_suffix('.partial')
        with tarfile.open(temporary_target, 'w:gz', compresslevel=1) as archive:
            for entry in sorted(staging.iterdir()):
                archive.add(entry, arcname=entry.name)
        os.replace(temporary_target, target)
    checksum = sha(target)
    Path(str(target) + '.sha256').write_text(checksum + '  ' + target.name + '\n')
    print(str(target))
    print('SHA256: ' + checksum)


def check_training(destination):
    database = destination / 'persistent/data/worktime.sqlite'
    if database.exists():
        with contextlib.closing(sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True)) as connection:
            for value, in connection.execute("SELECT value FROM objects WHERE kind='job'"):
                if json.loads(value).get('state') in ('queued', 'preparing', 'running', 'validating', 'saving', 'stopping'):
                    raise RuntimeError('Pause or finish the active training job before upgrading')


def install(archive, destination, checksum):
    archive = Path(archive).resolve()
    if not checksum:
        sidecar = Path(str(archive) + '.sha256')
        if not sidecar.exists():
            raise RuntimeError('A SHA256 sidecar or --sha256 is required')
        checksum = sidecar.read_text().split()[0]
    if sha(archive) != checksum:
        raise RuntimeError('Offline archive checksum mismatch')
    destination = Path(destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_dir = destination / 'release-state'
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    install_fd = os.open(state_dir / 'install.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(install_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        offline = None
        with tempfile.TemporaryDirectory(prefix='.worktime-import-', dir=destination) as temporary:
            staging = Path(temporary)
            with tarfile.open(archive, 'r:gz') as source:
                members = source.getmembers()
                for member in members:
                    parts = Path(member.name).parts
                    if (not parts or Path(member.name).is_absolute() or '..' in parts or
                            member.issym() or member.islnk() or not (member.isfile() or member.isdir())):
                        raise RuntimeError('Unsafe offline archive entry')
                    if parts[0] not in ('scripts', 'image.tar', 'offline.json', 'docker-compose.yml', 'release-manifest.json'):
                        raise RuntimeError('Unexpected offline archive entry')
                source.extractall(staging, members=members)
            offline = json.loads((staging / 'offline.json').read_text())
            image_tar = staging / 'image.tar'
            if sha(image_tar) != offline['image_sha256']:
                raise RuntimeError('Offline image checksum mismatch')
            deploy_fd = os.open(state_dir / 'deployment.lock', os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(deploy_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Preflight (disk space, training gate, host baseline) before docker load or replacing files.
                required_free = image_tar.stat().st_size + 2 * 1024**3
                if shutil.disk_usage(destination).free < required_free:
                    raise RuntimeError('Insufficient disk space for offline image load and rollback headroom')
                check_training(destination)
                run('python3', str(staging / 'scripts/release.py'), 'check')
                run('docker', 'load', '-i', str(image_tar))
                if inspected(offline['image'])['RootFS']['Layers'] != offline['rootfs_diff_ids']:
                    raise RuntimeError('Imported image layer mismatch')
                for file in ('docker-compose.yml', 'release-manifest.json'):
                    shutil.copy2(staging / file, destination / file)
                shutil.copytree(staging / 'scripts', destination / 'scripts', dirs_exist_ok=True)
            finally:
                os.close(deploy_fd)
        helper = str(destination / 'scripts/release.py')
        configure_env = os.environ.copy()
        configure_env['WORKTIME_IMAGE'] = offline['image']
        run('python3', helper, 'configure', cwd=destination, env=configure_env)
        ident = 'offline-' + str(time.time_ns())
        run('python3', helper, 'prepare', ident, cwd=destination)
        compose_env = {k: v for k, v in os.environ.items() if not k.startswith('WORKTIME_')}
        project = os.environ.get('COMPOSE_PROJECT_NAME', 'jetson_worktime')
        try:
            run('docker', 'compose', '--env-file', '.env', '-p', project,
                'up', '-d', '--wait', '--wait-timeout', '240',
                cwd=destination, env=compose_env)
            run('python3', helper, 'commit', ident, cwd=destination)
        except BaseException:
            run('python3', helper, 'rollback', ident, cwd=destination)
            raise
    finally:
        os.close(install_fd)
    print('Offline deployment complete: ' + str(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'publish', 'export', 'install', 'manifest'])
    parser.add_argument('--image', default=IMAGE)
    parser.add_argument('--build-dir', help='Path to image/ build directory from the source repository')
    parser.add_argument('--resources')
    parser.add_argument('--output')
    parser.add_argument('--archive')
    parser.add_argument('--sha256')
    parser.add_argument('--destination', default='~/.sensecraft/deployments/jetson_worktime')
    args = parser.parse_args()
    if args.action == 'build':
        if not args.resources: parser.error('--resources is required')
        build(args.resources, args.image, args.build_dir)
    elif args.action == 'publish': publish(args.image)
    elif args.action == 'manifest': manifest(args.image, args.build_dir)
    elif args.action == 'export':
        if not args.output: parser.error('--output is required')
        export(args.output, args.image)
    else:
        if not args.archive: parser.error('--archive is required')
        install(args.archive, args.destination, args.sha256)


if __name__ == '__main__':
    main()
