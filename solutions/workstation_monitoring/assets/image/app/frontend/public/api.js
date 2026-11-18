import {drawDetectionOverlay, overlayStyle} from './overlay.js';
import {getLanguage} from './i18n.js';
export const COCO_EDGES=overlayStyle.skeleton_edges;
export async function getJSON(url,options={}) {
  const response=await fetch(url,{cache:'no-store',...options,signal:options.signal||AbortSignal.timeout(4000)});
  const data=await response.json();
  if(!response.ok)throw Object.assign(new Error(data.error?.message||'Request failed'),{status:response.status,code:data.error?.code,message_key:data.error?.message_key,message_params:data.error?.message_params});
  return data;
}
export function workAction(action, payload = {}) {
  return getJSON('/api/v1/work/actions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,action})});
}
export function containRect(sourceWidth,sourceHeight,containerWidth,containerHeight) {
  const scale=Math.min(containerWidth/sourceWidth,containerHeight/sourceHeight);
  return {scale,x:(containerWidth-sourceWidth*scale)/2,y:(containerHeight-sourceHeight*scale)/2,width:sourceWidth*scale,height:sourceHeight*scale};
}
export function shouldRender(envelope,lastId) {
  return Boolean(envelope.available && envelope.fresh && envelope.observation && envelope.observation.observation_id!==lastId);
}
export function duration(seconds) {
  const s=Math.max(0,Math.floor(seconds||0));return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(x=>String(x).padStart(2,'0')).join(':');
}
export async function matchingImage(observation) {
  // The returned JPEG and geometry MUST carry the same ID. Never substitute live video here.
  const locale=getLanguage();
  const response=await fetch(observation.matching_frame_url,{cache:'no-store',signal:AbortSignal.timeout(4000)});
  if(!response.ok)throw Object.assign(new Error('Matching frame unavailable'),{status:response.status});
  if(response.headers.get('X-Observation-ID')!==observation.observation_id)throw new Error('Observation ID mismatch');
  const url=URL.createObjectURL(await response.blob());
  try {const image=new Image();image.src=url;await image.decode();if(locale!==getLanguage())throw new Error('Language changed');return image;}
  finally {URL.revokeObjectURL(url);}
}
export function drawResult(canvas,image,observation,options) {
  drawDetectionOverlay(canvas,image,observation,options);
}

export function currentObservation(camera, envelope) {
  return Boolean(camera?.status === 'online' && !camera?.algorithm_error && envelope?.fresh && envelope?.available
    && envelope.observation?.config_revision === camera?.config_revision
    && envelope.observation?.frame.stream_session_id === camera?.stream_session_id);
}

// Video health is independent of a slower, larger structured-result request.
export function previewReady(camera, envelope) {
  const fresh=typeof camera?.preview_fresh==='boolean'?camera.preview_fresh:(typeof camera?.algorithm_fresh==='boolean'?camera.algorithm_fresh:currentObservation(camera,envelope));
  return Boolean(camera?.status==='online' && camera?.operating_mode!=='training' && (!camera?.algorithm_error || (camera?.privacy_applied===false && typeof camera?.preview_fresh==='boolean')) && fresh
    && (typeof camera.preview_fresh==='boolean' || (camera.output_fps??0)>0));
}

// Business/session status must never own the lifetime of a live video connection.
// Keep a peer through brief telemetry/frame gaps; changed media/privacy still stop it.
export class PreviewContinuity {
  constructor() { this.identity=null; this.lastReady=-Infinity; }
  update(camera, envelope, now=performance.now(), mediaFresh=false) {
    const identity=camera ? JSON.stringify([camera.stream_session_id,
      camera.video?.epoch ?? camera.config_revision, camera.privacy_applied]) : this.identity;
    const changed=this.identity!==null && identity!==this.identity;
    const blocked=Boolean(camera && (camera.status!=='online' || camera.operating_mode==='training'
      || (camera.algorithm_error && camera.privacy_applied!==false)));
    const ready=previewReady(camera,envelope);
    if(changed || blocked)this.lastReady=-Infinity;
    if(ready)this.lastReady=now;
    this.identity=identity;
    const retain=!blocked && (ready || (!changed && (mediaFresh || now-this.lastReady<5000)));
    return {ready,retain,reset:changed || !retain};
  }
}

// Presentation values only. The backend owns session settlement and all timers.
export function dashboardView(camera, work, envelope) {
  const keys = ['work','rest','pending','unknown'];
  const seconds = Object.fromEntries(keys.map(key => [key, Number.isFinite(work?.[key+'_seconds']) ? Math.max(0, work[key+'_seconds']) : null]));
  const complete = keys.every(key => seconds[key] !== null);
  const total = complete ? keys.reduce((sum,key) => sum+seconds[key],0) : null;
  const ratios = Object.fromEntries(keys.map(key => [key,total>0 ? seconds[key]/total*100 : null]));
  const scope = work?.active ? 'v4.currentSession' : work?.session_end != null ? 'v4.lastSession' : 'v4.noSession';
  const fresh = currentObservation(camera, envelope);
  const processing = fresh ? envelope.observation.inference.local_processing_ms : null;
  const age = fresh ? envelope.age_ms : null;
  return {seconds, ratios, total, scope, outputFps: camera?.status==='online' && Number.isFinite(camera.output_fps) ? camera.output_fps : null,
    processingMs:Number.isFinite(processing)?processing:null,ageMs:Number.isFinite(age)?age:null};
}
export function displayMode(value) { return value === 'showcase' ? 'showcase' : 'standard'; }

export function systemMetricsView(metrics) {
  const valid = (value, minimum, maximum = Infinity) =>
    Number.isFinite(value) && value >= minimum && value <= maximum ? value : null;
  const fresh = metrics?.schema_version === '1.0' && valid(metrics.age_ms, 0, 5000) !== null;
  const data = fresh ? metrics : {};
  const total = valid(data.memory_total_bytes, 1);
  return {
    cpu: valid(data.cpu_percent, 0, 100),
    gpu: valid(data.gpu_percent, 0, 100),
    memoryUsed: total === null ? null : valid(data.memory_used_bytes, 0, total),
    memoryTotal: total,
    temperature: valid(data.temperature_celsius, -40, 150),
    uptime: valid(data.uptime_seconds, 0),
  };
}

// randomUUID is unavailable on ordinary LAN HTTP origins; getRandomValues is supported.
export function operationToken(source=globalThis.crypto) {
  if(typeof source.randomUUID==='function')return source.randomUUID();
  return Array.from(source.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('');
}
