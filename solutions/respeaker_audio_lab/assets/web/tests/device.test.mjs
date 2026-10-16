import test from 'node:test';
import assert from 'node:assert/strict';
import { ReSpeakerUSB, identifyDevice, PARAMETERS, OUTPUT_SIGNALS } from '../device.mjs';

function usbHarness({ inTransfer = null } = {}) {
  const usb = new EventTarget();
  const calls = { in: 0, out: 0 };
  const device = {
    vendorId: 0x2886, productId: 0x001e, productName: 'test reSpeaker', opened: false,
    async open() { this.opened = true; }, async close() { this.opened = false; },
    async controlTransferOut() { calls.out += 1; return { status: 'ok' }; },
    async controlTransferIn(setup, length) { calls.in += 1; return inTransfer ? inTransfer(calls.in, setup, length) : { status: 'ok', data: new Uint8Array(length) }; },
  };
  return { usb, device, calls };
}

async function withUsb(usb, fn) {
  const previous = globalThis.navigator;
  globalThis.navigator = { usb };
  try { return await fn(); } finally { globalThis.navigator = previous; }
}

test('disconnect event for the matching device clears state and prevents writes', async () => {
  const { usb, device, calls } = usbHarness();
  await withUsb(usb, async () => {
    const control = new ReSpeakerUSB(device);
    await control.connect();
    usb.dispatchEvent(Object.assign(new Event('disconnect'), { device }));
    await assert.rejects(control.write('PP_MIN_NS', 0.2), /not connected|disconnected|capability/);
    assert.equal(calls.out, 0);
  });
});

test('a failed capability probe prevents a write', async () => {
  const { device, calls } = usbHarness({ inTransfer: async () => { throw new Error('probe failed'); } });
  const control = new ReSpeakerUSB(device); control.identity = { controlProtocol: 'xvf3800-servicer' }; control.opened = true; control.firmwareValid = true;
  await assert.rejects(control.write('PP_MIN_NS', 0.2), /capability probe required/);
  assert.equal(calls.out, 0);
});

test('enum values must be exact options, not decimal values', async () => {
  const { device, calls } = usbHarness();
  const control = new ReSpeakerUSB(device); control.identity = { controlProtocol: 'xvf3800-servicer' }; control.opened = true; control.firmwareValid = true; control.capabilities.set('AEC_HPFONOFF', true);
  await assert.rejects(control.write('AEC_HPFONOFF', 1.5), /Invalid enum value/);
  assert.equal(calls.out, 0);
});

test('a one-byte status-64 reply is retried instead of treated as truncated', async () => {
  const { device, calls } = usbHarness({ inTransfer: async (attempt, _setup, length) => {
    if (attempt === 1) return { status: 'ok', data: new Uint8Array([64]) };
    const data = new Uint8Array(length); data[0] = 0; new DataView(data.buffer).setFloat32(1, 0.5, true); return { status: 'ok', data };
  } });
  const control = new ReSpeakerUSB(device); control.identity = { controlProtocol: 'xvf3800-servicer' }; control.opened = true; control.firmwareValid = true;
  assert.equal(await control.read('PP_MIN_NS'), 0.5);
  assert.equal(calls.in, 2);
});

test('device identification distinguishes supported Flex and USB-only Lite', () => {
  assert.equal(identifyDevice({ vendorId: 0x2886, productId: 0x001e }).id, 'respeaker_flex');
  const lite = identifyDevice({ vendorId: 0x2886, productId: 0x0019 });
  assert.equal(lite.controlProtocol, 'audio-only');
});

test('Lite control reads are unavailable', async () => {
  const { device, calls } = usbHarness(); device.productId = 0x0019;
  const control = new ReSpeakerUSB(device); control.identity = identifyDevice(device); control.opened = true;
  await assert.rejects(control.read('PP_MIN_NS'), /unavailable/);
  assert.equal(calls.in, 0);
});

