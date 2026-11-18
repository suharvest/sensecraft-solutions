"""Create auditable, temporally grouped full-frame and workbench datasets.

Requires Pillow, numpy and tesseract. Never changes the supplied VOC dataset.
Every derivative of one capture minute stays in the same split. Failed clock
reads go to training only. Metrics describe this camera, not unseen workplaces.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import random
import re
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageOps
import numpy as np

NAMES = ['box', 'not_packed', 'packed', 'part']
CLOCK_CORRECTIONS = {'1a89b97091d444f3b8c4628e0bc29e4c':'22:59:18',
                     '2bbacaa79dbd4162996b4a31e2e9a056':'23:02:24',
                     'b57e3df1504d408a8ab3da4dacde3258':'23:04:28'}


def read_sample(xml, images):
    root = ET.parse(xml).getroot()
    path = images / (xml.stem + '.jpg')
    image = Image.open(path).convert('RGB')
    boxes = []
    for obj in root.findall('object'):
        name = obj.findtext('name')
        if name not in NAMES:
            raise ValueError(f'Unknown class {name}: {xml}')
        box = [int(obj.findtext('bndbox/' + k)) for k in ('xmin', 'ymin', 'xmax', 'ymax')]
        if not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
            raise ValueError(f'Invalid box: {xml}')
        boxes.append([NAMES.index(name), *box])
    crop = ImageOps.grayscale(image.crop((300, 62, 512, 104))).resize((848, 168))
    crop = ImageOps.expand(ImageOps.invert(crop.point(lambda p:255 if p>210 else 0)),border=20,fill='white')
    buf = io.BytesIO(); crop.save(buf, format='PNG')
    result = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '7', '-c',
                             'tessedit_char_whitelist=0123456789-: '], input=buf.getvalue(), capture_output=True)
    clock_text=CLOCK_CORRECTIONS.get(xml.stem,result.stdout.decode().strip())
    clock = re.search(r'([012]\d):([0-5]\d):([0-5]\d)',clock_text)
    if clock and int(clock[1])>23:clock=None
    seconds = sum(int(v) * m for v, m in zip(clock.groups(), (3600, 60, 1))) if clock else None
    return dict(id=xml.stem, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size=list(image.size), boxes=boxes, clock=clock_text, clock_ocr=result.stdout.decode().strip(), seconds=seconds,
                group=f'minute-{seconds // 60}' if seconds is not None else 'unread-clock')


def write_image(out, variant, split, item, name, crop):
    image = Image.open(item['path']).convert('RGB')
    x1, y1, x2, y2 = crop; w, h = x2-x1, y2-y1
    labels = []
    for cls, a, b, c, d in item['boxes']:
        a, b, c, d = max(a, x1), max(b, y1), min(c, x2), min(d, y2)
        if c > a and d > b:
            labels.append(f'{cls} {((a+c)/2-x1)/w:.8f} {((b+d)/2-y1)/h:.8f} {(c-a)/w:.8f} {(d-b)/h:.8f}')
    target = out / variant
    for kind in ('images', 'labels'):
        (target / kind / split).mkdir(parents=True, exist_ok=True)
    image.crop(crop).save(target / 'images' / split / (name+'.jpg'), quality=95)
    (target / 'labels' / split / (name+'.txt')).write_text('\n'.join(labels)+'\n' if labels else '')
    return dict(name=name, source_id=item['id'], split=split, crop=crop, objects=len(labels), group=item['group'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output
    if (out/'manifest.json').exists(): raise SystemExit('Output already exists; keep the frozen split intact.')
    out.mkdir(parents=True,exist_ok=True)
    files=sorted((args.input/'detect_packed').glob('*.xml'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        items=list(pool.map(lambda p:read_sample(p,args.input/'images'),files))
    groups=defaultdict(list)
    for item in items: groups[item['group']].append(item)
    keys=sorted(k for k in groups if k!='unread-clock');random.Random(42).shuffle(keys)
    if len(keys)<5: raise SystemExit('Too few independent time groups; inspect clock reads.')
    # Whole groups, deterministic allocation. Do not shuffle neighboring frames.
    splits={}; counts=Counter()
    for key in sorted(keys,key=lambda k:-len(groups[k])):
        target=min(('train','val','test'),key=lambda s:counts[s]/({'train':.70,'val':.15,'test':.15}[s]*len(items)))
        splits[key]=target;counts[target]+=len(groups[key])
    splits['unread-clock']='train'
    # Dataset crop is fixed, includes every annotated material with context.
    all_boxes=[b for item in items for b in item['boxes']]
    bounds=[max(0,min(b[1] for b in all_boxes)-160), max(0,min(b[2] for b in all_boxes)-160),
            min(2560,max(b[3] for b in all_boxes)+160), min(1440,max(b[4] for b in all_boxes)+160)]
    derivatives=[]
    for item in items:
        split=splits[item['group']];item['split']=split
        derivatives.append(write_image(out,'full',split,item,item['id'],[0,0,*item['size']]))
        derivatives.append(write_image(out,'crop',split,item,item['id'],bounds))
        if split=='train' and int(item['sha256'][:8],16)%3==0:
            # Include known contextual distractors. Never create an empty label
            # for a crop that intersects a supplied annotation.
            for j,rect in enumerate(([0,360,720,1080],[0,0,720,600],[1720,720,2560,1440])):
                if not any(min(b[3],rect[2])>max(b[1],rect[0]) and min(b[4],rect[3])>max(b[2],rect[1]) for b in item['boxes']):
                    derivatives.append(write_image(out,'crop',split,item,item['id']+f'-background-{j}',list(rect)))
                    break
    for variant in ('full','crop'):
        (out/variant/'data.yaml').write_text('path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n'+''.join(f'  {i}: {n}\n' for i,n in enumerate(NAMES)))
    (out/'manifest.json').write_text(json.dumps(dict(seed=42,method='whole capture-minute groups',crop=bounds,groups=splits,
        originals=items,derivatives=derivatives,limitations=['One camera and one scene; no external-scene accuracy claim.',
        'Background crops inherit source split; not independent empty-scene recordings.']),indent=2))
    # Review all labels at useful scale, and all chosen background crops.
    for page,start in enumerate(range(0,len(items),20)):
        sheet=Image.new('RGB',(1600,1400),'#102027');d=ImageDraw.Draw(sheet)
        for index,item in enumerate(items[start:start+20]):
            im=Image.open(item['path']).convert('RGB');dr=ImageDraw.Draw(im)
            for cls,a,b,c,e in item['boxes']:
                color=['#ffa500','#ff55dd','#88ee22','#22ccff'][cls]
                dr.rectangle((a,b,c,e),outline=color,width=5);dr.text((a,b-15),NAMES[cls],fill=color,stroke_width=1)
            im=im.crop(bounds);im.thumbnail((400,250));x=index%4*400;y=index//4*280;sheet.paste(im,(x,y))
            d.text((x+4,y+253),f"{start+index}: {item['id'][:8]} {item['split']} {item['clock']}",fill='white')
        sheet.save(out/f'label-review-{page+1}.jpg')
    summary=dict(images=len(items),objects=dict(Counter(NAMES[b[0]] for i in items for b in i['boxes'])),
                 splits={s:sum(i['split']==s for i in items) for s in ('train','val','test')},groups={k:len(v) for k,v in groups.items()},
                 unread_clocks=sum(i['seconds'] is None for i in items),crop=bounds,background_crops=sum('-background-' in d['name'] for d in derivatives))
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
