import {visualizationDefaults,applyVisualization} from './overlay.js';
import {tr, text, errorDetails, LocalizedError} from './i18n.js';
import {getJSON} from './api.js';
import {RoiEditor, validateRegions} from './roi-editor.js';

const $ = id => document.getElementById(id);
if (document.documentElement.classList.contains('embedded')) {
  document.body.appendChild(document.querySelector('.save-bar'));
}
const timingFields = [
  ['start_seconds', 'timing.start', 'timing.startHelp', .1],
  ['short_away_seconds', 'timing.away', 'timing.awayHelp', 0],
  ['stop_absent_seconds', 'timing.stop', 'timing.stopHelp', .1],
  ['missing_grace_seconds', 'timing.grace', 'timing.graceHelp', 0],
  ['max_observation_age', 'timing.age', 'timing.ageHelp', .1]
];
const detectionFields = [
  ['person_confidence', 'detection.person', 'detection.personHelp', .10],
  ['keypoint_confidence', 'detection.keypoint', 'detection.keypointHelp', .25]
];
const detectionDefaults = {person_confidence:.10, keypoint_confidence:.40};
let sourceDirty = false;
let sourceBusy = false;
let sourceToken = null;
let sourceTestRevision = null;
let usbDevices = [];
let base = null;
let dirty = false;
let roiDirty = false;
let reference = null;
let takingFrame = false;
let saving = false;
let latestRevision = null;
let privacyAtFrame = null;
let refreshEpoch = 0;