test('HPF enum value 4 is encoded and validated by the readback', async () => {
  const { device, calls } = usbHarness({ inTransfer: async (_attempt, _setup, length) => {
    const data = new Uint8Array(length); data[0] = 0; new DataView(data.buffer).setInt32(1, 4, true); return { status: 'ok', data };
  } });
  const control = new ReSpeakerUSB(device); control.identity = { controlProtocol: 'xvf3800-servicer' }; control.opened = true; control.firmwareValid = true; control.capabilities.set('AEC_HPFONOFF', true);
  assert.equal(await control.write('AEC_HPFONOFF', 4), 4);
  assert.equal(calls.out, 1);
  assert.equal(calls.in, 1);
});

test('unknown devices cannot be written even when disconnected state is stale', async () => {
  const { device, calls } = usbHarness();
  device.vendorId = 0x1234; device.productId = 0x5678;
  const control = new ReSpeakerUSB(device); control.identity = identifyDevice(device); control.opened = true; control.firmwareValid = true;
  await assert.rejects(control.write('PP_MIN_NS', 0.2), /unavailable|capability/);
  assert.equal(calls.out, 0);
});

test('unknown device identity is explicitly audio-only', () => {
  const unknown = identifyDevice({ vendorId: 0x1234, productId: 0x5678, productName: 'mystery' });
  assert.equal(unknown.unknown, true);
  assert.equal(unknown.controlProtocol, 'audio-only');
  assert.equal(unknown.name, 'mystery');
});

test('complete native USB probe, DataView decode, write bytes, save and queued detach', async () => {
  const values = new Map([['48:0',[1,2,3]],['20:18',[90,1]],['17:21',0.25],['17:22',0.5],['17:23',1],['17:10',1],['33:1',2]]);
  const writes=[];
  const {device}=usbHarness();
  device.controlTransferIn=async(setup,length)=>{
    assert.deepEqual(setup,{requestType:'vendor',recipient:'device',request:0,value:setup.value,index:setup.index});
    const key=`${setup.index}:${setup.value&127}`,value=values.get(key),buffer=new ArrayBuffer(length+4),view=new DataView(buffer,2,length);
    if(value===undefined){view.setUint8(0,9);return {status:'ok',data:view};}
    if(key==='48:0')value.forEach((v,i)=>view.setUint8(i+1,v));
    else if(key==='20:18')value.forEach((v,i)=>view.setUint16(1+i*2,v,true));
    else if(['17:21','17:22'].includes(key))view.setFloat32(1,value,true);
    else view.setInt32(1,value,true);
    return {status:'ok',data:view};
  };
  device.controlTransferOut=async(setup,data)=>{
    assert.deepEqual(setup,{requestType:'vendor',recipient:'device',request:0,value:setup.value,index:setup.index});
    writes.push({setup,data:[...data]});const key=`${setup.index}:${setup.value}`;
    if(key!=='48:9'){const v=new DataView(data.buffer,data.byteOffset,data.byteLength);values.set(key,['17:21','17:22'].includes(key)?v.getFloat32(0,true):v.getInt32(0,true));}
    return {status:'ok',bytesWritten:data.byteLength};
  };
  const control=new ReSpeakerUSB(device),snap=await control.connect();
  assert.equal(snap.firmware,'1.2.3');assert.equal(snap.doaSupported,true);
  assert.deepEqual(await control.pollDoa(),{angle:90,speech:true});
  await control.write('PP_MIN_NS',0.75);assert.deepEqual(writes.at(-1).data,[0,0,64,63]);
  await control.write('AEC_HPFONOFF',4);assert.deepEqual(writes.at(-1).data,[4,0,0,0]);
  await control.save();assert.equal(writes.at(-1).setup.index,48);assert.equal(writes.at(-1).setup.value,9);assert.deepEqual(writes.at(-1).data,[1]);
  values.delete('17:21');assert.equal((await control.snapshot()).parameters.PP_MIN_NS.supported,false);
  await assert.rejects(control.write('PP_MIN_NS',0.5),/capability/);
  const before=writes.length,pending=control.write('PP_AGCONOFF',true);await control.disconnect();
  await assert.rejects(pending,/disconnected/);assert.equal(writes.length,before);
});

