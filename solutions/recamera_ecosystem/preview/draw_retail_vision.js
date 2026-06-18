/**
 * Retail Vision Overlay Renderer
 *
 * Renders people flow heatmap + bounding boxes for retail-vision solution.
 * Depends on: simpleheat (https://github.com/mourner/simpleheat)
 *
 * Input (data): retail-vision MQTT message
 * {
 *   timestamp: 1768969602957,
 *   frame_id: 107,
 *   fps: 12.5,
 *   inference_time_ms: 85.0,
 *   frame_width: 1280,
 *   frame_height: 720,
 *   zone: {
 *     occupancy_count: 2,
 *     browsing_count: 1,
 *     engaged_count: 1,
 *     assist_count: 0,
 *     peak_customer: 3,
 *     avg_dwell_time: 4.2,
 *     avg_engagement_time: 2.1,
 *     avg_velocity: 0.8,
 *     entry_count: 5,
 *     exit_count: 3
 *   },
 *   persons: [{
 *     track_id: 1,
 *     confidence: 0.87,
 *     bbox: { x: 0.3, y: 0.15, w: 0.2, h: 0.4 },  // normalized top-left + w/h
 *     velocity: { vx: 0.01, vy: 0.0, speed_m_s: 0.3 },
 *     state: "engaged",   // transient | dwelling | engaged | assistance
 *     dwell_duration: 8.9
 *   }]
 * }
 *
 * Variables: ctx, data, canvas, img (provided by PreviewWindow)
 */

// ========== Polyfill ==========
if (typeof ctx.roundRect !== 'function') {
  ctx.roundRect = function(x, y, w, h, r) {
    r = typeof r === 'number' ? r : (Array.isArray(r) ? r[0] : 0);
    this.moveTo(x + r, y);
    this.arcTo(x + w, y, x + w, y + h, r);
    this.arcTo(x + w, y + h, x, y + h, r);
    this.arcTo(x, y + h, x, y, r);
    this.arcTo(x, y, x + w, y, r);
    this.closePath();
  };
}

// ========== Configuration ==========
const CONFIG = {
  pointRadius: 35,
  blurRadius: 25,
  maxHeatValue: 100,
  decayRate: 0.985,

  stateWeights: {
    transient: 0.5,
    dwelling: 1.5,
    browsing: 1.5,
    engaged: 3.0,
    assistance: 5.0,
  },

  gradient: {
    0.0: 'rgba(0, 0, 255, 0)',
    0.2: 'blue',
    0.4: 'cyan',
    0.6: 'lime',
    0.8: 'yellow',
    1.0: 'red'
  },

  stateColors: {
    transient:  '#9CA3AF',
    dwelling:   '#3B82F6',
    browsing:   '#3B82F6',
    engaged:    '#F59E0B',
    assistance: '#EF4444',
  },

  boxLineWidth: 4,
  boxGlowBlur: 8,
  labelFont: 'bold 12px Inter, sans-serif',
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// ========== Persistent State ==========
if (!window._retailVisionState) {
  window._retailVisionState = {
    heat: null,
    points: new Map(),
    initialized: false,
    lastCanvasSize: { w: 0, h: 0 },
    bufferCanvas: null,
  };
}
const state = window._retailVisionState;

// Create / resize buffer canvas
if (!state.bufferCanvas ||
    state.bufferCanvas.width !== canvas.width ||
    state.bufferCanvas.height !== canvas.height) {
  state.bufferCanvas = document.createElement('canvas');
  state.bufferCanvas.width = canvas.width;
  state.bufferCanvas.height = canvas.height;
  state.initialized = false;
}
const bufferCtx = state.bufferCanvas.getContext('2d');

// Init simpleheat
if (!state.initialized || state.lastCanvasSize.w !== canvas.width || state.lastCanvasSize.h !== canvas.height) {
  if (typeof simpleheat === 'undefined') {
    console.warn('simpleheat library not loaded');
  } else {
    state.heat = simpleheat(state.bufferCanvas);
    state.heat.radius(CONFIG.pointRadius, CONFIG.blurRadius);
    state.heat.gradient(CONFIG.gradient);
    state.heat.max(CONFIG.maxHeatValue);
  }
  state.initialized = true;
  state.lastCanvasSize = { w: canvas.width, h: canvas.height };
}

// ========== Parse Data ==========
if (!data || !data.persons) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  return;
}