function message(key, type = '', params = {}) {
  text('message', key, params);
  $('message').className = type;
}
function messageError(error) {
  const details = errorDetails(error);
  message(details.key, 'error', details.params);
}
function updateSave() {
  $('saveSettings').disabled = !base || !dirty || saving || sourceBusy || !validDetection();
  $('saveSettings').textContent = saving ? tr('config.saving') : tr('config.save');
}
function changed() {
  dirty = true;
  message('config.dirty');
  updateSave();
}
const editor = new RoiEditor($('roiCanvas'), () => {
  roiDirty = true;
  changed();
  updateCounts();
});
const paletteKeys=['station','seat','person','skeleton','keypoint','anchor'];
function paletteValues() {
  return {colors:Object.fromEntries(paletteKeys.map(key=>[key,$('color_'+key).value])),
    station_fill_alpha:Number($('opacity_station').value)/100,seat_fill_alpha:Number($('opacity_seat').value)/100};
}
function previewPalette() {
  const value=paletteValues();
  editor.visualization=value;
  applyVisualization(value);
  editor.draw();
  for(const key of ['station','seat']) $('opacity_'+key+'Value').textContent=$('opacity_'+key).value+'%';
  const ctx=$('palettePreview').getContext('2d'),c=value.colors;
  ctx.clearRect(0,0,480,210);ctx.fillStyle='#0b1920';ctx.fillRect(0,0,480,210);
  for(const [key,x,y,w,h] of [['station',16,16,448,178],['seat',245,54,194,122]]) {
    ctx.globalAlpha=value[key+'_fill_alpha'];ctx.fillStyle=c[key];ctx.fillRect(x,y,w,h);ctx.globalAlpha=1;
    ctx.strokeStyle=c[key];ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);
    ctx.fillStyle=c[key];ctx.font='14px sans-serif';ctx.fillText(tr('visualization.'+key),x+8,y+20);
  }
  ctx.strokeStyle=c.person;ctx.lineWidth=3;ctx.strokeRect(120,44,90,140);
  const points=[[165,80],[140,105],[190,105],[150,140],[180,140],[140,170],[190,170]];
  ctx.strokeStyle=c.skeleton;ctx.lineWidth=3;
  for(const [a,b] of [[0,1],[0,2],[1,3],[2,4],[3,4],[3,5],[4,6]]){ctx.beginPath();ctx.moveTo(...points[a]);ctx.lineTo(...points[b]);ctx.stroke();}
  ctx.fillStyle=c.keypoint;
  for(const point of points){ctx.beginPath();ctx.arc(...point,4,0,2*Math.PI);ctx.fill();}
  ctx.strokeStyle=c.anchor;ctx.beginPath();ctx.arc(165,100,7,0,2*Math.PI);ctx.stroke();
}
function fillPalette(value) {
  for(const key of paletteKeys) $('color_'+key).value=value.colors[key];
  for(const key of ['station','seat']) $('opacity_'+key).value=String(value[key+'_fill_alpha']*100);
  previewPalette();
}
for(const key of paletteKeys) {
  const label=document.createElement('label');label.className='palette-row';
  const title=document.createElement('span');title.dataset.i18n='visualization.'+key;title.textContent=tr(title.dataset.i18n);
  const input=document.createElement('input');Object.assign(input,{type:'color',id:'color_'+key,value:visualizationDefaults().colors[key]});
  input.oninput=()=>{previewPalette();changed();};label.append(title,input);$('visualizationFields').append(label);
}
for(const key of ['station','seat']) {
  const label=document.createElement('label');label.className='palette-row opacity-row';
  const title=document.createElement('span');title.dataset.i18n='visualization.'+key+'Opacity';title.textContent=tr(title.dataset.i18n);
  const input=document.createElement('input');Object.assign(input,{type:'range',id:'opacity_'+key,min:'0',max:'100',step:'1',value:'10'});
  const output=document.createElement('output');output.id='opacity_'+key+'Value';
  input.oninput=()=>{previewPalette();changed();};label.append(title,input,output);$('visualizationFields').append(label);
}
$('restoreVisualization').onclick=()=>{fillPalette(base.visualization_defaults);changed();};
function updateCounts() {
  for (const name of ['station', 'seat']) $(name + 'Count').textContent = tr('roi.vertices', {count:editor.regions[name].length});
}
function privacyDescription() {
  const enabled = $('privacy').checked;
  $('privacyStatus').textContent = enabled ? tr('privacy.descriptionOn') : tr('privacy.descriptionOff');
  $('privacyStatus').classList.toggle('off', !enabled);
}
for (const [key, title, description, minimum] of timingFields) {
  const row = document.createElement('div');
  row.className = 'timing-row';
  const label = document.createElement('label');
  label.htmlFor = key;
  const titleNode = document.createElement('span');
  titleNode.dataset.i18n = title;
  titleNode.textContent = tr(title);
  label.appendChild(titleNode);
  const small = document.createElement('small');
  small.dataset.i18n = description;
  small.textContent = tr(description);
  label.appendChild(small);
  const wrapper = document.createElement('div');
  wrapper.className = 'number-input';
  const input = document.createElement('input');
  Object.assign(input, {id: key, type: 'number', min: String(minimum), max: '86400', step: '.1', required: true, inputMode: 'decimal'});
  input.addEventListener('input', changed);
  const unit = document.createElement('span');
  unit.dataset.i18n = 'timing.seconds';
  unit.textContent = tr('timing.seconds');
  wrapper.append(input, unit);
  row.append(label, wrapper);
  $('timingFields').appendChild(row);
}
function detectionValues() {
  return Object.fromEntries(detectionFields.map(([key]) => [key, Number($(key).value)]));
}
function validDetection() {
  return detectionFields.every(([key,,,minimum]) => $(key).value !== '' && Number.isFinite(Number($(key).value))
    && Number($(key).value) >= minimum && Number($(key).value) <= 1);
}
function validateDetection() {
  let invalid = false;
  for (const [key,,,minimum] of detectionFields) {
    const value = Number($(key).value);
    const valid = $(key).value !== '' && Number.isFinite(value) && value >= minimum && value <= 1;
    $(key).setAttribute('aria-invalid', String(!valid));
    invalid ||= !valid;
  }
  $('detectionError').hidden = !invalid;
  if (invalid) text('detectionError', 'detection.invalidInput');
}
function setDetectionValues(values) {
  for (const [key] of detectionFields) {
    $(key).value = String(values[key]);
    $(key+'Range').value = String(values[key]);
  }
  validateDetection();
}
for (const [key,title,description,minimum] of detectionFields) {
  const row = document.createElement('div');
  row.className = 'detection-row';
  const label = document.createElement('label');
  label.htmlFor = key;
  label.dataset.i18n = title;
  label.textContent = tr(title);
  const help = document.createElement('small');
  help.id = key+'Help';
  help.dataset.i18n = description;
  help.textContent = tr(description);
  const controls = document.createElement('div');
  controls.className = 'confidence-control';
  const range = document.createElement('input');
  Object.assign(range, {id:key+'Range', type:'range', min:String(minimum), max:'1', step:'.01'});
  range.setAttribute('aria-labelledby', key+'Label');
  const input = document.createElement('input');
  Object.assign(input, {id:key, type:'number', min:String(minimum), max:'1', step:'.01', required:true, inputMode:'decimal'});
  label.id = key+'Label';
  input.setAttribute('aria-describedby',help.id);
  input.addEventListener('input', () => {
    if (input.value !== '' && Number.isFinite(Number(input.value))) range.value = input.value;
    validateDetection();
    changed();
  });
  range.addEventListener('input', () => {
    input.value = Number(range.value).toFixed(2);
    validateDetection();
    changed();
  });
  controls.append(range,input);
  row.append(label,help,controls);
  $('detectionFields').appendChild(row);
}
$('restoreDetectionDefaults').onclick = () => {
  if (!base) return;
  setDetectionValues(base.detection_defaults);
  changed();
};

