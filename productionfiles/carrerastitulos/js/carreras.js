(()=>{'use strict';
const root=document.getElementById('ct-app');if(!root)return;
const $=s=>root.querySelector(s),modo=root.dataset.modo,fmt=n=>new Intl.NumberFormat('es-AR').format(n||0);
const form=$('#ct-filter-form');let page=1,pages=1,map=null,layer=null,seq=0,cartoControl=null;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function params(includePage=true){const p=new URLSearchParams(new FormData(form));if(modo==='ministerial')p.set('modo','ministerial');if(includePage)p.set('page',String(page));return p;}
async function get(base,p){const r=await fetch(base+'?'+p.toString(),{credentials:'same-origin'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
function makeButton(text,fn){const b=document.createElement('button');b.type='button';b.className='ct-btn ct-primary';b.textContent=text;b.addEventListener('click',fn);return b;}
function paintTable(payload){pages=payload.pages;$('#ct-status').textContent=fmt(payload.total)+' registros de oferta coincidentes';$('#ct-page').textContent='Página '+payload.page+' de '+pages;$('#ct-prev').disabled=page<=1;$('#ct-next').disabled=page>=pages;const body=$('#ct-rows');body.replaceChildren();for(const item of payload.data){const row=document.createElement('tr');for(const key of ['cueanexo','establecimiento','localidad','nivel','carrera','titulo']){const td=document.createElement('td');td.textContent=item[key]??'—';row.append(td);}const td=document.createElement('td');td.append(makeButton('Ver detalle',()=>detail(item.cueanexo)));row.append(td);body.append(row);}if(!payload.data.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=7;td.textContent='No se encontraron ofertas con los filtros seleccionados.';tr.append(td);body.append(tr);}}
function paintAnalysis(data){const cont=$('#ct-analisis');if(!cont)return;cont.replaceChildren();for(const [field,title] of [['region','Regiones educativas'],['departamento','Departamentos'],['localidad','Localidades'],['sector','Sector de gestión'],['nivel','Nivel'],['carrera','Carreras más ofrecidas'],['titulo','Títulos más frecuentes']]){const el=document.createElement('article'),h=document.createElement('h3');h.textContent=title;el.append(h);const max=Math.max(1,...(data[field]||[]).map(x=>x.ofertas));for(const x of data[field]||[]){const d=document.createElement('div');d.className='ct-bar';d.innerHTML='<div class="ct-bar-label"><span>'+esc(x.nombre)+'</span><b>'+fmt(x.ofertas)+'</b></div><div class="ct-bar-track"><div class="ct-bar-fill" style="width:'+Math.min(100,x.ofertas/max*100)+'%"></div></div>';el.append(d);}cont.append(el);}}

// CARTO Basemaps exige una API key para las teselas raster desde 2026.
// La clave pública de teselas se recibe desde el template en data-carto-key.
// Configurar restricciones por dominio en el panel de CARTO.
function createCartoLayer(style,apiKey){
 const attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attribution/" target="_blank" rel="noopener noreferrer">CARTO</a>';
 const prefix='rastertiles/'+style;
 return L.tileLayer('https://basemaps.cartocdn.com/'+prefix+'/{z}/{x}/{y}{r}.png?key='+encodeURIComponent(apiKey),{
   attribution,minZoom:3,maxZoom:20,maxNativeZoom:20,
   crossOrigin:true,keepBuffer:2,updateWhenIdle:true
 });
}
function initMap(){
 if(map)return true;
 if(typeof L==='undefined'){$('#ct-map').textContent='Leaflet no está disponible. Revisá la conexión o los archivos estáticos.';return false;}
 const apiKey=(root.dataset.cartoKey||'').trim();
 if(!apiKey){$('#ct-map').textContent='El mapa requiere configurar CARTO_BASEMAPS_API_KEY. Los resultados de carreras siguen disponibles en la tabla.';return false;}
 map=L.map('ct-map',{preferCanvas:true}).setView([-26.8,-60.5],7);
 const voyager=createCartoLayer('voyager',apiKey);
 const claro=createCartoLayer('light_all',apiKey);
 const oscuro=createCartoLayer('dark_all',apiKey);
 (modo==='ministerial'?claro:voyager).addTo(map);
 cartoControl=L.control.layers({'CARTO Voyager':voyager,'CARTO Claro':claro,'CARTO Oscuro':oscuro},null,{collapsed:true,position:'topright'}).addTo(map);
 layer=L.layerGroup().addTo(map);
 let warned=false;
 for(const base of [voyager,claro,oscuro])base.on('tileerror',()=>{if(!warned){warned=true;console.warn('CARTO: falló una tesela. Verificá la API key, restricciones de Referer y la consola de red.');}});
 return true;
}

function refreshMapSize(){if(!map)return;window.setTimeout(()=>map.invalidateSize({pan:false}),130);}
window.addEventListener('resize',refreshMapSize,{passive:true});
document.addEventListener('collapsed.lte.pushmenu',refreshMapSize);
document.addEventListener('shown.lte.pushmenu',refreshMapSize);
if(typeof window.jQuery!=='undefined'){
  window.jQuery(document).on('collapsed.lte.pushmenu shown.lte.pushmenu',refreshMapSize);
}
if(typeof ResizeObserver!=='undefined'){
  const mapBox=document.getElementById('ct-map');
  if(mapBox)new ResizeObserver(refreshMapSize).observe(mapBox);
}

function paintMap(data){
 const puntos=data.puntos||[];
 $('#ct-map-count').textContent=fmt(puntos.length)+' ubicaciones';
 if(!initMap())return;
 layer.clearLayers();const bounds=[];
 for(const p of puntos){
  const lat=Number(p.latitud),lng=Number(p.longitud);
  if(!Number.isFinite(lat)||!Number.isFinite(lng)||Math.abs(lat)>90||Math.abs(lng)>180||lat===0||lng===0)continue;
  const marker=L.marker([lat,lng]).addTo(layer);
  const node=document.createElement('div');node.textContent=(p.establecimiento||'Establecimiento')+' — '+(p.localidad||'')+' ('+p.cueanexo+')';
  const b=makeButton('Ver carreras',()=>detail(p.cueanexo));node.append(document.createElement('br'),b);marker.bindPopup(node);bounds.push([lat,lng]);
 }
 if(bounds.length)map.fitBounds(bounds,{padding:[22,22],maxZoom:12});
 setTimeout(()=>map.invalidateSize(),200);
}
async function detail(cue){try{const url=root.dataset.institucion.replace('CUEPLACEHOLDER',encodeURIComponent(cue)),item=await get(url,params(false));const div=$('#ct-detail');div.replaceChildren();const h=document.createElement('h2');h.textContent=item.establecimiento||cue;div.append(h);for(const [label,val] of [['CUEANEXO',item.cueanexo],['Localidad',item.localidad],['Departamento',item.departamento],['Región',item.region],['Sector',item.sector],['Domicilio',[(item.calle||''),(item.numero||'')].join(' ')],['Teléfono',item.telefono],['Correo',item.email]]){const p=document.createElement('p');p.textContent=label+': '+(val||'—');div.append(p);}const h3=document.createElement('h3');h3.textContent='Carreras y títulos ('+item.ofertas.length+')';div.append(h3);const ul=document.createElement('ul');for(const o of item.ofertas){const li=document.createElement('li');li.textContent=(o.carrera||'Carrera sin especificar')+' — '+(o.titulo||'Título sin especificar')+' ('+(o.nivel||'sin nivel')+')';ul.append(li);}div.append(ul);$('#ct-dialog').showModal();}catch(e){alert('No se pudo consultar el establecimiento. '+e.message);}}
async function refresh(){const id=++seq;$('#ct-status').textContent='Actualizando…';const p=params();$('#ct-csv').href=root.dataset.exportar+'?'+params(false).toString();const side=$('#ct-csv-side');if(side)side.href=$('#ct-csv').href;const jobs=[get(root.dataset.resultados,p),get(root.dataset.resumen,p),get(root.dataset.mapa,p)];if(modo==='ministerial')jobs.push(get(root.dataset.analisis,p));try{const out=await Promise.all(jobs);if(id!==seq)return;paintTable(out[0]);for(const [key,val]of Object.entries(out[1])){const target=root.querySelector('[data-kpi="'+key+'"]');if(target)target.textContent=fmt(val);}paintMap(out[2]);if(out[3])paintAnalysis(out[3]);}catch(e){if(id===seq)$('#ct-status').textContent='No se pudo consultar la información ('+e.message+'). Verificá la vista SQL y los permisos.';}}
for(const a of root.querySelectorAll('.ct-tab'))a.addEventListener('click',()=>{root.querySelectorAll('.ct-tab').forEach(x=>x.classList.remove('is-active'));a.classList.add('is-active');setTimeout(refreshMapSize,220);});
form.addEventListener('submit',e=>{e.preventDefault();page=1;refresh();});$('#ct-clear').addEventListener('click',()=>{form.reset();for(const sel of form.querySelectorAll('select'))sel.selectedIndex=-1;page=1;refresh();});$('#ct-prev').addEventListener('click',()=>{if(page>1){page--;refresh();}});$('#ct-next').addEventListener('click',()=>{if(page<pages){page++;refresh();}});$('#ct-close').addEventListener('click',()=>$('#ct-dialog').close());for(const sel of form.querySelectorAll('select'))sel.selectedIndex=-1;refresh();
})();