const persons       = data.persons || [];
const zone          = data.zone || {};
const inferenceTime = data.inference_time_ms || 0;

// Map retail-vision zone fields → display labels
const zoneDisplay = {
  total:      zone.occupancy_count  || 0,
  browsing:   zone.browsing_count   || 0,
  engaged:    zone.engaged_count    || 0,
  assistance: zone.assist_count     || 0,
  peak:       zone.peak_customer    || 0,
  entry:      zone.entry_count      || 0,
  exit:       zone.exit_count       || 0,
};

// ========== Decay Old Heatmap Points ==========
for (const [id, point] of state.points.entries()) {
  point.heat *= CONFIG.decayRate;
  if (point.heat < 0.5) state.points.delete(id);
}

// ========== Update Heatmap Points ==========
for (const person of persons) {
  const { bbox, track_id, state: personState } = person;
  if (!bbox) continue;

  // Support both object {x,y,w,h} and array [x,y,w,h]
  let bboxX, bboxY, bboxW, bboxH;
  if (Array.isArray(bbox)) {
    [bboxX, bboxY, bboxW, bboxH] = bbox;
  } else {
    ({ x: bboxX, y: bboxY, w: bboxW, h: bboxH } = bbox);
  }

  const centerX = (bboxX + bboxW / 2) * canvas.width;
  const centerY = (bboxY + bboxH / 2) * canvas.height;
  const weight  = CONFIG.stateWeights[personState] || 1.0;

  if (state.points.has(track_id)) {
    const p = state.points.get(track_id);
    p.x    = p.x * 0.7 + centerX * 0.3;
    p.y    = p.y * 0.7 + centerY * 0.3;
    p.heat = Math.min(p.heat + weight * 2, CONFIG.maxHeatValue);
  } else {
    state.points.set(track_id, { x: centerX, y: centerY, heat: weight * 10 });
  }
}

// ========== Draw Heatmap to Buffer ==========
bufferCtx.clearRect(0, 0, canvas.width, canvas.height);

if (state.heat && state.points.size > 0) {
  const heatData = Array.from(state.points.values()).map(p => [p.x, p.y, p.heat]);
  state.heat.data(heatData);
  state.heat.draw(0.15);
}

// ========== Draw Bounding Boxes to Buffer ==========
bufferCtx.font = CONFIG.labelFont;

for (const person of persons) {
  const { bbox, track_id, state: personState, dwell_duration = 0, confidence = 0 } = person;
  if (!bbox) continue;

  let bboxX, bboxY, bboxW, bboxH;
  if (Array.isArray(bbox)) {
    [bboxX, bboxY, bboxW, bboxH] = bbox;
  } else {
    ({ x: bboxX, y: bboxY, w: bboxW, h: bboxH } = bbox);
  }

  const bx = bboxX * canvas.width;
  const by = bboxY * canvas.height;
  const bw = bboxW * canvas.width;
  const bh = bboxH * canvas.height;

  const color = CONFIG.stateColors[personState] || CONFIG.stateColors.transient;

  // Glow
  bufferCtx.shadowColor = color;
  bufferCtx.shadowBlur  = CONFIG.boxGlowBlur;
  bufferCtx.strokeStyle = color;
  bufferCtx.lineWidth   = CONFIG.boxLineWidth;
  bufferCtx.strokeRect(bx, by, bw, bh);
  bufferCtx.shadowBlur  = 0;

  // Label
  const stateLabel   = (personState || 'transient').charAt(0).toUpperCase() + (personState || 'transient').slice(1);
  const dwellLabel   = dwell_duration > 0 ? ` ${dwell_duration.toFixed(1)}s` : '';
  const labelText    = `#${track_id} ${stateLabel}${dwellLabel}`;
  const textWidth    = bufferCtx.measureText(labelText).width;

  bufferCtx.fillStyle = color;
  bufferCtx.beginPath();
  bufferCtx.roundRect(bx, by - 22, textWidth + 10, 20, 3);
  bufferCtx.fill();

  bufferCtx.fillStyle = '#FFFFFF';
  bufferCtx.fillText(labelText, bx + 5, by - 7);
}

