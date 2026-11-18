from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import yaml

from jetson_worktime.behavior import SessionEngine
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.localization import reason


CONFIG = dict(image_size=[200, 200], regions={
    'station': [[0, 0], [199, 0], [199, 199], [0, 199]],
    'seat': [[20, 20], [110, 20], [110, 110], [20, 110]]},
    start_seconds=10, short_away_seconds=30, stop_absent_seconds=31)


def person(track=1, x=60, box=None):
    return dict(person_track_id=track, bbox_xyxy=box or [x-30, 5, x+30, 190],
        confidence=.9, valid=True,
        keypoints=[dict(x=x, y=70, confidence=.9) for _ in range(17)])


class OwnershipTests(unittest.TestCase):
    def observe(self, engine, t, people, **kwargs):
        return engine.observe_persons(t, deepcopy(people), 200, 200, **kwargs)

    def feed(self, engine, a, b, people, step=1):
        for i in range(round((b-a)/step)+1):
            self.observe(engine, round(a+i*step, 6), people)

    def working(self):
        engine = SessionEngine(CONFIG, run_id='unit-test')
        self.feed(engine, 0, 12, [person()])
        self.assertIsNotNone(engine.current)
        return engine

    def test_start_requires_one_continuous_track_and_restarts_for_another_person(self):
        e = SessionEngine(CONFIG)
        self.feed(e, 0, 9, [person(1)])
        self.feed(e, 10, 19, [person(2)])
        self.assertIsNone(e.current)
        self.observe(e, 20, [person(2)])
        self.assertEqual(e.current['start'], 10)
        self.assertEqual(e.current['ownership']['track_id'], 2)

    def test_no_id_and_multiple_people_cannot_start(self):
        for people in ([person(None)], [person(1), person(2, 145)]):
            with self.subTest(people=people):
                e = SessionEngine(CONFIG)
                self.feed(e, 0, 20, people)
                self.assertIsNone(e.current)

    def test_repeated_passers_do_not_reset_absence_or_resume_work(self):
        e = self.working()
        session = e.current['session_id']
        for t in range(13, 45):
            self.observe(e, t, [person(2+t%2, 145 if t%2 else 60)])
            if t < 44:
                self.assertEqual(e.absent_since, 13)
                self.assertNotEqual(e.raw, 'SEATED')
        self.assertEqual(len(e.completed), 1)
        self.assertEqual(e.completed[0]['session_id'], session)
        self.assertEqual(e.completed[0]['end'], 13)
        self.assertEqual(e.totals(e.completed[0])['work_seconds'], 13)

    def test_other_people_do_not_interrupt_a_visible_owner(self):
        e = self.working()
        self.feed(e, 13, 30, [person(1), person(2, 145)])
        self.assertEqual(e.snapshot(30)['state'], 'WORKING')
        self.assertEqual(e.snapshot(30)['work_seconds'], 30)
        self.assertEqual(e.ownership.ignored, [2])

    def test_owner_continuously_nearby_can_return_after_a_long_break(self):
        e = self.working()
        # Move within the permitted spatial continuity envelope.
        self.observe(e, 13, [person(1, 95)])
        self.feed(e, 14, 60, [person(1, 125)])
        self.assertEqual(e.snapshot(60)['state'], 'REST')
        self.assertIsNotNone(e.current)
        self.observe(e, 61, [person(1, 95)])
        self.assertEqual(e.snapshot(61)['state'], 'WORKING')

    def test_short_loss_same_id_bridges_but_long_loss_requires_confirmation(self):
        e = self.working()
        self.feed(e, 13, 14, [])
        self.observe(e, 15, [person(1)])
        self.assertEqual(e.snapshot(15)['work_seconds'], 15)
        self.feed(e, 16, 20, [])
        self.observe(e, 21, [person(1)])
        self.assertTrue(e.ownership.needs_confirmation)
        self.assertNotEqual(e.raw, 'SEATED')

    def test_changed_id_teleport_duplicate_id_and_crossing_are_conservative(self):
        for people in ([person(2)], [person(1, 145, [140, 60, 150, 80])],
                       [person(1), person(1, 145)], [person(1), person(2, 90)]):
            with self.subTest(people=people):
                e = self.working()
                self.observe(e, 13, people)
                self.assertNotEqual(e.raw, 'SEATED')
                self.assertTrue(e.ownership.needs_confirmation)

    def test_unknown_preserves_progress_and_excludes_unobserved_time(self):
        e = self.working()
        self.feed(e, 13, 20, [])
        self.observe(e, 21, [], blocked_reason=reason('reason.moved'))
        before = e.absent_elapsed
        self.observe(e, 22, [], blocked_reason=reason('reason.moved'))
        self.observe(e, 23, [], blocked_reason=reason('reason.moved'))
        self.assertEqual(e.absent_since, 13)
        self.assertEqual(e.absent_elapsed, before)
        self.feed(e, 24, 46, [])
        self.assertIsNotNone(e.current)
        self.observe(e, 47, [])
        self.assertEqual(e.completed[-1]['end'], 13)

    def test_health_tick_freezes_deadline_and_never_extends_work_forever(self):
        e = self.working()
        self.feed(e, 13, 20, [])
        e.tick(40)
        age = e.absent_elapsed
        e.tick(100)
        self.assertEqual(e.absent_since, 13)
        self.assertEqual(e.absent_elapsed, age)
        self.assertIsNotNone(e.current)
        self.assertEqual(e.snapshot(100)['state'], 'OBSERVATION_UNKNOWN')

    def test_unknown_time_is_not_reclassified_as_work_on_return(self):
        e = self.working()
        self.observe(e, 13, [person(1, 125)])
        self.observe(e, 14, [], blocked_reason=reason('reason.moved'))
        self.observe(e, 15, [], blocked_reason=reason('reason.moved'))
        self.observe(e, 16, [person(1)])
        self.assertEqual(e.snapshot(16)['unknown_seconds'], 2)
        self.assertEqual(e.snapshot(16)['work_seconds'], 14)

    def test_poor_keypoints_of_visible_owner_suspend_departure_confirmation(self):
        e = self.working()
        self.feed(e, 13, 17, [])
        uncertain = person()
        for point in uncertain['keypoints']:
            point.update(x=None, y=None, confidence=.1)
        self.feed(e, 18, 60, [uncertain])
        self.assertIsNotNone(e.current)
        self.assertEqual(e.absent_since, 13)
        self.assertLess(e.absent_elapsed, 6)
        self.assertEqual(e.raw, 'UNKNOWN')

    def test_status_never_serializes_private_source_credentials(self):
        e = SessionEngine({**CONFIG, 'camera_source':dict(url='private-source',password='secret')})
        serialized = json.dumps(e.snapshot(0))
        self.assertNotIn('private-source',serialized)
        self.assertNotIn('secret',serialized)

    def test_duplicate_sequence_late_results_and_old_stream_cannot_change_owner(self):
        e = self.working()
        self.observe(e, 13, [person(1)], sequence=100)
        before = e.ownership.identity()
        self.assertFalse(self.observe(e, 14, [person(2)], sequence=100))
        self.assertFalse(self.observe(e, 12, [person(2)]))
        self.assertFalse(self.observe(e, 14, [person(2)], now=20))
        self.assertEqual(before, e.ownership.identity())
        e.interrupt(20)
        self.assertFalse(self.observe(e, 21, [person(1)]))

    def test_new_stream_with_reset_timestamp_creates_a_new_binding(self):
        e = self.working()
        operator = e.ownership.operator_id
        self.observe(e, 0, [person(1)], stream='new', sequence=0)
        for t in range(1, 11):
            self.observe(e, t, [person(1)], stream='new', sequence=t)
        self.assertEqual(len(e.completed), 1)
        self.assertNotEqual(operator, e.ownership.operator_id)
        self.assertEqual(e.ownership.stream, 'new')

    def test_manual_confirmation_backdates_to_evidence_and_counts_each_interval_once(self):
        e = self.working()
        self.feed(e, 13, 17, [])
        self.feed(e, 18, 20, [person(2)])
        identity = e.ownership.operator_id
        e.confirm_return(e.persons[0], 19, 20, observation_id='selected')
        self.assertEqual(e.ownership.operator_id, identity)
        self.assertEqual(e.ownership.track_id, 2)
        self.assertEqual(e.snapshot(20)['work_seconds'], 20)
        segments = e.current['segments']
        self.assertTrue(all(a['end'] <= b['start'] for a,b in zip(segments, segments[1:])))
        with self.assertRaises(ValueError):
            e.confirm_return(e.persons[0], 19, 20, observation_id='selected')

    def test_frame_rate_does_not_change_timer_totals(self):
        result = []
        for step in (1, .2, .125):
            e = SessionEngine(CONFIG)
            self.feed(e, 0, 12, [person()], step)
            self.feed(e, 13, 45, [person(2)], step)
            result.append((e.completed[0]['end'], e.totals(e.completed[0])))
        self.assertEqual(result[0], result[1])
        self.assertEqual(result[0], result[2])

    def test_status_polling_does_not_commit_time_ahead_of_a_received_frame(self):
        e = self.working()
        self.assertAlmostEqual(e.snapshot(12.9)['work_seconds'],12.9)
        self.assertEqual(e.cursor,12)
        self.observe(e,12.5,[person(1,125)],now=12.95)
        self.feed(e,13,44,[person(1,125)])
        self.observe(e,45,[person(1,95)])
        self.assertAlmostEqual(e.snapshot(45)['work_seconds'],12.5)
        self.assertAlmostEqual(e.snapshot(45)['rest_seconds'],32.5)

    def test_inflight_frame_before_manual_confirmation_cannot_change_the_binding(self):
        e = self.working()
        self.feed(e,13,20,[person(2)])
        e.confirm_return(e.persons[0],19,20.5,observation_id='selected')
        self.assertFalse(self.observe(e,20.2,[person(1)],now=20.6))
        self.assertEqual(e.ownership.track_id,2)
        self.assertEqual(e.raw,'SEATED')

    def test_return_at_end_deadline_starts_a_new_confirmation_period(self):
        e=self.working()
        self.observe(e,13,[person(1,130)])
        self.feed(e,14,44,[person(1,199)])
        old_session=e.current['session_id']
        self.observe(e,45,[person(1,105)])
        self.assertEqual(e.completed[-1]['session_id'],old_session)
        self.assertEqual(e.completed[-1]['end'],14)
        self.assertIsNone(e.current)
        self.feed(e,46,55,[person(1,105)])
        self.assertEqual(e.current['start'],45)
        self.assertNotEqual(e.current['session_id'],old_session)


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'configs').mkdir()
        (self.root/'configs/behavior.yaml').write_text(yaml.safe_dump(CONFIG))
        self.service = BehaviorService(self.root, start_workers=False)
        self.addCleanup(self.service.close)
        self.origin = time.monotonic()-20
        self.engine = self.service.engine
        for t in range(13):
            self.engine.observe_persons(self.origin+t,[person()],200,200,'stream',sequence=t)
        for t in range(13,21):
            self.engine.observe_persons(self.origin+t,[person(2)],200,200,'stream',sequence=t)
        self.service.connected = True
        self.service.source_session = 'stream'
        self.service.persons = deepcopy(self.engine.persons)
        self.observation = dict(observation_id='fresh', config_revision=0,
            frame=dict(stream_session_id='stream',receive_monotonic_ns=str(int((self.origin+20)*1e9))),
            inference=dict(accepted=True),persons=deepcopy(self.engine.persons),camera_changed=False)
        self.service.observations.publish(self.observation,b'protected-jpeg')
        self.payload = dict(session_id=self.engine.current['session_id'], observation_id='fresh',
            stream_session_id='stream', config_revision=0, track_id=2)

    def test_confirmation_and_duplicate_rejection(self):
        with patch('jetson_worktime.behavior_service.time.monotonic', return_value=self.origin+20.1):
            status = self.service.action('confirm_return',self.payload)
            self.assertEqual(status['ownership']['track_id'],2)
            self.assertEqual(status['state'],'WORKING')
            with self.assertRaises(ValueError):
                self.service.action('confirm_return',self.payload)
        events = [json.loads(line) for line in (self.service.output/'events.jsonl').read_text().splitlines()]
        self.assertEqual(len([e for e in events if e['event']=='operator_return_confirmed']),1)

    def test_bad_reference_expiry_and_lost_candidate_rejected(self):
        cases = [dict(session_id='old'), dict(observation_id='evicted'),
                 dict(stream_session_id='old'),dict(config_revision=1),dict(config_revision=True),
                 dict(track_id=3),dict(track_id=None),dict(track_id=True)]
        original = self.engine.ownership.identity()
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.service.action('confirm_return',{**self.payload,**change})
            self.assertEqual(self.engine.ownership.identity(),original)
        with patch('jetson_worktime.behavior_service.time.monotonic',return_value=self.origin+22):
            with self.assertRaises(ValueError):self.service.action('confirm_return',self.payload)
        self.service.persons=[]
        with self.assertRaises(ValueError):self.service.action('confirm_return',self.payload)

    def test_ended_session_disconnected_or_moved_camera_rejected(self):
        self.service.camera_changed=True
        with self.assertRaises(ValueError):self.service.action('confirm_return',self.payload)
        self.service.camera_changed=False
        self.service.connected=False
        with self.assertRaises(ValueError):self.service.action('confirm_return',self.payload)
        self.service.connected=True
        self.engine.interrupt(self.origin+20)
        with self.assertRaises(ValueError):self.service.action('confirm_return',self.payload)

    def test_production_http_confirmation_status_codes(self):
        import ast
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        from urllib.parse import urlsplit
        from jetson_worktime.api import work_status
        from jetson_worktime.localization import LocalizedError
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'scripts/preview.py').read_text())
        definition=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        namespace=dict(BaseHTTPRequestHandler=BaseHTTPRequestHandler,json=json,
            behavior=self.service,work_status=work_status,LocalizedError=LocalizedError,urlsplit=urlsplit)
        from types import SimpleNamespace
        from jetson_worktime.studio_store import StudioError
        namespace['studio_http']=SimpleNamespace(handle=lambda *args:False)
        namespace['StudioError']=StudioError
        exec(compile(ast.Module(body=[definition],type_ignores=[]),'production_handler','exec'),namespace)
        server=ThreadingHTTPServer(('127.0.0.1',0),namespace['Handler'])
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        def post(body,headers=None):
            request=Request(f'http://127.0.0.1:{server.server_port}/api/v1/work/actions',
                data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**(headers or {})})
            try:
                with urlopen(request,timeout=3) as response:return response.status,json.load(response)
            except HTTPError as error:return error.code,json.load(error)
        try:
            self.assertEqual(post(dict(action='confirm_return',**{**self.payload,'session_id':'old'}))[0],409)
            self.assertEqual(post(dict(action='confirm_return',**self.payload),{'Origin':'http://invalid.example'})[0],403)
            code,status=post(dict(action='confirm_return',**self.payload))
            self.assertEqual(code,200)
            self.assertEqual(status['ownership']['track_id'],2)
            self.assertEqual(post(dict(action='confirm_return',**self.payload))[0],409)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
