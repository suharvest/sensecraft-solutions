import { ReSpeakerUSB, PARAMETERS, OUTPUT_SIGNALS, PRE_PROCESSING_CATEGORIES, DEMO_PRESETS, DEFAULT_CHANNEL_MAPS } from './device.js';
import { t, translateDom, LANG } from './i18n.js';
import { AudioCapture, wavBlob } from './audio.js';

const $ = id => document.getElementById(id);
const capture = new AudioCapture();
let usb = null, snapshot = null, usbEpoch = 0, doaTimer = null, configA = null;
let running = false, starting = false, recording = false, transcribing = false, lastRecord = null;
let signalView='energy', waveZoom=16, workspaceTab='noise', zeroSince=null;
let latestFrame = null, actualChannels = 0, lastDoa = null;
let worker = null, modelReady = false, modelLoading = false, recordId = 0;
let histories = [], parameterTimers = new Map(), pendingWrites = 0, playbackUrl = null;
let savedRouting=null, demoBefore=null, applyingDemo=false, captureCaps=null;
const recordUrls = {};
const jobs = new Map(), parameterEvents = [];
const palette = [[16,26,48],[55,83,160],[24,185,174],[244,189,90],[245,87,139]];

function notice(message, error = false) { $('notice').textContent = message; $('notice').classList.toggle('error', error); }
function errorText(error) { return error?.message || String(error); }
function color(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function resolvedColor(name) { const probe=document.createElement('span');probe.style.color=`var(${name})`;probe.hidden=true;document.body.append(probe);const result=getComputedStyle(probe).color;probe.remove();return result; }
function db(value) { return 20 * Math.log10(Math.max(1e-8, value)); }
function formatValue(value) { if (Array.isArray(value)) return `[${value.map(v => Number(Number(v).toFixed(3))).join(', ')}]`; return typeof value === 'boolean' ? (value ? t('开') : t('关')) : typeof value === 'number' ? Number(value.toFixed(3)).toString() : String(value ?? '—'); }
function addEvent(message) { parameterEvents.unshift(`${new Date().toLocaleTimeString()} · ${message}`);parameterEvents.splice(5);$('parameter-events').replaceChildren(...parameterEvents.map(text=>{const li=document.createElement('li');li.textContent=text;return li;})); }
function currentMap() { return { original:Number($('original-channel').value)||0, processed:$('processed-channel').value === '' ? null : Number($('processed-channel').value) }; }
function editableParameters() { return (snapshot?.parameterDefinitions||PARAMETERS).filter(p=>!p.readOnly&&!p.writeOnly&&!['VERSION','DOA_VALUE','SAVE_CONFIGURATION'].includes(p.key)); }
function supportedParameters() { return editableParameters().filter(p=>snapshot?.parameters?.[p.key]?.supported); }
function liteAudioSelected() { const option=$('audio-input')?.selectedOptions?.[0]; return !usb&&Boolean($('audio-input')?.value)&&/reSpeaker Lite/i.test(option?.textContent||''); }
function liteControlsHidden() { return snapshot?.identity?.controlProtocol==='audio-only'||liteAudioSelected(); }
function updateLiteUi() {
  const lite=liteControlsHidden();
  const note=$('control-capability-note');
  if(note) { note.classList.toggle('hidden',!lite); note.textContent=lite?t('当前设备的 USB 固件未提供本工具已适配的 USB 调参接口；Lite 支持板载降噪等音频处理，由设备固件执行；网页仍可采集、录音与转录。'):''; }
  $('noise-tools')?.classList.toggle('hidden',lite||workspaceTab!=='noise');
  for(const id of ['gain-tools','beam-tools','all-noise-section','all-echo-section','all-beam-section','all-gain-section','all-output-section'])$(id)?.classList.toggle('hidden',lite);
  $('echo-tuning')?.classList.toggle('hidden',lite||workspaceTab!=='echo');
  if($('parameter-status')&&lite)$('parameter-status').textContent=t('Lite 的板载音频处理由设备固件执行；当前 USB 固件未提供本工具已适配的调参接口。');
}
function cancelWrites() { for(const t of parameterTimers.values())clearTimeout(t);parameterTimers.clear(); }
function setConnectionPanel(open){
  $('connection-panel').classList.toggle('hidden',!open);
  $('connection-toggle').classList.toggle('active',open);
  $('connection-toggle').setAttribute('aria-expanded',String(open));
  if(open)$('connection-panel').scrollIntoView({block:'nearest',behavior:'smooth'});
}
function updateStage(){
  const lab=$('lab');
  const stage=running?'live':'connect';
  if(lab.dataset.stage!==stage){
    lab.dataset.stage=stage;
    if(stage==='live'){setConnectionPanel(false);$('signal-panel').scrollIntoView({block:'start',behavior:'smooth'});}
  }
}
function setBusy() {
  updateLiteUi();
  updateStage();
  updateDemoPair();
  const hasParameters=supportedParameters().length>0;
  const liteAudio=liteAudioSelected();
  const routeSupported=snapshot?.identity?.controlProtocol==='xvf3800-servicer'&&snapshot?.parameters?.AUDIO_MGR_OP_L?.supported&&snapshot?.parameters?.AUDIO_MGR_OP_R?.supported;
  $('channel-selection').classList.toggle('hidden',actualChannels<=2);
  $('output-routing-panel').classList.toggle('hidden',!routeSupported);
  $('stereo-routing-note').textContent=actualChannels===2?(routeSupported?t('浏览器只接收左、右两路；下方可从设备内部的麦克风与处理后信号中，分别选择一路输出。'):t('当前输入为左、右两路，无需选择浏览器通道；信号用途由当前固件决定。')):actualChannels>2?t('选择需要观察的两路；设备输出路由与浏览器通道选择是不同设置。'):t('开始采集后显示实际输入通道。');
  if(!usb)$('doa-status').textContent=liteAudio?t('当前 Lite USB 接入不提供声源方向数据'):t('USB 控制未连接');
  for(const tab of document.querySelectorAll('[data-workspace]'))tab.disabled=!snapshot&&!running;
  for(const id of ['output-left','output-right','apply-output-routing'])$(id).disabled=!routeSupported||recording||pendingWrites>0||parameterTimers.size>0;
  $('restore-output-routing').disabled=!routeSupported||!savedRouting||recording||pendingWrites>0||parameterTimers.size>0;
  $('reboot-device').disabled=!usb||recording||pendingWrites>0||parameterTimers.size>0;
  $('connect-usb').disabled=recording||pendingWrites>0;
  $('disconnect-usb').disabled=!usb||recording;
  $('start-audio').disabled=running||starting||!$('audio-input').value;
  $('stop-audio').disabled=!running||starting;
  $('audio-input').disabled=running||starting;
  $('authorize-audio').disabled=running||starting;
  $('original-channel').disabled=!running||recording||actualChannels<=2;
  $('processed-channel').disabled=!running||recording||actualChannels<=2;
  $('confirm-map').disabled=!running||recording||currentMap().processed===null||matchingOutputRoutes();
  const demoReady=Boolean(DEMO_PRESETS[snapshot?.identity?.controlProtocol])&&hasParameters;
  $('apply-demo').disabled=!demoReady||applyingDemo||recording||pendingWrites>0||parameterTimers.size>0;
  $('restore-demo').disabled=!demoBefore||demoBefore.epoch!==usbEpoch||applyingDemo||recording||pendingWrites>0||parameterTimers.size>0;
  $('save-a').disabled=!hasParameters||recording||pendingWrites>0||parameterTimers.size>0;
  $('restore-a').disabled=!configA||!hasParameters||recording||pendingWrites>0||parameterTimers.size>0;
  $('save-flash').disabled=snapshot?.canSave===false||!hasParameters||recording||pendingWrites>0||parameterTimers.size>0;
  $('record-input-note').textContent=!running?t('先连接音频并开始采集，即可录音；无需加载转录模型。'):t('将同步录制全部 {p0} 路 USB 输入 · 6 秒；录完可逐路试听',{p0:actualChannels});
  $('record').disabled=!running||actualChannels===0||recording||pendingWrites>0||parameterTimers.size>0||transcribing;
  $('record').textContent=recording?t('正在录音…'):lastRecord?t('重新录制 · 6 秒'):t('开始录音 · 6 秒');
  $('transcribe').disabled=!lastRecord||recording||transcribing;
  for(const element of document.querySelectorAll('.parameter-grid input,.parameter-grid select'))element.disabled=recording||pendingWrites>0||!snapshot?.parameters?.[element.dataset.key]?.supported;
}

async function connectUsb() {
  cancelWrites();clearTimeout(doaTimer);
  const previous=usb;usb=null;if(previous)await previous.disconnect().catch(()=>{});
  const token=++usbEpoch;
  snapshot=null;configA=null;demoBefore=null;savedRouting=null;lastDoa=null;renderParameters();drawDoa();
  const device=new ReSpeakerUSB();usb=device;
  device.addEventListener('disconnect',()=>{if(usb===device)clearUsb(t('USB 控制已断开。重新连接后会重新读取固件与参数。'));});
  $('usb-status').textContent=t('等待选择设备与读取能力…');$('connect-usb').disabled=true;
  try {
    const result=await device.connect({onProgress:(done,total)=>{if(token===usbEpoch)$('usb-status').textContent=t('正在读取固件与参数 {p0}/{p1}…',{p0:done,p1:total});}});
    if(token!==usbEpoch){await device.disconnect();return;}
    snapshot=result;if(matchingOutputRoutes())$('confirm-map').checked=false;if(actualChannels>0)updateMap();
    $('device-name').textContent=result.identity.name;
    const firmware=result.identity.controlProtocol==='audio-only'?t('未读取版本'):result.firmware||result.parameters?.VERSION?.value?.join?.('.')||t('不可读取');
    $('usb-info').textContent=t('固件 {p0} · {p1} 麦 · {p2}',{p0:firmware,p1:result.identity.physicalMics??t('未知'),p2:device.device?.productName||result.identity.name});
    const available=supportedParameters().length;
    $('usb-status').textContent=available?t('已读取 {p0} 个可调参数 · 音频需在右侧单独选择',{p0:available}):t('音频模式 · {p0}',{p0:t(result.identity.notes||'')||t('此固件未提供可用的 USB 控制接口')});
    $('doa-status').textContent=result.doaSupported?t('等待设备 DOA 数据'):t('当前型号或固件未提供可读 DOA');
    notice(t('USB 设备已识别。请选择同一台 reSpeaker 的音频输入，确认声道用途后再进行前后对比。'));
    if(!result.firmware&&result.identity.controlProtocol!=='audio-only'){notice(t('设备已识别，但控制读取失败。请重新连接 USB；音频可单独检查。'),true);$('usb-status').textContent=t('控制读取失败 · 固件未响应');}renderParameters();
    // Never rewrite device routing on connect: the first waveform the user sees must be the device's own output.
    if(result.identity.controlProtocol==='xvf3800-servicer'&&result.parameters.AUDIO_MGR_OP_L?.supported&&result.parameters.AUDIO_MGR_OP_R?.supported){
      const before={left:outputSignalLabel('left'),right:outputSignalLabel('right')};
      if(preProcessingSides().length!==1||matchingOutputRoutes()){
        await configureRouting('preset');
        if(token===usbEpoch&&savedRouting)notice(t('USB 设备已识别。设备原本两路是「{p0}」和「{p1}」，都在处理之后；已改成左 = 处理前、右 = 处理后，这样两张图才有可比性。只改运行路由，不写 Flash，「设备输出」里可随时恢复。',{p0:before.left,p1:before.right}));
      }
    }
    pollDoa(token);
  } catch(error) { if(token===usbEpoch){snapshot=null;notice(t('USB 控制连接失败：{p0}。仍可尝试右侧的 USB 声卡采集。',{p0:errorText(error)}),true);$('usb-status').textContent=t('控制连接失败：{p0}',{p0:errorText(error)});} }
  finally {setBusy();}
}
function clearUsb(message) {
  ++usbEpoch;cancelWrites();clearTimeout(doaTimer);savedRouting=null;snapshot=null;configA=null;demoBefore=null;usb=null;lastDoa=null;
  $('device-name').textContent=t('连接 reSpeaker');$('usb-info').textContent=t('XVF3000 / XVF3800 / Flex / Lite · 按型号与固件识别能力');$('usb-status').textContent=message;
  $('doa-status').textContent=liteAudioSelected()?t('当前 Lite USB 接入不提供声源方向数据'):t('USB 控制未连接');$('parameter-status').textContent=t('连接 USB 后读取可用参数');$('confirm-map').checked=false;if(actualChannels>0)updateMap();renderParameters();drawDoa();setBusy();
}
async function pollDoa(token) {
  if(token!==usbEpoch||!snapshot?.doaSupported||!usb)return;
  try { const value=await usb.pollDoa();if(token!==usbEpoch)return;lastDoa=value&&Number.isFinite(value.angle)?value:null;drawDoa();$('doa-status').textContent=!lastDoa?t('方向读取暂不可用'):lastDoa.speech?t('检测到语音 · 设备报告方向，不表示距离'):t('最近设备方向 · 当前语音标记未触发'); }
  catch {lastDoa=null;drawDoa();}
  if(token===usbEpoch)doaTimer=setTimeout(()=>pollDoa(token),200);
}
async function configureRouting(mode='preset',explicit=null){
  const restore=mode==='restore';
  if(!usb||recording||pendingWrites||parameterTimers.size)return;
  const device=usb,epoch=usbEpoch;pendingWrites++;setBusy();setRoutingStatus(t('正在设置运行路由并回读…'));
  try{
    if(restore){await device.restoreRouting(savedRouting);savedRouting=null;}
    else{const previous=mode==='custom'?await device.setOutputRouting(explicit||{left:$('output-left').value.split(':').map(Number),right:$('output-right').value.split(':').map(Number)}):await device.setComparisonRouting();savedRouting??=previous;}
    if(epoch!==usbEpoch)return;
    const values={};for(const key of ['AUDIO_MGR_OP_L','AUDIO_MGR_OP_R'])values[key]={supported:true,value:await device.read(key)};
    if(epoch!==usbEpoch)return;Object.assign(snapshot.parameters,values);histories=Array.from({length:actualChannels},()=>[]);latestFrame=null;
    $('confirm-map').checked=false;if(actualChannels>=2){$('original-channel').value='0';$('processed-channel').value='1';}updateMap();renderDiagnostics();
    setRoutingStatus(restore?t('已恢复原路由并回读确认。'):t('已应用：左路 {p0}；右路 {p1}。未保存到 Flash。{p2}',{p0:outputSignalLabel('left'),p1:outputSignalLabel('right'),p2:mode==='preset'?t('右路是常规处理输出，和左路共用同一个增益级。想看更强的抑制，把右路换成「AEC 残差 / ASR」那一组——那是给识别器用的支路，带自己的增益，不能当作常规音质参考。'):''}));
  }catch(error){if(epoch===usbEpoch){if(error.previousRouting)savedRouting??=error.previousRouting;setRoutingStatus(t('路由设置失败：{p0}',{p0:errorText(error)}));}}
  finally{pendingWrites--;setBusy();}
}
function setRoutingStatus(text){$('routing-status').textContent=text;$('output-routing-status').textContent=text;}
function asrOutputOn(){return snapshot?.parameters?.AEC_ASROUTONOFF?.value===true;}
function signalLabel(signal){
  // AEC_ASROUTONOFF defaults to 0: category 7 then carries AEC residuals, one channel per microphone —
  // a tuning tap, not a listening output, so its level sits far below the processed beam.
  if(signal.route[0]===7)return asrOutputOn()?t('ASR 输出 · 波束 {p0}',{p0:signal.route[1]+1}):t('诊断 · AEC 残差 · 麦克风 {p0}',{p0:signal.route[1]+1});
  return `${t(signal.group)} · ${t(signal.label,{n:signal.n})}`;
}
function isDiagnosticTap(status){return Boolean(status?.supported&&status.value?.[0]===7&&!asrOutputOn());}
function routeSide(side){return snapshot?.parameters?.[side==='left'?'AUDIO_MGR_OP_L':'AUDIO_MGR_OP_R'];}
function isPreProcessing(status){return Boolean(status?.supported&&Array.isArray(status.value)&&PRE_PROCESSING_CATEGORIES.includes(status.value[0]));}
function preProcessingSides(){return ['left','right'].filter(side=>isPreProcessing(routeSide(side)));}
function outputSignalLabel(side){
  const status=routeSide(side);
  if(!status?.supported)return t('信号用途待确认');
  const value=status.value.join(':');const signal=OUTPUT_SIGNALS.find(option=>option.value===value);
  return signal?signalLabel(signal):t('用途未知 · 固件返回 ({p0})',{p0:status.value.join(', ')});
}
// ReSpeaker Mic Array v2.0 6-channel layout: ch0 processed-for-ASR, ch1-4 raw mics, ch5 merged playback.
function legacyChannelLabel(index){
  const port=`USB ${index+1}（ch${index}）`;
  if(index===0)return t('处理后 · {p0} 供 ASR',{p0:port});
  if(index>=1&&index<=4)return t('处理前 · {p0} 麦克风 {p1}',{p0:port,p1:index});
  if(index===5)return t('回放混合 · {p0}',{p0:port});
  return port;
}
function channelLabel(index){
  const product=usb?.device?.productName,input=$('audio-input').selectedOptions[0]?.textContent||'';
  if(actualChannels===2&&product&&input.includes(product)&&snapshot?.parameters?.AUDIO_MGR_OP_L?.supported&&snapshot?.parameters?.AUDIO_MGR_OP_R?.supported)return `${index===0?t('左'):t('右')} · ${outputSignalLabel(index===0?'left':'right')}`;
  if(snapshot?.identity?.controlProtocol==='xvf3000-legacy')return legacyChannelLabel(index);
  return actualChannels===2?t('{p0}声道 · USB {p1}',{p0:index===0?t('左'):t('右'),p1:index+1}):t('USB 通道 {p0}',{p0:index+1});
}
function renderOutputSelectors(){
  for(const side of ['left','right']){
    const select=$(`output-${side}`),status=snapshot?.parameters?.[side==='left'?'AUDIO_MGR_OP_L':'AUDIO_MGR_OP_R'];
    select.replaceChildren();
    if(!status?.supported){select.append(new Option(t('连接 XVF3800 USB 控制后选择'),''));continue;}
    let group=null,holder=null;
    for(const signal of OUTPUT_SIGNALS){
      const groupName=signal.route[0]===7?(asrOutputOn()?t('ASR 输出'):t('诊断 · AEC 残差')):t(signal.group);
      if(groupName!==group){group=groupName;holder=document.createElement('optgroup');holder.label=group;select.append(holder);}
      const option=new Option(signal.route[0]===7?signalLabel(signal).replace(/^[^·]+· /,''):t(signal.label,{n:signal.n}),signal.value);holder.append(option);
    }
    const current=status.value.join(':');if(!OUTPUT_SIGNALS.some(signal=>signal.value===current)){const option=new Option(outputSignalLabel(side),current);option.disabled=true;select.append(option);}select.value=current;
  }
}
function matchingOutputRoutes(){
  const left=snapshot?.parameters?.AUDIO_MGR_OP_L,right=snapshot?.parameters?.AUDIO_MGR_OP_R;
  return left?.supported&&right?.supported&&Array.isArray(left.value)&&JSON.stringify(left.value)===JSON.stringify(right.value);
}
function renderDiagnostics(){renderOutputSelectors();updateRoutingSummary();
  const params=snapshot?.parameters||{},left=params.AUDIO_MGR_OP_L,right=params.AUDIO_MGR_OP_R;
  const pre=left?.supported&&right?.supported?preProcessingSides():[];
  $('hardware-route-note').textContent=left?.supported&&right?.supported
    ?t('设备当前输出：左 = {p0}（固件值 {p1}）；右 = {p2}（固件值 {p3}）。{p4}{p5}',{p0:outputSignalLabel('left'),p1:left.value.join(', '),p2:outputSignalLabel('right'),p3:right.value.join(', '),p4:matchingOutputRoutes()?t('左右是同一个信号，两张图会一样。'):pre.length===0?t('两路都是处理后的信号，这里看不到处理前的样子。要做前后对比，点「左：处理前 / 右：处理后」。'):pre.length===2?t('两路都取自处理前，图上不会体现处理效果。'):'',p5:[left,right].some(isDiagnosticTap)?t(' 其中 AEC 残差是回声消除后的误差信号，用于调试，电平天然比常规输出低十几 dB——它小不等于降噪更强。'):''})
    :snapshot?.identity?.controlProtocol==='xvf3000-legacy'&&actualChannels
      ?(actualChannels>=2
        ?t('XVF3000 固件没有输出路由，处理前 / 处理后取自 USB 通道：观察 = 通道 2（ch1，麦克风 1 原始），对比 = 通道 1（ch0，处理后供 ASR 使用），采集开始时已自动选好。{p0}前两路与 ch0 / ch1 的对应关系已实机确认（ch0 的人声/底噪落差明显更大）。',{p0:captureCaps?.channelCount?.max&&captureCaps.channelCount.max<6?t('该固件本身出 6 路，但浏览器把这个设备的通道上限报成 {p0} 路，只能拿到前两路——这是浏览器限制，不是固件问题。',{p0:captureCaps.channelCount.max}):''})
        :t('当前浏览器只提供 {p0} 路，无法做处理前后对比。',{p0:actualChannels}))
      :'';
  $('aec-diagnostic').textContent=params.AEC_AECCONVERGED?.supported?t('AEC 状态（连接时读取）：{p0}。需播放参考声音后观察，未收敛不等于未开启。{p1}{p2}',{p0:params.AEC_AECCONVERGED.value?t('已收敛'):t('未收敛'),p1:params.AEC_RT60?.supported?t(' RT60 估计 {p0} s（未收敛时可能无效）。',{p0:formatValue(params.AEC_RT60.value)}):'',p2:params.AEC_AECPATHCHANGE?.supported?t(' 声学路径变化：{p0}。',{p0:params.AEC_AECPATHCHANGE.value?t('检测到'):t('未检测到')}):''}):'';
  const spenergy=params.AEC_SPENERGY_VALUES;
  $('beam-diagnostic').textContent=spenergy?.supported&&Array.isArray(spenergy.value)?t('波束语音能量（最近渲染时读取，大于 0 表示该波束有语音）：聚焦1 {p0} · 聚焦2 {p1} · 快速 {p2} · 自动 {p3}',{p0:formatValue(spenergy.value[0]),p1:formatValue(spenergy.value[1]),p2:formatValue(spenergy.value[2]),p3:formatValue(spenergy.value[3])}):'';
  $('gain-diagnostic').textContent=params.PP_AGCGAIN?.supported?t('当前 AGC 增益（连接时读取）：{p0} 倍',{p0:formatValue(params.PP_AGCGAIN.value)}):'';
}
function updateRoutingSummary(){
  const l=snapshot?.parameters?.AUDIO_MGR_OP_L,r=snapshot?.parameters?.AUDIO_MGR_OP_R;
  if(actualChannels>0){const map=currentMap();$('routing-summary').textContent=actualChannels===2?t('观察 左 / 右'):t('观察 USB {p0}{p1}',{p0:map.original+1,p1:map.processed===null?t(' · 单路'):' ↔ USB '+(map.processed+1)});return;}
  if(usb&&l?.supported&&r?.supported){$('routing-summary').textContent=t('已配置 · {p0} / {p1}',{p0:outputSignalLabel('left'),p1:outputSignalLabel('right')});return;}
  $('routing-summary').textContent=usb?'—':t('等待采集');
}
const PARAMETER_SLOTS=[
  ['all-noise-parameters','noise','all'],['all-echo-parameters','echo','all'],['all-beam-parameters','beam','all'],['all-gain-parameters','gain','all'],['all-output-parameters','output','all'],
  ['bypass-control','bypass','primary'],
  ['noise-parameters','noise','primary'],['noise-parameters-advanced','noise','advanced'],
  ['echo-parameters','echo','primary'],['echo-parameters-advanced','echo','advanced'],
  ['gain-parameters','gain','primary'],['gain-parameters-advanced','gain','advanced'],
  ['beam-parameters','beam','primary'],['beam-parameters-advanced','beam','advanced'],
];
// AGC sits in the gain group, but it masks noise suppression, so it is also a primary control
// on the noise workspace: without it the two charts cannot be read against each other.
const PRIMARY_GUESTS={noise:['PP_AGCONOFF','AGCONOFF']};
function paramsFor(category,tier){
  const list=editableParameters();
  if(category==='bypass')return list.filter(p=>p.key==='SHF_BYPASS');
  const guests=tier==='primary'?(PRIMARY_GUESTS[category]||[]):[];
  const entries=list.filter(p=>p.group===category||guests.includes(p.key));
  if(tier==='all')return entries;
  const tunable=entries.filter(p=>p.key!=='SHF_BYPASS');
  return tier==='primary'?tunable.filter(p=>p.primary):tunable.filter(p=>!p.primary);
}
function renderParameters(){
  renderDiagnostics();
  if(liteControlsHidden()){
    for(const [id]of PARAMETER_SLOTS)$(id)?.replaceChildren();
    $('lab').dataset.control='off';
    updateLiteUi();
    return;
  }
  if($('parameter-status'))$('parameter-status').textContent=snapshot?t('已读取设备参数'):t('连接 USB 后读取可用参数');
  $('lab').dataset.control=snapshot?'on':'off';
  for(const [id,category,tier]of PARAMETER_SLOTS)renderParameterGroup($(id),category,tier);
}
function renderParameterGroup(container,category,tier='all') {
  if(!container)return;
  container.replaceChildren();
  const fold=container.closest('details.more-params');
  if(!snapshot){
    if(fold)fold.classList.add('hidden');
    else if(tier==='all'){const p=document.createElement('p');p.className='empty';p.textContent=t('尚未读取设备参数。连接后只启用固件实际支持的控制项。');container.append(p);}
    return;
  }
  const entries=paramsFor(category,tier);
  if(fold)fold.classList.toggle('hidden',!entries.length);
  if(container.id==='bypass-control')container.classList.toggle('hidden',!entries.length);
  for(const parameter of entries) {
    const status=snapshot.parameters?.[parameter.key],wrap=document.createElement('div');wrap.className=`param param-${parameter.type}`;
    const label=document.createElement('label'),name=document.createElement('span'),value=document.createElement('output'),code=document.createElement('code');
    name.textContent=t(tier==='all'?parameter.label:(parameter.plain||parameter.label));value.textContent=status?.supported?(()=>{const o=parameter.options?.find(option=>option.value===status.value);return o?t(o.label):formatValue(status.value);})():t('不可用');label.append(name,value);code.textContent=parameter.key;
    const input=document.createElement(parameter.type==='enum'?'select':'input');input.dataset.key=parameter.key;input.id=`${container.id}-${parameter.key}`;label.htmlFor=input.id;
    const hint=document.createElement('p');hint.className='meta';hint.textContent=status?.supported?(t(parameter.effect||'')||(parameter.key.includes('MIN_N')?t('增益下限越小，噪声抑制越强；需同时试听人声。'):t('改变后读取设备返回值。'))):`${status?.error||t('当前固件未开放此参数')}`;
    if(parameter.type==='enum') {for(const option of parameter.options||[]){const el=document.createElement('option');el.value=option.value;el.textContent=t(option.label);input.append(el);}input.value=status?.value??0;}
    else if(parameter.type==='bool'){input.type='checkbox';input.checked=Boolean(status?.value);}
    else if((parameter.count||1)>1){
      const stack=document.createElement('div');stack.className='multi-range';
      const current=status?.supported&&Array.isArray(status.value)?status.value.slice():Array.from({length:parameter.count},()=>parameter.min);
      const pending=current.slice();
      for(let i=0;i<parameter.count;i++){
        const row=document.createElement('div');row.className='multi-row';
        const tag=document.createElement('span');tag.className='meta';tag.textContent=`#${i+1}`;
        const slider=document.createElement('input');slider.type='range';slider.dataset.key=parameter.key;slider.min=parameter.min;slider.max=parameter.max;slider.step=parameter.step;slider.value=current[i];
        slider.style.setProperty('--range-fill',`${(Number(current[i])-parameter.min)/(parameter.max-parameter.min)*100}%`);
        if(i===0){slider.id=`${container.id}-${parameter.key}`;label.htmlFor=slider.id;hint.id=`${slider.id}-hint`;slider.setAttribute('aria-describedby',hint.id);}
        slider.disabled=!status?.supported||recording;
        slider.addEventListener('input',()=>{
          if(recording||!snapshot?.parameters?.[parameter.key]?.supported)return;
          pending[i]=Number(slider.value);slider.style.setProperty('--range-fill',`${(pending[i]-parameter.min)/(parameter.max-parameter.min)*100}%`);
          value.textContent=t('[{p0}] · 待回读',{p0:pending.map(formatValue).join(', ')});
          clearTimeout(parameterTimers.get(parameter.key));const epoch=usbEpoch;
          parameterTimers.set(parameter.key,setTimeout(()=>{parameterTimers.delete(parameter.key);if(epoch===usbEpoch)applyParameter(parameter.key,pending.slice(),epoch);},250));setBusy();
        });
        row.append(tag,slider);stack.append(row);
      }
      wrap.append(label,code,stack,hint);container.append(wrap);continue;
    }
    else {input.type='range';input.min=parameter.min;input.max=parameter.max;input.step=parameter.step;input.value=status?.value??parameter.min;input.style.setProperty('--range-fill',`${(Number(input.value)-parameter.min)/(parameter.max-parameter.min)*100}%`);}
    hint.id=`${input.id}-hint`;input.setAttribute('aria-describedby',hint.id);input.disabled=!status?.supported||recording;
    input.addEventListener(parameter.type==='float'?'input':'change',()=>{
      if(recording||!snapshot?.parameters?.[parameter.key]?.supported)return;
      const next=parameter.type==='bool'?input.checked:Number(input.value);value.textContent=t('{p0} · 待回读',{p0:parameter.options?.find(option=>option.value===next)?.label??formatValue(next)});if(input.type==='range')input.style.setProperty('--range-fill',`${(next-parameter.min)/(parameter.max-parameter.min)*100}%`);
      clearTimeout(parameterTimers.get(parameter.key));const epoch=usbEpoch;
      parameterTimers.set(parameter.key,setTimeout(()=>{parameterTimers.delete(parameter.key);if(epoch===usbEpoch)applyParameter(parameter.key,next,epoch);},250));setBusy();
    });
    wrap.append(label,code,input,hint);container.append(wrap);
  }
  if(!entries.length&&!fold){const p=document.createElement('p');p.className='empty';p.textContent=t('此设备没有这一组可用的控制项。');container.append(p);}
  setBusy();
}
function demoPreset(){return DEMO_PRESETS[snapshot?.identity?.controlProtocol]||null;}
function demoKeys(preset){return Object.keys(preset.values).filter(key=>snapshot?.parameters?.[key]?.supported);}
function setDemoStatus(text){$('demo-status').textContent=text;}
// Name the two taps being compared. The落差 numbers are only comparable across models once you know
// the baselines differ: XVF3800/Flex can tap the mic before any gain, the legacy family cannot.
function updateDemoPair(){
  const el=$('demo-pair');if(!el)return;
  if(!running||!actualChannels){el.textContent='';return;}
  const map=currentMap();
  if(map.processed===null){el.textContent=t('只选了一路，无法对比。');return;}
  const origin=routeSide(map.original===0?'left':'right');
  const baseline=snapshot?.identity?.controlProtocol==='xvf3000-legacy'
    ?t('该固件没有无增益的麦克风抽头，基准取的是已加增益的那一路，落差数字天然比 XVF3800 / Flex 保守，两者不能直接比大小。')
    :origin?.supported&&origin.value?.[0]===1
      ?t('基准是完全不过增益的原始麦克风，落差数字会比用已加增益的那一路更大。')
      :'';
  el.textContent=t('本次对比：{p0} ｜ {p1}。{p2}',{p0:$('original-title').textContent,p1:$('processed-title').textContent,p2:baseline});
}
async function runDemo(restore=false){
  const preset=demoPreset();
  if(!preset||applyingDemo||recording||pendingWrites||parameterTimers.size)return;
  const epoch=usbEpoch,keys=demoKeys(preset);
  applyingDemo=true;setBusy();
  try{
    if(restore){
      if(!demoBefore)return;
      if(demoBefore.epoch!==usbEpoch){demoBefore=null;setDemoStatus(t('设备已切换，上一台的演示前快照不再适用，已丢弃。'));return;}
      const failed=[];
      for(const [key,value] of Object.entries(demoBefore.values)){
        if(epoch!==usbEpoch)return;
        if(!await applyParameter(key,value,epoch))failed.push(key);
      }
      if(epoch!==usbEpoch)return;
      if(failed.length){setDemoStatus(t('恢复未完成：{p0} 项写回失败（{p1}），快照已保留，可重试。',{p0:failed.length,p1:failed.join('、')}));return;}
      demoBefore=null;setDemoStatus(t('已恢复演示前的参数。左右信号由上方「设备输出」决定，这里没有动过。'));
      return;
    }
    if(!demoBefore||demoBefore.epoch!==usbEpoch)
      demoBefore={epoch:usbEpoch,values:Object.fromEntries(keys.map(key=>[key,snapshot.parameters[key].value]))};
    let done=0;const failed=[];
    for(const [index,key] of keys.entries()){
      if(epoch!==usbEpoch)return;
      setDemoStatus(t('正在写入演示配置 {p0}/{p1}（{p2}）…',{p0:index+1,p1:keys.length,p2:key}));
      if(await applyParameter(key,preset.values[key],epoch))done++; else failed.push(key);
    }
    const skipped=Object.keys(preset.values).filter(key=>!snapshot?.parameters?.[key]?.supported);
    if(epoch===usbEpoch)setDemoStatus(t('{p0} 演示参数已写入 {p1}/{p2} 项：自动增益关、降噪拉到最强、停顿额外衰减、高通 125 Hz。{p3}{p4}左右是哪一路由上方「设备输出」决定，这里没动。说一句话再停顿，看两张图的差别。未保存到 Flash。',{p0:preset.label,p1:done,p2:Object.keys(preset.values).length,p3:skipped.length?t('本机固件不支持、已跳过：{p0}——同一套配置在这台设备上不完整。',{p0:skipped.join('、')}):'',p4:failed.length?t('写入失败 {p0} 项（{p1}），设备未按演示配置生效，请重试。',{p0:failed.length,p1:failed.join('、')}):''}));
  }catch(error){setDemoStatus(t('演示配置未完成：{p0}',{p0:errorText(error)}));}
  finally{applyingDemo=false;setBusy();}
}
async function applyParameter(key,next,epoch=usbEpoch) {
  if(!usb||epoch!==usbEpoch||recording)return false;
  const device=usb,old=snapshot.parameters[key]?.value;pendingWrites++;setBusy();$('parameter-status').textContent=t('正在写入 {p0}…',{p0:key});
  try {const actual=await device.write(key,next);if(epoch!==usbEpoch)return false;snapshot.parameters[key]={value:actual,supported:true};$('parameter-status').textContent=t('{p0} 回读确认：{p1}',{p0:key,p1:formatValue(actual)});addEvent(`${key} ${formatValue(old)} → ${formatValue(actual)}`);return true;}
  catch(error){if(epoch===usbEpoch){$('parameter-status').textContent=t('{p0} 未确认：{p1}',{p0:key,p1:errorText(error)});notice(t('调参失败：{p0}',{p0:errorText(error)}),true);}return false;}
  finally {pendingWrites--;if(epoch===usbEpoch)renderParameters();setBusy();}
}

async function rebootDevice() {
  if(!usb||recording||pendingWrites>0||parameterTimers.size>0)return;
  if(!window.confirm(t('重启设备？所有未保存到 Flash 的参数将恢复默认。')))return;
  const device=usb,epoch=usbEpoch;pendingWrites++;setBusy();$('parameter-status').textContent=t('正在发送重启指令…');
  try {await device.reboot();if(epoch===usbEpoch)notice(t('重启指令已发送。设备重新枚举后请重新连接 USB。'));}
  catch(error){if(epoch===usbEpoch)notice(t('重启失败：{p0}',{p0:errorText(error)}),true);}
  finally {pendingWrites--;if(epoch===usbEpoch){usb=null;snapshot=null;configA=null;renderParameters();setBusy();}}
}

async function listInputs(authorize=false) {
  try {
    if(authorize){const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop());}
    const previous=$('audio-input').value,devices=await capture.listInputs();$('audio-input').replaceChildren(new Option(t('选择 reSpeaker 音频设备'),''));
    devices.filter(d=>d.deviceId&&!['default','communications'].includes(d.deviceId)).forEach((d,i)=>$('audio-input').append(new Option(d.label||t('音频输入 {p0}（未授权名称）',{p0:i+1}),d.deviceId)));
    if([...$('audio-input').options].some(o=>o.value===previous))$('audio-input').value=previous;
    if(authorize)notice(t('已授权麦克风。请在列表中明确选择 reSpeaker，再开始采集。'));
  }catch(error){notice(t('麦克风设备列表不可用：{p0}',{p0:errorText(error)}),true);}setBusy();
}
async function startAudio() {
  if(!$('audio-input').value||running||starting)return;starting=true;setBusy();resetSignal();
  try {const info=await capture.start($('audio-input').value);running=true;captureCaps=info.capabilities||null;
    const processing=info.processing||{},enabled=Object.entries(processing).filter(([,v])=>v===true).map(([k])=>k);
    $('audio-status').textContent=`${$('audio-input').selectedOptions[0].textContent} · ${info.sampleRate} Hz`;
    if(enabled.length){await stopAudio();throw new Error(t('浏览器仍启用了 {p0}，停止采集以免混入额外处理',{p0:enabled.join(', ')}));}
    const unknown=Object.values(processing).some(v=>v!==true&&v!==false);
    notice(unknown?t('已开始真实采集；浏览器部分音频处理设置未报告，前后对比需核实系统音效。'):t('已开始真实采集；浏览器音频处理已关闭。请确认声道用途。'));
  }catch(error){running=false;await capture.stop().catch(()=>{});resetSignal();notice(t('采集失败：{p0}',{p0:errorText(error)}),true);}
  finally {starting=false;setBusy();}
}
async function stopAudio() {running=false;starting=false;await capture.stop().catch(()=>{});resetSignal();$('audio-status').textContent=t('采集已停止');setBusy();}
function resetSignal(){captureCaps=null;zeroSince=null;$('signal-health').textContent='';latestFrame=null;actualChannels=0;histories=[];$('stream-info').textContent=t('等待音频流');$('original-channel').replaceChildren(new Option(t('等待采集'),'0'));$('processed-channel').replaceChildren(new Option(t('不比较'),''));$('confirm-map').checked=false;updateRoutingSummary();$('original-title').textContent=t('观察通道');$('processed-title').textContent=t('对比通道');$('channel-monitor').textContent=t('开始采集后显示浏览器实际提供的通道。');drawSpectra();}
function configureChannels(count) {
  actualChannels=count;histories=Array.from({length:count},()=>[]);$('original-channel').replaceChildren();$('processed-channel').replaceChildren(new Option(t('不比较'),''));
  for(let i=0;i<count;i++){const label=t('USB 通道 {p0}（用途待确认）',{p0:i+1});$('original-channel').append(new Option(label,i));$('processed-channel').append(new Option(label,i));}
  const preferred=DEFAULT_CHANNEL_MAPS[snapshot?.identity?.controlProtocol];
  const usePreferred=preferred&&count>=preferred.minChannels;
  $('original-channel').value=String(usePreferred?preferred.original:0);
  $('processed-channel').value=usePreferred?String(preferred.processed):count>1?'1':'';
  $('confirm-map').checked=false;updateMap();$('channel-monitor').replaceChildren();
  for(let i=0;i<count;i++){const row=document.createElement('div');row.className='channel';const label=document.createElement('span');label.id=`channel-name-${i}`;label.textContent=channelLabel(i);const canvas=document.createElement('canvas');canvas.id=`wave-${i}`;canvas.className='wave';canvas.setAttribute('aria-label',t('USB 通道 {p0} 波形',{p0:i+1}));canvas.setAttribute('role','img');const level=document.createElement('span');level.id=`level-${i}`;level.className='level';level.textContent='— dBFS';const head=document.createElement('div');head.className='channel-head';head.append(label,level);const meter=document.createElement('div');meter.className='channel-meter';meter.setAttribute('aria-hidden','true');const fill=document.createElement('i');fill.id=`meter-${i}`;meter.append(fill);row.append(head,meter,canvas);$('channel-monitor').append(row);}setBusy();
}
function updateMap(){let map=currentMap();if(map.processed===map.original){$('processed-channel').value='';map=currentMap();notice(t('请选择不同的两个通道；同一路不能作为前后对比。'),true);}if(!recording)capture.setChannels(map);const confirmed=$('confirm-map').checked&&map.processed!==null&&!matchingOutputRoutes();
  updateRoutingSummary();
  $('original-title').textContent=confirmed?t('原声 · USB {p0}（用户确认）',{p0:map.original+1}):channelLabel(map.original);
  $('processed-title').textContent=map.processed===null?(actualChannels===1?t('仅收到 1 路输入'):t('未选择对比通道')):confirmed?t('处理后 · USB {p0}（用户确认）',{p0:map.processed+1}):channelLabel(map.processed);
  for(let i=0;i<actualChannels;i++){const label=$(`channel-name-${i}`);if(label)label.textContent=channelLabel(i);}
  $('mapping-note').textContent=actualChannels===1?t('浏览器当前只提供 1 路输入，暂时无法进行双通道对比。'):confirmed?t('通道用途由用户依据固件与路由确认。两路录音使用同一时间窗口。'):t('通道用途未确认：可以观察与录音，但不能据此宣称处理前后效果。');drawSpectra();setBusy();}
