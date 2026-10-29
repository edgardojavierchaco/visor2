"use strict";
(() => {
  const root = document.querySelector("#sigse"); if (!root) return;
  const api = root.dataset.api; let controller = null; let current = 0;
  const select = id => document.getElementById(id);
  const number = n => new Intl.NumberFormat("es-AR").format(n ?? 0);
  const update = async () => {
    if (controller) controller.abort(); controller = new AbortController(); const id = ++current;
    const status = select("sigse-status"); status.textContent = "Actualizando indicadores…";
    const query = new URLSearchParams();
    for (const key of ["region", "nivel", "situacion"]) {
      const val = select("sigse-" + key).value; if (val) query.set(key, val);
    }
    try {
      const response = await fetch(api + "?" + query.toString(), {credentials:"same-origin",signal:controller.signal,headers:{Accept:"application/json"}});
      const data = await response.json(); if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo consultar");
      if (id !== current) return;
      for (const [key, value] of Object.entries(data.indicadores)) {
        const target = select("k-" + key); if (target) target.textContent = number(value);
      }
      const bars = select("sigse-bars"); bars.replaceChildren();
      const max = Math.max(1, ...data.regionales_detalle.map(r => r.supervisores));
      if (!data.regionales_detalle.length) {bars.textContent="No existen asignaciones para los filtros seleccionados.";}
      for (const reg of data.regionales_detalle) {
        const row = document.createElement("div"); row.className="sigse-bar-item";
        const label=document.createElement("span"); label.textContent=reg.region__nombre || "Sin nombre";
        const track=document.createElement("div"); track.className="sigse-bar-track";
        const fill=document.createElement("div"); fill.className="sigse-bar-fill"; fill.style.width=(100*reg.supervisores/max)+"%"; track.append(fill);
        const value=document.createElement("strong"); value.textContent=number(reg.supervisores);
        row.append(label,track,value); bars.append(row);
      }
      status.textContent="Indicadores actualizados · filtros aplicados a las asignaciones registradas.";
    } catch (err) {if (err.name === "AbortError") return; status.textContent="Error: " + (err.message || "No disponible");}
  };
  for (const key of ["region", "nivel", "situacion"]) select("sigse-" + key).addEventListener("change",update);
  select("sigse-clear").addEventListener("click",()=>{for (const key of ["region", "nivel", "situacion"]) select("sigse-"+key).value="";update();});
  select("sigse-refresh").addEventListener("click",update);update();
})();
