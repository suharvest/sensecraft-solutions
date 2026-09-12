import { ReSpeakerUSB, PARAMETERS, OUTPUT_SIGNALS } from './device.mjs';
import { AudioCapture, wavBlob } from './audio.mjs';

const $ = id => document.getElementById(id);
const capture = new AudioCapture();
let usb = null, snapshot = null, usbEpoch = 0, doaTimer = null, configA = null;
let running = false, starting = false, recording = false, transcribing = false, lastRecord = null;
let signalView='energy', waveZoom=16, workspaceTab='noise', zeroSince=null;
let latestFrame = null, actualChannels = 0, lastDoa = null;
let worker = null, modelReady = false, modelLoading = false, recordId = 0;
let histories = [], parameterTimers = new Map(), pendingWrites = 0, playbackUrl = null;
let savedRouting=null;
const recordUrls = {};
const jobs = new Map(), parameterEvents = [];
const palette = [[16,26,48],[55,83,160],[24,185,174],[244,189,90],[245,87,139]];

function notice(message, error = false) { $('notice').textContent = message; $('notice').classList.toggle('error', error); }
function errorText(error) { return error?.message || String(error); }
function color(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function resolvedColor(name) { const probe=document.createElement('span');probe.style.color=`var(${name})`;probe.hidden=true;document.body.append(probe);const result=getComputedStyle(probe).color;probe.remove();return result; }
function db(value) { return 20 * Math.log10(Math.max(1e-8, value)); }
function formatValue(value) { return typeof value === 'boolean' ? (value ? '开' : '关') : typeof value === 'number' ? Number(value.toFixed(3)).toString() : String(value ?? '—'); }
function addEvent(message) { parameterEvents.unshift(`${new Date().toLocaleTimeString()} · ${message}`);parameterEvents.splice(5);$('parameter-events').replaceChildren(...parameterEvents.map(text=>{const li=document.createElement('li');li.textContent=text;return li;})); }
function currentMap() { return { original:Number($('original-channel').value || 0), processed:$('processed-channel').value === '' ? null : Number($('processed-channel').value) }; }
function editableParameters() { return (snapshot?.parameterDefinitions||PARAMETERS).filter(p=>!p.readOnly&&!p.writeOnly&&!['VERSION','DOA_VALUE','SAVE_CONFIGURATION'].includes(p.key)); }
function supportedParameters() { return editableParameters().filter(p=>snapshot?.parameters?.[p.key]?.supported); }
function liteAudioSelected() { const option=$('audio-input')?.selectedOptions?.[0]; return !usb&&Boolean($('audio-input')?.value)&&/reSpeaker Lite/i.test(option?.textContent||''); }
function liteControlsHidden() { return snapshot?.identity?.controlProtocol==='audio-only'||liteAudioSelected(); }
function updateLiteUi() {
  const lite=liteControlsHidden();
  const note=$('control-capability-note');
  if(note) { note.classList.toggle('hidden',!lite); note.textContent=lite?'当前设备的 USB 固件未提供本工具已适配的 USB 调参接口；Lite 支持板载降噪等音频处理，由设备固件执行；网页仍可采集、录音与转录。':''; }
  $('noise-tools')?.classList.toggle('hidden',lite||workspaceTab==='echo');
  for(const id of ['echo-tuning','gain-tools','all-noise-section','all-echo-section','all-gain-section'])$(id)?.classList.toggle('hidden',lite);
  if($('parameter-status')&&lite)$('parameter-status').textContent='Lite 的板载音频处理由设备固件执行；当前 USB 固件未提供本工具已适配的调参接口。';
}
function cancelWrites() { for(const t of parameterTimers.values())clearTimeout(t);parameterTimers.clear(); }
function setBusy() {
  updateLiteUi();
  const hasParameters=supportedParameters().length>0;
  const liteAudio=liteAudioSelected();
  const routeSupported=snapshot?.identity?.controlProtocol==='xvf3800-servicer'&&snapshot?.parameters?.AUDIO_MGR_OP_L?.supported&&snapshot?.parameters?.AUDIO_MGR_OP_R?.supported;
  $('channel-selection').classList.toggle('hidden',actualChannels<=2);
  $('output-routing-panel').classList.toggle('hidden',!routeSupported);
  document.querySelector('.routing-actions')?.classList.toggle('hidden',!routeSupported);
  $('stereo-routing-note').textContent=actualChannels===2?(routeSupported?'浏览器只接收左、右两路；下方可从设备内部的麦克风与处理后信号中，分别选择一路输出。':'当前输入为左、右两路，无需选择浏览器通道；信号用途由当前固件决定。'):actualChannels>2?'选择需要观察的两路；设备输出路由与浏览器通道选择是不同设置。':'开始采集后显示实际输入通道。';
  if(!usb)$('doa-status').textContent=liteAudio?'当前 Lite USB 接入不提供声源方向数据':'USB 控制未连接';
  for(const tab of document.querySelectorAll('[data-workspace]'))tab.disabled=!snapshot&&!running;
  for(const id of ['output-left','output-right','apply-output-routing'])$(id).disabled=!routeSupported||recording||pendingWrites>0||parameterTimers.size>0;
  $('restore-output-routing').disabled=!routeSupported||!savedRouting||recording||pendingWrites>0||parameterTimers.size>0;
  $('setup-comparison').disabled=!routeSupported||recording||pendingWrites>0||parameterTimers.size>0;
  $('restore-routing').disabled=!routeSupported||!savedRouting||recording||pendingWrites>0||parameterTimers.size>0;
  $('connect-usb').disabled=recording||pendingWrites>0;
  $('disconnect-usb').disabled=!usb||recording;
  $('start-audio').disabled=running||starting||!$('audio-input').value;
  $('stop-audio').disabled=!running||starting;
  $('audio-input').disabled=running||starting;
  $('authorize-audio').disabled=running||starting;
  $('original-channel').disabled=!running||recording||actualChannels<=2;
  $('processed-channel').disabled=!running||recording||actualChannels<=2;
  $('confirm-map').disabled=!running||recording||currentMap().processed===null||matchingOutputRoutes();
  $('save-a').disabled=!hasParameters||recording||pendingWrites>0||parameterTimers.size>0;
  $('restore-a').disabled=!configA||!hasParameters||recording||pendingWrites>0||parameterTimers.size>0;
  $('save-flash').disabled=snapshot?.canSave===false||!hasParameters||recording||pendingWrites>0||parameterTimers.size>0;
  $('record-input-note').textContent=!running?'先连接音频并开始采集，即可录音；无需加载转录模型。':`将同步录制全部 ${actualChannels} 路 USB 输入 · 6 秒；录完可逐路试听`;
  $('record').disabled=!running||actualChannels===0||recording||pendingWrites>0||parameterTimers.size>0||transcribing;
  $('record').textContent=recording?'正在录音…':lastRecord?'重新录制 · 6 秒':'开始录音 · 6 秒';
  $('transcribe').disabled=!lastRecord||recording||transcribing;
  for(const element of document.querySelectorAll('.parameter-grid input,.parameter-grid select'))element.disabled=recording||pendingWrites>0||!snapshot?.parameters?.[element.dataset.key]?.supported;
}

async function connectUsb() {
  cancelWrites();clearTimeout(doaTimer);
  const previous=usb;usb=null;if(previous)await previous.disconnect().catch(()=>{});
  const token=++usbEpoch;
  snapshot=null;configA=null;savedRouting=null;lastDoa=null;renderParameters();drawDoa();
  const device=new ReSpeakerUSB();usb=device;
  device.addEventListener('disconnect',()=>{if(usb===device)clearUsb('USB 控制已断开。重新连接后会重新读取固件与参数。');});
  $('usb-status').textContent='等待选择设备与读取能力…';$('connect-usb').disabled=true;
  try {
    const result=await device.connect();
    if(token!==usbEpoch){await device.disconnect();return;}
    snapshot=result;if(matchingOutputRoutes())$('confirm-map').checked=false;if(actualChannels>0)updateMap();
    $('device-name').textContent=result.identity.name;
    const firmware=result.identity.controlProtocol==='audio-only'?'未读取版本':result.firmware||result.parameters?.VERSION?.value?.join?.('.')||'不可读取';
    $('usb-info').textContent=`固件 ${firmware} · ${result.identity.physicalMics??'未知'} 麦 · ${device.device?.productName||result.identity.name}`;
    const available=supportedParameters().length;
    $('usb-status').textContent=available?`已读取 ${available} 个可调参数 · 音频需在右侧单独选择`:`音频模式 · ${result.identity.notes||'此固件未提供可用的 USB 控制接口'}`;
    $('doa-status').textContent=result.doaSupported?'等待设备 DOA 数据':'当前型号或固件未提供可读 DOA';
    notice('USB 设备已识别。请选择同一台 reSpeaker 的音频输入，确认声道用途后再进行前后对比。');
    if(!result.firmware&&result.identity.controlProtocol!=='audio-only'){notice('设备已识别，但控制读取失败。请重新连接 USB；音频可单独检查。',true);$('usb-status').textContent='控制读取失败 · 固件未响应';}renderParameters();pollDoa(token);
  } catch(error) { if(token===usbEpoch){snapshot=null;notice(`USB 控制连接失败：${errorText(error)}。仍可尝试右侧的 USB 声卡采集。`,true);$('usb-status').textContent=`控制连接失败：${errorText(error)}`;} }
  finally {setBusy();}
}
function clearUsb(message) {
  ++usbEpoch;cancelWrites();clearTimeout(doaTimer);savedRouting=null;snapshot=null;configA=null;usb=null;lastDoa=null;
  $('device-name').textContent='连接 reSpeaker';$('usb-info').textContent='XVF3000 / XVF3800 / Flex / Lite · 按型号与固件识别能力';$('usb-status').textContent=message;
  $('doa-status').textContent=liteAudioSelected()?'当前 Lite USB 接入不提供声源方向数据':'USB 控制未连接';$('parameter-status').textContent='连接 USB 后读取可用参数';$('confirm-map').checked=false;if(actualChannels>0)updateMap();renderParameters();drawDoa();setBusy();
}
async function pollDoa(token) {
  if(token!==usbEpoch||!snapshot?.doaSupported||!usb)return;
  try { const value=await usb.pollDoa();if(token!==usbEpoch)return;lastDoa=value&&Number.isFinite(value.angle)?value:null;drawDoa();$('doa-status').textContent=!lastDoa?'方向读取暂不可用':lastDoa.speech?'检测到语音 · 设备报告方向，不表示距离':'最近设备方向 · 当前语音标记未触发'; }
  catch {lastDoa=null;drawDoa();}
  if(token===usbEpoch)doaTimer=setTimeout(()=>pollDoa(token),200);
}
async function configureRouting(mode='preset'){
  const restore=mode==='restore';
  if(!usb||recording||pendingWrites||parameterTimers.size)return;
  const device=usb,epoch=usbEpoch;pendingWrites++;setBusy();setRoutingStatus('正在设置运行路由并回读…');
  try{
    if(restore){await device.restoreRouting(savedRouting);savedRouting=null;}
    else{const previous=mode==='custom'?await device.setOutputRouting({left:$('output-left').value.split(':').map(Number),right:$('output-right').value.split(':').map(Number)}):await device.setComparisonRouting();savedRouting??=previous;}
    if(epoch!==usbEpoch)return;
    const values={};for(const key of ['AUDIO_MGR_OP_L','AUDIO_MGR_OP_R'])values[key]={supported:true,value:await device.read(key)};
    if(epoch!==usbEpoch)return;Object.assign(snapshot.parameters,values);histories=Array.from({length:actualChannels},()=>[]);latestFrame=null;
    $('confirm-map').checked=false;if(actualChannels>=2){$('original-channel').value='0';$('processed-channel').value='1';}updateMap();renderDiagnostics();
    setRoutingStatus(restore?'已恢复原路由并回读确认。':`已应用：左路 ${outputSignalLabel('left')}；右路 ${outputSignalLabel('right')}。未保存到 Flash。`);
  }catch(error){if(epoch===usbEpoch){if(error.previousRouting)savedRouting??=error.previousRouting;setRoutingStatus(`路由设置失败：${errorText(error)}`);}}
  finally{pendingWrites--;setBusy();}
}
function setRoutingStatus(text){$('routing-status').textContent=text;$('output-routing-status').textContent=text;}
function outputSignalLabel(side){
  const status=snapshot?.parameters?.[side==='left'?'AUDIO_MGR_OP_L':'AUDIO_MGR_OP_R'];
  if(!status?.supported)return '信号用途待确认';
  if(status.value[0]===7&&snapshot.parameters.AEC_ASROUTONOFF?.value!==true)return snapshot.parameters.AEC_ASROUTONOFF?.supported?`AEC 残差 · 麦克风 ${status.value[1]+1}`:'AEC / ASR 信号（模式未读出）';
  const value=status.value.join(':');return OUTPUT_SIGNALS.find(option=>option.value===value)?.label||`固件信号 [${status.value.join(', ')}]`;
}
function channelLabel(index){
  const product=usb?.device?.productName,input=$('audio-input').selectedOptions[0]?.textContent||'';
  if(actualChannels===2&&product&&input.includes(product)&&snapshot?.parameters?.AUDIO_MGR_OP_L?.supported&&snapshot?.parameters?.AUDIO_MGR_OP_R?.supported)return `${index===0?'左':'右'} · ${outputSignalLabel(index===0?'left':'right')}`;
  return actualChannels===2?`${index===0?'左':'右'}声道 · USB ${index+1}`:`USB 通道 ${index+1}`;
}
function renderOutputSelectors(){
  for(const side of ['left','right']){
    const select=$(`output-${side}`),status=snapshot?.parameters?.[side==='left'?'AUDIO_MGR_OP_L':'AUDIO_MGR_OP_R'];
    select.replaceChildren();
    if(!status?.supported){select.append(new Option('连接 XVF3800 USB 控制后选择',''));continue;}
    for(const signal of OUTPUT_SIGNALS){const option=new Option(signal.label,signal.value);option.disabled=signal.route[0]===7&&snapshot.parameters.AEC_ASROUTONOFF?.value!==true;select.append(option);}
    const current=status.value.join(':');if(!OUTPUT_SIGNALS.some(signal=>signal.value===current)){const option=new Option(outputSignalLabel(side),current);option.disabled=true;select.append(option);}select.value=current;if(status.value[0]===7&&snapshot.parameters.AEC_ASROUTONOFF?.value!==true)select.selectedOptions[0].textContent=outputSignalLabel(side);
  }
}
function matchingOutputRoutes(){
  const left=snapshot?.parameters?.AUDIO_MGR_OP_L,right=snapshot?.parameters?.AUDIO_MGR_OP_R;
  return left?.supported&&right?.supported&&Array.isArray(left.value)&&JSON.stringify(left.value)===JSON.stringify(right.value);
}
function renderDiagnostics(){renderOutputSelectors();
  const params=snapshot?.parameters||{},left=params.AUDIO_MGR_OP_L,right=params.AUDIO_MGR_OP_R;
  $('hardware-route-note').textContent=left?.supported&&right?.supported?`设备输出（最近回读）：左 [${left.value.join(', ')}] · 右 [${right.value.join(', ')}]。${matchingOutputRoutes()?'左右输出为同一信号，不能作为处理前后对比。':'通道用途仍需结合固件确认。'}`:'';
  $('aec-diagnostic').textContent=params.AEC_AECCONVERGED?.supported?`AEC 状态（连接时读取）：${params.AEC_AECCONVERGED.value?'已收敛':'未收敛'}。需播放参考声音后观察，未收敛不等于未开启。`:'';
  $('gain-diagnostic').textContent=params.PP_AGCGAIN?.supported?`当前 AGC 增益（连接时读取）：${formatValue(params.PP_AGCGAIN.value)} 倍`:'';
}
function renderParameters(){
  renderDiagnostics();
  if(liteControlsHidden()){
    for(const id of ['all-noise-parameters','all-echo-parameters','all-gain-parameters','noise-parameters','echo-parameters','gain-parameters'])$(id).replaceChildren();
    updateLiteUi();
    return;
  }
  if($('parameter-status'))$('parameter-status').textContent=snapshot?'已读取设备参数':'连接 USB 后读取可用参数';
  for(const [id,category]of [['all-noise-parameters','noise'],['all-echo-parameters','echo'],['all-gain-parameters','gain'],['noise-parameters','noise'],['echo-parameters','echo'],['gain-parameters','gain']])renderParameterGroup($(id),category);
}
function renderParameterGroup(container,category) {
  container.replaceChildren();
  if(!snapshot){const p=document.createElement('p');p.className='empty';p.textContent='尚未读取设备参数。连接后只启用固件实际支持的控制项。';container.append(p);return;}
  const entries=editableParameters().filter(p=>p.group===category);
  for(const parameter of entries) {
    const status=snapshot.parameters?.[parameter.key],wrap=document.createElement('div');wrap.className=`param param-${parameter.type}`;
    const label=document.createElement('label'),name=document.createElement('span'),value=document.createElement('output'),code=document.createElement('code');
    name.textContent=parameter.label;value.textContent=status?.supported?(parameter.options?.find(option=>option.value===status.value)?.label??formatValue(status.value)):'不可用';label.append(name,value);code.textContent=parameter.key;
    const input=document.createElement(parameter.type==='enum'?'select':'input');input.dataset.key=parameter.key;input.id=`${container.id}-${parameter.key}`;label.htmlFor=input.id;
    if(parameter.type==='enum') {for(const option of parameter.options||[]){const el=document.createElement('option');el.value=option.value;el.textContent=option.label;input.append(el);}input.value=status?.value??0;}
    else if(parameter.type==='bool'){input.type='checkbox';input.checked=Boolean(status?.value);}
    else {input.type='range';input.min=parameter.min;input.max=parameter.max;input.step=parameter.step;input.value=status?.value??parameter.min;input.style.setProperty('--range-fill',`${(Number(input.value)-parameter.min)/(parameter.max-parameter.min)*100}%`);}
    const hint=document.createElement('p');hint.className='meta';hint.textContent=status?.supported?(parameter.key.includes('MIN_N')?'增益下限越小，噪声抑制越强；需同时试听人声。':'改变后读取设备返回值。'):`${status?.error||'当前固件未开放此参数'}`;
    hint.id=`${input.id}-hint`;input.setAttribute('aria-describedby',hint.id);input.disabled=!status?.supported||recording;
    input.addEventListener(parameter.type==='float'?'input':'change',()=>{
      if(recording||!snapshot?.parameters?.[parameter.key]?.supported)return;
      const next=parameter.type==='bool'?input.checked:Number(input.value);value.textContent=`${parameter.options?.find(option=>option.value===next)?.label??formatValue(next)} · 待回读`;if(input.type==='range')input.style.setProperty('--range-fill',`${(next-parameter.min)/(parameter.max-parameter.min)*100}%`);
      clearTimeout(parameterTimers.get(parameter.key));const epoch=usbEpoch;
      parameterTimers.set(parameter.key,setTimeout(()=>{parameterTimers.delete(parameter.key);if(epoch===usbEpoch)applyParameter(parameter.key,next,epoch);},250));setBusy();
    });
    wrap.append(label,code,input,hint);container.append(wrap);
  }
  if(!entries.length){const p=document.createElement('p');p.textContent='此设备没有这一组可用的控制项。';container.append(p);}
  setBusy();
}
async function applyParameter(key,next,epoch=usbEpoch) {
  if(!usb||epoch!==usbEpoch||recording)return;
  const device=usb,old=snapshot.parameters[key]?.value;pendingWrites++;setBusy();$('parameter-status').textContent=`正在写入 ${key}…`;
  try {const actual=await device.write(key,next);if(epoch!==usbEpoch)return;snapshot.parameters[key]={value:actual,supported:true};$('parameter-status').textContent=`${key} 回读确认：${formatValue(actual)}`;addEvent(`${key} ${formatValue(old)} → ${formatValue(actual)}`);}
  catch(error){if(epoch===usbEpoch){$('parameter-status').textContent=`${key} 未确认：${errorText(error)}`;notice(`调参失败：${errorText(error)}`,true);}}
  finally {pendingWrites--;if(epoch===usbEpoch)renderParameters();setBusy();}
}

async function listInputs(authorize=false) {
  try {
    if(authorize){const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());}
    const previous=$('audio-input').value,devices=await capture.listInputs();$('audio-input').replaceChildren(new Option('选择 reSpeaker 音频设备',''));
    devices.filter(d=>d.deviceId&&!['default','communications'].includes(d.deviceId)).forEach((d,i)=>$('audio-input').append(new Option(d.label||`音频输入 ${i+1}（未授权名称）`,d.deviceId)));
    if([...$('audio-input').options].some(o=>o.value===previous))$('audio-input').value=previous;
    if(authorize)notice('已授权麦克风。请在列表中明确选择 reSpeaker，再开始采集。');
  }catch(error){notice(`麦克风设备列表不可用：${errorText(error)}`,true);}setBusy();
}
async function startAudio() {
  if(!$('audio-input').value||running||starting)return;starting=true;setBusy();resetSignal();
  try {const info=await capture.start($('audio-input').value);running=true;
    const processing=info.processing||{},enabled=Object.entries(processing).filter(([,v])=>v===true).map(([k])=>k);
    $('audio-status').textContent=`${$('audio-input').selectedOptions[0].textContent} · ${info.sampleRate} Hz`;
    if(enabled.length){await stopAudio();throw new Error(`浏览器仍启用了 ${enabled.join(', ')}，停止采集以免混入额外处理`);}
    const unknown=Object.values(processing).some(v=>v!==true&&v!==false);
    notice(unknown?'已开始真实采集；浏览器部分音频处理设置未报告，前后对比需核实系统音效。':'已开始真实采集；浏览器音频处理已关闭。请确认声道用途。');
  }catch(error){running=false;await capture.stop().catch(()=>{});resetSignal();notice(`采集失败：${errorText(error)}`,true);}
  finally {starting=false;setBusy();}
}
async function stopAudio() {running=false;starting=false;await capture.stop().catch(()=>{});resetSignal();$('audio-status').textContent='采集已停止';setBusy();}
function resetSignal(){zeroSince=null;$('signal-health').textContent='';latestFrame=null;actualChannels=0;histories=[];$('stream-info').textContent='等待音频流';$('original-channel').replaceChildren(new Option('等待采集','0'));$('processed-channel').replaceChildren(new Option('不比较',''));$('confirm-map').checked=false;$('routing-summary').textContent='等待采集';$('original-title').textContent='观察通道';$('processed-title').textContent='对比通道';$('channel-monitor').textContent='开始采集后显示浏览器实际提供的通道。';drawSpectra();}
function configureChannels(count) {
  actualChannels=count;histories=Array.from({length:count},()=>[]);$('original-channel').replaceChildren();$('processed-channel').replaceChildren(new Option('不比较',''));
  for(let i=0;i<count;i++){const label=`USB 通道 ${i+1}（用途待确认）`;$('original-channel').append(new Option(label,i));$('processed-channel').append(new Option(label,i));}
  $('original-channel').value='0';$('processed-channel').value=count>1?'1':'';
  $('confirm-map').checked=false;updateMap();$('channel-monitor').replaceChildren();
  for(let i=0;i<count;i++){const row=document.createElement('div');row.className='channel';const label=document.createElement('span');label.id=`channel-name-${i}`;label.textContent=channelLabel(i);const canvas=document.createElement('canvas');canvas.id=`wave-${i}`;canvas.className='wave';canvas.setAttribute('aria-label',`USB 通道 ${i+1} 波形`);canvas.setAttribute('role','img');const level=document.createElement('span');level.id=`level-${i}`;level.className='level';level.textContent='— dBFS';const head=document.createElement('div');head.className='channel-head';head.append(label,level);const meter=document.createElement('div');meter.className='channel-meter';meter.setAttribute('aria-hidden','true');const fill=document.createElement('i');fill.id=`meter-${i}`;meter.append(fill);row.append(head,meter,canvas);$('channel-monitor').append(row);}setBusy();
}
function updateMap(){let map=currentMap();if(map.processed===map.original){$('processed-channel').value='';map=currentMap();notice('请选择不同的两个通道；同一路不能作为前后对比。',true);}if(!recording)capture.setChannels(map);const confirmed=$('confirm-map').checked&&map.processed!==null&&!matchingOutputRoutes();
  $('routing-summary').textContent=actualChannels===2?'左 / 右':actualChannels?`USB ${map.original+1}${map.processed===null?' · 单路观察':' ↔ USB '+(map.processed+1)}`:'等待采集';
  $('original-title').textContent=confirmed?`原声 · USB ${map.original+1}（用户确认）`:channelLabel(map.original);
  $('processed-title').textContent=map.processed===null?(actualChannels===1?'仅收到 1 路输入':'未选择对比通道'):confirmed?`处理后 · USB ${map.processed+1}（用户确认）`:channelLabel(map.processed);
  for(let i=0;i<actualChannels;i++){const label=$(`channel-name-${i}`);if(label)label.textContent=channelLabel(i);}
  $('mapping-note').textContent=actualChannels===1?'浏览器当前只提供 1 路输入，暂时无法进行双通道对比。':confirmed?'通道用途由用户依据固件与路由确认。两路录音使用同一时间窗口。':'通道用途未确认：可以观察与录音，但不能据此宣称处理前后效果。';drawSpectra();setBusy();}
