import {tr} from './i18n.js';
export const assemblyRegions=['pending','completed'];
export function modelBinding(model){return model?{model_id:model.id,sha256:model.sha256}:null;}
export function resetModelRules(material,model){return {...structuredClone(material),enabled:false,binding:modelBinding(model),rules:Object.fromEntries(assemblyRegions.map(r=>[r,{count:[],alert:[]}])),class_styles:{},confidence_by_class:{}};}
export function className(status,id){return status.class_styles?.[id]?.name||status.class_names?.[id]||String(id);}
export function assemblyRows(status){
 const rows=[];
 for(const region of assemblyRegions){
  const title=status.region_names?.[region]||tr('studio.'+region);
  if(status.by_class){for(const [id,n] of Object.entries(status.by_class[region]||{}))rows.push({group:region,title:title+' · '+className(status,id),value:status.available?n:'—'});}
  else rows.push({group:region,title,value:status.available?status[region]??'—':'—'});
 }
 for(const key of ['initial','added','cumulative'])rows.push({group:'production',title:tr('studio.'+key),value:status[key]??(key==='cumulative'?0:'—')});
 return rows;
}
export function renderAssemblyStatus(container,status){
 container.replaceChildren();
 for(const group of [...assemblyRegions,'production']){
  const section=document.createElement('section');section.className='assembly-group '+group;
  const heading=document.createElement('h3');heading.textContent=group==='production'?tr('operation.production'):(status.region_names?.[group]||tr('studio.'+group));section.append(heading);
  const rows=document.createElement('div');rows.className='assembly-values';
  for(const row of assemblyRows(status).filter(r=>r.group===group)){const item=document.createElement('div'),label=document.createElement('span'),value=document.createElement('strong');label.textContent=group==='production'?row.title:row.title.split(' · ').slice(1).join(' · ')||row.title;value.textContent=row.value;item.append(label,value);rows.append(item);}
  section.append(rows);container.append(section);
 }
 const note=(text,warning=false)=>{const e=document.createElement('span');e.className='material-note'+(warning?' assembly-alert':'');e.textContent=text;container.append(e);};
 if(!status.available)note(tr(status.detection_enabled===false?'operation.notDetected':'studio.unavailable'));
 if(status.available&&!status.session_id)note(tr('studio.noCountSession'));
 for(const a of status.alerts||[])note(tr('studio.zoneAlert',{region:status.region_names?.[a.region]||tr('studio.'+a.region),name:className(status,a.class_id)}),true);
 if(status.reviews?.length)note(tr('studio.reviewCount',{count:status.reviews.length}),true);
}

export function zoneCountRows(status,region){
 if(!status?.available || !status.by_class?.[region])return [];
 return Object.entries(status.by_class[region]).map(([id,value])=>({name:className(status,id),value}));
}
// Device totals already exclude ignored and alert-only classes. Never infer product sets.
export function zoneTotal(status,region,enabled=true){
 if(enabled===false || !status?.available)return null;
 const value=status[region];
 return Number.isFinite(value)&&value>=0?value:null;
}
export function completedAlertCount(status,enabled=true){
 if(enabled===false || !status?.available)return 0;
 const alerts=(status.alerts||[]).filter(a=>a.region==='completed'&&a.active===true);
 return new Set(alerts.map(a=>a.id)).size;
}
export function renderZoneCounts(container,status,region,enabled=true){
 container.replaceChildren();const value=document.createElement('strong');
 const total=zoneTotal(status,region,enabled);value.textContent=total===null?'—':String(total);
 container.append(value);
}
export function renderCompletedAlert(card,status,enabled=true){
 const count=completedAlertCount(status,enabled);card.hidden=count===0;
 card.querySelector('[data-alert-count]').textContent=String(count);
}

export function liveMaterials(camera,work){
 const status=work?.materials;
 if(!status)return null;
 if(camera?.status!=='online'||camera.algorithm_error||work.algorithm_error||camera.regions_match===false
   ||camera.camera_changed||work.camera_changed||work.detection_enabled===false||['training','preview'].includes(work.operating_mode)
   ||(work.config_revision!=null&&camera.config_revision!=null&&work.config_revision!==camera.config_revision))
   return {...status,available:false,alerts:[]};
 return status;
}
