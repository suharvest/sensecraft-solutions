/**
 * PP-OCR Overlay — ADAPTER
 *
 * Maps the ppocr-reader MQTT payload to a RecameraOverlay `model` and delegates
 * all drawing to the shared renderer (window.RecameraOverlay). This file
 * contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): ppocr-reader MQTT message (see main/mqtt_payload.cpp)
 * {
 *   timestamp, frame_id,
 *   inference_time_ms: { detection, recognition, total },   // OBJECT, not scalar
 *   text_count, frame_width, frame_height,
 *   texts: [{
 *     id: 0,
 *     box: [[x,y],[x,y],[x,y],[x,y]],   // 4 NORMALIZED points (quadrilateral)
 *     text: "Hello World",
 *     confidence: 0.95, det_confidence: 0.88
 *   }]
 * }
 *
 * Each text region → a polygon outline (the 4-point quad) labelled with the
 * recognized string. A metrics card (top-right) shows text count + timing.
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
  var texts = data.texts || [];
  var polyItems = [];

  for (var i = 0; i < texts.length; i++) {
    var item = texts[i];
    var box = item.box;
    if (!box || box.length < 3) continue;  // need >=3 points for a polygon

    polyItems.push({
      points: box,                              // already normalized [[x,y],...]
      stroke: '#8fc31f',
      fill: 'rgba(143,195,31,0.10)',
      label: item.text != null ? String(item.text) : undefined,
    });
  }

  var layers = [];
  if (polyItems.length) layers.push({ type: 'polygons', items: polyItems });

  // Metrics card (top-right): text count + per-stage timing.
  var t = data.inference_time_ms || {};
  var metrics = [];
  var textCount = data.text_count != null ? data.text_count : texts.length;
  metrics.push({ k: 'Texts', v: String(textCount) });
  if (t.detection != null) metrics.push({ k: 'Detect', v: t.detection + 'ms' });
  if (t.recognition != null) metrics.push({ k: 'Recog', v: t.recognition + 'ms' });
  if (t.total != null) metrics.push({ k: 'Total', v: t.total + 'ms' });
  layers.push({ type: 'card', variant: 'metrics', anchor: 'tr', data: { title: 'OCR', metrics: metrics } });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
