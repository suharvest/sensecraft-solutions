import {sourcePoint} from './roi-editor.js';

export function clampBox(box,size) {
  const [w,h]=size;
  return [Math.max(0,Math.min(w,Math.min(box[0],box[2]))),Math.max(0,Math.min(h,Math.min(box[1],box[3]))),Math.max(0,Math.min(w,Math.max(box[0],box[2]))),Math.max(0,Math.min(h,Math.max(box[1],box[3])))];
}
export const classColor=id=>`hsl(${(Number(id)*137.508+165)%360} 78% 62%)`;
export class BoxAnnotator {
  constructor(canvas,changed) {
    this.canvas=canvas;this.changed=changed;this.boxes=[];this.selected=-1;this.history=[];this.size=[1,1];this.image=null;this.classes={'0':'Object'};this.classId=0;
    canvas.addEventListener('pointerdown',e=>this.down(e));
    canvas.addEventListener('pointermove',e=>this.move(e));
    canvas.addEventListener('pointerup',e=>this.up(e));
    canvas.addEventListener('pointercancel',()=>{if(this.drag)this.boxes=this.drag.before;this.drag=null;this.draw();});
  }
  load(image,boxes,size) {this.image=image;this.boxes=boxes.map(b=>[...b.slice(0,4),b[4]??0]);this.size=size;this.selected=-1;this.history=[];this.canvas.width=image.naturalWidth;this.canvas.height=image.naturalHeight;this.draw();}
  point(e) {return sourcePoint(e.clientX,e.clientY,this.canvas.getBoundingClientRect(),this.size);}
  down(e) {
    if(!this.image||e.button>0||!Object.hasOwn(this.classes,String(this.classId)))return;const p=this.point(e);if(!p)return;e.preventDefault();
    this.canvas.setPointerCapture(e.pointerId);const before=structuredClone(this.boxes);
    const tolerance=12*this.size[0]/this.canvas.getBoundingClientRect().width;
    let handle=null;
    if(this.selected>=0) {
      const b=this.boxes[this.selected];
      for(const [i,j] of [[0,1],[2,1],[2,3],[0,3]])if(Math.hypot(b[i]-p[0],b[j]-p[1])<tolerance)handle=[i,j];
    }
    if(handle){this.drag={type:'resize',handle,start:p,before};return;}
    this.selected=this.createNext?-1:this.boxes.findLastIndex(b=>p[0]>=b[0]&&p[0]<=b[2]&&p[1]>=b[1]&&p[1]<=b[3]);
    if(this.selected<0){this.createNext=false;this.boxes.push([...p,...p,this.classId]);this.selected=this.boxes.length-1;this.drag={type:'new',start:p,before};}
    else this.drag={type:'move',start:p,before};
    this.draw();
  }
  move(e) {
    if(!this.drag)return;const p=this.point(e);if(!p)return;
    const d=this.drag;let box;
    if(d.type==='new')box=[...d.start,...p];
    else if(d.type==='resize'){box=d.before[this.selected].slice();box[d.handle[0]]=p[0];box[d.handle[1]]=p[1];}
    else {const b=d.before[this.selected],dx=Math.max(-b[0],Math.min(this.size[0]-b[2],p[0]-d.start[0])),dy=Math.max(-b[1],Math.min(this.size[1]-b[3],p[1]-d.start[1]));box=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy];}
    this.boxes[this.selected]=[...clampBox(box,this.size),this.boxes[this.selected][4]??this.classId];this.draw();
  }
  up(e) {
    if(!this.drag)return;this.move(e);this.history.push(this.drag.before);this.drag=null;
    const selected=this.boxes[this.selected],previous=this.history.at(-1);
    this.boxes=this.boxes.filter(b=>b[2]-b[0]>=2&&b[3]-b[1]>=2);this.selected=this.boxes.indexOf(selected);this.draw();
    if(JSON.stringify(previous)!==JSON.stringify(this.boxes))this.changed();this.selectionChanged?.();
  }
  beginBox(){this.selected=-1;this.createNext=true;this.draw();}
  setClass(id){if(!Object.hasOwn(this.classes,String(id)))return;this.classId=Number(id);if(this.selected>=0){this.history.push(structuredClone(this.boxes));this.boxes[this.selected][4]=this.classId;this.draw();this.changed();}}
  remove(){if(this.selected<0)return;this.history.push(structuredClone(this.boxes));this.boxes.splice(this.selected,1);this.selected=-1;this.draw();this.changed();}
  clear(){this.history.push(structuredClone(this.boxes));this.boxes=[];this.selected=-1;this.draw();this.changed();}
  undo(){const b=this.history.pop();if(!b)return;this.boxes=b;this.selected=-1;this.draw();this.changed();}
  draw(){const c=this.canvas.getContext('2d');c.clearRect(0,0,this.canvas.width,this.canvas.height);if(!this.image)return;c.drawImage(this.image,0,0,this.canvas.width,this.canvas.height);
    const sx=this.canvas.width/this.size[0],sy=this.canvas.height/this.size[1],scale=this.canvas.width/Math.max(1,this.canvas.getBoundingClientRect().width);
    this.boxes.forEach((b,i)=>{const color=classColor(b[4]??0);c.strokeStyle=color;c.lineWidth=2*scale;c.strokeRect(b[0]*sx,b[1]*sy,(b[2]-b[0])*sx,(b[3]-b[1])*sy);const label=this.classes[String(b[4]??0)]??String(b[4]??0);c.font=`${14*scale}px sans-serif`;const tw=Math.min(this.canvas.width,c.measureText(label).width+12*scale),tx=Math.max(0,Math.min(this.canvas.width-tw,b[0]*sx)),ty=Math.max(18*scale,b[1]*sy);c.fillStyle='#071920dd';c.fillRect(tx,ty-18*scale,tw,20*scale);c.fillStyle=color;c.fillText(label,tx+4*scale,ty-3*scale); if(i===this.selected)for(const [x,y] of [[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]){c.fillStyle='#fbbf24';c.fillRect(x*sx-4*scale,y*sy-4*scale,8*scale,8*scale);}});
  }
}
