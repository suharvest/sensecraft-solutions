// Display-only projection. The backend remains responsible for all timing.
export function pipelineState(camera, work) {
  if (camera.status !== 'online') return {phase:null, key:'camera.disconnected', tone:'offline'};
  if (work.operating_mode==='preview' || work.detection_enabled===false) return {phase:null,key:'operation.preview',tone:'preview'};
  if (camera.algorithm_error || work.algorithm_error) return {phase:null, key:'camera.algorithmError', tone:'unknown'};
  if (camera.camera_changed || work.camera_changed || camera.regions_match === false) return {phase:null, key:'state.reconfirm', tone:'unknown'};
  if (!work.active && work.session_end != null && work.state !== 'START_PENDING') return {phase:'done', key:'state.done', tone:'done'};
  const states = {
    NOT_STARTED:{phase:'idle', key:'state.idle', tone:''},
    START_PENDING:{phase:'start', key:'state.start', tone:''},
    WORKING:{phase:'working', key:'state.working', tone:'working'},
    AWAY_PENDING:{phase:'pause', key:'state.away', tone:'away'},
    REST:{phase:'pause', key:'state.rest', tone:'rest'}
  };
  return states[work.state] || {phase:null, key:'state.unknown', tone:'unknown'};
}