for (const id of ['privacy', 'boxes', 'station', 'seat', 'keypoints']) {
  $(id).addEventListener('change', () => {
    privacyDescription();
    changed();
  });
}

function fill(settings) {
  if (base && settings.revision !== base.revision) sourceToken = null;
  base = structuredClone(settings);
  base.visualization ??= visualizationDefaults();
  base.visualization_defaults ??= visualizationDefaults();
  fillPalette(base.visualization);
  base.detection ??= {...detectionDefaults};
  base.detection_defaults ??= {...detectionDefaults};
  setDetectionValues(base.detection);
  if (!sourceDirty) fillSource(settings.camera_source);
  latestRevision = settings.revision;
  $('revision').textContent = tr('config.effective', {revision:settings.revision});
  $('privacy').checked = settings.privacy.enabled;
  base.display.station ??= base.display.regions;
  base.display.seat ??= base.display.regions;
  for (const key of ['boxes', 'station', 'seat', 'keypoints']) $(key).checked = base.display[key];
  for (const [key] of timingFields) $(key).value = settings.timing[key];
  privacyDescription();
  editor.load(settings.regions, settings.image_size);
  updateCounts();
  dirty = false;
  roiDirty = false;
  sourceButtons();
}

async function takeFrame() {
  if (takingFrame) return;
  takingFrame = true;
  $('refreshFrame').disabled = true;
  const epoch = ++refreshEpoch;
  try {
    const camera = await getJSON('/api/v1/camera');
    if (camera.status !== 'online') throw new LocalizedError('roi.offline');
    const response = await fetch('/api/v1/video.jpg?t=' + Date.now(), {cache: 'no-store', signal: AbortSignal.timeout(5000)});
    if (!response.ok) throw new LocalizedError('roi.preparing');
    const revision = Number(response.headers.get('X-Config-Revision'));
    const applied = response.headers.get('X-Privacy-Applied') === 'true';
    if (Number.isFinite(revision) && latestRevision !== null && revision !== latestRevision) throw new LocalizedError('roi.revisionChanged');
    if (response.headers.get('X-Stream-Session-ID') !== camera.stream_session_id) throw new LocalizedError('roi.streamChanged');
    const blobURL = URL.createObjectURL(await response.blob());
    try {
      const image = new Image();
      image.src = blobURL;
      await image.decode();
      if (epoch !== refreshEpoch) return;
      const size = [camera.width, camera.height];
      if (editor.size.some((v, i) => v !== size[i])) {
        editor.load({station: [], seat: []}, size);
        roiDirty = true;
        dirty = true;
        message('roi.sizeChanged', 'warning');
      }
      editor.setImage(image, size);
      reference = {stream_session_id: camera.stream_session_id, image_size: size, camera_changed: Boolean(camera.camera_changed)};
      privacyAtFrame = applied;
      $('frameEmpty').hidden = true;
      $('imageLabel').textContent = size[0] + ' × ' + size[1] + ' · ' + tr(applied ? 'privacy.on' : 'privacy.off');
      updateCounts();
      updateSave();
    } finally {
      URL.revokeObjectURL(blobURL);
    }
  } catch (error) {
    reference = null;
    editor.clearImage();
    $('frameEmpty').hidden = false;
    const details = errorDetails(error);
    text('frameEmpty', details.key, details.params);
  } finally {
    takingFrame = false;
    $('refreshFrame').disabled = false;
  }
}

