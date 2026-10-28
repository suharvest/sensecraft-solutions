/* Browser WebUSB support for reSpeaker XVF devices.
 *
 * This module deliberately does not claim USB interfaces.  The audio function
 * belongs to the browser's audio stack; control requests use the device
 * recipient and are safe to issue while that function is streaming.
 */

const VID = 0x2886;
const STATUS_OK = 0;
const STATUS_RETRY = 64;
const MAX_RETRIES = 64;
const RETRY_DELAY_MS = 10;
const CONTROL_DEADLINE_MS = 1800;

const CONTROLS = [
  // 降噪（resource 17 postprocessor）
  { key: 'PP_MIN_NS', primary: true, plain: '环境噪声抑制', effect: '调小：停顿时的底噪更低，能量图的谷更深；调得太小人声会发闷。', label: '噪声抑制下限', min: 0, max: 1, step: 0.01, type: 'float', wireType: 'float', resource: 17, command: 21, count: 1, group: 'noise' },
  { key: 'PP_MIN_NN', label: '非稳态噪声下限', min: 0, max: 1, step: 0.01, type: 'float', wireType: 'float', resource: 17, command: 22, count: 1, group: 'noise' },
  { key: 'PP_LIMITONOFF', label: '输出限幅器', min: 0, max: 1, step: 1, type: 'bool', wireType: 'int32', resource: 17, command: 19, count: 1, group: 'noise' },
  { key: 'PP_LIMITPLIMIT', label: '限幅功率上限', min: 0.0001, max: 1, step: 0.001, type: 'float', wireType: 'float', resource: 17, command: 20, count: 1, group: 'noise' },
  { key: 'PP_ATTNS_MODE', primary: true, plain: '停顿时再压一层噪声', effect: '打开后，不说话的那几秒能量图会明显往下掉。', label: '非语音期额外衰减', min: 0, max: 1, step: 1, type: 'bool', wireType: 'int32', resource: 17, command: 32, count: 1, group: 'noise' },
  { key: 'PP_ATTNS_NOMINAL', label: '非语音衰减量', min: 0, max: 1, step: 0.01, type: 'float', wireType: 'float', resource: 17, command: 33, count: 1, group: 'noise' },
  { key: 'PP_ATTNS_SLOPE', label: '衰减随增益斜率', min: 0, max: 5, step: 0.1, type: 'float', wireType: 'float', resource: 17, command: 34, count: 1, group: 'noise' },
  // 增益（AGC 链路）
  { key: 'PP_AGCONOFF', primary: true, plain: '自动增益', effect: '打开后远处说话会被自动拉高，安静时底噪也一起被放大——降噪效果会被它抬回来。对比前后时先关掉。', label: '自动增益控制', min: 0, max: 1, step: 1, type: 'bool', wireType: 'int32', resource: 17, command: 10, count: 1, group: 'gain' },
  { key: 'PP_AGCMAXGAIN', primary: true, plain: '自动增益上限', effect: '上限越大，远处的声音拉得越高，底噪被放大的风险也越大。', label: 'AGC 最大增益（倍）', min: 1, max: 1000, step: 1, type: 'float', wireType: 'float', resource: 17, command: 11, count: 1, group: 'gain' },
  { key: 'PP_AGCDESIREDLEVEL', label: 'AGC 目标电平（功率）', min: 0.0001, max: 1, step: 0.0001, type: 'float', wireType: 'float', resource: 17, command: 12, count: 1, group: 'gain' },
  { key: 'PP_AGCTIME', label: 'AGC 时间常数（秒）', min: 0.5, max: 4, step: 0.05, type: 'float', wireType: 'float', resource: 17, command: 14, count: 1, group: 'gain' },
  { key: 'PP_AGCFASTTIME', label: 'AGC 峰值回落时间（秒）', min: 0.05, max: 4, step: 0.05, type: 'float', wireType: 'float', resource: 17, command: 15, count: 1, group: 'gain' },
  // 回声消除
  { key: 'PP_ECHOONOFF', primary: true, plain: '回声抑制', effect: '边放测试音频边说话时打开：对比通道里的喇叭声会被压下去。', label: '回声抑制', min: 0, max: 1, step: 1, type: 'bool', wireType: 'int32', resource: 17, command: 23, count: 1, group: 'echo' },
  { key: 'SHF_BYPASS', primary: true, plain: '听原始麦克风', effect: '切到「旁路」即可对照未处理的声音，用来判断处理到底改了什么。', label: '处理旁路', min: 0, max: 1, step: 1, type: 'enum', wireType: 'uint8', options: [{ value: 0, label: '处理（默认）' }, { value: 1, label: '旁路（原始麦克风）' }], resource: 33, command: 70, count: 1, group: 'echo' },
  { key: 'AEC_HPFONOFF', label: '高通滤波器', min: 0, max: 4, step: 1, type: 'enum', wireType: 'int32', options: [{ value: 0, label: '关闭' }, { value: 1, label: '70 Hz' }, { value: 2, label: '125 Hz' }, { value: 3, label: '150 Hz' }, { value: 4, label: '180 Hz' }], resource: 33, command: 1, count: 1, group: 'echo' },
  { key: 'AEC_AECEMPHASISONOFF', label: 'AEC 预加重', min: 0, max: 2, step: 1, type: 'enum', wireType: 'int32', options: [{ value: 0, label: '关闭' }, { value: 1, label: '开' }, { value: 2, label: '开（均衡参考）' }], resource: 33, command: 4, count: 1, group: 'echo' },
  { key: 'AEC_FAR_EXTGAIN', label: '远端参考增益（dB）', min: -60, max: 60, step: 1, type: 'float', wireType: 'float', resource: 33, command: 5, count: 1, group: 'echo' },
  { key: 'PP_GAMMA_E', label: '回声过减 · 直达/早期', min: 0, max: 2, step: 0.05, type: 'float', wireType: 'float', resource: 17, command: 24, count: 1, group: 'echo' },
  { key: 'PP_GAMMA_ETAIL', label: '回声过减 · 尾音', min: 0, max: 2, step: 0.05, type: 'float', wireType: 'float', resource: 17, command: 25, count: 1, group: 'echo' },
  { key: 'PP_GAMMA_ENL', label: '非线性回声过减', min: 0, max: 5, step: 0.1, type: 'float', wireType: 'float', resource: 17, command: 26, count: 1, group: 'echo' },
  { key: 'PP_NLATTENONOFF', label: '非线性回声衰减', min: 0, max: 1, step: 1, type: 'bool', wireType: 'int32', resource: 17, command: 27, count: 1, group: 'echo' },
  { key: 'PP_NLAEC_MODE', label: '非线性 AEC 模式', min: 0, max: 2, step: 1, type: 'enum', wireType: 'int32', options: [{ value: 0, label: '正常' }, { value: 1, label: '训练' }, { value: 2, label: '训练 2' }], resource: 17, command: 28, count: 1, group: 'echo' },
  { key: 'PP_DTSENSITIVE', primary: true, plain: '回声 / 双讲取舍', effect: '数值越小回声压得越干净；越大越保得住你和喇叭同时出声时的人声。', label: '回声抑制 / 双讲权衡', type: 'enum', wireType: 'int32', options: [{ value: 0, label: '0 · 最强回声抑制' }, { value: 1, label: '1' }, { value: 2, label: '2' }, { value: 3, label: '3' }, { value: 4, label: '4' }, { value: 5, label: '5 · 平衡' }, { value: 10, label: '10 · 偏双讲' }, { value: 11, label: '11' }, { value: 12, label: '12' }, { value: 13, label: '13' }, { value: 14, label: '14' }, { value: 15, label: '15 · 最强双讲' }], resource: 17, command: 31, count: 1, group: 'echo' },
  { key: 'PP_FMIN_SPEINDEX', label: '双讲低频抑制分界（Hz）', min: 0, max: 7999, step: 50, type: 'float', wireType: 'float', resource: 17, command: 30, count: 1, group: 'echo' },
  { key: 'AEC_PCD_COUPLINGI', label: '路径变化检测灵敏度', type: 'enum', wireType: 'float', options: [{ value: -1, label: '关闭' }, { value: 0.25, label: '0.25 · 低' }, { value: 0.5, label: '0.5' }, { value: 0.75, label: '0.75' }, { value: 1, label: '1 · 高' }], resource: 33, command: 6, count: 1, group: 'echo' },
  { key: 'AEC_PCD_MINTHR', label: 'PCD 最小阈值', min: 0, max: 0.02, step: 0.001, type: 'float', wireType: 'float', resource: 33, command: 7, count: 1, group: 'echo' },
  { key: 'AEC_PCD_MAXTHR', label: 'PCD 最大阈值', min: 0.025, max: 0.2, step: 0.005, type: 'float', wireType: 'float', resource: 33, command: 8, count: 1, group: 'echo' },
  // 波束（resource 33 beam manager）
  { key: 'AEC_FIXEDBEAMSONOFF', primary: true, plain: '锁定拾音方向', effect: '打开后波束不再跟着声源转，固定指向下面设定的角度。', label: '固定波束模式', min: 0, max: 1, step: 1, type: 'bool', wireType: 'int32', resource: 33, command: 37, count: 1, group: 'beam' },
  { key: 'AEC_FIXEDBEAMSGATING', label: '固定波束语音选通', min: 0, max: 1, step: 1, type: 'enum', wireType: 'uint8', options: [{ value: 0, label: '关' }, { value: 1, label: '开' }], resource: 33, command: 83, count: 1, group: 'beam' },
  { key: 'AEC_FIXEDBEAMSAZIMUTH_VALUES', primary: true, plain: '锁定的方向（弧度）', effect: '0 = 正前方，正值向逆时针。改完绕设备走一圈说话，看哪一路电平最高。', label: '波束方位角（弧度）', min: -3.15, max: 3.15, step: 0.01, type: 'float', wireType: 'float', resource: 33, command: 81, count: 2, group: 'beam' },
  { key: 'AEC_FIXEDBEAMSELEVATION_VALUES', label: '波束俯仰角（弧度）', min: -1.57, max: 1.57, step: 0.01, type: 'float', wireType: 'float', resource: 33, command: 82, count: 2, group: 'beam' },
  { key: 'AEC_FIXEDBEAMNOISETHR', label: '噪声更新阈值', min: 0, max: 1, step: 0.05, type: 'float', wireType: 'float', resource: 33, command: 38, count: 2, group: 'beam' },
  // 输出（ASR 链路与编解码器音量）
  { key: 'AEC_ASROUTGAIN', label: 'ASR 输出增益（倍）', min: 0, max: 1000, step: 1, type: 'float', wireType: 'float', resource: 33, command: 36, count: 1, group: 'output' },
  { key: 'AIC3104_HP_LEVEL', label: '耳机输出音量', min: 0, max: 9, step: 1, type: 'uint8', wireType: 'uint8', resource: 48, command: 11, count: 1, group: 'output' },
  { key: 'AIC3104_LINEOUT_LEVEL', label: '线路输出音量', min: 0, max: 9, step: 1, type: 'uint8', wireType: 'uint8', resource: 48, command: 12, count: 1, group: 'output' },
];
const INTERNAL = [
  { key: 'VERSION', label: 'Firmware version', type: 'enum', wireType: 'uint8', options: [], resource: 48, command: 0, count: 3, group: 'device', readOnly: true },
  { key: 'DOA_VALUE', label: 'Direction of arrival', type: 'enum', wireType: 'uint16', options: [], resource: 20, command: 18, count: 2, group: 'doa', readOnly: true },
  { key: 'SAVE_CONFIGURATION', label: 'Save configuration', min: 1, max: 1, step: 1, type: 'bool', wireType: 'uint8', resource: 48, command: 9, count: 1, group: 'device', writeOnly: true },
  { key: 'REBOOT', label: 'Reboot device', type: 'bool', wireType: 'uint8', resource: 48, command: 7, count: 1, group: 'device', writeOnly: true },
];
export const PARAMETERS = Object.freeze(CONTROLS.map((p) => Object.freeze({ ...p })));
// Source: XMOS XVF3800 User Guide v3.2.1, Table 26 — AUDIO_MGR_OP_L / AUDIO_MGR_OP_R mux options,
// as (category, source). Categories 1/3/11 are microphone taps ahead of SHF processing; 6/9 are
// processed outputs; 7 is the AEC residual (or ASR data when ASR output is enabled); 8 is the
// firmware's own channel pick, which currently copies the auto-select beam; 4/5/12 are far-end
// reference taps. Category 10 (I2S far end) is omitted: it is not reachable over USB audio.
const mk = (category, source, label, group, n) => ({ value: `${category}:${source}`, label, group, route: [category, source], ...(n === undefined ? {} : { n }) });
export const PRE_PROCESSING_CATEGORIES = Object.freeze([1, 3, 11]);
export const OUTPUT_SIGNALS = Object.freeze([
  ...[0, 1, 2, 3].map((i) => mk(3, i, '麦克风 {n} · 已加增益（送入处理核）', '处理前', i + 1)),
  ...[0, 1, 2, 3].map((i) => mk(1, i, '麦克风 {n} · 原始（无增益、无系统延时）', '处理前', i + 1)),
  ...[0, 1, 2, 3].map((i) => mk(11, i, '麦克风 {n} · 已加增益、无系统延时', '处理前', i + 1)),
  mk(6, 0, '慢速波束 1', '处理后'), mk(6, 1, '慢速波束 2', '处理后'), mk(6, 2, '快速波束', '处理后'), mk(6, 3, '自动波束', '处理后'),
  ...[0, 1, 2, 3].map((i) => mk(9, i, '用户后处理通道 {n}', '处理后', i + 1)),
  ...[0, 1, 2, 3].map((i) => mk(7, i, '波束 {n}', 'AEC 残差 / ASR', i + 1)),
  ...[0, 1].map((i) => mk(8, i, '固件自选通道 {n}（当前为自动波束副本）', '固件自选', i + 1)),
  mk(4, 0, '远端参考 · 重采样到 16 kHz', '参考信号'), mk(5, 0, '远端参考 · 含系统延时', '参考信号'), mk(12, 0, '远端参考 · 加增益、含系统延时', '参考信号'),
  mk(0, 0, '静音', '其他'),
].map((signal) => Object.freeze({ ...signal, route: Object.freeze(signal.route) })));
// One demo configuration, expressed per control protocol so the same story works on every model.
// Intent, not tuning advice: make the difference between "before" and "after" readable on screen.
//  - AGC off: it raises the floor back up and hides whatever the suppressor removed.
//  - MIN_NS / MIN_NN at 0.02: near the floor of the documented [0..1] range, i.e. strongest suppression.
//  - High-pass at 125 Hz (value 2 in both the XVF3800 and the legacy enum).
// Which signal each side carries is NOT part of this preset: routing is settled once on connect and
// owned by the device-output panel. This preset only touches the processing parameters.
// Levels are picked for visible contrast on the charts, not validated for listening quality.
export const DEMO_PRESETS = Object.freeze({
  'xvf3800-servicer': Object.freeze({
    label: 'XVF3800 / Flex',
    values: Object.freeze({ SHF_BYPASS: 0, PP_AGCONOFF: false, PP_MIN_NS: 0.02, PP_MIN_NN: 0.02, PP_ATTNS_MODE: true, PP_ECHOONOFF: true, AEC_HPFONOFF: 2 }),
  }),
  'xvf3000-legacy': Object.freeze({
    label: 'XVF3000',
    values: Object.freeze({ AGCONOFF: false, STATNOISEONOFF: true, NONSTATNOISEONOFF: true, MIN_NS: 0.02, MIN_NN: 0.02, ECHOONOFF: true, HPFONOFF: 2 }),
  }),
});
// ReSpeaker Mic Array v2.0 (XVF3000) 6-channel firmware: ch0 processed-for-ASR, ch1-4 raw mics,
// ch5 merged playback. Source: Seeed Studio wiki, ReSpeaker_Mic_Array_v2.0 firmware comparison table.
// Chrome does not hand over all six: measured on macOS, the track's getCapabilities().channelCount is
// {min:1, max:2} for 2886:0018 and {exact:6} is OverconstrainedError. The first two channels do line up
// with ch0/ch1 — measured on device: ch1 span 7.4 dB, ch0 span 13.7 dB, so ch0 is the processed one.
// The pair therefore stays usable at minChannels 2.
export const DEFAULT_CHANNEL_MAPS = Object.freeze({
  'xvf3000-legacy': Object.freeze({ original: 1, processed: 0, minChannels: 2 }),
});
const DIAGNOSTICS = [
  { key: 'AUDIO_MGR_OP_L', label: 'Left output routing', type: 'uint8', wireType: 'uint8', resource: 35, command: 15, count: 2, group: 'device', readOnly: true },
  { key: 'AUDIO_MGR_OP_R', label: 'Right output routing', type: 'uint8', wireType: 'uint8', resource: 35, command: 19, count: 2, group: 'device', readOnly: true },
  { key: 'AEC_AECCONVERGED', label: 'AEC converged', type: 'bool', wireType: 'int32', min: 0, max: 1, resource: 33, command: 3, count: 1, group: 'echo', readOnly: true },
  { key: 'AEC_ASROUTONOFF', label: 'ASR output enabled', type: 'bool', wireType: 'int32', min: 0, max: 1, resource: 33, command: 35, count: 1, group: 'device', readOnly: true },
  { key: 'PP_AGCGAIN', label: 'Current AGC gain', type: 'float', wireType: 'float', min: 1, max: 1000, resource: 17, command: 13, count: 1, group: 'gain', readOnly: true },
  { key: 'AEC_AECPATHCHANGE', label: 'AEC path change', type: 'bool', wireType: 'int32', resource: 33, command: 0, count: 1, group: 'echo', readOnly: true },
  { key: 'AEC_RT60', label: 'RT60 estimate', type: 'float', wireType: 'float', resource: 33, command: 9, count: 1, group: 'echo', readOnly: true },
  { key: 'AEC_SPENERGY_VALUES', label: 'Beam speech energy', type: 'float', wireType: 'float', resource: 33, command: 80, count: 4, group: 'doa', readOnly: true },
];
export const LEGACY_PARAMETERS = Object.freeze([
  { key: 'MIN_NS', primary: true, plain: '环境噪声抑制', effect: '调小：停顿时的底噪更低，能量图的谷更深；调得太小人声会发闷。', label: '噪声抑制下限', min: 0, max: 1, step: 0.01, type: 'float', resource: 19, offset: 10, group: 'noise' },
  { key: 'MIN_NN', label: '非稳态噪声下限', min: 0, max: 1, step: 0.01, type: 'float', resource: 19, offset: 13, group: 'noise' },
  { key: 'ECHOONOFF', primary: true, plain: '回声抑制', effect: '边放测试音频边说话时打开：对比通道里的喇叭声会被压下去。', label: '回声抑制', min: 0, max: 1, step: 1, type: 'bool', resource: 19, offset: 14, group: 'echo' },
  { key: 'AGCONOFF', primary: true, plain: '自动增益', effect: '打开后远处说话会被自动拉高，安静时底噪也一起被放大——降噪效果会被它抬回来。对比前后时先关掉。', label: '自动增益控制', min: 0, max: 1, step: 1, type: 'bool', resource: 19, offset: 0, group: 'gain' },
  { key: 'HPFONOFF', label: '高通滤波器', min: 0, max: 3, step: 1, type: 'enum', options: [{ value: 0, label: '关闭' }, { value: 1, label: '70 Hz' }, { value: 2, label: '125 Hz' }, { value: 3, label: '180 Hz' }], resource: 18, offset: 27, group: 'gain' },
  { key: 'STATNOISEONOFF', label: '稳态噪声抑制', min: 0, max: 1, step: 1, type: 'bool', resource: 19, offset: 8, group: 'noise' },
  { key: 'NONSTATNOISEONOFF', label: '非稳态噪声抑制', min: 0, max: 1, step: 1, type: 'bool', resource: 19, offset: 11, group: 'noise' },
]);
const LEGACY_VERSION = { key: 'VERSION', label: 'Firmware version', type: 'uint8', count: 1, group: 'device', readOnly: true };
const LEGACY_DOA = { key: 'DOA_VALUE', label: 'Direction of arrival', type: 'int32', resource: 21, offset: 0, group: 'doa', readOnly: true };
const LEGACY_SPEECH = { key: 'SPEECH_ACTIVITY', label: 'Voice activity', type: 'int32', resource: 19, offset: 32, group: 'doa', readOnly: true };
const byKey = new Map([...CONTROLS, ...INTERNAL, ...DIAGNOSTICS].map((p) => [p.key, p]));
const legacyByKey = new Map([LEGACY_VERSION, ...LEGACY_PARAMETERS, LEGACY_DOA, LEGACY_SPEECH].map((p) => [p.key, p]));

