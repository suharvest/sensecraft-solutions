"""Recovery ownership, immutable rollback, WAL-safe restore, and offline package regressions."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

RELEASE_SOURCE = (
    Path(__file__).resolve().parents[1]
    / 'solutions/workstation_monitoring/assets/docker/scripts/release.py'
)
release_spec = importlib.util.spec_from_file_location('worktime_release', RELEASE_SOURCE)
release = importlib.util.module_from_spec(release_spec)
release_spec.loader.exec_module(release)

PACKAGE_SOURCE = (
    Path(__file__).resolve().parents[1]
    / 'solutions/workstation_monitoring/assets/docker/scripts/package.py'
)
package_spec = importlib.util.spec_from_file_location('worktime_package', PACKAGE_SOURCE)
package = importlib.util.module_from_spec(package_spec)
package_spec.loader.exec_module(package)


def _create_offline_archive(directory: Path, image: str, layers: list[str]) -> tuple[Path, str]:
    staging = directory / 'archive_src'
    (staging / 'scripts').mkdir(parents=True)
    (staging / 'docker-compose.yml').write_text('name: jetson_worktime\nservices: {}\n', encoding='utf-8')
    (staging / 'release-manifest.json').write_text(
        json.dumps({'schema_version': 1, 'image': image, 'rootfs_diff_ids': layers}) + '\n',
        encoding='utf-8',
    )
    (staging / 'scripts/release.py').write_text('# stub release helper\n', encoding='utf-8')
    image_bytes = b'fake-oci-image-tar-payload'
    (staging / 'image.tar').write_bytes(image_bytes)
    image_sha = hashlib.sha256(image_bytes).hexdigest()
    (staging / 'offline.json').write_text(
        json.dumps({'image': image, 'image_sha256': image_sha, 'rootfs_diff_ids': layers}),
        encoding='utf-8',
    )
    archive = directory / 'offline.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for entry in sorted(staging.iterdir()):
            tar.add(entry, arcname=entry.name)
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    Path(str(archive) + '.sha256').write_text(f'{archive_sha}  {archive.name}\n', encoding='utf-8')
    return archive, archive_sha


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'release-state'
        self.data = self.root / 'persistent'
        self.patches = [
            patch.object(release, 'ROOT', self.root),
            patch.object(release, 'STATE', self.state),
            patch.object(release, 'PERSISTENT', self.data),
            patch.object(release, 'JOURNAL', self.state / 'release.json'),
        ]
        for item in self.patches:
            item.start()
        for name in ('configs', 'data', 'outputs/behavior', 'logs'):
            (self.data / name).mkdir(parents=True, exist_ok=True)
        self.state.mkdir()
        (self.root / '.env').write_text('WORKTIME_IMAGE="candidate:tag"\nWORKTIME_PORT="8088"\n')
        (self.root / 'docker-compose.yml').write_text('services: {}\n')

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_late_failure_callback_cannot_undo_committed_release(self):
        release.save(release.JOURNAL, {'deployment_id': 'new', 'phase': 'committed'})
        with patch.object(release, 'compose') as compose:
            release.rollback('new')
            release.rollback('old')
            compose.assert_not_called()
        self.assertEqual(release.journal()['phase'], 'committed')

    def test_commit_pins_old_image_by_content_id(self):
        release.save(release.JOURNAL, {'deployment_id': 'new', 'phase': 'switching'})
        (self.root / 'releases/new').mkdir(parents=True)
        image_id = 'sha256:' + 'a' * 64
        with patch.object(release, 'ready'), patch.object(
            release, 'command', return_value=json.dumps([{'Id': image_id}])
        ):
            release.commit('new')
        self.assertEqual(release.environment(self.state / 'active.env')['WORKTIME_IMAGE'], image_id)
        self.assertEqual(release.journal()['phase'], 'committed')
        self.assertEqual((self.state / 'active.env').stat().st_mode & 0o777, 0o600)

    def test_restore_removes_new_configuration_and_restores_sqlite(self):
        backup = self.root / 'releases/new'
        (backup / 'configs').mkdir(parents=True)
        (backup / 'configs/camera.json').write_text('{"safe":true}')
        (self.data / 'configs/added-by-candidate.json').write_text('{}')
        with sqlite3.connect(backup / 'worktime.sqlite') as db:
            db.execute('CREATE TABLE marker(value TEXT)')
            db.execute("INSERT INTO marker VALUES('original')")
        database = self.data / 'data/worktime.sqlite'
        database.write_bytes(b'candidate')
        Path(str(database) + '-wal').write_bytes(b'stale')
        Path(str(database) + '-shm').write_bytes(b'stale')
        (backup / 'previous-compose.yml').write_text('services: {}')
        (backup / 'previous.env').write_text('WORKTIME_IMAGE="sha256:old-id"\n')
        release.save(
            release.JOURNAL,
            {
                'deployment_id': 'new',
                'phase': 'switching',
                'backup': str(backup),
                'backup_complete': True,
                'previous': {'deployment_id': 'old', 'image_id': 'sha256:old-id'},
            },
        )
        with patch.object(release, 'compose') as compose:
            release.rollback('new')
            calls = compose.call_count
            release.rollback('new')
            self.assertEqual(compose.call_count, calls)
        self.assertFalse((self.data / 'configs/added-by-candidate.json').exists())
        self.assertTrue((self.data / 'configs/camera.json').exists())
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute('SELECT value FROM marker').fetchone()[0], 'original')
        self.assertFalse(Path(str(database) + '-wal').exists())
        self.assertEqual(release.environment(self.state / 'active.env')['WORKTIME_IMAGE'], 'sha256:old-id')
        self.assertEqual(release.journal()['phase'], 'rolled_back')

    def test_compose_recovery_ignores_new_shell_image_override(self):
        old = self.state / 'active.env'
        old.write_text('WORKTIME_IMAGE="sha256:original"\n')
        with patch.dict(os.environ, {'WORKTIME_IMAGE': 'candidate:latest'}), patch.object(
            release, 'command'
        ) as command:
            release.compose('up', '-d', env_file=old)
            self.assertEqual(command.call_args.kwargs['env']['WORKTIME_IMAGE'], 'sha256:original')
            self.assertIn('--project-directory', command.call_args.args)

    def test_configure_interrupted_recovery_preserves_new_root_compose(self):
        new_compose = 'name: jetson_worktime\nservices:\n  web:\n    image: new-candidate\n'
        old_compose = 'name: jetson_worktime\nservices:\n  web:\n    image: old-stable\n'
        (self.root / 'docker-compose.yml').write_text(new_compose)

        backup = self.root / 'releases/interrupted-1'
        (backup / 'configs').mkdir(parents=True)
        (backup / 'configs/camera.json').write_text('{"restored":true}')
        (backup / 'previous-compose.yml').write_text(old_compose)
        (backup / 'previous.env').write_text('WORKTIME_IMAGE="sha256:old-stable"\n')
        release.save(
            release.JOURNAL,
            {
                'deployment_id': 'interrupted-1',
                'phase': 'switching',
                'backup': str(backup),
                'backup_complete': True,
                'previous': {'deployment_id': 'old-1', 'image_id': 'sha256:old-stable'},
            },
        )

        with patch.object(release, 'compose') as compose, patch.dict(
            os.environ, {'WORKTIME_PORT': '8090', 'WORKTIME_MEDIA_PORT_OFFSET': '100', 'WORKTIME_ENCODER': 'x264'}
        ):
            release.configure()

        self.assertEqual((self.root / 'docker-compose.yml').read_text(), new_compose)
        self.assertEqual((self.state / 'active-compose.yml').read_text(), old_compose)
        self.assertEqual(release.environment(self.state / 'active.env')['WORKTIME_IMAGE'], 'sha256:old-stable')
        new_env = release.environment(self.root / '.env')
        self.assertEqual(new_env['WORKTIME_PORT'], '8090')
        self.assertEqual(new_env['WORKTIME_MEDIA_PORT_OFFSET'], '100')
        self.assertEqual(new_env['WORKTIME_ENCODER'], 'x264')
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)
        self.assertEqual(release.journal()['phase'], 'rolled_back')
        self.assertTrue(compose.called)

    def test_configure_rejects_invalid_ports_and_encoder_without_touching_env(self):
        sentinel = 'WORKTIME_PORT="8088"\n'
        (self.root / '.env').write_text(sentinel)

        for bad_env in (
            {'WORKTIME_PORT': '80'},
            {'WORKTIME_PORT': '8189'},
            {'WORKTIME_PORT': 'not-a-number'},
            {'WORKTIME_MEDIA_PORT_OFFSET': '-1'},
            {'WORKTIME_ENCODER': 'invalid-codec'},
        ):
            with self.subTest(bad_env=bad_env), patch.dict(os.environ, bad_env):
                with self.assertRaises((RuntimeError, ValueError)):
                    release.configure()
                self.assertEqual((self.root / '.env').read_text(), sentinel)

    def test_prepare_and_commit_auto_deployment_id_flow(self):
        release.configure()
        layers = ['sha256:' + '1' * 64]
        (self.root / 'release-manifest.json').write_text(
            json.dumps({'schema_version': 1, 'rootfs_diff_ids': layers}) + '\n'
        )
        (self.data / 'configs/site.json').write_text('{"ok":true}')
        with sqlite3.connect(self.data / 'data/worktime.sqlite') as db:
            db.execute('CREATE TABLE objects(kind TEXT, value TEXT)')
            db.execute("INSERT INTO objects VALUES('job', '{\"state\":\"completed\"}')")
        image_id = 'sha256:' + 'b' * 64
        inspect_payload = json.dumps(
            [{'Id': image_id, 'Architecture': 'arm64', 'Os': 'linux', 'RootFS': {'Layers': layers}}]
        )
        sock_opts = []

        class DummySocket:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def setsockopt(self, *args):
                sock_opts.append(args)

            def bind(self, *args):
                pass

        with patch.object(release, 'check_host'), patch.object(
            release, 'command', side_effect=[inspect_payload, '', inspect_payload]
        ), patch.object(release.socket, 'socket', return_value=DummySocket()), patch.object(
            release.subprocess, 'Popen'
        ), patch.object(
            release.time, 'sleep'
        ), patch.object(
            release, 'ready'
        ):
            release.prepare()
            state_after_prepare = release.journal()
            ident = state_after_prepare['deployment_id']
            self.assertRegex(ident, r'^deploy-\d+$')
            self.assertEqual(state_after_prepare['phase'], 'switching')
            self.assertTrue(state_after_prepare['backup_complete'])

            release.commit()

        state_after_commit = release.journal()
        self.assertEqual(state_after_commit['deployment_id'], ident)
        self.assertEqual(state_after_commit['phase'], 'committed')
        self.assertTrue(any(opt[1] == release.socket.SO_REUSEADDR and opt[2] == 1 for opt in sock_opts))
        active = json.loads((self.state / 'active.json').read_text())
        self.assertEqual(active['deployment_id'], ident)
        self.assertEqual(active['image_id'], image_id)

    def test_rollback_tolerates_compose_stop_failure_and_atomic_configs_error(self):
        backup = self.root / 'releases/fail-1'
        (backup / 'configs').mkdir(parents=True)
        (backup / 'configs/restored.json').write_text('{"v":1}')
        (self.data / 'configs/live.json').write_text('{"v":2}')
        release.save(
            release.JOURNAL,
            {
                'deployment_id': 'fail-1',
                'phase': 'switching',
                'backup': str(backup),
                'backup_complete': True,
                'previous': None,
            },
        )
        with patch.object(
            release, 'compose', side_effect=subprocess.CalledProcessError(1, ['docker', 'compose'])
        ):
            release.rollback('fail-1')
        self.assertTrue((self.data / 'configs/restored.json').exists())
        self.assertFalse((self.data / 'configs/live.json').exists())
        self.assertEqual(release.journal()['phase'], 'rolled_back')

        # Simulate disk-full failure while staging configs restore: live configs must survive.
        (self.data / 'configs/must-survive.json').write_text('{"keep":true}')
        release.save(
            release.JOURNAL,
            {
                'deployment_id': 'fail-2',
                'phase': 'switching',
                'backup': str(backup),
                'backup_complete': True,
                'previous': None,
            },
        )
        with patch.object(release, 'compose'), patch.object(
            shutil, 'copytree', side_effect=OSError('No space left on device')
        ):
            with self.assertRaises(OSError):
                release.rollback('fail-2')
        self.assertTrue((self.data / 'configs/must-survive.json').exists())

    def test_prepare_pulls_missing_image_only_when_enabled(self):
        release.configure()
        layers = ['sha256:' + '2' * 64]
        (self.root / 'release-manifest.json').write_text(
            json.dumps({'schema_version': 1, 'rootfs_diff_ids': layers}) + '\n'
        )
        image_id = 'sha256:' + 'f' * 64
        inspect_payload = json.dumps(
            [{'Id': image_id, 'Architecture': 'arm64', 'Os': 'linux', 'RootFS': {'Layers': layers}}]
        )
        missing_error = subprocess.CalledProcessError(1, ['docker', 'image', 'inspect', release.IMAGE])

        class DummySocket:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def setsockopt(self, *args):
                pass

            def bind(self, *args):
                pass

        with patch.object(release, 'check_host'), patch.object(
            release, 'command', side_effect=missing_error
        ), patch.object(release.subprocess, 'check_call') as check_call:
            with self.assertRaises(subprocess.CalledProcessError):
                release.prepare('no-pull-1')
            check_call.assert_not_called()

        with patch.object(release, 'check_host'), patch.object(
            release, 'command', side_effect=[missing_error, inspect_payload, '']
        ) as command_mock, patch.object(release.subprocess, 'check_call') as check_call, patch.object(
            release.socket, 'socket', return_value=DummySocket()
        ), patch.object(
            release.subprocess, 'Popen'
        ), patch.object(
            release.time, 'sleep'
        ):
            release.prepare('pull-1', pull_if_missing=True)

        check_call.assert_called_once_with(('docker', 'pull', release.IMAGE), cwd=self.root)
        self.assertEqual(command_mock.call_count, 3)
        self.assertEqual(release.journal()['phase'], 'switching')
        self.assertEqual(release.journal()['deployment_id'], 'pull-1')


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_resolve_build_dir_missing_reports_clear_hint(self):
        with self.assertRaises(RuntimeError) as ctx:
            package.resolve_build_dir(self.base / 'missing-image-dir')
        self.assertIn('--build-dir', str(ctx.exception))

    def test_install_passes_worktime_image_and_preflights_before_docker_load(self):
        layers = ['sha256:' + 'c' * 64]
        custom_image = 'custom-registry/jetson-worktime:offline-test'
        archive, checksum = _create_offline_archive(self.base, custom_image, layers)
        destination = self.base / 'dest'
        recorded_calls = []

        def fake_run(*args, capture=False, cwd=package.ROOT, env=None):
            recorded_calls.append((args, cwd, env))
            return ''

        fake_inspect = {'Id': 'sha256:' + 'd' * 64, 'RootFS': {'Layers': layers}}
        with patch.object(package, 'run', side_effect=fake_run), patch.object(
            package, 'inspected', return_value=fake_inspect
        ), patch.dict(os.environ, {'WORKTIME_IMAGE': 'stale-host-override:bad', 'WORKTIME_PORT': '9999'}):
            package.install(archive, destination, checksum)

        cmd_names = []
        configure_call = None
        compose_up_call = None
        for args, cwd, env in recorded_calls:
            if len(args) >= 3 and args[0] == 'python3' and args[2] == 'check':
                cmd_names.append('check')
            elif len(args) >= 2 and args[0] == 'docker' and args[1] == 'load':
                cmd_names.append('docker_load')
            elif len(args) >= 3 and args[0] == 'python3' and args[2] == 'configure':
                cmd_names.append('configure')
                configure_call = (args, cwd, env)
            elif len(args) >= 3 and args[0] == 'python3' and args[2] == 'prepare':
                cmd_names.append('prepare')
            elif len(args) >= 2 and args[0] == 'docker' and args[1] == 'compose':
                cmd_names.append('compose_up')
                compose_up_call = (args, cwd, env)
            elif len(args) >= 3 and args[0] == 'python3' and args[2] == 'commit':
                cmd_names.append('commit')

        self.assertEqual(cmd_names, ['check', 'docker_load', 'configure', 'prepare', 'compose_up', 'commit'])
        self.assertIsNotNone(configure_call)
        self.assertEqual(configure_call[2]['WORKTIME_IMAGE'], custom_image)
        self.assertIsNotNone(compose_up_call)
        compose_args, _, compose_env = compose_up_call
        self.assertIn('--env-file', compose_args)
        self.assertIn('.env', compose_args)
        self.assertIn('-p', compose_args)
        self.assertIn('jetson_worktime', compose_args)
        self.assertIn('240', compose_args)
        self.assertFalse(any(k.startswith('WORKTIME_') for k in compose_env))

    def test_install_blocks_before_docker_load_when_training_active(self):
        layers = ['sha256:' + 'e' * 64]
        archive, checksum = _create_offline_archive(self.base, 'custom/repo:tag', layers)
        destination = self.base / 'dest'
        (destination / 'persistent/data').mkdir(parents=True)
        with sqlite3.connect(destination / 'persistent/data/worktime.sqlite') as db:
            db.execute('CREATE TABLE objects(kind TEXT, value TEXT)')
            db.execute("INSERT INTO objects VALUES('job', '{\"state\":\"running\"}')")

        with patch.object(package, 'run') as mock_run:
            with self.assertRaises(RuntimeError) as ctx:
                package.install(archive, destination, checksum)
            self.assertIn('training job', str(ctx.exception))
            mock_run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