async function reload() {
  try {
    const settings = await getJSON('/api/v1/settings');
    fill(settings);
    message('config.loaded');
    await takeFrame();
  } catch (error) {
    message('config.loadFailed', 'error');
  }
}

for (const button of document.querySelectorAll('[data-region]')) {
  button.addEventListener('click', () => {
    editor.setRegion(button.dataset.region);
    for (const tab of document.querySelectorAll('[data-region]')) {
      const active = tab === button;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-pressed', String(active));
    }
    text('regionDescription', button.dataset.region === 'station' ? 'roi.stationHelp' : 'roi.seatHelp');
  });
}
const toolHints = {rectangle:'roi.rectangleHint', polygon:'roi.polygonHint', edit:'roi.editHint'};
for (const button of document.querySelectorAll('[data-tool]')) {
  button.addEventListener('click', () => {
    editor.setTool(button.dataset.tool);
    for (const tool of document.querySelectorAll('[data-tool]')) {
      tool.classList.toggle('active', tool === button);
      tool.setAttribute('aria-pressed', String(tool === button));
    }
    text('editorHint', toolHints[button.dataset.tool]);
  });
}
$('finishPolygon').onclick = () => editor.finishPolygon();
$('undo').onclick = () => editor.undo();
$('clearRegion').onclick = () => editor.clearRegion();
$('refreshFrame').onclick = takeFrame;
$('confirmRegions').onclick = () => {
  if (!reference || !editor.image) {
    message('roi.needsFrame', 'warning');
    return;
  }
  try {
    validateRegions(editor.regions, editor.size);
    roiDirty = true;
    changed();
    message('roi.confirmed');
  } catch (error) { messageError(error); }
};
$('cancelChanges').onclick = () => { sourceDirty = false; sourceToken = null; return reload(); };
$('fullscreen').onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await $('editorPanel').requestFullscreen();
    editor.draw();
  } catch {
    message('roi.noFullscreen', 'warning');
  }
};
document.addEventListener('fullscreenchange', () => {
  text('fullscreen', document.fullscreenElement ? 'video.exitFullscreen' : 'video.fullscreen');
  editor.draw();
});
window.addEventListener('resize', () => editor.draw());
$('restoreDefaults').onclick = () => {
  if (!base) return;
  for (const [key] of timingFields) $(key).value = base.defaults[key];
  changed();
};

