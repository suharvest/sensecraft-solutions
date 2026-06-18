/**
 * YOLO Heatmap Overlay Renderer (supports YOLO11 & YOLO26)
 *
 * Renders people flow heatmap and tracking visualization on canvas.
 * Depends on: simpleheat (https://github.com/mourner/simpleheat)
 *
 * Input (data): YOLO MQTT tracking message
 * {
 *   timestamp: 1768969602957,
 *   frame_id: 107,
 *   inference_time_ms: 308.0,
 *   frame_width: 1,
 *   frame_height: 1,
 *   zone_occupancy: { total: 1, browsing: 0, engaged: 1, assistance: 0 },
 *   persons: [{
 *     track_id: 1,
 *     confidence: 0.363,
 *     bbox: [0.3, 0.15, 0.2, 0.5],  // array [x, y, w, h], top-left coords, normalized
 *     speed_px_s: 0.2,
 *     speed_normalized: 0.2,
 *     state: "engaged",  // transient | dwelling | engaged | assistance
 *     dwell_duration_sec: 8.9
 *   }]
 * }
 *
 * Variables: ctx, data, canvas, img (provided by PreviewWindow)
 */

// ========== Configuration ==========
const CONFIG = {
  // Heatmap settings
  pointRadius: 35,
  blurRadius: 25,
  maxHeatValue: 100,
  decayRate: 0.985,

  // Weight by state
  stateWeights: {
    transient: 0.5,
    dwelling: 1.5,
    browsing: 1.5,
    engaged: 3.0,
    assistance: 5.0,
  },

  // Heatmap gradient (blue -> cyan -> lime -> yellow -> red)
  gradient: {
    0.0: 'rgba(0, 0, 255, 0)',
    0.2: 'blue',
    0.4: 'cyan',
    0.6: 'lime',
    0.8: 'yellow',
    1.0: 'red'
  },

  // State colors for bounding boxes
  stateColors: {
    transient: '#9CA3AF',   // Gray
    dwelling: '#3B82F6',    // Blue
    browsing: '#3B82F6',    // Blue
    engaged: '#F59E0B',     // Amber
    assistance: '#EF4444',  // Red
  },

  // UI settings
  boxLineWidth: 4,
  boxGlowBlur: 8,
  labelFont: 'bold 12px Inter, sans-serif',
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// ========== State Management ==========
// Persistent state across frames
if (!window._heatmapState) {
  window._heatmapState = {
    heat: null,
    points: new Map(),  // track_id -> { x, y, heat }
    initialized: false,
    lastCanvasSize: { w: 0, h: 0 },
    // Double buffering
    bufferCanvas: null,
    bufferCtx: null,
    // Static UI cache
    legendCache: null,
    statsPanelCache: null,
  };
}
const state = window._heatmapState;

// ========== Double Buffer Setup ==========
// Create or resize buffer canvas
if (!state.bufferCanvas ||
    state.bufferCanvas.width !== canvas.width ||
    state.bufferCanvas.height !== canvas.height) {
  state.bufferCanvas = document.createElement('canvas');
  state.bufferCanvas.width = canvas.width;
  state.bufferCanvas.height = canvas.height;
  state.bufferCtx = state.bufferCanvas.getContext('2d');
  // Force reinit of heatmap and caches
  state.initialized = false;
  state.legendCache = null;
  state.statsPanelCache = null;
}

const bufferCtx = state.bufferCtx;

// ========== Initialize / Reset Heatmap ==========
function initHeatmap() {
  if (typeof simpleheat === 'undefined') {
    console.warn('simpleheat library not loaded');
    return false;
  }

  // Initialize simpleheat on the BUFFER canvas, not the visible one
  state.heat = simpleheat(state.bufferCanvas);
  state.heat.radius(CONFIG.pointRadius, CONFIG.blurRadius);
  state.heat.gradient(CONFIG.gradient);
  state.heat.max(CONFIG.maxHeatValue);
  state.initialized = true;
  state.lastCanvasSize = { w: canvas.width, h: canvas.height };
  state.points.clear();
  return true;
}

// Reinitialize if canvas size changed
if (state.initialized &&
    (state.lastCanvasSize.w !== canvas.width || state.lastCanvasSize.h !== canvas.height)) {
  state.initialized = false;
}

// Initialize on first run
if (!state.initialized) {
  if (!initHeatmap()) {
    // Fallback: just draw boxes without heatmap
    ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
    ctx.font = '16px sans-serif';
    ctx.fillText('Loading heatmap...', 10, 30);
  }
}

// ========== Parse Data ==========
const persons = data?.persons || [];
const zoneOccupancy = data?.zone_occupancy || { total: 0, browsing: 0, engaged: 0, assistance: 0 };
const inferenceTime = data?.inference_time_ms || 0;

// ========== Update Heatmap Points ==========
// Decay existing points
state.points.forEach((point, trackId) => {
  point.heat *= CONFIG.decayRate;
  if (point.heat < 0.5) {
    state.points.delete(trackId);
  }
});

// Update/add current frame persons
for (const person of persons) {
  const { bbox, track_id, state: personState, dwell_duration_sec = 0 } = person;
  if (!bbox) continue;

  // Parse bbox: support both array [x, y, w, h] and object {x, y, w, h} formats
  let bboxX, bboxY, bboxW, bboxH;
  if (Array.isArray(bbox)) {
    [bboxX, bboxY, bboxW, bboxH] = bbox;
  } else {
    ({ x: bboxX, y: bboxY, w: bboxW, h: bboxH } = bbox);
  }

  // Convert top-left coordinates to center coordinates for heatmap
  // Hardware sends top-left, we need center for heat point
  const centerX = bboxX + bboxW / 2;
  const centerY = bboxY + bboxH / 2;

  // Convert normalized center coordinates to canvas pixels
  const x = centerX * canvas.width;
  const y = centerY * canvas.height;

  // Calculate heat increment based on state and dwell time
  const baseWeight = CONFIG.stateWeights[personState] || 1.0;
  const dwellBonus = Math.min(dwell_duration_sec / 10, 2.0);  // Bonus up to 2x for dwell
  const heatIncrement = baseWeight * (1 + dwellBonus);

  // Update or create point
  const existing = state.points.get(track_id);
  if (existing) {
    // Smooth position update
    existing.x = existing.x * 0.7 + x * 0.3;
    existing.y = existing.y * 0.7 + y * 0.3;
    existing.heat = Math.min(existing.heat + heatIncrement, CONFIG.maxHeatValue);
    existing.state = personState;
    existing.dwell = dwell_duration_sec;
  } else {
    state.points.set(track_id, {
      x, y,
      heat: heatIncrement * 2,  // Initial boost
      state: personState,
      dwell: dwell_duration_sec,
    });
  }
}

// ========== Render to Buffer ==========
// Clear buffer
bufferCtx.clearRect(0, 0, canvas.width, canvas.height);

// Draw heatmap to buffer
if (state.heat && state.points.size > 0) {
  // Convert Map to simpleheat data format: [[x, y, value], ...]
  const heatData = Array.from(state.points.values())
    .map(p => [p.x, p.y, p.heat]);

  state.heat.data(heatData);
  state.heat.draw(0.05);  // minOpacity
}

// ========== Render Person Bounding Boxes to Buffer ==========
for (const person of persons) {
  const { bbox, track_id, state: personState, dwell_duration_sec = 0, confidence = 0 } = person;
  if (!bbox) continue;

  const color = CONFIG.stateColors[personState] || '#FFFFFF';

  // Parse bbox: support both array [x, y, w, h] and object {x, y, w, h} formats
  let bboxX, bboxY, bboxW, bboxH;
  if (Array.isArray(bbox)) {
    [bboxX, bboxY, bboxW, bboxH] = bbox;
  } else {
    ({ x: bboxX, y: bboxY, w: bboxW, h: bboxH } = bbox);
  }

  // Calculate box coordinates (bbox is top-left based from hardware)
  const bx = bboxX * canvas.width;
  const by = bboxY * canvas.height;
  const bw = bboxW * canvas.width;
  const bh = bboxH * canvas.height;

  // Draw bounding box with glow effect for visibility
  bufferCtx.save();
  bufferCtx.shadowColor = color;
  bufferCtx.shadowBlur = CONFIG.boxGlowBlur;
  bufferCtx.strokeStyle = color;
  bufferCtx.lineWidth = CONFIG.boxLineWidth;
  bufferCtx.strokeRect(bx, by, bw, bh);
  // Draw twice for stronger glow
  bufferCtx.strokeRect(bx, by, bw, bh);
  bufferCtx.restore();

  // Draw semi-transparent fill
  bufferCtx.fillStyle = color;
  bufferCtx.globalAlpha = 0.15;
  bufferCtx.fillRect(bx, by, bw, bh);
  bufferCtx.globalAlpha = 1.0;

  // Draw label background
  const labelText = dwell_duration_sec > 1
    ? `#${track_id} ${dwell_duration_sec.toFixed(1)}s`
    : `#${track_id}`;

  bufferCtx.font = CONFIG.labelFont;
  const textWidth = bufferCtx.measureText(labelText).width;

  bufferCtx.fillStyle = color;
  bufferCtx.fillRect(bx, by - 22, textWidth + 10, 20);

  // Draw label text
  bufferCtx.fillStyle = '#FFFFFF';
  bufferCtx.fillText(labelText, bx + 5, by - 7);
}

// ========== Render Stats Panel to Buffer ==========
bufferCtx.globalAlpha = 1.0;

const panelWidth = 180;
const panelHeight = 130;
const panelX = 10;
const panelY = 10;

// Panel background
bufferCtx.fillStyle = 'rgba(0, 0, 0, 0.85)';
bufferCtx.beginPath();
bufferCtx.roundRect(panelX, panelY, panelWidth, panelHeight, 8);
bufferCtx.fill();

// Panel border
bufferCtx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
bufferCtx.lineWidth = 1;
bufferCtx.stroke();

// Title
bufferCtx.fillStyle = '#FFFFFF';
bufferCtx.font = CONFIG.statsHeaderFont;
bufferCtx.fillText('People Flow Stats', panelX + 12, panelY + 24);

// Stats
bufferCtx.font = CONFIG.statsFont;
let statY = panelY + 48;

// Total count
bufferCtx.fillStyle = '#FFFFFF';
bufferCtx.fillText(`Total: ${zoneOccupancy.total || 0}`, panelX + 12, statY);
statY += 20;

// Browsing
bufferCtx.fillStyle = CONFIG.stateColors.browsing;
bufferCtx.fillText(`Browsing: ${zoneOccupancy.browsing || 0}`, panelX + 12, statY);
statY += 20;

// Engaged
bufferCtx.fillStyle = CONFIG.stateColors.engaged;
bufferCtx.fillText(`Engaged: ${zoneOccupancy.engaged || 0}`, panelX + 12, statY);
statY += 20;

// Assistance
bufferCtx.fillStyle = CONFIG.stateColors.assistance;
bufferCtx.fillText(`Need Help: ${zoneOccupancy.assistance || 0}`, panelX + 12, statY);

// Inference time (bottom right of panel)
if (inferenceTime > 0) {
  bufferCtx.fillStyle = '#9CA3AF';
  bufferCtx.font = '10px Inter, sans-serif';
  bufferCtx.fillText(`${inferenceTime.toFixed(0)}ms`, panelX + panelWidth - 40, panelY + panelHeight - 8);
}

// ========== Render Legend to Buffer ==========
const legendItems = [
  { label: 'Moving', color: CONFIG.stateColors.transient },
  { label: 'Browsing', color: CONFIG.stateColors.browsing },
  { label: 'Engaged', color: CONFIG.stateColors.engaged },
  { label: 'Need Help', color: CONFIG.stateColors.assistance },
];
const legendW = 138;
const legendH = legendItems.length * 18 + 16;
const legendX = canvas.width - legendW - 10;
const legendY = canvas.height - legendH - 10;

// Legend background
bufferCtx.fillStyle = 'rgba(0, 0, 0, 0.85)';
bufferCtx.beginPath();
bufferCtx.roundRect(legendX, legendY, legendW, legendH, 6);
bufferCtx.fill();

// Legend border
bufferCtx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
bufferCtx.lineWidth = 1;
bufferCtx.stroke();

bufferCtx.font = '11px Inter, sans-serif';
legendItems.forEach((item, i) => {
  const y = legendY + 8 + i * 18 + 6;

  // Color box
  bufferCtx.fillStyle = item.color;
  bufferCtx.fillRect(legendX + 8, y - 8, 12, 12);

  // Label
  bufferCtx.fillStyle = '#FFFFFF';
  bufferCtx.fillText(item.label, legendX + 28, y);
});

// ========== Copy Buffer to Visible Canvas (Single Operation) ==========
ctx.clearRect(0, 0, canvas.width, canvas.height);
ctx.drawImage(state.bufferCanvas, 0, 0);
