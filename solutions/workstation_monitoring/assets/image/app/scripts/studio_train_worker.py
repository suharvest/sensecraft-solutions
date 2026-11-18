"""One persistent training process per job; independent of browser and web server."""
import os
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ['YOLO_AUTOINSTALL']='False'
def stop(*args): raise KeyboardInterrupt()
signal.signal(signal.SIGTERM,stop)
from jetson_worktime.training import run_worker
run_worker(ROOT,sys.argv[1])