const DEVICE_TABLE = Object.freeze({
  // Flex's normal USB product is 001e; 001a is the XVF3800 USB 4-Mic array.
  '2886:001e': { id: 'respeaker_flex', name: 'reSpeaker Flex (XVF3800)', physicalMics: 4, controlProtocol: 'xvf3800-servicer', notes: 'USB control is supported for the XVF3800 USB firmware.' },
  '2886:001a': { id: 'respeaker_xvf3800', name: 'reSpeaker XVF3800 4-Mic Array', physicalMics: 4, controlProtocol: 'xvf3800-servicer', notes: 'USB control is supported when the XVF3800 USB firmware exposes the servicer.' },
  '2886:0024': { id: 'respeaker_xvf3800_44mm', name: 'reSpeaker XVF3800 4-Mic 44mm', physicalMics: 4, controlProtocol: 'xvf3800-servicer', notes: 'USB control is supported for the XVF3800 USB firmware.' },
  '2886:0018': { id: 'respeaker_xvf3000', name: 'reSpeaker XVF3000', physicalMics: 4, controlProtocol: 'xvf3000-legacy', notes: 'Legacy XVF3000 USB control protocol.' },
  '2886:0019': { id: 'respeaker_lite', name: 'reSpeaker Lite', physicalMics: 2, controlProtocol: 'audio-only', notes: 'Lite 官方调参路径为 I2C（仅 I2S 固件）；本页不提供 USB 调参。采音需要 USB 固件并在系统中出现音频输入。' },
});

