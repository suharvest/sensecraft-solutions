"""User service: supervises durable local training jobs without owning live inference."""
from pathlib import Path
import signal
import sys
import threading
import os
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from jetson_worktime.studio import Studio
from jetson_worktime.training import TrainingQueue, process_start, boot_id
stop=threading.Event()
signal.signal(signal.SIGTERM,lambda *args:stop.set())
queue=TrainingQueue(Studio(ROOT))
# Prevent two supervisors from launching the same durable queue.
import fcntl
with (queue.store.data/'agent.lock').open('a') as guard:
    try: fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: sys.exit(0)
    # A power loss during spawn can leave preparing without a PID.
    for job in queue.store.list('job'):
        if (os.environ.get('WORKTIME_CONTAINER') == '1' and job['state'] in ('queued','preparing','running','validating','saving','stopping')) or (job['state'] in ('preparing','stopping') and not job.get('pid')):
            job.update(state='interrupted',stage='interrupted',error='interrupted');queue.store.put('job',job)
    while not stop.is_set():
        try:
            (queue.store.data/'agent-heartbeat').touch()
            queue.tick()
        except Exception:
            import traceback;traceback.print_exc()
        stop.wait(1)

    # Stop workers while their last complete checkpoints and GPU lease are recoverable.
    for job in queue.store.list('job'):
        pid = job.get('pid')
        if pid and job.get('boot_id') == boot_id() and process_start(pid) == job.get('pid_start'):
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        queue.recover()
        if not any(j['state'] in ('preparing','running','validating','saving','stopping') for j in queue.store.list('job')):
            break
        time.sleep(.25)
