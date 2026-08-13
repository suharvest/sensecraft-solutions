/**
 * Multi-person Fall Detection overlay — ADAPTER
 *
 * Shared by the reComputer J (Jetson), reComputer RK (RKNN) and reComputer R
 * (Hailo) presets. Maps their multi-stream fall-detection MQTT payload to a
 * RecameraOverlay `model` and delegates all drawing to the shared renderer
 * (window.RecameraOverlay). This file contains ONLY field mapping and the
 * coordinate-space correction — no drawing primitives.
 *
 * Why this is separate from draw_fall_detection.js (the reCamera adapter):
 * the two payloads agree on the top-level summary fields but differ on the
 * per-person shape. reCamera sends a ready-made `keypoints: [{points, edges}]`
 * group list; these runtimes send `persons[].pose17` and expect the consumer
 * to build the skeleton. They also track several people independently, so
 * each person gets a box and a state label rather than one global skeleton.
 *
 * Input (data): one Jetson MQTT message, published per processed frame to
 * `recamera/fall-detection/results/{stream_id}`
 * {
 *   timestamp: 1753689600123, frame_id: 4821, inference_time_ms: 24.3,
 *   stream_id: "cam-01",
 *   fall_detected: false, fall_event: false, event_id: 7,
 *   state: "normal",              // aggregate: normal|suspected|fallen|recovering
 *   person_detected: true, person_count: 2, fallen_count: 0, tracking: true,
 *   features: { … },              // highest-confidence person, compatibility field
 *   persons: [{
 *     track_id: 3, person_score: 0.91,
 *     fall_detected: false, fall_event: false, event_id: 0,
 *     state: "normal",
 *     bbox: [x, y, w, h],         // NORMALIZED, x/y are the CENTER
 *     pose17: [[x, y, conf], …],  // 17 COCO joints, normalized to the frame
 *     features: { torso_angle_deg, evidence_features, … }
 *   }]
 * }
 *
 * Coordinates: `bbox` x/y are the box CENTER (main/yolo_pose.cpp:133 divides
 * the midpoint of left/right by the source width), while the renderer's
 * `boxes` layer wants a top-left origin — hence the explicit conversion below.
 * `pose17` is already normalized to the frame, so points pass through unchanged.
 *
 * Joints below the keypoint threshold arrive as (0,0,0) rather than being
 * dropped, so a zero-confidence joint is skipped here; a partial skeleton is
 * expected during occlusion rather than an error.
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
  // COCO-17 skeleton. Indices follow main/pose.h's Joint enum, which is the
  // standard COCO ordering, so this edge list is shared with every other
  // COCO-17 pose overlay.
  var COCO_EDGES = [
    [15, 13], [13, 11], [16, 14], [14, 12], [11, 12],
    [5, 11], [6, 12], [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 6]
  ];

  var STATE_COLOR = {
    normal: '#38bdf8',
    suspected: '#facc15',
    fallen: '#ef4444',
    recovering: '#f97316'
  };

  // ---- Coordinate space -------------------------------------------------
  // Jetson normalizes pose17/bbox against the ORIGINAL frame. The RKNN and
  // Hailo runtimes normalize against the 640x640 LETTERBOXED model canvas and
  // say so in `coordinate_space`. Drawing the latter as if it were the former
  // squashes the skeleton towards the vertical centre, so invert the letterbox
  // here rather than mislabelling padded coordinates as original pixels.
  //
  // For a WxH source letterboxed into a square: the long side fills the canvas
  // and the short side occupies `ratio` of it, centred. Undo that on the short
  // axis only.
  var space = String(data.coordinate_space || '');
  var letterboxed = /letterbox/i.test(space);
  var aspect = (canvas && canvas.height) ? (canvas.width / canvas.height) : 1;
  var ratioX = 1, padX = 0, ratioY = 1, padY = 0;
  if (letterboxed && isFinite(aspect) && aspect > 0) {
    if (aspect >= 1) {            // landscape: height is padded
      ratioY = 1 / aspect; padY = (1 - ratioY) / 2;
    } else {                      // portrait: width is padded
      ratioX = aspect; padX = (1 - ratioX) / 2;
    }
  }
  function ux(x) { return ratioX === 1 ? x : (x - padX) / ratioX; }
  function uy(y) { return ratioY === 1 ? y : (y - padY) / ratioY; }

  var layers = [];
  var persons = data.persons || [];
  var kpItems = [];
  var boxItems = [];

  for (var i = 0; i < persons.length; i++) {
    var p = persons[i] || {};
    var state = p.state || 'normal';
    var color = STATE_COLOR[state] || STATE_COLOR.normal;

    // ---- Skeleton -------------------------------------------------------
    var pose = p.pose17 || [];
    if (pose.length) {
      var points = [];
      var valid = [];
      for (var j = 0; j < pose.length; j++) {
        var kp = pose[j] || [];
        var conf = kp.length > 2 ? kp[2] : 0;
        // Below-threshold joints are zeroed upstream, not omitted — drawing
        // them would staple the skeleton to the frame's top-left corner.
        var ok = conf > 0 && (kp[0] !== 0 || kp[1] !== 0);
        points.push(ok ? [ux(kp[0]), uy(kp[1])] : [kp[0] || 0, kp[1] || 0]);
        valid.push(ok);
      }
      var edges = [];
      for (var e = 0; e < COCO_EDGES.length; e++) {
        var a = COCO_EDGES[e][0], b = COCO_EDGES[e][1];
        if (valid[a] && valid[b]) edges.push([a, b]);
      }
      kpItems.push({ points: points, edges: edges, color: color });
    }

    // ---- Box ------------------------------------------------------------
    var bb = p.bbox;
    if (bb && bb.length >= 4) {
      // center → top-left, then out of letterbox space if needed
      var x0n = ux(bb[0] - bb[2] / 2), x1n = ux(bb[0] + bb[2] / 2);
      var y0n = uy(bb[1] - bb[3] / 2), y1n = uy(bb[1] + bb[3] / 2);
      var bx = x0n, by = y0n, bw = x1n - x0n, bh = y1n - y0n;
      var label = '#' + (p.track_id != null ? p.track_id : '?') + ' ' + state.toUpperCase();
      var pf = p.features || {};
      if (pf.torso_angle_deg != null) {
        label += ' ' + Math.round(pf.torso_angle_deg) + '°';
      }
      boxItems.push({
        bbox: { x: bx, y: by, w: bw, h: bh },
        label: label,
        trackId: p.track_id,
        color: color
      });
    }
  }

  if (kpItems.length) layers.push({ type: 'keypoints', items: kpItems });
  if (boxItems.length) layers.push({ type: 'boxes', items: boxItems });

  // ---- Status card ------------------------------------------------------
  // Corner-pinned rather than attached to a person: with several tracks the
  // aggregate state is what the operator is watching, and a label riding on
  // someone slides out of frame exactly when they hit the floor.
  var features = data.features || {};
  var metrics = [
    { k: 'State', v: data.state || 'normal' },
    { k: 'People', v: data.person_count != null ? data.person_count : 0 },
    { k: 'Fallen', v: data.fallen_count != null ? data.fallen_count : 0 },
    { k: 'Evidence', v: (features.evidence_features != null ? features.evidence_features : 0) + '/3' }
  ];
  if (data.stream_id) metrics.push({ k: 'Stream', v: data.stream_id });
  if (data.inference_time_ms != null) {
    metrics.push({ k: 'Infer', v: Math.round(data.inference_time_ms) + ' ms' });
  }

  var title = data.fall_detected ? 'FALL DETECTED' : (data.state || 'normal').toUpperCase();
  var tone = data.fall_detected ? 'alert' : (data.state === 'suspected' ? 'warn' : 'ok');
  var card = { title: title, tone: tone, metrics: metrics };
  // `fall_event` is true only on the transition into a confirmed event, so
  // this banner marks the edge rather than the whole time someone is down.
  if (data.fall_event) card.banner = 'New event #' + data.event_id;
  layers.push({ type: 'card', variant: 'status', anchor: 'tl', data: card });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
