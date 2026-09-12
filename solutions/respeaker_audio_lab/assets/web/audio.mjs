/** Browser microphone capture helpers.  This module has no browser side effects. */

const WORKLET_URL = new URL('./audio-worklet.js', import.meta.url);
const MAX_BUFFER_SECONDS = 12;

export function rms(samples) {
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return samples.length ? Math.sqrt(sum / samples.length) : 0;
}

/** Return a normalized one-sided magnitude spectrum, using a radix-2 FFT. */
export function fft(samples, size = 256) {
  let n = 1;
  while (n < size) n <<= 1;
  const re = new Float32Array(n);
  const im = new Float32Array(n);
  const count = Math.min(samples.length, n);
  for (let i = 0; i < count; i++) {
    const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / Math.max(1, count - 1));
    re[i] = samples[i] * w;
  }
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { const t = re[i]; re[i] = re[j]; re[j] = t; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const a = -2 * Math.PI / len;
    for (let start = 0; start < n; start += len) {
      for (let j = 0; j < len / 2; j++) {
        const c = Math.cos(a * j), s = Math.sin(a * j);
        const k = start + j, l = k + len / 2;
        const tr = re[l] * c - im[l] * s, ti = re[l] * s + im[l] * c;
        re[l] = re[k] - tr; im[l] = im[k] - ti;
        re[k] += tr; im[k] += ti;
      }
    }
  }
  const out = new Float32Array(n / 2);
  for (let i = 0; i < out.length; i++) out[i] = Math.hypot(re[i], im[i]) / n;
  return out;
}

/** Resample to Whisper's 16 kHz input rate with box-filter anti-aliasing. */
export function resample16k(samples, sampleRate) {
  if (!Number.isFinite(sampleRate) || sampleRate <= 0) throw new TypeError('sampleRate must be a positive number');
  if (!sampleRate || sampleRate === 16000) return new Float32Array(samples);
  const length = Math.max(0, Math.floor(samples.length * 16000 / sampleRate));
  const out = new Float32Array(length);
  if (sampleRate > 16000) {
    const ratio = sampleRate / 16000;
    for (let i = 0; i < length; i++) {
      const start = i * ratio, end = (i + 1) * ratio;
      const first = Math.floor(start), last = Math.min(samples.length - 1, Math.ceil(end) - 1);
      let total = 0, weight = 0;
      for (let j = first; j <= last; j++) {
        const portion = Math.max(0, Math.min(end, j + 1) - Math.max(start, j));
        total += samples[j] * portion; weight += portion;
      }
      out[i] = weight ? total / weight : 0;
    }
  } else {
    const ratio = sampleRate / 16000;
    for (let i = 0; i < length; i++) {
      const x = i * ratio, a = Math.floor(x), b = Math.min(samples.length - 1, a + 1), f = x - a;
      out[i] = samples[a] * (1 - f) + samples[b] * f;
    }
  }
  return out;
}

export function wavBlob(samples, sampleRate) {
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) pcm[i] = Math.max(-32768, Math.min(32767, Math.round(samples[i] * 32767)));
  const buffer = new ArrayBuffer(44 + pcm.byteLength), view = new DataView(buffer);
  const text = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  text(0, 'RIFF'); view.setUint32(4, 36 + pcm.byteLength, true); text(8, 'WAVE'); text(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, 'data'); view.setUint32(40, pcm.byteLength, true);
  new Int16Array(buffer, 44).set(pcm);
  return new Blob([buffer], { type: 'audio/wav' });
}

function waveform(samples, count = 128) {
  const out = new Float32Array(Math.min(count, samples.length || count));
  if (!samples.length) return out;
  for (let i = 0; i < out.length; i++) out[i] = samples[Math.min(samples.length - 1, Math.floor(i * samples.length / out.length))];
  return out;
}

export class AudioCapture extends EventTarget {
  constructor() {
    super(); this.stream = null; this.context = null; this.source = null; this.node = null; this.mute = null;
    this.sampleRate = 0; this.reportedChannels = 0; this.selected = { original: 0, processed: null };
    this.buffers = []; this.bufferedSamples = 0; this.pending = null; this._stopping = false; this._hasFrame = false; this._onMessage = null;
  }

