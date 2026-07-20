/**
 * Weather Classification Overlay Renderer
 *
 * Renders the current weather class + confidence + per-class score bars
 * on canvas. No external dependencies required.
 *
 * Input (data): weather classification MQTT message
 * {
 *   type: "classification",
 *   frame: 42,
 *   label: "foggy",
 *   class_id: 2,
 *   confidence: 0.8341,
 *   scores: { clear: 0.01, cloudy: 0.05, foggy: 0.83, rainy: 0.08, snowy: 0.03 },
 *   inference_time_ms: 12.1,
 *   capture_ms: 1.2,
 *   preprocess_ms: 3.44,
 *   total_ms: 17.02
 * }
 *
 * There is no bbox — this is a whole-frame classification, so the overlay
 * is a single status card, not per-object boxes.
 *
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
  cardFont: 'bold 22px Inter, sans-serif',
  confFont: '13px Inter, sans-serif',
  barFont: '11px Inter, sans-serif',
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// Weather class → { icon (emoji), color, display label }
const WEATHER_META = {
  clear: { icon: '☀️', color: '#F5A623', label: 'Clear' },
  cloudy: { icon: '☁️', color: '#9CA3AF', label: 'Cloudy' },
  foggy: { icon: '🌫️', color: '#B0BEC5', label: 'Foggy' },
  rainy: { icon: '🌧️', color: '#4A90D9', label: 'Rainy' },
  snowy: { icon: '❄️', color: '#7DD3FC', label: 'Snowy' },
};
const CLASS_ORDER = ['clear', 'cloudy', 'foggy', 'rainy', 'snowy'];

// ========== Parse Data ==========
const label = data?.label;
const confidence = data?.confidence;
const scores = data?.scores || {};
const inferenceMs = data?.inference_time_ms;
const totalMs = data?.total_ms;
const meta = WEATHER_META[label] || { icon: '❓', color: '#9CA3AF', label: label || 'Unknown' };

// ========== Render Weather Card (top-left) ==========
const cardX = 10;
const cardY = 10;
const cardWidth = 220;
const cardHeight = 92;

ctx.save();
ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
ctx.shadowBlur = 10;
ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
ctx.beginPath();
ctx.roundRect(cardX, cardY, cardWidth, cardHeight, 10);
ctx.fill();
ctx.restore();

ctx.strokeStyle = meta.color;
ctx.lineWidth = 2;
ctx.beginPath();
ctx.roundRect(cardX, cardY, cardWidth, cardHeight, 10);
ctx.stroke();

// Icon + label
ctx.font = CONFIG.cardFont;
ctx.fillStyle = '#FFFFFF';
ctx.fillText(`${meta.icon} ${meta.label}`, cardX + 14, cardY + 32);

// Confidence
if (confidence != null) {
  ctx.font = CONFIG.confFont;
  ctx.fillStyle = meta.color;
  ctx.fillText(`${(confidence * 100).toFixed(1)}% confidence`, cardX + 14, cardY + 52);
}

// ========== Per-class score bars ==========
const barX = cardX + 14;
let barY = cardY + 62;
const barMaxWidth = cardWidth - 28;
const barHeight = 5;

ctx.font = CONFIG.barFont;
for (const cls of CLASS_ORDER) {
  const score = scores[cls];
  if (score == null) continue;
  const m = WEATHER_META[cls];
  const w = Math.max(2, score * barMaxWidth);

  ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
  ctx.fillRect(barX, barY, barMaxWidth, barHeight);

  ctx.fillStyle = cls === label ? m.color : 'rgba(255, 255, 255, 0.4)';
  ctx.fillRect(barX, barY, w, barHeight);

  barY += barHeight + 3;
}

// ========== Stats Panel (top-right) ==========
if (inferenceMs != null || totalMs != null) {
  const panelWidth = 170;
  const lineCount = (inferenceMs != null ? 1 : 0) + (totalMs != null ? 1 : 0);
  const panelHeight = 28 + lineCount * 20;
  const panelX = canvas.width - panelWidth - 10;
  const panelY = 10;

  ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
  ctx.beginPath();
  ctx.roundRect(panelX, panelY, panelWidth, panelHeight, 8);
  ctx.fill();

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.fillStyle = '#FFFFFF';
  ctx.font = CONFIG.statsHeaderFont;
  ctx.fillText('Weather AI', panelX + 12, panelY + 24);

  ctx.font = CONFIG.statsFont;
  let statY = panelY + 48;

  if (inferenceMs != null) {
    ctx.fillStyle = '#9CA3AF';
    ctx.fillText(`Inference: ${inferenceMs}ms`, panelX + 12, statY);
    statY += 20;
  }
  if (totalMs != null) {
    ctx.fillStyle = '#9CA3AF';
    ctx.fillText(`Total: ${totalMs}ms`, panelX + 12, statY);
  }
}
