/**
 * Face Analysis Overlay Renderer
 *
 * Renders face detection + age/gender/emotion/race results on canvas.
 * No external dependencies required.
 *
 * Input (data): face-analysis MQTT message
 * {
 *   face_count: 2,
 *   inference_time_ms: 125.5,
 *   faces: [{
 *     bbox: { x: 0.25, y: 0.3, w: 0.15, h: 0.2 },
 *     confidence: 0.95,
 *     age_label: "20-29",
 *     gender: "male",
 *     gender_confidence: 0.88,
 *     emotion: "happy",
 *     emotion_confidence: 0.91,
 *     emotion_probs: { angry: 0.02, disgust: 0.01, fear: 0.0, happy: 0.91, sad: 0.01, surprise: 0.05, neutral: 0.0 },
 *     race: "East_Asian",
 *     race_confidence: 0.82
 *   }]
 * }
 *
 * Supports both FairFace format (age_bin/age_label/race) and
 * InsightFace format (age as integer, no race).
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
  boxColor: '#FF6B9D',
  boxLineWidth: 2,
  boxGlowBlur: 6,

  // Label styling
  labelFont: 'bold 12px Inter, sans-serif',
  labelBgColor: 'rgba(200, 50, 100, 0.85)',
  labelTextColor: '#FFFFFF',
  labelLineHeight: 18,
  labelPadding: 6,

  // Stats panel
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// Emotion display names
const EMOTION_LABELS = {
  happy: 'Happy',
  sad: 'Sad',
  angry: 'Angry',
  surprise: 'Surprised',
  fear: 'Fear',
  disgust: 'Disgust',
  neutral: 'Neutral',
};

// ========== Parse Data ==========
const faces = data?.faces || [];
const faceCount = data?.face_count ?? faces.length;
const inferenceMs = data?.inference_time_ms;

// ========== Render Face Boxes ==========
for (const face of faces) {
  const { bbox, confidence, gender, gender_confidence, emotion, emotion_confidence } = face;
  if (!bbox) continue;

  // Normalized coords (0-1) → canvas pixels
  // Canvas is already sized and positioned to match the video content area
  const x = bbox.x * canvas.width;
  const y = bbox.y * canvas.height;
  const w = bbox.w * canvas.width;
  const h = bbox.h * canvas.height;

  // Draw bounding box with glow
  ctx.save();
  ctx.shadowColor = CONFIG.boxColor;
  ctx.shadowBlur = CONFIG.boxGlowBlur;
  ctx.strokeStyle = CONFIG.boxColor;
  ctx.lineWidth = CONFIG.boxLineWidth;
  ctx.strokeRect(x, y, w, h);
  ctx.restore();

  // Build label lines
  const lines = [];

  // Line 1: Gender + Age
  if (gender != null) {
    const genderLabel = gender === 'male' ? 'M' : 'F';
    // Support both FairFace (age_label: "20-29") and InsightFace (age: 28)
    const ageStr = face.age_label || (face.age != null ? `${face.age}` : null);
    if (ageStr) {
      lines.push(`${genderLabel}, ${ageStr}`);
    } else {
      lines.push(genderLabel);
    }
  }

  // Line 2: Emotion
  if (emotion) {
    const emotionLabel = EMOTION_LABELS[emotion] || emotion;
    const conf = emotion_confidence != null ? ` ${(emotion_confidence * 100).toFixed(0)}%` : '';
    lines.push(`${emotionLabel}${conf}`);
  }

  // Line 3: Race (FairFace only)
  if (face.race) {
    const raceLabel = face.race.replace(/_/g, ' ');
    lines.push(raceLabel);
  }

  // Draw label above bounding box
  if (lines.length > 0) {
    ctx.font = CONFIG.labelFont;
    const maxWidth = Math.max(...lines.map(l => ctx.measureText(l).width));
    const labelX = x;
    const labelH = lines.length * CONFIG.labelLineHeight + CONFIG.labelPadding;
    const labelY = y - labelH - 4;

    // Background
    ctx.fillStyle = CONFIG.labelBgColor;
    ctx.fillRect(labelX, labelY, maxWidth + CONFIG.labelPadding * 2, labelH);

    // Text lines
    ctx.fillStyle = CONFIG.labelTextColor;
    for (let i = 0; i < lines.length; i++) {
      ctx.fillText(lines[i], labelX + CONFIG.labelPadding, labelY + CONFIG.labelPadding + 12 + i * CONFIG.labelLineHeight);
    }
  }
}

// ========== Render Stats Panel ==========
const panelWidth = 180;
const lineCount = 2 + (inferenceMs != null ? 1 : 0);
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
ctx.fillText('Face Analysis', panelX + 12, panelY + 24);

// Stats
ctx.font = CONFIG.statsFont;
let statY = panelY + 48;

// Face count
ctx.fillStyle = '#FFFFFF';
ctx.fillText(`Faces detected: ${faceCount}`, panelX + 12, statY);
statY += 20;

// Inference time
if (inferenceMs != null) {
  ctx.fillStyle = '#9CA3AF';
  ctx.fillText(`Inference: ${inferenceMs}ms`, panelX + 12, statY);
}
