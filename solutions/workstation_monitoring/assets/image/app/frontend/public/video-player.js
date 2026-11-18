import {tr} from './i18n.js';

export function videoProfile(hostname) {
  return hostname==='localhost'||/^127\./.test(hostname)||hostname==='[::1]'||/^10\./.test(hostname)||/^192\.168\./.test(hostname)||/^172\.(1[6-9]|2[0-9]|3[01])\./.test(hostname)?'local':'remote';
}

export function captureVideoProfile(hostname) {
  const host=hostname.toLowerCase().replace(/^\[|\]$/g,'');
  const parts=host.split('.').map(Number);
  const tailnet=parts.length===4&&parts.every(n=>Number.isInteger(n)&&n>=0&&n<=255)&&parts[0]===100&&parts[1]>=64&&parts[1]<=127;
  return tailnet||host==='ts.net'||host.endsWith('.ts.net')?'remote':'local';
}

export function addressedAnswer(sdp, hostname) {
  // When the browser used a literal device IP, keep media on that same network.
  // Retain both UDP and TCP; DNS / proxy access keeps the complete ICE fallback set.
  const host=(hostname??'').replace(/^\[|\]$/g,'');
  // Firefox rejects loopback ICE candidates by default. A page opened locally
  // must retain the device's interface candidates instead of pinning to 127/8.
  if(/^127\./.test(host))return sdp;
  if(!/^\d+\.\d+\.\d+\.\d+$/.test(host))return sdp;
  const lines=sdp.split(/\r?\n/),candidate=line=>line.startsWith('a=candidate:');
  if(!lines.some(line=>candidate(line)&&line.trim().split(/\s+/)[4]===host))return sdp;
  return lines.filter(line=>!candidate(line)||line.trim().split(/\s+/)[4]===host).join('\r\n');
}