capture.addEventListener('frame',event=>{if(!running&&!starting)return;const frame=event.detail;latestFrame=frame;const allZero=frame.channels.every(c=>c.peak===0);zeroSince=allZero?(zeroSince??performance.now()):null;$('signal-health').textContent=zeroSince!==null&&performance.now()-zeroSince>2000?t('已连续收到全零音频。请检查设备连接；这不是正常的安静声谱。停止并重新采集，仍无信号时重新插拔 USB。'):'';if(frame.channelCount!==actualChannels)configureChannels(frame.channelCount);
  frame.channels.forEach((channel,i)=>{histories[i].push({time:frame.time,spectrum:channel.spectrum,rms:channel.rms,peak:channel.peak});while(histories[i].length&&histories[i][0].time<frame.time-8000)histories[i].shift();});
  $('stream-info').textContent=t('实际 {p0} 通道 · {p1} Hz',{p0:frame.channelCount,p1:frame.sampleRate});
  drawSpectra();frame.channels.forEach((channel,i)=>{drawWave($(`wave-${i}`),channel.waveform);$(`level-${i}`).textContent=`${channel.rms===0?t('无信号'):db(channel.rms).toFixed(1)+' dBFS'}${channel.peak>=.99?t(' · 接近削波'):''}`;setMeter($(`meter-${i}`),channel,i);});
});
capture.addEventListener('error',event=>{notice(t('音频中断：{p0}',{p0:errorText(event.error||event.detail||t('请重新连接设备'))}),true);stopAudio();});

