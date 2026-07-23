/**
 * YOLO Heatmap Overlay Renderer (supports YOLO11 & YOLO26)
 *
 * Renders people flow heatmap and tracking visualization on canvas.
 * Depends on: simpleheat (https://github.com/mourner/simpleheat)
 *
 * Input (data): yolo-detector >= 0.4.0 results message
 * {
 *   timestamp: 1768969602957,
 *   frame_id: 107,
 *   inference_time_ms: 49.0,
 *   detection_count: 1,
 *   detections: [{
 *     class_id: 0, class_name: "person", confidence: 0.93,
 *     x: 0.4, y: 0.4, w: 0.2, h: 0.5,   // normalized CENTER coords
 *     track_id: 7                        // optional, present when tracking is on
 *   }],
 *   tracking: { active_tracks: 1 }       // optional
 * }
 * Legacy (< 0.4.0) tracking payloads (persons[] with top-left bbox +
 * zone_occupancy) are still accepted as a fallback.
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
// Normalize both payload generations into one shape:
// { key, cx, cy, w, h (normalized center), label, confidence }
function parsePersons(d) {
  const out = [];
  if (Array.isArray(d?.detections)) {
    // New schema (>= 0.4.0): flat normalized CENTER coords, class-filtered here
    d.detections.forEach((det, i) => {
      if (det.class_name !== 'person') return;
      out.push({
        key: det.track_id !== undefined ? det.track_id : `i${i}`,
        cx: det.x, cy: det.y, w: det.w, h: det.h,
        label: det.track_id !== undefined ? `#${det.track_id}` : `${Math.round((det.confidence || 0) * 100)}%`,
        confidence: det.confidence || 0,
      });
    });
  } else if (Array.isArray(d?.persons)) {
    // Legacy schema (< 0.4.0): bbox is TOP-LEFT, array or object form
    for (const p of d.persons) {
      const b = p.bbox;
      if (!b) continue;
      const [bx, by, bw, bh] = Array.isArray(b) ? b : [b.x, b.y, b.w, b.h];
      out.push({
        key: p.track_id,
        cx: bx + bw / 2, cy: by + bh / 2, w: bw, h: bh,
        label: p.dwell_duration_sec > 1 ? `#${p.track_id} ${p.dwell_duration_sec.toFixed(1)}s` : `#${p.track_id}`,
        confidence: p.confidence || 0,
      });
    }
  }
  return out;
}
const persons = parsePersons(data);
const totalCount = data?.detection_count !== undefined
  ? persons.length
  : (data?.zone_occupancy?.total || persons.length);
const activeTracks = data?.tracking?.active_tracks;
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
  // Convert normalized center coordinates to canvas pixels
  const x = person.cx * canvas.width;
  const y = person.cy * canvas.height;

  const heatIncrement = CONFIG.stateWeights.dwelling;

  // Update or create point
  const existing = state.points.get(person.key);
  if (existing) {
    // Smooth position update
    existing.x = existing.x * 0.7 + x * 0.3;
    existing.y = existing.y * 0.7 + y * 0.3;
    existing.heat = Math.min(existing.heat + heatIncrement, CONFIG.maxHeatValue);
  } else {
    state.points.set(person.key, {
      x, y,
      heat: heatIncrement * 2,  // Initial boost
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
  const color = CONFIG.stateColors.dwelling;

  // Box top-left from normalized CENTER coords
  const bx = (person.cx - person.w / 2) * canvas.width;
  const by = (person.cy - person.h / 2) * canvas.height;
  const bw = person.w * canvas.width;
  const bh = person.h * canvas.height;

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
  const labelText = person.label;

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

// Person count in frame
bufferCtx.fillStyle = '#FFFFFF';
bufferCtx.fillText(`People: ${totalCount}`, panelX + 12, statY);
statY += 20;

// Active tracks (new payloads only)
if (activeTracks !== undefined) {
  bufferCtx.fillStyle = CONFIG.stateColors.dwelling;
  bufferCtx.fillText(`Tracks: ${activeTracks}`, panelX + 12, statY);
  statY += 20;
}

// Heat spots currently alive on the map
bufferCtx.fillStyle = CONFIG.stateColors.engaged;
bufferCtx.fillText(`Heat spots: ${state.points.size}`, panelX + 12, statY);

// Inference time (bottom right of panel)
if (inferenceTime > 0) {
  bufferCtx.fillStyle = '#9CA3AF';
  bufferCtx.font = '10px Inter, sans-serif';
  bufferCtx.fillText(`${inferenceTime.toFixed(0)}ms`, panelX + panelWidth - 40, panelY + panelHeight - 8);
}

// ========== Render Legend to Buffer ==========
const legendItems = [
  { label: 'Person', color: CONFIG.stateColors.dwelling },
  { label: 'Low traffic', color: 'cyan' },
  { label: 'High traffic', color: 'red' },
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
