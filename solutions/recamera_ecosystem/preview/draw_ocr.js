/**
 * PP-OCRv3 Overlay Renderer
 *
 * Renders OCR text detection results on canvas.
 * No external dependencies required.
 *
 * Input (data): PP-OCR MQTT message (v0.2.x)
 * {
 *   timestamp: 1768969602957,
 *   frame_id: 42,
 *   inference_time_ms: { detection: 65.2, recognition: 48.3, total: 113.5 },
 *   text_count: 2,
 *   frame_width: 1,
 *   frame_height: 1,
 *   texts: [{
 *     id: 0,
 *     box: [[0.005, 0.042], [0.952, 0.042], [0.952, 0.104], [0.005, 0.104]],
 *     text: "Hello World",
 *     confidence: 0.95,
 *     det_confidence: 0.88
 *   }]
 * }
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
  // Box styling
  boxColor: '#00FF66',
  boxLineWidth: 2,
  boxGlowBlur: 6,

  // Label styling
  labelFont: 'bold 12px Inter, sans-serif',
  labelBgColor: 'rgba(0, 200, 80, 0.85)',
  labelTextColor: '#FFFFFF',

  // Stats panel
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// ========== Parse Data ==========
const texts = data?.texts || [];
const inferenceMs = data?.inference_time_ms || {};
const textCount = data?.text_count ?? texts.length;

// ========== Render Text Boxes ==========
for (const item of texts) {
  const { box, text, confidence, det_confidence } = item;
  if (!box || box.length < 4) continue;

  // Normalized coords (0-1) → canvas pixels
  // Canvas is already sized and positioned to match the video content area
  const pts = box.map(([x, y]) => [x * canvas.width, y * canvas.height]);

  // Draw quadrilateral outline with glow
  ctx.save();
  ctx.shadowColor = CONFIG.boxColor;
  ctx.shadowBlur = CONFIG.boxGlowBlur;
  ctx.strokeStyle = CONFIG.boxColor;
  ctx.lineWidth = CONFIG.boxLineWidth;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(pts[i][0], pts[i][1]);
  }
  ctx.closePath();
  ctx.stroke();
  ctx.restore();

  // Draw label above top-left corner
  if (text) {
    const conf = confidence != null ? ` ${(confidence * 100).toFixed(0)}%` : '';
    const labelText = `${text}${conf}`;

    ctx.font = CONFIG.labelFont;
    const textWidth = ctx.measureText(labelText).width;
    const labelX = pts[0][0];
    const labelY = pts[0][1] - 6;

    // Background
    ctx.fillStyle = CONFIG.labelBgColor;
    ctx.fillRect(labelX, labelY - 16, textWidth + 10, 20);

    // Text
    ctx.fillStyle = CONFIG.labelTextColor;
    ctx.fillText(labelText, labelX + 5, labelY - 1);
  }
}

// ========== Render Stats Panel ==========
const panelWidth = 180;
const lineCount = 3 + (inferenceMs.detection != null ? 1 : 0) + (inferenceMs.recognition != null ? 1 : 0);
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
ctx.fillText('OCR Stats', panelX + 12, panelY + 24);

// Stats
ctx.font = CONFIG.statsFont;
let statY = panelY + 48;

// Text count
ctx.fillStyle = '#FFFFFF';
ctx.fillText(`Texts detected: ${textCount}`, panelX + 12, statY);
statY += 20;

// Inference timing
if (inferenceMs.detection != null) {
  ctx.fillStyle = '#9CA3AF';
  ctx.fillText(`Detection: ${inferenceMs.detection}ms`, panelX + 12, statY);
  statY += 20;
}
if (inferenceMs.recognition != null) {
  ctx.fillStyle = '#9CA3AF';
  ctx.fillText(`Recognition: ${inferenceMs.recognition}ms`, panelX + 12, statY);
  statY += 20;
}
if (inferenceMs.total != null) {
  ctx.fillStyle = '#9CA3AF';
  ctx.fillText(`Total: ${inferenceMs.total}ms`, panelX + 12, statY);
}
