/**
 * FaceMesh Drowsiness Overlay — ADAPTER
 *
 * Maps the facemesh-reader MQTT payload to a RecameraOverlay `model` and
 * delegates all drawing to the shared renderer (window.RecameraOverlay). This
 * file contains ONLY app-specific field mapping.
 *
 * Input (data): facemesh-reader MQTT message
 * {
 *   face_count: 1, inference_time_ms: 125.5,
 *   faces: [{
 *     id: 0,
 *     bbox: { x, y, w, h },       // NORMALIZED CENTER (x,y = center), 0-1
 *     confidence: 0.95,
 *     ear: 0.1789, mar: 0.5678, eyes_closed: false, mouth_open: false,
 *     landmarks: [[x,y], …],      // optional, normalized 0-1 (468-pt mesh)
 *     drowsiness: {
 *       level: 0.42,              // NOTE: field is `level` (was misread as drowsiness_level)
 *       state: "Tired", perclos_pct: 12.5, continuous_closure_sec: 1.2,
 *       alert_active: false
 *     },
 *     yawn: { is_yawning: false, yawn_count_5min: 1 }
 *   }]
 * }
 *
 * ── Two bugs fixed here vs. the old hand-drawn version ──
 *  (1) bbox is a normalized CENTER; the old script treated x,y as top-left, so
 *      every box was offset down-right by half its size. We convert to top-left.
 *  (2) drowsiness level lives at `drowsiness.level`; the old stats panel read
 *      `drowsiness.drowsiness_level` (always undefined → bar stuck at 0). Fixed.
 *
 * State → tone:  Alert→ok(green)  Tired/Drowsy→warn(yellow)  Danger→alert(red)
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
} else {
  var faces = (data && data.faces) || [];
  var STATE_TONE = { Alert: 'ok', Tired: 'warn', Drowsy: 'warn', Danger: 'alert' };
  var STATE_COLOR = { Alert: '#22C55E', Tired: '#EAB308', Drowsy: '#F97316', Danger: '#EF4444' };

  var boxItems = [];
  var kpItems = [];

  for (var i = 0; i < faces.length; i++) {
    var face = faces[i];
    var bb = face.bbox;
    var d = face.drowsiness || {};
    var state = d.state || 'Alert';
    var color = STATE_COLOR[state] || '#8fc31f';

    if (bb) {
      // BUG FIX (1): MQTT bbox x,y is the CENTER → convert to top-left origin.
      var tl = { x: bb.x - bb.w / 2, y: bb.y - bb.h / 2, w: bb.w, h: bb.h };
      boxItems.push({ bbox: tl, label: state, confidence: face.confidence, color: color });
    }

    // Optional 468-pt face mesh, if the device pushed landmarks.
    if (Array.isArray(face.landmarks) && face.landmarks.length) {
      kpItems.push({ points: face.landmarks, color: color });
    }
  }

  var layers = [];
  if (boxItems.length) layers.push({ type: 'boxes', items: boxItems });
  if (kpItems.length) layers.push({ type: 'keypoints', items: kpItems });

  // Status card from the primary (first) face.
  if (faces.length) {
    var primary = faces[0];
    var pd = primary.drowsiness || {};
    var py = primary.yawn || {};
    var pstate = pd.state || 'Alert';
    var metrics = [];
    // BUG FIX (2): read `level`, not `drowsiness_level`.
    if (pd.level != null) metrics.push({ k: 'Drowsiness', v: (pd.level * 100).toFixed(0) + '%' });
    if (primary.ear != null) metrics.push({ k: 'EAR', v: primary.ear.toFixed(3) });
    if (primary.mar != null) metrics.push({ k: 'MAR', v: primary.mar.toFixed(3) });
    if (pd.perclos_pct != null) metrics.push({ k: 'PERCLOS', v: pd.perclos_pct.toFixed(1) + '%' });
    if (py.yawn_count_5min != null) metrics.push({ k: 'Yawns/5min', v: String(py.yawn_count_5min) });

    layers.push({
      type: 'card',
      variant: 'status',
      anchor: 'tr',
      data: {
        title: pstate,
        tone: STATE_TONE[pstate] || 'ok',
        metrics: metrics,
        banner: pd.alert_active ? 'DROWSINESS ALERT' : undefined,
      },
    });
  }

  if (layers.length) {
    R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
  }
}
