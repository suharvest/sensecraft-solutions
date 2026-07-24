/**
 * Face Analysis Overlay — ADAPTER
 *
 * Maps the face-analysis MQTT payload to a RecameraOverlay `model` and
 * delegates all drawing to the shared renderer (window.RecameraOverlay). This
 * file contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): face-analysis MQTT message (see main/mqtt_payload.cpp)
 * {
 *   timestamp, frame_id, inference_time_ms, face_count,
 *   faces: [{
 *     id: 0,
 *     bbox: { x, y, w, h },        // NORMALIZED TOP-LEFT (main.cpp: "x/y are top-left")
 *     confidence: 0.95,
 *     age_label: "20-29",          // FairFace bin string, or "age": 28 (InsightFace int)
 *     gender: "male" | "female", gender_confidence,
 *     emotion: "happy", emotion_confidence, emotion_probs: {...},
 *     race: "East_Asian", race_confidence   // FairFace only, optional
 *   }]
 * }
 *
 * Each face → one box (color hashed per gender) with a compact attribute label
 * "F·28·Happy". A metrics card (top-right) shows face count + inference time.
 *
 * bbox is TOP-LEFT here (unlike facemesh which is CENTER) — verified against
 * face_detector.cpp (center→top-left done device-side) so NO conversion.
 *
 * Variables: ctx, data, canvas, img (provided by the preview host).
 */

var R = (typeof window !== 'undefined') && window.RecameraOverlay;
if (!R || typeof R.render !== 'function') {
  ctx.fillStyle = 'rgba(200,0,0,0.8)';
  ctx.fillRect(10, 10, 320, 26);
  ctx.fillStyle = '#fff';
  ctx.font = '12px monospace';
  ctx.fillText('RecameraOverlay not loaded', 16, 28);
} else if (data) {
  var EMOTION_LABELS = {
    happy: 'Happy', sad: 'Sad', angry: 'Angry', surprise: 'Surprised',
    fear: 'Fear', disgust: 'Disgust', neutral: 'Neutral', contempt: 'Contempt',
  };
  var GENDER_COLOR = { male: '#4A90D9', female: '#E0518A' };

  var faces = data.faces || [];
  var boxItems = [];

  for (var i = 0; i < faces.length; i++) {
    var face = faces[i];
    var bb = face.bbox;
    if (!bb) continue;

    // Compact attribute label: gender initial · age · emotion  (e.g. "F·28·Happy")
    var parts = [];
    if (face.gender != null) parts.push(face.gender === 'male' ? 'M' : 'F');
    var ageStr = face.age_label || (face.age != null ? String(face.age) : null);
    if (ageStr) parts.push(ageStr);
    if (face.emotion) parts.push(EMOTION_LABELS[face.emotion] || face.emotion);
    var label = parts.join('·') || 'face';

    boxItems.push({
      bbox: { x: bb.x, y: bb.y, w: bb.w, h: bb.h },  // top-left, no conversion
      label: label,
      color: GENDER_COLOR[face.gender] || undefined,  // else hashed
    });
  }

  var layers = [];
  if (boxItems.length) layers.push({ type: 'boxes', items: boxItems });

  // Metrics card (top-right): face count + inference time.
  var metrics = [];
  var faceCount = data.face_count != null ? data.face_count : faces.length;
  metrics.push({ k: 'Faces', v: String(faceCount) });
  if (data.inference_time_ms != null) metrics.push({ k: 'Inference', v: data.inference_time_ms + 'ms' });
  layers.push({ type: 'card', variant: 'metrics', anchor: 'tr', data: { title: 'Face Analysis', metrics: metrics } });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
