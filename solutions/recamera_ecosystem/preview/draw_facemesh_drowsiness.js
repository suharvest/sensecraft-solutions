/**
 * FaceMesh Drowsiness Detection Overlay Renderer
 *
 * Renders face bounding boxes with EAR/MAR values and drowsiness state.
 * No external dependencies required.
 *
 * Input (data): facemesh-reader MQTT message
 * {
 *   face_count: 1,
 *   inference_time_ms: 125.5,
 *   faces: [{
 *     id: 0,
 *     bbox: { x: 0.25, y: 0.3, w: 0.15, h: 0.2 },
 *     confidence: 0.95,
 *     ear: 0.1789,
 *     mar: 0.5678,
 *     eyes_closed: false,
 *     mouth_open: false,
 *     drowsiness: {
 *       level: 0.42,
 *       state: "Tired",
 *       perclos_pct: 12.5,
 *       continuous_closure_sec: 1.2,
 *       alert_active: false,
 *       drowsy_by_ear: false,
 *       drowsy_by_perclos: false,
 *       drowsy_by_yawn: false
 *     },
 *     yawn: {
 *       is_yawning: false,
 *       yawn_count_5min: 1
 *     }
 *   }]
 * }
 *
 * State color mapping:
 *   Alert  (level < 0.3) — green
 *   Tired  (level < 0.6) — yellow
 *   Drowsy (level < 0.8) — orange
 *   Danger (level >= 0.8) — red
 *
 * Coordinates are normalized (0-1).
 * Variables: ctx, data, canvas, img (provided by PreviewWindow)
 */