function keyOf(vendorId, productId) { return `${Number(vendorId).toString(16).padStart(4, '0')}:${Number(productId).toString(16).padStart(4, '0')}`; }

export function identifyDevice({ vendorId, productId, productName = '' } = {}) {
  const known = DEVICE_TABLE[keyOf(vendorId, productId)];
  if (known) return { ...known, vendorId: Number(vendorId), productId: Number(productId) };
  return {
    id: 'unknown_respeaker', name: productName || 'Unknown reSpeaker USB device', physicalMics: null,
    controlProtocol: 'audio-only', notes: 'Unknown family: USB control is disabled until a supported protocol is verified.',
    vendorId: Number(vendorId), productId: Number(productId), unknown: true,
  };
}

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function bytes(value) {
  if (value instanceof Uint8Array) return value;
  if (value instanceof DataView) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  if (value?.buffer instanceof ArrayBuffer) return new Uint8Array(value.buffer, value.byteOffset || 0, value.byteLength);
  return new Uint8Array(value || 0);
}
async function withTimeout(promise, ms) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('USB control timeout')), ms); })]); }
  finally { clearTimeout(timer); }
}
function decode(def, body) {
  const wireType = def.wireType || def.type;
  const b = bytes(body).slice(1);
  const view = new DataView(b.buffer, b.byteOffset, b.byteLength);
  const out = [];
  for (let i = 0; i < def.count; i += 1) {
    const offset = wireType === 'uint8' ? i : i * (wireType === 'uint16' ? 2 : 4);
    if (wireType === 'uint8') out.push(b[offset]);
    else if (wireType === 'uint16') out.push(view.getUint16(offset, true));
    else if (wireType === 'float') out.push(view.getFloat32(offset, true));
    else out.push(view.getInt32(offset, true));
  }
  if (out.some(v => !Number.isFinite(v))) throw new Error('Invalid control value');
  if (def.key === 'DOA_VALUE' && (out[0] > 359 || out[1] > 1)) throw new Error('Invalid DOA value');
  if (def.min !== undefined && (out[0] < def.min || out[0] > def.max)) throw new Error('Control value outside range');
  if (def.type === 'bool') return Boolean(out[0]);
  return def.count === 1 ? out[0] : out;
}
function decodeLegacy(def, body) {
  const b = bytes(body);
  if (b.byteLength < 8) throw new Error(`Truncated legacy control reply (${b.byteLength}/8)`);
  const view = new DataView(b.buffer, b.byteOffset, b.byteLength);
  if (def.type === 'float') {
    const mantissa = view.getInt32(0, true); const exponent = view.getInt32(4, true);
    const value = mantissa * (2 ** exponent);
    if (!Number.isFinite(value) || (def.min !== undefined && (value < def.min || value > def.max))) throw new Error('Invalid legacy float');
    return value;
  }
  const value = view.getInt32(0, true);
  if (def.type === 'bool') { if (value !== 0 && value !== 1) throw new Error('Invalid legacy boolean'); return Boolean(value); }
  if (def.key === 'DOA_VALUE' && (value < 0 || value > 359)) throw new Error('Invalid legacy DOA');
  if (def.key === 'SPEECH_ACTIVITY' && value !== 0 && value !== 1) throw new Error('Invalid legacy voice activity');
  if (def.min !== undefined && (value < def.min || value > def.max)) throw new Error('Legacy control value outside range');
  return value;
}
function encodeLegacy(def, value) {
  const out = new ArrayBuffer(12); const view = new DataView(out);
  view.setInt32(0, def.offset, true);
  if (def.type === 'float') view.setFloat32(4, Number(value), true);
  else view.setInt32(4, def.type === 'bool' ? Number(Boolean(value)) : Number(value), true);
  view.setInt32(8, def.type === 'float' ? 0 : 1, true);
  return new Uint8Array(out);
}
function encode(def, value) {
  const wireType = def.wireType || def.type;
  const vals = Array.isArray(value) ? value : [value];
  const size = wireType === 'float' || wireType === 'int32' || wireType === 'bool' ? 4 : wireType === 'uint16' ? 2 : 1;
  const out = new ArrayBuffer(size * def.count);
  const view = new DataView(out);
  vals.forEach((v, i) => {
    const o = i * size;
    if (wireType === 'float') view.setFloat32(o, Number(v), true);
    else if (wireType === 'int32') view.setInt32(o, Number(v), true);
    else if (wireType === 'bool') view.setInt32(o, Number(Boolean(v)), true);
    else if (wireType === 'uint16') view.setUint16(o, Number(v), true);
    else view.setUint8(o, Number(v));
  });
  return new Uint8Array(out);
}
function same(a, b) {
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => same(v, b[i]));
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= 1e-4;
  return JSON.stringify(a) === JSON.stringify(b);
}

