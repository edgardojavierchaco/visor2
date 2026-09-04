"use strict";
(() => {
  const error = document.getElementById("network-error");
  const report = (message) => { error.textContent = message; error.hidden = false; };
  if (window.jQuery && window.jQuery.fn.select2) {
    window.jQuery(".select2").select2({width: "100%"});
  }
  const notify = (el) => {
    if (window.jQuery && window.jQuery.fn.select2) window.jQuery(el).trigger("change.select2");
  };
  const fill = (select, data, value, label) => {
    if (!select) return;
    select.replaceChildren(new Option("Seleccione", ""));
    for (const item of data) select.add(new Option(item[label], item[value]));
    notify(select);
  };
  const get = async (url, signal) => {
    const response = await fetch(url, {signal, headers: {"Accept": "application/json"}});
    if (!response.ok || response.redirected || !response.headers.get("content-type")?.includes("application/json")) throw new Error("No se pudieron cargar las opciones. Compruebe su sesión y reintente.");
    return response.json();
  };
  const onChange = (element, handler) => {
    if (!element) return;
    if (window.jQuery && window.jQuery.fn.select2) window.jQuery(element).on("change", handler);
    else element.addEventListener("change", handler);
  };
  for (const form of document.querySelectorAll("[data-editor]")) {
    const field = (name) => form.querySelector(`[name="${name}"], [name="actividad-${name}"], [name="persona-${name}"]`);
    let catalogsController, localitiesController;
    const catalogs = async () => {
      catalogsController?.abort(); catalogsController = new AbortController();
      const url = new URL(form.dataset.catalogUrl, location.origin);
      url.searchParams.set("modalidad", field("modalidad")?.value || "");
      url.searchParams.set("nivel", field("niveles")?.value || "");
      try {
        const data = await get(url, catalogsController.signal);
        fill(field("ceic"), data.ceic, "c_ceic", "descripcion");
        fill(field("grado_anio"), data.grado, "c_grado_anio", "nombre_grado_anio");
        fill(field("secciones"), data.secciones, "c_seccion", "nombre_seccion");
      } catch (e) { if (e.name !== "AbortError") report(e.message); }
    };
    onChange(field("modalidad"), catalogs); onChange(field("niveles"), catalogs);
    onChange(field("provincia"), async () => {
      localitiesController?.abort(); localitiesController = new AbortController();
      fill(field("localidad"), [], "", "");
      const url = new URL(form.dataset.localitiesUrl, location.origin);
      url.searchParams.set("provincia", field("provincia").value);
      try { fill(field("localidad"), await get(url, localitiesController.signal), "c_localidad", "descrip_localidad"); }
      catch (e) { if (e.name !== "AbortError") report(e.message); }
    });
    const category = () => {
      const disabled = field("categoria")?.value === "NO DOCENTE";
      for (const name of ["grado_anio", "secciones", "espacios"]) {
        const el = field(name); if (!el) continue;
        el.disabled = disabled;
        if (disabled) { el.value = ""; notify(el); }
        el.closest("[data-field]").hidden = disabled;
      }
    };
    onChange(field("categoria"), category); category();
  }
  for (const form of document.querySelectorAll("form")) {
    form.addEventListener("submit", event => {
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
      if (form.dataset.submitting) { event.preventDefault(); return; }
      form.dataset.submitting = "1";
      for (const button of form.querySelectorAll('button[type="submit"],button:not([type])')) button.disabled = true;
    });
  }
  window.addEventListener("pageshow", () => {
    for (const form of document.querySelectorAll("form")) {
      delete form.dataset.submitting;
      for (const button of form.querySelectorAll("button")) button.disabled = false;
    }
  });
})();
