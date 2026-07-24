/**
 * People-Flow Heatmap Overlay — ADAPTER
 *
 * Maps the yolo-detector MQTT payload to a RecameraOverlay `model` and delegates
 * all drawing to the shared renderer (window.RecameraOverlay). This file
 * contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): yolo-detector >= 0.4.0 results message (see main/mqtt_payload.cpp)
 * {
 *   timestamp, frame_id, inference_time_ms, detection_count,
 *   detections: [{
 *     class_id, class_name: "person", confidence,
 *     x, y, w, h,            // NORMALIZED CENTER coords
 *     track_id              // optional, present when tracking is on
 *   }],
 *   tracking: { active_tracks }   // optional
 * }
 * Legacy (< 0.4.0) payloads with persons[] (TOP-LEFT bbox + zone_occupancy) are
 * still accepted as a fallback.
 *
 * Renders a density heatmap (people positions accumulated across frames) under
 * person boxes, plus a metrics card. The shared renderer's heatmap layer is
 * STATELESS ([[x,y,weight],…]) by contract, so cross-frame accumulation lives
 * here in a small adapter-side window store (a decaying spatial grid), NOT in
 * the renderer. This preserves the 0.4.0 detections-schema adaptation.
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
  var GRID = 44;         // heatmap grid resolution (cell = 1/GRID of the frame)
  var DECAY = 0.94;      // per-frame heat decay
  var HEAT_MAX = 10;     // heat value that maps to weight 1.0
  var HEAT_MIN = 0.12;   // prune cells below this

  // ── Normalize both payload generations → { cx, cy, w, h (center), trackId, confidence } ──
  function parsePersons(d) {
    var out = [];
    if (Array.isArray(d.detections)) {
      for (var i = 0; i < d.detections.length; i++) {
        var det = d.detections[i];
        if (det.class_name !== 'person') continue;
        out.push({
          cx: det.x, cy: det.y, w: det.w, h: det.h,
          trackId: det.track_id, confidence: det.confidence || 0,
        });
      }
    } else if (Array.isArray(d.persons)) {
      for (var j = 0; j < d.persons.length; j++) {
        var p = d.persons[j];
        var b = p.bbox;
        if (!b) continue;
        var bx, by, bw, bh;
        if (Array.isArray(b)) { bx = b[0]; by = b[1]; bw = b[2]; bh = b[3]; }
        else { bx = b.x; by = b.y; bw = b.w; bh = b.h; }
        out.push({
          cx: bx + bw / 2, cy: by + bh / 2, w: bw, h: bh,
          trackId: p.track_id, confidence: p.confidence || 0,
        });
      }
    }
    return out;
  }

  var persons = parsePersons(data);

  // ── Adapter-side decaying spatial grid (renderer heatmap is stateless) ──
  if (typeof window !== 'undefined' && !window._heatGrid) window._heatGrid = {};
  var grid = (typeof window !== 'undefined') ? window._heatGrid : {};
  for (var key in grid) {
    if (!grid.hasOwnProperty(key)) continue;
    grid[key] *= DECAY;
    if (grid[key] < HEAT_MIN) delete grid[key];
  }
  for (var k = 0; k < persons.length; k++) {
    var gx = Math.min(GRID - 1, Math.max(0, Math.floor(persons[k].cx * GRID)));
    var gy = Math.min(GRID - 1, Math.max(0, Math.floor(persons[k].cy * GRID)));
    var gkey = gx + 'x' + gy;
    grid[gkey] = Math.min(HEAT_MAX, (grid[gkey] || 0) + 2);
  }

  var heatPoints = [];
  for (var ck in grid) {
    if (!grid.hasOwnProperty(ck)) continue;
    var parts = ck.split('x');
    var cx = (parseInt(parts[0], 10) + 0.5) / GRID;
    var cy = (parseInt(parts[1], 10) + 0.5) / GRID;
    heatPoints.push([cx, cy, Math.min(1, grid[ck] / HEAT_MAX)]);
  }

  // ── Person boxes (center → top-left) ──
  var boxItems = [];
  for (var m = 0; m < persons.length; m++) {
    var pr = persons[m];
    var item = {
      bbox: { x: pr.cx - pr.w / 2, y: pr.cy - pr.h / 2, w: pr.w, h: pr.h },
      color: '#8fc31f',
    };
    if (pr.trackId != null) item.trackId = pr.trackId;
    else item.confidence = pr.confidence;
    boxItems.push(item);
  }

  var layers = [];
  if (heatPoints.length) layers.push({ type: 'heatmap', points: heatPoints });
  if (boxItems.length) layers.push({ type: 'boxes', items: boxItems });

  // Metrics card (top-right).
  var count = data.detection_count != null
    ? persons.length
    : ((data.zone_occupancy && data.zone_occupancy.total) || persons.length);
  var metrics = [{ k: 'People', v: String(count) }];
  if (data.tracking && data.tracking.active_tracks != null) {
    metrics.push({ k: 'Tracks', v: String(data.tracking.active_tracks) });
  }
  metrics.push({ k: 'Heat cells', v: String(heatPoints.length) });
  if (data.inference_time_ms != null) {
    metrics.push({ k: 'Inference', v: (Number(data.inference_time_ms)).toFixed(0) + 'ms' });
  }
  layers.push({ type: 'card', variant: 'metrics', anchor: 'tr', data: { title: 'People Flow', metrics: metrics } });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
