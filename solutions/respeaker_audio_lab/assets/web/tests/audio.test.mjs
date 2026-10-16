import test from 'node:test';
import assert from 'node:assert/strict';
import { AudioCapture, fft, resample16k, rms, wavBlob } from '../audio.mjs';

test('resample16k preserves duration and level', () => {
  const output = resample16k(new Float32Array(48000).fill(0.25), 48000);
  assert.equal(output.length, 16000);
  assert.ok(Math.abs(rms(output) - 0.25) < 1e-5);
});

test('rms and fft expose numeric per-channel helpers', () => {
  assert.equal(rms(new Float32Array([1, -1, 1, -1])), 1);
  const samples = new Float32Array(256);
  for (let i = 0; i < samples.length; i++) samples[i] = Math.sin(2 * Math.PI * 8 * i / 256);
  const spectrum = fft(samples, 256);
  assert.equal(spectrum.length, 128);
  assert.ok(spectrum[8] > spectrum[1]);
});

test('pcm event exposes unchanged channels and sample rate before the frame event', () => {
  const capture = new AudioCapture(); capture.sampleRate = 16000;
  const channels = [Float32Array.of(0.25, -0.5), Float32Array.of(0.75, -1)];
  const events = [];
  capture.addEventListener('pcm', event => {
    events.push('pcm');
    assert.strictEqual(event.detail.channels, channels);
    assert.equal(event.detail.sampleRate, 16000);
    assert.deepEqual(event.detail.channels.map(channel => [...channel]), [[0.25, -0.5], [0.75, -1]]);
  });
  capture.addEventListener('frame', () => events.push('frame'));
  capture._pcm(channels);
  assert.deepEqual(events, ['pcm', 'frame']);
  assert.equal(channels[0].byteLength, 8);
  capture._pcm([Float32Array.of(1), Float32Array.of(1, 2)]);
  assert.deepEqual(events, ['pcm', 'frame']);
});

test('wavBlob writes a mono PCM16 RIFF header', async () => {
  const blob = wavBlob(new Float32Array([0, 1, -1]), 16000);
  assert.equal(blob.type, 'audio/wav');
  const bytes = new Uint8Array(await blob.arrayBuffer());
  assert.equal(new TextDecoder().decode(bytes.slice(0, 4)), 'RIFF');
  assert.equal(new TextDecoder().decode(bytes.slice(8, 12)), 'WAVE');
  assert.equal(bytes.length, 50);
});

test('record captures the same selected multi-channel window and rejects reconfiguration', async () => {
  const capture = new AudioCapture();
  capture.stream = {}; capture.sampleRate = 1000; capture.reportedChannels = 2; capture._hasFrame = true;
  capture.setChannels({ original: 0, processed: 1 });
  const recording = capture.record(6);
  assert.throws(() => capture.setChannels({ original: 1, processed: null }), /during recording/);
  for (let i = 0; i < 6; i++) capture._pcm([new Float32Array(1000).fill(i), new Float32Array(1000).fill(i + 10)]);
  const result = await recording;
  assert.equal(result.original.length, 6000);
  assert.equal(result.processed.length, 6000);
  assert.equal(result.original[0], 0);
  assert.equal(result.processed[0], 10);
  assert.throws(() => capture.setChannels({ original: 0, processed: 0 }), /differ/);
});

test('record rejects unavailable channels and invalid resampling rates', async () => {
  const capture = new AudioCapture(); capture.stream = {}; capture.sampleRate = 1000; capture.reportedChannels = 1; capture._hasFrame = true;
  capture.setChannels({ original: 1 });
  await assert.rejects(capture.record(1), /unavailable/);
  assert.throws(() => resample16k(new Float32Array(1), 0), /positive/);
  capture.setChannels({ original: 0 });
  const pending = capture.record(1);
  await capture.stop();
  await assert.rejects(pending, /stopped/);
});

test('record retains every channel over one exact window and reuses selected arrays', async () => {
  const capture = new AudioCapture();
  capture.stream = {}; capture.sampleRate = 10; capture.reportedChannels = 3; capture._hasFrame = true;
  capture.setChannels({ original: 2, processed: 0 });
  const pending = capture.record(0.5);
  capture._pcm([Float32Array.of(1, 2, 3), Float32Array.of(11, 12, 13), Float32Array.of(21, 22, 23)]);
  capture._pcm([Float32Array.of(4, 5, 6), Float32Array.of(14, 15, 16), Float32Array.of(24, 25, 26)]);
  const result = await pending;
  assert.equal(result.allChannels.length, 3);
  result.allChannels.forEach((channel, index) => {
    assert.ok(channel instanceof Float32Array);
    assert.equal(channel.length, 5);
    assert.deepEqual([...channel], [1, 2, 3, 4, 5].map(value => value + index * 10));
  });
  assert.strictEqual(result.original, result.allChannels[2]);
  assert.strictEqual(result.processed, result.allChannels[0]);
  assert.deepEqual(result.channels, { original: 2, processed: 0 });
  assert.equal(result.sampleRate, 10);

  capture.setChannels({ original: 1, processed: null });
  const singleSelection = capture.record(0.1);
  capture._pcm([Float32Array.of(7), Float32Array.of(17), Float32Array.of(27)]);
  const single = await singleSelection;
  assert.deepEqual(single.allChannels.map(channel => [...channel]), [[7], [17], [27]]);
  assert.strictEqual(single.original, single.allChannels[1]);
  assert.equal(single.processed, null);
});

test('record rejects when the live channel count increases during the window', async () => {
  const capture = new AudioCapture(); capture.stream = {}; capture.sampleRate = 1000; capture.reportedChannels = 2; capture._hasFrame = true;
  const pending = capture.record(1);
  capture._pcm([new Float32Array(1000), new Float32Array(1000), new Float32Array(1000)]);
  await assert.rejects(pending, /layout changed/);
});

test('record rejects when the live channel count drops during the window', async () => {
  const capture = new AudioCapture(); capture.stream = {}; capture.sampleRate = 1000; capture.reportedChannels = 2; capture._hasFrame = true;
  capture.setChannels({ original: 0, processed: 1 });
  const pending = capture.record(1);
  capture._pcm([new Float32Array(1000)]);
  await assert.rejects(pending, /unavailable|layout changed/);
});
