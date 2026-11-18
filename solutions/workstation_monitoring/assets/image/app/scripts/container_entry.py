"""Container initialization and foreground service entrypoints."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def initialize():
    uid = int(os.environ.get('WORKTIME_UID', '1000'))
    gid = int(os.environ.get('WORKTIME_GID', '1000'))
    for name in ('data', 'configs', 'outputs', 'logs'):
        directory = ROOT / name
        directory.mkdir(exist_ok=True, mode=0o700)
        if os.geteuid() == 0:
            os.chown(directory, uid, gid)
    with (ROOT / 'data/init.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for source in (ROOT / 'defaults').glob('*'):
            target = ROOT / 'configs' / source.name
            if not target.exists():
                shutil.copyfile(source, target)
                target.chmod(0o600)
                if os.geteuid() == 0:
                    os.chown(target, uid, gid)
        if os.geteuid() == 0:
            os.chown(ROOT / 'data/init.lock', uid, gid)
            os.setgid(gid)
            os.setuid(uid)
        from jetson_worktime.studio import Studio
        studio = Studio(ROOT)
        catalog = json.loads((ROOT / 'configs/model-catalog.json').read_text())
        for name, item in catalog.items():
            existing = [value for value in studio.store.list('model')
                        if value.get('source') == 'official' and value.get('sha256') == item['sha256']]
            if existing:
                continue
            source = ROOT / 'pretrained' / (name + '.pt')
            if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
                raise RuntimeError('Pretrained model checksum failed: ' + name)
            scratch = ROOT / 'data' / (name + '.pt')
            shutil.copyfile(source, scratch)
            try:
                studio.import_model(scratch, 'material', name.replace('yolo', 'YOLO'), 'official')
            finally:
                scratch.unlink(missing_ok=True)
        (ROOT / 'data/initialized').write_text(str(time.time()))


def gpu_check():
    import torch
    import torchvision
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    x = torch.arange(16, device='cuda', dtype=torch.float32).reshape(4, 4)
    result = x @ x.T
    torch.cuda.synchronize()
    if not torch.allclose(result.cpu(), x.cpu() @ x.cpu().T):
        raise RuntimeError('GPU matrix result mismatch')
    boxes = torch.tensor([[0, 0, 10, 10], [1, 1, 9, 9]], device='cuda', dtype=torch.float32)
    scores = torch.tensor([.9, .8], device='cuda')
    if torchvision.ops.nms(boxes, scores, .5).cpu().tolist() != [0]:
        raise RuntimeError('GPU NMS result mismatch')
    print(json.dumps({'status': 'PASS', 'torch': torch.__version__,
                      'torchvision': torchvision.__version__, 'cuda': torch.version.cuda}))


def main():
    mode = sys.argv[1]
    if mode == 'init':
        initialize()
        return
    if mode == 'gpu-check':
        gpu_check()
        return
    if mode == 'web':
        marker = ROOT / 'logs/gpu-startup.json'
        marker.unlink(missing_ok=True)
        result = subprocess.check_output([sys.executable, __file__, 'gpu-check'], text=True)
        json.loads(result)
        marker.write_text(result)
        entry = 'preview.py'
    elif mode == 'trainer':
        entry = 'studio_agent.py'
    else:
        raise ValueError('Unknown container service')
    os.chdir(ROOT)
    os.execv(sys.executable, [sys.executable, '-u', str(ROOT / 'scripts' / entry)])


if __name__ == '__main__':
    main()