test('XVF3800 diagnostics decode into the snapshot but cannot be written', async () => {
  const replies = new Map([
    ['48:128', [0, 2, 1, 0]], ['35:143', [0, 8, 0]], ['35:147', [0, 7, 3]],
    ['33:131', [0, 1, 0, 0, 0]], ['33:163', [0, 1, 0, 0, 0]], ['17:141', [0, 0, 0, 200, 65]],
  ]);
  const { device, calls } = usbHarness({ inTransfer: async (_attempt, setup, length) => {
    const reply = replies.get(`${setup.index}:${setup.value}`);
    if (!reply) return { status: 'ok', data: Uint8Array.of(9) };
    assert.equal(length, reply.length);
    return { status: 'ok', data: Uint8Array.from(reply) };
  } });
  const control = new ReSpeakerUSB(device), snapshot = await control.connect();
  const expected = { AUDIO_MGR_OP_L: [8, 0], AUDIO_MGR_OP_R: [7, 3], AEC_AECCONVERGED: true, AEC_ASROUTONOFF: true, PP_AGCGAIN: 25 };
  for (const [key, value] of Object.entries(expected)) {
    assert.deepEqual(snapshot.parameters[key], { value, supported: true });
    assert.equal(PARAMETERS.some(parameter => parameter.key === key), false);
    assert.equal(snapshot.parameterDefinitions.some(parameter => parameter.key === key), false);
    await assert.rejects(control.write(key, value), /read-only/);
  }
  assert.equal(calls.out, 0);
  device.productId = 0x0018;
  const legacy = new ReSpeakerUSB(device);
  await assert.rejects(legacy.read('AUDIO_MGR_OP_L'), /unavailable/);
});

function routingHarness({ asr = 1, failWrites = [], ignoreWrites = [] } = {}) {
  const { device } = usbHarness();
  const routes = { 15: [7, 3], 19: [8, 1] }, writes = [];
  device.controlTransferIn = async (setup, length) => {
    assert.equal(setup.requestType, 'vendor'); assert.equal(setup.recipient, 'device'); assert.equal(setup.request, 0);
    if (setup.index === 33) {
      assert.equal(setup.value, 0xa3); assert.equal(length, 5);
      return { status: 'ok', data: Uint8Array.of(0, asr, 0, 0, 0) };
    }
    assert.equal(setup.index, 35); assert.equal(length, 3);
    return { status: 'ok', data: Uint8Array.of(0, ...routes[setup.value & 127]) };
  };
  device.controlTransferOut = async (setup, data) => {
    assert.deepEqual(setup, { requestType: 'vendor', recipient: 'device', request: 0, value: setup.value, index: 35 });
    writes.push({ command: setup.value, bytes: [...data] });
    if (failWrites.includes(writes.length)) throw new Error('simulated write failure');
    if (!ignoreWrites.includes(writes.length)) routes[setup.value] = [...data];
    return { status: 'ok', bytesWritten: data.length };
  };
  const control = new ReSpeakerUSB(device); control.opened = true; control.firmwareValid = true;
  return { control, routes, writes };
}

test('comparison routing writes exact uint8 pairs, verifies and restores previous routes', async () => {
  const { control, routes, writes } = routingHarness();
  const saved = await control.setComparisonRouting();
  assert.deepEqual(saved, { left: [7, 3], right: [8, 1] });
  assert.deepEqual(writes, [{ command: 15, bytes: [3, 0] }, { command: 19, bytes: [7, 3] }]);
  assert.deepEqual(routes, { 15: [3, 0], 19: [7, 3] });
  await control.restoreRouting(saved);
  assert.deepEqual(routes, { 15: [7, 3], 19: [8, 1] });
  await assert.rejects(control.write('AUDIO_MGR_OP_L', [1, 0]), /read-only/);
  assert.equal(writes.length, 4);
});

test('second routing write failure restores both sides and reports rollback success', async () => {
  const { control, routes, writes } = routingHarness({ failWrites: [2] });
  await assert.rejects(control.setComparisonRouting(), error => {
    assert.equal(error.rollbackSucceeded, true);
    assert.deepEqual(error.rollbackErrors, []);
    assert.deepEqual(error.previousRouting, { left: [7, 3], right: [8, 1] });
    return /rollback succeeded/.test(error.message);
  });
  assert.deepEqual(writes.slice(2), [{ command: 15, bytes: [7, 3] }, { command: 19, bytes: [8, 1] }]);
  assert.deepEqual(routes, { 15: [7, 3], 19: [8, 1] });
});

