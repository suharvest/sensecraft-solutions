import {getJSON,operationToken} from './api.js';
import {tr,getLanguage,errorDetails} from './i18n.js';

export function productionView(work,material){
 const verified=material?.production_basis==='completion_events_v1';
 return {total:verified&&Number.isFinite(material.production_total)?material.production_total:null,
   fresh:!!material?.available, reviews:material?.reviews?.length||0};
}
export function reviewChoices(event){
 if(event.kind!=='review'||event.resolved)return [];
 if(event.review_reason==='counted_became_abnormal')return [-1,0];
 return event.review_reason==='label_conflict'||event.already_counted?[0]:[1,0];
}
export function createProductionPanel(){
 const $=id=>document.getElementById(id);let session=null,lastFetch=0,pending=false,history=null,selected=null,expanded=false,lastRendered='';
 const dialog=$('evidenceDialog');
 $('closeEvidence').onclick=()=>dialog.close();
 function show(event){
   selected=event;
   $('evidenceTitle').textContent=event.kind==='review'?tr('production.review'):tr('production.event.'+event.kind);
   $('evidenceReason').textContent=tr('production.reason.'+(event.review_reason||event.kind));
   $('evidenceMeta').textContent=new Date(event.timestamp*1000).toLocaleString(getLanguage())+' · '+tr('production.frame',{value:event.frame_sequence??'—'});
   const img=$('evidenceImage'),box=$('evidenceBox');img.hidden=true;box.hidden=true;
   img.onload=()=>{
     if(selected!==event)return;img.hidden=false;
     const g=event.evidence_geometry,b=event.bbox_xyxy;
     if(g?.image_size&&b){
       const [w,h]=g.image_size,[x,y]=g.source_offset;
       const left=Math.max(0,(b[0]-x)*g.scale),top=Math.max(0,(b[1]-y)*g.scale);
       Object.assign(box.style,{left:left/w*100+'%',top:top/h*100+'%',
         width:Math.max(0,Math.min(w,(b[2]-x)*g.scale)-left)/w*100+'%',
         height:Math.max(0,Math.min(h,(b[3]-y)*g.scale)-top)/h*100+'%'});box.hidden=false;
     }
   };
   if(event.evidence_frame_url)img.src=event.evidence_frame_url;else img.removeAttribute('src');
   $('evidenceMissing').hidden=!!event.evidence_frame_url;
   img.onerror=()=>{img.hidden=true;box.hidden=true;$('evidenceMissing').hidden=false;};
   $('evidenceResult').textContent='';$('evidenceActions').replaceChildren();
   for(const delta of reviewChoices(event)){
     const button=document.createElement('button');button.type='button';
     button.textContent=tr('production.resolve.'+delta);button.onclick=()=>resolve(event,delta);
     $('evidenceActions').append(button);
   }
   if(!dialog.open)dialog.showModal();
 }
 async function resolve(event,delta){
   const sid=session;const token=operationToken();
   for(const button of $('evidenceActions').children)button.disabled=true;
   try{
     await getJSON('/api/v1/materials/sessions/'+encodeURIComponent(sid)+'/adjustments',{
       method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,event_id:event.id,delta,expected_total:history.cumulative,
         reason:tr('production.resolve.'+delta)})});
     lastFetch=0;await refresh(sid);if(session===sid){const updated=history?.events.find(e=>e.id===event.id);if(updated)show(updated);}
   }catch(error){const details=errorDetails(error);$('evidenceResult').textContent=tr(details.key,details.params);
     for(const button of $('evidenceActions').children)button.disabled=false;}
 }
 function renderEvents(){
   const signature=JSON.stringify([history?.events,getLanguage(),expanded]);
   if(signature===lastRendered)return;lastRendered=signature;
   const root=$('productionEvents');root.replaceChildren();
   const events=(history?.events||[]).filter(e=>['completed','review','initial'].includes(e.kind));
   // Unresolved reviews stay visible even when newer completion events arrive.
   const ordered=[...events.filter(e=>e.kind==='review'&&!e.resolved).reverse(),
     ...events.filter(e=>e.kind!=='review'||e.resolved).reverse()].slice(0,expanded?undefined:6);
   $('moreEvents').hidden=events.length<=6;
   $('moreEvents').textContent=tr(expanded?'production.fewer':'production.more',{value:events.length});
   $('productionEventsEmpty').hidden=ordered.length>0;
   for(const event of ordered){
     const button=document.createElement('button');button.type='button';button.className='event-tile';
     button.dataset.kind=event.kind==='review'&&!event.resolved?'review':'complete';
     const label=document.createElement('strong'),time=document.createElement('span');
     label.textContent=event.resolved?tr('production.resolved'):tr('production.event.'+event.kind);
     time.textContent=new Date(event.timestamp*1000).toLocaleTimeString(getLanguage());
     button.append(label,time);button.onclick=()=>show(event);root.append(button);
   }
 }
 $('moreEvents').onclick=()=>{expanded=!expanded;renderEvents();};
 async function refresh(sid){
   if(!sid||pending)return;pending=true;
   try{const result=await getJSON('/api/v1/materials/sessions/'+encodeURIComponent(sid));
     if(session===sid){history=result;renderEvents();
       const updated=dialog.open&&selected?history.events.find(e=>e.id===selected.id):null;
       if(updated&&(updated.evidence_frame_url!==selected.evidence_frame_url||updated.resolved!==selected.resolved))show(updated);
     }}
   catch{if(session===sid){history=null;renderEvents();}}
   finally{lastFetch=Date.now();pending=false;}
 }
 window.addEventListener('languagechange',()=>{renderEvents();if(dialog.open&&selected)show(selected);});
 return (work,material)=>{
   const view=productionView(work,material);$('productionTotal').textContent=view.total??'—';
   $('evidenceWarning').hidden=!work?.evidence_error;
   $('productionFresh').textContent=tr(view.fresh?'production.current':'production.paused');
   $('productionReviewCount').textContent=tr('production.reviewCount',{value:view.reviews});
   const sid=work?.session_id||null;
   if(sid!==session){session=sid;history=null;lastFetch=0;expanded=false;renderEvents();if(dialog.open)dialog.close();}
   if(Date.now()-lastFetch>2000)refresh(sid);
 };
}
