import { resample16k } from './audio.mjs';

let pipelinePromise = null;
const queue = [];
let running = false;
// ModelScope serves these files with browser CORS; hf-mirror redirects without it.
const MODEL_HOST = 'https://modelscope.cn/models/';
const MODEL = 'onnx-community/whisper-tiny';

async function load() {
  if (!pipelinePromise) {
    postMessage({ type: 'progress', progress: 0, status: 'loading' });
    pipelinePromise = import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.2/+esm')
      .then(({ pipeline, env }) => {
        env.remoteHost = MODEL_HOST; env.remotePathTemplate = '{model}/resolve/master/'; env.allowLocalModels = false; env.allowRemoteModels = true;
        return pipeline('automatic-speech-recognition', MODEL, { dtype: { encoder_model: 'q8', decoder_model_merged: 'q8' }, device: 'wasm', progress_callback: p => postMessage({ type: 'progress', file: p?.file, progress: p?.progress ?? 0, status: p?.status || 'loading' }) });
      }).then(p => { postMessage({ type: 'ready', model: MODEL }); return p; }).catch(error => { pipelinePromise = null; throw error; });
  }
  return pipelinePromise;
}

async function drain() {
  if (running) return; running = true;
  while (queue.length) {
    const job = queue.shift();
    try {
      const asr = await load(); const audio = resample16k(job.audio, job.sampleRate);
      const out = await asr(audio, { language: job.language === 'auto' ? undefined : job.language, task: 'transcribe', return_timestamps: false });
      postMessage({ type: 'result', id: job.id, text: out?.text || '' });
    } catch (error) { postMessage({ type: 'error', id: job.id, error: String(error?.message || error) }); }
  }
  running = false;
}

self.onmessage = event => {
  const data = event.data || {};
  if (data.type === 'load') { load().catch(error => postMessage({ type: 'error', error: String(error?.message || error) })); return; }
  if (data.type === 'transcribe') { queue.push({ ...data, audio: data.audio instanceof Float32Array ? data.audio : new Float32Array(data.audio), sampleRate: data.sampleRate || 16000 }); drain(); }
};
