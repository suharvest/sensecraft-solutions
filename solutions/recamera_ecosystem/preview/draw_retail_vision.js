/**
 * Retail Vision Overlay — ADAPTER
 *
 * Maps the retail-vision MQTT payload to a RecameraOverlay `model` and delegates
 * all drawing to the shared renderer (window.RecameraOverlay). This file
 * contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): retail-vision MQTT message (see main/mqtt_payload.cpp)
 * {
 *   timestamp, frame_id, frame_width, frame_height, fps, inference_time_ms,
 *   zone: {
 *     occupancy_count, browsing_count, engaged_count, assist_count,
 *     peak_customer, avg_dwell_time, avg_engagement_time, avg_velocity,
 *     entry_count, exit_count
 *   },
 *   persons: [{
 *     track_id, confidence,
 *     bbox: { x, y, w, h },     // NORMALIZED TOP-LEFT (payload does center→top-left)
 *     velocity: { vx, vy, speed_m_s },
 *     state: "transient" | "dwelling" | "engaged" | "assistance",
 *     dwell_duration
 *   }]
 * }
 *
 * Each person → a box coloured by dwell state, labelled "#id State 8.9s".
 * A short per-track trajectory trail (path) is accumulated across frames in a
 * small adapter-side window store (the shared renderer's path/heatmap layers are
 * stateless by contract, so cross-frame accumulation lives in the adapter). A
 * metrics card (top-left) shows occupancy / entered / exited + state breakdown.
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
  var STATE_COLOR = {
    transient: '#9CA3AF', dwelling: '#4A90D9', browsing: '#4A90D9',
    engaged: '#F5A623', assistance: '#EF4444',
  };
  var TRAIL_MAX = 16;   // points kept per track
  var TRAIL_TTL = 45;   // frames a stale track's trail survives before pruning

  // ── Adapter-side trail accumulator (renderer path layer is stateless) ──
  if (typeof window !== 'undefined' && !window._retailTrails) window._retailTrails = {};
  var trails = (typeof window !== 'undefined') ? window._retailTrails : {};
  for (var id in trails) if (trails.hasOwnProperty(id)) trails[id].ttl -= 1;

  var persons = data.persons || [];
  var boxItems = [];
  var seen = {};

  for (var i = 0; i < persons.length; i++) {
    var p = persons[i];
    var bb = p.bbox;
    if (!bb) continue;
    var bx, by, bw, bh;
    if (Array.isArray(bb)) { bx = bb[0]; by = bb[1]; bw = bb[2]; bh = bb[3]; }
    else { bx = bb.x; by = bb.y; bw = bb.w; bh = bb.h; }

    var pstate = p.state || 'transient';
    var color = STATE_COLOR[pstate] || STATE_COLOR.transient;
    var stateLabel = pstate.charAt(0).toUpperCase() + pstate.slice(1);
    var dwell = (p.dwell_duration != null && p.dwell_duration > 0) ? ' ' + p.dwell_duration.toFixed(1) + 's' : '';

    boxItems.push({
      bbox: { x: bx, y: by, w: bw, h: bh },  // top-left, no conversion
      label: stateLabel + dwell,
      trackId: p.track_id,
      color: color,
    });

    // Accumulate normalized center into this track's trail.
    if (p.track_id != null) {
      var key = String(p.track_id);
      seen[key] = true;
      var cx = bx + bw / 2, cy = by + bh / 2;
      if (!trails[key]) trails[key] = { pts: [], color: color, ttl: TRAIL_TTL };
      trails[key].color = color;
      trails[key].ttl = TRAIL_TTL;
      var pts = trails[key].pts;
      pts.push([cx, cy]);
      if (pts.length > TRAIL_MAX) pts.shift();
    }
  }

  // Prune expired trails.
  for (var tid in trails) {
    if (trails.hasOwnProperty(tid) && trails[tid].ttl <= 0) delete trails[tid];
  }

  var pathItems = [];
  for (var k in trails) {
    if (trails.hasOwnProperty(k) && trails[k].pts.length >= 2) {
      pathItems.push({ points: trails[k].pts.slice(), color: trails[k].color });
    }
  }

  var layers = [];
  if (pathItems.length) layers.push({ type: 'path', items: pathItems });
  if (boxItems.length) layers.push({ type: 'boxes', items: boxItems });

  // Count card (top-left).
  var z = data.zone || {};
  var metrics = [
    { k: 'In zone', v: String(z.occupancy_count || 0) },
    { k: 'Entered', v: String(z.entry_count || 0) },
    { k: 'Exited', v: String(z.exit_count || 0) },
    { k: 'Browsing', v: String(z.browsing_count || 0) },
    { k: 'Engaged', v: String(z.engaged_count || 0) },
    { k: 'Need help', v: String(z.assist_count || 0) },
  ];
  layers.push({ type: 'card', variant: 'metrics', anchor: 'tl', data: { title: 'Retail People Flow', metrics: metrics } });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
