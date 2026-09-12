import test from 'node:test';
import assert from 'node:assert/strict';
import { LEGACY_PARAMETERS, ReSpeakerUSB, identifyDevice } from '../device.mjs';

function legacyHarness() {
  const usb = new EventTarget();
  const values = new Map([['19:10', 0.25], ['19:13', 0.5], ['19:14', 1], ['19:0', 1], ['18:27', 3], ['19:8', 1], ['19:11', 0], ['21:0', 135], ['19:32', 1]]);
  const calls = { in: [], out: [] };
  const device = { vendorId: 0x2886, productId: 0x0018, productName: 'XVF3000 test', opened: false,
    async open() { this.opened = true; }, async close() { this.opened = false; },
    async controlTransferIn(setup, length) {
      calls.in.push({ setup, length });
      assert.equal(setup.requestType, 'vendor'); assert.equal(setup.recipient, 'device'); assert.equal(setup.request, 0);
      if (setup.index === 0 && setup.value === 0x80) return { status: 'ok', data: new DataView(Uint8Array.from([7]).buffer) };
      assert.equal(setup.value & 0x80, 0x80);
      const key = `${setup.index}:${setup.value & 0x3f}`; const value = values.get(key);
      if (value === undefined) throw new Error(`unknown read ${key}`);
      const buffer = new ArrayBuffer(8); const view = new DataView(buffer);
      if (key === '19:10' || key === '19:13') { const mantissa = Math.round(value * 2 ** 20); view.setInt32(0, mantissa, true); view.setInt32(4, -20, true); }
      else view.setInt32(0, value, true);
      return { status: 'ok', data: view };
    },
    async controlTransferOut(setup, data) {
      calls.out.push({ setup, data: [...data] });
      assert.equal(setup.requestType, 'vendor'); assert.equal(setup.recipient, 'device'); assert.equal(setup.request, 0);
      assert.equal(setup.value, 0);
      const view = new DataView(data.buffer, data.byteOffset, data.byteLength); const offset = view.getInt32(0, true); const key = `${setup.index}:${offset}`;
      values.set(key, view.getInt32(8, true) === 0 && (key === '19:10' || key === '19:13') ? view.getFloat32(4, true) : view.getInt32(4, true));
      return { status: 'ok', bytesWritten: data.byteLength };
    },
  };
  return { usb, device, calls };
}

async function withUsb(usb, fn) { const previous = globalThis.navigator; globalThis.navigator = { usb }; try { return await fn(); } finally { globalThis.navigator = previous; } }

test('XVF3000 identity selects the legacy protocol and definitions', () => {
  const identity = identifyDevice({ vendorId: 0x2886, productId: 0x0018 });
  assert.equal(identity.controlProtocol, 'xvf3000-legacy');
  assert.equal(LEGACY_PARAMETERS.find((p) => p.key === 'HPFONOFF').max, 3);
  assert.deepEqual(LEGACY_PARAMETERS.find((p) => p.key === 'MIN_NS').slice?.(), undefined);
});

test('legacy version uses one byte, decodes float pair and returns definitions', async () => {
  const { usb, device, calls } = legacyHarness();
  await withUsb(usb, async () => {
    const control = new ReSpeakerUSB(device); const snap = await control.connect();
    assert.equal(snap.firmware, '7'); assert.equal(snap.identity.controlProtocol, 'xvf3000-legacy');
    assert.equal(snap.parameters.MIN_NS.value, 0.25); assert.equal(snap.parameters.MIN_NS.supported, true);
    assert.equal(snap.parameters.HPFONOFF.value, 3); assert.ok(snap.parameterDefinitions.some((p) => p.key === 'AGCONOFF'));
    assert.equal(calls.in.find((call) => call.setup.index === 19 && call.setup.value === 0xc0)?.setup.value, 0xc0);
    assert.equal(calls.in.find((call) => call.setup.index === 18 && call.setup.value === 0xdb)?.setup.value, 0xdb);
    assert.deepEqual(calls.in[0].setup, { requestType: 'vendor', recipient: 'device', request: 0, value: 0x80, index: 0 });
    assert.equal(calls.in[0].length, 1);
  });
});

test('legacy write sends offset, value and type, then validates readback', async () => {
  const { usb, device, calls } = legacyHarness();
  await withUsb(usb, async () => {
    const control = new ReSpeakerUSB(device); await control.connect();
    await control.write('MIN_NS', 0.75);
    const write = calls.out.at(-1); const view = new DataView(Uint8Array.from(write.data).buffer);
    assert.equal(write.setup.value, 0); assert.equal(write.setup.index, 19); assert.equal(write.data.length, 12);
    assert.equal(view.getInt32(0, true), 10); assert.ok(Math.abs(view.getFloat32(4, true) - 0.75) < 1e-6); assert.equal(view.getInt32(8, true), 0);
    await control.write('HPFONOFF', 3);
    assert.equal(calls.out.at(-1).setup.value, 0); assert.equal(new DataView(Uint8Array.from(calls.out.at(-1).data).buffer).getInt32(0, true), 27); assert.equal(new DataView(Uint8Array.from(calls.out.at(-1).data).buffer).getInt32(8, true), 1);
  });
});

test('legacy DOA and speech activity are read from separate resources', async () => {
  const { usb, device } = legacyHarness();
  await withUsb(usb, async () => { const control = new ReSpeakerUSB(device); await control.connect(); assert.deepEqual(await control.pollDoa(), { angle: 135, speech: true }); });
});

test('legacy save is explicitly unsupported and Lite remains audio-only', async () => {
  const { usb, device } = legacyHarness();
  await withUsb(usb, async () => { const control = new ReSpeakerUSB(device); const snap = await control.connect(); assert.equal(snap.canSave, false); await assert.rejects(control.save(), /does not expose USB flash save/); });
  assert.equal(identifyDevice({ vendorId: 0x2886, productId: 0x0019 }).controlProtocol, 'audio-only');
});
