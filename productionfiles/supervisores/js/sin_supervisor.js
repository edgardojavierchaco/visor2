/* SIGSE — capa opcional de ofertas del padrón sin supervisor. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let capa = null, controlador = null, pagina = 1, total = 0, perPage = 150;
  const toggle = $('sigseMostrarSin');
  if (!toggle) return;
  const estado = $('sigseSinEstado');
  const crear = (tag, value) => { const node = document.createElement(tag); node.textContent = String(value ?? ''); return node; };
  const limpiar = () => { if (capa) capa.clearLayers(); $('sigseSinFilas').replaceChildren(); };
  const recargar = async () => {
    if (controlador) controlador.abort();
    controlador = new AbortController();
    if (!toggle.checked) {
      limpiar(); $('sigseSinResumen').hidden = true; $('sigseSinTablaCont').hidden = true;
      estado.textContent = 'Capa desactivada.'; return;
    }
    const mapa = window.sigseMapaLeaflet?.();
    if (!mapa) return;
    if (!capa) capa = L.layerGroup().addTo(mapa);
    limpiar(); estado.textContent = 'Consultando las ofertas del padrón…';
    const params = new URLSearchParams({pagina: String(pagina)});
    for (const id of ['region','nivel']) {
      const value = $('filtro'+id[0].toUpperCase()+id.slice(1))?.value;
      if (value) params.set(id, value);
    }
    const q = $('filtroBusqueda')?.value?.trim();
    if (q) params.set('q',q.slice(0,80));
    try {
      const res = await fetch('/supreg/api/observatorio/sin-supervisor/?'+params, {
        credentials:'same-origin', signal:controlador.signal, headers:{'Accept':'application/json'}
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'No fue posible consultar el padrón.');
      total = data.total; perPage = data.por_pagina;
      estado.textContent = data.parcial ? 'Consulta parcial: el padrón supera el límite de seguridad. Acotá los filtros.' : 'Consulta realizada.';
      const resumen = $('sigseSinResumen'); resumen.hidden = false;
      resumen.textContent = `${total.toLocaleString('es-AR')} oferta(s) sin supervisor · ${data.sin_coordenadas} sin coordenadas · ${data.puntos_mostrados} punto(s) representados. ${data.parcial ? 'RESULTADO INCOMPLETO.' : ''}`;
      const cuerpo = $('sigseSinFilas');
      for (const row of data.filas) {
        const tr = document.createElement('tr');
        for (const key of ['regional','cueanexo','escuela','oferta']) tr.appendChild(crear('td',row[key]));
        cuerpo.appendChild(tr);
      }
      $('sigseSinTablaCont').hidden = false;
      for (const row of data.puntos) {
        const marker = L.circleMarker([row.lat,row.lon], {radius:7,color:'#7c2d12',weight:2,fillColor:'#fb923c',fillOpacity:.88});
        const contenido = document.createElement('div');
        for (const key of ['cueanexo','escuela','oferta','regional']) {
          const line = document.createElement('div'); line.appendChild(crear('strong', key+': '));
          line.appendChild(crear('span',row[key])); contenido.appendChild(line);
        }
        marker.bindPopup(contenido); marker.addTo(capa);
      }
      $('sigseSinPagina').textContent = `Página ${pagina} de ${Math.max(1,Math.ceil(total/perPage))}`;
      $('sigseSinPrev').disabled = pagina <= 1;
      $('sigseSinNext').disabled = pagina * perPage >= total;
    } catch (err) {
      if (err.name !== 'AbortError') {estado.textContent = err.message; $('sigseSinResumen').hidden=true; $('sigseSinTablaCont').hidden=true;}
    }
  };
  toggle.addEventListener('change', () => {pagina=1;recargar();});
  $('sigseSinPrev').addEventListener('click',()=>{ if(pagina>1){pagina--;recargar();} });
  $('sigseSinNext').addEventListener('click',()=>{if(pagina*perPage<total){pagina++;recargar();}});
  window.sigseSinSupervisorActualizar = ()=>{pagina=1;recargar();};
})();
