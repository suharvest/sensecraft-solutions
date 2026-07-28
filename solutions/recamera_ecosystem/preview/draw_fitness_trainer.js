/**
 * Fitness Trainer Overlay — ADAPTER
 *
 * Maps the fitness-trainer MQTT payload to a RecameraOverlay `model` and
 * delegates all drawing to the shared renderer (window.RecameraOverlay). This
 * file contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): fitness-trainer MQTT message
 * {
 *   timestamp: 1753689600123, frame_id: 4821, inference_time_ms: 55,
 *   exercise: "squat", stage: "down", angle: 92.4,
 *   reps: 7, target_reps: 12, set: 2, target_sets: 3,
 *   workout_complete: false, person_detected: true, tracking: true,
 *   rep_completed: false, set_completed: false,
 *   form_warning: "Partial rep - squat deeper",   // only when form is off
 *   reps_left: 4, reps_right: 3,                  // hammer_curl only
 *   keypoints: [{ points: [[x,y], …], edges: [[i,j], …] }]  // normalized 0-1
 * }
 *
 * Two things are drawn:
 *   - the COCO-17 skeleton, as a `keypoints` layer. A bounding box would say
 *     nothing useful here; the skeleton is what shows whether the model is
 *     actually tracking the joints the rep counter reads.
 *   - a corner-pinned status card with the count. It stays put instead of
 *     riding on the athlete — a label attached to the person slides out of
 *     frame at the bottom of a squat, which is exactly when you want to read it.
 *
 * `points` are already normalized to the video frame and `edges` index into
 * that array, both produced device-side; nothing to convert here. Joints below
 * the confidence threshold are omitted upstream, so a partial skeleton (say,
 * upper body only) is expected rather than an error.
 *
 * Variables: ctx, data, canvas, img (provided by the preview host).
 */

var R = (typeof window !== 'undefined') && window.RecameraOverlay;
if (!R || typeof R.render !== 'function') {
  // Renderer not loaded — fail visibly rather than silently.
  ctx.fillStyle = 'rgba(200,0,0,0.8)';
  ctx.fillRect(10, 10, 320, 26);
  ctx.fillStyle = '#fff';
  ctx.font = '12px monospace';
  ctx.fillText('RecameraOverlay not loaded', 16, 28);
} else if (data) {
  var layers = [];

  // ---- Skeleton -----------------------------------------------------------
  var groups = data.keypoints || [];
  if (groups.length) {
    var kpItems = [];
    for (var g = 0; g < groups.length; g++) {
      var grp = groups[g];
      if (!grp || !grp.points || !grp.points.length) continue;
      kpItems.push({ points: grp.points, edges: grp.edges || [] });
    }
    if (kpItems.length) {
      layers.push({ type: 'keypoints', items: kpItems });
    }
  }

  // ---- Status card --------------------------------------------------------
  var metrics = [];
  if (data.exercise != null) metrics.push({ k: 'Exercise', v: data.exercise });
  if (data.set != null) {
    metrics.push({ k: 'Set', v: data.set + ' / ' + (data.target_sets != null ? data.target_sets : '?') });
  }
  if (data.stage != null) metrics.push({ k: 'Stage', v: data.stage });
  if (data.angle != null) metrics.push({ k: 'Angle', v: Math.round(data.angle) + '°' });
  // Hammer curl counts each arm; the set counter advances at the slower arm's pace.
  if (data.reps_left != null && data.reps_right != null) {
    metrics.push({ k: 'L / R', v: data.reps_left + ' / ' + data.reps_right });
  }

  var title = data.workout_complete
    ? 'DONE'
    : (data.reps != null ? data.reps : 0) + ' / ' + (data.target_reps != null ? data.target_reps : '?');

  // Green once counting, amber when nobody is being tracked — the colour
  // answers "is it seeing me?" without reading the rows.
  var tone = data.workout_complete ? 'ok' : (data.tracking ? 'ok' : 'warn');

  var card = { title: title, tone: tone, metrics: metrics };
  if (data.form_warning) card.banner = data.form_warning;

  layers.push({ type: 'card', variant: 'status', anchor: 'tl', data: card });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
