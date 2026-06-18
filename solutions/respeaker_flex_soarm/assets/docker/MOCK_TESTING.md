# Mock Testing (x86 / no SO-ARM hardware)

For dry-running the voice pipeline without a Jetson and without the
SO-ARM hardware, you can stub out `robot_arm.RobotArm` with a fake
that no-ops `connect/disconnect/execute_action` and returns canned
data from `get_cached_observation`. This lets you validate the Groq
link (wake → STT → LLM → TTS) on a developer laptop with just the
reSpeaker plugged in.

Suggested approach (do NOT commit this stub — it's a dev convenience):

```python
# robot_arm_mock.py — drop next to robot_arm.py and import it
# instead of robot_arm in pipeline.py.
class MockRobotArm:
    def __init__(self, *a, **kw):
        self._port = "MOCK"
    def connect(self): print("[MOCK] connect")
    def disconnect(self): print("[MOCK] disconnect")
    def update_cache(self): return {}
    def get_cached_observation(self):
        return {"shoulder_pan.pos": 0.0, "gripper.pos": 0.0}
    def observation_features(self):
        return {"shoulder_pan.pos": {"type": "float"},
                "gripper.pos": {"type": "float"}}
    def execute_action(self, name, actions_map):
        print(f"[MOCK] execute_action({name})"); return True
```

Run order:
1. Plug in reSpeaker + a USB speaker on a Linux x86 box
2. Build a CPU-only image variant (drop `nvcr.io/...` base, use
   `python:3.11-slim-bookworm` + remove `lerobot[feetech]` from
   requirements.txt)
3. Run `docker compose up`, talk to it
4. Confirm `curl http://localhost:8765/observation` returns the mock dict

This is for the engineering loop only. Real verification happens on
Jetson with a real SO-ARM connected.