// ========== Polyfill ==========
if (typeof ctx.roundRect !== 'function') {
  ctx.roundRect = function(x, y, w, h, radii) {
    const r = typeof radii === 'number' ? radii : (Array.isArray(radii) ? radii[0] : 0);
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
  // Drowsiness state colors
  stateColors: {
    'Alert':  { box: '#22C55E', bg: 'rgba(34, 197, 94, 0.85)' },    // green
    'Tired':  { box: '#EAB308', bg: 'rgba(234, 179, 8, 0.85)' },    // yellow
    'Drowsy': { box: '#F97316', bg: 'rgba(249, 115, 22, 0.85)' },   // orange
    'Danger': { box: '#EF4444', bg: 'rgba(239, 68, 68, 0.85)' },    // red
  },
  defaultColor: '#8CC63F',

  boxLineWidth: 2,
  boxGlowBlur: 6,

  // Label styling
  labelFont: 'bold 12px Inter, sans-serif',
  labelTextColor: '#FFFFFF',
  labelLineHeight: 18,
  labelPadding: 6,

  // State indicator
  stateFont: 'bold 14px Inter, sans-serif',

  // Stats panel
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// ========== Helpers ==========
function getStateColor(state) {
  const colors = CONFIG.stateColors[state];
  return colors || { box: CONFIG.defaultColor, bg: 'rgba(140, 198, 63, 0.85)' };
}

function formatDuration(seconds) {
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  return `${seconds.toFixed(1)}s`;
}

// ========== Parse Data ==========
const faces = data?.faces || [];
const faceCount = data?.face_count ?? faces.length;
const inferenceMs = data?.inference_time_ms;

// ========== Render Face Boxes ==========
for (const face of faces) {
  const { bbox, confidence, ear, mar, eyes_closed, mouth_open } = face;
  const drowsiness = face.drowsiness || {};
  const yawn = face.yawn || {};
  if (!bbox) continue;

  // Normalized coords (0-1) → canvas pixels
  const x = bbox.x * canvas.width;
  const y = bbox.y * canvas.height;
  const w = bbox.w * canvas.width;
  const h = bbox.h * canvas.height;

  // Determine box color from drowsiness state
  const state = drowsiness.state || 'Alert';
  const colors = getStateColor(state);

  // Draw bounding box with glow
  ctx.save();
  ctx.shadowColor = colors.box;
  ctx.shadowBlur = CONFIG.boxGlowBlur;
  ctx.strokeStyle = colors.box;
  ctx.lineWidth = CONFIG.boxLineWidth;
  ctx.strokeRect(x, y, w, h);
  ctx.restore();

  // Build label lines
  const lines = [];

  // Line 1: EAR + MAR
  const earStr = ear != null ? `EAR: ${ear.toFixed(3)}` : '';
  const marStr = mar != null ? `MAR: ${mar.toFixed(3)}` : '';
  if (earStr || marStr) {
    lines.push([earStr, marStr].filter(Boolean).join('  '));
  }

  // Line 2: Eyes / Mouth state
  const eyeState = eyes_closed ? 'Eyes: CLOSED' : 'Eyes: Open';
  const mouthState = mouth_open ? 'Mouth: Open' : 'Mouth: Closed';
  lines.push(`${eyeState}  ${mouthState}`);

  // Line 3: Yawn info
  if (yawn.is_yawning) {
    lines.push(`YAWNING (${yawn.yawn_count_5min}/5min)`);
  } else if (yawn.yawn_count_5min > 0) {
    lines.push(`Yawns: ${yawn.yawn_count_5min} in 5min`);
  }

  // Line 4: Drowsiness state indicator
  if (state !== 'Alert') {
    const perclos = drowsiness.perclos_pct != null ? `PERCLOS: ${drowsiness.perclos_pct.toFixed(1)}%` : '';
    const closure = drowsiness.continuous_closure_sec != null
      ? `Closure: ${formatDuration(drowsiness.continuous_closure_sec)}` : '';
    lines.push([perclos, closure].filter(Boolean).join('  '));
  }

  // Draw state badge above bounding box (bigger, colored)
  ctx.font = CONFIG.stateFont;
  const stateText = state === 'Alert' ? 'Alert' : state;
  const stateWidth = ctx.measureText(stateText).width;

  // Label box for metrics
  if (lines.length > 0) {
    ctx.font = CONFIG.labelFont;
    const maxWidth = Math.max(...lines.map(l => ctx.measureText(l).width));
    const labelX = x;
    const metricsH = lines.length * CONFIG.labelLineHeight + CONFIG.labelPadding + 14;
    const metricsY = y - metricsH - 4;

    // Background for metrics
    ctx.fillStyle = colors.bg;
    ctx.beginPath();
    ctx.roundRect(labelX, metricsY, maxWidth + CONFIG.labelPadding * 2, metricsH, 4);
    ctx.fill();

    // State label (bigger, at top of label box)
    ctx.font = CONFIG.stateFont;
    ctx.fillStyle = CONFIG.labelTextColor;
    ctx.fillText(stateText, labelX + CONFIG.labelPadding, metricsY + 14);

    // Metric lines below
    ctx.font = CONFIG.labelFont;
    for (let i = 0; i < lines.length; i++) {
      ctx.fillText(lines[i], labelX + CONFIG.labelPadding, metricsY + 14 + 14 + i * CONFIG.labelLineHeight);
    }
  }
}

// ========== Render Stats Panel ==========
const panelWidth = 195;
const lineCount = 2 + (faceCount > 0 ? 2 : 0) + (inferenceMs != null ? 1 : 0) + 2;
const panelHeight = 28 + lineCount * 20;
const panelX = 10;
const panelY = 10;

// Panel background
ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
ctx.beginPath();
ctx.roundRect(panelX, panelY, panelWidth, panelHeight, 8);
ctx.fill();

// Panel border
ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
ctx.lineWidth = 1;
ctx.stroke();

// Title
ctx.fillStyle = '#FFFFFF';
ctx.font = CONFIG.statsHeaderFont;
ctx.fillText('Drowsiness Detection', panelX + 12, panelY + 24);

// Stats
ctx.font = CONFIG.statsFont;
let statY = panelY + 48;

// Face count
ctx.fillStyle = '#FFFFFF';
ctx.fillText(`Faces: ${faceCount}`, panelX + 12, statY);
statY += 20;

// Inference time
if (inferenceMs != null) {
  ctx.fillStyle = '#9CA3AF';
  ctx.fillText(`Inference: ${inferenceMs}ms`, panelX + 12, statY);
  statY += 20;
}

// Per-face summary
if (faces.length > 0) {
  statY += 4;

  // Collect summary for first face (primary)
  const primary = faces[0];
  const d = primary.drowsiness || {};

  // Drowsiness level bar
  const level = d.drowsiness_level != null ? d.drowsiness_level : 0;
  const stateLabel = d.state || 'Alert';
  const barW = 160;
  const barH = 8;
  const barX = panelX + 12;
  const barY = statY;

  // Bar background
  ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
  ctx.beginPath();
  ctx.roundRect(barX, barY, barW, barH, 4);
  ctx.fill();

  // Bar fill (color-coded)
  const fillW = Math.min(level, 1) * barW;
  const barColors = { 'Alert': '#22C55E', 'Tired': '#EAB308', 'Drowsy': '#F97316', 'Danger': '#EF4444' };
  ctx.fillStyle = barColors[stateLabel] || '#8CC63F';
  ctx.beginPath();
  ctx.roundRect(barX, barY, fillW, barH, 4);
  ctx.fill();

  statY += 16;

  // PERCLOS
  if (d.perclos_pct != null) {
    ctx.fillStyle = d.perclos_pct > 15 ? '#EF4444' : '#FFFFFF';
    ctx.fillText(`PERCLOS: ${d.perclos_pct.toFixed(1)}%`, panelX + 12, statY);
    statY += 20;
  }

  // Yawn count
  const y = primary.yawn || {};
  if (y.yawn_count_5min > 0) {
    ctx.fillStyle = y.is_yawning ? '#F97316' : '#9CA3AF';
    ctx.fillText(`Yawns (5min): ${y.yawn_count_5min}${y.is_yawning ? ' ★' : ''}`, panelX + 12, statY);
    statY += 20;
  }

  // Closure time
  if (d.continuous_closure_sec != null && d.continuous_closure_sec > 0.5) {
    ctx.fillStyle = '#F97316';
    ctx.fillText(`Eyes closed: ${formatDuration(d.continuous_closure_sec)}`, panelX + 12, statY);
  }
}