capture.addEventListener('frame',event=>{if(!running&&!starting)return;const frame=event.detail;latestFrame=frame;const allZero=frame.channels.every(c=>c.peak===0);zeroSince=allZero?(zeroSince??performance.now()):null;$('signal-health').textContent=zeroSince!==null&&performance.now()-zeroSince>2000?'已连续收到全零音频。请检查设备连接；这不是正常的安静声谱。停止并重新采集，仍无信号时重新插拔 USB。':'';if(frame.channelCount!==actualChannels)configureChannels(frame.channelCount);
  frame.channels.forEach((channel,i)=>{histories[i].push({time:frame.time,spectrum:channel.spectrum,rms:channel.rms,peak:channel.peak});while(histories[i].length&&histories[i][0].time<frame.time-8000)histories[i].shift();});
  $('stream-info').textContent=`实际 ${frame.channelCount} 通道 · ${frame.sampleRate} Hz`;
  drawSpectra();frame.channels.forEach((channel,i)=>{drawWave($(`wave-${i}`),channel.waveform);$(`level-${i}`).textContent=`${channel.rms===0?'无信号':db(channel.rms).toFixed(1)+' dBFS'}${channel.peak>=.99?' · 接近削波':''}`;setMeter($(`meter-${i}`),channel);});
});
capture.addEventListener('error',event=>{notice(`音频中断：${errorText(event.error||event.detail||'请重新连接设备')}`,true);stopAudio();});

