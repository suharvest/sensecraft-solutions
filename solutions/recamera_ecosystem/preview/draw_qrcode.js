/**
 * QR Code Reader Overlay — ADAPTER
 *
 * Maps the qrcode-reader MQTT payload to a RecameraOverlay `model` and
 * delegates all drawing to the shared renderer (window.RecameraOverlay). This
 * file contains ONLY app-specific field mapping — no drawing primitives.
 *
 * Input (data): qrcode-reader MQTT message
 * {
 *   type: "qrcode", frame: 4821, qr_found: true, detect_cost_ms: 34.10,
 *   codes: [{
 *     text: "https://www.seeedstudio.com",
 *     points: [[x,y], [x,y], [x,y], [x,y]]   // normalized 0-1, stream frame
 *   }]
 * }
 *
 * The four corners come straight from quirc in winding order (top-left,
 * top-right, bottom-right, bottom-left for an upright code), already
 * normalized device-side against the video frame. A rotated code keeps the
 * same winding, so the quad is drawn as-is — do not sort or bounding-box it,
 * that is what loses the rotation the decoder worked out.
 *
 * NOTE: this replaces the adapter from the retired standalone solution, which
 * polled `GET /api/qr/latest` on a different application (qrcode-rec) that had
 * no corner data and could only draw a text panel.
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
  var codes = (data && data.codes) || [];

  // ---- One closed quad per decoded code, labelled with its payload ---------
  var polys = [];
  for (var i = 0; i < codes.length; i++) {
    var c = codes[i];
    if (!c || !Array.isArray(c.points) || c.points.length < 3) continue;
    var text = String(c.text == null ? '' : c.text);
    // Long payloads (URLs with query strings, vCards) would run off frame;
    // the full value is in the MQTT message for anything that needs it.
    var label = text.length > 48 ? text.slice(0, 47) + '…' : text;
    polys.push({ points: c.points, label: label });
  }
  if (polys.length) {
    layers.push({ type: 'polygons', items: polys });
  }

  // ---- Status card --------------------------------------------------------
  var metrics = [];
  metrics.push({ k: 'Codes', v: String(codes.length) });
  if (data.detect_cost_ms != null) {
    metrics.push({ k: 'Decode', v: Math.round(data.detect_cost_ms) + 'ms' });
  }
  if (data.frame != null) metrics.push({ k: 'Frame', v: String(data.frame) });

  var found = Boolean(data.qr_found) && codes.length > 0;
  layers.push({
    type: 'card',
    variant: 'status',
    anchor: 'tl',
    data: {
      // Green with a count once something decodes, amber while the view is
      // empty — the colour answers "is it reading anything?" at a glance.
      title: found ? codes.length + (codes.length === 1 ? ' code' : ' codes') : 'No code',
      tone: found ? 'ok' : 'warn',
      metrics: metrics,
    },
  });

  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
