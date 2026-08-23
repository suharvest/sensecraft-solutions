/** Fall Detection overlay adapter for the shared reCamera renderer. */
var R = (typeof window !== 'undefined') && window.RecameraOverlay;
if (!R || typeof R.render !== 'function') {
  ctx.fillStyle = 'rgba(200,0,0,0.8)';
  ctx.fillRect(10, 10, 320, 26);
  ctx.fillStyle = '#fff';
  ctx.font = '12px monospace';
  ctx.fillText('RecameraOverlay not loaded', 16, 28);
} else if (data) {
  var layers = [];
  var groups = data.keypoints || [];
  var kpItems = [];
  for (var g = 0; g < groups.length; g++) {
    var grp = groups[g];
    if (grp && grp.points && grp.points.length) {
      kpItems.push({ points: grp.points, edges: grp.edges || [] });
    }
  }
  if (kpItems.length) layers.push({ type: 'keypoints', items: kpItems });

  var features = data.features || {};
  var metrics = [
    { k: 'State', v: data.state || 'normal' },
    { k: 'People', v: data.person_count != null ? data.person_count : 0 },
    { k: 'Evidence', v: (features.evidence_features != null ? features.evidence_features : 0) + '/3' }
  ];
  if (features.torso_angle_deg != null) {
    metrics.push({ k: 'Torso', v: Math.round(features.torso_angle_deg) + '°' });
  }
  var title = data.fall_detected ? 'FALL DETECTED' : (data.state || 'normal').toUpperCase();
  var tone = data.fall_detected ? 'alert' : (data.state === 'suspected' ? 'warn' : 'ok');
  var card = { title: title, tone: tone, metrics: metrics };
  if (data.fall_event) card.banner = 'New event #' + data.event_id;
  layers.push({ type: 'card', variant: 'status', anchor: 'tl', data: card });
  R.render(ctx, { layers: layers }, { width: canvas.width, height: canvas.height });
}