export class ReSpeakerUSB extends EventTarget {
  static supported(device) {
    if (!device) return Object.freeze(Object.values(DEVICE_TABLE).map((x) => ({ ...x })));
    return Number(device.vendorId) === VID && ['001e', '001a', '0019', '0018', '0024'].includes(Number(device.productId).toString(16).padStart(4, '0'));
  }

  constructor(device = null) {
    super(); this.device = device; this.identity = device ? identifyDevice(device) : null;
    this.opened = false; this.capabilities = new Map(); this._queue = Promise.resolve(); this._onDisconnect = null; this._epoch = 0; this.firmwareValid = false;
  }
  _serial(fn) { const next = this._queue.then(fn, fn); this._queue = next.catch(() => {}); return next; }
  _canControl(def, write = false) {
    if (this.identity?.controlProtocol === 'xvf3000-legacy') {
      return def.key === 'VERSION' || (this.firmwareValid && (!write || !def.readOnly));
    }
    if (this.identity?.controlProtocol === 'xvf3800-servicer') return (def.key === 'VERSION' || this.firmwareValid) && (!write || !def.readOnly);
    if (this.identity?.unknown && def.key === 'VERSION' && !write) return true;
    return Boolean(this.identity?.unknown && this.firmwareValid && !write ? !def.writeOnly : this.identity?.unknown && this.firmwareValid && write && !def.readOnly);
  }
  async connect({ onProgress } = {}) {
    if (!this.device) {
      if (!globalThis.navigator?.usb) throw new Error('WebUSB is unavailable');
      // Reuse a device this origin was already granted, so a reload does not reopen the native chooser.
      const remembered = (await navigator.usb.getDevices().catch(() => [])).filter((d) => ReSpeakerUSB.supported(d));
      this.device = remembered.length === 1 ? remembered[0] : await navigator.usb.requestDevice({ filters: [{ vendorId: VID }] });
    }
    this.identity = identifyDevice(this.device);
    try { if (!this.device.opened) await this.device.open(); this.opened = true; }
    catch (error) { try { if (this.device.opened) await this.device.close(); } catch {} this.opened = false; throw error; }
    if (globalThis.navigator?.usb?.addEventListener && !this._onDisconnect) {
      this._onDisconnect = (event) => { if (event.device === this.device) { this._epoch += 1; this.opened = false; this.firmwareValid = false; this.capabilities.clear(); globalThis.navigator?.usb?.removeEventListener?.('disconnect', this._onDisconnect); this._onDisconnect = null; this.dispatchEvent(new Event('disconnect')); } };
      globalThis.navigator?.usb?.addEventListener?.('disconnect', this._onDisconnect);
    }
    const snap = await this.snapshot(onProgress); this.dispatchEvent(new CustomEvent('connect', { detail: snap })); return snap;
  }
  async disconnect() {
    this._epoch += 1;
    if (!this.device) return;
    this.opened = false;
    try { if (this.device.opened) await this.device.close(); }
    finally { if (this._onDisconnect) globalThis.navigator?.usb?.removeEventListener?.('disconnect', this._onDisconnect); this._onDisconnect = null; this.dispatchEvent(new Event('disconnect')); }
  }
  async _transfer(def, write, value) {
    if (!this.opened || !this.device) throw new Error('Device is not connected');
    if (!this._canControl(def, write)) throw new Error(`${def.key} is unavailable for this device`);
    const started = Date.now(); let attempt = 0; const epoch = this._epoch;
    if (this.identity?.controlProtocol === 'xvf3000-legacy') {
      const setup = { requestType: 'vendor', recipient: 'device', request: 0, value: write ? 0 : (0x80 | def.offset | (def.type === 'float' ? 0 : 0x40)), index: def.resource };
      const result = write
        ? await withTimeout(this.device.controlTransferOut(setup, encodeLegacy(def, value)), CONTROL_DEADLINE_MS)
        : await withTimeout(this.device.controlTransferIn(setup, 8), CONTROL_DEADLINE_MS);
      if (epoch !== this._epoch || !this.opened) throw new Error('Device disconnected');
      if (write) { if (result?.status && result.status !== 'ok') throw new Error(`USB write failed: ${result.status}`); return; }
      if (!result || (result.status && result.status !== 'ok')) throw new Error(`USB read failed: ${result?.status || 'unknown'}`);
      return decodeLegacy(def, result.data);
    }
    while (attempt <= MAX_RETRIES && Date.now() - started < CONTROL_DEADLINE_MS) {
      if (epoch !== this._epoch || !this.opened) throw new Error('Device disconnected');
      const setup = { requestType: 'vendor', recipient: 'device', request: 0, value: write ? def.command : (0x80 | def.command), index: def.resource };
      const result = write
        ? await withTimeout(this.device.controlTransferOut(setup, encode(def, value)), CONTROL_DEADLINE_MS)
        : await withTimeout(this.device.controlTransferIn(setup, 1 + ((def.wireType || def.type) === 'uint8' ? def.count : (def.wireType || def.type) === 'uint16' ? def.count * 2 : def.count * 4)), CONTROL_DEADLINE_MS);
      if (epoch !== this._epoch) throw new Error('Device disconnected');
      if (write) { if (result.status && result.status !== 'ok') throw new Error(`USB write failed: ${result.status}`); return; }
      if (!result || (result.status && result.status !== 'ok')) throw new Error(`USB read failed: ${result?.status || 'unknown'}`);
      const data = bytes(result.data); const expected = 1 + ((def.wireType || def.type) === 'uint8' ? def.count : (def.wireType || def.type) === 'uint16' ? def.count * 2 : def.count * 4);
      if (!data.byteLength || (data[0] === STATUS_OK && data.byteLength < expected)) throw new Error(`Truncated control reply (${data.byteLength}/${expected})`);
      if (data[0] === STATUS_OK) return decode(def, data);
      if (data[0] !== STATUS_RETRY) throw new Error(`Control status ${data[0]}`);
      attempt += 1; await sleep(RETRY_DELAY_MS);
    }
    throw new Error('Control request retry timeout');
  }
  async read(key) {
    const legacy = this.identity?.controlProtocol === 'xvf3000-legacy';
    const def = (legacy ? legacyByKey : byKey).get(key);
    if (!def || def.writeOnly) throw new Error(`Unknown/read unavailable parameter: ${key}`);
    if (legacy && key === 'VERSION') {
      const epoch = this._epoch;
      return this._serial(async () => { if (epoch !== this._epoch || !this.opened) throw new Error('Device disconnected'); const result = await withTimeout(this.device.controlTransferIn({ requestType: 'vendor', recipient: 'device', request: 0, value: 0x80, index: 0 }, 1), CONTROL_DEADLINE_MS); if (epoch !== this._epoch || !this.opened) throw new Error('Device disconnected'); if (!result || (result.status && result.status !== 'ok')) throw new Error(`USB read failed: ${result?.status || 'unknown'}`); const data = bytes(result.data); if (data.byteLength < 1) throw new Error('Missing legacy firmware version'); return data[0]; });
    }
    return this._serial(() => this._transfer(def, false));
  }
  async write(key, value) {
    const legacy = this.identity?.controlProtocol === 'xvf3000-legacy';
    const def = (legacy ? legacyByKey : byKey).get(key); if (!def || def.readOnly) throw new Error(`Unknown/read-only parameter: ${key}`);
    if (legacy && def.type === 'enum' && !def.options.some(o => o.value === value)) throw new RangeError('Invalid enum value');
    if (!this._canControl(def, true) || !this.firmwareValid || (key !== 'SAVE_CONFIGURATION' && key !== 'REBOOT' && !this.capabilities.get(key))) throw new Error(`${key} unavailable: capability probe required`);
    if (def.type === 'bool' && ![true, false, 0, 1].includes(value)) throw new RangeError('Expected boolean');
    if (def.type === 'bool') value = Boolean(value);
    if (def.type === 'enum' && !def.options.some(o => o.value === value)) throw new RangeError('Invalid enum value');
    if (Array.isArray(value)) {
      if (value.length !== def.count) throw new RangeError(`${key} expects ${def.count} values`);
      if (value.some(v => { const n = Number(v); return !Number.isFinite(n) || n < def.min || n > def.max; })) throw new RangeError(`${key} values must be between ${def.min} and ${def.max}`);
    } else {
      const n = Number(value); if (def.type !== 'bool' && (!Number.isFinite(n) || n < def.min || n > def.max)) throw new RangeError(`${key} must be between ${def.min} and ${def.max}`);
    }
    const epoch = this._epoch;
    return this._serial(async () => { if(epoch !== this._epoch) throw new Error('Device disconnected'); await this._transfer(def, true, value); if (def.writeOnly) return value; const actual = await this._transfer(def, false); if (!same(actual, def.type === 'bool' ? Boolean(value) : value)) throw new Error(`${key} write validation failed`); return actual; });
  }
  async save() { if (this.identity?.controlProtocol === 'xvf3000-legacy') throw new Error('XVF3000 firmware does not expose USB flash save'); if (!this.firmwareValid || !CONTROLS.some(p => this.capabilities.get(p.key))) throw new Error('Firmware capability probe required before save'); return this.write('SAVE_CONFIGURATION', 1); }
  async reboot() { if (this.identity?.controlProtocol !== 'xvf3800-servicer') throw new Error('Reboot requires a probed XVF3800 device'); if (!this.firmwareValid || !CONTROLS.some(p => this.capabilities.get(p.key))) throw new Error('Firmware capability probe required before reboot'); const epoch = this._epoch; return this._serial(async () => { if (epoch !== this._epoch || !this.opened) throw new Error('Device disconnected'); await this._transfer(byKey.get('REBOOT'), true, 1); }); }
  async setComparisonRouting() {
    // Left is category 3 (microphone 1 after the gain stage), right is the auto-select beam after
    // processing.
    //
    // This used to be category 1 (raw microphone, no gain, no system delay), on the argument that
    // category 3 sits after the gain stage and so turning AGC off — which the demo preset does —
    // drops the "before" reference along with the "after" one and collapses the comparison. That
    // argument is UNVERIFIED: PP_AGCONOFF is a post-processing control and the category 3 tap may
    // sit ahead of it in the signal chain. Confirming it needs the XVF3800 signal-chain diagram or
    // a measurement on hardware; neither has been done.
    //
    // Category 1 was changed away from because it fails three ways on first use, measured on an
    // XVF3800: the tap reads about -87 dBFS while the processed side reads -48, so (a) the waveform
    // renders as a flat line at every zoom step the UI offers, (b) playback is inaudible, and
    // (c) wavBlob writes 16-bit PCM, where -87 dBFS is ~1.4 LSB, so the recording is destroyed by
    // quantisation rather than merely quiet. A first-run failure was judged worse than a possible
    // quality loss in the demo-preset comparison.
    //
    // If the comparison does turn out to collapse with AGC off, the fix is not to revert but to
    // couple routing to the preset: keep category 3 on connect, switch the left side to [1, 0] when
    // the demo preset is applied. Reverting outright brings back all three first-run failures.
    // Users can still select any tap by hand in the device-output panel.
    return this.setOutputRouting({ left: [3, 0], right: [6, 3] });
  }
  async setOutputRouting(routing) {
    for (const side of ['left', 'right']) {
      const pair = routing?.[side];
      if (!Array.isArray(pair) || pair.length !== 2 || !OUTPUT_SIGNALS.some(signal => signal.route[0] === pair[0] && signal.route[1] === pair[1])) throw new RangeError('Unsupported output signal');
    }
    return this._changeRouting(routing, routing.left[0] === 7 || routing.right[0] === 7);
  }
  async restoreRouting(savedRouting) {
    return this._changeRouting(savedRouting, false);
  }
  async _changeRouting(routing, requireAsr) {
    const target = {};
    for (const side of ['left', 'right']) {
      const pair = routing?.[side];
      if (!Array.isArray(pair) || pair.length !== 2 || !pair.every(v => Number.isInteger(v) && v >= 0 && v <= 255)) throw new RangeError('Routing must contain two uint8 values per side');
      target[side] = [...pair];
    }
    const epoch = this._epoch;
    const check = () => {
      if (epoch !== this._epoch || !this.opened) throw new Error('Device disconnected');
      if (this.identity?.controlProtocol !== 'xvf3800-servicer' || !this.firmwareValid) throw new Error('Routing requires a probed XVF3800 device');
    };
    check();
    return this._serial(async () => {
      check();
      if (requireAsr) {
        const asr = await this._transfer(byKey.get('AEC_ASROUTONOFF'), false);
        if (!asr) throw new Error('Comparison routing requires AEC_ASROUTONOFF=1');
      }
      const definitions = { left: byKey.get('AUDIO_MGR_OP_L'), right: byKey.get('AUDIO_MGR_OP_R') };
      const previous = {};
      for (const side of ['left', 'right']) { check(); previous[side] = await this._transfer(definitions[side], false); }
      const writeSide = async (side, values) => {
        check();
        // Only this routing transaction makes the diagnostic definition writable.
        await this._transfer({ ...definitions[side], readOnly: false }, true, values);
        check();
        const actual = await this._transfer(definitions[side], false);
        if (!same(actual, values)) throw new Error(`${side} routing readback mismatch`);
      };
      try {
        for (const side of ['left', 'right']) await writeSide(side, target[side]);
      } catch (cause) {
        const rollbackErrors = [];
        for (const side of ['left', 'right']) {
          try { await writeSide(side, previous[side]); }
          catch (error) { rollbackErrors.push(`${side}: ${error.message}`); }
        }
        const rollbackSucceeded = rollbackErrors.length === 0;
        const error = new Error(`Routing failed: ${cause.message}; rollback ${rollbackSucceeded ? 'succeeded' : `failed (${rollbackErrors.join('; ')})`}`);
        Object.assign(error, { cause, rollbackSucceeded, rollbackErrors, previousRouting: previous });
        throw error;
      }
      return previous;
    });
  }
  async snapshot(onProgress) {
    this.firmwareValid = false; this.capabilities.clear();
    const legacy = this.identity?.controlProtocol === 'xvf3000-legacy';
    const parameters = {}; const defs = legacy ? [LEGACY_VERSION, ...LEGACY_PARAMETERS, LEGACY_DOA, LEGACY_SPEECH] : [...INTERNAL.filter((p) => p.key === 'VERSION'), ...CONTROLS, ...INTERNAL.filter((p) => p.key === 'DOA_VALUE'), ...DIAGNOSTICS];
    let done = 0;
    for (const def of defs) {
      onProgress?.(done, defs.length); done += 1;
      if (!this._canControl(def)) { parameters[def.key] = { value: null, supported: false, error: this.identity?.controlProtocol==='audio-only'?'此设备可用于 USB 音频；本页不提供该设备 USB 调参':'固件探测未成功，控制项暂不可用' }; continue; }
      try { const value = await this.read(def.key); if (def.key === 'VERSION') this.firmwareValid = legacy ? Number.isInteger(value) : Array.isArray(value) && value.length === 3 && value.every((v) => Number.isInteger(v) && v >= 0 && v <= 255); this.capabilities.set(def.key, this.firmwareValid || def.key !== 'VERSION'); parameters[def.key] = { value, supported: this.firmwareValid || def.key !== 'VERSION' }; }
      catch (error) { this.capabilities.set(def.key, false); parameters[def.key] = { value: null, supported: false, error: error.message }; }
    }
    const version = parameters.VERSION?.value; const firmware = Array.isArray(version) ? version.join('.') : (Number.isInteger(version) ? String(version) : null);
    const parameterDefinitions = legacy ? LEGACY_PARAMETERS : PARAMETERS;
    return { identity: this.identity, firmware, parameters, parameterDefinitions, canSave: !legacy, doaSupported: parameters.DOA_VALUE?.supported === true, usb: this._usbDescriptorSnapshot() };
  }
  _usbDescriptorSnapshot() { const d = this.device; return d ? { configurations: d.configurations?.map((c) => ({ configurationValue: c.configurationValue, interfaces: c.interfaces?.map((i) => ({ interfaceNumber: i.interfaceNumber, alternates: i.alternates?.map((a) => ({ alternateSetting: a.alternateSetting, interfaceClass: a.interfaceClass, interfaceSubclass: a.interfaceSubclass, interfaceProtocol: a.interfaceProtocol })) })) })) || [] } : { configurations: [] }; }
  async pollDoa() { if (!['xvf3800-servicer', 'xvf3000-legacy'].includes(this.identity?.controlProtocol)) return null; try { const v = await this.read('DOA_VALUE'); const speech = this.identity?.controlProtocol === 'xvf3000-legacy' ? await this.read('SPEECH_ACTIVITY') : (Array.isArray(v) ? v[1] : 0); const angle = Array.isArray(v) ? v[0] : v; return { angle, speech: Boolean(speech) }; } catch { return null; } }
}
