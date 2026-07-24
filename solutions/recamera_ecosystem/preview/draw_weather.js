/**
 * Weather Classification Overlay — ADAPTER
 *
 * Maps the weather-classifier MQTT payload to a RecameraOverlay `model` and
 * delegates all drawing to the shared renderer (window.RecameraOverlay). This
 * file contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): weather classification MQTT message
 * {
 *   type: "classification", frame: 42,
 *   label: "foggy", class_id: 2, confidence: 0.8341,
 *   scores: { clear: 0.01, cloudy: 0.05, foggy: 0.83, rainy: 0.08, snowy: 0.03 },
 *   inference_time_ms: 12.1, total_ms: 17.02
 * }
 *
 * Whole-frame classification → a single classification card (top-left) plus a
 * small metrics card (top-right) for timing.
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
  var layers = [
    {
      type: 'card',
      variant: 'classification',
      anchor: 'tl',
      data: {
        label: data.label,
        confidence: data.confidence,
        scores: data.scores || {},
      },
    },
  ];

  // Optional timing metrics card (top-right).
  var metrics = [];
  if (data.inference_time_ms != null) metrics.push({ k: 'Inference', v: data.inference_time_ms + 'ms' });
  if (data.total_ms != null) metrics.push({ k: 'Total', v: data.total_ms + 'ms' });
  if (metrics.length) {
    layers.push({ type: 'card', variant: 'metrics', anchor: 'tr', data: { title: 'Weather AI', metrics: metrics } });
  }

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