test('routing rollback failure is reported and still attempts the other side', async () => {
  const { control, writes } = routingHarness({ failWrites: [2, 3] });
  await assert.rejects(control.setComparisonRouting(), error => {
    assert.equal(error.rollbackSucceeded, false);
    assert.match(error.rollbackErrors[0], /left:/);
    return /rollback failed/.test(error.message);
  });
  assert.equal(writes.length, 4);
});

test('routing readback mismatch also rolls back instead of reporting success', async () => {
  const { control, routes } = routingHarness({ ignoreWrites: [2] });
  await assert.rejects(control.setComparisonRouting(), error => {
    assert.equal(error.rollbackSucceeded, true);
    return /right routing readback mismatch/.test(error.message);
  });
  assert.deepEqual(routes, { 15: [7, 3], 19: [8, 1] });
});

test('comparison routing rejects disabled ASR, legacy, and queued detach without writes', async () => {
  const disabled = routingHarness({ asr: 0 });
  await assert.rejects(disabled.control.setComparisonRouting(), /ASROUTONOFF=1/);
  assert.equal(disabled.writes.length, 0);
  const legacy = routingHarness(); legacy.control.identity.controlProtocol = 'xvf3000-legacy';
  await assert.rejects(legacy.control.setComparisonRouting(), /XVF3800/);
  await assert.rejects(legacy.control.restoreRouting({ left: [7, 3], right: [7, 3] }), /XVF3800/);
  assert.equal(legacy.writes.length, 0);
  const detached = routingHarness();
  const pending = detached.control.setComparisonRouting();
  await detached.control.disconnect();
  await assert.rejects(pending, /disconnected/);
  assert.equal(detached.writes.length, 0);
});

test('output catalog is frozen and every listed left/right combination is supported', async () => {
  assert.equal(OUTPUT_SIGNALS.length, 9);
  assert.ok(Object.isFrozen(OUTPUT_SIGNALS));
  for (const signal of OUTPUT_SIGNALS) {
    assert.ok(Object.isFrozen(signal)); assert.ok(Object.isFrozen(signal.route));
    assert.equal(signal.value, signal.route.join(':'));
  }
  for (const left of OUTPUT_SIGNALS) for (const right of OUTPUT_SIGNALS) {
    const { control, routes, writes } = routingHarness();
    await control.setOutputRouting({ left: left.route, right: right.route });
    assert.deepEqual(routes, { 15: left.route, 19: right.route });
    assert.deepEqual(writes, [{ command: 15, bytes: left.route }, { command: 19, bytes: right.route }]);
  }
});

test('generic output selection rejects unlisted routes without writing', async () => {
  const { control, writes } = routingHarness();
  for (const pair of [[1, 0], [3, 4], [6, -1], [7, 0], [8, 0], [3, 0, 1], ['3', 0], null]) {
    await assert.rejects(control.setOutputRouting({ left: pair, right: [6, 3] }), /Unsupported/);
    await assert.rejects(control.setOutputRouting({ left: [3, 0], right: pair }), /Unsupported/);
  }
  assert.equal(writes.length, 0);
});

test('disabled ASR allows microphone/processed routing but rejects category 7 on either side', async () => {
  const { control, routes, writes } = routingHarness({ asr: 0 });
  await control.setOutputRouting({ left: [6, 2], right: [3, 3] });
  assert.deepEqual(routes, { 15: [6, 2], 19: [3, 3] });
  await assert.rejects(control.setOutputRouting({ left: [7, 3], right: [3, 0] }), /ASROUTONOFF=1/);
  await assert.rejects(control.setOutputRouting({ left: [6, 1], right: [7, 3] }), /ASROUTONOFF=1/);
  assert.equal(writes.length, 2);
  await control.restoreRouting({ left: [8, 1], right: [0, 0] });
  assert.deepEqual(routes, { 15: [8, 1], 19: [0, 0] });
});

test('generic output selection rolls back both routes after a partial failure', async () => {
  const { control, routes } = routingHarness({ asr: 0, failWrites: [2] });
  await assert.rejects(control.setOutputRouting({ left: [6, 0], right: [3, 2] }), error => error.rollbackSucceeded === true);
  assert.deepEqual(routes, { 15: [7, 3], 19: [8, 1] });
});