$('saveSettings').onclick = async () => {
  if (!base || saving) return;
  const request = {expected_revision: base.revision};
  const privacy = {enabled: $('privacy').checked};
  const display = Object.fromEntries(['boxes', 'station', 'seat', 'keypoints'].map(key => [key, $(key).checked]));
  display.regions=display.station||display.seat;
  const timing = Object.fromEntries(timingFields.map(([key]) => [key, Number($(key).value)]));
  const detection = detectionValues();
  try {
    if (!validDetection()) throw new LocalizedError('detection.invalidInput');
    for (const [key] of timingFields) if (!$(key).checkValidity()) throw new LocalizedError('timing.invalid');
    if (JSON.stringify(privacy) !== JSON.stringify(base.privacy)) request.privacy = privacy;
    if (JSON.stringify(display) !== JSON.stringify(base.display)) request.display = display;
    if (JSON.stringify(timing) !== JSON.stringify(base.timing)) request.timing = timing;
    if (JSON.stringify(detection) !== JSON.stringify(base.detection)) request.detection = detection;
    if (JSON.stringify(paletteValues()) !== JSON.stringify(base.visualization)) request.visualization=paletteValues();
    if (roiDirty) {
      if (editor.draft.length) throw new LocalizedError('roi.unfinished');
      if (!reference || !editor.image) throw new LocalizedError('roi.saveNeedsFrame');
      validateRegions(editor.regions, editor.size);
      request.regions = structuredClone(editor.regions);
      request.image_size = editor.size.slice();
      request.reference_frame = reference;
    }
    if (Object.keys(request).length === 1) {
      dirty = false;
      updateSave();
      message('config.same');
      return;
    }
    saving = true;
    updateSave();
    const result = await getJSON('/api/v1/settings', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)});
    fill(result);
    editor.clearImage();
    reference = null;
    message(request.regions || request.timing || request.detection ? 'config.savedTiming' : 'config.saved');
    await new Promise(resolve => setTimeout(resolve, 400));
    await takeFrame();
  } catch (error) {
    if (error.status === 409) message('config.conflict', 'error');
    else messageError(error);
  } finally {
    saving = false;
    updateSave();
  }
};