export class VideoPlayer {
  constructor(video, fallback, changed, options = {}) {
    this.video = video;
    this.fallback = fallback;
    this.changed = changed;
    this.raw = options.raw === true;
    this.generation = 0;
    this.mode = 'idle';
    this.metrics = null;
    this.renderIntervals = [];
    this.renderStalls = 0;
    this.renderDeltas = [];
    this.renderFrames = 0;
    this.renderElapsed = 0;
    this.unobservedIntervals = 0;
    this.lastMediaAt = -Infinity;
    video.onloadeddata = () => {if(this.mode!=='idle'){this.lastMediaAt=performance.now();this.changed(true);}};
    fallback.onload = () => {this.lastMediaAt=performance.now();this.changed(true);};
    fallback.onerror = () => this.changed(false);
  }
  visibilityChanged(hidden) {
    // Browser background throttling must not be treated as a failed camera.
    // Retain the same peer/session and allow fresh decoding to resume first.
    this.background=hidden;
    if (!hidden) {
      this.resumedAt=performance.now();
      if (this.pc && this.video.srcObject) this.video.play?.().catch(()=>{});
    }
  }
  isFresh(now=performance.now()) {
    return now-this.lastMediaAt<2000 || Boolean(this.pc?.connectionState==='connected'
      && (globalThis.document?.hidden || now-(this.resumedAt??-Infinity)<2000));
  }
  stop() {
    this.generation++;
    clearTimeout(this.deadline);
    clearTimeout(this.retry);
    clearInterval(this.interval);
    if (this.renderCallback != null) this.video.cancelVideoFrameCallback?.(this.renderCallback);
    this.renderCallback = null;
    this.renderIntervals = [];
    this.renderStalls = 0;
    this.renderDeltas = [];
    this.renderFrames = 0;
    this.renderElapsed = 0;
    this.unobservedIntervals = 0;
    this.abort?.abort();
    this.pc?.close();
    this.pc = null;
    for(const resource of [this.resource,this.fallbackResource])if(resource)fetch(resource,{method:'DELETE',keepalive:true}).catch(()=>{});
    this.fallbackResource=null;
    this.resource = null;
    this.video.srcObject = null;
    this.video.removeAttribute('src');
    this.video.hidden = true;
    this.fallback.onerror=null;
    this.fallback.onload=null;
    this.fallback.removeAttribute('src');
    this.fallback.hidden = true;
    this.metrics = null;
    this.lastMediaAt = -Infinity;
    this.mode = 'idle';
  }
  async start(locale, available, profile=videoProfile(globalThis.location?.hostname??'')) {
    this.stop();
    const generation = this.generation;
    this.locale = locale;
    this.profile = profile;
    this.resumedAt=performance.now();
    this.mode = 'connecting';
    if (!available || !globalThis.RTCPeerConnection) return this.useFallback(generation);
    this.abort = new AbortController();
    const pc = this.pc = new RTCPeerConnection({iceServers:[]});
    const receiver=pc.addTransceiver('video',{direction:'recvonly'}).receiver;
    // Optional browser hints, in milliseconds (standard) / seconds (legacy).
    try {
      if ('jitterBufferTarget' in receiver) receiver.jitterBufferTarget=100;
      else if ('playoutDelayHint' in receiver) receiver.playoutDelayHint=.1;
    } catch { /* Unsupported hints must not prevent playback. */ }
    pc.ontrack = event => {
      if (generation !== this.generation) return;
      this.video.srcObject = event.streams[0] ?? new MediaStream([event.track]);
      this.video.hidden = false;
      this.fallback.hidden = true;
      this.video.play().catch(() => this.useFallback(generation));
      this.measureDisplay(generation);
    };
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'failed') this.useFallback(generation);
    };
    this.deadline = setTimeout(() => this.useFallback(generation),15000);
    try {
      await pc.setLocalDescription(await pc.createOffer());
      await new Promise(resolve => {
        if (pc.iceGatheringState === 'complete') return resolve();
        const timer = setTimeout(resolve,2500);
        pc.addEventListener('icegatheringstatechange',() => {
          if (pc.iceGatheringState === 'complete') {clearTimeout(timer);resolve();}
        });
      });
      if (generation !== this.generation) return;
      const stream=this.raw?'raw':locale;
      const response = await fetch('/api/v1/video/whep/'+stream+'?profile='+this.profile,{
        method:'POST',headers:{'Content-Type':'application/sdp'},body:pc.localDescription.sdp,signal:this.abort.signal
      });
      if (!response.ok) throw new Error('WHEP unavailable');
      const resource = response.headers.get('Location');
      if (generation !== this.generation) {
        if (resource) fetch(resource,{method:'DELETE'}).catch(() => {});
        return;
      }
      if (!resource?.startsWith('/api/v1/video/sessions/')) throw new Error('Invalid session');
      this.resource = resource;
      await pc.setRemoteDescription({type:'answer',sdp:addressedAnswer(await response.text(),globalThis.location?.hostname)});
      let previous = null;
      let lastFrame = performance.now();
      let heartbeat = 0;
      this.interval = setInterval(async () => {
        if (generation !== this.generation || pc.connectionState === 'closed') return;
        try {
          const stats = await pc.getStats();
          if(generation!==this.generation)return;
          const now = performance.now();
          let inbound, pair;
          stats.forEach(report => {
            if (report.type === 'inbound-rtp' && report.kind === 'video') inbound = report;
            if (report.type === 'candidate-pair' && report.state === 'succeeded' && report.nominated) pair=report;
          });
          if (inbound?.framesDecoded > (previous?.framesDecoded ?? 0)) {
            lastFrame = now;
            this.lastMediaAt = now;
            clearTimeout(this.deadline);
            this.mode = 'webrtc';
            this.changed(true);
          }
          if (inbound && previous) {
            const seconds=(inbound.timestamp-previous.timestamp)/1000;
            const emitted=(inbound.jitterBufferEmittedCount??0)-(previous.jitterBufferEmittedCount??0);
            this.metrics = {
              fps:seconds>0?(inbound.framesDecoded-previous.framesDecoded)/seconds:0,
              kbps:seconds>0?(inbound.bytesReceived-previous.bytesReceived)*8/seconds/1000:0,
              rtt_ms:pair?.currentRoundTripTime==null?null:pair.currentRoundTripTime*1000,
              buffer_ms:emitted>0?((inbound.jitterBufferDelay??0)-(previous.jitterBufferDelay??0))*1000/emitted:null
            };

          }
          previous=inbound;
          const hidden=globalThis.document?.hidden===true;
          if (!hidden && now-Math.max(lastFrame,this.resumedAt??0)>5000) return this.useFallback(generation);
          if (now-heartbeat>5000 && this.resource) {
            heartbeat=now;
            const health=await fetch(this.resource,{signal:AbortSignal.timeout(3000)});
            // A control request can fail while RTP is still arriving normally.
            // An expired session requires reconnecting; transient 5xx/network errors do not.
            if (!health.ok && health.status>=400 && health.status<500 && !hidden) this.useFallback(generation);
          }
        } catch {
          if(!globalThis.document?.hidden && performance.now()-Math.max(lastFrame,this.resumedAt??0)>5000)this.useFallback(generation);
        }
      },1000);
    } catch {
      if (generation === this.generation) this.useFallback(generation);
    }
  }
  useFallback(generation) {
    if (generation !== this.generation || this.mode === 'mjpeg') return;
    const locale=this.locale;
    this.stop();
    this.locale=locale;
    this.mode='mjpeg';
    this.fallback.hidden=false;
    const current=this.generation;
    this.fallback.onload=()=>{if(current===this.generation){this.lastMediaAt=performance.now();this.changed(true);}};
    this.fallback.onerror=()=>{
      if(current!==this.generation)return;
      clearTimeout(this.retry);
      this.changed(false);
      this.retry=setTimeout(()=>{this.stop();this.changed(false,true);},1000);
    };
    const bytes=globalThis.crypto?.getRandomValues?.(new Uint8Array(16));
    const token=bytes?Array.from(bytes,n=>n.toString(16).padStart(2,'0')).join(''):null;
    this.fallbackResource=token?'/api/v1/video/sessions/'+token:null;
    this.fallback.src=(this.raw?'/api/v1/video.mjpg?':'/stream.mjpg?lang='+locale+'&')+'profile='+this.profile+(token?'&client_id='+token:'')+'&t='+Date.now();
    this.changed(false);
    this.retry=setTimeout(() => {this.stop();this.changed(false,true);},30000);
  }
  measureDisplay(generation) {
    if (!this.video.requestVideoFrameCallback) return;
    let previous = null,previousFrames=null;
    const displayed = (now,metadata={}) => {
      if (generation !== this.generation) return;
      this.lastMediaAt=performance.now();
      if (previous !== null && !globalThis.document?.hidden) {
        const interval=now-previous;
        const delta=Number.isFinite(metadata.presentedFrames)&&previousFrames!==null?metadata.presentedFrames-previousFrames:1;
        if(Number.isFinite(metadata.presentedFrames)&&delta>0){this.renderFrames+=delta;this.renderElapsed+=interval;}
        if(delta>0){this.renderDeltas.push(delta);if(this.renderDeltas.length>600)this.renderDeltas.shift();}
        if(delta===1){
          this.renderIntervals.push(interval);
          if(this.renderIntervals.length>600)this.renderIntervals.shift();
          if(interval>500)this.renderStalls++;
        }else if(delta>1)this.unobservedIntervals+=delta-1;
      }
      previous=now;
      previousFrames=Number.isFinite(metadata.presentedFrames)?metadata.presentedFrames:null;
      if (this.video.dataset) this.video.dataset.displayQuality = JSON.stringify(this.displayQuality());
      this.renderCallback = this.video.requestVideoFrameCallback(displayed);
    };
    this.renderCallback = this.video.requestVideoFrameCallback(displayed);
  }
  displayQuality() {
    const intervals = [...this.renderIntervals].sort((a,b)=>a-b);
    const represented=this.renderDeltas.reduce((sum,n)=>sum+n,0);
    const coverage=represented?this.renderDeltas.filter(n=>n===1).length/represented:1;
    return {samples:intervals.length,p95_ms:intervals.length&&coverage>=.5?intervals[Math.floor((intervals.length-1)*.95)]:null,
      stalls_over_500ms:coverage>=.5?this.renderStalls:null,
      presented_fps:this.renderElapsed>0?this.renderFrames*1000/this.renderElapsed:null,
      unobserved_frame_intervals:this.unobservedIntervals};
  }

  summary() {
    if (this.mode==='webrtc' && this.metrics) {
      const m=this.metrics;
      const value=n=>Number.isFinite(n)?Math.round(n):'—';
      const quality = this.displayQuality();
      const detail = quality.samples ? ' · '+tr('video.renderQuality',{p95:value(quality.p95_ms),stalls:value(quality.stalls_over_500ms)}) : '';
      return tr('video.webrtcStats',{quality:tr(this.profile==='local'?'video.hd':'video.fluent'),fps:this.metrics.fps.toFixed(1),kbps:value(m.kbps),rtt:value(m.rtt_ms),buffer:value(m.buffer_ms)}) + detail;
    }
    return tr(this.mode==='mjpeg'?'video.lowBandwidth':this.mode==='connecting'?'video.connectingRTC':'video.waiting');
  }
}
