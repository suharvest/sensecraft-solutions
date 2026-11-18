from copy import deepcopy
import json
from pathlib import Path
import runpy
import tempfile
import unittest

from jetson_worktime.behavior import SessionEngine
from test_ownership import CONFIG, person


class OwnershipReplayTests(unittest.TestCase):
    def test_live_and_replay_with_manual_return_have_identical_totals(self):
        replay = runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/replay_behavior.py'))['replay']
        engine = SessionEngine(CONFIG)
        records = []
        for t in range(26):
            people = [person(1 if t < 13 else 2)]
            engine.observe_persons(t, people, 200, 200, 'stream', sequence=t)
            records.append(dict(observation_id=str(t), persons=deepcopy(people), width=200,
                height=200, session_id='stream',receive_sequence=t,receive_monotonic_ns=t*10**9))
            if t == 20:
                engine.confirm_return(engine.persons[0],19,20.1,observation_id='19')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observations=root/'observations.jsonl'
            observations.write_text(''.join(json.dumps(row)+'\n' for row in records))
            events=root/'events.jsonl'
            events.write_text(''.join(json.dumps(row)+'\n' for row in engine.events))
            replayed=replay(observations,CONFIG,root/'replayed.jsonl',events)
            for key in ('work_seconds','rest_seconds','pending_seconds','unknown_seconds'):
                self.assertEqual(engine.snapshot(25)[key],replayed.snapshot(25)[key])
            self.assertEqual(replayed.ownership.track_id,2)

    def test_missing_track_evidence_is_explicitly_unverified(self):
        replay = runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/replay_behavior.py'))['replay']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'legacy.jsonl'
            source.write_text(json.dumps(dict(persons=[person(None)],width=200,height=200,
                receive_monotonic_ns=0,session_id='stream'))+'\n')
            replay(source,CONFIG,root/'replayed.jsonl')
            record=json.loads((root/'replayed.jsonl').read_text())
            self.assertEqual(record['ownership_verification'],'UNVERIFIED')
            self.assertFalse(record['status']['active'])
