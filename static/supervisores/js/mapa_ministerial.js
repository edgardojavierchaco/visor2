document.addEventListener('DOMContentLoaded', () => {
  const aplicar = document.getElementById('mapaAplicar');
  const limpiar = document.getElementById('mapaLimpiar');
  aplicar?.addEventListener('click', () => window.mostrarCoberturaGeneral?.());
  limpiar?.addEventListener('click', () => {
    ['filtroRegion','filtroNivel','filtroSituacion','filtroBusqueda'].forEach(id => {const el=document.getElementById(id);if(el)el.value='';});
    window.mostrarCoberturaGeneral?.();
  });
  const params=new URLSearchParams(location.search);
  for (const key of ['region','nivel','situacion']) {
    const el=document.getElementById('filtro'+key.charAt(0).toUpperCase()+key.slice(1));
    if(el && params.get(key) && [...el.options].some(o=>o.value===params.get(key))) el.value=params.get(key);
  }
  if (params.get('q')) {const input=document.getElementById('filtroBusqueda');if(input)input.value=params.get('q').slice(0,80);}
  if ([...params.keys()].length) window.mostrarCoberturaGeneral?.();
});