async function poll() {
  try {
    const current = await getJSON('/api/v1/settings');
    latestRevision = current.revision;
    $('revision').textContent = tr('config.effective', {revision:current.revision});
    const online = current.camera.status === 'online';
    if (current.camera.stream_session_id?.startsWith('mock')) text('connection', 'camera.mock');
    else if (online) text('connection', 'camera.onlineFps', {fps:current.camera.output_fps ?? '—'});
    else text('connection', 'camera.connectingShort');
    if (online && (current.camera.camera_changed || current.camera.regions_match === false) && !dirty) message('config.positionWarning', 'warning');
    $('connection').classList.toggle('offline', !online);
    if (!online || (reference && reference.stream_session_id !== current.camera.stream_session_id)) reference = null;
    if (base && current.revision !== base.revision) {
      if (dirty || sourceDirty) message('config.externalChange', 'warning');
      else fill(current);
    }
    if (privacyAtFrame !== null && privacyAtFrame !== current.privacy.enabled) {
      editor.clearImage();
      reference = null;
      privacyAtFrame = null;
      await takeFrame();
    }
  } catch {
    text('connection', 'camera.deviceLost');
    $('connection').classList.add('offline');
    reference = null;
  }
  setTimeout(poll, 1000);
}
window.addEventListener('languagechange', () => {
  updateSave();
  updateCounts();
  privacyDescription();
  validateDetection();
  if (latestRevision !== null) text('revision', 'config.effective', {revision:latestRevision});
  text('regionDescription', editor.region === 'station' ? 'roi.stationHelp' : 'roi.seatHelp');
  text('editorHint', toolHints[editor.tool]);
  if (privacyAtFrame !== null) $('imageLabel').textContent = editor.size[0] + ' × ' + editor.size[1] + ' · ' + tr(privacyAtFrame ? 'privacy.on' : 'privacy.off');
  editor.draw();
});
function sourceVisibility() {
  const usb = $('sourceType').value === 'usb';
  $('usbFields').hidden = !usb;
  $('rtspFields').hidden = usb;
}
function sourceButtons() {
  updateSave();
  $('testSource').disabled = !base || sourceBusy;
  $('saveSource').disabled = !base || sourceBusy || !sourceToken;
  $('refreshDevices').disabled = sourceBusy;
  for (const id of sourceInputs) $(id).disabled = sourceBusy;
}
function sourceMessage(key, type = '', params = {}) {
  text('sourceMessage', key, params);
  $('sourceMessage').className = type;
}
function sourceError(error) {
  const details = errorDetails(error);
  sourceMessage(details.key, 'error', details.params);
}
function fillSource(source) {
  if (!source) return;
  $('sourceType').value = source.type === 'usb' ? 'usb' : 'rtsp';
  $('sourceUrl').value = source.url || '';
  $('sourceUsername').value = source.username || '';
  $('sourcePassword').value = '';
  $('sourceCodec').value = source.codec || 'h264';
  if (source.type === 'usb') {
    $('sourceDevice').replaceChildren(new Option(source.device, source.device));
    $('sourceFormat').replaceChildren(new Option(source.format.toUpperCase(), source.format));
  }
  text('sourceCurrent', source.type === 'unconfigured' ? 'source.unconfigured' : source.type === 'usb' ? 'source.usb' : 'source.rtsp');
  sourceVisibility();
}
function candidateSource() {
  if ($('sourceType').value === 'usb') return {type:'usb', device:$('sourceDevice').value, format:$('sourceFormat').value};
  return {type:'rtsp', url:$('sourceUrl').value.trim(), username:$('sourceUsername').value, password:$('sourcePassword').value, codec:$('sourceCodec').value};
}
function sourceChanged() {
  sourceDirty = true;
  sourceToken = null;
  sourceMessage('source.needsTest');
  sourceButtons();
}
function usbFormats() {
  const device = usbDevices.find(item => item.device === $('sourceDevice').value);
  $('sourceFormat').replaceChildren(...(device?.formats || []).map(format => new Option(format.toUpperCase(), format)));
}
async function refreshDevices() {
  try {
    const result = await getJSON('/api/v1/camera/devices');
    usbDevices = result.devices;
    const selected = $('sourceDevice').value;
    $('sourceDevice').replaceChildren(...usbDevices.map(item => new Option(item.name + ' · ' + item.device, item.device)));
    if (usbDevices.some(item => item.device === selected)) $('sourceDevice').value = selected;
    usbFormats();
    if (!usbDevices.length) sourceMessage('source.noUsb');
  } catch (error) { sourceError(error); }
}
const sourceInputs = ['sourceType','sourceUrl','sourceUsername','sourcePassword','sourceCodec','sourceDevice','sourceFormat'];
for (const id of sourceInputs) $(id).addEventListener('input', sourceChanged);
$('sourceType').addEventListener('change', async () => {
  sourceVisibility();
  if ($('sourceType').value === 'usb') await refreshDevices();
});
$('sourceDevice').addEventListener('change', usbFormats);
$('refreshDevices').onclick = async () => { sourceChanged(); await refreshDevices(); };
$('testSource').onclick = async () => {
  sourceBusy = true;
  sourceToken = null;
  sourceButtons();
  sourceMessage('source.testing');
  try {
    const result = await getJSON('/api/v1/camera/test', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({expected_revision:base.revision, camera_source:candidateSource()}), signal:AbortSignal.timeout(15000)});
    sourceToken = result.test_token;
    sourceTestRevision = base.revision;
    sourceMessage('source.testPassed', 'success', {width:result.width, height:result.height});
  } catch (error) { sourceError(error); }
  finally { sourceBusy = false; sourceButtons(); }
};
$('saveSource').onclick = async () => {
  const otherDraft = $('privacy').checked !== base.privacy.enabled
    || ['boxes','station','seat','keypoints'].some(key => $(key).checked !== base.display[key])
    || timingFields.some(([key]) => Number($(key).value) !== base.timing[key])
    || JSON.stringify(paletteValues()) !== JSON.stringify(base.visualization)
    || !validDetection()
    || detectionFields.some(([key]) => Number($(key).value) !== base.detection[key]);
  if (otherDraft) { sourceMessage('source.otherDraft', 'error'); return; }
  sourceBusy = true;
  sourceButtons();
  sourceMessage('source.switching');
  try {
    const result = await getJSON('/api/v1/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({expected_revision:sourceTestRevision, camera_source:candidateSource(), test_token:sourceToken}), signal:AbortSignal.timeout(15000)});
    sourceDirty = false;
    sourceToken = null;
    fill(result);
    reference = null;
    editor.clearImage();
    sourceMessage('source.switched', 'success');
    message('source.roiRequired', 'warning');
    await new Promise(resolve => setTimeout(resolve, 1200));
    await takeFrame();
  } catch (error) { sourceError(error); }
  finally { sourceBusy = false; sourceButtons(); }
};
await reload();
sourceButtons();
poll();

window.addEventListener('languagechange',()=>previewPalette());