// ========== Stats Panel ==========
bufferCtx.globalAlpha = 1.0;

const panelW = 190, panelH = 170, panelX = 10, panelY = 10;
bufferCtx.fillStyle = 'rgba(0,0,0,0.85)';
bufferCtx.beginPath();
bufferCtx.roundRect(panelX, panelY, panelW, panelH, 8);
bufferCtx.fill();
bufferCtx.strokeStyle = 'rgba(255,255,255,0.3)';
bufferCtx.lineWidth = 1;
bufferCtx.stroke();

bufferCtx.fillStyle = '#FFFFFF';
bufferCtx.font = CONFIG.statsHeaderFont;
bufferCtx.fillText('Retail People Flow', panelX + 10, panelY + 22);

bufferCtx.font = CONFIG.statsFont;
let sy = panelY + 44;
const rows = [
  { label: `Total:`,    val: zoneDisplay.total,      color: '#FFFFFF' },
  { label: `Browsing:`, val: zoneDisplay.browsing,   color: CONFIG.stateColors.browsing },
  { label: `Engaged:`,  val: zoneDisplay.engaged,    color: CONFIG.stateColors.engaged },
  { label: `Need Help:`,val: zoneDisplay.assistance, color: CONFIG.stateColors.assistance },
  { label: `Entry:`,    val: zoneDisplay.entry,      color: '#A3E635' },
  { label: `Exit:`,     val: zoneDisplay.exit,       color: '#FB923C' },
];
for (const row of rows) {
  bufferCtx.fillStyle = row.color;
  bufferCtx.fillText(`${row.label} ${row.val}`, panelX + 12, sy);
  sy += 20;
}

if (inferenceTime > 0) {
  bufferCtx.fillStyle = '#9CA3AF';
  bufferCtx.font = '10px Inter, sans-serif';
  bufferCtx.fillText(`${inferenceTime.toFixed(0)}ms`, panelX + panelW - 40, panelY + panelH - 8);
}

// ========== Legend ==========
const legendItems = [
  { label: 'Moving',    color: CONFIG.stateColors.transient },
  { label: 'Browsing',  color: CONFIG.stateColors.browsing },
  { label: 'Engaged',   color: CONFIG.stateColors.engaged },
  { label: 'Need Help', color: CONFIG.stateColors.assistance },
];
const legendW = 138, legendH = legendItems.length * 18 + 16;
const legendX = canvas.width - legendW - 10;
const legendY = canvas.height - legendH - 10;

bufferCtx.fillStyle = 'rgba(0,0,0,0.85)';
bufferCtx.beginPath();
bufferCtx.roundRect(legendX, legendY, legendW, legendH, 6);
bufferCtx.fill();
bufferCtx.strokeStyle = 'rgba(255,255,255,0.3)';
bufferCtx.lineWidth = 1;
bufferCtx.stroke();

bufferCtx.font = '11px Inter, sans-serif';
legendItems.forEach((item, i) => {
  const y = legendY + 8 + i * 18 + 6;
  bufferCtx.fillStyle = item.color;
  bufferCtx.fillRect(legendX + 8, y - 8, 12, 12);
  bufferCtx.fillStyle = '#FFFFFF';
  bufferCtx.fillText(item.label, legendX + 28, y);
});

// ========== Flush to Visible Canvas ==========
ctx.clearRect(0, 0, canvas.width, canvas.height);
ctx.drawImage(state.bufferCanvas, 0, 0);