function prepareCanvas(canvas){const rect=canvas.getBoundingClientRect(),scale=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.round(rect.width)),h=Math.max(1,Math.round(rect.height));if(canvas.width!==w*scale||canvas.height!==h*scale){canvas.width=w*scale;canvas.height=h*scale;}const ctx=canvas.getContext('2d');ctx.setTransform(scale,0,0,scale,0,0);ctx.clearRect(0,0,w,h);return {ctx,w,h};}
function spectralColor(value){const t=Math.max(0,Math.min(1,(db(value)+90)/90))*(palette.length-1),i=Math.min(palette.length-2,Math.floor(t)),f=t-i;return `rgb(${palette[i].map((v,j)=>Math.round(v+(palette[i+1][j]-v)*f)).join(',')})`;}
function drawSpectrum(canvas,channel){const {ctx,w,h}=prepareCanvas(canvas);ctx.fillStyle=resolvedColor('--surface2');ctx.fillRect(0,0,w,h);ctx.strokeStyle=resolvedColor('--line');ctx.lineWidth=.5;ctx.beginPath();for(let i=1;i<8;i++){ctx.moveTo(i*w/8,0);ctx.lineTo(i*w/8,h);}for(let i=1;i<4;i++){ctx.moveTo(0,i*h/4);ctx.lineTo(w,i*h/4);}ctx.stroke();const history=channel===null?null:histories[channel];if(!history?.length){ctx.fillStyle=resolvedColor('--muted');ctx.font='12px system-ui';ctx.textAlign='center';ctx.fillText(channel===null?t('选择对比通道'):t('等待音频输入'),w/2,h/2);ctx.textAlign='left';return;}const now=latestFrame.time,maxFrequency=Math.min(8000,latestFrame.sampleRate/2),bins=64;
  history.forEach((frame,index)=>{const x=Math.max(0,w*(1-(now-frame.time)/8000)),next=history[index+1]?.time??now+50,width=Math.max(1,(next-frame.time)*w/8000);for(let band=0;band<bins;band++){const freq=(band+.5)/bins*maxFrequency,bin=Math.min(frame.spectrum.length-1,Math.floor(freq/(latestFrame.sampleRate/2)*frame.spectrum.length));ctx.fillStyle=spectralColor(frame.spectrum[bin]);ctx.fillRect(x,h-(band+1)*h/bins,width,Math.ceil(h/bins));}});
}
// Fixed dB scale shared by every channel; visualization does not change PCM.
const ENERGY_SPAN=60;
const FULL_SCALE={top:0,floor:-ENERGY_SPAN};
function energyWindow(index){
  let peak=-Infinity;
  for(const frame of histories[index]||[])if(frame.rms>0)peak=Math.max(peak,db(frame.rms));
  if(!Number.isFinite(peak))return FULL_SCALE;
  const top=Math.max(-90,Math.min(0,Math.ceil((peak+6)/10)*10));
  return {top,floor:top-ENERGY_SPAN};
}
function levelFraction(rms,window=FULL_SCALE){return Math.max(0,Math.min(1,(db(rms)-window.floor)/ENERGY_SPAN));}
function setMeter(element,channel,index=null){if(!element)return;element.style.width=`${channel?levelFraction(channel.rms,index===null?FULL_SCALE:energyWindow(index))*100:0}%`;element.classList.toggle('clipping',Boolean(channel&&channel.peak>=.99));}
function drawEnergy(canvas,channel){
  const {ctx,w,h}=prepareCanvas(canvas),left=38,bottom=h-20,top=22,height=bottom-top,width=w-left-10;
  const win=channel===null?FULL_SCALE:energyWindow(channel);
  ctx.fillStyle=resolvedColor('--surface2');ctx.fillRect(0,0,w,h);ctx.font='10px system-ui';
  for(const level of [win.floor,win.floor+20,win.floor+40,win.top]){const y=bottom-(level-win.floor)/ENERGY_SPAN*height;ctx.strokeStyle=resolvedColor('--line');ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(w-10,y);ctx.stroke();ctx.fillStyle=resolvedColor('--muted');ctx.fillText(String(level),8,y+3);}
  ctx.fillStyle=resolvedColor('--muted');ctx.fillText(t('声音更强 ↑'),left,13);
  const history=channel===null?null:histories[channel];
  if(!history?.length){ctx.textAlign='center';ctx.fillText(channel===null?t('选择第二路，比较声音起伏'):t('开始采集后，说句话试试'),w/2,h/2);ctx.textAlign='left';return;}
  const now=latestFrame.time;ctx.save();ctx.beginPath();ctx.rect(left,top,width,height);ctx.clip();
  ctx.fillStyle=resolvedColor('--accent');
  history.forEach((frame,i)=>{const x=left+width*(1-(now-frame.time)/8000),next=history[i+1]?.time??now+50,bw=Math.max(1,(next-frame.time)*width/8000-1),bar=levelFraction(frame.rms,win)*height;ctx.globalAlpha=.8;ctx.fillRect(x,bottom-bar,bw,bar);});ctx.restore();
}
function drawFrequency(canvas,channel){
  const {ctx,w,h}=prepareCanvas(canvas),left=38,right=w-12,top=22,bottom=h-24;
  ctx.fillStyle=resolvedColor('--surface2');ctx.fillRect(0,0,w,h);ctx.font='10px system-ui';
  for(const level of [-90,-60,-30,0]){const y=bottom-(level+90)/90*(bottom-top);ctx.strokeStyle=resolvedColor('--line');ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle=resolvedColor('--muted');ctx.fillText(String(level),6,y+3);}
  const history=channel===null?null:histories[channel];if(!history?.length){ctx.fillStyle=resolvedColor('--muted');ctx.textAlign='center';ctx.fillText(channel===null?t('选择对比通道'):t('等待音频输入'),w/2,h/2);ctx.textAlign='left';return;}
  const maxFrequency=Math.min(8000,latestFrame.sampleRate/2),recent=history.filter(f=>f.time>=latestFrame.time-400),n=recent[0].spectrum.length,lastBin=Math.min(n-1,Math.floor(maxFrequency/(latestFrame.sampleRate/2)*n));
  ctx.strokeStyle=resolvedColor('--accent-ink');ctx.lineWidth=2;ctx.beginPath();
  for(let i=0;i<=lastBin;i++){const magnitude=Math.sqrt(recent.reduce((sum,f)=>sum+f.spectrum[i]**2,0)/recent.length),x=left+(right-left)*i/Math.max(1,lastBin),y=bottom-Math.max(0,Math.min(1,(db(magnitude)+90)/90))*(bottom-top);i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.fillStyle=resolvedColor('--muted');ctx.fillText(t('低频 · 0 Hz'),left,h-6);ctx.textAlign='right';ctx.fillText(t('高频 · {p0} kHz',{p0:maxFrequency/1000}),right,h-6);ctx.textAlign='left';
}
function drawSpectra(){
  const map=currentMap();
  if($('energy-guide')){
    const wins=[map.original,map.processed].filter(i=>i!==null).map(i=>energyWindow(i));
    const scale=wins.length===2&&wins[0].top!==wins[1].top?t('两张图各自按自己的信号调整刻度（左 {p0}…{p1}，右 {p2}…{p3} dBFS），因为两路抽头的增益不同——不要横向比柱子高度，要比就看下面的落差数字。',{p0:wins[0].floor,p1:wins[0].top,p2:wins[1].floor,p3:wins[1].top}):t('两张图当前使用同一刻度。');
    $('energy-guide').textContent=t('柱子越高，这一路自己的声音越强。{p0}',{p0:scale});
  }
  const draw=signalView==='energy'?drawEnergy:signalView==='frequency'?drawFrequency:drawSpectrum;
  for(const [name,index]of [['original',map.original],['processed',map.processed]]){const canvas=$(`${name}-spectrum`),channel=index===null?null:latestFrame?.channels[index];draw(canvas,index);canvas.setAttribute('aria-label',t('{p0}通道{p1}',{p0:name==='original'?t('观察'):t('对比'),p1:signalView==='energy'?t('声音强弱随时间变化'):signalView==='frequency'?t('频段分布曲线'):t('频率细节声谱图')}));$(`${name}-level`).textContent=channel?(channel.rms===0?t('无信号'):`${db(channel.rms).toFixed(1)} dBFS`):'— dBFS';setMeter($(`${name}-meter`),channel,index);}
  const note=$('comparison-note');if(!note)return;if(matchingOutputRoutes()){note.textContent=t('设备左右输出路由相同：当前观察的是同一信号，不能据此评估处理前后差异。');return;}
  const a=latestFrame?.channels[map.original],b=map.processed===null?null:latestFrame?.channels[map.processed];
  if(!a||!b){note.textContent=t('选择两路输入，观察同一时刻的声音强弱。');return;}
  if(a.rms<1e-6||b.rms<1e-6){note.textContent=t('有通道低于 −120 dBFS，视为无信号；检查该路是否被固件送出。');return;}
  // A single level difference cannot separate noise suppression from plain gain: read the quiet
  // stretches and the loud stretches apart. Suppression shows up as the floor dropping more than the peaks.
  const percentileDb=(index,ratio)=>{
    const values=(histories[index]||[]).map(f=>f.rms).filter(v=>v>0).sort((x,y)=>x-y);
    return values.length<20?null:db(values[Math.min(values.length-1,Math.floor(values.length*ratio))]);
  };
  const floorA=percentileDb(map.original,.1),floorB=percentileDb(map.processed,.1);
  const peakA=percentileDb(map.original,.9),peakB=percentileDb(map.processed,.9);
  if(floorA===null||floorB===null||peakA===null||peakB===null){note.textContent=t('正在累计 8 秒样本，之后给出安静段与响声段的分别对比。');return;}
  const sideName=index=>index===map.original?t('观察'):index===map.processed?t('对比'):`USB ${index+1}`;
  // Each tap has its own gain, so cross-channel levels are not comparable. What is comparable is how
  // far each channel separates speech from silence: suppression widens that span, plain gain does not.
  const spanA=peakA-floorA,spanB=peakB-floorB,gained=spanB-spanA;
  const agc=snapshot?.parameters?.PP_AGCONOFF?.value===true||snapshot?.parameters?.AGCONOFF?.value===true;
  const verdict=gained>=6?t('处理后把人声与底噪的落差拉大了 {p0} dB——这就是降噪效果，与两路的绝对音量无关。',{p0:gained.toFixed(1)})
    :gained<=-6?t('处理后的落差反而更小，检查对比通道是不是选反了。')
    :t('两路落差接近，看不出明显降噪{p0}。',{p0:agc?t('——「自动增益」还开着，先关掉'):t('；在安静环境里说一句话再停顿几秒')});
  // A tap the firmware does not actually feed reads as near-silence: say so instead of calling it "降噪".
  // Both taps flat means the window holds only room tone. Say that, instead of reading a verdict
  // (or a dead-channel warning) out of eight seconds of silence.
  if(spanA<6&&spanB<6){
    note.textContent=t('过去 8 秒｜{p0} 落差 {p1} dB，{p2} 落差 {p3} dB——两路都没有明显起伏，这段时间里多半没人说话。对着设备说一句话，再停顿 3 秒。',{p0:sideName(map.original),p1:spanA.toFixed(1),p2:sideName(map.processed),p3:spanB.toFixed(1)});
    return;
  }
  const starved=[[map.original,peakA,spanA],[map.processed,peakB,spanB]].filter(([,peak,span])=>peak<-90&&span<3)
    .map(([index,peak,span])=>t('{p0}路峰值 {p1} dBFS、落差只有 {p2} dB，基本没有起伏——该固件可能没有把这个抽头送出来，在「设备输出」里换一路试试。',{p0:sideName(index),p1:peak.toFixed(1),p2:span.toFixed(1)}));
  note.textContent=t('过去 8 秒｜{p0}：响声段 {p1} / 安静段 {p2}，落差 {p3} dB。{p4}：响声段 {p5} / 安静段 {p6}，落差 {p7} dB。{p8}',{p0:sideName(map.original),p1:peakA.toFixed(1),p2:floorA.toFixed(1),p3:spanA.toFixed(1),p4:sideName(map.processed),p5:peakB.toFixed(1),p6:floorB.toFixed(1),p7:spanB.toFixed(1),p8:starved.length?starved.join(' '):verdict});
}
function drawWave(canvas,samples){if(!canvas)return;const {ctx,w,h}=prepareCanvas(canvas);ctx.strokeStyle=resolvedColor('--line');ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke();ctx.strokeStyle=resolvedColor('--accent-ink');ctx.lineWidth=1.5;ctx.beginPath();samples.forEach((v,i)=>{const x=i*w/Math.max(1,samples.length-1),y=h/2-Math.max(-1,Math.min(1,v*waveZoom))*h*.43;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();if(samples.some(v=>Math.abs(v*waveZoom)>1)){ctx.fillStyle=resolvedColor('--muted');ctx.font='10px system-ui';ctx.fillText(t('显示超出范围 · 可降低倍率'),6,12);}}
function drawDoa(){const {ctx,w,h}=prepareCanvas($('doa-chart')),cx=w/2,cy=h/2,r=Math.min(w,h)*.39;ctx.strokeStyle=resolvedColor('--line');ctx.lineWidth=1;for(const ratio of [.35,.7,1]){ctx.beginPath();ctx.arc(cx,cy,r*ratio,0,Math.PI*2);ctx.stroke();}ctx.fillStyle=resolvedColor('--muted');ctx.font='12px system-ui';ctx.fillText('0°',cx-7,cy-r-7);ctx.fillText('90°',cx+r+4,cy+4);$('doa-value').textContent='—';if(!lastDoa)return;const angle=lastDoa.angle*Math.PI/180;ctx.strokeStyle=resolvedColor(lastDoa.speech?'--accent-ink':'--muted');ctx.setLineDash(lastDoa.speech?[]:[5,5]);ctx.lineWidth=lastDoa.speech?3:2;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+Math.sin(angle)*r,cy-Math.cos(angle)*r);ctx.stroke();$('doa-value').textContent=`${Math.round(lastDoa.angle)}°`;$('doa-value').style.opacity=lastDoa.speech?'1':'.55';ctx.setLineDash([]);}

function ensureWorker(){if(worker)return;worker=new Worker('./transcription-worker.js',{type:'module'});worker.onmessage=event=>{const message=event.data;if(message.type==='ready'){modelReady=true;modelLoading=false;$('model-status').textContent=t('Tiny 已就绪 · 本地运行');}
  if(message.type==='progress'){$('model-status').textContent=t('加载 Tiny：{p0}{p1}',{p0:message.file||message.status||t('下载模型'),p1:Number.isFinite(message.progress)?` ${Math.round(message.progress)}%`:''});}
  if(message.type==='result'||message.type==='error'){const job=jobs.get(message.id);if(job){jobs.delete(message.id);message.type==='result'?job.resolve(message.text):job.reject(new Error(message.error||t('识别失败')));}else if(message.type==='error'){modelReady=false;modelLoading=false;$('model-status').textContent=t('加载失败：{p0}',{p0:message.error});notice(t('Tiny 未就绪：{p0}',{p0:message.error}),true);}}setBusy();};worker.onerror=event=>{modelReady=false;modelLoading=false;for(const job of jobs.values())job.reject(new Error(event.message));jobs.clear();worker.terminate();worker=null;$('model-status').textContent=t('模型运行失败，可重试加载');setBusy();};}
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
    title.textContent=lastRecord.labels?.[index]||t('USB 通道 {p0}',{p0:index+1});canvas.id=`record-wave-${index}`;canvas.className='record-wave';canvas.setAttribute('role','img');canvas.setAttribute('aria-label',t('USB 通道 {p0} 录音波形，显示放大 8 倍',{p0:index+1}));
    recordUrls[index]=URL.createObjectURL(wavBlob(samples,lastRecord.sampleRate));player.src=recordUrls[index];player.controls=true;player.preload='metadata';player.setAttribute('aria-label',t('试听 USB 通道 {p0}',{p0:index+1}));
    player.addEventListener('play',()=>document.querySelectorAll('#recordings audio').forEach(other=>{if(other!==player)other.pause();}));
    info.className='meta';info.textContent=t('{p0} 秒 · {p1} Hz · 波形显示 ×8',{p0:(samples.length/lastRecord.sampleRate).toFixed(1),p1:lastRecord.sampleRate});
    download.className='experiment-link';download.href=recordUrls[index];download.download=`respeaker-${lastRecord.id}-usb-${index+1}.wav`;download.textContent=t('下载 WAV');
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
async function recordAudio(){if(recording||!running)return;cancelWrites();recording=true;lastRecord=null;clearRecordPlayers();$('record-progress').value=0;const recordStart=performance.now();const progressTimer=setInterval(()=>{$('record-progress').value=Math.min(5.9,(performance.now()-recordStart)/1000);},100);setBusy();$('record-status').textContent=t('正在录制 6 秒 · 参数与声道选择已锁定');$('original-text').textContent=t('录音中…');$('processed-text').textContent=currentMap().processed===null?t('未选择第二路'):t('录音中…');const settings=Object.fromEntries(supportedParameters().map(p=>[p.key,snapshot.parameters[p.key].value]));const confirmed=$('confirm-map').checked&&!matchingOutputRoutes();
  try{const result=await capture.record(6);lastRecord={...result,labels:result.allChannels.map((_,index)=>channelLabel(index)),settings,confirmed,device:$('audio-input').selectedOptions[0]?.textContent,id:++recordId};renderRecordPlayers();$('record-progress').value=6;$('record-original-title').textContent=lastRecord.labels[result.channels.original];$('record-processed-title').textContent=result.processed?lastRecord.labels[result.channels.processed]:t('未录制第二路');$('original-text').textContent=t('录音就绪，等待转录');$('processed-text').textContent=result.processed?t('录音就绪，等待转录'):t('当前仅有单路录音');$('record-status').textContent=t('{p0} · {p1} 秒 · {p2} Hz · {p3}',{p0:new Date(result.startedAt).toLocaleTimeString(),p1:(result.original.length/result.sampleRate).toFixed(1),p2:result.sampleRate,p3:confirmed?t('用户已确认原声/处理后映射'):t('通道用途未确认')});}
  catch(error){$('record-status').textContent=t('录音失败：{p0}',{p0:errorText(error)});$('original-text').textContent=t('没有完成的录音');$('processed-text').textContent=t('没有完成的录音');}
  finally{clearInterval(progressTimer);recording=false;if(!lastRecord)$('record-progress').value=0;setBusy();}
}
async function transcribeRecord(){if(!lastRecord||recording||transcribing)return;transcribing=true;setBusy();const completed=new Set();const record=lastRecord,language=$('language').value;$('original-text').textContent=t('Tiny 正在识别…');if(record.processed)$('processed-text').textContent=t('等待同一模型识别…');
  try{ensureWorker();if(!modelReady){modelLoading=true;$('model-status').textContent=t('首次转录，正在加载 Tiny…');}const text=await transcribeChannel(`${record.id}-original`,record.original,record.sampleRate,language);$('original-text').textContent=text||t('未识别出文字');completed.add('original');if(record.processed){$('processed-text').textContent=t('Tiny 正在识别…');$('processed-text').textContent=await transcribeChannel(`${record.id}-processed`,record.processed,record.sampleRate,language)||t('未识别出文字');completed.add('processed');}}
  catch(error){modelLoading=false;if(!modelReady)$('model-status').textContent=t('模型加载失败，点击转录重试；录音仍可试听');for(const name of ['original','processed'])if(record[name]&&!completed.has(name))$(`${name}-text`).textContent=t('转录未完成，可重试；录音仍可试听与下载。');notice(t('本地转录失败：{p0}',{p0:errorText(error)}),true);$('record-status').textContent=t('转录未完成，可保留录音后重试');}finally{transcribing=false;setBusy();}
}

for(const button of document.querySelectorAll('button[data-signal-view]'))button.onclick=()=>{signalView=button.dataset.signalView;document.querySelectorAll('button[data-signal-view]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});$('spectrum-legend').classList.toggle('hidden',signalView!=='spectrum');$('energy-guide').classList.toggle('hidden',signalView!=='energy');$('frequency-guide').classList.toggle('hidden',signalView!=='frequency');document.querySelectorAll('.spectra .axis').forEach(axis=>{axis.children[0].textContent=signalView==='frequency'?t('最近 0.4 秒平均'):t('过去 8 秒');axis.children[1].textContent=signalView==='frequency'?t('频率：低 → 高'):t('时间 → 现在');});drawSpectra();};
$('wave-zoom').onchange=()=>{waveZoom=Number($('wave-zoom').value);$('monitor-note').textContent=t('电平条使用真实电平；波形显示 ×{p0}，不改变录音或设备增益。',{p0:waveZoom});latestFrame?.channels.forEach((c,i)=>drawWave($(`wave-${i}`),c.waveform));};
function setWorkspaceTab(name){
  workspaceTab=name;const echo=name==='echo',signal=name==='noise'||echo;
  document.querySelectorAll('[data-workspace]').forEach(b=>{const active=b.dataset.workspace===name;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
  $('signal-title').textContent=echo?t('回声对比'):t('声音对比');
  $('signal-panel').classList.toggle('hidden',!signal);$('signal-panel').setAttribute('aria-labelledby',echo?'tab-echo':'tab-noise');$('spatial-panel').classList.toggle('hidden',name!=='spatial');$('transcription').classList.toggle('hidden',name!=='transcription');$('noise-tools').classList.toggle('hidden',echo||liteControlsHidden());$('echo-tools').classList.toggle('hidden',!echo);$('echo-tuning').classList.toggle('hidden',!echo||liteControlsHidden());
  $('experiment-guide').textContent=echo?(liteControlsHidden()?t('播放参考语音，同时说话：观察两路输入变化，再录音试听。'):t('播放参考语音，同时说话：在同一组图里观察两路变化，再录音试听。')):t('说一句话，再停顿：比较人声起伏和停顿时的声音强度。');
  drawSpectra();drawDoa();drawRecordWaves();latestFrame?.channels.forEach((c,i)=>drawWave($(`wave-${i}`),c.waveform));
}
for(const button of document.querySelectorAll('[data-workspace]')){button.onclick=()=>setWorkspaceTab(button.dataset.workspace);button.onkeydown=event=>{const buttons=[...document.querySelectorAll('[data-workspace]')].filter(b=>!b.disabled),index=buttons.indexOf(button);let next;if(event.key==='ArrowRight')next=(index+1)%buttons.length;if(event.key==='ArrowLeft')next=(index+buttons.length-1)%buttons.length;if(event.key==='Home')next=0;if(event.key==='End')next=buttons.length-1;if(next!==undefined){event.preventDefault();buttons[next].focus();setWorkspaceTab(buttons[next].dataset.workspace);}};}
document.querySelector('#echo-tuning .experiment-link').onclick=event=>{event.preventDefault();setWorkspaceTab('transcription');$('tab-transcription').focus();if(!$('record').disabled)recordAudio();else $('record-status').textContent=t('先开始音频采集，再点击开始录音。');};
for(const event of ['play','pause','ended','emptied','error'])$('reference-player').addEventListener(event,()=>{const player=$('reference-player');$('reference-indicator').textContent=player.error?t('测试音频无法播放，请选择浏览器支持的音频文件'):player.paused?t('已暂停 · 点击播放后观察下方两路'):t('正在播放 · 先保持安静，再边播放边说话');if(workspaceTab==='echo')$('experiment-guide').textContent=player.paused?t('准备测试音频和播放输出，再观察下方回声对比。'):liteControlsHidden()?t('测试音频播放中：观察两路输入变化，也可录下试听。'):t('测试音频播放中：切换回声抑制，观察两路变化，也可录下试听。');});
$('connect-usb').onclick=connectUsb;$('disconnect-usb').onclick=async()=>{const device=usb;clearUsb(t('USB 控制已断开'));await device?.disconnect().catch(()=>{});};
$('authorize-audio').onclick=()=>listInputs(true);$('audio-input').onchange=()=>{renderParameters();setBusy();};$('start-audio').onclick=startAudio;$('stop-audio').onclick=stopAudio;$('reboot-device').onclick=rebootDevice;
for(const id of ['original-channel','processed-channel'])$(id).onchange=()=>{$('confirm-map').checked=false;updateMap();};$('confirm-map').onchange=updateMap;
$('control-mode').onclick=()=>{$('workbench').showModal();};
$('close-parameters').onclick=()=>{$('workbench').close();};
$('ui-lang').value=LANG==='zh'?'zh-hans':'en';
$('ui-lang').onchange=()=>{
  const url=new URL(location.href);
  url.searchParams.set('lang',$('ui-lang').value);
  location.replace(url);
};
$('connection-toggle').onclick=()=>setConnectionPanel($('connection-panel').classList.contains('hidden'));
$('begin').onclick=()=>{setConnectionPanel(true);$('connect-usb').focus();};
$('save-a').onclick=()=>{configA={epoch:usbEpoch,values:Object.fromEntries(supportedParameters().map(p=>[p.key,snapshot.parameters[p.key].value]))};addEvent(t('配置 A 已记录到当前页面'));setBusy();};
$('restore-a').onclick=async()=>{if(!configA||configA.epoch!==usbEpoch||recording)return;const epoch=usbEpoch;for(const [key,value]of Object.entries(configA.values)){if(epoch!==usbEpoch)return;if(snapshot.parameters[key]?.supported)await applyParameter(key,value,epoch);}};
$('save-flash').onclick=async()=>{if(!usb||recording)return;const epoch=usbEpoch;pendingWrites++;setBusy();try{await usb.save();if(epoch===usbEpoch)addEvent(t('设备已接受 Flash 保存指令'));}catch(error){notice(t('保存未确认：{p0}',{p0:errorText(error)}),true);}finally{pendingWrites--;setBusy();}};
$('record').onclick=recordAudio;$('transcribe').onclick=transcribeRecord;
$('apply-demo').onclick=()=>runDemo(false);$('restore-demo').onclick=()=>runDemo(true);
$('apply-output-routing').onclick=()=>configureRouting('custom');$('restore-output-routing').onclick=()=>configureRouting('restore');
$('reference-file').onchange=()=>{if(playbackUrl)URL.revokeObjectURL(playbackUrl);const file=$('reference-file').files[0];$('reference-filename').textContent=file?file.name:t('尚未选择文件');if(file){playbackUrl=URL.createObjectURL(file);$('reference-player').src=playbackUrl;}};
$('choose-output').onclick=async()=>{try{if(navigator.mediaDevices.selectAudioOutput){const device=await navigator.mediaDevices.selectAudioOutput();await $('reference-player').setSinkId(device.deviceId);$('reference-status').textContent=t('播放输出：{p0} · 请核对为 reSpeaker',{p0:device.label||t('已选择设备')});}else if($('reference-player').setSinkId){const devices=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='audiooutput'&&/respeaker/i.test(d.label));if(devices.length!==1)throw new Error(t('请在系统声音设置中选择 reSpeaker 播放输出；当前无法唯一确定输出设备'));await $('reference-player').setSinkId(devices[0].deviceId);$('reference-status').textContent=t('播放输出：{p0}',{p0:devices[0].label});}else throw new Error(t('此浏览器不支持网页选择输出，请在系统声音设置中选择 reSpeaker'));}catch(error){$('reference-status').textContent=errorText(error);}};
navigator.mediaDevices?.addEventListener?.('devicechange',()=>{if(!running&&!starting)listInputs();});
window.addEventListener('pagehide',()=>{++usbEpoch;cancelWrites();clearTimeout(doaTimer);capture.stop();usb?.disconnect();worker?.terminate();if(playbackUrl)URL.revokeObjectURL(playbackUrl);Object.values(recordUrls).forEach(url=>URL.revokeObjectURL(url));});
new ResizeObserver(()=>{drawSpectra();drawDoa();drawRecordWaves();}).observe($('lab'));matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawSpectra();drawDoa();});
if(!window.isSecureContext)notice(t('请通过 HTTPS 或 localhost 打开页面，浏览器设备权限需要安全环境。'),true);
if(!navigator.usb)$('usb-status').textContent=t('此浏览器没有 WebUSB，可使用支持该功能的桌面 Chrome / Edge；音频采集可单独使用。');
translateDom();
renderParameters();drawSpectra();drawDoa();setBusy();