function prepareCanvas(canvas){const rect=canvas.getBoundingClientRect(),scale=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.round(rect.width)),h=Math.max(1,Math.round(rect.height));if(canvas.width!==w*scale||canvas.height!==h*scale){canvas.width=w*scale;canvas.height=h*scale;}const ctx=canvas.getContext('2d');ctx.setTransform(scale,0,0,scale,0,0);ctx.clearRect(0,0,w,h);return {ctx,w,h};}
function spectralColor(value){const t=Math.max(0,Math.min(1,(db(value)+90)/90))*(palette.length-1),i=Math.min(palette.length-2,Math.floor(t)),f=t-i;return `rgb(${palette[i].map((v,j)=>Math.round(v+(palette[i+1][j]-v)*f)).join(',')})`;}
function drawSpectrum(canvas,channel){const {ctx,w,h}=prepareCanvas(canvas);ctx.fillStyle=resolvedColor('--surface2');ctx.fillRect(0,0,w,h);ctx.strokeStyle=resolvedColor('--line');ctx.lineWidth=.5;ctx.beginPath();for(let i=1;i<8;i++){ctx.moveTo(i*w/8,0);ctx.lineTo(i*w/8,h);}for(let i=1;i<4;i++){ctx.moveTo(0,i*h/4);ctx.lineTo(w,i*h/4);}ctx.stroke();const history=channel===null?null:histories[channel];if(!history?.length){ctx.fillStyle=resolvedColor('--muted');ctx.font='12px system-ui';ctx.textAlign='center';ctx.fillText(channel===null?'选择对比通道':'等待音频输入',w/2,h/2);ctx.textAlign='left';return;}const now=latestFrame.time,maxFrequency=Math.min(8000,latestFrame.sampleRate/2),bins=64;
  history.forEach((frame,index)=>{const x=Math.max(0,w*(1-(now-frame.time)/8000)),next=history[index+1]?.time??now+50,width=Math.max(1,(next-frame.time)*w/8000);for(let band=0;band<bins;band++){const freq=(band+.5)/bins*maxFrequency,bin=Math.min(frame.spectrum.length-1,Math.floor(freq/(latestFrame.sampleRate/2)*frame.spectrum.length));ctx.fillStyle=spectralColor(frame.spectrum[bin]);ctx.fillRect(x,h-(band+1)*h/bins,width,Math.ceil(h/bins));}});
}
// Fixed dB scale shared by every channel; visualization does not change PCM.
function levelFraction(rms){return Math.max(0,Math.min(1,(db(rms)+60)/60));}
function setMeter(element,channel){if(!element)return;element.style.width=`${channel?levelFraction(channel.rms)*100:0}%`;element.classList.toggle('clipping',Boolean(channel&&channel.peak>=.99));}
function drawEnergy(canvas,channel){
  const {ctx,w,h}=prepareCanvas(canvas),left=38,bottom=h-20,top=22,height=bottom-top,width=w-left-10;
  ctx.fillStyle=resolvedColor('--surface2');ctx.fillRect(0,0,w,h);ctx.font='10px system-ui';
  for(const level of [-60,-40,-20,0]){const y=bottom-(level+60)/60*height;ctx.strokeStyle=resolvedColor('--line');ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(w-10,y);ctx.stroke();ctx.fillStyle=resolvedColor('--muted');ctx.fillText(String(level),8,y+3);}
  ctx.fillStyle=resolvedColor('--muted');ctx.fillText('声音更强 ↑',left,13);
  const history=channel===null?null:histories[channel];
  if(!history?.length){ctx.textAlign='center';ctx.fillText(channel===null?'选择第二路，比较声音起伏':'开始采集后，说句话试试',w/2,h/2);ctx.textAlign='left';return;}
  const now=latestFrame.time;ctx.save();ctx.beginPath();ctx.rect(left,top,width,height);ctx.clip();
  ctx.fillStyle=resolvedColor('--accent');
  history.forEach((frame,i)=>{const x=left+width*(1-(now-frame.time)/8000),next=history[i+1]?.time??now+50,bw=Math.max(1,(next-frame.time)*width/8000-1),bar=levelFraction(frame.rms)*height;ctx.globalAlpha=.8;ctx.fillRect(x,bottom-bar,bw,bar);});ctx.restore();
}
function drawFrequency(canvas,channel){
  const {ctx,w,h}=prepareCanvas(canvas),left=38,right=w-12,top=22,bottom=h-24;
  ctx.fillStyle=resolvedColor('--surface2');ctx.fillRect(0,0,w,h);ctx.font='10px system-ui';
  for(const level of [-90,-60,-30,0]){const y=bottom-(level+90)/90*(bottom-top);ctx.strokeStyle=resolvedColor('--line');ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle=resolvedColor('--muted');ctx.fillText(String(level),6,y+3);}
  const history=channel===null?null:histories[channel];if(!history?.length){ctx.fillStyle=resolvedColor('--muted');ctx.textAlign='center';ctx.fillText(channel===null?'选择对比通道':'等待音频输入',w/2,h/2);ctx.textAlign='left';return;}
  const maxFrequency=Math.min(8000,latestFrame.sampleRate/2),recent=history.filter(f=>f.time>=latestFrame.time-400),n=recent[0].spectrum.length,lastBin=Math.min(n-1,Math.floor(maxFrequency/(latestFrame.sampleRate/2)*n));
  ctx.strokeStyle=resolvedColor('--accent-ink');ctx.lineWidth=2;ctx.beginPath();
  for(let i=0;i<=lastBin;i++){const magnitude=Math.sqrt(recent.reduce((sum,f)=>sum+f.spectrum[i]**2,0)/recent.length),x=left+(right-left)*i/Math.max(1,lastBin),y=bottom-Math.max(0,Math.min(1,(db(magnitude)+90)/90))*(bottom-top);i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.fillStyle=resolvedColor('--muted');ctx.fillText('低频 · 0 Hz',left,h-6);ctx.textAlign='right';ctx.fillText(`高频 · ${maxFrequency/1000} kHz`,right,h-6);ctx.textAlign='left';
}
function drawSpectra(){
  const map=currentMap(),draw=signalView==='energy'?drawEnergy:signalView==='frequency'?drawFrequency:drawSpectrum;
  for(const [name,index]of [['original',map.original],['processed',map.processed]]){const canvas=$(`${name}-spectrum`),channel=index===null?null:latestFrame?.channels[index];draw(canvas,index);canvas.setAttribute('aria-label',`${name==='original'?'观察':'对比'}通道${signalView==='energy'?'声音强弱随时间变化':signalView==='frequency'?'频段分布曲线':'频率细节声谱图'}`);$(`${name}-level`).textContent=channel?(channel.rms===0?'无信号':`${db(channel.rms).toFixed(1)} dBFS`):'— dBFS';setMeter($(`${name}-meter`),channel);}
  const note=$('comparison-note');if(!note)return;if(matchingOutputRoutes()){note.textContent='设备左右输出路由相同：当前观察的是同一信号，不能据此评估处理前后差异。';return;}
  const a=latestFrame?.channels[map.original],b=map.processed===null?null:latestFrame?.channels[map.processed];
  if(!a||!b){note.textContent='选择两路输入，观察同一时刻的声音强弱。';return;}
  if(a.rms<.001||b.rms<.001){note.textContent='有通道低于电平条显示下限（−60 dBFS）；这不代表没有声音。';return;}
  const recentMean=index=>{const frames=histories[index].filter(f=>f.time>=latestFrame.time-400);return Math.sqrt(frames.reduce((sum,f)=>sum+f.rms*f.rms,0)/Math.max(1,frames.length));};
  const delta=db(recentMean(map.processed))-db(recentMean(map.original));
  note.textContent=Math.abs(delta)<.5?'最近 0.4 秒，两路输入电平接近。':`最近 0.4 秒，USB ${map.processed+1} 比 USB ${map.original+1} ${delta>0?'高':'低'} ${Math.abs(delta).toFixed(1)} dB；电平差不等于降噪效果。`;
}
function drawWave(canvas,samples){if(!canvas)return;const {ctx,w,h}=prepareCanvas(canvas);ctx.strokeStyle=resolvedColor('--line');ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke();ctx.strokeStyle=resolvedColor('--accent-ink');ctx.lineWidth=1.5;ctx.beginPath();samples.forEach((v,i)=>{const x=i*w/Math.max(1,samples.length-1),y=h/2-Math.max(-1,Math.min(1,v*waveZoom))*h*.43;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();if(samples.some(v=>Math.abs(v*waveZoom)>1)){ctx.fillStyle=resolvedColor('--muted');ctx.font='10px system-ui';ctx.fillText('显示超出范围 · 可降低倍率',6,12);}}
function drawDoa(){const {ctx,w,h}=prepareCanvas($('doa-chart')),cx=w/2,cy=h/2,r=Math.min(w,h)*.39;ctx.strokeStyle=resolvedColor('--line');ctx.lineWidth=1;for(const ratio of [.35,.7,1]){ctx.beginPath();ctx.arc(cx,cy,r*ratio,0,Math.PI*2);ctx.stroke();}ctx.fillStyle=resolvedColor('--muted');ctx.font='12px system-ui';ctx.fillText('0°',cx-7,cy-r-7);ctx.fillText('90°',cx+r+4,cy+4);$('doa-value').textContent='—';if(!lastDoa)return;const angle=lastDoa.angle*Math.PI/180;ctx.strokeStyle=resolvedColor(lastDoa.speech?'--accent-ink':'--muted');ctx.setLineDash(lastDoa.speech?[]:[5,5]);ctx.lineWidth=lastDoa.speech?3:2;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+Math.sin(angle)*r,cy-Math.cos(angle)*r);ctx.stroke();$('doa-value').textContent=`${Math.round(lastDoa.angle)}°`;$('doa-value').style.opacity=lastDoa.speech?'1':'.55';ctx.setLineDash([]);}

function ensureWorker(){if(worker)return;worker=new Worker('./transcription-worker.mjs',{type:'module'});worker.onmessage=event=>{const message=event.data;if(message.type==='ready'){modelReady=true;modelLoading=false;$('model-status').textContent='Tiny 已就绪 · 本地运行';}
  if(message.type==='progress'){$('model-status').textContent=`加载 Tiny：${message.file||message.status||'下载模型'}${Number.isFinite(message.progress)?` ${Math.round(message.progress)}%`:''}`;}
  if(message.type==='result'||message.type==='error'){const job=jobs.get(message.id);if(job){jobs.delete(message.id);message.type==='result'?job.resolve(message.text):job.reject(new Error(message.error||'识别失败'));}else if(message.type==='error'){modelReady=false;modelLoading=false;$('model-status').textContent=`加载失败：${message.error}`;notice(`Tiny 未就绪：${message.error}`,true);}}setBusy();};worker.onerror=event=>{modelReady=false;modelLoading=false;for(const job of jobs.values())job.reject(new Error(event.message));jobs.clear();worker.terminate();worker=null;$('model-status').textContent='模型运行失败，可重试加载';setBusy();};}
function transcribeChannel(id,audio,sampleRate,language){return new Promise((resolve,reject)=>{jobs.set(id,{resolve,reject});worker.postMessage({type:'transcribe',id,audio,sampleRate,language});});}
function clearRecordPlayers(){
  document.querySelectorAll('#recordings audio').forEach(player=>player.pause());
  Object.values(recordUrls).forEach(url=>URL.revokeObjectURL(url));
  for(const key of Object.keys(recordUrls))delete recordUrls[key];
  $('recordings').replaceChildren();
}
function renderRecordPlayers(){
  clearRecordPlayers();
  for(const [index,samples] of (lastRecord?.allChannels||[]).entries()){
    const card=document.createElement('article'),title=document.createElement('h3'),canvas=document.createElement('canvas'),player=document.createElement('audio'),info=document.createElement('p'),download=document.createElement('a');
    title.textContent=lastRecord.labels?.[index]||`USB 通道 ${index+1}`;canvas.id=`record-wave-${index}`;canvas.className='record-wave';canvas.setAttribute('role','img');canvas.setAttribute('aria-label',`USB 通道 ${index+1} 录音波形，显示放大 8 倍`);
    recordUrls[index]=URL.createObjectURL(wavBlob(samples,lastRecord.sampleRate));player.src=recordUrls[index];player.controls=true;player.preload='metadata';player.setAttribute('aria-label',`试听 USB 通道 ${index+1}`);
    player.addEventListener('play',()=>document.querySelectorAll('#recordings audio').forEach(other=>{if(other!==player)other.pause();}));
    info.className='meta';info.textContent=`${(samples.length/lastRecord.sampleRate).toFixed(1)} 秒 · ${lastRecord.sampleRate} Hz · 波形显示 ×8`;
    download.className='experiment-link';download.href=recordUrls[index];download.download=`respeaker-${lastRecord.id}-usb-${index+1}.wav`;download.textContent='下载 WAV';
    card.append(title,canvas,player,info,download);$('recordings').append(card);
  }
  drawRecordWaves();
}
function drawRecordWaves(){
  for(const [index,samples] of (lastRecord?.allChannels||[]).entries()){
    const canvas=$(`record-wave-${index}`);if(!canvas)continue;
    const {ctx,w,h}=prepareCanvas(canvas);ctx.strokeStyle=resolvedColor('--accent');ctx.lineWidth=1;ctx.beginPath();
    for(let x=0;x<w;x++){let peak=0;const from=Math.floor(x*samples.length/w),to=Math.floor((x+1)*samples.length/w);for(let i=from;i<to;i++)peak=Math.max(peak,Math.abs(samples[i]));const height=Math.min(1,peak*8)*(h-12)/2;ctx.moveTo(x,h/2-height);ctx.lineTo(x,h/2+height);}ctx.stroke();
  }
}
async function recordAudio(){if(recording||!running)return;cancelWrites();recording=true;lastRecord=null;clearRecordPlayers();$('record-progress').value=0;const recordStart=performance.now();const progressTimer=setInterval(()=>{$('record-progress').value=Math.min(5.9,(performance.now()-recordStart)/1000);},100);setBusy();$('record-status').textContent='正在录制 6 秒 · 参数与声道选择已锁定';$('original-text').textContent='录音中…';$('processed-text').textContent=currentMap().processed===null?'未选择第二路':'录音中…';const settings=Object.fromEntries(supportedParameters().map(p=>[p.key,snapshot.parameters[p.key].value]));const confirmed=$('confirm-map').checked&&!matchingOutputRoutes();
  try{const result=await capture.record(6);lastRecord={...result,labels:result.allChannels.map((_,index)=>channelLabel(index)),settings,confirmed,device:$('audio-input').selectedOptions[0]?.textContent,id:++recordId};renderRecordPlayers();$('record-progress').value=6;$('record-original-title').textContent=lastRecord.labels[result.channels.original];$('record-processed-title').textContent=result.processed?lastRecord.labels[result.channels.processed]:'未录制第二路';$('original-text').textContent='录音就绪，等待转录';$('processed-text').textContent=result.processed?'录音就绪，等待转录':'当前仅有单路录音';$('record-status').textContent=`${new Date(result.startedAt).toLocaleTimeString()} · ${(result.original.length/result.sampleRate).toFixed(1)} 秒 · ${result.sampleRate} Hz · ${confirmed?'用户已确认原声/处理后映射':'通道用途未确认'}`;}
  catch(error){$('record-status').textContent=`录音失败：${errorText(error)}`;$('original-text').textContent='没有完成的录音';$('processed-text').textContent='没有完成的录音';}
  finally{clearInterval(progressTimer);recording=false;if(!lastRecord)$('record-progress').value=0;setBusy();}
}
async function transcribeRecord(){if(!lastRecord||recording||transcribing)return;transcribing=true;setBusy();const completed=new Set();const record=lastRecord,language=$('language').value;$('original-text').textContent='Tiny 正在识别…';if(record.processed)$('processed-text').textContent='等待同一模型识别…';
  try{ensureWorker();if(!modelReady){modelLoading=true;$('model-status').textContent='首次转录，正在加载 Tiny…';}const text=await transcribeChannel(`${record.id}-original`,record.original,record.sampleRate,language);$('original-text').textContent=text||'未识别出文字';completed.add('original');if(record.processed){$('processed-text').textContent='Tiny 正在识别…';$('processed-text').textContent=await transcribeChannel(`${record.id}-processed`,record.processed,record.sampleRate,language)||'未识别出文字';completed.add('processed');}}
  catch(error){modelLoading=false;if(!modelReady)$('model-status').textContent='模型加载失败，点击转录重试；录音仍可试听';for(const name of ['original','processed'])if(record[name]&&!completed.has(name))$(`${name}-text`).textContent='转录未完成，可重试；录音仍可试听与下载。';notice(`本地转录失败：${errorText(error)}`,true);$('record-status').textContent='转录未完成，可保留录音后重试';}finally{transcribing=false;setBusy();}
}

for(const button of document.querySelectorAll('button[data-signal-view]'))button.onclick=()=>{signalView=button.dataset.signalView;document.querySelectorAll('button[data-signal-view]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});$('spectrum-legend').classList.toggle('hidden',signalView!=='spectrum');$('energy-guide').classList.toggle('hidden',signalView!=='energy');$('frequency-guide').classList.toggle('hidden',signalView!=='frequency');document.querySelectorAll('.spectra .axis').forEach(axis=>{axis.children[0].textContent=signalView==='frequency'?'最近 0.4 秒平均':'过去 8 秒';axis.children[1].textContent=signalView==='frequency'?'频率：低 → 高':'时间 → 现在';});drawSpectra();};
$('wave-zoom').onchange=()=>{waveZoom=Number($('wave-zoom').value);$('monitor-note').textContent=`电平条使用真实电平；波形显示 ×${waveZoom}，不改变录音或设备增益。`;latestFrame?.channels.forEach((c,i)=>drawWave($(`wave-${i}`),c.waveform));};
function setWorkspaceTab(name){
  workspaceTab=name;const echo=name==='echo',signal=name==='noise'||echo;
  $(name==='spatial'?'spatial-output-slot':'signal-output-slot').append($('output-routing-panel'));
  document.querySelectorAll('[data-workspace]').forEach(b=>{const active=b.dataset.workspace===name;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
  $('signal-title').textContent=echo?'回声对比':'声音对比';
  $('signal-panel').classList.toggle('hidden',!signal);$('signal-panel').setAttribute('aria-labelledby',echo?'tab-echo':'tab-noise');$('spatial-panel').classList.toggle('hidden',name!=='spatial');$('transcription').classList.toggle('hidden',name!=='transcription');$('noise-tools').classList.toggle('hidden',echo||liteControlsHidden());$('echo-tools').classList.toggle('hidden',!echo);
  $('experiment-guide').textContent=echo?(liteControlsHidden()?'播放参考语音，同时说话：观察两路输入变化，再录音试听。':'播放参考语音，同时说话：在同一组图里观察两路变化，再录音试听。'):'说一句话，再停顿：比较人声起伏和停顿时的声音强度。';
  drawSpectra();drawDoa();drawRecordWaves();latestFrame?.channels.forEach((c,i)=>drawWave($(`wave-${i}`),c.waveform));
}
for(const button of document.querySelectorAll('[data-workspace]')){button.onclick=()=>setWorkspaceTab(button.dataset.workspace);button.onkeydown=event=>{const buttons=[...document.querySelectorAll('[data-workspace]')].filter(b=>!b.disabled),index=buttons.indexOf(button);let next;if(event.key==='ArrowRight')next=(index+1)%buttons.length;if(event.key==='ArrowLeft')next=(index+buttons.length-1)%buttons.length;if(event.key==='Home')next=0;if(event.key==='End')next=buttons.length-1;if(next!==undefined){event.preventDefault();buttons[next].focus();setWorkspaceTab(buttons[next].dataset.workspace);}};}
document.querySelector('#echo-tools .experiment-link').onclick=event=>{event.preventDefault();setWorkspaceTab('transcription');$('tab-transcription').focus();if(!$('record').disabled)recordAudio();else $('record-status').textContent='先开始音频采集，再点击开始录音。';};
for(const event of ['play','pause','ended','emptied','error'])$('reference-player').addEventListener(event,()=>{const player=$('reference-player');$('reference-indicator').textContent=player.error?'测试音频无法播放，请选择浏览器支持的音频文件':player.paused?'已暂停 · 点击播放后观察下方两路':'正在播放 · 先保持安静，再边播放边说话';if(workspaceTab==='echo')$('experiment-guide').textContent=player.paused?'准备测试音频和播放输出，再观察下方回声对比。':liteControlsHidden()?'测试音频播放中：观察两路输入变化，也可录下试听。':'测试音频播放中：切换回声抑制，观察两路变化，也可录下试听。';});
$('connect-usb').onclick=connectUsb;$('disconnect-usb').onclick=async()=>{const device=usb;clearUsb('USB 控制已断开');await device?.disconnect().catch(()=>{});};
$('authorize-audio').onclick=()=>listInputs(true);$('audio-input').onchange=()=>{renderParameters();setBusy();};$('start-audio').onclick=startAudio;$('stop-audio').onclick=stopAudio;
for(const id of ['original-channel','processed-channel'])$(id).onchange=()=>{$('confirm-map').checked=false;updateMap();};$('confirm-map').onchange=updateMap;
$('control-mode').onclick=()=>{$('workbench').showModal();};
$('close-parameters').onclick=()=>{$('workbench').close();};
$('connection-toggle').onclick=()=>{const open=$('connection-panel').classList.contains('hidden');$('connection-panel').classList.toggle('hidden',!open);$('connection-toggle').classList.toggle('active',open);$('connection-toggle').setAttribute('aria-expanded',String(open));};
$('save-a').onclick=()=>{configA={epoch:usbEpoch,values:Object.fromEntries(supportedParameters().map(p=>[p.key,snapshot.parameters[p.key].value]))};addEvent('配置 A 已记录到当前页面');setBusy();};
$('restore-a').onclick=async()=>{if(!configA||configA.epoch!==usbEpoch||recording)return;const epoch=usbEpoch;for(const [key,value]of Object.entries(configA.values)){if(epoch!==usbEpoch)return;if(snapshot.parameters[key]?.supported)await applyParameter(key,value,epoch);}};
$('save-flash').onclick=async()=>{if(!usb||recording)return;const epoch=usbEpoch;pendingWrites++;setBusy();try{await usb.save();if(epoch===usbEpoch)addEvent('设备已接受 Flash 保存指令');}catch(error){notice(`保存未确认：${errorText(error)}`,true);}finally{pendingWrites--;setBusy();}};
$('record').onclick=recordAudio;$('transcribe').onclick=transcribeRecord;
$('setup-comparison').onclick=()=>configureRouting();$('restore-routing').onclick=()=>configureRouting('restore');$('apply-output-routing').onclick=()=>configureRouting('custom');$('restore-output-routing').onclick=()=>configureRouting('restore');
$('reference-file').onchange=()=>{if(playbackUrl)URL.revokeObjectURL(playbackUrl);const file=$('reference-file').files[0];$('reference-filename').textContent=file?file.name:'尚未选择文件';if(file){playbackUrl=URL.createObjectURL(file);$('reference-player').src=playbackUrl;}};
$('choose-output').onclick=async()=>{try{if(navigator.mediaDevices.selectAudioOutput){const device=await navigator.mediaDevices.selectAudioOutput();await $('reference-player').setSinkId(device.deviceId);$('reference-status').textContent=`播放输出：${device.label||'已选择设备'} · 请核对为 reSpeaker`;}else if($('reference-player').setSinkId){const devices=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='audiooutput'&&/respeaker/i.test(d.label));if(devices.length!==1)throw new Error('请在系统声音设置中选择 reSpeaker 播放输出；当前无法唯一确定输出设备');await $('reference-player').setSinkId(devices[0].deviceId);$('reference-status').textContent=`播放输出：${devices[0].label}`;}else throw new Error('此浏览器不支持网页选择输出，请在系统声音设置中选择 reSpeaker');}catch(error){$('reference-status').textContent=errorText(error);}};
navigator.mediaDevices?.addEventListener?.('devicechange',()=>{if(!running&&!starting)listInputs();});
window.addEventListener('pagehide',()=>{++usbEpoch;cancelWrites();clearTimeout(doaTimer);capture.stop();usb?.disconnect();worker?.terminate();if(playbackUrl)URL.revokeObjectURL(playbackUrl);Object.values(recordUrls).forEach(url=>URL.revokeObjectURL(url));});
new ResizeObserver(()=>{drawSpectra();drawDoa();drawRecordWaves();}).observe($('lab'));matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawSpectra();drawDoa();});
if(!window.isSecureContext)notice('请通过 HTTPS 或 localhost 打开页面，浏览器设备权限需要安全环境。',true);
if(!navigator.usb)$('usb-status').textContent='此浏览器没有 WebUSB，可使用支持该功能的桌面 Chrome / Edge；音频采集可单独使用。';
renderParameters();drawSpectra();drawDoa();setBusy();
