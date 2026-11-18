"""Recovery ownership, immutable rollback and WAL-safe restore regressions."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'solutions/workstation_monitoring/assets/docker/scripts/release.py'
spec = importlib.util.spec_from_file_location('worktime_release', SOURCE)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'release-state'
        self.data = self.root / 'persistent'
        self.patches = [patch.object(release, 'ROOT', self.root), patch.object(release, 'STATE', self.state),
                        patch.object(release, 'PERSISTENT', self.data),
                        patch.object(release, 'JOURNAL', self.state / 'release.json')]
        for item in self.patches: item.start()
        for name in ('configs', 'data', 'outputs/behavior', 'logs'):
            (self.data / name).mkdir(parents=True, exist_ok=True)
        self.state.mkdir()
        (self.root / '.env').write_text('WORKTIME_IMAGE="candidate:tag"\nWORKTIME_PORT="8088"\n')
        (self.root / 'docker-compose.yml').write_text('services: {}\n')

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
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
        image_id = 'sha256:' + 'a'*64
        with patch.object(release, 'ready'), patch.object(release, 'command', return_value=json.dumps([{'Id': image_id}])):
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
        release.save(release.JOURNAL, {'deployment_id': 'new', 'phase': 'switching',
                                     'backup': str(backup), 'backup_complete': True,
                                     'previous': {'deployment_id': 'old', 'image_id': 'sha256:old-id'}})
        with patch.object(release, 'compose') as compose:
            release.rollback('new')
            calls = compose.call_count
            release.rollback('new')
            self.assertEqual(compose.call_count, calls)
        self.assertFalse((self.data / 'configs/added-by-candidate.json').exists())
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute('SELECT value FROM marker').fetchone()[0], 'original')
        self.assertFalse(Path(str(database) + '-wal').exists())
        self.assertEqual(release.environment(self.state / 'active.env')['WORKTIME_IMAGE'], 'sha256:old-id')
        self.assertEqual(release.journal()['phase'], 'rolled_back')

    def test_compose_recovery_ignores_new_shell_image_override(self):
        old = self.state / 'active.env'
        old.write_text('WORKTIME_IMAGE="sha256:original"\n')
        with patch.dict(os.environ, {'WORKTIME_IMAGE': 'candidate:latest'}), patch.object(release, 'command') as command:
            release.compose('up', '-d', env_file=old)
            self.assertEqual(command.call_args.kwargs['env']['WORKTIME_IMAGE'], 'sha256:original')
            self.assertIn('--project-directory', command.call_args.args)


if __name__ == '__main__': unittest.main()
