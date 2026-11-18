import json, torch, torchvision, numpy as np
from pathlib import Path
assert torch.cuda.is_available(), 'CUDA unavailable'
x = torch.arange(16, dtype=torch.float32, device='cuda').reshape(4, 4)
y = x @ x.T
torch.cuda.synchronize()
a = x.cpu().numpy()
assert np.isfinite(y.cpu().numpy()).all() and torch.allclose(y.cpu(), torch.from_numpy(a) @ torch.from_numpy(a).T)
boxes = torch.tensor([[0,0,10,10],[1,1,9,9],[20,20,30,30]],dtype=torch.float32,device='cuda')
scores = torch.tensor([0.9,0.8,0.7],device='cuda')
keep = torchvision.ops.nms(boxes,scores,0.5)
torch.cuda.synchronize()
assert keep.device.type == 'cuda' and keep.cpu().tolist() == [0,2]
report={'status':'PASS','torch':torch.__version__,'torch_path':torch.__file__,'torchvision':torchvision.__version__,'torchvision_path':torchvision.__file__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'nms':keep.cpu().tolist()}
Path('reports').mkdir(exist_ok=True)
Path('reports/gpu-smoke.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