  async listInputs() {
    if (!globalThis.navigator?.mediaDevices?.enumerateDevices) throw new Error('MediaDevices API unavailable');
    return (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'audioinput').map(d => ({ deviceId: d.deviceId, label: d.label }));
  }

  async start(deviceId) {
    if (this.stream) await this.stop();
    if (!globalThis.navigator?.mediaDevices?.getUserMedia || !globalThis.AudioContext) throw new Error('Audio capture unavailable');
    const audio = { channelCount: { ideal: 6 }, echoCancellation: { exact: false }, noiseSuppression: { exact: false }, autoGainControl: { exact: false } };
    if (deviceId) audio.deviceId = { exact: deviceId };
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio });
      const track = this.stream.getAudioTracks()[0];
      this.context = new AudioContext({ latencyHint: 'interactive' }); this.sampleRate = this.context.sampleRate;
      await this.context.resume?.();
      this.source = this.context.createMediaStreamSource(this.stream);
      await this.context.audioWorklet.addModule(WORKLET_URL.href);
      this.node = new AudioWorkletNode(this.context, 'pcm-capture', { numberOfInputs: 1, numberOfOutputs: 1, channelCountMode: 'max', channelInterpretation: 'discrete' });
      this.mute = this.context.createGain(); this.mute.gain.value = 0;
      this.source.connect(this.node).connect(this.mute).connect(this.context.destination);
      let firstPcm;
      const firstFrame = new Promise(resolve => { firstPcm = resolve; });
      this._onMessage = e => { if (e.data?.type === 'pcm') { this._pcm(e.data.channels); firstPcm(); } };
      this.node.port.onmessage = this._onMessage;
      track.addEventListener('ended', () => { this.dispatchEvent(new ErrorEvent('error', { error: new Error('microphone track ended') })); this.stop(); }, { once: true });
      const settings = track.getSettings?.() || {}, capabilities = track.getCapabilities?.() || {};
      await Promise.race([firstFrame, new Promise(resolve => setTimeout(resolve, 500))]);
      const processing = Object.fromEntries(['echoCancellation', 'noiseSuppression', 'autoGainControl'].map(k => [k, settings[k] === undefined ? null : settings[k]]));
      return { sampleRate: this.sampleRate, reportedChannels: this.reportedChannels, processing, capabilities, settings };
    } catch (error) {
      await this.stop();
      throw error;
    }
  }

  setChannels({ original = 0, processed = null } = {}) {
    if (this.pending) throw new Error('cannot change channels during recording');
    if (!Number.isInteger(original) || original < 0 || (processed !== null && (!Number.isInteger(processed) || processed < 0))) throw new Error('channel indices must be non-negative integers');
    if (processed !== null && processed === original) throw new Error('original and processed channels must differ');
    this.selected = { original, processed };
  }

  _pcm(channels) {
    if (!channels?.length) return;
    const n = channels[0].length;
    if (!channels.every(ch => ch.length === n)) { this._rejectPending(new Error('inconsistent channel frame')); return; }
    this.dispatchEvent(new CustomEvent('pcm', { detail: { channels, sampleRate: this.sampleRate } }));
    if (this.pending && channels.length !== this.pending.channelCount) this._rejectPending(new Error('channel layout changed during recording'));
    this.reportedChannels = channels.length; this._hasFrame = true;
    while (this.buffers.length < channels.length) this.buffers.push([]);
    for (let c = 0; c < channels.length; c++) this.buffers[c].push(new Float32Array(channels[c]));
    this.bufferedSamples += n;
    const frameChannels = channels.map(ch => ({ rms: rms(ch), peak: ch.reduce((p, x) => Math.max(p, Math.abs(x)), 0), spectrum: fft(ch), waveform: waveform(ch) }));
    this.dispatchEvent(new CustomEvent('frame', { detail: { channels: frameChannels, sampleRate: this.sampleRate, channelCount: channels.length, time: globalThis.performance?.now?.() ?? Date.now() } }));
    if (this.bufferedSamples > this.sampleRate * MAX_BUFFER_SECONDS) this._trim();
    if (this.pending) {
      const p = this.pending; const take = Math.min(n, p.target - p.count);
      if (p.originalChannel >= channels.length || (p.processedChannel !== null && p.processedChannel >= channels.length)) { this._rejectPending(new Error('selected channel is unavailable')); return; }
      channels.forEach((channel, index) => p.allChannels[index].push(new Float32Array(channel.subarray(0, take))));
      p.count += take;
      if (p.count >= p.target) { this.pending = null; clearTimeout(p.timer); const allChannels = p.allChannels.map(concat); p.resolve({ allChannels, original: allChannels[p.originalChannel], processed: p.processedChannel === null ? null : allChannels[p.processedChannel], sampleRate: this.sampleRate, channels: { original: p.originalChannel, processed: p.processedChannel }, startedAt: p.startedAt }); }
    }
  }
  _trim() { const keep = this.sampleRate * MAX_BUFFER_SECONDS; while (this.bufferedSamples > keep && this.buffers[0]?.length) { this.bufferedSamples -= this.buffers[0].shift().length; for (let c = 1; c < this.buffers.length; c++) this.buffers[c].shift(); } }

  record(seconds = 6) {
    if (!this.stream || !this.sampleRate) return Promise.reject(new Error('capture is not started'));
    if (this.pending) return Promise.reject(new Error('a recording is already pending'));
    if (!(seconds > 0 && seconds <= MAX_BUFFER_SECONDS)) return Promise.reject(new Error(`seconds must be between 0 and ${MAX_BUFFER_SECONDS}`));
    if (!this._hasFrame) return Promise.reject(new Error('waiting for first audio frame'));
    if (this.selected.original >= this.reportedChannels || (this.selected.processed !== null && this.selected.processed >= this.reportedChannels)) return Promise.reject(new Error('selected channel is unavailable'));
    const selected = { ...this.selected };
    return new Promise((resolve, reject) => { const pending = { channelCount: this.reportedChannels, target: Math.ceil(seconds * this.sampleRate), count: 0, allChannels: Array.from({ length: this.reportedChannels }, () => []), originalChannel: selected.original, processedChannel: selected.processed, resolve, reject, startedAt: Date.now() }; pending.timer = setTimeout(() => this._rejectPending(new Error('audio capture stalled')), Math.max(2000, seconds * 2000)); this.pending = pending; });
  }

  async play(samples, sampleRate = this.sampleRate) {
    if (!globalThis.AudioContext) throw new Error('audio playback unavailable');
    const ctx = new AudioContext(), buffer = ctx.createBuffer(1, samples.length, sampleRate), source = ctx.createBufferSource(); buffer.copyToChannel(samples, 0); source.buffer = buffer; source.connect(ctx.destination); source.start(); return new Promise(resolve => { source.onended = () => { ctx.close(); resolve(); }; });
  }

  async stop() {
    if (this._stopping) return; this._stopping = true;
    this._rejectPending(new Error('capture stopped'));
    if (this.node?.port) this.node.port.onmessage = null;
    this.node?.disconnect(); this.source?.disconnect(); this.mute?.disconnect(); this.stream?.getTracks?.().forEach(t => t.stop());
    await this.context?.close(); this.stream = this.context = this.source = this.node = this.mute = null; this._onMessage = null; this.buffers = []; this.bufferedSamples = 0; this.reportedChannels = 0; this._hasFrame = false; this._stopping = false;
  }

  _rejectPending(error) { if (!this.pending) return; const p = this.pending; this.pending = null; clearTimeout(p.timer); p.reject(error); }
}

function concat(parts) { const length = parts.reduce((n, p) => n + p.length, 0), out = new Float32Array(length); let offset = 0; for (const p of parts) { out.set(p, offset); offset += p.length; } return out; }
