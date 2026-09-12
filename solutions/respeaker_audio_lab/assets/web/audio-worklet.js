class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() { super(); this.pending = []; this.size = Math.max(128, Math.floor(sampleRate * 0.05)); }
  process(inputs) {
    const input = inputs[0];
    if (!input?.length || !input[0]?.length) return true;
    const count = input[0].length;
    for (let i = 0; i < count; i++) for (let c = 0; c < input.length; c++) (this.pending[c] ||= []).push(input[c][i] || 0);
    if (this.pending[0]?.length >= this.size) {
      const n = this.pending[0].length, channels = this.pending.map(a => new Float32Array(a.splice(0, n)));
      this.port.postMessage({ type: 'pcm', channels }, channels.map(a => a.buffer));
    }
    return true;
  }
}
registerProcessor('pcm-capture', PcmCaptureProcessor);

